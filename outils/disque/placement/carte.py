"""Carte d'un fichier .trc sur le volume : extents NTFS, répertoire des tronçons, projection.

Lecture seule, sans droit d'administrateur, sans lire les données du fichier (seulement ses
métadonnées NTFS par FSCTL_GET_RETRIEVAL_POINTERS, et l'en-tête plus le RÉPERTOIRE du .trc,
quelques centaines de Kio).

  python -I -X utf8 outils/disque/placement/carte.py extents <fichier> [--json sortie.json]
  python -I -X utf8 outils/disque/placement/carte.py projeter <fichier.trc> [--json sortie.json]
  python -I -X utf8 outils/disque/placement/carte.py temoin          (témoin et cassure)

« extents » : chaque extent (VCN de départ, nombre de grappes, LCN), la taille de grappe, la taille
du volume en grappes. « projeter » : en plus, chaque tronçon (décalage, longueur lue par le moteur
= longueur du niveau 0) projeté sur les extents : nombre de morceaux physiques (1 = la lecture tient
dans un extent), LCN de début, et le saut LCN entre lectures consécutives dans l'ordre de la phase
disque (`troncons disque --n 1500 --graine 20261017`, même xorshift64* que main.rs).

Témoin (sous-commande temoin) : sur un petit fichier écrit ici d'une traite, la somme des grappes
des extents égale ⌈taille / grappe⌉ ; la projection d'une lecture couvrant tout le fichier a autant
de morceaux que d'extents. Cassure : on retire un extent de la liste, le témoin doit tomber.
"""
import bisect
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import pathlib
import struct
import sys

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.CreateFileW.restype = wt.HANDLE
k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
k32.DeviceIoControl.argtypes = [wt.HANDLE, wt.DWORD, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD,
                                ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.GetDiskFreeSpaceW.argtypes = [wt.LPCWSTR, ctypes.POINTER(wt.DWORD), ctypes.POINTER(wt.DWORD),
                                  ctypes.POINTER(wt.DWORD), ctypes.POINTER(wt.DWORD)]

FSCTL_GET_RETRIEVAL_POINTERS = 0x00090073
FILE_READ_ATTRIBUTES = 0x80
PARTAGE = 0x1 | 0x2 | 0x4
OPEN_EXISTING = 3
ERROR_MORE_DATA = 234
INVALIDE = wt.HANDLE(-1).value


def geometrie(chemin):
    """(octets par grappe, grappes du volume, grappes libres) du volume qui porte `chemin`."""
    racine = os.path.splitdrive(os.path.abspath(chemin))[0] + "\\"
    spc, bps, libres, total = wt.DWORD(), wt.DWORD(), wt.DWORD(), wt.DWORD()
    if not k32.GetDiskFreeSpaceW(racine, ctypes.byref(spc), ctypes.byref(bps), ctypes.byref(libres), ctypes.byref(total)):
        raise OSError(ctypes.get_last_error(), "GetDiskFreeSpaceW")
    return spc.value * bps.value, total.value, libres.value


def extents(chemin):
    """Liste de (vcn, grappes, lcn) ; lcn = -1 pour un trou (fichier creux)."""
    h = k32.CreateFileW(str(chemin), FILE_READ_ATTRIBUTES, PARTAGE, None, OPEN_EXISTING, 0, None)
    if h == INVALIDE or h is None:
        raise OSError(ctypes.get_last_error(), f"CreateFileW {chemin}")
    try:
        sortie = []
        vcn = 0
        taille_tampon = 1 << 20
        tampon = ctypes.create_string_buffer(taille_tampon)
        while True:
            entree = struct.pack("<q", vcn)
            rendu = wt.DWORD()
            ok = k32.DeviceIoControl(h, FSCTL_GET_RETRIEVAL_POINTERS, entree, 8, tampon, taille_tampon, ctypes.byref(rendu), None)
            err = ctypes.get_last_error()
            if not ok and err != ERROR_MORE_DATA:
                if err == 38:  # ERROR_HANDLE_EOF : fichier vide ou résident dans la MFT
                    return sortie
                raise OSError(err, "FSCTL_GET_RETRIEVAL_POINTERS")
            n, = struct.unpack_from("<I", tampon, 0)
            depart, = struct.unpack_from("<q", tampon, 8)
            prec = depart
            for i in range(n):
                suivant, lcn = struct.unpack_from("<qq", tampon, 16 + 16 * i)
                sortie.append((prec, suivant - prec, lcn))
                prec = suivant
            if ok:
                return sortie
            vcn = prec
    finally:
        k32.CloseHandle(h)


# ------------------------------------------------------------------------------- le .trc

def repertoire(chemin):
    """RÉPERTOIRE du .trc (format § 4.7, trc-format/src/lib.rs) : entrées (couche, expert, décalage,
    longueur du niveau 0, longueur du niveau 1), empreinte64 du répertoire vérifiée."""
    with open(chemin, "rb") as f:
        tete = f.read(4096)
        couches, experts = struct.unpack_from("<HH", tete, 72)
        sections = [struct.unpack_from("<QQ", tete, 136 + 16 * i) for i in range(8)]
        dec, lg = sections[3]
        f.seek(dec)
        rb = f.read(lg)
    n = couches * experts
    assert lg == n * 64 + 8, (lg, n)
    attendue = struct.unpack_from("<Q", rb, n * 64)[0]
    calculee = struct.unpack_from("<Q", hashlib.sha256(rb[: n * 64]).digest()[:8])[0]
    assert attendue == calculee, "empreinte du RÉPERTOIRE"
    sortie = []
    for i in range(n):
        d, l0, l1 = struct.unpack_from("<QII", rb, 64 * i)
        c, x = struct.unpack_from("<HH", rb, 64 * i + 48)
        sortie.append((c, x, d, l0, l1))
    return {"couches": couches, "experts": experts, "sections": sections, "entrees": sortie}


class Tirage:
    """xorshift64* de moteur/bins/troncons/src/main.rs (fonction disque)."""

    def __init__(self, graine):
        self.x = (graine | 1) & 0xFFFFFFFFFFFFFFFF

    def suivant(self):
        x = self.x
        x ^= x >> 12
        x ^= (x << 25) & 0xFFFFFFFFFFFFFFFF
        x ^= x >> 27
        self.x = x
        return (x * 0x2545F4914F6CDD1D) & 0xFFFFFFFFFFFFFFFF


def ordre_disque(n_entrees, n, graine):
    """L'ordre des tronçons de `troncons disque` (mélange de Fisher-Yates, puis troncature)."""
    ordre = list(range(n_entrees))
    t = Tirage(graine)
    for i in range(n_entrees - 1, 0, -1):
        j = t.suivant() % (i + 1)
        ordre[i], ordre[j] = ordre[j], ordre[i]
    return ordre[: min(n, n_entrees)]


def morceaux(ext, grappe, decalage, longueur, debuts=None):
    """Les morceaux physiques (lcn de début, octets) d'une lecture [decalage, decalage+longueur)."""
    if debuts is None:
        debuts = [e[0] for e in ext]
    v0 = decalage // grappe
    v1 = (decalage + longueur - 1) // grappe
    i = bisect.bisect_right(debuts, v0) - 1
    sortie = []
    while i < len(ext) and ext[i][0] <= v1:
        vcn, n, lcn = ext[i]
        a, b = max(v0, vcn), min(v1, vcn + n - 1)
        sortie.append((lcn + (a - vcn) if lcn >= 0 else -1, (b - a + 1) * grappe))
        i += 1
    return sortie


def projeter(chemin, graine=20261017, n=1500):
    grappe, total, libres = geometrie(chemin)
    ext = extents(chemin)
    debuts = [e[0] for e in ext]
    rep = repertoire(chemin)
    lectures = []
    for (c, x, d, l0, l1) in rep["entrees"]:
        m = morceaux(ext, grappe, d, l0, debuts)
        lectures.append({"couche": c, "expert": x, "decalage": d, "longueur": l0, "morceaux": len(m),
                         "lcn": m[0][0], "lcn_fin": m[-1][0] + m[-1][1] // grappe - 1,
                         "plus_petit_morceau": min(o for _, o in m)})
    ordre = ordre_disque(len(lectures), n, graine)
    sauts = [lectures[b]["lcn"] - lectures[a]["lcn_fin"] - 1 for a, b in zip(ordre, ordre[1:])]
    return grappe, total, libres, ext, rep, lectures, ordre, sauts


def resume(chemin, ext, grappe, total):
    taille = os.path.getsize(chemin)
    tailles = sorted(e[1] * grappe for e in ext)
    lcns = [e[2] for e in ext if e[2] >= 0]
    poids = sum(e[1] for e in ext)
    lcn_moyen = sum((e[2] + e[1] / 2) * e[1] for e in ext if e[2] >= 0) / max(1, poids)
    st = os.stat(chemin)
    return {
        "fichier": str(chemin).replace("\\", "/"), "taille": taille, "grappe": grappe, "grappes_volume": total,
        "extents": len(ext), "grappes": poids, "couverture_ok": poids == -(-taille // grappe),
        "extent_median_o": tailles[len(tailles) // 2] if tailles else 0,
        "extent_min_o": tailles[0] if tailles else 0, "extent_max_o": tailles[-1] if tailles else 0,
        "lcn_min_frac": min(lcns) / total if lcns else None, "lcn_max_frac": max(lcns) / total if lcns else None,
        "lcn_moyen_frac": lcn_moyen / total,
        "creation": getattr(st, "st_birthtime", st.st_ctime), "ecriture": st.st_mtime,
    }


def temoin(casser=False):
    d = pathlib.Path(os.environ.get("TEMP", ".")) / "troncons-placement-temoin"
    d.mkdir(exist_ok=True)
    f = d / "temoin.bin"
    with open(f, "wb") as g:
        for _ in range(16):
            g.write(os.urandom(1 << 20))
    grappe, total, _ = geometrie(f)
    ext = extents(f)
    if casser and ext:
        ext = ext[:-1]
    taille = os.path.getsize(f)
    ok1 = sum(e[1] for e in ext) == -(-taille // grappe)
    ok2 = len(morceaux(ext, grappe, 0, taille)) == len(ext) and len(ext) > 0
    f.unlink()
    print(f"témoin{' (cassé)' if casser else ''} : {len(ext)} extents, couverture {'tient' if ok1 else 'TOMBE'}, morceaux {'tient' if ok2 else 'TOMBE'}")
    return ok1 and ok2


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 2
    sortie = None
    if "--json" in a:
        i = a.index("--json")
        sortie = a[i + 1]
        del a[i:i + 2]
    if a[0] == "temoin":
        t = temoin(False)
        c = temoin(True)
        print("instrument :", "TIENT" if t and not c else "TOMBE")
        return 0 if t and not c else 1
    if a[0] == "extents":
        grappe, total, _ = geometrie(a[1])
        ext = extents(a[1])
        r = resume(a[1], ext, grappe, total)
        print(json.dumps(r, ensure_ascii=False))
        if sortie:
            r["liste"] = ext
            pathlib.Path(sortie).write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
        return 0
    if a[0] == "projeter":
        grappe, total, libres, ext, rep, lectures, ordre, sauts = projeter(a[1])
        r = resume(a[1], ext, grappe, total)
        r.update({
            "troncons": len(lectures), "lectures_coupees": sum(1 for l in lectures if l["morceaux"] > 1),
            "morceaux_total": sum(l["morceaux"] for l in lectures),
            "morceaux_par_lecture_max": max(l["morceaux"] for l in lectures),
            "octets_lus_par_lecture_moyen": sum(l["longueur"] for l in lectures) / len(lectures),
            "phase_disque": {"graine": 20261017, "n": len(ordre),
                             "lectures_coupees": sum(1 for i in ordre if lectures[i]["morceaux"] > 1),
                             "morceaux": sum(lectures[i]["morceaux"] for i in ordre),
                             "octets": sum(lectures[i]["longueur"] for i in ordre),
                             "saut_lcn_abs_median": sorted(abs(s) for s in sauts)[len(sauts) // 2],
                             "sauts_negatifs": sum(1 for s in sauts if s < 0)},
        })
        print(json.dumps(r, ensure_ascii=False))
        if sortie:
            r["liste_extents"] = ext
            r["lectures"] = [[l["couche"], l["expert"], l["decalage"], l["longueur"], l["morceaux"], l["lcn"], l["plus_petit_morceau"]] for l in lectures]
            pathlib.Path(sortie).write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
