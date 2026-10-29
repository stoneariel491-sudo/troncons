"""Juge de la piste « spectres » : le chiffre principal refait par un chemin propre.

Seuils : genome/pistes/spectres/juge-seuil.md (commité avant ce fichier).
Données : mesures/pistes/spectres/valeurs-singulieres.npz (lambda = sigma^2).

Chemin écrit de zéro, sans lire csn.py ni second_chemin.py :
- lambda_min par sommes suffixes de ln(lambda), KS bilatérale exacte, queue >= 50 points ;
- log-normale tronquée = gaussienne tronquée en y = ln(lambda / lambda_min), paramètres naturels
  (c1 >= 0, b), densité proportionnelle à exp(-c1 y^2 + b y) sur y >= 0, normalisée par erfcx ;
  la loi de puissance est le bord c1 = 0 de cette famille ;
- exponentielle tronquée en forme close ; Vuong normalisé ;
- p_gof par répliques semi-paramétriques (graine 777).

Usage : python juge_csn.py [--sans-repliques] [--casser] [--repliques 100]
"""
import os
import sys

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import ctypes
import csv
import json
import math
import re
import time
from pathlib import Path

import numpy as np
from scipy import optimize, special

RACINE = Path(__file__).resolve().parents[4]
NPZ = RACINE / "mesures/pistes/spectres/valeurs-singulieres.npz"
PUBLIE = RACINE / "mesures/pistes/spectres/ajustements.out"
SORTIE = RACINE / "mesures/pistes/spectres/juge"
VERROU = Path("~/dev/verrou-carte.txt")
GARDE = 50


def priorite_inactive():
    try:
        k32 = ctypes.windll.kernel32
        k32.SetPriorityClass(k32.GetCurrentProcess(), 0x4000)  # BELOW_NORMAL_PRIORITY_CLASS
    except Exception:
        pass


def pid_vivant(pid):
    try:
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, int(pid))
        if not h:
            return False
        code = ctypes.c_ulong()
        k32.GetExitCodeProcess(h, ctypes.byref(code))
        k32.CloseHandle(h)
        return code.value == 259
    except Exception:
        return True


def seance_de_vitesse():
    try:
        texte = VERROU.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if not re.search(r"ABBA|\bJ1\b|vitesse", texte, re.IGNORECASE):
        return False
    m = re.search(r"pid\s+(\d+)", texte)
    if m:
        return pid_vivant(m.group(1))
    return (time.time() - VERROU.stat().st_mtime) < 3 * 3600


def attendre(journal):
    signale = False
    while seance_de_vitesse():
        if not signale:
            journal(f"[pause] séance de vitesse en cours ({time.strftime('%H:%M:%S')})")
            signale = True
        time.sleep(60)
    if signale:
        journal(f"[reprise] {time.strftime('%H:%M:%S')}")


# ---------------------------------------------------------------- loi de puissance

def balayage(x, bloc=64):
    """x trié croissant, > 0. Rend (k, alpha, D) du lambda_min de KS minimale.

    Tous les candidats k sont évalués par blocs de lignes d'une matrice (k, j), j >= k ; le
    premier minimum (plus petit k) est retenu, comme la boucle simple qu'elle remplace.
    """
    n = x.size
    lx = np.log(x)
    suffixe = np.cumsum(lx[::-1])[::-1]
    kmax = n - GARDE
    ks = np.arange(0, kmax + 1)
    nk = (n - ks).astype(np.float64)
    denom = suffixe[ks] - nk * lx[ks]
    with np.errstate(divide="ignore", invalid="ignore"):
        alpha = np.where(denom > 0, 1.0 + nk / denom, np.nan)
    Dk = np.full(ks.size, np.inf)
    j = np.arange(n)
    for d in range(0, ks.size, bloc):
        kb = ks[d:d + bloc]
        ab = alpha[d:d + bloc]
        jj = j[kb[0]:]
        y = lx[None, jj] - lx[kb, None]                       # ln(x_j / x_k)
        valide = jj[None, :] >= kb[:, None]
        F = -np.expm1((1.0 - ab[:, None]) * np.where(valide, y, 0.0))
        i = (jj[None, :] - kb[:, None]).astype(np.float64)     # rang dans la queue
        nkb = nk[d:d + bloc][:, None]
        haut = np.where(valide, (i + 1.0) / nkb - F, -np.inf)
        bas = np.where(valide, F - i / nkb, -np.inf)
        Db = np.maximum(haut.max(axis=1), bas.max(axis=1))
        Db[~np.isfinite(ab)] = np.inf
        Dk[d:d + bloc] = Db
    k = int(np.argmin(Dk))
    return k, float(alpha[k]), float(Dk[k])


def ks_fixe(t, xmin, a):
    nk = t.size
    F = 1.0 - (t / xmin) ** (1.0 - a)
    i = np.arange(nk)
    return max(np.max((i + 1) / nk - F), np.max(F - i / nk))


# ---------------------------------------------------------------- log-normale tronquée

def log_Z(c1, b):
    """log de l'intégrale sur y >= 0 de exp(-c1 y^2 + b y)."""
    if c1 <= 0.0:
        return -math.log(-b) if b < 0 else math.inf
    z = -b / (2.0 * math.sqrt(c1))
    if z < -25.0:
        le = math.log(2.0) + z * z
    else:
        le = math.log(special.erfcx(z))
    return math.log(0.5) + 0.5 * math.log(math.pi / c1) + le


def ajuste_lognormale(y):
    n = y.size
    s1, s2 = y.sum(), (y * y).sum()

    def nll(p):
        c1, b = p
        lz = log_Z(c1, b)
        if not math.isfinite(lz):
            return 1e300
        return -(-c1 * s2 + b * s1 - n * lz)

    v = max(float(np.var(y)), 1e-12)
    m = float(np.mean(y))
    # départ par les moments de la gaussienne non tronquée (jamais le point loi de puissance)
    depart = np.array([1.0 / (2.0 * v), m / v])
    meilleur = None
    for d in (depart, depart * np.array([0.1, 1.0]), np.array([1.0 / (2.0 * v), -1.0 / max(m, 1e-6)])):
        r = optimize.minimize(nll, d, method="L-BFGS-B", bounds=[(0.0, None), (None, None)],
                              options={"ftol": 1e-15, "gtol": 1e-12, "maxiter": 5000})
        if meilleur is None or r.fun < meilleur.fun:
            meilleur = r
    c1, b = meilleur.x
    return float(c1), float(b), -float(meilleur.fun)


def vuong(l):
    n = l.size
    R = float(l.sum())
    s = float(l.std())
    if s == 0.0 or not math.isfinite(s):
        return R, 1.0
    return R, float(special.erfc(abs(R) / (s * math.sqrt(2.0 * n))))


def ajuste(lam):
    x = np.sort(lam[lam > 0])
    k, a, D = balayage(x)
    xmin = x[k]
    t = x[k:]
    nq = t.size
    y = np.log(t / xmin)
    # loi de puissance, en x et en y
    lp_pl_x = math.log(a - 1.0) - math.log(xmin) - a * y
    lp_pl_y = math.log(a - 1.0) - (a - 1.0) * y
    # exponentielle
    taux = 1.0 / (t.mean() - xmin)
    lp_exp_x = math.log(taux) - taux * (t - xmin)
    R_exp, p_exp = vuong(lp_pl_x - lp_exp_x)
    # log-normale (gaussienne tronquée en y)
    c1, b, ll = ajuste_lognormale(y)
    lp_ln_y = -c1 * y * y + b * y - log_Z(c1, b)
    R_ln, p_ln = vuong(lp_pl_y - lp_ln_y)
    sigma = 1.0 / math.sqrt(2.0 * c1) if c1 > 0 else math.inf
    return dict(n=int(x.size), n_zero=int(lam.size - x.size), k=int(k), x_min=float(xmin), n_queue=int(nq),
                alpha=float(a), ks=float(D), R_exp=R_exp, p_exp=p_exp, R_ln=R_ln, p_ln=p_ln,
                c1=c1, b=b, sigma_ln=sigma), x


def p_gof(x, f, reps, rng):
    k, a, xmin, D0 = f["k"], f["alpha"], f["x_min"], f["ks"]
    n = x.size
    corps = x[:k]
    pq = (n - k) / n
    plus = 0
    for _ in range(reps):
        nq = rng.binomial(n, pq)
        queue = xmin * (1.0 - rng.random(nq)) ** (-1.0 / (a - 1.0))
        bas = corps[rng.integers(0, k, n - nq)] if k > 0 and n - nq > 0 else np.empty(0)
        s = np.sort(np.concatenate([bas, queue]))
        if s.size < GARDE:
            continue
        _, _, D = balayage(s)
        if D >= D0:
            plus += 1
    return plus / reps


def verdicts(f):
    exp_ecartee = f["R_exp"] > 0 and f["p_exp"] < 0.05
    ln_battue = f["R_ln"] > 0 and f["p_ln"] < 0.05
    autre = (f["R_exp"] < 0 and f["p_exp"] < 0.05) or (f["R_ln"] < 0 and f["p_ln"] < 0.05)
    if exp_ecartee and ln_battue:
        v = "loi de puissance"
    elif autre:
        v = "autre loi préférée"
    else:
        v = "non départagée"
    ln_preferee = f["R_ln"] < 0 and f["p_ln"] < 0.05
    comp = None
    if f.get("p_gof") is not None:
        comp = bool(f["p_gof"] >= 0.1 and exp_ecartee and not ln_preferee)
    return v, comp


# ---------------------------------------------------------------- programme

def main():
    priorite_inactive()
    args = sys.argv[1:]
    sans = "--sans-repliques" in args
    casser = "--casser" in args
    reps = 100
    if "--repliques" in args:
        reps = int(args[args.index("--repliques") + 1])
    SORTIE.mkdir(parents=True, exist_ok=True)
    nom = "juge-csn" + ("-casse" if casser else "") + ("-rapide" if sans else "")
    flog = open(SORTIE / f"{nom}.log", "w", encoding="utf-8")

    def journal(s):
        print(s, flush=True)
        flog.write(s + "\n")
        flog.flush()

    journal(f"début {time.strftime('%Y-%m-%d %H:%M:%S')} casser={casser} repliques={0 if sans else reps}")
    z = np.load(NPZ)
    rng = np.random.default_rng(777)

    # ----- témoins
    temoins = []
    # le npz garde des valeurs singulières : lambda = sigma^2
    spec = {"T-Pareto": z["pareto"] ** 2}
    for cle in ("mp/2880x2880", "mp/4096x2880", "mp/2880x4096", "mp/512x2880"):
        spec["T-MP " + cle[3:]] = z[cle] ** 2
    if casser:
        spec["T-Pareto"], spec["T-MP 2880x2880"] = spec["T-MP 2880x2880"], spec["T-Pareto"]
    g = np.random.default_rng(4242)
    for i in range(20):
        spec[f"P2.5#{i:02d}"] = (1.0 - g.random(2880)) ** (-1.0 / 1.5)
    g = np.random.default_rng(4243)
    for i in range(20):
        spec[f"EXP#{i:02d}"] = g.exponential(1.0, 2880)

    # contrôle de l'ajustement log-normal
    g = np.random.default_rng(4244)
    ln = np.sort(g.lognormal(0.0, 1.0, 2880))
    c1, b, _ = ajuste_lognormale(np.log(ln / ln[0]))
    sig = 1.0 / math.sqrt(2.0 * c1)
    ctrl_ln = abs(sig - 1.0) <= 0.05
    journal(f"contrôle log-normal : sigma estimé {sig:.4f} (attendu 1 à 5 %) -> {'TIENT' if ctrl_ln else 'ÉCHEC'}")

    lignes = []

    def traite(ident, lam, groupe):
        f, x = ajuste(lam)
        if not sans:
            attendre(journal)
            f["p_gof"] = p_gof(x, f, reps, rng)
        else:
            f["p_gof"] = None
        v, comp = verdicts(f)
        f.update(id=ident, groupe=groupe, verdict=v, compatible=comp)
        lignes.append(f)
        journal(f"{ident:18s} a={f['alpha']:.6f} xmin={f['x_min']:.6g} nq={f['n_queue']:4d} "
                f"Rexp={f['R_exp']:+.3f} pexp={f['p_exp']:.4f} Rln={f['R_ln']:+.2e} pln={f['p_ln']:.4f} "
                f"sig_ln={f['sigma_ln']:.3g} pgof={f['p_gof']} {v} compat={comp}")
        return f

    for ident, lam in spec.items():
        traite(ident, lam, "témoin")
    if not casser:
        ids = [k[5:] for k in z.files if k.startswith("reel/")]
        for ident in ids:
            traite(ident, z["reel/" + ident] ** 2, "réel")
            traite(ident, z["perm/" + ident] ** 2, "permuté")

    # ----- écriture
    champs = ["id", "groupe", "n", "n_zero", "x_min", "n_queue", "alpha", "ks", "R_exp", "p_exp", "R_ln", "p_ln",
              "c1", "b", "sigma_ln", "p_gof", "verdict", "compatible"]
    with open(SORTIE / f"{nom}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=champs, extrasaction="ignore")
        w.writeheader()
        for l in lignes:
            w.writerow(l)

    # ----- témoins : verdicts
    def T(nomt):
        return next(l for l in lignes if l["id"] == nomt)

    res = {"controle_lognormal": ctrl_ln}
    if not sans:
        tp = T("T-Pareto")
        res["T-Pareto"] = bool(tp["compatible"] and 2.3 <= tp["alpha"] <= 2.7)
        res["T-MP"] = all(not T(n_)["compatible"] for n_ in spec if n_.startswith("T-MP"))
        res["P2.5 compatibles"] = sum(bool(l["compatible"]) for l in lignes if l["id"].startswith("P2.5"))
        res["EXP compatibles"] = sum(bool(l["compatible"]) for l in lignes if l["id"].startswith("EXP"))
        res["P2.5 >= 18"] = res["P2.5 compatibles"] >= 18
        res["EXP <= 2"] = res["EXP compatibles"] <= 2
    res["Rln max (toutes lignes)"] = max(l["R_ln"] for l in lignes)
    res["J1 Rln <= 1e-6"] = res["Rln max (toutes lignes)"] <= 1e-6
    journal("TÉMOINS " + json.dumps(res, ensure_ascii=False))
    if casser:
        journal("cassure : T-Pareto et T-MP 2880x2880 doivent être en ÉCHEC -> "
                + ("les deux tombent" if (not res.get("T-Pareto", True) and not res.get("T-MP", True)) else
                   "AU MOINS UN TIENT ENCORE"))
    journal(f"fin {time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
