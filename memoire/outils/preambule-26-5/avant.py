"""Témoin « avant » : le pilote commun compilé sous MiKTeX 26.5 avec le préambule d'avant le correctif
(git show 7db2673~1:memoire/commun/preambule.tex, le dernier avant le correctif A, copié en preambule-avant.tex). Il doit lever six erreurs."""
import pathlib
import subprocess

R = pathlib.Path("~/dev/active/troncons")
C = R / "memoire/essai/construction-tomes"
avant = subprocess.run(["git", "-C", str(R), "show", "7db2673~1:memoire/commun/preambule.tex"],
                       capture_output=True, check=True).stdout
(C / "preambule-avant.tex").write_bytes(avant)
pilote = (R / "memoire/essai/pilote-tome3-commun.tex").read_text(encoding="utf-8")
ancien = "\\input{~/dev/active/troncons/memoire/commun/preambule}"
assert pilote.count(ancien) == 1, "chemin du préambule introuvable dans le pilote"
neuf = "\\input{~/dev/active/troncons/memoire/essai/construction-tomes/preambule-avant}"
(C / "pilotes/p-commun-avant.tex").write_text(pilote.replace(ancien, neuf), encoding="utf-8")
print("écrit :", C / "preambule-avant.tex", C / "pilotes/p-commun-avant.tex")
