# P3, cahier de l'étage B (la KL excédentaire) : non lancé, rendu

Écrit le 2026-10-27. L'étage B est la seule mesure qui peut faire dire « tient » à P3. Je ne le lance pas, pour deux raisons
que la consigne nomme : (1) le verrou de la carte (`~/dev/verrou-carte.txt`) était tenu par une séance de vitesse ABBA du
disque, et une passe de référence lit ~9,7 Go d'experts ; (2) la RAM de pointe de `trc-reference` en f64 sur le 20b n'est relevée nulle part
dans les journaux que j'ai vus, et rien n'assure qu'elle tienne sous 2 Go.

## Ce qui est prêt

- Les ensembles biaisés de l'étage A, au format exact du journal de routage (`u32 couches, u32 positions, puis par couche et position
  4 × u8 experts + f32 marge`), un fichier par (β, budget), sous `~/dev/essais/troncons/mimetisme/P3/routage-impose-V1-b<β>-N<19|31>.bin`.
  Leurs empreintes SHA-256 sont dans `mesures/mimetisme/P3/etage-A.json` (champ `sha256_journal`). Le biais est appliqué au budget N, donc un jeu de
  fichiers par budget ; le budget 19 % (N = 146) est le principal.
- Le moteur sait déjà imposer un routage : `--imposer-routage` de `juge reference` (voir `mesures/moteur/R/r1_reference.py`, fonction `reference`, expérience B).
  Il calcule alors le softmax des quatre choisis sur les logits d'origine de la couche : c'est la règle de l'article de Skliar et al. (sélection biaisée, poids non biaisés).

## Commande (à lancer par quelqu'un qui a vérifié le verrou et la RAM)

Pour chaque β retenu, en commençant par celui que l'étage A désigne comme le plus proche de −10 % de défauts :

1. Copier le fichier voulu à `mesures/moteur/R/r1/routage/p3-b<β>-N19.bin` (le moteur lit `JOURNAUX / "routage" / "<nom>.bin"`).
2. Depuis `mesures/moteur/R` : `python -I -X utf8 -c "import r1_reference as r; r.reference('20b', variante='openai', suffixe='-p3-b<β>', imposer='p3-b<β>-N19')"`.
   Cela écrit `ref-openai-p3-b<β>-20b.kld` sous `~/dev/essais/troncons/lot-R/r1` (~1 Go).
3. KL excédentaire = `juge kl --base ref-openai-20b.kld --test ref-openai-p3-b<β>-20b.kld` (chemin 2) ; premier choix identique lu dans le même rapport.
4. Témoin : β = 0 (le fichier des ensembles non biaisés) doit rendre une KL nulle **au bit** (le routage imposé égale le routage propre de la référence : W de l'expérience D).
   Cassure : un fichier dont 1 % des cellules ont leur 4e expert remplacé par un expert tiré au hasard doit rendre une KL nettement non nulle.

## Arrêt séquentiel (humain E6)

Quatre passes de ~2 168 s (JUGEMENT § 3), ~2,5 h sur 2 fils. Pour réduire : ne lancer que les β qui encadrent −10 % de défauts, dans l'ordre croissant de la part de cellules
changées ; arrêt d'O'Brien-Fleming sur les fenêtres (plancher de 6 fenêtres sur 10) : si la KL excédentaire cumulée dépasse déjà le seuil de mort
(0,07) avec 6 fenêtres, on arrête ce β.

## Ce qui ferait dire quoi (seuils du tri, inchangés)

- tient : ∃ β avec ≥ 10 % de défauts en moins (aux deux budgets) et KL excédentaire ≤ 0,038 et premier choix ≥ 95 % ;
- tombe : au β à −10 % de défauts, KL > 0,07 ; ou aucun β ne rend −5 % avec KL ≤ 0,038 ;
- entre les deux : non concluant.

## Limites de l'étage B tel qu'il est écrit

Les ensembles sont calculés sur la trajectoire du modèle exact (boucle ouverte), puis imposés : dans le moteur de référence la trajectoire réelle de h dérive un peu autour d'eux,
donc l'ensemble qu'un routeur biaisé en ligne aurait choisi n'est pas exactement celui qui est imposé. À l'échelle des perturbations en jeu (marges de 0,01 à 0,3 contre des
écarts de h de l'ordre de 1e-3 en relatif) l'écart est au plus de second ordre, mais il n'est pas mesuré ici. Un routeur biaisé en ligne dans le moteur est l'épreuve finale,
après l'étage B.
