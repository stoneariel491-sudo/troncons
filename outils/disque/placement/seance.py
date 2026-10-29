"""Séances de mesure du placement disque (08 § 2.3), sous le verrou de la carte, machine calme.

  python -I -X utf8 outils/disque/placement/seance.py <seance> [--sans-attendre-calme]

Séances :
  p2a     lecture seule : ABBA `troncons disque` A20/B20 ; même série par lire.py (témoin de l'outil) ;
          témoin et cassure de lire.py ; profils complets A120 B120 C120 C120 B120 A120 et A20 B20 B20 A20 ;
          H4 (ordre aléatoire contre trié) sur A120 et B120.
  p2b-D   copie D20 de A20 d'une traite (placer.py --mode traite), empreinte, carte, lecture fraîche,
          ABBA A20 / D20 / B20, profil.
  p2b-D2  D20 relu après au moins 60 min sans écriture de ma part (H5 b), ABBA A20 / D20.
  p2b-E   copie E20 de A20 entrelacée, empreinte, carte, ABBA A20 / E20 / D20 si présent, profil.
  p3      bout en bout : `troncons mesurer` (invite wiki-3000, 256 jetons gloutons) A20 / D20 en
          A D D A A D D A ; mêmes jetons attendus au bit (même contenu), octets lus par jeton égaux.

Chaque passe : verrou rafraîchi, secteur exigé, relevé des autres flux avant et après (« SOUS CHARGE »
sinon), SMART avant et après (dans le journal de la passe). Le verrou est rendu à la fin, même sur
erreur.
"""
import json
import os
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import commun  # noqa: E402

R = commun.RACINE
OUT = R / "mesures/disque/placement"
TRONCONS = "~/dev/cibles/troncons-codon/release/troncons.exe"
PY = sys.executable
OUTILS = R / "outils/disque/placement"
M = "~/dev/modeles/trc"
F = {
    "A120": f"{M}/gpt-oss-120b.trc", "B120": f"{M}/gpt-oss-120b-v12.trc", "C120": f"{M}/temoin-codon/gpt-oss-120b-v10-recode.trc",
    "A20": f"{M}/gpt-oss-20b.trc", "B20": f"{M}/gpt-oss-20b-v12.trc",
    "D20": str(commun.ESSAIS / "D20.trc").replace("\\", "/"), "E20": str(commun.ESSAIS / "E20.trc").replace("\\", "/"),
    "F20": str(commun.ESSAIS / "F20.trc").replace("\\", "/"),
    "G20a": str(commun.ESSAIS / "G20a.trc").replace("\\", "/"), "G20b": str(commun.ESSAIS / "G20b.trc").replace("\\", "/"),
}
SHA_A20 = "e8bd6ae13288344d0ab29b70dd311e0045769624651b56e943ca39a878c7169f"
SHA_B20 = "ef1cf7407edb7088bca42c9be30e2f3f87e8e052f7b6a8c877b7c26622d0c433"


def disque(seance, i, cle):
    nom = f"{seance}-{i:02d}-disque-{cle}"
    return nom, [TRONCONS, "disque", "--modele", F[cle], "--n", "1500", "--graine", "20261017", "--repos", "5",
                 "--journal", str(OUT / seance / f"{nom}.json")]


def lire(seance, i, cle, plan, extra=()):
    nom = f"{seance}-{i:02d}-lire-{plan}-{cle}"
    return nom, [PY, "-I", "-X", "utf8", str(OUTILS / "lire.py"), F[cle], "--plan", plan, "--sortie", str(OUT / seance / nom), *extra]


def plan_p2a(s):
    p = []
    i = 1
    for cle in "A20 B20 B20 A20 A20 B20 B20 A20".split():
        p.append(disque(s, i, cle)); i += 1
    for cle in "A20 B20 B20 A20".split():
        p.append(lire(s, i, cle, "disque")); i += 1
    p.append(lire(s, i, "B20", "disque", ["--temoin"])); i += 1
    p.append(lire(s, i, "B20", "disque", ["--casser"])); i += 1
    for cle in "A120 B120 C120 C120 B120 A120".split():
        p.append(lire(s, i, cle, "tout")); i += 1
    for cle in "A20 B20 B20 A20".split():
        p.append(lire(s, i, cle, "tout")); i += 1
    for cle, plan in (("A120", "disque"), ("A120", "trie"), ("A120", "trie"), ("A120", "disque"),
                      ("B120", "disque"), ("B120", "trie"), ("B120", "trie"), ("B120", "disque")):
        p.append(lire(s, i, cle, plan)); i += 1
    return p


def plan_copie(s, cle, mode):
    p = [(f"{s}-01-copier-{cle}", [PY, "-I", "-X", "utf8", str(OUTILS / "placer.py"), "copier", F["A20"], F[cle], "--mode", mode,
                                    "--journal", str(OUT / s / f"{s}-01-copier-{cle}.json")])]
    p.append(lire(s, 2, cle, "disque"))  # lecture fraîche (H5 b)
    p.append((f"{s}-03-empreinte-{cle}", [PY, "-I", "-X", "utf8", str(OUTILS / "placer.py"), "empreinte", F[cle], "--attendu", SHA_A20,
                                          "--journal", str(OUT / s / f"{s}-03-empreinte-{cle}.json")]))
    p.append((f"{s}-04-carte-{cle}", [PY, "-I", "-X", "utf8", str(OUTILS / "carte.py"), "projeter", F[cle], "--json", str(OUT / s / f"carte-{cle}.json")]))
    i = 5
    autres = ["D20"] if cle == "E20" and os.path.exists(F["D20"]) else []
    for c in ["A20", cle, "B20", *autres, *autres, "B20", cle, "A20"]:
        p.append(disque(s, i, c)); i += 1
    for c in [cle, "A20", "A20", cle]:
        p.append(lire(s, i, c, "tout")); i += 1
    return p


def plan_p4(s):
    """H7 (08 § 2.6) : la profondeur de file de l'étage disque, 2 à 16, sur A20 et B20."""
    p = []
    i = 1
    for q in (4, 8, 16, 2, 2, 16, 8, 4):
        for c in (("A20", "B20") if i % 4 == 1 else ("B20", "A20")):
            nom = f"{s}-{i:02d}-disque-q{q}-{c}"
            p.append((nom, [TRONCONS, "disque", "--modele", F[c], "--n", "1500", "--graine", "20261017", "--repos", "5",
                            "--profondeur", str(q), "--journal", str(OUT / s / f"{nom}.json")]))
            i += 1
    return p


def plan_p5(s):
    """H7, amendement du 2026-10-22 à 10 h 35 (08 § 2.7) : q = 1, 2, 4 seulement, quatre passes par (fichier, q)."""
    p = []
    i = 1
    for q in (4, 2, 1, 1, 2, 4, 4, 2, 1, 1, 2, 4):
        for c in (("A20", "B20") if i % 4 == 1 else ("B20", "A20")):
            nom = f"{s}-{i:02d}-disque-q{q}-{c}"
            p.append((nom, [TRONCONS, "disque", "--modele", F[c], "--n", "1500", "--graine", "20261017", "--repos", "5",
                            "--profondeur", str(q), "--journal", str(OUT / s / f"{nom}.json")]))
            i += 1
    return p


def plan_p6(s, q):
    """Bout en bout : troncons mesurer sur A20, profondeur 4 (défaut) contre q, A Q Q A A Q Q A."""
    p = []
    for i, x in enumerate("4 Q Q 4 4 Q Q 4".split(), 1):
        prof = "4" if x == "4" else str(q)
        nom = f"{s}-{i:02d}-mesurer-A20-q{prof}"
        p.append((nom, [TRONCONS, "mesurer", "--modele", F["A20"], "--vocab", f"{M}/gpt-oss-20b.vocab.gguf",
                        "--invite", "~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt", "-n", "256",
                        "--profondeur", prof, "--repos", "10", "--sortie", str(OUT / s / f"{nom}.txt"), "--journal", str(OUT / s / f"{nom}.json")]))
    return p


def plan_p7(s):
    """Hypothèse de relais (08 § 2.8, amendement du 2026-10-26) : deux copies de A20 écrites comme le codeur,
    l'une après l'autre, après le retrim ; empreinte et carte de chacune ; lecture fraîche ; ABBA frais."""
    p = []
    for k, c in enumerate(("G20a", "G20b"), 1):
        p.append((f"{s}-0{k}-copier-{c}", [PY, "-I", "-X", "utf8", str(OUTILS / "placer.py"), "copier", F["A20"], F[c], "--mode", "filet",
                                         "--plafond-go", "22.4", "--journal", str(OUT / s / f"{s}-0{k}-copier-{c}.json")]))
    i = 3
    for c in ("G20a", "G20b"):
        p.append(lire(s, i, c, "disque")); i += 1
    for c in ("G20a", "G20b"):
        p.append((f"{s}-{i:02d}-empreinte-{c}", [PY, "-I", "-X", "utf8", str(OUTILS / "placer.py"), "empreinte", F[c], "--attendu", SHA_A20,
                                                "--journal", str(OUT / s / f"{s}-{i:02d}-empreinte-{c}.json")])); i += 1
        p.append((f"{s}-{i:02d}-carte-{c}", [PY, "-I", "-X", "utf8", str(OUTILS / "carte.py"), "projeter", F[c],
                                            "--json", str(OUT / s / f"carte-{c}.json")])); i += 1
    for c in "A20 G20a G20b B20 B20 G20b G20a A20".split():
        p.append(disque(s, i, c)); i += 1
    return p


def plan_p7_relire(s):
    """La relecture à au moins + 2 h (08 § 2.8) : deux tours A Ga Gb B B Gb Ga A ; témoin et cassure de lire.py."""
    p = []
    i = 1
    for c in "A20 G20a G20b B20 B20 G20b G20a A20 A20 G20a G20b B20 B20 G20b G20a A20".split():
        p.append(disque(s, i, c)); i += 1
    for c in ("G20a", "G20b"):
        p.append(lire(s, i, c, "tout")); i += 1
    p.append(lire(s, i, "G20a", "disque", ["--temoin"])); i += 1
    p.append(lire(s, i, "G20a", "disque", ["--casser"])); i += 1
    return p


def plan_mesurer(s, cle):
    """Bout en bout : troncons mesurer A20 contre `cle`, A X X A A X X A."""
    p = []
    for i, c in enumerate(f"A20 {cle} {cle} A20 A20 {cle} {cle} A20".split(), 1):
        nom = f"{s}-{i:02d}-mesurer-{c}"
        p.append((nom, [TRONCONS, "mesurer", "--modele", F[c], "--vocab", f"{M}/gpt-oss-20b.vocab.gguf",
                        "--invite", "~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt", "-n", "256",
                        "--repos", "10", "--sortie", str(OUT / s / f"{nom}.txt"), "--journal", str(OUT / s / f"{nom}.json")]))
    return p


def plan_p3(s):
    p = []
    for i, c in enumerate("A20 D20 D20 A20 A20 D20 D20 A20".split(), 1):
        nom = f"{s}-{i:02d}-mesurer-{c}"
        p.append((nom, [TRONCONS, "mesurer", "--modele", F[c], "--vocab", f"{M}/gpt-oss-20b.vocab.gguf",
                        "--invite", "~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt", "-n", "256",
                        "--repos", "10", "--sortie", str(OUT / s / f"{nom}.txt"), "--journal", str(OUT / s / f"{nom}.json")]))
    return p


def plan_relire(s, cle, avec_b=False):
    p = []
    i = 1
    ordre = ["A20", cle, "B20", "B20", cle, "A20"] * 1 if avec_b else ["A20", cle, cle, "A20", "A20", cle, cle, "A20"]
    if avec_b:
        ordre = ["A20", cle, "B20", "B20", cle, "A20", "A20", cle, "B20", "B20", cle, "A20"]
    for c in ordre:
        p.append(disque(s, i, c)); i += 1
    p.append(lire(s, i, cle, "tout"))
    return p


def main():
    seance = sys.argv[1]
    attendre = "--sans-attendre-calme" not in sys.argv
    plans = {"p2a": lambda: plan_p2a(seance), "p2b-D": lambda: plan_copie(seance, "D20", "traite"),
             "p2b-D2": lambda: plan_relire(seance, "D20"), "p2b-E": lambda: plan_copie(seance, "E20", "entrelace"),
             "p2b-E2": lambda: plan_relire(seance, "E20"), "p3": lambda: plan_p3(seance),
             "p2b-F": lambda: plan_copie(seance, "F20", "filet"), "p2b-F2": lambda: plan_relire(seance, "F20", avec_b=True),
             "p4": lambda: plan_p4(seance), "p5": lambda: plan_p5(seance),
             "p7": lambda: plan_p7(seance), "p7-2": lambda: plan_p7_relire(seance), "p8": lambda: plan_mesurer(seance, "G20a"),
             "p6-q1": lambda: plan_p6(seance, 1), "p6-q2": lambda: plan_p6(seance, 2),
             "p2b-Fb": lambda: plan_copie(seance, "F20", "filet"), "p2b-Fb2": lambda: plan_relire(seance, "F20", avec_b=True)}
    if seance not in plans:
        print(__doc__)
        return 2
    plan = plans[seance]()
    (OUT / seance).mkdir(parents=True, exist_ok=True)
    nj = f"seance-{seance}.log"
    commun.journal(nj, f"séance {seance} : {len(plan)} passes ; place libre {commun.place_libre() / 1e9:.1f} Go")
    commun.verrou_prendre(seance, "outils/disque/placement/seance.py", nj)
    resume = {"seance": seance, "debut": commun.maintenant(), "passes": []}
    try:
        if attendre:
            commun.attendre_calme(nj)
        for nom, cmd in plan:
            commun.verrou_rafraichir()
            al = commun.alimentation()
            if al != "2":
                commun.journal(nj, f"{nom} : alimentation {al}, pas sur secteur : arrêt")
                break
            av = commun.autres_lourds()
            sa = commun.smart()
            t0 = time.time()
            with open(OUT / seance / f"{nom}.log", "w", encoding="utf-8") as f:
                r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=R)
            duree = time.time() - t0
            sb = commun.smart()
            ap = commun.autres_lourds()
            charge = bool(av or ap)
            sortie = (OUT / seance / f"{nom}.log").read_text(encoding="utf-8", errors="replace").strip().splitlines()
            p = {"nom": nom, "commande": [str(c).replace("\\", "/") for c in cmd], "code": r.returncode, "secondes": duree,
                 "alimentation": al, "autres_avant": av, "autres_apres": ap, "sous_charge": charge,
                 "smart_avant": sa, "smart_apres": sb, "smart_ecart": commun.ecart_smart(sa, sb), "derniere_ligne": sortie[-1] if sortie else ""}
            resume["passes"].append(p)
            commun.journal(nj, f"{nom} : code {r.returncode}, {duree:.0f} s, {sa.get('temperature_c')}→{sb.get('temperature_c')} °C"
                               + (f" ; SOUS CHARGE avant {av} après {ap}" if charge else "") + f" ; {p['derniere_ligne'][:220]}")
            (OUT / seance / f"seance-{seance}.json").write_text(json.dumps(resume, ensure_ascii=False, indent=1), encoding="utf-8")
            if r.returncode != 0 and "casser" not in " ".join(map(str, cmd)):
                commun.journal(nj, f"{nom} : code {r.returncode} : arrêt de la séance")
                break
    finally:
        resume["fin"] = commun.maintenant()
        (OUT / seance / f"seance-{seance}.json").write_text(json.dumps(resume, ensure_ascii=False, indent=1), encoding="utf-8")
        commun.verrou_rendre(nj)
    return 0


if __name__ == "__main__":
    sys.exit(main())
