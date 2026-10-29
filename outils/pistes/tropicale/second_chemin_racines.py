"""Second chemin, en Python pur (lecture de bascules.py, lot R), du chiffre exploratoire des racines :
part des premières bascules de chaque position signalées par la garde (marge de B < τ₁₀ global).
Doit égaler cascades.py à l'unité.

Usage : python -I -X utf8 second_chemin_racines.py
"""

import importlib.util
import json
import sys
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import routage as R  # noqa: E402  (priorité et verrou seulement)

spec = importlib.util.spec_from_file_location("bascules_lot_r", DEPOT / "mesures/moteur/R/bascules.py")
lot_r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lot_r)


def main():
    R.sous_la_normale()
    R.attendre_calme()
    L, N, ea, _ = lot_r.lire(str(DEPOT / "mesures/moteur/R/r1/routage/ref-openai-bis-20b.bin"))
    _, _, eb, mb = lot_r.lire(str(DEPOT / "mesures/moteur/R/r1/routage/ref-llamacpp-bis-20b.bin"))
    tau10 = sorted(mb[l][p] for l in range(L) for p in range(N))[int(0.10 * L * N)]
    racines = signalees = secondaires = sec_signalees = 0
    for p in range(N):
        deja = False
        for l in range(L):
            if ea[l][p] != eb[l][p]:
                if not deja:
                    racines += 1
                    signalees += mb[l][p] < tau10
                    deja = True
                else:
                    secondaires += 1
                    sec_signalees += mb[l][p] < tau10
    res = {"outil": "outils/pistes/tropicale/second_chemin_racines.py", "tau10": tau10,
           "racines": racines, "racines_signalees": int(signalees), "part_racines": signalees / racines,
           "secondaires": secondaires, "secondaires_signalees": int(sec_signalees), "part_secondaires": sec_signalees / secondaires}
    c = json.loads((R.SORTIE / "cascades.json").read_text(encoding="utf-8"))
    res["egal_a_cascades"] = (c["primaires"] == racines and c["secondaires"] == secondaires
                              and round(c["b_tau10_primaires"] * racines) == signalees
                              and round(c["b_tau10_secondaires"] * secondaires) == sec_signalees)
    (R.SORTIE / "second-chemin-racines.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
