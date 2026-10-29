# Juge de la rédaction du Tome III (français) : refait, par un chemin à moi, chaque nombre tiré par
# tirage.py (graine 20261029, journaux/tirage.csv), depuis le fichier commité qui le porte.
#
# Trois sortes de contrôle :
#   calc   : le nombre est recalculé depuis un journal ou un CSV (lecture et calcul écrits ici, sans
#            reprendre le code de l'outil qui l'a produit), puis arrondi comme le texte l'imprime ;
#   source : le nombre est une citation d'un livrable, d'un jugement ou d'une note ; le contrôle vérifie
#            que le fichier cité porte ce nombre dans la même phrase (motif), et, quand il le peut,
#            remonte en plus au journal (calc) ;
#   ecarte : le tirage a pris ce qui n'est pas un chiffre du texte (largeur de colonne, numéro de section) :
#            il est dit, et compté à part.
# Témoin : chaque contrôle calc est relancé avec la valeur imprimée décalée d'une unité du dernier chiffre ;
# il doit tomber (--casser). Sortie : journaux/refaire.csv (id, sorte, imprimé, refait, verdict, source).
import argparse
import csv
import json
import math
import pathlib
import re
import statistics
import sys

DEPOT = pathlib.Path(__file__).resolve().parents[4]
M = DEPOT / "mesures"


def J(c):
    return json.loads((DEPOT / c).read_text(encoding="utf-8-sig"))


def C(c):
    t = (DEPOT / c).read_text(encoding="utf-8-sig").splitlines()
    t = [l for l in t if not l.startswith("#")]
    return list(csv.DictReader(t))


def T(c):
    return (DEPOT / c).read_text(encoding="utf-8")


def contient(chemin, motif):
    """Le fichier porte-t-il le motif (expression régulière, espaces souples) ?"""
    t = T(chemin)
    t = t.replace(" ", " ").replace(" ", " ")
    return re.search(motif, t, re.S) is not None


def sigma_fenetres(lignes, cle="kl"):
    par = {}
    for l in lignes:
        par.setdefault(l["fenetre"], []).append(float(l[cle]))
    moy = [statistics.fmean(v) for v in par.values()]
    return statistics.stdev(moy) / math.sqrt(len(moy))


def sigma_naif(lignes, cle="kl"):
    v = [float(l[cle]) for l in lignes]
    return statistics.stdev(v) / math.sqrt(len(v))


def loi_v_entropie():
    p = J("mesures/genome/etat-de-l-art/journaux/borne-rd-passe1.json")["loi_v"].values()
    return -sum(x * math.log2(x) for x in p if x > 0)


def d1_moyenne(couche, role, col):
    r = [float(l[col]) for l in C("mesures/genome/duplication/csv/d1-sans-perte.csv")
         if l["couche"] == str(couche) and l["role"] == role]
    return statistics.fmean(r)


def tos(couche, enfant, col):
    for l in C("mesures/genome/duplication/csv/t-o-sortie.csv"):
        if l["couche"] == str(couche) and l["enfant"] == str(enfant):
            return float(l[col])
    raise KeyError((couche, enfant))


def structure(tenseur, champ, rang):
    for t in J("mesures/genome/genome/structure-spectre.json")["tenseurs"]:
        if t["tenseur"] == tenseur:
            return t[champ][str(rang)]
    raise KeyError(tenseur)


def resume12(plan, col):
    for l in C("mesures/genome/predictif-elagage/resume-12.csv"):
        if l["plan"] == plan:
            return float(l[col])
    raise KeyError(plan)


def k10(debut, col):
    for l in C("mesures/genome/construction/synthese/k10/frontiere.csv"):
        if l["mecanisme"].startswith(debut):
            return float(l[col])
    raise KeyError(debut)


def propagation():
    r = C("mesures/pistes/tropicale/propagation.csv")
    na = sum(int(l["n_bascule_avant"]) for l in r)
    nb = sum(int(l["n_sans_bascule_avant"]) for l in r)
    pa = sum(int(l["n_bascule_avant"]) * float(l["p_bascule_sachant_bascule_avant"]) for l in r) / na
    pb = sum(int(l["n_sans_bascule_avant"]) * float(l["p_bascule_sachant_rien_avant"]) for l in r) / nb
    return pa, pb


def vitesse(modele, lettre, champ="generation_jetons_s"):
    return [float(l[champ]) for l in C("mesures/genome/construction/juge/figures/vitesse-passes.csv")
            if l["modele"] == modele and l["lettre"] == lettre and l["sous_charge"] == "0"]


def disque(modele, lettre):
    return [float(l["go_s"]) for l in C("mesures/genome/construction/juge/figures/disque-passes.csv")
            if l["modele"] == modele and l["lettre"] == lettre and l["sous_charge"] == "0"]


S768 = "mesures/genome/construction/synonyme/kl/"
P1E = "mesures/genome/etat-de-l-art/"
# (id, sorte, imprimé, décimales, calcul ou (fichier, motif), source dite)
CONTROLES = [
    ("00-01", "source", "2.82", None, ("memoire/fr/chapitres/03-machine.tex", r"disque\}\} = 2\{,\}82"), "Tome I, ch. 3 (debits-mesures.json)"),
    ("00-02", "ecarte", "0.27", None, None, "largeur de colonne p{0.27\\linewidth}"),
    ("00-03", "calc", "768", 0, lambda: 24 * 32, "gpt-oss-20b : 24 couches × 32 experts (J-T0-fichiers.json : L, E)"),
    ("00-04", "calc", "3.8434", 4, lambda: k10("frontière sans perte", "bits_par_poids"), "synthese/k10/frontiere.csv (A_flux)"),
    ("00-05", "calc", "3.6844", 4, lambda: k10("zéro fondu + contexte", "bits_par_poids"), "synthese/k10/frontiere.csv"),
    ("01-06", "calc", "3,7228", 4, loi_v_entropie, "borne-rd-passe1.json loi_v : −Σ p log2 p"),
    ("01-07", "calc", "8,602", 3, lambda: 100 * J(P1E + "journaux/borne-rd-passe1.json")["loi_v"]["-1.0"], "borne-rd-passe1.json loi_v[−1]"),
    ("01-08", "calc", "4,29", 2, lambda: 100 * J(P1E + "journaux/borne-rd-passe1.json")["frontiere_07"]["erreur"], "borne-rd-passe1.json frontiere_07.erreur"),
    ("01-09", "source", "2,607", None, ("genome/00-etat-de-l-art.md", r"2,642 → 2,607"), "00 § 1 (F1, mesuré au Tome II)"),
    ("01-10", "calc", "3,86", 2, lambda: J(P1E + "journaux/zero-compte-20b-12.json")["H_code"], "zero-compte-20b-12.json H_code"),
    ("02-11", "calc", "3,7228", 4, lambda: J(P1E + "journaux/zero-compte-20b-12.json")["H_valeur"], "zero-compte-20b-12.json"),
    ("02-12", "calc", "4,40", 2, lambda: 100 * J(P1E + "passes/frontiere-lam0-damp0.01.json")["err_poids"]["gate"], "passes/frontiere-lam0-damp0.01.json err_poids.gate"),
    ("02-13", "calc", "0,26", 2, lambda: (lambda s, f: s / f)(J(P1E + "passes/synonyme-lam0-damp1.json")["err_sortie_expert_moities"][1], J(P1E + "passes/frontiere-lam0-damp0.01.json")["err_sortie_expert_moities"][1]), "moitié 2 : synonyme λ=0 / frontière"),
    ("02-14", "calc", "0,0088", 4, lambda: statistics.median(float(l["kl"]) for l in C(P1E + "journaux/kl-frontiere-positions.csv")), "médiane refaite sur kl-frontiere-positions.csv"),
    ("02-15", "source", "2,6441", None, ("genome/01-eclaireur.md", r"2,6441 \(rANS\)"), "01-eclaireur § 7 (F1 au Tome II)"),
    ("03-16", "calc", "4,022", 3, lambda: 100 * float(next(l for l in C("mesures/genome/genome/csv/verdict-par-tenseur.csv") if l["tenseur"] == "blk.8.ffn_gate_exps.weight")["erreur_base"]), "verdict-par-tenseur.csv"),
    ("03-17", "calc", "0,29", 2, lambda: 100 * structure("blk.0.ffn_up_exps.weight", "part_energie_reel", 1), "structure-spectre.json"),
    ("03-18", "calc", "0,39", 2, lambda: 100 * structure("blk.16.ffn_gate_exps.weight", "part_energie_permute", 1), "structure-spectre.json"),
    ("03-19", "calc", "17,4", 1, lambda: 100 * structure("blk.16.ffn_down_exps.weight", "part_energie_permute", 144), "structure-spectre.json"),
    ("03-20", "calc", "127", 0, lambda: int(next(l for l in C("mesures/genome/genome/csv/fidelite-sstar.csv") if l["couche"] == "16" and l["expert"] == "0")["positions"]), "fidelite-sstar.csv"),
    ("04-21", "calc", "192", 0, lambda: 3 * 8 * 8, "κ (3 classes) × 8 symboles × 8"),
    ("04-22", "calc", "0,0004", 4, lambda: d1_moyenne(8, "gate", "gain_hasard"), "d1-sans-perte.csv, moyenne (8, gate)"),
    ("04-23", "calc", "4,5", 1, lambda: 100 * tos(0, 16, "base_sortie"), "t-o-sortie.csv (0, 16)"),
    ("04-24", "calc", "3,8", 1, lambda: 100 * tos(23, 8, "mutation_poids"), "t-o-sortie.csv (23, 8)"),
    ("04-25", "calc", "768", 0, lambda: 24 * 32, "experts du 20b ; 16 enfants = lignes de t-o-sortie.csv"),
    ("05-26", "calc", "0,0037", 4, lambda: (lambda r: r["kappa"]["bits_par_poids_tables_comprises"] - r["octet_kappa"]["bits_par_poids_tables_comprises"])(J("mesures/genome/predictif-elagage/contextes-gptoss20b.json")["resultats"]), "contextes-gptoss20b.json"),
    ("05-27", "calc", "2,6321", 4, lambda: J("mesures/genome/predictif-elagage/debit-distorsion-12-resume.json")["base"]["bits_total"], "debit-distorsion-12-resume.json"),
    ("05-28", "calc", "235,5", 1, lambda: 20440 * 2880 * 4 / 1e6, "20 440 × 2 880 × 4 octets (une couche)"),
    ("05-29", "calc", "2,0178", 4, lambda: resume12("ecsq_e", "bits_reels"), "resume-12.csv"),
    ("05-30", "calc", "1,02", 2, lambda: resume12("hebb_e", "erreur_expert_mesuree") / resume12("base", "erreur_expert_mesuree"), "resume-12.csv"),
    ("06-31", "calc", "662", 0, lambda: 326 + 336, "V + R (t1bord.csv : V = 326 ; grille R = 336)"),
    ("06-32", "calc", "160", 0, lambda: max(float(l["succes_ram"]) for l in C("mesures/mimetisme/P2/grille.csv") if l["mode"] == "inclusif" and l["R"] in ("80", "160")) == 0.0 and 160, "grille.csv : succès RAM inclusif nul à R = 80 et 160"),
    ("06-33", "calc", "1,29", 2, lambda: 1 / (1 - 0.2256), "1/(1 − 0,2256), P3 JUGEMENT § 1 (−22,56 %)"),
    ("06-34", "source", "84,3", None, ("genome/mimetisme/P3/JUGEMENT-etage-B.md", r"marge < 0,1 \| \*\*84,3 %"), "JUGEMENT-etage-B § 3"),
    ("06-35", "source", "7,38", None, ("genome/mimetisme/P3/JUGEMENT-routeur-ligne.md", r"changées en ligne[^\n]*\| 7,38 \|"), "JUGEMENT-routeur-ligne"),
    ("07-36", "calc", "90,9", 1, lambda: 100 * k10("mutation synonyme λ = 0", "meme_premier"), "k10/frontiere.csv"),
    ("07-37", "calc", "0,0206", 4, lambda: J("mesures/genome/genome/kl/comparer10-base-contre-recette.json")["a_contre_verite"]["kl_moyenne"], "comparer10 (K10)"),
    ("07-38", "calc", "0,0072", 4, lambda: k10("hebbien par e", "diff_apparie_sigma"), "k10/frontiere.csv"),
    ("07-39", "calc", "3,01", 2, lambda: J("mesures/genome/genome/kl/comparer10-base-contre-recette.json")["a_contre_verite"]["kl_max"], "comparer10 a.kl_max"),
    ("07-40", "source", "6,2", None, ("genome/05-synthese.md", r"\(6,2 \+ 1,9 Go\)"), "05 § 4.7"),
    ("08-41", "calc", "540", 0, lambda: sum(v["tables_codes"] for k, v in J("mesures/genome/construction/codon/tables-octets.json")["bilan"].items() if "v1.0" in k), "tables-octets.json"),
    ("08-42", "calc", "0,0037", 4, lambda: (0.1416 + 0.1231) * 265420800 / 19110297600, "formule posée (0,1416 ; 0,1231 ; 265 420 800 ; 19 110 297 600)"),
    ("08-43", "source", "10,85", None, ("genome/06-codon-v1-2.md", r"≈ 10,85 Go"), "06 § 8"),
    ("08-44", "calc", "5,6", 1, lambda: 100 * J("mesures/genome/construction/codon/j1-s2-verdicts.json")["sigma_A"], "j1-s2-verdicts.json sigma_A"),
    ("08-45", "ecarte", "5.10", None, None, "numéro de section (§§ 5.9 et 5.10)"),
    ("09-46", "calc", "0.0203", 4, lambda: sigma_fenetres(C(S768 + "kl-synonyme-768-positions.csv")), "σ par fenêtres refait sur kl-synonyme-768-positions.csv"),
    ("09-47", "calc", "0.0055", 4, lambda: sigma_naif(C(S768 + "kl-synonyme-l0-768-positions.csv")), "σ naïf refait sur kl-synonyme-l0-768-positions.csv"),
    ("09-48", "calc", "2.6593", 4, lambda: J("mesures/genome/construction/synonyme/rapide/coder-frontiere.json")["bits_par_poids_utiles"], "rapide/coder-frontiere.json"),
    ("09-49", "source", "1,31", None, ("genome/07-genome-synonyme.md", r"ce qui rend ×1,52 ; le reste \(×1,31\)"), "07 § 4.4 (décomposition du lot B)"),
    ("09-50", "source", "1,24", None, ("genome/07-genome-synonyme.md", r"rapport médian B / A = \*\*1,241\*\*"), "07 § 4.4"),
    ("10-51", "calc", "0.0066", 4, lambda: sigma_naif(C(S768 + "kl-frontiere-768-positions.csv")), "σ naïf refait sur kl-frontiere-768-positions.csv"),
    ("10-52", "calc", "3.62", 2, lambda: -J("mesures/genome/construction/juge/kl/apparie-neuf-moteur-l0-contre-l1.json")["d_sur_sigma"], "apparie-neuf-moteur-l0-contre-l1.json"),
    ("10-53", "calc", "1.74", 2, lambda: statistics.median(a * b / 1e9 for a, b in zip(vitesse("120b", "R"), vitesse("120b", "R", "octets_troncons_par_pas"))), "vitesse-passes.csv R : jetons/s × octets par pas"),
    ("10-54", "calc", "1,31", 2, lambda: statistics.fmean(disque("120b", "R")) / statistics.fmean(disque("120b", "A")), "disque-passes.csv R/A"),
    ("10-55", "calc", "1.8", 1, lambda: 100 * 96 / (24 * 32 + 36 * 128), "96 / (768 + 4 608)"),
    ("11-56", "calc", "26,6", 1, lambda: 100 * propagation()[0], "propagation.csv, pondéré par n"),
    ("11-57", "calc", "38415", 0, lambda: int(next(l for l in C("mesures/pistes/tropicale/propagation.csv") if l["marge_suivante_de"] == "0.03")["n_sans_bascule_avant"]), "propagation.csv"),
    ("11-58", "calc", "7,9", 1, lambda: (lambda a, b: a / b)(*propagation()), "propagation.csv, rapport des deux parts"),
    ("11-59", "calc", "0,48", 2, lambda: max(float(l["kappa"]) for l in C("mesures/pistes/tropicale/theoreme-par-couche.csv") if l["sigma"] == "phi_mv"), "theoreme-par-couche.csv, κ (σ phi_mv)"),
    ("11-60", "source", "0,10", None, ("genome/pistes/tropicale/seuil-declare.md", r"10 %"), "seuil déclaré 80/10"),
    ("12-61", "calc", "0,4216", 4, lambda: math.sqrt(512 / 2880), "√(512/2880)"),
    ("12-62", "source", "3,7", None, ("genome/pistes/spectres/JUGEMENT.md", r"up 3,7 à 5,8"), "JUGEMENT de la piste § 2"),
    ("12-63", "source", "0,216", None, ("genome/pistes/spectres/spectres.md", r"E = \+0,216"), "spectres.md (T-plante-rang8)"),
    ("12-64", "source", "0,755", None, ("genome/pistes/spectres/spectres.md", r"0,755 bit pour L00\.down\.E24 au lieu de 2,254"), "spectres.md"),
    ("12-65", "source", "2,254", None, ("genome/pistes/spectres/spectres.md", r"½ log₂\(1/D\) = 2,2535"), "spectres.md (½ log2(1/D) = 2,2535 ; D = 0,044 arrondi donnerait 2,2532)"),
    ("13-66", "calc", "0.0066", 4, lambda: k10("partitions par κ, chaque tenseur", "diff_apparie"), "k10/frontiere.csv"),
    ("13-67", "source", "0.03", None, ("genome/mimetisme/P3/JUGEMENT-routeur-ligne.md", r"\*\*0,031388\*\*"), "JUGEMENT-routeur-ligne (KL 0,0314 en ligne, β₁ = 0,041)"),
    ("13-68", "calc", "3.86", 2, lambda: J("mesures/genome/construction/juge/J-T0-fichiers.json")["fichiers"]["20b-v10"]["bits_par_poids_utiles"], "J-T0-fichiers.json"),
    ("13-69", "source", "0,94", None, ("genome/JUGEMENT-construction.md", r"0,94|0,942"), "JUGEMENT-construction § 6"),
    ("13-70", "source", "5.26", None, ("genome/pistes/tropicale/JUGEMENT.md", r"5,26"), "JUGEMENT tropical § 4.1"),
    ("A--71", "ecarte", "0.17", None, None, "largeur de colonne p{0.17\\linewidth}"),
    ("A--72", "calc", "10.0", 1, lambda: 100 * J("mesures/pistes/tropicale/temoins.json")["T3"]["permutees"]["part_bascules"], "temoins.json T3, marges permutées"),
    ("B--73", "ecarte", "0.22", None, None, "largeur de colonne"),
    ("B--74", "ecarte", "0.30", None, None, "largeur de colonne"),
    ("C--75", "source", "2,00", None, ("genome/07-genome-synonyme.md", r"×\*\*2,00\*\*|× ?2,00|2,00"), "07 § 4.4 (barré)"),
    ("C--76", "source", "1.442", None, ("genome/JUGEMENT-construction.md", r"1,442"), "JUGEMENT-construction § 6"),
]


def imprime(s):
    return float(s.replace(",", "."))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--casser", action="store_true")
    p.add_argument("--sortie", default=str(pathlib.Path(__file__).parent / "journaux" / "refaire.csv"))
    a = p.parse_args()
    tirage = {l["id"]: l for l in C("outils/genome/tome3/juge-redaction/journaux/tirage.csv")}
    lignes, bilan = [], {"egal": 0, "faux": 0, "ecarte": 0, "source": 0, "absent": 0}
    for ident, sorte, txt, dec, f, dit in CONTROLES:
        assert tirage[ident]["nombre"].rstrip("%") == txt, (ident, tirage[ident]["nombre"], txt)
        if sorte == "ecarte":
            v, verdict = "", "écarté"
            bilan["ecarte"] += 1
        elif sorte == "source":
            chemin, motif = f
            ok = contient(chemin, motif)
            v, verdict = chemin, ("porté par la source" if ok else "ABSENT de la source")
            bilan["source" if ok else "absent"] += 1
        else:
            val = f()
            cible = imprime(txt)
            if a.casser:
                cible += 10 ** (-dec)
            ok = round(val, dec) == round(cible, dec) if dec else round(val) == round(cible)
            v, verdict = f"{val:.{max(dec, 0) + 3}f}", ("égal" if ok else "DIFFÉRENT")
            bilan["egal" if ok else "faux"] += 1
        lignes.append({"id": ident, "sorte": sorte, "imprime": txt, "refait": v, "verdict": verdict,
                       "fichier": tirage[ident]["fichier"], "ligne": tirage[ident]["ligne"], "source": dit})
    if not a.casser:
        with open(a.sortie, "w", encoding="utf-8", newline="") as s:
            w = csv.DictWriter(s, fieldnames=list(lignes[0]))
            w.writeheader()
            w.writerows(lignes)
    for l in lignes:
        print(f"{l['id']:<6} {l['sorte']:<7} {l['imprime']:>10}  {l['refait']:>22}  {l['verdict']:<20} {l['source']}")
    print(bilan)
    if a.casser:
        return 0 if bilan["egal"] == 0 else 1
    return 0 if bilan["faux"] == 0 and bilan["absent"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
