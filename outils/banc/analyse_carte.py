"""Lecture du journal du banc carte : tableaux par opération, taille et interface (Vulkan, DX12),
série ABBA vulkan, dx12, dx12, vulkan : on donne les deux passages et leur écart, la règle de
décision déclarée (écart ≥ 2 × bruit et ≥ 3 %) pour Vulkan contre DX12.

Usage : python -I -X utf8 outils/banc/analyse_carte.py fondations/journaux/01-machine/carte.jsonl
"""

import json
import math
import statistics
import sys


def val(d):
    """Le débit de la carte (horodatages) s'il existe, sinon celui du mur."""
    c = d.get("go_s_carte_mediane")
    if isinstance(c, float) and not math.isnan(c):
        return c, "carte"
    return d.get("go_s_mur_mediane"), "mur"


def main(chemin):
    L = [json.loads(l) for l in open(chemin, encoding="utf-8")]
    print("## Témoins (--fausser : doivent ÉCHOUER)")
    for d in L:
        if d.get("genre") == "temoin":
            t = d.get("temoin_aller_retour") or d.get("temoin_somme") or d.get("temoin")
            print(f"- {d.get('op')} {d.get('format', '')} : {t}")
    print("\n## Transferts : Go/s [source du chrono] (passage 1 / passage 2), plafond respecté")
    tr = [d for d in L if d.get("genre") == "transfert" and "op" in d]
    cles = []
    for d in tr:
        k = (d["op"], int(d["taille"]))
        if k not in cles:
            cles.append(k)
    print("| opération | taille | Vulkan | DX12 | Vulkan/DX12 |")
    print("|---|---|---|---|---|")
    for op, t in cles:
        cel = {}
        for api in ("vulkan", "dx12"):
            v = [d for d in tr if d["op"] == op and int(d["taille"]) == t and d["api"] == api]
            xs = [val(d)[0] for d in v]
            src = val(v[0])[1] if v else ""
            pl = all(str(d.get("sous_plafond")) in ("True", "true", "sans_objet(L2)") for d in v)
            bruit = max((d.get("bruit_abba") or 0) for d in v) if v else 0
            cel[api] = (xs, src, pl, bruit)
        def fmt(c):
            xs, src, pl, bruit = c
            if not xs:
                return ""
            return f"{statistics.mean(xs):.2f} [{src}] ({' / '.join(f'{x:.2f}' for x in xs)}) {'' if pl else 'HORS PLAFOND'}"
        va, vd = cel["vulkan"], cel["dx12"]
        verdict = ""
        if va[0] and vd[0]:
            ma, md = statistics.mean(va[0]), statistics.mean(vd[0])
            na = abs(va[0][0] - va[0][-1]) / ma if len(va[0]) > 1 else 0
            nd = abs(vd[0][0] - vd[0][-1]) / md if len(vd[0]) > 1 else 0
            ecart = abs(ma - md) / ((ma + md) / 2)
            reel = ecart >= max(2 * max(na, nd), 0.03)
            verdict = f"{ma / md:.2f} {'(réel)' if reel else '(dans le bruit)'}"
        taille = f"{t >> 20} Mio" if t >= 1 << 20 else f"{t >> 10} Kio"
        print(f"| {op} | {taille} | {fmt(va)} | {fmt(vd)} | {verdict} |")

    print("\n## Lecture de la VRAM (shader)")
    for d in L:
        if d.get("genre") == "vram" and "op" in d:
            print(f"- {d['api']} {int(d['taille']) >> 20} Mio : carte {d['go_s_carte_mediane']} Go/s (min {d['go_s_carte_min']}, "
                  f"max {d['go_s_carte_max']}), mur {d['go_s_mur_mediane']}, témoin {d['temoin_somme']}, sous plafond {d['sous_plafond']}, "
                  f"util. avant {d['carte_avant']['utilization.gpu']} %")
    print("\n## GEMV")
    print("| format | résidence | lot | API | Go/s carte (méd.) | µs/GEMV | GFLOP/s | écart rel. | témoin | plafond | util. avant |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for d in L:
        if d.get("genre") == "gemv" and "op" in d:
            print(f"| {d['format']} | {d['residence']} | {int(d['lot'])} | {d['api']} | {d['go_s_carte_mediane']} | "
                  f"{d['us_par_gemv_carte']} | {d['gflops_carte']} | {d['ecart_relatif_max']:.1e} | {d['temoin']} | "
                  f"{d['sous_plafond']} | {d['carte_avant']['utilization.gpu']} % |")
        elif d.get("genre") == "gemv":
            print(f"| erreur | | | | {str(d.get('erreur'))[:160]} |")


if __name__ == "__main__":
    main(sys.argv[1])
