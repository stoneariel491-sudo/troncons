"""P4 : préchargement et rétention à confiance calibrée (prédiction conforme), qui cède à la demande.

Protocole : mesures/mimetisme/P4/00-seuils-declares.md (seuils et témoins déclarés AVANT toute lecture de trace).
Le prédicteur recopie la logique de outils/mimetisme/humain/e4b_defauts.py (non modifié), généralisée à toutes les
couches d'observation l0 et rendue avec ses confiances par candidat.

Contenu :
  charger        lecture des traces (un jeton par ligne, couches séparées par « | »)
  predire        voisins de chemin (précédents), causal (jetons <= t - 2) : pred[t, couche cible, m], conf[...]
  passe_cache    LRU global (couche, expert), groupe courant épinglé ; défauts par groupe, présence au moment de
                 la prédiction, épingles optionnelles du bras R
  calibrer       calibration conforme fendue (Clopper-Pearson unilatérale, séquence fixe du haut vers le bas)
  des            simulateur à événements discrets du temps d'un jeton, avec file de fond (priorité ou FIFO)
Aucune carte graphique, aucun fichier modèle ; numpy et scipy seulement.
"""
import os
import sys
from collections import OrderedDict, deque

import numpy as np
from scipy.stats import beta

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(RACINE, "outils"))
import chargement_localite as cl  # noqa: E402

GRILLE = np.round(np.arange(0.30, 1.0001, 0.02), 2)


# ----------------------------------------------------------------------------- données
def charger(dossier):
    """{ 'genre.mode': (J[t, l, k] int16, E) } pour tous les *.trace du dossier."""
    out = {}
    for nom in sorted(os.listdir(dossier)):
        if not nom.endswith(".trace"):
            continue
        parts = nom.split(".")
        jetons, E = cl.lire_trace(os.path.join(dossier, nom))
        out[f"{parts[1]}.{parts[2]}"] = (np.array(jetons, dtype=np.int16), E)
    return out


def multihot(J, E):
    T, L, k = J.shape
    M = np.zeros((L, T, E), dtype=np.float32)
    ti = np.arange(T)[:, None]
    for l in range(L):
        M[l, ti, J[:, l, :]] = 1.0
    return M


# ----------------------------------------------------------------------------- prédicteur
def predire(J, E, d, m=6, K=20, aleatoire=False, graine=20261027, M=None):
    """pred[t, lt, i] : i-ième candidat (par vote décroissant) pour la couche lt = l0 + d du jeton t, vu à la fin du
    routage de l0 ; -1 si aucun antécédent. conf[t, lt, i] : part pondérée des voisins qui portent le candidat.
    Causal : voisins parmi les jetons <= t - 2 (comme e4b_defauts.py)."""
    T, L, k = J.shape
    if M is None:
        M = multihot(J, E)
    rng = np.random.default_rng(graine)
    S = np.zeros((T, T), dtype=np.float32)
    ok = np.tril(np.ones((T, T), dtype=bool), -2)
    pred = -np.ones((T, L, m), dtype=np.int16)
    conf = np.zeros((T, L, m), dtype=np.float32)
    kk = min(K, T - 1)
    for l0 in range(L - d):
        S += M[l0] @ M[l0].T
        if aleatoire:
            Sm = np.where(ok, rng.random((T, T), dtype=np.float32), -1.0)
        else:
            Sm = np.where(ok, S, -1.0)
        top = np.argpartition(-Sm, kk - 1, axis=1)[:, :kk]
        w = np.take_along_axis(Sm, top, axis=1)
        valid = (w >= 0) if aleatoire else (w > 0)
        w = np.where(valid, np.maximum(w, 0) + 1e-9, 0.0).astype(np.float32)
        votes = np.einsum("tk,tke->te", w, M[l0 + d][top])
        wsum = w.sum(axis=1, keepdims=True)
        idx = np.argsort(-votes, axis=1)[:, :m]
        cv = np.take_along_axis(votes, idx, axis=1) / np.maximum(wsum, 1e-12)
        bon = (wsum > 0) & (cv > 0)
        pred[:, l0 + d] = np.where(bon, idx, -1)
        conf[:, l0 + d] = np.where(bon, cv, 0.0)
    return pred, conf


def etiquettes(J, pred):
    """vrai si le candidat est dans l'ensemble réellement choisi à la couche cible."""
    T, L, m = pred.shape
    lab = np.zeros((T, L, m), dtype=bool)
    for i in range(m):
        lab[:, :, i] = (J == pred[:, :, i][:, :, None]).any(axis=2) & (pred[:, :, i] >= 0)
    return lab


# ----------------------------------------------------------------------------- cache
def passe_cache(J, E, N, d, pred=None, conf=None, theta=None, t_from=0, pin_frac=0.10):
    """LRU global sur les cellules (couche, expert) ; les experts du groupe courant ne sont pas évinçables
    (règle de trc-cache). Rend :
      faults[g]   : liste des experts en défaut au groupe g = t * L + l
      present[t, lt, i] : le candidat i (prédit à la fin du routage de lt - d) était dans le cache à cet instant
    Si theta est donné (bras R) : les candidats de confiance >= theta DÉJÀ présents sont épinglés jusqu'à la fin de la
    couche cible, pour t >= t_from, au plus pin_frac * N épingles à la fois."""
    T, L, k = J.shape
    cache = OrderedDict()
    faults = [None] * (T * L)
    m = pred.shape[2] if pred is not None else 0
    present = np.zeros((T, L, m), dtype=bool) if pred is not None else None
    pins = {}          # clé -> compte
    pins_par_cible = {}
    pin_max = int(pin_frac * N)
    npins = 0
    for g in range(T * L):
        t, l = divmod(g, L)
        cles = [l * E + int(e) for e in J[t, l]]
        cur = set(cles)
        fl = []
        for e, key in zip(J[t, l], cles):
            if key in cache:
                cache.move_to_end(key)
            else:
                fl.append(int(e))
                cache[key] = None
                while len(cache) > N:
                    victime = None
                    for v in cache:
                        if v not in cur and v not in pins:
                            victime = v
                            break
                    if victime is None:
                        break
                    del cache[victime]
        faults[g] = fl
        # libérer les épingles dont la cible est ce groupe
        for key in pins_par_cible.pop(g, ()):
            pins[key] -= 1
            npins -= 1
            if pins[key] == 0:
                del pins[key]
        # prédictions faites à la fin du routage de la couche l pour la couche l + d
        lt = l + d
        if pred is not None and lt < L:
            for i in range(m):
                e = int(pred[t, lt, i])
                if e < 0:
                    continue
                key = lt * E + e
                pres = key in cache
                present[t, lt, i] = pres
                if theta is not None and t >= t_from and pres and conf[t, lt, i] >= theta and npins < pin_max:
                    pins[key] = pins.get(key, 0) + 1
                    pins_par_cible.setdefault(g + d, []).append(key)
                    npins += 1
    return faults, present


def lru_liste(acces, N):
    """Seconde implémentation (liste simple) pour le témoin : acces = liste de groupes (listes de clés)."""
    lst = []
    defauts = 0
    for grp in acces:
        for key in grp:
            if key in lst:
                lst.remove(key)
                lst.append(key)
            else:
                defauts += 1
                lst.append(key)
                while len(lst) > N:
                    for v in lst:
                        if v not in grp:
                            lst.remove(v)
                            break
                    else:
                        break
    return defauts


# ----------------------------------------------------------------------------- calibration conforme
def borne_cp(x, n, delta):
    """Borne inférieure de Clopper-Pearson unilatérale (niveau 1 - delta) de la probabilité de succès."""
    if n == 0 or x == 0:
        return 0.0
    return float(beta.ppf(delta, x, n - x + 1))


def calibrer(conf, lab, cible=0.9, delta=0.1, n_min=30, grille=GRILLE):
    """theta* : le plus petit seuil tel que tous les seuils de la grille au-dessus (et lui) passent le test
    borne_cp >= cible, séquence fixe du haut vers le bas, départ au plus haut seuil retenant >= n_min éléments.
    None si aucun. Rend (theta*, courbe[(seuil, n, x, borne)])."""
    conf = np.asarray(conf)
    lab = np.asarray(lab)
    courbe = []
    best = None
    depart = False
    for th in grille[::-1]:
        sel = conf >= th - 1e-9
        n = int(sel.sum())
        if not depart:
            if n < n_min:
                continue
            depart = True
        x = int(lab[sel].sum())
        lb = borne_cp(x, n, delta)
        courbe.append((float(th), n, x, lb))
        if lb < cible:
            break
        best = float(th)
    return best, courbe


# ----------------------------------------------------------------------------- simulateur
def des(J, E, d, faults, charges, par, mode="prio", t_from=0, purge_totale=False):
    """Temps d'un jeton. charges[g] = liste d'experts à lire d'avance pour la cible g (émis à la fin du routage du
    groupe g - d). par : w_layer (fenêtre de calcul par couche, ms), tail, tr (lecture), o (surcoût bloquant).
    mode 'prio' : lectures de fond seulement dans les fenêtres de calcul, cédant à la demande ; 'fifo' : tout
    démarre dès que le disque est libre et la demande attend. Rend dict (temps par jeton, octets de demande et de
    fond par groupe)."""
    T, L, k = J.shape
    a = c = par["w_layer"] / 2.0
    tail, tr, o = par["tail"], par["tr"], par["o"]
    D = 0.0
    now = 0.0
    file = deque()
    pret = {}
    tok = np.zeros(T)
    dem = np.zeros(T * L, dtype=np.int32)
    bg = np.zeros(T * L, dtype=np.int32)
    tstart = 0.0

    def drainer(g, ws, we):
        nonlocal D
        while file:
            key, tg, iss = file[0]
            if tg < g:
                file.popleft()
                continue
            s = max(D, iss, ws)
            if s >= we:
                break
            file.popleft()
            D = s + tr
            pret[key] = D
            bg[g] += 1

    for g in range(T * L):
        t, l = divmod(g, L)
        if l == 0:
            tstart = now
        t_route = now + a
        if mode == "prio":
            drainer(g, now, t_route)
        else:
            # FIFO : tout ce qui a été émis avant passe avant la demande
            while file:
                key, tg, iss = file.popleft()
                if tg < g:
                    continue
                s = max(D, iss)
                D = s + tr
                pret[key] = D
                bg[g] += 1
        # arrivée de la demande : les lectures de fond pas commencées pour cette cible, ou périmées, sont annulées
        if purge_totale:
            file.clear()
        else:
            if file:
                file = deque(x for x in file if x[1] > g)
        prets = 0.0
        nd = 0
        nst = 0
        for e in faults[g]:
            key = (g, e)
            if key in pret:
                prets = max(prets, pret.pop(key))
                nst += 1
            else:
                D = max(D, t_route) + tr
                nd += 1
        dem[g] = nd
        tD = max(t_route, D if nd else t_route, prets)
        # nettoyer la zone d'accueil de cette cible (lectures inutiles)
        for key in [x for x in pret if x[0] <= g]:
            del pret[key]
        # émissions : prédictions faites ici, pour la cible g + d
        gc = g + d
        if gc < T * L and charges[gc]:
            for e in charges[gc]:
                file.append(((gc, e), gc, t_route))
        tc = tD + (tail if (nd or nst) else 0.0)   # v2 : la copie + décodage se font aussi pour un tronçon lu d'avance
        if mode == "prio":
            drainer(g + 1, tc, tc + c)   # g + 1 : une cible égale à g est déjà servie
        now = tc + c + o
        if l == L - 1:
            tok[t] = now - tstart
    return {"tok": tok, "dem": dem, "bg": bg}


def construire_charges(J, E, d, pred, conf, present, theta, t_from):
    """Chargements du bras P : candidats de confiance >= theta, ABSENTS du cache au moment de la prédiction, pour
    les jetons t >= t_from. charges[g] = liste d'experts ; justes[g] = nombre qui sont dans l'ensemble vrai."""
    T, L, m = pred.shape
    charges = [[] for _ in range(T * L)]
    just = np.zeros(T * L, dtype=np.int32)
    if theta is None:
        return charges, just
    lab = etiquettes(J, pred)
    sel = (pred >= 0) & (~present) & (conf >= theta - 1e-9)
    sel[:t_from] = False
    ts, ls, ms = np.nonzero(sel)
    for t, l, i in zip(ts, ls, ms):
        g = t * L + l
        charges[g].append(int(pred[t, l, i]))
        just[g] += int(lab[t, l, i])
    return charges, just
