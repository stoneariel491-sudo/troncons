"""Les experts routés par les fenêtres neuves que R1 n'a jamais routés (J-K, « ce que je publie de plus »).

Journal de routage de `juge reference --routage` (juge.rs) : u32 couches, u32 positions, puis, couche par
couche (ordre vérifié : la lecture « couche majeure » du journal de R1 rend 734 experts distincts, le
nombre de lectures d'experts du journal ref-openai-20b.json), pour chaque position, 4 × u8 experts et
une marge f32.

  python -I -X utf8 routage_juge.py NEUF.bin R1.bin
"""
import json
import pathlib
import struct
import sys

import numpy as np

DEPOT = pathlib.Path(__file__).resolve().parents[4]
JOURNAUX = DEPOT / "mesures" / "genome" / "construction" / "juge" / "kl"


def experts(chemin):
    b = pathlib.Path(chemin).read_bytes()
    L, P = struct.unpack_from("<II", b, 0)
    a = np.frombuffer(b, dtype=np.uint8, offset=8).reshape(L, P, 8)
    e = a[:, :, :4]
    s = {(l, int(x)) for l in range(L) for x in np.unique(e[l])}
    comptes = {}
    for l in range(L):
        u, c = np.unique(e[l], return_counts=True)
        for x, n in zip(u, c):
            comptes[(l, int(x))] = int(n)
    return L, P, s, comptes


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    neuf, r1 = sys.argv[1], sys.argv[2]
    Ln, Pn, sn, cn = experts(neuf)
    L1, P1, s1, c1 = experts(r1)
    nouveaux = sorted(sn - s1)
    jamais = sorted({(l, x) for l in range(Ln) for x in range(32)} - sn - s1)
    r = {"neuf": neuf.replace("\\", "/"), "r1": r1.replace("\\", "/"), "positions_neuf": Pn, "positions_r1": P1,
         "experts_routes_neuf": len(sn), "experts_routes_r1": len(s1), "routes_par_les_deux": len(sn & s1),
         "routes_par_le_neuf_seulement": len(nouveaux), "liste_neuf_seulement": [list(x) for x in nouveaux],
         "appels_aux_neuf_seulement": int(sum(cn[x] for x in nouveaux)), "appels_neuf": int(sum(cn.values())),
         "jamais_routes_par_les_vingt_fenetres": len(jamais), "liste_jamais": [list(x) for x in jamais]}
    (JOURNAUX / "routage-neuf-contre-r1.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print({k: v for k, v in r.items() if not k.startswith("liste")})


if __name__ == "__main__":
    main()
