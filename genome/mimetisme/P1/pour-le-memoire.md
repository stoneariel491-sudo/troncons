# P1 : ce qu'il faut au mémoire (dérivations, données, figures)

Étiquettes : [mes.] mesuré (outil et journal commités) ; [calc.] dérivé ici ; [mém.] de mémoire, non relu (à vérifier avant publication).
Sources : `memoire/sources/p1.bib`. Résultat et réserves : `resultat.md`.

## 1. Le score à décroissance exponentielle comme estimateur de taux

Soit un expert x accédé aux jetons s₁ < s₂ < … Pour une demi-vie h (en jetons) on pose, au jeton t,

  c_h(t) = Σ_{sᵢ ≤ t} 2^{−(t − sᵢ)/h},    mise à jour : c ← c·2^{−Δt/h} + 1.

**Lemme 1 (espérance).** Si les accès de x forment un processus de Poisson de taux λ par jeton, E[c_h] = λ ∫₀^∞ 2^{−u/h} du = λ·h/ln 2.
Donc r̂_h = c_h · ln 2 / h est un estimateur sans biais de λ [calc.].

**Lemme 2 (variance).** Var[c_h] = λ ∫₀^∞ 4^{−u/h} du = λ·h/(2 ln 2) (propriété de Campbell pour un processus de Poisson filtré), donc
Var[r̂_h] = λ ln 2 /(2h) [calc.]. L'écart relatif √(ln 2/(2hλ)) est le prix de la mémoire courte : à λ = 0,1 par jeton et h = 8, il vaut 0,66.

**Lemme 3 (biais sous dérive).** Si λ(t) = λ₀ + λ′ t (dérive linéaire) et τ = h/ln 2 la constante de temps, alors E[r̂_h(t)] = λ(t) − λ′τ (biais de retard)
[calc. : ∫₀^∞ (λ(t) − λ′u) e^{−u/τ} du/τ]. L'erreur quadratique moyenne est EQM(τ) = λ/(2τ) + λ′²τ².

**Proposition 1 (horizon optimal).** dEQM/dτ = −λ/(2τ²) + 2λ′²τ = 0 donne τ* = (λ/(4λ′²))^{1/3} [calc.]. L'horizon optimal croît quand la dérive faiblit
et quand le taux est faible ; il n'est ni 0 (LRU) ni ∞ (LFU) tant que 0 < λ′ < ∞. La mesure place h* = 32 (τ = 46 jetons) comme meilleur choix sur les lectures
des autres genres à 326 comme à 922 emplacements (h* = 32 ou 64) [mes., `juge-120b-*.json`, champ `cv`].

## 2. Le continuum LRU – LFU

**Proposition 2.** Quand h → 0 l'ordre des scores tend vers l'ordre des derniers accès (LRU) ; quand h → ∞ vers l'ordre des comptes (LFU).
Preuve : score(x, t) = Σᵢ 2^{−(t − sᵢ)/h} = 2^{−(t − s_dernier)/h}(1 + Σ_{autres} 2^{−(s_dernier − sᵢ)/h}) ; le second facteur tend vers 1 quand h → 0, le premier ordonne
par s_dernier. Quand h → ∞ chaque terme tend vers 1. [calc.] Témoins : à h = 0,001 le succès égale celui du LRU à 0 près sur huit traces ; à h = ∞ il égale
`cache2` « lfu » à 0 près [mes., `temoins.json`]. C'est la famille LRFU (Lee et al., 2001 [mém.]).

## 3. Deux réservoirs : le mélange d'échelles

Le mélange M(w) = (1 − w) r̂₈ + w r̂₁₂₈ est la sortie d'un filtre linéaire de réponse impulsionnelle
k(u) = (1 − w)(ln 2/8) 2^{−u/8} + w (ln 2/128) 2^{−u/128}, somme de deux relaxations. C'est la structure à deux réservoirs du modèle climatique stochastique
de Hasselmann (1976 [mém.]) : un réservoir rapide suit le forçage, un réservoir lent l'intègre. Fonction de transfert : K(s) = (1−w)/(1 + 8s/ln 2) + w/(1 + 128s/ln 2),
deux pôles réels. [calc.] M(0) = LFU(8) et M(1) = LFU(128) : témoin W3, égalité à 0 près [mes.]. **Résultat négatif** : à 326 emplacements le mélange n'est
pas meilleur que le LFU(32) seul (−0,0031 / +0,1042 / −0,0657 / +0,0892 contre −0,0176 / +0,1136 / −0,0449 / +0,0981 sur les quatre cas du verdict) [mes.].

## 4. De l'échec du cache à la vitesse

Si le disque borne tout, le temps d'un jeton est proportionnel aux défauts : v ∝ 1/(1 − s). Gain de vitesse d'un cache de succès s₁ contre s₀ :
ρ = (1 − s₀)/(1 − s₁) [calc.]. Exemples [calc. sur mes.] : fenêtre froide 120b, 326 : LRU 0,35 à 0,51, d̄ = +0,094, soit ρ ≈ 1,19 pour un LRU de 0,45 ;
génération wiki : 0,3944 → 0,5080, ρ = 1,23 (en boucle, donc non transférable) ; seuil déclaré : +0,02 sur 0,2621 de défauts, ρ = 1,083.

## 5. Les trois figures (toutes tirées des données commitées par `figures_p1.py`)

1. `figures/p1-blocs-generations.png`. Haut : succès par bloc de 32 jetons des deux générations du 120b (LRU, LFU(32), LFU sans décroissance, horloge de couches). Bas : jetons
   distincts par bloc. Ce que la figure dit : dès que le nombre de jetons distincts tombe (boucle), le LRU monte à 1 (prose-en) ou s'effondre (wiki, balayage cyclique), et
   tout l'écart LFU − LRU se décide dans la boucle. Données : `mesures/mimetisme/P1/figure-blocs.csv`.
2. `figures/p1-fenetres-froides.png`. Nuage (succès LRU, succès de la politique) pour les 42 fenêtres froides de 256 jetons du 120b (326) et du 20b (217) ; la diagonale est le LRU.
   LFU(32) et LFU sans décroissance sont presque confondus : ce qui paie est la fréquence, pas la demi-vie. Données : `fenetres-{120b,20b}.csv`.
3. `figures/p1-topologie-usages.png`. **Espace latent des blocs de 32 jetons** : chaque bloc est le vecteur de ses usages d'experts (4 608 dimensions, norme 1). Haut : matrice de
   similarité cosinus (lecture puis génération) ; la génération forme un bloc séparé (cosinus 0,4 à 0,5 avec la lecture, 0,3 pour la queue en boucle). Bas : projection sur les deux premiers
   axes principaux (SVD des vecteurs centrés ; 41 % et 15 % de la variance pour wiki, 30 % et 13 % pour prose-en) ; la lecture occupe un nuage compact, la génération part sur une
   trajectoire distincte qui se resserre dans la boucle. Ce qui l'explique : un cache chauffé par la lecture contient la mauvaise région ; les comptes anciens polluent (chaîne : LFU sans
   décroissance 0,6627 → 0,1411 sur prose-en). Données : `figure-topologie.csv`.

Figure à produire pour le mémoire avec les traces saines : la même matrice cosinus, avec la demi-vie qui minimise l'erreur de rang du score (Proposition 1) tracée sur la matrice.

## 6. Données de mesure (CSV et JSON pour pgfplots)

- `mesures/mimetisme/P1/juge-120b-326.json`, `-922.json`, `juge-20b-{217,307}.json` : par cas, succès de chaque politique, d, σ, z, h*, h oracle (champs `cas`, `cv`).
- `mesures/mimetisme/P1/fenetres-{120b,20b}.csv` : une ligne par fenêtre (capacité, genre, fenêtre, h*, succès LRU et LFU, d).
- `hits-120b.npz`, `hits-20b.npz`, `hits-120b-rust.npz` : succès par jeton, pour recalculer tout σ par blocs.
- `temoins.json` : toutes les lignes de témoins.

## 7. Reproduire

```
python -I -X utf8 outils/mimetisme/P1/cache_p1.py temoins
python -I -X utf8 outils/mimetisme/P1/cache_p1.py grille 120b 326,922
python -I -X utf8 outils/mimetisme/P1/rust_p1.py 120b 326,922     # noyau-p1 : mélange + second chemin
python -I -X utf8 outils/mimetisme/P1/rust_p1.py comparer 120b
python -I -X utf8 outils/mimetisme/P1/cache_p1.py juge 120b 326
python -I -X utf8 outils/mimetisme/P1/fenetres_p1.py 120b 326,922
python -I -X utf8 outils/mimetisme/P1/figures_p1.py
```
Les traces se lisent dans `~/dev/mimetisme-P1-donnees/{t120,t20}` (extraites des archives de `mesures/localite-gpt-oss/`) ; `noyau-p1` se compile avec `cargo build --release`.

## 8. Pistes ouvertes pour une section « travaux futurs »

- Générations saines du 120b : seule mesure qui tranche P1.
- Fonte des comptes à la frontière lecture / génération (§ `resultat.md` 6.2) : une échelle de plus, déclenchée par un événement du moteur (début de génération) et non par le temps.
- Lien avec P2 (cache exclusif) : si le LFU entre dans le moteur, le score sert aussi de critère de démotion de la VRAM vers la RAM.
