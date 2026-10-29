# Reprise : juge de design du premier flux de figures du Tome III

Style télégraphique. 2026-10-27.

## Fait

- Les trois pilotes (construction, ronde, latents) sont copiés sous `memoire/essai/juge-design/` (ignoré par
  git) et compilés en FR et en EN, deux passes : 0 erreur, 0 avertissement LaTeX ; 7 boîtes trop pleines
  (2 à 4,4 pt), toutes dans le pilote construction. Le pilote tropicale est compilé pour comparer le style.
- Chaque page est lue à 100 dpi, chaque figure agrandie de 200 à 500 dpi, et les pages EN en planches. Rendus
  en gris, deutéranope et protanope simulés.
- `outils/genome/tome3/juge-design/palette.py` : ΔE des paires de couleurs. Témoins tenus, cassure tombée
  (`journaux/palette*.json`).
- Jugement : `memoire/tome3/JUGEMENT-figures-design.md`, avec 10 graves et 31 mineurs (D1 à D31). Aucune figure
  n'est modifiée (consigne).

## Décisions (réponses par délégation du 2026-10-27, réversibles)

- Un dictionnaire des couleurs du Tome III (§ 2.1 du jugement) : le rouge plein ne sert plus qu'au signe ; le
  synonyme λ = 1 est bleu partout.
- Une seule convention de légende (G9) : `\Titre…`, puis `\Legende…` ouverte par une phrase de tête en gras et
  une étiquette `\mes`, puis `\sourcefig{\Source…}` dans le caption.
- Les graves de dessin s'ajoutent à ceux des juges des chiffres ; les deux listes ne se remplacent pas.

## Reste (au flux qui corrigera les figures)

- Les dix graves d'abord : G9 et le dictionnaire (D23) en premier, car ils touchent tous les lots ; puis G1,
  G4, G5 (mécaniques) ; puis G2, G3, G6, G7, G8, G10 (à redessiner).
- Les mineurs D1 à D31.
- Proposer le dictionnaire au flux des pistes pour III-11.x (R6 : ne pas y écrire).

## Pièges

- Une lecture à 100 dpi trompe : la légende de III-9.2 y paraissait fausse, et elle est juste. Agrandir avant
  de conclure.
- L'outil d'écriture refuse le dépôt : écrire dans le brouillon, puis `cp`.
- `pdftoppm` est celui de MiKTeX (dans le PATH) ; Python avec `-I -X utf8`.
