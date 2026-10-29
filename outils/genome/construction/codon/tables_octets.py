"""Les fréquences des tables CODES_CTX lues dans les fichiers .trc, v1.0 et v1.2 (figure F2 du mémoire :
la carte des 256 octets avant et après le fondu du zéro).

Lecteur écrit depuis la seule spécification (ARCHITECTURE § 4.3 et § 4.6), indépendant de trc-format :
en-tête (sections au décalage 136 + 16 i), section TABLES (u32 n, u32 0, enregistrements de 8 octets
puis leur charge, empreinte64 finale vérifiée).

Écrit mesures/genome/construction/codon/tables-octets.csv : modele, version, couche, matrice, kappa,
octet, frequence (sur 4 096), pour les couches 0, L/2 et L − 1, et tables-octets.json (bilan : pour
chaque fichier v1.2, nombre de tables dont un octet portant un 8 a une fréquence non nulle, qui doit
être 0 ; pour chaque v1.0, masse des 31 octets portant un 8, sur 4 096).

  python -I -X utf8 outils/genome/construction/codon/tables_octets.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import struct

RACINE = pathlib.Path(__file__).resolve().parents[4]
T = pathlib.Path("~/dev/modeles/trc")
FICHIERS = [("20b", "1.0", T / "gpt-oss-20b.trc"), ("20b", "1.2", T / "gpt-oss-20b-v12.trc"),
            ("120b", "1.0", T / "gpt-oss-120b.trc"), ("120b", "1.2", T / "gpt-oss-120b-v12.trc")]
SORTIE = RACINE / "mesures/genome/construction/codon"


def porte_un_8(o: int) -> bool:
    return (o & 15) == 8 or (o >> 4) == 8


def lire_tables(p: pathlib.Path):
    with open(p, "rb") as f:
        tete = f.read(4096)
        assert tete[:8] == b"TRONCONS"
        version = struct.unpack_from("<HH", tete, 8)
        drapeaux, = struct.unpack_from("<I", tete, 12)
        couches, = struct.unpack_from("<H", tete, 72)
        dec, lon = struct.unpack_from("<QQ", tete, 136 + 16 * 2)
        f.seek(dec)
        b = f.read(lon)
    corps = b[:-8]
    assert hashlib.sha256(corps).digest()[:8] == b[-8:], "empreinte de TABLES"
    n, res = struct.unpack_from("<II", b, 0)
    assert res == 0
    p, tables = 8, []
    for _ in range(n):
        couche, matrice, sorte, ctx, tc, r = struct.unpack_from("<HBBBBH", b, p)
        p += 8
        taille = {1: 32, 2: 512, 3: 16}[tc]
        charge = b[p:p + taille]
        p += taille
        if tc in (1, 2):
            fr = list(struct.unpack_from(f"<{taille // 2}H", charge, 0))
            assert sum(fr) == 4096
        else:
            fr = None
        tables.append((couche, matrice, sorte, ctx, fr))
    assert p == len(corps)
    return version, drapeaux, couches, tables


def main() -> int:
    lignes, bilan = [], {}
    for modele, v, chemin in FICHIERS:
        version, drapeaux, couches, tables = lire_tables(chemin)
        assert f"{version[0]}.{version[1]}" == v, (chemin, version)
        codes = [t for t in tables if t[2] == 0x04]
        avec_8 = sum(1 for t in codes if any(t[4][o] for o in range(256) if porte_un_8(o)))
        masse_8 = [sum(t[4][o] for o in range(256) if porte_un_8(o)) for t in codes]
        bilan[f"{modele} v{v}"] = {"fichier": str(chemin), "drapeaux": drapeaux, "tables_codes": len(codes),
                                    "tables_avec_fente_pour_un_8": avec_8,
                                    "masse_des_octets_8_sur_4096": {"min": min(masse_8), "max": max(masse_8), "moyenne": sum(masse_8) / len(masse_8)}}
        garder = {0, couches // 2, couches - 1}
        for couche, matrice, _, ctx, fr in codes:
            if couche in garder:
                for o in range(256):
                    lignes.append({"modele": modele, "version": v, "couche": couche, "matrice": matrice, "kappa": ctx, "octet": o, "frequence": fr[o]})
    with open(SORTIE / "tables-octets.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)
    (SORTIE / "tables-octets.json").write_text(json.dumps({"outil": "outils/genome/construction/codon/tables_octets.py", "bilan": bilan}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(bilan, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
