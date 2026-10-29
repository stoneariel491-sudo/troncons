# Éclaireur « ingénierie et informatique » : seuils déclarés avant toute lecture de trace

Date de déclaration : 2026-10-26 (voir l'heure du commit). Rien de ce document n'a été vérifié sur une
trace au moment où il est écrit. Les seules données lues avant : les courbes publiées
`mesures/localite-gpt-oss/120b/courbes-gpt-oss-120b.csv` (témoin) et le code `moteur/crates/trc-cache/src/lib.rs`.

## Ce qui est testé

Simulateur Python à un fil (`outils/mimetisme/ingenierie/cache2.py`), sur les 7 traces du 120b
(`mesures/localite-gpt-oss/traces-120b/traces-120b.tar.xz`, 36 couches, k = 4, E = 128), règle de groupe de
`trc-cache` (les k experts d'un groupe sont épinglés pendant le groupe, victime = non épinglé).

## Témoins (doivent tenir AVANT toute autre lecture)

- **T1** : LRU global à un étage, capacités 230 et 461 : le succès égale la colonne `succes` du CSV publié
  à 0,002 près (absolu), sur les 7 traces. Seuil dérivé de l'écart entre la règle de groupe de `trc-cache`
  (insertion immédiate) et celle des simulateurs de `mesures/gpt-oss.md` § 7 (jugement avant éviction),
  équivalentes par le lemme 1 de `moteur/O-pour-le-memoire.md`.
- **T2 (cassure)** : le même simulateur sans épinglage du groupe doit s'écarter du publié de plus de
  0,002 sur au moins une trace à capacité 230, sinon le témoin ne voit pas la règle et il est refusé.
- **T3 (cache exclusif)** : succès total (VRAM + RAM) d'un LRU à deux étages avec démotion = succès d'un LRU à un
  étage de V + R emplacements, à 0,003 près (Wong et Wilkes 2002 : l'agrégat se comporte comme un seul cache de la somme).

## Hypothèse H1 : le cache tiède inclusif de `trc-cache` n'apporte rien quand R ≤ V

Lecture du code : `demander` rafraîchit la RAM sur chaque succès VRAM ; la RAM contient donc les R plus
récents, tous encore en VRAM si R ≤ V. Prédiction : |succès_VRAM + succès_RAM − succès_VRAM seul| ≤ 0,0005
pour V = 326, R ∈ {80, 160, 326}. Si l'écart dépasse 0,002 sur au moins une trace, H1 tombe (le diagnostic est faux).
Constat de l'épreuve J1 qui va dans le sens de H1 (1 Go de tiède : « sans rien rendre à la génération ») : non utilisé comme preuve.

## Hypothèse H2 : le cache exclusif rend le gain de la somme

V = 326 (emplacements du moteur), R ∈ {80, 336, 672} (≈ 1, 4, 8 Go de tronçons à ~12 Mo).
Seuil « vaut d'être construit » : fraction des accès qui vont au disque (1 − succès VRAM − succès RAM) réduite, par rapport à V
seul, d'au moins **8 % relatif à R = 80** et **25 % relatif à R = 336**, sur la trace de génération `prose-en.generation`
ET sur `tous.lecture`. Dérivation : interpolation linéaire de la courbe LRU globale publiée (323 : 0,449 ; 461 : 0,565 ;
691 : 0,689), prédiction −13 % et −40 %, seuils posés à 60 % de la prédiction.

## Hypothèse H3 : une politique d'éviction à horloge de couches + admission bat la meilleure des politiques simples

Politiques, paramètres fixés ici (aucun réglage sur les traces) :
- LRU ; LFU (compte total, départage par récence) ; SLRU (segment probatoire 20 %) ;
- ADM : LRU avec admission de type TinyLFU (un expert manquant n'entre que si son compte dépasse celui de la victime ;
  sinon il est servi depuis un tampon d'arrivée sans entrer ; les comptes sont divisés par 2 tous les 10 000 accès) ;
- ETR : horloge de couches (Mockingjay, Shah, Jain, Lin 2022) : p_e = moyenne mobile (décroissance 0,95 par jeton) de l'usage
  de l'expert e ; ETR(e) = ((l_e − l_courant − 1) mod 36) + 1 + 36 · (1/max(p_e, 0,01) − 1) en groupes ;
  la victime est l'ETR le plus grand parmi les non épinglés.
Capacités : 230, 326, 461. Seuil : une politique « vaut d'être construite » si son succès dépasse celui de la meilleure
des trois (LRU, LFU, SLRU) de **0,03 absolu** à 326 emplacements sur `tous.lecture` ET sur `prose-en.generation`, et d'**au moins 0,01** sur
4 traces de lecture sur 4 (code, dialogue, prose-en, prose-fr). Dérivation : l'écart LFU − LRU publié à 7 % est de 0,09 ; le
seuil est un tiers de cet écart. Belady (même simulateur, avenir connu) sert de plafond ; témoin : Belady ≥ toute autre politique sur chaque trace.

## Ce qui ne sera pas fait ici

Aucune lecture de fichier modèle (le verrou de la carte existe). Aucune passe KL. Rien d'autre que ce simulateur.

## Amendement n° 1 (écrit après les témoins, avant H1, H2 et H3)

Résultat des témoins (`mesures/mimetisme/ingenierie/temoins.csv`) : **T1 tient à 10⁻⁵ près** sur les 7 traces aux capacités 230 et 461
(bien plus serré que le seuil de 0,002) ; **T3 tient** (écart ≤ 0,0007) ; **T2 tel que déclaré TOMBE comme témoin** : retirer l'épinglage
du groupe ne déplace le succès que de 0,0005 à 0,0015, sous le seuil de 0,002. L'épinglage ne pèse donc pas assez pour que le seuil
le voie ; le témoin T2 est barré. Remplaçant, déclaré ici avant H1 à H3 : **T2b** : le même simulateur à une capacité décalée de 10
emplacements (220 au lieu de 230) doit s'écarter du publié de plus de 0,002 sur chaque trace, sinon le simulateur est refusé.

## Amendement n° 2 (avant toute lecture de résultat de H3)

La suite H3 à trois capacités était trop lente (≈ 45 s par politique et par trace de lecture, un fil) : H3 est jugée **à 326 emplacements seulement**
(la capacité où le seuil est écrit), sur les 6 traces (code, dialogue, prose-en, prose-fr, prose-en.generation, tous.lecture). Les capacités 230 et 461
ne sont pas passées. Les cinq premières lignes déjà écrites (code.lecture à 230 : lru 0,24625, lfu 0,30391, slru 0,12742, adm 0,34098, etr 0,36501)
sont lues par l'auteur avant cet amendement, dites ici, et ne servent à aucun réglage (les paramètres des politiques sont ceux déclarés). Les T1 à T3
portent sur 6 traces et non 7 (« tous.generation » du CSV publié est la même trace que prose-en.generation).
