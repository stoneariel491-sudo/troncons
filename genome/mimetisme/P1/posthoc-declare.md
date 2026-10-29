# P1, analyses post hoc : déclarées avant d'être lancées

Écrit le 2026-10-27, après le jugement principal (verdict mécanique au seuil déclaré : voir `resultat.md`) et
avant le calcul ci-dessous. **Rien de ce fichier ne change le verdict du protocole c861e8f.** Il répond à une
question que le jugement a fait naître.

## Pourquoi

Le jugement principal rend `tombe` (prose-en en génération : d = −0,0176), mais les deux traces de génération
du 120b sont des **boucles du décodage glouton** dans leur seconde moitié (le journal `mesures/epreuve-J1.md` § 6
le dit déjà de la sortie du moteur) : prose-en finit sur un ou deux jetons répétés (2 jetons distincts par bloc de
32 dès le jeton 128), wiki sur « Here is a summary » (4 à 5 jetons distincts par bloc sur les 100 derniers). Avec 326
emplacements (2,26 jetons de 144 accès), une boucle de période 1 à 2 tient entièrement dans le LRU (succès 0,97 à
1,00) et une boucle de période 5 à 10 est la pathologie classique du LRU sur un balayage cyclique. Les deux écarts
mesurés sont donc deux effets de boucle de signes opposés, pas une mesure de la mémoire du cache sur un texte qui
avance. La question que le protocole voulait trancher (« le gain de l'LFU à demi-vie existe-t-il en génération
de texte ? ») reste donc posée.

## L'analyse A : fenêtres froides de 256 jetons sur des textes cohérents (120b)

- Données : les cinq traces de **lecture** du 120b (texte réel, imposé, sans boucle), découpées en fenêtres
  disjointes de 256 jetons (code 9, dialogue 11, prose-en 9, prose-fr 11, wiki 2 : 42 fenêtres), **cache vide au
  début de chaque fenêtre**. C'est le régime « 256 jetons à froid » du jugement, sur un texte qui avance. Limite
  dite d'avance : le texte est imposé, pas produit par le modèle, et le routage de lecture est celui du traceur.
- Politiques : LRU et LFU(h), h ∈ {8, 32, 64, 128, ∞} ; capacités 326 (principale) et 922.
- Choix de h* : pour les fenêtres du genre g, le h qui maximise l'écart moyen sur les fenêtres des **autres genres**.
- Grandeur : écart par fenêtre d_i = succès LFU(h*) − succès LRU ; moyenne d̄ ; σ = écart-type des fenêtres / √n ;
  z = d̄/σ.
- **Seuil, repris du protocole** : succès si d̄ ≥ +0,02 et z > 2 à 326 emplacements ; mort si d̄ < +0,005 ;
  ouvert entre les deux. Il est de plus **exigé que l'écart moyen par genre soit ≥ +0,02 pour au moins 3 genres sur 5**
  (sinon le gain est celui d'un genre, pas d'une règle).
- Cassure : décroissance inversée (h = 8) sur les mêmes fenêtres doit tomber sous le LRU de plus de 0,02.

## L'analyse B : les traces de génération du 20b (descriptive)

Le 20b a cinq générations, dont quatre sans boucle visible (code, dialogue, prose-fr, wiki : 24 à 31 jetons distincts
par bloc de 32 ; prose-en boucle comme celles du 120b). Les capacités déclarées au protocole pour le 20b (54 et 154) ont
été mal choisies : **54 est plus petit que les 96 accès d'un seul jeton** (24 couches × 4), le LRU y vaut exactement 0 sur
les cinq générations et rien n'y est mesurable. Capacités ajoutées **post hoc**, à travail égal en jetons que le 120b à 326
(2,26 jetons) : 217 (≈ 2,26 × 96) et 307 (≈ 3,2 jetons). Sans verdict : on rapporte d, σ, z par génération, avec le h* de
la validation croisée sur les lectures des autres genres.

## L'analyse B2 (ajoutée après avoir vu B, avant son calcul) : fenêtres froides du 20b

B montre, sur les générations saines du 20b à 217 emplacements, un écart moyen proche de 0 (−0,0015 ; +0,0015 ; +0,052 ; −0,030),
alors que A donne +0,094 sur le 120b. Pour séparer « modèle » de « génération contre lecture », on refait A sur le 20b :
mêmes fenêtres froides de 256 jetons des cinq lectures du 20b, capacités 217 et 307, même choix de h* par genres tenus à l'écart,
même cassure. Pas de seuil nouveau : on rapporte d̄, σ, z et le nombre de genres au-dessus de +0,02 ; l'étiquette de A (tient /
ouvert / tombe) est donnée par la même règle, à titre indicatif.
