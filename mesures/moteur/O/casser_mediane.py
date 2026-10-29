"""Cassure de C3 (lot O) : une copie de gpt-oss-20b.trc où une seule médiane d'un seul expert change.

Pourquoi : la copie corrompue du lot E fait tomber le moteur dès le premier expert touché (décodage
faux, erreur fatale nommée) ; mais une médiane (MEDIANES, flux brut) faussée ne fait sortir aucune
voie de L : la production ne la voit pas (REPRISE-E, E2). Le témoin C3 doit alors la voir dans les
logits (empreintes des pas différentes), et le mode témoin dans l'empreinte de l'expert.

La médiane change de +1 (une échelle × 2 sur toute une ligne de la matrice gate) : faute plausible
d'un codeur. Le décalage se lit dans le fichier même (répertoire, table des flux de la partie, § 4.7,
§ 4.8), écrit ici depuis la spécification seule.

Usage : python -I -X utf8 mesures/moteur/O/casser_mediane.py <source.trc> <copie.trc> <couche> <expert> <ligne> <journal.json>
"""
from __future__ import annotations

import hashlib
import json
import shutil
import struct
import sys


def main() -> int:
    src, dst, couche, expert, ligne, journal = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
    with open(src, "rb") as f:
        tete = f.read(4096)
        assert tete[:8] == b"TRONCONS"
        experts = struct.unpack_from("<H", tete, 74)[0]
        sections = [struct.unpack_from("<QQ", tete, 136 + 16 * i) for i in range(8)]
        rep_dec = sections[3][0]
        f.seek(rep_dec + 64 * (couche * experts + expert))
        e = f.read(64)
        dec_troncon, = struct.unpack_from("<Q", e, 0)
        c, x = struct.unpack_from("<HH", e, 48)
        assert (c, x) == (couche, expert)
        f.seek(dec_troncon)
        partie = f.read(4096)
        n_flux, = struct.unpack_from("<H", partie, 10)
        cible = None
        for i in range(n_flux):
            sorte, matrice = partie[64 + 16 * i], partie[64 + 16 * i + 1]
            d, = struct.unpack_from("<I", partie, 64 + 16 * i + 4)
            if sorte == 0x01 and matrice == 0:
                cible = dec_troncon + d + ligne
        assert cible is not None, "flux MEDIANES de la matrice 0 introuvable"
    shutil.copyfile(src, dst)
    with open(dst, "r+b") as g:
        g.seek(cible)
        avant = g.read(1)[0]
        apres = (avant + 1) % 256
        g.seek(cible)
        g.write(bytes([apres]))
    v = {"outil": "casser_mediane.py", "source": src, "copie": dst, "couche": couche, "expert": expert, "matrice": 0, "ligne": ligne,
         "decalage_fichier": cible, "avant": avant, "apres": apres}
    with open(journal, "w", encoding="utf-8") as j:
        json.dump(v, j, ensure_ascii=False, indent=1)
    print(json.dumps(v, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
