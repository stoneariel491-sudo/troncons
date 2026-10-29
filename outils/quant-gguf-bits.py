"""Bits par poids réels d'un fichier GGUF, métadonnées comprises, et octets lus par jeton.

Lit l'en-tête GGUF (version 3) sans dépendance, recense chaque tenseur, son type et
sa taille sur disque, puis rend :
  - les bits par poids du fichier entier (taille du fichier * 8 / nombre de poids) ;
  - les bits par poids des seuls tenseurs (sans l'en-tête ni le vocabulaire) ;
  - les octets lus par jeton au décodage (batch 1) : tous les tenseurs sauf la table
    d'enchâssement, dont une seule ligne est lue par jeton, sauf si la tête de sortie
    est liée à elle (pas de tenseur output.weight), auquel cas elle est lue en entier.

Témoin : la fin du dernier tenseur, alignée, doit tomber exactement sur la fin du
fichier. Une table de tailles de blocs fausse fait tomber ce témoin (option --casser
pour le vérifier : elle fausse la taille d'un bloc Q4_K de 144 à 145 octets).

Tailles de blocs : relevées dans ggml/src/ggml-common.h de llama.cpp (commit 843e7dc,
2026-10-15), d'après les static_assert de chaque structure de bloc.
"""
import struct
import sys
import json
import os

# type -> (nom, poids par bloc, octets par bloc)
TYPES = {
    0: ("F32", 1, 4), 1: ("F16", 1, 2), 2: ("Q4_0", 32, 18), 3: ("Q4_1", 32, 20),
    6: ("Q5_0", 32, 22), 7: ("Q5_1", 32, 24), 8: ("Q8_0", 32, 34), 9: ("Q8_1", 32, 36),
    10: ("Q2_K", 256, 84), 11: ("Q3_K", 256, 110), 12: ("Q4_K", 256, 144),
    13: ("Q5_K", 256, 176), 14: ("Q6_K", 256, 210), 15: ("Q8_K", 256, 292),
    16: ("IQ2_XXS", 256, 66), 17: ("IQ2_XS", 256, 74), 18: ("IQ3_XXS", 256, 98),
    19: ("IQ1_S", 256, 50), 20: ("IQ4_NL", 32, 18), 21: ("IQ3_S", 256, 110),
    22: ("IQ2_S", 256, 82), 23: ("IQ4_XS", 256, 136), 24: ("I8", 1, 1),
    25: ("I16", 1, 2), 26: ("I32", 1, 4), 27: ("I64", 1, 8), 28: ("F64", 1, 8),
    29: ("IQ1_M", 256, 56), 30: ("BF16", 1, 2), 34: ("TQ1_0", 256, 54),
    35: ("TQ2_0", 256, 66), 39: ("MXFP4", 32, 17), 40: ("NVFP4", 64, 36),
    41: ("Q1_0", 128, 18), 42: ("Q2_0", 64, 18),
}

# types de valeurs des métadonnées GGUF -> taille fixe (None = chaîne ou tableau)
VAL_FIXE = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
VAL_FMT = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?",
           10: "<Q", 11: "<q", 12: "<d"}


class Lecteur:
    def __init__(self, f):
        self.f = f

    def u32(self):
        return struct.unpack("<I", self.f.read(4))[0]

    def u64(self):
        return struct.unpack("<Q", self.f.read(8))[0]

    def chaine(self):
        n = self.u64()
        return self.f.read(n).decode("utf-8", errors="replace")

    def valeur(self, t):
        if t in VAL_FIXE:
            return struct.unpack(VAL_FMT[t], self.f.read(VAL_FIXE[t]))[0]
        if t == 8:
            return self.chaine()
        if t == 9:
            sous = self.u32()
            n = self.u64()
            if sous in VAL_FIXE:
                self.f.seek(VAL_FIXE[sous] * n, 1)  # tableau de taille fixe : sauté
                return f"<tableau {n}>"
            elements = [self.valeur(sous) for _ in range(n)]  # chaînes : lues pour avancer
            return elements if n < 64 else f"<tableau {n}>"
        raise ValueError(f"type de valeur GGUF inconnu {t}")


def lire(chemin, casser=False):
    types = dict(TYPES)
    if casser:
        types[12] = ("Q4_K", 256, 145)
    taille_fichier = os.path.getsize(chemin)
    with open(chemin, "rb") as f:
        L = Lecteur(f)
        if f.read(4) != b"GGUF":
            raise ValueError("pas un GGUF")
        version = L.u32()
        n_tenseurs = L.u64()
        n_kv = L.u64()
        meta = {}
        for _ in range(n_kv):
            cle = L.chaine()
            t = L.u32()
            v = L.valeur(t)
            if not (isinstance(v, str) and v.startswith("<tableau")):
                meta[cle] = v
        alignement = int(meta.get("general.alignment", 32))
        tenseurs = []
        for _ in range(n_tenseurs):
            nom = L.chaine()
            nd = L.u32()
            dims = [L.u64() for _ in range(nd)]
            t = L.u32()
            decalage = L.u64()
            tenseurs.append((nom, dims, t, decalage))
        fin_entete = f.tell()
    debut_donnees = (fin_entete + alignement - 1) // alignement * alignement

    lignes = []
    fin_max = 0
    for nom, dims, t, dec in tenseurs:
        n = 1
        for d in dims:
            n *= d
        tn, bloc, octets = types[t]
        assert n % bloc == 0, (nom, n, bloc)
        taille = n // bloc * octets
        fin_max = max(fin_max, dec + taille)
        lignes.append({"nom": nom, "dims": dims, "type": tn, "poids": n, "octets": taille})
    fin_tenseurs = debut_donnees + fin_max
    temoin_ok = (fin_tenseurs == taille_fichier)

    n_poids = sum(l["poids"] for l in lignes)
    o_tenseurs = sum(l["octets"] for l in lignes)
    noms = {l["nom"] for l in lignes}
    lie = "output.weight" not in noms
    emb = next((l for l in lignes if l["nom"] == "token_embd.weight"), None)
    o_par_jeton = o_tenseurs
    if emb is not None and not lie:
        ligne = emb["octets"] // emb["dims"][1]
        o_par_jeton = o_tenseurs - emb["octets"] + ligne

    par_type = {}
    for l in lignes:
        p = par_type.setdefault(l["type"], {"tenseurs": 0, "poids": 0, "octets": 0})
        p["tenseurs"] += 1
        p["poids"] += l["poids"]
        p["octets"] += l["octets"]
    for p in par_type.values():
        p["bpp"] = round(p["octets"] * 8 / p["poids"], 4)

    return {
        "fichier": os.path.basename(chemin),
        "version_gguf": version,
        "architecture": meta.get("general.architecture"),
        "type_fichier": meta.get("general.file_type"),
        "taille_fichier": taille_fichier,
        "entete_et_meta": debut_donnees,
        "temoin_fin_tenseurs_egale_fin_fichier": temoin_ok,
        "fin_calculee": fin_tenseurs,
        "n_tenseurs": len(lignes),
        "n_poids": n_poids,
        "bpp_fichier": round(taille_fichier * 8 / n_poids, 4),
        "bpp_tenseurs": round(o_tenseurs * 8 / n_poids, 4),
        "sortie_liee_a_l_enchassement": lie,
        "octets_lus_par_jeton": o_par_jeton,
        "par_type": par_type,
    }


if __name__ == "__main__":
    casser = "--casser" in sys.argv
    chemins = [a for a in sys.argv[1:] if not a.startswith("--")]
    sortie = [lire(c, casser) for c in chemins]
    print(json.dumps(sortie, indent=1, ensure_ascii=False))
    if not all(s["temoin_fin_tenseurs_egale_fin_fichier"] for s in sortie):
        print("TEMOIN TOMBE : la table des tailles de blocs ne rend pas la taille du fichier",
              file=sys.stderr)
        sys.exit(1)
