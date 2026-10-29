# Reprise : étude 06, les modèles ultra lourds visés, et comment juger

Livrable : `fondations/06-modeles.md`. Outils : `outils/` (inventaire_modeles.py, préfixe `modeles-`).
Journaux : `fondations/journaux/06-modeles/`.
Essais : `~/dev/essais/troncons/modeles/`.

## 2026-10-15
- Reprise d'un prédécesseur mort sans note : outils/inventaire_modeles.py (en-têtes safetensors
  par requêtes Range, aucun poids téléchargé) et journaux/06-modeles/inventaire.json (10 dépôts,
  Qwen3-235B en erreur réseau sur un fragment). Adoptés tels quels, commités.
- Prochain : liste des modèles du jour (API HF), compléter l'inventaire, tailles GGUF, octets/jeton,
  protocole de jugement, liste des téléchargements.
- 01:30-02:05 : passe 2 (47 dépôts) puis outil corrigé (FP4 en U8/I8 par la forme de l'échelle,
  index safetensors contre les doublons Mistral, clé top-k, experts fusionnés « .moe. », tables
  de n-grammes et Engram = « recherche »). Passe 3 en cours -> inventaire-3.json.
- Témoin modeles-temoin-inventaire.py : tombe sur la passe 2 (6 échecs, tous des bogues connus).
  À relancer sur la passe 3 (attendu : 0 échec ; Step-3.5 à refaire après la passe 3).
- En-têtes GGUF distants (gguf-entetes.json) : octets/jeton exacts des fichiers candidats ;
  plafonds-fichiers.md (calculé). Juge : modeles-juge.sh, validation 4B/9B sur la carte en cours
  (essais/troncons/modeles/juge). PPL 4B Q4_K_M = 8,7259 ± 0,2295 (40 fenêtres, carte).
- Reste : passe 3 + témoin, tableau octets/jeton, lecture licences, rédaction 06-modeles.md.
- 02:00-02:45 : livrable 06-modeles.md écrit et commité (52e39df, puis corrections). Banc base
  (modeles-base.py, PDH au lieu de typeperf), témoin disque (2/3 passes tiennent, machine chargée),
  témoins KL : même modèle = plancher 16 bits (max 6,8e-5) ; 9B contre base 4B = KL 0,294, top-1 76,9 %
  (l'instrument tombe, bien). ATTENTION : « -ngl 0 » n'est PAS le processeur seul (déchargement des
  opérations par défaut, --op-offload) ; plancher processeur pur (CUDA_VISIBLE_DEVICES=-1) en cours
  -> juge/plancher-cpu-pur-contre-carte.kld.log ; corriger § 0 et § 7.3 avec ce chiffre.
- MMLU 4B tombé en manque de VRAM (autres agents) à 758 questions (36,9 %). ARC non fait. Suite 9B
  arrêtée (inutile au témoin).
- 03:05 : plancher processeur pur mesuré (KL 0,0055 moyenne, top-1 95,96 % contre la carte) ; doc
  corrigé (phrases barrées), journaux copiés sous fondations/journaux/06-modeles/juge/.
- ÉTAT : livrable complet. Restes possibles : MMLU/ARC du 4B à refaire carte libre (N_MC=400) ;
  témoin disque à refaire machine calme ; plancher entre moteurs sur gpt-oss dès le téléchargement ;
  premier banc base (modeles-base.py) sur gpt-oss-20b puis 120b quand l'orchestrateur aura téléchargé.
