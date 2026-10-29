# Juge de design du second flux (Tome III) : les couleurs RENDUES d'une page de pilote, et leurs distances.
#
# Ce que l'outil fait.
#   1. Rend une page d'un PDF par pdftoppm (celui de MiKTeX), à une résolution donnée, et la découpe (fractions).
#   2. Relève les couleurs présentes : une couleur compte si elle couvre au moins `--min` pixels (cœur des
#      traits, des marques et des aplats ; les pixels de lissage, trop rares, ne comptent pas). Les couleurs à
#      ΔE < 3 l'une de l'autre (vision normale) sont fondues dans la plus fréquente. Le blanc du papier est écarté.
#   3. Nomme chaque couleur par la plus proche du dictionnaire (palette-tome3-couleurs.csv) ou du préambule, si
#      elle en est à ΔE < 3 ; sinon « ? ».
#   4. Chiffre toutes les paires : ΔE CIE76 en vision normale, deutéranope, protanope et en gris, par les
#      fonctions de l'outil du premier juge (outils/genome/tome3/juge-design/palette.py), appelées sans
#      modification. Une paire « tombe » si ΔE gris < 5 ou ΔE deutéranope < 10 (seuils déclarés avant la
#      lecture, JUGEMENT-figures2-design.md § 1.1).
#
# Témoins (déclarés avant, § 1.1 du jugement) :
#   TD1 : un gris pur reste gris sous la matrice deutéranope (|a*|, |b*| < 0,5) ;
#   TD2 : Signe / SerieC tombe sous la moitié de son ΔE normal en deutéranope ;
#   TD3 : sur la page du nuancier du commun, l'outil retrouve dans les pixels l'aplat CouleurSigne (C0392B) à
#         ΔE < 2, et ses vues gris et deutéranope calculées sur les pixels égalent à ΔE < 2 les colonnes « gris »
#         et « deutéranope » que le nuancier imprime (lues aussi dans les pixels).
#   Cassure (--casser) : les matrices de Machado deviennent l'identité ; TD2 et TD3 (deutéranope) doivent tomber.
#
# Usage :
#   python -I -X utf8 couleurs.py page PDF PAGE DPI x0 y0 x1 y1 [--min N] [--casser]   -> JSON sur la sortie
#   python -I -X utf8 couleurs.py temoins NUANCIER_PDF PAGE [--casser]                 -> JSON des témoins
import contextlib, csv, io, itertools, json, os, runpy, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image

DEPOT = Path(__file__).resolve().parents[4]
JUGE1 = DEPOT / "outils/genome/tome3/juge-design/palette.py"
CASSER = "--casser" in sys.argv

# Les fonctions du premier juge, sans les modifier : le script s'exécute (il imprime son JSON, qu'on jette).
argv0 = sys.argv
sys.argv = [str(JUGE1)] + (["--casser"] if CASSER else [])
with contextlib.redirect_stdout(io.StringIO()):
    J1 = runpy.run_path(str(JUGE1))
sys.argv = argv0
vue, de, lin, lab = J1["vue"], J1["de"], J1["lin"], J1["lab"]
MACHADO = J1["MACHADO"]
MODES = ["normal", "deuter", "protan", "gris"]
SEUIL = {"gris": 5.0, "deuter": 10.0}


def hexa(rgb):
    return "%02X%02X%02X" % tuple(int(v) for v in rgb)


def noms_connus():
    """Couleurs nommées : le dictionnaire (CSV du commun), le préambule et quelques gris."""
    noms = {}
    csvp = DEPOT / "memoire/figures/tome3/donnees/palette-tome3-couleurs.csv"
    with open(csvp, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            noms.setdefault(r["code"], r["nom"].replace("Couleur", ""))
    pre = (DEPOT / "memoire/commun/preambule.tex").read_text(encoding="utf-8")
    import re
    for m in re.finditer(r"\\definecolor\{(\w+)\}\{HTML\}\{([0-9A-Fa-f]{6})\}", pre):
        noms.setdefault(m.group(2).upper(), m.group(1))
    for p in range(5, 100, 5):
        v = round(255 * (1 - p / 100))
        noms.setdefault(hexa((v, v, v)), "black!%d" % p)
    return noms


def rendre(pdf, page, dpi, boite):
    tmp = tempfile.mkdtemp()
    base = os.path.join(tmp, "p")
    subprocess.run(["pdftoppm", "-r", str(dpi), "-f", str(page), "-l", str(page), "-png", "-singlefile",
                    pdf, base], check=True)
    im = Image.open(base + ".png").convert("RGB")
    w, h = im.size
    x0, y0, x1, y1 = boite
    return np.asarray(im.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))))


def releve(a, nmin):
    px = a.reshape(-1, 3)
    cles, comptes = np.unique(px, axis=0, return_counts=True)
    ordre = np.argsort(-comptes)
    gardees = []
    for i in ordre:
        if comptes[i] < nmin:
            break
        c = cles[i]
        if c.min() >= 250:
            continue
        h = hexa(c)
        fondu = False
        for g in gardees:
            if de(h, g["code"], "normal") < 3.0:
                g["pixels"] += int(comptes[i])
                fondu = True
                break
        if not fondu:
            gardees.append({"code": h, "pixels": int(comptes[i])})
    return gardees


def nommer(gardees, noms):
    for g in gardees:
        best, dbest = "?", 1e9
        for code, nom in noms.items():
            d = de(g["code"], code, "normal")
            if d < dbest:
                best, dbest = nom, d
        g["nom"] = best if dbest < 3.0 else "?"
        g["ecart_nom"] = round(dbest, 1)
        g["gris"] = hexa(np.round(255 * np.clip(srgb(vue_lin(g["code"], "gris")), 0, 1)))
        g["deuter"] = hexa(np.round(255 * np.clip(srgb(vue_lin(g["code"], "deuter")), 0, 1)))
    return gardees


def vue_lin(h, mode):
    l = lin(h)
    if mode == "gris":
        y = float(l @ np.array([0.2126, 0.7152, 0.0722]))
        return np.array([y, y, y])
    return np.clip(np.array(MACHADO[mode]) @ l, 0, 1)


def srgb(l):
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * np.power(l, 1 / 2.4) - 0.055)


def paires(gardees):
    sortie = []
    for a, b in itertools.combinations(gardees, 2):
        d = {m: round(de(a["code"], b["code"], m), 1) for m in MODES}
        tombe = d["gris"] < SEUIL["gris"] or d["deuter"] < SEUIL["deuter"]
        sortie.append({"a": a["nom"] + " " + a["code"], "b": b["nom"] + " " + b["code"], **d,
                       "verdict": "tombe" if tombe else "tient"})
    return sortie


def cmd_page(args):
    pdf, page, dpi = args[0], int(args[1]), int(args[2])
    boite = tuple(map(float, args[3:7]))
    nmin = int(args[args.index("--min") + 1]) if "--min" in args else 150
    a = rendre(pdf, page, dpi, boite)
    g = nommer(releve(a, nmin), noms_connus())
    print(json.dumps({"pdf": os.path.basename(pdf), "page": page, "dpi": dpi, "boite": boite, "min": nmin,
                      "casse": CASSER, "couleurs": g, "paires": paires(g)}, ensure_ascii=False, indent=1))


def cmd_temoins(args):
    pdf, page = args[0], int(args[1])
    res = {"casse": CASSER}
    # TD1, TD2 : sur les couleurs nominales.
    L = lab(vue_lin("808080", "deuter"))
    res["TD1_gris_reste_gris"] = bool(abs(L[1]) < 0.5 and abs(L[2]) < 0.5)
    dn, dd = de("C0392B", "2E8B57", "normal"), de("C0392B", "2E8B57", "deuter")
    res["TD2_rouge_vert"] = {"normal": round(dn, 1), "deuter": round(dd, 1), "tient": bool(dd < 0.5 * dn)}
    # TD3 : sur les pixels du nuancier. La rangée « signe » a trois aplats : couleur, gris, deutéranope.
    a = rendre(pdf, page, 200, (0, 0, 1, 1))
    g = releve(a, 150)
    def plus_proche(code):
        best = min(g, key=lambda x: de(x["code"], code, "normal"))
        return best["code"], round(de(best["code"], code, "normal"), 2)
    c_sig, d_sig = plus_proche("C0392B")
    # Les aplats imprimés par le nuancier (vues nominales du commun, palette-tome3-couleurs.csv).
    c_gris_imp, _ = plus_proche("6A6A6A")
    c_deut_imp, _ = plus_proche("827525")
    vg = hexa(np.round(255 * np.clip(srgb(vue_lin(c_sig, "gris")), 0, 1)))
    vd = hexa(np.round(255 * np.clip(srgb(vue_lin(c_sig, "deuter")), 0, 1)))
    res["TD3"] = {
        "aplat_signe_rendu": c_sig, "ecart_au_nominal": d_sig,
        "gris_calcule": vg, "gris_imprime": c_gris_imp, "ecart_gris": round(de(vg, c_gris_imp, "normal"), 2),
        "deuter_calcule": vd, "deuter_imprime": c_deut_imp, "ecart_deuter": round(de(vd, c_deut_imp, "normal"), 2),
    }
    t = res["TD3"]
    t["tient"] = bool(t["ecart_au_nominal"] < 2 and t["ecart_gris"] < 2 and t["ecart_deuter"] < 2)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if x != "--casser"]
    {"page": cmd_page, "temoins": cmd_temoins}[args[0]](args[1:])
