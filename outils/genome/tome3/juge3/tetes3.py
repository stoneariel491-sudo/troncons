# Juge de la troisième passe : DN1 au rendu. Pour chaque légende des pilotes (bloc « Figure 1.n »), prend la tête (du
# début jusqu'à l'étiquette de provenance « [mes. », « [calc. », « [schém », « [meas. », « [schem ») et relève chaque
# morceau de texte qui porte un chiffre ou un symbole mathématique, avec sa police et son épaisseur de tracé : une
# police « Bold » est grasse ; une police mathématique est grasse si elle est épaissie (FakeBold de luaotfload : rendu
# « remplir et tracer », relevé par le mode de rendu du texte dans le flux de la page, faute de mieux par PyMuPDF).
# Usage : python -I -X utf8 tetes3.py PDF...
import json, re, sys
import fitz

PROV = re.compile(r"\[(mes|calc|sch|meas|schem)")
res = {}
for pdf in sys.argv[1:]:
    D = fitz.open(pdf)
    for i, pg in enumerate(D):
        d = pg.get_text("rawdict")
        spans = [s for b in d["blocks"] for l in b.get("lines", []) for s in l["spans"]]
        texte = "".join("".join(c["c"] for c in s["chars"]) for s in spans)
        k = texte.find("Figure 1.")
        if k < 0 or texte[k:k + 40].find(":") < 0:
            continue
        # parcours des morceaux à partir de « Figure 1.n : » jusqu'à la provenance
        pos, dans, fini, maigres, gras = 0, False, False, [], []
        for s in spans:
            t = "".join(c["c"] for c in s["chars"])
            if not dans and t.startswith("Figure 1."):
                dans = True
                continue
            if dans and not fini:
                if PROV.search(t):
                    fini = True
                    continue
                if re.search(r"[0-9λκ×±∗*=√%−+]", t) or "Math" in s["font"]:
                    gr = "Bold" in s["font"] or bool(s["flags"] & 16)
                    (gras if gr else maigres).append((t.strip()[:30], s["font"]))
        if dans:
            res[f"{pdf.split('/')[-1]} p.{i + 1}"] = {"maigres": maigres, "gras": len(gras)}
print(json.dumps(res, ensure_ascii=False, indent=1))
