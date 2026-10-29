# Tome III, figures : où on en est (2026-10-27, vers 13 h 55)

## Premier flux : fini et jugé
Run `<session>` (7 agents, aucun en erreur), lancé vers 8 h 05 et fini vers 13 h 50.

- **Lots** : construction (13 figures, ch. 8 à 10), ronde (11 figures, ch. 1 à 4 et 7), espaces latents (3 figures :
  III-7.6, III-9.1 (c), III-9.7). Macros sous `memoire/figures/tome3/*-figures.tex`, scripts `memoire/outils/tome3_*.py`,
  pilotes sous `memoire/essai/pilote-tome3-*.tex` (ignorés par git). Notes : `REPRISE-figures-<lot>.md`.
- **Juges des chiffres** :
  - construction (`JUGEMENT-figures-construction.md`) : 154 nombres refaits, tous justes ; 5 graves (III-8.8,
    III-9.1 (c), III-9.2, III-9.3 tombent en l'état) ; dix figures tiennent, dont III-8.6 refaite selon R1 ;
  - ronde (`JUGEMENT-figures-ronde.md`) : 282 nombres refaits ; 1 grave, III-7.1 tombe (les partitions par κ sont
    « égales » par la règle de sa propre légende, pas « gagne ») ; 23 mineurs ; 3 corrections mécaniques faites ;
  - espaces latents (`JUGEMENT-figures-latents.md`) : les trois tiennent, 0 grave, 10 mineurs.
- **Juge de design** (`JUGEMENT-figures-design.md`) : justes mais pas encore belles d'un bout à l'autre ; 10 graves
  (G1 à G10), 31 mineurs ; tombent pour le dessin III-4.8, III-7.1, III-7.4 (EN), III-7.6, III-8.6, III-9.1, III-9.2,
  III-9.3, III-9.6, et l'ensemble (trois conventions de légende). Il fixe un dictionnaire des couleurs du Tome III
  (§ 2.1, à mettre dans un `palette-tome3.tex` commun) et une convention unique de légende (G9).

## Hors du flux, à corriger
- La phrase barrée par R1 survit dans `genome/construction-codon-pour-le-memoire.md` (§ 3 et § 5 F6) : relevé par le
  juge de la construction.

## Second flux (proposé, puis lancé le 2026-10-27 : voir plus bas)
1. Le commun d'abord : `palette-tome3.tex` (dictionnaire du juge de design) et la convention de légende (G9), portés
   dans les neuf fichiers de figures.
2. Les graves des juges des chiffres (construction G1 à G5, ronde G1) et les graves de dessin mécaniques (G1, G4, G5),
   puis les figures à redessiner (G2, G3, G6, G7, G8, G10).
3. Un juge des chiffres et un juge de design qui relisent seulement ce qui a changé.
Ensuite : le reste de l'inventaire (§ 5 de `INVENTAIRE-figures.md`), puis la rédaction des chapitres.

## Second flux : fini et jugé (2026-10-27, vers 16 h 50)
Run `<session>` (8 agents, aucun en erreur).
- **Commun** : `memoire/figures/tome3/palette-tome3.tex` (dictionnaire du juge en noms sémantiques, 33 paires sur 36
  tiennent en gris et en deutéranope) et `legende-tome3.tex` (convention G9) ; mode d'emploi `CONVENTIONS-figures.md`.
- **Corrections** portées dans les huit fichiers de figures ; la note du codon barrée et corrigée pour R1 (cadf276).
- **Juges des chiffres** (`JUGEMENT-figures2-*.md`) : tous les graves du premier flux levés, tous les nombres tiennent.
  Graves neufs, chacun une phrase à réécrire : III-8.5 (« pas un fichier codé » est faux : codec réel), III-10.1
  (« aucune mesure ne les a jugés » : C1 les a décodés, il leur manque seulement une KL), III-9.7 (la tête parle des
  projections comme des entrées : sur les entrées réelles le rapport va de 0,49 à 0,81, aucune sous 0,135). Ronde : 0 grave.
- **Juge de design** (`JUGEMENT-figures2-design.md`) : huit graves sur dix levés. Restent G7 (III-9.6 : 47,6 % de la
  largeur pour plus de 50 % déclarés ; xmin = 2,56), G10 (III-7.1 FR : le trait de la loupe barre une étiquette) et un
  grave neuf GD1 (le bleu a douze sens, par Accent ; correctif sans mesure au § 4). Mineur principal DN1 : chiffres en
  maigre dans les têtes en gras (\boldmath et detect-weight dans legende-tome3.tex).
- **Incident hors du flux** : MiKTeX est passé de 26.2 à 26.5 vers 12 h 20 ; depuis, le préambule commun lève six erreurs
  (thmtools, \c@proposition already defined). Les PDF sortent encore, mais aucun pilote ni aucun tome ne compile plus
  sans erreur. À réparer dans `memoire/commun/preambule.tex` (commun aux trois tomes).

## Troisième passe (proposée, puis lancée le 2026-10-27 : voir plus bas)
Une passe courte : les trois phrases (III-8.5, III-10.1, III-9.7), G7, G10, GD1, DN1, et l'erreur du préambule sous
MiKTeX 26.5 ; puis un juge unique (chiffres et dessin) sur ce qui a changé, et la construction des Tomes I et II pour
vérifier que le préambule réparé ne casse rien.

## Troisième passe : arrêtée par la garde, son juge avait fini (2026-10-27, vers 23 h 40)
Run `<session>`, scriptPath `<session>\workflows\scripts\troncons-tome3-figures-3-<session>.js`.
Arrêtée (TaskStop). Le juge avait déjà commité son jugement (`d255267`) : rien n'est perdu, la passe est à reprendre
seulement pour le retour du flux, inutile. Ne pas relancer avec resumeFromRunId : tout est commité.
- **Préambule** (`7db2673`, `4a9dfb3`, `2e3578c`, `c31bf39`) : deux causes sous MiKTeX 26.5 (A : thmtools et l'alias
  de compteurs du noyau 2026-06-01 ; B : \textsubscript dans un nœud TikZ après un \textsuperscript). Juge : tient ;
  Tomes I et II reconstruits, 0 erreur, toutes les pages égales aux PDF commités. Une phrase fausse de
  `REPRISE-figures3-preambule.md` (« deux preuves coupées autrement ») est à barrer : artefact de pdftotext.
- **Retouches** (`7a40c54`, `6137230`, `1482dbe`) : les trois phrases, G7 (61,1 % de la largeur) et G10 levés ;
  50 nombres neufs sur 51 égaux (le 51e n'est imprimé nulle part).
- **Reste** (`JUGEMENT-figures3.md`) : GJ1, grave neuf : en III-2.1, le halo blanc sous « tout le modèle » cache le
  sommet de 37 barres ; GD1 tombe encore pour un reste : le \cref ajouté dans la note de III-8.7 s'imprime dans le
  bleu des liens (Accent) ; 11 mineurs (DN1 manque en III-8.6, borne 0,135 sans son cône en III-9.7…).
Suite : une retouche de quelques lignes (GJ1, GD1, la barre dans la note du préambule), avec un juge court.

## Rédaction : le Tome III construit en français et en anglais (2026-10-29)
Stone, le 2026-10-29 : « finissons » le Tome III, un vrai mémoire comme les Tomes I et II, autour des figures
jugées. Notes de chaque rôle : `REPRISE-redaction-ossature.md`, `-B`, `-C`, `-D`, `-juge-fr`, `-correcteur-fr`,
`-traducteur-EN1`, `-traducteur-EN2`, `-construction` ; jugement : `JUGEMENT-redaction-fr.md`.

### Ce qui est fait
- **Les deux PDF**, construits par `memoire/construire.sh tome3` (les huit outils de données, figures des
  spectres, `tome3_annexes.py`, latexmk), code 0 :
  `memoire/tome3/fr/troncons-tome3-fr.pdf`, **300 pages** ; `memoire/tome3/en/troncons-tome3-en.pdf`,
  **300 pages**. 0 erreur, 0 renvoi ni citation indéfinis, biber sans erreur ni avertissement, aucun caractère
  manquant. Les fichiers régénérés (annexes, données des figures) sont égaux aux fichiers commités.
- **Mêmes pièces dans les deux langues**, comptées dans les `.toc`, `.lof`, `.lot`, `.lol` et `.aux` construits,
  numéros compris : 3 parties, 17 chapitres (introduction, 13 chapitres, 3 annexes), 121 sections,
  106 sous-sections, 50 figures, 99 tableaux, 1 listing, 65 équations numérotées ; dans les sources, chapitre
  par chapitre, les mêmes environnements de figure, de tableau, d'équation et de formule hors texte, les mêmes
  appels de figure, citations, barres et étiquettes (liste des étiquettes identique, ordre compris).
- **Ce que la construction a demandé** (commit de la construction ; aucun chiffre changé) :
  - au français 02 et 03, deux formules passées hors texte comme dans l'anglais (le traducteur EN1 les y avait
    passées pour deux boîtes trop pleines) : les deux langues ont ainsi les mêmes formules affichées ;
  - trois phrases devenues fausses, signalées par le traducteur EN2, **barrées** en français et en anglais avec
    ce qui a changé : au 07, « substituer n'est jamais meilleur que retirer l'expert » (corrigé au chapitre de
    la duplication ; `genome/duplication.md` et `genome/05-synthese.md` la barrent depuis 800d59e) ; au 08,
    deux phrases qui disaient non barrée la ligne du § 8 de `genome/JUGEMENT-construction.md` (elle l'est
    depuis 800d59e) ; à l'annexe B, « il n'est pas encore dans la cible tome3 » (il y est depuis 57db4ce).
- **Boîtes trop pleines** restantes : ~~FR 5 (4 dans la table des matières, 1,5 à 5,1 pt, préambule commun, M15 ;
  0,57 pt au chapitre 11) ; EN 7 (les mêmes 4 de la table des matières, et 3 sous 1 pt aux chapitres 11 et 12)~~.
  Depuis le correctif du préambule commun (46d5816, 2026-10-29) : 0 dans la table des matières ; FR 1, EN 3,
  toutes sous 1 pt.
- **Jugement final et corrections** (2026-10-29) : `JUGEMENT-final.md` (juge final, 35dc26a) ; corrections dans
  les deux langues (`REPRISE-final-correcteur.md`) : vocabulaire anglais unique (control, synonymous mutation,
  zero-synonym codon, lead, fold, le juge « it »), Résumé français du tome anglais en typographie française,
  outil des annexes qui lit le commit, « Il reste » de l'annexe B barré, mineurs M1 à M6, trois répétitions
  ramenées à un récit et des renvois. Reconstruit : FR 300 pages, EN 300 pages, 0 erreur, 0 indéfini.

### Ce qui reste
- ~~**Aucun juge n'a relu le tome anglais** ni les retouches de la construction ; la langue anglaise n'est jugée
  que par ses traducteurs.~~ Le juge final les a relus (`JUGEMENT-final.md`, 35dc26a) ; la langue reste jugée
  par un non-anglophone (calques : M1, en partie corrigé).
- ~~Les boîtes trop pleines de la table des matières (M15) : dans `memoire/commun/preambule.tex`, commun aux trois
  tomes ; non touché.~~ Corrigé (46d5816) ; Tomes I et II reconstruits, seules leurs pages 7 et 10 (table des
  matières) changent (`REPRISE-final-correcteur.md`).
- Les décimales groupées (« 0,131 8 » contre « 0.1318 », M8 du jugement final) : règle commune aux trois tomes,
  non tranchée.
- Les figures du mimétisme ne sont pas vues page par page au rendu anglais (réserve du traducteur EN1).
- Le mineur du correcteur : un paragraphe jugé à couper, pour une relecture de forme
  (`REPRISE-redaction-correcteur-fr.md`).
