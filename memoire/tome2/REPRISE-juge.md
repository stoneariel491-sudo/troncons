# Reprise : juge technique indépendant du Tome II

Rôle : juger les deux PDF du Tome II sans en écrire une ligne ; chaque chiffre contre sa source,
par les outils du dépôt et par un second chemin ; chaque preuve et chaque schéma au bit près ;
parité EN/FR. Ne modifie pas les chapitres. Aucun calcul sur la carte. Aucune question.

Fichiers à moi : `memoire/tome2/JUGEMENT.md`, `memoire/outils/tome2_juge.py`, cette note.

## Journal
- 2026-10-16 : départ. Arbre propre (seuls des __pycache__ non suivis). HEAD `ef30835` (Tome II
  construit, EN 231 p., FR 235 p.). Lu SOCLE, ARCHITECTURE § 4 et § 7, les dix chapitres FR, les
  annexes, les figures de schémas ; passages EN critiques.
- Reproductibilité : données dérivées sauvegardées dans le brouillon, cinq outils tome2_*.py
  relancés : code 0, 0 écart, `git status` inchangé (CSV régénérés égaux au bit).
- Second chemin : `memoire/outils/tome2_juge.py` (parité des nombres EN/FR + recalculs des chiffres
  visés). Témoin `--casser` (0.884 → 0.885 dans l'EN du ch. 08) : tombe.
- Verdict : 1 grave (« 5·10⁻¹¹ » non barré aux ch. 04 et 07, contredit par le théorème des deux
  régimes du ch. 05 qui le barre), 22 mineures, éloges. Tout est dans JUGEMENT.md.
- Réponse par délégation du 2026-10-16, réversible : classement grave/mineur (grave = deux
  résultats incompatibles affirmés, ou chiffre de verdict faux) ; l'outil du juge rangé sous
  `memoire/outils/` (là où sont les autres seconds chemins du mémoire).

## Pour qui reprend
- Les corrections demandées sont aux rédacteurs (propriétaires des chapitres) ; ce jugement ne
  touche aucun chapitre. Après correction : relancer `tome2_juge.py`, reconstruire, vérifier que
  les phrases visées ont changé dans les deux PDF.
- Non vérifié ici (dit dans JUGEMENT.md) : figures point par point à l'écran, bibliographie,
  journaux bruts du lot K et `c8-juge.json` champ par champ.
