"""Calcul jouet (pas une mesure sur le modèle) : lissage de Maslov d'une décision à seuil.

Une décision dure « garder l'expert 4 si sa marge m > 0 » reçoit un bruit gaussien de marge delta ~ N(0, 1)
(unité : l'écart-type du bruit). Le résultat exact est la décision dure sur la marge propre m. La version lissée
mélange les deux experts avec le poids a = clip(1/2 + (m + delta)/(2 w), 0, 1) (rampe de largeur w).
Erreur quadratique moyenne par rapport au résultat dur exact, intégrée sur la marge m (densité plate près de 0) :
  dur  : integrale de P(signe(m + delta) != signe(m)) dm = E|delta| = 0,798
  lisse: integrale de E[(a - 1[m > 0])^2] dm
Rend le rapport lisse/dur pour plusieurs w. Le saut J de la sortie est supposé égal des deux côtés."""
import json, sys
import numpy as np
rng = np.random.default_rng(20261026)
d = rng.normal(size=60000)
ms = np.linspace(-12, 12, 721)
dm = ms[1] - ms[0]
dur = sum(np.mean(((m + d) > 0) != (m > 0)) for m in ms) * dm
res = {"dur": float(dur), "attendu_E_abs_delta": float(np.mean(np.abs(d))), "rapports": {}}
for w in (0.25, 0.5, 1, 2, 3, 4):
    tot = sum(np.mean((np.clip(0.5 + (m + d) / (2 * w), 0, 1) - (1.0 if m > 0 else 0.0)) ** 2) for m in ms) * dm
    res["rapports"][str(w)] = float(tot / dur)
print(json.dumps(res, indent=1))
json.dump(res, open(sys.argv[1], "w"), indent=1)
