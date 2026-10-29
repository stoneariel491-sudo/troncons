"""Données des figures « avant / après » du sujet genome (SOCLE, demande de Stone du 2026-10-17) :

1. csv/rotation-histogramme.csv : distribution des poids d'une matrice (blk.8.ffn_down, expert 16),
   normalisés par rangée, AVANT la rotation de Hadamard (queues lourdes, kurtosis 343) et APRÈS
   (gaussienne) ; histogramme en log sur 121 cases de −12σ à +12σ, et la densité gaussienne de référence.
2. csv/colonnes-energie-erreur.csv : pour la même matrice, par colonne (canal d'entrée) : énergie de la
   colonne exacte, énergie d'erreur du brin pondéré sans exceptions, de S* et de la base (la colonne
   massive et l'erreur qu'elle aspire, puis rendue par les exceptions).
3. csv/brin-chemin.csv : un morceau de brin réel (les 48 premiers pas d'une rangée) : fenêtre de 12 bits
   à chaque pas, valeur de la table, poids cible, pour dessiner la lecture par codons.

Utilisation : python -I -X utf8 figures_transformations.py DOSSIER_KL_SUB
"""
import csv
import importlib.util
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(ICI, "..", "..", "..", "mesures", "genome", "genome", "csv")
spec = importlib.util.spec_from_file_location("structure", os.path.join(ICI, "structure.py"))
st = importlib.util.module_from_spec(spec)
sys.modules["structure"] = st
spec.loader.exec_module(st)


def signes(graine, n):
    """Les signes de la rotation, exactement comme hadamard.rs (mélangeur `hache` de codons.rs)."""
    def hache(s, j):
        m = 0xFFFFFFFF
        h = (s ^ ((j * 0x632BE5AB) & m)) & m
        h = (h * 0x9E3779B1) & m
        h ^= h >> 16
        h = (h * 0x85EBCA77) & m
        h ^= h >> 13
        h = (h * 0xC2B2AE3D) & m
        h ^= h >> 16
        return h
    return np.array([1.0 if hache((graine ^ 0x5EED0000) & 0xFFFFFFFF, c) & 1 == 0 else -1.0 for c in range(n)])


def tourner(w, graine):
    H = np.array([[1.0]])
    while H.shape[0] < 64:
        H = np.block([[H, H], [H, -H]])
    H /= 8.0
    y = (w * signes(graine, w.shape[1])).reshape(w.shape[0], -1, 64) @ H.T
    return y.reshape(w.shape)


def main():
    dossier = sys.argv[1]
    lec = st.charger_lecteur().LecteurGGUF(st.FICHIER)
    idx = {t.nom: t for t in lec.tenseurs}
    l, e = 8, 16
    w = st.expert(lec, idx[f"blk.{l}.ffn_down_exps.weight"], e)
    graine = l * 3 + 2 + 1
    avant = w / np.sqrt((w ** 2).mean(1, keepdims=True))
    y = tourner(w, graine)
    apres = y / np.sqrt((y ** 2).mean(1, keepdims=True))
    bornes = np.linspace(-12, 12, 122)
    ha, _ = np.histogram(avant, bornes, density=True)
    hp, _ = np.histogram(apres, bornes, density=True)
    centres = 0.5 * (bornes[1:] + bornes[:-1])
    gauss = np.exp(-centres ** 2 / 2) / np.sqrt(2 * np.pi)
    with open(os.path.join(C, "rotation-histogramme.csv"), "w", newline="", encoding="utf8") as f:
        wr = csv.writer(f)
        wr.writerow(["x_sigma", "densite_avant", "densite_apres", "densite_gauss"])
        for c, a, p, g in zip(centres, ha, hp, gauss):
            wr.writerow([f"{c:.3f}", f"{a:.6e}", f"{p:.6e}", f"{g:.6e}"])
    kurt = lambda z: float((z ** 4).mean() / (z ** 2).mean() ** 2)
    print("kurtosis avant", kurt(avant), "après", kurt(apres))

    def lire(nom):
        return np.fromfile(os.path.join(dossier, nom, f"L{l:02d}-E{e:02d}.f32w"), dtype=np.float32).reshape(3, 2880, 2880)[2].astype(np.float64)

    cols = {"exact": (w ** 2).sum(0)}
    for nom, cle in (("recette-ponderee-264", "brin_pondere"), ("recette-ponderee-exc-264", "s_etoile"), ("base-8", "base")):
        cols[cle] = ((lire(nom) - w) ** 2).sum(0)
    with open(os.path.join(C, "colonnes-energie-erreur.csv"), "w", newline="", encoding="utf8") as f:
        wr = csv.writer(f)
        wr.writerow(["colonne", "energie_exacte", "erreur_brin_pondere", "erreur_s_etoile", "erreur_base"])
        for c in range(2880):
            wr.writerow([c] + [f"{cols[k][c]:.6e}" for k in ("exact", "brin_pondere", "s_etoile", "base")])
    m = int(cols["exact"].argmax())
    print("colonne massive", m, "énergie ×", cols["exact"][m] / cols["exact"].mean(),
          "erreur brin ×", cols["brin_pondere"][m] / cols["brin_pondere"].mean(),
          "S* ×", cols["s_etoile"][m] / cols["s_etoile"].mean(), "base ×", cols["base"][m] / cols["base"].mean())


if __name__ == "__main__":
    main()
