"""Entropie réelle des poids quantifiés d'un GGUF, champ par champ.

Pour chaque tenseur quantifié (Q4_K, Q5_K, Q6_K, Q8_0) :
  - H0(code)        : entropie d'ordre 0 des codes entiers, table par tenseur ;
  - H(code|préc.)   : entropie conditionnelle au code précédent (ordre logique) ;
  - H(code|échelle) : conditionnelle à l'échelle 6 bits de son sous-bloc ;
  - H des champs de métadonnées (d, dmin en fp16 vus comme u16 ; exposant et
    mantisse de d séparés ; échelles et minimums 6 bits ; échelles int8) ;
  - H0 des octets bruts (ce que voit un codeur d'octets générique) ;
  - zstd (niveau 3 et 19 sur un échantillon) et lz4 : taux et débit de
    décompression sur un fil du processeur (meilleur de 3 passes).
Pour les tenseurs F32 : entropie du signe, de l'exposant et de la mantisse.

Toutes les entropies sont des estimations « plug-in » (fréquences observées) :
elles sous-estiment de (K-1)/(2 N ln 2) bits au plus ; le terme est écrit dans
le journal quand il dépasse 0,001 bit.

Usage : python mesure_entropie.py <fichier.gguf> <sortie.json> [--sans-zstd]
"""
from __future__ import annotations

import json
import re
import sys
import time

import lz4.frame
import numpy as np
import zstandard

import champs_k
from gguf_lecture import LecteurGGUF

PAQUET = 1 << 16   # blocs traités à la fois


def entropie(hist: np.ndarray) -> float:
    n = hist.sum()
    if n == 0:
        return 0.0
    p = hist[hist > 0] / n
    return float(-(p * np.log2(p)).sum())


def entropie_cond(joint: np.ndarray) -> float:
    """joint[a, b] : H(B | A) = H(A,B) - H(A)."""
    return entropie(joint.ravel()) - entropie(joint.sum(axis=1))


def longueur_huffman(hist: np.ndarray) -> float:
    """Longueur moyenne (bits/symbole) d'un code de Huffman optimal sur hist."""
    import heapq
    feuilles = [i for i, c in enumerate(hist) if c > 0]
    if len(feuilles) <= 1:
        return 1.0
    parent = {}
    tas = [(int(hist[i]), ("f", i)) for i in feuilles]
    heapq.heapify(tas)
    k = 0
    while len(tas) > 1:
        c1, n1 = heapq.heappop(tas)
        c2, n2 = heapq.heappop(tas)
        noeud = ("n", k)
        k += 1
        parent[n1] = noeud
        parent[n2] = noeud
        heapq.heappush(tas, (c1 + c2, noeud))
    prof = {}

    def profondeur(n):
        if n not in parent:
            return 0
        if n not in prof:
            prof[n] = profondeur(parent[n]) + 1
        return prof[n]

    total = sum(int(hist[i]) * profondeur(("f", i)) for i in feuilles)
    return total / float(hist.sum())


def biais(hist: np.ndarray) -> float:
    k = int((hist > 0).sum())
    n = int(hist.sum())
    return (k - 1) / (2 * n * np.log(2)) if n else 0.0


def chrono_decomp(fonction, donnees, passes=3) -> float:
    meilleur = float("inf")
    for _ in range(passes):
        t0 = time.perf_counter()
        fonction(donnees)
        meilleur = min(meilleur, time.perf_counter() - t0)
    return meilleur


def mesurer_compresseurs(brut: bytes, avec_z19: bool) -> dict:
    r = {}
    cz = zstandard.ZstdCompressor(level=3)
    dz = zstandard.ZstdDecompressor()
    z = cz.compress(brut)
    t = chrono_decomp(dz.decompress, z)
    r["zstd3"] = {"taux": len(brut) / len(z), "decomp_Go_s_1fil": len(brut) / t / 1e9}
    l4 = lz4.frame.compress(brut)
    t = chrono_decomp(lz4.frame.decompress, l4)
    r["lz4"] = {"taux": len(brut) / len(l4), "decomp_Go_s_1fil": len(brut) / t / 1e9}
    if not avec_z19:
        return r
    # zstd 19 sur un échantillon de 16 Mo : le taux plafond d'un LZ + huff0/FSE
    ech = brut[: 16 << 20]
    z19 = zstandard.ZstdCompressor(level=19).compress(ech)
    t = chrono_decomp(dz.decompress, z19)
    r["zstd19_echantillon16Mo"] = {"taux": len(ech) / len(z19),
                                   "decomp_Go_s_1fil": len(ech) / t / 1e9}
    return r


def mesurer_quantifie(L, t, avec_zstd: bool) -> dict:
    decoupe, taille = champs_k.DECOUPEURS[t.nom_type]
    brut = L.octets(t)
    nb_blocs = t.nb_octets // taille
    K = 1 << {"Q4_K": 4, "Q5_K": 5, "Q6_K": 6, "Q8_0": 8, "MXFP4": 4}[t.nom_type]
    h_code = np.zeros(K, np.int64)
    h_paire = np.zeros(K * K, np.int64)
    h_ech_code = (np.zeros(64 * K, np.int64) if t.nom_type in ("Q4_K", "Q5_K")
                  else np.zeros(256 * K, np.int64) if t.nom_type == "MXFP4" else None)
    h_d = np.zeros(65536, np.int64)
    h_dmin = np.zeros(65536, np.int64)
    h_ech = np.zeros(256, np.int64)
    h_min = np.zeros(256, np.int64)
    h_octet = np.zeros(256, np.int64)
    for i in range(0, nb_blocs, PAQUET):
        blocs = np.asarray(brut[i * taille: min(nb_blocs, i + PAQUET) * taille]).reshape(-1, taille)
        h_octet += np.bincount(blocs.ravel(), minlength=256)
        f = decoupe(blocs)
        c = f["codes"]
        h_code += np.bincount(c.ravel(), minlength=K)
        paires = c[:, :-1].astype(np.int64) * K + c[:, 1:]
        h_paire += np.bincount(paires.ravel(), minlength=K * K)
        h_d += np.bincount(f["d"], minlength=65536)
        if "dmin" in f:
            h_dmin += np.bincount(f["dmin"], minlength=65536)
        if t.nom_type in ("Q4_K", "Q5_K"):
            h_ech += np.bincount(f["echelles"].ravel(), minlength=256)
            h_min += np.bincount(f["minimums"].ravel(), minlength=256)
            ech32 = np.repeat(f["echelles"], 32, axis=1).astype(np.int64)
            h_ech_code += np.bincount((ech32 * K + c).ravel(), minlength=64 * K)
        elif t.nom_type == "Q6_K":
            h_ech += np.bincount(f["echelles"].ravel(), minlength=256)
        elif t.nom_type == "MXFP4":
            e32 = np.repeat(f["d"][:, None].astype(np.int64), 32, axis=1)
            h_ech_code += np.bincount((e32 * K + c).ravel(), minlength=256 * K)

    n_poids = t.nb_poids
    # exposant (5 bits) et mantisse (10 bits) de d en fp16
    valeurs = np.nonzero(h_d)[0]
    expo = np.bincount((valeurs >> 10) & 0x1F, weights=h_d[valeurs], minlength=32)
    mant = np.bincount(valeurs & 0x3FF, weights=h_d[valeurs], minlength=1024)
    r = {
        "nom": t.nom, "type": t.nom_type, "dims": list(t.dims),
        "octets": t.nb_octets, "poids": n_poids, "blocs": nb_blocs,
        "bits_par_poids_stockes": t.nb_octets * 8 / n_poids,
        "H0_code": entropie(h_code),
        "H_code_sachant_precedent": entropie_cond(h_paire.reshape(K, K)),
        "H_d_u16": entropie(h_d), "H_d_exposant": entropie(expo),
        "H_d_mantisse": entropie(mant),
        "biais_H_d": biais(h_d),
        "H0_octet": entropie(h_octet),
        "L_huffman_code": longueur_huffman(h_code),
        "L_huffman_paire": longueur_huffman(h_paire) / 2,
        "H0_paire_par_code": entropie(h_paire) / 2,
        "histogramme_code": h_code.tolist(),
    }
    if t.nom_type == "MXFP4":
        r["H_code_sachant_echelle"] = entropie_cond(h_ech_code.reshape(256, K))
        bits_ideaux = n_poids * r["H0_code"] + nb_blocs * r["H_d_u16"]
        r["bits_ideaux_cond_echelle_par_poids"] = (bits_ideaux - n_poids * (r["H0_code"] - r["H_code_sachant_echelle"])) / n_poids
    elif h_ech_code is not None:
        r["H_code_sachant_echelle"] = entropie_cond(h_ech_code.reshape(64, K))
        r["H_dmin_u16"] = entropie(h_dmin)
        r["H_echelle6"] = entropie(h_ech)
        r["H_minimum6"] = entropie(h_min)
        sous_blocs = nb_blocs * 8
        bits_ideaux = (n_poids * r["H0_code"] + nb_blocs * (r["H_d_u16"] + r["H_dmin_u16"])
                       + sous_blocs * (r["H_echelle6"] + r["H_minimum6"]))
        bits_ideaux_cond = bits_ideaux - n_poids * (r["H0_code"] - r["H_code_sachant_echelle"])
        r["bits_ideaux_cond_echelle_par_poids"] = bits_ideaux_cond / n_poids
    elif t.nom_type == "Q6_K":
        r["H_echelle8"] = entropie(h_ech)
        bits_ideaux = n_poids * r["H0_code"] + nb_blocs * (r["H_d_u16"] + 16 * r["H_echelle8"])
    else:
        bits_ideaux = n_poids * r["H0_code"] + nb_blocs * r["H_d_u16"]
    r["bits_ideaux_ordre0_par_poids"] = bits_ideaux / n_poids
    r["taux_ideal_ordre0"] = t.nb_octets * 8 / bits_ideaux
    if avec_zstd:
        z19 = not t.nom.startswith("blk.") or t.nom.startswith(("blk.0.", "blk.3.", "blk.16."))
        r["compresseurs"] = mesurer_compresseurs(bytes(brut), z19)
    return r


def mesurer_f32(L, t) -> dict:
    v = np.asarray(L.octets(t)).view(np.uint32)
    return {"nom": t.nom, "type": "F32", "poids": t.nb_poids, "octets": t.nb_octets,
            "H_signe": entropie(np.bincount(v >> 31, minlength=2)),
            "H_exposant8": entropie(np.bincount((v >> 23) & 0xFF, minlength=256)),
            "H_exposant_bf16_mantisse7": entropie(np.bincount((v >> 16) & 0x7F, minlength=128))}


def main():
    chemin, sortie = sys.argv[1], sys.argv[2]
    avec_zstd = "--sans-zstd" not in sys.argv
    L = LecteurGGUF(chemin)
    resultats = []
    t0 = time.time()
    for t in L.tenseurs:
        if t.nom_type in champs_k.DECOUPEURS:
            r = mesurer_quantifie(L, t, avec_zstd)
        elif t.nom_type == "F32":
            r = mesurer_f32(L, t)
        else:
            continue
        r["role"] = re.sub(r"blk\.\d+\.", "", t.nom)
        resultats.append(r)
        if r["type"] != "F32":
            print(f"{t.nom:34s} {t.nom_type} H0={r['H0_code']:.3f} "
                  f"H|prec={r['H_code_sachant_precedent']:.3f} "
                  f"ideal={r['bits_ideaux_ordre0_par_poids']:.3f}/{r['bits_par_poids_stockes']:.3f} b/p"
                  + (f" zstd3={r['compresseurs']['zstd3']['taux']:.3f}" if avec_zstd else ""),
                  flush=True)
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump({"fichier": chemin, "duree_s": time.time() - t0,
                   "tenseurs": resultats}, f, ensure_ascii=False)
    print("durée", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
