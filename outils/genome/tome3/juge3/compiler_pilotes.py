# Juge de la troisième passe : copie les quatre pilotes du Tome III (memoire/essai/pilote-tome3-*.tex, non commités)
# dans memoire/essai/juge3/pilotes/ et les compile là, en français et en anglais, lualatex deux passes (une troisième
# si le journal la demande). Variante « commun-avant » : le pilote commun avec le préambule d'avant 7db2673 (extrait
# par extraire_correctifs.py), témoin qui doit lever les six erreurs. Relève erreurs, boîtes trop pleines, renvois
# indéfinis, polices manquantes, pages.
# Usage : python -I -X utf8 compiler_pilotes.py [lots…]   (défaut : commun ronde construction latents commun-avant)
import json, re, shutil, subprocess, sys, time
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[4]
ESSAI = DEPOT / "memoire/essai"
D = ESSAI / "juge3/pilotes"
D.mkdir(parents=True, exist_ok=True)
PRE_HEAD = "~/dev/active/troncons/memoire/commun/preambule"
lots = sys.argv[1:] or ["commun", "ronde", "construction", "latents", "commun-avant"]


def releve(log: Path, pdf: Path) -> dict:
    t = log.read_text(encoding="utf-8", errors="replace")
    pages = None
    if pdf.exists():
        out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True).stdout.decode("utf-8", "replace")
        m = re.search(r"Pages:\s+(\d+)", out)
        pages = int(m.group(1)) if m else None
    return {
        "erreurs": sum(1 for l in t.splitlines() if l.startswith("!")),
        "messages": sorted({l.strip() for l in t.splitlines() if l.startswith("!")})[:8],
        "trop_pleines": len(re.findall(r"^Overfull \\[hv]box", t, re.M)),
        "trop_creuses": len(re.findall(r"^Underfull \\[hv]box", t, re.M)),
        "renvois_indefinis": len(re.findall(r"(Reference|Citation) `[^']*' on page \d+ undefined", t)),
        "polices": sorted(set(re.findall(r"Font shape `([^']*)' undefined", t))),
        "rerun": bool(re.search(r"Rerun to get|Label\(s\) may have changed", t)),
        "noyau": (re.search(r"LaTeX2e <([^>]+)>", t) or [None, None])[1],
        "pages": pages,
    }


res = {}
for lot in lots:
    src = ESSAI / f"pilote-tome3-{lot.replace('-avant', '')}.tex"
    nom = f"pilote-tome3-{lot}"
    texte = src.read_text(encoding="utf-8")
    if lot.endswith("-avant"):
        assert texte.count(PRE_HEAD) == 1
        texte = texte.replace(PRE_HEAD, str(DEPOT / "memoire/essai/juge3/minimal/preambule-avant").replace("\\", "/"))
    (D / f"{nom}.tex").write_text(texte, encoding="utf-8")
    for langue, job, pre in (("fr", nom, ""), ("en", f"{nom}-en", r"\def\ANGLAIS{1}")):
        debut = time.time()
        for passe in range(3):
            subprocess.run(["lualatex", "-interaction=nonstopmode", f"-jobname={job}", pre + r"\input{" + nom + "}"],
                           cwd=D, capture_output=True)
            r = releve(D / f"{job}.log", D / f"{job}.pdf")
            if passe >= 1 and not r["rerun"]:
                break
        r["passes"] = passe + 1
        r["secondes"] = round(time.time() - debut)
        res[f"{lot}-{langue}"] = r
        print(lot, langue, json.dumps(r, ensure_ascii=False), flush=True)
(D / "compilation.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
