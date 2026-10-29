# P1, juge : critères de reproduction déclarés avant d'exécuter mon chemin

Écrit le 2026-10-27, rôle « juge indépendant de P1 ». Commité avant que mon simulateur tourne sur une seule trace.

## Ce que j'ai vu avant d'écrire

Les chiffres du rôle de mesure (`resultat.md`, `juge-120b-326.json` en partie), le protocole `c861e8f`, le seuil de
`ec124f5`, et le texte des deux générations du 120b (`*.generation.txt`). Je n'ai lu ni `cache_p1.py` ni `cache2.py` :
mon simulateur est écrit depuis la spécification du protocole seule (règle de groupe, horloge = indice du jeton,
`c ← c·2^(−Δt/h) + 1`, départage par numéro d'accès, compte perdu à l'éviction).

## Chemin

`outils/mimetisme/P1/juge/juge_p1.py` : lecteur de trace écrit à neuf, cache à clé (couche, expert), tas à invalidation
paresseuse, score logarithmique `log2 c + t_dernier/h` (invariant par le facteur commun) ; LFU(∞) en compte entier exact.

## Reproduction exigée (sinon : « non reproduit = ne tient pas »)

1. h* = 32 retrouvé par ma validation croisée (moyenne des écarts sur les lectures des autres genres, 326 emplacements),
   pour les deux genres.
2. Les quatre écarts du verdict (gen prose-en −0,0176 ; gen wiki +0,1136 ; chaîne prose-en −0,0449 ; chaîne wiki +0,0981)
   retrouvés à **2e-3** absolu chacun, et le z à 0,2 près. Le signe et la décision mécanique (tombe) doivent être les mêmes.
3. LRU des deux générations à 326 : 0,7379 et 0,3944 à 1e-3.

## Témoins de mon instrument (doivent tenir) et cassures (doivent tomber)

- T1 : LFU(h = 1e-3) = mon LRU à 1e-4 sur gen prose-en.
- T2 : mon LFU(∞) sur gen prose-en à 1e-3 de 0,66268 (repère du seuil).
- C1 (cassure, l'instrument doit voir une différence) : trace synthétique, balayage cyclique de 82 jetons fictifs de
  4 experts sur une couche contre 326 emplacements (328 experts > 326) : le LRU doit rendre 0 et le LFU(∞) > 0,5.
- C2 (cassure de la décroissance) : décroissance inversée (h = 8) sous le LRU de plus de 0,02 sur gen prose-en.
- C3 (le z doit pouvoir tomber) : sur gen prose-en, permuter les blocs de 32 jetons de la trace LFU contre ceux du LRU
  ne doit pas laisser z inchangé (contrôle que le z est bien apparié par bloc).

## Sondes (descriptives, hors reproduction)

- S1, frontière de fin de message : dans gen prose-en, position du jeton `<|return|>` (fin de la réponse). Tout ce qui suit
  n'existe pas dans un moteur qui s'arrête au jeton de fin. Je rapporte LFU(32) − LRU sur la tête **avant** cette fin.
- S2, sensibilité : écart de gen prose-en pour chaque h de la grille (h* change-t-il le verdict ?).
- S3, fenêtres froides : je refais le d̄ à 326 de l'analyse A (+0,0939) sur les 42 fenêtres, à 2e-3, et le LFU(∞) (+0,0849).

## Garde

Un fil, priorité sous la normale, aucune carte, aucun fichier modèle (verrou absent au moment d'écrire, mais rien n'en est lu).
