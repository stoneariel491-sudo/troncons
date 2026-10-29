"""Analyse d'une passe thermique (pilote_thermique.py) : débit de la GEMV par fenêtre de 5 s et
relevé nvidia-smi par seconde.

Règle déclarée avant la mesure (00-seuils-declares.md) : bridage si le débit moyen des 30 dernières
secondes tombe sous 95 % de celui des 30 premières. Le bruit de référence est l'écart type relatif
des fenêtres de 5 s sur toute la passe ; il est dit à côté du verdict.

Bibliothèque standard seulement. Usage :
  python -I -X utf8 outils/banc/analyse_thermique.py DOSSIER [--csv SORTIE.csv]
"""
import argparse
import re
import statistics as st

# Bits de clocks_throttle_reasons.active (documentation de nvidia-smi --help-query-gpu)
RAISONS = {0x1: "repos", 0x2: "consigne applicative", 0x4: "plafond de puissance logiciel",
           0x8: "ralentissement matériel", 0x10: "synchronisation", 0x20: "thermique logiciel",
           0x40: "thermique matériel", 0x80: "frein de puissance matériel", 0x100: "horloges d'affichage"}


def lire(dossier):
    fen = []
    for l in open(f"{dossier}/thermique.log", encoding="utf-8", errors="replace"):
        m = re.match(r"THERMIQUE t_s=([\d.]+) go_s=([\d.]+)", l)
        if m:
            fen.append((float(m.group(1)), float(m.group(2))))
    nv = []
    for l in open(f"{dossier}/thermique-nvsmi.csv", encoding="utf-8", errors="replace"):
        c = [x.strip() for x in l.split(",")]
        if len(c) < 9:
            continue
        try:
            nv.append({"temp": float(c[1]), "sm": float(c[2].split()[0]), "mem": float(c[3].split()[0]),
                       "w": float(c[4].split()[0]), "util": float(c[5].split()[0]), "pstate": c[6],
                       "raisons": int(c[7], 16), "gen": c[8]})
        except ValueError:
            pass
    return fen, nv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier")
    ap.add_argument("--csv")
    a = ap.parse_args()
    fen, nv = lire(a.dossier)
    debut = [g for t, g in fen if t <= 30.5]
    fin_t = fen[-1][0]
    fin = [g for t, g in fen if t >= fin_t - 30.0]
    tous = [g for _, g in fen]
    bruit = st.pstdev(tous) / st.mean(tous)
    rapport = st.mean(fin) / st.mean(debut)
    charge = [r for r in nv if r["util"] >= 90]
    print(f"fenêtres de 5 s : {len(fen)} ; durée {fin_t:.0f} s")
    print(f"débit : 30 premières s {st.mean(debut):.2f} Go/s, 30 dernières {st.mean(fin):.2f}, "
          f"rapport {rapport:.3f} ; médiane {st.median(tous):.2f}, min {min(tous):.2f}, max {max(tous):.2f}")
    print(f"bruit (écart type relatif des fenêtres) : {100 * bruit:.1f} %")
    print(f"verdict (règle 95 %) : {'BRIDAGE' if rapport < 0.95 else 'pas de bridage'}")
    if charge:
        print(f"relevés sous charge (util ≥ 90 %) : {len(charge)} ; température max {max(r['temp'] for r in charge):.0f} °C, "
              f"finale {charge[-1]['temp']:.0f} °C ; horloge SM médiane {st.median(r['sm'] for r in charge):.0f} MHz, "
              f"min {min(r['sm'] for r in charge):.0f} ; mémoire {st.median(r['mem'] for r in charge):.0f} MHz ; "
              f"puissance médiane {st.median(r['w'] for r in charge):.1f} W, max {max(r['w'] for r in charge):.1f} W")
        compte = {}
        for r in charge:
            for bit, nom in RAISONS.items():
                if r["raisons"] & bit:
                    compte[nom] = compte.get(nom, 0) + 1
        print("raisons de bridage actives (relevés sous charge) :", compte or "aucune")
        print("génération PCIe sous charge :", sorted({r["gen"] for r in charge}))
    if a.csv:
        with open(a.csv, "w", encoding="utf-8") as f:
            f.write("t_s,go_s\n")
            for t, g in fen:
                f.write(f"{t},{g}\n")


if __name__ == "__main__":
    main()
