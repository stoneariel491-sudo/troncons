"""Le codon synonyme du zéro, compté : combien de codes −0 et +0, et ce que coûte le signe d'un zéro.

Éclaireur du génome des poids (genome/01-eclaireur.md § 4). Écrit de zéro pour troncons, 2026-10-16.

Pour chaque tenseur d'experts MXFP4 demandé : n(+0) (code 0), n(−0) (code 8), H(code) et H(valeur)
à l'ordre 0 (la valeur fusionne ±0), leur écart (le coût du signe des zéros, en bits par poids),
H(signe | zéro), et les blocs dont les 32 codes sont des zéros (leur échelle E8M0 est elle aussi un
synonyme : n'importe quel exposant donne les mêmes poids). Comptes exacts, aucun échantillonnage.

Témoin (déclaré avant) : sur les 12 tenseurs de 07 (couches 0, 8, 16, 23 de gpt-oss-20b), H(code)
égale 3,860 (07) à 0,001 près ; cassure (--casser) : le code 1 compté comme un zéro, l'écart
H(code) − H(valeur) doit alors changer de plus de 0,05 bit.

Utilisation : python -I -X utf8 zero_compte.py <modele.gguf> <couches, ex. 0,8,16,23 ou tout> [--casser] > journal.json
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
import synonyme as S  # noqa: E402


def h(n):
    n = n[n > 0].astype(np.float64)
    p = n / n.sum()
    return float(-(p * np.log2(p)).sum())


def main():
    chemin, couches = sys.argv[1], sys.argv[2]
    casser = "--casser" in sys.argv
    lec = S.charger_lecteur().LecteurGGUF(chemin)
    tens = [t for t in lec.tenseurs if t.nom.endswith("_exps.weight") and t.nom_type == "MXFP4"]
    if couches != "tout":
        garde = {int(c) for c in couches.split(",")}
        tens = [t for t in tens if int(t.nom.split(".")[1]) in garde]
    t0 = time.time()
    lignes = []
    tot = np.zeros(16)
    nul_tot = 0
    blocs_tot = 0
    for t in tens:
        o = np.asarray(lec.octets(t))
        n_e = t.dims[2]
        par = o.size // n_e
        n = np.zeros(16)
        nuls = 0
        blocs = 0
        for e in range(n_e):
            b = o[e * par:(e + 1) * par].reshape(-1, 17)[:, 1:]
            c = np.concatenate([b & 15, b >> 4], axis=1)
            n += np.bincount(c.ravel(), minlength=16)
            nuls += int(((c & 7) == 0).all(axis=1).sum())
            blocs += c.shape[0]
        nv = n.copy()
        zero_codes = [0, 8] if not casser else [0, 8, 1]
        nz = nv[zero_codes].sum()
        nv = np.delete(nv, zero_codes)
        nv = np.append(nv, nz)
        hc, hv = h(n), h(nv)
        hs = h(n[[0, 8]])
        lignes.append({"tenseur": t.nom, "poids": float(n.sum()), "p_plus0": n[0] / n.sum(), "p_moins0": n[8] / n.sum(),
                       "H_code": hc, "H_valeur": hv, "cout_signe_des_zeros": hc - hv, "H_signe_sachant_zero": hs,
                       "blocs_tout_zero": nuls, "blocs": blocs})
        tot += n
        nul_tot += nuls
        blocs_tot += blocs
        print(f"{t.nom} : {hc - hv:.4f} bit, {time.time() - t0:.0f} s", file=sys.stderr, flush=True)
    nv = tot.copy()
    zc = [0, 8] if not casser else [0, 8, 1]
    nz = nv[zc].sum()
    nv = np.append(np.delete(nv, zc), nz)
    j = {"outil": "zero_compte.py", "modele": chemin, "couches": couches, "casser": casser, "tenseurs": len(tens),
         "poids": float(tot.sum()), "p_plus0": tot[0] / tot.sum(), "p_moins0": tot[8] / tot.sum(),
         "H_code": h(tot), "H_valeur": h(nv), "cout_signe_des_zeros": h(tot) - h(nv),
         "H_signe_sachant_zero": h(tot[[0, 8]]), "blocs_tout_zero": nul_tot, "blocs": blocs_tot,
         "temoin_H_code_07": abs(h(tot) - 3.860) < 1e-3 if couches == "0,8,16,23" else None,
         "par_tenseur": lignes, "duree_s": time.time() - t0}
    print(json.dumps(j, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
