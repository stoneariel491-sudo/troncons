"""Écrit les enveloppes des quatre pilotes du Tome III (FR et EN) sous memoire/essai/construction-tomes/pilotes/.
Chaque enveloppe \\input le pilote commité par son chemin absolu : la compilation se fait dans ce dossier,
loin de memoire/essai/, et ne peut ni écraser ni effacer les PDF des pilotes des autres agents."""
import pathlib

ESSAI = "~/dev/active/troncons/memoire/essai"
SORTIE = pathlib.Path(ESSAI) / "construction-tomes" / "pilotes"
SORTIE.mkdir(parents=True, exist_ok=True)
for lot in ("commun", "construction", "ronde", "latents"):
    source = f"{ESSAI}/pilote-tome3-{lot}.tex"
    (SORTIE / f"p-{lot}-fr.tex").write_text("\\input{" + source + "}\n", encoding="utf-8")
    (SORTIE / f"p-{lot}-en.tex").write_text("\\def\\ANGLAIS{1}\\input{" + source + "}\n", encoding="utf-8")
print(sorted(p.name for p in SORTIE.glob("*.tex")))
