"""Écrire une copie d'un fichier d'une manière choisie, et vérifier son empreinte.

  python -I -X utf8 outils/disque/placement/placer.py copier <source> <dest> --mode traite|entrelace
         [--morceau-kio 8192] [--brouillage-mio 256] [--journal j.json]
  python -I -X utf8 outils/disque/placement/placer.py empreinte <fichier> [--attendu SHA] [--casser]

Garde : la copie va sous ~/dev/essais/troncons/placement/, il doit rester 45 Go libres après,
et elle ne dépasse pas --plafond-go (12 par défaut, la règle de la séance du 2026-10-22).

Modes :
- traite : la taille du fichier est réservée d'avance (FileAllocationInfo puis fin de fichier posée ;
  NTFS choisit alors les grappes d'un coup, au lieu de les prendre au fil d'un fichier qui croît), puis
  une seule écriture séquentielle sans tampon (FILE_FLAG_NO_BUFFERING | FILE_FLAG_WRITE_THROUGH), par
  morceaux de 8 Mio, lus sans tampon dans la source. Aucun autre écrivain de ma part.
- entrelace : même réservation, mais la copie s'écrit par morceaux de 64 Kio, et après chaque morceau
  un morceau de 64 Kio est écrit dans un fichier de brouillage de 256 Mio (réservé lui aussi, réécrit en
  boucle). NTFS reste contigu pour la copie ; la FTL reçoit deux flux mêlés page à page.
- filet (amendement du 2026-10-22, 6 h 05) : comme le codeur `trc-codeur` écrit ses fichiers : écriture
  tamponnée par le cache de Windows (fichier ouvert normalement, qui croît, sans taille réservée), par
  morceaux de 8 Mio, au débit moyen du codeur (`--debit-mo-s`, 30 par défaut, celui de B20) ; le
  gestionnaire de cache écrit sur le disque à son rythme.

La taille du fichier doit être un multiple de 4 096 (c'est le cas des .trc, format aligné).

empreinte : SHA-256 par lectures sans tampon de 8 Mio (un fil lit, un fil hache), sans remplir le cache
de Windows. Témoin : sur un original dont l'empreinte est publiée par un autre outil (Get-FileHash,
`recoder.log`), elle doit être égale ; cassure (--casser) : un octet du premier morceau est changé avant
hachage, l'empreinte doit différer.
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import pathlib
import queue
import struct
import sys
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import carte  # noqa: E402
import commun  # noqa: E402

k32 = commun.k32
FILE_ALLOCATION_INFO, FILE_END_OF_FILE_INFO = 5, 6
ESSAIS = commun.ESSAIS


def ouvrir_ecriture(chemin, sans_tampon=True):
    flags = (commun.FILE_FLAG_NO_BUFFERING | commun.FILE_FLAG_WRITE_THROUGH) if sans_tampon else 0
    h = k32.CreateFileW(str(chemin), commun.GENERIC_WRITE | commun.GENERIC_READ, 0, None, 2, flags, None)  # CREATE_ALWAYS
    if h in (None, commun.INVALIDE):
        raise OSError(ctypes.get_last_error(), f"création de {chemin}")
    return h


def reserver(h, taille):
    v = ctypes.c_longlong(taille)
    if not k32.SetFileInformationByHandle(h, FILE_ALLOCATION_INFO, ctypes.byref(v), 8):
        raise OSError(ctypes.get_last_error(), "FileAllocationInfo")
    if not k32.SetFileInformationByHandle(h, FILE_END_OF_FILE_INFO, ctypes.byref(v), 8):
        raise OSError(ctypes.get_last_error(), "FileEndOfFileInfo")


def ecrire_a(h, tampon, decalage, longueur):
    nouv = ctypes.c_longlong()
    if not k32.SetFilePointerEx(h, decalage, ctypes.byref(nouv), 0):
        raise OSError(ctypes.get_last_error(), "SetFilePointerEx")
    ecrits = wt.DWORD()
    if not k32.WriteFile(h, tampon.p, longueur, ctypes.byref(ecrits), None) or ecrits.value != longueur:
        raise OSError(ctypes.get_last_error(), f"WriteFile à {decalage}")


def copier_filet(source, dest, morceau, debit_o_s):
    """Écriture tamponnée, au débit moyen imposé (pause après chaque morceau si l'on est en avance)."""
    taille = os.path.getsize(source)
    hs = commun.ouvrir_lecture(source)
    tampon = commun.Tampon(morceau)
    t0 = time.time()
    try:
        with open(dest, "wb", buffering=0) as g:
            pos = 0
            while pos < taille:
                n = min(morceau, taille - pos)
                commun.lire_a(hs, tampon, pos, n)
                g.write(ctypes.string_at(tampon.p, n))
                pos += n
                avance = pos / debit_o_s - (time.time() - t0)
                if avance > 0:
                    time.sleep(avance)
    finally:
        tampon.liberer()
        commun.fermer(hs)


def copier(source, dest, mode, morceau, brouillage_o, journal_p, debit_o_s=30e6, plafond_o=12e9):
    taille = os.path.getsize(source)
    if taille % 4096:
        raise SystemExit("taille non multiple de 4 096")
    if not str(pathlib.Path(dest).resolve()).replace("\\", "/").startswith(str(ESSAIS).replace("\\", "/")):
        raise SystemExit(f"destination hors de {ESSAIS} : refusé")
    libre = commun.place_libre()
    besoin = taille + (brouillage_o if mode == "entrelace" else 0)
    if libre - besoin < 45e9:
        raise SystemExit(f"place : {libre / 1e9:.1f} Go libres, il en resterait {(libre - besoin) / 1e9:.1f} < 45 : refusé")
    deja = sum(f.stat().st_size for f in ESSAIS.glob("*") if f.is_file()) if ESSAIS.exists() else 0
    if deja + besoin > plafond_o:
        raise SystemExit(f"{(deja + besoin) / 1e9:.1f} Go (dont {deja / 1e9:.1f} déjà sous {ESSAIS}) > {plafond_o / 1e9:.1f} Go "
                         "de fichiers temporaires (--plafond-go) : refusé")
    pathlib.Path(dest).parent.mkdir(parents=True, exist_ok=True)
    s0 = commun.smart()
    t0 = time.time()
    if mode == "filet":
        copier_filet(source, dest, morceau, debit_o_s)
    hs = commun.ouvrir_lecture(source)
    hd = ouvrir_ecriture(dest) if mode != "filet" else None
    hb = None
    tb = None
    tampon = commun.Tampon(morceau)
    try:
        if hd is not None:
            reserver(hd, taille)
        if mode == "entrelace":
            chemin_b = pathlib.Path(dest).with_suffix(".brouillage")
            hb = ouvrir_ecriture(chemin_b)
            reserver(hb, brouillage_o)
            tb = commun.Tampon(morceau)
            ctypes.memmove(tb.p, os.urandom(morceau), morceau)
        pos, pos_b = 0, (0 if hd is not None else taille)
        if hd is None:
            pos = taille
        while pos < taille:
            n = min(morceau, taille - pos)
            commun.lire_a(hs, tampon, pos, n)
            ecrire_a(hd, tampon, pos, n)
            pos += n
            if hb is not None:
                ecrire_a(hb, tb, pos_b, morceau)
                pos_b = (pos_b + morceau) % brouillage_o
    finally:
        tampon.liberer()
        commun.fermer(hs)
        if hd is not None:
            commun.fermer(hd)
        if hb is not None:
            commun.fermer(hb)
            tb.liberer()
            pathlib.Path(dest).with_suffix(".brouillage").unlink()
    duree = time.time() - t0
    s1 = commun.smart()
    grappe, total, _ = carte.geometrie(dest)
    ext = carte.extents(dest)
    r = {"outil": "outils/disque/placement/placer.py copier", "date": commun.maintenant(), "source": str(source).replace("\\", "/"),
         "dest": str(dest).replace("\\", "/"), "mode": mode, "morceau": morceau, "brouillage_o": brouillage_o if mode == "entrelace" else 0,
         "taille": taille, "secondes": duree, "mo_s": taille / duree / 1e6, "place_libre_avant": libre,
         "extents": len(ext), "lcn_moyen_frac": sum((e[2] + e[1] / 2) * e[1] for e in ext) / max(1, sum(e[1] for e in ext)) / total,
         "smart_avant": s0, "smart_apres": s1, "smart_ecart": commun.ecart_smart(s0, s1), "fin_ecriture_t": time.time()}
    if journal_p:
        pathlib.Path(journal_p).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"placer.py copier {mode} : {taille / 1e9:.3f} Go en {duree:.1f} s ({r['mo_s']:.0f} Mo/s), {len(ext)} extents, "
          f"LCN moyen {r['lcn_moyen_frac']:.3f}")
    return r


def empreinte(chemin, casser=False, morceau=8 << 20):
    taille = os.path.getsize(chemin)
    h = commun.ouvrir_lecture(chemin)
    q = queue.Queue(maxsize=4)
    tampons = [commun.Tampon(morceau) for _ in range(6)]
    libres = queue.Queue()
    for t in tampons:
        libres.put(t)
    sha = hashlib.sha256()
    erreur = []

    def hacher():
        premier = True
        while True:
            x = q.get()
            if x is None:
                return
            t, n = x
            b = bytearray(ctypes.string_at(t.p, n))
            if casser and premier:
                b[100] ^= 1
            premier = False
            sha.update(b)
            libres.put(t)

    th = threading.Thread(target=hacher)
    th.start()
    t0 = time.time()
    try:
        pos = 0
        while pos < taille:
            n = min(morceau, taille - pos)
            t = libres.get()
            lus = commun.lire_a(h, t, pos, -(-n // 4096) * 4096)
            if lus < n:
                erreur.append(pos)
                break
            q.put((t, n))
            pos += n
    finally:
        q.put(None)
        th.join()
        commun.fermer(h)
        for t in tampons:
            t.liberer()
    if erreur:
        raise RuntimeError(f"lecture courte à {erreur}")
    return sha.hexdigest(), time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("commande")
    ap.add_argument("chemins", nargs="+")
    ap.add_argument("--mode", default="traite")
    ap.add_argument("--morceau-kio", type=int)
    ap.add_argument("--brouillage-mio", type=int, default=256)
    ap.add_argument("--debit-mo-s", type=float, default=30.0)
    ap.add_argument("--plafond-go", type=float, default=12.0)
    ap.add_argument("--journal")
    ap.add_argument("--attendu")
    ap.add_argument("--casser", action="store_true")
    a = ap.parse_args()
    if a.commande == "copier":
        morceau = (a.morceau_kio or (64 if a.mode == "entrelace" else 8192)) * 1024
        copier(a.chemins[0], a.chemins[1], a.mode, morceau, a.brouillage_mio << 20, a.journal, a.debit_mo_s * 1e6, a.plafond_go * 1e9)
        return 0
    if a.commande == "empreinte":
        e, s = empreinte(a.chemins[0], a.casser)
        ok = (a.attendu is None) or (e == a.attendu)
        taille = os.path.getsize(a.chemins[0])
        print(f"SHA-256 {e} {a.chemins[0]} ({taille / s / 1e9:.2f} Go/s){'' if a.attendu is None else (' : ÉGALE à l’attendue' if ok else ' : DIFFÉRENTE de l’attendue')}{' (cassé)' if a.casser else ''}")
        if a.journal:
            pathlib.Path(a.journal).write_text(json.dumps({"fichier": a.chemins[0], "sha256": e, "attendu": a.attendu, "egale": ok, "casse": a.casser,
                                                           "secondes": s, "date": commun.maintenant()}, ensure_ascii=False), encoding="utf-8")
        return 0 if ok else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
