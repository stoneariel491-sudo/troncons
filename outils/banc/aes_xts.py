"""Débit du déchiffrement XTS-AES sur le processeur, par l'API CNG de Windows (bcrypt.dll), de 1 à N
fils : le coût logiciel de BitLocker, mesuré par un second chemin.

Pourquoi : le volume C: est chiffré par BitLocker et le filtre fvevol refuse BypassIO (01-machine,
§ 2.5). Chaque octet lu du disque traverse un déchiffrement XTS-AES. Si ce déchiffrement plafonne
près des 2,8 Go/s lus, il est un suspect du plafond du disque ; s'il va bien plus vite, il ne l'est
pas (sans rien prouver sur fvevol lui-même, qui peut découper ou sérialiser autrement).

Témoins :
  - vecteur connu de la norme IEEE 1619-2007, annexe B, vecteur 1 : clés nulles, ajustement 0,
    32 octets nuls -> 917cf69e bd68b2ec 9b9fe9a3 eadda692 cd43d2f5 9598ed85 8c02c265 2fbf922e ;
  - aller-retour chiffrer puis déchiffrer : le clair revient octet pour octet ;
  - --fausser change un octet de l'attendu : les deux témoins doivent tomber.

Bibliothèque standard seulement. Usage :
  python -I -X utf8 outils/banc/aes_xts.py [--cle 128|256] [--fils 1,2,4,8] [--mio 32] [--passes 3] [--fausser]
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import os
import statistics as st
import threading
import time

bc = ctypes.WinDLL("bcrypt")
BCRYPT_ALG_HANDLE = ctypes.c_void_p
for nom, args in {
    "BCryptOpenAlgorithmProvider": [ctypes.POINTER(ctypes.c_void_p), wt.LPCWSTR, wt.LPCWSTR, wt.ULONG],
    "BCryptSetProperty": [ctypes.c_void_p, wt.LPCWSTR, ctypes.c_void_p, wt.ULONG, wt.ULONG],
    "BCryptGenerateSymmetricKey": [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, wt.ULONG,
                                   ctypes.c_void_p, wt.ULONG, wt.ULONG],
    "BCryptEncrypt": [ctypes.c_void_p, ctypes.c_void_p, wt.ULONG, ctypes.c_void_p, ctypes.c_void_p, wt.ULONG,
                      ctypes.c_void_p, wt.ULONG, ctypes.POINTER(wt.ULONG), wt.ULONG],
    "BCryptDecrypt": [ctypes.c_void_p, ctypes.c_void_p, wt.ULONG, ctypes.c_void_p, ctypes.c_void_p, wt.ULONG,
                      ctypes.c_void_p, wt.ULONG, ctypes.POINTER(wt.ULONG), wt.ULONG],
}.items():
    getattr(bc, nom).argtypes = args
    getattr(bc, nom).restype = ctypes.c_long


def verifier(st_, quoi):
    if st_ != 0:
        raise OSError(f"{quoi} : NTSTATUS 0x{st_ & 0xffffffff:08x}")


def cle_xts(octets_cle, unite):
    alg = ctypes.c_void_p()
    verifier(bc.BCryptOpenAlgorithmProvider(ctypes.byref(alg), "XTS-AES", None, 0), "ouverture XTS-AES")
    k = ctypes.c_void_p()
    tampon = ctypes.create_string_buffer(octets_cle, len(octets_cle))
    verifier(bc.BCryptGenerateSymmetricKey(alg, ctypes.byref(k), None, 0, tampon, len(octets_cle), 0), "clé")
    u = wt.ULONG(unite)
    verifier(bc.BCryptSetProperty(k, "MessageBlockLength", ctypes.byref(u), 4, 0), "longueur d'unité")
    return k


def operer(fn, k, src, dst, n, ajustement):
    iv = ctypes.create_string_buffer(ajustement.to_bytes(8, "little"), 8)
    res = wt.ULONG()
    verifier(fn(k, src, n, None, iv, 8, dst, n, ctypes.byref(res), 0), fn.__name__)
    return res.value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cle", default="128")
    ap.add_argument("--fils", default="1,2,4,8")
    ap.add_argument("--mio", type=int, default=32)
    ap.add_argument("--morceau-kio", type=int, default=1024)
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--fausser", action="store_true")
    a = ap.parse_args()

    # Témoin 1 : vecteur connu (IEEE 1619-2007, annexe B, vecteur 1), unité de 32 octets.
    k0 = cle_xts(bytes(32), 32)
    src = ctypes.create_string_buffer(bytes(32), 32)
    dst = ctypes.create_string_buffer(32)
    operer(bc.BCryptEncrypt, k0, src, dst, 32, 0)
    attendu = bytes.fromhex("917cf69ebd68b2ec9b9fe9a3eadda692cd43d2f59598ed858c02c2652fbf922e")
    if a.fausser:
        attendu = bytes([attendu[0] ^ 1]) + attendu[1:]
    print(f"TEMOIN vecteur_ieee1619_1={'ok' if dst.raw == attendu else 'ECHEC'}")

    # Témoin 2 : aller-retour sur 1 Mio, unité de 4 Kio (secteur BitLocker sur disque 4K).
    lk = int(a.cle) // 8 * 2
    octets_cle = os.urandom(lk)
    k = cle_xts(octets_cle, 4096)
    clair = os.urandom(1 << 20)
    c = ctypes.create_string_buffer(clair, len(clair))
    chiffre = ctypes.create_string_buffer(len(clair))
    retour = ctypes.create_string_buffer(len(clair))
    operer(bc.BCryptEncrypt, k, c, chiffre, len(clair), 7)
    operer(bc.BCryptDecrypt, k, chiffre, retour, len(clair), 7)
    attendu2 = clair if not a.fausser else bytes([clair[0] ^ 1]) + clair[1:]
    print(f"TEMOIN aller_retour={'ok' if retour.raw == attendu2 else 'ECHEC'} change={chiffre.raw != clair}")

    # Débit : chaque fil déchiffre sa propre zone de --mio Mio, par morceaux de --morceau-kio.
    taille = a.mio << 20
    m = a.morceau_kio << 10
    for f in [int(x) for x in a.fils.split(",")]:
        # Une clé par fil (mêmes octets) : aucun état partagé entre fils dans CNG.
        zones = [(ctypes.create_string_buffer(os.urandom(1 << 20) * a.mio, taille), ctypes.create_string_buffer(taille),
                  cle_xts(octets_cle, 4096)) for _ in range(f)]
        debits = []
        for _ in range(a.passes):
            barriere = threading.Barrier(f + 1)

            def travail(z):
                s, d, kf = z
                base_s, base_d = ctypes.addressof(s), ctypes.addressof(d)
                barriere.wait()
                for o in range(0, taille, m):
                    operer(bc.BCryptDecrypt, kf, ctypes.c_void_p(base_s + o), ctypes.c_void_p(base_d + o), m, o // 4096)

            ts = [threading.Thread(target=travail, args=(z,)) for z in zones]
            for t in ts:
                t.start()
            barriere.wait()
            t0 = time.perf_counter()
            for t in ts:
                t.join()
            debits.append(f * taille / (time.perf_counter() - t0) / 1e9)
        print(f"RESULTAT op=xts_aes_{a.cle}_dechiffrer fils={f} morceau={m} go_s_mediane={st.median(debits):.3f} "
              f"go_s_min={min(debits):.3f} go_s_max={max(debits):.3f}", flush=True)


if __name__ == "__main__":
    main()
