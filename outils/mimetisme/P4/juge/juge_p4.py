"""P4, juge indépendant : refait précision, couverture, octets et gain du bras P par un second chemin.

Écrit d'après le texte du protocole (mesures/mimetisme/P4/00-seuils-declares.md, § 1 et amendement), sans reprendre le code
de P4. Seuil du juge : mesures/mimetisme/P4/juge/00-seuil-du-juge.md.

Usage : python -I -X utf8 juge_p4.py <dossier_traces_120b> <sortie.json>
"""
import json
import os
import sys
import time
from collections import OrderedDict

import numpy as np
from scipy.stats import binom

TR = 4.1        # ms par lecture d'un tronçon
TAIL = 1.85     # copie + décodage
W_TOK = 80.0    # fenêtre de calcul par jeton (ms)
BASE_MS = 460.0
GRILLE = [round(0.30 + 0.02 * i, 2) for i in range(36)]   # 0,30 .. 1,00


# ------------------------------------------------------------------ lecture
def lire(chemin):
    E = None
    rangs = []
    with open(chemin, encoding="utf-8") as f:
        for brut in f:
            s = brut.strip()
            if not s or s[0] == "#":
                continue
            if s.startswith("E="):
                E = int(s[2:])
                continue
            rangs.append([[int(x) for x in bloc.split()] for bloc in s.split("|")])
    return np.array(rangs, dtype=np.int32), E


# ------------------------------------------------------------------ prédicteur (boucle jeton par jeton)
def predire(J, E, d, K=20, m=6):
    T, L, k = J.shape
    H = np.zeros((L, T, E), dtype=np.int8)
    for l in range(L):
        for j in range(k):
            H[l, np.arange(T), J[:, l, j]] = 1
    cand = -np.ones((T, L, m), dtype=np.int32)
    conf = np.zeros((T, L, m))
    for t in range(2, T):
        n = t - 1                      # voisins admis : 0 .. t-2
        ov = np.zeros(n, dtype=np.int32)
        for l0 in range(L - d):
            ov += H[l0, :n][:, J[t, l0]].sum(axis=1)
            ordre = np.argsort(-ov, kind="stable")[:K]
            w = ov[ordre].astype(float)
            garde = w > 0
            if not garde.any():
                continue
            ordre, w = ordre[garde], w[garde]
            votes = (w[:, None] * H[l0 + d, ordre]).sum(axis=0)
            tot = w.sum()
            top = np.argsort(-votes, kind="stable")[:m]
            for i, e in enumerate(top):
                if votes[e] > 0:
                    cand[t, l0 + d, i] = e
                    conf[t, l0 + d, i] = votes[e] / tot
    return cand, conf


def etiqueter(J, cand):
    T, L, m = cand.shape
    lab = np.zeros((T, L, m), dtype=bool)
    for i in range(m):
        c = cand[:, :, i]
        lab[:, :, i] = (c >= 0) & (J == c[:, :, None]).any(axis=2)
    return lab


# ------------------------------------------------------------------ cache LRU global
def lru(J, E, N, d, cand):
    """Rend les défauts par groupe et, pour chaque candidat, s'il est dans le cache à la fin du routage de la couche
    d'émission. Horloge d'usage : dernier accès ; éviction du plus ancien hors groupe courant."""
    T, L, k = J.shape
    m = cand.shape[2]
    dernier = OrderedDict()            # du plus ancien au plus récent
    defauts = []
    present = np.zeros((T, L, m), dtype=bool)
    for t in range(T):
        for l in range(L):
            courant = {(l, int(e)) for e in J[t, l]}
            f = []
            for e in J[t, l]:
                cle = (l, int(e))
                if cle in dernier:
                    dernier.move_to_end(cle)
                    continue
                f.append(int(e))
                if len(dernier) >= N:
                    for c in dernier:
                        if c not in courant:
                            del dernier[c]
                            break
                dernier[cle] = None
            defauts.append(f)
            lt = l + d
            if lt < L:
                for i in range(m):
                    e = cand[t, lt, i]
                    if e >= 0:
                        present[t, lt, i] = (lt, int(e)) in dernier
    return defauts, present


# ------------------------------------------------------------------ calibration
def borne_inf(x, n, delta=0.1):
    """Clopper-Pearson unilatérale par bissection : le plus petit p tel que P(X >= x | n, p) >= delta."""
    if x == 0:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if binom.sf(x - 1, n, mid) >= delta:
            hi = mid
        else:
            lo = mid
    return hi


def calibrer(conf, lab, cible=0.9, nmin=30):
    meilleur = None
    parti = False
    for th in reversed(GRILLE):
        s = conf >= th - 1e-12
        n = int(s.sum())
        if not parti:
            if n < nmin:
                continue
            parti = True
        if borne_inf(int(lab[s].sum()), n) < cible:
            break
        meilleur = th
    return meilleur


# ------------------------------------------------------------------ simulateur (d'après le texte)
def simuler(defauts, charges, T, L, d, o, a_frac=0.5):
    """charges[g] : experts lus d'avance pour la cible g, émis à la fin du routage de g - d.
    Rend temps par jeton, lectures de demande et lectures de fond commencées, par groupe."""
    w = W_TOK / L
    a, c = a_frac * w, (1 - a_frac) * w
    disque = 0.0
    t_now = 0.0
    attente = []            # file de fond : [cible, expert]
    fini = {}               # (cible, expert) -> heure de fin
    tok = np.zeros(T)
    ndem = np.zeros(T * L, dtype=np.int64)
    nbg = np.zeros(T * L, dtype=np.int64)

    def fond(g_min, debut, fin, g_compte):
        nonlocal disque, attente
        reste = []
        for idx, (cib, e) in enumerate(attente):
            if cib < g_min:
                continue
            s = max(disque, debut)
            if s >= fin:
                reste.extend(x for x in attente[idx:] if x[0] >= g_min)
                break
            disque = s + TR
            fini[(cib, e)] = disque
            nbg[g_compte] += 1
        attente = reste

    t0 = 0.0
    for g in range(T * L):
        t, l = divmod(g, L)
        if l == 0:
            t0 = t_now
        route = t_now + a
        fond(g, t_now, route, g)                     # fenêtre a de cette couche
        # arrivée de la demande : fond non commencé pour g annulé (devient demande), cibles passées purgées
        attente = [x for x in attente if x[0] > g]
        pret = route
        nd = 0
        servi = 0
        for e in defauts[g]:
            if (g, e) in fini:
                pret = max(pret, fini[(g, e)])
                servi += 1
            else:
                disque = max(disque, route) + TR
                pret = max(pret, disque)
                nd += 1
        ndem[g] = nd
        for cle in [x for x in fini if x[0] <= g]:
            del fini[cle]
        gc = g + d
        if gc < T * L:
            attente.extend((gc, e) for e in charges[gc])
        fin_lecture = pret + (TAIL if (nd or servi) else 0.0)
        fond(g + 1, fin_lecture, fin_lecture + c, g)  # fenêtre c de cette couche
        t_now = fin_lecture + c + o
        if l == L - 1:
            tok[t] = t_now - t0
    return tok, ndem, nbg


def ajuster_o(defauts, T, L, d, demi):
    vide = [[] for _ in range(T * L)]
    tok, _, _ = simuler(defauts, vide, T, L, d, 0.0)
    return (BASE_MS - tok[demi:].mean()) / L


# ------------------------------------------------------------------ session
def session(nom, J, E, N, d, o_global, alea_lab=False):
    T, L, k = J.shape
    demi = T // 2
    cand, conf = predire(J, E, d)
    lab = etiqueter(J, cand)
    defauts, present = lru(J, E, N, d, cand)
    valide = cand >= 0
    cal = np.zeros_like(valide)
    cal[:demi] = True
    pop_cal = cal & valide & ~present
    pop_tst = ~cal & valide & ~present
    th = calibrer(conf[pop_cal], lab[pop_cal])
    F = sum(len(defauts[g]) for g in range(demi * L, T * L))
    r = {"session": nom, "T": T, "N": N, "d": d, "theta": th, "defauts_test": F,
         "defauts_par_jeton": F / (T - demi), "succes_cache_test": 1 - F / ((T - demi) * L * k)}
    # témoin J1 : étiquettes mélangées
    rng = np.random.default_rng(1729)
    lab_m = etiqueter(J[rng.permutation(T)], cand)
    r["J1_theta_melange"] = calibrer(conf[pop_cal], lab_m[pop_cal])
    if th is None:
        r.update(gain={}, precision=None, couverture=0.0, octets=0.0)
        return r, cand, conf, defauts, present, lab
    s = pop_tst & (conf >= th - 1e-12)
    C, U = int(s.sum()), int(lab[s].sum())
    r["J1_precision_melange_a_theta"] = float(lab_m[s].mean()) if C else None
    r.update(charges=C, justes=U, precision=U / C, couverture=U / F)
    charges = [[] for _ in range(T * L)]
    for t, l, i in zip(*np.nonzero(s)):
        charges[t * L + l].append(int(cand[t, l, i]))
    gains = {}
    o_sess = ajuster_o(defauts, T, L, d, demi)
    for etiquette, o in (("o_global", o_global), ("o_session", o_sess), ("o_zero", 0.0)):
        vide = [[] for _ in range(T * L)]
        tb, _, _ = simuler(defauts, vide, T, L, d, o)
        ta, nd, nb = simuler(defauts, charges, T, L, d, o)
        gains[etiquette] = {"o": o, "ms_base": float(tb[demi:].mean()), "gain": float(tb[demi:].sum() / ta[demi:].sum() - 1),
                            "octets": float((nd[demi * L:].sum() + nb[demi * L:].sum()) / F - 1)}
    # sensibilité : partage a / c de la fenêtre
    for af in (0.2, 0.8):
        vide = [[] for _ in range(T * L)]
        tb, _, _ = simuler(defauts, vide, T, L, d, o_global, af)
        ta, _, _ = simuler(defauts, charges, T, L, d, o_global, af)
        gains[f"a_frac_{af}"] = float(tb[demi:].sum() / ta[demi:].sum() - 1)
    # borne analytique : économie <= min(U*TR, U*TR... limitée par la fenêtre totale de calcul)
    tb_ms = gains["o_global"]["ms_base"] * (T - demi)
    eco = min(U * TR, W_TOK * (T - demi))
    gains["borne_analytique"] = float(eco / (tb_ms - eco))
    r["gain"] = gains
    r["octets"] = gains["o_global"]["octets"]
    r["o_session"] = o_sess
    return r, cand, conf, defauts, present, lab


def main():
    dossier, sortie = sys.argv[1], sys.argv[2]
    N, d = 326, 2
    out = {"N": N, "d": d, "sessions": []}
    t0 = time.time()
    # o global : ajusté pour 460 ms au jeton de base, en commun sur les 4 genres de lecture (le texte ne dit pas lequel)
    noms = ["t120b.code.lecture", "t120b.dialogue.lecture", "t120b.prose-en.lecture", "t120b.prose-fr.lecture"]
    donnees = {n: lire(os.path.join(dossier, n + ".trace")) for n in noms}
    for n in ("t120b.prose-en.generation", "w120b.wiki.generation"):
        donnees[n] = lire(os.path.join(dossier, n + ".trace"))
    # o commun : moyenne des o par session sur les 4 lectures, calculée sur la base sans prédicteur
    os_ = []
    cache_def = {}
    for n in noms:
        J, E = donnees[n]
        T, L, _ = J.shape
        cand0 = -np.ones((T, L, 1), dtype=np.int32)
        dft, _ = lru(J, E, N, d, cand0)
        cache_def[n] = dft
        os_.append(ajuster_o(dft, T, L, d, T // 2))
    o_global = float(np.mean(os_))
    out["o_par_session_base"] = dict(zip(noms, os_))
    out["o_global"] = o_global
    print(f"o par session {os_} -> o commun {o_global:.3f} ms/couche [{time.time()-t0:.0f}s]", flush=True)

    for n in noms + ["t120b.prose-en.generation", "w120b.wiki.generation"]:
        J, E = donnees[n]
        r, cand, conf, defauts, present, lab = session(n, J, E, N, d, o_global)
        out["sessions"].append(r)
        g = r["gain"].get("o_global", {}).get("gain") if r["gain"] else 0.0
        print(f"{n:28s} theta={r['theta']} prec={r['precision']} couv={r['couverture']:.3f} octets={r['octets']:+.4f} "
              f"gain={g if g is None else round(100*g, 2)} % J1theta={r['J1_theta_melange']} succes={r['succes_cache_test']:.3f} "
              f"[{time.time()-t0:.0f}s]", flush=True)
        if n == "t120b.code.lecture":
            # témoin J2 : prédicteur parfait à d = 1, tous les défauts lus d'avance
            T, L, _ = J.shape
            dft = cache_def[n]
            parf = [[] for _ in range(T * L)]
            for gg in range(T * L):
                parf[gg] = list(dft[gg])
            vide = [[] for _ in range(T * L)]
            tb, _, _ = simuler(dft, vide, T, L, 1, o_global)
            ta, _, _ = simuler(dft, parf, T, L, 1, o_global)
            x = float(tb[T // 2:].sum() / ta[T // 2:].sum())
            out["J2_parfait_d1_x"] = x
            print(f"J2 parfait d=1 : x{x:.4f}", flush=True)
        json.dump(out, open(sortie, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=float)
    json.dump(out, open(sortie, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=float)


if __name__ == "__main__":
    main()
