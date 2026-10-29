"""Liste exacte des fichiers à demander : nom, taille, empreinte SHA-256 (champ LFS de l'API).

Aucun poids n'est téléchargé ici : l'API « tree » donne la taille et l'empreinte de chaque
fichier, ce qui permet à l'orchestrateur de vérifier le téléchargement octet pour octet.

Usage : python -I modeles-fichiers-a-telecharger.py <sortie.json> <dépôt>:<motif> [...]
  motif = sous-chaîne du chemin (ex. « UD-Q4_K_XL », « mxfp4 »).
"""
import json
import re
import sys
import time
import urllib.request

UA = {"User-Agent": "troncons-recherche/1.0"}


def arbre(depot):
    url = f"https://huggingface.co/api/models/{depot}/tree/main?recursive=true&expand=true"
    out = []
    while url:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            out += json.loads(r.read())
            m = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get("Link") or "")
            url = m.group(1) if m else None
    return [f for f in out if f.get("type") == "file"]


res = {}
for arg in sys.argv[2:]:
    depot, motif = arg.split(":", 1)
    info = json.loads(urllib.request.urlopen(urllib.request.Request(
        f"https://huggingface.co/api/models/{depot}", headers=UA), timeout=60).read())
    fic = [f for f in arbre(depot) if motif.lower() in f["path"].lower() and f["path"].endswith(".gguf")
           and "mmproj" not in f["path"].lower()]
    res[arg] = {"depot": depot, "sha_depot": info.get("sha"), "licence": (info.get("cardData") or {}).get("license"),
                "consulte": time.strftime("%Y-%m-%d"),
                "fichiers": [{"chemin": f["path"], "octets": f.get("size"),
                              "sha256": (f.get("lfs") or {}).get("oid")} for f in fic],
                "octets_total": sum(f.get("size", 0) for f in fic)}
    print(f"{arg}: {len(fic)} fichier(s), {res[arg]['octets_total']/1e9:.2f} Go, licence {res[arg]['licence']}")
json.dump(res, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
