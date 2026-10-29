"""Figures de P6 (étape 0), tirées de mesures/mimetisme/P6/*.json. Usage : python -I -X utf8 figures.py <racine du dépôt>"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
rac = sys.argv[1]
M = os.path.join(rac, "mesures/mimetisme/P6")
out = os.path.join(rac, "genome/mimetisme/P6/figures")
E0 = json.load(open(os.path.join(M, "etape0.json"), encoding="utf-8"))
B = json.load(open(os.path.join(M, "etape0_B_120b.json"), encoding="utf-8"))
RHO = 0.718
ST = 1 - RHO
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "font.family": "DejaVu Sans"})
C = {"acc": "#1f5f8b", "r40": "#c05a1a", "orc": "#2e7d4f", "B": "#7a3b8f", "gris": "#8a8a8a"}

# ---- figure 1 : plan (octets économisés, énergie perturbée)
fig, ax = plt.subplots(figsize=(7.2, 4.8))
x = np.linspace(0, 0.30, 50)
ax.plot(100 * x, x / ST, color=C["gris"], ls="--", lw=1.2, label="tout-rapide proportionnel (r = 1)")
for nom, col, lab in (("accepter", C["acc"], "décodage, accepter"), ("remonter0.40", C["r40"], "décodage, remonter à 0,40")):
    pts = [(r[nom]["S"], r[nom]["E_rel"]) for r in E0["courbe_f"] if nom in r and r["theta"] <= 1.0]
    pts.sort()
    ax.plot([100 * p[0] for p in pts], [p[1] for p in pts], color=col, lw=2, label=lab)
orc = E0["120b"]["cumul_generation"]["oracle"]
po = sorted((v["S"], v["E_rel"]) for v in orc.values())
ax.plot([100 * p[0] for p in po], [p[1] for p in po], color=C["orc"], lw=2, marker="o", ms=4, label="décodage, borne clairvoyante")
pb = []
for i, S in enumerate(B["S_cibles"]):
    rs = [B["lot512"][g]["r_a_S_egal"][f"S{S:.2f}"]["masse"]["r"] for g in ("code", "dialogue", "prose-en", "prose-fr")]
    pb.append((S, float(np.mean(rs)) * S / ST))
ax.plot([100 * p[0] for p in pb], [p[1] for p in pb], color=C["B"], lw=2, marker="s", ms=4, label="préremplissage, masse agrégée (lots de 512)")
ax.axvline(8, color="k", lw=0.6, ls=":")
ax.text(8.3, 0.03, "8 %", fontsize=8)
ax.set_xlim(0, 28.5); ax.set_ylim(0, 1.02)
ax.set_xlabel("octets économisés (% des octets du tout-exact)")
ax.set_ylabel("énergie perturbée (part de celle du tout-rapide)")
ax.set_title("Plan octets - énergie : plus la courbe est basse, moins la perte coûte par octet", fontsize=10)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(out, "plan-octets-energie.png"), dpi=200); plt.close(fig)

# ---- figure 2 : r selon theta, avec sigma, cumul des deux générations du 120b
fig, ax = plt.subplots(figsize=(7.2, 4.2))
P = E0["120b"]["cumul_generation"]["portillon"]
ths = ["0.15", "0.20", "0.25"]
for nom, col in (("accepter", C["acc"]), ("remonter0.30", "#6a9fc0"), ("remonter0.40", C["r40"]), ("remonter0.50", "#e0a070")):
    ys = [P[t][nom]["r"] for t in ths]; es = [P[t][nom]["sigma_r"] for t in ths]
    ax.errorbar([float(t) for t in ths], ys, yerr=es, color=col, marker="o", ms=4, capsize=3, label=nom)
ax.plot([float(t) for t in ths], [orc[t]["r"] for t in ths], color=C["orc"], marker="s", ms=4, label="clairvoyant")
ax.axhline(0.70, color="k", lw=0.8, ls=":"); ax.text(0.152, 0.715, "seuil 0,70", fontsize=8)
ax.axhline(1.0, color=C["gris"], lw=0.8, ls="--")
ax.set_xlabel("theta (poids de mélange sous lequel on lit en rapide)"); ax.set_ylabel("r = énergie par octet économisé / celle du tout-rapide")
ax.set_ylim(0, 1.05); ax.legend(frameon=False, fontsize=8, ncol=2)
ax.set_title("r selon theta, cumul des deux générations du 120b (barres : 1 sigma, blocs de 32 jetons)", fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(out, "r-selon-theta.png"), dpi=200); plt.close(fig)
print("ok")

# ---- CSV pour le mémoire
with open(os.path.join(M, "courbe-plan-decodage.csv"), "w", encoding="utf-8") as f:
    f.write("theta,f_defauts_servis_rapide,regle,S,E_rel,r,KL_hyp_lineaire\n")
    for r in E0["courbe_f"]:
        for nom in ("accepter", "remonter0.40"):
            if nom in r:
                v = r[nom]
                f.write(f"{r['theta']},{r['f_defauts_servis_rapide']:.6f},{nom},{v['S']:.6f},{v['E_rel']:.6f},{v['r']:.6f},{v['KL_hyp_lineaire']:.6f}\n")
with open(os.path.join(M, "courbe-plan-prefill-B.csv"), "w", encoding="utf-8") as f:
    f.write("genre,S,regle,r,sigma,E_rel\n")
    for g in ("code", "dialogue", "prose-en", "prose-fr"):
        for S in B["S_cibles"]:
            for rg, v in B["lot512"][g]["r_a_S_egal"][f"S{S:.2f}"].items():
                f.write(f"{g},{S},{rg},{v['r']:.6f},{v['sigma']:.6f},{v['r'] * S / ST:.6f}\n")
