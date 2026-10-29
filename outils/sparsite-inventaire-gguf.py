"""Inventaire d'un fichier GGUF, sans dépendance : métadonnées scalaires et
octets par famille de tenseurs.

Sert l'étude 05 (sparsité) : pour savoir combien d'octets un jeton lit, il faut
savoir combien pèsent les poids de l'attention, du réseau dense (FFN), des
plongements et de la tête de sortie, couche par couche.

La taille d'un tenseur se déduit de l'écart entre son décalage et celui du
tenseur suivant dans la zone de données (le dernier va jusqu'à la fin du
fichier) : aucune table de types de quantification n'est nécessaire, donc rien
à tenir à jour quand llama.cpp ajoute un type.

Usage : python -I sparsite-inventaire-gguf.py FICHIER.gguf [--json SORTIE.json]
"""
import json
import os
import re
import struct
import sys
from collections import defaultdict

TYPES_SCALAIRES = {
    0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i",
    6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d",
}


def lire(f, fmt):
    taille = struct.calcsize(fmt)
    return struct.unpack(fmt, f.read(taille))[0]


def lire_chaine(f):
    n = lire(f, "<Q")
    return f.read(n).decode("utf-8", errors="replace")


def lire_valeur(f, t):
    if t in TYPES_SCALAIRES:
        return lire(f, TYPES_SCALAIRES[t])
    if t == 8:
        return lire_chaine(f)
    if t == 9:
        sous_type = lire(f, "<I")
        n = lire(f, "<Q")
        # Les longs tableaux (vocabulaire, fusions) ne servent pas ici : on
        # les parcourt sans les garder.
        garder = n <= 64
        valeurs = []
        for _ in range(n):
            v = lire_valeur(f, sous_type)
            if garder:
                valeurs.append(v)
        return valeurs if garder else f"<tableau de {n} éléments, type {sous_type}>"
    raise ValueError(f"type GGUF inconnu : {t}")


def famille(nom):
    """Range un tenseur dans une famille qui a un sens pour le coût par jeton."""
    if nom.startswith("token_embd"):
        return "plongement (lu par ligne : 1 ligne par jeton)"
    if nom.startswith("output.") or nom == "output.weight":
        return "tete de sortie"
    if nom.startswith("output_norm"):
        return "normes"
    m = re.match(r"blk\.(\d+)\.(.+)", nom)
    if not m:
        return "autre"
    reste = m.group(2)
    if "norm" in reste:
        return "normes"
    if reste.startswith("ffn_") and ("_exps" in reste or "_shexp" in reste or "gate_inp" in reste):
        return "MoE : " + reste.split(".")[0]
    if reste.startswith("ffn_"):
        return "FFN dense : " + reste.split(".")[0]
    if reste.startswith("attn_") or reste.startswith("ssm_"):
        return "melangeur de sequence : " + reste.split(".")[0]
    if reste.startswith("nextn") or "eh_proj" in reste or "enorm" in reste or "hnorm" in reste:
        return "MTP : " + reste.split(".")[0]
    return "bloc, autre : " + reste.split(".")[0]


def inventaire(chemin):
    taille_fichier = os.path.getsize(chemin)
    with open(chemin, "rb") as f:
        if f.read(4) != b"GGUF":
            raise SystemExit("pas un fichier GGUF")
        version = lire(f, "<I")
        n_tenseurs = lire(f, "<Q")
        n_cles = lire(f, "<Q")
        meta = {}
        for _ in range(n_cles):
            cle = lire_chaine(f)
            t = lire(f, "<I")
            meta[cle] = lire_valeur(f, t)
        tenseurs = []
        for _ in range(n_tenseurs):
            nom = lire_chaine(f)
            nd = lire(f, "<I")
            dims = [lire(f, "<Q") for _ in range(nd)]
            ttype = lire(f, "<I")
            decalage = lire(f, "<Q")
            tenseurs.append({"nom": nom, "dims": dims, "type": ttype, "decalage": decalage})
        alignement = meta.get("general.alignment", 32)
        debut = f.tell()
        debut_donnees = (debut + alignement - 1) // alignement * alignement
    ordonnes = sorted(tenseurs, key=lambda t: t["decalage"])
    for i, t in enumerate(ordonnes):
        fin = ordonnes[i + 1]["decalage"] if i + 1 < len(ordonnes) else taille_fichier - debut_donnees
        t["octets"] = fin - t["decalage"]
        n_elem = 1
        for d in t["dims"]:
            n_elem *= d
        t["elements"] = n_elem
    return version, meta, tenseurs, taille_fichier, debut_donnees


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    chemin = sys.argv[1]
    version, meta, tenseurs, taille_fichier, debut_donnees = inventaire(chemin)
    print(f"fichier : {chemin}")
    print(f"version GGUF : {version} ; tenseurs : {len(tenseurs)} ; octets : {taille_fichier}")
    print(f"entete + metadonnees : {debut_donnees} octets")
    print("\n# Metadonnees (hors tokeniseur)")
    for cle, v in meta.items():
        if cle.startswith("tokenizer."):
            continue
        print(f"{cle} = {v}")
    par_famille = defaultdict(lambda: [0, 0, 0])
    par_couche = defaultdict(int)
    types_par_famille = defaultdict(set)
    for t in tenseurs:
        fam = famille(t["nom"])
        par_famille[fam][0] += t["octets"]
        par_famille[fam][1] += t["elements"]
        par_famille[fam][2] += 1
        types_par_famille[fam].add(t["type"])
        m = re.match(r"blk\.(\d+)\.", t["nom"])
        if m:
            par_couche[int(m.group(1))] += t["octets"]
    total = sum(v[0] for v in par_famille.values())
    print("\n# Octets par famille (bits/poids = 8*octets/elements)")
    for fam, (o, e, n) in sorted(par_famille.items(), key=lambda kv: -kv[1][0]):
        print(f"{fam:55s} {o/2**20:10.1f} Mio  {100*o/total:5.1f} %  {8*o/e:5.2f} b/poids  "
              f"{n:4d} tenseurs  types {sorted(types_par_famille[fam])}")
    print(f"{'TOTAL':55s} {total/2**20:10.1f} Mio")
    if par_couche:
        valeurs = list(par_couche.values())
        print(f"\n# Couches : {len(par_couche)} ; min {min(valeurs)/2**20:.1f} Mio ; "
              f"max {max(valeurs)/2**20:.1f} Mio")
    print("\n# Tenseurs de la couche 0 et de la derniere couche")
    derniere = max(par_couche) if par_couche else -1
    for t in tenseurs:
        if t["nom"].startswith("blk.0.") or t["nom"].startswith(f"blk.{derniere}.") or not t["nom"].startswith("blk."):
            print(f"  {t['nom']:40s} dims {t['dims']} type {t['type']} {t['octets']/2**20:8.2f} Mio")
    if "--json" in sys.argv:
        sortie = sys.argv[sys.argv.index("--json") + 1]
        with open(sortie, "w", encoding="utf-8") as f:
            json.dump({"meta": {k: v for k, v in meta.items() if not k.startswith("tokenizer.")},
                       "tenseurs": tenseurs, "octets_fichier": taille_fichier}, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
