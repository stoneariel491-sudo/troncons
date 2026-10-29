# Juge de la troisième passe : extrait du préambule commité (memoire/commun/preambule.tex, tel que dans git HEAD)
# les lignes des deux correctifs, mot pour mot, vers deux fichiers à \input dans mes documents d'essai ; écrit aussi
# le préambule d'avant 7db2673 (git show 7db2673^:...) pour les témoins. Rien n'est retapé à la main.
# Usage : python -I -X utf8 extraire_correctifs.py DOSSIER_SORTIE
import subprocess, sys
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[4]
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)


def show(ref: str) -> list[str]:
    t = subprocess.run(["git", "-C", str(DEPOT), "show", f"{ref}:memoire/commun/preambule.tex"],
                       capture_output=True, check=True).stdout.decode("utf-8")
    return t.splitlines()


tete = show("HEAD")
# Correctif A : de « \ifdefined\newcounteralias » au « \fi » qui le ferme (premier bloc), puis la ligne de remise.
i = next(k for k, l in enumerate(tete) if l.strip() == r"\ifdefined\newcounteralias")
j = next(k for k in range(i + 1, len(tete)) if tete[k].strip() == r"\fi")
remise = [l for l in tete if l.strip().startswith(r"\ifdefined\AliasCompteurNoyau")]
assert len(remise) == 1
(sortie / "correctif-a-pose.tex").write_text("\n".join(tete[i:j + 1]) + "\n", encoding="utf-8")
(sortie / "correctif-a-remise.tex").write_text(remise[0] + "\n", encoding="utf-8")
# Correctif B : de « \ifdefined\textsuperscript@offset » à son « \fi », entouré de \makeatletter / \makeatother.
i = next(k for k, l in enumerate(tete) if l.strip() == r"\ifdefined\textsuperscript@offset")
j = next(k for k in range(i + 1, len(tete)) if tete[k].strip() == r"\fi")
(sortie / "correctif-b.tex").write_text("\\makeatletter\n" + "\n".join(tete[i:j + 1]) + "\n\\makeatother\n",
                                        encoding="utf-8")
# Le préambule d'avant les deux correctifs, et celui de HEAD, pour les témoins des pilotes.
(sortie / "preambule-avant.tex").write_text("\n".join(show("7db2673^")) + "\n", encoding="utf-8")
(sortie / "preambule-tete.tex").write_text("\n".join(tete) + "\n", encoding="utf-8")
for f in sorted(sortie.glob("*.tex")):
    print(f.name, len(f.read_text(encoding="utf-8").splitlines()), "lignes")
