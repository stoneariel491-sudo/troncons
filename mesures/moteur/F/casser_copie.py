"""Cassure C1 sur une vraie copie du fichier (§ 6.5 : « une médiane faussée dans une copie →
inexact détecté »). Copie le .trc, retourne le bit 0 de la première médiane de la matrice 0 du
tronçon (COUCHE, EXPERT) dans la copie, en lisant les décalages par le seul § 4 (en-tête →
RÉPERTOIRE → partie → table des flux), et rend le décalage absolu touché.

Usage : python -I -X utf8 casser_copie.py <source.trc> <copie.trc> <COUCHE> <EXPERT>
"""
import shutil, struct, sys

src, dst, c, x = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
shutil.copyfile(src, dst)
with open(dst, "r+b") as f:
    h = f.read(4096)
    assert h[:8] == b"TRONCONS"
    experts = struct.unpack_from("<H", h, 74)[0]
    rep = struct.unpack_from("<Q", h, 136 + 16 * 3)[0]
    f.seek(rep + 64 * (c * experts + x))
    e = f.read(64)
    dec = struct.unpack_from("<Q", e, 0)[0]
    assert struct.unpack_from("<HH", e, 48) == (c, x)
    f.seek(dec)
    p = f.read(4096)
    n_flux = struct.unpack_from("<H", p, 10)[0]
    for i in range(n_flux):
        sorte, mat = p[64 + 16 * i], p[65 + 16 * i]
        if sorte == 0x01 and mat == 0:
            off = struct.unpack_from("<I", p, 68 + 16 * i)[0]
            break
    else:
        raise SystemExit("flux MEDIANES de la matrice 0 introuvable")
    a = dec + off
    f.seek(a)
    b = f.read(1)[0]
    f.seek(a)
    f.write(bytes([b ^ 1]))
print(f"copie {dst} : octet {a} (tronçon ({c}, {x}), médiane 0 de la matrice 0) {b} -> {b ^ 1}")
