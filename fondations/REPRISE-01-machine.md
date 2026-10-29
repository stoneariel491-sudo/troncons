# Reprise : étude 01, la machine mesurée (le banc de chaque étage)

Livrable : `fondations/01-machine.md`. Outils : `outils/banc/` (Rust, crate `banc` ; pilotes Python).
Journaux : `fondations/journaux/01-machine/` (sous-dossier `secteur/` pour la suite sur secteur).
Cible de compilation hors dépôt : `CARGO_TARGET_DIR=~/dev/essais/troncons/banc/target`.
Fichier de test disque : `~/dev/essais/troncons/banc/test.bin` (32 Gio). La suite secteur
l'efface à sa fin ; sinon l'effacer à la main avant de rendre.

## Plan
1. Disque : FAIT (balayage ABBA 188 passes, IOCP = IoRing, BypassIO refusé par BitLocker).
2. Capacités : FAIT (IoRing v4, DirectStorage NuGet 1.3.0 = 2 816 824 o, non téléchargé).
3. RAM : mesure 1 inutilisable (charge), mesure batterie faite (verrou + témoin des fautes) ; SECTEUR À FAIRE.
4. Carte : FAIT (DMA 12,2, VRAM 251,3, GEMV f16 250, q4b 122, zéro copie 11,75, ALU).
5. Thermique : passe 1 (secteur, chargée) sans bridage ; passe 2 = régime BATTERIE (52,6 W, mémoire 6 GHz).
6. llama.cpp : 3/12 au premier passage (contaminés) ; SECTEUR À FAIRE (suite_secteur.py).
7. Toit : FAIT (toit.py, CSV) ; BitLocker : XTS-AES CNG mesuré (aes_xts.py).

## 2026-10-15
- 01:13-03:40 : prédécesseur (disque, carte, thermique 1, llama 3/12), mort à 03:40.
- 07:24 : reprise. GPU calme, mais llama-quantize d'un autre agent (4,3 Go) ; RAM libre 1,1 Go.
- 07:25 : thermique 2 → la machine est SUR BATTERIE (Win32_Battery = 1, 62 %) : plafond carte 52,6 W,
  mémoire carte 6 001 MHz (P4), PCIe Gen 3, processeur ~1,5 GHz. Mesures courtes du régime batterie.
- RAM : latence 1 µs même verrouillée et sans faute de page → pas la pagination ; VBS/HVCI actif
  (DeviceGuard 2) = pagination imbriquée, hypothèse non prouvée. À refaire sur secteur.
- AES-XTS-128 (CNG) sur batterie : 3,2-4,2 Go/s 1 fil, 8,7 Go/s 8 fils. Témoins IEEE 1619 et aller-retour, tombent avec --fausser.
- Batterie tombe ~1 %/min (39 % à 07:50) : pas de longue charge de ma part.
- suite_secteur.py lancée en arrière-plan : attend 120 s de secteur puis disque, AES, RAM, carte, llama 9B, gpt-oss-20b, thermique.
- 08:00-08:25 : § 2.7 (BitLocker), 3, 5.4, 5.5, 6, 7 (proposition 1, corollaires 2-3, architectures A/B),
  8-11 écrits et commités ; bib `memoire/sources/01-machine.bib` ; CSV des figures.
- 08:25 : toujours sur batterie (28 %). Suite secteur arrêtée (elle ne survit pas à la fin de l'agent).
  test.bin EFFACÉ (320 Go libres). La suite le refait seule (`disque preparer`, ~5 min) si absent.
- RESTE (pour qui reprend, machine BRANCHÉE) :
  `python -I -X utf8 outils/banc/suite_secteur.py --sortie fondations/journaux/01-machine/secteur`
  puis porter dans 01-machine.md : § 3 (RAM secteur), § 6.2 (ABBA llama 9B, gpt-oss-20b), § 5.4
  (thermique llama), et `debits-mesures.json` champ `ram`. Effacer test.bin à la fin (la suite le fait).
