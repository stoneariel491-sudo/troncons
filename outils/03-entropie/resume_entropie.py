"""Résumé des journaux de mesure_entropie.py : par type, par rôle, et pour le modèle.

Pour chaque groupe : octets stockés, bits/poids stockés, H0 des codes, H des codes
sachant le précédent et sachant l'échelle, longueur de Huffman (codes seuls, paires),
taille idéale d'ordre 0 de tout le bloc (codes + métadonnées), taux zstd/lz4 mesurés.
Les moyennes sont pondérées par le nombre de poids (entropies) ou d'octets (taux).

Usage : python resume_entropie.py <entropie-XX.json> [...]
"""
import json
import sys
from collections import defaultdict


def resume(chemin):
    d = json.load(open(chemin, encoding="utf-8"))
    ts = [t for t in d["tenseurs"] if t["type"] != "F32"]
    f32 = [t for t in d["tenseurs"] if t["type"] == "F32"]
    groupes = defaultdict(list)
    for t in ts:
        groupes[(t["type"], t["role"])].append(t)
        groupes[(t["type"], "*")].append(t)
        groupes[("*", "*")].append(t)
    print(f"\n# {chemin}")
    print(f"{'type':5s} {'rôle':22s} {'Mio':>8s} {'b/p':>6s} {'H0':>6s} {'H|pr':>6s} {'H|éch':>6s} "
          f"{'Huff':>6s} {'Hpaire':>6s} {'idéal':>6s} {'taux0':>6s} {'zstd3':>6s} {'lz4':>6s} {'z19':>6s} "
          f"{'zstdGo/s':>8s} {'lz4Go/s':>7s}")
    lignes = []
    for (ty, role), g in sorted(groupes.items(), key=lambda kv: (kv[0][0] == "*", kv[0][0], -sum(t["octets"] for t in kv[1]))):
        p = sum(t["poids"] for t in g)
        o = sum(t["octets"] for t in g)

        def moy(cle, poids="poids"):
            v = [(t[cle], t[poids]) for t in g if cle in t]
            if not v:
                return float("nan")
            return sum(a * b for a, b in v) / sum(b for _, b in v)

        def taux(nom):
            v = [(t["compresseurs"][nom]["taux"], t["octets"]) for t in g
                 if "compresseurs" in t and nom in t["compresseurs"]]
            if not v:
                return float("nan")
            return sum(b for _, b in v) / sum(b / a for a, b in v)

        def debit(nom):
            v = [(t["compresseurs"][nom]["decomp_Go_s_1fil"], t["octets"]) for t in g
                 if "compresseurs" in t and nom in t["compresseurs"]]
            if not v:
                return float("nan")
            return sum(b for _, b in v) / sum(b / a for a, b in v)

        bits_ideaux = sum(t["bits_ideaux_ordre0_par_poids"] * t["poids"] for t in g)
        ligne = {
            "type": ty, "role": role, "octets": o, "poids": p,
            "bits_par_poids": o * 8 / p, "H0": moy("H0_code"),
            "H_prec": moy("H_code_sachant_precedent"), "H_ech": moy("H_code_sachant_echelle"),
            "huffman": moy("L_huffman_code"), "huffman_paire": moy("L_huffman_paire"),
            "ideal_bits_par_poids": bits_ideaux / p, "taux_ideal": o * 8 / bits_ideaux,
            "zstd3": taux("zstd3"), "lz4": taux("lz4"), "zstd19": taux("zstd19_echantillon16Mo"),
            "zstd3_go_s": debit("zstd3"), "lz4_go_s": debit("lz4"),
            "H_d": moy("H_d_u16", "blocs"), "H_dmin": moy("H_dmin_u16", "blocs"),
            "H_echelle6": moy("H_echelle6", "blocs"), "H_minimum6": moy("H_minimum6", "blocs"),
        }
        lignes.append(ligne)
        print(f"{ty:5s} {role:22s} {o/2**20:8.1f} {ligne['bits_par_poids']:6.3f} {ligne['H0']:6.3f} "
              f"{ligne['H_prec']:6.3f} {ligne['H_ech']:6.3f} {ligne['huffman']:6.3f} {ligne['huffman_paire']:6.3f} "
              f"{ligne['ideal_bits_par_poids']:6.3f} {ligne['taux_ideal']:6.4f} {ligne['zstd3']:6.4f} "
              f"{ligne['lz4']:6.4f} {ligne['zstd19']:6.4f} {ligne['zstd3_go_s']:8.2f} {ligne['lz4_go_s']:7.2f}")
    print("\nchamps de métadonnées (moyennes par bloc) :")
    for l in lignes:
        if l["role"] == "*" and l["type"] != "*":
            print(f"  {l['type']}: H(d)={l['H_d']:.2f} b/16, H(dmin)={l['H_dmin']:.2f} b/16, "
                  f"H(échelle)={l['H_echelle6']:.2f} b, H(minimum)={l['H_minimum6']:.2f} b")
    if f32:
        o = sum(t["octets"] for t in f32)
        print(f"F32 : {len(f32)} tenseurs, {o/2**20:.2f} Mio ; H exposant moyen "
              f"{sum(t['H_exposant8']*t['poids'] for t in f32)/sum(t['poids'] for t in f32):.2f} b/8")
    return lignes


if __name__ == "__main__":
    tout = {}
    for c in sys.argv[1:]:
        tout[c] = resume(c)
    json.dump(tout, open(sys.argv[1].replace(".json", "") + "-resume.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
