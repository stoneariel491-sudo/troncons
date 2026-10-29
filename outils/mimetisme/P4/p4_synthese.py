"""P4 : synthèse au seuil déclaré (mesures/mimetisme/P4/00-seuils-declares.md § 2) à partir des JSON de p4_mesure.py.
Usage : python -I -X utf8 p4_synthese.py <mesure-120b.json> <mesure-20b.json> <sortie.json>
"""
import json
import sys

LECT = ["code.lecture", "dialogue.lecture", "prose-en.lecture", "prose-fr.lecture"]
GEN120 = ["prose-en.generation", "wiki.generation"]


def trouve(res, nom, budget, d):
    for s in res["sessions"]:
        if s["session"] == nom and s["budget"] == budget and s["d"] == d:
            return s
    return None


def bras(res, arm, budget, d, lect, gens):
    """Évalue le seuil pour un bras ; rend un dict de verdict partiel."""
    lig = []
    for nom in lect:
        s = trouve(res, nom, budget, d)
        if s is None:
            continue
        a = s[arm]
        lig.append((nom, s["t_base_test_ms"], a.get("gain", 0.0), a.get("octets_plus") or 0.0,
                    a.get("precision_test") if arm == "P" else a.get("precision_epingles_test"),
                    a.get("justes", 0), a.get("charges", 0)))
    ok_lect = [x for x in lig if x[2] >= 0.05 and x[3] <= 0.05]
    gl = []
    for nom in gens:
        s = trouve(res, nom, budget, d)
        if s is None:
            continue
        a = s[arm]
        gl.append((nom, s["t_base_test_ms"], a.get("gain", 0.0), a.get("octets_plus") or 0.0,
                   a.get("precision_test") if arm == "P" else a.get("precision_epingles_test"),
                   a.get("justes", 0), a.get("charges", 0)))
    if gl:
        tb = sum(x[1] for x in gl)
        ta = sum(x[1] / (1 + x[2]) for x in gl)
        gain_gen = tb / ta - 1.0
        ok_gen = gain_gen >= 0.05 and all(x[2] >= 0.02 for x in gl) and all(x[3] <= 0.05 for x in gl)
    else:
        gain_gen, ok_gen = None, None
    tous = lig + gl
    J = sum(x[5] for x in tous)
    C = sum(x[6] for x in tous)
    prec = (J / C) if (arm == "P" and C) else None
    precs = [x[4] for x in tous if x[4] is not None]
    gm = sum(x[2] for x in lig) / len(lig) if lig else None
    return {"arm": arm, "budget": budget, "d": d, "lecture": lig, "generation": gl,
            "n_lecture_ok": len(ok_lect), "gain_moyen_lecture": gm, "gain_generation": gain_gen, "ok_generation": ok_gen,
            "precision_agregee": prec, "precisions_par_session": precs}


def verdict(b):
    if b["gain_moyen_lecture"] is None:
        return "indéterminé"
    if b["n_lecture_ok"] >= 3 and b["ok_generation"] and (b["precision_agregee"] is None or b["precision_agregee"] >= 0.85):
        return "tient"
    return "ni tient ni tombe"


def main():
    r120 = json.load(open(sys.argv[1], encoding="utf-8"))
    r20 = json.load(open(sys.argv[2], encoding="utf-8"))
    out = {}
    for tag, res, lect, gens in (("120b", r120, LECT, GEN120),
                                 ("20b", r20, [x.replace("lecture", "lecture") for x in LECT],
                                  ["code.generation", "dialogue.generation", "prose-en.generation", "prose-fr.generation", "wiki.generation"])):
        for budget in ("7%", "20%"):
            for d in (1, 2, 4, 8):
                for arm in ("P", "R"):
                    b = bras(res, arm, budget, d, lect, gens)
                    b["verdict_brut"] = verdict(b)
                    out[f"{tag}|{budget}|d={d}|{arm}"] = b
    json.dump(out, open(sys.argv[3], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for k, b in out.items():
        if k.split("|")[2] in ("d=2",):
            gm = b["gain_moyen_lecture"]
            print(f"{k:22s} lecture gain moyen {100*(gm if gm is not None else float('nan')):+.2f} % ; genres >= +5 % et <= 5 % octets : {b['n_lecture_ok']}/4 ; "
                  f"génération {100*(b['gain_generation'] if b['gain_generation'] is not None else float('nan')):+.2f} % ; "
                  f"précision agrégée {b['precision_agregee']} ; {b['verdict_brut']}")


if __name__ == "__main__":
    main()
