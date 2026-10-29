"""La KL du juge, calculée par son propre code depuis les fichiers .kld (format de llama-perplexity).

Seuils : mesures/genome/construction/juge/00-seuils-declares.md, J-K (commit 1f5fe0f).
Convention (celle du lot R, R-pour-le-memoire § 2.4, redérivée ici) : P et Q décodés de leur codage
16 bits (log p_i = pas · code_i + log p_min), sans renormalisation ; par position notée,
  KL = Σ_{i : log p_i > −16} p_i (log p_i − log q_i) ;
premier choix identique : argmax de P = argmax de Q (premier indice en cas d'égalité) ;
nll de Q au jeton suivant : − log q_{suivant} (sans renormalisation, comme le juge).

  python -I -X utf8 kl_juge.py kl P.kld Q.kld --nom N            → kl-N.json, kl-N-positions.csv
  python -I -X utf8 kl_juge.py apparier N_a N_b --nom N          → apparie-N.json, apparie-N-par-fenetre.csv
      (d = KL_a − KL_b par position, depuis les deux CSV de positions)
  python -I -X utf8 kl_juge.py temoin P.kld Q.kld JUGE.json      → mon KL contre celui de `juge kl` ; cassure (Q décalé)
"""
import json
import math
import pathlib
import struct
import sys

import numpy as np

DEPOT = pathlib.Path(__file__).resolve().parents[4]
JOURNAUX = DEPOT / "mesures" / "genome" / "construction" / "juge" / "kl"


class Kld:
    def __init__(self, chemin):
        self.chemin = pathlib.Path(chemin)
        with open(self.chemin, "rb") as f:
            h = f.read(20)
        assert h[:8] == b"_logits_", chemin
        self.n_ctx, self.n_vocab, self.n_chunk = struct.unpack_from("<Iii", h, 8)
        self.nv = 2 * ((self.n_vocab + 1) // 2) + 4
        self.notees = self.n_ctx - 1 - self.n_ctx // 2
        self.jetons = np.fromfile(self.chemin, dtype="<i4", count=self.n_ctx * self.n_chunk, offset=20)
        debut = 20 + 4 * self.n_ctx * self.n_chunk
        n = self.n_chunk * self.notees
        assert self.chemin.stat().st_size == debut + 2 * self.nv * n, "taille inattendue"
        self.m = np.memmap(self.chemin, dtype="<u2", mode="r", offset=debut, shape=(n, self.nv))

    def logp(self, i0, i1):
        """log p décodés des entrées [i0, i1) (positions notées, toutes fenêtres à la suite), en f64."""
        bloc = np.asarray(self.m[i0:i1])
        tete = bloc[:, :4].copy().view("<f4").astype(np.float64)    # (n, 2) : pas, log_p_min
        codes = bloc[:, 4:4 + self.n_vocab].astype(np.float64)
        return codes * tete[:, 0:1] + tete[:, 1:2]


def kl_positions(P: Kld, Q: Kld, n_fen=None, decalage=0, paquet=24):
    assert (P.n_ctx, P.n_vocab) == (Q.n_ctx, Q.n_vocab)
    n_fen = n_fen or min(P.n_chunk, Q.n_chunk)
    assert (P.jetons[:n_fen * P.n_ctx] == Q.jetons[:n_fen * Q.n_ctx]).all(), "jetons différents"
    lignes = []
    for f in range(n_fen):
        for a in range(0, P.notees, paquet):
            b = min(a + paquet, P.notees)
            i0 = f * P.notees + a
            lp = P.logp(i0, i0 + b - a)
            j0 = min(i0 + decalage, Q.m.shape[0] - (b - a))
            lq = Q.logp(j0, j0 + b - a)
            masque = lp > -16.0
            kl = np.where(masque, np.exp(lp) * (lp - lq), 0.0).sum(axis=1)
            am_p = lp.argmax(axis=1)
            am_q = lq.argmax(axis=1)
            for r in range(b - a):
                t = P.n_ctx // 2 + a + r
                suiv = int(P.jetons[f * P.n_ctx + t + 1])
                lignes.append((f, t, float(kl[r]), int(am_p[r] == am_q[r]), float(-lq[r, suiv]), float(-lp[r, suiv])))
    return lignes


def resume(lignes, n_fen):
    kl = np.array([l[2] for l in lignes])
    mp = np.array([l[3] for l in lignes])
    nq = np.array([l[4] for l in lignes])
    np_ = np.array([l[5] for l in lignes])
    fen = np.array([l[0] for l in lignes])
    par_f = np.array([kl[fen == f].mean() for f in range(n_fen)])
    n = len(kl)
    p = mp.mean()
    z = 1.96
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    demi = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return {"n": n, "kl_moyenne": float(kl.mean()), "kl_incertitude": float(math.sqrt(((kl ** 2).mean() - kl.mean() ** 2) / (n - 1))),
            "kl_sigma_par_fenetres": float(par_f.std(ddof=1) / math.sqrt(n_fen)), "kl_par_fenetre": par_f.tolist(),
            "mediane": float(np.median(kl)), "q90": float(np.quantile(kl, 0.90)), "q99": float(np.quantile(kl, 0.99)),
            "q999": float(np.quantile(kl, 0.999)), "max": float(kl.max()),
            "meme_premier": float(p), "meme_premier_wilson95": [centre - demi, centre + demi],
            "ppl_q": float(math.exp(nq.mean())), "ppl_p": float(math.exp(np_.mean()))}


def ecrire_positions(nom, lignes):
    JOURNAUX.mkdir(parents=True, exist_ok=True)
    with open(JOURNAUX / f"kl-{nom}-positions.csv", "w", encoding="utf-8") as f:
        f.write("fenetre,position,kl,meme_premier,nll_q,nll_p\n")
        for l in lignes:
            f.write(f"{l[0]},{l[1]},{l[2]:.12e},{l[3]},{l[4]:.9f},{l[5]:.9f}\n")


def lire_positions(nom):
    t = np.loadtxt(JOURNAUX / f"kl-{nom}-positions.csv", delimiter=",", skiprows=1)
    return t


def cmd_kl(p, q, nom):
    P, Q = Kld(p), Kld(q)
    n_fen = min(P.n_chunk, Q.n_chunk)
    lignes = kl_positions(P, Q, n_fen)
    r = resume(lignes, n_fen)
    r.update({"outil": "kl_juge.py kl", "p": str(p).replace("\\", "/"), "q": str(q).replace("\\", "/"), "fenetres": n_fen})
    ecrire_positions(nom, lignes)
    (JOURNAUX / f"kl-{nom}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(nom, {k: v for k, v in r.items() if k != "kl_par_fenetre"})
    return r


def cmd_apparier(na, nb, nom):
    a, b = lire_positions(na), lire_positions(nb)
    assert (a[:, :2] == b[:, :2]).all()
    d = a[:, 2] - b[:, 2]
    fen = a[:, 0].astype(int)
    nf = fen.max() + 1
    par_f = np.array([d[fen == f].mean() for f in range(nf)])
    dm = d.mean()
    s_f = par_f.std(ddof=1) / math.sqrt(nf)
    s_n = d.std(ddof=1) / math.sqrt(len(d))
    pm = a[:, 3] - b[:, 3]
    pm_f = np.array([pm[fen == f].mean() for f in range(nf)])
    r = {"outil": "kl_juge.py apparier", "a": na, "b": nb, "n": int(len(d)), "fenetres": int(nf),
         "kl_a": float(a[:, 2].mean()), "kl_b": float(b[:, 2].mean()),
         "d_moyenne": float(dm), "sigma_naif": float(s_n), "sigma_par_fenetres": float(s_f), "d_sur_sigma": float(dm / s_f),
         "d_plus_2sigma": float(dm + 2 * s_f), "d_moins_2sigma": float(dm - 2 * s_f),
         "verdict": ("a meilleure" if dm + 2 * s_f < 0 else ("b meilleure" if dm - 2 * s_f > 0 else "égales")),
         "positions_a_moins": int((d < 0).sum()), "fenetres_a_moins": int((par_f < 0).sum()), "d_par_fenetre": par_f.tolist(),
         "premier_choix_a_moins_b": float(pm.mean()), "premier_choix_sigma_par_fenetres": float(pm_f.std(ddof=1) / math.sqrt(nf))}
    with open(JOURNAUX / f"apparie-{nom}-par-fenetre.csv", "w", encoding="utf-8") as f:
        f.write("fenetre,d\n")
        for i, v in enumerate(par_f):
            f.write(f"{i},{v:.9f}\n")
    (JOURNAUX / f"apparie-{nom}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(nom, {k: v for k, v in r.items() if k != "d_par_fenetre"})
    return r


def cmd_temoin(p, q, juge_json, nom):
    P, Q = Kld(p), Kld(q)
    n_fen = min(P.n_chunk, Q.n_chunk)
    mien = resume(kl_positions(P, Q, n_fen), n_fen)["kl_moyenne"]
    j = json.loads(pathlib.Path(juge_json).read_text(encoding="utf-8"))
    sien = j.get("kl_moyenne") or j.get("resume", {}).get("kl_moyenne")
    casse = resume(kl_positions(P, Q, n_fen, decalage=1), n_fen)["kl_moyenne"]
    r = {"p": str(p), "q": str(q), "kl_juge_py": mien, "kl_juge_kl": sien, "ecart_relatif": abs(mien - sien) / max(abs(sien), 1e-300),
         "temoin_tient": abs(mien - sien) <= 1e-6 * abs(sien), "kl_q_decale_d_une_position": casse,
         "cassure_tombe": abs(casse - mien) > 10 * abs(mien)}
    (JOURNAUX / f"temoin-{nom}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(r)
    return r


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    JOURNAUX.mkdir(parents=True, exist_ok=True)
    a = sys.argv[1:]
    nom = a[a.index("--nom") + 1] if "--nom" in a else "sans-nom"
    if a and a[0] == "kl":
        cmd_kl(a[1], a[2], nom)
    elif a and a[0] == "apparier":
        cmd_apparier(a[1], a[2], nom)
    elif a and a[0] == "temoin":
        cmd_temoin(a[1], a[2], a[3], nom)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
