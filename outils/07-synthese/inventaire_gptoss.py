"""Inventaire local des fichiers gpt-oss MXFP4, par lecture de leur en-tête GGUF.

Rôle dans l'étude 07 : refaire par un second chemin (le fichier sur le disque de
la machine, et non l'en-tête distant lu par l'étude 06) les grandeurs dont dépend
l'équation du jeton :
  A  = octets toujours lus par jeton (tout sauf les experts routés et la table
       d'enchâssement, dont une seule ligne est lue) ;
  R  = octets d'experts routés lus par jeton = (k / E) x octets de tous les experts ;
  e  = octets d'un expert (ses trois matrices et leurs biais) ;
  la taille contiguë d'une matrice d'un expert dans le fichier (l'expert est la
  dimension la plus lente du tenseur, donc chaque tranche est d'un seul tenant).

Témoin : la fin du dernier tenseur, alignée, doit tomber sur la taille du fichier
(à l'alignement près). Cassure : --casser ajoute un tenseur fictif ; le témoin doit
alors échouer.

Utilisation :
  python -I -X utf8 outils/07-synthese/inventaire_gptoss.py [--casser] > journal.json
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
LECTEUR = os.path.join(ICI, "..", "03-entropie", "gguf_lecture.py")

FICHIERS = {
    "gpt-oss-20b": "~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf",
    "gpt-oss-120b": "~/dev/modeles/gguf/gpt-oss-120b-MXFP4.gguf",
}


def charger_lecteur():
    spec = importlib.util.spec_from_file_location("gguf_lecture", LECTEUR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gguf_lecture"] = mod  # dataclass exige un module inscrit
    spec.loader.exec_module(mod)
    return mod


def inventaire(mod, nom: str, chemin: str, casser: bool) -> dict:
    lec = mod.LecteurGGUF(chemin)
    arch = lec.meta.get("general.architecture", "?")
    E = int(lec.meta[f"{arch}.expert_count"])
    k = int(lec.meta[f"{arch}.expert_used_count"])
    L = int(lec.meta[f"{arch}.block_count"])

    tenseurs = list(lec.tenseurs)
    taille = os.path.getsize(chemin)
    fin = max(t.decalage + t.nb_octets for t in tenseurs)
    if casser:
        fin += 4096  # tenseur fictif de 4 Kio : le témoin doit tomber
    align = int(lec.meta.get("general.alignment", 32))
    temoin_ok = taille - align < fin <= taille

    experts = [t for t in tenseurs if "_exps" in t.nom]
    embd = [t for t in tenseurs if t.nom.startswith("token_embd")]
    autres = [t for t in tenseurs if t not in experts and t not in embd]

    oct_experts = sum(t.nb_octets for t in experts)
    oct_autres = sum(t.nb_octets for t in autres)
    oct_embd = sum(t.nb_octets for t in embd)

    # Tranches contiguës : une matrice d'un expert = octets du tenseur / E.
    matrices = sorted({t.nb_octets // E for t in experts if t.nom.endswith(".weight")})
    biais = sorted({t.nb_octets // E for t in experts if t.nom.endswith(".bias")})
    e = oct_experts / (E * L)

    par_type: dict[str, int] = {}
    for t in autres:
        par_type[t.nom_type] = par_type.get(t.nom_type, 0) + t.nb_octets

    return {
        "modele": nom,
        "fichier": chemin,
        "taille_fichier_octets": taille,
        "architecture": arch,
        "couches": L,
        "experts_par_couche_E": E,
        "experts_actifs_k": k,
        "temoin_fin_du_dernier_tenseur": {"fin": fin, "taille": taille,
                                           "alignement": align, "tient": temoin_ok},
        "A_octets_toujours_lus": oct_autres,
        "A_par_type": par_type,
        "R_octets_experts_par_jeton": oct_experts * k / E,
        "octets_tous_experts": oct_experts,
        "octets_table_enchassement": oct_embd,
        "e_octets_par_expert": e,
        "matrice_contigue_par_expert_octets": matrices,
        "biais_contigu_par_expert_octets": biais,
        "experts_lus_par_jeton": k * L,
    }


def main():
    casser = "--casser" in sys.argv
    mod = charger_lecteur()
    sortie = {"etude": "07-synthese", "casser": casser, "modeles": []}
    for nom, chemin in FICHIERS.items():
        sortie["modeles"].append(inventaire(mod, nom, chemin, casser))
    sortie["temoins_tiennent"] = all(m["temoin_fin_du_dernier_tenseur"]["tient"]
                                     for m in sortie["modeles"])
    json.dump(sortie, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
