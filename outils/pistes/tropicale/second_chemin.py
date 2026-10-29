"""Second chemin du point principal de la garde tropicale, indépendant du chemin numpy.

La lecture est celle de mesures/moteur/R/bascules.py (`lire`, Python pur, écrite par le lot R) ;
le décile, les comptes et le verdict se refont ici par boucles et `sorted`, sans numpy. Le point
doit égaler, à l'unité, celui de garde.py (seuil-declare.md § 3).

Usage : python -I -X utf8 second_chemin.py
"""

import importlib.util
import json
import sys
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import routage as R  # noqa: E402  (seulement pour la priorité et le verrou ; aucune lecture)

spec = importlib.util.spec_from_file_location("bascules_lot_r", DEPOT / "mesures/moteur/R/bascules.py")
bascules_lot_r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bascules_lot_r)


def main():
    R.sous_la_normale()
    R.attendre_calme()
    ca, na, ea, ma = bascules_lot_r.lire(str(DEPOT / "mesures/moteur/R/r1/routage/ref-openai-bis-20b.bin"))
    cb, nb, eb, mb = bascules_lot_r.lire(str(DEPOT / "mesures/moteur/R/r1/routage/ref-llamacpp-bis-20b.bin"))
    assert (ca, na) == (cb, nb)
    cellules = []  # (marge de B, bascule)
    for l in range(ca):
        for p in range(na):
            cellules.append((mb[l][p], ea[l][p] != eb[l][p]))
    n = len(cellules)
    triees = sorted(m for m, _ in cellules)
    tau10 = triees[int(0.10 * n)]
    signalees = 0
    attrapees = 0
    total_bascules = 0
    for m, b in cellules:
        if b:
            total_bascules += 1
        if m < tau10:
            signalees += 1
            if b:
                attrapees += 1
    res = {"outil": "outils/pistes/tropicale/second_chemin.py", "lecture": "mesures/moteur/R/bascules.py:lire",
           "cellules": n, "bascules": total_bascules, "tau10": tau10,
           "cellules_signalees": signalees, "bascules_signalees": attrapees,
           "part_cellules": signalees / n, "part_bascules": attrapees / total_bascules}
    principal = json.loads((R.SORTIE / "garde-resume.json").read_text(encoding="utf-8"))["variantes"]["marge_B"]["decile"]
    res["egal_au_chemin_principal"] = (principal["cellules_signalees"] == signalees
                                       and principal["bascules_signalees"] == attrapees
                                       and principal["tau"] == tau10)
    res["verdict_second_chemin"] = "LA GARDE PASSE" if attrapees / total_bascules >= 0.80 else "LA GARDE TOMBE"
    (R.SORTIE / "second-chemin.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
