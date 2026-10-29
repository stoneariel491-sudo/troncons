# Reprise du second tirage du routeur biaisé en ligne (P3), note télégraphique

État au 2026-10-27, ~15 h 30. **Aucune mesure utilisable : la seule passe lancée (P0) a été arrêtée par mon garde-fou disque à la
fenêtre 10/10.** Aucun verdict, aucun chiffre de défauts, de KL ou de premier choix sur le nouveau texte.

## Fait (commité)
- `mesures/mimetisme/P3/07-second-tirage-declare.md` (commit `67a8621`, avant toute passe) : texte, seuils, règle de lecture,
  témoin, cassure, prédictions chiffrées.
- Texte choisi : `~/dev/essais/troncons/genome/juge/base-juge-20b.kld` (« fenêtres neuves du juge » : dix extraits de
  wiki.test au-delà de 120 000 octets), SHA-256 `2108487d…50a4` ; 0 fenêtre et 0 8-gramme de jetons commun avec R1 ; sa référence
  f64 existe (`ref-juge-20b.kld`, `a84cb11c…a639`) et sert d'information.
- Outils : `outils/mimetisme/P3/p3_second_tirage.py` (pilote : reprend celui du premier tirage, attend la RAM ≥ 2,5 Go, exige C: ≥ 25 Go
  au lancement et ≥ 18 Go entre passes, pendant la passe arrête à C: < 15 Go) et `p3_second_tirage_analyse.py` (`ab` : chemins A et B,
  défauts par trois chemins, T0 ; `juge` : chemin C, intervalles par fenêtres et par blocs de 51, défauts sous les conventions du
  protocole, cellules par couche, verdict aux seuils déclarés). Écrits, **jamais exécutés** (aucun `.kld` sur lequel les essayer) :
  attendre au moins une erreur de plomberie à la première exécution.
- Journaux de la passe arrêtée : `mesures/mimetisme/P3/second-tirage/{seance.log,P0.log,P0-pilote.json}`.

## Ce qui s'est passé
- Départ : C: libre 24,1 Go puis 21,3 Go (d'autres processus de la machine écrivent sur C: : rien de ce que je lançais ne l'explique).
  Libéré 5 Go en effaçant des doublons de R0 **vérifiés égaux octet pour octet à leur original par SHA-256** (`b28ab190…` pour les
  trois `carte_*` et leurs `-bis`, `46f5d384…` pour `processeur`) : `lot-R/r0/{carte_cmoe-bis,carte_fit-bis,carte_fitauto-bis,
  processeur-bis}.kld` et `lot-R/r0/carte_fit.kld` (identique à `carte_cmoe.kld`). Régénérables par `mesures/moteur/R/r0_ecart.py` ;
  les JSON de témoin (`mesures/moteur/K/k3/*`, `O/journaux/o2/*`) citent ces noms comme entrées. **Restent** : `carte_cmoe.kld`,
  `carte_fitauto.kld` (même hash), `processeur.kld`. Aucun `.kld` de référence touché.
- 14 h 55 : verrou posé, `P0` lancé (C: 25,2 Go, RAM disponible 4,3 Go, swap 3,2 Go). Pendant la passe, C: libre est tombé à **12,1 Go**
  (−13 Go en 27 min alors que ma passe n'écrit que 1 Go) : mon garde-fou (15 Go) a tué le moteur à la **fenêtre 9/10 terminée** (1 608 s).
  Trace non écrite (le moteur l'écrit à la fin). `P0.kld` partiel (953 Mo) effacé. Quelques minutes plus tard C: libre remontait à
  22,9 Go : l'occupant était transitoire. Le message imprimé par le pilote (« C: libre sous 30 Go ») est le texte codé en dur du pilote du
  premier tirage ; le seuil réellement appliqué était 15 Go (déclaré).
- Verrou de la carte supprimé. Aucune passe en cours.

## Pour reprendre (décision de Stone ou de l'orchestrateur)
1. Libérer de la place sur C: et surtout savoir **qui écrit 10 à 13 Go temporaires** pendant 25 min (disque libre 22,9 Go à l'arrêt).
   Les `.kld` de `essais/troncons/genome/juge/` (≈ 13 Go, régénérables, **mais `base-juge-20b.kld` et `ref-juge-20b.kld` sont le texte et
   la référence de ce tirage : à garder**) sont notés « effaçables quand Stone le veut » dans `genome/JUGEMENT-construction.md` § 6 : je n'y
   ai pas touché sans son accord.
2. Poser `~/dev/verrou-carte.txt` (« P3 second tirage, … »), vérifier verrou libre, secteur, C: ≥ 25 Go, RAM ≥ 2,5 Go.
3. `cd outils/mimetisme/P3 && python -X utf8 p3_second_tirage.py P0 B0.041 P0b B0.3` (SANS -I ; ~27 min par passe mesuré ici, ~2 h pour
   quatre ; 1 Go de `.kld` par passe, `P0b.kld` effaçable une fois son SHA-256 relevé).
4. Jamais d'analyse pendant une passe. Ensuite `python -X utf8 p3_second_tirage_analyse.py ab` puis `... juge` (chacun sur machine calme),
   puis écrire `genome/mimetisme/P3/resultat-second-tirage.md` (verdict aux seuils du § 5 de la déclaration, comparaison aux deux tirages,
   ce qui pourrait être faux).
5. Si le disque reste instable : abaisser le seuil en passe de 15 Go à ~5 Go (une passe n'écrit que 1 Go) **en le datant dans la déclaration**
   avant de relancer ; ce n'est pas un seuil de mesure.

## Techniques essayées (pour RECETTES.md)
- Réutiliser le pilote et l'analyse du premier tirage en surchargeant les globales du module (`SORTIE`, `LOURDS`, `BASE`, `C_MIN`) plutôt que
  de les copier : un seul code pour les deux tirages.
- Trouver un second texte sans télécharger ni tokeniser : les « fenêtres neuves » du dossier de construction du juge existaient déjà au
  format `.kld` avec leur référence f64 ; vérification de disjonction par les jetons des en-têtes (fenêtres égales, 8-grammes communs).
- Échec : un seuil d'espace disque en passe fixé au jugé (15 Go) a coûté 27 minutes de carte parce qu'un autre processus a occupé 13 Go
  transitoirement. Le seuil utile est « de quoi finir ma passe » (1 Go + marge), pas « de quoi satisfaire la règle de départ ».

---

# Mise à jour du 2026-10-27, ~23 h 45 : deuxième séance, toujours aucune passe utilisable

**Aucune mesure utilisable, aucun verdict.** Faits, dans l'ordre :
- 22 h 19 : amendement `07b-amendement-garde-disque.md` commité (`e02da16`) : garde disque en passe 15 Go -> 5 Go (`P.C_MIN`). Rien d'autre.
- Verrou posé (« P3 second tirage reprise, agent, … »), secteur branché, C: 32,9 Go, RAM disponible 4,1 Go, swap 2,2 Go : `P0` lancée à 22 h 19.
- Tentative 2 (`P0-tentative2*`) : coupée à 281 s (fenêtre 2/10) par le garde-fou « secteur coupé » : le portable a été débranché
  quelques secondes (`power_plugged=False`, rebranché à la relecture). Cause extérieure.
- Tentatives 3, 4, 5 (`P0-tentative3/4/5*`) : coupées à 29 s, 66 s et 30 s par « RAM disponible sous 0,4 Go (3 relevés) ». Occupants de la RAM (non
  touchés) : la session voix (`cours-llm/recherche/voix`, `venv-kyutai` python 2,3 à 3 Go, `venv-banc` `transcrire.py` 2,1 Go, une dizaine de python),
  `rustc` 1,3 à 1,5 Go, `lualatex` 0,7 Go ; swap 3,5 à 4,4 Go (déjà sur le seuil d'arrêt de 4 Go, qui ne redescend pas tout seul) ; RAM totale 16 Go,
  pointe du moteur 2,9 Go.
- Deux lancements refusés au départ par le pilote : « C: libre 11,1 Go < 25 Go » puis « 24,9 Go < 25 Go ». **Le disque oscille** : 33 Go -> 27 -> 11,9 Go
  (écriture transitoire de 13 à 15 Go par un autre processus, remontée à 26,7 Go environ 10 min plus tard) -> 12,2 Go de nouveau à 23 h 45. Même schéma
  que la première tentative de l'après-midi : l'occupant n'est pas mon moteur (qui n'écrit que 1 Go) ; il coïncide avec la session voix.
- Un relanceur (scratchpad, non commité) a attendu RAM >= 4,5 Go, swap <= 3,4 Go, C: >= 25 Go sans que les trois soient réunis pendant 20 min ; arrêté.
- Fichiers effacés cette séance : les `P0.kld` partiels (200 Mo, 953 Mo avant) de mes propres passes coupées, rien d'autre. Verrou supprimé.

## Pour reprendre
1. Il faut une machine calme pendant ~2 h : session voix/kyutai/banc en pause, pas de cargo, C: libre durablement >= 25 Go (libre 12,2 Go à 23 h 45). Si le disque
   ne remonte pas : seule voie propre = effacer des `.kld` régénérables de `essais/troncons/genome/juge/` (≈ 12 Go, hors `base-juge-20b.kld` et
   `ref-juge-20b.kld`), décision de Stone (noté « effaçable quand Stone le veut » dans `genome/JUGEMENT-construction.md` § 6).
2. Le swap (3,8 à 4,0 Go sans moteur) est sur le seuil d'arrêt déclaré : un redémarrage du poste le remet à zéro ; ou Stone relève le seuil de swap (garde-fou,
   pas un seuil de mesure) en le datant dans un amendement 07c.
3. Même commande qu'avant (`cd outils/mimetisme/P3 && python -X utf8 p3_second_tirage.py P0 B0.041 P0b B0.3`, verrou posé avant). **Garder `P0b.kld`
   jusqu'à la fin de l'analyse `ab`** : `p3_routeur_ligne_analyse.py` traite toute passe de code 0 autre que P0 et P-1 (donc P0b) comme une passe à comparer et
   lit son `.kld` ; l'effacer avant fait échouer `juge_kl`. (Erreur de plomberie prévue par lecture ; l'analyse n'a toujours jamais été exécutée.)
4. Le pilote écrit `P0.log` / `P0-pilote.json` à chaque tentative, en écrasant : renommer ceux d'une tentative coupée en `*-tentativeN*` avant de relancer.
