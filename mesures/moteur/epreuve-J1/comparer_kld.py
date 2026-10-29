"""Juge de l'épreuve : KL(vérité ‖ fichier) et premier choix, position par position.

La vérité est soit le .npz de gptoss_numpy.py (log-probabilités f64 exactes), soit un .kld. Chaque
fichier jugé est un .kld de llama-perplexity (format relevé sur le fichier lui-même : « _logits_ »,
n_ctx, n_vocab, n_chunk, jetons, puis par position notée nv = 2⌈V/2⌉ + 4 mots u16 : f32 pas,
f32 log p min, V codes ; log p ≈ pas · code + log p min). Aucun outil d'un lot n'est importé.

Commande : python -I -X utf8 comparer_kld.py <vérité.npz|.kld> <journal.json> [--csv c.csv]
           --fichier nom=chemin.kld [--fichier …] [--fenetre 0 --positions 256:288]
"""
import argparse
import json
import struct
import sys

import numpy as np


class Kld:
    def __init__(self, chemin):
        self.f = open(chemin, "rb")
        t = self.f.read(20)
        assert t[:8] == b"_logits_", chemin
        self.n_ctx, self.V, self.n_chunk = struct.unpack("<Iii", t[8:20])
        self.jetons = np.frombuffer(self.f.read(4 * self.n_ctx * self.n_chunk), "<i4").reshape(self.n_chunk, self.n_ctx)
        self.debut = 20 + 4 * self.n_ctx * self.n_chunk
        self.nv = 2 * ((self.V + 1) // 2) + 4
        self.par_fenetre = self.n_ctx - 1 - self.n_ctx // 2

    def log_p(self, fenetre, position):
        i = fenetre * self.par_fenetre + (position - self.n_ctx // 2)
        self.f.seek(self.debut + 2 * self.nv * i)
        b = self.f.read(2 * self.nv)
        pas, lmin = struct.unpack("<ff", b[:8])
        codes = np.frombuffer(b[8:8 + 2 * self.V], "<u2").astype(np.float64)
        return float(pas) * codes + float(lmin)


def kl(lp, lq):
    p = np.exp(lp)
    return float(np.sum(p * (lp - lq)))


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("verite")
    ap.add_argument("journal")
    ap.add_argument("--csv")
    ap.add_argument("--fichier", action="append", default=[])
    ap.add_argument("--fenetre", type=int, default=0)
    ap.add_argument("--positions", default=None)
    a = ap.parse_args()

    if a.verite.endswith(".npz"):
        z = np.load(a.verite)
        pos = z["positions"].tolist()
        fen = int(z["fenetre"])
        lp_tout = z["log_p"]
        verite = {p: lp_tout[i] for i, p in enumerate(pos)}
        jetons_v = z["jetons"]
    else:
        kv = Kld(a.verite)
        fen = a.fenetre
        p0, p1 = (int(s) for s in a.positions.split(":"))
        pos = list(range(p0, p1))
        verite = {p: kv.log_p(fen, p) for p in pos}
        jetons_v = kv.jetons[fen]
    fichiers = dict(f.split("=", 1) for f in a.fichier)
    res = {"verite": a.verite, "fenetre": fen, "positions": [pos[0], pos[-1] + 1], "n": len(pos), "fichiers": {}}
    lignes = ["position,jeton_suivant," + ",".join(f"kl_{n},meme_premier_{n}" for n in fichiers)]
    par = {n: [] for n in fichiers}
    for n, c in fichiers.items():
        k = Kld(c)
        egal = bool(np.array_equal(k.jetons[fen][:len(jetons_v)], jetons_v[:k.n_ctx]))
        kls, memes = [], []
        for p in pos:
            lq = k.log_p(fen, p)
            lp = verite[p]
            kls.append(kl(lp, lq))
            memes.append(int(np.argmax(lp) == np.argmax(lq)))
        par[n] = list(zip(kls, memes))
        kls = np.array(kls)
        res["fichiers"][n] = {"chemin": c, "jetons_egaux": egal, "kl_moyenne": float(kls.mean()),
                              "kl_mediane": float(np.median(kls)), "kl_max": float(kls.max()),
                              "kl_erreur_type": float(kls.std(ddof=1) / np.sqrt(kls.size)),
                              "meme_premier_choix": float(np.mean(memes)), "n": int(kls.size)}
    for i, p in enumerate(pos):
        suiv = int(jetons_v[p + 1]) if p + 1 < len(jetons_v) else -1
        lignes.append(f"{p},{suiv}," + ",".join(f"{par[n][i][0]:.10e},{par[n][i][1]}" for n in fichiers))
    if a.csv:
        open(a.csv, "w", encoding="utf-8").write("\n".join(lignes) + "\n")
    json.dump(res, open(a.journal, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for n, r in res["fichiers"].items():
        print(f"{n:28s} KL moy {r['kl_moyenne']:.3e} méd {r['kl_mediane']:.3e} max {r['kl_max']:.3e} "
              f"premier {r['meme_premier_choix']:.3f} jetons_egaux {r['jetons_egaux']}")


if __name__ == "__main__":
    principal()
