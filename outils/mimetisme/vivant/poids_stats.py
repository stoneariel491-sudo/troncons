"""Statistiques complémentaires de E-C : forme de la loi des poids de mélange (descriptif). Usage : python -I poids_stats.py DOSSIER"""
import importlib.util, json, sys
from pathlib import Path
import numpy as np
ici = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("bt", ici / "bancs_traces.py")
bt = importlib.util.module_from_spec(spec); spec.loader.exec_module(bt)
out = {}
for m in ("20b", "120b"):
    W = np.concatenate([bt.charger(sys.argv[1], m, g)[1].reshape(-1, 4) for g in bt.GENRES])
    W = np.sort(W, axis=1)[:, ::-1]
    out[m] = {"n": int(len(W)), "w1_median": float(np.median(W[:, 0])), "w4_median": float(np.median(W[:, 3])),
              "P_w1_ge_0.5": float((W[:, 0] >= 0.5).mean()), "P_w1_ge_0.9": float((W[:, 0] >= 0.9).mean()),
              "P_w4_le_0.05": float((W[:, 3] <= 0.05).mean()), "P_w4_le_0.10": float((W[:, 3] <= 0.10).mean()),
              "P_w4_le_0.02": float((W[:, 3] <= 0.02).mean()),
              "entropie_moyenne_bits": float(-(W * np.log2(np.clip(W, 1e-12, 1))).sum(1).mean())}
    print(m, out[m])
bt.ecrire("ec-poids-stats.json", out)
