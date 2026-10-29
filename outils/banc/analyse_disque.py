"""Lecture du journal du banc disque : tableaux bloc x profondeur (moyenne des passages A et B,
bruit ABBA), comparaison IOCP / IoRing selon la règle déclarée, second chemin (compteur du système).

Usage : python -I outils/banc/analyse_disque.py fondations/journaux/01-machine/disque-balayage.jsonl
"""

import json
import statistics
import sys


def main(chemin):
    lignes = [json.loads(l) for l in open(chemin, encoding="utf-8")]
    bal = [d for d in lignes if d.get("genre") == "balayage"]
    mot = [d for d in lignes if d.get("genre") == "moteurs"]
    tem = [d for d in lignes if d.get("genre") == "temoin"]
    ver = [d for d in lignes if d.get("genre") == "verdicts"]

    print("## Témoins")
    for d in tem:
        o = d.get("octets_systeme_fenetre") or {}
        print(f"- {d['nom']}: {d['debit_go_s']:.3f} Go/s, pages fausses {int(d['pages_fausses'])}/{int(d['pages_verifiees'])}, "
              f"rapport système/outil {d.get('rapport_systeme_sur_outil')}, cpu processus {d['cpu_s']:.2f} s, "
              f"cpu système {o.get('cpu_occupe')}, réussi {d.get('reussi')}")
    for v in ver:
        print("- verdicts :", v["verdicts"], "relevés :", v.get("releves_compteur"))

    for acces in ("alea", "seq"):
        print(f"\n## {acces} : Go/s (moyenne A,B) [bruit |A-B|/moy] p50 µs")
        cles = sorted({(int(d["bloc"]), int(d["qd"])) for d in bal if d["acces"] == acces})
        blocs = sorted({b for b, _ in cles})
        qds = sorted({q for _, q in cles})
        print("| bloc | " + " | ".join(f"qd {q}" for q in qds) + " |")
        print("|---|" + "---|" * len(qds))
        for b in blocs:
            cellules = []
            for q in qds:
                v = [d for d in bal if d["acces"] == acces and int(d["bloc"]) == b and int(d["qd"]) == q]
                if len(v) < 2:
                    cellules.append("")
                    continue
                x = [d["debit_go_s"] for d in v]
                m = statistics.mean(x)
                bruit = abs(x[0] - x[1]) / m if m else 0
                p50 = statistics.mean(d["lat_p50_us"] for d in v)
                cellules.append(f"{m:.3f} [{bruit:.0%}] {p50:.0f}")
            nom = f"{b // 1024} Kio" if b < 1 << 20 else f"{b >> 20} Mio"
            print(f"| {nom} | " + " | ".join(cellules) + " |")

    print("\n## Processeur et compteur du système (balayage)")
    for acces in ("alea", "seq"):
        v = [d for d in bal if d["acces"] == acces and d.get("octets_systeme_fenetre")]
        for b in sorted({int(d["bloc"]) for d in v}):
            w = [d for d in v if int(d["bloc"]) == b]
            meilleur = max(w, key=lambda d: d["debit_go_s"])
            o = meilleur["octets_systeme_fenetre"]
            cpu_par_go = meilleur["cpu_s"] / max(meilleur["octets"] / 1e9, 1e-9)
            print(f"- {acces} {b} o, meilleur qd {int(meilleur['qd'])}: {meilleur['debit_go_s']:.3f} Go/s, "
                  f"cpu processus {meilleur['cpu_s']:.2f} s ({cpu_par_go:.2f} s/Go), cpu système moyen {o['cpu_occupe']:.0%} "
                  f"(noyau {o['cpu_noyau']:.0%}), rapport système/outil {meilleur.get('rapport_systeme_sur_outil')}")

    print("\n## IOCP contre IoRing (ABBA, deux fois)")
    groupes = {}
    for d in mot:
        groupes.setdefault((d["acces"], int(d["bloc"]), int(d["qd"])), []).append(d)
    for k, v in groupes.items():
        a = [d["debit_go_s"] for d in v if d["moteur"] == "iocp"]
        b = [d["debit_go_s"] for d in v if d["moteur"] == "ioring"]
        # Bruit : écart d'un moteur à lui-même dans chaque bloc ABBA (A1 contre A2, B1 contre B2).
        bruit_a = max(abs(a[i] - a[i + 1]) / statistics.mean(a[i:i + 2]) for i in range(0, len(a), 2))
        bruit_b = max(abs(b[i] - b[i + 1]) / statistics.mean(b[i:i + 2]) for i in range(0, len(b), 2))
        ma, mb = statistics.mean(a), statistics.mean(b)
        ecart = abs(ma - mb) / ((ma + mb) / 2)
        reel = ecart >= max(2 * max(bruit_a, bruit_b), 0.03)
        ca = statistics.mean(d["cpu_s"] for d in v if d["moteur"] == "iocp")
        cb = statistics.mean(d["cpu_s"] for d in v if d["moteur"] == "ioring")
        la = statistics.mean(d["lat_p50_us"] for d in v if d["moteur"] == "iocp")
        lb = statistics.mean(d["lat_p50_us"] for d in v if d["moteur"] == "ioring")
        print(f"- {k}: iocp {ma:.3f} Go/s (bruit {bruit_a:.0%}, cpu {ca:.2f} s, p50 {la:.0f} µs) ; "
              f"ioring {mb:.3f} Go/s (bruit {bruit_b:.0%}, cpu {cb:.2f} s, p50 {lb:.0f} µs) ; écart {ecart:.0%} -> "
              f"{'différence réelle' if reel else 'pas de différence au-dessus du bruit'}")


if __name__ == "__main__":
    main(sys.argv[1])
