"""L'espace latent des états de la couche 23 de gpt-oss-20b (Tome III, figure III-7.6).

Écrit pour troncons, lot « espaces latents » du premier flux de figures du Tome III, le 2026-10-27.
Calcul sur le processeur seul, en mémoire bornée (moins de 1 Go) : aucune passe du modèle, aucune carte.

LES ENTRÉES. Les 6 132 états de calibration de la couche 23 (h après la norme d'après l'attention,
f32, fenêtres 10 à 21 de wiki.test), capturés par l'éclaireur (genome-capture, genome/01-eclaireur.md
§ 1) : `h-L23.f32` (6 132 × 2 880, petit-boutiste) et `routage-L23.bin` (par position : 4 octets
d'experts, puis leurs 4 poids f32). Le routeur réel, lu dans le GGUF : `blk.23.ffn_gate_inp.weight`
(32 × 2 880, F32) et `.bias` (32, F32) ; ses logits biaisés z = W_r h + b_r.

CE QUI EST TIRÉ, par état :
  - l'expert premier (celui de plus grand logit, le premier octet du journal de routage) ;
  - la marge du routeur, au sens de la capture et de la piste tropicale : z(4) − z(5), l'écart entre
    le 4e et le 5e logit biaisé, la distance à un changement de l'ensemble des 4 experts servis ; et,
    pour mémoire, z(1) − z(2), la distance à un changement de l'expert premier ;
  - deux projections planes de h : l'ACP (centrée, non réduite : la géométrie réelle des états, dans
    les unités où le routeur les lit), puis t-SNE (van der Maaten et Hinton 2008), écrit ici de zéro.

T-SNE, PARAMÈTRES (déclarés avant la passe, écrits au JSON) : distances euclidiennes de h en 2 880
dimensions ; P gaussienne sur les 90 plus proches voisins (3 × perplexité, comme van der Maaten 2014),
perplexité 30 ; P symétrisée ; gradient exact contre Q dense (Student à un degré de liberté) ;
initialisation par l'ACP, réduite à un écart-type 1e-4 sur le premier axe (Kobak et Berens 2019) ;
exagération 12 pendant 250 pas, inertie 0,5 puis 0,8, pas d'apprentissage n/12 (Belkina et al. 2019),
gains de Jacobs (+0,2, ×0,8, plancher 0,01) ; 1 000 pas. Un seul fil de calcul (BLAS à 1 fil) : la
passe est déterministe et se redonne au bit. La graine ne sert qu'aux tirages (paires du Spearman,
permutation du témoin W1).

LA FIDÉLITÉ D'UNE PROJECTION (mesurée, écrite en légende) : avec k = 10, la confiance T(k) et la
continuité C(k) (Venna et Kaski 2001), qui pèsent les voisins inventés et les voisins perdus par leur
rang dans l'espace d'origine ; la part des k plus proches voisins gardés ; la corrélation de Spearman
entre distances d'origine et distances planes sur 200 000 paires tirées ; la part de variance du plan
(ACP). Et, pour lire les couleurs : la part des k voisins qui partagent l'expert premier de l'état,
dans l'espace d'origine, dans chaque plan, et au hasard (Σ p_e²).

SEUIL, DÉCLARÉ AVANT LA PASSE (2026-10-27) : la projection t-SNE n'est gardée pour la figure que si
sa confiance T(10) ET sa continuité C(10) sont toutes deux au moins égales à celles du plan de l'ACP,
mesurées dans la même passe (la projection non linéaire ne se montre que si elle garde mieux les
voisinages que la projection linéaire qu'elle remplace) ; sinon la figure ne montre que l'ACP.

TÉMOINS (chacun doit pouvoir tomber ; sa cassure est calculée dans la même passe et écrite) :
  W0 le routeur relu : l'ensemble des 4 experts recalculé depuis h et le GGUF égale celui du journal
     de routage pour les 6 132 états, l'expert premier aussi, et le softmax des 4 logits égale les
     poids du journal à 1e-6 ; cassure : le biais du routeur omis, des ensembles doivent changer.
  W1 l'instrument de fidélité : l'ACP complète (toutes les composantes, une rotation de h) rend
     T(10) = C(10) = 1 à 1e-6 ; cassure : le plan de l'ACP dont les lignes sont permutées (graine)
     doit tomber près du hasard, T(10) < 0,6.

Sorties (mesures/genome/tome3/latents/) :
  etats-c23.csv  : position, expert premier, les 4 experts, marge z4−z5, marge z1−z2, x et y de l'ACP,
                   x et y de t-SNE (vides si la projection n'est pas gardée) ;
  etats-c23.json : paramètres, graine, témoins, fidélités, quantiles des marges, comptes par expert.

  python -I -X utf8 outils/genome/tome3/latents_etats.py
"""
from __future__ import annotations

import os

for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ[_v] = "1"

import csv  # noqa: E402
import importlib.util  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402
from scipy import sparse, stats  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", "..", ".."))
GGUF = "~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf"
CALIB = "~/dev/essais/troncons/genome/eclaireur/calib"
SORTIE = os.path.join(RACINE, "mesures/genome/tome3/latents")
COUCHE = 23
D = 2880
GRAINE = 20261027
K_FID = 10
PAIRES = 200_000
PARAMS_TSNE = {"perplexite": 30.0, "voisins": 90, "pas": 1000, "exageration": 12.0, "pas_exageration": 250,
               "inertie": [0.5, 0.8], "apprentissage": "n/12", "init": "ACP, écart-type 1e-4 sur l'axe 1",
               "gains": [0.2, 0.8, 0.01], "fils_blas": 1}


def lecteur():
    spec = importlib.util.spec_from_file_location("gguf_lecture", os.path.join(RACINE, "outils/03-entropie/gguf_lecture.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gguf_lecture"] = mod
    spec.loader.exec_module(mod)
    lec = mod.LecteurGGUF(GGUF)
    return lec, {t.nom: t for t in lec.tenseurs}


def routeur(lec, tens):
    w = tens[f"blk.{COUCHE}.ffn_gate_inp.weight"]
    b = tens[f"blk.{COUCHE}.ffn_gate_inp.bias"]
    assert w.nom_type == "F32" and tuple(w.dims) == (D, 32), (w.nom_type, w.dims)
    Wr = np.asarray(lec.octets(w)).view("<f4").reshape(32, D).astype(np.float64)
    br = np.asarray(lec.octets(b)).view("<f4").astype(np.float64)
    return Wr, br


def top4(z):
    o = np.argsort(-z, axis=1, kind="stable")
    return o[:, :4]


# ---------------------------------------------------------------- distances et fidélité

def distances2(X):
    """Carrés des distances euclidiennes (n × n, f64 calculé, rendu en f32), diagonale à +inf."""
    n2 = np.einsum("ij,ij->i", X, X)
    G = X @ X.T
    D2 = n2[:, None] + n2[None, :] - 2.0 * G
    del G
    np.maximum(D2, 0.0, out=D2)
    D2 = D2.astype(np.float32)
    np.fill_diagonal(D2, np.inf)
    return D2


def rangs_ligne(d):
    """Rang (1 = plus proche) de chaque point dans une ligne de distances (le point lui-même à +inf)."""
    o = np.argsort(d, kind="stable")
    r = np.empty(d.size, dtype=np.int32)
    r[o] = np.arange(1, d.size + 1, dtype=np.int32)
    return r


def fidelite(D2_haut, Y, k, premier):
    """Confiance T(k), continuité C(k), part des k voisins gardés, accord de l'expert premier (plan)."""
    n = Y.shape[0]
    D2_bas = distances2(Y)
    s_t = s_c = 0.0
    garde = 0
    accord = 0
    for i in range(n):
        rh = rangs_ligne(D2_haut[i])
        rb = rangs_ligne(D2_bas[i])
        vh = rh <= k
        vb = rb <= k
        s_t += float((rh[vb & ~vh] - k).sum())
        s_c += float((rb[vh & ~vb] - k).sum())
        garde += int((vh & vb).sum())
        accord += int((premier[vb] == premier[i]).sum())
    z = 2.0 / (n * k * (2 * n - 3 * k - 1))
    return {"T": 1 - z * s_t, "C": 1 - z * s_c, "voisins_gardes": garde / (n * k),
            "accord_premier_plan": accord / (n * k)}


def accord_haut(D2_haut, k, premier):
    n = D2_haut.shape[0]
    a = 0
    for i in range(n):
        v = np.argpartition(D2_haut[i], k)[:k]
        a += int((premier[v] == premier[i]).sum())
    return a / (n * k)


def spearman(D2_haut, Y, rng):
    n = Y.shape[0]
    i = rng.integers(0, n, PAIRES)
    j = rng.integers(0, n, PAIRES)
    m = i != j
    i, j = i[m], j[m]
    dh = np.sqrt(D2_haut[i, j].astype(np.float64))
    db = np.sqrt(((Y[i] - Y[j]) ** 2).sum(axis=1))
    return float(stats.spearmanr(dh, db).statistic)


# ---------------------------------------------------------------- t-SNE, écrit ici

def p_conditionnelles(D2, voisins, perplexite):
    """P_{j|i} gaussienne sur les `voisins` plus proches, σ_i par dichotomie sur l'entropie."""
    n = D2.shape[0]
    cible = np.log(perplexite)
    lignes, cols, vals = [], [], []
    for i in range(n):
        v = np.argpartition(D2[i], voisins)[:voisins]
        d = D2[i, v].astype(np.float64)
        d = d - d.min()
        beta, bas, haut = 1.0, 0.0, np.inf
        for _ in range(200):
            p = np.exp(-d * beta)
            sp = p.sum()
            h = np.log(sp) + beta * (d * p).sum() / sp
            if abs(h - cible) < 1e-10:
                break
            if h > cible:
                bas = beta
                beta = beta * 2 if haut == np.inf else (beta + haut) / 2
            else:
                haut = beta
                beta = (beta + bas) / 2
        lignes.append(np.full(voisins, i))
        cols.append(v)
        vals.append(p / sp)
    P = sparse.csr_matrix((np.concatenate(vals), (np.concatenate(lignes), np.concatenate(cols))), shape=(n, n))
    P = P + P.T
    P = P / P.sum()
    return P.tocoo()


def tsne(P, Y0, params, journal):
    n = Y0.shape[0]
    Y = Y0.copy()
    iY = np.zeros_like(Y)
    gains = np.ones_like(Y)
    eta = n / 12.0
    pi, pj, pv = P.row, P.col, P.data
    bloc = 1024
    for t in range(params["pas"]):
        ex = params["exageration"] if t < params["pas_exageration"] else 1.0
        mom = params["inertie"][0] if t < params["pas_exageration"] else params["inertie"][1]
        # part attractive, sur les arêtes de P
        dy = Y[pi] - Y[pj]
        num_e = 1.0 / (1.0 + (dy * dy).sum(axis=1))
        att = np.zeros_like(Y)
        w = (ex * pv * num_e)[:, None] * dy
        np.add.at(att, pi, w)
        # part répulsive, contre Q dense, par blocs de lignes
        rep = np.zeros_like(Y)
        Z = 0.0
        n2 = (Y * Y).sum(axis=1)
        for a in range(0, n, bloc):
            b = min(a + bloc, n)
            d2 = n2[a:b, None] + n2[None, :] - 2.0 * (Y[a:b] @ Y.T)
            num = 1.0 / (1.0 + np.maximum(d2, 0.0))
            num[np.arange(b - a), np.arange(a, b)] = 0.0
            Z += float(num.sum())
            num2 = num * num
            rep[a:b] = Y[a:b] * num2.sum(axis=1)[:, None] - num2 @ Y
        grad = 4.0 * (att - rep / Z)
        gains = np.where(np.sign(grad) != np.sign(iY), gains + params["gains"][0], gains * params["gains"][1])
        np.maximum(gains, params["gains"][2], out=gains)
        iY = mom * iY - eta * gains * grad
        Y = Y + iY
        Y = Y - Y.mean(axis=0)
        if t % 100 == 0 or t == params["pas"] - 1:
            # KL(P || Q) sur les arêtes de P (Q du pas, avant la mise à jour de Z)
            dy = Y[pi] - Y[pj]
            q = 1.0 / (1.0 + (dy * dy).sum(axis=1)) / Z
            kl = float((pv * np.log(pv / np.maximum(q, 1e-300))).sum())
            journal.append({"pas": t, "kl": kl, "exageration": ex})
            print(f"t-SNE pas {t} : KL {kl:.5f}", file=sys.stderr, flush=True)
    return Y


# ---------------------------------------------------------------- la passe

def main() -> int:
    t0 = time.time()
    os.makedirs(SORTIE, exist_ok=True)
    lec, tens = lecteur()
    Wr, br = routeur(lec, tens)
    h = np.memmap(os.path.join(CALIB, f"h-L{COUCHE:02d}.f32"), dtype="<f4", mode="r").reshape(-1, D)
    r = np.fromfile(os.path.join(CALIB, f"routage-L{COUCHE:02d}.bin"), dtype=np.uint8).reshape(-1, 20)
    choix = r[:, :4].astype(np.int64)
    g = r[:, 4:].copy().view("<f4").reshape(-1, 4).astype(np.float64)
    n = h.shape[0]
    assert n == choix.shape[0]
    X = np.asarray(h, dtype=np.float64)

    # W0 : le routeur relu
    z = X @ Wr.T + br
    o = top4(z)
    w0_ens = int((np.sort(o, axis=1) == np.sort(choix, axis=1)).all(axis=1).sum())
    w0_prem = int((o[:, 0] == choix[:, 0]).sum())
    zc = np.take_along_axis(z, choix, axis=1)
    p = np.exp(zc - zc.max(axis=1, keepdims=True))
    p /= p.sum(axis=1, keepdims=True)
    w0_poids = float(np.abs(p - g).max())
    o_c = top4(X @ Wr.T)
    w0_cassure = int((np.sort(o_c, axis=1) == np.sort(choix, axis=1)).all(axis=1).sum())
    W0 = {"ensembles_egaux": w0_ens, "premiers_egaux": w0_prem, "ecart_poids_max": w0_poids,
          "tient": w0_ens == n and w0_prem == n and w0_poids < 1e-6,
          "cassure_sans_biais_ensembles_egaux": w0_cassure, "cassure_tombe": w0_cassure < n}
    print(f"W0 : {W0}", file=sys.stderr, flush=True)
    premier = choix[:, 0]
    zs = -np.sort(-z, axis=1)
    marge45 = zs[:, 3] - zs[:, 4]
    marge12 = zs[:, 0] - zs[:, 1]

    # ACP
    Xc = X - X.mean(axis=0)
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    var = S ** 2 / (S ** 2).sum()
    acp = U[:, :2] * S[:2]
    # orientation fixée : la coordonnée de plus grand module de chaque axe est positive
    for a in range(2):
        if acp[np.abs(acp[:, a]).argmax(), a] < 0:
            acp[:, a] *= -1
    complet = U * S
    del U, Vt, Xc

    D2 = distances2(X)
    rng = np.random.default_rng(GRAINE)
    fid = {}
    fid["acp"] = fidelite(D2, acp, K_FID, premier)
    fid["acp"]["spearman"] = spearman(D2, acp, rng)
    print(f"ACP : {fid['acp']}", file=sys.stderr, flush=True)
    # W1 : l'instrument
    w1 = fidelite(D2, complet, K_FID, premier)
    del complet
    perm = rng.permutation(n)
    w1c = fidelite(D2, acp[perm], K_FID, premier)
    W1 = {"acp_complete_T": w1["T"], "acp_complete_C": w1["C"],
          "tient": abs(w1["T"] - 1) < 1e-6 and abs(w1["C"] - 1) < 1e-6,
          "cassure_plan_permute_T": w1c["T"], "cassure_plan_permute_C": w1c["C"],
          "cassure_tombe": w1c["T"] < 0.6}
    print(f"W1 : {W1}", file=sys.stderr, flush=True)

    # t-SNE
    journal = []
    P = p_conditionnelles(D2, PARAMS_TSNE["voisins"], PARAMS_TSNE["perplexite"])
    Y0 = acp / acp[:, 0].std() * 1e-4
    Y = tsne(P, Y0, PARAMS_TSNE, journal)
    for a in range(2):
        if Y[np.abs(Y[:, a]).argmax(), a] < 0:
            Y[:, a] *= -1
    fid["tsne"] = fidelite(D2, Y, K_FID, premier)
    fid["tsne"]["spearman"] = spearman(D2, Y, rng)
    print(f"t-SNE : {fid['tsne']}", file=sys.stderr, flush=True)
    garde = fid["tsne"]["T"] >= fid["acp"]["T"] and fid["tsne"]["C"] >= fid["acp"]["C"]
    accord_h = accord_haut(D2, K_FID, premier)
    cpt = np.bincount(premier, minlength=32)
    hasard = float(((cpt / n) ** 2).sum())

    with open(os.path.join(SORTIE, "etats-c23.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["position", "premier", "e1", "e2", "e3", "e4", "marge45", "marge12", "acp1", "acp2", "tsne1", "tsne2"])
        for i in range(n):
            ts = [f"{Y[i, 0]:.6f}", f"{Y[i, 1]:.6f}"] if garde else ["", ""]
            w.writerow([i, int(premier[i]), *[int(c) for c in choix[i]], f"{marge45[i]:.9e}", f"{marge12[i]:.9e}",
                        f"{acp[i, 0]:.6f}", f"{acp[i, 1]:.6f}", *ts])
    q = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
    j = {"outil": "outils/genome/tome3/latents_etats.py", "date": "2026-10-27", "graine": GRAINE,
         "entrees": {"h": f"{CALIB}/h-L{COUCHE:02d}.f32", "routage": f"{CALIB}/routage-L{COUCHE:02d}.bin",
                     "gguf": GGUF, "routeur": f"blk.{COUCHE}.ffn_gate_inp.weight, .bias (F32)",
                     "fenetres_calibration": "10 à 21 de wiki.test"},
         "couche": COUCHE, "etats": n, "d_modele": D,
         "temoin_W0_routeur": W0, "temoin_W1_fidelite": W1,
         "acp_part_variance": var[:10].tolist(), "acp_part_variance_plan": float(var[:2].sum()),
         "k_fidelite": K_FID, "paires_spearman": PAIRES, "fidelite": fid,
         "accord_premier_espace_origine": accord_h, "accord_premier_hasard": hasard,
         "seuil_declare": "t-SNE gardée si T(10) et C(10) ≥ ceux de l'ACP (même passe)",
         "tsne_gardee": bool(garde), "tsne_parametres": PARAMS_TSNE, "tsne_journal": journal,
         "marge45_quantiles": dict(zip([str(x) for x in q], np.quantile(marge45, q).tolist())),
         "marge12_quantiles": dict(zip([str(x) for x in q], np.quantile(marge12, q).tolist())),
         "comptes_premier": cpt.tolist(), "experts_premiers_distincts": int((cpt > 0).sum()),
         "duree_s": time.time() - t0}
    with open(os.path.join(SORTIE, "etats-c23.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(json.dumps({k: j[k] for k in ("temoin_W0_routeur", "temoin_W1_fidelite", "fidelite", "tsne_gardee",
                                        "acp_part_variance_plan", "accord_premier_espace_origine", "accord_premier_hasard", "duree_s")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
