"""P4 : figures et CSV du mémoire, tirés de mesures/mimetisme/P4/mesure-*.json (aucune valeur saisie à la main).
Usage : python -I -X utf8 p4_figures.py <dossier_mesures> <dossier_sortie>
"""
import csv
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from scipy.stats import beta  # noqa: E402

LECT = ["code.lecture", "dialogue.lecture", "prose-en.lecture", "prose-fr.lecture"]
COUL = {"code.lecture": "#1b6ca8", "dialogue.lecture": "#d1495b", "prose-en.lecture": "#2e933c", "prose-fr.lecture": "#edae49"}


def main():
    mes, sortie = sys.argv[1], sys.argv[2]
    os.makedirs(sortie, exist_ok=True)
    r = json.load(open(os.path.join(mes, "mesure-120b.json"), encoding="utf-8"))
    r20 = json.load(open(os.path.join(mes, "mesure-20b.json"), encoding="utf-8"))
    sess = {s["session"]: s for s in r["sessions"] if s["budget"] == "7%" and s["d"] == 2}

    # CSV précision-couverture par seuil (test et calibration, avec la borne de Clopper-Pearson de la calibration)
    with open(os.path.join(sortie, "p4-precision-couverture.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["session", "theta", "n_cal", "x_cal", "borne_cp_cal", "n_test", "x_test", "precision_test", "couverture_test"])
        for nom in LECT:
            s = sess[nom]
            for c in s["courbe"]:
                lb = float(beta.ppf(0.1, c["x_cal"], c["n_cal"] - c["x_cal"] + 1)) if c["x_cal"] > 0 and c["n_cal"] > 0 else 0.0
                w.writerow([nom, c["theta"], c["n_cal"], c["x_cal"], f"{lb:.4f}", c["n_test"], c["x_test"],
                            f"{c['x_test'] / c['n_test']:.4f}" if c["n_test"] else "", f"{c['x_test'] / s['F_test_base']:.5f}"])

    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.2))
    a = ax[0]
    for nom in LECT:
        s = sess[nom]
        xs = [c["x_test"] / s["F_test_base"] for c in s["courbe"] if c["n_test"] >= 30]
        ys = [c["x_test"] / c["n_test"] for c in s["courbe"] if c["n_test"] >= 30]
        a.plot(xs, ys, "-", color=COUL[nom], lw=1.6, label=nom.split(".")[0])
        if s["thP"] is not None:
            c = [c for c in s["courbe"] if abs(c["theta"] - s["thP"]) < 1e-6][0]
            a.plot([c["x_test"] / s["F_test_base"]], [c["x_test"] / c["n_test"]], "o", color=COUL[nom], ms=7, mec="k")
    a.axhline(0.9, color="k", lw=0.8, ls="--")
    a.axhline(0.85, color="gray", lw=0.8, ls=":")
    a.text(0.5, 0.905, "cible 0,9", fontsize=8, ha="right")
    a.text(0.5, 0.855, "seuil du verdict 0,85", fontsize=8, ha="right", color="gray")
    a.set_xlabel("couverture : part des défauts de la moitié de test précédés d'un chargement juste")
    a.set_ylabel("précision des chargements (moitié de test)")
    a.set_title("120b, 7 % : la précision se tient, la couverture reste petite\n(points : seuil theta* calibré sur l'autre moitié)", fontsize=9)
    a.set_xlim(0, 0.55)
    a.set_ylim(0.3, 1.0)
    a.legend(frameon=False, loc="lower left")

    b = ax[1]
    noms = LECT
    x = range(len(noms))
    g120 = [100 * sess[n]["P"]["gain"] for n in noms]
    s20 = {s["session"]: s for s in r20["sessions"] if s["budget"] == "20%" and s["d"] == 2}
    g20 = [100 * s20[n]["P"]["gain"] for n in noms]
    b.bar([i - 0.2 for i in x], g120, 0.4, color="#1b6ca8", label="120b, 7 %")
    b.bar([i + 0.2 for i in x], g20, 0.4, color="#2e933c", label="20b, 20 %")
    b.axhline(5, color="k", lw=0.9, ls="--")
    b.axhline(2, color="gray", lw=0.9, ls=":")
    b.text(3.6, 5.15, "seuil +5 %", fontsize=8, ha="right")
    b.text(3.6, 2.15, "mort +2 %", fontsize=8, ha="right", color="gray")
    b.set_xticks(list(x))
    b.set_xticklabels([n.split(".")[0] for n in noms])
    b.set_ylabel("gain de vitesse simulé, bras P (%)")
    b.set_title("Gain simulé (simulateur non validé : témoin FIFO manqué)", fontsize=9)
    b.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(sortie, "p4-precision-couverture-gain.png"), dpi=170)
    print("figure écrite")

    # CSV des gains par session
    with open(os.path.join(sortie, "p4-gains-par-session.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["modele", "budget", "d", "session", "theta_P", "charges", "justes", "precision_test", "couverture", "octets_plus",
                    "gain_P", "gain_P_purge_totale", "gain_P_fifo", "gain_formule_fermee_declaree", "theta_R", "gain_R", "defauts_moins_R"])
        for tag, res in (("120b", r), ("20b", r20)):
            for s in res["sessions"]:
                P, R = s["P"], s["R"]
                w.writerow([tag, s["budget"], s["d"], s["session"], s["thP"], P.get("charges"), P.get("justes"),
                            P.get("precision_test"), P.get("couverture"), P.get("octets_plus"), P.get("gain"),
                            P.get("gain_purge_totale"), P.get("gain_fifo_meme_charges"), P.get("gain_formule_fermee"),
                            s["thR"], R.get("gain"), R.get("defauts_moins")])


if __name__ == "__main__":
    main()
