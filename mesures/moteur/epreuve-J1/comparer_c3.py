"""C3 par le chemin du juge : .kld et empreintes de logits, codé contre brut, et contre le lot O.

Les .kld du juge (n fenêtres) sont comparés octet pour octet entre eux, puis à la même tranche des
.kld du lot O (10 fenêtres, boucle de pas) : en-tête recalculé pour n fenêtres, jetons des n
premières fenêtres, entrées des n premières fenêtres. Les empreintes CSV ligne pour ligne.
Commande : python -I -X utf8 comparer_c3.py <code.kld> <brut.kld> <code.csv> <brut.csv>
           <O-code.kld> <O-brut.kld> <O-code.csv> <journal.json>
"""
import hashlib
import json
import struct
import sys

code, brut, ccsv, bcsv, ocode, obrut, ocsv, journal = sys.argv[1:9]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest()


def tranche(p, n):
    """Les octets qu'aurait un .kld de n fenêtres tiré de p (10 fenêtres)."""
    with open(p, "rb") as f:
        t = f.read(20)
        n_ctx, V, n_chunk = struct.unpack("<Iii", t[8:20])
        jet = f.read(4 * n_ctx * n_chunk)
        nv = 2 * ((V + 1) // 2) + 4
        par = (n_ctx - 1 - n_ctx // 2) * nv * 2
        h = hashlib.sha256()
        h.update(t[:8] + struct.pack("<Iii", n_ctx, V, n))
        h.update(jet[:4 * n_ctx * n])
        reste = par * n
        while reste:
            b = f.read(min(reste, 1 << 24))
            h.update(b)
            reste -= len(b)
        return h.hexdigest()


def lignes(p):
    return open(p, encoding="utf-8").read().splitlines()


with open(code, "rb") as f:
    n = struct.unpack("<Iii", f.read(20)[8:20])[2]
r = {"fenetres": n, "sha_code": sha(code), "sha_brut": sha(brut)}
r["kld_code_egal_brut"] = r["sha_code"] == r["sha_brut"]
lc, lb, lo = lignes(ccsv), lignes(bcsv), lignes(ocsv)
r["pas"] = len(lc) - 1
r["empreintes_differentes_code_brut"] = sum(a != b for a, b in zip(lc[1:], lb[1:])) + abs(len(lc) - len(lb))
r["entetes_csv"] = [lc[0], lo[0]]
r["empreintes_differentes_juge_lotO"] = sum(a != b for a, b in zip(lc[1:], lo[1:len(lc)]))
r["sha_tranche_lotO_code"] = tranche(ocode, n)
r["sha_tranche_lotO_brut"] = tranche(obrut, n)
r["kld_juge_flux_egal_lotO_boucle"] = r["sha_code"] == r["sha_tranche_lotO_code"]
json.dump(r, open(journal, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(r, ensure_ascii=False, indent=1))
