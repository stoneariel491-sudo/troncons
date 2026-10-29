# Reprise : la carte au travail (mesures sur gpt-oss)

Livrable : `mesures/gpt-oss.md`. Données : `mesures/base-gpt-oss/`, `mesures/localite-gpt-oss/`.
Outils : `outils/gptoss-routage/` (traceur C++ sur l'API publique de llama.dll b11515),
`outils/gptoss_*.py`. Essais et binaires (non commités) : `~/dev/essais/troncons/gpt-oss/`.
Sources de llama.cpp b11515 (commit 3d65c90d0, MIT, lues, rien copié) :
`~/dev/lectures/troncons/gpt-oss/llama.cpp-b11515`.
Seul agent sur la carte. Commits : `git commit -- <mes fichiers>` (l'index porte des fichiers
d'autres agents : ne jamais commiter l'index entier).

## 2026-10-15
- 10:15 secteur (BatteryStatus 2), carte libre (909 Mio occupés par l'affichage et les applis).
  Modèles vérifiés (EGAL), sur C: chiffré BitLocker.
- b11515 a `--moe-cache-mib` (cache LRU des experts de l'hôte en VRAM, partagé entre les couches,
  journal de succès à la fin : second chemin pour la simulation de cache).
- Plan : (1) traceur (rappel d'évaluation : ffn_moe_argsort-<il>, ffn_moe_logits_biased-<il>),
  (2) base ABBA 20b puis 120b, (3) traces 20b/120b (4 genres + génération), (4) analyse, doc.
- 10:20-10:45 traceur construit et éprouvé sur 20b (383 jetons : désaccords tri/top-k 0 sur 9 192 ;
  relecture d'une génération : 96,4 % des choix (jeton, couche) identiques). Pièges : le tenseur
  « ffn_moe_logits_biased » est renommé « ffn_moe_probs » (porte SOFTMAX_WEIGHT) ; les vues
  « (reshaped) » ont le même préfixe ; la dernière couche n'est calculée que pour les jetons dont
  on demande la sortie (il faut logits = 1 pour tous, par lots de 1 024).
- Exploration (non retenue, essais/…/explo) : 20b cpu-moe + cache 4 096 Mio : 7,69 j/s génération,
  30,3 j/s préremplissage, 19,9 Go lus (le fichier de 12,1 Go ne reste pas en cache) ;
  120b cpu-moe : 0,49 j/s génération, 3,21 j/s préremplissage, 295 Go lus en 761 s, 12 min 46.
- llama-fit-params : 20b -> experts des couches 0-9 en carte (10 sur 24) ; 120b -> couches 0-1.
- Octets (en-têtes locaux) : un expert 13,254 Mo (les deux) ; 20b A 1,302 Go, R 1,272 Go/jeton ;
  120b A 1,686 Go, R 1,909 Go/jeton. mesures/localite-gpt-oss/octets-gpt-oss.json.
- 10:50 série 20b lancée (échauffement + 2 palindromes cmoe/fit/cache4096, -t 6 -c 2048 -lv 3).
  Prochain : série 120b (même plan), traces, analyse (outils/gptoss_localite.py écrit, pas lancé).
- 11:13 série 20b finie (mesures/base-gpt-oss/20b, resume.csv) : génération cmoe 11,4 / fit 18,9 /
  cache4096 10,2 j/s ; trois textes gloutons différents selon la configuration. -lv 3 ne montre
  pas le bilan du cache : -lv 4 le montre (2 passes « cachelv4 » : 84,59 % de succès, 323 emplacements).
- Témoins : étude 04 revalidés (et cassure qui tombe) ; témoins globaux : deux attendus faux dits
  (G1 uniforme = N/(L·E) faux pour un cache partagé ; G1a N = L·k-1 -> 0 faux sous la règle
  « juger le groupe avant d'évincer » de llama.cpp) ; corrigés, INSTRUMENT VALIDE.
- 11:25 traces 20b lancées (tracer.sh) ; ensuite traces 120b, puis série 120b.
- 11:30 traces 20b faites (xz commité) ; G5 EXACT : réplique de plan() de llama.cpp sur nos traces =
  20 373 et 88 443 succès, comme le journal de llama.cpp ; 322 emplacements -> tombe. Analyse 20b
  commitée (réutilisation 0,50 contre 0,125 uniforme et 0,31 à popularité ; LRU global = 0 sous
  L·k emplacements, pathologie cyclique ; Belady 0,61/0,81/0,955 à 10/20/40 %). G4 (mélange) tombe bien.
- 12:08 traces 120b avec op_offload abandonnées (12 min par lot de 1 024 : copie des 61 Go par fautes
  de page à ~170 Mo/s) ; relancées avec --sans-op-offload (experts des grands lots sur le processeur).
  Partiel abandonné : essais/…/traces-120b-op-offload-abandon (prose-en lecture seule).
- Reste : traces 120b -> analyse (vram libre ~4,5 Go pour deux étages), série 120b (cmoe/fit/cache,
  -lv 4), figures, mesures/gpt-oss.md, bib.
- 13:20 CONTENTION : d'autres agents lisent gpt-oss en même temps (banc_k_justesse sur 120b, qui
  figure aussi parmi les processus de la carte ; trc-codeur sur 20b ; llama-perplexity sur 20b) ;
  RAM libre 64 à 800 Mo. Les traces (contenu déterministe) n'en souffrent qu'en durée ; la série
  120b, si elle tourne sous cette charge, le dira passe par passe (colonnes concurrents, RAM libre,
  ajoutées au pilote).
- 15:06 REPRISE par un nouvel agent (le précédent est mort vers 15:05). Secteur (BatteryStatus 2, 80 %).
  Traceur 120b (lancé 12:09) enlisé : prose-en lecture + génération et prose-fr lecture faites
  (12:18, 12:30, 12:43), puis 2 h 25 dans la génération de prose-fr (12 min sans contention).
  Cause mesurée (PDH) : pagination 200-370 Mo/s, 170-290 Mo libres ; llama-perplexity (lot R, 20b,
  -ngl 0, 10 Go privés) et banc_k (lot K, 120b) d'autres agents ; le traceur avait 8,7 Go privés pour
  1,4 à 5,7 Go résidents. Sortie console retrouvée dans les fichiers de tâche de la session :
  essais/…/traces-120b/journal-traceur-120b-partiel.log (prose-en 0/85 608 désaccords, génération
  0,47 j/s, relecture 8 268/9 216 ; prose-fr 0/103 932).
- 15:15 traceur 27844 arrêté (processus de ce rôle, shell parent mort). tracer.sh paramétré
  (GENRES, GENERER, ETAPES). Relance : dialogue + code en lecture seule (GENERER=0), puis l'invite
  de la base (G5), vers essais/…/traces-120b-reprise/. prose-fr génération abandonnée (réserve : les
  générations sont dégénérées, la lecture est le résultat principal).
- 16:46 traces 120b COMPLÈTES : dialogue (1 600 s), code (1 314 s) en lecture seule ; invite de la base
  (lecture 512 s, génération 0,22 j/s, relecture 7 794/9 216). 0 désaccord tri/top-k sur 409 572 choix
  (4 lectures + wiki). Archive mesures/localite-gpt-oss/traces-120b/traces-120b.tar.xz (4,4 Mo),
  journal des deux relevés. G5 EXACT sur 120b : 14 446 = 14 446 (322 emplacements : 14 425, tombe).
- Analyse 120b commitée (120b/) : r̄ 0,312 (uniforme 0,031, popularité 0,131, +664 σ) ; LRU global
  10/20/40 % 0,565/0,777/0,939 ; Belady 0,780/0,901/0,976 ; à 7,0 % (VRAM) LRU 0,449, Belady 0,706.
  G4 (mélange) tombe : 0,131 (+2,1 σ) ; dialogue −4,2 σ et génération −5,0 σ (dit).
- Outil : témoin de la Proposition 1 aux capacités du seuil (+ cassure --casser-seuil, tombe) ;
  égalité exacte à N = L·k (iii), démontrée. 20b réanalysé : CSV identiques au bit près.
- Cache de la base contre l'optimum sur sa génération (outils/gptoss_cache_base.py) : 120b llama
  39,2 %, oracle fixe 50,0 %, LFU 48,0 %, Belady 68,5 % ; 20b 82,9 / 91,8 %.
- Figures 120b commitées (plafonds sur la lecture).
- 16:47 SÉRIE 120b lancée : 13 passes (échauffement + 2 palindromes cmoe/fit/cache, -lv 4),
  mesures/base-gpt-oss/120b, sortie console essais/…/serie-120b.out (~13 min par passe, ~3 h).
  Ensuite : resume.csv (gptoss_base_resume.py), § 3.2 du livrable, figures (base 120b), En bref.
- 19:58 SÉRIE 120b FINIE (13 passes, secteur) : génération cmoe 0,543, fit 0,568 (dans le bruit),
  cache 0,260 j/s (−52 %, réel ; 35,53 % de succès ; 300 Go copiés par passe). Disque brut pendant la
  génération : cmoe 0,42-0,44 Go/s (0,77 Go/jeton au calme) : pagination à 15 % du débit du disque.
  Outil gptoss_disque_phases.py (témoin contre le total du banc ; défaut du 1er échantillon trouvé).
  Figures avec les points de la base. Biber valide le .bib (Crossref pour Belady et Mattson).
  Livrable mesures/gpt-oss.md COMPLET et relu ; note mesures/gpt-oss-pour-le-memoire.md.
- 20:05 carte prise par le lot R (llama-perplexity) dès la fin de la série : test de la file du disque
  (outils/gptoss_file_disque.py, seuil commité dac1ac3) NON lancé, à faire au calme.
- Rien en cours. Prochain agent : test de la file du disque au calme ; reprise sur D: non chiffré.
