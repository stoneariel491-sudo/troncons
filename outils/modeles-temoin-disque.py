"""Témoin du compteur de disque de modeles-base.py (PDH, PhysicalDisk(_Total) / Disk Read Bytes/sec).

Cas à réponse connue : lire N octets d'un fichier sans tampon (FILE_FLAG_NO_BUFFERING, blocs de
1 Mio alignés) force N octets de lecture disque ; le compteur doit en voir au moins N, au-dessus de
la charge de repos. Cas qui doit faire tomber l'instrument naïf : relire le même fichier par lecture
ordinaire deux fois ; la seconde lecture est servie par le cache de Windows et le compteur ne doit
presque rien voir de plus que le repos.

Seuils déclarés avant l'exécution :
  - sans tampon : octets vus − repos × durée ≥ 0,95 × N (5 % pour l'imprécision de l'intégration
    à 0,5 s sur des passes de quelques secondes) ;
  - seconde lecture ordinaire : octets vus − repos × durée ≤ 0,10 × N.

Usage : python -I modeles-temoin-disque.py <fichier de quelques centaines de Mo> <sortie.json>
"""
import ctypes
import ctypes.wintypes as wt
import importlib.util
import json
import os
import sys
import time

_spec = importlib.util.spec_from_file_location(
    "modeles_base", os.path.join(os.path.dirname(os.path.abspath(__file__)), "modeles-base.py"))
mb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mb)

GENERIC_READ = 0x80000000
FILE_SHARE_READ = 1
OPEN_EXISTING = 3
FILE_FLAG_NO_BUFFERING = 0x20000000
BLOC = 1 << 20


def lire_sans_tampon(chemin):
    k = ctypes.windll.kernel32
    k.CreateFileW.restype = wt.HANDLE
    k.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
    k.VirtualAlloc.restype = ctypes.c_void_p
    k.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, wt.DWORD]
    k.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wt.DWORD]
    k.ReadFile.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
    k.CloseHandle.argtypes = [wt.HANDLE]
    h = k.CreateFileW(chemin, GENERIC_READ, FILE_SHARE_READ, None, OPEN_EXISTING, FILE_FLAG_NO_BUFFERING, None)
    if h is None or h == ctypes.c_void_p(-1).value:
        raise OSError("CreateFileW")
    tampon = k.VirtualAlloc(None, BLOC, 0x3000, 0x04)  # aligné sur la page
    lus, n = 0, wt.DWORD()
    while k.ReadFile(h, tampon, BLOC, ctypes.byref(n), None) and n.value:
        lus += n.value
    k.CloseHandle(h)
    k.VirtualFree(tampon, 0, 0x8000)
    return lus


def lire_ordinaire(chemin):
    lus = 0
    with open(chemin, "rb", buffering=0) as f:
        while True:
            b = f.read(BLOC)
            if not b:
                break
            lus += len(b)
    return lus


def passe(fonction, chemin, repos_o_s):
    c = mb.CompteurDisque()
    c.start()
    time.sleep(0.6)
    t0 = time.time()
    n = fonction(chemin)
    time.sleep(1.2)
    c.stop.set()
    c.join()
    vus = c.octets()
    return {"octets_lus_par_le_programme": n, "octets_vus": vus, "duree_s": c.duree(),
            "octets_attribuables": vus - repos_o_s * c.duree(), "secondes_lecture": time.time() - t0}


def main(chemin, sortie):
    c = mb.CompteurDisque()
    c.start()
    time.sleep(5)
    c.stop.set()
    c.join()
    repos = c.octets() / c.duree()
    N = os.path.getsize(chemin)
    sans = passe(lire_sans_tampon, chemin, repos)
    ordi1 = passe(lire_ordinaire, chemin, repos)
    ordi2 = passe(lire_ordinaire, chemin, repos)
    ok_sans = sans["octets_attribuables"] >= 0.95 * N
    ok_cache = ordi2["octets_attribuables"] <= 0.10 * N
    res = {"fichier": chemin, "taille": N, "repos_o_s": repos, "sans_tampon": sans,
           "ordinaire_1": ordi1, "ordinaire_2_cache": ordi2,
           "temoin_sans_tampon_vu": ok_sans, "temoin_cache_invisible": ok_cache,
           "date": time.strftime("%Y-%m-%d %H:%M:%S")}
    json.dump(res, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if (ok_sans and ok_cache) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
