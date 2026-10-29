"""Vitesse de décodage (lot de 1) de fichiers GGUF quantifiés et débit effectif des poids.

Pour chaque fichier : jetons/s de génération mesurés par llama-bench (-p 0 -n N), et
débit effectif = octets de poids lus par jeton / temps par jeton. Les octets lus par
jeton viennent de quant-gguf-bits.py (somme des tenseurs, enchâssement exclu sauf s'il
sert aussi de sortie). Le rapport à 256 Go/s (plafond théorique de la GDDR6 128 bits à
16 Gb/s de la RTX 4060 Laptop) dit quelle part de la bande passante le noyau de
décodage laisse passer.

Contre le bruit (la carte est partagée avec d'autres agents) : séries ABBA, chaque
type B étant encadré par la référence A ; l'écart de la référence à elle-même entre
ses passes est le bruit de référence, journalisé.

Usage : python quant-vitesse.py <reference.gguf> <journal.json> <a.gguf> [<b.gguf> ...]
"""
import json
import os
import statistics
import subprocess
import sys
import time

BIN = "~/dev/modeles/llama.cpp-b11515/llama-bench.exe"
OUTILS = os.path.dirname(os.path.abspath(__file__))
N_GEN = int(os.environ.get("N_GEN", "64"))
REPET = int(os.environ.get("REPET", "3"))
# Options ajoutées à llama-bench (passe 3 : « -mmp 0 --prio 2 », sans mmap, fil prioritaire).
EXTRA = os.environ.get("LLAMA_BENCH_EXTRA", "").split()
PLAFOND = 256e9


def octets_par_jeton(chemin):
    r = subprocess.run([sys.executable, "-I", os.path.join(OUTILS, "quant-gguf-bits.py"), chemin],
                       capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    if isinstance(d, list):
        d = d[0]
    return d["octets_lus_par_jeton"], d["bpp_tenseurs"]


def banc(chemin):
    r = subprocess.run([BIN, "-m", chemin, "-p", "0", "-n", str(N_GEN), "-r", str(REPET),
                        "-ngl", "99", "-o", "json"] + EXTRA, capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr[-400:]
    d = json.loads(r.stdout)
    return d[0]["avg_ts"], d[0].get("stddev_ts")


def main():
    ref, journal, autres = sys.argv[1], sys.argv[2], sys.argv[3:]
    resultat = {"outil": "quant-vitesse.py", "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "n_gen": N_GEN, "repetitions": REPET, "options_llama_bench": EXTRA, "reference": os.path.basename(ref),
                "mesures": []}
    o_ref, b_ref = octets_par_jeton(ref)
    refs = []
    for chemin in autres:
        o, b = octets_par_jeton(chemin)
        serie = []
        # A B B A
        for nom, ch in (("A", ref), ("B", chemin), ("B", chemin), ("A", ref)):
            ts, sd = banc(ch)
            serie.append({"role": nom, "jetons_s": ts, "ecart_type": sd})
        ta = [s["jetons_s"] for s in serie if s["role"] == "A" and s["jetons_s"]]
        tb = [s["jetons_s"] for s in serie if s["role"] == "B" and s["jetons_s"]]
        refs += ta
        m = {"fichier": os.path.basename(chemin), "bpp_tenseurs": b, "octets_lus_par_jeton": o,
             "serie_abba": serie}
        if tb:
            vb = statistics.mean(tb)
            m["jetons_s"] = round(vb, 2)
            m["go_s_effectifs"] = round(o * vb / 1e9, 1)
            m["part_du_plafond_256"] = round(o * vb / PLAFOND, 3)
        if ta:
            m["reference_jetons_s"] = round(statistics.mean(ta), 2)
            m["bruit_reference_relatif"] = round((max(ta) - min(ta)) / statistics.mean(ta), 3)
        resultat["mesures"].append(m)
        print(json.dumps(m, ensure_ascii=False), file=sys.stderr)
    if refs:
        vr = statistics.mean(refs)
        resultat["reference_bilan"] = {"bpp_tenseurs": b_ref, "octets_lus_par_jeton": o_ref,
                                       "jetons_s_moyen": round(vr, 2),
                                       "jetons_s_min": round(min(refs), 2), "jetons_s_max": round(max(refs), 2),
                                       "go_s_effectifs": round(o_ref * vr / 1e9, 1),
                                       "part_du_plafond_256": round(o_ref * vr / PLAFOND, 3)}
    with open(journal, "w", encoding="utf-8") as f:
        json.dump(resultat, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
