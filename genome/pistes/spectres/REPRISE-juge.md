# REPRISE du juge de la piste spectres

Style télégraphique. Mis à jour au fil.

- 2026-10-27 00:50 : seuils du juge déclarés et commités (a52beeb, `juge-seuil.md`).
- 00:48 : passe sans répliques (`juge_csn.py --sans-repliques`) : J1, J3, J4 tiennent (2ca319b).
- 00:49 : cassure + passe complète lancées, en pause sur ABBA (verrous successifs : placement p7, juge j10).
- 01:20 : balayage de λ_min vectorisé par blocs (résultat identique au bit sur les 141 lignes de la passe
  rapide, vérifié) ; priorité passée de « inactive » à « sous la normale » (consigne), 1 fil.
  Les deux premières passes avec répliques, coupées par moi (mes propres processus), n'ont rien rendu.
- `juge_npz.py` écrit (SHA + SVD de L00.down.E24 et L23.attn_q contre le npz) : à lancer verrou libre.
- 01:43 cassure finie (les deux témoins tombent) ; juge_npz : SHA égales, SVD à 1,5e-14 (e20651e).
- 02:27 passe complète finie : J2 tient (9/48, accord 48/48), témoins tiennent. JUGEMENT.md écrit et commité.
- Fait. Ce qui reste est pour le rôle de recherche (corrections listées au § 4 de JUGEMENT.md).
- ~~Reste : J2~~ (compatibles) et témoins quand la passe complète finit ; `comparer.py juge-csn.csv` ;
  `juge_npz.py` ; remplir `JUGEMENT.md` (balises VERDICT et SUITE) ; commit ciblé.
