"""P2 : verdict de la démotion sélective sur le 20b au seuil déclaré (seuil-declare-selectif.md)."""
import csv
import json

B = "~/dev/active/troncons/mesures/mimetisme/P2"
rows = list(csv.DictReader(open(f"{B}/holdout20b.csv", encoding="utf-8")))
d = {(r["trace"], int(r["V"]), r["mode"]): r for r in rows}
GENS = [t for t in {r["trace"] for r in rows} if t.endswith("generation")]
GENS.sort()
out = {}
for V in (54, 154):
    det = {}
    for t in GENS:
        inc = float(d[(t, V, "inclusif")]["part_disque"])
        s0, s1 = d[(t, V, "sel_s0")], d[(t, V, "sel_s1")]
        seul = float(d[(t, V, "seul")]["part_disque"])
        p0, p1 = float(s0["part_disque"]), float(s1["part_disque"])
        d0, d1 = float(s0["demotions_par_jeton"]), float(s1["demotions_par_jeton"])
        fv = float(d[(t, V, "sel_s1_defauts_vram")]["part_disque"]) * 24 * 4  # defauts VRAM par jeton (s1)
        rho1 = (fv - p1 * 24 * 4) / fv if fv else 0.0
        det[t] = dict(seul=seul, inclusif=inc, s0=p0, s1=p1, red_s1_vs_incl=(inc - p1) / inc,
                      red_s0_vs_incl=(inc - p0) / inc, dem_s0=d0, dem_s1=d1, ratio_dem=d1 / d0,
                      b_ok=p1 <= p0 + 0.01, a_ok=(inc - p1) / inc >= 0.15, c_ok=d1 <= 0.6 * d0,
                      serie_par_jeton_gain_ms=None)
    a = sum(v["a_ok"] for v in det.values()); b = sum(v["b_ok"] for v in det.values()); c = sum(v["c_ok"] for v in det.values())
    n = len(det)
    verdict = "tient" if (a >= 4 and b >= 4 and c == n) else ("tombe" if (n - b) >= 3 else "ouvert")
    out[f"V={V}"] = dict(generations=det, a=a, b=b, c=c, n=n, verdict=verdict)
json.dump(out, open(f"{B}/verdict-selectif.json", "w", encoding="utf-8"), indent=1)
for k, v in out.items():
    print(k, "a", v["a"], "b", v["b"], "c", v["c"], "/", v["n"], "->", v["verdict"])
    for t, x in v["generations"].items():
        print("  ", t, {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in x.items() if kk != "serie_par_jeton_gain_ms"})
# lectures, rapport
for V in (54, 154):
    L = sorted({r["trace"] for r in rows if r["trace"].endswith("lecture")})
    print("lectures V", V, [(t, round(float(d[(t, V, "sel_s0")]["part_disque"]), 3), round(float(d[(t, V, "sel_s1")]["part_disque"]), 3)) for t in L])
