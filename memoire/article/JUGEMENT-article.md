# Le jugement de l'article court (`memoire/article/{en,fr}/troncons-article.tex`)

Rôle : juge indépendant de l'article. Je n'en ai rien écrit, ni le texte, ni les figures, ni les outils du
rédacteur. Date : 2026-10-29. Objet : les deux versions telles que commitées en f22889e et dd08635 (EN 13 pages,
FR 14 pages), leurs paquets arXiv, `construire-article.sh`, `commun/troncons-article.bib`,
`REPRISE-article.md`.

Étiquettes : **[mes.]** refait ici par un outil commité ; **[lu]** lu dans le fichier ou le jugement cité, non
refait ; **[litt.]** source extérieure, lue à l'adresse donnée le 2026-10-29.

Mes outils, écrits sans ouvrir `medianes_j1.py`, `parite_nombres.py` ni `medianes_j1.json` (sous
`memoire/article/juge/`) :
- `refaire_chiffres.py` : relit les journaux commités, recalcule chaque chiffre, l'écrit au format de l'article et
  vérifie qu'il figure dans le corps anglais **et** dans le corps français. Journal : `refaire_chiffres.txt`.
  Témoin : `--casser` (médiane B du J1 × 1,001) fait tomber la médiane et r, code 1. Tenu.
- `parite_structure.py` : parité EN/FR élément par élément et dans l'ordre (structure, citations, étiquettes de
  provenance, figures, nombres). Témoin : `--casser` retire une citation au français, la parité des citations
  tombe. Tenu.
- `chemins_cites.py` (chaque `\fichier{…}` existe), `longueur_resume.py` (limite d'arXiv). Journal :
  `verifications.txt`.

---

## 0. Verdict

**Les chiffres tiennent ; l'article ne se soumet pas en l'état.** Trois graves, tous corrigeables par du
texte seul, sans aucune mesure neuve :

- **G1, la nouveauté est mal dite** : « nous ne connaissons pas de travail antérieur qui mesure ou retire » le
  −0 de FP4 est faux tel qu'écrit. Deux articles d'arXiv (NxFP, RaZeR) décrivent ce code redondant et le
  réaffectent ; un troisième étend le codage sans perte au FP4. Aucun n'est cité.
- **G2, l'exactitude est dite plus large que le Tome II ne l'établit** : « les logits sont ceux du modèle au
  bit », « servi exactement » ; et la KL 0,00308 contre 0,0607 est donnée sans dire qu'elle vient d'une seule
  fenêtre de 255 positions, ni que le Tome II attribue l'essentiel de l'écart de llama.cpp à son arrondi de
  la rampe YaRN.
- **G3, la mémoire est dite sans la carte** : « un ensemble de travail de pointe de 384 Mo », dans le résumé,
  se lit comme une mémoire totale. Le moteur occupe aussi environ 6,3 Go de la carte.

**Ce qui tient, par mes chemins :**
- **156 chiffres sur 156** sont recalculés depuis leurs journaux et présents à l'identique dans les deux langues.
  Les autres (Tome II, spectres, durée des pistes) sont lus dans leurs jugements et redonnés.
- Le ×1,44 est bien dit propre à ce disque et au motif des requêtes, et non aux octets ni à l'état des
  fichiers. La phrase fausse est montrée barrée, avec ce qui a changé.
- « Sans perte » repose sur une démonstration (que j'ai relue contre le noyau) et sur des logits égaux au bit
  sur des fenêtres neuves.
- Chaque résultat négatif est donné avec son seuil.
- Les deux paquets arXiv se compilent seuls par pdflatex (EN 13, FR 14, 0 erreur) et rendent le texte des PDF
  commités.
- La parité EN/FR tient.

On trouve aussi **18 mineurs** (§ 6), dont un hérité du Tome III (H1).

---

## 1. Chaque chiffre, refait (consigne, point 1)

### 1.1 Recalculés depuis leur journal par `refaire_chiffres.py` [mes.] : 156 sur 156 tiennent

| Bloc | Source commitée | Chiffres de l'article redonnés |
|---|---|---|
| Tailles | `mesures/genome/construction/codon/tailles.json` | poids d'experts, octets de tronçons, fichiers, plus grands tronçons, −0 fondus (1 221 698 587 ; 7 199 491 948), parts 6,393 % et 6,279 %, gain **recalculé depuis les octets** 0,12791 et 0,12562, 1 800 486 912 octets (1,80 Go), 3,26 % (0,12562 / 3,85456), 3,25 %, +3,4 %, prédictions 0,12786 et 0,12558 |
| Théorème | `tailles-par-tenseur.csv` (180 lignes) | écart −0,00017 à +0,00016, moyenne +0,00005, 1,7 × 10⁻⁴ ; gain 0,115 (120b, couche 26, up) à 0,239 (120b, couche 0, up ; 11,9 % de −0) ; ordre gate, up, down vérifié contre `zero-compte-20b.json` |
| La pièce | `mesures/genome/etat-de-l-art/journaux/zero-compte-20b.json` | 6,3920 % et 6,3929 % ; H = 0,9999999967 ; 3,8638 ; 3,7360 ; 0,1278 ; rayon ×1,88 (0,4 + 44 × part) |
| J1 s2 | `j1-s2-passes.csv`, médianes par ma fonction | huit passes ; 1,988 et 2,890 ; r = 1,454 ; σ = 5,6 % ; 2σ = 0,113 ; rapports appariés 1,450, 1,451, 1,444, 1,626 ; octets 710 118 798 et 686 756 916 ; 0,9671 ; 59,08 ; 0,5897 ; 0,391 et 0,259 s ; 1,81 et 2,65 Go/s ; 62,1 et 42,7 ms ; 96,2 et 68,2 ms ; 388,67 et 382,21 Mo ; −6,45 Mo ; 4 472 832 octets |
| Disque s2 | `disque-s2.json` | 1,742 ; 1,741 ; 2,254 ; 2,391 ; 1,356 ; 1,331 |
| Juge de la construction | `mesures/genome/construction/juge/vitesse/analyse-{120b,20b}.json` | 2,889 / 2,004 = 1,442 ; σ = 5,8 % ; disque B/A 1,37 ; reste 1,394 ; 1/0,9671 ; R/B 1,284 et 0,942 |
| Motif croisé | `mesures/disque/placement/juge/seance/Jb3-*.json` (16 passes) | les seize débits ; médianes 1,801, 2,501, 2,528, 1,808 ; ×1,388 (non arrondies), ×1,389 (arrondies), ×0,715 |
| Motif borné | `Jb9-*`, `J10-*`, `J11-*`, `J5-*`, `J6-*` | ×1,421 ; ×0,713 ; ×0,851 ; ×0,882 ; ×1,26 ; 0,981 (passes écartées par le juge, SMART 1,036 et batterie, écartées ici aussi) |
| Tables | `tables-octets.json` | 540 tables, 13 % des fentes |
| Machine, modèle | `fondations/journaux/01-machine/debits-mesures.json`, `mesures/localite-gpt-oss/octets-gpt-oss.json` | 2,82 Go/s ; 63 387 346 208 et 12 109 566 624 octets ; 63,4 Go ; 4 608 experts ; 61,07 Go ; 1,69 Go ; 36 × 3 × 3 × 31 = 10 044 ; 225 |
| Pistes | `mesures/pistes/tropicale/juge/juge.json`, `mesures/genome/construction/juge/kl/apparie-neuf-sub-l0-contre-frontiere.json`, `mesures/mimetisme/P3/routeur-ligne/analyse.json` | 2 905 / 5 087 ; 12 264 / 122 640 ; 57,1 % ; 26,6 % ; −0,1565 ± 0,0334 ; 4,7 σ ; 0,0314 ; 0,0384 |

### 1.2 Lus dans leur document jugé et redonnés [lu]

- **Tome II, chapitre 7** : 384,19 et 380,50 Mo ; 10,93 Go ; 1,965 jeton/s avec la garde ; 0,884 ; ×2,22 ;
  KL 0,00308 et 0,0607 (fenêtre 0) ; logits égaux sur 5 120 pas.
- **`genome/06-codon-v1-2.md`** (§§ 1, 3, 5, 7) : 8 640 lignes, 2 486 216 demi-octets 8, 768 + 4 608 experts,
  huit contrôles, 512 sur 512, A-C2 ≥ 0,12.
- **`genome/JUGEMENT-construction.md`** (§§ 2, 4) : 96 sur 96, 0 sur 5 120 sur fenêtres neuves.
- **`genome/JUGEMENT-placement.md`** (§§ 5.3, 5.5, 5.9) : seuils 3,2 % et 11,8 % ; 1,398, 1,362, 1,404, 1,406 ;
  267 473 extents contre 65.
- **Pistes** : `genome/pistes/spectres/JUGEMENT.md` (0/48, 9/48, 32) ; `genome/duplication.md` (0,0034 et
  0,0016) ; `genome/pistes/tropicale/garde-tropicale.md` (88 %).
- **Commits** a50c380 (2026-10-17 08:47), 71905dd (2026-10-21 23:36), 000cef9, 96533df : existent, et sont
  datés avant leurs passes comme l'article le dit.

### 1.3 Ce qui ne tient pas exactement

Ces écarts sont recalculés ; le détail est aux mineurs.
- « environ 1,9 Mo non expliqués » : le reste de s2 vaut 6,45 − 4,47 = **1,98 Mo**, et 1,9 est celui de s1 (M8).
- Les « 540 tables des couches 0, L/2 et L−1 » sont en fait **216 + 324 = toutes les couches** (M6).
- Le tableau 2 et la figure 3 mêlent des bits de flux et des octets de tronçons (M7).
- Les seuils déclarés du mode rapide valent **1,769 et 1,227**, et non « ×2,00 et ×1,24 reproduits » (M16).
- La KL 0,0314 de P3 est prise contre le moteur sans biais, et non contre la référence (M14).

L'écart de consigne relevé par le rédacteur est juste. −3,56 % vient de l'éclaireur (12 tenseurs du 20b,
`genome/01-eclaireur.md`). Sur le 120b dans le format, c'est −3,26 % des bits, et l'article écrit bien 3,26 %.

---

## 2. Ce que les affirmations disent (consigne, point 2)

- **Le ×1,44 tient, propre à ce disque, par le motif.**
  - Résumé, § 4.5, limites et conclusion le disent, et la seule borne transportable reste +3,4 % pour les octets.
  - La phrase « pas le format » est barrée là où elle était citée, avec la date et la raison.
  - Le motif croisé a été mesuré sur le 20b à l'étage disque, et le 120b n'a qu'une borne basse. Les limites le
    disent ; le résumé et la contribution 4 le taisent (M1).
- **« Sans perte » est prouvé.**
  - J'ai relu la proposition A1 contre `gemv.cuh` au commit cité. Chaque bloc part de `0.0f`, avance par
    `fmaf` dans un ordre fixe, et son échelle s'applique au bloc fini ; les pas (0) à (3) de l'esquisse sont
    justes.
  - Le lemme des tables est juste (M = 4 096, `x & 4095`, ARCHITECTURE § 4.9.2).
  - La mesure le confirme : 8 640 lignes, puis 0 sur 5 120 sur des fenêtres neuves.
  - Ce qui déborde, c'est l'exactitude **du moteur** prêtée au modèle (G2).
- **On ne généralise pas au-delà d'une machine.** Chaque vitesse est dite de ce NVMe, sous BitLocker et VMD.
  Un seul écart : l'empreinte mémoire est dite sans la carte (G3).
- **Les résultats négatifs ont leurs seuils.**
  - La garde, les spectres, P3 et le mode rapide sont donnés avec leur seuil.
  - Les seuils du mode rapide sont mal recopiés (M16).
  - Les « cinq autres pistes » n'ont aucun seuil dans le tableau, et l'une est dite « inutile » contre son
    juge (M14).
- **Les passages trop beaux :**
  - « une pièce juste que rien ne prédit » (M4) ;
  - « ce qui est vrai à la place » sur les spectres, une mesure exploratoire ni déclarée ni jugée (M13) ;
  - « la raison est mesurée aussi » pour la garde (M12) ;
  - G2 et G3 ci-dessus.

---

## 3. Lu par un relecteur d'arXiv qui ne connaît pas le projet (consigne, point 3)

**Clarté.**
- La méthode, les règles de mesure et les limites sont nettes et rares dans le domaine.
- Le résumé porte trois histoires à la fois (le codon, le moteur, le motif du disque) ; un lecteur ne sait pas
  laquelle est la contribution. Le titre promet la deuxième ; le texte développe la première et la troisième.
- Le jargon du projet arrive sans définition au premier passage : « J1 », « séance s2 », « A-C2 », « tronçon »,
  « juge », les étiquettes [meas.] et les chemins du dépôt dans le texte courant.
- « Des juges qui n'ont pas fait le travail » ne dit pas qui sont ces juges, et un lecteur le demandera. Ce
  qu'on en dit revient à Stone.

**Nouveauté.**
- Le théorème du gain est la règle de chaîne ; un relecteur le jugera élémentaire.
- La contribution réelle tient en quatre choses :
  - la mesure, sur un modèle déjà publié, que le signe d'un zéro est une pièce juste, tenseur par tenseur ;
  - la preuve sur le vrai noyau ;
  - le lemme du format, qui fait passer le fondu par les tables seules ;
  - la mesure de bout en bout.
- Telle quelle, la nouveauté est mal bornée (G1) : le code −0 redondant de FP4 est connu et déjà réaffecté
  (NxFP, RaZeR), et le sans-perte en FP4 a un antécédent (Heilper et Singer). Ces articles manquent aux
  travaux liés.
- Le gain (3,26 %) est modeste ; il faut le dire pour ce qu'il est : exact, gratuit et prouvé.

**Ce qui manque pour être pris au sérieux.**
1. Le code et les données publics : `\Emplacement` est vide. Sans dépôt, aucun chiffre n'est vérifiable de
   l'extérieur, et les trois tomes cités sont introuvables.
2. Les travaux les plus proches (G1).
3. L'empreinte sur la carte (G3), et une comparaison qui ne mette pas 384 Mo d'hôte contre 10,93 Go d'hôte
   sans dire que les deux moteurs se servent aussi de la carte.
4. Pour le ×1,44, un second disque ou une seconde machine. À défaut, présenter le § 4.5 comme une étude de cas
   assumée. Le mécanisme manque, et l'article le dit.
5. La v1.2 contre llama.cpp dans une même séance. Le ×2,22 du Tome II mêle deux séances (M2).
6. Une seule famille de modèles. L'article le dit ; un second modèle MXFP4, même petit, montrerait si la pièce
   juste est propre à gpt-oss.

---

## 4. Conformité à arXiv et parité des langues (consigne, point 4)

Pages d'aide lues le 2026-10-29 [litt.] : https://info.arxiv.org/help/submit_tex.html,
https://info.arxiv.org/help/faq/texlive.html, https://info.arxiv.org/help/prep.html,
https://info.arxiv.org/help/translations.html.

### 4.1 Ce qui tient

- **Moteur** : arXiv dit « fully supports and automatically recognizes PDFLaTeX ». TeX Live 2023 et 2025 sont
  servis, 2025 par défaut ; les processeurs listés sont tex, pdftex, latex, pdflatex et xelatex, sans
  lualatex. Le choix de pdflatex est juste.
- **`\pdfoutput=1`** : la page dit « You should not use `\pdfoutput` to change the output format ». Sous
  pdflatex, cette ligne ne change rien (la sortie est déjà en PDF) ; elle est sans effet, non fautive. À la
  soumission, il faut choisir « pdflatex » explicitement.
- **Bibliographie** : arXiv lance bibtex, mais « will use the .bbl file if it is present », et son nom doit
  égaler celui du .tex. C'est le cas pour les deux langues : `troncons-article.bbl` est dans chaque archive,
  égal octet pour octet au commité. Le .bbl de BibTeX/natbib n'a pas le couplage de version de biblatex.
- **Figures** : « Figures can be included in JPEG, PNG, or PDF format ». `troncons-figures.pdf` (PDF 1.5,
  LuaTeX) est dans chaque archive, égal au commité.
- **Polices** : toutes incorporées et sous-ensemblées, dans les deux PDF (`pdffonts`).
- **Paquets compilés seuls** [mes.] : déplié dans un dossier vide, chaque paquet donne par pdflatex EN 13 pages
  et FR 14 pages, 0 erreur. Le texte de mes PDF (`pdftotext`) est égal à celui des PDF commités.
- **Champ « abstract » d'arXiv** (limite 1 920 caractères) [mes.] : EN 1 710 à 1 770, sous la limite ; FR 1 836
  à 1 904, sous la limite mais à 16 caractères près en LaTeX brut.
- **Titre** : ASCII, sans majuscules continues ; il tient la règle de prep.html.

### 4.2 Ce qui ne tient pas

- **EN** : après deux passes, le journal dit « Label(s) may have changed. Rerun » ; la troisième passe
  stabilise. AutoTeX relance, mais le témoin de `construire-article.sh` ne cherche pas cet avertissement (M17).

### 4.3 La parité EN/FR [mes.]

- Structure (58 éléments), citations (29, même ordre), étiquettes de provenance (32), figures et largeurs (5),
  `\barre` (1), `\textbf` (39), `\emph` (10) : égales et dans le même ordre.
- Nombres : 827 hors chemins et étiquettes, même multiensemble (l'outil du rédacteur dit 274 distincts et 876
  occurrences, comptés avec les chemins).
- L'ordre diffère en quatre places, toutes d'ordre des mots (« an 8 GB RTX 4060 » contre « une RTX 4060 de
  8 Go » ; « KL to an f64 reference of 0.00308 » contre « KL de 0,00308 contre une référence f64 »).
- J'ai lu les deux versions phrase à phrase : elles disent la même chose, aucun sens n'a dérivé.

---

## 5. Graves

### G1. La nouveauté : le −0 de FP4 est connu, et le sans-perte en FP4 a un antécédent

**Où** : EN l. 99, « We know of no prior work that measures or removes it. » ; FR l. 106, « Nous ne connaissons
pas de travail antérieur qui la mesure ou la retire. » Et, par ricochet, la contribution 1.

**Pourquoi c'est faux** [litt., lus le 2026-10-29] :
- **NxFP** (Lo, Wei, Brooks), arXiv:2412.19821, 2024-12-15, https://arxiv.org/abs/2412.19821, § 4.3 « Code
  Recycling ». Il remappe le code binaire de −0 des formats signe-grandeur, dont MXFP4, vers une valeur utile
  (« remapping the binary code representing −0 in sign-magnitude numbers to a useful value »).
- **RaZeR** (Chen et al.), arXiv:2501.04052, v1 2025-01-06, v3 2026-01-31, https://arxiv.org/abs/2501.04052.
  Selon son résumé, le FP4 « contains both positive and negative zeros », et RaZeR réaffecte le zéro redondant.
- **Heilper et Singer**, arXiv:2508.19263, 2025-08-20, https://arxiv.org/abs/2508.19263. Ils étendent la
  compression sans perte de ZipNN au FP8 et au FP4, en codant entropiquement exposant et mantisse.

Ces travaux ne font pas ce que fait l'article : ils créent un format neuf, avec perte, ou ne mesurent pas le
signe des zéros d'un modèle publié. Mais un relecteur les connaîtra, et la phrase les nie.

**Correctif** (deux langues, sans mesure neuve) :
1. Ajouter les trois entrées au `.bib`, avec `\Consulte{2026-10-29}`. Le rédacteur lit d'abord leur texte, au
   moins NxFP § 4.3 et la section de RaZeR sur le zéro (SOCLE : source primaire, adresse, dates).
2. Remplacer la phrase par :
   - EN : « The redundancy of the signed zero in sign-magnitude FP4 is known: NxFP's code recycling
     \citep{…} and RaZeR \citep{…} reassign the $-0$ code to another value, in new and lossy formats, and
     lossless entropy coding has been extended to FP4 \citep{…}. We know of no work that measures, in a model
     already published in MXFP4, whether the sign of a zero carries information, and removes it without
     loss, with a proof that the kernel returns the same bits. »
   - FR, fidèle : « La redondance du zéro signé dans le FP4 signe-grandeur est connue : le recyclage de code de
     NxFP et RaZeR réaffectent le code $-0$ à une autre valeur, dans des formats neufs et avec perte, et le
     codage entropique sans perte a été étendu au FP4. Nous ne connaissons pas de travail qui mesure, dans un
     modèle déjà publié en MXFP4, si le signe d'un zéro porte une information, et qui le retire sans perte,
     avec une démonstration que le noyau rend les mêmes bits. »
3. Dans l'introduction, une phrase qui dit pourquoi l'article ne réaffecte pas le code, comme RaZeR le fait :
   on garde le modèle tel que publié, au bit près en valeur.

### G2. L'exactitude du moteur prêtée au modèle, et une KL sans son contexte

**Où** :
- (a) EN l. 77, « *exactly* (the same logits as the model's own arithmetic) » ; FR l. 84, « (les mêmes
  logits que l'arithmétique propre du modèle) ».
- (b) EN l. 97, « and the logits are those of the model to the bit » ; FR l. 104, « et les logits sont ceux du
  modèle au bit près ».
- (c) EN l. 402, « how a 63.4 GB model is served exactly » ; FR l. 409, « se sert exactement ».
- (d) EN l. 119 et FR l. 126, « a KL divergence to an f64 reference of 0.00308, against 0.0607 for
  llama.cpp ».

**Ce que le Tome II établit** [lu] (chapitre 7, § C3 et § C4, tableau C4, « Six times closer, requalified »,
§ « The f16 KV cache carried the whole gap ») :
- L'égalité au bit est celle du fichier codé et du fichier brut **par le même moteur**.
- Contre la vérité f64, troncons fait 0,00308 **sur la fenêtre 0 (255 positions)**, cache KV en f16, et
  −0,00048 avec un cache KV en f32 (« au plancher du format »).
- Sur le 20b, 55 % de l'écart de llama.cpp vient de son arrondi des bornes de la rampe YaRN, un choix de
  modélisation et non la précision des noyaux.

Un modèle n'a pas de « logits au bit » ; écrit ainsi, l'article promet ce qu'aucune mesure ne montre.

**Correctif** :
- (a) EN « *exactly* (to the bit, the logits that the same engine computes from the uncompressed weights) » ;
  FR « (au bit, les logits que le même moteur calcule sur les poids non compressés) ».
- (b) EN « and the logits are, to the bit, those that the engine computes from the raw GGUF weights » ; FR « et
  les logits sont, au bit, ceux que le moteur calcule sur les poids bruts du GGUF ».
- (c) EN « served from a 384 MB host working set, its logits equal to the bit to those of the raw file » ; FR
  fidèle.
- (d) Ajouter « on window 0 (255 positions), with an f16 KV cache » et « Volume II traces most of llama.cpp's
  gap, on the 20b, to its rounding of the YaRN ramp rather than to kernel precision; with an f32 KV cache,
  troncons sits at the floor of the file format ». FR fidèle.

### G3. « 384 Mo » sans la carte

**Où** :
- résumé, EN l. 71 / FR l. 78 : « with a peak working set of 384 MB » ;
- § 3.1, EN l. 119 / FR l. 126 : « 384 MB […] where llama.cpp holds 10.93 GB » ;
- conclusion, EN l. 402 / FR l. 409 : « from a 384 MB working set ».

**Ce qui manque** [lu] (Tome II, chapitre 7, § C10) :
- Le moteur occupe aussi la carte : 6 317 303 600 octets, et une pointe lue par `nvidia-smi` de 6 520 à
  6 537 Mio, sous le seuil C10 de 7 279 Mio.
- Cette part est fixée par la carte, pas par le modèle, et la thèse tient.
- Mais « 384 MB », seul dans le résumé, se lit comme une mémoire totale. Et 384 Mo d'hôte contre 10,93 Go
  d'hôte compare deux moteurs qui se servent tous deux de la carte, sans le dire.

**Correctif** :
- Résumé : EN « with a host working set of 384 MB and a GPU footprint set by the card, not by the model (about
  6.3 GB of its 8 GB) » ; FR « avec un ensemble de travail de 384 Mo sur l'hôte et une empreinte sur la carte
  fixée par la carte et non par le modèle (environ 6,3 Go de ses 8 Go) ».
- Même précision au § 3.1 et à la conclusion.

---

## 6. Mineurs

Chaque mineur s'applique dans les deux langues ; les numéros de ligne sont ceux de l'anglais.

- **M1.** Résumé (l. 71) et contribution 4 (l. 88) : « a crossed experiment shows that the gain follows the
  pattern » → « a crossed experiment **on gpt-oss-20b, at the disk stage**, shows… ». Le § 6 le dit déjà ;
  le résumé doit le dire aussi.
- **M2.** § 3.1 (l. 119), ×2,22 : le Tome II prévient que troncons et la base viennent de deux séances du même
  matin (bruit entre séances que la règle ne voit pas). Ajouter « (two sessions; Volume II) ».
- **M3.** Remarque 3 (l. 154) : « when the signs of zeros are independent of everything else » → « …are fair
  coins, independent of everything else ». L'indépendance seule ne donne pas un bit entier.
- **M4.** § 4.1 (l. 221) : « a fair coin that nothing predicts » → « that neither the scale class nor the other
  nibble of its byte predicts ». Ce sont les seuls contextes que le codeur voit ; 06 § 6 le dit ainsi.
- **M5.** Proposition A1 (l. 160) et limites (l. 393) : 000cef9 est un commit de la synthèse ; `gemv.cuh` y est
  dans sa version 4473050. Le fichier a changé depuis (0be464a : le lecteur des valeurs devient un paramètre
  de patron, et le mode exact « fait exactement les mêmes fmaf »). C'est cette version, celle du lot A, que la
  mesure des 8 640 lignes a éprouvée. Citer les deux : démontrée sur 4473050, inchangée dans le chemin exact
  en 0be464a, mesurée sur cette dernière. « The kernel of today » se lit alors juste.
- **M6.** Légende de la figure 2 (l. 201) : « Over the 540 CODES_CTX tables of layers 0, L/2 and L−1 » est faux.
  Les 540 tables sont celles de **toutes** les couches (216 + 324, `tables-octets.json`). Seul le relevé des
  fréquences (`tables-octets.csv`, données de la figure) se borne aux couches 0, L/2 et L−1. Écrire « Over all
  540 CODES_CTX tables of both models ». Hérité du Tome III (H1).
- **M7.** Tableau 2 (l. 241) et figure 3 (l. 226) : la ligne « bits per expert weight » donne des bits de flux
  (médianes + δ + codes ; leur différence vaut 0,12563 sur le 120b). La ligne du gain (0,12562) vient des
  octets de tronçons. Le (a) de la figure 3 est en bits de flux de codes par tenseur, pas en « coded chunks ».
  Nommer la ligne « coded streams » et corriger la légende. Le 3,26 % (0,12562 / 3,85456) mêle les deux et
  reste juste à l'arrondi.
- **M8.** § 4.4 (l. 304) et limites (l. 394) : « about 1.9 MB are not explained » → « about 2.0 MB »
  (s2 : 6,45 − 4,47 = 1,98 ; 1,9 est le reste de s1).
- **M9.** § 4.4 (l. 305) : « none of 36 passes under load » ; les 36 passes sont celles des **deux** séances du
  juge (120b et 20b). Écrire « none of the 36 passes of the judge's two sessions ».
- **M10.** § 4.5 (l. 321) : en anglais, la phrase barrée est une traduction (l'original est en français,
  06 § 8). Ajouter « (translated) ».
- **M11.** § 4.5 (l. 323) : « fast ones stop before » ; les requêtes rapides finissent aussi exactement à une
  fin de tronçon v1.2 (B20 natif, A20 au motif de B20 ; `JUGEMENT-placement.md` § 5.6). Le dire.
- **M12.** § 5, garde (l. 360) : « The reason is measured too » ne donne que les cascades. Selon le juge
  (`genome/pistes/tropicale/JUGEMENT.md` §§ 4.2 et 12), l'échec vient de l'hétérogénéité des couches (38 à
  60 % attrapées aux couches 8 à 23) et des bascules secondaires ; la cascade verticale stricte n'en explique
  qu'un quart. Ajouter les couches.
- **M13.** § 5, spectres (l. 362) : « What is true instead » couvre une partie que le Tome III dit
  « exploratory measurement, not declared and not judged » (la queue des lignes géantes, l'échelle par
  ligne ; `spectres.md`, « Ce qui pourrait être faux », point 5). Garder « 48/48 ont plus de queue que leur
  permutée » comme jugé ; marquer le reste.
- **M14.** § 5, mimétisme (l. 364), et tableau 5 (l. 378-379) : trois corrections.
  - (i) La KL 0,0314 est mesurée contre le même moteur sans biais (gpt-oss-20b, 238 emplacements), pas contre
    la référence ; contre la référence f64, elle vaut 0,03135, à titre d'information. Dire « against the
    unbiased engine ».
  - (ii) « open (four) or useless (inclusive RAM tier) » fait d'une des cinq pistes une piste inutile. Le juge
    de P2 (cache exclusif) dit « ouverte » ; l'étage inclusif est un résultat de côté.
  - (iii) Aucun seuil n'est donné pour ces cinq pistes. Renvoyer à leurs seuils (Tome III, chapitre 6), ou
    donner celui qui décide pour chacune.
- **M15.** § 5, mode rapide (l. 366), deux corrections.
  - « its announced generation gains, ×2.00 on the 120b » : sur le 120b, le compagnon rapide était la
    **frontière** avec perte. La mutation synonyme du 120b n'a jamais été écrite (`genome/07-genome-synonyme.md`
    § 0, point 6). Écrire « the announced gains of the fast mode ».
  - « KL −0.1565 ± 0.0334 » est une différence appariée (λ = 0 moins la frontière), pas une KL. Écrire
    « ΔKL = −0.1565 ± 0.0334 ».
- **M16.** Tableau 5 (l. 380), seuil du mode rapide : les seuils déclarés sont r(R/B) ≥ 1,769 (120b) et
  ≥ 1,227 (20b), c'est-à-dire g(1 − 2σ) (`JUGEMENT-construction.md` §§ 6.2-6.3 ; `analyse-*.json`). Les écrire
  à la place de « ×2.00 and ×1.24 reproduced ».
- **M17.** `construire-article.sh` : le témoin du paquet compile deux fois et ne cherche que « undefined ». En
  anglais, la deuxième passe laisse « Label(s) may have changed. Rerun ». Ajouter une troisième passe, ou
  faire tomber le témoin sur « Rerun ». « 0 avertissement » ne vaut que pour la construction complète.
- **M18.** Bibliographie : deux corrections.
  - Le titre du Tome I est inventé. Sa page de titre dit « troncons: running a model far larger than memory »
    (sous-titre « Research thesis — Part I and II: the measured foundations »), pas « troncons, Volume I: the
    measured foundations ».
  - BibTeX met « volume » en minuscule ; protéger `{Volume}`. La version française cite les titres anglais des
    tomes ; ils ont des titres français (« troncons, Tome II : le système », etc.).

---

## 7. Hors du flux (lecture seule pour moi, pour l'orchestrateur)

- **H1.** Le Tome III, chapitre 8 (EN l. 96, « What the fold does to the tables », et la légende de la figure
  III-8.2 si elle le reprend), écrit « Over the 540 CODES_CTX tables of layers 0, L/2 and L−1 ». Même erreur que
  M6, née là : les 540 tables sont toutes les couches. Le juge final du Tome III ne l'a pas vue. Je n'y touche
  pas.

---

## 8. Ce qui revient à Stone (à lui seul, sans réponse par délégation)

- L'emplacement public (`\Emplacement`) du code, des journaux et des tomes. Sans lui, l'article ne se soumet
  pas : il renvoie à un dépôt que personne ne peut ouvrir.
- **Le nom d'auteur.** arXiv demande « Firstname Lastname » (prep.html, lu le 2026-10-29). « Stone » seul
  pourrait être refusé à la modération ; la forme du nom est la sienne.
- **La forme de la soumission bilingue.** arXiv accepte les traductions (translations.html) mais ne dit pas
  ici s'il faut une soumission ou deux. Deux options : anglais seul avec le français dans la même archive, ou
  deux soumissions liées.
- Le compte, le parrainage, la catégorie (cs.LG proposé, cs.DC en liste croisée) et la licence.

---

## 9. Ce qui pourrait être faux (dans ce jugement)

- **La recherche des travaux antérieurs** (G1) tient en deux recherches web et la lecture de trois pages
  d'arXiv (résumés, et le § 4.3 de NxFP en HTML), le 2026-10-29. D'autres travaux peuvent exister (codage sans
  perte du FP4, canonisation du zéro signé). Je n'ai pas lu RaZeR ni Heilper et Singer en entier, seulement
  leur résumé.
- **Les pages d'aide d'arXiv** ont été lues par un outil qui résume. Les phrases citées le sont telles qu'il
  les a rendues ; je n'ai pas vu la mise en page.
- **Les paquets** sont compilés sous MiKTeX 26.5, pas sous le TeX Live 2025 d'arXiv. Un écart d'une page reste
  possible, comme le rédacteur le dit.
- **La longueur du résumé** est approchée (entre le LaTeX brut et un texte nettoyé) ; le champ réel d'arXiv
  tombera entre les deux.
- **Les chiffres du Tome II, des spectres et de la duplication** sont lus dans leurs documents jugés, pas
  recalculés depuis les journaux bruts (§ 1.2).
- **Les fichiers de données des figures** (`memoire/figures/tome3/donnees/codon-*.csv`) sont marqués modifiés
  dans l'arbre de travail. `git diff` n'y montre aucun changement de contenu (fins de ligne) ; je les ai lus
  tels quels.
- **La frontière entre grave et mineur** est la mienne. J'ai appelé grave une phrase qui fait dire à
  l'article plus que les mesures ou les jugements, sur un point qu'un relecteur retiendra, ou une absence qui
  fait tomber la nouveauté. M6, M13 et M15 sont à la limite.
- **M5** suppose que la mesure des 8 640 lignes a tourné sur la version 0be464a de `gemv.cuh`. Le lot A
  (a50c380, 08 h 47) suit 0be464a (08 h 31) et ajoute ce témoin, mais je n'ai pas relu le journal de
  compilation.

---

## 10. Ce qui reste

1. Le rédacteur corrige G1 à G3, puis M1 à M18, dans les deux langues. Il reconstruit (`construire-article.sh`)
   et relance `parite_nombres.py`, `medianes_j1.py` et mes `refaire_chiffres.py` et `parite_structure.py`
   (ce dernier se lit en multiensemble : l'ordre peut changer avec les mots).
2. Un contre-jugement des corrections, par un juge qui ne les a pas écrites.
3. Corriger le Tome III pour H1 (orchestrateur).
4. Les gestes de Stone (§ 8).
