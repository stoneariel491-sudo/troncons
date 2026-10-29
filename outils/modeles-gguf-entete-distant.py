"""Octets lus par jeton d'un fichier GGUF précis, lus dans son en-tête à distance (requêtes Range).

Pourquoi. Les quantifications « dynamiques » mélangent les types par tenseur (experts en 2 bits,
attention en 8 bits, plongement en 6 bits…) : seul l'en-tête du fichier dit combien d'octets un
jeton lit vraiment. On lit l'en-tête GGUF par morceaux, sans télécharger les poids.

Format GGUF (v3), écrit d'après la spécification publique de ggml (docs/gguf.md) et non d'après
un lecteur existant : « GGUF », version u32, nombre de tenseurs u64, nombre de paires u64 ; les
paires clé-valeur (clé = chaîne u64+octets, type u32, valeur) ; puis pour chaque tenseur : nom,
nombre de dimensions u32, dimensions u64, type u32, décalage u64 dans la zone de données. La zone
de données commence à l'alignement (clé general.alignment, 32 par défaut) après l'en-tête.

Taille d'un tenseur : différence entre décalages consécutifs (triés), et pour le dernier, la taille
du fichier moins le début des données moins son décalage. Ce calcul ne dépend d'aucune table de
types : c'est son témoin intégré (la somme des tailles plus l'en-tête égale la taille du fichier).

Catégories (noms de tenseurs de llama.cpp) :
  experts routés  : « _exps » (ffn_gate_exps, ffn_up_exps, ffn_down_exps, ffn_gate_up_exps) ;
  partagés        : « _shexp » ; plongement : « token_embd » (une ligne lue par jeton) ;
  tête            : « output.weight » ; MTP : « nextn » ou couches au-delà de block_count ;
  recherche       : tables de n-grammes ou Engram (noms contenant « ngram » ou « engram », et
                    « per_layer_token_embd », nom de la table de n-grammes de Qwen3.8 dans llama.cpp) ;
  le reste        : toujours lu.

Usage : python -I modeles-gguf-entete-distant.py <sortie.json> <dépôt>/<chemin.gguf> [...]
"""
import json
import re
import struct
import sys
import time
import urllib.request
from collections import defaultdict

UA = {"User-Agent": "troncons-recherche/1.0"}


class Distant:
    """Lecture séquentielle d'un fichier distant, par blocs de 8 Mio obtenus en Range."""

    def __init__(self, url, bloc=8 << 20):
        self.url, self.bloc, self.tampon, self.debut, self.pos = url, bloc, b"", 0, 0
        self.taille = None

    def _charger(self, n):
        while self.pos + n > self.debut + len(self.tampon):
            a = self.debut + len(self.tampon)
            req = urllib.request.Request(self.url, headers=dict(UA, Range=f"bytes={a}-{a + self.bloc - 1}"))
            with urllib.request.urlopen(req, timeout=120) as r:
                cr = r.headers.get("Content-Range") or ""
                if "/" in cr:
                    self.taille = int(cr.rsplit("/", 1)[1])
                self.tampon += r.read()

    def lire(self, n):
        self._charger(n)
        i = self.pos - self.debut
        self.pos += n
        return self.tampon[i:i + n]

    def u32(self):
        return struct.unpack("<I", self.lire(4))[0]

    def u64(self):
        return struct.unpack("<Q", self.lire(8))[0]

    def chaine(self):
        return self.lire(self.u64()).decode("utf-8", "replace")


TAILLES_SCALAIRES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
FMT = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}


def valeur(f, t):
    if t == 8:
        return f.chaine()
    if t == 9:
        st, n = f.u32(), f.u64()
        if st == 8:
            for _ in range(n):
                f.chaine()
            return f"<tableau de {n} chaînes>"
        f.lire(TAILLES_SCALAIRES[st] * n)
        return f"<tableau de {n}>"
    return struct.unpack(FMT[t], f.lire(TAILLES_SCALAIRES[t]))[0]


def entete(url):
    f = Distant(url)
    if f.lire(4) != b"GGUF":
        raise ValueError("pas un GGUF")
    version, nt, nkv = f.u32(), f.u64(), f.u64()
    kv = {}
    for _ in range(nkv):
        k = f.chaine()
        kv[k] = valeur(f, f.u32())
    tenseurs = []
    for _ in range(nt):
        nom = f.chaine()
        nd = f.u32()
        dims = [f.u64() for _ in range(nd)]
        typ = f.u32()
        dec = f.u64()
        tenseurs.append([nom, dims, typ, dec])
    align = int(kv.get("general.alignment", 32))
    debut_donnees = (f.pos + align - 1) // align * align
    if f.taille is None:
        raise RuntimeError("taille du fichier inconnue")
    tenseurs.sort(key=lambda x: x[3])
    for i, t in enumerate(tenseurs):
        fin = tenseurs[i + 1][3] if i + 1 < len(tenseurs) else f.taille - debut_donnees
        t.append(fin - t[3])
    return version, kv, tenseurs, debut_donnees, f.taille


def categorie(nom, n_blocs):
    bas = nom.lower()
    if "ngram" in bas or "engram" in bas or bas.startswith("per_layer_token_embd"):
        return "recherche"
    if "nextn" in bas or "mtp" in bas:
        return "mtp"
    m = re.match(r"blk\.(\d+)\.", nom)
    if m and n_blocs is not None and int(m.group(1)) >= n_blocs:
        return "mtp"
    if "_exps" in bas:
        return "expert"
    if "_shexp" in bas:
        return "partage"
    if bas.startswith("token_embd"):
        return "plongement"
    if bas.startswith("output.weight"):
        return "tete"
    return "toujours"


def analyser(chemins):
    tot = defaultdict(int)
    familles = defaultdict(lambda: [0, set()])
    kv_tous = {}
    formes = {}
    taille_fichiers = 0
    for depot_chemin in chemins:
        depot, chemin = depot_chemin.split("/", 2)[:2], depot_chemin.split("/", 2)[2]
        url = f"https://huggingface.co/{depot[0]}/{depot[1]}/resolve/main/{chemin}"
        version, kv, tenseurs, debut, taille = entete(url)
        kv_tous.update({k: v for k, v in kv.items() if not str(v).startswith("<tableau")})
        taille_fichiers += taille
        arch = kv_tous.get("general.architecture", "")
        n_blocs = kv_tous.get(f"{arch}.block_count")
        nextn = kv_tous.get(f"{arch}.nextn_predict_layers") or 0
        n_principaux = n_blocs - nextn if (n_blocs is not None and nextn) else None
        somme = sum(t[4] for t in tenseurs)
        tot["entetes_et_alignement"] += taille - somme
        for nom, dims, typ, dec, octets in tenseurs:
            c = categorie(nom, n_principaux)
            tot[c] += octets
            if c in ("recherche", "plongement"):
                formes[nom] = {"dims": dims, "type_ggml": typ, "octets": octets}
            fam = re.sub(r"\.\d+\.", ".#.", nom)
            familles[fam][0] += octets
            familles[fam][1].add(typ)
    arch = kv_tous.get("general.architecture", "")
    E = kv_tous.get(f"{arch}.expert_count")
    k = kv_tous.get(f"{arch}.expert_used_count")
    lus = tot["toujours"] + tot["partage"] + tot["tete"]
    routes_lus = tot["expert"] * k / E if (E and k) else None
    return {
        "fichiers": chemins, "octets_fichiers": taille_fichiers, "architecture": arch,
        "experts": E, "experts_par_jeton": k, "octets_par_categorie": dict(tot),
        "temoin_somme_egale_taille": sum(tot.values()) == taille_fichiers,
        "octets_toujours_lus": lus, "octets_experts_routes_lus_par_jeton": routes_lus,
        "octets_lus_par_jeton_hors_plongement": lus + (routes_lus or 0),
        "tables": formes,
        "familles": {f: {"octets": o, "types_ggml": sorted(t)} for f, (o, t) in
                     sorted(familles.items(), key=lambda kv: -kv[1][0])[:40]},
        "cles": {k2: v for k2, v in kv_tous.items() if k2.startswith(arch + ".") or k2.startswith("general.")},
    }


if __name__ == "__main__":
    sortie = sys.argv[1]
    try:
        res = json.load(open(sortie, encoding="utf-8"))
    except Exception:
        res = {}
    # Arguments : groupes de fichiers d'un même modèle séparés par « + ».
    for groupe in sys.argv[2:]:
        chemins = groupe.split("+")
        cle = chemins[0]
        try:
            r = analyser(chemins)
            r["consulte"] = time.strftime("%Y-%m-%d")
            res[cle] = r
            print(f"{cle}: {r['octets_fichiers']/1e9:.2f} Go, toujours lus {r['octets_toujours_lus']/1e9:.2f} Go, "
                  f"experts routés lus/jeton {(r['octets_experts_routes_lus_par_jeton'] or 0)/1e9:.2f} Go "
                  f"(E={r['experts']}, k={r['experts_par_jeton']}), recherche "
                  f"{r['octets_par_categorie'].get('recherche', 0)/1e9:.2f} Go, témoin {r['temoin_somme_egale_taille']}",
                  flush=True)
        except Exception as e:
            res[cle] = {"erreur": repr(e)}
            print(f"{cle}: ERREUR {e!r}", flush=True)
        json.dump(res, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
