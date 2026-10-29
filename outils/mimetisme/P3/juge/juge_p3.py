"""P3, juge indépendant : second chemin de l'étage A (routage biaisé vers les résidents du cache).

Critères : mesures/mimetisme/P3/juge/00-criteres-du-juge.md (commités avant la première exécution).
Rien n'est importé de l'outil de l'expérimentateur : lecteur GGUF, logits, cache et sélection sont réécrits ici.

Usage : python -I -X utf8 juge_p3.py logits | mesure
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "2"

try:  # priorité sous la normale (règle de cohabitation)
    import ctypes
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass

import json
import struct
import sys
import time

import numpy as np

GGUF = "~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf"
CAPTURE = "~/dev/essais/troncons/genome/eclaireur/eval"
LOURDS = "~/dev/essais/troncons/mimetisme/P3/juge"
VERROU = "~/dev/verrou-carte.txt"
ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.normpath(os.path.join(ICI, "..", "..", "..", "..", "mesures", "mimetisme", "P3", "juge"))
D, L, E, K = 2880, 24, 32, 4


# ------------------------------------------------------------------ lecteur GGUF minimal (écrit pour ce jugement)

def lire_gguf_index(chemin):
    """Rend (alignement, début des données, {nom: (dims, type, décalage)})."""
    f = open(chemin, "rb")
    lu = lambda fmt: struct.unpack("<" + fmt, f.read(struct.calcsize("<" + fmt)))[0]
    def chaine():
        n = lu("Q")
        return f.read(n).decode("utf-8", "replace")
    tailles = {0: "B", 1: "b", 2: "H", 3: "h", 4: "I", 5: "i", 6: "f", 7: "?", 10: "Q", 11: "q", 12: "d"}
    def valeur(t):
        if t in tailles:
            return lu(tailles[t])
        if t == 8:
            return chaine()
        if t == 9:
            st, n = lu("I"), lu("Q")
            return [valeur(st) for _ in range(n)]
        raise ValueError(f"type GGUF inconnu {t}")
    assert f.read(4) == b"GGUF"
    version, nt, nkv = lu("I"), lu("Q"), lu("Q")
    meta = {}
    for _ in range(nkv):
        k = chaine()
        t = lu("I")
        v = valeur(t)
        if not isinstance(v, list) or len(v) < 64:
            meta[k] = v
    tens = {}
    for _ in range(nt):
        nom = chaine()
        nd = lu("I")
        dims = [lu("Q") for _ in range(nd)]
        typ, dec = lu("I"), lu("Q")
        tens[nom] = (dims, typ, dec)
    al = int(meta.get("general.alignment", 32))
    pos = f.tell()
    debut = (pos + al - 1) // al * al
    f.close()
    return version, meta, debut, tens


def tenseur_f32(chemin, debut, info):
    dims, typ, dec = info
    assert typ == 0, f"attendu F32, type {typ}"
    n = int(np.prod(dims))
    return np.fromfile(chemin, dtype="<f4", count=n, offset=debut + dec).reshape(list(reversed(dims)))


# ------------------------------------------------------------------ logits

def cmd_logits():
    if os.path.exists(VERROU):
        print("verrou de la carte présent : pas de lecture lourde")
        return 3
    os.makedirs(LOURDS, exist_ok=True)
    version, meta, debut, tens = lire_gguf_index(GGUF)
    assert int(meta["gpt-oss.block_count"]) == L and int(meta["gpt-oss.expert_count"]) == E
    T = os.path.getsize(f"{CAPTURE}/h-L00.f32") // (4 * D)
    Z = np.empty((T, L, E))
    Zsb = np.empty((T, L, E))
    R = np.empty((T, L, K), dtype=np.int64)
    P = np.empty((T, L, K))
    t0 = time.time()
    for l in range(L):
        W = tenseur_f32(GGUF, debut, tens[f"blk.{l}.ffn_gate_inp.weight"]).astype(np.float64)  # (32, 2880)
        b = tenseur_f32(GGUF, debut, tens[f"blk.{l}.ffn_gate_inp.bias"]).astype(np.float64)
        assert W.shape == (E, D) and b.shape == (E,)
        h = np.memmap(f"{CAPTURE}/h-L{l:02d}.f32", dtype="<f4", mode="r", shape=(T, D))
        Zsb[:, l, :] = np.einsum("td,ed->te", np.asarray(h, dtype=np.float64), W, optimize=True)
        Z[:, l, :] = Zsb[:, l, :] + b
        del h
        brut = np.fromfile(f"{CAPTURE}/routage-L{l:02d}.bin", dtype=np.uint8).reshape(T, 20)
        R[:, l, :] = brut[:, :4]
        P[:, l, :] = brut[:, 4:].copy().view("<f4").reshape(T, 4)
    np.save(f"{LOURDS}/Z.npy", Z)
    # accord avec la capture, et cassure sans biais
    top = np.argpartition(-Z, K - 1, axis=-1)[..., :K]
    acc = (np.sort(top, -1) == np.sort(R, -1)).all(-1)
    top2 = np.argpartition(-Zsb, K - 1, axis=-1)[..., :K]
    acc2 = (np.sort(top2, -1) == np.sort(R, -1)).all(-1)
    zr = np.take_along_axis(Z, R, -1)
    w = np.exp(zr - zr.max(-1, keepdims=True)); w /= w.sum(-1, keepdims=True)
    res = {"gguf_version": version, "T": T, "duree_s": time.time() - t0,
           "accord_capture": float(acc.mean()), "desaccords": int((~acc).sum()),
           "accord_sans_biais_routeur": float(acc2.mean()),
           "ecart_poids_max": float(np.abs(w - P)[acc].max()),
           "somme_poids_capture_min_max": [float(P.sum(-1).min()), float(P.sum(-1).max())]}
    print(json.dumps(res, indent=1))
    json.dump(res, open(f"{SORTIE}/01-accord.json", "w", encoding="utf-8"), indent=1)
    return 0


# ------------------------------------------------------------------ cache LRU à horodatage

def passe(Z, ordre, N, beta, variante="V1", masque="residents", ordre_groupe="decroissant", epingle=True, graine=99):
    """Rend (ensembles (T,L,4), défauts). Résidents de décision = cache juste avant le groupe."""
    T = Z.shape[0]
    date = np.full(L * E, np.inf)      # inf = absent
    resid = np.zeros(L * E, dtype=bool)
    n_res = 0
    horloge = 0.0
    defauts = 0
    S = np.empty((T, L, K), dtype=np.int16)
    rng = np.random.default_rng(graine)
    for t in range(T):
        for l in range(L):
            z = Z[t, l]
            base = l * E
            if beta == 0.0:
                ch = ordre[t, l, :K]
            else:
                r = resid[base:base + E].astype(np.float64)
                if masque == "hasard":
                    r = (rng.random(E) < r.mean()).astype(np.float64)
                if variante == "V1":
                    zb = z + beta * r
                    ch = np.argpartition(-zb, K - 1)[:K]
                else:
                    a, c = ordre[t, l, K - 1], ordre[t, l, K]
                    pris = c if z[c] + beta * r[c] > z[a] + beta * r[a] else a
                    ch = np.array([ordre[t, l, 0], ordre[t, l, 1], ordre[t, l, 2], pris])
                ch = ch[np.argsort(-z[ch])]
            if ordre_groupe == "croissant":
                ch = ch[::-1]
            S[t, l] = ch
            g = [base + int(e) for e in ch]
            for x in g:
                horloge += 1.0
                if resid[x]:
                    date[x] = horloge
                    continue
                defauts += 1
                if n_res >= N:
                    if epingle:
                        sauve = date[g].copy()
                        date[g] = np.inf
                        v = int(np.argmin(date))
                        date[g] = sauve
                    else:
                        v = int(np.argmin(date))
                    resid[v] = False
                    date[v] = np.inf
                    n_res -= 1
                resid[x] = True
                date[x] = horloge
                n_res += 1
    return S, defauts


def part_changee(S0, S):
    return float((np.sort(S0, -1) != np.sort(S, -1)).any(-1).mean())


def cmd_mesure():
    Z = np.load(f"{LOURDS}/Z.npy")
    T = Z.shape[0]
    ordre = np.argsort(-Z, axis=-1)
    journal = []
    log = lambda s: (journal.append(s), print(s, flush=True))
    out = {"lignes": []}
    t0 = time.time()
    for nom, N in (("19", round(0.19 * L * E)), ("31", round(0.31 * L * E))):
        S0, d0 = passe(Z, ordre, N, 0.0)
        log(f"N={N} beta=0 : défauts {d0}")
        out[f"defauts0_{nom}"] = d0
        for variante, beta, masque in [("V1", b, "residents") for b in (0.01, 0.03, 0.04, 0.05, 0.06, 0.07, 0.1, 0.3, -0.1)] + \
                                      [("V2", 0.1, "residents"), ("V1", 0.1, "hasard")]:
            S, d = passe(Z, ordre, N, beta, variante, masque)
            pc = part_changee(S0, S)
            ligne = {"N": N, "variante": variante, "beta": beta, "masque": masque, "defauts": d,
                     "variation": d / d0 - 1, "part_changee": pc, "kl_prior_0309": 0.309 * pc, "kl_prior_racines_0755": 0.755 * pc}
            out["lignes"].append(ligne)
            log(f"  {variante} {masque:9s} beta={beta:+.2f} : {d} ({(d / d0 - 1) * 100:+.2f} %), changées {pc * 100:.2f} %, "
                f"KLp {0.309 * pc:.4f} / racines {0.755 * pc:.4f}")
            if variante == "V1" and masque == "residents" and beta == 0.06 and nom == "19":
                sonde_s2(Z, ordre, S0, S, out, log)
        # cassures du cache
        _, dc = passe(Z, ordre, N, 0.0, ordre_groupe="croissant")
        _, de = passe(Z, ordre, N, 0.0, epingle=False)
        out[f"cassure_ordre_{nom}"] = dc
        out[f"cassure_sans_epingle_{nom}"] = de
        log(f"  cassure ordre croissant : {dc} ({'change' if dc != d0 else 'IDENTIQUE'}) ; sans épinglage : {de} ({'change' if de != d0 else 'IDENTIQUE'})")
    out["duree_s"] = time.time() - t0
    json.dump(out, open(f"{SORTIE}/02-mesure.json", "w", encoding="utf-8"), indent=1)
    open(f"{SORTIE}/02-mesure.log", "w", encoding="utf-8").write("\n".join(journal) + "\n")
    return 0


def sonde_s2(Z, ordre, S0, S, out, log):
    """Cellules changées : écart de logit retiré - ajouté, poids softmax (z non biaisé, parmi les 4 d'origine) du retiré.
    En regard : échange 4e/5e des cellules à marge < 0,0095."""
    ch = (np.sort(S0, -1) != np.sort(S, -1)).any(-1)
    ecarts, poids = [], []
    for t, l in zip(*np.nonzero(ch)):
        a, b = set(S0[t, l].tolist()), set(S[t, l].tolist())
        z = Z[t, l]
        z0 = z[list(S0[t, l])]
        w0 = np.exp(z0 - z0.max()); w0 /= w0.sum()
        for x, y in zip(sorted(a - b), sorted(b - a)):
            ecarts.append(z[x] - z[y])
            poids.append(float(w0[list(S0[t, l]).index(x)]))
    ecarts, poids = np.array(ecarts), np.array(poids)
    marge = np.take_along_axis(Z, ordre[..., K - 1:K], -1)[..., 0] - np.take_along_axis(Z, ordre[..., K:K + 1], -1)[..., 0]
    sel = marge < 0.0095
    z4 = np.take_along_axis(Z, ordre[..., :K], -1)
    w4 = np.exp(z4 - z4.max(-1, keepdims=True)); w4 /= w4.sum(-1, keepdims=True)
    w4s = w4[..., K - 1][sel]
    q = lambda v: {k: float(np.quantile(v, p)) for k, p in (("q10", .1), ("med", .5), ("q90", .9))} | {"moy": float(v.mean()), "moy_carre": float((v ** 2).mean())}
    r = {"forcees_ecart_logit": q(ecarts), "forcees_poids_retire": q(poids), "n_echanges": int(len(poids)),
         "subies_proxy_marge": q(marge[sel]), "subies_proxy_poids_4e": q(w4s), "n_subies_proxy": int(sel.sum())}
    out["S2"] = r
    log(f"  S2 forcées : écart médian {r['forcees_ecart_logit']['med']:.4f}, poids retiré médian {r['forcees_poids_retire']['med']:.4f} "
        f"(moy carré {r['forcees_poids_retire']['moy_carre']:.4f}) ; subies (marge<0,0095) : poids 4e médian {r['subies_proxy_poids_4e']['med']:.4f} "
        f"(moy carré {r['subies_proxy_poids_4e']['moy_carre']:.4f})")


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"logits": cmd_logits, "mesure": cmd_mesure}.get(c, lambda: (print(__doc__), 2)[1])())
