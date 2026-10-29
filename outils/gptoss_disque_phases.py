"""Octets lus sur le disque par phase (lecture de la demande, génération), bruts, pour chaque passe de la
base (JSON de outils/modeles-base.py, champ « disque_serie » : [instant en s, octets/s] toutes les 0,5 s,
compteur système PDH « PhysicalDisk(_Total) / Disk Read Bytes/sec »).

Pourquoi un second calcul : gptoss_base_serie.py soustrait le débit moyen de 10 s de repos relevé avant
chaque passe ; sur la machine partagée du 2026-10-15, ce repos a valu jusqu'à 440 Mo/s (lectures d'un
autre programme ou du système), et la différence est devenue négative (passe 120b-cmoe-2 : -24,7 Go).
Ici, rien n'est soustrait : les octets bruts de chaque fenêtre sont un MAJORANT de ce que lit
llama.cpp (le compteur est global à la machine), et le débit de repos est donné à côté pour juger.

Fenêtres : la génération est la dernière phase, [fin - durée de génération, fin] ; la lecture de la
demande la précède, [début génération - durée de lecture, début génération] (durées publiées par
llama.cpp, « --perf »).

Usage : python -I gptoss_disque_phases.py <dossier de la série> <sortie.csv>
"""
import csv
import glob
import json
import os
import sys


def integrer(serie, t0, t1):
    # chaque échantillon v (octets/s) vaut pour l'intervalle qui le précède, depuis l'instant 0 du
    # compteur pour le premier (règle du banc, CompteurDisque.octets) ; défaut trouvé par le témoin le
    # 2026-10-15 : le premier échantillon sauté, 1,2 % manquait sur une passe courte de 20b
    octs, prec = 0.0, 0.0
    for ti, v in serie:
        if ti > t0 and prec < t1:
            octs += (min(ti, t1) - max(prec, t0)) * v
        prec = ti
    return octs


def main():
    dossier, sortie = sys.argv[1:3]
    lignes = []
    for f in sorted(glob.glob(os.path.join(dossier, "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        if "disque_serie" not in d or not d.get("generation", {}).get("ms"):
            continue
        fin = d["fin_s"]
        tg = d["generation"]["ms"] / 1000.0
        tp = d["prefill"]["ms"] / 1000.0
        # témoin : l'intégrale de toute la série doit retrouver le total que publie le banc (même série,
        # autre code) à 1 % près ; il tomberait si la série était lue comme des octets et non des débits
        tout = integrer(d["disque_serie"], 0.0, fin + 1.0)
        ref = d["disque"]["octets_lus_pendant"]
        if abs(tout - ref) > 0.01 * max(ref, 1.0):
            raise SystemExit(f"témoin tombé sur {d['etiquette']} : {tout:.4g} contre {ref:.4g}")
        g = integrer(d["disque_serie"], fin - tg, fin)
        p = integrer(d["disque_serie"], fin - tg - tp, fin - tg)
        lignes.append({"passe": d["etiquette"], "date": d["date"],
                       "prefill_s": round(tp, 1), "prefill_go_brut": round(p / 1e9, 3),
                       "prefill_go_s_brut": round(p / 1e9 / tp, 4),
                       "generation_s": round(tg, 1), "generation_go_brut": round(g / 1e9, 3),
                       "generation_go_s_brut": round(g / 1e9 / tg, 4),
                       "generation_go_par_jeton_brut": round(g / 1e9 / d["generation"]["n"], 4),
                       "repos_mo_s": round(d["disque"]["debit_repos_moyen_o_s"] / 1e6, 2),
                       "total_go_brut": round(d["disque"]["octets_lus_pendant"] / 1e9, 3)})
    with open(sortie, "w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)
    for l in lignes:
        print(l)
    return 0


if __name__ == "__main__":
    sys.exit(main())
