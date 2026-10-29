# Le contre-jugement des corrections de l'article court

Rôle : contre-juge indépendant. Je n'ai rien écrit de l'article, ni du jugement (`JUGEMENT-article.md`, 0e4dac8 /
7d77131 sur `main`), ni des corrections. Date : 2026-10-29. Objet : le commit des corrections, **2010c97** sur `main`
(même contenu que a8b27fc sur la branche de l'arbre de travail du correcteur : `git diff a8b27fc 2010c97` est vide
sur `memoire/article/{en,fr,commun}` et `construire-article.sh`). J'ai lu `SOCLE.md`, le jugement, la note du
correcteur (`REPRISE-correcteur-article.md`), `correcteur/verifications.txt`, le diff entier, puis les deux
articles en entier.

Étiquettes : **[mes.]** refait ici ; **[lu]** lu dans le fichier cité, non refait ; **[litt.]** source extérieure
lue à son adresse le 2026-10-29.

Mes outils, hors du dépôt (dans mon répertoire temporaire, non commités : ils ne produisent aucun chiffre publié) :
un extracteur des nombres du corps EN et FR, écrit sans ouvrir `parite_nombres.py` (multiensemble et ordre ;
témoin `--casser` : un nombre ajouté au français fait tomber le multiensemble, vérifié), et deux dossiers neufs de
compilation.

---

## 0. Verdict

**Les trois graves sont levés, dans les deux langues. Aucune correction ne fait dire faux. Aucun grave neuf.**

- Chaque chiffre neuf ou déplacé par le diff, refait par mon chemin depuis son journal ou son jugement source :
  tous tiennent (§ 2). Aucun chiffre barré ne revient : ni −3,56 %, ni « l'état du fichier », ni « pas le format »
  hors de la phrase barrée.
- La parité EN/FR tient, chiffre pour chiffre (833 nombres de part et d'autre, même multiensemble, par mon outil ;
  287 distincts et 926 occurrences par celui du rédacteur).
- Les deux paquets arXiv se déplient et compilent seuls (pdflatex, trois passes, 0 erreur, 0 renvoi indéfini,
  0 « Rerun » à la dernière passe), 14 et 14 pages ; leur texte est égal à celui des PDF commités ; le `.bbl`
  refait par BibTeX depuis la source est égal à celui du paquet.

**Du point de vue du contenu, l'article peut être soumis tel quel.** Il ne peut pas l'être tant que
`\Emplacement` est vide (« [location to be filled in] ») : c'est à Stone (§ 6). Je recommande, sans en faire une
condition, trois mineurs neufs peu coûteux (N1 à N3, texte seul) : un antécédent de plus au recyclage du zéro
(BitMoD), une phrase ambiguë sur « le plancher du format de fichier », et la mémoire engagée de 6,93 Go que le
Tome II publie.

---

## 1. Les graves

### G1, la nouveauté : levé

**Ce que l'article dit maintenant** (EN l. 104, FR l. 111, et une phrase neuve de l'introduction, EN l. 86) :
la redondance est connue ; NxFP remappe le code −0 des formats signe-grandeur à la moitié du plus petit niveau et
l'applique à MXFP4 ; RaZeR remappe le zéro redondant de NVFP4 à des valeurs de quantification de plus ; ce sont des
formats neufs, avec perte, et aucun ne mesure la fréquence des −0 dans un modèle publié ; Heilper et Singer
étendent le codage sans perte au FP8 et au FP4, mais pour le FP4 ne compressent que les échelles. Ce qui reste neuf :
la mesure, dans un modèle déjà publié en MXFP4, que le signe d'un zéro ne porte pas d'information, et son retrait
sans perte avec une démonstration sur le noyau. La contribution 1 est réécrite (la mesure d'abord, l'énoncé dit
« élémentaire »).

**Ce que les sources disent** [litt., lues le 2026-10-29, page d'arXiv et texte HTML] :
- **NxFP**, https://arxiv.org/abs/2412.19821 (v1 seule, 2024-12-15) et https://arxiv.org/html/2412.19821v1.
  § 4.3 « Code Recycling » : le code de −0 (`1000`, figure 6) est remappé à 1/2 × V_smallest ; § 3 : MxFP4
  gaspille deux codes pour +0 et −0 ; § 7.6 et figure 6 : appliqué à MxFP4 (et à BFP4). Quantification directe
  depuis une précision plus haute (« direct-cast »), donc avec perte ; aucune fréquence de −0 mesurée dans un modèle
  publié. **L'article dit exactement cela.**
- **RaZeR**, https://arxiv.org/abs/2501.04052 (v1 2025-01-06, v2 2026-01-29, v3 2026-01-31) et
  https://arxiv.org/html/2501.04052v3. NVFP4 ; le zéro redondant du FP4 est remappé, par bloc, à une valeur
  spéciale (§ 4.2), au moyen du bit de signe inutile de l'échelle FP8 ; quantification de modèles FP16, avec perte
  de perplexité rapportée (§ 5.2) ; MXFP4 seulement comme base de comparaison (§ 5.1) ; aucune fréquence de −0, rien
  sur l'information portée par le signe. **L'article dit exactement cela.** Le `.bib` donne v1 et v3 ; v2 existe
  (2026-01-29), ce qui ne change rien.
- **Heilper et Singer**, https://arxiv.org/abs/2508.19263 (v1 seule, 2025-08-20) et
  https://arxiv.org/html/2508.19263v1. § 3.4 : pour le FP4, « targets only the scaling factors » et range les
  valeurs quantifiées sans les compresser ; § 4.4 : les flux des valeurs 4 bits paraissent statistiquement
  uniformes ; rien sur le zéro signé. **L'article dit exactement cela**, et le correcteur a eu raison de préciser
  le texte proposé par le jugement (« étendu au FP4 » seul aurait exagéré l'antécédent).

**Ni exagéré, ni minimisé.** La phrase de nouveauté est bornée à ce qui est mesuré (un modèle publié, le signe des
zéros, le retrait sans perte, la preuve sur le noyau) et ne nie plus l'antécédent. La phrase neuve de l'introduction
(« nous gardons le modèle tel qu'il a été publié, chaque poids avec la même valeur ») dit la vraie différence de
contrat avec NxFP et RaZeR.

**Un antécédent de plus, non cité (mineur N1, pas un grave)** [litt.] : **BitMoD** (Chen, AbouElhamayed, Dai,
Wang, Andronic, Constantinides, Abdelfattah), https://arxiv.org/abs/2411.11745, v1 2024-11-18, v2 2025-04-26,
HPCA 2025. Son § II-C propose de « repurposing a redundant zero value with another special value », et le § III-A
remplace le zéro redondant de variantes FP3/FP4 par une valeur spéciale. Il précède NxFP d'un mois ; le billet des
auteurs de RaZeR (https://abdelfattah-lab.github.io/blogs/razer-blog, sans date, citation 2025) dit l'idée
« originally published » là, et étend RaZeR à MXFP4 (expériences sur Llama et Qwen, pas sur gpt-oss ; aucune mesure
de la fréquence des −0). La phrase de nouveauté de l'article reste vraie avec lui : BitMoD réaffecte, avec perte, et
ne mesure pas le signe des zéros d'un modèle publié. Mais un relecteur qui connaît RaZeR connaît BitMoD.

### G2, l'exactitude du moteur : levé

Les quatre endroits (a) à (d) du jugement sont corrigés dans les deux langues :
- (a) introduction : « au bit, les logits que le même moteur calcule sur les poids non compressés » ;
- (b) travaux liés : « ceux que le moteur calcule sur les poids bruts du GGUF » ;
- (c) conclusion : « ses logits égaux au bit à ceux du fichier brut » ; et au § 3.1 : « par le même moteur » ;
- (d) § 3.1 : « sur la fenêtre 0 (255 positions) avec un cache KV en f16 », puis l'écart de llama.cpp ramené, sur le
  20b, à son arrondi de la rampe YaRN, et troncons au plancher en KV f32.

Le résumé dit « the engine's logits stay identical to the bit », et plus « the logits of the model ». Aucune phrase
ne prête plus au modèle l'exactitude du moteur. Les chiffres viennent du Tome II, refaits au § 2.

Reste une ambiguïté de lecture, en mineur N2 : « au plancher du format de fichier » désigne le format `.kld` des
logits (log q quantifié sur 16 bits), et non le `.trc` ni MXFP4. Dans un article sur un format de fichier, un lecteur
le lira de travers.

### G3, la mémoire sans la carte : levé

- Résumé : « host working set of 384 MB and a GPU footprint set by the card, not by the model (about 6.3 GB of its
  8 GB) » ; FR fidèle.
- § 3.1 : « peak host working set » ; « pinned memory included » ; llama.cpp « 10.93 GB of host memory » ; « both
  engines also use the GPU, troncons about 6.3 GB of its 8 GB (6 317 303 600 bytes), a share set by the card, not by
  the model ».
- Conclusion : « a 384 MB host working set and a GPU footprint set by the card » ; « Host memory no longer follows
  the size of the model ».

« Fixée par la carte, non par le modèle » est vérifié par mon chemin [mes.] : les journaux bruts du J1 et du lot A
donnent `octets_vram_moteur` = 6 317 303 600 (120b, v1.0, 326 emplacements ;
`mesures/genome/construction/codon/journaux/s1-j1-1-A.json`), 6 312 830 768 (120b, v1.2 : 6 317 303 600 −
4 472 832, les 12 tampons, au bit), et 6 350 913 200 à 6 355 582 640 (20b, 362 emplacements ;
`s1-c1-20b-*.json`). Le modèle cinq fois plus petit occupe autant de carte : le nombre d'emplacements remplit le
budget.

Deux trous de même nature restent, en mineurs : la mémoire engagée privée de 6,93 Go que le Tome II publie (N3), et
l'empreinte de llama.cpp sur la carte, que « both engines also use the GPU » ne chiffre pas (N4).

---

## 2. Chaque chiffre neuf ou déplacé, refait (consigne, point 2)

| Chiffre (EN / FR) | Où | Mon chemin | Verdict |
|---|---|---|---|
| 6 317 303 600 octets ; « about 6.3 GB of its 8 GB » | résumé, § 3.1, conclusion | journaux bruts `s1-j1-*-A.json` (`octets_vram_moteur`) ; 6,317 Go décimaux ; 8 Go nominaux (8 188 Mio mesurés) | tient [mes.] |
| part « fixée par la carte, non par le modèle » | idem | 20b : 6 350 913 200 et 6 355 582 640 octets à 362 emplacements, 120b : 6,31 à 6,32 Go à 326 | tient [mes.] |
| 384,19 Mo « mémoire épinglée comprise » | § 3.1 | Tome II, 07-resultats.tex l. 121 (« pinned memory included ») | tient [lu] |
| 10,93 Go « de mémoire hôte » | § 3.1 | idem l. 121 | tient [lu] |
| « fenêtre 0 (255 positions) », KV f16, 0,00308 et 0,0607 | § 3.1 | Tome II, tableau C4 l. 316-317 (244/255 et 205/255) | tient [lu] |
| « l'essentiel » de l'écart de llama.cpp, sur le 20b, par la rampe YaRN | § 3.1 | Tome II l. 326 : 0,0143 sur 0,0261 (55 %) sur la fenêtre 0, 0,0145 sur 0,0226 (64 %) sur 10 fenêtres ; je refais les deux rapports | tient [lu, calc.] |
| KV f32 « au plancher » | § 3.1 | Tome II l. 69, 318 : −0,00048, 255/255 | tient [lu] ; formulation : N2 |
| « deux séances du même matin » (×2,22) | § 3.1 | Tome II l. 255-256 (06:41-07:19 contre 08:13-10:06) | tient [lu] |
| 0,12563 bit (flux, 120b) | source du tableau 2 | `tailles.json`, `gain_bpp_flux` = 0,1256338 | tient [mes.] ; voir N5 |
| « stream bits per weight » 3,85456 → 3,72892 | tableau 2 | `tailles.json`, `bpp_total_03_v10/v12` = 3,8545552 et 3,7289214 | tient [mes.] |
| 3,26 % = 0,12562 / 3,85456 | résumé, § 4.2 | 3,259 % ; c'est bien −3,26 % sur le 120b, et non −3,56 % (éclaireur, 12 tenseurs du 20b) | tient [calc.] |
| environ 2,0 Mo non expliqués | § 4.4, limites | 6,45 − 4,472832 = 1,977 Mo | tient [calc.] |
| 36 passes des deux séances du juge | § 4.4 | `JUGEMENT-construction.md` l. 284 ; 2 × (6 disque + 12 moteur) = 36 | tient [lu, calc.] |
| seuils 1,769 et 1,227, « gain annoncé × (1 − 2σ) » | tableau 5 | `analyse-120b.json` : seuil 1,76942 (2,00 × (1 − 2 × 0,057645)) ; `analyse-20b.json` : 1,22722 (1,241 × (1 − 2 × 0,005552)) | tient [mes.] |
| ΔKL = −0,1565 ± 0,0334 (différence appariée) | § 5 | redonné par `refaire_chiffres.py` ; libellé conforme au jugement M15 | tient |
| 0,0314 contre le moteur sans biais ; borne 0,0384 | § 5, tableau 5 | `JUGEMENT-routeur-ligne.md` l. 14 (« Base … P0, même moteur sans biais ») et l. 96 (0,031388) ; seuil déclaré sur la même base | tient [lu] |
| cinq pistes ouvertes | § 5, tableau 5 | Tome III, 06-mimetisme.tex l. 15 : P1 ouvert, P2 ouvert, P4 ouvert (plutôt du côté de tombe), P5 ouvert, P6 ouvert au décodage ; P3 à la limite | tient [lu] |
| l'étage inclusif n'ajoute rien tant qu'il n'est pas plus grand que le cache en VRAM | § 5 | `P2/resultat.md` l. 57 : 0,0000 à R = 80 et 160 ; au plus 7,65 × 10⁻⁴ à R = V (l. 32) | tient [lu] |
| couches 8 à 23 : 38 à 60 % ; la cascade verticale stricte : un quart | § 5 | `genome/pistes/tropicale/JUGEMENT.md` l. 69 (37,8 % à 60,5 %), l. 132-133, l. 281 (24,5 %) | tient [lu] |
| requêtes rapides : 3,5 % avant une fin v1.0, ou exactement à une fin v1.2 | § 4.5 | `JUGEMENT-placement.md` § 5.6, l. 266-269 | tient [lu] |
| commits 4473050, 000cef9, 0be464a, a50c380 | prop. A1, limites | `git log` de `gemv.cuh` : deux commits seulement ; blob 75456f5 à 4473050 et à 000cef9 ; blob df6776b à 0be464a, à a50c380 et à HEAD ; `git diff 4473050 0be464a` relu : le lecteur des valeurs devient un paramètre de patron, mêmes `fmaf` dans le même ordre | tient [mes.] |
| 540 tables : toutes les couches | légende fig. 2 | 24 × 9 + 36 × 9 = 216 + 324 (recalcul de `refaire_chiffres.py`, relancé) | tient [mes.] |
| titres des tomes | `.bib`, macros | pages de titre : Tome II et III égaux mot pour mot dans chaque langue ; Tome I : le titre de `memoire/commun/page-titre.tex` est abrégé (sa seconde moitié « compress to the extreme… » est omise), sans rien d'inventé | tient [lu] |

`refaire_chiffres.py` du juge, relancé : **156 chiffres sur 156 tiennent**, code 0 [mes.]. Sa section « Relevés »
imprime encore l'état d'avant les corrections (« l'article écrit « about 1.9 MB » », etc.) : ce texte est figé dans
l'outil et ne reflète pas l'article (hors du flux, H2).

**Aucun chiffre barré ne revient** [mes., recherche dans les deux `.tex`] : 0 occurrence de « 3.56 » / « 3,56 »,
de « not the format » / « pas le format » hors de la phrase barrée, de « the model's own », « du modèle au bit »,
« served exactly ». Le ×1,44 reste dit propre à ce disque, par le motif des requêtes de lecture, et non par les
octets ni par l'état du fichier ; « the state of the files » n'apparaît qu'aux limites, comme erreur barrée d'un juge.

---

## 3. Les deux langues (consigne, point 3)

- `parite_nombres.py` (rédacteur) : EN 287 distincts, 926 occurrences ; FR idem ; « PARITÉ : tient », code 0 ;
  `--casser` fait tomber (424242, FR 1). [mes.]
- Mon extracteur : **833 nombres de part et d'autre, 272 distincts, multiensemble égal** ; témoin cassé : tombe.
  Quatre écarts d'ordre, tous d'ordre des mots (« an 8 GB RTX 4060 » / « RTX 4060 de 8 Go » ; « KL … of 0.00308 » /
  « KL de 0,00308 contre » ; « gpt-oss-20b's v1.0 file » / « le fichier v1.0 de gpt-oss-20b » ; « overrun a v1.2
  chunk end by 3.5 % » / « débordent de 3,5 % une fin de tronçon v1.2 »). [mes.]
- `parite_structure.py` (juge) : structure 58/58, citations 33/33 dans le même ordre, provenance 32/32, figures
  5/5, `\barre` 1/1, `\textbf` 39/39, `\emph` 10/10 ; il rend « tombe » sur l'ordre des nombres pour ces mêmes
  écarts de mots, comme le jugement le prévoyait (à lire en multiensemble). [mes.]
- J'ai lu chaque passage corrigé dans les deux langues, phrase contre phrase (résumé, introduction, contributions,
  travaux liés, § 3.1, remarque 3, prop. A1, légendes des figures 2 et 3, tableau 2, § 4.4, § 4.5, § 5 en entier,
  tableau 5, limites, conclusion) : même sens partout. La note de traduction est juste dans chaque langue
  (« Translated from the French original » ; « Texte d'origine, en français »).
- `longueur_resume.py` : EN 1 808 (LaTeX brut) / 1 746 (approché) ; FR 1 875 / 1 805 ; limite 1 920. [mes.]

---

## 4. Les paquets arXiv (consigne, point 4)

Dans un dossier neuf par langue, sous mon répertoire temporaire [mes.] :
- `arxiv-en.tar.gz` et `arxiv-fr.tar.gz` se déplient à plat en trois fichiers (`troncons-article.tex`, `.bbl`,
  `troncons-figures.pdf`). Le `.tex` du paquet ne diffère du commité que par `\bibliography{troncons-article}` (fins
  de ligne mises à part) ; `.bbl` et figures égaux octet pour octet aux commités.
- pdflatex trois fois, sans BibTeX (arXiv lit le `.bbl`) : **0 erreur, 0 renvoi ou citation indéfini, 0 « Rerun to
  get » ni « Label(s) may have changed » à la troisième passe ; 14 pages chacun** (EN 1 060 912 octets, FR
  1 075 231, la taille des PDF commités). Après deux passes, l'anglais laisse encore un « Rerun » : le témoin neuf
  de `construire-article.sh` (M17) le voit bien (3 lignes après une passe, 1 après deux, 0 après trois). AutoTeX
  relance de lui-même.
- `pdftotext` de mes PDF : **texte égal** à celui des PDF commités, dans les deux langues.
- Construction depuis la source, avec BibTeX, dans un dossier neuf (`.tex`, `.bib` de `commun/`, figures) :
  BibTeX code 0, sans avertissement ; 14 pages ; 0 erreur ni renvoi indéfini ; **le `.bbl` refait est égal à celui
  du paquet**, dans les deux langues.

---

## 5. Lu comme un relecteur d'arXiv (consigne, point 5)

Je n'y trouve plus d'affirmation fausse. Ce qui reste est de la précision ou de la clarté ; chaque mineur vaut
pour les deux langues, et les numéros de ligne sont ceux de l'anglais.

- **N1. Un antécédent de plus : BitMoD** (§ 1, G1). Correctif, dans les travaux liés, avant NxFP : EN « BitMoD
  first replaced the redundant zero of FP3 and FP4 variants by a special value \citep{chen2025bitmod}; the code
  recycling of NxFP… » ; FR « BitMoD a le premier remplacé le zéro redondant de variantes FP3 et FP4 par une valeur
  spéciale \citep{chen2025bitmod} ; le recyclage de code de NxFP… », et « Both are » → « All three are » / « Ce
  sont trois formats ». Entrée `.bib` : Chen, AbouElhamayed, Dai, Wang, Andronic, Constantinides, Abdelfattah,
  « BitMoD: Bit-serial Mixture-of-Datatype LLM Acceleration », arXiv:2411.11745 (v1 2024-11-18, v2 2025-04-26),
  HPCA 2025, `\Consulte{2026-10-29}`, après lecture de son § II-C. Optionnel : citer le billet de RaZeR pour son
  extension à MXFP4.
- **N2. « the floor of the file format »** (l. 124 ; FR « au plancher du format de fichier »). Le plancher est
  celui du format `.kld` des logits (log q sur 16 bits, pas d'environ 2,44 × 10⁻⁴ nat ; Tome II l. 300), pas du
  `.trc`. Correctif : EN « with an f32 KV cache, troncons's KL (−0.00048) is at the resolution floor of the logit
  files themselves » ; FR « avec un cache KV en f32, la KL de troncons (−0,00048) est au plancher de résolution des
  fichiers de logits eux-mêmes ». Le chiffre −0,00048 est au Tome II (tableau C4) ; l'ajouter demande de relancer
  la parité.
- **N3. La mémoire engagée** (l. 124). Le Tome II (07-resultats.tex l. 168) publie, non jugée, une mémoire engagée
  privée de 6,93 Go, de l'ordre des allocations sur la carte et de la mémoire épinglée, réservée contre la limite
  d'engagement de Windows sans occuper la RAM. « Host working set of 384 MB » est juste, mais un relecteur qui
  mesurera la mémoire engagée trouvera 18 fois plus, et lira de nouveau G3. Correctif, au § 3.1 : EN « (its private
  committed memory, 6.93 GB, is of the order of its GPU allocations and pinned memory: reserved against the commit
  limit, not resident; Volume II) » ; FR fidèle. Ou une ligne aux limites.
- **N4. L'empreinte de llama.cpp sur la carte** (l. 124). « both engines also use the GPU » ne chiffre que
  troncons. Donner l'empreinte de llama.cpp si le Tome II l'a, sinon écrire que la comparaison porte sur la mémoire
  de l'hôte seule.
- **N5. Tableau 2.** Les valeurs arrondies donnent 3,85456 − 3,72892 = 0,12564, la ligne de source dit 0,12563
  (juste, depuis les valeurs non arrondies de `tailles.json`). Ajouter « unrounded » / « non arrondies ».
- **N6. « no computation ever reads it »** (résumé ; conclusion « no computation reads »). Ce qui est établi : les
  lecteurs des codes de ce moteur et de ggml rendent les mêmes bits sur les deux codes (§ 3.2 ; la GEMV lit bien le
  code 8, comme −0,0f). L'article dit lui-même qu'un noyau qui partirait de −0 sortirait du résultat. Correctif :
  EN « and no computation of the engines considered depends on it » ; FR « et aucun calcul des moteurs considérés
  n'en dépend ».
- **N7. Heilper et Singer trouvent les valeurs FP4 sans redondance** (§ 4.4 : flux « statistically uniform »,
  sur DeepSeek-R1 en NVFP4). Le v1.0 de troncons code pourtant 3,85 bits par poids d'expert, plus 0,126 retirés par
  le fondu. Un relecteur demandera pourquoi. Une demi-phrase suffit, par exemple : autre modèle et autre format
  (NVFP4, blocs de 16), et un codeur par contexte de classe d'échelle sur l'alphabet des octets.
- **N8. Bibliographie.** En français, `\NoteTome` commence en minuscule après un point (« Rapport technique, 2026.
  versions anglaise et française »). Le Tome I s'appelle « Volume I » / « Tome I » dans le texte et « Research
  thesis, Parts I and II » / « parties I et II » dans sa référence ; un lecteur se demandera si ce sont deux
  documents. Ajouter « (Volume I) » / « (Tome I) » au titre.
- **Hérité du jugement, toujours ouvert** (jugement § 3, laissé par le correcteur, par délégation) : le jargon du
  projet (J1, séance s2, A-C2, « tronçon », les étiquettes [meas.]) est défini au premier passage, mais tard pour
  certains ; « des juges qui n'ont pas fait le travail » ne dit pas qui ils sont, et un relecteur le demandera.
  Ce qu'on en dit revient à Stone.

**Ce qui tient, à la lecture** : la nouveauté est dite à sa juste taille et le gain pour ce qu'il est (3,26 %,
exact et prouvé) ; chaque vitesse est dite de cette machine ; le ×1,45 est attribué au motif de lecture, avec la
phrase fausse barrée et sa date ; chaque résultat négatif a son seuil déclaré ; les limites disent ce qu'un
relecteur chercherait (un disque, une famille de modèles, le noyau d'une version donnée, des juges qui partagent des
conventions).

---

## 6. Ce qui revient à Stone (rien de changé depuis le jugement, § 8)

- L'emplacement public du code, des journaux et des tomes (`\Emplacement`). Sans lui l'article renvoie à un dépôt
  que personne ne peut ouvrir : c'est la seule chose qui bloque la soumission.
- La forme du nom d'auteur (arXiv demande « Prénom Nom »), la forme bilingue (une soumission ou deux), le compte, le
  parrainage, la catégorie, la licence, et les déclarations qu'arXiv demande à la soumission.

## 7. Hors du flux

- **H1** (Tome III, « 540 tables des couches 0, L/2, L−1 ») : toujours ouvert, à l'orchestrateur ; l'article est
  corrigé (M6).
- **H2.** `memoire/article/juge/refaire_chiffres.py` imprime une section « Relevés » figée sur l'article d'avant les
  corrections. Ce texte ne change pas le code de retour et ne dit rien de faux sur l'ancien article, mais il trompe
  qui lit son journal aujourd'hui. Je n'y touche pas : ce n'est pas mon outil.

---

## 8. Ce qui pourrait être faux (dans ce contre-jugement)

- **Les sources** ont été lues sous forme de pages converties par un outil qui résume (pages abs et HTML d'arXiv,
  billet de RaZeR), pas dans leur PDF entier. Les courtes citations sont celles qu'il a rendues. La fin du HTML de
  RaZeR (environ 30 000 caractères) et celle de BitMoD (environ 17 000) n'ont pas été lues : une mesure de la
  fréquence des −0 pourrait s'y trouver, ce qui m'étonnerait.
- **La recherche des antécédents** tient en une recherche sur le web et la lecture de cinq pages. D'autres travaux
  peuvent exister (canonisation du zéro signé, codage entropique de MXFP4).
- **Les chiffres du Tome II** (fenêtre 0, 55 %, deux séances, 384,19 Mo, mémoire engagée) sont lus dans le
  chapitre 7 jugé, pas recalculés depuis les journaux bruts ; seul l'octet de VRAM du moteur l'est.
- **Mon extracteur de nombres** est une expression régulière simple ; il compte 833 nombres là où l'outil du
  rédacteur en compte 926 (il ne lit pas les chemins ni certaines macros). Les deux disent la parité ; un nombre qui
  manquerait aux deux de la même façon échapperait aux deux.
- **Les compilations** sont faites sous MiKTeX, pas sous le TeX Live 2025 d'arXiv ; une page d'écart reste
  possible. Je n'ai pas relancé `construire-article.sh` (il réécrit les fichiers commités) : j'ai refait ses étapes
  à part, dans des dossiers neufs.
- **La frontière entre grave et mineur** est la mienne. N1 et N3 sont les plus proches d'un grave : N1 parce qu'un
  relecteur de RaZeR connaît BitMoD, N3 parce qu'il reprend la question de G3 sous une autre forme. Je ne les fais
  pas graves, parce qu'aucune phrase de l'article n'en devient fausse.
