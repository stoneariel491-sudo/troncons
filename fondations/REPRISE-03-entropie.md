# Reprise : étude 03, entropie (compression sans perte, décompression à la vitesse du calcul)

Livrable : fondations/03-entropie.md (+ 03-entropie-derivations.md pour le mémoire). Outils : outils/03-entropie/. Journaux : fondations/journaux/03-entropie/ (CSV : csv/, régénérés par vers_csv.py). Sources : memoire/sources/03-entropie.bib. Figures : memoire/figures/03-entropie/*.tex (lualatex, compilent sans erreur).
Venv d'essai : ~/dev/essais/troncons/entropie/venv (numpy, zstandard, lz4, gguf 0.19.0). PYTHONIOENCODING=utf-8 pour les journaux.
Rust : outils/03-entropie/rans (wgpu 30, --offline), CARGO_TARGET_DIR=~/dev/essais/troncons/entropie/cible (cible2 : copie pour construire pendant qu'un binaire tourne).
CUDA : outils/03-entropie/cuda/construire.bat -> essais/troncons/entropie/cuda/{rans_v4,dispersion}.exe ; flux d'essai : essais/troncons/entropie/flux-4B (vider_flux).
Clones de lecture : ~/dev/lectures/troncons/entropie (DFloat11, zipnn, recoil, dietgpu, multians, DirectStorage, ZipServ, vram-compression).

## 2026-10-15, première session
- Lecteur GGUF, champs K, entropie 4B/9B, rANS v1-v4 Vulkan, ECSQ proxy, flux d'octets (18651a8), MXFP4 dans le lecteur (086e9a1).

## 2026-10-15, reprise — ÉTAT : livrable complet, rien en cours
- Batterie jusqu'à ~08:30 (limite carte 43 W), puis secteur ; passes de carte refaites sur secteur. Calme jugé sur la puissance de la carte (< 12 W).
- Question clé MESURÉE (banc_gemv, MXFP4 réel) : brut 209 Go/s équiv., fondu 57 (3,7x plus lent), deux passes 56. Décoder à l'arrivée du tronçon, jamais dans le produit.
- Décodeur v4 : Vulkan 70-72 Go/s, CUDA 81-82 (second chemin, mêmes octets).
- MXFP4 : échelles 1,01 b (20b) / 0,91 b (120b) sachant la médiane de ligne ; taux réel exact 1,0888 (20b), 1,0887 (120b) ; avec 3 classes d'échelle 1,1037 (20b), 1,1026 (120b) ; 5 classes +0,0008 seulement ; réassemblage 102 Go/s.
- État de l'art de la reprise (EntQuant, vram-compression, ECF8, WaterSIC) ; trou 3 barré.
- Restes possibles : débits processeur au calme (jamais pris), écrire la sortie du décodeur directement à sa place (supprime le réassemblage), poids BF16 (téléchargement à demander) pour les exposants et l'ECSQ sur poids d'origine, reproduction DietGPU/Recoil.
