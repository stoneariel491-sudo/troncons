# Note de reprise : le juge de l'article court

Rôle : juge indépendant de `memoire/article/{en,fr}/`. 2026-10-29. Style télégraphique.

## État

- **Fait** : `JUGEMENT-article.md`. Verdict : chiffres tenus (156 sur 156 recalculés depuis leurs journaux,
  présents dans EN et FR ; le reste lu dans les documents jugés) ; **ne se soumet pas en l'état** : 3 graves
  (G1 nouveauté : NxFP, RaZeR, Heilper et Singer non cités ; G2 exactitude du moteur prêtée au modèle, KL sans
  « fenêtre 0 » ni YaRN ; G3 384 Mo sans les ≈ 6,3 Go de la carte), 18 mineurs, 1 hors du flux (H1 : Tome III,
  « 540 tables des couches 0, L/2, L−1 », ce sont toutes les couches).
- **Outils** (`memoire/article/juge/`, écrits sans ouvrir ceux du rédacteur) : `refaire_chiffres.py` (journal
  `refaire_chiffres.txt` ; témoin `--casser` → code 1, tenu), `parite_structure.py` (témoin `--casser` → les
  citations tombent, tenu), `chemins_cites.py`, `longueur_resume.py` (journal `verifications.txt`).
- **Paquets arXiv** dépliés dans un dossier vide et compilés seuls par pdflatex : EN 13, FR 14, 0 erreur, texte
  égal aux PDF commités ; EN demande une troisième passe (« Rerun », M17).
- **Pages d'aide d'arXiv** relues le 2026-10-29 : submit_tex, faq/texlive, prep (résumé ≤ 1 920 caractères ;
  « Firstname Lastname »), translations.

## Décisions (réponses par délégation du 2026-10-29, réversibles)

- **Seuil grave / mineur** : grave = une phrase qui fait dire plus que les mesures ou les jugements, sur un point
  qu'un relecteur retiendra, ou une absence qui fait tomber la nouveauté. Raison : la consigne (point 2) et la
  barre du SOCLE (« rien de trop beau »).
- **Sources neuves proposées (G1)** lues seulement en résumé (et NxFP § 4.3) : le rédacteur les lit avant de
  les citer. Raison : SOCLE, source primaire.
- **Aucune correction faite dans l'article** : le juge ne corrige pas ce qu'il juge ; les correctifs sont écrits
  mot pour mot dans le jugement.
- **Rien touché** hors de `memoire/article/juge/`, `JUGEMENT-article.md` et cette note. Les fichiers
  `memoire/figures/tome3/donnees/*` marqués modifiés dans l'arbre (fins de ligne seulement) ne sont pas à moi.

## Ce qui reste

- Corrections du rédacteur (G1-G3, M1-M18), reconstruction, puis contre-jugement par un autre juge.
- H1 au Tome III (orchestrateur).
- Gestes de Stone : emplacement public, forme du nom d'auteur pour arXiv, forme bilingue de la soumission,
  compte, parrainage, catégorie, licence.
- Commits sur la branche de l'arbre de travail (`stone/goofy-feynman-9939ea`), pas sur `main` : fusion par
  l'orchestrateur.
