"""§ 4.13 : le compagnon <nom>.vocab.gguf est un GGUF v3 valide, n_tenseurs = 0, toutes les paires
du source octet pour octet, aucune donnée. Lecteur GGUF de decodeur_s4.py (écrit ici).
Commande : python -I -X utf8 verifier_vocab.py <vocab.gguf> <source.gguf>"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decodeur_s4 import Gguf  # noqa: E402

v, s = Gguf(sys.argv[1]), Gguf(sys.argv[2])
taille = os.path.getsize(sys.argv[1])
r = {"vocab": sys.argv[1], "version": v.version, "n_tenseurs": v.n_tenseurs, "n_kv": v.n_kv,
     "n_kv_source": s.n_kv,
     "paires_octet_pour_octet": v.tete[v.debut_kv:v.fin_kv] == s.tete[s.debut_kv:s.fin_kv],
     "taille": taille, "fin_kv": v.fin_kv, "octets_apres_paires": taille - v.fin_kv}
r["tient"] = (r["version"] == 3 and r["n_tenseurs"] == 0 and r["n_kv"] == r["n_kv_source"]
              and r["paires_octet_pour_octet"])
print(json.dumps(r, ensure_ascii=False))
