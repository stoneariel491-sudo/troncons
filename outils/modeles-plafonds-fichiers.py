"""Plafonds physiques par jeton pour les fichiers GGUF exacts candidats au téléchargement.

Entrée : gguf-entetes.json (modeles-gguf-entete-distant.py). Modèle de coût : modeles_physique.py.
Tout est calculé ; rien n'est mesuré ici.

Pour une table de n-grammes (Qwen3.8 : clés « ple.ngram_size » et « ple.heads_per_ngram »), on lit
par jeton (ngram_size − 1) × heads_per_ngram lignes (ordres 2 à ngram_size, une ligne par tête et par
ordre, schéma de l'article Engram, arXiv 2601.07372) ; chaque ligne lue sur le NVMe coûte au moins
une page de 4 Kio. Hypothèse dite : aucune ligne en cache (borne pessimiste).

Usage : python -I modeles-plafonds-fichiers.py <gguf-entetes.json> <sortie.md>
"""
import importlib.util
import json
import os
import sys

_spec = importlib.util.spec_from_file_location(
    "modeles_physique", os.path.join(os.path.dirname(os.path.abspath(__file__)), "modeles_physique.py"))
phys = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(phys)

PAGE = 4096


def main(entree, sortie):
    d = json.load(open(entree, encoding="utf-8"))
    md = ["| Fichier | Taille (Go) | Toujours lus (Go) | Experts routés : total / lus par jeton (Go) "
          "| Table de recherche : total (Go) / lue par jeton (Kio) | Succès cache uniforme | "
          "Plafond jetons/s (opt. – pess.) | Tout depuis le NVMe (jetons/s) |",
          "|---|---:|---:|---|---|---:|---|---:|"]
    for cle, r in d.items():
        if "erreur" in r:
            continue
        cat = r["octets_par_categorie"]
        A = r["octets_toujours_lus"]
        R = r["octets_experts_routes_lus_par_jeton"] or 0.0
        E = cat.get("expert", 0)
        T = cat.get("recherche", 0)
        lu_table = 0.0
        arch = r["architecture"]
        ng = r["cles"].get(f"{arch}.ple.ngram_size")
        tetes = r["cles"].get(f"{arch}.ple.heads_per_ngram")
        if T and ng and tetes:
            lignes = (ng - 1) * tetes
            lu_table = lignes * PAGE  # une page par ligne lue sur le disque
        t_opt, t_pes, h = phys.plafonds(A, R, E, T, lu_table)
        t_disque = A / (phys.VRAM_GO_S * 1e9) + (R + lu_table) / (phys.NVME_GO_S * 1e9)
        nom = cle.split("/")[1] + "/" + cle.split("/")[-1].split("-0000")[0].replace(".gguf", "")
        md.append(f"| {nom} | {r['octets_fichiers']/1e9:.1f} | {A/1e9:.2f} | {E/1e9:.1f} / {R/1e9:.2f} | "
                  f"{T/1e9:.1f} / {lu_table/1024:.0f} | {h:.0%} | {1/t_opt:.1f} – {1/t_pes:.1f} | {1/t_disque:.1f} |")
    open(sortie, "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
