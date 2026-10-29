# Reprise : l'arbitre

Livrable : `decisions/ARCHITECTURE.md`. Outils : `outils/arbitre/` (verif_plafonds.py, decoupe/).
Journaux : `decisions/journaux/arbitre/`. Rien sur la carte (un autre agent mesure).

## 2026-10-15
- 11:15 lu : SOCLE, 07 en entier, partisan-A et partisan-B en entier, 01/02/03/04/06 là où il faut.
  mesures/gpt-oss.md pas commité (série 20b en cours chez l'autre agent).
- Second chemin des plafonds (verif_plafonds.py) : 7 témoins tiennent (A 6,24 ; A0 3,59 ; B1 de 07
  8,88 ; B1 complété 6,16 / 4,83 ; B3 10,89) ; cassure (b_compl = 0) fait tomber W5 seul.
  La correction du partisan B tient : le ×1,42 de 07 est à barrer.
- F1 (decoupe-arbitre, processeur seul, priorité basse, 2 fils) lancé 11:47 sur 12 tenseurs de
  gpt-oss-20b (couches 0, 8, 16, 23) : A_flux, A_ctx (table par voie), B_cond, B_mag, brut.
  Premier tenseur : découpe +0,4 % sur les codes, complément rANS −2,9 % contre brut.
- Prochain : résultats F1, puis ARCHITECTURE.md, barrer 07 et partisan-A (f*), commit.
- 12:09 F1 passe 1 (journal decoupe-gptoss20b-passe1.json) : A_ctx 3,8431 ≤ A_flux 3,8434 (S2 tient) ;
  B_cond/A_ctx 1,004145 (S1 tombe de peu) ; B_mag +0,78 % ; complément rANS = 0,970 × brut (S3) ;
  erreur base 0,042919745 = 07 (S4) ; aimantée 5,913 % (= partisan B) ; tronçon A moyen 11 990 368 o.
- Variante B_riche ajoutée (contexte : classe voisine + complément faible), seuil S1bis = S1 déclaré
  avant la passe 2. Passe 2 et cassure lancées (PowerShell, priorité Idle).
- 07 barré (×1,42, ×1,75, tableaux B1) ; partisan-A barré (f*). ARCHITECTURE.md brouillon commité,
  marqueurs ⟦F1-…⟧ à remplir après la passe 2 ; vers_csv.py écrit, à lancer.
- 12:30 passe 2 : B_riche 3,8550 b/p, rapport 1,00308 (S1bis tient) ; mêmes octets que la passe 1
  pour les variantes communes. Cassure : B_cond inexact, 130 047 voies hors de L, le reste exact.
  avec_F1 (verif_plafonds) : B1 complété 6,22, B3 11,10. CSV écrits. ARCHITECTURE.md rempli.
- Fait. Livrable commité. Reste aux autres : mesures/gpt-oss.md (h, ρ, base), puis lots F, E, K, R, O.
