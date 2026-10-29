# L'épreuve indépendante de J1 : ce qu'elle apporte au mémoire (Tome II)

Rapport : `mesures/epreuve-J1.md`. Données : `mesures/moteur/epreuve-J1/csv/` et `journaux/`. Sources :
`memoire/sources/moteur-epreuve-J1.bib`.

## Chapitre proposé : « L'épreuve indépendante » (EN : *The independent trial*)

D'où l'on part : J1 déclaré tenu par les lots, sur leurs instruments. Ce que l'épreuve établit : la
spécification décode au bit près sous un troisième implémenteur ; la référence f64 est confirmée par un
troisième calcul ; C3 tient d'une construction à l'autre ; C4 tient sur le 120b. Ce qui reste : G1, G2
et M1 (robustesse et intégrité), C7, C8, la base de C6.

## Schémas (TikZ)

- **E1, les trois chemins de la vérité** : GGUF → (a) `trc-reference` (lot R, Rust f64), (b)
  `gptoss_numpy.py` (juge, numpy f64), (c) llama.cpp ; et GGUF → `trc-codeur` → `.trc` → (d)
  troncons, (e) `decodeur_s4.py`. Sur chaque flèche, la mesure qui relie : 0,504 pas (a–b), C4
  (b–d, b–c), C1 au bit (e–GGUF), C3 (d codé – d brut).
- **E2, le décodeur vectorisé sur les tuiles** : 127 tuiles × 32 voies, 1 024 pas séquentiels ; le
  rang des renormalisations dans une tuile par somme cumulée sur les voies (`p + cumsum(besoin) − 1`).
  C'est la forme exacte de la règle « pour l = 0 à 31 dans l'ordre » du § 4.9.2.
- **E3, la pile du blocage G1** : `principal` → `drop(Moteur)` → `Arc<Interne>::drop_slow` →
  `drop(Vec<[Evenement; 2]>)` → `Evenement::drop` → `nvcuda64.dll` (100 % des échantillons).
- **E4, l'orphelin G2** : arbre des processus (pilote → troncons → nvidia-smi) et poignées héritées ;
  le parent attend la fin des tuyaux que l'orphelin tient ouverts.

## Graphes (pgfplots), depuis les CSV commités

- **G-E1** : génération (j/s) des 12 passes de la séance, dans l'ordre du palindrome, deux couleurs
  (troncons, llama.cpp `-t 6` et `-t 10`) ; `csv/s1-2026-10-16-passes.csv`.
- **G-E2** : pointe de l'ensemble de travail, mémoire engagée et perte de la machine, par passe
  (échelle logarithmique) ; même CSV.
- **G-E3** : KL par position contre la vérité numpy, troncons et llama.cpp, 20b et 120b (nuage,
  axe logarithmique) ; `csv/c4-numpy-20b-f0.csv`, `csv/c4-numpy-120b-f0.csv`.
- **G-E4** : écart maximal des log-probabilités en pas de quantification, référence contre numpy (une
  ligne à 0,5) ; `journaux/ecart-logp-20b-f0.json` (à exporter en CSV par position si le rédacteur le
  veut : `ecart_logp.py` se modifie en une ligne).

## Tableaux

Le tableau critère par critère (rapport, § 3.1) ; les cassures rejouées (§ 4) ; la base à 6 et 10
fils (§ 5) ; C8 par deux instruments (§ 3.5) ; les constats (§ 8).

## Dérivations, en entier

1. **Le décodage rANS vectorisé est le décodage du § 4.9.2.** Dans une tuile, au sous-pas k du
   macro-pas m, les voies l = 0 … 31 lisent dans l'ordre ; la voie l renormalise si y_l < L ; elle lit
   alors le mot `p + #{l' < l : y_l' < L}`. C'est `p + cumsum(besoin)_l − 1` pour une voie qui
   renormalise ; puis `p ← p + Σ_l besoin_l`. Les tuiles sont indépendantes (chacune a son
   `début[t]` et ses états). Aucune voie ne renormalise deux fois au même sous-pas : avec x ≥ L, on a
   x ≫ 12 ≥ 16, donc y ≥ 16 f ≥ 16 ; et pour y < L, (y ≪ 16) | mot ≥ 2¹⁶ = L.
2. **Borne de l'écart dû au seul format.** Un `.kld` code log q = pas · code + log q_min, avec un
   code arrondi au plus proche ; un calcul identique s'en écarte donc d'au plus pas/2 sur les jetons au-dessus du plancher,
   plus l'arrondi f32 de pas et de log q_min (≈ 10⁻⁶ relatif). Mesuré : 0,504 pas, soit pas/2 plus
   0,004 pas.
3. **La KL négative contre un fichier.** Σ_i p_i (log p_i − log q̃_i), où q̃ est la distribution lue,
   non normalisée : Σ q̃ = e^{δ}, δ mesuré à 0,0020 en moyenne. Les jetons sous le plancher reçoivent
   log q̃ = log q_min > log q. Pour un calcul identique, la KL tend vers −Σ_{i sous le plancher}
   p_i (log q_min − log p_i), qui est négative ; mesurée à −4,8·10⁻⁴.
4. **Le plancher en série de C5** (formule du lot O, recalculée) : 1 / (t_disque + t_pcie + t_dec +
   t_gemv + T0), avec t_disque = 710,12 Mo / 1,822 Go/s = 389,7 ms, t_gemv = (1,686 Go + 4 · 36 ·
   13 254 144 o) / 235 Go/s = 15,3 ms, et T0 = 3,5 ms. Passe 01 : 1/(389,7 + 79,2 + 57,0 + 15,3 + 3,5) ms
   = 1,836 j/s, seuil 0,8 × = 1,469.
5. **Le test apparié de C4** : d_i = KL_t,i − KL_l,i, d̄ ± s_d/√n ; l'appariement retire la
   variance commune des positions difficiles. Intervalles de Wilson pour les premiers choix
   (Wilson 1927).
6. **Le coût du hachage en production (M1)** : 59 défauts par jeton (15 065 / 255, 120b), soit 710 Mo
   lus par jeton. Le tronçon entier, à environ 2 Go/s par cœur [est.], coûte 0,35 s de cœur par
   jeton, parallélisable sur 1 cœur au débit du disque (1,8 Go/s). Le seul préfixe brut, 59 × 43 Ko =
   2,5 Mo, coûte environ 1,3 ms.

## Ce qui pourrait être faux

Voir le rapport, § 10. Le plus important : la passe numpy et la référence partagent la lecture du
GGUF et la lecture du modèle ; elles ne se valident l'une l'autre que sur l'arithmétique et l'ordre
des opérations, pas sur la convention.

## Ajout : le premier jeton de C12 et le cache KV en f16

- **G-E5** : accord de routage moteur / vérité par couche, 20b et 120b, positions 256 à 511 et 512
  et au-delà ; `mesures/moteur/epreuve-J1/csv/routage-par-couche-invite.csv`. Le 120b décroche avec
  la profondeur ; le 20b non.
- **E5, la cascade de la position 707** : 36 couches en colonne, une case par couche, cochée si le
  routage diffère de la vérité (20 cases à partir de la couche 12) ; à côté, la même colonne pour la
  vérité avec le KV en f16 (mêmes 20 cases) ; en bas, les deux distributions de sortie (1008 contre
  313).
- **Dérivation 7, le coût d'un KV en f32** : 18 couches pleines × 4 096 positions + 18 couches à
  fenêtre × 128, × 2 × 512 valeurs × (4 − 2) o = +156 Mo ; ÷ 13 254 144 o par emplacement = 11,7
  emplacements de moins sur 326.
