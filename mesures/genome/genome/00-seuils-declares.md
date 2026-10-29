# Seuils déclarés avant la mesure (sujet genome, 2026-10-16)

Écrits et commités **avant** toute mesure d'une recette sur les poids réels. Seule mesure faite avant :
le témoin S0 de la frontière (`frontiere.json`), qui ne juge aucune recette.

## La frontière (rappel, fichiers commités)

- Sans perte : A_ctx, **3,8431** bits par poids (F1, `decisions/journaux/arbitre/decoupe-gptoss20b.json`).
- Base seule de B : **2,6441** bits par poids lus (F1, en-têtes, tables, δ et médianes compris) à
  **4,2920 %** d'erreur quadratique relative (07 § 4.2), sur les 12 tenseurs de F1 (couches 0, 8, 16, 23 ×
  gate, up, down de gpt-oss-20b). Par tenseur : `f1-par-tenseur.csv` (base + δ + 8/2880 de médianes +
  0,00007 de tables).

## Témoins

- **S0** (fait) : la base refaite par un second chemin (comptes exacts (e, code) des 12 tenseurs entiers,
  centres recalculés) retrouve 0,042919745124980 à 10⁻⁶ relatif. Cassure : chaque classe lit le centre de la
  suivante, l'écart doit dépasser 10⁻⁶. *Résultat : tient (5,8·10⁻¹⁵) ; la cassure tombe (×27).*
- **T1** (lecture par codons, source connue) : sur une source gaussienne i.i.d. (128 rangées de 2 880), le
  treillis l = 12, kb = 2, v = 1, q = 8, table gaussienne sans apprentissage, doit rendre une erreur
  quadratique moyenne dans **[0,0625 ; 0,080]**. Bas : 2^(−2·2) = 0,0625 est la borne de Shannon, la battre
  dénoncerait une faute de comptabilité. Haut : 0,080 est le milieu entre le treillis publié à l = 16
  (0,069, QTIP tableau 1) et le meilleur quantificateur vectoriel de dimension 8 publié (E8P, 0,089) : un
  treillis plus mauvais que cela ne vaudrait pas mieux qu'un réseau de dimension 8 et l'instrument serait
  suspect. Cassure : table nulle, l'erreur doit valoir ≈ 1 et sortir de l'intervalle.
- **T2** (comptabilité des bits) : le brin écrit puis relu par le seul décodeur rend la reconstruction dont
  l'erreur est comptée (tests `brin_ecrit_puis_lu_*`, tiennent à la construction).
- **T3** (recette littérale) : un bloc engendré exactement par une graine et des coefficients quantifiables
  se retrouve à erreur nulle (test `bloc_engendre_retrouve_exactement`) ; le LFSR a la période 65 535
  (test `periode_maximale`).

## Le critère « marche » (W), déclaré

Une recette **marche** si, sur l'échantillon (experts 0, 8, 16, 24 de chacun des 12 tenseurs ; rangées
entières), **à l'erreur quadratique relative de la base mesurée sur les mêmes rangées**, elle lit
**moins de bits par poids** que la frontière F1 du même tenseur, **sur chacun des 12 tenseurs** (test du
signe : une recette sans effet passerait les 12 avec une probabilité 2⁻¹² ≈ 2,4·10⁻⁴), et en global.

Tout ce que la recette lit est compté : le brin, la fenêtre initiale, l'indice de forme de la rangée
(3 bits), σ de la rangée (16 bits) quand elle sert, les échelles E8M0 (δ + médianes de F1) quand elles
servent, les tables (2^q valeurs de 16 bits par forme et par tenseur de 32 experts), et l'alignement de
chaque matrice d'expert sur 4 096 octets au pire (32 768 / 8 294 400 = 0,0040 bit par poids).

Le débit à erreur égale se lit sur la courbe débit-distorsion de la recette (allocation lagrangienne par
rangée), par interpolation linéaire en log(erreur) entre deux points voisins.

## Sortie d'une couche d'experts (O), déclaré

Sur des entrées réelles (états normalisés des couches 0, 8, 16, 23 capturés par la référence f64), pour les
experts de l'échantillon : erreur relative de la sortie de l'expert (projection down, biais compris)
Σ‖y − ŷ‖² / Σ‖y‖² sur les jetons routés vers lui. La recette au point de fonctionnement retenu doit faire
**au plus** l'erreur de sortie de la base, couche par couche (4 sur 4).

## Divergence KL (K), si elle est mesurée

KL(référence ‖ recette substituée) moyenne sur les positions, appariée contre KL(référence ‖ base
substituée) aux mêmes couches et mêmes positions : la recette doit faire moins, par le test du signe sur
les positions (p < 0,01).

## Transcription (C)

Coût de décodage en opérations par poids ≤ budget × octets lus par poids, budget = 214 opérations par
octet compressé (01-machine) ; le Tome II a corrigé ce budget à 926 au débit du disque (m12), les deux sont
dits.

## Le complément exact (L)

Recette + H(code | case de la reconstruction de la recette) + échelles : la combinaison « marche » sans
perte si elle lit moins que A_ctx du même tenseur. Attendu, par la règle de chaîne
(H(X) ≤ H(Y) + H(X | Y) pour Y fonction des bits de la recette) : elle ne le peut pas, sauf structure
que le contexte de A ne voit pas. Le seuil reste celui-là.

## Précision de l'échantillon (ajoutée avant la première passe sur les 12 tenseurs, 2026-10-16)

Le coût du Viterbi (l = 12 : ≈ 230 000 poids par seconde et par forme sur les 16 fils) impose une rangée
sur quatre : rangées r ≡ 0 (mod 4) des experts 0, 8, 16, 24, soit 720 rangées entières par expert,
34 560 rangées et 99,5 millions de poids sur les 12 tenseurs. Les tables (code génétique) s'apprennent
par Lloyd (2 itérations) sur les 48 premières rangées échantillonnées de chaque expert ; elles sont
comptées dans les bits. Formes : (kb, v) = (2, 1), (7, 3), (5, 2), (8, 3), (3, 1), soit 2 ; 2,33 ; 2,5 ;
2,67 ; 3 bits par poids. Un essai de rodage (couche 0, 64 rangées par expert, `--entrainement 16`) a
été fait avant cette précision pour vérifier l'outil ; il n'entre pas dans le verdict.

## Protocole de la sortie et de la KL (ajouté avant ces passes, 2026-10-16 vers 23 h 45)

- **O** : `genome sortie --norme tourne`, experts 0, 8, 16, 24 des couches 0, 8, 16, 23 ; entrées = les
  512 premières positions routées vers l'expert dans la capture « eval » de l'éclaireur (fenêtres 0 à 9
  du .kld de R1, référence f64 arrondie en f32) ; les tables et λ sont ceux de l'échantillon (CSV de la
  passe `codons tourne`), donc **aucun réglage sur ces entrées**. Deux répartitions au même nombre de
  bits sur l'échantillon : « energie » (le point du critère W) et « relatif » (chaque rangée minimise son
  erreur relative + λ · bits). Verdict O par couche (4 sur 4) et par expert, et test du signe sur les
  positions (la recette gagne sur plus de la moitié des positions, p < 0,01 par la loi binomiale).
- **Témoin de la fourche KL** : sans expert substitué, une fenêtre : la KL contre `ref-openai-20b.kld`
  doit être ≤ 10⁻⁹ (mêmes opérations que la référence).
- **K** : les 16 experts ci-dessus substitués (F32) dans la référence f64, 6 fenêtres (3 066 positions) ;
  `juge comparer --verite ref --a base --b recette` : la recette **fait mieux** si KL_recette < KL_base et
  la différence appariée d̄ = KL_recette − KL_base vérifie d̄ < −2 σ(d̄) ; **égale** si |d̄| ≤ 2 σ(d̄) ;
  **pire** sinon.

## Ce que la première sortie a dit, et le protocole qui en découle (2026-10-17 vers 0 h 10)

**Observé** (couche 0, expert 0, 499 positions « eval », `sortie-tourne-point-W-interrompu.log`) : au point
du critère W (erreur de poids 4,25 % contre 4,27 % pour la base, 2,30 bits), l'erreur de **sortie** de
la recette est **7,63 %** contre **6,77 %** pour la base (la recette ne gagne que sur 146 positions sur
499) ; la répartition « relative » au même débit fait pire (10,05 %). **Le critère O, tel que déclaré
(au point W), tombe sur ce premier expert.** La passe a été arrêtée là (les 15 autres experts au point W
ne sont pas mesurés) pour mesurer ce qui décide vraiment : la fidélité en fonction du débit.

**Protocole F (fidélité), déclaré avant sa passe** : `genome fidelite`, experts 0 et 16 des couches 0,
8, 16, 23 (8 experts). Pour chaque expert, deux variantes du brin : **uniforme** (Viterbi non pondéré,
comme W) et **pondérée** (Viterbi pondéré par h = diag(R Σ Rᵀ), Σ = E[x xᵀ] estimée sur la capture
« calib », fenêtres 10 à 21 : 1 024 positions routées au plus ; pour down, x = l'activation
intermédiaire calculée par les poids exacts). Cibles de débit par matrice : 2,0 ; 2,2 ; 2,4 ; 2,64 ;
2,9 bits par poids (σ et indices compris). Mesure sur la capture « eval » (fenêtres 0 à 9, 512 positions
au plus) : aucune entrée de mesure ne sert au réglage.

**Verdict F** : la recette pondérée **marche en sortie** si, à **2,64 bits ou moins** (le débit de la
frontière), son erreur de sortie est **inférieure** à celle de la base **sur chacun des 8 experts**
(test du signe, 2⁻⁸ ≈ 0,004). On rapporte aussi, par interpolation en log(erreur), les bits qu'il faut à
chaque variante pour égaler l'erreur de sortie de la base.

**Témoin de la fourche KL** (fait, 2026-10-17 vers 1 h 15) : sans substitution, une fenêtre, KL contre la
référence = **0** exactement (255 positions notées, même premier choix partout ; `kl/temoin-vide.json`) :
il tient. Il tombera de lui-même dès qu'un expert est substitué (passe « base »).

**Changement déclaré avant la passe K** : 3 fenêtres au lieu de 6 (765 positions notées). Raison : une
fenêtre a pris 13 min sous la charge des autres équipes ; 6 fenêtres × 2 passes dépasseraient 2,5 h. Les
experts substitués sont ceux de la passe F (0 et 16 des couches 0, 8, 16, 23), la recette à 2,64 bits
(variante pondérée, écrite par `fidelite`), la base par `base-f32w`.

## Les exceptions (déclaré avant la passe, 2026-10-17 vers 3 h)

**Observé** : à la couche 8, la recette perd en sortie à 2,64 bits sur l'expert 16 (uniforme 8,93 %,
pondérée 9,41 %, base 7,45 %) et ne gagne que pondérée sur l'expert 0 (7,91 % contre 8,30 % ; uniforme
8,80 %). blk.8.ffn_down a un kurtosis de 343 (§ 6) : quelques poids portent une grande part de l'énergie,
et la base les rend presque exacts (la classe {6} est exacte), le brin non.

**Passe** : `genome fidelite --couches 8 --experts 0,16 --variantes u --exceptions 0.001` : dans chaque
rangée, les ⌈0,001 · 2 880⌉ = 3 poids de plus grande magnitude sont gardés exacts à part (8 bits de compte
+ 3 × 24 bits = 80 bits par rangée, 0,028 bit par poids, comptés), le reste passe par le brin.
**Verdict** : les exceptions « marchent » si, sur ces deux experts, l'erreur de sortie à 2,64 bits
(exceptions comprises) passe sous celle de la base.

## Le brin sur la source brute, pondéré par les entrées (déclaré avant la passe, 2026-10-17 vers 3 h 30)

**Observé en plus** : couche 16, expert 0, uniforme, 2,64 bits : sortie 6,02 % contre 5,72 % pour la base.
Les exceptions (0,1 %) ne changent presque rien à la couche 8 (8,98 % contre 8,80 % sans). Hypothèse :
la rotation mélange les colonnes par 64 ; la pondération diag(R Σ Rᵀ) ne peut plus protéger une colonne
d'entrée précise ; or les entrées réelles concentrent leur énergie sur quelques canaux.

**Passe** : `genome fidelite --norme brut --couches 8,16 --experts 0,16 --variantes up` : source brute
(valeurs E2M1, échelles E8M0 gardées et comptées : δ + médianes de F1), Viterbi pondéré par
4^(e − 128) · h_c, h = diag(Σ) **sans rotation** (Σ sur « calib »), mêmes cibles de débit.
**Verdict** : cette variante « marche en sortie » sur un expert si, à 2,64 bits, son erreur de sortie
passe sous celle de la base ; on la retient si elle le fait sur les experts où la source tournée perd.

## Le système retenu, S* (déclaré avant sa passe, 2026-10-17 vers 4 h)

**Observé** : exceptions 0,1 % à la couche 8, uniforme, 2,64 bits : expert 16, sortie **6,20 %** contre
7,45 % pour la base (105 positions sur 131), poids 3,16 % au lieu de 4,63 % ; expert 0 : 8,98 % (sans
effet). La pondération corrige la couche 8 expert 0 et la couche 16 expert 0 ; les exceptions corrigent la
couche 8 expert 16. **S* = rotation + brin pondéré par diag(R Σ Rᵀ) + exceptions 0,1 %**, les deux
remèdes ensemble.

**Passe** : `genome fidelite --variantes p --exceptions 0.001 --couches 0,8,16,23 --experts 0,16 --ecrire …`
(écrit S* à 2,64 bits pour la KL). **Verdict F(S*)** : à 2,64 bits, erreur de sortie sous celle de la
base sur **chacun des 8 experts** (2⁻⁸). Risque dit d'avance : S* a été choisie après avoir vu 5 experts
sur 8 ; les 3 experts restants (couche 16 expert 16, couche 23 experts 0 et 16) sont le témoin propre ;
la KL (K) sera mesurée sur S*.

**La passe brute pondérée est arrêtée** (2026-10-17 vers 4 h 40) après son premier point (couche 8,
expert 0, uniforme : 11,2 % d'erreur de sortie à 2,64 bits, `fidelite-brut-interrompu.log`) : le
diagnostic par colonne (`erreur-colonnes-ponderee-264.json`) montre que l'erreur de sortie vient des
**colonnes massives** que le brin écrête (blk.8.ffn_down expert 16 : la colonne 1011, ×144 l'énergie
moyenne, reçoit ×334 l'erreur moyenne), ce que les exceptions de S* traitent directement ; la passe brute
ralentissait S* et ne portait plus d'hypothèse ouverte.

**La passe F (uniforme et pondérée, sans exceptions) est arrêtée** (2026-10-17 vers 5 h) après 5 experts
complets et la moitié du 6e (couche 16 expert 16, uniforme) : son verdict est déjà acquis — **F tombe**
(couche 8 expert 16 et couche 16 expert 16 perdent dans les deux variantes) — et S* a besoin du
processeur. Le journal `fidelite.log` fait foi (le JSON n'est écrit qu'en fin de passe) ; l'analyse le lit.

## Le résultat de K, et une passe K10 (déclarée avant, 2026-10-17 vers 8 h)

**K (3 fenêtres, 765 positions)** : KL moyenne contre la référence : base **0,0226** (± 0,0031), S\*
**0,0301** (± 0,0050) ; différence appariée d̄ = +0,0076, σ(d̄) = 0,0047 (1,6 σ) : par la règle déclarée,
**égale** (|d̄| ≤ 2 σ), avec une estimation ponctuelle **défavorable** à S\* ; S\* fait mieux sur 345
positions sur 765 seulement ; même premier choix 90,3 % contre 91,4 % (`kl/comparer-base-contre-recette.*`).

**K10** : mêmes substitutions, **10 fenêtres** (2 550 positions) ; la passe ne prend plus que quelques
minutes (le processeur est libre). Même règle : mieux si d̄ < −2σ, égale si |d̄| ≤ 2σ, pire sinon.
