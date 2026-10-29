"""Éclaireur Terre et cosmos : M-C, éviction par temps estimé jusqu'à la prochaine utilisation.

Déclarée dans genome/mimetisme/terre_cosmos/seuil-declare.md (addendum du 2026-10-27, commité avant
l'exécution). Un expert x de la couche l_x a un taux q̂_x (compteur décroissant de demi-vie h jetons,
q̂ = compteur effectif · (1 − d), d = 0,5^(1/h)) et un temps estimé jusqu'à sa prochaine utilisation
  τ_x = φ_x + L · (1/q̂_x − 1),  φ_x = ((l_x − l_c − 1) mod L) + 1   (en groupes d'accès)
où l_c est la couche courante. On évince le plus grand τ_x hors du groupe courant.
Variantes pour les témoins : phase constante (doit redonner la LFU) et phase à l'envers (cassure).

Usage : python -I -X utf8 phase_terre.py mesure <20b|120b> <dossier_traces> <sortie_dir> [--melange]
        python -I -X utf8 phase_terre.py temoins <dossier_traces_20b> <sortie_dir>
"""
import json
import math
import os
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np  # noqa: E402

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..")))
import cache_terre as ct  # noqa: E402
import gptoss_localite as gl  # noqa: E402

HL = [2, 4, 8, 16, 32]


def g_phase(groupes, N, L, E, hl, mode="phase"):
    """mode : 'phase' (M-C), 'const' (phase constante : la LFU), 'envers' (phase à l'envers : cassure)."""
    d = 0.5 ** (1.0 / hl)
    ld = math.log(d)
    n_items = L * E
    c = np.zeros(n_items)
    tl = np.zeros(n_items)
    dernier = np.full(n_items, -1, dtype=np.int64)
    couche_de = (np.arange(n_items) // E).astype(np.int64)
    pos = {}
    membres = np.zeros(N + 16, dtype=np.int64)
    taille = 0
    succes = total = 0
    for i, g in enumerate(groupes):
        t = i // L
        lc = i % L
        for x in g:
            total += 1
            if x in pos:
                succes += 1
            else:
                pos[x] = taille
                membres[taille] = x
                taille += 1
            c[x] = c[x] * math.exp(ld * (t - tl[x])) + 1.0
            tl[x] = t
            dernier[x] = i
        exces = taille - N
        if exces > 0:
            m = membres[:taille]
            ceff = c[m] * np.exp(ld * (t - tl[m]))
            q = np.maximum(ceff * (1.0 - d), 1e-9)
            if mode == "const":
                phi = np.full(taille, L / 2.0)
            elif mode == "envers":
                phi = ((lc - couche_de[m] - 1) % L) + 1.0
            else:
                phi = ((couche_de[m] - lc - 1) % L) + 1.0
            tau = phi + L * (1.0 / q - 1.0)
            for x in g:
                tau[pos[x]] = -np.inf
            # on évince les plus grands tau ; ex aequo : le plus ancien (dernier plus petit), puis le plus petit id
            ordre = np.lexsort((m, dernier[m], -tau))[:exces]
            ev = sorted(int(j) for j in ordre)
            for j in reversed(ev):
                x = int(membres[j])
                del pos[x]
                taille -= 1
                if j != taille:
                    y = int(membres[taille])
                    membres[j] = y
                    pos[y] = j
    return succes, total


def mesure(prefixe, dossier, sortie, melange):
    os.makedirs(sortie, exist_ok=True)
    data = {g: ct.charger(prefixe, dossier, g, melange) for g in ct.GENRES}
    E = data[ct.GENRES[0]][1]
    L = len(data[ct.GENRES[0]][0][0])
    k = len(data[ct.GENRES[0]][0][0][0])
    flux = {g: gl.flux(data[g][0], E) for g in ct.GENRES}
    res = {"modele": prefixe, "melange": melange, "L": L, "E": E, "k": k, "budgets": {}}
    t0 = time.time()
    for f in ct.BUDGETS:
        N = max(k, round(f * L * E))
        brut = {g: {} for g in ct.GENRES}
        for g in ct.GENRES:
            gr = flux[g]
            b = brut[g]
            b["lru"] = gl.g_lru(gr, N)
            b["belady"] = gl.g_belady(gr, N)
            for hl in HL:
                b[f"lfu{hl}"] = gl.g_lfu(gr, N, L, float(hl))
                for mode in ("phase", "const", "envers"):
                    s, tot = g_phase(gr, N, L, E, hl, mode)
                    b[f"{mode}{hl}"] = s / tot
            print(f"f={f} {g} : {time.time() - t0:.0f} s", flush=True)
        lignes = {}
        for g in ct.GENRES:
            autres = [x for x in ct.GENRES if x != g]
            cC = max([f"phase{hl}" for hl in HL], key=lambda cle: sum(brut[x][cle] for x in autres))
            cL = max([f"lfu{hl}" for hl in HL], key=lambda cle: sum(brut[x][cle] for x in autres))
            ligne = {"C_choix": cC, "C": brut[g][cC], "lfu_choix": cL, "lfu_regle": brut[g][cL],
                     "lru": brut[g]["lru"], "belady": brut[g]["belady"],
                     "const_meme_hl": brut[g]["const" + cC[5:]], "envers_meme_hl": brut[g]["envers" + cC[5:]],
                     "lfu_meme_hl": brut[g]["lfu" + cC[5:]]}
            ligne["dC"] = ligne["C"] - ligne["lfu_regle"]
            lignes[g] = ligne
        moy = lambda cle: sum(lignes[g][cle] for g in ct.GENRES) / 4
        res["budgets"][f"{f:.2f}"] = {
            "N": N, "brut": brut, "genres": lignes, "moy_dC": moy("dC"),
            "pos_dC": sum(1 for g in ct.GENRES if lignes[g]["dC"] > 0),
            "moy_C": moy("C"), "moy_lfu": moy("lfu_regle"), "moy_lru": moy("lru"), "moy_belady": moy("belady"),
            "moy_envers": moy("envers_meme_hl"), "moy_const": moy("const_meme_hl")}
    nom = f"mesure-phase-{prefixe}{'-melange' if melange else ''}.json"
    with open(os.path.join(sortie, nom), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    for fk, s in res["budgets"].items():
        print(f"f={fk} N={s['N']} : LRU {s['moy_lru']:.4f} LFU réglée {s['moy_lfu']:.4f} "
              f"C {s['moy_C']:.4f} (dC {s['moy_dC']*100:+.2f} pt, {s['pos_dC']}/4) envers {s['moy_envers']:.4f} "
              f"const {s['moy_const']:.4f} Belady {s['moy_belady']:.4f}")
    print(f"total {time.time() - t0:.0f} s")


def temoins(dossier, sortie):
    os.makedirs(sortie, exist_ok=True)
    out = {}
    jetons, E = ct.charger("t20b", dossier, "prose-en")
    L, k = len(jetons[0]), len(jetons[0][0])
    gr = gl.flux(jetons, E)
    N = round(0.20 * L * E)
    for hl in (4, 8, 16):
        s, tot = g_phase(gr, N, L, E, hl, "const")
        lfu = gl.g_lfu(gr, N, L, float(hl))
        ph, _ = g_phase(gr, N, L, E, hl, "phase")
        en, _ = g_phase(gr, N, L, E, hl, "envers")
        out[f"hl{hl}"] = {"const": s / tot, "lfu": lfu, "ecart_const_lfu": s / tot - lfu,
                          "tient_T6": abs(s / tot - lfu) <= 0.002,
                          "phase": ph / tot, "envers": en / tot, "phase_meilleure_que_envers": ph > en}
        print(hl, out[f"hl{hl}"], flush=True)
    with open(os.path.join(sortie, "temoins-phase.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    if sys.argv[1] == "mesure":
        mesure("t" + sys.argv[2], sys.argv[3], sys.argv[4], "--melange" in sys.argv)
    else:
        temoins(sys.argv[2], sys.argv[3])
