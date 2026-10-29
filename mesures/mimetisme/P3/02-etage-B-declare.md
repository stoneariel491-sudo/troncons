# P3, étage B : seuils et protocole déclarés avant toute lecture de KL (2026-10-27)

Seuils : ceux de `00-seuils-declares.md` § 3 et de `cahier-etage-B.md`, **inchangés**. Rien d'une KL réelle de P3 n'a été lue avant ce texte.

## Seuils (rappel littéral)
- tient : ∃ β avec ≥ 10 % de défauts en moins et KL excédentaire ≤ 0,038 et premier choix identique ≥ 95 % ;
- tombe : au β à −10 % de défauts, KL > 0,07 ; ou aucun β ne rend −5 % avec KL ≤ 0,038 ;
- entre les deux : non concluant.
- KL excédentaire = KL(ref-openai ‖ référence à routage imposé), `juge kl` chemin 2. Au β = 0 elle est nulle (témoin), donc l'excédent est la KL elle-même.

## Périmètre de cette séance
- Budget 19 % (N = 146) seulement. Le budget 31 % n'est pas passé : tout « tient » est donc dit **partiel** (la condition « aux deux budgets » n'est pas vérifiée ici).
- Fichiers : `mimetisme/P3/B/routage-impose-V1-b0.0-N19.bin` (témoin), `...-CASSURE-1pct.bin`, `...-b0.06-N19.bin` (−9,93 % de défauts : 194 904 contre 216 397) et `...-b0.07-N19.bin` (−11,53 % : 191 442), empreintes dans `fichiers-B.json`.
  Le franchissement de −10 % est entre les deux ; le β qui atteint ≥ 10 % est 0,07.
- Ordre : témoin β = 0, cassure, β = 0,06, β = 0,07.

## Témoins
- T0 : β = 0 doit rendre KL = 0 et premier choix identique 100 %, **au bit** (fichier .kld identique octet pour octet à `ref-openai-20b.kld`, ou à défaut KL max = 0 exactement ; un écart est dit, non masqué).
  Cassure de T0 : T1.
- T1 cassure : 1 % des 4es experts remplacés au hasard (1 226 cellules) doit rendre une KL nettement non nulle : seuil déclaré **> 1e-4** (cent fois la plus petite KL jugée à 7e-5 en R1, ordre du bruit des bascules spontanées 1,7e-3 / 5 087 cellules : 1 226 cellules forcées doivent au moins égaler 1e-4).
- Second chemin du chiffre principal : `juge kl` est le chemin 2 ; le chemin 1 (llama-perplexity) ne lit pas un routage imposé. Second chemin retenu : recalcul indépendant en Python (numpy) de la KL moyenne et du premier choix à partir des .kld des deux passes via le CSV par position du juge, et vérification que la KL de la passe β = 0,06 contre β = 0,07 est cohérente (inégalité triangulaire grossière), à défaut d'un second lecteur de .kld. Dit comme tel.

## Arrêt séquentiel (O'Brien-Fleming, tel que le cahier le pose)
La référence calcule couche par couche pour les 10 fenêtres à la fois : les logits n'existent qu'à la fin de la passe, donc l'arrêt ne peut pas couper une passe. Il s'applique **entre les β** : après la passe d'un β, la KL cumulée sur les fenêtres 0 à 5 (plancher de 6 sur 10) est lue dans le CSV ; si elle dépasse 0,07, ce β est « tombé », et les β plus grands ne sont pas lancés (la part de cellules changées croît avec β). La KL sur les 10 fenêtres reste le chiffre jugé.

## Garde-fous de séance
Verrou de la carte pris pour la séance ; secteur exigé ; arrêt si C: libre < 30 Go, si la RAM libre tombe sous 0,5 Go de façon durable ou si le swap explose ; RAM de pointe relevée sur la première passe (pointe de la mémoire de travail du processus, échantillonnée toutes les 5 s) et notée.

## Prédiction écrite avant
KL a priori de l'étage A : 0,309 × part de cellules changées = 0,037 à β = 0,06 (12,0 %) et ~0,043 à 0,07. Je ne sais pas dans quel sens l'erreur va (étage A § 4.2).
