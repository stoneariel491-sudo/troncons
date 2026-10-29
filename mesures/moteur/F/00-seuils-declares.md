# Lot F : seuils déclarés avant les lancements de F2 et F3

Écrit le 2026-10-15 à 13 h 05, avant le premier codage d'un modèle réel. Chaque seuil dit la
grandeur dont il dérive. Rien ici ne se desserre après coup ; une phrase fausse se barre.

## Instrument

- `trc-codeur coder` (GGUF → `.trc`), `trc-codeur vocab` (compagnon), `trc-codeur verifier`
  (C1). Construction `cargo build --release --offline -p trc-codeur`, cible
  `~/dev/cibles/troncons-F`. Fichiers produits sous `~/dev/modeles/trc/`.
- La vérification ne fait pas confiance au codeur : elle relit le `.trc` par `trc-format`
  (`Fichier::ouvrir`, toutes empreintes), décode chaque expert par `trc-codec::decoder_partie`, et
  compare aux tranches lues dans le GGUF ; les taux sont recomptés depuis les tables de flux du
  fichier, pas depuis le journal du codeur.

## C1 (F2 sur gpt-oss-20b, F3 sur gpt-oss-120b)

| Grandeur | Seuil | D'où il vient |
|---|---|---|
| experts dont les octets reconstruits (blocs puis biais) diffèrent du GGUF | **0** sur 768 (20b), 0 sur 4 608 (120b) | sans perte par définition (§ 7.1, C1) |
| experts dont l'empreinte reconstruite, ou celle des tranches du GGUF, ou celle de la partie, diffère du répertoire | **0** | idem |
| résidents dont les octets ou l'empreinte diffèrent | **0** sur 315 (20b), 0 sur 471 (120b) | recopie |
| méta | paires du GGUF identiques octet pour octet, plus les trois paires du codeur | § 4.4 |
| SHA-256 du GGUF recalculée par le codeur, et une seconde fois par la vérification | égale à `fondations/journaux/06-modeles/telechargements.json` | second chemin de l'empreinte de téléchargement |
| **cassure** : un bit de la première médiane de la matrice 0 d'un tronçon retourné après lecture (`--casser C E`) | exactement **1** expert faux, celui-là ; ses contrôles « empreinte de partie » et « octets » tombent | § 6.5 : « une médiane faussée dans une copie → inexact détecté » ; sur le 20b, la cassure est aussi faite sur une vraie copie du fichier |

## Taux (F2, F3)

Comptabilité de l'étude 03 : original = blocs MXFP4 (17 octets pour 32 poids) ; codé = flux
MEDIANES + DELTA + CODES_CTX tels que rangés (en-têtes de flux, tuiles, états, bourrage à 16).

| Grandeur | Seuil | D'où il vient |
|---|---|---|
| 20b, les 12 tenseurs de F1 (couches 0, 8, 16, 23) : octets des flux CODES_CTX et DELTA par tenseur, tailles de tronçon (moyenne, minimum, maximum) | **identiques** à la mesure F1 : `bpp_a_ctx` de chaque tenseur et `bpp.delta` au millionième (6 décimales publiées), tronçons 11 990 368 / 11 837 440 / 12 144 640 octets exactement | même algorithme et même règle d'arrondi des tables que `decoupe-arbitre` (témoin d'identité de F1 avec le codeur de 03) : un seul octet de différence est un défaut, pas un bruit |
| 20b, tout le modèle (72 tenseurs) : r_03 | à **0,1 %** de **1,1037** | étude 03, 72 tenseurs, trois classes réassemblées ; la table par voie fait le même taux à 0,008 % près (F1, S2) et le découpage par expert ajoute moins de 0,01 % (une tuile partielle de plus par flux) ; 0,1 % = le critère du § 6.5 |
| 120b (108 tenseurs) : r_03 | à **0,1 %** de **1,1026** | étude 03, 108 tenseurs ; § 6.5 |
| taille du fichier `.trc` | à 1 % de 11,1 Go (20b) et de 57,65 Go (120b) | estimation de l'arbitre (§ 4.14), arrondie au dixième de Go : un repère, pas un critère |
| plus grand tronçon | relevé et publié | § 4.14 : « à relever par le codeur » |

## Compagnon `.vocab.gguf`

- relu par le codeur : mêmes paires octet pour octet, zéro tenseur ;
- essai (non critère, le témoin formel est au lot R) : `llama-tokenize` b11515 découpe le même
  texte en les mêmes identifiants avec le compagnon et avec le GGUF d'origine.

## Ce qui n'est pas mesuré ici

Aucun débit n'est jugé par le lot F : les durées du codeur et de la vérification sont relevées
pour information (machine partagée avec cinq lots qui compilent), pas comparées à un seuil.

## Ajout du 2026-10-15, 15 h 40 : codeur et vérification à mémoire bornée (avant F3)

Pourquoi : à 15 h 10, la machine n'avait que **336 Mo disponibles** (relevé
`Win32_PerfFormattedData_PerfOS_Memory`, 27,7 Go validés pour 15,6 Go physiques ; un `traceur`
d'un autre agent lit gpt-oss-120b et tient 8,7 Go privés). La version à une passe garde les
128 experts préparés d'une couche (≈ 1,7 Go sur le 120b, 3 × 128 × 4,4 Mo) : elle aurait fait
paginer la mesure d'un autre. La version à deux passes (comptes puis codage, par paquets de
2 × fils experts, lectures sans tampon, recopies par morceaux de 16 Mio) ne garde qu'un paquet.
Réponse par délégation du 2026-10-15, réversible : le format ne change pas d'un octet ; le prix
est une seconde lecture des experts.

| Grandeur | Seuil | D'où il vient |
|---|---|---|
| **témoin d'identité** : `gpt-oss-20b.trc` recodé par la version à deux passes (`--date 2026-10-15`) | **SHA-256 égale** à celle du fichier de F2 (deux calculs : `Get-FileHash` de PowerShell, chemin indépendant de notre code) | mêmes comptes (sommes commutatives), mêmes tables, même ordre d'écriture : un seul octet de différence est un défaut |
| cassure de l'instrument d'identité | `Get-FileHash` de la copie cassée de F2 (un octet changé) **différente** | l'instrument doit pouvoir tomber |
| lecture sans tampon (`gguf::lire_dans`) | test unitaire sur fichier connu, aligné ou non, une ou plusieurs fenêtres ; trois cassures, chacune doit faire tomber le test (`casser-lecture.log`) | SOCLE : tout témoin neuf doit pouvoir échouer |
| pointe de l'ensemble de travail, codeur et vérification, 20b (repère, pas un critère) | ≤ celle de la version à une passe (0,65 Go codeur, 1,28 Go vérification) | la version bornée ne garde qu'un paquet de 12 experts (≈ 12 × 39 Mo) au lieu d'une couche |
| **pointe 120b contre 20b**, même outil | 120b ≤ **1,25 × 20b**, codeur comme vérification | les seuls termes qui croissent avec le modèle : répertoire (4 608 × 64 o = 0,3 Mo), tables (432 × 520 o), résultats par expert (< 1 Mo), biais d'une couche (4,4 Mo contre 1,1 Mo) : < 6 Mo ; 25 % = marge déclarée pour le bruit de l'ensemble de travail (allocateur, fils), non mesurée |

## Ajout du 2026-10-15, 20 h 50 : second chemin de C1 (avant tout lancement de `second_chemin_c1.py`)

Pourquoi : la vérification de F2/F3 lit le GGUF par les mêmes fonctions que le codeur
(`gguf::lire_dans`) ; une erreur systématique de lecture (un décalage, un ordre des matrices) serait
commune aux deux et C1 tiendrait à tort (`verdicts.md`, « Ce qui pourrait être faux »). Le second
chemin ne partage **aucune ligne** avec le lot F : un outil Python (bibliothèque standard seule,
`hashlib` d'OpenSSL et non `sha2`), écrit depuis le seul § 4 d'`ARCHITECTURE.md` et la
spécification GGUF v3, sans lire `trc-format`, `trc-codec` ni le lecteur GGUF du codeur ; le
GGUF lu sans tampon (`FILE_FLAG_NO_BUFFERING` par `ctypes`, aucune page du cache du système
prise à un autre agent) ; ses décalages de tenseurs refaits une troisième fois par le lecteur
GGUF de llama.cpp lui-même (`gguf_init_from_file` de `ggml-base.dll` b11515, MIT).

Ce qu'il ne fait pas : décoder le rANS (c'est l'épreuve du § 8, réservée à un juge qui n'a pas
écrit le lot). Il ferme donc le maillon « GGUF → empreinte du répertoire » ; le maillon « tronçon
décodé → empreinte du répertoire » est celui de `verifier-120b.json` (contrôle « empreinte du
décodé ») et, par un décodeur indépendant, celui du témoin `temoin-trc` du lot K (carte).
Ensemble : décodé = GGUF lu par un chemin qui ne passe pas par `gguf::lire_dans`.

| Grandeur (20b puis 120b) | Seuil | D'où il vient |
|---|---|---|
| lecteur GGUF Python contre llama.cpp : nombre de tenseurs et de paires, version, alignement, début des données, et pour chaque tenseur nom, type, décalage, taille | **0 écart** | deux lecteurs justes d'un même format rendent les mêmes nombres |
| pavage : les tenseurs, triés par décalage, se suivent au bourrage d'alignement près ; le dernier finit à la fin du fichier | **0 trou, 0 chevauchement** | GGUF v3 : rien d'autre dans la zone de données |
| SHA-256 du GGUF entier par `hashlib`, lecture sans tampon | **= `telechargements.json` = en-tête du `.trc`** (champ 32) | témoin à réponse connue : le lecteur lit bien le fichier |
| en-tête du `.trc` (§ 4.3) : magie, version 1.0, drapeaux, tailles, L, E, k, dimensions, 32 / 17 / 39, niveaux, classes, réservés à zéro, empreinte64 | tout égal au GGUF et au § 4.3 | § 4.3 |
| MÉTA (§ 4.4) : les paires du GGUF octet pour octet, puis les trois paires du codeur, puis l'empreinte64 | identique | § 4.4 |
| TABLES (§ 4.6) : 432 (120b) ou 288 (20b) enregistrements, sommes à 4 096, empreinte64 | 0 écart | § 4.6 |
| RÉPERTOIRE (§ 4.7) : empreinte64, (couche, expert) à leur rang, alignements, niveau 1 vide en v1.0, réservés | 0 écart | § 4.7 |
| **experts : empreinte64 de l'expert d'origine refaite depuis le GGUF (§ 4.11 : blocs des matrices 0, 1, 2, puis biais) contre le répertoire** | **0 faux sur 768, puis 0 sur 4 608** | sans perte par définition (§ 7.1, C1) |
| experts : flux BIAIS_j de la partie contre la tranche de biais du GGUF, **octet pour octet** | 0 faux | § 4.10 (brut) |
| experts : flux MEDIANES_j contre `tri[B/2]` des échelles E8M0 de chaque ligne, refaites depuis le GGUF | 0 faux | § 4.10 |
| experts : empreinte64 des octets utiles de la partie contre le répertoire ; en-tête de partie, table des flux, en-têtes rANS (P, N = 256, géométrie 1, T, longueur), bourrage à zéro jusqu'à `longueur0` | 0 écart | § 4.7 à 4.9.1 |
| résidents : 471 (120b) ou 315 (20b) ; nom, type, dimensions, octets **comparés octet pour octet** au GGUF, empreinte64 | 0 faux | § 4.5 |

**Cassures** (chacune doit faire tomber exactement ce qu'elle vise et rien d'autre ; une passe
combinée par modèle, plus une passe de décalage) :
- `--casser-expert C,X` : un bit d'un octet de codes (octet 1 du bloc 0, matrice 0) retourné dans
  la tranche lue du GGUF pour (C, X) → exactement cet expert faux, au seul contrôle d'empreinte ;
- `--casser-mediane C,X` : la médiane refaite de la ligne 0, matrice 0, de (C, X) retournée →
  exactement cet expert faux, au seul contrôle MEDIANES ;
- `--casser-biais C,X` : un bit du biais de la matrice 2 lu pour (C, X) retourné → exactement cet
  expert faux, aux contrôles d'empreinte et BIAIS ;
- `--casser-parseur` : le décalage du premier tenseur du lecteur Python décalé de l'alignement →
  exactement **1** écart contre llama.cpp ;
- `--casser-sha` : un octet du premier morceau retourné dans la passe SHA-256 → SHA différente ;
- `--casser-decalage` (passe à part) : les tranches de poids prises à l'expert `(x + 1) mod E`
  → **tous** les experts des couches lues faux au contrôle d'empreinte (le contrôle voit bien
  quelle tranche il hache). Sur le 120b, cette passe se limite aux couches 0 et 1 (256 experts),
  déclaré ici : son verdict ne dépend pas du nombre de couches.

Conditions : lectures sans tampon, 4 fils, priorité sous la normale ; alimentation relevée
(`Win32_Battery.BatteryStatus`) au début et à la fin ; aucune durée n'est jugée. La passe lit tout
le disque qu'elle peut : je prends le verrou de la carte pendant les passes, pour qu'aucune mesure
de débit d'un autre lot ne coure en même temps (réponse par délégation du 2026-10-15, réversible ;
raison : une lecture de 180 Go au débit du disque fausserait la mesure d'un autre, et le verrou est
le seul signal partagé).
