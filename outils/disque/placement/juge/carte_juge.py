"""Carte d'un .trc pour le juge du placement disque : extents NTFS, RÉPERTOIRE, ordre du moteur, tirages.

Écrit pour le juge (00-seuils-declares.md § 2), sans rien importer de carte.py.

  python -I -X utf8 outils/disque/placement/juge/carte_juge.py carte <fichier> [--json sortie.json]
  python -I -X utf8 outils/disque/placement/juge/carte_juge.py temoin

- extents : FSCTL_GET_RETRIEVAL_POINTERS (0x00090073) sur une poignée ouverte avec le seul droit
  FILE_READ_ATTRIBUTES (aucune lecture de données, aucun administrateur). Chaque extent : (VCN, grappes, LCN).
- RÉPERTOIRE : en-tête de 4 096 octets (couches u16 à 72, experts u16 à 74, sections (décalage u64, longueur
  u64) à 136 + 16 i, i = 3 pour le RÉPERTOIRE), entrées de 64 octets (décalage u64 à 0, longueurs des niveaux
  u32 à 8 et 12, couche u16 à 48, expert u16 à 50), puis l'empreinte64 des entrées (8 premiers octets, petit
  boutiste, du SHA-256), vérifiée (trc-format, `serialiser_repertoire`).
- ordre du moteur : `troncons disque --graine G` : Fisher-Yates de i = n − 1 à 1, j = x mod (i + 1), x tiré par
  xorshift64* d'état initial G | 1 (main.rs, `Tirage`, `disque`).
- témoin : sur chaque fichier, somme des grappes = ⌈taille / grappe⌉ ; liste égale à celle de
  `fsutil file queryextents` (chemin de Windows). Cassure : un extent retiré, les deux tombent.
"""
import bisect
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import pathlib
import re
import struct
import subprocess
import sys

_k = ctypes.WinDLL("kernel32", use_last_error=True)
_k.CreateFileW.restype = ctypes.c_void_p
_k.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, ctypes.c_void_p]
_k.DeviceIoControl.restype = wt.BOOL
_k.DeviceIoControl.argtypes = [ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD,
                               ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
_k.CloseHandle.argtypes = [ctypes.c_void_p]
_k.GetDiskFreeSpaceExW.argtypes = [wt.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
_k.GetDiskFreeSpaceW.argtypes = [wt.LPCWSTR] + [ctypes.POINTER(wt.DWORD)] * 4
_INVALIDE = ctypes.c_void_p(-1).value
GRAINE_JUGE = 1618033


def grappe_et_volume(racine="C:\\"):
    a, b, c, d = wt.DWORD(), wt.DWORD(), wt.DWORD(), wt.DWORD()
    if not _k.GetDiskFreeSpaceW(racine, ctypes.byref(a), ctypes.byref(b), ctypes.byref(c), ctypes.byref(d)):
        raise OSError(ctypes.get_last_error(), "GetDiskFreeSpaceW")
    return a.value * b.value, d.value


def extents(chemin):
    h = _k.CreateFileW(str(chemin), 0x80, 0x7, None, 3, 0, None)
    if h in (None, _INVALIDE):
        raise OSError(ctypes.get_last_error(), f"ouverture de {chemin}")
    sortie = []
    try:
        vcn_depart = 0
        taille = 1 << 22
        tampon = ctypes.create_string_buffer(taille)
        while True:
            rendu = wt.DWORD()
            ok = _k.DeviceIoControl(h, 0x00090073, ctypes.byref(ctypes.c_longlong(vcn_depart)), 8, tampon, taille,
                                    ctypes.byref(rendu), None)
            e = ctypes.get_last_error()
            if not ok and e not in (234,):  # ERROR_MORE_DATA
                if e == 38:  # fin de fichier : fichier vide ou résident
                    return sortie
                raise OSError(e, "FSCTL_GET_RETRIEVAL_POINTERS")
            # RETRIEVAL_POINTERS_BUFFER : ExtentCount (u32), 4 octets de bourrage, StartingVcn (i64), puis paires
            # (NextVcn i64, Lcn i64)
            n = struct.unpack_from("<I", tampon, 0)[0]
            vcn = struct.unpack_from("<q", tampon, 8)[0]
            for i in range(n):
                suivant, lcn = struct.unpack_from("<qq", tampon, 16 + 16 * i)
                sortie.append((vcn, suivant - vcn, lcn))
                vcn = suivant
            if ok:
                return sortie
            vcn_depart = vcn
    finally:
        _k.CloseHandle(h)


def extents_fsutil(chemin):
    """La liste de `fsutil file queryextents` (chemin de Windows, indépendant de mon appel)."""
    s = subprocess.run(["fsutil", "file", "queryextents", str(chemin).replace("/", "\\")], capture_output=True).stdout
    s = s.decode("utf-8", errors="replace") if s else ""
    l = []
    for ligne in s.splitlines():
        v = re.findall(r"0x[0-9a-fA-F]+|-1\b", ligne)
        if len(v) == 3:
            vcn, n, lcn = (int(x, 16) if x.startswith("0x") else int(x) for x in v)
            l.append((vcn, n, lcn))
    return l


def repertoire(chemin):
    with open(chemin, "rb") as f:
        tete = f.read(4096)
        couches, experts = struct.unpack_from("<HH", tete, 72)
        dec, lg = struct.unpack_from("<QQ", tete, 136 + 16 * 3)
        f.seek(dec)
        corps = f.read(lg)
    n = couches * experts
    if lg != 64 * n + 8:
        raise ValueError(f"RÉPERTOIRE de {lg} octets pour {n} entrées")
    attendu = struct.unpack_from("<Q", corps, 64 * n)[0]
    if attendu != int.from_bytes(hashlib.sha256(corps[:64 * n]).digest()[:8], "little"):
        raise ValueError("empreinte64 du RÉPERTOIRE fausse")
    entrees = []
    for i in range(n):
        d, l0, l1 = struct.unpack_from("<QII", corps, 64 * i)
        c, x = struct.unpack_from("<HH", corps, 64 * i + 48)
        entrees.append({"i": i, "couche": c, "expert": x, "decalage": d, "longueur": l0, "longueur1": l1})
    return {"couches": couches, "experts": experts, "entrees": entrees,
            "empreinte": hashlib.sha256(corps).hexdigest()}


def ordre_moteur(n, graine=20261017):
    """L'ordre de `troncons disque --graine` (main.rs)."""
    masque = (1 << 64) - 1
    x = (graine | 1) & masque
    o = list(range(n))
    for i in range(n - 1, 0, -1):
        x ^= x >> 12
        x = (x ^ (x << 25)) & masque
        x ^= x >> 27
        j = ((x * 0x2545F4914F6CDD1D) & masque) % (i + 1)
        o[i], o[j] = o[j], o[i]
    return o


def tirage(indices, k, sel=""):
    """Mon tirage déclaré : rangement par SHA-256(« juge-placement:1618033:<sel><i> »), k premiers."""
    cle = lambda i: hashlib.sha256(f"juge-placement:{GRAINE_JUGE}:{sel}{i}".encode()).digest()
    return sorted(indices, key=cle)[:k]


def morceaux(ext, debuts, grappe, decalage, longueur):
    """Nombre d'extents que touche [decalage, decalage + longueur)."""
    v0, v1 = decalage // grappe, (decalage + longueur - 1) // grappe
    i = bisect.bisect_right(debuts, v0) - 1
    j = bisect.bisect_right(debuts, v1) - 1
    return j - i + 1


def carte(chemin):
    grappe, total = grappe_et_volume()
    ext = extents(chemin)
    taille = os.path.getsize(chemin)
    debuts = [e[0] for e in ext]
    rep = repertoire(chemin)
    for e in rep["entrees"]:
        e["morceaux"] = morceaux(ext, debuts, grappe, e["decalage"], e["longueur"])
    tailles = sorted(n * grappe for _, n, _ in ext)
    st = os.stat(chemin)
    return {"fichier": str(chemin).replace("\\", "/"), "taille": taille, "grappe": grappe, "grappes_volume": total,
            "extents": len(ext), "couverture": sum(n for _, n, _ in ext) == -(-taille // grappe),
            "extent_median_o": tailles[len(tailles) // 2], "lcn_moyen_frac": sum((l + n / 2) * n for _, n, l in ext) / sum(n for _, n, _ in ext) / total,
            "ecrit": st.st_mtime, "cree": getattr(st, "st_birthtime", None),
            "troncons": len(rep["entrees"]), "coupes": sum(1 for e in rep["entrees"] if e["morceaux"] > 1),
            "empreinte_repertoire": rep["empreinte"], "liste": ext, "repertoire": rep}


def temoin(fichiers):
    """Témoins (couverture, égalité à fsutil) et leur cassure, sur des fichiers existants."""
    grappe, _ = grappe_et_volume()
    r = []
    for f in fichiers:
        ext = extents(f)
        taille = os.path.getsize(f)
        fs = extents_fsutil(f) if len(ext) < 1000 else None
        cas = {"fichier": str(f), "extents": len(ext),
               "couverture": sum(n for _, n, _ in ext) == -(-taille // grappe),
               "egal_fsutil": (fs == ext) if fs is not None else None}
        casse = ext[:-1]
        cas["cassure_couverture_tombe"] = sum(n for _, n, _ in casse) != -(-taille // grappe)
        cas["cassure_fsutil_tombe"] = (fs != casse) if fs is not None else None
        r.append(cas)
    return r


def main():
    a = sys.argv[1:]
    if a and a[0] == "carte":
        c = carte(a[1])
        sortie = a[a.index("--json") + 1] if "--json" in a else None
        print(json.dumps({k: v for k, v in c.items() if k not in ("liste", "repertoire")}, ensure_ascii=False))
        if sortie:
            pathlib.Path(sortie).write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
        return 0
    if a and a[0] == "temoin":
        print(json.dumps(temoin(a[1:]), ensure_ascii=False, indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
