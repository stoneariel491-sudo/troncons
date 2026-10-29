"""Erreur quadratique de quantificateurs à 1, 2 et 3 bits par poids sur une source
gaussienne i.i.d. N(0, 1), refaite de zéro, pour vérifier par un chemin indépendant les
chiffres publiés (QTIP, arXiv 2406.11235, tableau 1) dont dépend l'étude 02.

Pourquoi une gaussienne : après une rotation incohérente (Hadamard aléatoire, QuIP#,
QTIP, EXL3, QuaRot), les poids d'une ligne sont presque gaussiens i.i.d. ; la MSE sur
N(0, 1) est donc la grandeur que ces méthodes optimisent, et la borne de Shannon
D(R) = 2^(-2R) en donne le plancher.

Quantificateurs, tous écrits ici d'après leur définition mathématique :
  lloyd      scalaire optimal (Lloyd-Max), calculé analytiquement par l'algorithme de
             Lloyd sur la densité exacte, puis mesuré par Monte-Carlo (le témoin).
  vq8        quantification vectorielle en dimension 8, livre de codes gaussien
             aléatoire de 2^(8R) mots, recherche exhaustive du plus proche voisin.
  kt8        idem, mais le livre de codes est calculé à partir d'une graine de 8R bits
             par un générateur congruentiel (l'idée des types IQn_KT d'ik_llama.cpp :
             multiplication par 0xCBAC1FED, somme des 4 octets masqués à 6 bits, -126).
  treillis   quantification en treillis à décalage (« bitshift trellis » de QTIP) :
             état de L bits, chaque pas fait entrer k = R bits, la valeur reconstruite
             est f(état). Viterbi exact sur des suites de T poids. f est soit une table
             gaussienne aléatoire (« rptc »), soit un code calculé : « 3inst » (QTIP) ou
             « mul1 » (EXL3), définis plus bas par leur formule.

Seuil du témoin, déclaré avant le lancement : |MSE Monte-Carlo - MSE analytique| doit
rester sous 4 erreurs-types de Monte-Carlo (erreur-type = écart-type des erreurs
quadratiques / racine du nombre d'échantillons). L'option --casser-temoin décale tous
les niveaux du quantificateur mesuré de 0,1 pour vérifier que le témoin tombe. Le biais
n'est pas +0,01 comme un calcul naïf le dirait : le plus proche voisin réaffecte les
échantillons ; mesuré +0,0037 à 1 bit et +0,0013 à 2 bits (le témoin tombe), +0,0003 à
3 bits (sous le seuil : à 3 bits l'instrument ne voit pas un tel décalage).
Premier essai de cassure, un seul niveau décalé de 0,05 : trop faible (+0,0008 à
1 bit, sous les 4 erreurs-types), le témoin ne tombait pas ; journal gardé.

Usage : python quant-mse-gaussien.py [--graine 1] [--casser-temoin] > journal.json
"""
import argparse
import json
import math
import sys
import time

import numpy as np


def phi(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi) if math.isfinite(x) else 0.0


def Phi(x):
    if x == math.inf:
        return 1.0
    if x == -math.inf:
        return 0.0
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def lloyd_max_analytique(niveaux, iterations=2000):
    """Algorithme de Lloyd sur la densité N(0,1) exacte (intégrales fermées)."""
    c = np.linspace(-1.5, 1.5, niveaux)
    for _ in range(iterations):
        seuils = [-math.inf] + [(c[i] + c[i + 1]) / 2 for i in range(niveaux - 1)] + [math.inf]
        nouveaux = []
        for i in range(niveaux):
            a, b = seuils[i], seuils[i + 1]
            p = Phi(b) - Phi(a)
            nouveaux.append((phi(a) - phi(b)) / p)
        c = np.array(nouveaux)
    seuils = [-math.inf] + [(c[i] + c[i + 1]) / 2 for i in range(niveaux - 1)] + [math.inf]
    # D = E[x^2] - sum p_i c_i^2 quand chaque c_i est le centroïde de sa cellule
    d = 1.0 - sum((Phi(seuils[i + 1]) - Phi(seuils[i])) * c[i] ** 2 for i in range(niveaux))
    return c, d


def mse_scalaire_mc(x, niveaux_c):
    idx = np.abs(x[:, None] - niveaux_c[None, :]).argmin(axis=1)
    e2 = (x - niveaux_c[idx]) ** 2
    return float(e2.mean()), float(e2.std() / math.sqrt(len(e2)))


def plus_proche(xv, cb, morceau=2048):
    """MSE par poids du plus proche voisin de chaque vecteur de xv dans cb."""
    n2 = (cb * cb).sum(axis=1)
    tot = np.empty(len(xv))
    for i in range(0, len(xv), morceau):
        b = xv[i:i + morceau]
        d = n2[None, :] - 2.0 * b @ cb.T
        j = d.argmin(axis=1)
        tot[i:i + morceau] = ((b - cb[j]) ** 2).sum(axis=1)
    e = tot / xv.shape[1]
    return float(e.mean()), float(e.std() / math.sqrt(len(e)))


def livre_kt8(bits_graine):
    """Livre de codes calculé façon IQn_KT : graine + décalage 4096, puis 8 pas de
    x <- 0xCBAC1FED * x mod 2^32 ; valeur = somme des 4 octets de (x & 0x3f3f3f3f) - 126."""
    n = 1 << bits_graine
    x = (np.arange(n, dtype=np.uint64) + 4096) & 0xFFFFFFFF
    sortie = np.empty((n, 8))
    for k in range(8):
        x = (x * 0xCBAC1FED) & 0xFFFFFFFF
        s = x & 0x3F3F3F3F
        somme = (s & 0xFF) + ((s >> 8) & 0xFF) + ((s >> 16) & 0xFF) + ((s >> 24) & 0xFF)
        sortie[:, k] = somme.astype(np.float64) - 126.0
    return sortie


def f16_depuis_bits(u16):
    return u16.astype(np.uint16).view(np.float16).astype(np.float64)


def code_3inst(etats):
    """QTIP « 3INST » : x <- 89226354 * s + 64248484 mod 2^32, puis (x & 0x8fff8fff) ^
    0x3b603b60, lu comme deux demi-flottants dont on fait la somme."""
    x = (etats.astype(np.uint64) * 89226354 + 64248484) & 0xFFFFFFFF
    x = (x & 0x8FFF8FFF) ^ 0x3B603B60
    return f16_depuis_bits(x & 0xFFFF) + f16_depuis_bits(x >> 16)


def code_mul1(etats):
    """EXL3 « mul1 » : x <- s * 0x83DCD12D mod 2^32, somme des 4 octets, centrée sur 510."""
    x = (etats.astype(np.uint64) * 0x83DCD12D) & 0xFFFFFFFF
    somme = (x & 0xFF) + ((x >> 8) & 0xFF) + ((x >> 16) & 0xFF) + ((x >> 24) & 0xFF)
    return somme.astype(np.float64) - 510.0


def viterbi_treillis(suite, table, L, k):
    """Coût minimal (somme des erreurs quadratiques) d'une suite sur le treillis à
    décalage : état suivant = ((état << k) | b) mod 2^L ; valeur émise = table[état].
    État initial libre. Les prédécesseurs de s' sont (s' >> k) | (h << (L - k))."""
    n_etats = 1 << L
    cout = (suite[0] - table) ** 2
    for t in range(1, len(suite)):
        # min sur les 2^k bits sortants h, pour chaque valeur de (s' >> k)
        m = cout.reshape(1 << k, n_etats >> k).min(axis=0)
        cout = np.repeat(m, 1 << k) + (suite[t] - table) ** 2
    return float(cout.min())


def mse_treillis(x, table, L, k, T):
    suites = x[: (len(x) // T) * T].reshape(-1, T)
    e = np.array([viterbi_treillis(s, table, L, k) / T for s in suites])
    return float(e.mean()), float(e.std() / math.sqrt(len(e))), len(suites)


def meilleur_gain(fonction_mse, gains):
    res = [(fonction_mse(g)[0], g) for g in gains]
    return min(res)[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graine", type=int, default=1)
    ap.add_argument("--casser-temoin", action="store_true")
    ap.add_argument("--n-scalaire", type=int, default=1 << 20)
    ap.add_argument("--n-vq", type=int, default=1 << 14)
    ap.add_argument("--suites", type=int, default=24)
    ap.add_argument("--T", type=int, default=4096)
    ap.add_argument("--L", type=int, default=16)
    ap.add_argument("--R-treillis", default="1,2,3", help="débits du treillis, ex. 2")
    ap.add_argument("--codes", default="rptc,3inst,mul1")
    ap.add_argument("--sauter-vq", action="store_true", help="ne refait pas la VQ (déjà journalisée)")
    a = ap.parse_args()
    rng = np.random.default_rng(a.graine)
    journal = {"source": "N(0,1) i.i.d.", "graine": a.graine, "resultats": []}

    def note(**kw):
        journal["resultats"].append(kw)
        print(json.dumps(kw, ensure_ascii=False), file=sys.stderr)

    # 1. Témoin : Lloyd-Max analytique contre Monte-Carlo, à 1, 2 et 3 bits.
    x = rng.standard_normal(a.n_scalaire)
    temoin_ok = True
    for R in (1, 2, 3):
        c, d = lloyd_max_analytique(2 ** R)
        mesure = c.copy()
        if a.casser_temoin:
            mesure += 0.1
        m, se = mse_scalaire_mc(x, mesure)
        ok = bool(abs(m - d) < 4 * se)
        temoin_ok = temoin_ok and ok
        note(methode="lloyd", R=R, bits_par_poids=R, mse_analytique=round(d, 6),
             mse_monte_carlo=round(m, 6), erreur_type=round(se, 7), temoin_dans_4_et=ok,
             niveaux=[round(v, 5) for v in c])
    journal["temoin_lloyd_max"] = "tient" if temoin_ok else "TOMBE"
    if a.casser_temoin:
        print(json.dumps(journal, ensure_ascii=False, indent=1))
        return

    # 2. VQ en dimension 8, livre gaussien aléatoire et livre calculé KT, à R = 1 et 2.
    for R in (() if a.sauter_vq else (1, 2)):
        nb = 1 << (8 * R)
        xv = rng.standard_normal((a.n_vq, 8))
        cb = rng.standard_normal((nb, 8))
        g = meilleur_gain(lambda g: plus_proche(xv[:2048], cb * g), np.linspace(0.5, 1.1, 13))
        m, se = plus_proche(xv, cb * g)
        note(methode="vq8-gaussien-aleatoire", R=R, bits_par_poids=R, gain=round(g, 3),
             mse_monte_carlo=round(m, 6), erreur_type=round(se, 7))
        kt = livre_kt8(8 * R)
        kt = kt / kt.std()
        g = meilleur_gain(lambda g: plus_proche(xv[:2048], kt * g), np.linspace(0.5, 1.1, 13))
        m, se = plus_proche(xv, kt * g)
        note(methode="vq8-kt-calcule", R=R, bits_par_poids=R, gain=round(g, 3),
             mse_monte_carlo=round(m, 6), erreur_type=round(se, 7))

    # 3. Treillis à décalage, L = 16 bits d'état, k = R bits par poids.
    L = a.L
    etats = np.arange(1 << L, dtype=np.uint32)
    codes = {
        "rptc": rng.standard_normal(1 << L),
        "3inst": code_3inst(etats),
        "mul1": code_mul1(etats),
    }
    xs = rng.standard_normal(a.suites * a.T)
    for R in [int(r) for r in a.R_treillis.split(",")]:
        for nom in a.codes.split(","):
            table = codes[nom]
            t = (table - table.mean()) / table.std()
            t0 = time.time()
            court = xs[: 2 * 1024]
            g = meilleur_gain(lambda g: mse_treillis(court, t * g, L, R, 1024),
                              np.linspace(0.75, 1.05, 7))
            m, se, ns = mse_treillis(xs, t * g, L, R, a.T)
            # bits réels : R par poids, plus (L - R) bits d'amorce par suite (état initial)
            bits = R + (L - R) / a.T
            note(methode=f"treillis-{nom}", R=R, L=L, T=a.T, suites=ns,
                 bits_par_poids=round(bits, 4), gain=round(float(g), 3),
                 mse_monte_carlo=round(m, 6), erreur_type=round(se, 7),
                 secondes=round(time.time() - t0, 1))

    for R in (1, 2, 3):
        note(methode="borne-shannon", R=R, bits_par_poids=R, mse_analytique=round(2 ** (-2 * R), 6))
    print(json.dumps(journal, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
