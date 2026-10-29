"""La séance du juge du placement disque (00-seuils-declares.md §§ 2 à 4), sous le verrou, machine calme.

  python -I -X utf8 outils/disque/placement/juge/seance_juge.py principale      (J1 à J8)
  python -I -X utf8 outils/disque/placement/juge/seance_juge.py bout-en-bout    (J7 bis)
  python -I -X utf8 outils/disque/placement/juge/seance_juge.py jbis            (amendement § 5 : J3, J4, J7
                                                                                  refaites, J9, J8)

Chaque passe : secteur exigé (sinon arrêt propre, verrou rendu), verrou rafraîchi, relevé des autres flux
avant (on attend le calme) et après (« sous charge » sinon), SMART avant et après. Une ligne CSV par lecture,
un JSON par passe, sous mesures/disque/placement/juge/seance/ ; journal seance.log.
"""
import csv
import json
import os
import pathlib
import statistics as st
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import carte_juge as cj  # noqa: E402
import lecteur  # noqa: E402
import machine  # noqa: E402

R = pathlib.Path(__file__).resolve().parents[4]
OUT = R / "mesures/disque/placement/juge/seance"
M = "~/dev/modeles/trc"
F = {"A20": f"{M}/gpt-oss-20b.trc", "B20": f"{M}/gpt-oss-20b-v12.trc",
     "A120": f"{M}/gpt-oss-120b.trc", "B120": f"{M}/gpt-oss-120b-v12.trc",
     "C120": f"{M}/temoin-codon/gpt-oss-120b-v10-recode.trc",
     "R20": "~/dev/essais/troncons/genome/synonyme/trc/gpt-oss-20b-synonyme-l0.rapide.trc"}
TRONCONS = "~/dev/cibles/troncons-codon/release/troncons.exe"
CARTES_08 = R / "mesures/disque/placement"
journal = machine.Journal(OUT / "seance.log")


class Arret(Exception):
    pass


def avant_passe(nom):
    if not machine.secteur():
        raise Arret(f"le portable n'est plus sur secteur avant {nom}")
    machine.verrou_rafraichir()
    a = machine.charge_autres()
    n = 0
    while a:
        if n % 4 == 0:
            journal(f"{nom} : attente du calme : {a}")
        n += 1
        time.sleep(30)
        machine.verrou_rafraichir()
        if not machine.secteur():
            raise Arret(f"le portable n'est plus sur secteur avant {nom}")
        a = machine.charge_autres()
        if not a:
            time.sleep(30)
            a = machine.charge_autres()
    return machine.smart()


def apres_passe(nom, s0, info):
    s1 = machine.smart()
    autres = machine.charge_autres()
    info.update({"smart_avant": s0, "smart_apres": s1, "smart_ecart": machine.ecart_smart(s0, s1),
                 "autres_apres": autres, "sous_charge": bool(autres), "secteur_apres": machine.secteur()})
    (OUT / f"{nom}.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    e = info["smart_ecart"] or {}
    journal(f"{nom} : {info.get('go_s', 0):.3f} Go/s ; {info.get('n', 0)} lectures ; disque lu / demandé "
            f"{(e.get('octets_lus_disque', 0) / info['octets']) if info.get('octets') else 0:.4f} ; "
            f"{e.get('temperature')} °C ; TMT {e.get('tmt')} ; écrit par l'hôte {e.get('octets_ecrits_disque', 0) / 1e6:.0f} Mo"
            + (f" ; SOUS CHARGE {autres}" if autres else ""))
    if not info["secteur_apres"]:
        raise Arret(f"le portable est passé sur batterie pendant {nom}")


def arret_s(res, t0):
    """Secondes passées sous 0,5 Go/s dans des plages de 3 s ou plus (dernière seconde partielle exclue)."""
    fin = max(r[4] for r in res)
    n = int((fin - t0) / 1e9)
    o = [0.0] * (n + 1)
    for _, _, l, a, b, _ in res:
        a, b = (a - t0) / 1e9, (b - t0) / 1e9
        v = l / (b - a)
        k = int(a)
        while k < b and k <= n:
            o[k] += v * (min(b, k + 1) - max(a, k))
            k += 1
    o = [x / 1e9 for x in o[:n]]
    total, k = 0, 0
    while k < len(o):
        if o[k] < 0.5:
            j = k
            while j < len(o) and o[j] < 0.5:
                j += 1
            if j - k >= 3:
                total += j - k
            k = j
        else:
            k += 1
    return total


def lire(nom, cle, lectures, q=4, frein_ms=0.0, morceaux=None, pas_tampon=None):
    s0 = avant_passe(nom)
    res, sec, octets, t0, _ = lecteur.passe(F[cle], lectures, q=q, frein_ms=frein_ms, pas_tampon=pas_tampon)
    with open(OUT / f"{nom}.csv", "w", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        w.writerow(["indice", "decalage", "longueur", "morceaux", "debut_us", "fin_us"])
        for i, d, l, a, b, n in res:
            w.writerow([i, d, l, (morceaux or {}).get(i, ""), round((a - t0) / 1e3, 1), round((b - t0) / 1e3, 1)])
    durees = sorted((b - a) / 1e3 for _, _, _, a, b, _ in res)
    info = {"outil": "outils/disque/placement/juge/lecteur.py", "nom": nom, "fichier": F[cle], "cle": cle, "q": q,
            "frein_ms": frein_ms, "pas_tampon": pas_tampon, "n": len(res), "octets": octets, "secondes": sec,
            "go_s": octets / sec / 1e9, "duree_us_mediane": durees[len(durees) // 2], "arret_s": arret_s(res, t0),
            "date": machine.horodatage()}
    apres_passe(nom, s0, info)
    return info


def troncons_disque(nom, cle):
    s0 = avant_passe(nom)
    j = OUT / f"{nom}.troncons.json"
    p = subprocess.run([TRONCONS, "disque", "--modele", F[cle], "--n", "1500", "--graine", "20261017", "--journal", str(j)],
                       capture_output=True, text=True)
    d = json.loads(j.read_text(encoding="utf-8")) if j.exists() else {}
    info = {"outil": "troncons disque (lot A)", "nom": nom, "cle": cle, "code": p.returncode, "derniere_ligne": p.stderr.strip()[-200:],
            "go_s": d.get("go_s"), "n": d.get("n"), "octets": d.get("octets"), "secondes": d.get("secondes"), "date": machine.horodatage()}
    apres_passe(nom, s0, info)
    return info


def motif(rep, ordre, taille_max=None):
    e = rep["entrees"]
    return [(i, e[i]["decalage"], e[i]["longueur"]) for i in ordre
            if taille_max is None or e[i]["decalage"] + e[i]["longueur"] <= taille_max]


def principale():
    OUT.mkdir(parents=True, exist_ok=True)
    machine.verrou_prendre("outils/disque/placement/juge/seance_juge.py principale", journal)
    try:
        if not machine.secteur():
            raise Arret("pas sur secteur au départ")
        machine.attendre_calme(journal)
        # ---------------------------------------------------------------- J1 : cartes
        cartes = {}
        resume = {}
        for k in ["A20", "B20", "R20", "A120", "B120", "C120"]:
            t = time.time()
            c = cj.carte(F[k])
            c["secondes_carte"] = time.time() - t
            cartes[k] = c
            r = {x: y for x, y in c.items() if x not in ("liste", "repertoire")}
            # contre la carte commitée de 08 (même liste d'extents au bit ?)
            nom08 = CARTES_08 / f"carte-{pathlib.Path(F[k]).name}.json"
            if nom08.exists():
                c08 = json.loads(nom08.read_text(encoding="utf-8"))
                l08 = c08.get("liste_extents") or c08.get("liste")
                r["egal_carte_08"] = [tuple(x) for x in l08] == [tuple(x) for x in c["liste"]] if l08 else None
                r["extents_08"] = c08.get("extents")
            resume[k] = r
            journal(f"J1 carte {k} : {r['extents']} extents, couverture {r['couverture']}, {r['coupes']}/{r['troncons']} tronçons coupés, "
                    f"égale à 08 : {r.get('egal_carte_08')} ; {c['secondes_carte']:.2f} s")
        resume["temoins"] = cj.temoin([F[k] for k in ["A20", "B20", "R20", "A120", "B120"]])
        resume["repertoires_A120_C120_egaux"] = cartes["A120"]["repertoire"]["empreinte"] == cartes["C120"]["repertoire"]["empreinte"]
        (OUT / "J1-cartes.json").write_text(json.dumps(resume, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        for k in ["A20", "B20", "R20"]:
            (OUT / f"J1-extents-{k}.json").write_text(json.dumps(cartes[k]["liste"]), encoding="utf-8")
        journal(f"J1 témoins : {resume['temoins']} ; RÉPERTOIRES A120 = C120 : {resume['repertoires_A120_C120_egaux']}")
        rep = {k: c["repertoire"] for k, c in cartes.items()}
        mor = {k: {e["i"]: e["morceaux"] for e in c["repertoire"]["entrees"]} for k, c in cartes.items()}
        taille = {k: c["taille"] for k, c in cartes.items()}
        natif = {k: motif(rep[k], cj.ordre_moteur(len(rep[k]["entrees"]))) for k in ["A20", "B20", "R20"]}
        # ---------------------------------------------------------------- J2 : ABBA A20 / B20 et témoins
        for n, k in enumerate("A20 B20 B20 A20 A20 B20 B20 A20".split(), 1):
            lire(f"J2-{n:02d}-{k}", k, natif[k], morceaux=mor[k])
        troncons_disque("J2-09-troncons-A20", "A20")
        troncons_disque("J2-10-troncons-B20", "B20")
        lire("J2-11-frein-A20", "A20", natif["A20"], frein_ms=10.0, morceaux=mor["A20"])
        tem = {}
        for k in ["A20", "B20"]:
            idx = cj.tirage(range(len(rep[k]["entrees"])), 16, sel=f"J2sha{k}:")
            lec = motif(rep[k], idx)
            _, _, _, _, emp = lecteur.passe(F[k], lec, q=4, garder=set(idx))
            b = lecteur.empreintes_tamponnees(F[k], lec)
            x = lecteur.empreintes_tamponnees(F[k], lec, decale=4096)
            tem[k] = {"egales": sum(emp[i] == b[i] for i in idx), "cassure_egales": sum(emp[i] == x[i] for i in idx), "n": len(idx)}
        (OUT / "J2-temoin-sha.json").write_text(json.dumps(tem, ensure_ascii=False), encoding="utf-8")
        journal(f"J2 témoin SHA-256 : {tem}")
        # ---------------------------------------------------------------- J3 : motif croisé
        croise = {"A20": motif(rep["B20"], cj.ordre_moteur(len(rep["B20"]["entrees"])), taille["A20"]),
                  "B20": motif(rep["A20"], cj.ordre_moteur(len(rep["A20"]["entrees"])), taille["B20"])}
        for n, (k, m) in enumerate([("A20", "n"), ("A20", "x"), ("B20", "n"), ("B20", "x"), ("B20", "x"), ("B20", "n"),
                                    ("A20", "x"), ("A20", "n")], 1):
            lire(f"J3-{n:02d}-{k}-{'natif' if m == 'n' else 'croise'}", k, natif[k] if m == "n" else croise[k])
        # ---------------------------------------------------------------- J4 : R20
        for n, k in enumerate("A20 R20 B20 B20 R20 A20 A20 R20 B20 B20 R20 A20".split(), 1):
            lire(f"J4-{n:02d}-{k}", k, natif[k], morceaux=mor[k])
        # ---------------------------------------------------------------- J7 : profondeur
        n = 0
        for _ in range(2):
            for k, q in [("A20", 4), ("A20", 2), ("B20", 4), ("B20", 2), ("B20", 2), ("B20", 4), ("A20", 2), ("A20", 4)]:
                n += 1
                lire(f"J7-{n:02d}-q{q}-{k}", k, natif[k], q=q)
        for k in ["A20", "B20", "B20", "A20"]:
            n += 1
            lire(f"J7-{n:02d}-q8-{k}", k, natif[k], q=8)
        # ---------------------------------------------------------------- J5 : modèle de C120
        idx5 = cj.tirage(range(len(rep["C120"]["entrees"])), 1200, sel="J5:")
        for n in (1, 2):
            lire(f"J5-{n:02d}-C120", "C120", motif(rep["C120"], idx5), morceaux=mor["C120"])
        # ---------------------------------------------------------------- J6 : C120 non coupé seul
        u = cj.tirage([i for i, m in mor["C120"].items() if m == 1], 800, sel="J6U:")
        v = cj.tirage([i for i, m in mor["B120"].items() if m == 1], 800, sel="J6V:")
        plan6 = {"C120": motif(rep["C120"], u), "A120": motif(rep["A120"], u), "B120": motif(rep["B120"], v)}
        for n, k in enumerate("C120 A120 B120 B120 A120 C120 C120 A120 B120 B120 A120 C120".split(), 1):
            lire(f"J6-{n:02d}-{k}", k, plan6[k], morceaux=mor[k])
        # ---------------------------------------------------------------- J8 : A120 en entier
        idx8 = cj.tirage(range(len(rep["A120"]["entrees"])), len(rep["A120"]["entrees"]), sel="J8:")
        lire("J8-01-A120-entier", "A120", motif(rep["A120"], idx8), morceaux=mor["A120"])
        journal("séance principale finie")
    except Arret as e:
        journal(f"ARRÊT : {e}")
        return 3
    finally:
        machine.verrou_rendre(journal)
    return 0


def bout_en_bout():
    """J7 bis : `troncons mesurer` sur A20, --profondeur 2 contre 4, A Q Q A A Q Q A (réglages de p3)."""
    OUT.mkdir(parents=True, exist_ok=True)
    machine.verrou_prendre("outils/disque/placement/juge/seance_juge.py bout-en-bout", journal)
    try:
        if not machine.secteur():
            raise Arret("pas sur secteur au départ")
        machine.attendre_calme(journal)
        for n, q in enumerate([4, 2, 2, 4, 4, 2, 2, 4], 1):
            nom = f"J7bis-{n:02d}-mesurer-q{q}-A20"
            s0 = avant_passe(nom)
            j = OUT / f"{nom}.mesurer.json"
            p = subprocess.run([TRONCONS, "mesurer", "--modele", F["A20"], "--vocab", f"{M}/gpt-oss-20b.vocab.gguf",
                                "--invite", "~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt",
                                "-n", "256", "--repos", "10", "--profondeur", str(q),
                                "--sortie", str(OUT / f"{nom}.txt"), "--journal", str(j)], capture_output=True, text=True)
            d = json.loads(j.read_text(encoding="utf-8")) if j.exists() else {}
            c = d.get("compteurs_generation", {})
            info = {"outil": "troncons mesurer", "nom": nom, "q": q, "code": p.returncode, "jetons_s": d.get("generation_jetons_s"),
                    "texte": d.get("texte_sha256"), "octets_troncons": c.get("octets_lus_troncons"), "s_lectures": c.get("s_lectures"),
                    "s_pas": c.get("s_pas"), "go_s": 0, "date": machine.horodatage()}
            apres_passe(nom, s0, info)
            journal(f"{nom} : {info['jetons_s']} jetons/s ; texte {str(info['texte'])[:12]} ; octets {info['octets_troncons']}")
        journal("séance bout-en-bout finie")
    except Arret as e:
        journal(f"ARRÊT : {e}")
        return 3
    finally:
        machine.verrou_rendre(journal)
    return 0


def serie(prefixe, plan):
    """plan : liste de (étiquette, clé, lectures, q, pas_tampon). Une passe à arrêt est refaite en fin de série
    (au plus deux fois par série), amendement § 5."""
    n = 0
    refaire = []
    for etq, cle, lec, q, pas in plan:
        n += 1
        i = lire(f"{prefixe}-{n:02d}-{etq}", cle, lec, q=q, pas_tampon=pas)
        if i["arret_s"]:
            refaire.append((etq, cle, lec, q, pas))
    for etq, cle, lec, q, pas in refaire[:2]:
        n += 1
        journal(f"{prefixe} : passe {etq} refaite (arrêt du disque)")
        lire(f"{prefixe}-{n:02d}-{etq}", cle, lec, q=q, pas_tampon=pas)


def jbis():
    OUT.mkdir(parents=True, exist_ok=True)
    machine.verrou_prendre("outils/disque/placement/juge/seance_juge.py jbis", journal)
    try:
        if not machine.secteur():
            raise Arret("pas sur secteur au départ")
        machine.attendre_calme(journal)
        rep = {k: cj.repertoire(F[k]) for k in ["A20", "B20", "R20", "A120"]}
        taille = {k: os.path.getsize(F[k]) for k in rep}
        natif = {k: motif(rep[k], cj.ordre_moteur(len(rep[k]["entrees"]))) for k in ["A20", "B20", "R20"]}
        croise = {"A20": motif(rep["B20"], cj.ordre_moteur(768), taille["A20"]),
                  "B20": motif(rep["A20"], cj.ordre_moteur(768), taille["B20"])}
        # J3 refaite : quatre passes par cas
        p3 = []
        for _ in range(2):
            for k, m in [("A20", "n"), ("A20", "x"), ("B20", "n"), ("B20", "x"), ("B20", "x"), ("B20", "n"), ("A20", "x"), ("A20", "n")]:
                p3.append((f"{k}-{'natif' if m == 'n' else 'croise'}", k, natif[k] if m == "n" else croise[k], 4, None))
        serie("Jb3", p3)
        # J4 refaite
        serie("Jb4", [(k, k, natif[k], 4, None) for k in "A20 R20 B20 B20 R20 A20 A20 R20 B20 B20 R20 A20".split()])
        # J7 refaite
        p7 = []
        for _ in range(2):
            for k, q in [("A20", 4), ("A20", 2), ("B20", 4), ("B20", 2), ("B20", 2), ("B20", 4), ("A20", 2), ("A20", 4)]:
                p7.append((f"q{q}-{k}", k, natif[k], q, None))
        p7 += [(f"q8-{k}", k, natif[k], 8, None) for k in ["A20", "B20", "B20", "A20"]]
        serie("Jb7", p7)
        # J9 : longueur des lectures (raccourcies / allongées) et pas des tampons
        racc = [(i, d, (int(l * 0.965) // 4096) * 4096) for i, d, l in natif["A20"]]
        allo = [(i, d, min(-(-int(l * 1.035) // 4096) * 4096, taille["B20"] - d)) for i, d, l in natif["B20"]]
        lmaxA = max(l for _, _, l in natif["A20"])
        p9 = []
        for _ in range(2):
            p9 += [("A20-natif", "A20", natif["A20"], 4, None), ("A20-raccourci", "A20", racc, 4, None),
                   ("B20-natif", "B20", natif["B20"], 4, None), ("B20-allonge", "B20", allo, 4, None),
                   ("B20-allonge", "B20", allo, 4, None), ("B20-natif", "B20", natif["B20"], 4, None),
                   ("A20-raccourci", "A20", racc, 4, None), ("A20-natif", "A20", natif["A20"], 4, None)]
        p9 += [("A20-pas12Mio", "A20", natif["A20"], 4, 12582912), ("B20-pasA", "B20", natif["B20"], 4, lmaxA),
               ("B20-pasA", "B20", natif["B20"], 4, lmaxA), ("A20-pas12Mio", "A20", natif["A20"], 4, 12582912)]
        serie("Jb9", p9)
        # J8 : A120 en entier
        idx8 = cj.tirage(range(len(rep["A120"]["entrees"])), len(rep["A120"]["entrees"]), sel="J8:")
        lire("Jb8-01-A120-entier", "A120", motif(rep["A120"], idx8))
        journal("séance jbis finie")
    except Arret as e:
        journal(f"ARRÊT : {e}")
        return 3
    finally:
        machine.verrou_rendre(journal)
    return 0


def j10():
    """Amendement § 6 : chaque tronçon de A20 en deux requêtes, q = 8, contre le motif natif à q = 4."""
    OUT.mkdir(parents=True, exist_ok=True)
    machine.verrou_prendre("outils/disque/placement/juge/seance_juge.py j10", journal)
    try:
        if not machine.secteur():
            raise Arret("pas sur secteur au départ")
        if not machine.attendre_calme(journal, limite_s=1800):
            raise Arret("pas de calme en 30 min : J10 non faite")
        rep = cj.repertoire(F["A20"])
        natif = motif(rep, cj.ordre_moteur(len(rep["entrees"])))
        moities = []
        for i, d, l in natif:
            a = (l // 2 // 4096) * 4096
            moities += [(i, d, a), (i + 100000, d + a, l - a)]
        # témoin : chaque moitié lue sans tampon égale, au SHA-256, la même moitié lue tamponnée ; les deux moitiés
        # bout à bout couvrent le tronçon (a + (l − a) = l, même décalage de départ). Cassure : seconde moitié lue
        # 4 096 octets plus loin.
        import hashlib
        idx = cj.tirage(range(len(rep["entrees"])), 16, sel="J10sha:")
        e = rep["entrees"]
        tem = {"egales": 0, "cassure_egales": 0, "n": 16}
        for i in idx:
            d, l = e[i]["decalage"], e[i]["longueur"]
            a = (l // 2 // 4096) * 4096
            _, _, _, _, emp = lecteur.passe(F["A20"], [(0, d, a), (1, d + a, l - a)], q=2, garder={0, 1})
            _, _, _, _, empc = lecteur.passe(F["A20"], [(0, d, a), (1, d + a + 4096, l - a)], q=2, garder={0, 1})
            with open(F["A20"], "rb") as f:
                f.seek(d)
                h1 = hashlib.sha256(f.read(a)).hexdigest()
                h2 = hashlib.sha256(f.read(l - a)).hexdigest()
            tem["egales"] += emp[0] == h1 and emp[1] == h2
            tem["cassure_egales"] += empc[0] == h1 and empc[1] == h2
        (OUT / "J10-temoin.json").write_text(json.dumps(tem, ensure_ascii=False), encoding="utf-8")
        journal(f"J10 témoin : {tem}")
        plan = []
        if "j11" in sys.argv:
            for _ in range(2):
                plan += [("A20-natif", "A20", natif, 4, None), ("A20-moities-q4", "A20", moities, 4, None),
                         ("A20-moities-q4", "A20", moities, 4, None), ("A20-natif", "A20", natif, 4, None)]
            serie("J11", plan)
            journal("séance j11 finie")
            return 0
        for _ in range(2):
            plan += [("A20-natif", "A20", natif, 4, None), ("A20-moities", "A20", moities, 8, None),
                     ("A20-moities", "A20", moities, 8, None), ("A20-natif", "A20", natif, 4, None)]
        serie("J10", plan)
        journal("séance j10 finie")
    except Arret as e:
        journal(f"ARRÊT : {e}")
        return 3
    finally:
        machine.verrou_rendre(journal)
    return 0


if __name__ == "__main__":
    quoi = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit(principale() if quoi == "principale" else bout_en_bout() if quoi == "bout-en-bout" else jbis() if quoi == "jbis" else j10() if quoi in ("j10", "j11") else 2)
