# Ronde de corrections après l'épreuve J1 : seuils déclarés avant chaque passe

Lot O, ronde de corrections (2026-10-16). Chaque bloc est commité avant la première passe qu'il
juge ; l'heure du commit fait foi (`git log`). Un seuil ne change pas après sa passe : une phrase
fausse se barre.

## Bloc 1 : G1 et G2 (sortie sur erreur, enfant nvidia-smi), déclaré le 2026-10-16 ~~vers 06 h 25~~ à 06 h 12 min 40 s (heure du commit ca5d338)

Outil : `temoin_sortie.py`. Trois cas (absent, corrompu, tué), lancés comme les pilotes (sorties en
tuyaux, attente de leur fermeture).

- **Reproduction** (binaire d'avant la ronde, commit 7b288a6, copié dans
  `~/dev/cibles/troncons-O/avant-7b288a6/`) : attendu « tombe » sur les trois cas, par
  un enfant `nvidia-smi` vivant après la sortie du parent et une attente des tuyaux jusqu'au délai de
  90 s. Si l'un des cas tient avec l'ancien binaire, le témoin ne prouve rien pour ce cas et je le dis.
- **Après correction** : seuil pour « absent » et « corrompu » : retour de `communicate` en moins de
  **30 s** (le chemin d'erreur ne dure qu'une ouverture, quelques secondes : XE2 finissait « en
  quelques secondes » à l'épreuve), code 1, l'erreur écrite sur la sortie d'erreur ; pour les trois
  cas : **0 enfant `nvidia-smi` vivant** 2 s après le retour.
- Cassure du témoin : c'est la passe de reproduction elle-même (même outil, ancien binaire).

Passes du bloc 1 (journaux sous `journaux/`) : `g1g2-avant-7b288a6-passe1.json` (cas « tué » tué à 8 s,
avant la naissance de l'enfant : ne prouvait rien) ; `g1g2-avant-7b288a6-tue-passe2.json` (le témoin
ne vidait pas les tuyaux pendant l'attente : l'enfant s'est bloqué sur sa sortie d'erreur pleine ;
défaut du témoin, corrigé par deux fils de lecture) ; `g1g2-avant-7b288a6.json` (reproduction
valable : **tombe** sur les trois cas, retour à 90 s, un orphelin chacun) ; `g1g2-apres.json`
(**tient** sur les trois : 1,5 s, 4,9 s, 4,9 s, 0 orphelin).

## Bloc 2 : m2 (construction avec vcvars), déclaré avant la passe corrigée

Outil : `construire-avec-vcvars.bat [sans]` (arbre de travail, cibles à part). Seuil : avec et sans
vcvars, la construction de `trc-noyaux` réussit, et les trois images `noyaux.fatbin` (cible du lot O,
avec vcvars, sans vcvars) sont égales octet pour octet. Reproduction (avant la correction) : échec à
`build.rs:75` (`journaux/m2-avec-vcvars-avant.log`). Après : les deux réussissent
(`m2-avec-vcvars-apres.log`, `m2-sans-vcvars-apres.log`), les trois images ont la même empreinte
SHA-256 (aeae5bdcc05ad84a…, 295 864 o) : **tient**.

## Bloc 3 : M1 (garde de production), déclaré avant toute passe du moteur gardé

Construit : `trc-ordo/src/garde.rs` ; options `--sans-garde`, `--casser-garde troncon:N|ligne:N`.
Débit de l'empreinte mesuré d'abord (`examples/debit_empreinte.rs`, deux passes) : 1,07 à 1,10 Go/s
par fil, 3,8 à 4,3 Go/s sur 4 fils, témoin SHA-256(« abc ») tenu ; le juge l'estimait à 2 Go/s par
cœur [est.] : ~~2 Go/s~~ 1,1 Go/s mesuré.

Témoins de justesse (20b, courts, sans verrou ; outil `temoin_garde.py`) :
- **G-XO3** : `generer --flux -n 32` sur la copie à médiane faussée du lot O (couche 0, expert 30) :
  avec la garde, **erreur fatale nommée « garde de production : couche 0, expert 30 »**, code 1 ; sans
  la garde (cassure : `--sans-garde`), la passe va au bout, sans erreur (comportement de l'épreuve).
- **G-T** : fichier sain, `--casser-garde troncon:5` : erreur nommée ; avec `--sans-garde` en plus :
  pas d'erreur (la cassure de la garde).
- **G-L** : fichier sain, `--casser-garde ligne:3` : erreur nommée sur la ligne ; avec `--sans-garde` :
  pas d'erreur.
- **G-=** : fichier sain, 32 jetons, garde et sans garde : **même texte au bit** (SHA-256 égales) ;
  garde : 0 erreur, tronçons vérifiés = lectures de tronçons, lignes vérifiées = lignes lues.
- **G-E2** : copie E2 du lot E : une erreur fatale nommée (garde ou voies), publiée.

Coût (120b, verrou de la carte, secteur vérifié, aucun llama-*) : série A B B A, A = garde (défaut),
B = `--sans-garde`, `troncons mesurer --flux` sur l'invite wikitext, 256 jetons, mode A0, plus une
passe D (`troncons disque`) d'échauffement jetée puis une passe D gardée, avant la série. Publiés :
génération et préremplissage (j/s), ouverture (s), attente de la garde par jeton, octets hachés.
Seuils : (1) **la garde reste active par défaut si C5 tient avec elle** (seuil du § 7.1 recalculé
dans la séance, formule de REPRISE-O point O4, avec la passe D gardée) ; (2) son coût est **réel**
s'il dépasse 2 × le plus grand bruit d'une paire et 3 % (règle de 06 § 7.5) ; prédiction [calc.] :
au plus le hachage du dernier tronçon d'un pas (≈ 12 Mo ÷ 1,1 Go/s ≈ 11 ms sur ≈ 460 ms, 2,4 %) :
coût non réel. (3) Textes des quatre passes égaux à e4c6dbac… (le texte publié).

Passe des témoins de justesse du bloc 3 (`journaux/m1-temoin-garde.json`, binaire ebad7c2) : **G-XO3
tient** (« garde de production : couche 0, expert 30 : empreinte des 11 836 992 octets utiles lus
17d8974e… au lieu de 9aa7c5fb… ») et sa cassure tombe (sans garde : texte 48f70a45…, celui du fichier
sain, comme à l'épreuve) ; **G-T tient** (couche 0, expert 4), cassure : texte changé (0298579f…) sans
erreur ; **G-L tient** (ligne du jeton 13169), cassure : texte inchangé, sans erreur (un bit d'une
ligne Q8_0 ne change pas ces 32 jetons : invisible) ; **G-= tient** (même texte 48f70a45… avec et sans
garde ; 920 tronçons vérifiés sur 920 lus, 739 lignes sur 739) ; **G-E2** : la garde nomme couche 2,
expert 19 (avant le contrôle des voies). Débit de l'empreinte : `journaux/debit-empreinte.jsonl`.

## Bloc 4 : G1 rejoué sous la charge de l'épreuve, déclaré avant sa passe

Charge : la passe numpy f64 du juge sur le 120b (`gptoss_numpy.py`, fenêtre 0, 511 positions : 61 Go
lus, ≈ 17 min), lancée d'abord ; 60 s après, `troncons evaluer --flux --brut` sur les 10 fenêtres du
120b brut (la passe figée de l'épreuve), nouveau binaire. Puis, si le temps le permet, la même paire
avec l'ancien binaire (7b288a6), tuée à 25 min si elle se fige (processus que je lance).
- Seuil (nouveau binaire) : la passe **finit** (code 0, `.kld` = 5b212fe9…, C3) **ou écrit son erreur**
  (code 1, ligne « troncons : erreur : … » et `<journal>.erreur.json`) en moins de 30 min ; jamais une
  attente muette. Publié : `flux_conflits_evites` (> 0 : le chevauchement d'arrivée, cause supposée,
  s'est produit et a été évité [hyp. → mes.]) et les battements.
- Ancien binaire : publié tel qu'observé (figé, erreur, ou fini). S'il finit, la reproduction n'a
  pas eu lieu et je le dis (le phénomène dépend de l'ordre des achèvements).

## Bloc 5 : M5 (cache KV en f32, essai), déclaré avant ses passes

Passes (120b et 20b, nouveau binaire, `--kv-f32` contre le défaut f16) : `evaluer --flux` fenêtre 0 de
`ref-openai-20b.kld` ; `evaluer` sur l'invite de 708 jetons (`base-invite-708.kld` du juge), par flux
(argmax de chaque position) et en boucle avec `--trace` (routage) ; `mesurer --flux` (texte de C12).
Vérités : les `.npz` f64 du juge (`np-120b-f0-openai`, `np-20b-f0-openai`, `np-120b-invite-toutes`).
Hypothèses déclarées (H5, à trancher par l'arbitre, couture N ; rien ne change par défaut) :
- **H5a** : le premier jeton de C12 en KV f32 est **1008** (« ... »), celui de la vérité f64.
- **H5b** : l'accord de routage avec la vérité sur l'invite passe de 96,9 / 93,1 % (f16, positions
  0-511 / 512+, juge) à **au moins 98,3 / 96,9 %** (l'accord du moteur f16 avec la vérité + KV f16,
  99,3 / 97,9 %, moins un point : la part qui ne vient pas du KV).
- **H5c** : KL(vérité ‖ troncons) sur la fenêtre 0 du 120b **≤ 0,00308** (le f16), premier choix ≥
  95,7 % ; publiés à côté, pour les deux : la part des positions de KL > 0,1 et la KL au 99ᵉ centile
  (critère de queue proposé par le juge), avant et après 512 (invite).
- Coût : VRAM du moteur (+156 Mo prévus [calc. juge]), emplacements (≈ −12 prévus), génération en
  série A B B A (A = f16, B = f32), réel selon 06 § 7.5 ; prédiction : non réel (−1 à −2 %).

## Bloc 6 : M2 (la base llama.cpp balayée), déclaré avant ses passes

Configuration publiée (`fit`, `-c 2048`, mesures/gpt-oss.md § 3.2) et ses variantes, toutes sur la
même invite et les mêmes 256 jetons : `-t 6`, `-t 10`, `-t 12`, `-t 16`, et `-ngl 99 --n-cpu-moe 34
--fit off -t 10` (deux couches d'experts en carte, comme `fit`). Ordre : une passe `-t 10`
d'échauffement jetée, puis le palindrome t6 t10 t12 t16 m m t16 t12 t10 t6. Bruit d'une configuration
= |X₁ − X₂| / moyenne ; la meilleure est celle de plus grande moyenne ; elle bat une autre si l'écart
dépasse 2 × le plus grand des deux bruits et 3 % (06 § 7.5). **C6 recalculé** : génération moyenne
des passes T120g (garde, f16) de la séance du bloc 3 ÷ la meilleure base ; ~~× 3,85~~ barré partout
où il est écrit. Textes : celui de la base (45a1f638…) attendu pour `fit` ; une variante au texte
différent est publiée et gardée (le texte de llama.cpp dépend de sa configuration).
