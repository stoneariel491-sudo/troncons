# P5, juge indépendant : seuils déclarés avant toute lecture de capture par mes outils

Date : 2026-10-27. Rôle : juge de la piste P5 (recuit et échange de répliques sur le choix des symboles
synonymes). Je n'ai rien construit de P5. À l'heure de ce commit, j'ai lu les documents de P5
(`00-seuil-declare.md`, `resultat.md`), le code (`etape1.py`, `p5lib.py`, `synonyme.py`) et les **dates**
des journaux (git log, mtime) ; aucun outil à moi n'a ouvert un octet de `calib/` ou `eval/`, et je n'ai pas
ouvert les JSON de résultats de P5 au-delà des chiffres recopiés dans `resultat.md`.

## Mon chemin (outils/mimetisme/P5/juge/)

Écrit de zéro en numpy, sans le noyau Rust de P5, sans `p5lib.py`, sans `etape1.py` :
lecture des captures (h, routage) par mon propre lecteur ; H pondéré g² ; quantification MXFP4 des poids
synthétiques ; Babai (rétroaction colonne par colonne, signe fixé par w, ma propre factorisation) ;
descente cyclique (CD) vectorisée sur les rangées, tenue à jour de g = H r. Le seul objet repris du dépôt
est la définition de la référence (« Babai déployé » = `synonyme.py::choisir`), contre laquelle mon Babai est
vérifié symbole par symbole (J0).

## Mesures et seuils

- **J0, identité du pipeline** (mêmes poids que P5 : `default_rng(1).standard_normal((64, 2880))`) : mon
  Babai rend les mêmes symboles que `synonyme.py::choisir` sur mon H (0 différence attendue ; > 0 = mon chemin
  ou le leur est faux, dit et cherché). Mon erreur d'évaluation de Babai doit égaler celle des JSON de P5 à
  1e-6 relatif sur les 8 instances (sinon, H ou quantification diffèrent : dit).
- **J1, chiffre principal par mon chemin, mêmes poids** (δ = 1, λ = 0, 8 instances) : gain d'évaluation de CD
  contre Babai. **Reproduit** si ma médiane est à ±1,0 point de la médiane CD λ = 0 de P5 (5,1 %) et si aucune
  instance ne s'écarte de plus de 2 points. Sinon : non reproduit, donc ne tient pas.
- **J2, robustesse, poids neufs** (graine 2026, mêmes 8 instances, δ = 1, λ = 0) : la classe du verdict est
  **reproduite** si ma médiane de CD est dans [3 ; 10 [ % et si moins de 6 instances sur 8 dépassent 10 %
  (ni succès ni mort). Médiane ≥ 10 % sur ≥ 6 / 8 : P5 sous-estime. Médiane < 3 % ou négatif sur ≥ 4 : piste
  morte et le verdict « OUVERT » ne tient pas.
- **J3, addendum 3 par mon chemin** (mêmes poids, CD λ = 0) : régimes test2 (entraînement = calib, test =
  seconde moitié des positions d'évaluation) et plus (entraînement = calib + première moitié). Reproduit si la
  montée médiane du gain de CD est ≥ 2 points et monte sur ≥ 6 / 8 (leur règle), et si mon rapport
  « erreur de test de CD plus / erreur de test de Babai test2 » est à ±0,02 du 0,866 (moyenne) publié.
- **J4, nombre d'entrées** : je recompte N (calibration) par expert ; `resultat.md` donne à la fois
  « N = 762 à 1 329 » (§ 0) et 147 à 762 (§ 3) : un seul des deux est vrai, je dis lequel.
- **Phase optionnelle, PT** : si le temps le permet, un échange de répliques numpy (8 températures,
  40 balayages) sur les poids de J1 ; descriptif, il ne change pas le verdict de J1 à J3.

## Témoins capables de tomber (déclarés avant)

- **T1, zéro balayage** : CD arrêtée avant le premier balayage rend exactement Babai (gain 0, à 1e-12).
- **T2, H mélangé** : CD optimisée sous un H d'entraînement aux colonnes permutées (mêmes valeurs, mauvaises
  colonnes) : le gain d'évaluation doit tomber sous 0 % en médiane (l'instrument voit qu'on lui a pris son H).
- **T3, test inclus** : CD entraînée sur calib + test (régime « inclus ») : gain de test ≥ 20 % en médiane.
  Si T2 ne tombe pas ou si T3 ne monte pas, mon instrument ne sait rien distinguer et mes chiffres ne
  jugent rien.

## Règles

Calculs sous la normale, 2 fils (OMP/OPENBLAS/MKL = 2), pas de carte, aucune lecture de fichier modèle ;
journaux commités sous `mesures/mimetisme/P5/juge/`. Par défaut, non reproduit = ne tient pas.

## Addendum J5 (2026-10-27, après le lancement du lot J1-J4, avant tout résultat de J5 ; j'ai vu L08-E00 de J1 et la table des régimes de P5)

Le test causal de P5 (addendum 3) ajoute des entrées **qui viennent du fichier d'évaluation** (fenêtres 0-4),
voisines du test (5-9). Il confond deux causes : « plus de N » et « des données d'entraînement plus proches du
test ». Test qui sépare les deux, sans changer de source : **N seul, en retirant** des entrées de calibration.
- Régime « demi » : entraînement = première moitié des positions de calibration (N/2, même source), test = toute
  l'évaluation (fenêtres 0-9), comme le régime de base. CD et Babai, λ = 0, δ = 1, graine 1, 8 instances.
- Le mécanisme « N » est **soutenu par mon chemin** si le gain médian de CD sur l'évaluation baisse d'au moins
  2 points de « base » à « demi » et baisse sur ≥ 6 instances sur 8 ; **non soutenu** si la baisse est < 0,5 point
  ou si le gain monte ; entre les deux, non tranché. (Une baisse de l'erreur de Babai lui-même est rapportée à
  part : elle dit l'effet de N sur le déployé.)
