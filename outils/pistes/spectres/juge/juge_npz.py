"""Juge de la piste « spectres » : les spectres du npz viennent-ils bien du modèle ?

Pour deux matrices fixées d'avance (L00.down.E24, la queue la plus lourde ; L23.attn_q, compatible
de α̂ < 2) : octets lus par le lecteur GGUF du projet (seul point commun avec la piste), puis
déquantification écrite par le juge depuis la spécification (OCP MX v1.0 : E2M1 = signe, 2 bits
d'exposant de biais 1, 1 bit de mantisse ; échelle E8M0 = 2^(e − 127) ; Q8_0 = f16 d puis 32 int8),
empreinte SHA-256 des octets f64 comparée au manifeste, valeurs singulières comparées au npz.
Lancé seulement quand le verrou ne nomme aucune séance de vitesse.
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(ICI))
import commun  # noqa: E402  (lecteur GGUF et index des tenseurs seulement)
from juge_csn import priorite_inactive, seance_de_vitesse  # noqa: E402

RACINE = ICI.parents[3]
M = RACINE / "mesures/pistes/spectres"


def e2m1(code):
    s = np.where(code & 8, -1.0, 1.0)
    e = (code >> 1) & 3
    m = code & 1
    val = np.where(e == 0, 0.5 * m, (1.0 + 0.5 * m) * np.ldexp(1.0, e.astype(np.int64) - 1))
    return s * val


def mxfp4_juge(lec, t, expert):
    colonnes, lignes, ne = t.dims
    o = np.asarray(lec.octets(t))
    tr = o.size // ne
    b = o[expert * tr:(expert + 1) * tr].reshape(-1, 17)
    echelle = np.ldexp(1.0, b[:, 0].astype(np.int64) - 127)
    qs = b[:, 1:].astype(np.int64)
    codes = np.concatenate([qs & 15, qs >> 4], axis=1)
    return (e2m1(codes) * echelle[:, None]).reshape(lignes, colonnes)


def q80_juge(lec, t):
    colonnes, lignes = t.dims
    o = np.asarray(lec.octets(t)).reshape(-1, 34)
    d = np.frombuffer(o[:, :2].tobytes(), dtype="<f2").astype(np.float64)
    q = np.frombuffer(o[:, 2:].tobytes(), dtype=np.int8).astype(np.float64).reshape(-1, 32)
    return (q * d[:, None]).reshape(lignes, colonnes)


def main():
    priorite_inactive()
    if seance_de_vitesse():
        print("séance de vitesse en cours : rien n'est lu")
        return
    man = {m["id"]: m for m in json.loads((M / "manifeste.json").read_text(encoding="utf-8"))["matrices"]}
    z = np.load(M / "valeurs-singulieres.npz")
    lec = commun.lecteur()
    index = {t.nom: t for t in lec.tenseurs}
    lignes = []
    for ident in ("L00.down.E24", "L23.attn_q"):
        m = man[ident]
        t = index[m["tenseur"]]
        if m["expert"] >= 0:
            # -0,0 -> +0,0 : l'empreinte publiée est celle de la table (zéros positifs)
            w = mxfp4_juge(lec, t, m["expert"]) + 0.0
        else:
            w = q80_juge(lec, t)
        sha = hashlib.sha256(np.ascontiguousarray(w).tobytes()).hexdigest()
        s = np.linalg.svd(w, compute_uv=False)
        ref = z["reel/" + ident]
        k = 400
        ecart = float(np.max(np.abs(s[:k] - ref[:k]) / ref[:k]))
        ligne = (f"{ident:14s} forme {w.shape} sha {'ÉGALE' if sha == m['sha256_f64'] else 'DIFFÉRENTE'} "
                 f"; valeurs singulières, écart relatif max sur les {k} premières {ecart:.2e} "
                 f"; sigma1 {s[0]:.6f} (npz {ref[0]:.6f})")
        print(ligne, flush=True)
        lignes.append(ligne)
    (M / "juge" / "juge-npz.log").write_text("\n".join(lignes) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
