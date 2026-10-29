"""P2 : lit temoins.csv, grille.csv, chaine.csv (et rust.csv s'il existe), vérifie les témoins déclarés
dans genome/mimetisme/P2/seuil-declare.md, calcule le verdict au seuil, écrit mesures/mimetisme/P2/verdict.json.
Usage : python -I -X utf8 verdict.py
"""
import csv
import json
import os

B = "~/dev/active/troncons/mesures/mimetisme/P2"
H2 = "~/dev/active/troncons/mesures/mimetisme/ingenierie/h2.csv"
GENS = ["prose-en.generation", "wiki.generation"]
T_JETON = 345.0   # ms, un jeton (consigne)
T_DISQUE, T_RAM, T_RAM_ENC, T_DESC = 4.1, 1.09, 1.8, 1.09


def lire(nom):
    return list(csv.DictReader(open(f"{B}/{nom}", encoding="utf-8")))


def cle(r):
    return (r["trace"], int(r["V"]), int(r["R"]), r["mode"])


def idx(rows):
    return {cle(r): r for r in rows}


tem, gri, cha = idx(lire("temoins.csv")), idx(lire("grille.csv")), idx(lire("chaine.csv"))
bord = idx(lire("t1bord.csv"))
out = {"temoins": {}}
f = lambda r, k: float(r[k])

# T0 : R = 0, tous les modes == seul (entiers)
t0 = []
for (tr, V, R, m), r in tem.items():
    if R == 0 and m in ("inclusif", "exclusif", "cass_a", "cass_b", "cass_c"):
        s = tem[(tr, V, 0, "seul")]
        t0.append(r["disque"] == s["disque"] and r["succes_vram"] == s["succes_vram"])
out["temoins"]["T0_R0_egale_LRU_seul"] = dict(ok=all(t0), n=len(t0))

# T1 : inclusif R<=V ajoute ~0
t1 = {}
for tr in {k[0] for k in tem}:
    for R, tol in ((80, 1e-4), (160, 1e-4), (326, 1e-3)):
        r = tem.get((tr, 326, R, "inclusif")) or bord.get((tr, 326, R, "inclusif"))
        if r:
            t1[f"{tr}|R={R}"] = dict(ajout=f(r, "succes_ram"), tol=tol, ok=f(r, "succes_ram") <= tol)
out["temoins"]["T1_inclusif_ajoute_0"] = dict(ok=all(v["ok"] for v in t1.values()), detail=t1)

# T2 : exclusif = LRU unique V+R a 7e-4
t2 = {}
for tr in {k[0] for k in tem}:
    for R in (80, 336):
        e = tem[(tr, 326, R, "exclusif")]
        u = tem[(tr, 326 + R, 0, "unique_V+R")] if (tr, 326 + R, 0, "unique_V+R") in tem else None
        # le mode 'unique_V+R' a ete ecrit avec le mode 'seul' et l'etiquette ci-dessus
        if u is None:
            continue
        ecart = (f(e, "succes_vram") + f(e, "succes_ram")) - f(u, "succes_vram")
        t2[f"{tr}|R={R}"] = dict(ecart=round(ecart, 6), ok=abs(ecart) <= 7e-4)
out["temoins"]["T2_exclusif_egale_LRU_V+R"] = dict(ok=all(v["ok"] for v in t2.values()), detail=t2)

# T3 : cassures
t3a = [tem[(tr, 326, R, "cass_a")]["disque"] == tem[(tr, 326, R, "seul")]["disque"]
       for tr in {k[0] for k in tem} for R in (80, 336) if (tr, 326, R, "cass_a") in tem]
t3b = [tem[(tr, 326, R, "cass_b")]["disque"] == tem[(tr, 326, R, "inclusif")]["disque"]
       for tr in {k[0] for k in tem} for R in (80, 336) if (tr, 326, R, "cass_b") in tem]
out["temoins"]["T3a_demotion_supprimee_redonne_seul"] = dict(ok=all(t3a), n=len(t3a))
out["temoins"]["T3b_remplissage_au_defaut_redonne_inclusif"] = dict(ok=all(t3b), n=len(t3b))

# T4 : reproduction de h2.csv de l'eclaireur (5e-4)
t4 = {}
for x in csv.DictReader(open(H2, encoding="utf-8")):
    if x["mode"] in ("inclusif", "exclusif"):
        k = (x["trace"], 326, int(x["R"]), x["mode"])
        if k in gri:
            d = abs(f(gri[k], "part_disque") - float(x["part_disque"]))
            t4[f"{k[0]}|{k[3]}|R={k[2]}"] = dict(ecart=round(d, 6), ok=d <= 5e-4)
out["temoins"]["T4_reproduit_h2_de_l_eclaireur"] = dict(ok=all(v["ok"] for v in t4.values()), n=len(t4), detail=t4)

# --- verdict au seuil
V, R = 326, 336
res = {}
for tr in GENS:
    inc, exc, seul = gri[(tr, V, R, "inclusif")], gri[(tr, V, R, "exclusif")], gri[(tr, V, 0, "seul")]
    di, de, ds = f(inc, "part_disque"), f(exc, "part_disque"), f(seul, "part_disque")
    desc_tok = f(exc, "demotions_par_jeton")
    desc_ms = desc_tok * T_DESC
    jetons = int(exc["jetons"])
    fautes_tok = f(exc, "acces") / jetons * (1 - f(exc, "succes_vram"))           # defauts VRAM par jeton
    # temps de service des defauts VRAM par jeton (ms)
    base = fautes_tok * T_DISQUE
    ram_hits_tok = f(exc, "succes_ram") * f(exc, "acces") / jetons
    disk_tok = f(exc, "disque") / jetons
    serie = disk_tok * T_DISQUE + ram_hits_tok * T_RAM + desc_ms                   # tout en serie
    recouvert = disk_tok * T_DISQUE + ram_hits_tok * T_RAM                         # descente cachee
    res[tr] = dict(
        part_disque_seul=ds, part_disque_inclusif=di, part_disque_exclusif=de,
        reduction_vs_inclusif=(di - de) / di, reduction_vs_seul=(ds - de) / ds,
        demotions_par_jeton=desc_tok, descente_ms_par_jeton=desc_ms,
        descente_part_du_jeton=desc_ms / T_JETON,
        defauts_vram_par_jeton=fautes_tok, temps_defauts_base_ms=base,
        temps_defauts_exclusif_serie_ms=serie, temps_defauts_exclusif_recouvert_ms=recouvert,
        gain_serie_ms=base - serie, gain_recouvert_ms=base - recouvert,
    )
out["seuil_V326_R336"] = res
red = [res[t]["reduction_vs_inclusif"] for t in GENS]
desc = [res[t]["descente_part_du_jeton"] for t in GENS]
if min(red) < 0.05:
    verdict = "tombe"
elif min(red) >= 0.15 and max(desc) <= 0.25:
    verdict = "tient"
else:
    verdict = "ouvert"
out["verdict"] = verdict
out["reductions_vs_inclusif"] = red
out["descente_parts"] = desc

# table des reductions sur la grille
tab = []
for tr in list(GENS) + ["tous.lecture"] + [t for t in ("code.lecture", "dialogue.lecture", "prose-en.lecture", "prose-fr.lecture", "wiki.lecture")]:
    for Vv in (326, 922):
        for Rr in (80, 160, 336, 672, 1344):
            i, e = gri[(tr, Vv, Rr, "inclusif")], gri[(tr, Vv, Rr, "exclusif")]
            tab.append(dict(trace=tr, V=Vv, R=Rr, disque_incl=f(i, "part_disque"), disque_excl=f(e, "part_disque"),
                            reduction=(f(i, "part_disque") - f(e, "part_disque")) / f(i, "part_disque"),
                            demotions_par_jeton=f(e, "demotions_par_jeton")))
out["grille"] = tab
chtab = []
for g in ("prose-en", "wiki"):
    for Vv in (326, 922):
        for Rr in (80, 160, 336, 672, 1344):
            i, e = cha[(f"{g}.chaine", Vv, Rr, "inclusif")], cha[(f"{g}.chaine", Vv, Rr, "exclusif")]
            chtab.append(dict(chaine=g, V=Vv, R=Rr, disque_seul=f(cha[(f"{g}.chaine", Vv, 0, "seul")], "part_disque"),
                              disque_incl=f(i, "part_disque"), disque_excl=f(e, "part_disque"),
                              reduction=(f(i, "part_disque") - f(e, "part_disque")) / f(i, "part_disque"),
                              demotions_par_jeton=f(e, "demotions_par_jeton")))
out["chaine"] = chtab

# second chemin Rust s'il existe
if os.path.exists(f"{B}/rust.csv"):
    ru = {}
    for r in csv.DictReader(open(f"{B}/rust.csv", encoding="utf-8")):
        ru[(r["trace"], int(r["V"]), int(r["R"]), r["mode"])] = r
    d2 = {}
    for k, r in ru.items():
        if k in gri:
            d2["|".join(map(str, k))] = round(abs(float(r["part_disque"]) - f(gri[k], "part_disque")), 7)
    out["second_chemin_rust"] = dict(n=len(d2), max_ecart=max(d2.values()) if d2 else None, ok=(max(d2.values()) <= 1e-4) if d2 else None,
                                     detail=d2)

json.dump(out, open(f"{B}/verdict.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("verdict :", verdict)
for k, v in out["temoins"].items():
    print(k, v["ok"])
for tr in GENS:
    r = res[tr]
    print(tr, {k: round(v, 4) for k, v in r.items()})
if "second_chemin_rust" in out:
    print("rust", out["second_chemin_rust"]["n"], out["second_chemin_rust"]["max_ecart"], out["second_chemin_rust"]["ok"])
