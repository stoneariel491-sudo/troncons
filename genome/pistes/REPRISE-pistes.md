# Reprise du flux des pistes (mis en pause le 2026-10-22 vers 13 h 55)

Pause demandée par Stone le 2026-10-22 vers 13 h 50, ses mots : « Met une pause temporaire à tout » puis « Toutes sections confondues ». Rien n'est abandonné.

Flux : `troncons-pistes`, run `<session>`. Pour reprendre :

```
Workflow({scriptPath: "<session>\workflows\scripts\troncons-pistes-<session>.js", resumeFromRunId: "<session>"})
```

La piste tropicale et son juge sont en cache. Seul l'agent de la piste des spectres repartira : il doit lire `genome/pistes/spectres/REPRISE.md` d'abord.

## État de chaque piste
- **Garde tropicale** : finie et jugée (`genome/pistes/tropicale/garde-tropicale.md`, `JUGEMENT.md`). Elle tombe au seuil déclaré : 57,1 % des bascules pour 10 % des cellules. La garde des racines de cascade (85,2 % pour 10 %) reste à mesurer (mesure G2, décrite dans le livrable).
- **Spectres et fractale** : verdict écrit (0/48 loi de puissance, 9/48 compatibles, second chemin égal) ; levier mesuré nul (L1 0,0009, L2 0,0036, L3d 0,0007 bit par poids). À la pause, en cours : le plafond au-delà des échelles de rangée (§ 7 nonies ; journaux `mesures/pistes/spectres/plafond-rangee*`) ; en file : le test de prédiction déclaré sur un échantillon neuf (§ 7 octies). Le juge de la piste n'a pas commencé.

## Machine à la pause
Aucun processus Python des pistes ne tourne plus.
