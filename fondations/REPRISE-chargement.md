# Reprise : étude 04, chargement à la demande, déchargement, recouvrement

Livrable : `fondations/04-chargement.md`. Outils : `outils/` (préfixe `chargement`).
Journaux : `fondations/journaux/04-chargement/`.
Clones de lecture : `~/dev/lectures/troncons/chargement/` (FlexLLMGen, MoE-Infinity,
PowerInfer, airllm, fiddler, ktransformers, llama.cpp, mixtral-offloading).
Essais : `~/dev/essais/troncons/chargement/`.

## 2026-10-15
- Pas 1 (prédécesseur, mort vers 00:09) : outil `chargement_pcie.py` + `pcie-1.json`, non commités. Repris.
- pcie-1 : H2D épinglé plafonne 6,4 Go/s ; témoin VRAM tombé à 16 Mio (719 Go/s) = cache L2.
- nvidia-smi pendant une passe : lien Gen1 au repos, Gen3 surtout pendant les copies seules,
  Gen4 sous charge -> 6,4 Go/s = Gen3 x8 (7,88 théorique). Journal `lien-nvidia-smi-passe-1b.csv`.
- Outil révisé : NVML (gen/largeur/pstate par mesure), L2 lu (attribut 38 = 32 Mio ; l'attribut 89
  de la passe 2 était faux, L2 lu 0), phase H2D sous charge, occupation de la carte au journal.
- pcie-2 : carte PARTAGÉE (llama-imatrix d'un autre agent en calcul) et L2 faux -> renommé
  `pcie-2-carte-partagee-l2-faux.json`, non exploitable sauf « H2D sous charge Gen4 ~7,6 Go/s ».
- À refaire : passe 3 quand la carte est calme (occupation_depart < 5 %).
- Outil `chargement_localite.py` : trace de routage -> réutilisation adjacente (et hasard uniforme
  / à popularité), distances, succès LRU/LFU/statique/Belady par budget. Témoins T1-T4 valides ;
  `--casser` (ordre mélangé) fait tomber T3. Deux erreurs de la 1re passe corrigées et dites dans
  le code (attendu de T3 ; statique hors invariant de Belady). Journaux localite-temoins*.json.
- Aucune trace réelle : aucun MoE sur la machine. Téléchargement à demander (Qwen3-30B-A3B ou
  OLMoE-1B-7B, > 500 Mo) + un moyen de vider le routage (llama.cpp à compiler, CUDA 13.1.2 dépaqueté).
- Outil `chargement_juge.py` : octets/jeton par étage / débit -> bornes (recouvrement, série), et
  « succès impliqué » d'une mesure publiée. 5 témoins publiés sous leur borne ; `--casser`
  (débits / 10) en fait tomber 4. Tableau de la machine : `juge-stone.txt` (débits RAM et disque
  = hypothèses tant que l'étude 01 n'a pas mesuré).
- Lu et noté (web, 2026-10-15) : FlexGen, LLM in a flash, PowerInfer 1/2, Mixtral-offloading,
  Mixtral (table 5), MoE-Infinity, Fiddler, ProMoE, HOBBIT, AdapMoE, ExpertFlow, KTransformers
  (PDF), DALI, SeqMoE, SpecMD, Cache-conditional experts, Cacheable by design, SSD-LLaMA,
  PR llama.cpp 25294, #20757, #24528, #27149, moe-stream, DirectStorage 1.4, CommitMoE.
  llama.cpp HEAD : --moe-cache-mib, --load-mode dio, lazy read + PrefetchVirtualMemory.
- Prochain : écrire fondations/04-chargement.md.
- Livrable écrit : fondations/04-chargement.md (§0 en bref, §1 loi et étages mesurés, §2 denses,
  §3 MoE, §4 localité, §5 pipelines, §6 juge sur la machine, §7 trous, §8 proposition, §9 faux,
  §10 sources, §11 recettes, §12 téléchargements).
- Reste : passe PCIe propre quand la carte est libre (pcie-3) ; remplacer RAM/disque du juge par
  les mesures de l'étude 01 (barrer) ; trace réelle dès qu'un MoE est téléchargé.
- Disque lu dans le journal provisoire de l'étude 01 : 2,4 Go/s aléatoire à 1 Mio (pas 6,7) ->
  juge refait (--disque-go-s 2.4, juge-stone-disque-2.4.txt), phrases barrées dans le livrable.
