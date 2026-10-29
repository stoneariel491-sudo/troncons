"""Calcul (pas une mesure) : gain d'octets du décodage spéculatif à brouillon d'acceptation alpha par jeton,
long de gamma jetons, de coût relatif c (octets lus par jeton du brouillon / octets d'un jeton exact),
vérification groupée de T = gamma + 1 jetons dont le coût vaut |U_T| = 4T / G(T) experts par couche (G mesuré
par m1_m2.py, moyenne des cinq traces de lecture), sans cache.
  jetons validés par cycle : (1 - alpha^(gamma+1)) / (1 - alpha)          (acceptation i.i.d., Leviathan et al.)
  octets par cycle         : 4*T/G(T) + 4*gamma*c                          (en experts par couche)
  gain                     : 4 * jetons validés / octets par cycle         (1 = pas de gain)
Aucune lecture de donnée brute : lit mesures/mimetisme/mathematiques/m1_m2.json."""
import json, os, sys
d = json.load(open(os.path.join(sys.argv[1], "m1_m2.json")))
G = {T: sum(d["M2"][n][str(T)]["G"] for n in d["M2"]) / len(d["M2"]) for T in (2, 4, 8)}
lignes = []
for alpha in (0.7, 0.9, 0.99, 1.0):
    for c in (0.0, 0.66):
        for gamma in (1, 3, 7):
            T = gamma + 1
            acc = T if alpha == 1.0 else (1 - alpha ** T) / (1 - alpha)
            octets = 4 * T / G[T] + 4 * gamma * c
            lignes.append({"alpha": alpha, "c": c, "gamma": gamma, "G": G[T], "jetons_valides": acc,
                           "gain": 4 * acc / octets})
json.dump(lignes, open(os.path.join(sys.argv[1], "plafond_speculatif.json"), "w"), indent=1)
for l in lignes:
    print(f"alpha {l['alpha']:<5} c {l['c']:<4} gamma {l['gamma']}: G(T) {l['G']:.3f} jetons/cycle {l['jetons_valides']:.2f} gain {l['gain']:.3f}")
