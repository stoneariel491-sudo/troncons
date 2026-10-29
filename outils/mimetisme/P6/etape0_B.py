"""P6 étape 0, variante B : préremplissage par lots, décision rapide/exact par masse agrégée.
Seuils : mesures/mimetisme/P6/00-seuils-declares.md § 3. Pas de cache : chaque expert appelé dans un lot,
à une couche, est lu une fois (exact = 1, rapide = rho).
Usage : python -I -X utf8 etape0_B.py <dossier traces> <préfixe 120b|20b> <sortie.json>"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import tiers

dossier, modele, sortie = sys.argv[1:4]
RHO = 0.718
S_CIBLES = [0.05, 0.08, 0.10, 0.14]
TAILLES = [128, 256, 512]
if modele == "120b":
    GENRES = {"code": "t120b.code.lecture", "dialogue": "t120b.dialogue.lecture", "prose-en": "t120b.prose-en.lecture",
              "prose-fr": "t120b.prose-fr.lecture"}
    SUPP = {"wiki-lecture": "w120b.wiki.lecture"}
else:
    GENRES = {"code": "t20b.code.lecture", "dialogue": "t20b.dialogue.lecture", "prose-en": "t20b.prose-en.lecture",
              "prose-fr": "t20b.prose-fr.lecture"}
    SUPP = {"wiki-lecture": "w20b.wiki.lecture"}


def cles(ex, w, E, taille):
    """Une ligne par (lot, couche, expert) appelé : n appels, masse, max, énergie (somme w^2), lot."""
    T, L, K = ex.shape
    lot = (np.arange(T) // taille)[:, None, None]
    cle = ((lot * L + np.arange(L)[None, :, None]) * E + ex).reshape(-1).astype(np.int64)
    wf = w.reshape(-1)
    u, inv = np.unique(cle, return_inverse=True)
    n = np.bincount(inv)
    masse = np.bincount(inv, weights=wf)
    e2 = np.bincount(inv, weights=wf * wf)
    mx = np.zeros(len(u))
    np.maximum.at(mx, inv, wf)
    lot_u = u // (L * E)
    return {"n": n, "masse": masse, "max": mx, "e2": e2, "lot": lot_u}


REGLES = ("max", "masse", "energie", "hasard")


def rangs(K, rng):
    """Ordre croissant de chaque score (ex æquo départagés au hasard) : un tri par règle."""
    sc = {"max": K["max"], "masse": K["masse"], "energie": K["e2"], "hasard": rng.random(len(K["e2"]))}
    return {r: np.lexsort((rng.random(len(K["e2"])), sc[r])) for r in REGLES}


def r_a_S(K, ordres, fracs):
    """r pour chaque règle et chaque fraction de clés rapides (à octets économisés égaux)."""
    tot = K["e2"].sum()
    out = {}
    for r in REGLES:
        cum = np.cumsum(K["e2"][ordres[r]])
        out[r] = [float(cum[int(round(f * len(cum))) - 1] / tot) / f for f in fracs]
    return out


def evalue_genre(K, fracs, tirages=100):
    rng = np.random.default_rng(11)
    pt = r_a_S(K, rangs(K, np.random.default_rng(1)), fracs)
    lots = np.unique(K["lot"])
    par_lot = [np.flatnonzero(K["lot"] == b) for b in lots]
    rs = {r: [] for r in REGLES}
    for _ in range(tirages):
        tir = rng.integers(0, len(lots), size=len(lots))
        idx = np.concatenate([par_lot[i] for i in tir])
        Ks = {k: v[idx] for k, v in K.items()}
        x = r_a_S(Ks, rangs(Ks, rng), fracs)
        for r in REGLES:
            rs[r].append(x[r])
    return {r: [{"S": S, "r": pt[r][i], "sigma": float(np.std([t[i] for t in rs[r]]))}
                for i, S in enumerate(S_CIBLES)] for r in REGLES}


R = {"rho": RHO, "S_cibles": S_CIBLES}
for taille in TAILLES:
    R[f"lot{taille}"] = {}
    for groupe, dic in (("genres", GENRES), ("supplement", SUPP)):
        for genre, base in dic.items():
            ex, w, E = tiers.charger(os.path.join(dossier, base + ".trace"), os.path.join(dossier, base + ".poids"))
            K = cles(ex, w, E, taille)
            stats = {"jetons": int(ex.shape[0]), "lots": int(len(np.unique(K["lot"]))), "cles": int(len(K["n"])),
                     "part_cles_a_1_appel": float((K["n"] == 1).mean())}
            # la remarque de vivant #3 : part des clés qui portent les 1,2 % de masse les plus basses
            ordre = np.argsort(K["masse"])
            cum = np.cumsum(K["masse"][ordre]) / K["masse"].sum()
            stats["part_cles_portant_1.2pct_de_la_masse"] = float((cum <= 0.012).mean())
            ev = evalue_genre(K, [S / (1.0 - RHO) for S in S_CIBLES])
            res = {f"S{S:.2f}": {r: {"r": ev[r][i]["r"], "sigma": ev[r][i]["sigma"]} for r in REGLES}
                   for i, S in enumerate(S_CIBLES)}
            R[f"lot{taille}"][genre] = {"stats": stats, "r_a_S_egal": res}
            print(taille, genre, stats, {k: {rg: round(v["r"], 3) for rg, v in vv.items()} for k, vv in res.items() if k == "S0.08"},
                  flush=True)

# verdict déclaré § 3, lots de 512, S = 8 %
V = {}
comp = {}
for genre in GENRES:
    x = R["lot512"][genre]["r_a_S_egal"]["S0.08"]
    comp[genre] = {"r_A": x["max"]["r"], "r_B": x["masse"]["r"], "r_energie": x["energie"]["r"],
                   "B_le_0.70": x["masse"]["r"] <= 0.70, "B_le_0.9A": x["masse"]["r"] <= 0.9 * x["max"]["r"],
                   "B_ge_A": x["masse"]["r"] >= x["max"]["r"], "B_gt_0.9": x["masse"]["r"] > 0.9}
V["par_genre"] = comp
V["tient"] = bool(sum(1 for c in comp.values() if c["B_le_0.70"] and c["B_le_0.9A"]) >= 3)
V["tombe"] = bool(sum(1 for c in comp.values() if c["B_ge_A"]) >= 3 or sum(1 for c in comp.values() if c["B_gt_0.9"]) >= 3)
R["verdict_B_lot512_S8pct"] = V
print(json.dumps(V, indent=1))
json.dump(R, open(sortie, "w", encoding="utf-8"), indent=1, default=float)
