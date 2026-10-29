# Les mesures sur gpt-oss : ce qu'elles apportent au mémoire

Rédigé le 2026-10-15 par l'agent « la carte au travail ». Livrable source : `mesures/gpt-oss.md` (tous
les chiffres en viennent, et viennent eux-mêmes des fichiers commités qu'il cite). Étiquettes :
**[mes.]** mesuré, **[calc.]** calculé, **[dém.]** démontré, **[lit.]** littérature.

## D'où on part, où on va

- **Au départ** : le plafond des études 04 et 06 sous routage uniforme (h = C/E), un instrument de
  cache validé sur des traces synthétiques, aucune trace réelle, aucun chiffre de llama.cpp sur
  gpt-oss.
- **Ce que l'étape établit** : la base llama.cpp b11515 mesurée sur gpt-oss-20b et 120b ; les traces de
  routage réelles (10 669 jetons de lecture par modèle, quatre genres), relevées par le même moteur
  que la base (témoin G5 exact sur les deux modèles) ; la localité et les courbes de succès de cinq
  politiques ; la Proposition 1 (seuil et plateau du LRU partagé) ; les plafonds de jetons/s avec les
  débits mesurés ; deux faits sur le routage (dépendance au chemin de calcul).
- **Ce qui reste** : § 10 du livrable (D: non chiffré, repos, conversation, prédicteur réel).

## 1. Ce que le travail mérite dans le mémoire

### Schémas (TikZ)

1. **Le relevé du routage** : le graphe de calcul d'une couche MoE de gpt-oss (attention → norme →
   routeur `ffn_gate_inp` → `ffn_moe_probs` [E, n] → `ffn_moe_argsort` [E, n] → top-k → softmax des k
   scores → experts → somme pondérée), avec les deux nœuds lus par le rappel `cb_eval` marqués, la
   question « ask » puis la lecture `ggml_backend_tensor_get`, et le second chemin (notre top-k sur les
   scores).
2. **Les trois pièges** (§ 4.2) en trois vignettes : le renommage `logits_biased → probs`, la vue
   « (reshaped) » au même préfixe, l'élagage de la dernière couche aux seuls jetons de sortie.
3. **Le flux global des accès** : un anneau de L secteurs (couches) de k accès, un jeton = un tour ;
   l'expert (l, e) et les (L − 1)·k accès qui le séparent de sa prochaine demande ; un LRU de N
   emplacements dessiné comme un arc ; les trois régimes de la Proposition 1 (N ≤ (L−1)k : rien ;
   N = Lk : exactement la réutilisation adjacente ; au-delà : le plateau).
4. **Les deux étages de 120b** : disque (2,82 Go/s) → RAM (page cache) → PCIe (12,2 Go/s) → VRAM
   (251,3 Go/s), avec h_v, h_r, 1 − h sur les flèches, et le chronogramme « recouvert » d'un jeton à
   20 % LRU : 10,1 ms VRAM, 86,2 ms PCIe, 151 ms disque, le disque borne.
5. **Le cache de llama.cpp** (lu dans `src/llama-moe-cache.cpp`) : un seul LRU par groupe de couches de
   même disposition, la règle de `plan()` (succès touchés dans l'ordre du score, défauts triés par
   numéro, emplacement le plus ancien), la synchronisation par couche en décodage, la lecture seule
   en grand lot.

### Structures

- **Le format de trace** (étude 04) : en-tête « # … », ligne « E=<n> », puis une ligne par jeton, les
  L couches séparées par « | », les k experts dans l'ordre du score ; et le fichier `.poids` (les k
  poids de mélange, softmax des scores retenus).
- **Les octets de gpt-oss** (`octets-gpt-oss.json`, lus dans l'en-tête GGUF) : un expert =
  13 253 760 o (gate, up, down en MXFP4 et leurs biais F32) ; A = toujours lus ; R = k·L·e routés par
  jeton ; tableau champ par champ (§ 1 du livrable).
- **Le relevé d'une passe de base** (`passes.csv`, 32 colonnes) : alimentation, jetons/s, mémoire de
  pointe, VRAM, octets disque (compteur PDH intégré, repos soustrait), bilan du cache, concurrents.

### Graphes (pgfplots ; données dans `mesures/localite-gpt-oss/figures/`, script `outils/gptoss_figures.py`)

1. Succès du cache global selon le budget, cinq politiques et la diagonale sans localité, 20b et 120b
   (`succes-gpt-oss-*-lecture.csv`) ; marquer sur 20b la falaise (12 %) et sur 120b la capacité réelle
   de la base (7,0 %).
2. Réutilisation par couche contre ses deux hasards (`reutilisation-gpt-oss-*.csv`).
3. Plafond de jetons/s selon le budget (`plafonds-gpt-oss-*.csv`), avec les points mesurés de la base
   (`base-gpt-oss-*.csv`) : la base sous son plafond.
4. À ajouter : la série de base en barres avec min et max par configuration (`resume.csv`), et le
   bruit de chaque configuration.
5. À ajouter : la Proposition 1 sur la courbe dense du lot O (`mesures/moteur/O/csv/falaise-20b-dense.csv`),
   avec la droite r̄·(T − 1)/T = 0,5026 posée par-dessus le plateau.

### Tableaux

- La base, 20b et 120b (§ 3), avec la règle de décision et les verdicts.
- La réutilisation par genre et ses deux hasards (§ 6.1, § 6.2).
- Les succès par budget et par politique, portée globale et par couche (§ 6).
- Le cache de la base contre l'optimum sur sa propre génération (`cache-base-contre-optimum.json`) :
  120b, 323 emplacements, llama.cpp 0,392, LFU 0,480, ensemble fixe oracle 0,500, Belady 0,685.
- Les témoins (§ 5) : ce qu'ils vérifient, la réponse connue, le résultat, la cassure qui les fait
  tomber.

### Théorème (énoncé, démonstration, vérification : § 7 du livrable) [dém.]

**Proposition 1** (LRU partagé entre couches, groupes jugés avant éviction) : (i) N ≤ (L−1)·k → aucun
succès ; (ii) N ≥ L·k → h ≥ r̄ sur t ≥ 1 ; (iii) N = L·k → h = r̄ exactement. Corollaire en fraction des
experts. Vérifiée au succès près sur 17 traces réelles (deux modèles), cassure qui tombe. Le point (i)
est aussi le lemme 3 du lot O ; (iii) donne la hauteur du plateau qu'il a mesuré.

### Calculs posés (à reprendre pas à pas dans le texte)

- Les plafonds de la base 20b (§ 3.1) : `cmoe` à 93 % de 15,6 Go/s, `fit` à 90 %, `cache` à 27 %.
- Le seuil « égaler le processeur » : h = 0,22 (§ 8.2).
- Le point LRU 20 % de 120b à deux étages (§ 8.3) et l'effet d'une compression ×2 en transit.

### Listings commentés

- `traceur.cpp` : le rappel `rappel()` (ask puis lecture, nom exact « préfixe + couche »), `passer()`
  (sortie de tous les jetons, par lots) ; environ 60 lignes.
- `gptoss_localite.py` : `g_lru_llama` (la réplique de `plan()`, 20 lignes) et `g_belady` (prochain
  usage pris à l'accès, mise de côté du groupe courant).

## 2. Ce qui pourrait être faux (pour la section du mémoire)

Le § 11 du livrable, en entier ; les trois points qui pèsent le plus : la machine n'était pas au repos
(jetons/s minorants) ; 10 669 jetons de quatre textes sans gabarit de conversation ; le routage dépend
du chemin de calcul (une trace vaut pour son chemin).

## 3. Sources

`memoire/sources/mesures-gpt-oss.bib` (llama.cpp b11515, carte du modèle gpt-oss, fichiers GGUF,
wikitext, Gutenberg, CPython, Belady 1966, Mattson et al. 1970).
