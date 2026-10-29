# Seuils et témoins déclarés avant toute mesure (2026-10-15, 01:35)

Écrit et commité avant le premier lancement du banc. Toute mesure se lit contre ces règles ;
aucune ne se règle après coup.

## Plafonds physiques (calculés, d'après les caractéristiques nommées)
- Lien NVMe : PCIe 4.0 ×4 = 4 × 16 GT/s × 128/130 / 8 = **7,877 Go/s**. Une lecture sans tampon
  qui le dépasse prouve une lecture servie par un cache : l'instrument tombe.
- RAM : un seul module DDR5 relevé (Micron MTC8C1084S1SC56BD1, 16 Gio, « Controller0-ChannelA-DIMM0 »,
  configuré à 5 200 MT/s). Un module DDR5 = deux sous-canaux de 32 bits = 64 bits :
  5 200e6 × 8 o = **41,6 Go/s**. Toute lecture de RAM sur un tampon ≥ 10 × L3 (24 Mio) au-dessus de ce
  plafond fait tomber l'instrument.
- PCIe de la carte : 4.0 ×8 = **15,754 Go/s** (même calcul, 8 voies).
- VRAM : GDDR6 16 Gbit/s (horloge mémoire 8 001 MHz relevée par nvidia-smi, débit double) sur 128 bits
  = **256 Go/s**. Copie carte → carte comptée lecture + écriture. Valable seulement pour des tampons
  plus grands que le cache L2 (32 Mio au plus sur AD107) ; en dessous, le dépassement est attendu et
  sert de témoin positif du cache.

## Témoins
- Disque, contenu : chaque page de 4 Kio porte son numéro ; `pages_fausses` doit valoir 0 et
  `erreurs` 0. Avec `--fausser`, `pages_fausses` doit valoir `pages_verifiees` (sinon l'instrument ne
  vérifie rien).
- ~~Disque, cache : le moteur `tampon` (cache de Windows actif) relu sur une région de 1 Gio doit dépasser
  7,877 Go/s : preuve que le cache est visible quand il joue, donc absent quand il ne joue pas.~~
  **Barré à 02:05, avant le balayage complet.** L'essai du pilote (journal d'essai hors dépôt) a donné
  3,1 Go/s pour la relecture en cache, avec 2,98 s de processeur pour 3 s de fenêtre : la copie depuis
  le cache de Windows est bornée par un fil de processeur, pas par la RAM. La prémisse « le cache dépasse
  le lien » était fausse. Remplacé par le témoin au compteur ci-dessous, plus fort.
- Disque, cache (remplaçant) : à la seconde relecture en cache, le disque (compteur du système) doit
  avoir lu moins de 10 % des octets livrés par l'outil.
- Disque, second chemin : compteur cumulé du système (`Win32_PerfRawData_PerfDisk_PhysicalDisk`,
  `_Total`, `DiskReadBytesPersec`, relevé toutes les 0,5 s ; typeperf refuse les noms anglais sur ce
  Windows français). Sans tampon, le disque doit avoir vu au moins 90 % des octets de l'outil ; le
  surplus chiffre la charge des autres agents. Occupation du processeur relevée de même
  (`Win32_PerfRawData_PerfOS_Processor`).
- RAM : la somme lue doit égaler la somme connue du motif ; `--fausser` change l'attendu et doit
  faire échouer.
- Carte : aller-retour hôte → carte → carte → hôte octet pour octet ; GEMV comparé à un calcul de
  référence sur le processeur (écart relatif ≤ 1e-3 sur 64 lignes) ; `--fausser` perturbe la référence
  et doit échouer.

## Bruit et décision
- Chaque comparaison A/B se mesure en séries ABBA (A1 B1 B2 A2), répétées au moins deux fois.
- Bruit d'un programme à lui-même : |A1 − A2| / moyenne(A).
- Une différence entre A et B est déclarée réelle seulement si |A − B| / moyenne ≥ 2 × le plus grand
  des deux bruits, et ≥ 3 %.
- Thermique : bridage déclaré si le débit moyen des 30 dernières secondes tombe sous 95 % de celui des
  30 premières (5 %, soit plus du double du bruit attendu d'une GEMV répétée ; à confirmer par le bruit
  mesuré, et alors je le dirai).

## Biais connu et dit d'avance
D'autres agents travaillent sur la même machine pendant ces mesures (llama-imatrix, scripts Python ;
1,7 Gio de RAM libre relevés à 01:20). Chaque passe journalise la charge (compteurs disque, nvidia-smi).
Les chiffres sont des planchers de ce que la machine donne au repos.
