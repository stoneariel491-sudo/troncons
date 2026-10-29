"""Juge P6 : second chemin indépendant du chiffre principal (variante A) et de la variante B.

Seuils : mesures/mimetisme/P6/juge/00-seuils-du-juge.md (commités avant ce calcul).
N'importe rien des outils du rôle de mesure. Python pur, accès après accès, un fil, priorité basse.
Usage : python -I -X utf8 juge_p6.py <dossier traces 120b> <dossier traces 20b> <sortie.json>
"""
import ctypes
import json
import random
import sys

try:  # priorité sous la normale (BELOW_NORMAL_PRIORITY_CLASS)
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass

RHO = 0.718
K = 4


def lire(chemin, conv):
    lignes, E = [], None
    with open(chemin, encoding="utf-8") as f:
        for brute in f:
            l = brute.strip()
            if not l or l.startswith("#"):
                continue
            if l.startswith("E="):
                E = int(l[2:])
                continue
            groupes = [g for g in l.split("|") if g.strip()]
            lignes.append([[conv(v) for v in g.split()] for g in groupes])
    return lignes, E


def charger(dossier, base):
    ex, E = lire(f"{dossier}/{base}.trace", int)
    wt, _ = lire(f"{dossier}/{base}.poids", float)
    assert len(ex) == len(wt)
    for a, b in zip(ex, wt):
        assert len(a) == len(b) and all(len(x) == K and len(y) == K for x, y in zip(a, b))
    return ex, wt, E


def simuler(ex, E, N, demi_vie=8.0):
    """Rend la liste des accès dans l'ordre : (t, l, s, x, defaut, sejour)."""
    T, L = len(ex), len(ex[0])
    compte, dernier_t, dernier_g = {}, {}, {}
    resident = set()
    sej_de, n_sej, g_idx = {}, 0, 0
    acces = []
    for t in range(T):
        for l in range(L):
            g_idx += 1
            groupe = [l * E + e for e in ex[t][l]]
            for s, x in enumerate(groupe):
                c = compte.get(x, 0.0)
                if x in dernier_t:
                    c = c * 2.0 ** (-(t - dernier_t[x]) / demi_vie)
                compte[x] = c + 1.0
                dernier_t[x] = t
                dernier_g[x] = g_idx
                d = x not in resident
                if d:
                    resident.add(x)
                    n_sej += 1
                    sej_de[x] = n_sej
                acces.append((t, l, s, x, d, sej_de[x]))
            gs = set(groupe)
            while len(resident) > N:
                victime, meilleur = None, None
                for y in resident:
                    if y in gs:
                        continue
                    sc = compte[y] * 2.0 ** (-(t - dernier_t[y]) / demi_vie)
                    cle = (sc, dernier_g[y])
                    if meilleur is None or cle < meilleur:
                        meilleur, victime = cle, y
                resident.discard(victime)
    return acces


def appliquer(acces, poids, theta, regle, theta_p=None, poids_porte=None):
    """Automate d'étiquettes par séjour. poids_porte : poids lu par la porte (défaut : le vrai)."""
    pp = poids if poids_porte is None else poids_porte
    etiq = {}
    E_rapide = octets = E_tout = 0.0
    n_def = 0
    par_t = {}
    for (t, l, s, x, d, sj) in acces:
        w = poids[t][l][s]
        wp = pp[t][l][s]
        E_tout += w * w
        e = o = 0.0
        if d:
            n_def += 1
            if wp < theta:
                etiq[sj] = "F"
                o = RHO
                e = w * w
            else:
                etiq[sj] = "E"
                o = 1.0
        else:
            if etiq[sj] == "F":
                if regle == "remonter" and wp >= theta_p:
                    etiq[sj] = "E"
                    o = 1.0
                else:
                    e = w * w
        E_rapide += e
        octets += o
        b = par_t.setdefault(t, [0.0, 0.0, 0.0, 0])
        b[0] += e
        b[1] += o
        b[2] += w * w
        b[3] += 1 if d else 0
    return par_t


def bilan(blocs_t):
    E_ = sum(b[0] for b in blocs_t)
    O_ = sum(b[1] for b in blocs_t)
    Et = sum(b[2] for b in blocs_t)
    Nd = sum(b[3] for b in blocs_t)
    S = (Nd - O_) / Nd
    e = E_ / Et
    r = e / (S / (1 - RHO)) if S > 0 else float("inf")
    return S, e, r, Nd


def amorce(par_t_liste, bloc=32, tirages=2000, graine=7):
    """Sigma par blocs de 32 jetons (blocs regroupés de toutes les traces), tirage à remise."""
    blocs = []
    for par_t in par_t_liste:
        T = max(par_t) + 1
        for i in range(0, T, bloc):
            agg = [0.0, 0.0, 0.0, 0]
            for t in range(i, min(T, i + bloc)):
                for j in range(4):
                    agg[j] += par_t[t][j]
            blocs.append(agg)
    rng = random.Random(graine)
    Ss, rs = [], []
    for _ in range(tirages):
        ech = [blocs[rng.randrange(len(blocs))] for _ in blocs]
        S, e, r, _ = bilan(ech)
        Ss.append(S)
        if r != float("inf"):
            rs.append(r)

    def sd(v):
        m = sum(v) / len(v)
        return (sum((a - m) ** 2 for a in v) / len(v)) ** 0.5
    return sd(Ss), sd(rs)


def variante_b(ex, wt, E, lot=512, S_cible=0.08, complets=True):
    """Par lot et couche, chaque expert appelé lu une fois. Classement global (genre) par score,
    les plus petits en rapide jusqu'à la part f = S/(1-rho). Rend r pour max, masse, oracle Σw², hasard."""
    T, L = len(ex), len(ex[0])
    items = []  # (max, masse, energie)
    nlots = T // lot if complets else (T + lot - 1) // lot
    for i in range(nlots):
        for l in range(L):
            acc = {}
            for t in range(i * lot, min(T, (i + 1) * lot)):
                for s in range(K):
                    x = ex[t][l][s]
                    w = wt[t][l][s]
                    a = acc.setdefault(x, [0.0, 0.0, 0.0])
                    a[0] = max(a[0], w)
                    a[1] += w
                    a[2] += w * w
            items.extend(acc.values())
    Et = sum(a[2] for a in items)
    n = len(items)
    k = round(S_cible / (1 - RHO) * n)
    f = k / n
    out = {"items": n, "lots": nlots, "f": f}
    for nom, idx in (("max", 0), ("masse", 1), ("oracle", 2)):
        tri = sorted(range(n), key=lambda j: (items[j][idx], j))
        Ef = sum(items[j][2] for j in tri[:k])
        out[nom] = (Ef / Et) / f
    rng = random.Random(11)
    rh = []
    for _ in range(50):
        ch = rng.sample(range(n), k)
        rh.append((sum(items[j][2] for j in ch) / Et) / f)
    out["hasard"] = sum(rh) / len(rh)
    return out


def main():
    d120, d20, sortie = sys.argv[1:4]
    res = {"seuils": "mesures/mimetisme/P6/juge/00-seuils-du-juge.md"}
    G = {"gen-prose-en": "t120b.prose-en.generation", "gen-wiki": "w120b.wiki.generation"}
    regles = [("accepter", None), ("remonter", 0.30), ("remonter", 0.40), ("remonter", 0.50)]
    donnees = {}
    for k, base in G.items():
        ex, wt, E = charger(d120, base)
        acc = simuler(ex, E, 323)
        donnees[k] = (ex, wt, E, acc)
        print(k, "jetons", len(ex), "défauts", sum(a[4] for a in acc), flush=True)
    A = {}
    for nom, tp in regles:
        cle = nom if tp is None else f"remonter{tp:.2f}"
        A[cle] = {}
        tous = []
        for k, (ex, wt, E, acc) in donnees.items():
            pt = appliquer(acc, wt, 0.20, nom, tp)
            tous.append(pt)
            S, e, r, Nd = bilan(list(pt.values()))
            sS, sr = amorce([pt])
            A[cle][k] = {"S": S, "E_rel": e, "r": r, "defauts": Nd, "sigma_S": sS, "sigma_r": sr}
        S, e, r, Nd = bilan([b for pt in tous for b in pt.values()])
        sS, sr = amorce(tous)
        A[cle]["cumul"] = {"S": S, "E_rel": e, "r": r, "defauts": Nd, "sigma_S": sS, "sigma_r": sr}
        print(cle, json.dumps(A[cle]), flush=True)
    res["A_120b_gen_theta020"] = A
    # T-J0
    tj0 = {}
    for k, (ex, wt, E, acc) in donnees.items():
        S0, e0, _, _ = bilan(list(appliquer(acc, wt, 0.0, "accepter").values()))
        S2, e2, r2, _ = bilan(list(appliquer(acc, wt, 2.0, "accepter").values()))
        tj0[k] = {"theta0_S": S0, "theta0_E": e0, "theta2_r": r2}
    res["T_J0"] = tj0
    # T-J1 : porte sur un poids permuté globalement, énergie sur le vrai poids
    rng = random.Random(20261027)
    tous = []
    for k, (ex, wt, E, acc) in donnees.items():
        plat = [w for row in wt for g in row for w in g]
        rng.shuffle(plat)
        it = iter(plat)
        perm = [[[next(it) for _ in g] for g in row] for row in wt]
        tous.append(appliquer(acc, wt, 0.20, "accepter", poids_porte=perm))
    S, e, r, _ = bilan([b for pt in tous for b in pt.values()])
    res["T_J1_porte_aveugle_cumul"] = {"S": S, "E_rel": e, "r": r}
    print("T-J1", res["T_J1_porte_aveugle_cumul"], flush=True)
    # Contrôle du raisonnement sur T2 (mélange par couche) : énergie des seuls succès
    # Variante B, 120b et 20b
    B = {}
    for dossier, pre, gens in ((d120, "120b", ["code", "dialogue", "prose-en", "prose-fr"]),
                              (d20, "20b", ["code", "dialogue", "prose-en", "prose-fr"])):
        for g in gens:
            ex, wt, E = charger(dossier, f"t{pre}.{g}.lecture")
            for S_c in (0.08, 0.14):
                B[f"{pre}-{g}-S{S_c:.2f}"] = variante_b(ex, wt, E, 512, S_c)
                print(pre, g, S_c, B[f"{pre}-{g}-S{S_c:.2f}"], flush=True)
            B[f"{pre}-{g}-S0.08-avec-lot-partiel"] = variante_b(ex, wt, E, 512, 0.08, complets=False)
    res["B"] = B
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
