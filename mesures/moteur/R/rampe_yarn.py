"""Second chemin de la rampe de YaRN de gpt-oss (figure R-M3 du mémoire ; lot R).

Recalcule, depuis les seules formules (OpenAI `gpt_oss/torch/model.py`, `truncate: false` ; forme
arrondie de llama.cpp b11515 `ggml_rope_yarn_corr_dims`), sans importer le code de la référence, les
fréquences ω_i des 32 paires, puis les compare au CSV écrit par `juge rampe` (le code Rust de la
référence).

SEUILS DÉCLARÉS AVANT LE LANCEMENT (2026-10-15) :
  témoin : |ω_python − ω_rust| ≤ 4 · 2⁻⁵² · ω (quelques ulp : pow, ln et divisions en double des
           deux côtés, dans des ordres qui peuvent différer) pour les 64 valeurs ;
  cassure (--casser) : le chemin Python prend la rampe arrondie pour la variante OpenAI ; au moins
           une paire de la rampe (8 ≤ i ≤ 17) doit alors dépasser le seuil.

Usage : python -I -X utf8 rampe_yarn.py <rampe.csv écrit par juge rampe> [--casser]
Sortie : un résumé JSON sur la sortie standard.
"""

import json
import math
import sys

BASE, FACTEUR, L0, BETA_RAPIDE, BETA_LENT, D = 150000.0, 32.0, 4096.0, 32.0, 1.0, 64


def frequences(arrondie):
    demi = D // 2
    corr = lambda beta: demi * math.log(L0 / (beta * 2 * math.pi)) / math.log(BASE)
    bas, haut = corr(BETA_RAPIDE), corr(BETA_LENT)
    if arrondie:
        bas, haut = max(math.floor(bas), 0.0), min(math.ceil(haut), D - 1.0)
    omegas = []
    for i in range(demi):
        theta = BASE ** (-(2 * i) / D)
        r = min(max((i - bas) / (haut - bas), 0.0), 1.0)
        m = 1.0 - r
        omegas.append(theta / FACTEUR * (1.0 - m) + theta * m)
    return bas, haut, omegas


def main():
    chemin = sys.argv[1]
    casser = "--casser" in sys.argv
    lignes = [l for l in open(chemin, encoding="utf-8") if l.strip() and not l.startswith("#")]
    entete = lignes[0].strip().split(",")
    rust = [dict(zip(entete, map(float, l.strip().split(",")))) for l in lignes[1:]]
    _, _, o_py = frequences(arrondie=casser)
    bas, haut, l_py = frequences(arrondie=True)
    ecarts = []
    for i, r in enumerate(rust):
        for nom, py in (("omega_openai", o_py[i]), ("omega_llamacpp", l_py[i])):
            e = abs(py - r[nom])
            ecarts.append({"paire": i, "variante": nom, "ecart": e, "ulp_relatifs": e / (r[nom] * 2.0 ** -52), "dans_le_seuil": e <= 4 * 2.0 ** -52 * r[nom]})
    hors = [e for e in ecarts if not e["dans_le_seuil"]]
    bas_o, haut_o, _ = frequences(arrondie=False)
    print(json.dumps({
        "outil": "rampe_yarn.py",
        "casser": casser,
        "bornes_openai": [bas_o, haut_o],
        "bornes_llamacpp": [bas, haut],
        "valeurs_comparees": len(ecarts),
        "hors_seuil": len(hors),
        "paires_hors_seuil": sorted({e["paire"] for e in hors}),
        "ulp_relatifs_max": max(e["ulp_relatifs"] for e in ecarts),
        "tient": len(hors) == 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
