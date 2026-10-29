"""P3 : routage conditionné par le cache, borné par la marge. Étage A (boucle ouverte), outils et témoins.

Seuils et témoins : mesures/mimetisme/P3/00-seuils-declares.md (commit 1606f9f, avant toute lecture de données).

Ce que fait ce fichier
  - recalcule les 32 logits du routeur de gpt-oss-20b depuis les entrées capturées (h-Lll.f32) et le routeur F32 du GGUF ;
  - applique un biais bêta aux experts résidents du cache avant le top-4 (Skliar et al., arXiv 2412.00099), le cache étant
    rejoué en même temps (les résidents sont ceux du cache juste avant le groupe : causal) ;
  - compte les défauts d'un LRU global à règle de groupe (celui de trc-cache), la part de cellules qui changent, etc. ;
  - passe les témoins W1 à W6 et leurs cassures ; écrit les ensembles biaisés au format du journal de routage du moteur de référence
    (pour l'étage B, que ce fichier ne lance pas).

Usage (Python -I -X utf8) :
  p3_routage.py synthetique                 témoins W2 à W6 sur des logits synthétiques (aucune donnée lue)
  p3_routage.py reel [--sans-attendre]      attend la disparition du verrou de la carte, lit h et le routeur, passe W1 à W6, mesure

Limites assumées : boucle ouverte (la trajectoire du modèle reste la trajectoire exacte) ; aucune KL mesurée ici.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "2"

import csv
import hashlib
import json
import struct
import sys
import time
from collections import OrderedDict

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", "..", ".."))
CAPTURE = "~/dev/essais/troncons/genome/eclaireur/eval"
LOURDS = "~/dev/essais/troncons/mimetisme/P3"
VERROU = "~/dev/verrou-carte.txt"
SORTIE = os.path.join(RACINE, "mesures", "mimetisme", "P3")
K = 4
BETAS = [0.0, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0]
BETAS_NEG = [-0.1, -0.3]
BUDGETS = {"19": 0.19, "31": 0.31}
KL_PAR_CELLULE = 0.309  # 05 § 2.2 : (0,0145 - 0,00168) / (5087 / 122640)


# ----------------------------------------------------------------------------------------------- cache


class CacheLRU:
    """LRU global, règle de groupe de trc-cache : les k experts du groupe sont épinglés, la victime est le moins récent non épinglé."""

    def __init__(self, n, total):
        self.n = n
        self.od = OrderedDict()
        self.res = np.zeros(total)  # 1.0 si résident (lecture rapide du masque d'une couche)
        self.defauts = 0

    def groupe(self, ids, t=None):
        """ids : identifiants globaux dans l'ordre d'accès (t : indice de position, ignoré par le LRU). Rend le nombre de défauts du groupe et les drapeaux par accès."""
        pins = set(ids)
        manque = []
        for x in ids:
            if x in self.od:
                self.od.move_to_end(x)
                manque.append(False)
                continue
            if len(self.od) >= self.n:
                for v in self.od:
                    if v not in pins:
                        del self.od[v]
                        self.res[v] = 0.0
                        break
            self.od[x] = True
            self.res[x] = 1.0
            self.defauts += 1
            manque.append(True)
        return manque


def preparer(Z):
    """Rangs non biaisés : ORD (T, L, E) indices par logit décroissant (stable)."""
    return np.argsort(-Z, axis=-1, kind="stable")


def simuler(Z, ORD, n_cache, beta, variante="V1", masque="residents", avenir=False, fuite=False, fabrique=None):
    """Une passe : sélection biaisée + rejeu du cache. Rend (ensembles locaux (T,L,4) triés par logit décroissant, manque (T,L,4), défauts).

    variante V1 : top-4 de z + beta * masque sur les E experts ; V2 : les trois premiers restent, le 5e remplace le 4e si son logit biaisé l'emporte.
    masque 'residents' (normal), 'absents' (cassure W3 : on favorise les absents ; classement identique à beta négatif, donc cassure équivalente par construction) ou 'hasard' (W3-hasard : même densité, sans lien avec le cache).
    avenir=True : cassure W6, le masque inclut les experts non biaisés du groupe (t+1, l) (information du futur).
    fuite=True : cassure W6 bis, le masque est lu après l'insertion de l'ensemble non biaisé du groupe (information du présent).
    """
    T, L, E = Z.shape
    cache = (fabrique or CacheLRU)(n_cache, L * E)
    rng = np.random.default_rng(12345)
    S = np.zeros((T, L, K), dtype=np.int16)
    M = np.zeros((T, L, K), dtype=bool)
    for t in range(T):
        for l in range(L):
            z = Z[t, l]
            o = ORD[t, l]
            if beta == 0.0:
                ch = o[:K]
            else:
                res = cache.res[l * E:(l + 1) * E]
                if fuite:
                    res = res.copy()
                    res[o[:K]] = 1.0
                if avenir and t + 1 < T:
                    res = res.copy()
                    res[ORD[t + 1, l][:K]] = 1.0
                if masque == "residents":
                    m = res
                elif masque == "absents":
                    m = 1.0 - res
                else:  # 'hasard' : un masque sans lien avec le cache, de même densité (le gain doit venir de la résidence)
                    m = (rng.random(E) < res.mean()).astype(float)
                if variante == "V1":
                    zb = z + beta * m
                    ch = np.argsort(-zb, kind="stable")[:K]
                else:
                    a, b = o[K - 1], o[K]
                    pris = b if (z[b] + beta * m[b]) > (z[a] + beta * m[a]) else a
                    ch = np.concatenate([o[:K - 1], [pris]])
                ch = ch[np.argsort(-z[ch], kind="stable")]
            S[t, l] = ch
            M[t, l] = cache.groupe([l * E + int(e) for e in ch], t)
    return S, M, cache.defauts


def rejouer_cache2(S, n_cache, E=32):
    """Second chemin (W5) : le LRU de cache2.py (Python indépendant), L et E posés pour le 20b."""
    sys.path.insert(0, os.path.join(RACINE, "outils", "mimetisme", "ingenierie"))
    import cache2
    T, L, _ = S.shape
    cache2.L, cache2.E, cache2.K = L, E, K
    G = (S.astype(np.int32) + (np.arange(L, dtype=np.int32) * E)[None, :, None])
    r = cache2.lru1(G, n_cache)
    acces = T * L * K
    return acces - round(r * acces)


def statistiques(Z, ORD, S0, S):
    """Part de cellules à ensemble changé, experts changés par cellule changée, plus haut logit conservé."""
    a = np.sort(S0, axis=-1)
    b = np.sort(S, axis=-1)
    change = (a != b).any(axis=-1)
    n_change = (S[..., :, None] == S0[..., None, :]).any(-1)  # (T,L,4) : l'expert biaisé était dans l'ensemble exact
    changes = (~n_change).sum(-1)
    haut = (S == ORD[..., :1]).any(-1)
    return {"part_cellules_changees": float(change.mean()),
            "experts_changes_par_cellule_changee": float(changes[change].mean()) if change.any() else 0.0,
            "part_plus_haut_logit_garde": float(haut.mean())}


# ----------------------------------------------------------------------------------------------- journal de routage


def ecrire_journal(S, marges, chemin):
    """Format du journal de routage (r1_reference.py, bascules.py) : u32 couches, u32 positions, puis par couche et par
    position 4 x u8 experts et f32 marge. C'est ce que lit `--imposer-routage` de la référence."""
    T, L, _ = S.shape
    o = bytearray(struct.pack("<II", L, T))
    for l in range(L):
        for p in range(T):
            o += bytes(int(e) for e in S[p, l]) + struct.pack("<f", float(marges[p, l]))
    open(chemin, "wb").write(o)
    return hashlib.sha256(o).hexdigest()


# ----------------------------------------------------------------------------------------------- témoins (sans données)


def temoins_machine(Z, ORD, budgets, log):
    """W2, W3, W5, W6 et leurs cassures. Rend un dict {nom: (tient, détail)}."""
    T, L, E = Z.shape
    r = {}
    for nom, frac in budgets.items():
        n = round(frac * L * E)
        S0, M0, d0 = simuler(Z, ORD, n, 0.0)
        # W2 : beta = 0 ne change rien ; cassure : beta = 0,3 doit changer des cellules.
        S3, M3, d3 = simuler(Z, ORD, n, 0.3)
        chg3 = statistiques(Z, ORD, S0, S3)["part_cellules_changees"]
        top4 = np.sort(ORD[..., :K], -1)
        ens_ok = bool((np.sort(S0, -1) == top4).all())
        d_top4 = rejouer_cache2(ORD[..., :K].astype(np.int16), n, E)
        r[f"W2/{nom}"] = (ens_ok and d_top4 == d0, f"beta=0 : ensembles = top-4 non biaisé ({ens_ok}), défauts {d0} = rejeu indépendant {d_top4}")
        r[f"W2-cassure/{nom}"] = (chg3 > 0.0, f"{chg3:.4f}")
        # W3 : signe ; cassure : masque inversé avec beta positif doit monter les défauts.
        Sn, Mn, dn = simuler(Z, ORD, n, -0.3)
        r[f"W3/{nom}"] = (dn > d0, f"défauts(-0,3)={dn} > défauts(0)={d0}")
        Si, Mi, di = simuler(Z, ORD, n, 0.3, masque="absents")
        r[f"W3-cassure/{nom}"] = (di > d0, f"masque inversé, beta=+0,3 : {di} > {d0}")
        Sh_, Mh_, dh = simuler(Z, ORD, n, 0.3, masque="hasard")
        r[f"W3-hasard/{nom}"] = (dh > d3, f"masque au hasard, beta=+0,3 : {dh} > masque des résidents {d3} (le gain vient de la résidence)")
        r[f"gain-bruit/{nom}"] = (d3 < d0, f"beta=+0,3 : {d3} < {d0} (sens attendu du levier)")
        # W5 : second chemin ; cassure : permuter dans un groupe de cellules doit changer le compte.
        d_cache2 = rejouer_cache2(S3, n, E)
        r[f"W5/{nom}"] = (d_cache2 == d3, f"cache2.lru1={d_cache2} contre simuler={d3}")
        rng = np.random.default_rng(1)
        S3b = S3.copy()
        idx = rng.permutation(T * L)[:1000]
        for i in idx:
            t, l = divmod(int(i), L)
            S3b[t, l] = rng.permutation(E)[:K]
        d_cass = rejouer_cache2(S3b, n, E)
        r[f"W5-cassure/{nom}"] = (d_cass != d3, f"ensembles abîmés : {d_cass} != {d3}")
        log(f"  budget {nom} % (N={n}) : défauts beta=0 {d0}, +0,3 {d3}, -0,3 {dn}, masque inversé +0,3 {di}")
    # W6 : causalité, sur le budget 19.
    n = round(BUDGETS["19"] * L * E)
    moitie = T // 2
    Sf, _, _ = simuler(Z, ORD, n, 0.3)
    Sh, _, _ = simuler(Z[:moitie], ORD[:moitie], n, 0.3)
    r["W6"] = (bool((Sf[:moitie] == Sh).all()), "ensembles des premières positions égaux sur la trace entière et tronquée")
    Sa, _, _ = simuler(Z, ORD, n, 0.3, avenir=True)
    Sah, _, _ = simuler(Z[:moitie], ORD[:moitie], n, 0.3, avenir=True)
    r["W6-cassure-avenir"] = (not bool((Sa[:moitie] == Sah).all()), "un biais qui lit le futur doit être détecté par la troncature")
    return r


def synthetique(T=1000, L=6, E=32, graine=7):
    rng = np.random.default_rng(graine)
    pop = rng.normal(0, 1.2, size=(L, E))
    a = np.zeros((T, L, E))
    for t in range(1, T):
        a[t] = 0.85 * a[t - 1] + rng.normal(0, 0.8, size=(L, E))
    return pop[None] + a + rng.normal(0, 0.05, size=(T, L, E))


def cmd_synthetique():
    journal = []
    log = lambda s: (journal.append(s), print(s, flush=True))
    Z = synthetique()
    ORD = preparer(Z)
    log(f"# synthétique T={Z.shape[0]} L={Z.shape[1]} E={Z.shape[2]} (aucune donnée du projet lue)")
    t0 = time.time()
    res = temoins_machine(Z, ORD, BUDGETS, log)
    tout = True
    for k, (ok, d) in res.items():
        log(f"{'TIENT' if ok else 'TOMBE'}  {k} : {d}")
        tout &= ok
    log(f"# {'tous les témoins de la machine tiennent' if tout else 'AU MOINS UN TÉMOIN TOMBE'} ({time.time() - t0:.0f} s)")
    open(os.path.join(SORTIE, "temoins-synthetiques.log"), "w", encoding="utf-8").write("\n".join(journal) + "\n")
    return 0 if tout else 1


# ----------------------------------------------------------------------------------------------- données réelles


def attendre_verrou(log):
    t0 = time.time()
    while os.path.exists(VERROU):
        age = time.time() - os.path.getmtime(VERROU)
        if age > 2 * 3600:
            log(f"verrou vieux de {age / 60:.0f} min (> 2 h) : règle du dépôt, on passe")
            return
        if int(time.time() - t0) % 600 < 60:
            log(f"{time.strftime('%H:%M:%S')} verrou tenu ({open(VERROU, encoding='utf-8', errors='replace').read().strip()[:120]}) ; attente")
        time.sleep(60)


def logits_reels(log, tmax=None):
    """(Z (T, L, 32) f64, routage (T, L, 4) experts, poids (T, L, 4), B (L, 32) biais du routeur)."""
    sys.path.insert(0, os.path.join(RACINE, "outils", "genome", "duplication"))
    import experts as X
    ex = X.Experts()
    L, E, d = ex.couches, ex.nb_experts, 2880
    T = os.path.getsize(os.path.join(CAPTURE, "h-L00.f32")) // (4 * d)
    if tmax:
        T = min(T, tmax)
    Z = np.zeros((T, L, E))
    B = np.zeros((L, E))
    R = np.zeros((T, L, 4), dtype=np.int64)
    P = np.zeros((T, L, 4))
    for l in range(L):
        W = np.frombuffer(ex.lecteur.octets(ex.par_nom[f"blk.{l}.ffn_gate_inp.weight"]).tobytes(), dtype=np.float32).reshape(E, d)
        b = np.frombuffer(ex.lecteur.octets(ex.par_nom[f"blk.{l}.ffn_gate_inp.bias"]).tobytes(), dtype=np.float32)
        h = np.fromfile(os.path.join(CAPTURE, f"h-L{l:02d}.f32"), dtype=np.float32, count=T * d).reshape(T, d)
        Z[:, l, :] = h.astype(np.float64) @ W.astype(np.float64).T + b.astype(np.float64)
        B[l] = b
        r = np.fromfile(os.path.join(CAPTURE, f"routage-L{l:02d}.bin"), dtype=np.uint8, count=T * 20).reshape(-1, 20)
        R[:, l, :] = r[:, :4]
        P[:, l, :] = np.frombuffer(r[:, 4:].tobytes(), dtype="<f4").reshape(-1, 4)
        log(f"  couche {l:2d} lue")
    return Z, R, P, B


def w1(Z, R, P, B, log):
    T, L, E = Z.shape
    ORD = preparer(Z)
    S = ORD[..., :K]
    accord = (np.sort(S, -1) == np.sort(R, -1)).all(-1)
    taux = float(accord.mean())
    marge = np.sort(-Z, -1)  # croissant de -z
    m = -(marge[..., K - 1]) + marge[..., K]  # z4 - z5
    pire = float(m[~accord].max()) if (~accord).any() else 0.0
    ok_marge = bool(((~accord) <= (np.abs(m) < 1e-4)).all())
    # poids : softmax des logits non biaisés des quatre experts du fichier, dans l'ordre du fichier
    zc = np.take_along_axis(Z, R, axis=-1)
    e = np.exp(zc - zc.max(-1, keepdims=True))
    w = e / e.sum(-1, keepdims=True)
    ecart_w = float(np.abs(w - P)[accord].max())
    # cassure : sans le biais du routeur
    Z2 = Z - B[None]
    S2 = preparer(Z2)[..., :K]
    accord2 = float((np.sort(S2, -1) == np.sort(R, -1)).all(-1).mean())
    res = {"accord": taux, "desaccords": int((~accord).sum()), "marge_max_des_desaccords": pire,
           "desaccords_tous_a_marge_<1e-4": ok_marge, "ecart_poids_max": ecart_w, "accord_sans_biais_routeur": accord2}
    tient = taux >= 0.999 and ok_marge and ecart_w <= 1e-4
    cass = accord2 < 0.99
    log(f"W1 {'TIENT' if tient else 'TOMBE'} : accord {taux:.6f}, {res['desaccords']} désaccords (marge max {pire:.3g}), écart de poids {ecart_w:.3g}")
    log(f"W1-cassure {'TIENT' if cass else 'TOMBE'} : sans le biais du routeur l'accord est {accord2:.4f}")
    return tient and cass, res, ORD


def cmd_reel(attendre=True):
    os.makedirs(SORTIE, exist_ok=True)
    os.makedirs(LOURDS, exist_ok=True)
    journal = []
    log = lambda s: (journal.append(s), print(s, flush=True))
    log(f"# P3 étage A, réel, {time.strftime('%Y-%m-%d %H:%M:%S')}")
    if attendre:
        attendre_verrou(log)
    t0 = time.time()
    Z, R, P, B = logits_reels(log)
    T, L, E = Z.shape
    log(f"# logits lus : T={T} L={L} E={E} en {time.time() - t0:.0f} s")
    ok1, res1, ORD = w1(Z, R, P, B, log)
    delta = Z.max(-1) - Z.min(-1)
    delta_avg = delta.mean(0)
    sortie = {"w1": res1, "delta_avg_par_couche": [float(x) for x in delta_avg], "delta_avg_moyen": float(delta_avg.mean())}
    marge = np.take_along_axis(Z, ORD[..., K - 1:K], -1)[..., 0] - np.take_along_axis(Z, ORD[..., K:K + 1], -1)[..., 0]
    sortie["marge_quantiles"] = {str(q): float(np.quantile(marge, q)) for q in (0.05, 0.1, 0.25, 0.5, 0.75)}
    np.save(os.path.join(LOURDS, "logits-20b-eval.npy"), Z)
    lignes, jeux = [], {}
    for nom, frac in BUDGETS.items():
        n = round(frac * L * E)
        S0, M0, d0 = simuler(Z, ORD, n, 0.0)
        acces = T * L * K
        # borne statique rang 4 (recomptée sous LRU, 5e supposé résident) : défauts du 4e avec marge < tau
        bornes = {str(tau): int((M0[..., K - 1] & (marge < tau)).sum()) for tau in BETAS[1:5]}
        sortie.setdefault("defauts_beta0", {})[nom] = {"N": n, "defauts": d0, "acces": acces, "taux_succes": 1 - d0 / acces,
                                                       "defauts_par_rang": [int(M0[..., r].sum()) for r in range(K)],
                                                       "bornes_rang4_marge<tau": bornes}
        # W2 réel : défauts du rejeu des ensembles du fichier routage-L
        Sref = np.array(R, dtype=np.int16)
        o = np.argsort(-np.take_along_axis(Z, R, -1), -1, kind="stable")
        Sref = np.take_along_axis(Sref, o, -1)
        cache = CacheLRU(n, L * E)
        for t in range(T):
            for l in range(L):
                cache.groupe([l * E + int(e) for e in Sref[t, l]])
        w2 = (cache.defauts == d0)
        log(f"W2 {'TIENT' if w2 else 'TOMBE'} budget {nom} : β=0 {d0} défauts, rejeu des ensembles du fichier {cache.defauts}")
        sortie.setdefault("w2", {})[nom] = {"beta0": d0, "rejeu_fichier": cache.defauts, "tient": w2}
        for variante in ("V1", "V2"):
            for beta in BETAS[1:] + BETAS_NEG:
                if variante == "V2" and beta > 1.0:
                    continue
                S, M, d = simuler(Z, ORD, n, beta, variante)
                st = statistiques(Z, ORD, S0, S)
                ligne = {"variante": variante, "budget": nom, "N": n, "beta": beta, "lambda_equiv": beta / float(delta_avg.mean()),
                         "defauts": d, "variation_relative": d / d0 - 1.0, **st,
                         "kl_prior": KL_PAR_CELLULE * st["part_cellules_changees"]}
                if variante == "V1" and beta > 0:
                    ligne["sha256_journal"] = ecrire_journal(S, marge, os.path.join(LOURDS, f"routage-impose-V1-b{beta}-N{nom}.bin"))
                if variante == "V1":
                    jeux[(nom, beta)] = (S, d)
                lignes.append(ligne)
                log(f"  {variante} N={n} β={beta:+.2f} : défauts {d} ({ligne['variation_relative'] * 100:+.1f} %), cellules changées {st['part_cellules_changees'] * 100:.2f} %, KL a priori {ligne['kl_prior']:.4f}")
    # W3 réel
    for nom in BUDGETS:
        d0 = sortie["defauts_beta0"][nom]["defauts"]
        dn = [l_["defauts"] for l_ in lignes if l_["variante"] == "V1" and l_["budget"] == nom and l_["beta"] == -0.3][0]
        log(f"W3 {'TIENT' if dn > d0 else 'TOMBE'} budget {nom} : β=-0,3 {dn} > β=0 {d0}")
        sortie.setdefault("w3", {})[nom] = dn > d0
    # W4 réel : V2 contre la borne statique
    for nom in BUDGETS:
        b = sortie["defauts_beta0"][nom]["bornes_rang4_marge<tau"]
        d0 = sortie["defauts_beta0"][nom]["defauts"]
        for tau in BETAS[1:5]:
            v2 = [l_ for l_ in lignes if l_["variante"] == "V2" and l_["budget"] == nom and l_["beta"] == tau][0]
            evites = d0 - v2["defauts"]
            rapport = evites / max(b[str(tau)], 1)
            log(f"W4 budget {nom} τ={tau} : V2 évite {evites} défauts, borne statique {b[str(tau)]}, rapport {rapport:.2f} (tolérance 1,5) {'TIENT' if rapport <= 1.5 else 'TOMBE'}")
            sortie.setdefault("w4", {}).setdefault(nom, {})[str(tau)] = {"evites": evites, "borne_statique": b[str(tau)], "rapport": rapport}
    # W5 réel : second chemin sur chaque ligne V1 positive
    w5 = True
    for (nom, beta), (S, d) in jeux.items():
        n = round(BUDGETS[nom] * L * E)
        d2 = rejouer_cache2(S, n)
        ok = d2 == d
        w5 &= ok
        if not ok:
            log(f"W5 TOMBE budget {nom} β={beta} : cache2={d2} contre {d}")
    log(f"W5 {'TIENT' if w5 else 'TOMBE'} : {len(jeux)} lignes V1 rejouées par cache2.lru1")
    sortie["w5"] = w5
    sortie["lignes"] = lignes
    json.dump(sortie, open(os.path.join(SORTIE, "etage-A.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    with open(os.path.join(SORTIE, "etage-A.csv"), "w", newline="", encoding="utf-8") as f:
        champs = ["variante", "budget", "N", "beta", "lambda_equiv", "defauts", "variation_relative", "part_cellules_changees",
                  "experts_changes_par_cellule_changee", "part_plus_haut_logit_garde", "kl_prior"]
        w = csv.DictWriter(f, fieldnames=champs, extrasaction="ignore")
        w.writeheader()
        w.writerows(lignes)
    open(os.path.join(SORTIE, "etage-A.log"), "w", encoding="utf-8").write("\n".join(journal) + "\n")
    log(f"# fin, {time.time() - t0:.0f} s ; W6 est passé par la commande `causalite`")
    return 0


def cmd_essai(tmax=64):
    """Essai léger du chemin réel (64 positions, 24 couches, ~20 Mo lus) : W1 seulement, pour ne pas découvrir un bogue après 1,4 Go de lecture."""
    journal = []
    log = lambda s: (journal.append(s), print(s, flush=True))
    Z, R, P, B = logits_reels(log, tmax)
    ok, res, ORD = w1(Z, R, P, B, log)
    print(json.dumps(res, indent=1))
    return 0 if ok else 1


def cmd_causalite():
    """W6 sur les données réelles (relance ; lourd : à lancer après etage-A, les logits sont dans LOURDS)."""
    Z = np.load(os.path.join(LOURDS, "logits-20b-eval.npy"))
    ORD = preparer(Z)
    T, L, E = Z.shape
    n = round(BUDGETS["19"] * L * E)
    Sf, _, _ = simuler(Z, ORD, n, 0.3)
    Sh, _, _ = simuler(Z[:T // 2], ORD[:T // 2], n, 0.3)
    ok = bool((Sf[:T // 2] == Sh).all())
    Sa, _, _ = simuler(Z, ORD, n, 0.3, avenir=True)
    Sah, _, _ = simuler(Z[:T // 2], ORD[:T // 2], n, 0.3, avenir=True)
    cass = not bool((Sa[:T // 2] == Sah).all())
    msg = f"W6 {'TIENT' if ok else 'TOMBE'} ; W6-cassure {'TIENT' if cass else 'TOMBE'}"
    print(msg)
    open(os.path.join(SORTIE, "w6-reel.log"), "w", encoding="utf-8").write(msg + "\n")
    return 0 if ok and cass else 1


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    if c == "synthetique":
        sys.exit(cmd_synthetique())
    if c == "reel":
        sys.exit(cmd_reel(attendre="--sans-attendre" not in sys.argv))
    if c == "essai":
        sys.exit(cmd_essai())
    if c == "causalite":
        sys.exit(cmd_causalite())
    print(__doc__)
    sys.exit(2)
