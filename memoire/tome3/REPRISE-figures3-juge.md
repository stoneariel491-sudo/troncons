# Troisième passe des figures : le juge (note de reprise)

Rôle : juge indépendant de la troisième passe, chiffres et dessin. Rien fait de ce qui est jugé. Livrable :
`memoire/tome3/JUGEMENT-figures3.md`. Outils et journaux : `outils/genome/tome3/juge3/`. Compilations :
`memoire/essai/juge3/` (ignoré par git). Aucune mesure, aucune carte, aucune passe du modèle ; MiKTeX 26.5 tel quel.

## État (2026-10-27)
- [x] Lu : SOCLE, REPRISE-figures, CONVENTIONS, quatre JUGEMENT-figures2-*, REPRISE-figures3-preambule et -retouches,
  `git show` des sept commits.
- [x] Seuils déclarés (§ 1 du jugement), commit avant toute lecture de rendu.
- [x] Tomes I et II, FR et EN, reconstruits (22 h 21 à 23 h 17) : 0 erreur, 0 indéfini, 173/169/237/233 pages ; toutes
  les pages égales aux PDF commités par les mots (boîtes à moins de 0,2 pt) et par l'image (au plus 0,0033 % de pixels).
  Les « deux preuves coupées autrement » du rôle préambule : artefact de pdftotext (pages 103 et 131 FR égales au
  pixel à 150 dpi). Journaux `compare-t*.json`, `tomes-construction.json`.
- [x] Document minimal à moi (`minimal-juge3.tex`) : cause A confirmée (crochet retiré : 0 erreur ; trace :
  
ewcounteralias {proposition}{proposition}) ; correctif A 0 erreur, mêmes renvois ; témoin faux : 2 erreurs.
  Cause B reproduite en dix lignes (`minimal-b-juge3.tex` : un 	extsuperscript au niveau du texte, puis un nœud
  	iny avec 	extsubscript) ; correctif B : 0. Pilote commun, ancien préambule : 6 erreurs ; neuf : 0.
- [x] 51 nombres refaits (`refaire3.py`) : 50 égaux ; SynoNVarPartLargeur 61,1 contre 61,2 en pleine précision (non
  imprimé). Régénération : 117 sur 121 au bit, 4 de la palette égales au contenu (CRLF), 1 de cassure non écrite.
  Gardes forcées à faux : GN2, GN1, G7, J6, compagnon, j = 11, E1 tombent ; seconde pointe tombe à la compilation ;
  DN7 tombe (boîte doublée).
- [x] Pilotes FR et EN : 0 erreur, 0 trop pleine, 0 indéfini, 0 police manquante (7, 14, 18, 6 pages). Pages
  touchées lues en couleur, gris, deutéranope ; G7 61,1 % au rendu (FR/EN) ; G10 0,52 mm FR, 1,19 mm EN, frôle « 2,644 » ;
  GD1 0 pixel bleu sauf III-8.7 (lien `\cref` ajouté, 461/473 px) ; DN1 manque en III-8.6.
- [x] III-9.7 refait à la source (`sources_latents.py`) : égal au journal du juge 2 au 16e chiffre ; T1 1,8e-12.
- [x] Ce qu'une retouche casse ailleurs : GJ1 (halo blanc de III-2.1 : 37 sommets de barres cachés, 40 coupés) ;
  diff des chevauchements second flux / troisième passe : rien d'autre.
- [x] Jugement écrit (`JUGEMENT-figures3.md`) et commité.

## Verdict, en bref
Préambule tient (Tomes I et II égaux aux PDF commités ; la « coupure autrement » du rôle est un artefact de
pdftotext). GN2, GN1 (construction), GN1 (latents), G7, G10 levés ; GD1 non levé au critère pour un lien bleu dans
III-8.7 ; grave neuf GJ1 (III-2.1) ; 11 mineurs. À l'orchestrateur : GJ1 (retirer ou tracer avant les barres le trait
blanc de `\EclZeros`), `\cref*` dans la note de III-8.7, M2 (`\num` en maths de la tête de III-8.6), M3, M4 ; barrer
les phrases fausses des deux notes de reprise (M8, M9).
