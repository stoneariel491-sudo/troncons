"""Second chemin du chiffre principal de P6 (étape 0) : le automate Rust à étiquettes contre tiers.py.
Usage : python -I -X utf8 second_chemin.py <t120> <t20> <exe niveaux-rust> <etape0.json> <sortie.json>"""
import json, os, subprocess, sys, tempfile
d120, d20, exe, e0, sortie = sys.argv[1:6]
R = json.load(open(e0, encoding="utf-8"))
RHO = 0.718
CAS = [("120b", "gen-prose-en", d120 + "/t120b.prose-en.generation", 36, 128, 323),
       ("120b", "gen-wiki", d120 + "/w120b.wiki.generation", 36, 128, 323)]
for k, p in [("code", "t"), ("dialogue", "t"), ("prose-en", "t"), ("prose-fr", "t"), ("wiki", "w")]:
    CAS.append(("20b", f"20b-gen-{k}", f"{d20}/{p}20b.{k}.generation", 24, 32, 54))
REGLES = [("accepter", 0.0), ("remonter0.30", 0.30), ("remonter0.40", 0.40), ("remonter0.50", 0.50)]
out, pire = [], 0.0
for modele, cle, base, L, E, N in CAS:
    for nom, tp in REGLES:
        f = tempfile.mktemp(suffix=".json")
        subprocess.run([exe, base + ".trace", base + ".poids", str(L), str(E), str(N), "8", str(RHO), "0.20", str(tp), f], check=True)
        ru = json.load(open(f))
        os.remove(f)
        py = (R["120b"][cle]["portillon"] if modele == "120b" else R["20b"][cle])["0.20"][nom]
        ec = {k: abs(ru[k2] - py[k]) for k, k2 in (("S", "S"), ("E_rel", "E_rel"), ("r", "r"))}
        pire = max(pire, max(ec.values()))
        out.append({"modele": modele, "trace": cle, "regle": nom, "rust": ru, "py": {k: py[k] for k in ("S", "E_rel", "r", "defauts")}, "ecart": ec})
        print(modele, cle, nom, "S rust/py %.5f/%.5f  r %.4f/%.4f  ecart max %.2e" % (ru["S"], py["S"], ru["r"], py["r"], max(ec.values())), flush=True)
json.dump({"pire_ecart": pire, "cas": out}, open(sortie, "w", encoding="utf-8"), indent=1)
print("pire écart", pire)
