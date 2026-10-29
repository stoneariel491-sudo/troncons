# Reprise du flux de construction (terminé le 2026-10-22)

## Fin du flux (2026-10-22, vers 8 h 25)
- Relancé le 2026-10-21 à 23 h 30, run `<session>` : le journal de `<session>` n'était plus sur le
  disque, le même script est reparti sans reprise, avec une phrase ajoutée à la synthèse (« rôle terminé, ne
  réécris rien »). Elle n'a rien écrit ni commité.
- Lot A fini à 0 h 51 (06 complet), lot B fini à 3 h 40 (07 complet), juge fini à 8 h 21 :
  `genome/JUGEMENT-construction.md` (commit 9948602).
- Verdict du juge : le lot A tient en entier, le génome synonyme tient hors de R1 et B2 se renforce ; deux
  graves (G1, G2) : les gains de vitesse du mode rapide ×2,00 (120b) et ×1,24 (20b) sont barrés comme gains du
  mode (×1,28 et ×0,94 contre le v1.2 du même âge) ; cinq mineurs (M1 à M5). Barres portées dans 07 par le juge.
- Ce qui reste : JUGEMENT § 11 (B3 à reprendre avec r(R/B), placement disque en 08, recettes à porter dans
  RECETTES.md, Tome III).

L'historique ci-dessous est celui de la coupure du 2026-10-17, gardé tel quel.

# (Historique) Reprise du flux de construction

Arrêté le 2026-10-17 à 13 h 47, sur la consigne de Stone.

Flux : `troncons-genome-construction`, run `<session>`. Pour reprendre :

```
Workflow({scriptPath: "<session>\workflows\scripts\troncons-genome-construction-<session>.js", resumeFromRunId: "<session>"})
```

La synthèse est en cache (fini). Les agents des lots A et B ont été coupés en cours : ils repartiront de zéro, mais leurs notes de reprise disent tout ce qui est fait. Leur consigne doit donc ajouter : « lis d'abord ta note de reprise et reprends au premier pas non coché ».

## Où en était chaque agent

**Synthèse** : fini. `genome/05-synthese.md`, note `REPRISE-construction-synthese.md`.

**Lot A, codon du zéro** (note : `REPRISE-construction-codon.md`, livrable `06-codon-v1-2.md`) :
- fait : format v1.2, codec, codeur `--canonique`, vérificateur ; 20b v1.2 (10 851 844 096 o) et 120b v1.2 (55 930 175 488 o, −1,80 Go), C1 en valeur sur tous les experts, logits égaux au bit sur les deux modèles (A-C1), A-C2 tenu ;
- J1 s1 : jetons égaux, octets par jeton 0,9671 (prédit 0,967), vitesse r = 1,11 non annoncée (σ 21,6 %) ; le témoin « copie neuve du v1.0 » est confondu (289 545 fragments) ; séance s2 déclarée avec le v1.0 recodé par le codeur modifié (identité SHA-256 tenue) ;
- reste : la séance J1 s2 (ABBA, machine calme), puis le § 8 de 06.
- **2026-10-22, fait** : séance s2 sur machine calme (aucune passe sous charge) : 2,89 contre 1,99 jetons/s
  (r = 1,454, σ = 5,6 %), jetons égaux, octets 0,9671 ; mais deux v1.0 identiques au bit diffèrent de 30 %
  à l'étage disque : le gain suit le fichier, pas le format (toit 3,4 %). 06 complet. Le lot A n'attend
  plus que le juge, et la décision de Stone sur le témoin décisif (place disque).

**Lot B, génome synonyme** (note : `REPRISE-construction-synonyme.md`, livrable `07-genome-synonyme.md`) :
- fait : KL à 768 experts, λ = 1 : 0,1522 contre 0,2640 pour la frontière (appariée −0,1118 ± 0,0296, 3,8 σ), premier choix 67,5 % contre 47,8 %, perplexité 466,5 (référence 460,2) ; compagnon 20b 2,5861 bits (8,11 Go) ; option `--rapide` du moteur ; compagnon frontière du 120b écrit (40,45 Go) et vérifié (120b-T1) ;
- en cours à l'arrêt : codage λ = 0 des 768 experts (pour la règle B2 entre les deux λ), en processus Python lancés à 12 h 14 et 12 h 29. TaskStop ne les a pas arrêtés : ils finissent seuls et écrivent sous `~/dev/essais/troncons/genome/synonyme/` et `mesures/genome/construction/synonyme/codage/` ;
- reste : KL λ = 0 à 768 et B2, vitesse s2 machine calme (s1 sous charge, non concluante), ABBA du 120b.

**Juge** : pas commencé.

## Pièges vus pendant le flux
- Disque presque plein après le compagnon du 120b : l'équipe synonyme a retiré des fichiers régénérables (voir sa note).
- Les mesures de vitesse faites pendant que l'autre lot lit le disque ne concluent pas : refaire les deux en séance calme, l'une après l'autre.
