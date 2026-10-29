# Lot F : dérivations, en entier

Ce que le code du lot F suppose, démontré pas à pas pour le mémoire. Notations du § 4.9 :
M = 2¹² (probabilités), L = 2¹⁶ (borne basse), mots de b = 16 bits, état x entier.
Un symbole s a une fréquence f = f[s] ∈ [1, M] et un cumul c = c[s] ; Σ f = M.

## 1. Le pas rANS et son inverse

Codage de s depuis l'état x' : `C(s, x') = ⌊x'/f⌋ · M + (x' mod f) + c`.
Décodage depuis x : fente `i = x mod M`, symbole s tel que `c ≤ i < c + f`, puis
`D(x) = f · ⌊x/M⌋ + i − c`.

**Lemme 1 (inverse exact).** Pour tout x' ≥ 0, `D(C(s, x')) = (s, x')`.

Posons q = ⌊x'/f⌋ et r = x' mod f, donc x' = q f + r avec 0 ≤ r < f. Alors
C = q M + (r + c) avec 0 ≤ r + c < c + f ≤ M : la fente vaut i = r + c ∈ [c, c + f), donc le
symbole lu est s ; et ⌊C/M⌋ = q. D'où D = f q + (r + c) − c = q f + r = x'. ∎

## 2. L'intervalle des états et la renormalisation

Invariant : avant et après chaque symbole, sur chaque voie, x ∈ I = [L, 2³²).

**Codeur.** Avant de coder s depuis x ∈ I : si x ≥ f · 2²⁰, il émet le mot `x mod 2¹⁶` et pose
x' = ⌊x / 2¹⁶⌋ ; sinon x' = x. Puis x ← C(s, x').

**Lemme 2.** Avec cette règle, x' ∈ [f · 2⁴, f · 2²⁰) et C(s, x') ∈ I.

- Sans émission : L ≤ x < f · 2²⁰. Or f · 2⁴ ≤ M · 2⁴ = 2¹⁶ = L ≤ x : x' = x ∈ [f · 2⁴, f · 2²⁰).
- Avec émission : f · 2²⁰ ≤ x < 2³², donc x' = ⌊x/2¹⁶⌋ ∈ [f · 2⁴, 2¹⁶). Et 2¹⁶ ≤ f · 2²⁰
  puisque f ≥ 1 : x' ∈ [f · 2⁴, f · 2²⁰).
- C(s, x') ≥ ⌊x'/f⌋ · M ≥ 2⁴ · 2¹² = L, et C(s, x') < (⌊x'/f⌋ + 1) · M ≤ 2²⁰ · 2¹² = 2³². ∎

**Décodeur.** Depuis x ∈ I, y = D(x) ; si y < L, il lit un mot w et pose x ← y · 2¹⁶ + w ;
sinon x ← y.

**Lemme 3 (une lecture suffit, et le décodeur lit exactement quand le codeur a émis).**
Par le lemme 1, y est le x' du codeur. Si le codeur a émis, x' < 2¹⁶ = L : le décodeur lit, et
y · 2¹⁶ + w reconstitue exactement le x d'avant l'émission (w = x mod 2¹⁶), qui est dans I. Si
le codeur n'a pas émis, x' = x ≥ L : le décodeur ne lit pas. Les deux décisions sont donc les
mêmes, pas à pas. ∎

## 3. Les deux contrôles gratuits d'une tuile

Le codeur parcourt les symboles d'une tuile dans l'ordre exactement inverse de celui du décodeur
(macro-pas, sous-pas, voies décroissants), part de x = L sur chaque voie, empile ses mots, puis
renverse la pile.

**Proposition 4.** Sur un flux intègre, le décodeur (a) finit chaque voie sur x = L ;
(b) consomme exactement les `début[t+1] − début[t]` mots de la tuile t.

(a) Par récurrence sur les pas inverses, avec le lemme 3 : l'état du décodeur après le k-ième
symbole décodé égale l'état du codeur avant le codage de ce symbole ; après le dernier symbole
décodé (le premier codé), c'est l'état initial du codeur, L.

(b) Par le lemme 3, le décodeur lit un mot à chaque pas où le codeur en a émis un, et seulement
là ; le nombre total de lectures est donc le nombre d'émissions, qui est la taille de la pile de
la tuile, c'est-à-dire `début[t+1] − début[t]`. L'ordre des lectures entre voies est l'ordre des
émissions renversé : les 32 voies partagent la pile parce que l'ordre inverse du codeur, renversé
par la pile, est exactement l'ordre direct du décodeur. ∎

Ni (a) ni (b) ne garde la table : un décodeur qui lit une table faussée reste dans I et peut
finir sur L par hasard. C'est pourquoi le format porte les empreintes des tables et des parties
(§ 4.12). Le témoin du témoin de F1 l'a vérifié sur le code : retirer le compte des voies, ou le
compte des mots, fait tomber un test chacun (`casser-temoins-f1.log`) ; la passe 1 avait montré
qu'un test qui ne regardait que leur conjonction ne voyait pas la perte du premier.

## 4. Le contexte connu du décodeur

**Proposition 5.** Si le contexte k(n) du symbole n est une fonction de données que le
décodeur possède avant de décoder n (les δ déjà décodés pour la table par voie ; la base et les
compléments déjà décodés pour la table par symbole), le décodage reste exact, et le nombre de
bits émis est Σ_n −log₂(f_{k(n)}[s_n] / M) à l'en-tête près.

Exactitude : le lemme 1 vaut pour toute table ; le codeur et le décodeur appliquent au symbole n
la même table puisqu'ils calculent le même k(n) (le codeur depuis la source, le décodeur depuis
ce qu'il a déjà rendu, identique par récurrence). Taux : un pas de codage multiplie l'état par
M / f à l'arrondi près (x' ↦ ≈ x' · M / f), et chaque mot émis retire 16 bits ; le nombre de mots
est donc, à une constante par voie près, Σ log₂(M / f) / 16. ∎

Pour la table par voie, le contexte du mot w est κ(⌊w/4⌋) : les quatre mots d'un bloc (16
octets) sont produits par quatre voies voisines du même macro-pas, et toutes les voies d'un
sous-pas lisent leur table dans le même jeu de trois LUT. Il n'y a ni réassemblage ni somme
préfixe à faire (contre les trois flux de classe de 03).

## 5. La classe d'échelle des blocs de bourrage

Une matrice de R · B blocs donne P_δ = ⌈R·B / 128⌉ · 128 octets de δ et P_q = ⌈16 R B / 128⌉ ·
128 octets de codes, soit ⌈R·B / 8⌉ · 8 blocs. Comme ⌈R·B/8⌉ · 8 ≤ ⌈R·B/128⌉ · 128, tout bloc de
bourrage des codes a un δ décodé, qui vaut 0 (bourrage), donc κ = 0. Le codeur bourre de même et
compte ces octets dans les tables ; le décodeur n'a aucune règle de plus à connaître. Pour
gpt-oss : R · B = 2 880 × 90 = 259 200 = 2 025 × 128, aucun bourrage.

## 6. L'expert d'origine dans le GGUF

Le tenseur `blk.ℓ.ffn_*_exps.weight` a pour dimensions ggml [C, R, E] : ne₀ = C (poids d'une
ligne), ne₁ = R (lignes), ne₂ = E (experts), rangé ne₀ le plus rapide. Une ligne de C poids MXFP4
fait B = C/32 blocs de 17 octets. Le bloc b de la ligne r de l'expert x est donc le bloc
`(x · R + r) · B + b` du tenseur (§ 4.11), et l'expert x occupe les octets
`[17 x R B, 17 (x+1) R B)`, d'un seul tenant. De même ses biais (tenseur F32 [R, E]) occupent
`[4 x R, 4 (x+1) R)`. L'empreinte d'origine se calcule donc sans rien réordonner :
SHA-256(gate_x ‖ up_x ‖ down_x ‖ biais_gate_x ‖ biais_up_x ‖ biais_down_x), ses 8 premiers
octets. Le codeur la calcule sur les tranches du GGUF, la vérification la recalcule sur
l'expert décodé et sur les tranches, indépendamment.

## 7. Le taux, comptabilité et ce qui le sépare de 03

r₀₃ = (17 · R · B octets d'origine par matrice) / (MEDIANES + DELTA + CODES_CTX tels que
rangés). Par rapport à l'étude 03, qui codait un tenseur entier en un flux par classe :
- la table par voie au lieu des trois flux réassemblés : −0,008 % d'octets (F1, S2) ;
- un flux par matrice d'expert au lieu d'un flux par tenseur : chaque flux recommence ses
  tuiles ; R·B·16 / 128 = 32 400 macro-pas, soit 126,6 tuiles de 256 : une tuile partielle de
  plus par flux, c'est-à-dire au plus 4 + 128 octets d'en-tête de tuile et d'états, plus 16
  octets d'en-tête de flux et au plus 15 de bourrage, sur ≈ 4,1 Mo : moins de 0,005 % ;
- les tables par (couche, matrice) ne sont pas comptées dans r₀₃ (03 ne les comptait pas) ;
  elles le sont dans `bpp_avec_tables`.

## 8. Le codeur à deux passes : mêmes octets, mémoire bornée

**Notation.** Une couche a E experts ; pour la matrice j, l'expert x donne la préparation
P_j(x) = (médianes, δ, qs) (fonction de ses seuls blocs d'origine), et des comptes
N_j(x) = (histogramme de δ, histogrammes des codes par classe κ), vecteurs d'entiers.

**Proposition 6 (identité).** Les octets écrits par le codeur à deux passes sont ceux du codeur
à une passe.

1. *Les comptes.* À une passe : N_j = Σ_x N_j(x), sommé par un repli parallèle dans un ordre
   quelconque. À deux passes : N_j = Σ_paquets Σ_{x ∈ paquet} N_j(x). L'addition d'entiers
   (u64, sans débordement : au plus E · R · B · 16 ≈ 5,3·10⁸ par case pour le 120b) est
   associative et commutative : les deux N_j sont égaux.
2. *Les tables* sont une fonction déterministe de N_j (`ComptesMatrice::tables`, règle
   d'arrondi du § F1) : égales.
3. *Un tronçon* est une fonction de (P_0(x), P_1(x), P_2(x), biais de x, tables de la couche) ;
   P_j(x) se recalcule à la seconde passe depuis les mêmes octets (§ 6 : le bloc β de x est au
   bloc (x · R + r) · B + b, d'un seul tenant pour x fixé) : mêmes tronçons.
4. *L'ordre d'écriture* est (couche, expert) dans les deux cas (paquets dans l'ordre, résultats
   d'un paquet recueillis dans l'ordre de x par `collect` de rayon) : mêmes décalages, même
   répertoire, mêmes empreintes, même en-tête. ∎

L'empreinte d'origine de x, calculée à une passe par un hacheur incrémental par expert nourri
matrice après matrice puis biais après biais, et à deux passes d'un seul appel sur la suite
(blocs_0, blocs_1, blocs_2, biais_0, biais_1, biais_2), porte sur la même suite d'octets :
SHA-256 ne dépend que de la suite, pas de son découpage en appels.

**Témoin.** Le 20b recodé doit avoir la SHA-256 du fichier de F2, calculée par `Get-FileHash`
(chemin indépendant de notre code). Cassure : la copie au bit retourné de F2 doit différer.

**Proposition 7 (mémoire).** Avec p = 2 · fils experts par paquet, la pointe de la boucle des
experts est bornée par

  p · (Σ_j 17 R_j B_j)            les blocs lus d'un paquet (3 matrices)
+ p · (Σ_j (16 + 1) R_j B_j)      les préparations en vol (au plus une par fil et par matrice
                                    pendant le codage, p en passe 1)
+ p · T_max                       les tronçons assemblés du paquet
+ 3 · 4 R E                       les biais de la couche
+ 2 · 16 Mio                      le rebond d'une lecture sans tampon et le morceau recopié,

où seul le terme des biais dépend de E. Pour gpt-oss (R = 2 880, B = 90, T_max ≈ 12,1 Mo), p = 12 :
12 · 13,2 Mo + 12 · 13,2 Mo + 12 · 12,1 Mo + 3 · 4 · 2 880 · E + 32 Mio ≈ 0,47 Go + 34 560 · E
octets, soit +1,1 Mo pour le 20b (E = 32) et +4,4 Mo pour le 120b (E = 128). La version à une
passe gardait en plus 3 · E · 4,4 Mo de préparations : 0,42 Go (20b), 1,69 Go (120b). Le
répertoire (64 · L · E octets) et les tables (520 · 12 · L octets) croissent avec le modèle mais
restent sous 0,5 Mo. **D'où le seuil déclaré** : pointe 120b ≤ 1,25 × pointe 20b.

**Le prix.** Les experts sont lus deux fois : 2 × 61,0 Go sur le 120b au lieu de 61,0 Go, soit
~~≈ 24 minutes de plus~~ **≈ 24 secondes de plus** (61,0 / 2,58 = 23,6 s ; l'unité était fausse,
barrée le 2026-10-15 à 21 h 10 en relisant ce paragraphe) au débit séquentiel du disque
(2,58 Go/s, [mes. 01]) si la lecture ne recouvre pas le calcul (ici elle ne le recouvre pas :
lecture d'un paquet, puis codage). Le codage du 120b a duré 1 153 s en tout : la seconde lecture
y pèse au plus 2 %, le rANS du processeur fait le reste.


## 9. Le second chemin de C1 : ce que prouvent des égalités d'empreintes

**Notation.** G(x) les octets de l'expert d'origine x lus dans le GGUF (§ 4.11), D(x) l'expert
décodé du tronçon, r(x) l'empreinte64 rangée au répertoire, h = empreinte64 (§ 4.12).

**Les deux chemins.** Le premier (`trc-codeur verifier`) établit h(D(x)) = r(x) et D(x) = G₁(x)
octet pour octet, où G₁ est lu par `gguf::lire_dans`, la fonction même du codeur. Le second
(`second_chemin_c1.py`) établit h(G₂(x)) = r(x), où G₂ est lu par un autre programme, à des
décalages que deux lecteurs indépendants (Python, llama.cpp) rendent égaux.

**Proposition 8.** Si h(D(x)) = r(x) et h(G₂(x)) = r(x), alors h(D(x)) = h(G₂(x)) : D(x) ≠ G₂(x)
exigerait une collision de h sur ce couple.

**Borne.** Pour une erreur qui n'est pas construite contre SHA-256 (un décalage, un ordre de
matrices, un bit retourné), on modélise h comme une fonction aléatoire sur 64 bits : la
probabilité qu'un couple distinct donné ait la même image vaut 2⁻⁶⁴. Par la borne de l'union sur
les 4 608 experts du 120b :

    P(au moins un expert faux non vu) ≤ 4 608 · 2⁻⁶⁴ = 4 608 / 1,8447·10¹⁹ ≈ 2,50·10⁻¹⁶.

Ce n'est pas une preuve contre un adversaire (le préfixe de 64 bits se casse en 2³² essais par
l'anniversaire, si l'on choisit les deux contenus) ; personne ici ne fabrique les octets du GGUF.

**Pourquoi la comparaison G₂ contre r suffit à exclure une erreur de lecture commune.** Une erreur
systématique de `gguf::lire_dans` (lire la tranche d'un autre expert, d'une autre matrice, à un
décalage faux) rendrait G₁(x) ≠ G(x) pour presque tout x ; le codeur aurait alors rangé
r(x) = h(G₁(x)), et la vérification aurait trouvé D = G₁, à tort. Le second chemin compare r(x)
à h(G₂(x)) : il faudrait que G₂ se trompe exactement comme G₁, c'est-à-dire que deux programmes
sans ligne commune, dont un (llama.cpp) sert de référence au format, se trompent de la même façon.
La cassure `--casser-decalage` montre que le contrôle voit une telle erreur : prendre la tranche
de l'expert x + 1 fait tomber 768 experts sur 768 (20b), 256 sur 256 (120b, couches 0 et 1).

**Les médianes, refaites.** Pour la ligne r d'une matrice à B blocs, les échelles e[rB + b] sont
les octets d'indice 17 (rB + b) de la tranche (le premier octet de chaque bloc MXFP4, § 4.11) ;
la médiane est `tri[B/2]` (§ 4.10) : pour B = 90, le 46ᵉ plus petit des 90 octets (indice 45).
Le flux MEDIANES_j étant brut, il se compare octet pour octet, sans décoder.

**La lecture sans tampon.** Le GGUF est lu avec `FILE_FLAG_NO_BUFFERING` : chaque requête
commence et finit sur un multiple de 4 096 (décalage arrondi en dessous, fin arrondie au-dessus,
dans un tampon dont l'adresse est elle aussi un multiple de 4 096), et l'outil rend la vue
[décalage, décalage + n) de ce tampon. Deux raisons : aucune page du cache du système n'est prise
aux mesures d'un autre agent ; et l'octet comparé est celui du disque, pas une copie en cache qui
aurait pu servir au codeur.

**Durées, pour information (pas d'ABBA, aucun seuil).** 120b : SHA-256 de 63,39 Go en 101,3 s
(0,63 Go/s : une seule voie de `hashlib` [hyp. : c'est elle qui borne ce débit, non mesuré]) ; 4 608 experts en 278,2 s (13,25 Mo
du GGUF et 12,03 Mo du `.trc` en moyenne par expert, soit 116,5 Go lus en tout, ≈ 0,42 Go/s : les médianes
en Python pur, sous le verrou global de l'interpréteur, dominent [hyp., non mesuré]) ; pointe de l'ensemble de
travail 0,27 Go (20b : 0,26 Go).
