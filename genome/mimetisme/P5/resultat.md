# P5 : recuit et échange de répliques sur le choix des symboles synonymes (verre de spin) — résultat de l'étape 1

Rôle : expérimentateur de la piste P5 (tri : `genome/mimetisme/tri.md`). Date : 2026-10-27.
Seuils déclarés **avant** toute lecture de capture : `mesures/mimetisme/P5/00-seuil-declare.md` (commit ab92f4e) ;
trois addendums, chacun commité avant son lancement (598042a, puis deux autres). Outils : `outils/mimetisme/P5/` ;
journaux : `mesures/mimetisme/P5/`. Étiquettes : **[mes.]** mesuré ici ; **[calc.]** calculé ici ; **[mém.]** de ma mémoire.
Matière pour le mémoire (dérivations, figures) : `genome/mimetisme/P5/pour-le-memoire.md`.

---

## 0. Verdict au seuil

**La piste telle que déclarée (l'optimiseur : recuit et échange de répliques à la place du passage glouton) est OUVERTE, sous le
seuil de succès, hors de la zone de mort.** L'étape 2 (poids réels) n'est **pas lancée** : la règle déclarée ne l'autorise pas
(il fallait ≥ 10 % sur ≥ 6 instances sur 8), et le verrou de la carte existait au début de la séance (il manquait à 01 h 48,
mais ni l'autorisation de la règle ni l'accord de l'orchestrateur n'étaient là).

| Grandeur [mes.], 8 instances (couches 0, 8, 16, 23 × experts 0, 16), δ = 1, débit égal ±0,005 bit | descente cyclique | échange de répliques |
|---|---|---|
| baisse de l'erreur **d'évaluation tenue à l'écart**, médiane (seuil de succès 10 %, mort < 3 %) | **5,5 %** | **6,8 %** |
| instances sur 8 au-dessus de 10 % (succès : ≥ 6) | 0 | 1 (12,3 % à L0-E16) |
| baisse sur la calibration, médiane | 51,5 % | 54,6 % |
| baisse de l'objectif optimisé, médiane | 6,8 % | 7,8 % |

**Le mécanisme est trouvé, et il est autre que celui visé.** L'optimiseur est bon sur ce qu'on lui donne (−52 % sur la
calibration) et ce gain ne se transfère presque pas (−5,5 %) : le H de calibration a un rang ≤ N = 762 à 1 329 pour
n = 2 880 dimensions ; l'erreur d'évaluation vit pour 40 à 47 % dans le noyau de la calibration (figure
`spectre-erreur`). Le test causal (addendum 3, seuil déclaré avant) : avec 40 % d'entrées d'entraînement de plus
(calibration + fenêtres 0-4, test sur 5-9), le gain de la descente cyclique sur le test monte de +5,9 % à +7,3 %
(7 instances sur 8 en hausse, +2,6 points ; seuil « soutenu » : ≥ 2 points et ≥ 6 sur 8, **tenu**) ; l'erreur du test
de la descente entraînée avec les données en plus vaut **0,866 fois** celle du Babai déployé (médiane 0,851 ; 5 instances sur 8 sous 0,90 ;
écart de débit ≤ 0,0046 bit sur toutes). Un signal a été envoyé à la session principale pour cette seule piste.

## 1. D'où on part, où on va

**Au départ** : la mutation synonyme (Babai/GPTQ sur 8 niveaux, δ = 1, λ = 0) est le seul gain avec perte qui ait passé la KL
(−0,0098 ± 0,0033) ; son optimiseur est un seul passage glouton ; aucun recuit ni échange de répliques sur la
quantification de LLM n'avait été trouvé par l'éclaireur. Gain visé : 20 % d'erreur en moins = 0,16 bit/poids = 6 % du débit du mode rapide [hyp.].

**Ce que l'étape 1 a établi** : (1) l'instrument peut tomber et le verre de spin est réel à petite dimension ; (2) à n = 2 880 et δ = 1 le gain de l'optimiseur existe
mais se transfère à 10 % ; (3) la cause est la finitude de l'échantillon de calibration.

**Ce qui reste** : § 6.

## 2. Les témoins (tous déclarés avant d'être lancés)

| Témoin | Résultat [mes.] |
|---|---|
| W1 force brute, 10 poids × 5 niveaux, 1 000 H corrélés | Babai manque l'optimum sur **847 / 1 000** (excès médian 106 %, max ×33) : l'instrument peut tomber. PT final (3 000 balayages, 12 températures, 0,01 à 3) : **1 000 / 1 000** à l'optimum. ~~PT à 200 balayages, 8 températures : à l'optimum sur toutes~~ **échoue sur 43 / 1 000** (barré, réglage trop court, journal `temoins-passe1-200balayages.json`) |
| W1 second énumérateur (numpy, indépendant) | égal au Rust à 1e-9 sur 12 / 12 |
| W2 cassures | zéro balayage rend Babai exactement (1 000 / 1 000) ; températures gelées : optimum retrouvé sur 107 / 847 seulement ; H permuté : 2 / 847 : l'instrument tombe quand on le prive de sa chaleur ou de son H |
| W3 second chemin, décodage par sphère (Fincke-Pohst) n = 16, 10 instances, bloc réel | PT = sphère sur **10 / 10** ; Babai non optimal sur 6 / 10 (8 à 44 % au-dessus) |
| W4 Babai générique contre `synonyme.py::choisir` | 0 symbole différent sur 2 048 |
| Chiffre principal, second chemin | l'erreur d'évaluation calculée par la forme quadratique de H et recalculée sur les entrées X (Σ g² ‖(W − Ŵ)x‖²) s'accordent à 1,5·10⁻¹⁵ relatif (max sur les 8 instances) |
| Cohérence du noyau | énergie du noyau = énergie numpy à 1,3·10⁻¹⁵ |
| Étalonnage contre un chiffre publié | Babai contre frontière sur l'évaluation : ÷1,65 (L8-E0), 07 § 2 publie ÷1,57 (autre échantillon de poids, vrais poids) : même ordre |

## 3. Le chiffre principal, par instance (δ = 1, meilleur des deux λ à débit égal, gains en %)

| Instance | CD : calib / objectif / **évaluation** | PT : calib / objectif / **évaluation** |
|---|---|---|
| L0-E0 | 49,3 / 7,4 / **4,7** | 53,0 / 8,6 / **5,6** |
| L0-E16 | 42,6 / 8,4 / **8,9** | 45,7 / 9,3 / **12,3** |
| L8-E0 | 34,9 / 6,7 / **7,9** | 38,8 / 7,6 / **9,1** |
| L8-E16 | 57,8 / 6,9 / **3,8** | 62,1 / 8,1 / **2,8** |
| L16-E0 | 57,2 / 7,0 / **3,2** | 60,1 / 8,0 / **4,6** |
| L16-E16 | 67,9 / 5,3 / **1,4** | 71,4 / 6,3 / **3,0** |
| L23-E0 | 51,0 / 4,8 / **7,6** | 53,2 / 5,5 / **9,5** |
| L23-E16 | 52,1 / 4,6 / **6,2** | 56,0 / 5,2 / **7,9** |

Moyenne PT 6,9 %, écart-type entre instances 3,4 points, erreur standard 1,2 point : intervalle à 95 % ≈ [4 ; 10] %.
Les 64 rangées par instance (256 déclarées) sont dites. Les instances à peu d'entrées (L16-E16 : 147 ; L23-E16 : 239 ; L8-E16 : 300) ne sont pas
systématiquement pires que celles à beaucoup (L0-E0 : 762 donne 4,7 %) : N seul ne fait pas tout, l'instance compte.

## 4. Les autres mesures (toutes avec seuil déclaré avant)

- **Amortissement** (δ ∈ {0,1 ; 0,3 ; 1 ; 3}, `etape1/table-delta.csv`, figure `delta`) : l'erreur d'évaluation moyenne rapportée à Babai déployé
  (δ = 1) vaut, pour Babai, 1,157 / 1,040 / 1,000 / 1,044 ; pour CD 1,191 / 1,039 / 0,946 / 0,946 ; pour PT 1,196 / 1,025 / 0,935 / 0,945.
  δ = 1 est près de l'optimum de Babai, et l'optimiseur ne déplace pas le meilleur δ ; à δ ≤ 0,3 il sur-ajuste et perd contre le Babai déployé.
  ~~Le verdict par δ de `verdict-etape1.json` donne « OUVERT, 5 instances sur 8 ≥ 10 % » à δ = 3~~ : artefact (il compare à Babai au même δ,
  lui-même dégradé de 4,4 %), la règle déclarée ne se lit qu'à δ = 1 ; les lignes « MORT » à δ = 0,3 et 0,1 sont de la même
  famille (sensibilités, pas le verdict).
- **Estimateur de Gibbs** (mécanique statistique de l'apprentissage : un état tiré à T finie généralise mieux que le fondamental ; pas de seuil de
  verdict, test descriptif sur L8-E0, 32 rangées) : gain d'évaluation 8,1 / 9,0 / 8,9 / 7,9 / 4,3 / 0,3 % à T/e_b = 0 / 0,05 / 0,2 / 0,4 / 0,7 / 1,0 :
  plateau dans le bruit puis dégradation. **Pas de gain de généralisation par la chaleur.**
- **Cible diagonale de l'amortissement** (addendum 2, seuil déclaré avant : ≥ 10 % sur ≥ 6 sur 8 pour Babai seul) : Babai −2,3 % (δ = 1), −3,7 % (δ = 3), −9,7 % (δ = 0,3) ;
  CD +2,4 % / +5,4 % / −9,4 % ; 0 instance sur 8 à 10 % ; la cassure à cible permutée (−0,5 % Babai) ne se distingue pas de la vraie diagonale.
  **Fermé** : la diagonale de H ne porte pas l'information qui manque.
- **Variation de N** (addendum 3) : voir § 0 ; témoin « test inclus dans l'entraînement » : gain de test +49,6 % (≈ calibration, seuil ≥ 20 %), **tient** ; tableau par instance dans `etape1-regime/table-regime.csv`.
- **Coût** [calc., hyp.] : CD ≈ 0,1 s par rangée contre 6 ms pour Babai (07 : 54 s pour 8 640 rangées d'un expert), soit ×15 à ×30 ; PT ≈ ×15 de plus que CD (mesuré : 68 à 115 s contre 5 à 7 s pour 64 rangées, machine partagée). Sur les 768 experts du 20b, CD seul se chiffre en centaines d'heures-fil sur Python+Rust ; un codeur dédié sur la carte est le passage obligé.
- **Ce que ça rapporte** [calc., haute résolution D ∝ 2^(−2R)] : ρ = 0,935 (PT) = 0,049 bit/poids ; ρ = 0,946 (CD) = 0,040 bit ; ρ = 0,866 (CD + 40 % de données) = 0,103 bit ; contre 0,16 visés (ρ = 0,80) : de 1,5 % à 3,9 % de 2,65 bits (Babai seul avec les données en plus, 0,941 : 0,044 bit).

## 5. Ce qui pourrait être faux

- **Poids synthétiques gaussiens i.i.d.** (étape 1 : rien d'autre n'était permis sous le verrou). Les vrais poids ont des colonnes géantes corrélées au H ;
  l'écart Babai/optimum peut changer dans les deux sens. Aucun chiffre de ce document n'est un chiffre sur les vrais poids.
- **Le débit** est H0 sur 64 rangées, pas le débit du codeur réel (contexte κ) ; seul le H d'entrée de gate/up est mesuré (pas down).
- **Fuite possible dans l'addendum 3** : les fenêtres 0-4 (entraînement « plus ») et 5-9 (test) sont voisines dans wiki.test ; un thème commun
  pourrait gonfler la montée. Le témoin « inclus » mesure le cas extrême (+49,6 %), pas ce voisinage. À lever en prenant des fenêtres lointaines.
- **Le meilleur de deux λ par instance** (à débit égal) avantage un peu la méthode ; les deux λ sont dans `gains-d1.csv` (CD λ = 0 : médiane 5,1 % ; PT λ = 0, 7 instances comparables sur 8 : 5,9 %).
- **Le PT n'est pas prouvé optimal à n = 2 880** (il l'est à 10 et 16). Un meilleur optimiseur baisserait l'objectif davantage, pas l'évaluation au-delà de ce que la décomposition spectrale laisse.
- Un défaut de `etape1.py` (cache de Cholesky clé sur `id(H)`) a été trouvé et corrigé en cours de route ; W3 relancé, identique ; les 8 instances (un H par exécution) n'étaient pas concernées.
- L'étape 2, la KL et le fichier du mode rapide ne sont pas touchés : **aucune affirmation sur la qualité du texte**.

## 6. Suite possible

1. **Le levier est le nombre d'entrées de calibration, pas l'optimiseur** : le gain du CD est de 5 à 7 % à N ≈ 600-830 et monte avec N. À mesurer sans modèle : des fenêtres
   d'entraînement **lointaines** (pas de fuite) en plus des 13 de la calibration, N cible 2 à 3 fois plus grand (les 6 132 positions déjà capturées couvrent 13 fenêtres ; les fenêtres
   0-9 d'évaluation en ajoutent 5 110), puis relire le gain du CD sur des fenêtres de test tenues à l'écart. Si le gain dépasse 10 % sur ≥ 6 instances : **étape 2** (poids réels).
2. **Étape 2, cahier prêt** (`outils/mimetisme/P5/etape2.py`, **non testé** : écrit mais jamais lancé, il refuse de tourner sous le verrou) :
   `python -I -X utf8 etape2.py --couche L --expert E --lignes 256 --pt-lignes 64 --damp 1 --lams 0 0.2 --sweeps 40` pour les 8 couples ; lecture ≈ 13 Mo par expert (≈ 106 Mo au total), RAM < 1,5 Go, 2 fils ;
   durée estimée 10 à 20 min par expert avec CD sur 256 rangées et PT sur 64 (à mesurer au premier) ; sortie : erreur d'évaluation sommée sur les trois rôles (gate, up, down), gain par rangée, débit regroupé. **À lancer seulement si le point 1 passe**, et hors verrou, après accord de l'orchestrateur.
3. **Si l'on ne veut pas de nouvelle passe du modèle** : entraîner le fichier final sur calibration + évaluation (fenêtres 0-22), valider sur des fenêtres neuves (23 et au-delà), c'est-à-dire un seul réglage de plus au codeur.
4. Le **recuit** ne se justifie pas seul : +1,4 point au-dessus de CD pour ×15 de coût ; à garder pour le cas où N sera grand (le paysage y est plus dur, et c'est là que l'objectif et l'évaluation redeviennent proches).

## 7. Techniques essayées (pour `RECETTES.md`)

- **Marche** : balayage de bain thermique à une coordonnée avec vecteur H·r tenu à jour (n opérations par changement) ; échange de répliques par rangée dans un seul appel Rust (les rangées sont indépendantes, 2 fils côté Python) ; Cholesky retourné de `synonyme.py`.
- **Marche** : décodage par sphère comme second chemin exact à n = 16 ; énumération de Cholesky comme force brute exacte à n = 10.
- **Échoue** : PT court (200 balayages, 8 températures) : 4,3 % d'échecs sur le jouet ; il en faut 3 000 balayages et 12 températures de 0,01 à 3 (en unités de la trace moyenne de H).
- **Échoue** : cible diagonale de l'amortissement ; estimateur de Gibbs à T > 0 (rien au-delà du bruit) ; recuit en plus de CD (+1,4 point seulement).
- **À éviter** : cache indexé sur `id()` d'un tableau sans en garder la référence.
- **Piège de lecture** : un verdict par δ qui compare à Babai au même δ rend « 11 % » à δ = 3 ; comparer toujours au déployé.
