"""Données des figures des chapitres 1 et 2 du Tome III (la question du génome, l'éclaireur), tirées des
journaux commités de mesures/genome/etat-de-l-art/ (aucun chiffre recopié à la main).

Écrit sous memoire/figures/tome3/donnees/ (virgule, fin de ligne LF, lisible par pgfplots) :
  eclaireur-borne-rd.csv         III-1.2 : les 40 points `uniforme_precis` de journaux/borne-rd.json
                                 (bits, D en %, converge 0/1), D > 1e-6 seulement (au-delà, la courbe est
                                 collée à H(V) et l'axe logarithmique ne la montre plus) ;
  eclaireur-borne-converge.csv,  les mêmes, séparés selon la convergence de Blahut-Arimoto (marques
  eclaireur-borne-nonconv.csv    pleines ou creuses) ;
  eclaireur-zeros-20b.csv,       III-2.1 : par couche, l'écart H(code) − H(valeur) (le coût du signe des
  eclaireur-zeros-120b.csv       zéros, bits par poids) des trois matrices gate, up, down ;
  eclaireur-nombres.csv          chaque nombre écrit dans une légende ou une annotation de ces figures
                                 (cle, valeur, source) ; la macro \\eclNombre{cle} le lit.

  python -I -X utf8 memoire/outils/tome3_eclaireur.py
"""
from __future__ import annotations

import csv
import json
import pathlib

RACINE = pathlib.Path(__file__).resolve().parents[2]
J = RACINE / "mesures/genome/etat-de-l-art/journaux"
D = RACINE / "memoire/figures/tome3/donnees"
NOMBRES: list[tuple[str, str, str]] = []


def nombre(cle: str, valeur: float, source: str, chiffres: int = 6) -> float:
    NOMBRES.append((cle, f"{valeur:.{chiffres}g}", source.replace(",", " ;")))  # pgfplotstable ne lit pas les guillemets
    return valeur


def ecrire(nom: str, entete: list[str], lignes: list[list]) -> None:
    with open(D / nom, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=",", lineterminator="\n")
        w.writerow(entete)
        w.writerows(lignes)


def lire(nom: str) -> dict:
    with open(J / nom, encoding="utf-8") as f:
        return json.load(f)


def corde(points: list[tuple[float, float]], x: float) -> float:
    """Interpolation linéaire sur une suite (abscisse croissante) : le partage du temps entre deux codes
    atteignables est atteignable, donc la corde reste une borne supérieure de R(D)."""
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            return y0 + (x - x0) / (x1 - x0) * (y1 - y0)
    raise ValueError(x)


def borne_rd() -> None:
    src = "mesures/genome/etat-de-l-art/journaux/borne-rd.json"
    b = lire("borne-rd.json")
    pts = [p for p in b["uniforme_precis"] if p["D"] > 1e-6]
    lignes = [[f"{p['bits']:.6f}", f"{100 * p['D']:.6e}", int(p["converge"])] for p in pts]
    ecrire("eclaireur-borne-rd.csv", ["bits", "d_pct", "converge"], lignes)
    ecrire("eclaireur-borne-converge.csv", ["bits", "d_pct"], [l[:2] for l in lignes if l[2] == 1])
    ecrire("eclaireur-borne-nonconv.csv", ["bits", "d_pct"], [l[:2] for l in lignes if l[2] == 0])
    nombre("points-uniformes", len(b["uniforme_precis"]), src)
    nombre("points-converges", b["uniforme_precis_points_converges"], src)
    nombre("H-v", b["H_v_bits"], src)
    # Le point de la frontière : le codec rANS réel sans le drapeau du codon (le témoin qui redonne F1 au
    # bit) ; le même codec sur code canonique ; l'erreur commune des deux (identique au poids près).
    zs = lire("zero-temoin-sans-drapeau.json")
    zc = lire("zero-canonique.json")
    err = zc["erreur_base_commune"]
    assert abs(err - b["frontiere_07"]["erreur"]) < 1e-9
    nombre("frontiere-bits", zs["bpp"]["niveau0_base"], "journaux/zero-temoin-sans-drapeau.json")
    nombre("canonique-bits", zc["bpp"]["niveau0_base"], "journaux/zero-canonique.json")
    nombre("frontiere-d-pct", 100 * err, "journaux/zero-canonique.json (erreur_base_commune)")
    # Les cordes : débit borné à l'erreur de la frontière, erreur bornée à son débit.
    par_d = sorted((p["D"], p["bits"]) for p in b["uniforme_precis"])
    par_r = sorted((p["bits"], p["D"]) for p in b["uniforme_precis"])
    r_a_d = corde(par_d, err)
    d_a_r = corde(par_r, zs["bpp"]["niveau0_base"])
    nombre("corde-bits-a-d", r_a_d, "calculé : corde entre deux points uniforme_precis")
    nombre("corde-d-pct-a-r", 100 * d_a_r, "calculé : corde entre deux points uniforme_precis")
    nombre("ecart-bits", zs["bpp"]["niveau0_base"] - r_a_d, "calculé")
    nombre("part-erreur", d_a_r / err, "calculé")
    lo = [p for p in b["uniforme_precis"] if not p["converge"]]
    nombre("points-nonconverges", len(lo), src)
    nombre("nonconv-bits-min", min(p["bits"] for p in lo), src)
    nombre("nonconv-bits-max", max(p["bits"] for p in lo), src)
    # Ce que la borne ne compte pas (M12 du juge ronde) : R(D) est la borne des codes sachant l'échelle ;
    # la frontière à 2,6441 bits compte ses échelles (et son contexte κ). La passe de la base frontière sur
    # les experts de P1-sorties donne le coût des échelles et H0 des seuls symboles ; contre ce H0, l'écart
    # à la borne change peu.
    fp = "mesures/genome/etat-de-l-art/passes/frontiere-lam0-damp0.01-e0_8_16_24.json"
    with open(RACINE / fp, encoding="utf-8") as f:
        pf = json.load(f)
    nombre("echelles-bits", pf["bits_lus_H0_plus_echelles"] - pf["bits_H0_sym"], fp + " (calculé : lus − H0 des symboles)")
    nombre("h0-bits", pf["bits_H0_sym"], fp)
    nombre("h0-experts", len(pf["experts"]) * len(pf["couches"]), fp + " (experts × couches)")
    nombre("ecart-bits-h0", pf["bits_H0_sym"] - r_a_d, "calculé")


def zeros() -> None:
    for m in ("20b", "120b"):
        src = f"mesures/genome/etat-de-l-art/journaux/zero-compte-{m}.json"
        z = lire(f"zero-compte-{m}.json")
        par = {}
        for t in z["par_tenseur"]:
            _, c, role = t["tenseur"].split(".")[:3]  # blk.<couche>.ffn_<rôle>_exps.weight
            role = role.replace("ffn_", "").replace("_exps", "")
            par.setdefault(int(c), {})[role] = t
        couches = sorted(par)
        assert len(couches) * 3 == z["tenseurs"] == len(z["par_tenseur"])
        ecrire(f"eclaireur-zeros-{m}.csv", ["couche", "gate", "up", "down"],
               [[c] + [f"{par[c][r]['cout_signe_des_zeros']:.6f}" for r in ("gate", "up", "down")] for c in couches])
        couts = [t["cout_signe_des_zeros"] for t in z["par_tenseur"]]
        nombre(f"{m}-tenseurs", z["tenseurs"], src)
        nombre(f"{m}-couches", len(couches), src)
        nombre(f"{m}-poids", z["poids"], src, 15)
        nombre(f"{m}-cout", z["cout_signe_des_zeros"], src)
        nombre(f"{m}-cout-min", min(couts), src)
        nombre(f"{m}-cout-max", max(couts), src)
        nombre(f"{m}-H-signe", z["H_signe_sachant_zero"], src, 12)
        nombre(f"{m}-H-signe-min", min(t["H_signe_sachant_zero"] for t in z["par_tenseur"]), src, 12)
        nombre(f"{m}-p-plus", 100 * z["p_plus0"], src)
        nombre(f"{m}-p-moins", 100 * z["p_moins0"], src)
        nombre(f"{m}-blocs-nuls", z["blocs_tout_zero"], src)
        nombre(f"{m}-blocs", z["blocs"], src, 15)


def main() -> int:
    D.mkdir(parents=True, exist_ok=True)
    borne_rd()
    zeros()
    ecrire("eclaireur-nombres.csv", ["cle", "valeur", "source"], [list(n) for n in NOMBRES])
    for c, v, _ in NOMBRES:
        print(f"{c:22s} {v}")
    print("écrit :", sorted(p.name for p in D.glob("eclaireur-*.csv")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
