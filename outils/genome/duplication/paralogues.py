"""Les paralogues : un expert absent peut-il être remplacé par un autre expert de sa couche ?

Dans le vivant, deux gènes paralogues (nés d'une duplication) gardent souvent assez de fonction
commune pour que l'un compense la perte de l'autre (robustesse génétique). Transposé à troncons :
sur un défaut de cache, servir l'expert manquant c par un paralogue s déjà résident ne lit AUCUN
octet du disque pour cet usage. La question n'est plus la parenté des poids (mesurée par
mutation.py) mais celle des FONCTIONS, sur les entrées que l'expert reçoit vraiment.

Mesure, couche L, entrées réelles (capture de l'éclaireur : h-Lll.f32, routage-Lll.bin) :
  pour chaque expert c, les jetons routés vers c (au plus --jetons) ; y_e(x) pour les E experts ;
  erreur de substitution de c par s : ε(c, s) = Σ‖y_c − β y_s‖² / Σ‖y_c‖², β moindres carrés
  (β = 1 aussi rapporté) ; le meilleur paralogue s* = argmin_s ε ; le 5ᵉ choix du routeur
  (rechargé depuis les logits du routeur, poids F32 du GGUF) comme substitut naturel ;
  erreur de la SORTIE DE LA COUCHE (somme des 4 experts pondérés) quand c est remplacé par s* contre
  quand c est retiré (ses 3 compagnons renormalisés), à comparer à la base de B (mutation.py, O).
Témoin de l'instrument : ε(c, c) = 0 ; témoin de hasard : y_s remplacé par la sortie de s sur des
jetons pris au hasard (même énergie, aucun lien) : ε ≈ 1 + ‖y_s‖²/‖y_c‖² sans β, ≈ 1 avec β.

Utilisation : python -I -X utf8 paralogues.py --couche 8 --capture DOSSIER [--jetons 256] > j.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import experts as X  # noqa: E402


def sortie(x, Wg, Wu, Wd, bg, bu, bd):
    g = np.minimum(x @ Wg.T + bg, 7.0)
    u = np.clip(x @ Wu.T + bu, -7.0, 7.0)
    a = g / (1.0 + np.exp(-1.702 * g)) * (u + 1.0)
    return a @ Wd.T + bd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--couche", type=int, required=True)
    ap.add_argument("--capture", required=True)
    ap.add_argument("--jetons", type=int, default=256, help="jetons routés par expert, au plus")
    ap.add_argument("--graine", type=int, default=20261016)
    a = ap.parse_args()
    ex = X.Experts()
    L, E, d = a.couche, ex.nb_experts, ex.d_entree_gate
    rng = np.random.default_rng(a.graine)
    t0 = time.time()
    h = np.fromfile(os.path.join(a.capture, f"h-L{L:02d}.f32"), dtype=np.float32).reshape(-1, d)
    r = np.fromfile(os.path.join(a.capture, f"routage-L{L:02d}.bin"), dtype=np.uint8).reshape(-1, 20)
    choix = r[:, :4].astype(np.int64)
    gw = r[:, 4:].copy().view(np.float32).reshape(-1, 4).astype(np.float64)
    # Logits du routeur (F32 du GGUF) pour le 5e choix.
    Wr = np.frombuffer(ex.lecteur.octets(ex.par_nom[f"blk.{L}.ffn_gate_inp.weight"]).tobytes(), dtype=np.float32).reshape(E, d)
    br = np.frombuffer(ex.lecteur.octets(ex.par_nom[f"blk.{L}.ffn_gate_inp.bias"]).tobytes(), dtype=np.float32)
    # Jetons retenus : pour chaque c, au plus --jetons parmi ceux routés vers c ; union.
    par_c = {}
    for c in range(E):
        pos = np.nonzero((choix == c).any(axis=1))[0]
        par_c[c] = np.sort(rng.choice(pos, size=min(a.jetons, len(pos)), replace=False)) if len(pos) else pos
    union = np.unique(np.concatenate([par_c[c] for c in range(E)]))
    idx = {p: i for i, p in enumerate(union)}
    x = h[union].astype(np.float32)
    logits = x.astype(np.float64) @ Wr.T.astype(np.float64) + br
    ordre = np.argsort(-logits, axis=1, kind="stable")
    # Vérification du routage capturé : le top-4 recalculé doit égaler le routage écrit.
    top4_ok = float((np.sort(ordre[:, :4], axis=1) == np.sort(choix[union], axis=1)).all(axis=1).mean())
    # Stockage f16 (précision relative 5·10⁻⁴ par composante, bien sous les erreurs mesurées) : mémoire.
    Y = np.empty((E, len(union), d), dtype=np.float16)
    for e in range(E):
        Wg, Wu, Wd = (ex.poids(L, ro, e) for ro in X.ROLES)
        bg, bu, bd = (ex.biais(L, ro)[e] for ro in X.ROLES)
        Y[e] = sortie(x, Wg, Wu, Wd, bg, bu, bd)
        print(f"[{time.time() - t0:5.0f} s] expert {e}", file=sys.stderr, flush=True)
    res = []
    for c in range(E):
        ii = np.array([idx[p] for p in par_c[c]])
        if len(ii) == 0:
            continue
        yc = Y[c, ii].astype(np.float64)
        Ec = (yc ** 2).sum()
        eps1, epsb = np.empty(E), np.empty(E)
        for s in range(E):
            ys = Y[s, ii].astype(np.float64)
            eps1[s] = ((yc - ys) ** 2).sum() / Ec
            beta = (yc * ys).sum() / max((ys ** 2).sum(), 1e-300)
            epsb[s] = ((yc - beta * ys) ** 2).sum() / Ec
        autres = [s for s in range(E) if s != c]
        s_star = min(autres, key=lambda s: epsb[s])
        # Témoin de hasard : sortie d'un autre expert sur des jetons de hasard.
        jh = rng.choice(len(union), size=len(ii), replace=True)
        yh = Y[s_star, jh].astype(np.float64)
        bh = (yc * yh).sum() / (yh ** 2).sum()
        eps_hasard = ((yc - bh * yh) ** 2).sum() / Ec
        # 5e choix du routeur, jeton par jeton (substitut naturel).
        cinq = ordre[ii, 4]
        y5 = Y[cinq, ii].astype(np.float64)
        eps_5e = ((yc - y5) ** 2).sum() / Ec
        # Sortie de la couche : 4 experts pondérés ; c remplacé par s* ou retiré (renormalisé).
        pos = par_c[c]
        ref = np.zeros((len(ii), d))
        sub = np.zeros((len(ii), d))
        ret = np.zeros((len(ii), d))
        for k, (p, i) in enumerate(zip(pos, ii)):
            w = gw[p]
            reste = 0.0
            for j in range(4):
                e = choix[p, j]
                ref[k] += w[j] * Y[e, i]
                if e == c:
                    sub[k] += w[j] * Y[s_star, i]
                else:
                    sub[k] += w[j] * Y[e, i]
                    reste += w[j]
            for j in range(4):
                e = choix[p, j]
                if e != c:
                    ret[k] += w[j] / reste * Y[e, i]
        Er = (ref ** 2).sum()
        res.append({"expert": c, "jetons": int(len(ii)), "temoin_soi": float(eps1[c]),
                    "meilleur_paralogue": int(s_star), "eps_paralogue_beta": float(epsb[s_star]),
                    "eps_paralogue_beta_1": float(eps1[s_star]), "eps_hasard": float(eps_hasard),
                    "eps_5e_choix": float(eps_5e), "eps_mediane_autres_beta": float(np.median(epsb[autres])),
                    "couche_substitue": float(((sub - ref) ** 2).sum() / Er),
                    "couche_retire": float(((ret - ref) ** 2).sum() / Er)})
        print(f"c {c} : s* {s_star} ε {epsb[s_star]:.3f} (hasard {eps_hasard:.3f}, 5e {eps_5e:.3f}) ; "
              f"couche : substitué {res[-1]['couche_substitue']:.4f}, retiré {res[-1]['couche_retire']:.4f}",
              file=sys.stderr, flush=True)
    agg = {k: float(np.mean([r_[k] for r_ in res])) for k in res[0] if k not in ("expert", "meilleur_paralogue")}
    print(json.dumps({"outil": "paralogues.py", "arguments": vars(a), "routage_recalcule_egal": top4_ok,
                      "jetons_union": int(len(union)), "par_expert": res, "moyennes": agg,
                      "duree_s": time.time() - t0}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
