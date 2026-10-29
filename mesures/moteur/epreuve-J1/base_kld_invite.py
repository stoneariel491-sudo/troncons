"""Fabrique un .kld de base d'UNE fenêtre de n jetons donnés (format de llama-perplexity), pour que
`troncons evaluer` passe ces jetons depuis la position 0 et écrive l'argmax de chaque position.
Les entrées notées sont une distribution uniforme (pas = 0, log p = −ln V) : elles ne servent pas.
Commande : python -I -X utf8 base_kld_invite.py <ids.txt (liste Python)> <sortie.kld> [V=201088]
"""
import ast
import math
import struct
import sys

ids = ast.literal_eval(open(sys.argv[1]).read().strip().splitlines()[-1])
V = int(sys.argv[3]) if len(sys.argv) > 3 else 201088
n = len(ids)
nv = 2 * ((V + 1) // 2) + 4
entrees = n - 1 - n // 2
with open(sys.argv[2], "wb") as f:
    f.write(b"_logits_" + struct.pack("<Iii", n, V, 1))
    f.write(struct.pack(f"<{n}i", *ids))
    une = struct.pack("<ff", 0.0, -math.log(V)) + bytes(2 * (nv - 4))
    for _ in range(entrees):
        f.write(une)
print(n, entrees, nv)
