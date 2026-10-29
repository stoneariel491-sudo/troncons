"""Témoin O1 du lot O : le simulateur du moteur (trc-cache, `rejouer`) contre les simulateurs Python
des études 04 et gpt-oss, compté à l'unité (ARCHITECTURE.md § 6.5, ligne O1).

SEUIL, DÉCLARÉ AVANT LE LANCEMENT (2026-10-15) : 0 écart. Chaque comparaison porte sur un nombre
entier de succès ; une seule unité d'écart fait tomber le témoin. La source du seuil : le § 6.5
(« 0 écart ») et la nature de la chose, deux simulations déterministes des mêmes règles.

Les chemins comparés (aucun code copié ; les outils Python sont importés tels quels, inchangés) :
  P1  étude 04, cache PAR COUCHE (`outils/chargement_localite.py`, cache_lru et cache_belady) :
      chaque couche d'une trace synthétique est écrite seule (L = 1) et rejouée par `rejouer` avec
      C emplacements. Traces : uniforme, figée, collante (ρ = 0,6), T = 4 000, L = 4, E = 128,
      k = 8, graine 20261015, générateurs de l'étude 04 ; C ∈ {8, 16, 32, 64} (les budgets de 04).
  P2  cache GLOBAL entre couches (`outils/gptoss_localite.py`, g_lru et g_belady) : les mêmes
      traces entières, N ∈ {k, L·k − 1, L·k, 51, 128, 205} (51, 128, 205 = 10, 25, 40 % de L·E).
  P3  deux étages (règle 2 de trc-cache) : `rejouer --tiedes r` avec v emplacements ; succès VRAM
      = g_lru(N = v) et succès VRAM + RAM = g_lru(N = r), pour r ≥ v.
  P4  traces RÉELLES de gpt-oss-20b (mesures/localite-gpt-oss/traces-20b/traces-20b.tar.xz,
      commitées par l'agent de mesure) : chaque trace, et les concaténations « tous.lecture » et
      « tous.generation » de l'outil gpt-oss, aux budgets de l'outil (5 à 40 % de L·E, N ≥ k) :
      `rejouer` contre g_lru et g_belady recalculés ici, ET contre les taux PUBLIÉS dans
      mesures/localite-gpt-oss/20b/localite-gpt-oss-20b.json (égalité du flottant succès / accès).
CASSURE (--casser) : `rejouer --casser` ignore les succès dans la politique (LRU devient FIFO) ;
le témoin doit tomber sur P1, P2, P4 (LRU) ; Belady y perd aussi sa mise à jour d'instant.

Usage :
  python -I -X utf8 mesures/moteur/O/temoin_o1.py --rejouer <rejouer.exe> --sortie <journal.json>
         [--csv <courbes.csv>] [--casser]
"""
import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import tarfile
import tempfile
import time

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.normpath(os.path.join(ICI, "..", "..", ".."))
sys.path.insert(0, os.path.join(DEPOT, "outils"))
import chargement_localite as cl  # noqa: E402  (étude 04, inchangé)
import gptoss_localite as gl  # noqa: E402  (mesure gpt-oss, inchangé)

TRACES_20B = os.path.join(DEPOT, "mesures", "localite-gpt-oss", "traces-20b", "traces-20b.tar.xz")
PUBLIE_20B = os.path.join(DEPOT, "mesures", "localite-gpt-oss", "20b", "localite-gpt-oss-20b.json")


def ecrire_trace(chemin, jetons, E, entete):
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# {entete}\nE={E}\n")
        for t in jetons:
            f.write(" | ".join(" ".join(str(e) for e in c) for c in t) + "\n")


def compte(taux, total):
    """Le nombre entier de succès derrière un taux Python succès / accès, vérifié exact."""
    n = round(taux * total)
    if n / total != taux:
        raise SystemExit(f"taux {taux!r} sur {total} accès : pas un quotient entier exact")
    return n


def rejouer(exe, trace, emplacements, politique, casser, tiedes=(0,)):
    cmd = [exe, "--trace", trace, "--emplacements", ",".join(map(str, emplacements)),
           "--tiedes", ",".join(map(str, tiedes)), "--politique", politique]
    if casser:
        cmd.append("--casser")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise SystemExit(f"rejouer a échoué ({r.returncode}) : {r.stderr}")
    return json.loads(r.stdout)


class Bilan:
    def __init__(self):
        self.comparaisons, self.ecarts, self.lignes = 0, 0, []

    def comparer(self, chemin, attendu, mesure, **contexte):
        self.comparaisons += 1
        ecart = mesure - attendu
        if ecart:
            self.ecarts += 1
        self.lignes.append({"chemin": chemin, "attendu": attendu, "rejouer": mesure, "ecart": ecart, **contexte})


def synthetiques():
    """Les trois traces de l'étude 04 (mêmes générateurs, même graine, mêmes paramètres)."""
    rng = random.Random(20261015)
    T, L, E, k = 4000, 4, 128, 8
    return E, k, L, {
        "uniforme": cl.synth_uniforme(T, L, E, k, rng),
        "figee": cl.synth_fige(T, L, E, k, rng),
        "collante_rho0.6": cl.synth_collant(T, L, E, k, 0.6, rng),
    }


def p1_p2_p3(exe, casser, tmp, bilan):
    E, k, L, traces = synthetiques()
    budgets_04 = [8, 16, 32, 64]
    n_globaux = [k, L * k - 1, L * k, round(0.10 * L * E), round(0.25 * L * E), round(0.40 * L * E)]
    deux_etages = [(8, 32), (16, 64), (32, 32), (51, 205)]
    for nom, jetons in traces.items():
        # P1 : par couche, contre l'étude 04
        for c in range(L):
            seq = cl.par_couche(jetons, c)
            total = sum(len(s) for s in seq)
            chemin = os.path.join(tmp, f"{nom}.couche{c}.trace")
            ecrire_trace(chemin, [[s] for s in seq], E, f"témoin O1, {nom}, couche {c} seule")
            for pol, f04 in (("lru", cl.cache_lru), ("belady", cl.cache_belady)):
                res = rejouer(exe, chemin, budgets_04, pol, casser)["resultats"]
                for C, r in zip(budgets_04, res):
                    assert r["emplacements"] == C and r["acces"] == total
                    bilan.comparer("P1 étude 04 par couche", compte(f04(seq, C), total), r["succes_vram"],
                                   trace=nom, couche=c, politique=pol, emplacements=C)
        # P2 : global, contre gpt-oss
        groupes = gl.flux(jetons, E)
        total = sum(len(g) for g in groupes)
        chemin = os.path.join(tmp, f"{nom}.trace")
        ecrire_trace(chemin, jetons, E, f"témoin O1, {nom}")
        for pol, fg in (("lru", gl.g_lru), ("belady", gl.g_belady)):
            res = rejouer(exe, chemin, n_globaux, pol, casser)["resultats"]
            for N, r in zip(n_globaux, res):
                assert r["acces"] == total
                bilan.comparer("P2 global gpt-oss", compte(fg(groupes, N), total), r["succes_vram"],
                               trace=nom, politique=pol, emplacements=N)
        # P3 : deux étages
        for v, rr in deux_etages:
            r = rejouer(exe, chemin, [v], "lru", casser, tiedes=[rr])["resultats"][0]
            bilan.comparer("P3 deux étages, VRAM", compte(gl.g_lru(groupes, v), total), r["succes_vram"],
                           trace=nom, emplacements=v, tiedes=rr)
            bilan.comparer("P3 deux étages, VRAM + RAM", compte(gl.g_lru(groupes, rr), total),
                           r["succes_vram"] + r["succes_ram"], trace=nom, emplacements=v, tiedes=rr)


def traces_reelles():
    """Les traces de gpt-oss-20b, lues dans l'archive commitée, au format de l'étude 04."""
    sortie = {}
    with tarfile.open(TRACES_20B, "r:xz") as tar:
        for m in tar.getmembers():
            if not m.isfile() or not m.name.endswith(".trace"):
                continue
            texte = tar.extractfile(m).read().decode("utf-8")
            sortie[os.path.basename(m.name)] = texte
    return sortie


def p4(exe, casser, tmp, bilan, csv_lignes):
    publie = json.load(open(PUBLIE_20B, encoding="utf-8"))
    textes = traces_reelles()
    jeux = {}
    for nom_fichier, texte in sorted(textes.items()):
        chemin = os.path.join(tmp, nom_fichier)
        with open(chemin, "w", encoding="utf-8", newline="\n") as f:
            f.write(texte)
        jetons, E = cl.lire_trace(chemin)
        prefixe, genre, mode, _ = nom_fichier.split(".")
        nom = f"{genre}.{mode}"
        jeux[(prefixe, nom)] = (chemin, jetons, E)
    # concaténations de l'outil gpt-oss (ordre trié des noms, préfixe t20b seulement)
    for mode in ("lecture", "generation"):
        noms = sorted(n for (p, n) in jeux if p == "t20b" and n.endswith("." + mode))
        jetons = [t for n in noms for t in jeux[("t20b", n)][1]]
        E = jeux[("t20b", noms[0])][2]
        chemin = os.path.join(tmp, f"t20b.tous.{mode}.trace")
        ecrire_trace(chemin, jetons, E, f"concaténation de {', '.join(noms)} (ordre de gptoss_localite.py)")
        jeux[("t20b", f"tous.{mode}")] = (chemin, jetons, E)
    for (prefixe, nom), (chemin, jetons, E) in sorted(jeux.items()):
        L, k = len(jetons[0]), len(jetons[0][0])
        groupes = gl.flux(jetons, E)
        total = sum(len(g) for g in groupes)
        budgets = [(f, max(k, round(f * L * E))) for f in gl.BUDGETS]
        Ns = [N for _, N in budgets]
        res = {pol: rejouer(exe, chemin, Ns, pol, casser)["resultats"] for pol in ("lru", "belady")}
        pub = publie["traces"].get(nom, {}).get("global") if prefixe == "t20b" else None
        for (f, N), rl, rb in zip(budgets, res["lru"], res["belady"]):
            assert rl["acces"] == total and rl["emplacements"] == N
            for pol, r, fg in (("lru", rl, gl.g_lru), ("belady", rb, gl.g_belady)):
                bilan.comparer("P4 trace réelle, recalcul", compte(fg(groupes, N), total), r["succes_vram"],
                               trace=f"{prefixe}.{nom}", politique=pol, emplacements=N)
                if pub is not None:
                    p = pub[f"{f:.2f}"]
                    assert p["emplacements"] == N
                    bilan.comparer("P4 trace réelle, taux publié", compte(p[pol], total), r["succes_vram"],
                                   trace=f"{prefixe}.{nom}", politique=pol, emplacements=N)
            csv_lignes.append({"trace": f"{prefixe}.{nom}", "jetons": len(jetons), "L": L, "E": E, "k": k,
                               "budget_pct": round(100 * f), "emplacements": N, "acces": total,
                               "succes_lru": rl["succes_vram"], "succes_belady": rb["succes_vram"],
                               "h_lru": rl["succes_vram"] / total, "h_belady": rb["succes_vram"] / total})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rejouer", required=True)
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--csv")
    ap.add_argument("--casser", action="store_true")
    a = ap.parse_args()
    debut = time.strftime("%Y-%m-%d %H:%M:%S")
    bilan, csv_lignes = Bilan(), []
    with tempfile.TemporaryDirectory(prefix="temoin-o1-") as tmp:
        p1_p2_p3(a.rejouer, a.casser, tmp, bilan)
        p4(a.rejouer, a.casser, tmp, bilan, csv_lignes)
    par_chemin = {}
    for l in bilan.lignes:
        c = par_chemin.setdefault(l["chemin"], {"comparaisons": 0, "ecarts": 0, "ecart_absolu_max": 0})
        c["comparaisons"] += 1
        c["ecarts"] += 1 if l["ecart"] else 0
        c["ecart_absolu_max"] = max(c["ecart_absolu_max"], abs(l["ecart"]))
    verdict = "TIENT" if bilan.ecarts == 0 else "TOMBE"
    sortie = {"outil": "mesures/moteur/O/temoin_o1.py", "debut": debut, "fin": time.strftime("%Y-%m-%d %H:%M:%S"),
              "seuil": "0 écart, déclaré avant le lancement", "casser": a.casser, "rejouer": a.rejouer,
              "rejouer_sha256": hashlib.sha256(open(a.rejouer, "rb").read()).hexdigest(),
              "commit": subprocess.run(["git", "-C", DEPOT, "rev-parse", "HEAD"], capture_output=True,
                                       text=True).stdout.strip(),
              "comparaisons": bilan.comparaisons, "ecarts": bilan.ecarts, "verdict": verdict,
              "par_chemin": par_chemin, "detail": bilan.lignes}
    os.makedirs(os.path.dirname(os.path.abspath(a.sortie)), exist_ok=True)
    with open(a.sortie, "w", encoding="utf-8", newline="\n") as f:
        json.dump(sortie, f, ensure_ascii=False, indent=1)
    if a.csv:
        cles = list(csv_lignes[0].keys())
        with open(a.csv, "w", encoding="utf-8", newline="\n") as f:
            f.write(",".join(cles) + "\n")
            for l in csv_lignes:
                f.write(",".join(f"{l[c]:.6f}" if isinstance(l[c], float) else str(l[c]) for c in cles) + "\n")
    for c, v in par_chemin.items():
        print(f"{c:32s} {v['comparaisons']:5d} comparaisons, {v['ecarts']:4d} écarts (max {v['ecart_absolu_max']})")
    print(f"témoin O1 : {verdict} ({bilan.ecarts} écarts sur {bilan.comparaisons})")
    # la cassure réussit quand le témoin tombe
    return 0 if (verdict == "TIENT") != a.casser else 1


if __name__ == "__main__":
    sys.exit(main())
