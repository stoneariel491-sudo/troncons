# Lot B, génome synonyme : seuils et témoins déclarés avant les passes

Rôle « synonyme » de la construction (genome/05-synthese.md § 4.7 à 4.11). Écrit le 2026-10-17,
**avant** le lancement du codage des 768 experts et avant toute passe KL de ce rôle. Toute règle
ajoutée plus tard porte sa date et dit qu'elle vient après.

## Ce qui est construit

La variante **synonyme λ = 1, δ* = 1** de `outils/genome/eclaireur/synonyme.py` (fonctions
`hessienne`, `facteur_inverse`, `choisir`, `symboles_variante`, commande `ecrire-sym`), **sans aucune
modification du code**, sur les 24 couches × 32 experts × 3 matrices de gpt-oss-20b ; calibration :
les captures de l'éclaireur (fenêtres 10 à 21 de wiki.test, 6 132 positions,
`~/dev/essais/troncons/genome/eclaireur/calib`, `capture.json`). Même environnement
que l'éclaireur : venv `genome-etat-de-l-art` (numpy 2.5.4, scipy 1.18.1), `OPENBLAS_NUM_THREADS=4`.

*Réponse par délégation du 2026-10-17, réversible* : pas de calibration élargie. Le cahier (§ 3.4) la
range en « option déclarée, pas recherche » ; Stone a demandé d'avancer avec ce qui est mesuré, et
toute autre calibration est une autre variante qui demanderait sa propre mesure. On construit donc
exactement la variante dont l'erreur de sortie est publiée (01 § 5.4).

Et la **base frontière** des mêmes 768 experts (`--variante frontiere`, symbole = fonction du code),
écrite par le même outil : c'est la base de comparaison du critère B2 (i).

## Pas S1 : le codage

- **W1, reproduction (témoin connu d'avance)** : `ecrire-sym --variante synonyme --lam 0 --damp 1`
  sur L00-E00 rend **octet pour octet** le fichier `sym/synonyme-d1/L00-E00.sym` de l'éclaireur
  (celui de sa passe KL). Cassure : la même commande à `--damp 0.99` doit rendre un fichier différent.
- **W2, second chemin** : un script indépendant (`outils/genome/synonyme/verifier_sym.py`, écrit
  par ce rôle, qui ne réutilise ni `choisir` ni `reconstruire`) relit les fichiers λ = 1 des experts
  0, 8, 16, 24 des couches 0, 8, 16, 23, reconstruit les matrices et recalcule l'erreur relative
  sur les poids et l'erreur de sortie d'expert sur l'évaluation (fenêtres 0 à 9, pondérées par g²).
  Seuil : égales aux valeurs du journal de l'éclaireur
  (`mesures/genome/etat-de-l-art/passes/synonyme-lam1-damp1-e0_8_16_24.csv`) à **1e-9 relatif**.
  Cassure : un fichier dont un bit de classe est inversé sur une ligne entière fait différer.
- **Couverture** : 768 fichiers, chacun de 4 + 32 + 3 × 2 880 × 1 440 = 12 441 636 octets ; le nombre
  d'experts sans entrée de calibration (servis par la frontière, règle de `ecrire_sym`) est relevé.
- **Débit** : entropie H0 des symboles par tenseur et H(symbole | κ), sur les 72 tenseurs entiers,
  contre la frontière sur les mêmes tenseurs (même estimateur), par un outil commité. Prédit
  (01 § 5.4, 16 experts) : −0,078 bit en H0. Pas de seuil de décision sur le débit : il est publié.

## Pas S2 : la KL de bout en bout, 768 experts substitués

**Protocole** : `genome-capture kl --sub <dossier des 768 .sym>` sur les **10 fenêtres de R1**
(2 550 positions notées, fenêtres 0 à 9, disjointes de la calibration), contre
`~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld` (référence f64) ; `juge kl` pour
chaque passe ; `juge comparer --verite ref --a frontiere --b synonyme` pour l'appariement ; écart-type
**par blocs de fenêtres** (10 blocs) calculé depuis le CSV apparié, comme `frontiere.py`.

**Témoins** :
- ~~le journal de chaque passe porte `experts_substitues = 768` (cassure connue : la passe de
  l'éclaireur sur 32 fichiers porte 32) ;~~ *Corrigé le 2026-10-17 à 10 h 50, après la passe
  frontière, qui porte 732* : le compteur compte les experts **chargés** (un chargement par expert
  routé et par couche, les 10 fenêtres étant passées ensemble), pas les fichiers présents ; 36
  experts ne sont routés par aucune des 2 550 positions. Le témoin juste est
  `experts_substitues = lectures_experts` (tout expert lu est servi par sa base) ; cassure connue :
  la passe de l'éclaireur, 32 substitués sur 731 lus. La passe frontière : 732 sur 732, tient ;
- la KL moyenne recalculée depuis le CSV du juge égale celle du juge ~~à 1e-12 près~~ à 1e-9 en
  valeur relative (*corrigé le 2026-10-17 à 11 h 35, après une chute sans cause sur la passe
  synonyme* : écarts de 9e-13 et 1,2e-12 pour des KL de 0,26 et 0,15 ; le CSV porte 10 chiffres
  significatifs, soit au plus 5e-10 d'erreur relative par valeur ; le seuil absolu de 1e-12 venait
  des KL de 0,03 de l'éclaireur) ; cassure : le CSV amputé de sa première ligne doit faire différer.

**Critères** (cahier § 4.10, B2) :
- **(i) meilleure que la frontière entière** : d̄ + 2 σ_fenêtres < 0, d = KL_synonyme − KL_frontière
  position par position. Égale si |d̄| ≤ 2 σ_fenêtres ; pire si d̄ > 2 σ_fenêtres.
- Premier choix et perplexité : publiés avec leurs incertitudes (Wilson ; ln du rapport), et
  l'appariement du premier choix (ē ± 2σ).
- **(ii) repère de l'outil de référence** : la KL de la meilleure requantification llama.cpp du même
  GGUF à débit d'experts égal ou inférieur, sur les mêmes fenêtres ; mesurée si le temps le permet
  (pas de porte).

**La porte du pas 3** (*réponse par délégation du 2026-10-17, réversible* : la consigne dit « si
elle tient » sans chiffre ; le seul seuil déclaré par le cahier pour le mode rapide entier est B2 (i)) :
le mode rapide se construit dans le moteur si **(i) tient**. Si la synonyme n'est qu'égale à la
frontière, elle garde son avantage de débit (même KL, moins de bits) et se construit aussi, en le
disant ; si elle est pire, elle ne se construit pas et la raison est donnée.

## Pas S3 : le mode rapide dans le moteur

Section ajoutée le 2026-10-17 vers 8 h 50, **avant** toute mesure de ce pas (les fichiers rapides
ne sont pas encore écrits ; le noyau `gemv_base` et son témoin de carte sont commités).

- **S3-T1, le fichier** : `trc-rapide verifier` sur chaque fichier rapide (variante frontière,
  témoin ; variante synonyme) : 100 % des 768 experts ont leurs demi-octets décodés égaux à ceux du
  `.sym`, leurs échelles et biais égaux à ceux de l'expert exact, leur empreinte égale au répertoire ;
  le lien MÉTA vers l'en-tête exact tient. Cassure : `--casser C X` fait trouver faux l'expert (C, X)
  et lui seul.
- **S3-T2, le moteur** : une passe `--temoin` (chaque expert décodé sur la carte redescend et son
  empreinte est comparée au répertoire) sans aucune erreur.
- **S3-K, les deux chemins du mode rapide** : le moteur (`troncons evaluer --rapide`, f32, carte)
  contre la référence f64 (`genome-capture kl`), même fichier de symboles, mêmes 10 fenêtres :
  KL(réf. f64 rapide ‖ moteur rapide) **≤ 0,011** et premier choix identique **≥ 95 %**. Source
  du seuil : l'écart mesuré entre le moteur exact et la référence exacte sur le 20b, 0,00368 ± 0,00046
  et 97,18 % (O, critère C4), multiplié par trois pour l'amplification par les bascules (un modèle
  plus loin de l'exact a des marges différentes). Cassure : la même mesure entre la référence f64
  **frontière** et le moteur **synonyme** doit dépasser 0,011.
- **S3-KL, la qualité servie** : `juge kl` et `juge comparer` du moteur rapide contre la référence
  (`ref-openai-20b.kld`) et contre le moteur exact ; publiés avec premier choix et perplexité.
- **S3-V, la vitesse** : `troncons mesurer` sur le 20b, invite et options de la série O4 (Y20 :
  `invite-wiki-3000.txt`, -n 256, repos 10 s), séance **A B B A A B B A** (A le fichier exact v1.0,
  B le compagnon rapide synonyme), secteur vérifié (Win32_Battery = 2) avant chaque passe, aucun
  `llama*`, verrou de la carte tenu toute la séance. Bruit de référence σ : l'écart relatif des passes
  A entre elles. Gain **annoncé** seulement si le rapport médian B / A dépasse 1 + 2σ ; prédit au toit
  du disque ×1,41 à ×1,45 (cahier § 4.7), le 20b ayant une part de ses experts en VRAM.

## Pas S3 sur le 120b (frontière seulement) : ajouté le 2026-10-17 vers 12 h 10, avant ces mesures

Le 120b n'a ni captures de calibration ni référence f64 sur les 10 fenêtres (épreuve J1 § « ce qui
manque ») : la mutation synonyme ne peut pas y être écrite dans ce travail (raison chiffrée dans 07).
Ce qui se mesure : le **mode rapide de la frontière** (symbole = fonction du code, sans calibration),
qui a la taille du mode rapide à 0,07 bit près, donc sa vitesse.

- **120b-T1** : `trc-rapide verifier --symboles frontiere-directe` : 100 % des 4 608 experts (demi-octets
  = frontière des codes exacts, échelles et biais = exact, empreintes) ; cassure `--casser C X`.
  Témoin préalable du mode « frontière directe » sur le 20b : même fichier que celui des `.sym`
  (fait : même taille au bit près, vérifié contre les `.sym`, 0 faux).
- **120b-T2** : `troncons generer --rapide --temoin`, 32 jetons, 0 erreur.
- **120b-V** : séance A B B A A B B A, A = `gpt-oss-120b.trc` (v1.0), B = le compagnon frontière,
  mêmes règles que S3-V (secteur, verrou, σ des passes A ; gain annoncé si > 1 + 2σ). Prédit au toit
  du disque : ×1,43 à ×1,46 (cahier § 4.7).
- **Proxy de qualité, sans référence f64** : KL(moteur exact ‖ moteur rapide) sur les 10 fenêtres
  (`troncons evaluer`, le moteur exact servant de base), publiée sans seuil ; sa validité se lit sur
  le 20b, où les deux KL existent (contre le moteur exact et contre la référence f64).

Et S3-V refait sur une machine sans autre passe (séance s2) : la séance s1 a tourné pendant la passe
KL B0 (6 fils), le calcul du débit et l'écriture du compagnon 120b ; elle est publiée comme telle.

## B2 entre les deux λ, à 768 experts : ajouté le 2026-10-17 à 12 h 15, après B0, avant le codage λ = 0

B0 (P1, 32 experts) rend λ = 1 **égale** à la frontière et **pire** que λ = 0 (+0,0088 ± 0,0032). Par
la règle B0 du cahier (05 § 4.10), les deux variantes se construisent à 768 experts et B2 les
départage. Codage λ = 0, δ* = 1 des 768 experts (même outil, mêmes réglages ; les 32 fichiers λ = 0
de l'éclaireur, reproduits au bit par W1 pour L00-E00, sont repris), puis la même passe KL.
Règle : d = KL_{λ=0} − KL_{λ=1} position par position ; si d̄ + 2σ_fenêtres < 0, λ = 0 devient la
variante du mode rapide (et son compagnon est écrit) ; si |d̄| ≤ 2σ, λ = 1 reste (même KL, 0,07 bit de
moins) ; si d̄ > 2σ, λ = 1 reste.

## Séance s2 de la vitesse (20b et 120b) : amendement ajouté le 2026-10-22 vers 0 h, avant toute passe de s2

B2 entre les deux λ est lu (2026-10-21, 23 h 58) : λ = 0 meilleure, de justesse (d̄ + 2σ = −0,0009).
Par la règle ci-dessus, **λ = 0 devient la variante du mode rapide** : son compagnon est écrit, vérifié
(S3-T1 et cassure) et mesuré par le moteur (S3-K, S3-KL, mêmes seuils que λ = 1), et c'est lui, B, dans
la séance s2 du 20b. Les règles de S3-V et de 120b-V restent ; s'y ajoute le calme
(`pilote_vitesse.py`, docstring) : la séance ne part que sur deux relevés vides des autres flux à une
minute d'écart ; une passe dont le relevé d'avant ou d'après n'est pas vide est marquée « sous_charge »,
publiée, et **ne conclut pas** ; le verdict se lit sur les seules passes calmes (au moins deux A et deux
B, sinon pas de verdict). Rien ne se desserre : gain annoncé si le rapport médian B / A dépasse 1 + 2σ.
