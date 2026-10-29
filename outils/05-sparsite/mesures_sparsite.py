"""Mesures de sparsité des activations sur la passe avant numpy (étude 05).

Deux sous-commandes.

stats : une passe sans rien modifier ; pour chaque entrée crochetée (attn_in,
  o_in, ffn_in, down_in) et chaque couche, on prend le masque « top-k par
  jeton » (les (1-s)·D composantes de plus grande valeur absolue, s = sparsité)
  et l'on mesure :
  - union(n) : densité de l'union des masques de n jetons consécutifs. C'est
    la fraction des colonnes de W qu'une passe de vérification spéculative de
    n jetons doit lire si chaque jeton garde son propre masque ;
  - la prédiction d'indépendance 1 - (1 - d)^n, pour voir la corrélation ;
  - fenetrage(w) : fraction des composantes du masque du jeton t absentes des
    masques des w jetons précédents (ce qu'un cache des neurones récents, le
    « windowing » de LLM in a flash, doit encore aller chercher) ;
  - neurones chauds : part des canaux qui portent 50/80/90/95 % des
    activations retenues (la loi de puissance de PowerInfer).

ppl : perplexité sous une règle de masquage, sur les mêmes fenêtres que
  llama-perplexity (512 jetons, seconde moitié notée). Règles :
  - aucune ;
  - jeton:s : top-k par jeton (variante de TEAL à densité fixe) ;
  - jetonw:s : idem, score |v_j|·||W[:, j]|| (le poids compte) ;
  - bloc:n:s : un SEUL masque pour chaque bloc de n jetons consécutifs, choisi
    sur l'énergie du bloc  sum_i v_ij^2 ; c'est la règle qui rend la sparsité
    compatible avec la vérification spéculative : la passe de n jetons lit
    exactement (1-s) des colonnes ;
  - blocw:n:s : idem, énergie pondérée par ||W[:, j]||^2.

Usage :
  python -I mesures_sparsite.py stats MODELE test.ids SORTIE.json [--fenetres N]
  python -I mesures_sparsite.py ppl MODELE test.ids SORTIE.json REGLE [REGLE...] [--fenetres N]
  python -I mesures_sparsite.py energie MODELE test.ids SORTIE.json [--fenetres N]
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402

from llama_numpy import ENTREES, Modele, nll_chunk  # noqa: E402

N_CTX, PREMIER = 512, 256
SPARSITES = (0.25, 0.5, 0.7, 0.9)
NS = (1, 2, 4, 8, 16, 32)
WS = (1, 2, 4, 8, 16)
COUVERTURES = (0.5, 0.8, 0.9, 0.95)


def masque_topk(score, densite):
    """score (n, D) -> masque booléen des k = round(densite·D) plus grands par ligne."""
    n, D = score.shape
    k = max(1, int(round(densite * D)))
    idx = np.argpartition(-score, k - 1, axis=1)[:, :k]
    m = np.zeros((n, D), dtype=bool)
    np.put_along_axis(m, idx, True, axis=1)
    return m


def normes_colonnes(modele):
    """||W[:, j]|| des matrices lues derrière chaque entrée, par couche."""
    out = []
    for c in modele.c:
        out.append({
            "attn_in": np.sqrt((c["attn_q"] ** 2).sum(0) + (c["attn_k"] ** 2).sum(0)
                               + (c["attn_v"] ** 2).sum(0)),
            "o_in": np.sqrt((c["attn_output"] ** 2).sum(0)),
            "ffn_in": np.sqrt((c["ffn_gate"] ** 2).sum(0) + (c["ffn_up"] ** 2).sum(0)),
            "down_in": np.sqrt((c["ffn_down"] ** 2).sum(0)),
        })
    return out


def cmd_stats(modele, jetons, sortie, n_fen):
    acc = {}  # (entree, s) -> sommes

    def cle(e, s):
        if (e, s) not in acc:
            acc[(e, s)] = {"union": {n: [0.0, 0] for n in NS},
                           "fen": {w: [0.0, 0] for w in WS},
                           "freq": None, "n_couches_vues": 0}
        return acc[(e, s)]

    freq = {}  # (entree, s, couche) -> compte par canal

    def crochet(i, e, v):
        a = np.abs(v)
        for s in SPARSITES:
            m = masque_topk(a, 1.0 - s)
            st = cle(e, s)
            n_tok = m.shape[0]
            for n in NS:
                nb = n_tok // n
                u = m[:nb * n].reshape(nb, n, -1).any(axis=1).mean(axis=1)
                st["union"][n][0] += float(u.sum())
                st["union"][n][1] += nb
            for w in WS:
                if n_tok <= w:
                    continue
                # cache = union des w masques précédents (fenêtre glissante)
                cache = np.zeros_like(m[w:])
                for d in range(1, w + 1):
                    cache |= m[w - d: n_tok - d]
                neuf = (m[w:] & ~cache).sum(axis=1) / m.shape[1]
                st["fen"][w][0] += float(neuf.sum())
                st["fen"][w][1] += len(neuf)
            f = freq.setdefault((e, s, i), np.zeros(m.shape[1]))
            f += m.sum(axis=0)
        return v

    t0 = time.time()
    for k in range(n_fen):
        fen = jetons[k * N_CTX:(k + 1) * N_CTX]
        modele.avant(fen, crochet=crochet, depuis=N_CTX - 1)
        print(f"fenêtre {k + 1}/{n_fen} : {time.time() - t0:.0f} s", flush=True)

    res = {"fenetres": n_fen, "jetons": n_fen * N_CTX, "entrees": {}}
    for (e, s), st in acc.items():
        d = 1.0 - s
        u = {n: st["union"][n][0] / st["union"][n][1] for n in NS}
        ind = {n: 1.0 - (1.0 - d) ** n for n in NS}
        fw = {w: st["fen"][w][0] / st["fen"][w][1] for w in WS}
        # neurones chauds : moyenne sur les couches de la part des canaux qui
        # portent X % des sélections
        couv = {c: [] for c in COUVERTURES}
        for i in range(modele.n_couches):
            f = np.sort(freq[(e, s, i)])[::-1]
            cum = np.cumsum(f) / f.sum()
            for c in COUVERTURES:
                couv[c].append(float((np.searchsorted(cum, c) + 1) / len(f)))
        res["entrees"].setdefault(e, {})[str(s)] = {
            "densite_par_jeton": d,
            "union": {str(n): u[n] for n in NS},
            "union_si_independant": {str(n): ind[n] for n in NS},
            "neuf_apres_cache_w": {str(w): fw[w] for w in WS},
            "part_canaux_pour_couverture": {str(c): float(np.mean(couv[c])) for c in COUVERTURES},
        }
    res["duree_s"] = time.time() - t0
    Path(sortie).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")


def faire_crochet(regle, normes):
    morceaux = regle.split(":")
    genre = morceaux[0]
    if genre == "aucune":
        return None, 1.0, 1
    if genre in ("jeton", "jetonw"):
        s = float(morceaux[1])
        n = 1
    elif genre in ("bloc", "blocw"):
        n, s = int(morceaux[1]), float(morceaux[2])
    else:
        raise ValueError(regle)
    poids = genre.endswith("w")

    def crochet(i, e, v):
        nrm = normes[i][e] if poids else None
        if n == 1:
            sc = np.abs(v) * nrm if poids else np.abs(v)
            m = masque_topk(sc, 1.0 - s)
        else:
            T, D = v.shape
            m = np.zeros((T, D), dtype=bool)
            for a in range(0, T, n):
                bloc = v[a:a + n]
                en = (bloc ** 2).sum(axis=0)
                if poids:
                    en = en * nrm ** 2
                mb = masque_topk(en[None, :], 1.0 - s)[0]
                m[a:a + n] = mb
        return v * m

    return crochet, 1.0 - s, n


def cmd_ppl(modele, jetons, sortie, regles, n_fen):
    normes = normes_colonnes(modele)
    res = {"fenetres": n_fen, "regles": {}}
    if Path(sortie).exists():
        res = json.loads(Path(sortie).read_text(encoding="utf-8"))
    for r in regles:
        if r in res["regles"]:
            print(f"{r} : déjà mesurée, sautée", flush=True)
            continue
        crochet, dens, n = faire_crochet(r, normes)
        t0 = time.time()
        tot, cnt, par_fen = 0.0, 0, []
        for k in range(n_fen):
            fen = jetons[k * N_CTX:(k + 1) * N_CTX]
            s, c = nll_chunk(modele.avant(fen, crochet=crochet, depuis=PREMIER), fen, PREMIER)
            tot, cnt = tot + s, cnt + c
            par_fen.append(s / c)
        ppl = math.exp(tot / cnt)
        res["regles"][r] = {"ppl": ppl, "nll_par_fenetre": par_fen, "densite": dens,
                            "bloc": n, "duree_s": time.time() - t0}
        print(f"{r} : ppl {ppl:.4f} ({time.time() - t0:.0f} s)", flush=True)
        Path(sortie).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")


def cmd_energie(modele, jetons, sortie, n_fen):
    """Part de l'énergie sum_j v_ij^2 de chaque jeton gardée par un masque de
    densité 0,5 : top-k par jeton, masque commun à un bloc de n (énergie du
    bloc), masque aléatoire (témoin : doit garder ~50 %)."""
    rng = np.random.default_rng(20261015)
    acc = {}

    def ajoute(cle, val):
        a = acc.setdefault(cle, [0.0, 0])
        a[0] += float(val.sum())
        a[1] += val.size

    def crochet(i, e, v):
        e2 = v * v
        tot = e2.sum(axis=1)
        tot = np.where(tot > 0, tot, 1.0)
        m = masque_topk(np.abs(v), 0.5)
        ajoute((e, "jeton"), (e2 * m).sum(axis=1) / tot)
        mr = rng.random(v.shape) < 0.5
        ajoute((e, "aleatoire"), (e2 * mr).sum(axis=1) / tot)
        for n in (2, 4, 16):
            T = v.shape[0] - v.shape[0] % n
            blocs = e2[:T].reshape(T // n, n, -1)
            mb = masque_topk(blocs.sum(axis=1), 0.5)
            garde = (blocs * mb[:, None, :]).sum(axis=2).reshape(-1) / tot[:T]
            ajoute((e, f"bloc{n}"), garde)
        return v

    for k in range(n_fen):
        fen = jetons[k * N_CTX:(k + 1) * N_CTX]
        modele.avant(fen, crochet=crochet, depuis=N_CTX - 1)
        print(f"fenêtre {k + 1}/{n_fen}", flush=True)
    res = {}
    for (e, r), (s_, c) in acc.items():
        res.setdefault(e, {})[r] = s_ / c
    Path(sortie).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=1, ensure_ascii=False))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cmd, mod, ids, sortie = sys.argv[1:5]
    n_fen = 4
    args = sys.argv[5:]
    if "--fenetres" in args:
        j = args.index("--fenetres")
        n_fen = int(args[j + 1])
        args = args[:j] + args[j + 2:]
    modele = Modele(mod)
    jetons = json.loads(Path(ids).read_text())
    if cmd == "stats":
        cmd_stats(modele, jetons, sortie, n_fen)
    elif cmd == "energie":
        cmd_energie(modele, jetons, sortie, n_fen)
    elif cmd == "ppl":
        cmd_ppl(modele, jetons, sortie, args, n_fen)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
