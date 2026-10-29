"""Tailles réelles des quantifications GGUF publiées, lues dans l'arbre des dépôts Hugging Face.

Principe. L'API « tree » donne la taille exacte de chaque fichier sans le télécharger. Un même
niveau de quantification est souvent coupé en plusieurs fichiers (« -00001-of-00005.gguf »),
parfois rangé dans un sous-dossier qui porte son nom ; on regroupe par étiquette de
quantification et par dossier, on somme, et l'on garde une seule copie quand un niveau est publié
dans deux dossiers (cas d'unsloth/Llama-3.3-70B-Instruct-GGUF, Q6_K en double). Les fichiers « mmproj » (tour de vision) sont exclus : ils ne sont pas
lus pour un jeton de texte.

Usage : python -I modeles-gguf-tailles.py <sortie.json> <dépôt-gguf> [<dépôt-gguf> ...]
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request

UA = {"User-Agent": "troncons-recherche/1.0"}
BASE = "https://huggingface.co"

RE_QUANT = re.compile(
    r"(UD-)?(Q1_0|IQ1_S|IQ1_M|IQ2_XXS|IQ2_XS|IQ2_S|IQ2_M|IQ3_XXS|IQ3_XS|IQ3_S|IQ3_M|IQ4_XS|IQ4_NL|"
    r"TQ1_0|TQ2_0|Q2_K_XL|Q2_K_L|Q2_K_S|Q2_K|Q3_K_XL|Q3_K_S|Q3_K_M|Q3_K_L|Q4_K_XL|Q4_K_S|Q4_K_M|"
    r"Q4_K_L|Q4_0|Q4_1|Q5_K_XL|Q5_K_S|Q5_K_M|Q5_K_L|Q6_K_XL|Q6_K_L|Q6_K|Q8_K_XL|Q8_0|MXFP4_MOE|MXFP4|"
    r"BF16|F16|F32)(?![A-Z0-9])", re.I)


def obtenir_json(url, essais=6):
    for n in range(essais):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read()), r.headers.get("Link") or ""
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404):
                raise
            time.sleep(2 * (n + 1))
        except Exception:
            time.sleep(2 * (n + 1))
    raise RuntimeError("échec : " + url)


def arbre(depot):
    url = f"{BASE}/api/models/{depot}/tree/main?recursive=true&expand=false"
    out = []
    while url:
        page, lien = obtenir_json(url)
        out += page
        m = re.search(r'<([^>]+)>;\s*rel="next"', lien)
        url = m.group(1) if m else None
    return [f for f in out if f.get("type") == "file"]


def etiquette(chemin):
    nom = chemin.split("/")[-1]
    m = RE_QUANT.search(nom) or RE_QUANT.search(chemin)
    if not m:
        return None
    return ((m.group(1) or "") + m.group(2)).upper().replace("UD-", "UD-")


def analyser(depot):
    info, _ = obtenir_json(f"{BASE}/api/models/{depot}")
    groupes = {}
    for f in arbre(depot):
        p = f["path"]
        if not p.lower().endswith(".gguf") or "mmproj" in p.lower():
            continue
        q = etiquette(p)
        if q is None:
            q = "?" + p.split("/")[-1]
        dossier = p.rsplit("/", 1)[0] if "/" in p else ""
        g = groupes.setdefault(q, {}).setdefault(dossier, {"octets": 0, "fichiers": 0})
        g["octets"] += f.get("size", 0)
        g["fichiers"] += 1
    # Un même niveau est parfois publié deux fois (deux dossiers) : on garde une seule copie,
    # la plus grosse, et on note le nombre de copies.
    groupes = {q: dict(max(d.values(), key=lambda v: v["octets"]), copies=len(d)) for q, d in groupes.items()}
    lic = (info.get("cardData") or {}).get("license")
    return {"depot": depot, "sha": info.get("sha"), "modifie": info.get("lastModified"), "licence": lic,
            "quantifications": dict(sorted(groupes.items(), key=lambda kv: kv[1]["octets"]))}


if __name__ == "__main__":
    sortie = sys.argv[1]
    try:
        res = json.load(open(sortie, encoding="utf-8"))
    except Exception:
        res = {}
    for depot in sys.argv[2:]:
        if depot in res and "erreur" not in res[depot]:
            continue
        try:
            r = analyser(depot)
            r["consulte"] = time.strftime("%Y-%m-%d")
            res[depot] = r
            qs = ", ".join(f"{k} {v['octets']/1e9:.1f}" for k, v in r["quantifications"].items())
            print(f"{depot}: {qs}", flush=True)
        except Exception as e:
            res[depot] = {"depot": depot, "erreur": repr(e)}
            print(f"{depot}: ERREUR {e!r}", flush=True)
        json.dump(res, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
