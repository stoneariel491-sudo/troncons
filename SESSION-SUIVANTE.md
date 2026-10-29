# Session suivante : reprise de troncons après le 2026-10-22

Écrit le 2026-10-21 pour une session neuve, moins chère que la longue session du 15 au 21 octobre (chaque message y relisait tout l'historique). Stone l'a demandé : « lance une nouvelle session avec ce qu'on a fait pour repartir moins chère avec un ajustement automatique du modèle et du niveau ».

## À lire, dans cet ordre
1. `SOCLE.md` (il fait loi).
2. `genome/REPRISE-construction.md` : où en était chaque agent, et la commande de reprise du flux.
3. `genome/05-synthese.md` § 3 (pistes ouvertes) et § 4 (cahier de construction).

## Les règles de modèle et de niveau (« ajustement automatique »)
Elles sont écrites dans le flux lui-même, agent par agent, pour s'appliquer sans qu'on y pense :
- synthèse : en cache, ne repart pas ;
- lots A et B (code Rust et CUDA, mesures) : modèle de la session, niveau `high` ;
- juge indépendant : niveau `xhigh` ;
- tâches mécaniques d'un futur flux (commits, journaux, lancer un banc déjà écrit) : `model: 'haiku'`, `effort: 'low'` ;
- `max` : seulement pour le juge final avant une publication.
La session principale (conversation, bilans, garde) n'a pas besoin de plus que Sonnet au niveau moyen : Stone choisit le modèle dans le sélecteur de l'application.

## Le gabarit obligatoire (leçon du 2026-10-20)
1. Avant de lancer : fichier d'échange actif (`Win32_PageFileUsage`), portable sur secteur, disque C: libre (28 Go le 2026-10-17 : trop peu pour un nouveau compagnon de 40 Go), verrou de la carte libre, aucun processus d'un flux précédent encore en cours.
2. Agents courts qui commitent après chaque pas.
3. Aucun chiffre dans le mémoire ni dans un message à Stone avant le juge.
4. Mesures de vitesse en séance calme, l'une après l'autre.

## Ensuite, dans l'ordre
1. Finir la construction (lots A et B), puis le juge.
2. La garde tropicale (05 § 3.1) : se juge sur les journaux de routage déjà là, sans nouvelle passe du modèle. Seuil déclaré avant : au moins 80 % des bascules attrapées pour au plus 10 % des cellules.
3. Le Tome III (figures belles et vraies), puis la passe qui unifie les trois tomes.
