"""Piste spectres : le plafond par rang, offert ou payé (seuil.md § 7 septies).

G_r(D) : plafond quand seules les r premières directions propres sont offertes, les p − r autres
codées comme un bruit blanc de variance égale à leur moyenne (même énergie totale). Levier payé :
N_r(b) = G_r − b · r · (m + n) / (m n), facteurs à b bits par coefficient.
Sur `valeurs-singulieres.npz` et le planté régénéré (plafond.spectres_plante) ; aucune lecture du modèle.

Utilisation : python -X utf8 plafond_rang.py [--casser] > plafond-rang.out 2> plafond-rang.log
"""
from __future__ import annotations

import commun

import csv
import os
import sys

import numpy as np

import plafond

D = plafond.D_PRINCIPAL
RANGS = (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2880)
BITS = (16, 8, 4)
SEUIL = plafond.SEUIL_LEVIER


def g_rang(sig: np.ndarray, q: int, r: int) -> float:
    lam = np.sort(sig.astype(np.float64) ** 2 / q)[::-1]
    p = lam.size
    if r >= p:
        return plafond.plafond_forme_close(lam, D)
    reste = lam[r:]
    lam2 = np.concatenate([lam[:r], np.full(p - r, reste.mean())])
    return plafond.plafond_forme_close(lam2, D)


def cout(b: int, r: int, m: int, n: int) -> float:
    return b * r * (m + n) / (m * n)


def courbe(sig, m, n):
    p, q = min(m, n), max(m, n)
    rs = [r for r in RANGS if r < p] + [p]
    return {r: g_rang(sig, q, r) for r in rs}


def meilleur(g: dict, b: int, m: int, n: int):
    nets = {r: g[r] - cout(b, r, m, n) for r in g}
    r = max(nets, key=nets.get)
    return nets[r], r


def main() -> None:
    commun.priorite_basse()
    casser = "--casser" in sys.argv
    z = np.load(os.path.join(commun.MESURES, "valeurs-singulieres.npz"))
    commun.attendre_calme()
    pl, plp = plafond.spectres_plante()
    if casser:
        pl, plp = plp, pl
        print("[cassure] planté et son permuté échangés", file=sys.stderr)

    ecr = csv.writer(sys.stdout, lineterminator="\n")
    ecr.writerow(["id", "genre", "m", "n", "r", "G_r"] + [f"N_r_{b}" for b in BITS])

    def ecrire(ident, genre, m, n, g):
        for r, v in g.items():
            ecr.writerow([ident, genre, m, n, r, f"{v:.6f}"] + [f"{v - cout(b, r, m, n):.6f}" for b in BITS])

    # --- témoins ---
    gpl, gplp = courbe(pl, 2880, 2880), courbe(plp, 2880, 2880)
    ecrire("T-plante-rang8", "temoin", 2880, 2880, gpl)
    ecrire("T-plante-rang8.perm", "temoin", 2880, 2880, gplp)
    n1, r1 = meilleur(gpl, 16, 2880, 2880)
    n2, r2 = meilleur(gplp, 16, 2880, 2880)
    t1 = n1 > SEUIL and r1 == 8
    t2 = n2 < SEUIL / 4
    print(f"T-plante-rang8 : max_r N_r(16) {n1:+.4f} à r = {r1} (attendu > {SEUIL} à r = 8) : "
          f"{'TIENT' if t1 else 'ÉCHEC'}", file=sys.stderr)
    print(f"T-plante-rang8.perm : max_r N_r(16) {n2:+.4f} à r = {r2} (attendu < {SEUIL / 4}) : "
          f"{'TIENT' if t2 else 'ÉCHEC'}", file=sys.stderr)
    print("T-plante-rang8, G_r : " + ", ".join(f"{r} : {v:.4f}" for r, v in gpl.items()), file=sys.stderr)
    sys.stdout.flush()
    if not (t1 and t2):
        print("TÉMOINS EN ÉCHEC : aucun chiffre ne sort", file=sys.stderr)
        return

    # --- l'échantillon ---
    fams: dict[str, list] = {"gate": [], "up": [], "down": [], "attention": []}
    print("", file=sys.stderr)
    for mat in commun.echantillon():
        f = "attention" if mat["role"].startswith("attn") else mat["role"]
        m, n = {"attn_q": (4096, 2880), "attn_k": (512, 2880), "attn_v": (512, 2880),
                "attn_output": (2880, 4096)}.get(mat["role"], (2880, 2880))
        gr = courbe(z["reel/" + mat["id"]], m, n)
        gp = courbe(z["perm/" + mat["id"]], m, n)
        ecrire(mat["id"], "reel", m, n, gr)
        ecrire(mat["id"] + ".perm", "perm", m, n, gp)
        p = min(m, n)
        e = gr[p] - gp[p]
        res = {"id": mat["id"], "E": e, "m": m, "n": n}
        for b in BITS:
            res[f"N{b}"], res[f"r{b}"] = meilleur(gr, b, m, n)
            res[f"P{b}"], _ = meilleur(gp, b, m, n)
        for r in (8, 64, 512):
            if r < p:
                res[f"part{r}"] = (gr[r] - gp[r]) / e
        fams[f].append(res)
        print(f"{mat['id']:22s} E {e:+.4f}  max N(16) {res['N16']:+.4f} (r {res['r16']:4d})  "
              f"N(8) {res['N8']:+.4f} (r {res['r8']:4d})  N(4) {res['N4']:+.4f} (r {res['r4']:4d})  "
              f"permuté N(16) {res['P16']:+.4f}  part r8 {res.get('part8', float('nan')):.2f} "
              f"r64 {res.get('part64', float('nan')):.2f} r512 {res.get('part512', float('nan')):.2f}",
              file=sys.stderr)
    sys.stdout.flush()
    print("", file=sys.stderr)
    tot = {b: [0.0, 0.0] for b in BITS}
    for f, l in fams.items():
        morceaux = []
        for b in BITS:
            med = float(np.median([x[f"N{b}"] for x in l]))
            medp = float(np.median([x[f"P{b}"] for x in l]))
            verdict = "LEVIER" if (med > SEUIL and medp < med / 4) else "pas de levier"
            morceaux.append(f"b {b:2d} : médiane {med:+.4f}, permuté {medp:+.4f}"
                            + (f" → {verdict}" if b == 16 else " (sensibilité)"))
        parts = "; ".join(f"r {r} : {np.median([x[f'part{r}'] for x in l if f'part{r}' in x]):.2f}"
                          for r in (8, 64, 512))
        print(f"famille {f:9s} | " + " | ".join(morceaux) + f" | part du plafond prise par les r premières : {parts}",
              file=sys.stderr)
        for x in l:
            w = x["m"] * x["n"]
            for b in BITS:
                tot[b][0] += max(x[f"N{b}"], 0.0) * w
                tot[b][1] += w
    print("échantillon, moyenne pondérée de max(0, max_r N_r(b)) : " +
          ", ".join(f"b {b} : {tot[b][0] / tot[b][1]:.4f}" for b in BITS) + " bit par poids", file=sys.stderr)


if __name__ == "__main__":
    main()
