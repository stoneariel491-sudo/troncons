"""H7 : débit de l'étage disque selon la profondeur de file (séances p4, p5), aux seuils déclarés (08 § 2.6).

  python -I -X utf8 outils/disque/placement/analyse_qd.py p4 [p5 …]

Pour chaque (fichier, q) : passes, médiane, e_soi. S = max(2 · max e_soi de la séance, 11,8 %).
Verdict du levier : sur A20, débit(q) / débit(4) > 1 + S, et sur B20 débit(q) / débit(4) > 1 − S / 2.
Écrit mesures/disque/placement/<seance>/analyse-qd.json.
"""
import json
import pathlib
import re
import statistics
import sys

OUT = pathlib.Path(__file__).resolve().parents[3] / "mesures/disque/placement"


def main():
    for s in sys.argv[1:]:
        d = OUT / s
        res = json.loads((d / f"seance-{s}.json").read_text(encoding="utf-8"))
        v = {}
        charge = []
        for p in res["passes"]:
            m = re.search(r"-q(\d+)-(A20|B20)$", p["nom"])
            if not m:
                continue
            j = json.loads((d / f"{p['nom']}.json").read_text(encoding="utf-8"))
            v.setdefault((m.group(2), int(m.group(1))), []).append(j["go_s"])
            if p["sous_charge"]:
                charge.append(p["nom"])
        e_soi = {f"{k[0]} q{k[1]}": (max(x) - min(x)) / statistics.mean(x) for k, x in v.items() if len(x) > 1}
        S = max(2 * max(e_soi.values()), 0.118)
        med = {k: statistics.median(x) for k, x in v.items()}
        verdicts = {}
        for q in sorted({k[1] for k in v}):
            if q == 4 or ("A20", q) not in med:
                continue
            ra, rb = med[("A20", q)] / med[("A20", 4)], med[("B20", q)] / med[("B20", 4)]
            verdicts[f"q{q}"] = {"A20_sur_q4": ra, "B20_sur_q4": rb,
                                 "levier": ra > 1 + S and rb > 1 - S / 2,
                                 "A20": "diffèrent" if abs(ra - 1) > S else ("égaux" if abs(ra - 1) < S / 2 else "entre deux")}
        r = {"seance": s, "sous_charge": charge, "passes": {f"{k[0]} q{k[1]}": x for k, x in sorted(v.items())},
             "mediane": {f"{k[0]} q{k[1]}": m for k, m in sorted(med.items())}, "e_soi": e_soi, "S": S, "verdicts": verdicts}
        (d / "analyse-qd.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        print(s, "sous charge", charge, "S", round(S, 4))
        for k, m in sorted(med.items()):
            print(f"  {k[0]} q{k[1]} : {[round(x, 3) for x in v[k]]} médiane {m:.3f}")
        for q, x in verdicts.items():
            print(f"  {q} : A20/q4 {x['A20_sur_q4']:.3f} ({x['A20']}), B20/q4 {x['B20_sur_q4']:.3f}, levier {x['levier']}")


if __name__ == "__main__":
    main()
