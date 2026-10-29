"""Lectures du motif du moteur, sans tampon, chaque lecture journalisée (décalage, LCN, durée).

Le moteur (trc-es) lit un tronçon entier par requête (longueur du niveau 0), sans le cache de Windows
(FILE_FLAG_NO_BUFFERING), 4 requêtes en vol. Ici : `--qd` fils, une poignée sans tampon par fil, chaque
fil prend la lecture suivante de la liste (donc au plus `qd` en vol, dans l'ordre de la liste, comme la
file de trc-es). Le débit est octets / horloge de l'hôte, du départ de la première au retour de la
dernière.

  python -I -X utf8 outils/disque/placement/lire.py <fichier> --plan disque|tout|trie [--graine G] [--n N]
         [--qd 4] [--repertoire autre.trc] [--limite-octets X] [--sortie prefixe] [--temoin] [--casser]

  disque : les tronçons de `troncons disque --n 1500 --graine 20261017` (même xorshift64*, même ordre)
  tout   : chaque tronçon une fois, ordre tiré (graine G, 20261022 par défaut)
  trie   : les tronçons de « disque », triés par décalage croissant
  --repertoire : le répertoire d'un autre .trc de même contenu (copie partielle, par exemple)
  --limite-octets : ne garder que les tronçons qui finissent avant X (copie partielle)

Sorties : <prefixe>.csv (une ligne par lecture) et <prefixe>.json (résumé, SMART avant et après).

Témoin (--temoin, après la passe chronométrée) : 16 lectures tirées sont relues sans tampon et par une
lecture tamponnée ordinaire (open/seek/read de Python, chemin indépendant) ; leurs SHA-256 doivent être
égaux. Cassure (--casser) : la lecture tamponnée se fait 4 096 octets plus loin ; le témoin doit tomber.
"""
import argparse
import csv
import hashlib
import json
import os
import pathlib
import random
import statistics
import sys
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import carte  # noqa: E402
import commun  # noqa: E402


def plan_lectures(rep, plan, graine, n, limite):
    entrees = rep["entrees"]
    if plan in ("disque", "trie"):
        ordre = carte.ordre_disque(len(entrees), n or 1500, 20261017 if graine is None else graine)
    elif plan == "tout":
        ordre = list(range(len(entrees)))
        random.Random(20261022 if graine is None else graine).shuffle(ordre)
        if n:
            ordre = ordre[:n]
    else:
        raise SystemExit(f"plan inconnu : {plan}")
    if limite:
        ordre = [i for i in ordre if entrees[i][2] + entrees[i][3] <= limite]
    if plan == "trie":
        ordre.sort(key=lambda i: entrees[i][2])
    return ordre


def passe(fichier, lectures, qd):
    """lectures : liste de (indice, décalage, longueur). Rend (durées par lecture, t0, t1)."""
    lmax = max(l for _, _, l in lectures)
    lmax = -(-lmax // 4096) * 4096
    res = [None] * len(lectures)
    suivant = [0]
    verrou = threading.Lock()
    erreurs = []
    pret = threading.Barrier(qd + 1)

    def fil(k):
        h = commun.ouvrir_lecture(fichier)
        t = commun.Tampon(lmax)
        try:
            pret.wait()
            while True:
                with verrou:
                    j = suivant[0]
                    suivant[0] += 1
                if j >= len(lectures):
                    return
                _, d, l = lectures[j]
                a = time.perf_counter_ns()
                lus = commun.lire_a(h, t, d, l)
                b = time.perf_counter_ns()
                if lus != l:
                    erreurs.append((j, lus, l))
                res[j] = (a, b, k)
        except Exception as e:  # noqa: BLE001
            erreurs.append(repr(e))
        finally:
            t.liberer()
            commun.fermer(h)

    fils = [threading.Thread(target=fil, args=(k,)) for k in range(qd)]
    for f in fils:
        f.start()
    pret.wait()
    t0 = time.perf_counter_ns()
    for f in fils:
        f.join()
    t1 = time.perf_counter_ns()
    if not erreurs:
        t0 = min(x for x, _, _ in res)  # départ de la première lecture (les fils partent juste avant t0)
    if erreurs:
        raise RuntimeError(f"erreurs de lecture : {erreurs[:5]}")
    return res, t0, t1


def temoin(fichier, lectures, casser):
    tirage = random.Random(7).sample(lectures, min(16, len(lectures)))
    egales = 0
    h = commun.ouvrir_lecture(fichier)
    lmax = -(-max(l for _, _, l in tirage) // 4096) * 4096
    t = commun.Tampon(lmax)
    try:
        with open(fichier, "rb") as f:
            for _, d, l in tirage:
                commun.lire_a(h, t, d, l)
                a = hashlib.sha256(t.octets(l)).hexdigest()
                f.seek(d + (4096 if casser else 0))
                b = hashlib.sha256(f.read(l)).hexdigest()
                egales += a == b
    finally:
        t.liberer()
        commun.fermer(h)
    return {"lectures": len(tirage), "egales": egales, "casse": casser, "tient": egales == len(tirage)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fichier")
    ap.add_argument("--plan", default="disque")
    ap.add_argument("--graine", type=int)
    ap.add_argument("--n", type=int)
    ap.add_argument("--qd", type=int, default=4)
    ap.add_argument("--repertoire")
    ap.add_argument("--limite-octets", type=int)
    ap.add_argument("--sortie")
    ap.add_argument("--temoin", action="store_true")
    ap.add_argument("--casser", action="store_true")
    a = ap.parse_args()
    fichier = pathlib.Path(a.fichier)
    rep = carte.repertoire(a.repertoire or fichier)
    grappe, total, _ = carte.geometrie(fichier)
    ext = carte.extents(fichier)
    debuts = [e[0] for e in ext]
    ordre = plan_lectures(rep, a.plan, a.graine, a.n, a.limite_octets)
    entrees = rep["entrees"]
    lectures = [(i, entrees[i][2], entrees[i][3]) for i in ordre]
    s0 = commun.smart()
    res, t0, t1 = passe(fichier, lectures, a.qd)
    s1 = commun.smart()
    octets = sum(l for _, _, l in lectures)
    sec = (t1 - t0) / 1e9
    durees = sorted((b - x) / 1e3 for x, b, _ in res)
    lignes = []
    for (i, d, l), (x, b, k) in zip(lectures, res):
        m = carte.morceaux(ext, grappe, d, l, debuts)
        lignes.append({"indice": i, "couche": entrees[i][0], "expert": entrees[i][1], "decalage": d, "longueur": l,
                       "morceaux": len(m), "lcn_frac": round(m[0][0] / total, 6),
                       "debut_us": round((x - t0) / 1e3, 1), "fin_us": round((b - t0) / 1e3, 1), "fil": k})
    r = {
        "outil": "outils/disque/placement/lire.py", "commande": " ".join(sys.argv).replace("\\", "/"),
        "date": commun.maintenant(), "fichier": str(fichier).replace("\\", "/"), "plan": a.plan, "qd": a.qd,
        "n": len(lectures), "octets": octets, "secondes": sec, "go_s": octets / sec / 1e9,
        "duree_us_mediane": durees[len(durees) // 2], "duree_us_p90": durees[len(durees) * 9 // 10],
        "debit_par_lecture_median_go_s": statistics.median(l / ((y - x) / 1e9) / 1e9 for (_, _, l), (x, y, _) in zip(lectures, res)),
        "morceaux": sum(x["morceaux"] for x in lignes), "lectures_coupees": sum(1 for x in lignes if x["morceaux"] > 1),
        "smart_avant": s0, "smart_apres": s1, "smart_ecart": commun.ecart_smart(s0, s1),
    }
    if r["smart_ecart"]:
        r["octets_disque_sur_demandes"] = r["smart_ecart"]["octets_lus_disque"] / octets
    if a.temoin or a.casser:
        r["temoin"] = temoin(fichier, lectures, a.casser)
    if a.sortie:
        p = pathlib.Path(a.sortie)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p.with_suffix(".csv"), "w", newline="", encoding="utf-8") as g:
            w = csv.DictWriter(g, fieldnames=list(lignes[0].keys()))
            w.writeheader()
            w.writerows(lignes)
        p.with_suffix(".json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    e = r["smart_ecart"] or {}
    print(f"lire.py : {fichier.name} {a.plan} qd {a.qd} : {len(lectures)} lectures, {octets / 1e9:.3f} Go en {sec:.2f} s : "
          f"{r['go_s']:.3f} Go/s ; médiane {r['duree_us_mediane'] / 1e3:.1f} ms ; disque lu {e.get('octets_lus_disque', 0) / 1e9:.3f} Go ; "
          f"écrit {e.get('octets_ecrits_disque', 0) / 1e6:.0f} Mo ; {e.get('temp_avant')}→{e.get('temp_apres')} °C"
          + (f" ; témoin {r['temoin']}" if "temoin" in r else ""))
    return 0 if r.get("temoin", {}).get("tient", True) or a.casser else 1


if __name__ == "__main__":
    sys.exit(main())
