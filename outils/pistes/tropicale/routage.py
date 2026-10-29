"""Lecture des journaux de routage du lot R, et la cohabitation avec le flux qui mesure des vitesses.

Format (tête de mesures/moteur/R/bascules.py) : u32 couches, u32 positions aplaties (fenêtre × 511 +
position), puis pour chaque couche et chaque position 4 × u8 experts et f32 marge (4e − 5e logit
biaisé du routeur). Ce module est le chemin principal (numpy) ; le second chemin est la lecture en
Python pur de bascules.py, appelée par second_chemin.py.

Cohabitation (consigne de la piste) : priorité « sous la normale », un fil de calcul, jamais la carte
graphique, et pause tant que le verrou de la carte annonce une séance de vitesse.
"""

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import time
from pathlib import Path

import numpy as np

DEPOT = Path(__file__).resolve().parents[3]
ROUTAGE = DEPOT / "mesures" / "moteur" / "R" / "r1" / "routage"
A = ROUTAGE / "ref-openai-bis-20b.bin"          # rampe d'OpenAI, la référence du juge
B = ROUTAGE / "ref-llamacpp-bis-20b.bin"        # rampe de llama.cpp, le calcul qui s'écarte
C = ROUTAGE / "ref-llamacpp-routage-openai-20b.bin"  # rampe de llama.cpp, routage de A imposé
K3 = DEPOT / "mesures" / "moteur" / "K" / "k3" / "k3-chaine-d1-gptoss20b-marges.csv"
SORTIE = DEPOT / "mesures" / "pistes" / "tropicale"
VERROU = Path("~/dev/verrou-carte.txt")
N_CTX = 512
LONG = N_CTX - 1  # positions par fenêtre dans le journal (0 … 510)

CELLULE = np.dtype([("e", "u1", (4,)), ("m", "<f4")])


def sous_la_normale():
    """Baisse la priorité du processus courant ; ne touche à aucun autre processus."""
    # `python -I` ne voit pas les paquets de l'utilisateur (psutil) : l'appel Windows direct suffit.
    try:
        import ctypes
        k = ctypes.windll.kernel32
        k.GetCurrentProcess.restype = ctypes.c_void_p  # pseudo-poignée −1 sur 64 bits, pas un int de 32
        k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        ok = k.SetPriorityClass(k.GetCurrentProcess(), 0x00004000)  # BELOW_NORMAL_PRIORITY_CLASS
        if not ok:
            print("priorité non baissée : SetPriorityClass a échoué")
    except Exception as e:  # la mesure reste juste, seule la politesse manque : on le dit
        print(f"priorité non baissée : {e}")


def attendre_calme(pas=30):
    """Attend tant que le verrou de la carte annonce une séance de vitesse (J1, ABBA, vitesse)."""
    while True:
        try:
            t = VERROU.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            return
        if not any(m in t for m in ("abba", "j1", "vitesse")):
            return
        print(f"séance de vitesse annoncée par le verrou ({t.strip()[:80]}) : pause {pas} s")
        time.sleep(pas)


def lire(chemin, pas=8):
    """Rend (experts triés (L, N, 4) u1, marges (L, N) f32). Refuse un fichier de taille fausse."""
    o = Path(chemin).read_bytes()
    couches, n = np.frombuffer(o, "<u4", 2)
    couches, n = int(couches), int(n)
    if len(o) != 8 + couches * n * pas or pas != CELLULE.itemsize:
        raise ValueError(f"{chemin} : taille {len(o)} incompatible avec {couches} × {n} × {pas} + 8")
    t = np.frombuffer(o, CELLULE, couches * n, 8).reshape(couches, n)
    return np.sort(t["e"], axis=2), t["m"].copy()


def bascules(ea, eb):
    """Cellules où l'ensemble des quatre experts diffère (les experts sont déjà triés)."""
    return np.any(ea != eb, axis=2)


def quantiles_bascules_py(v, fs=(0.01, 0.1, 0.5, 0.9)):
    """La définition exacte de bascules.py (indice int(f (n − 1)) du tri), pour le témoin T1."""
    s = np.sort(np.asarray(v, dtype=np.float32))
    return {str(f): float(s[min(len(s) - 1, int(f * (len(s) - 1)))]) for f in fs} if len(s) else {}


def tau_decile(m, part=0.10):
    """Le seuil qui signale `part` des cellules : la valeur triée d'indice floor(part · N)."""
    s = np.sort(m.ravel())
    return float(s[int(part * s.size)])


def grille():
    return np.logspace(-4, -1, 61)


def courbe(m, bas, taus):
    """(part des cellules sous τ, part des bascules sous τ, nombres) pour chaque τ."""
    m, bas = m.ravel(), bas.ravel()
    s_all = np.sort(m)
    s_bas = np.sort(m[bas])
    nc = np.searchsorted(s_all, taus, side="left")
    nb = np.searchsorted(s_bas, taus, side="left")
    return nc / m.size, nb / max(1, bas.sum()), nc, nb


def auc(score_positif_bas, y):
    """Aire sous la courbe ROC d'un score où une petite valeur annonce y = 1 (rangs, ex aequo moyennés)."""
    from scipy.stats import rankdata
    s = -np.asarray(score_positif_bas, dtype=np.float64).ravel()
    y = np.asarray(y, dtype=bool).ravel()
    r = rankdata(s)
    n1, n0 = y.sum(), (~y).sum()
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")
