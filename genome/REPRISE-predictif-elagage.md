# Reprise : codage prédictif et élagage synaptique (sujet predictif-elagage)

- État au 2026-10-17 : **étude close pour cette ronde**, tout commité. Note du mémoire :
  genome/predictif-elagage-pour-le-memoire.md ; bib : memoire/sources/genome-predictif-elagage.bib ;
  synthèse : mesures/genome/predictif-elagage/resume-12.csv.
- Venv : ~\dev\lectures\venvs\genome-predictif-elagage. Cibles cargo :
  ~\dev\cibles\genome-predictif-elagage-3 (la plus récente).
- Hors dépôt : ~\dev\essais\troncons\genome\predictif-elagage\ (entrees/ 940 Mo, kld/).

## Résultats
- Sans perte en valeur : ±0 fondus (codons synonymes) + contexte de colonne : 3,6844 bits réels
  contre 3,8434 (12 tenseurs), exact ; ±0 seul : 3,7230 (20b entier), 3,7292 (120b entier).
- Avec perte : partitions par κ, μ par tenseur : 2,4079 réels (0,911 × la base 2,6444),
  KL 0,0702 contre 0,0636, appariée +0,0066 ± 0,0053 (égal statistiquement).
- Échecs mesurés : élagage par magnitude ; tout remplissage inverse à travers les échelles absolues
  (KL 0,09 à 0,31), même hebbien à erreur d'expert égale (KL 0,195).

## Prochain (si une ronde reprend)
- Brancher la canonisation ±0 et le contexte de colonne dans trc-codeur (vérifier d'abord que les
  noyaux du lot K lisent ±0 comme 0).
- κ dominé + colonne sur les 24 couches, KL ; puis 120b.
- Sensibilité jugée par jeton ou contre la KL ; GPTQ sur l'alphabet des cellules.
