# Tome III, figures, second flux : reprise du rôle « construction » (2026-10-27)

Rôle : corriger le lot « construction » du premier flux (ch. 8 à 10). Fichiers du rôle, et eux seuls :
`memoire/figures/tome3/{codon,synonyme,juge}-figures.tex`, `memoire/outils/tome3_{codon,synonyme,juge}.py`,
données `memoire/figures/tome3/donnees/{codon,synonyme,juge}-*`. Aucune mesure lancée (ni passe du modèle, ni
carte). Style télégraphique.

## Fait
- Palette et convention G9 portées dans les trois fichiers : `\input{\Racine/figures/tome3/legende-tome3}` dans
  chaque garde ; `\Titre`, `\Legende` (tête en gras, provenance, texte), `\Source` pour chaque figure ; couleurs et
  styles `t3` du dictionnaire (20b/120b, v1.0/v1.2/compagnon, frontière/λ = 1/λ = 0/Q2_0/exact, R1/neuves, seuil,
  cassure, hors domaine) ; `t3 graphe`, `t3 decimales`, `t3 etiquette` (halo), `t3 sans cesure`, plancher
  `\scriptsize`.
- Graves du juge des chiffres : G1 (III-9.3, un seul axe tiré des données, le script s'arrête si un point ou une
  bande sort ; fenêtre 7 de R1 visible à +0,061), G2 (III-8.8, axe 4 à 12 % tiré des données, l'expert à 11,68 %
  dessiné et nommé), G3 (III-9.1 : phrase retirée ; les deux aires tracées et chiffrées, 0,32 et 0,17 ; le
  sur-apprentissage dit par le rapport des coûts, ×1,67 contre ×0,975), G4 (III-9.2 : trois positions au-dessus
  de chaque 99,9e centile ; −3,4 / −20,8 % et −17,2 / −15,9 % sur R1 / neuves ; comparaison λ = 0 contre λ = 1
  dite non faisable), G5 (III-9.3 : panneau 1 des neuves dit à deux chemins, indicatif, losanges creux ; le mélange
  déplace d̄ de 0,0014 sur R1).
- Graves de dessin : G3 (axe commun), G4 (traits du dictionnaire, axe 10⁻² à 10¹, médianes et centiles à la marque
  de leur série, rappel « ÷ 2,66 »), G6 (III-8.6 scindée : `CodonJalon` (a)(b), `CodonJalonBis` (c)(d) ; une clé
  dans (c), passes en points noirs ; titre de l'encart sous son cadre ; « ≥ ×1,394 »), G7 (III-9.6 : cadre 2,54
  à 2,72 bits et 0,08 à 0,36 de KL, tiré des données ; Q2_0 et le moteur exact en repères de marge, hors du cadre).
- Reçu de III-7.1 : l'axe sans perte en panneau (c) de III-8.5 (3,8434 → 3,7064 → 3,6844 ; témoin : les moyennes
  redonnent `k10/frontiere.csv`).
- Mineurs faits : M1 (roue sur les 72 tenseurs, témoin : code 8 = `moins_zero_fondus`), M2 (valeurs OCP, pas égal,
  épaisseur affine ×1,88), M3 (encart : toutes les barres des rapports écrits ; 0,981 médianes et 0,980 moyennes),
  M4 (motif « ≥ », compagnon frontière, étage disque B/A 1,370), M6 (cases de l'en-tête au décalage juste), M7
  (amortissement 0,41, 433 valeurs propres), M9, M11 (bits utiles 3,86 pour l'exact ; « la seule
  requantification » retirée), M12 (511 jetons dont 256 de contexte ; 4 764 un jeu, 9 331 les deux ; portée de
  « aucune KL » dite), M13 (écart des chemins chiffré : −0,0014 en moyenne, −0,0076 à +0,0010, et 0,0002),
  M14 (« trois à neuf » tiré du script : 3,2 à 8,9), M15 ; D10 à D16, D17, D19, D21, D22.
- Pilote `memoire/essai/pilote-tome3-construction.tex` (ignoré) : 15 figures, FR et EN, deux passes, 0 erreur,
  0 boîte trop pleine, 0 renvoi manquant.

## Décisions (réponses par délégation du 2026-10-27, réversibles)
- III-9.1 : la part cumulée devient (b′), pour laisser (c) à la rangée de 32 poids du lot « espaces latents »
  (l'inventaire range la part cumulée dans (b)).
- III-9.3 : un axe commun plutôt qu'un bandeau d'échelle : le panneau 2 se lit petit, c'est la vérité ; aucune
  flèche au bord n'est plus nécessaire (aucun point hors du cadre, vérifié par le script).
- III-9.1 : calibration en trait plein, évaluation en pointillé, la couleur restant celle de la variante (les
  styles `t3 synonyme` tiretés ne servent pas ici, où le trait dit déjà autre chose).
- III-8.5 : la colonne en `Accent` (hors dictionnaire, dite en légende), le codon du zéro en `CouleurVunDeux`.
- Marques : celles du commun (frontière losange, λ = 1 cercle, λ = 0 carré, exact triangle, Q2_0 pentagone), pas
  celles de D22.
- III-8.8 : les tailles des fichiers sous les barres ; les parts du fichier en légende de l'axe (deux tirets).

- Commits : 3275a6c (figures, scripts, données, cette note) ; cadf276 (`genome/construction-codon-pour-le-memoire.md`,
  § 3 et § 5 F6 barrés et corrigés, renvoi à JUGEMENT-placement, comme 06 § 8 et JUGEMENT-construction § 6) ;
  puis typographie anglaise (D30 : `\Pourcent`, `\Pv` dans les lignes « Données ») et cette note.

## Reste (hors de ce rôle, ou non fait, et pourquoi)
- III-9.1 assemblée : le panneau (c) du lot « espaces latents » (couleurs G1, pas de 200, D18) reste à ce lot ;
  ici (a)(b)(b′) suivent le dictionnaire et le pas de 500.
- III-7.1 garde encore son axe sans perte tant que le lot « ronde » ne l'a pas retiré (G10) : III-8.5 (c) le porte
  désormais.
- M4 : la KL du compagnon frontière du 120b (« proxy 0,14 » du juge) n'est pas écrite : aucun fichier commité lu
  par ce lot ne la porte ; la légende dit « avec perte » et renvoie à III-9.6.
- M16 : `REPRISE-figures-construction.md` (premier flux) dit « 17 figures » pour 14 ; fichier hors de la liste de
  ce rôle, non barré.
- Un juge des chiffres et un juge de design du second flux doivent relire ce qui a changé (nombres neufs des trois
  `*-nombres.tex`, nouvelles bornes d'axes, III-8.6 bis, III-8.5 (c)).

## Pièges
- Pas de `\num` dans `xticklabels` (« \def cs{...} » à la compilation) : poser un nœud sous l'axe.
- `select coords between index` n'existe pas dans cette version de pgfplots : `restrict expr to domain={\coordindex}{i:i}`.
- `\textprime` absent en TU : `$'$`.
- Dans un axe, `($(axis cs:…)+(…)$)` se place mal : `yshift` sur le nœud.
