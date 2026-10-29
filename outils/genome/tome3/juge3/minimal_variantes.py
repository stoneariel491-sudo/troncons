# Juge de la troisième passe : compile les variantes du document minimal (deux passes chacune) et relève, pour
# chacune, les erreurs du journal (lignes « ! »), leurs messages, le texte des renvois (pdftotext) et la trace.
# Usage : python -I -X utf8 minimal_variantes.py DOSSIER   (le dossier contient minimal-juge3.tex et les correctifs)
import json, re, subprocess, sys
from pathlib import Path

d = Path(sys.argv[1])
VARIANTES = {
    "nu": "", "corr": r"\def\CORR{1}", "crochet": r"\def\SANSCROCHET{1}", "amsseul": r"\def\AMSSEUL{1}",
    "faux": r"\def\CORR{1}\def\FAUX{1}", "trace": r"\def\TRACE{1}",
}
res = {}
for nom, pre in VARIANTES.items():
    for _ in range(2):
        subprocess.run(["lualatex", "-interaction=nonstopmode", f"-jobname={nom}", pre + r"\input{minimal-juge3}"],
                       cwd=d, capture_output=True)
    log = (d / f"{nom}.log").read_text(encoding="utf-8", errors="replace")
    erreurs = [l.strip() for l in log.splitlines() if l.startswith("!")]
    texte = subprocess.run(["pdftotext", "-layout", str(d / f"{nom}.pdf"), "-"], capture_output=True).stdout.decode(
        "utf-8", "replace") if (d / f"{nom}.pdf").exists() else ""
    m = re.search(r"RENVOIS(.*?)FIN", " ".join(texte.split()))
    noyau = re.search(r"LaTeX2e <([^>]+)>", log)
    res[nom] = {"erreurs": len(erreurs), "messages": erreurs, "renvois": m.group(1).strip() if m else None,
                "noyau": noyau.group(1) if noyau else None}
    if nom == "trace":
        appels = re.findall(r"\\newcounteralias \{[^}]*\}\{[^}]*\}", log)
        res[nom]["appels_newcounteralias"] = sorted(set(appels))
        # d'où vient l'appel : la macro \@ynthm développée juste avant
        res[nom]["ynthm_contient_newcounteralias"] = bool(re.search(r"\\@ynthm[^\n]*->[^\n]*\n?[^\n]*newcounteralias",
                                                                     log))
print(json.dumps(res, ensure_ascii=False, indent=1))
