# Troisième passe des figures : le préambule commun sous MiKTeX 26.5 (note de reprise)

Rôle : réparer `memoire/commun/preambule.tex` (commun aux trois tomes), qui lève six erreurs depuis le passage de
MiKTeX 26.2 à 26.5 (2026-10-27, vers 12 h 20). Aucune mesure, aucune carte graphique, aucune passe du modèle.
MiKTeX n'a pas été touché (ni mise à jour, ni paquet, ni réglage) : seule la source est corrigée.

## État (2026-10-27)
- [x] Cause A (les six erreurs de thmtools) trouvée et écrite (§ 1), reproduite sur un document minimal (§ 2).
- [x] Correctif A dans `memoire/commun/preambule.tex` (§ 3) ; aucun fichier du Tome II à changer (commit 7db2673).
- [x] Document minimal : 0 erreur ; témoins tenus (§ 2).
- [x] Les huit pilotes du Tome III (FR et EN) : 0 erreur, 0 manque (§ 4) ; témoin « avant » : 6 erreurs.
- [x] Tome I, FR et EN : 0 erreur, 0 manque ; 173 et 169 pages, comme les PDF commités.
- [x] Tome II, FR et EN : **une seconde erreur de MiKTeX 26.5**, fatale, cachée jusque-là par la première
  (`-halt-on-error` s'arrêtait au préambule) : TikZ « Giving up on this path » dans `\SchemaNoyStructures`
  (ch. 4). Cause B et correctif B : § 1 bis et § 3 bis. Éprouvé en contexte (chapitre 2 puis la figure).
- [x] Correctif B dans `memoire/commun/preambule.tex` (§ 3 bis, commit 4a9dfb3).
- [x] Tomes I et II reconstruits avec les deux correctifs, FR et EN : **0 erreur, 0 renvoi ni citation
  manquant**, biber propre ; pages 173, 169, 237, 233, comme les PDF commités (§ 4).
- [x] Mot à mot contre les PDF commités : Tome I identique page pour page ; Tome II, ~~deux preuves coupées
  autrement (2 pages en FR, 3 en EN), effet de MiKTeX 26.5 et non des correctifs~~ **corrigé le 2026-10-28,
  d'après `JUGEMENT-figures3.md` § 3.4** : toutes les pages sont égales aux PDF commités, par les mots et par
  l'image ; la « coupure » venait de pdftotext, qui extrait le « ■ » du PDF de 26.5 et pas celui de 26.2 ; avec
  l'ancien et le nouveau
  préambule sous 26.5, les chapitres 4 et 5 du Tome II rendent le même PDF à l'octet près, date et
  identifiant mis à part (§ 4).
- Reste (hors de mon rôle) : les PDF commités datent de 26.2 ; les reconstruire sous 26.5 changerait les deux
  preuves ci-dessus et rendrait le « ■ » extractible. Je ne les ai pas remplacés (consigne : ne pas toucher les
  PDF commités).

En bref : deux régressions de MiKTeX 26.5, deux correctifs de quelques lignes dans le seul préambule commun,
même mise en page, les trois tomes et les huit pilotes passent sous `-halt-on-error`.

## 1. La cause

Versions lues dans les journaux (`.log`) :

| | MiKTeX 26.2 (journaux du 16 et du 27 octobre au matin) | MiKTeX 26.5 (depuis 12 h 20) |
|---|---|---|
| LuaHBTeX | 1.24.0, format du 2026-09-08 | 1.25.7, format du 2026-10-27 |
| noyau LaTeX | `LaTeX2e <2025-11-01>` | `LaTeX2e <2026-06-01>` |
| amsthm | 2020/05/29 v2.20.6 | le même |
| thmtools | 2023/05/04 v0.76 | le même |
| cleveref | 2018/03/27 v0.21.4 | le même |

Parmi ces paquets, seul le noyau a changé (pgf aussi, voir § 1 bis). Le mécanisme, lu dans les sources
installées :

1. Le noyau 2026-06-01 a une commande neuve, `\newcounteralias{x}{y}` (`latex.ltx`, section `ltcounts.dtx`) : elle
   fait de `\c@x` le registre de `\c@y` et pose `\the`, `\theH`, `\p@`, `\cl@` et `\alias@ctr@x`. Elle commence
   par `\@ifdefinable\c@x` : si `\c@x` existe déjà, elle lève « Command \c@x already defined » et ne fait rien.
2. Ses premiers soins pour les paquets extérieurs (`tex/latex/firstaid/latex2e-first-aid-for-external-files.ltx`,
   2026-03-12 v1.1x, crochet `package/amsthm/after`, étiquette `firstaid/aliascounter`) remplacent la macro
   `\@ynthm` d'amsthm, celle de `\newtheorem{x}[y]{Nom}` (compteur partagé) : elle appelle désormais
   `\newcounteralias{x}{y}` (le fichier dit « UF »), là où amsthm 2.20.6 ne posait que `\thex`. Le même crochet
   remet cette macro après cleveref, qui avait la sienne.
3. thmtools 0.76 (`thm-autoref.sty`, `\thmt@autorefsetup`, appelé avant toute définition) fait **déjà** l'alias
   par sa propre commande, `\@counteralias{x}{y}` (`aliasctr.sty`), puis remplace le compteur frère par `x`
   lui-même : `\declaretheorem[sibling=theoreme]{proposition}` devient
   `\newtheorem{proposition}[proposition]{Proposition}`.
4. Le `\@ynthm` des premiers soins appelle donc `\newcounteralias{proposition}{proposition}` : `\c@proposition`
   existe (thmtools vient de le poser), d'où l'erreur. Une fois par déclaration `sibling=theoreme` : proposition,
   lemme, corollaire, definition, hypothese, remarque, les six erreurs (lignes 190 à 195 de l'ancien préambule).

Lu dans la trace (`\tracingmacros`, `d-trace2.log`) : `\@ynthm` en mémoire contient `\newcounteralias {#1}{#2}`,
et l'erreur part de `\newcounteralias {proposition}{proposition}`.

Pourquoi les PDF sortaient quand même : en `nonstopmode`, la commande en erreur est ignorée ; elle ne faisait que
refaire un alias que thmtools avait déjà posé. Le compteur partagé, les numéros et les noms de cleveref restaient
justes. Mais `latexmkrc` passe `-halt-on-error` : la construction des tomes s'arrêtait dans le préambule.

Précision au juge latents (JUGEMENT-figures2-latents.md § 7 : « sans thmtools, amsthm passe ») : c'est juste,
et la condition est plus étroite encore : il faut thmtools **et** une déclaration `sibling=` (témoins du § 2) ;
thmtools avec `numberwithin=` seul passe aussi. Sa phrase n'est pas fausse, elle n'est pas barrée.

## 1 bis. La seconde cause : `\textsubscript` dans un nœud TikZ (Tome II)

- Le symptôme : `./chapitres/04-noyaux.tex:321: Package tikz Error: Giving up on this path. Did you forget a
  semicolon?`, dans `\SchemaNoyStructures` (`memoire/figures/tome2/noyaux-figures.tex`), FR et EN ; erreur
  fatale, pas de PDF. Elle ne se voyait pas : avec les six erreurs du préambule, `-halt-on-error` arrêtait la
  construction avant le chapitre 4 ; les pilotes du Tome III et le Tome I n'ont pas ce cas.
- Les versions : pgf et TikZ 3.1.11a (2025-08-29) sous 26.2, 3.1.12 (2026-08-01) sous 26.5 ; noyau 2025-11-01
  puis 2026-06-01.
- Le mécanisme, lu dans `latex.ltx` (2026-06-01) et dans le contexte de l'erreur : `\textsubscript` et
  `\textsuperscript` n'entrent plus en mode mathématique ; `\@textsubscript` appelle `\check@mathfonts` **hors de
  tout groupe**. Quand la taille des fontes mathématiques globales n'est pas celle du nœud, `\check@mathfonts`
  pose `\aftergroup\restglb@settings` (et ses `\aftergroup\mv@normal@reset`, `\mv@bold@reset`) dans le groupe qui
  le contient : le texte du nœud. Ces jetons tombent juste après l'accolade fermante, avant le « ; ». TikZ sait
  sauter `\reset@color` à cet endroit, pas `\restglb@settings`, dont le développement commence par
  `\begingroup` : il abandonne le chemin. Le contexte de l'erreur le montre :
  `<to be read again> ...esetcolor \restglb@settings \mv@normal@reset \mv@bold@...`, puis `; \node`.
- Le nœud en cause : `ctx\textsubscript{0}`, dans la ligne `ParamsRope` de `\NoyOctets` (le seul texte de la
  figure qui appelle `\check@mathfonts` hors des maths ; le contexte, tronqué, ne le nomme pas ; le remède,
  qui ne touche que `\textsubscript` et `\textsuperscript`, le confirme).
- La condition dépend de l'état : le chapitre 4 seul passe, la figure seule passe ; le chapitre 2 (`02-format`)
  lu avant la figure suffit à la faire tomber (`ctx-02a` : 1 erreur ; chapitres 0, 1 ou 3 avant : 0). Un document
  court (une formule à la taille du texte, puis six nœuds `\tiny` avec `\textsubscript`, `tikz-indice.tex`) ne
  la reproduit **pas**, ni avec l'ancien préambule ni avec le neuf : je n'ai pas isolé la condition exacte sur
  les tailles, seulement le mécanisme et le remède.

## 2. Le document minimal

`memoire/essai/preambule-minimal.tex` (dossier ignoré par git ; son texte entier est au § 6 de cette note) :
scrbook, amsthm, hyperref, cleveref, thmtools, comme le préambule ; un théorème, deux frères, un second chapitre ;
il imprime `\ref` et `\cref` de chaque énoncé. Compilé deux fois sous MiKTeX 26.5, dans
`memoire/essai/construction-tomes/minimal/v2/` :

| variante | erreurs | renvois imprimés |
|---|---|---|
| `m-erreur` (l'état d'avant) | **2** (`\c@proposition`, `\c@lemme`) | 1.1, 1.2, 1.3, 1.4 ; théorème 1.1, proposition 1.2, lemme 1.3, proposition 1.4 ; lemme 2.1 |
| `m-sans-thmtools` (amsthm seul, témoin) | 0 | les mêmes |
| `m-sans-sibling` (thmtools sans frère, témoin) | 0 | 1.1, 1.1, 1.1, 1.2 (compteurs séparés, attendu) |
| `m-corrige` (le correctif) | **0** | les mêmes que `m-erreur` |
| `m-ancien` (noyau d'avant simulé, correctif en place) | 0 | les mêmes |
| `m-ancien-sans-correctif` (noyau d'avant simulé) | 0 | les mêmes |
| `m-doublon` (témoin qui doit tomber) | **2** (`\c@lemme already defined`, `No counter 'absent'`) | les mêmes |

- Le noyau d'avant se simule en retirant le crochet des premiers soins (`\RemoveFromHook{package/amsthm/after}
  [firstaid/aliascounter]`) et en ôtant `\newcounteralias`, avant `\documentclass`. C'est une simulation, pas le
  noyau 2025-11-01 lui-même : je n'installe pas d'autre version.
- Le témoin `m-doublon` vérifie que le correctif ne tait pas une vraie faute : un alias de `lemme` sur `chapter`
  (registre différent) et un alias sur un compteur absent lèvent toujours leur erreur.
- Le compteur de l'instrument (`verifier.py`) compte 2 erreurs sur `m-erreur` et 6 sur le pilote commun compilé
  avec l'ancien préambule (`p-commun-avant`) : il voit ce qu'il doit voir.

## 3. Le correctif

Dans `memoire/commun/preambule.tex`, juste après `\usepackage{thmtools}` et autour des huit `\declaretheorem`,
quatorze lignes ajoutées, aucune changée :

```latex
\ifdefined\newcounteralias
  \let\AliasCompteurNoyau\newcounteralias
  \renewcommand*{\newcounteralias}[2]{%
    \ifcsname c@#1\endcsname
      \expandafter\ifx\csname c@#1\expandafter\endcsname\csname c@#2\endcsname
      \else\AliasCompteurNoyau{#1}{#2}\fi
    \else\AliasCompteurNoyau{#1}{#2}\fi}
\fi
% ... les huit \declaretheorem, inchangés ...
\ifdefined\AliasCompteurNoyau \let\newcounteralias\AliasCompteurNoyau \fi
```

- Pendant les déclarations seulement, un alias déjà fait (`\c@x` est le même registre que `\c@y`, ici `x = y`) ne
  se refait pas ; tout autre appel va à la commande du noyau, intacte. Après les déclarations, la commande du
  noyau est remise telle quelle.
- Même mise en page sous 26.5 : la seule commande sautée est celle que l'erreur faisait déjà ignorer ; thmtools
  pose le même alias qu'avant. Seul `\alias@ctr@proposition` (etc.) reste non défini, comme dans les PDF sortis
  avec les six erreurs et comme sous 26.2 ; le noyau ne s'en sert que pour refuser un alias dans un
  `\@addtoreset`, que le mémoire ne fait pas.
- Juste sous une version plus ancienne : sans `\newcounteralias` (noyau sans la commande), `\ifdefined` est faux
  et le préambule est celui d'avant, ligne pour ligne. Si un noyau a la commande sans les premiers soins d'amsthm,
  l'enveloppe est posée mais personne ne l'appelle. Vérifié par la simulation (§ 2), pas sous MiKTeX 26.2 réel.
- Écarté : ôter thmtools (amsthm et cleveref suffisent pour les numéros : témoin `m-sans-thmtools`). Les têtes
  d'énoncés passeraient par d'autres crochets (ceux de thmtools posent un compteur factice et des ancres) : la
  même mise en page serait à prouver page à page, je ne l'ai pas fait. Remplacer `sibling=` par une autre clé :
  même chemin dans thmtools (`numberlike`, `sharenumber` sont des synonymes). Corriger thmtools ou MiKTeX :
  interdit (on corrige nos sources).
- Fichiers communs du Tome II (`memoire/tome2/commun/`) : aucun ne déclare de théorème ; rien à changer.

## 3 bis. Le correctif B

Dans `memoire/commun/preambule.tex`, juste après `\usepackage{tikz}`, onze lignes ajoutées :

```latex
\makeatletter
\ifdefined\textsuperscript@offset
  \DeclareRobustCommand*\textsuperscript[1]{{\@textsuperscript{\selectfont#1}}}
  \DeclareRobustCommand*\textsubscript[1]{{\@textsubscript{\selectfont#1}}}
\fi
\makeatother
```

- C'est la définition du noyau 2026-06-01, mot pour mot, dans une paire d'accolades de plus : les jetons
  `\aftergroup` tombent à la fin de ce groupe, dans le texte, et plus après l'accolade d'un nœud. La boîte
  levée ou baissée, son décalage (lu par `\check@mathfonts` au même endroit) et l'espace qui suit
  (`\textsuperscript@space`) ne changent pas.
- Gardé par `\textsuperscript@offset`, qui n'existe qu'avec la nouvelle mise en œuvre : sous un noyau plus
  ancien, rien ne change.
- Pourquoi dans le préambule et pas dans la figure : `\textsuperscript` est dans des nœuds TikZ ailleurs aussi
  (`synonyme-figures.tex` du Tome III, `noyaux-figures.tex` en légende d'axe) ; la condition dépend de l'état,
  donc une figure qui passe aujourd'hui peut tomber demain si un chapitre change avant elle. Le préambule
  est commun aux trois tomes : un seul endroit.
- Éprouvé : `ctx-02a` (chapitre 2 puis la figure, ancien préambule) : 1 erreur TikZ ; `ctx-02-essai` (même
  document, préambule avec le correctif B) : 0 erreur, document mené jusqu'au bout.

## 4. Vérifications

Toutes sous MiKTeX 26.5 (LuaHBTeX 1.25.7, LaTeX 2026-06-01), `latexmk -r memoire/latexmkrc -lualatex -outdir=…`
(donc `-halt-on-error`), sorties sous `memoire/essai/construction-tomes/` (ignoré par git). Les pilotes se
compilent par des enveloppes (`pilotes/p-<lot>-<langue>.tex`, un `\input` du pilote commité) : aucun PDF de
`memoire/essai/` n'est écrit ni effacé. Les tomes se compilent dans leur dossier, sous un nom de travail
distinct (`t1-fr`, …), pour que le PDF commité ne puisse pas être effacé (piège relevé par le juge latents :
LuaTeX efface le PDF du nom de travail dans le dossier courant malgré `-output-directory`).

| document | erreurs | renvois ou citations manquants | pages |
|---|---|---|---|
| minimal (`m-corrige`) | 0 | 0 | 3 |
| pilote commun, FR | 0 | 0 | 6 |
| pilote commun, EN | 0 | 0 | 6 |
| pilote commun, ancien préambule (témoin) | 6 | 0 | 6 |
| pilote construction, FR | 0 | 0 | 18 |
| pilote construction, EN | 0 | 0 | 18 (au second essai, voir plus bas) |
| pilote ronde, FR | 0 | 0 | 14 |
| pilote ronde, EN | 0 | 0 | 14 |
| pilote latents, FR | 0 | 0 | 6 |
| pilote latents, EN | 0 | 0 | 6 |
| Tome I, FR (correctif A seul) | 0 | 0 | 173 (PDF commité : 173) |
| Tome I, EN (correctif A seul) | 0 | 0 | 169 (PDF commité : 169) |
| Tome II, FR (correctif A seul) | **1 fatale** (TikZ, cause B) | — | pas de PDF |
| Tome II, EN (correctif A seul) | **1 fatale** (TikZ, cause B) | — | pas de PDF |

- Pages des pilotes : 6, 18, 14 et 6, comme le juge de design du second flux (6, 14, 6 et 18).
- Le texte du pilote commun (pdftotext) est identique, octet pour octet, avant et après le correctif A.
- Le pilote construction EN est d'abord tombé au troisième passage de lualatex : « TeX capacity exceeded
  [token memory size=3417909] » sur `\GrapheSynoBasePropre`. Relancé seul, depuis rien, dans
  `pilotes-bis/` : 0 erreur, 18 pages, 4 101 490 mots de mémoire alloués (comme le FR et comme sous 26.2).
  Lecture : LuaTeX n'a pas pu agrandir sa mémoire de jetons pendant que quatre compilations tournaient et que
  la machine manquait de RAM (d'autres agents) ; ce n'est pas une erreur des sources. Hypothèse, non prouvée.
- `verifier.py` compte les erreurs (« ! », « fichier:ligne: », et les fatales coupées par le retour à la ligne
  du journal : il manquait d'abord la « capacity exceeded », corrigé), les manques (mêmes motifs que
  `construire.sh`), les « rerun », biber. Les messages « fichier:ligne: ignored: Infinite glue shrinkage » des
  journaux de 26.2 (9 dans le Tome I EN du 16 octobre) ne sont pas fatals ; ils se comptent à part (0 sous 26.5).

Avec les deux correctifs (commit 4a9dfb3), constructions de 17 h 47 à 19 h 33 (deux à la fois ; la machine
manquait de RAM, d'où 104 à 106 minutes par tome au lieu de 8) :

| document | erreurs | renvois ou citations manquants | biber | boîtes trop pleines | pages (commité) |
|---|---|---|---|---|---|
| Tome II, FR | 0 | 0 | 0 erreur, 0 entrée absente ou en double | 7 (7 sous 26.2) | 237 (237) |
| Tome II, EN | 0 | 0 | idem | 5 (5 sous 26.2) | 233 (233) |

Comparaison mot à mot, page à page, avec les PDF commités (`comparer.py`, pdftotext sans mise en page ; le
carré de fin de preuve « ■ » est retiré des deux côtés, parce que 26.5 le rend extractible et 26.2 non : 0 dans
les PDF commités, 42 dans le Tome I FR neuf, 71 dans le Tome II FR neuf) :

- Tome I, FR et EN (correctif A seul) : **0 page différente** sur 173 et 169 ; même nombre de mots.
- Tome II, FR : 2 pages sur 237 (p. 103 et 131), 111 043 mots contre 111 046. Chaque fois une coupure de mot
  de plus dans le dernier paragraphe d'une preuve (« comp-teurs », « exponen-tielle ») : ch. 4, preuve de
  `prop:t2n-det-decodeur` ; ch. 5, preuve de `prop:t2r-croisee`. Le paragraphe reste sur sa page, la page
  suivante ne bouge pas.
- Tome II, EN : 3 pages sur 233 (p. 81, 101, 131) : les deux mêmes preuves (« commu-tative »,
  « renor-malised ») ; p. 81, seulement l'ordre d'extraction d'un accent (« 𝑣̄. » contre « 𝑣.̄ »).
- Les entrées des constructions (fichier `.fls`) qui ont changé dans git depuis le commit des PDF : le seul
  `memoire/commun/preambule.tex` (`entrees.py`). Fontes Libertinus (2024-10-18), unicode-math (0.8), amsthm
  (2.20.6) : les mêmes sous 26.2 et 26.5.
- Tome I reconstruit avec les deux correctifs (`t1-fr-b`, `t1-en-b`) : 0 erreur, 0 manque, 173 et 169 pages,
  0 page différente contre le PDF commité et contre la construction au correctif A seul.

| document | erreurs | manques | biber | boîtes trop pleines | pages (commité) |
|---|---|---|---|---|---|
| Tome I, FR (A et B) | 0 | 0 | 0 erreur, 0 entrée absente ou en double | 31 (31 sous 26.2) | 173 (173) |
| Tome I, EN (A et B) | 0 | 0 | idem | 33 (33 sous 26.2) | 169 (169) |

D'où viennent les deux coupures du Tome II : de MiKTeX 26.5, pas des correctifs. Témoin
`theoremes/t2-avant-apres.tex` : les chapitres 4 et 5 du Tome II FR (les deux preuves, le `\textsuperscript`
du texte, la figure au `\textsubscript`), compilés deux fois sous 26.5, une fois avec l'ancien préambule (six
erreurs thmtools, `nonstopmode`), une fois avec le préambule commité. Les deux PDF ont 47 pages, 1 046 698
octets, les mêmes mots page à page, et ne diffèrent que par 74 octets : `/CreationDate`, `/ModDate` et `/ID`.
Seul, ce document ne coupe pas « compteurs » (les numéros de chapitre, donc les largeurs des renvois, ne sont
pas ceux du tome) : il montre que les correctifs ne changent rien, pas d'où vient la coupure. Hors des
correctifs, ce qui a changé entre les deux constructions est MiKTeX lui-même (LuaHBTeX 1.24.0 vers 1.25.7,
noyau, pgf) ; je n'ai pas isolé lequel. Le « ■ » devenu extractible est l'indice que la sortie des caractères
mathématiques a changé dans le moteur.

## 5. Ce qui pourrait être faux
- La justesse sous une version plus ancienne n'est vérifiée que par simulation (crochet retiré, commande ôtée),
  pas sous un vrai MiKTeX 26.2 : il n'est plus sur la machine.
- Si une version future de thmtools cesse de faire son propre alias, le noyau fera le sien (registre différent
  de rien : `\c@x` n'existe pas encore) et l'enveloppe le laisse passer : correct, mais non éprouvé.
- Si les premiers soins changent encore (autre étiquette de crochet, autre commande), le correctif peut devenir
  inutile ou insuffisant ; l'erreur reviendrait alors, visible (`-halt-on-error`), pas silencieuse.
- Cause B : le mécanisme est lu dans le noyau et dans le contexte de l'erreur, mais la condition exacte sur les
  tailles n'est pas isolée (le document court `tikz-indice.tex` ne reproduit pas l'erreur). Le remède est
  éprouvé sur le cas qui tombait et sur les quatre tomes, pas sur toutes les combinaisons de tailles. Une
  autre commande du noyau qui appellerait `\check@mathfonts` hors des maths dans un nœud TikZ (je n'en connais
  pas d'autre dans nos sources) tomberait de même.
- Le correctif B redéfinit deux commandes du noyau, mot pour mot plus une paire d'accolades. Si une version
  future du noyau change leur corps, notre définition masquera la sienne tant que `\textsuperscript@offset`
  existe. À relire à chaque montée de MiKTeX.
- « Même mise en page » est prouvé mot à mot et page à page (pdftotext), et à l'octet près sur les chapitres 4
  et 5 du Tome II ; ce n'est pas une comparaison de pixels des quatre tomes avant et après (impossible pour le
  Tome II : sans correctif B, il ne se construit pas sous `-halt-on-error`).
- La lecture « mémoire de la machine » pour la chute du pilote construction EN est une hypothèse : relancé
  seul, il passe ; je n'ai pas reproduit la chute.
- Je n'ai rien changé à `JUGEMENT-figures2-*.md` ni à `REPRISE-figures.md` : la phrase « le préambule commun
  lève six erreurs » y reste vraie de l'état d'avant ; c'est à l'orchestrateur de dire qu'elle est levée.

## 5 bis. Les outils et les journaux

Commités sous `memoire/outils/preambule-26-5/` (les sorties restent sous `memoire/essai/construction-tomes/`,
ignoré par git) :
- `construire-tomes.sh` : un tome par langue, `latexmk -lualatex -outdir`, nom de travail distinct ;
- `verifier.py` : erreurs, fatales, manques, rerun, boîtes trop pleines, pages, biber, d'un journal ;
- `comparer.py` : deux PDF mot à mot, page à page ; `entrees.py` : entrées d'une construction changées dans
  git depuis le commit d'un PDF ;
- les documents d'essai : `preambule-minimal.tex` (§ 6), `tikz-indice.tex`, `tikz-contexte.tex`,
  `t2-avant-apres.tex`, `theoremes-avant-apres.tex` (ce dernier, le même témoin sur les chapitres 4 et 6 du
  Tome I, a été lancé mais pas mené au bout avant la fin de mon tour : son résultat n'est pas publié ; le
  Tome I étant identique mot à mot au PDF commité de 26.2, il n'est pas nécessaire à la conclusion).

## 6. Le document minimal, texte entier

`memoire/essai/preambule-minimal.tex`, tel que compilé :

```latex
% Document minimal : l'erreur « \c@proposition already defined » du préambule commun sous MiKTeX 26.5,
% et son correctif. Même ordre que memoire/commun/preambule.tex : amsthm, hyperref, cleveref, thmtools.
% Depuis memoire/essai/construction-tomes/minimal/ (deux passes chacune) :
%   lualatex -jobname=m-erreur       "\input{../../preambule-minimal.tex}"                       l'erreur
%   lualatex -jobname=m-sans-thmtools "\def\SANSTHMTOOLS{1}\input{../../preambule-minimal.tex}"  témoin : amsthm seul
%   lualatex -jobname=m-sans-sibling  "\def\SANSSIBLING{1}\input{../../preambule-minimal.tex}"   témoin : sans sibling
%   lualatex -jobname=m-corrige       "\def\CORRIGE{1}\input{../../preambule-minimal.tex}"       le correctif
%   lualatex -jobname=m-ancien        "\def\ANCIEN{1}\def\CORRIGE{1}\input{../../preambule-minimal.tex}"
%       noyau d'avant simulé : sans les premiers soins d'amsthm ni \newcounteralias, correctif en place.
%   lualatex -jobname=m-doublon       "\def\DOUBLON{1}\def\CORRIGE{1}\input{../../preambule-minimal.tex}"
%       témoin qui doit tomber : deux vrais défauts d'alias, que le correctif ne doit pas taire.
\ifdefined\ANCIEN
  \RemoveFromHook{package/amsthm/after}[firstaid/aliascounter]
  \let\newcounteralias\undefined
\fi
\documentclass{scrbook}
\usepackage{amsthm}
\usepackage{hyperref}
\usepackage[french, nameinlink, noabbrev]{cleveref}
\ifdefined\SANSTHMTOOLS
  \newtheorem{theoreme}{Théorème}[chapter]
  \newtheorem{proposition}[theoreme]{Proposition}
  \newtheorem{lemme}[theoreme]{Lemme}
\else
  \usepackage{thmtools}
  \ifdefined\CORRIGE
    % Les lignes du correctif, telles que dans memoire/commun/preambule.tex.
    \ifdefined\newcounteralias
      \let\AliasCompteurNoyau\newcounteralias
      \renewcommand*{\newcounteralias}[2]{%
        \ifcsname c@#1\endcsname
          \expandafter\ifx\csname c@#1\expandafter\endcsname\csname c@#2\endcsname
          \else\AliasCompteurNoyau{#1}{#2}\fi
        \else\AliasCompteurNoyau{#1}{#2}\fi}
    \fi
  \fi
  \ifdefined\SANSSIBLING
    \declaretheorem[numberwithin=chapter, name=Théorème]{theoreme}
    \declaretheorem[numberwithin=chapter, name=Proposition]{proposition}
    \declaretheorem[numberwithin=chapter, name=Lemme]{lemme}
  \else
    \declaretheorem[numberwithin=chapter, name=Théorème]{theoreme}
    \declaretheorem[sibling=theoreme, name=Proposition]{proposition}
    \declaretheorem[sibling=theoreme, name=Lemme]{lemme}
  \fi
  % Témoin : le correctif ne doit taire que l'alias déjà fait. Un vrai doublon (lemme sur chapter)
  % et un compteur absent doivent encore lever leur erreur (deux erreurs attendues).
  \ifdefined\DOUBLON \newcounteralias{lemme}{chapter}\newcounteralias{zzz}{absent}\fi
  \ifdefined\AliasCompteurNoyau \let\newcounteralias\AliasCompteurNoyau \fi
\fi
\crefname{theoreme}{théorème}{théorèmes}
\crefname{lemme}{lemme}{lemmes}
\crefname{proposition}{proposition}{propositions}
\begin{document}
\chapter{Un}
\begin{theoreme}\label{t}A.\end{theoreme}
\begin{proposition}\label{p}B.\end{proposition}
\begin{lemme}\label{l}C.\end{lemme}
\begin{proposition}\label{p2}D.\end{proposition}
RENVOIS : \ref{t}, \ref{p}, \ref{l}, \ref{p2} ; \cref{t}, \cref{p}, \cref{l}, \cref{p2}.
\chapter{Deux}
\begin{lemme}\label{l2}E.\end{lemme}
SUITE : \cref{l2}.
\end{document}
```
