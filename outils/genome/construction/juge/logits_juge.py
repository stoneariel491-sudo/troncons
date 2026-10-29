"""Les logits au bit (J-C1) : comparaison des empreintes de logits de deux passes `troncons evaluer`, et la
copie à biais retournés de la cassure.

Seuils : mesures/genome/construction/juge/00-seuils-declares.md, J-C1 (commit 1f5fe0f).

  python -I -X utf8 logits_juge.py comparer A.csv B.csv A.kld B.kld --nom N
      (fenetre, position) → empreinte64 des logits f32 ; compte les différentes ; argmax ; SHA-256 des .kld
  python -I -X utf8 logits_juge.py casser SOURCE.trc COPIE.trc
      copie octet pour octet, puis, pour les 32 experts de la couche 0, le bit de signe du biais f32 de la
      rangée 0 de la matrice 0 (flux BIAIS, brut) retourné ; journal des décalages touchés
"""
import hashlib
import json
import pathlib
import struct
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import decodeur_juge as dj  # noqa: E402

DEPOT = pathlib.Path(__file__).resolve().parents[4]
JOURNAUX = DEPOT / "mesures" / "genome" / "construction" / "juge" / "logits"


def sha(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest()


def lire_csv(ch):
    d = {}
    with open(ch, encoding="utf-8") as f:
        next(f)
        for l in f:
            fe, po, je, am, em = l.strip().split(",")
            d[(int(fe), int(po))] = (int(je), int(am), em)
    return d


def comparer(a, b, ka, kb, nom):
    A, B = lire_csv(a), lire_csv(b)
    cles = sorted(set(A) | set(B))
    manq = [k for k in cles if k not in A or k not in B]
    diff = [k for k in cles if k in A and k in B and A[k][2] != B[k][2]]
    diff_am = [k for k in cles if k in A and k in B and A[k][1] != B[k][1]]
    jetons_egaux = all(A[k][0] == B[k][0] for k in cles if k in A and k in B)
    sa, sb = sha(ka), sha(kb)
    r = {"a": str(a).replace("\\", "/"), "b": str(b).replace("\\", "/"), "pas": len(cles), "manquants": len(manq),
         "empreintes_differentes": len(diff), "argmax_differents": len(diff_am), "jetons_egaux": jetons_egaux,
         "premiere_difference": list(diff[0]) if diff else None, "kld_a_sha256": sa, "kld_b_sha256": sb, "kld_egaux": sa == sb,
         "csv_a_sha256": sha(a), "csv_b_sha256": sha(b)}
    JOURNAUX.mkdir(parents=True, exist_ok=True)
    (JOURNAUX / f"comparer-{nom}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(nom, r)
    return r


def casser(src, dst):
    src, dst = pathlib.Path(src), pathlib.Path(dst)
    with open(src, "rb") as fi, open(dst, "wb") as fo:
        while b := fi.read(1 << 24):
            fo.write(b)
    t = dj.Trc(src)
    rep, _ = t.repertoire()
    touches = []
    with open(dst, "r+b") as f:
        for x in range(t.E):
            e = rep[0 * t.E + x]
            tete = t.lire(e["decalage"], 64 + 16 * 12)
            nflux = struct.unpack_from("<H", tete, 10)[0]
            for i in range(nflux):
                sorte, mat, ctxf, res, off, lg, prod = struct.unpack_from("<BBBBIII", tete, 64 + 16 * i)
                if sorte == 2 and mat == 0:
                    pos = e["decalage"] + off + 3              # octet de poids fort du premier f32 (rangée 0)
                    f.seek(pos)
                    v = f.read(1)[0]
                    f.seek(pos)
                    f.write(bytes([v ^ 0x80]))
                    avant = struct.unpack("<f", t.lire(e["decalage"] + off, 4))[0]
                    touches.append({"expert": x, "decalage": pos, "biais_avant": avant})
    r = {"source": str(src).replace("\\", "/"), "copie": str(dst).replace("\\", "/"), "octets_touches": len(touches), "touches": touches}
    JOURNAUX.mkdir(parents=True, exist_ok=True)
    (JOURNAUX / "cassure-copie.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print({k: v for k, v in r.items() if k != "touches"}, touches[:3])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    if a and a[0] == "comparer":
        nom = a[a.index("--nom") + 1]
        comparer(a[1], a[2], a[3], a[4], nom)
    elif a and a[0] == "casser":
        casser(a[1], a[2])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
