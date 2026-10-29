"""Affiche les lignes d'un journal etape1 (une ou plusieurs)."""
import json, sys
for f in sys.argv[1:]:
    d = json.load(open(f, encoding="utf-8"))
    print(f.split("/")[-1], {k: d[k] for k in ("couche", "expert", "damp", "lignes", "n_calib", "n_eval") if k in d})
    base = {r["lam"]: r for r in d["lignes_res"] if r["methode"] == "babai"}
    for r in d["lignes_res"]:
        b = base.get(r["lam"])
        g = ""
        if b and r["methode"] in ("cd", "pt"):
            g = " gain_train %+.1f%% calib %+.1f%% eval %+.1f%%" % tuple(100 * (1 - r[k] / b[k]) for k in ("err_train", "err_calib", "err_eval"))
        print("  %-9s lam=%-4s H0=%.4f train=%.5f calib=%.5f eval=%.5f t=%.0fs%s" % (r["methode"], r["lam"], r["bits_H0"], r["err_train"], r["err_calib"], r["err_eval"], r.get("t_s", 0), g),
              ("ech=%.2f froid=%.4f chaud=%.3f" % (r["taux_echange"], r["chg_froid"], r["chg_chaud"])) if "taux_echange" in r else "")
