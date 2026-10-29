# Épreuve J1 : seuils déclarés avant toute passe (2026-10-16, ~~02 h 40~~ 02 h 26, heure locale ; corrigé : le commit 4832184 est de 02 h 26 min 05 s)

Juge : l'épreuve indépendante (§ 8 de decisions/ARCHITECTURE.md). Programme construit depuis un clone
propre (commit 527dff5) dans `~/dev/cibles/troncons-epreuve`, par `construire.bat`.

## Séance de vitesse et de mémoire (`pilote_epreuve.py`)
Ordre déclaré : D120 T120 L120 L120t10 L120t10 L120 T120 D120 T20 T20 T120tiede1 T120.
- T120 : `troncons mesurer` 120b, invite wikitext (SHA-256 eadbe87e…), 256 jetons, A0, `--flux`
  (préremplissage J1+ ; la génération est la boucle de pas de J1, inchangée).
- L120 : llama.cpp `fit`, commande de `mesures/base-gpt-oss/120b/120b-fit-1.json` telle quelle
  (`-t 6 -c 2048 -lv 4`). L120t10 : la même à 10 fils (§ 8.4 : une autre configuration choisie par le
  juge ; raison : sous mmap, chaque fil en faute de page est une lecture en vol ; plus de fils, plus de
  profondeur de file sur le disque).
- D120 : `troncons disque`, 1 500 tronçons tirés (graine 20261016), profondeur 4.

Seuils :
- **Reproduction** (§ 8.3) : une différence avec un journal d'un lot n'est réelle que si elle dépasse
  2 × le plus grand des deux bruits et 3 % (06 § 7.5). Repères : génération 120b 2,179 / 2,182 j/s
  (lot O, séance s2, avec flux), 2,186 / 2,182 (s1) ; llama.cpp `fit` 0,568 (0,50 – 0,63).
- **C5** : génération T120 ≥ 0,8 × plancher en série recalculé dans MA séance par la formule du lot
  O (REPRISE-O, O4) avec mes D120 (médiane), les octets lus par jeton et les temps de carte du
  journal ; repère publié 1,505.
- **C7** : pointe de l'ensemble de travail tenue par le système (poignée lue après la sortie) de T120
  ≤ 1,9 Go. Écart T120 − T20 jugé par la borne déclarée du § 7.1 (2 × bruit + 0,5 Mo), bruit = le
  plus grand écart entre deux passes d'un même modèle dans ma séance.
- **Perte de la machine** (mesure neuve, publiée, non jugée par le § 7) : repos médian moins minimum
  de la mémoire physique disponible pendant la passe. Constat si, pour T120, elle dépasse 2 × la
  pointe de l'ensemble de travail + 200 Mo (200 Mo : l'ordre du bruit de la mémoire disponible
  d'une machine partagée, à vérifier sur les passes elles-mêmes).
- **C10** : VRAM de pointe (mon échantillonnage, 250 ms) ≤ 7 279 Mio.
- **§ 8.5** : pointe(T120tiede1) − pointe(T120 voisin) dans [0,9 ; 1,1] × 1 Gio (1 073,7 Mo) ; sinon
  l'instrument ne voit pas la fenêtre, ou le cache tiède n'est pas tenu.
- **§ 8.4 et C6** : L120t10 contre L120 par la règle de 06 § 7.5 ; C6 tient si T120 dépasse la
  meilleure des deux de plus de 2 × le plus grand bruit et 3 %.
- **Textes** : T120 = empreinte e4c6dbacb63a… (lot O) ; les deux T20 égaux entre eux et au Y20 du lot
  O ; L120 égal à 45a1f638… (base).

## C3 et C11 sur le 120b (après la séance)
`troncons evaluer --flux` sur les 10 fenêtres de `ref-openai-20b.kld`, `.trc` codé puis brut.
Seuil : 0 empreinte de logits différente sur 5 120 pas ; les deux `.kld` égaux octet pour octet.
En plus (personne ne l'a mesuré) : mes `.kld` par flux égaux octet pour octet à ceux du lot O par
boucle de pas (témoin F du lot O sur le 120b, et reproduction d'une construction à l'autre).

## Le premier jeton de C12 (déclaré le 2026-10-16 à ~~05 h 50~~ 05 h 31 (commit 549b38b de 05 h 31 min 09 s), avant la passe)
Constat : à la position 707 de l'invite du 120b, la vérité f64 donne l'argmax 1008 (log p = −1,46),
troncons 313 (log p vrai = −10,03), avec 20 couches sur 36 au routage différent. Expérience : la même
passe numpy f64, le cache KV arrondi en f16 (k après RoPE, v), seule imitation.
- argmax(707) = 313 : le cache KV en f16 (couture N) suffit à produire la cascade ;
- argmax(707) = 1008 : la cause est ailleurs (autres approximations du moteur, ou un défaut) ;
- autre : publié tel quel.
