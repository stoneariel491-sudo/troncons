# Reprise du lot F (format et codeur)

Lot F : `moteur/crates/trc-format/**`, `moteur/crates/trc-codec/**`, `moteur/bins/trc-codeur/**`,
journaux et outils sous `mesures/moteur/F/`. Spécification : `decisions/ARCHITECTURE.md` § 4,
§ 5.3, § 5.4, § 6.5 (F1, F2/F3), § 7.1 (C1).

## 2026-10-15

- **F1 fait** : `trc-format` (en-tête, MÉTA et paires GGUF, RÉSIDENTS, TABLES, RÉPERTOIRE, parties,
  `Ecrivain`, empreinte64) et `trc-codec` (TableRans, flux § 4.9.1, codeur et décodeur génériques à
  contexte, chemins rapides par voie et à une table, reconstruction v1.0 et brute, codage d'une
  matrice v1.0). 11 tests verts (`mesures/moteur/F/tests-f1.log`).
- Témoins F1 : aller-retour écrit → relu identique ; flux à une table **identiques octet pour octet
  à ceux du codeur de l'étude 03** (géométries 1 et 2, LUT comprises) et relus par notre décodeur ;
  chemin rapide par voie = chemin générique ; expert MXFP4 synthétique reconstruit au bit près.
- Cassures F1 : en-tête faussé (magie, version, réservé, empreinte, section, couches) refusé ;
  version 1.9 et drapeau inconnu refusés une fois ré-empreints ; sections faussées refusées ;
  fichier tronqué refusé ; partie faussée (magie, sorte 0x05, réservés, bourrage) refusée ; table
  faussée (deux fréquences échangées) → sortie fausse et voies hors de L ; mot, état faussés →
  vus ; mot de trop → vu par le seul second contrôle (mots consommés).
- **Témoin des témoins** (`casser_temoins_f1.py`, journaux `casser-temoins-f1-passe1.log` et
  `casser-temoins-f1.log`) : 9 cassures du code, chacune fait tomber au moins un test, fichiers
  restaurés à l'octet près. **Passe 1 : une cassure ne tombait pas** (« ne compte pas les voies
  hors de L ») : les tests ne regardaient que `intact()`, que le contrôle des mots rendait faux à
  lui seul. Corrigé : assertions séparées sur `voies_hors_l` et `tuiles_mots_faux`, plus un cas qui
  n'est vu que par le second contrôle. Passe 2 : 9 sur 9 tombent.
- Ajout au décodeur (sans changer un octet du format) : **second contrôle gratuit**, chaque tuile
  doit consommer exactement ses mots (`début[t+1] − début[t]`), en plus du retour des voies à L.
- **Construction** : l'espace de travail `moteur/` ne se charge pas tant que
  `crates/trc-noyaux/` (lot K) n'a pas de `Cargo.toml` (règle écrite par le lot O en tête de
  `moteur/Cargo.toml`). En attendant, je construis par un espace cargo de brouillon hors du dépôt
  qui dépend de `trc-codec` par chemin (les crates du lot F héritent quand même des versions de
  `[workspace.dependencies]`). Rien à faire de mon côté ; le signaler au lot K / à l'orchestrateur.

### Précisions de la spécification (à porter à l'arbitre ; aucune ne change un octet fixé par le § 4)

Choix pris, les plus prudents, marqués « réponse par délégation du 2026-10-15, réversible » :
1. **Longueur d'une section** (§ 4.3, champ sections) : octets utiles, empreinte finale comprise,
   sans le bourrage qui mène à la section suivante. Raison : le § 4.4 dit « puis des zéros jusqu'à
   4 096 » sans dire s'ils comptent ; avec ce choix, l'empreinte de toute section finissant par une
   empreinte est à `fin − 8`.
2. **Place de l'empreinte de la table des RÉSIDENTS** (§ 4.5, « après la zone de données ») : juste
   après le dernier octet du tenseur qui finit le plus loin, sans alignement ; donc aux 8 derniers
   octets de la section. Le lecteur la lit à `fin − 8` et vérifie que la longueur vaut
   `début_zone + fin_données + 8`.
3. **Octets utiles d'une partie** (§ 4.7, 4.8) : fin du dernier flux. Pour la v1.0, le dernier flux
   est un rANS, déjà bourré à 16 : pas d'ambiguïté en pratique.
4. **Champ « contexte fixe »** (§ 4.8) : 0 pour DELTA ; 0xFF pour MEDIANES, BIAIS, les flux bruts et
   les flux à contexte variable (CODES_CTX, BASE_CTX, COMPL_CTX).
5. **Champ « octets produits »** d'un flux rANS (§ 4.8) : P (bourrage compris), égal au champ P de
   l'en-tête du flux ; d'un flux brut : sa longueur.
6. **Classe d'échelle des blocs de bourrage** (§ 4.9.3 ne la dit pas si R · B · 16 n'est pas un
   multiple de 128) : κ = 0, celle du δ de bourrage (0). Le DELTA bourré couvre toujours les blocs
   de bourrage des codes (⌈R·B/128⌉·128 ≥ ⌈R·B/8⌉·8). Sans effet sur gpt-oss (R · B = 259 200 =
   2 025 × 128).
7. **Structures du § 5.3 étendues** (champs ajoutés, rien d'existant changé) : `Entete` porte
   aussi `poids_par_bloc`, `octets_par_bloc`, `type_ggml` (champs 112, 116, 120 du § 4.3) ;
   `Partie` porte `n_matrices` et `utiles`. Fonctions ajoutées : `Fichier::paires/paire/table/
   toutes_tables/repertoire/chemin`, `lire_paires`, `assembler_partie`, `serialiser_*`,
   `empreinte64_morceaux` ; dans `trc-codec`, `decoder_partie`, `verifier_partie`,
   `reconstruire_avec`, `TablesFichier`, `decoder_matrice_v10`, `preparer_matrice`,
   `ComptesMatrice`, `coder_matrice_v10`, `flux_bruts`, et le module `rans` public.
8. **Règle d'arrondi des tables** (non normative : les fréquences sont stockées) : celle de 03 et
   de F1, pour que les mêmes comptes donnent les mêmes octets (témoin d'identité).
9. **Ordre des flux du fichier brut** (§ 4.8, « ECHELLES_BRUTES_j, CODES_BRUTS_j, BIAIS_j ») : pour
   j = 0, 1, 2, les trois flux de la matrice j à la suite. TABLES vide (n = 0) dans un fichier brut.

### Étape suivante

F2 : `trc-codeur` (GGUF → .trc, compagnon vocab, vérification C1), seuils déclarés avant dans
`mesures/moteur/F/00-seuils-declares.md`, puis codage de gpt-oss-20b sous
`~/dev/modeles/trc/`.

## 2026-10-15, F2 (gpt-oss-20b) : fait

- `trc-codeur coder` 20b : 13 h 05 → 13 h 22, sur secteur (BatteryStatus 2 au début et à la fin),
  6 fils, priorité sous la normale ; `gpt-oss-20b.trc` = 11 157 405 696 o (repère 11,1 Go : +0,5 %,
  dans le 1 % déclaré) ; SHA-256 du GGUF recalculée = `telechargements.json`. Pointe de l'ensemble
  de travail 0,65 Go. Code de sortie non relevé par `lancer.ps1` (ExitCode vide sans descripteur
  gardé : corrigé, `$p.Handle` puis `WaitForExit()`) ; le journal JSON prouve la fin normale.
- **C1 tient** (`verifier-20b.json`) : 768 experts sur 768 exacts, 0 contrôle faux sur les cinq ;
  315 résidents égaux ; méta identique ; SHA-256 recalculée une seconde fois par la vérification.
- **Taux** (`comparer-f1-20b.json`, `csv/f1-contre-trc-20b.csv`) : les 12 tenseurs de F1 égaux au
  millionième (codes, δ, médianes, total A_ctx 3,843137), tronçons 11 990 368 / 11 837 440 /
  12 144 640 exactement ; r_03 du modèle entier 1,103732 contre 1,1037 (écart 2,9·10⁻⁵, seuil 10⁻³).
  Plus grand tronçon : 12 144 640 o ; moyen sur les 768 : 12 013 664 o.
- **Cassures** : en mémoire (`--casser 7 13`) → exactement 1 expert faux, (7, 13), contrôles
  « empreinte de partie », « octets », « empreinte du décodé » faux, « empreinte GGUF » juste
  (attendu : la source n'est pas touchée) ; sur une vraie copie (`casser_copie.py`, décalages lus
  par le seul § 4 ; `cmp -l` : un seul octet différent, 8 818 286 848, 120 → 121) → exactement
  (17, 29) faux, mêmes contrôles, code de sortie 1. Copie laissée sous `modeles/trc/casse/`
  (11,2 Go, hors dépôt ; à effacer quand Stone le veut).
- Recette : `cmp -l` de Git Bash sur 11 Go a pris ≈ 1 h 30 (13 h 32 → 15 h 05) : lent ; pour le
  120b, la cassure se fait en mémoire seulement (déclaré dans `00-seuils-declares.md`).

### Étape suivante : F3 (gpt-oss-120b)
- 15 h 10 : 336 Mo de RAM disponibles (traceur d'un autre agent sur le 120b, 8,7 Go privés) →
  codeur et vérification réécrits à **mémoire bornée** (deux passes par paquets de 12 experts,
  lectures sans tampon, recopies par morceaux de 16 Mio). Format inchangé. Témoin d'identité :
  20b recodé = F2 au SHA-256 près (Get-FileHash), copie cassée différente. Pointes : codeur
  0,38 Go (0,65 avant), vérification 0,42 Go (1,28 avant). Défaut trouvé en route : SHA-256 sans
  tampon relisait après la lecture courte de fin (décalage non aligné → erreur 87) ; corrigé,
  témoin et cassure ajoutés (`casser-lecture.log`, 4 cassures sur 4 tombent).
- Recette : une cassure qui fait boucler le code (« if k == 0 && false ») ne fait pas tomber le
  test, elle le fait pendre ; délai de 15 min dans le script, et cassure reformulée.
- Recette : arrêter un processus de test pendu par Stop-Process est refusé par la permission ;
  TaskStop de la tâche de fond qui l'a lancé l'arrête avec son arbre (fichier cassé restauré à la main).
- 15 h 52 : lancement du codage du 120b (`coder-120b`), vers `modeles/trc/gpt-oss-120b.trc`.

## 2026-10-15, F3 (gpt-oss-120b) : fait

- `gpt-oss-120b.trc` : 57 730 662 400 o (repère 57,65 Go : +0,14 %), codé en 1 153 s, pointe
  0,391 Go ; SHA-256 du GGUF = téléchargement (codeur et vérification).
- **C1 tient** : 4 608 experts sur 4 608 exacts, 0 contrôle faux, 471 résidents égaux, méta
  identique. r_03 = 1,102592 (1,1026 attendu, écart 7,7·10⁻⁶). Plus grand tronçon 12 251 136 o
  (à porter au § 4.14 par l'arbitre : taille du tampon d'arrivée), moyen 12 026 060 o.
- Cassure en mémoire (29, 101) : exactement cet expert faux, code 0.
- Pointes 120b / 20b : codeur 1,033, vérification 1,028 (seuil 1,25) : fenêtre indépendante du
  modèle.
- Verdicts complets : `mesures/moteur/F/verdicts.md` ; CSV régénérés (`vers_csv.py`).
- Fichiers hors dépôt sous `~/dev/modeles/trc/` : gpt-oss-20b.trc, gpt-oss-120b.trc,
  les deux .vocab.gguf ; `casse/gpt-oss-20b-casse.trc` (11,2 Go) et
  `temoin/gpt-oss-20b-2passes.trc` (11,2 Go, identique à F2) à effacer quand Stone le veut.

### Étape suivante : F4 (v1.1, J2), pas avant la décision de l'arbitre.

## 2026-10-15, 20 h 40 à 21 h 15 : second chemin de C1 (consigne : « si tout est fait, vérifie C1 sur le 120b par un second chemin »)

- F1 à F3 déjà faits : rien d'autre à terminer.
- Seuils déclarés avant (00-seuils-declares.md, commit c87c562).
- Outil `mesures/moteur/F/second_chemin_c1.py` (Python, bibliothèque standard, écrit depuis le seul
  § 4 + spéc. GGUF v3, sans relire trc-format / trc-codec / gguf.rs) ; lanceur `lancer_py.ps1`.
  GGUF lu sans tampon ; décalages des tenseurs croisés avec `gguf_init_from_file` de
  `ggml-base.dll` b11515 (llama.cpp) ; SHA-256 par hashlib.
- **Tient sur les deux modèles, sur secteur (2 / 2), verrou tenu** : 768/768 et 4 608/4 608
  empreintes d'experts refaites depuis le GGUF = répertoire ; biais et médianes égaux octet pour
  octet ; parties, structure, en-tête, MÉTA, TABLES (288 / 432), RÉPERTOIRE, résidents (315 / 471)
  sans écart ; 0 écart contre llama.cpp ; SHA-256 = téléchargement (troisième calcul).
- Cassures : 6 sur 6 tombent exactement où déclaré (3 experts nommés sur 768 et sur 4 608 ;
  1 écart llama.cpp ; SHA différente ; décalage → 768/768 et 256/256).
- Journaux `journaux/second-chemin-*.json`, CSV `csv/second-chemin-c1.csv`, verdicts.md (section
  ajoutée, une phrase barrée), derivations.md § 9 (proposition 8) ; § 8 : « 24 minutes » barré →
  24 secondes (unité fausse).
- **Défaut de l'outil trouvé en route** : version GGUF lue sur la magie (curseur à 0) → repli de
  relecture croissante sans borne → le fichier de 12 Go chargé en RAM (pointe 10 Go) avant échec.
  Arrêt par Stop-Process refusé par la permission ; TaskStop a tué le shell mais pas le python
  (lancé sous `timeout`) ; il a fini seul en ~2 min. Corrigé (curseur 4, relecture ≤ 256 Mio).
  Recette : jamais de lecture « jusqu'à ce que ça passe » sans borne ; jamais `open().read()` d'un
  modèle dans un essai.

### Reste (lot F)
- Maillon « tronçon → décodé » du 120b par un second décodeur : `temoin-trc` du lot K sur la carte
  (`temoin-trc.exe ~/dev/modeles/trc/gpt-oss-120b.trc k1-trc-gptoss120b.json --fils 3`,
  au lot K) ; et l'épreuve du § 8 (juge).
- F4 (v1.1, J2) après décision de l'arbitre ; fichier brut (`--brut`) quand O3/O4 le demandent.
- Disque à libérer quand Stone le veut : `modeles/trc/casse/` et `modeles/trc/temoin/` (22,4 Go).
