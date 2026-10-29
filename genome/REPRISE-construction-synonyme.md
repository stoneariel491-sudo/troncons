# Reprise, construction lot B « génome synonyme » (rôle synonyme)

Livrable : genome/07-genome-synonyme.md. Journaux : mesures/genome/construction/synonyme/.
Seuils : mesures/genome/construction/synonyme/00-seuils-declares.md (déclarés avant).
Outils : outils/genome/synonyme/. Cible cargo : ~/dev/cibles/troncons-synonyme.
Données lourdes (hors dépôt) : ~/dev/essais/troncons/genome/synonyme/.

## Reprise du 2026-10-21 / 22 : FINI (tous les pas du lot B sont faits et commités)

- [x] Codage λ = 0 des 768 (1f0b2d0). KL λ = 0 à 768 : 0,1318 ; B2 : λ = 0 meilleure de justesse (8238f6f).
- [x] Compagnon λ = 0 : 2,6717 bits, 8,31 Go, S3-T1 + cassure ; moteur 0,1313 ; S3-K 0,0038 (tient).
- [x] Vitesse s2 20b (machine calme) : ×1,24 annoncé ; octets par pas égaux (cause ouverte, 07 § 4.4).
- [x] 120b-T2 : 56 671 experts vérifiés, 0 erreur. Proxy : validé sur le 20b (≤ 0,002), 120b 0,1404.
- [x] 120b-V : ×2,00 annoncé (octets par pas ×0,656).
- [x] 07 complet (§ 0, 4.2 quater, 4.3, 4.4, 5, 6, 7, 8) ; note mémoire (F-S7, F-S8, CSV variantes-768).
- Reste (07 § 8) : synonyme du 120b (capture f64 + codeur carte), cause du gain du 20b (cache vidé, texte
  imposé), seconde série de fenêtres pour B2, queue (garde tropicale), juge.
- Données lourdes à garder : trc/gpt-oss-20b-synonyme-l0.rapide.trc (8,3 Go), synonyme.rapide (8,1),
  120b-frontiere.rapide (40,5) ; kl/*.kld (≈ 1 Go chacun, dont moteur-exact-20b/120b, rapide-frontiere-120b).

## État (2026-10-17)

- Lu : SOCLE, 05-synthese (cahier B), 01-eclaireur, synonyme.py, capture/main.rs, juge comparer.
- Arbre trouvé sale (pas à moi) : mesures/genome/genome/kl/*10* = passe K10 de l'équipe genome, non
  commitée par elle. Laissé tel quel.
- W1 tenu : ecrire-sym λ=0 δ=1 L00-E00 = fichier de l'éclaireur octet pour octet (54 s l'expert,
  machine libre).
- Coût : ≈ 54 s par expert en Python (3 matrices) → 768 experts ≈ 11,5 h sur un processus.
  Lancé en 3 processus parallèles (couches 0-7, 8-15, 16-23), OPENBLAS 4 fils chacun.

## Fait (commits)

- 78ce4ed seuils S1/S2 ; W1 tenu (octets égaux, sha256 9079dcf1…), cassure δ=0,99 : 117 501 symboles
  différents (codage/W1-reproduction.json).
- 0be464a gemv_base + Noyaux::centres_rapides + test carte (exact au bit, cassure tombe, exact
  inchangé). verifier_sym.py (W2, débit). Témoin fourche reconstruite : 0 logit différent.
- 8c43c15 drapeau RAPIDE (bit 5, v1.2) dans trc-format + test ; trc-rapide (outils/genome/synonyme/rapide :
  coder, verifier).
- f4f7df3 troncons --rapide (Config::rapide, centres de CENTRES).
- seuils S3 déclarés (00-seuils-declares.md § S3).

## En cours (12 h 20)

- Codage λ = 0, δ* = 1 des 768 (coder_768.sh synonyme-l0 → sym/synonyme-l0-d1 ; 32 repris de
  l'éclaireur) : B2 entre les deux λ (règle déclarée dans les seuils). Puis kl_passe.sh synonyme-l0-768,
  apparier.py (a = λ=1, b = λ=0) ; si λ=0 meilleure : trc-rapide coder λ=0 + verifier + evaluer_moteur.
- Compagnon frontière 120b (frontiere-directe, 4 fils) : ≈ 150 s par couche × 36.
- Vitesse s1 (20b, ABBA) : sous charge (B0, débit, 120b) → à refaire en s2 machine calme.
- Ensuite : 120b verifier (frontiere-directe, binaire de cibles/troncons-synonyme-2), témoin, ABBA
  120b, evaluer exact 20b et 120b (proxy KL moteur exact ‖ rapide).

## Résultats acquis (tous commités)

- KL 768 : synonyme λ=1 0,1522 contre frontière 0,2640 ; appariée −0,1118 ± 0,0296 (3,8 σ) ;
  premier 67,5 % contre 47,8 % ; PPL 466,5 (réf 460,2). Moteur rapide 0,1522 ; S3-K tient.
- B0 (P1, 32 experts) : λ=1 égale à la frontière (−0,0010 ± 0,0022), pire que λ=0 (+0,0088 ± 0,0032).
- Débit 72 tenseurs : H0 2,5683 contre 2,6413 ; compagnon réel 2,5861 contre 2,6593 bits.
- W1, W2 tiennent ; compagnons vérifiés (S3-T1) ; témoin moteur 0 erreur ; repère Q2_0 KL 1,597.

## Acquis depuis

- Repère llama.cpp Q2_0 (2,25 bits) : KL 1,597, premier choix 13,6 %, PPL 881 (repere/).
- Compagnon frontière : 2,6593 bits utiles, 8,29 Go ; S3-T1 tient + cassure ; moteur --temoin :
  5 856 experts vérifiés, 0 erreur ; refus croisés tiennent (rapide/).
- KL frontière-768 réf. f64 : 0,2640 ± 0,0066, premier 47,8 % ; moteur rapide frontière 0,2626 ;
  S3-K tient (0,00207 ; 98,5 %). Témoin « 768 substitués » barré (compteur = chargements : 732/732).

## Reste

- W2 (verifier_sym.py verifier, + --casser) quand L23 E0/8/16/24 existent.
- Débit H0/Hκ des 72 tenseurs (verifier_sym.py debit --dossier synonyme-l1-d1 --dossier2 frontiere).
- KL synonyme-768 (kl_passe.sh synonyme-768 …/synonyme-l1-d1) ; apparier.py frontière contre synonyme.
- trc-rapide coder synonyme ; verifier (+ cassure) ; evaluer_moteur.sh synonyme ; S3-K (juge kl
  base = kld capture, test = kld moteur ; cassure frontière contre synonyme) ; vitesse :
  python -I -X utf8 outils/genome/synonyme/pilote_vitesse.py --seance s1 --rapide <synonyme.rapide.trc>.
- 07-genome-synonyme.md ; note mémoire § résultats ; CSV.
- 120b : pas de captures de calibration (passe f64 du 120b hors budget) → dit dans 07.

## Disque (13 h 20) : C: à 11 Go libres, nettoyé à 33 Go

Retirés (mes fichiers, régénérables, mesures faites et empreintes journalisées) :
gpt-oss-20b-frontiere-directe.rapide.trc (témoin, identique au suivant), gpt-oss-20b-frontiere.rapide.trc
(trc-rapide coder --symboles sym/frontiere, 6 min), gpt-oss-20b-experts-q2_0.gguf (llama-quantize,
repere_llama.sh, 10 min). Restent : sym/ (21 Go), trc/ (synonyme 20b 8,1 Go, frontière 120b 40,5 Go),
kl/ (4,8 Go). Le lot A écrit aussi sur C:.

## Pièges

- Python isolé : -I -X utf8. OPENBLAS_NUM_THREADS=4 (comme l'éclaireur : reproduction au bit).
- verrou de la carte : ~/dev/verrou-carte.txt (fichier ; attendre s'il existe et a < 2 h).
- ecrire-sym saute un fichier déjà écrit : relancer la même commande reprend.
