"""Codage prédictif sans perte des codes MXFP4 : ce que chaque prédicteur retire de l'entropie.

Question. Le cerveau ne transmet que l'écart entre ce qu'il attendait et ce qui arrive. Pour un
alphabet discret de 16 codes, « prédire puis coder l'écart » s'écrit exactement : coder le code
avec une loi conditionnée par ce que le décodeur sait déjà (son contexte). Le gain est
l'information mutuelle I(code ; contexte) = H(code | κ) − H(code | κ, contexte), où κ est la
classe d'échelle du bloc (sous, égale, au-dessus de la médiane de la ligne) que le format de
troncons connaît déjà avant les codes (ARCHITECTURE § 3, A_ctx).

Prédicteurs mesurés, chacun disponible au décodeur au moment du code :
  - gauche : le code signé de la colonne précédente, même ligne ;
  - dessus : le code signé de la même colonne, ligne précédente ;
  - parent : le code signé à la même place dans l'expert précédent de la couche (e − 1) ;
  - colonne : la classe d'énergie de la colonne d'entrée (quartile, carte de 2 bits par colonne
    envoyée une fois par tenseur, 720 octets) ;
  - δ exact borné à ±2 (cinq classes au lieu de trois) ;
  - gauche × dessus ;
  - contrainte du maximum de bloc : un « grand » code (magnitude ≥ 4, soit 2 et plus en E2M1)
    a-t-il déjà paru dans le bloc, et est-ce la dernière place (l'échelle OCP place le maximum du
    bloc dans [4, 8) : au moins un grand code par bloc si le quantificateur suit la règle).
Référence du codec réel : l'octet entier (deux demi-octets du même bloc) sachant κ, ce que code
A_ctx (3,8056 bits par poids réels, en-têtes compris, ARCHITECTURE § 3.3).

Seuil déclaré avant la mesure : un prédicteur n'est retenu que s'il retire au moins
**0,015 bit par poids** à H(code | κ) : c'est le coût d'en-tête d'un flux de plus, 0,40 % de
3,84 bits (mesuré 03 § 3.1). Sous ce seuil, le gain ne paie pas l'ingénierie.

Témoins (connus d'avance) :
  - contexte = le code lui-même : H(code | contexte) doit valoir 0 (à 1e-12) ;
  - contexte = étiquettes de gauche permutées au hasard : le gain doit retomber sous le biais
    de l'estimateur, (K − 1)(16 − 1) / (2 N ln 2) ;
  - cassure (--casser) : le premier témoin reçoit le code privé de son bit bas, H ne vaut plus 0
    et le témoin doit tomber.

Utilisation : python -I -X utf8 contextes.py [--casser] [--fichier F] > journal.json
Mémoire : un tenseur à la fois (265 Mo de codes) ; ≈ 1,5 Go de pointe.
"""
from __future__ import annotations

import json
import math
import sys
import time

import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import mxfp4 as mx  # noqa: E402

SEUIL_BITS = 0.015
GRAND = 4  # indice de magnitude m >= 4 : |K| >= 4, soit E2M1 >= 2


def main():
    casser = "--casser" in sys.argv
    fichier = mx.FICHIER_20B
    if "--fichier" in sys.argv:
        fichier = sys.argv[sys.argv.index("--fichier") + 1]
    lec = mx.lecteur(fichier)
    rng = np.random.default_rng(20261016)
    familles = {}  # nom -> [bits, n, nb_contextes]

    def ajouter(nom, ctx, sym, K, S=16):
        c = np.bincount(ctx.astype(np.int64).ravel() * S + sym.astype(np.int64).ravel(),
                        minlength=K * S).reshape(K, S)
        b, n = mx.entropie_conditionnelle(c)
        f = familles.setdefault(nom, [0.0, 0.0, K * S, 0])
        f[0] += b
        f[1] += n
        f[3] += 1  # une table par tenseur

    par_tenseur = []
    t0 = time.time()
    tenseurs = mx.tenseurs_etude(lec)
    for t in tenseurs:
        E, R, C = mx.forme(t)
        # Passe 1 : énergie relative par colonne d'entrée (v = K[c] · 2^δ), sur tous les experts.
        energie_col = np.zeros(C)
        for e in range(E):
            codes, ech = mx.expert(lec, t, e)
            med = mx.mediane_ligne(ech)
            d = np.repeat(ech.astype(np.float64) - med[:, None], 32, axis=1)
            energie_col += ((mx.VAL[codes] * np.exp2(d)) ** 2).sum(axis=0)
        quart = np.quantile(energie_col, [0.25, 0.5, 0.75])
        classe_col = np.searchsorted(quart, energie_col).astype(np.uint8)  # 0..3
        rapport_col = float(np.sqrt(energie_col.max() / np.median(energie_col)))
        precedent = None
        grands_sans = 0
        blocs = 0
        for e in range(E):
            codes, ech = mx.expert(lec, t, e)
            med = mx.mediane_ligne(ech)
            k = mx.kappa(ech, med)                       # (R, 90)
            kc = np.repeat(k, 32, axis=1)                # (R, C)
            dl = np.clip(ech.astype(np.int16) - med[:, None].astype(np.int16), -2, 2) + 2
            dc = np.repeat(dl, 32, axis=1)
            ajouter("rien", np.zeros_like(codes), codes, 1)
            ajouter("kappa", kc, codes, 3)
            ajouter("delta_5", dc, codes, 5)
            # Octet du codec : demi-octets (i, i + 16) du même bloc, sachant κ.
            cb = codes.reshape(R, C // 32, 32)
            octet = cb[:, :, :16].astype(np.int64) | (cb[:, :, 16:].astype(np.int64) << 4)
            ajouter("octet_kappa", np.repeat(k, 16, axis=1), octet, 3, 256)
            gauche = np.full_like(codes, 16)
            gauche[:, 1:] = codes[:, :-1]
            ajouter("kappa_gauche", kc * 17 + gauche, codes, 51)
            dessus = np.full_like(codes, 16)
            dessus[1:, :] = codes[:-1, :]
            ajouter("kappa_dessus", kc * 17 + dessus, codes, 51)
            parent = np.full_like(codes, 16) if precedent is None else precedent
            ajouter("kappa_parent", kc * 17 + parent, codes, 51)
            col = np.broadcast_to(classe_col[None, :], codes.shape)
            ajouter("kappa_colonne", kc * 4 + col, codes, 12)
            ajouter("kappa_gauche_dessus",
                    (kc.astype(np.int64) * 17 + gauche) * 17 + dessus, codes, 3 * 17 * 17)
            # Contrainte du maximum de bloc, dans l'ordre des places 0..31 du bloc.
            grand = (cb & 7) >= GRAND
            vu = np.zeros_like(grand)
            vu[:, :, 1:] = np.cumsum(grand, axis=2)[:, :, :-1] > 0
            derniere = np.zeros_like(grand)
            derniere[:, :, 31] = True
            ctx_max = (np.repeat(k, 32, axis=1).reshape(R, C // 32, 32).astype(np.int64) * 2
                       + vu) * 2 + derniere
            ajouter("kappa_max_bloc", ctx_max, cb, 12)
            grands_sans += int((~grand.any(axis=2)).sum())
            blocs += grand.shape[0] * grand.shape[1]
            # Témoins.
            if e == 0:
                ctx_t = (codes >> 1) if casser else codes
                ajouter("temoin_code_lui_meme", ctx_t, codes, 16)
                perm = rng.permutation(gauche.ravel()).reshape(gauche.shape)
                ajouter("temoin_gauche_permute", kc * 17 + perm, codes, 51)
                ajouter("temoin_kappa_meme_lot", kc, codes, 3)
            precedent = codes
        par_tenseur.append({"nom": t.nom, "colonne_rapport_max_sur_mediane_rms": rapport_col,
                            "blocs_sans_grand_code": grands_sans, "blocs": blocs})
        print(f"{t.nom} : {time.time() - t0:.0f} s", file=sys.stderr)

    res = {}
    for nom, (b, n, KS, ntab) in familles.items():
        # Coût des tables : (contextes × symboles) fréquences de 12 bits, une table par tenseur.
        cout_tables = ntab * KS * 12
        res[nom] = {"bits_par_poids": b / n, "bits_par_poids_tables_comprises": (b + cout_tables) / n,
                    "poids": n, "contextes_x_symboles": KS}
    res["octet_kappa"]["bits_par_poids"] = res["octet_kappa"]["bits_par_poids"] / 2
    res["octet_kappa"]["bits_par_poids_tables_comprises"] /= 2
    ref = res["kappa"]["bits_par_poids"]
    gains = {nom: ref - r["bits_par_poids_tables_comprises"] for nom, r in res.items()
             if not nom.startswith("temoin") and nom not in ("rien", "kappa")}
    # Biais de l'estimateur sur la différence H(code | κ) − H(code | κ, gauche permutée) : les tables
    # sont par tenseur ; chaque tenseur ajoute (51 − 3) × 15 paramètres libres estimés sur N_t
    # symboles, d'où (51 − 3) · 15 / (2 N_t ln 2) bit par symbole. (Première version, barrée le
    # 2026-10-16 : (51 − 1) · 15 / (2 N ln 2) avec N poolé sur les 12 tenseurs, douze fois trop
    # petit ; le témoin était tombé à tort : 6,33e-5 mesuré pour 6,26e-5 attendu.)
    n0 = res["temoin_gauche_permute"]["poids"] / len(tenseurs)
    biais = (51 - 3) * 15 / (2 * n0 * math.log(2))
    gain_permute = res["temoin_kappa_meme_lot"]["bits_par_poids"] - res["temoin_gauche_permute"]["bits_par_poids"]
    temoins = {
        "code_lui_meme_H_nulle": bool(res["temoin_code_lui_meme"]["bits_par_poids"] < 1e-12),
        "gauche_permute_sans_gain": bool(gain_permute <= 1.5 * biais),
    }
    sortie = {
        "outil": "genome/predictif-elagage/contextes.py", "fichier": fichier, "casser": casser,
        "seuil_bits_declare": SEUIL_BITS, "resultats": res,
        "gain_sur_kappa_tables_comprises": gains,
        "retenus": [nom for nom, g in gains.items() if g >= SEUIL_BITS],
        "biais_estimateur_51_contextes": biais, "gain_contexte_permute": gain_permute,
        "temoins": temoins, "temoins_tiennent": all(temoins.values()),
        "par_tenseur": par_tenseur, "duree_s": time.time() - t0,
    }
    json.dump(sortie, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
