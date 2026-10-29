# Reprise : audit des traces personnelles (2026-10-29)

- Fait : `memoire/article/AUDIT-traces.md`, audit en lecture seule de `e6f5df5` (main) et de
  tout l'historique (1 068 commits, 41 versions de PDF). Rien d'autre touché.
- Résultat en bref : PDF seuls (P1) : à retirer, les chemins `~/…` des
  Tomes II (4 par langue) et III (1 par langue), 6 lignes de source ; à décider, « Toronto »
  en page 1 des six PDF et le fuseau des métadonnées. Dépôt (P2) : chemins dans 1 769
  fichiers, identité des commits (adresse Gmail sur les 1 068), identifiants de session,
  23 `.pyc`. Aucun numéro de série, aucun poids de modèle, aucune clé.
- Décidé (réponse par délégation du 2026-10-29, réversible) : deux commits, l'audit puis
  cette note (la consigne dit « ce seul fichier » pour l'audit ; la règle de survie
  demande la note). Scripts d'audit laissés hors du dépôt (consigne), méthode et commandes
  écrites au § 5 de l'audit.
- Décidé : l'adresse électronique des commits n'est écrite nulle part (règle du projet) ;
  l'identifiant de compte est tronqué (`stoneariel…-sudo`).
- Incident : deux fichiers temporaires (`a.tmp`, `b.tmp`) créés puis effacés dans la même
  commande à la racine du dépôt ; non suivis, plus présents.
- Reste à Stone : choisir P1/P2, voie A (instantané) ou B (réécriture), § 4 de l'audit.
- Non audité : les 82 fichiers non suivis de l'arbre de travail au moment de l'audit.
