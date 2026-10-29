"""Juge de P3 à N = 238 : mon propre chemin, sans importer p3_*.py, le `juge kl` ni le lecteur du juge de N = 146.

  python -I -X utf8 juge_N238.py empreintes  → SHA-256 des .kld, des journaux imposés, des copies lues, des routages enregistrés
  python -I -X utf8 juge_N238.py defauts     → défauts du cache (N = 238) par MON LRU à horodatage, imposition cellule par cellule
  python -I -X utf8 juge_N238.py kl          → KL, premier choix et marges relus des .kld en flux (référence + 10 fichiers)
  python -I -X utf8 juge_N238.py analyse     → verdicts, sensibilité à la marge, bootstrap par blocs, témoins
  python -I -X utf8 juge_N238.py comparer    → mes positions contre le CSV de `juge kl` (lu seulement ici, après mon calcul)

Lecture du .kld écrite de nouveau depuis la description du format (en-tête "_logits_", u32 n_ctx, i32 n_vocab, i32 n_fenêtres,
jetons i32, puis par position notée un bloc de 2·⌈n_vocab/2⌉ + 4 mots u16 : f32 pas, f32 log p_min, n_vocab codes).
Je contrôle le décodage par Σ exp(log p) ≈ 1 sur chaque position.

LRU : écrit depuis la définition de 00-seuils-declares.md § 2, avec un horodatage par expert (et non une liste ordonnée) :
global sur 24 × 32 = 768 experts, accès t croissant puis l croissant, dans le groupe l'ordre du fichier ; les 4 experts
du groupe sont épinglés pendant le groupe ; la victime est l'expert résident non épinglé de plus petit horodatage.
"""
import csv
import hashlib
import json
import os
import pathlib
import struct
import sys

import numpy as np

DEPOT = pathlib.Path(__file__).resolve().parents[5]
SORTIE = DEPOT / "mesures" / "mimetisme" / "P3" / "juge" / "N238"
R1 = pathlib.Path("~/dev/essais/troncons/lot-R/r1")
P3 = pathlib.Path("~/dev/essais/troncons/mimetisme/P3")
ROUT = DEPOT / "mesures" / "moteur" / "R" / "r1" / "routage"
N_CACHE = round(0.31 * 768)
assert N_CACHE == 238

TESTS = {  # nom → .kld (contre ref-openai-20b.kld)
    "b0.041": "ref-openai-p3-N238-b0.041-20b.kld",
    "b0.05": "ref-openai-p3-N238-b0.05-20b.kld",
    # témoins et calibration : passes réelles déjà calculées, aucune relance
    "T0": "ref-openai-p3-T0-20b.kld",
    "T1": "ref-openai-p3-T1-20b.kld",
    "N146-b0.06": "ref-openai-p3-b0.06-20b.kld",
    "N146-b0.07": "ref-openai-p3-b0.07-20b.kld",
    "openai-bis": "ref-openai-bis-20b.kld",
    "sans-echelle": "ref-openai-sans-echelle-20b.kld",
    "llamacpp": "ref-llamacpp-20b.kld",
    "llamacpp-imite-q8": "ref-llamacpp-imite-q8-kv16-20b.kld",
    "llamacpp-routage-openai": "ref-llamacpp-routage-openai-20b.kld",
}
PAQUET = 8


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while b := f.read(1 << 22):
            h.update(b)
    return h.hexdigest()


def ecrire(nom, obj):
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / nom).write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=float), encoding="utf-8")


# ---------------------------------------------------------------- empreintes
def empreintes():
    r = {"kld": {}, "journaux": {}, "routages_enregistres": {}}
    for nom in ("ref", "T0", "T1", "b0.041", "b0.05"):
        f = "ref-openai-20b.kld" if nom == "ref" else TESTS[nom]
        r["kld"][nom] = sha256(R1 / f)
        print(nom, r["kld"][nom], flush=True)
    avant = json.loads((DEPOT / "mesures/mimetisme/P3/juge/etage-B/empreintes.json").read_text(encoding="utf-8"))
    r["T0_egal_ref"] = r["kld"]["T0"] == r["kld"]["ref"]
    r["T0_egal_N146"] = r["kld"]["T0"] == avant["kld"]["T0"]["sha256"]
    r["T1_egal_N146"] = r["kld"]["T1"] == avant["kld"]["T1"]["sha256"]
    r["ref_egal_N146"] = r["kld"]["ref"] == avant["kld"]["ref"]["sha256"]
    decl = json.loads((DEPOT / "mesures/mimetisme/P3/ensembles-N238.json").read_text(encoding="utf-8"))
    for b in ("0.041", "0.05"):
        src = P3 / "B238" / f"routage-impose-V1-b{b}-N31.bin"
        cop = ROUT / f"p3-N238-b{b}-N31.bin"
        r["journaux"][b] = {"source": sha256(src), "copie_lue": sha256(cop), "declare": decl["lignes"][b]["sha256"]}
        r["journaux"][b]["tout_egal"] = len(set(r["journaux"][b].values())) == 1
        # le fichier β₂ calculé le matin pour N31 (avant le critère)
        if b == "0.05":
            r["journaux"][b]["egal_au_fichier_du_matin"] = sha256(P3 / "B" / "routage-impose-V1-b0.05-N31.bin") == r["journaux"][b]["source"]
    r["beta0_N19"] = sha256(P3 / "B" / "routage-impose-V1-b0.0-N19.bin")
    r["beta0_N31"] = sha256(P3 / "B" / "routage-impose-V1-b0.0-N31.bin")
    r["beta0_N19_egal_N31"] = r["beta0_N19"] == r["beta0_N31"]
    r["cassure_T1"] = sha256(P3 / "B" / "routage-impose-CASSURE-1pct.bin")
    for p in (ROUT / "ref-openai-p3-N238-b0.041-20b.bin", ROUT / "ref-openai-p3-N238-b0.05-20b.bin",
              DEPOT / "mesures/mimetisme/P3/etage-B/N238/routage-enregistre-premiere-passe-b0.041.bin"):
        r["routages_enregistres"][p.name] = sha256(p)
    print(json.dumps(r, indent=1), flush=True)
    ecrire("empreintes.json", r)


# ---------------------------------------------------------------- journaux et LRU
def journal(p):
    d = pathlib.Path(p).read_bytes()
    L, T = struct.unpack_from("<II", d, 0)
    assert len(d) == 8 + 8 * L * T
    a = np.frombuffer(d, dtype=np.uint8, offset=8).reshape(L, T, 8)
    e = a[:, :, :4].copy()                       # (L, T, 4) experts, ordre du fichier
    m = a[:, :, 4:8].copy().view("<f4")[..., 0]  # marge enregistrée
    return e, m


def mon_lru(e, n, ordre_t_puis_l=True):
    """e : (L, T, 4). Horodatage par expert global (l * 32 + e). Renvoie le nombre de défauts."""
    L, T, _ = e.shape
    stamp = np.full(L * 32, -1, dtype=np.int64)  # -1 = absent
    resident = np.zeros(L * 32, dtype=bool)
    occ = 0
    horloge = 0
    defauts = 0
    big = np.iinfo(np.int64).max
    boucle = ((t, l) for t in range(T) for l in range(L)) if ordre_t_puis_l else ((t, l) for l in range(L) for t in range(T))
    for t, l in boucle:
        g = l * 32 + e[l, t].astype(np.int64)
        for k in range(4):
            x = g[k]
            if not resident[x]:
                defauts += 1
                if occ >= n:
                    s = np.where(resident, stamp, big)
                    s[g] = big                     # épinglés : les 4 du groupe
                    v = int(s.argmin())
                    resident[v] = False
                    occ -= 1
                resident[x] = True
                occ += 1
            stamp[x] = horloge
            horloge += 1
    return defauts


def defauts():
    r = {"N": N_CACHE}
    e0, _ = journal(P3 / "B" / "routage-impose-V1-b0.0-N31.bin")
    d0 = mon_lru(e0, N_CACHE)
    r["beta0"] = d0
    r["seuil_10pct"] = 0.9 * d0
    print("beta0", d0, flush=True)
    for nom, p in (("0.041", P3 / "B238/routage-impose-V1-b0.041-N31.bin"), ("0.05", P3 / "B238/routage-impose-V1-b0.05-N31.bin"),
                   ("0.04", P3 / "B/routage-impose-V1-b0.04-N31.bin"),
                   ("0.1", P3 / "routage-impose-V1-b0.1-N31.bin"), ("0.3", P3 / "routage-impose-V1-b0.3-N31.bin"),
                   ("1.0", P3 / "routage-impose-V1-b1.0-N31.bin"), ("3.0", P3 / "routage-impose-V1-b3.0-N31.bin")):
        e, _ = journal(p)
        d = mon_lru(e, N_CACHE)
        chg = (np.sort(e, -1) != np.sort(e0, -1)).any(-1)
        r[nom] = {"defauts": d, "variation": d / d0 - 1, "passe_10pct": d <= 0.9 * d0,
                  "cellules_changees": int(chg.sum()), "part_changee": float(chg.mean())}
        print(nom, r[nom], flush=True)
    # cassures du LRU : ordre l puis t ; ordre inverse dans le groupe ; un ensemble permuté au hasard sur 1 000 cellules
    r["cassure_ordre_l_puis_t_beta0"] = mon_lru(e0, N_CACHE, ordre_t_puis_l=False)
    r["cassure_ordre_inverse_groupe_beta0"] = mon_lru(e0[:, :, ::-1].copy(), N_CACHE)
    rng = np.random.default_rng(238)
    e_p = e0.copy()
    L, T, _ = e0.shape
    for c in rng.choice(L * T, 1000, replace=False):
        l, t = divmod(int(c), T)
        e_p[l, t] = rng.choice(32, 4, replace=False)
    r["cassure_1000_cellules_aleatoires_beta0"] = mon_lru(e_p, N_CACHE)
    # imposition : les 4 experts imposés, dans le même ordre, cellule par cellule, dans le routage enregistré
    imp = {}
    for b in ("0.041", "0.05"):
        ei, _ = journal(P3 / f"B238/routage-impose-V1-b{b}-N31.bin")
        er, mr = journal(ROUT / f"ref-openai-p3-N238-b{b}-20b.bin")
        _, mi = journal(P3 / f"B238/routage-impose-V1-b{b}-N31.bin")
        imp[b] = {"cellules": int(ei.shape[0] * ei.shape[1]),
                  "egales_meme_ordre": int((ei == er).all(-1).sum()),
                  "egales_ensemble": int((np.sort(ei, -1) == np.sort(er, -1)).all(-1).sum()),
                  "cellules_enregistrees_differentes_de_beta0": int((np.sort(er, -1) != np.sort(e0, -1)).any(-1).sum()),
                  "ecart_max_marge_enregistree_vs_imposee": float(np.abs(mr - mi).max())}
        print("imposition", b, imp[b], flush=True)
    er1, _ = journal(DEPOT / "mesures/mimetisme/P3/etage-B/N238/routage-enregistre-premiere-passe-b0.041.bin")
    er2, _ = journal(ROUT / "ref-openai-p3-N238-b0.041-20b.bin")
    imp["premiere_passe_b0.041_egale_derniere"] = bool((er1 == er2).all())
    r["imposition"] = imp
    ecrire("defauts.json", r)


# ---------------------------------------------------------------- .kld
class Kld:
    def __init__(self, p):
        self.f = open(p, "rb", buffering=1 << 20)
        h = self.f.read(20)
        assert h[:8] == b"_logits_", p
        self.n_ctx, self.n_vocab, self.n_fen = struct.unpack("<Iii", h[8:20])
        self.mots = 2 * ((self.n_vocab + 1) // 2) + 4
        self.jetons = np.frombuffer(self.f.read(4 * self.n_ctx * self.n_fen), "<i4").reshape(self.n_fen, self.n_ctx)
        self.par_fen = self.n_ctx - 1 - self.n_ctx // 2
        self.n = self.par_fen * self.n_fen
        assert os.path.getsize(p) == 20 + 4 * self.n_ctx * self.n_fen + 2 * self.mots * self.n

    def lire(self, k):
        u = np.frombuffer(self.f.read(2 * self.mots * k), "<u2").reshape(k, self.mots)
        tete = np.ascontiguousarray(u[:, :4]).view("<f4")
        return u[:, 4:4 + self.n_vocab].astype(np.float64) * tete[:, :1].astype(np.float64) + tete[:, 1:2].astype(np.float64)


def deux_premiers(lp):
    i1 = lp.argmax(1)
    r = np.arange(len(lp))
    v1 = lp[r, i1].copy()
    lp2 = lp.copy()
    lp2[r, i1] = -np.inf
    i2 = lp2.argmax(1)
    return i1, i2, v1 - lp2[r, i2]


def kl():
    ref = Kld(R1 / "ref-openai-20b.kld")
    lec = {}
    for nom, f in TESTS.items():
        x = Kld(R1 / f)
        assert (x.n_ctx, x.n_vocab, x.n_fen) == (ref.n_ctx, ref.n_vocab, ref.n_fen)
        assert (x.jetons == ref.jetons).all(), nom
        lec[nom] = x
    n = ref.n
    R = {"i1": np.zeros(n, np.int64), "i2": np.zeros(n, np.int64), "marge": np.zeros(n), "somme_p": np.zeros(n)}
    S = {nom: {"kl16": np.zeros(n), "kl_tout": np.zeros(n), "kl_renorm": np.zeros(n), "i1": np.zeros(n, np.int64),
               "marge": np.zeros(n), "somme_q": np.zeros(n)} for nom in TESTS}
    i = 0
    while i < n:
        k = min(PAQUET, n - i)
        lp = ref.lire(k)
        p = np.exp(lp)
        sp = p.sum(1)
        i1, i2, mg = deux_premiers(lp)
        sl = slice(i, i + k)
        R["i1"][sl], R["i2"][sl], R["marge"][sl], R["somme_p"][sl] = i1, i2, mg, sp
        lpn = lp - np.log(sp)[:, None]
        pn = np.exp(lpn)
        for nom, x in lec.items():
            lq = x.lire(k)
            d = p * (lp - lq)
            S[nom]["kl16"][sl] = np.where(lp > -16.0, d, 0.0).sum(1)
            S[nom]["kl_tout"][sl] = d.sum(1)
            sq = np.exp(lq).sum(1)
            S[nom]["kl_renorm"][sl] = (pn * (lpn - (lq - np.log(sq)[:, None]))).sum(1)
            S[nom]["somme_q"][sl] = sq
            j1, _, mq = deux_premiers(lq)
            S[nom]["i1"][sl], S[nom]["marge"][sl] = j1, mq
        i += k
        if i % 255 == 0:
            print("positions", i, flush=True)
    SORTIE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(SORTIE / "positions.npz", **{f"ref_{a}": b for a, b in R.items()},
                        **{f"{nom}__{a}": b for nom, d in S.items() for a, b in d.items()}, par_fen=ref.par_fen)
    # CSV lisible des deux passes neuves
    for nom in ("b0.041", "b0.05"):
        with open(SORTIE / f"kl-{nom}-positions.csv", "w", newline="", encoding="utf-8") as fo:
            w = csv.writer(fo)
            w.writerow(["fenetre", "position", "kl16", "kl_renorm", "premier_ref", "second_ref", "premier_test", "meme_premier", "marge_ref"])
            for j in range(n):
                f_, t = divmod(j, ref.par_fen)
                w.writerow([f_, ref.n_ctx // 2 + t, f"{S[nom]['kl16'][j]:.9g}", f"{S[nom]['kl_renorm'][j]:.9g}", R["i1"][j], R["i2"][j],
                            S[nom]["i1"][j], int(R["i1"][j] == S[nom]["i1"][j]), f"{R['marge'][j]:.6f}"])
    print("fini", flush=True)


# ---------------------------------------------------------------- analyse
def charger():
    z = np.load(SORTIE / "positions.npz")
    return z, int(z["par_fen"])


def boot(accord, masque, fen, nfen, tirages=20000, graine=1):
    """Rééchantillonnage des blocs (fenêtres ou blocs fixes) avec remise ; estimateur de rapport Σ accords / Σ positions."""
    a = np.bincount(fen, weights=(accord & masque).astype(float), minlength=nfen)
    m = np.bincount(fen, weights=masque.astype(float), minlength=nfen)
    rng = np.random.default_rng(graine)
    idx = rng.integers(0, nfen, size=(tirages, nfen))
    v = a[idx].sum(1) / m[idx].sum(1)
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))], float((v < 0.95).mean())


def analyse():
    z, pf = charger()
    n = len(z["ref_i1"])
    fen = np.arange(n) // pf
    blocs51 = np.arange(n) // 51              # 50 blocs de 51 positions contiguës (5 par fenêtre)
    marge = z["ref_marge"]
    out = {"n": n, "par_fenetre": pf, "somme_p_min_max": [float(z["ref_somme_p"].min()), float(z["ref_somme_p"].max())],
           "positions_marge>=0.3": int((marge >= 0.3).sum()), "seuils_marge": {}, "passes": {}}
    for nom in TESTS:
        acc = z["ref_i1"] == z[f"{nom}__i1"]
        d = {"kl16": float(z[f"{nom}__kl16"].mean()), "kl_tout": float(z[f"{nom}__kl_tout"].mean()),
             "kl_renorm": float(z[f"{nom}__kl_renorm"].mean()), "litteral": float(acc.mean()), "desaccords": int((~acc).sum())}
        for s in (0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0):
            msk = marge >= s
            d[f"pondere_{s}"] = float(acc[msk].mean())
            d[f"n_{s}"] = int(msk.sum())
        msk = marge >= 0.3
        d["desaccords_pondere_0.3"] = int((~acc & msk).sum())
        d["boot_fenetres_0.3"], d["boot_fenetres_0.3_part_sous_95"] = boot(acc, msk, fen, 10)
        d["boot_blocs51_0.3"], d["boot_blocs51_0.3_part_sous_95"] = boot(acc, msk, blocs51, n // 51)
        d["boot_fenetres_litteral"], _ = boot(acc, np.ones(n, bool), fen, 10)
        d["pondere_par_fenetre_0.3"] = [float(acc[(fen == w) & msk].mean()) for w in range(10)]
        # plus petite marge (grille 0,005) à partir de laquelle le premier choix pondéré atteint 95 %
        grille = np.round(np.arange(0, 1.0001, 0.005), 3)
        ok = [float(s) for s in grille if acc[marge >= s].mean() >= 0.95]
        d["marge_minimale_pour_95"] = ok[0] if ok else None
        d["marge_de_desaccord_mediane"] = float(np.median(marge[~acc])) if (~acc).any() else None
        out["passes"][nom] = d
        print(nom, {k: (round(v, 5) if isinstance(v, float) else v) for k, v in d.items() if not isinstance(v, list)}, flush=True)
    # témoin d'instrument : un décalage d'une position entre référence et test doit faire tomber la porte pondérée
    acc_dec = z["ref_i1"][1:] == z["b0.041__i1"][:-1]
    out["cassure_decalage_1_b0.041_pondere_0.3"] = float(acc_dec[marge[1:] >= 0.3].mean())
    # témoin hors moteur : remplacer au hasard les premiers choix de b0.041 par ceux de sans-echelle sur une part des positions
    rng = np.random.default_rng(7)
    msk = marge >= 0.3
    perte = {}
    for part in (0.05, 0.1, 0.2, 0.4):
        i1 = z["b0.041__i1"].copy()
        sel = rng.random(n) < part
        i1[sel] = z["sans-echelle__i1"][sel]
        perte[str(part)] = float((z["ref_i1"] == i1)[msk].mean())
    out["melange_b0.041_sans_echelle_pondere_0.3"] = perte
    ecrire("analyse.json", out)


def comparer():
    z, pf = charger()
    res = {}
    for nom in ("b0.041", "b0.05"):
        with open(DEPOT / f"mesures/mimetisme/P3/etage-B/N238/juge-kl-p3-N238-{nom}.csv", encoding="utf-8") as f:
            j = list(csv.DictReader(f))
        assert len(j) == len(z["ref_i1"])
        kj = np.array([float(x["kl"]) for x in j])
        mj = np.array([int(x["meme_premier"]) for x in j])
        marj = np.array([float(x["marge_ref"]) for x in j]) if "marge_ref" in j[0] else None
        km = z[f"{nom}__kl16"]
        mm = (z["ref_i1"] == z[f"{nom}__i1"]).astype(int)
        res[nom] = {"kl_moi": float(km.mean()), "kl_juge": float(kj.mean()), "ecart_abs_max": float(np.abs(km - kj).max()),
                    "positions_premier_different": int((mm != mj).sum()),
                    "ecart_marge_max": float(np.abs(marj - z["ref_marge"]).max()) if marj is not None else None}
        print(nom, res[nom], flush=True)
    ecrire("comparaison-juge-kl.json", res)


if __name__ == "__main__":
    {"empreintes": empreintes, "defauts": defauts, "kl": kl, "analyse": analyse, "comparer": comparer}[sys.argv[1]]()
