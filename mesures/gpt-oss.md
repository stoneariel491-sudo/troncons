# La carte au travail : la base llama.cpp et la localité des experts, mesurées sur gpt-oss

Mesures de troncons, 2026-10-15. Lire `SOCLE.md` d'abord. Étiquettes : **[mes.]** mesuré ici, sur la
machine de Stone ; **[calc.]** calculé par une formule écrite ici à partir de chiffres nommés ;
**[lit.]** littérature (éditeur ou article, non reproduit).

Deux mesures que toutes les études de fondation attendaient :
1. **la base** : llama.cpp b11515 tel quel sur gpt-oss-20b et gpt-oss-120b (protocole de
   `fondations/06-modeles.md` § 7), en séries alternées, sur secteur ;
2. **la localité des experts** (le trou n° 1 des études 04 et 06 : « l'instrument est prêt, la trace
   manque ») : le routage relevé jeton par jeton et couche par couche sur du texte réel, passé dans
   l'instrument de l'étude 04, et le plafond de jetons/s qui en découle avec les débits mesurés de
   l'étude 01.

Outils (tous commités) : `outils/gptoss-routage/` (traceur C++ et sa construction),
`outils/gptoss_corpus.py`, `outils/gptoss_octets.py`, `outils/gptoss_base_serie.py`,
`outils/gptoss_base_resume.py`, `outils/gptoss_localite.py`, `outils/gptoss_comparer_traces.py`,
`outils/gptoss_cache_base.py`, `outils/gptoss_disque_phases.py`, `outils/gptoss_file_disque.py`
(prêt, non lancé), `outils/gptoss_figures.py` ; l'outil de l'étude 06 `outils/modeles-base.py` (une ligne ajoutée : la
série du compteur disque, pour séparer les phases) et l'instrument de l'étude 04
`outils/chargement_localite.py` (inchangé). Données : `mesures/base-gpt-oss/`,
`mesures/localite-gpt-oss/`. Sources : `memoire/sources/mesures-gpt-oss.bib`.

---

## 0. En bref

- **La base, mesurée** [mes.] (séries ABBA, sur secteur, machine partagée) : gpt-oss-20b, génération
  **18,9 j/s** (`fit`), 11,4 (`cmoe`), 10,2 (cache d'experts de llama.cpp, 84,6 % de succès) ;
  gpt-oss-120b, **0,57 j/s** (`fit`), 0,54 (`cmoe`), **0,26 avec le cache** (35,5 % de succès : le cache
  divise la génération par deux, écart réel).
- **120b est borné par la pagination à la demande** : 0,77 à 0,91 Go lus par jeton à **0,43 Go/s**, 15 %
  du débit du disque en grands blocs (2,82 Go/s). Lire les mêmes experts à plein débit donnerait
  ×4,6 à ×6,7 [calc.], sans toucher au cache.
- **Les traces existent** : 10 669 jetons de lecture par modèle en quatre genres (prose anglaise et
  française, dialogue, code), relevés par le même moteur que la base (0 désaccord sur 345 336 et
  444 276 choix ; témoin G5 **exact** : 20 373, 88 443 et 14 446 succès simulés pour autant publiés par
  llama.cpp).
- **La localité est forte** : un jeton reprend 50 % (20b) et 31 % (120b) des experts du précédent,
  contre 12,5 % et 3,1 % au hasard uniforme ; à 20 % des experts, Belady sert 81 % (20b) et 90 %
  (120b) des accès, LRU 60 % et 78 %. L'hypothèse uniforme des études 04 et 06 sous-estimait le cache
  d'un facteur 3 à 4 sur la part servie.
- **Un théorème** [dém.] : un LRU partagé entre les L couches n'a **aucun** succès sous (L−1)·k
  emplacements (20b : 92 ; 120b : 140), et vaut **exactement** la réutilisation adjacente à L·k ;
  vérifié au succès près sur 17 traces, cassure qui tombe.
- **Le cache de la base est loin de l'optimum** : sur la génération réelle de 120b, à 323 emplacements,
  llama.cpp sert 39,2 %, un ensemble fixe 50,0 %, Belady 68,5 %. Le cache de pages du système sert
  52 à 60 % des octets d'experts, là où un LRU par expert de même taille en servirait 74 à 76 %.
- **Plafonds** [calc., succès mesurés] : 120b à 20 % du budget (atteignable ici) en LRU, 4,0 j/s en
  série et 6,6 recouvert, bornés par le disque ; au-delà de 30 %, par la PCIe. Chaque facteur de
  compression des experts en transit multiplie ces plafonds d'autant : c'est le levier de troncons.
- **Le routage dépend du chemin de calcul** (carte contre processeur : 81,1 % de choix identiques ;
  décodage contre relecture : 77,7 à 95,7 %) : la justesse d'un moteur se juge contre une base du même
  chemin.
- Machine : sur secteur à chaque passe (BatteryStatus 2) ; fichiers sur C: chiffré par BitLocker (à
  refaire sur D: non chiffré) ; d'autres agents tournaient pendant une partie des mesures (§ 11).

**D'où on part, où on va.** Au départ : un plafond calculé sous routage uniforme (étude 06, § 5 :
h = C/E), des chiffres de localité publiés sur d'autres modèles (étude 04, § 4), un instrument de
cache validé sur des traces synthétiques, et aucun chiffre de llama.cpp sur gpt-oss. Ce que ce travail
établit : la base mesurée sur les deux modèles, les traces réelles (plus de 10 000 jetons de lecture
par modèle, quatre genres), la localité et les courbes de succès qui remplacent l'hypothèse uniforme,
un théorème qui explique l'échec du LRU partagé à petit budget, le plafond de jetons/s qui en découle,
et deux faits sur le routage lui-même (sa fragilité numérique, sa dépendance au chemin de calcul).
Ce qui reste : § 10.

---

## 1. Conditions de mesure

- **Alimentation** : relevée par WMI (`Win32_Battery.BatteryStatus`, 2 = secteur) avant chaque passe de
  la base (colonne `batterie` de chaque `passes.csv`) et avant et après chaque relevé de trace
  (journaux `journal-traceur-*.log`). Toutes les passes retenues sont sur secteur (charge 80 %).
- **Disque** : les deux fichiers sont sur C:, **chiffré par BitLocker** (XTS-AES-128, étude 01, § 2.7).
  Toutes ces mesures seront refaites sur un disque D: non chiffré ; la différence donnera le coût de
  BitLocker sur un modèle réel.
- **Machine partagée** : d'autres agents travaillaient en même temps (processeur, disque, mémoire ;
  la carte était à moi seul). Le compteur disque est global : le banc soustrait la charge relevée
  pendant 10 s de repos avant chaque passe, ce qui donne parfois des octets « attribuables » négatifs
  (une rafale d'un autre programme pendant le repos). La mémoire libre variait. C'est le bruit des
  § 3.1 et 3.2, et il est grand ; pour 120b, `outils/gptoss_disque_phases.py` publie les octets bruts
  par phase à côté du débit de repos.
- **Carte** : RTX 4060 Laptop, 8 188 Mio ; 830 à 930 Mio déjà occupés par l'affichage et les applications
  de Stone au repos (colonne `vram_repos_mio`).
- **Logiciel** : llama.cpp b11515 (commit `3d65c90d0`, 2026-10-09, binaires officiels CUDA 12.4,
  licence MIT), `-t 6` (les six cœurs performants), `-c 2048`, mmap (le défaut), invite fixée de
  l'étude 06 (3 000 premiers octets de wikitext-2 test, SHA-256 `eadbe87e…eff`), 256 jetons gloutons
  (`--temp 0 --seed 1 --ignore-eos`).
- **Octets** (lus dans l'en-tête des fichiers locaux, `octets-gpt-oss.json`, témoin de fin de fichier
  tenu) [mes.] :

  | | couches L | experts E | k | un expert | experts en tout | toujours lus A | routés par jeton R = k·L·e |
  |---|---:|---:|---:|---:|---:|---:|---:|
  | gpt-oss-20b | 24 | 32 | 4 | 13,254 Mo | 10,179 Go | 1,302 Go | 1,272 Go |
  | gpt-oss-120b | 36 | 128 | 4 | 13,254 Mo | 61,073 Go | 1,686 Go | 1,909 Go |

  (A compte la tête de sortie et une ligne de la table d'enchâssement ; les deux colonnes de 120b
  retrouvent l'en-tête distant lu par l'étude 06 : 1,69 + 1,91 Go.)

---

## 2. Méthode de la base

`outils/gptoss_base_serie.py` enchaîne des passes de `outils/modeles-base.py` (étude 06) dans un ordre
en palindrome répété, la généralisation de ABBA à plusieurs configurations : (A B C C B A) × R. Une
dérive linéaire dans le temps (cache de pages qui se remplit, chauffe) pèse autant sur chaque
configuration. Bruit d'une configuration = le plus grand |X₁ − X₂| / moyenne sur ses deux passes d'un
même palindrome ; une différence est **réelle** si elle dépasse 2 × le plus grand des deux bruits **et**
3 % (règle de 06-modeles.md § 7.5, déclarée avant la mesure). Une passe d'échauffement est jetée en tête.

Les trois configurations, pour chaque modèle :

| Nom | Arguments | Ce que c'est |
|---|---|---|
| `cmoe` | `-ngl 99 --cpu-moe --fit off` | toutes les couches en carte, **tous les experts en RAM** (mmap), calculés par le processeur au décodage |
| `fit` | (rien : `--fit on` par défaut) | llama.cpp choisit seul ; il met en carte les experts des **premières** couches (20b : couches 0 à 9, et une partie de la 10 ; 120b : couches 0 et 1, et une partie de la 2 ; `llama-fit-params`, mesuré) |
| `cache` | `-ngl 99 --cpu-moe --fit off --moe-cache-mib 4096` | experts en RAM, plus le **cache d'experts en VRAM** de b11515 (EXPÉRIMENTAL) : 323 emplacements de 12,64 Mio, soit 42,1 % des experts de 20b et 7,0 % de ceux de 120b |

Ce que fait ce cache (lu dans `src/llama-moe-cache.cpp`, rien copié) : un seul LRU pour toutes les
couches de même disposition (donc partagé entre les 24 ou 36 couches) ; à chaque micro-lot de 32 jetons
au plus, il lit sur l'hôte les experts choisis (une synchronisation par couche), « touche » les succès,
puis donne aux défauts, triés par numéro, les emplacements les moins récemment utilisés, et copie ces
experts vers la carte ; les grands lots (préremplissage) ne font que lire le cache. Son bilan
(« llama_moe_cache: ubatch <= 8: hits = … ») ne s'affiche qu'avec `-lv 4` : la série 20b a été
lancée avec `-lv 3` (aucun bilan), complétée par deux passes `cachelv4` ; la série 120b est en `-lv 4`.

## 3. Résultats de la base

### 3.1 gpt-oss-20b (12,1 Go : plus que la VRAM, moins que la RAM) [mes.]

Série de 13 passes (échauffement compris) de 10:47 à 11:13 (`mesures/base-gpt-oss/20b/`, `resume.csv`),
plus deux passes `cachelv4` à 11:22.

| Configuration | génération (j/s) | préremplissage (j/s) | VRAM de pointe | ensemble de travail de pointe | texte produit (SHA-256) |
|---|---:|---:|---:|---:|---|
| `cmoe` | **11,38** (10,03 – 12,03 ; bruit 15 %) | 33,1 (21,5 – 48,9 ; bruit 46 %) | 2 630 Mio | 9,43 Go | `09e04f9f…` (4 fois) |
| `fit` | **18,92** (18,13 – 19,70 ; bruit 3,3 %) | 76,3 (73,0 – 84,8 ; bruit 15 %) | 6 885 Mio | 9,42 Go | `cfc6c660…` (4 fois) |
| `cache` 4 096 Mio | **10,15** (9,26 – 11,74 ; bruit 14 %) | 34,4 (27,1 – 47,0 ; bruit 52 %) | 6 662 Mio | 9,43 Go | `265f4af5…` (4 fois) |
| `cachelv4` (même chose, bilan affiché) | 11,21 (8,42 ; 13,99) | 40,8 | 6 640 Mio | 9,68 Go | `265f4af5…` ; **succès du cache 84,59 %** (deux fois) |

Décisions (règle du § 2) : `fit` bat `cmoe` (+66 % en génération, seuil 30 %) et `cache` (+86 %) :
réel. `cache` contre `cmoe` : −11 %, **dans le bruit** (seuil 30 %). Le préremplissage est trop
bruité pour départager autre chose que `fit`.

Ce que ces chiffres disent, confrontés aux débits mesurés de l'étude 01 [calc.] :
- **`cmoe` est borné par la RAM à un seul canal.** Le processeur lit R = 1,272 Go d'experts par jeton ;
  à 15,6 Go/s (lecture mesurée, étude 01) cela fait 81,5 ms, soit au plus **12,3 j/s** ; mesuré 11,4 :
  **93 % de ce plafond**. Ce qui manque est l'attention en carte et les synchronisations.
- **`fit` aussi.** Les experts de 14 couches sur 24 restent au processeur : 14/24 × 1,272 = 0,742 Go
  par jeton, 47,6 ms à 15,6 Go/s, plafond **21,0 j/s** ; mesuré 18,9 : **90 %**. La carte, elle, lit
  A + 10/24 · R = 1,83 Go en 7,3 ms à 251 Go/s : elle attend le processeur.
- **`cache` ne gagne rien, alors qu'il sert 84,6 % des experts depuis la VRAM.** Par jeton, 15,4 % de
  96 accès manquent : 14,8 experts × 13,25 Mo = 196 Mo copiés par la PCIe, 16 ms à 12,2 Go/s, plus
  9,5 ms de VRAM : plafond **39 j/s** ; mesuré 10,2 à 11,2 : **27 %**. Le cache de llama.cpp n'est pas
  limité par les octets mais par sa mécanique : une lecture synchrone des experts choisis par couche
  (24 allers-retours carte → hôte par jeton) et des copies d'experts non recouvertes par le calcul.
  C'est exactement le terme que l'étude 04 (§ 3.4, Edge0) désigne : **la latence domine, pas le
  volume**. Hypothèse, non isolée par une mesure de profil.
- **Disque pendant la génération** : 0,002 à 0,008 Go par jeton généré (attribuables, bruit énorme) :
  le fichier de 12,1 Go est servi par le cache de pages pendant la génération. Mais chaque passe lit
  encore **11 à 21 Go** sur le disque au chargement et au préremplissage (le fichier ne reste pas entier
  en RAM entre deux passes sur cette machine de 16 Go partagée).
- **Trois configurations, trois textes gloutons différents** pour les mêmes poids sans perte, chacun
  reproduit à l'identique par ses quatre passes. Confirme, sur gpt-oss, le constat de l'étude 06
  (§ 7.3) : le chemin de calcul fait partie du résultat.

### 3.2 gpt-oss-120b (63,4 Go : 4 fois la RAM, 8 fois la VRAM) [mes.]

Série de 13 passes (échauffement compris) de 16:47 à 19:58 (`mesures/base-gpt-oss/120b/`,
`resume.csv`, `console.log`), toutes sur secteur ; `-lv 4` (bilan du cache affiché). Un autre agent
(`juge.exe`) tournait pendant les quatre premières passes, aucun ensuite (colonne `concurrents`) : la
machine s'est calmée en cours de série, et les passes du second palindrome sont plus rapides ; l'ordre
en palindrome répartit cette dérive également.

| Configuration | génération (j/s) | préremplissage (j/s) | VRAM de pointe | ensemble de travail de pointe | texte produit (SHA-256) |
|---|---:|---:|---:|---:|---|
| `cmoe` | **0,543** (0,47 – 0,58 ; bruit 19 %) | 3,31 (2,70 – 3,77) | 3 014 Mio | 11,1 Go | `2bd58359…` (5 fois) |
| `fit` (experts des couches 0 et 1 en carte) | **0,568** (0,50 – 0,63 ; bruit 9,5 %) | 3,63 (2,96 – 4,09) | 6 041 Mio | 10,9 Go | `45a1f638…` (4 fois) |
| `cache` 4 096 Mio (323 emplacements, 7,0 %) | **0,260** (0,23 – 0,29 ; bruit 4,3 %) | 3,60 (3,20 – 3,94) | 6 934 Mio | 10,9 Go | `c7795c50…` (4 fois) ; **succès du cache 35,53 %** (13 133 sur 36 961, les quatre fois) |

Décisions (règle du § 2) : `fit` contre `cmoe` : +4,6 %, **dans le bruit** (seuil 38 %). `cache` contre
`cmoe` : **−52 %**, réel ; contre `fit` : −54 %, réel. Préremplissage : rien ne se départage.

**Ajout de la ronde de corrections après l'épreuve J1 (lot O, 2026-10-16)** : ces trois
configurations tournaient toutes à `-t 6`. Le nombre de fils change tout : sous mmap, chaque fil en
faute de page est une lecture en vol. Séance `mesures/moteur/O/corrections/journaux/verdicts-base-2026-10-16.json`
(palindrome, même invite, 256 jetons) : `fit -t 6` 0,574, `-t 10` 0,665, `-t 12` 0,836, **`-t 16`
0,884 j/s**, `-ngl 99 --n-cpu-moe 34 --fit off -t 10` 0,640. ~~La meilleure base du 120b est `fit`,
0,568 j/s~~ : la meilleure mesurée est `fit -t 16`, 0,884 j/s (+54 % sur `-t 6`, réel), même texte
45a1f638…

**Octets lus sur le disque pendant la génération** (`disque-phases.csv`, bruts : majorants, le compteur
est global à la machine ; la soustraction du repos est inutilisable ici, le repos ayant valu jusqu'à
440 Mo/s pendant la passe `cmoe-2`) [mes.] :

| Configuration | Go par jeton généré | débit pendant la génération |
|---|---:|---:|
| `cmoe` (passes au calme : 3, 4, 5) | 0,76 – 0,78 (0,91 au début, machine chargée) | **0,42 – 0,44 Go/s** |
| `fit` | 0,68 – 0,83 | 0,40 – 0,43 Go/s |
| `cache` | 0,78 – 0,88 | **0,20 – 0,23 Go/s** |

Ce que ces chiffres disent [calc. sur mes.] :
- **120b est borné par la pagination à la demande, pas par le disque.** Les experts sont projetés
  (mmap) ; chaque expert absent du cache de pages est lu par fautes de page. En `cmoe`, au calme :
  0,77 Go par jeton à 0,435 Go/s = **1,77 s**, pour 1,72 à 1,82 s par jeton mesurées : la lecture
  explique tout le temps. Or le disque lit **2,82 Go/s** en blocs de 16 Mio (étude 01) : les fautes de
  page n'en tirent que **15 %**. Lus à pleine vitesse, ces 0,77 Go prendraient 0,27 s ; avec la lecture
  des 1,909 Go d'experts en RAM par le processeur (0,12 s à 15,6 Go/s), le plafond serait de **2,5 j/s
  en série, 3,7 recouvert**, soit 4,6 à 6,7 fois la base, **sans rien changer au cache**.
- **Le cache de pages de Windows sert environ 52 à 60 % des octets d'experts** (1 − 0,91/1,909 à
  1 − 0,77/1,909 ; minorant, puisque le compteur compte aussi les autres programmes), avec un ensemble
  de travail de 10,5 à 11,5 Go. Sur la génération relevée de la même invite, un cache géré **expert par
  expert** de 10 à 11 Go servirait 74 à 76 % des accès en LRU, 85 à 87 % avec l'optimum
  (`cache-ram-120b.json`) : le système de pages perd 15 à 25 points sur une gestion par expert
  (granularité de 4 Kio, lecture anticipée, pages d'autres données dans l'ensemble de travail ; et le
  chemin de calcul de la trace n'est pas celui de la base, § 5).
- **Le cache d'experts de llama.cpp divise la génération par deux sur 120b.** Il sert 35,5 % des accès
  depuis la VRAM, mais chaque défaut (93 experts, 1,23 Go par jeton : 300 Go copiés par passe) est lu
  dans la projection puis copié vers la carte, et le débit disque pendant la génération tombe de
  0,43 à 0,21 Go/s. Hypothèse, non isolée par un profil : en `cmoe`, six fils de calcul provoquent les
  fautes de page en parallèle (une file d'attente profonde sur le NVMe) ; la copie du cache, elle, lit
  ses experts couche par couche, de façon synchrone (une file de profondeur 1 par fautes de 4 Kio à
  quelques dizaines de Kio). Sur 20b, où le fichier tient en RAM, le même cache ne coûtait rien de mesurable (−11 %, dans le bruit, § 3.1).
- **Le taux de succès réel (35,53 %) est sous celui de la trace relevée** (39,19 %) : même invite, mais
  pas le même chemin de calcul (le traceur demande la sortie de tous les jetons et calcule les experts
  des grands lots sur le processeur) ; le texte produit diffère, donc le routage. Le témoin G5 se juge
  dans la même exécution, où il est exact.
- **Trois configurations, trois textes gloutons**, chacun reproduit à l'identique (cinq fois pour
  `cmoe`, échauffement compris) : le constat de 20b, retrouvé sur 120b.
- **Contre la première exploration** (une passe `cmoe` à 10:45, avant la série) : 0,49 j/s en
  génération, 3,21 en préremplissage, 295 Go lus ; dans la fourchette de la série.

---

## 4. Le traceur du routage

### 4.1 Le chemin choisi, et pourquoi

La consigne laissait deux voies : compiler l'exemple `eval-callback` de llama.cpp avec CUDA 13.1.2, ou
un autre moyen justifié. J'ai pris l'autre : **un programme de 498 lignes écrit ici
(`outils/gptoss-routage/traceur.cpp`), lié aux DLL officielles de b11515**, par l'interface publique de
llama.cpp (en-têtes `include/llama.h`, `ggml/include/ggml*.h` du même commit, licence MIT), rien copié.
Raisons :
- la trace sort du **même moteur, des mêmes binaires** que la base mesurée : les experts relevés sont
  ceux que la base lit ; le témoin G5 (§ 5) le prouve à l'accès près ;
- une seule unité de compilation (MSVC 14.44, quelques secondes) ; le paquet binaire ne livre pas de
  bibliothèque d'importation, je les tire des exports des DLL (`dumpbin /exports` → `.def` → `lib`,
  `construire.bat`, `faire_def.py`) ;
- CUDA 13.1.2 n'a donc pas servi : le calcul est celui des binaires CUDA 12.4 de la base.

Le mécanisme : `llama_context_params.cb_eval` est le rappel que l'ordonnanceur de ggml appelle pour
chaque nœud (ask = vrai : « voulez-vous ce tenseur ? » ; ask = faux : il est calculé, on le lit par
`ggml_backend_tensor_get`). La construction du MoE nomme ses nœuds (`src/llama-graph.cpp`) ; le
traceur lit, pour chaque couche l et chaque micro-lot :
- `ffn_moe_argsort-l` (I32 [E, n]) : les experts triés par score ; ses k premières colonnes sont le
  top-k de llama.cpp (la **trace**) ;
- `ffn_moe_probs-l` (F32 [E, n]) : les scores du routeur ; notre propre top-k sur ces scores est un
  **second chemin** (désaccords comptés : **0** sur 345 336 choix pour 20b, **0** sur 444 276 pour 120b : quatre lectures, l'invite de la base et sa génération) ;
  les poids de mélange de gpt-oss sont le softmax des k scores retenus (porte `SOFTMAX_WEIGHT`), écrits
  dans les fichiers `.poids`.

### 4.2 Trois pièges, trouvés par la mesure

1. **Le nœud attendu n'arrive jamais.** J'avais demandé `ffn_moe_logits_biased-l` : pour la porte
   `SOFTMAX_WEIGHT`, `probs = logits`, et le rappel de nommage renomme le **même** tenseur en
   `ffn_moe_probs-l`. Le premier essai relevait le tri, jamais les scores.
2. **Les vues ont le même préfixe** (`ffn_moe_probs-0 (reshaped)`, forme [1, E, n]) : le deuxième essai
   s'est arrêté sur une forme fausse puis sur une assertion de llama.cpp (refuser un tenseur interrompt
   le calcul). Le nom doit être exactement « préfixe + numéro de couche ».
3. **La dernière couche n'est calculée que pour les jetons dont on demande la sortie** (élagage avant
   le FFN de la dernière couche) : avec la sortie du seul dernier jeton, la couche 23 de 20b relevait 1
   jeton sur 383. Le traceur demande donc la sortie de **tous** les jetons, par lots de 1 024 (le tampon
   des logits vaut lot × 201 088 × 4 octets).

Un quatrième, de coût : sur 120b, les grands lots copient par défaut les experts de l'hôte vers la carte
(`op_offload`) ; par mmap et fautes de page à ~170 Mo/s (mesuré par PDH), un lot de 1 024 jetons prenait
**12 minutes**. Le traceur de 120b calcule les experts des grands lots sur le processeur
(`--sans-op-offload`) : 9,4 min pour 2 378 jetons au lieu de 36. Les décodages jeton par jeton, eux,
passent par le cache d'experts en carte dans les deux cas.

### 4.3 Le corpus : quatre genres de texte réel

`outils/gptoss_corpus.py`, extraits de 11 000 octets au plus, coupés en fin de ligne, empreintes dans
`mesures/localite-gpt-oss/corpus/corpus.json` (calculées sur les fins de ligne LF) :

| Genre | Source | Licence | Jetons (o200k) |
|---|---|---|---:|
| prose-en | wikitext-2 test, à partir de la ligne qui suit l'invite de la base | CC BY-SA 3.0 | 2 378 |
| prose-fr | Hugo, *Les Misérables* I, Gutenberg n° 17489, à partir de « En 1815, M. Charles-François-Bienvenu Myriel » | domaine public | 2 887 |
| dialogue | Wilde, *The Importance of Being Earnest*, Gutenberg n° 844, à partir de « FIRST ACT » | domaine public | 2 862 |
| code | CPython 3.13.12 `Lib/functools.py`, à partir de `__all__` (l'en-tête porte des adresses électroniques, laissées hors du dépôt) | PSF | 2 542 |

Soit **10 669 jetons de lecture** par modèle. Deux modes par genre :
- **lecture** : tout le texte passe dans le modèle, chaque jeton voit le vrai texte qui le précède ;
- **génération** : les 256 premiers jetons servent d'invite, puis 256 jetons gloutons sont produits un à
  un (le régime du décodage). Sans gabarit de conversation, sur une invite coupée en plein texte, ces
  générations sont souvent **dégénérées** (prose-en : une suite de points de suspension ; prose-fr :
  « et l'âme de la vie » répété) : leur localité est gonflée par la répétition. La lecture est le
  résultat principal ; la génération se lit avec cette réserve.
Plus l'invite de la base elle-même, avec 256 jetons gloutons (témoin G5).

Les traces : `mesures/localite-gpt-oss/traces-20b/traces-20b.tar.xz` (2,8 Mo) et
`traces-120b/traces-120b.tar.xz` (4,4 Mo) ; format de l'étude 04 (une ligne par jeton, couches
séparées par « | », experts dans l'ordre du score).

---

## 5. Les témoins

| Témoin | Ce qu'il vérifie | Réponse connue | Résultat | Cassure qui le fait tomber |
|---|---|---|---|---|
| Étude 04, T1 à T4 (`temoins/localite-temoins.json`) | l'instrument par couche, sur routages synthétiques | uniforme r = k/E ; figé r = 1 ; collant r = ρ ; Belady ≥ LRU | **INSTRUMENT VALIDE** | ordre mélangé : T3 tombe (`localite-temoins-casse.json`) |
| Top-k maison | la trace lue est bien le top-k du routeur | 0 désaccord entre le tri de llama.cpp et notre top-k sur ses scores | 0 sur 345 336 (20b) ; 0 sur 444 276 (120b : quatre lectures, l'invite de la base et sa génération) | — (deux chemins indépendants) |
| G1a | le cache global, routage figé | N = (L−1)k → 0 ; N = Lk − 1 → (k−1)/k·(1 − 1/T) ; N = Lk → 1 − 1/T | 0 ; 0,74981 ; 0,99975 : exacts | deux attendus faux de ma première passe l'ont fait tomber (ci-dessous) |
| G1b | épinglage statique calibré, routage uniforme | N/(L·E) à 4 σ | 0,0995 / 0,2487 / 0,3975 pour 0,1016 / 0,25 / 0,3984 | — |
| G2 | le cache global à une couche = le cache par couche de l'étude 04 | égalité exacte | égal (LRU et Belady, trois capacités) | — |
| G3 | Belady ≥ LRU, LFU, sur chaque trace réelle et chaque budget | invariant | aucune violation (l'outil s'arrête sinon) | — |
| G4 | l'instrument voit l'ordre des jetons | ordre mélangé : réutilisation = hasard à popularité réelle | 20b : 0,309 contre 0,310 (−2,5 σ) en lecture ; en ordre : 0,503 (+422 σ). 120b : 0,131 contre 0,131 (+2,1 σ) ; en ordre : 0,312 (+664 σ) ; deux traces seules au-delà de 4 σ (§ 6.2) | c'est la cassure elle-même |
| **G5** | la simulation reproduit le cache réel de llama.cpp | succès publiés par llama.cpp dans la même exécution | **20 373 / 24 576 et 88 443 / 98 304 : identiques à l'accès près** (20b) ; **14 446 / 36 864 : identique à l'accès près** (120b, invite de la base, 39,19 %) | 322 emplacements au lieu de 323 : 20 357 (20b) et 14 425 (120b), tombe |
| Proposition 1 (§ 7) | LRU partagé aux capacités exactes du seuil | 0 à N = (L−1)·k ; au moins r̄·(T−1)/T à N = L·k | tenu sur les 17 traces ; égalité (iii) au succès près | zéro attendu à (L−1)·k + 1 : LRU(93) = 0,0972 sur 20b, tombe |
| Intégrale du compteur disque | `gptoss_disque_phases.py` relit la série du banc | le total publié par le banc, à 1 % | tenu sur les 28 passes (20b et 120b), après correction d'un défaut qu'il a trouvé (premier échantillon sauté : 1,2 %) | série lue comme des octets : 680 Go pour 340, tombe |

**G5 en détail.** Pendant le relevé, llama.cpp tenait son cache de 323 emplacements et publiait son
bilan ; ma réplique de sa règle (`g_lru_llama` : succès touchés dans l'ordre du score, défauts triés par
numéro, emplacement le moins récemment utilisé) rejouée sur la trace de génération de la même exécution
retrouve **exactement** le même nombre de succès, deux fois (invite de la base : 82,90 % ; corpus,
quatre générations enchaînées : 89,97 %), puis une troisième fois sur 120b (invite de la base : 14 446
succès sur 36 864 accès, 39,19 %). Mon LRU générique (`g_lru`, défauts dans l'ordre du score) en
diffère de 5, 4 et 5 succès. La trace, la simulation et le moteur disent la même chose.

**Deux erreurs de ma première passe, dites** (`temoins/temoins-global-passe1-attendu-faux.json`,
`-passe2-…`) :
- ~~Sous routage uniforme, un LRU global vaut N/(L·E).~~ Mesuré : 0,032 contre 0,102 à 10 %. Le flux
  global est cyclique dans les couches ; voir le théorème du § 7.
- ~~Routage figé, N = Lk − 1 : zéro succès.~~ Vrai pour un LRU qui évince à chaque accès, faux pour
  celui de llama.cpp, qui juge les k experts d'une couche avant d'évincer : mesuré (k−1)/k.

**Deux mesures de la fragilité du routage** (pas des témoins de l'instrument, des faits sur le modèle) :
- *Décodage contre relecture.* Les jetons produits un à un sont relus ensuite en un seul lot ; part des
  choix (jeton, couche) identiques [mes.] : 20b 77,7 % (prose-en), 90,7 % (prose-fr), 95,2 % (dialogue),
  95,7 % (code), 92,6 % (invite de la base) ; 120b 89,7 % (prose-en, 8 268 / 9 216), 84,6 % (invite de la base, 7 794 / 9 216). Même modèle, mêmes poids : seule la
  forme du calcul (lot de 1 contre lot de 512, cache KV construit autrement) change, et une fraction des
  choix bascule, puis l'écart se propage.
- *Carte contre processeur* (120b, prose-en, même texte, même moteur : grands lots calculés sur la carte
  par copie des experts, ou sur le processeur) : **81,1 %** des choix identiques, **94,3 %** des experts
  communs, premier écart au 3e jeton, couche 24 ; par couche, de 100 % (couche 0) à 59 % (couche 32),
  décroissant avec la profondeur (`chemins/120b-prose-en-carte-contre-processeur.csv`).
Conséquence pour troncons : **un moteur qui calcule les experts ailleurs que la base routera
autrement** ; la justesse d'un moteur sans perte se juge contre une base du même étage (règle de
l'étude 06, ici étendue au routage), et la justesse d'un prédicteur d'experts a un plancher fixé par ce
bruit, pas par 100 %.

---

## 6. La localité mesurée

Instrument : `outils/gptoss_localite.py` sur les traces de lecture (le résultat principal) et de
génération (avec la réserve du § 4.3). Deux portées :
- **par couche** (l'instrument de l'étude 04, inchangé) : un cache de C experts par couche, C = arrondi
  de f·E ; seuls les C ≥ k ont un sens (20b : 15 à 40 % ; 120b : 5 à 40 %) ;
- **globale** : un seul cache de N = arrondi de f·L·E emplacements pour toutes les couches, le flux des
  accès dans l'ordre du calcul, ce que fait le cache de llama.cpp.
Politiques : LRU ; LFU à compteurs décroissants (demi-vie 8 jetons) ; épinglage statique **calibré**
(les plus fréquents des 10 % premiers jetons, évalué sur le reste : sans biais de sélection) et
**oracle** (les plus fréquents de toute la trace : le meilleur ensemble fixe) ; Belady (l'optimum
hors ligne, borne supérieure de toute politique sans préchargement).

### 6.1 gpt-oss-20b [mes.]

**Réutilisation d'un jeton au suivant** (part des k experts d'un jeton déjà choisis par le jeton
précédent, même couche, moyenne des couches) :

| Trace | jetons | réutilisation r̄ | hasard uniforme k/E | hasard à popularité réelle | écart en σ |
|---|---:|---:|---:|---:|---:|
| prose-en, lecture | 2 378 | 0,513 | 0,125 | 0,401 | +110 |
| prose-fr, lecture | 2 887 | 0,538 | 0,125 | 0,423 | +123 |
| dialogue, lecture | 2 862 | 0,519 | 0,125 | 0,446 | +77 |
| code, lecture | 2 542 | 0,434 | 0,125 | 0,296 | +150 |
| **quatre genres, lecture** | **10 669** | **0,503** | 0,125 | 0,310 | **+422** |
| quatre genres, génération | 1 024 | 0,577 | 0,125 | 0,223 | +266 |

Le « hasard à popularité réelle » est la réutilisation qu'aurait un routage qui tire ses experts
indépendamment d'un jeton à l'autre, avec la fréquence mesurée de chacun : il sépare la **popularité**
(certains experts servent plus que d'autres) de la **récence** (le jeton suivant reprend les experts du
précédent). Les deux existent : la popularité porte la réutilisation de 0,125 à 0,31 ; la récence, de
0,31 à 0,50. Le témoin G4 (ordre mélangé : 0,309) montre que ce second terme tient à l'ordre du texte.

**Par couche** (`20b/couches-gpt-oss-20b.csv`, figure 2) : la réutilisation croît avec la profondeur,
de 0,23 (couche 0) à 0,60-0,66 (couches 10 à 13 et 20 à 23) ; la distance médiane de réutilisation
passe de 4 jetons (couche 0) à 1 (couches 9 à 13, 17, 20 à 23) ; il faut 29 experts sur 32 pour couvrir
95 % des accès de la couche 0, 14 pour la couche 23. Les couches profondes sont à la fois plus
concentrées et plus collantes.

**Succès selon le budget** (quatre genres, lecture ; `20b/courbes-gpt-oss-20b.csv`, figure 1) :

| Budget (part des experts) | 10 % | 15 % | 20 % | 30 % | 40 % |
|---|---:|---:|---:|---:|---:|
| global, LRU | **0,000** | 0,503 | 0,601 | 0,774 | 0,882 |
| global, LFU (demi-vie 8) | 0,470 | 0,592 | 0,684 | 0,817 | 0,902 |
| global, statique calibré | 0,198 | 0,269 | 0,313 | 0,412 | 0,492 |
| global, statique oracle | 0,407 | 0,509 | 0,591 | 0,720 | 0,812 |
| global, **Belady** | **0,605** | 0,733 | **0,814** | **0,906** | **0,955** |
| par couche, LRU (C = 5, 6, 8, 10, 13) | — | 0,563 | 0,624 (C = 6) | 0,795 (C = 10) | 0,872 (C = 13) |
| par couche, Belady | — | 0,636 | 0,720 | 0,881 | 0,933 |

(Les budgets par couche sont C/E : 15 % = 5, 20 % = 6, 25 % = 8, 30 % = 10, 35 % = 11, 40 % = 13 experts.)

Cinq faits :
1. **Le routage a une forte localité.** À 20 % des experts, Belady sert 81 % des accès, LRU 60 % ;
   sans localité, un ensemble fixe en servirait 20 %. Le plafond de l'étude 06 (h = C/E) est donc
   pessimiste d'un facteur 3 à 4 sur la part manquée.
2. **LRU partagé : zéro à 10 %**, exactement, sur toutes les traces (le théorème du § 7). LFU, qui ne
   dépend pas de la seule récence, en sert 47 %.
3. **L'écart à Belady est grand** : 0,60 contre 0,81 à 20 %, 0,77 contre 0,91 à 30 % ; c'est la marge
   d'un prédicteur (étude 04, § 3.3 : le routeur de la couche suivante est calculable une couche à
   l'avance).
4. **Le statique calibré s'effondre quand le genre change.** Calibré sur les 10 % premiers jetons de
   la trace « quatre genres » (ordre alphabétique : du code), il ne sert que 0,198 à 10 % ; dans chaque
   genre pris seul, calibré sur son propre début, il sert de 0,22 (code) à 0,49 (dialogue). Un
   épinglage choisi hors ligne sur un corpus ne vaut que pour ce corpus.
5. **Les genres diffèrent peu sous LRU et Belady** (Belady à 20 % : 0,776 code, 0,817 prose-en, 0,824
   dialogue, 0,834 prose-fr) : le code a la réutilisation la plus basse et la popularité la plus
   faible, mais l'avantage de récence (+150 σ) le plus net.

### 6.2 gpt-oss-120b [mes.]

Traces : prose-en et prose-fr (relevé du 12:09, arrêté ensuite), dialogue et code (relevé de reprise du
15:16) ; 10 669 jetons de lecture, comme 20b ; une seule génération (prose-en, 256 jetons), la
génération de prose-fr ayant été abandonnée (§ 13, délégation 2). Données : `120b/`.

| Trace | jetons | réutilisation r̄ | hasard uniforme k/E | hasard à popularité réelle | écart en σ |
|---|---:|---:|---:|---:|---:|
| prose-en, lecture | 2 378 | 0,317 | 0,031 | 0,209 | +155 |
| prose-fr, lecture | 2 887 | 0,357 | 0,031 | 0,228 | +199 |
| dialogue, lecture | 2 862 | 0,325 | 0,031 | 0,238 | +132 |
| code, lecture | 2 542 | 0,239 | 0,031 | 0,113 | +241 |
| **quatre genres, lecture** | **10 669** | **0,312** | 0,031 | 0,131 | **+664** |
| prose-en, génération | 256 | 0,472 | 0,031 | 0,295 | +74 |

**Dix fois le hasard uniforme.** Avec 128 experts, k/E = 3,1 % ; un jeton reprend en moyenne 31 % des
experts du précédent. La popularité seule en expliquerait 13 % (quatre genres mêlés) ; la récence porte
le reste. Par couche (`120b/couches-gpt-oss-120b.csv`), de **0,139 à la couche 0** (distance médiane
de réutilisation 10 jetons, 102 experts sur 128 pour 95 % des accès) à **0,529 à la couche 35**
(distance médiane 1, 57 experts pour 95 %), avec un creux autour des couches 15 et 30.

**Succès selon le budget** (quatre genres, lecture ; `120b/courbes-gpt-oss-120b.csv`) :

| Budget | 5 % | 7,0 % (VRAM) | 10 % | 15 % | 20 % | 30 % | 40 % |
|---|---:|---:|---:|---:|---:|---:|---:|
| emplacements N | 230 | 323 | 461 | 691 | 922 | 1 382 | 1 843 |
| global, LRU | 0,333 | 0,449 | 0,565 | 0,689 | 0,777 | 0,883 | 0,939 |
| global, LFU | 0,460 | 0,539 | 0,625 | 0,724 | 0,794 | 0,887 | 0,940 |
| global, statique calibré | 0,078 | 0,108 | 0,147 | 0,232 | 0,297 | 0,416 | 0,509 |
| global, statique oracle | 0,358 | 0,428 | 0,509 | 0,610 | 0,684 | 0,790 | 0,864 |
| global, **Belady** | **0,632** | **0,706** | **0,780** | **0,856** | **0,901** | **0,951** | **0,976** |
| par couche, LRU (C = 6, —, 13, 19, 26, 38, 51) | 0,384 | — | 0,586 | 0,690 | 0,775 | 0,870 | 0,928 |
| par couche, Belady | 0,508 | — | 0,744 | 0,829 | 0,886 | 0,939 | 0,968 |

Ce que 120b ajoute à 20b :
1. **Partager le budget entre couches ne profite qu'à une bonne politique.** Belady partagé bat
   Belady par couche à tout budget (0,632 contre 0,508 à 5 % ; 0,780 contre 0,744 à 10 %) : un budget
   commun va aux couches qui en ont besoin. LRU partagé, lui, reste **sous** LRU par couche jusqu'à
   15 % (0,333 contre 0,384 à 5 % ; 0,565 contre 0,586 à 10 % ; 0,689 contre 0,690 à 15 %) et ne le
   dépasse qu'ensuite (0,883 contre 0,870 à 30 %) : même au-dessus du seuil du § 7, le flux cyclique
   entre couches lui coûte. (Budgets comparables : 6 × 36 = 216 emplacements par couche contre 230.)
2. **À la capacité réelle du cache de llama.cpp (323 emplacements, 7,0 %)**, LRU sert 0,449 des accès
   de lecture ; Belady 0,706. Le cache de la base est donc à 26 points de l'optimum.
3. **L'épinglage calibré s'effondre encore plus** : 0,147 à 10 % sur les quatre genres, contre 0,37
   (code) à 0,64 (dialogue) dans chaque genre ; avec 128 experts, les populaires d'un genre ne sont
   pas ceux d'un autre.
4. **Le code est le genre le moins local** (r̄ = 0,239 ; Belady à 20 % : 0,862 contre 0,90 à 0,92
   pour la prose et le dialogue), comme sur 20b.
5. **La génération est plus locale** (0,472) que la lecture, avec la réserve du § 4.3 (une seule
   génération, en partie dégénérée).

**Témoins sur 120b.** Top-k maison : **0 désaccord sur 384 084 choix** (quatre lectures, journaux
`traces-120b/journal-traceur-120b.log`). G3 (Belady ≥ LRU, LFU) : aucune violation. G4, ordre mélangé
(`120b/analyse-casse.log`) : quatre genres 0,131 pour 0,131 attendu (+2,1 σ) ; prose-en +1,0 σ,
prose-fr +1,0 σ, code +1,6 σ ; **dialogue −4,2 σ et génération −5,0 σ**, un peu au-delà des 4 σ
déclarés : l'écart-type suppose des tirages indépendants, alors que les k experts d'un jeton sont
distincts (tirage sans remise), ce qui abaisse un peu la réutilisation au hasard ; hypothèse, non
démontrée. En ordre, l'écart est de +664 σ : l'instrument voit l'ordre. G5 : § 5.

---

## 7. Un théorème : le LRU partagé entre couches, et son seuil

**Cadre.** Un cache de N emplacements sert le flux des accès d'un MoE à L couches et k experts
distincts par couche, dans l'ordre du calcul : jeton t, couche 0, 1, …, L−1, puis jeton t+1. Un
« groupe » = les k accès d'un (jeton, couche). Règle de llama.cpp (et de mes simulateurs) : les accès
d'un groupe sont jugés contre le contenu **avant** toute éviction ; les k experts entrent ensemble.
Le rang de récence d'une clé est sa place dans l'ordre des derniers usages (1 = la plus récente).

**Proposition 1.** *Pour tout routage, (i) si N ≤ (L−1)·k, le LRU partagé n'a aucun succès ;
(ii) si N ≥ L·k, chaque expert réutilisé d'un jeton au suivant est un succès, donc le taux de succès
du LRU partagé est au moins la réutilisation adjacente moyenne r̄ (sur les jetons t ≥ 1) ;
(iii) si N = L·k exactement, il vaut r̄ exactement (sur les jetons t ≥ 1) : un succès, et seulement
lui, est une réutilisation adjacente.*

*Démonstration.* Soit la clé (l, e) demandée au jeton t+1. (i) Son dernier usage date au plus tard du
jeton t, à la couche l. Entre ce dernier usage et le jugement du groupe (t+1, l), le flux a servi au
moins les groupes (t, l+1), …, (t, L−1), (t+1, 0), …, (t+1, l−1) : L−1 groupes, chacun de k clés
distinctes, toutes d'autres couches que l, donc (L−1)·k clés distinctes de (l, e), toutes plus récentes.
Son rang est au moins (L−1)·k + 1 > N : elle n'est plus dans le cache (un LRU de N emplacements tient
exactement les N clés de rang ≤ N, l'éviction après le groupe ne change pas cet ensemble au moment du
jugement suivant). Aucun succès. (ii) Si (l, e) a servi au jeton t, les clés plus récentes qu'elle
au moment du jugement sont au plus les (L−1)·k clés ci-dessus et au plus k − 1 clés de son propre
groupe (t, l) : rang ≤ L·k ≤ N, elle est dans le cache. Chaque réutilisation adjacente est donc un
succès : sur les accès des jetons t ≥ 1, h ≥ r̄. (iii) Si (l, e) n'a pas servi au jeton t, son dernier
usage date au plus tard du jeton t − 1 ; entre lui et le jugement de (t+1, l), le flux a servi tout le
jeton t (L groupes, L·k clés distinctes, toutes différentes de (l, e) : celles de la couche l au jeton t
ne la contiennent pas, celles des autres couches ont une autre couche). Son rang est au moins
L·k + 1 > N : défaut. Avec (ii), à N = L·k, succès ⟺ réutilisation adjacente. ∎

Rapportée à tous les accès (le jeton 0 n'a que des défauts), la valeur exacte de (iii) est
r̄ · (T − 1)/T.

**Corollaire 2 (budget en fraction des experts).** Avec f = N/(L·E), le LRU partagé est nul pour
f ≤ (L−1)/L · k/E, et vaut au moins r̄ pour f ≥ k/E. gpt-oss-20b : nul jusqu'à **11,98 %**, au moins
r̄ dès 12,5 % ; gpt-oss-120b : nul jusqu'à **3,04 %**, au moins r̄ dès 3,125 %.

**Vérification sur les traces réelles** [mes.] : 20b, lecture, LRU partagé = **0,000** exactement à 5 %
et 10 % (N = 38 et 77 ≤ 92 = (L−1)k) ; à 15 % (N = 115 ≥ 96 = Lk), **0,503** pour r̄ = 0,503 : la borne
(ii) est atteinte presque à l'égalité.

**Témoin aux capacités exactes du seuil** (ajouté à `outils/gptoss_localite.py`, déclaré avant le
calcul ; l'outil s'arrête s'il tombe) : LRU partagé à N = (L−1)·k doit valoir 0 exactement, et à
N = L·k au moins r̄·(T−1)/T. Mesuré, à N = L·k, l'**égalité (iii) au succès près sur les 17 traces des
deux modèles** (écart inférieur à 10⁻¹⁰ accès, l'arrondi de deux ordres de sommation ; égalité au bit
sur 11 traces). Exemple, 20b dialogue, lecture : N = 92 → 0 ; N = 95 → 0,3592 ; N = 96 → 0,518566 = r̄·(T−1)/T ; N = 97 →
0,518566 aussi (aucun succès de plus ; sur les 17 traces, seule la génération dégénérée de prose-en sur
20b, et la trace des quatre générations qui la contient, en gagnent 4 à L·k + 1) : un expert de la couche l absent du jeton t a encore devant lui, à son
jugement, tout le jeton t et les clés des autres couches servies depuis son dernier usage hors du
jeton t ; le plateau s'étend donc bien au-delà de L·k + 1 (le lot O du moteur l'a relevé de 96 à 120
emplacements sur 20b, `mesures/moteur/O/`, commit `b75dcc7`). **Cassure** (`--casser-seuil` : le
zéro attendu à (L−1)·k + 1) : LRU(93) = 0,0972, le témoin tombe (code 1).
120b, quatre genres en lecture (T = 10 669) : N = 140 = (L−1)·k → **0** ; N = 143 → 0,2073 ;
N = 144 = L·k → **0,311491 = r̄·(T−1)/T** (au succès près) ; N = 145 → la même valeur. Sur chaque genre
et sur la génération, mêmes égalités (`120b/analyse.log`, `120b/localite-gpt-oss-120b.json`, champs
`seuil_lru_partage` et `seuil_borne_ii`).

**Deux chemins indépendants.** Le lot O du moteur a démontré le point (i) de son côté, le même jour
(lemme 3 de `moteur/O-pour-le-memoire.md`, « la falaise », avec son témoin unitaire et la courbe
dense `mesures/moteur/O/csv/falaise-20b-dense.csv`). Ce que la Proposition 1 ajoute : (ii) et (iii)
donnent **la hauteur exacte du plateau** que le lot O a mesuré au-dessus de la falaise. Son chiffre,
50,26 % à N = 96 sur les quatre lectures de 20b, est exactement r̄·(T−1)/T = 0,5026 (§ 6.1, et champ
`seuil_borne_ii` de `20b/localite-gpt-oss-20b.json`) : le plateau est la réutilisation adjacente, et
rien d'autre.

**Ce que cela dit.** Un cache partagé géré par LRU (le cache de llama.cpp, et la plupart des
propositions publiées) gaspille tout budget inférieur à un jeton de travail (L·k experts) ; entre
(L−1)k et Lk il ne sert que la récence immédiate. Sous ce seuil, LFU (0,47 à 10 % sur 20b), un
épinglage statique (0,41) ou un partage par couche font mieux qu'un LRU nul. Le seuil ne dépend que
de (L, k), pas du texte : c'est un théorème d'ordre, pas de statistique. Pour 120b et ses 323
emplacements de llama.cpp, N = 323 > L·k = 144 : le cache de la base est au-dessus du seuil ; et
pourtant, sur sa propre génération, un ensemble fixe le bat (0,500 contre 0,392, § 9) : être au-dessus
du seuil ne suffit pas, la récence seule reste une mauvaise règle pour ce flux.

---

## 8. Le plafond de jetons/s qui en découle

### 8.1 Les formules [calc.]

Pour un jeton : A octets toujours lus (résidents en VRAM, lus à B_v), R = k·L·e octets routés, dont
une part h servie par le cache en VRAM et 1 − h par l'étage suivant. Débits **mesurés** (étude 01) :
B_v = 251,3 Go/s (lecture de VRAM), B_p = 12,2 Go/s (RAM → carte), B_d = 2,82 Go/s (disque, 16 Mio,
QD 1, BitLocker). Le calcul est supposé gratuit (une carte calcule un expert présent à la vitesse de sa
VRAM ; étude 01 : la GEMV f16 atteint 98 % de la VRAM).

- Scénario **RAM** (le fichier tient en RAM : 20b) :
  t_série = (A + hR)/B_v + (1 − h)R/B_p ;  t_recouvert = max[(A + hR)/B_v, (1 − h)R/B_p].
- Scénario **disque** (les défauts viennent du disque, puis de la PCIe) :
  t_série = (A + hR)/B_v + (1 − h)R(1/B_d + 1/B_p) ;  t_recouvert = max[(A + hR)/B_v, (1 − h)R/B_p, (1 − h)R/B_d].
- Scénario **deux étages** (120b : VRAM de capacité f_v, RAM jusqu'à f, disque). LRU, Belady et
  l'épinglage statique sont des **algorithmes à pile** (Mattson et al., 1970 : le contenu à la capacité
  C est inclus dans celui à C' > C, à règle de départage fixée), donc h_v = h(f_v),
  h_r = h(f) − h(f_v), défauts 1 − h(f) :
  t_série = (A + h_v R)/B_v + h_r R/B_p + (1 − h)R(1/B_d + 1/B_p) ;
  t_recouvert = max[(A + h_v R)/B_v, (1 − h_v)R/B_p, (1 − h)R/B_d].
  Jetons/s = 1/t.

Calcul posé, un point : 20b, LRU partagé à 40 % (h = 0,882, lecture), scénario RAM.
(A + hR)/B_v = (1,302 + 0,882 × 1,272) / 251,3 = 2,424 / 251,3 = 9,65 ms ;
(1 − h)R/B_p = 0,118 × 1,272 / 12,2 = 0,1501 / 12,2 = 12,30 ms ;
série : 21,95 ms → **45,6 j/s** ; recouvert : 12,30 ms → **81,3 j/s** (`plafonds-gpt-oss-20b.csv`,
45,47 et 80,98 : l'écart vient des arrondis de h et des octets dans ce calcul à la main).

### 8.2 gpt-oss-20b [calc., succès mesurés]

Succès du cache global sur les quatre genres en lecture (`20b/plafonds-gpt-oss-20b.csv`) ; A = 1,302 Go,
R = 1,272 Go par jeton. Scénario RAM : le fichier de 12,1 Go tient dans les 16 Go.

| Budget | politique | h | RAM, série | RAM, recouvert | disque, série |
|---|---|---:|---:|---:|---:|
| 0 (rien en VRAM) | — | 0 | 9,13 | 9,59 | 1,78 |
| 10 % | LRU | 0,000 | 9,13 | 9,59 | 1,78 |
| 10 % | LFU | 0,470 | 15,9 | 18,1 | 3,31 |
| 10 % | Belady | 0,605 | 20,2 | 24,3 | 4,39 |
| 20 % | LRU | 0,601 | 20,1 | 24,0 | 4,35 |
| 20 % | Belady | 0,814 | 34,9 | 51,6 | 8,89 |
| 30 % | LRU | 0,774 | 30,6 | 42,4 | 7,43 |
| 30 % | Belady | 0,906 | 51,2 | 102 | 16,2 |
| 40 % | LRU | 0,882 | 45,5 | 81,0 | 13,3 |
| 40 % | Belady | 0,955 | 68,2 | 99,8 | 28,8 |
| 42,1 % (cache de la base) | LRU de llama.cpp, mesuré | 0,846 | 39,2 | 62,2 | 10,5 |

**La base contre son plafond.** Le cache de llama.cpp (42,1 % des experts) sert 84,6 % des accès de
génération : son plafond en série est de 39 j/s ; il en fait 10,2 à 11,2 (27 %), moins que `fit`
(18,9) qui ne met que 10 couches d'experts en carte. Le cache est donc bon, sa mécanique ne l'est pas
(§ 3.1). Le plafond « sans cache » de la PCIe (9,1 j/s) est sous `cmoe` mesuré (11,4) parce que `cmoe`
calcule les experts sur le processeur, sans rien copier : la RAM du processeur (15,6 Go/s) est plus
rapide que la PCIe (12,2 Go/s). Un moteur qui copie les experts manqués vers la carte doit donc
servir **au moins 22 % des accès depuis la VRAM** pour seulement égaler le processeur [calc.] :
1/11,4 = 87,7 ms = A/B_v + h·R/B_v + (1 − h)·R/B_p = 5,18 + 5,06·h + 104,3·(1 − h) ms, d'où h = 0,22.

### 8.3 gpt-oss-120b [calc., succès mesurés]

Succès du cache global sur les quatre genres en lecture (`120b/plafonds-gpt-oss-120b.csv`) ; A = 1,686 Go,
R = 1,909 Go par jeton. Scénario **deux étages** : la VRAM tient 7,0 % des experts (4,28 Go, la
capacité du cache de la base) ; la RAM, le reste du budget ; le disque, les défauts. Budgets
atteignables sur cette machine : ≈ 23 % (VRAM + ~10 Go de RAM libre ; délégation 4). Au-dessus, c'est
une machine à plus de RAM.

| Budget | politique | h (budget) | h_v (VRAM, 7,0 %) | deux étages, série | deux étages, recouvert | étage qui borne (recouvert) |
|---|---|---:|---:|---:|---:|---|
| 0 | — | 0 | 0 | 1,19 (disque seul) | 1,48 | disque |
| 10 % | LRU | 0,565 | 0,449 | 2,56 | 3,40 | disque |
| 10 % | Belady | 0,780 | 0,706 | 4,83 | 6,71 | disque |
| 15 % | LRU | 0,689 | 0,449 | 3,26 | 4,75 | disque |
| 20 % | LRU | 0,777 | 0,449 | 4,04 | 6,61 | disque |
| 20 % | Belady | 0,901 | 0,706 | 8,01 | 15,0 | disque |
| 25 % | LRU | 0,839 | 0,449 | 4,87 | 9,16 | disque |
| 30 % | LRU | 0,883 | 0,449 | 5,70 | 11,6 | **PCIe** |
| 40 % | LRU | 0,939 | 0,449 | 7,26 | 11,6 | **PCIe** |
| 40 % | Belady | 0,976 | 0,706 | 13,4 | 21,7 | **PCIe** |

Calcul posé, un point [calc.] : LRU à 20 %, recouvert. VRAM : (A + h_v·R)/B_v = (1,686 + 0,449 ×
1,909)/251,3 = 2,543/251,3 = 10,1 ms ; PCIe : (1 − h_v)·R/B_p = 0,551 × 1,909/12,2 = 86,2 ms ; disque :
(1 − h)·R/B_d = 0,223 × 1,909/2,82 = 151 ms. Le maximum, 151 ms, donne **6,6 j/s**.

En génération (une seule trace de 256 jetons, plus locale), LRU à 20 % : h = 0,852, h_v = 0,736,
6,5 j/s en série, 10,0 recouvert ; Belady : 10,3 et 17,0.

**La base contre ses plafonds** (figure 6 de `figures-gpt-oss.pdf`). `cmoe` (0,54 j/s) est sous le
plafond « sans cache » du disque à 2,82 Go/s (1,19 j/s en série) : c'est la pagination à la demande
(0,43 Go/s, § 3.2) qui la borne, pas le disque. `cache` (0,26 j/s, h_v = 0,355 mesuré) est à **un
dixième** de son plafond à deux étages calculé avec le h_v mesuré et le cache de pages de ~60 % [calc.] :
(A + h_v·R)/B_v + (0,60 − h_v)·R/B_p + 0,40·R·(1/B_d + 1/B_p) = 9,4 + 38,3 + 333 ms = 381 ms, soit
2,6 j/s.

**Ce que disent ces plafonds.** (i) Au budget atteignable (~20 %), le **disque** borne tout : 151 ms
sur 86 ms de PCIe et 10 ms de VRAM. (ii) Dès 30 %, la **PCIe** prend le relais et plafonne LRU à
11,6 j/s, quel que soit le budget de RAM : le seul levier y est h_v, ou moins d'octets par expert sur
la PCIe. (iii) La VRAM ne borne jamais : 10 ms par jeton, soit ~100 j/s si rien d'autre ne coûtait.
(iv) Tout facteur de compression c des experts **en transit** (stockés compressés sur le disque et en
RAM, décompressés sur la carte) divise les termes disque et PCIe par c [calc.] : à 20 % LRU, c = 2
donne max(10,1 ; 43,1 ; 75,5) ms = **13,2 j/s** au lieu de 6,6, tant que la décompression sur la
carte suit le débit de la PCIe. C'est exactement le levier de troncons.

---

## 9. Ce que cela change pour troncons

1. **L'hypothèse uniforme est remplacée par des succès mesurés.** Le plafond de l'étude 06 (h = C/E)
   sous-estime le cache d'un facteur 3 à 4 sur la part servie (20b, 20 % : Belady 0,81, LRU 0,60
   contre 0,20 ; 120b, 10 % : Belady 0,78, LRU 0,57 contre 0,10). Les études 04 et 06 peuvent
   reprendre leurs plafonds avec les colonnes `succes` de `courbes-*.csv`.
2. **Un cache partagé ne se gère pas par LRU pur sous L·k emplacements** (Proposition 1, démontrée et
   vérifiée à l'égalité sur 17 traces). Le moteur de troncons doit soit garder N > L·k (20b : 96 ; 120b :
   144 emplacements, soit 1,27 et 1,91 Go), soit employer une politique qui n'est pas de pure récence.
3. **Sur la génération réelle de 120b, au budget de la base (323 emplacements, 7 %), un ensemble fixe
   bat le LRU de llama.cpp** (0,500 contre 0,392) et Belady atteint 0,685 (`cache-base-contre-optimum.json`).
   Il y a 29 points de succès en VRAM à prendre par une meilleure politique ou un prédicteur, avant
   tout gain de format.
4. **Ce qui borne 120b sur cette machine est le disque, puis la PCIe ; jamais la VRAM** (§ 8.3). Au
   budget atteignable (~20 %), 151 ms de disque, 86 ms de PCIe, 10 ms de VRAM par jeton. D'où la
   conclusion la plus directe pour la mission : **chaque facteur de compression des experts en transit
   multiplie le plafond d'autant**, tant que la décompression sur la carte tient le débit de la PCIe
   (à 20 % LRU : ×2 de compression → 6,6 à 13,2 j/s). La décompression « à l'instant exact du nœud »
   de Stone est le levier chiffré.
5. **Sur 120b, le premier levier n'est même pas le cache : c'est la façon de lire.** La base lit
   ses experts par fautes de page à 0,43 Go/s, 15 % des 2,82 Go/s que le disque donne en blocs de
   16 Mio (§ 3.2). Un chargeur qui lit les experts manquants en grands blocs, en parallèle, au débit du
   disque, gagnerait **×4,6 à ×6,7** sur la base sans changer de politique ; c'est la première
   brique du moteur (lot E : fichiers sans tampon et ports de complétion ; lot F : le format `.trc`).
6. **Le cache de pages du système perd 15 à 25 points sur une gestion par expert** (52 à 60 %
   servis pour 74 à 76 % en LRU par expert, 85 à 87 % avec l'optimum, à 10-11 Go) : garder les
   experts en RAM soi-même, à la granularité de l'expert, vaut mieux que de s'en remettre au système.
7. **Un cache en VRAM mal nourri ralentit** : celui de llama.cpp divise par deux la génération
   de 120b (−52 %, réel), parce que ses défauts passent par des fautes de page synchrones (hypothèse).
   Un cache n'aide que si ses défauts arrivent au moins aussi vite que ce qu'il remplace.
8. **Un épinglage choisi hors ligne ne voyage pas d'un genre à l'autre** (statique calibré : 0,147
   sur quatre genres contre 0,37 à 0,64 par genre sur 120b) : la politique doit apprendre en ligne.
9. **Les couches diffèrent** (réutilisation 0,14 à 0,53 sur 120b, 0,23 à 0,66 sur 20b) : un budget
   partagé bien géré (Belady partagé > Belady par couche à tout budget) les sert mieux qu'un découpage
   fixe ; un découpage par couche protège mieux un LRU.
10. **La mécanique coûte plus que les octets** : le cache de llama.cpp sur 20b atteint 27 % de son
   plafond (§ 3.1), la synchronisation par couche et les copies non recouvertes en sont les suspects ;
   c'est le terrain du lot E (copies recouvertes).
11. **La justesse se juge contre une base du même chemin de calcul** : le routage bascule entre carte
   et processeur (81,1 % de choix identiques sur 120b) et entre décodage et relecture (77,7 à 95,7 %
   sur 20b ; 84,6 et 89,7 % sur 120b). Un prédicteur d'experts a un plafond fixé par ce bruit.

---

## 10. Ce qui reste

- **Refaire la base et les traces sur le disque D: non chiffré** (coût de BitLocker) et **au repos**
  (sans autres agents), pour des jetons/s qui ne soient plus des minorants bruités.
- **Traces en conversation** (gabarit harmony de gpt-oss, raisonnement), et générations longues non
  dégénérées sur les quatre genres de 120b (seule prose-en et l'invite de la base ont une génération).
- **Mesurer un prédicteur réel** (le routeur de la couche l+1 appliqué à l'état de la couche l, étude
  04, § 3.3) contre Belady sur ces traces : combien des 29 points de 120b il récupère.
- **Profiler le cache de llama.cpp** (où vont les 73 % de son plafond sur 20b) : synchronisations par
  couche, copies, attente.
- **Élucider la mémoire privée du traceur sur 120b** (8,6 Go).
- **Isoler le coût du chemin de calcul sur la localité** : relever les quatre lectures de 120b tout sur
  la carte (op_offload) quand la machine sera au calme, et comparer les courbes.
- **Isoler la cause du ralentissement du cache de llama.cpp sur 120b.** L'outil est prêt et commité,
  seuil déclaré : `outils/gptoss_file_disque.py` échantillonne la file moyenne en lecture et la taille
  des lectures pendant des passes `cmoe` et `cache` ; l'hypothèse tient si la file de `cmoe` vaut au
  moins le double de celle de `cache`, tombe sous 1,5. Non lancé le 2026-10-15 : à la fin de la série,
  un autre agent a pris la carte et le disque (llama-perplexity du lot R, 280 Mo/s de lectures) ; la
  mesure se fera au calme (ABBA cmoe, cache, cache, cmoe, `--n 64`, environ 30 min).
- **Mesurer un chargeur à lectures directes** (grands blocs, file profonde, sans projection) sur les
  mêmes traces : c'est le gain ×4,6 à ×6,7 du § 3.2, à démontrer.

---

## 11. Ce qui pourrait être faux

1. **La machine n'était pas au repos.** D'autres agents lisaient les mêmes fichiers, calculaient et
   occupaient la RAM pendant une grande partie de ces mesures (le second palindrome de 120b, lui, a
   tourné sans autre programme lourd ; llama-perplexity à 10 Go privés, banc_k sur 120b, un
   juge, trc-codeur ; relevés dans la colonne `concurrents` de chaque passe et dans la note de
   reprise). Les jetons/s de la base sont donc des **minorants bruités** ; les décisions du § 3 ne
   portent que sur des écarts qui dépassent deux fois le bruit mesuré. Les **traces**, elles, sont
   déterministes à chemin de calcul fixé : la contention n'en change que la durée.
2. **La localité vient de 10 669 jetons de quatre textes**, sans gabarit de conversation. Un usage en
   conversation (gabarit harmony de gpt-oss, raisonnement, outils) peut avoir une autre localité ; les
   générations relevées ici sont souvent dégénérées et gonflent la récence.
3. **Le routage dépend du chemin de calcul** (§ 5 : 81,1 % des choix identiques entre carte et
   processeur sur 120b). Une trace relevée avec un chemin vaut pour ce chemin ; un moteur qui calcule
   autrement aura un routage voisin, pas identique. Sur 120b, la lecture de prose-fr a suivi une
   génération qui avait rempli le cache d'experts, que les grands lots lisent aussi (« large batches :
   experts copied from the cache », journal de 20b) : une partie de ses experts a été calculée sur la
   carte, les autres sur le processeur ; prose-en, dialogue et code ont été lus cache vide, tout sur le
   processeur.
4. **Les plafonds supposent le calcul gratuit** et des débits mesurés au calme (étude 01) : ce sont des
   bornes, pas des prévisions. Le scénario « recouvert » suppose un recouvrement parfait des étages.
5. **Belady est un oracle** : il connaît l'avenir. L'écart LRU–Belady est la marge d'un prédicteur
   parfait, pas celle d'un prédicteur réel.
6. **Les octets d'un expert** (13,254 Mo = 12,64 Mio, le même nombre que les emplacements du cache de
   llama.cpp) viennent de l'en-tête GGUF des fichiers MXFP4 ; un format compressé (troncons) changera
   R et donc les plafonds, dans le rapport des tailles.
7. **La mémoire privée du traceur sur 120b (8,6 Go) n'est pas élucidée** : ni le cache d'experts
   (petits tableaux d'hôte, lu dans `src/llama-moe-cache.cpp`), ni le tampon des logits (824 Mo) ne
   l'expliquent. Elle a aggravé la pagination ; elle ne change pas le routage relevé.
8. **BitLocker** : tout est sur C: chiffré ; les débits disque et les durées incluent son coût, qui
   sera isolé par la reprise sur un disque D: non chiffré.
9. **Les octets disque de la base sont bruts** (majorants : le compteur est global) ; la part servie par
   le cache de pages (52 à 60 %) est donc un minorant, et l'écart au LRU par expert (15 à 25 points)
   un majorant. Cette comparaison mêle en outre deux chemins de calcul (routage de la trace contre
   routage de la base) et deux granularités (pages de 4 Kio contre experts de 13,25 Mo).
10. **L'explication du ralentissement du cache sur 120b (fautes de page synchrones) est une
   hypothèse** : ni la profondeur de file ni la taille des lectures n'ont été relevées.
11. **L'abscisse de `fit` sur la figure des plafonds** compte les couches entières mises en carte par
   `llama-fit-params` (10 sur 24, 2 sur 36), pas la couche partielle qui suit.
12. **G4 sur 120b** : deux traces mélangées (dialogue, génération) s'écartent du hasard à popularité
   réelle de 4,2 et 5,0 σ, au-delà des 4 σ déclarés ; l'hypothèse (tirage sans remise des k experts)
   n'est pas démontrée. La trace des quatre genres, elle, tient (+2,1 σ).

---

## 12. Recettes (techniques essayées)

Chaque technique essayée, avec ce qu'elle a donné et pourquoi :

| Technique | Résultat | Raison |
|---|---|---|
| Relever le routage par le rappel d'évaluation (`cb_eval`) sur l'API publique des DLL officielles, au lieu de compiler `eval-callback` | **marche** (0 désaccord tri/top-k sur 345 336 choix pour 20b) | même moteur, mêmes binaires que la base ; G5 exact |
| Demander le nœud `ffn_moe_logits_biased-l` | **échoue** (jamais servi) | renommé `ffn_moe_probs-l` pour la porte `SOFTMAX_WEIGHT` |
| Accepter les tenseurs par préfixe de nom | **échoue** (forme fausse puis assertion) | les vues « (reshaped) » ont le même préfixe ; refuser un tenseur interrompt le calcul |
| Ne demander la sortie que du dernier jeton | **échoue** (couche 23 : 1 jeton relevé sur 383) | élagage avant le FFN de la dernière couche ; demander la sortie de tous les jetons, par lots de 1 024 |
| Lecture de 120b avec les experts des grands lots copiés vers la carte (`op_offload`, défaut) | **échoue en pratique** (12 min par lot de 1 024 jetons) | 61 Go par lot par fautes de page à ~170 Mo/s ; `--sans-op-offload` : 9,4 min pour 2 378 jetons |
| `-lv 3` pour voir le bilan du cache d'experts | **échoue** (rien) | le bilan est au niveau 4 : `-lv 4` |
| Compteur disque PDH par son nom anglais (`PdhAddEnglishCounterW`) | **marche** | `typeperf` et `Get-Counter` refusent les noms anglais sur ce Windows en français |
| Laisser un long relevé de 120b sous la pression mémoire d'autres programmes | **échoue** (2 h 25 dans une génération de 9 min) | 170 à 290 Mo libres, pagination 200 à 370 Mo/s ; arrêter, relancer en lecture seule |
| Retrouver la sortie console d'un agent mort dans les fichiers de tâche de la session | **marche** | le tube de sortie du traceur écrivait dans un fichier qui a survécu |
| Écrire un CSV avec les colonnes de la première ligne | **échoue** sur 120b | le scénario « deux étages » n'existe qu'au-dessus de la capacité de la VRAM ; union ordonnée des colonnes |
| Vérifier la Proposition 1 aux capacités exactes du seuil, avec une cassure à un emplacement près | **marche** (zéro exact, borne atteinte à l'égalité, cassure qui tombe) | un témoin d'ordre n'a pas de bruit : il tombe ou il tient |
| Calibrer un épinglage statique sur le début d'un corpus de plusieurs genres | **échoue** (0,198 contre 0,22 à 0,49 par genre, 20b à 10 %) | le genre change, l'ensemble des experts populaires aussi |
| Prendre pour attendu « LRU global uniforme = N/(L·E) » | **faux** (attendu, pas le code) | flux cyclique entre couches ; d'où le théorème du § 7 |
| Cache d'experts de llama.cpp (`--moe-cache-mib 4096`) sur 120b, fichier quatre fois plus gros que la RAM | **échoue** (−52 % en génération, réel) | ses défauts passent par des fautes de page synchrones (hypothèse) ; sur 20b, fichier en RAM, il ne coûte rien de mesurable |
| Soustraire 10 s de repos au compteur disque global sur une machine partagée | **échoue** (octets négatifs) | le repos a valu jusqu'à 440 Mo/s ; publier le brut par phase et le repos à côté |
| Intégrer la série PDH en sautant le premier échantillon | **échoue** (1,2 % manquant, trouvé par le témoin) | le banc compte l'intervalle de 0 au premier échantillon |
| Faire les calculs lourds (analyses, figures) pendant la passe d'échauffement jetée | **marche** | aucune passe retenue n'est perturbée |
| Vérifier des références classiques par l'API Crossref, User-Agent neutre | **marche** | métadonnées primaires sans agrégateur |
| Passer du code LaTeX par un heredoc Python dans Bash | **échoue** (échappements perdus) | écrire par l'outil d'édition, morceau par morceau |

---

## 13. Délégations

Aucune question n'a été posée à Stone ; chaque choix ouvert a reçu une réponse par délégation, d'après
ses mots (« gratuit », « au top du top ») :
1. **Le traceur par l'API publique des DLL officielles plutôt que l'exemple `eval-callback` compilé
   avec CUDA 13.1.2.** Réponse par délégation du 2026-10-15, réversible : la trace doit venir du même
   moteur que la base qu'elle explique ; G5 le prouve à l'accès près.
2. **L'arrêt du relevé enlisé de 120b et l'abandon de la génération de prose-fr.** Réponse par
   délégation du 2026-10-15, réversible : 2 h 25 sans fin prévisible sous la pression mémoire d'autres
   agents ; la lecture (résultat principal) de dialogue et de code valait plus qu'une génération
   dégénérée de plus.
3. **La capacité de VRAM du scénario à deux étages : 4,28 Go**, soit les 323 emplacements du cache
   d'experts de llama.cpp de 4 096 Mio (7,0 % des experts de 120b). Réponse par délégation du
   2026-10-15, réversible : c'est la capacité que la base mesure, sur cette carte, avec l'affichage.
4. **Les budgets atteignables sur cette machine pour 120b** : VRAM 4,28 Go + RAM libre ~10 Go
   (15,6 Go utilisables moins le système, les applications de Stone et les tampons du moteur) ≈ 23 %
   des experts ; au-delà, les plafonds sont ceux d'une machine à plus de RAM. Réponse par délégation
   du 2026-10-15, réversible : chiffre estimé, pas mesuré au repos (la machine n'a pas été au repos).
5. **La série de 120b en deux palindromes complets (13 passes, 3 h 11)**, comme celle de 20b, plutôt
   qu'un seul. Réponse par délégation du 2026-10-15, réversible : le protocole de l'étude 06 et la
   comparaison avec 20b l'exigent ; la carte était libre.
6. **Les octets disque bruts par phase plutôt que la différence au repos.** Réponse par délégation du
   2026-10-15, réversible : un repos de 10 s à 440 Mo/s rendait la différence négative ; le brut est un
   majorant honnête, le repos est publié à côté.

---

## 14. Fichiers

- Livrable : `mesures/gpt-oss.md` ; pour le mémoire : `mesures/gpt-oss-pour-le-memoire.md` ; note de
  reprise : `mesures/REPRISE-gpt-oss.md`.
- Base : `mesures/base-gpt-oss/20b/` et `120b/` (par passe : `.json`, `.stderr.log`, `.sortie.txt` ;
  `passes.csv`, `resume.csv`, `journal.log`, `disque-phases.csv` ; pour 120b, `console.log`).
- Localité : `mesures/localite-gpt-oss/` :
  - `corpus/` (quatre textes et `corpus.json`), `octets-gpt-oss.json` ;
  - `traces-20b/traces-20b.tar.xz`, `traces-120b/traces-120b.tar.xz` et leurs journaux ;
  - `20b/`, `120b/` : `localite-*.json`, `courbes-*.csv`, `couches-*.csv`, `plafonds-*.csv`, et leur
    cassure G4 (`*-casse.*`) ; `120b/analyse.log`, `analyse-casse.log` ;
  - `temoins/` (étude 04, témoins globaux et leurs attendus faux, G5 de 20b et de 120b) ;
  - `chemins/` (120b, carte contre processeur) ; `cache-base-contre-optimum.json` ;
    `cache-ram-120b.json` ;
  - `figures/` (CSV larges, `figures-gpt-oss.tex`, PDF).
- Outils : `outils/gptoss-routage/` (`traceur.cpp`, `construire.bat`, `faire_def.py`, `tracer.sh`),
  `outils/gptoss_corpus.py`, `gptoss_octets.py`, `gptoss_base_serie.py`, `gptoss_base_resume.py`,
  `gptoss_disque_phases.py`, `gptoss_file_disque.py`, `gptoss_localite.py`, `gptoss_cache_base.py`,
  `gptoss_comparer_traces.py`, `gptoss_figures.py` ;
  de l'étude 06 `modeles-base.py`, de l'étude 04 `chargement_localite.py`.
- Sources : `memoire/sources/mesures-gpt-oss.bib`.
- Hors dépôt (binaires, traces brutes, essais) : `~/dev/essais/troncons/gpt-oss/`.

## 15. Sources (consultées le 2026-10-15)

- llama.cpp b11515, https://github.com/ggml-org/llama.cpp/releases/tag/b11515 (publiée le 2026-10-09,
  commit 3d65c90d04d337e88f2b1f7f0061f40a5324e662, MIT) ; sources lues sans copie, clone sous
  `~/dev/lectures/troncons/gpt-oss/llama.cpp-b11515`.
- gpt-oss-120b & gpt-oss-20b Model Card, arXiv 2508.10925 (2025-08-08).
- Merity et al., Pointer Sentinel Mixture Models (wikitext), arXiv 1609.07843 (2016-09-26).
- Project Gutenberg n° 17489 et n° 844 (domaine public), https://www.gutenberg.org/cache/epub/… .
- CPython 3.13.12, `Lib/functools.py` (PSF), copie de l'installation locale.
- Belady (1966), IBM Systems Journal 5(2), 78-101, doi 10.1147/sj.52.0078 ; Mattson, Gecsei, Slutz,
  Traiger (1970), IBM Systems Journal 9(2), 78-117, doi 10.1147/sj.92.0078 : métadonnées vérifiées
  auprès de Crossref le 2026-10-15 (les articles eux-mêmes n'ont pas été relus ; les résultats utilisés,
  l'optimalité de Belady et la propriété d'inclusion des algorithmes à pile, sont vérifiés ici par les
  témoins G3 et le garde-fou de pile de l'outil).
- Études de troncons : `fondations/01-machine.md` (débits), `04-chargement.md` (instrument, littérature
  de la localité), `06-modeles.md` (protocole, banc de base).
BibTeX : `memoire/sources/mesures-gpt-oss.bib`.
