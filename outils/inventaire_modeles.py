"""Inventaire des modèles lourds : paramètres totaux et actifs, lus dans les en-têtes safetensors.

Principe. Un fichier safetensors commence par 8 octets (longueur N, petit-boutiste) puis N octets
de JSON qui donnent, pour chaque tenseur, son type et sa forme. Deux requêtes HTTP à plage
(Range) par fragment suffisent donc à connaître la forme exacte de chaque tenseur d'un modèle
sans télécharger ses poids. On classe ensuite chaque tenseur :

  - experts routés  : un seul expert sur E est lu par jeton et par choix de routeur ;
  - toujours actifs : attention, normes, routeur, experts partagés, couches denses, tête de sortie ;
  - plongement      : une seule ligne lue par jeton (négligeable), comptée à part ;
  - MTP             : couches de prédiction multi-jetons, lues seulement en décodage spéculatif ;
  - hors texte      : tour de vision ou d'audio, jamais lue pour un jeton de texte ;
  - recherche       : table de mémoire conditionnelle (Engram de DeepSeek V4.1, plongement de
                      n-grammes de Qwen3.8-Flash-Next) : quelques lignes lues par jeton, adressées
                      par un hachage des n-grammes de jetons, comptée à part.

Poids FP4 empaquetés. DeepSeek V4 range ses experts FP4 dans des tenseurs I8 (deux valeurs par
octet) accompagnés d'une échelle F8_E8M0 ; gpt-oss dans des tenseurs U8 « _blocks ». Ces deux cas
comptent deux paramètres logiques par octet stocké.

Paramètres actifs par jeton = toujours actifs + k/E × experts routés (couche par couche).

Usage : python -I inventaire_modeles.py <sortie.json> <dépôt> [<dépôt> ...]
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "troncons-recherche/1.0"}
BASE = "https://huggingface.co"

# Octets par élément stocké, et nombre de paramètres logiques par élément stocké.
OCTETS = {"F64": 8, "F32": 4, "BF16": 2, "F16": 2, "F8_E4M3": 1, "F8_E5M2": 1, "F8_E8M0": 1,
          "I64": 8, "I32": 4, "I16": 2, "I8": 1, "U8": 1, "BOOL": 1, "F4": 0.5, "F6_E2M3": 0.75}

RE_VISION = re.compile(r"(^|\.)(vision|visual|vpm|vision_tower|vision_model|mm_projector|multi_modal"
                       r"|audio|audio_tower|image_newline|patch_embed|merger|vit|aligner)(\.|_|$)", re.I)
RE_EXPERT_IDX = re.compile(r"\.experts\.(\d+)\.")
RE_LAYER = re.compile(r"(?:layers|layer|h|blocks)\.(\d+)\.")
RE_ECHELLE = re.compile(r"(scale|scales|_scale_inv|zero_point|zeros|absmax|g_idx|input_scale)", re.I)


def obtenir(url, plage=None, essais=7):
    for n in range(essais):
        req = urllib.request.Request(url, headers=dict(UA))
        if plage:
            req.add_header("Range", "bytes=%d-%d" % plage)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404):
                raise
            time.sleep(1.5 * (n + 1))
        except Exception:
            time.sleep(1.5 * (n + 1))
    raise RuntimeError("échec : " + url)


def api_modele(depot):
    return json.loads(obtenir(f"{BASE}/api/models/{depot}"))


def arbre(depot):
    """Liste récursive des fichiers avec leur taille (pagination par en-tête Link)."""
    url = f"{BASE}/api/models/{depot}/tree/main?recursive=true&expand=false"
    out = []
    while url:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            out += json.loads(r.read())
            lien = r.headers.get("Link") or ""
            m = re.search(r'<([^>]+)>;\s*rel="next"', lien)
            url = m.group(1) if m else None
    return [f for f in out if f.get("type") == "file"]


def entete(depot, fichier):
    url = f"{BASE}/{depot}/resolve/main/{urllib.parse.quote(fichier)}"
    n = int.from_bytes(obtenir(url, (0, 7)), "little")
    return json.loads(obtenir(url, (8, 8 + n - 1)))


def config(depot):
    try:
        return json.loads(obtenir(f"{BASE}/{depot}/raw/main/config.json"))
    except Exception:
        pass
    # Format natif de Mistral (Mistral-Large-3) : params.json, experts dans un sous-dictionnaire « moe ».
    try:
        p = json.loads(obtenir(f"{BASE}/{depot}/raw/main/params.json"))
    except Exception:
        return {}
    c = dict(p)
    c.update(p.get("moe") or {})
    c.setdefault("num_hidden_layers", p.get("n_layers"))
    c.setdefault("hidden_size", p.get("dim"))
    return c


def cfg_texte(c):
    for cle in ("text_config", "language_config", "llm_config", "thinker_config"):
        if isinstance(c.get(cle), dict):
            t = dict(c[cle])
            if cle == "thinker_config" and isinstance(t.get("text_config"), dict):
                t = t["text_config"]
            return t
    return c


def premier(d, *cles, defaut=None):
    for k in cles:
        if d.get(k) is not None:
            return d[k]
    return defaut


def params_logiques(nom, dtype, numel, fp4_empaquetes=frozenset()):
    """Paramètres logiques et octets stockés d'un tenseur. Les échelles sont du surcoût."""
    octets = numel * OCTETS.get(dtype, 2)
    if nom in fp4_empaquetes:
        return numel * 2, octets
    if "norm" not in nom and (RE_ECHELLE.search(nom.split(".")[-1]) or nom.endswith("_scales")):
        return 0, octets
    if (nom.endswith("_blocks") or nom.endswith(".blocks")) and dtype in ("U8", "I8"):  # MXFP4 de gpt-oss : 2 valeurs par octet
        return numel * 2, octets
    if dtype in ("I32",) and ("packed" in nom or "qweight" in nom):  # int4 empaqueté par 8
        return numel * 8, octets
    return numel, octets


def est_fp4_empaquete(nom, v, tous):
    """Vrai si un tenseur I8/U8 porte deux valeurs de 4 bits par octet.

    Trois signes, chacun vérifié sur un dépôt réel (2026-10-15) :
      - sœur « X.scale » en F8_E8M0 (DeepSeek V4) ;
      - sœur d'échelle (« X.weight_scale », « X.scale ») dont la dernière dimension × 16 égale celle
        du tenseur : groupes de 32 valeurs de 4 bits par échelle (MXFP4 : MiMo V2.6, Kimi K3) ;
      - même chose × 8 : groupes de 16 (NVFP4).
    Un INT8 par blocs de 128 (échelle × 128) n'est pas empaqueté et reste à un paramètre par octet.
    """
    if v["dtype"] not in ("I8", "U8"):
        return False
    for suffixe in (".weight", ".weight_packed"):
        if nom.endswith(suffixe):
            racine = nom[:-len(suffixe)]
            break
    else:
        return False
    for nom_echelle in (racine + ".scale", racine + ".weight_scale", racine + ".weight_scale_inv"):
        e = tous.get(nom_echelle)
        if not e:
            continue
        if e["dtype"] == "F8_E8M0" and nom_echelle.endswith(".scale"):
            return True
        if e["shape"] and v["shape"] and e["shape"][-1] * 16 == v["shape"][-1]:
            return True
        if e["shape"] and v["shape"] and e["shape"][-1] * 8 == v["shape"][-1]:
            return True
    return False


def classer(nom, n_couches, forme=None, E_cfg=None):
    if RE_VISION.search(nom):
        return "hors_texte"
    if "mtp" in nom.lower() or "nextn" in nom.lower():
        return "mtp"
    if ("engram" in nom.lower() and nom.endswith("embed.weight")) or "ngram_embedding" in nom.lower():
        return "recherche"
    m = RE_LAYER.search(nom)
    if m and n_couches and int(m.group(1)) >= n_couches:
        return "mtp"
    bas = nom.lower()
    if (any(x in bas for x in ("embed_tokens", "tok_embeddings", "wte.", "word_embeddings", "embedding.weight"))
            or bas in ("embed.weight", "model.embed.weight")) and "lm_head" not in bas:
        return "plongement"
    if "lm_head" in bas or bas in ("output.weight", "model.output.weight", "head.weight", "model.head.weight"):
        return "tete"
    if "shared_expert" in bas or "shared_mlp" in bas or "share_expert" in bas:
        return "partage"
    if RE_EXPERT_IDX.search(nom) or (".experts." in nom and "shared" not in bas):
        return "expert"
    # Experts fusionnés sans le mot « experts » (Step 3.5 : « layers.N.moe.up_proj.weight » de forme
    # [E, ...]) : la première dimension égale au nombre d'experts du config suffit.
    if ".moe." in bas and forme and E_cfg and len(forme) >= 3 and forme[0] == E_cfg:
        return "expert"
    return "actif"


def analyser(depot, travailleurs=16):
    info = api_modele(depot)
    fichiers = arbre(depot)
    # Seuls les fragments de la racine comptent : des sous-dossiers (original/, metal/...) portent
    # parfois une seconde copie des mêmes poids dans un autre format.
    racine = [f for f in fichiers if f["path"].endswith(".safetensors") and "/" not in f["path"]]
    # Quand l'index existe, seuls ses fragments comptent : Mistral publie à la racine deux copies des
    # mêmes poids (« consolidated-* » et « model-* »), ce qui doublait le compte (Mistral-Small-4).
    try:
        index = json.loads(obtenir(f"{BASE}/{depot}/resolve/main/model.safetensors.index.json"))
        listes = set(index["weight_map"].values())
        racine = [f for f in racine if f["path"] in listes] or racine
    except Exception:
        pass
    shards = sorted(f["path"] for f in racine)
    taille_st = sum(f.get("size", 0) for f in racine)
    c = config(depot)
    t = cfg_texte(c)
    n_couches = premier(t, "num_hidden_layers", "n_layers", "num_layers")
    # « top_k » vient en dernier : chez Kimi K3 c'est un paramètre d'échantillonnage (50), pas le
    # nombre d'experts par jeton (16).
    k = premier(t, "num_experts_per_tok", "num_experts_per_token", "moe_topk", "moe_top_k", "experts_per_token",
                "moe_k", "n_activated_experts", "top_k")
    if isinstance(k, list):
        k = max(k)
    E_cfg = premier(t, "n_routed_experts", "num_experts", "num_local_experts", "moe_num_experts", "n_experts")
    if isinstance(E_cfg, list):
        E_cfg = max(E_cfg)

    with ThreadPoolExecutor(travailleurs) as ex:
        entetes = list(ex.map(lambda f: entete(depot, f), shards))

    cat_p = defaultdict(int)
    cat_o = defaultdict(int)
    # experts routés : par couche, l'ensemble des indices et la somme des paramètres
    exp_p = defaultdict(int)
    exp_o = defaultdict(int)
    exp_ids = defaultdict(set)
    exp_fusionnes = {}
    dtypes = defaultdict(int)
    motifs = defaultdict(lambda: [0, 0, None, None])
    # FP4 empaqueté dans I8/U8 : le tenseur « X.weight » a une sœur « X.scale » en F8_E8M0.
    tous = {}
    for h in entetes:
        tous.update({n: v for n, v in h.items() if n != "__metadata__"})
    fp4 = frozenset(n for n, v in tous.items() if est_fp4_empaquete(n, v, tous))
    for h in entetes:
        for nom, v in h.items():
            if nom == "__metadata__":
                continue
            numel = 1
            for s in v["shape"]:
                numel *= s
            p, o = params_logiques(nom, v["dtype"], numel, fp4)
            cat = classer(nom, n_couches, v["shape"], E_cfg)
            dtypes[v["dtype"]] += o
            motif = re.sub(r"\.\d+\.", ".#.", nom)
            motif = re.sub(r"\.\d+\.", ".#.", motif)
            mm = motifs[motif]
            mm[0] += 1
            mm[1] += p
            mm[2] = v["dtype"]
            mm[3] = v["shape"]
            if cat == "expert":
                lm = RE_LAYER.search(nom)
                couche = int(lm.group(1)) if lm else -1
                ei = RE_EXPERT_IDX.search(nom)
                if ei:
                    exp_ids[couche].add(int(ei.group(1)))
                else:  # tenseur fusionné : première dimension = nombre d'experts
                    if not RE_ECHELLE.search(nom.split(".")[-1]) and len(v["shape"]) >= 3:
                        exp_fusionnes[couche] = v["shape"][0]
                exp_p[couche] += p
                exp_o[couche] += o
            cat_p[cat] += p
            cat_o[cat] += o

    # actifs routés : k/E par couche
    actifs_routes_p = 0.0
    actifs_routes_o = 0.0
    E_trouves = {}
    for couche in exp_p:
        E = len(exp_ids[couche]) or exp_fusionnes.get(couche) or E_cfg
        E_trouves[couche] = E
        if E and k:
            actifs_routes_p += exp_p[couche] * k / E
            actifs_routes_o += exp_o[couche] * k / E
    tie = bool(premier(t, "tie_word_embeddings", defaut=c.get("tie_word_embeddings", False)))
    tete_p = cat_p["tete"] if cat_p["tete"] else (cat_p["plongement"] if tie else 0)
    tete_o = cat_o["tete"] if cat_o["tete"] else (cat_o["plongement"] if tie else 0)
    toujours_p = cat_p["actif"] + cat_p["partage"] + tete_p
    toujours_o = cat_o["actif"] + cat_o["partage"] + tete_o
    texte_p = sum(v for kk, v in cat_p.items() if kk not in ("hors_texte",))
    lic = (info.get("cardData") or {}).get("license") or next(
        (x.split(":", 1)[1] for x in info.get("tags", []) if x.startswith("license:")), None)
    lic_nom = (info.get("cardData") or {}).get("license_name")
    lic_lien = (info.get("cardData") or {}).get("license_link")
    Es = sorted(set(v for v in E_trouves.values() if v))
    return {
        "depot": depot,
        "sha": info.get("sha"),
        "cree": info.get("createdAt"),
        "modifie": info.get("lastModified"),
        "licence": lic, "licence_nom": lic_nom, "licence_lien": lic_lien,
        "gated": info.get("gated"),
        "architectures": c.get("architectures"),
        "model_type": c.get("model_type") or t.get("model_type"),
        "api_safetensors_total": (info.get("safetensors") or {}).get("total"),
        "api_safetensors_par_type": (info.get("safetensors") or {}).get("parameters"),
        "n_fragments": len(shards),
        "octets_safetensors": taille_st,
        "octets_par_dtype": dict(dtypes),
        "config": {
            "couches": n_couches, "hidden": premier(t, "hidden_size", "d_model", "dim"),
            "experts_routes_cfg": E_cfg, "experts_par_jeton": k,
            "experts_partages": premier(t, "n_shared_experts", "num_shared_experts", "shared_expert_intermediate_size"),
            "tetes_q": premier(t, "num_attention_heads", "n_heads"), "tetes_kv": premier(t, "num_key_value_heads", "n_kv_heads"),
            "head_dim": t.get("head_dim"), "kv_lora_rank": t.get("kv_lora_rank"), "q_lora_rank": t.get("q_lora_rank"),
            "qk_rope_head_dim": t.get("qk_rope_head_dim"), "v_head_dim": t.get("v_head_dim"),
            "mtp": premier(t, "num_nextn_predict_layers", "mtp_num_hidden_layers", "num_mtp_layers"),
            "vocab": t.get("vocab_size"), "ctx_max": t.get("max_position_embeddings"),
            "layer_types": sorted(set(t["layer_types"])) if isinstance(t.get("layer_types"), list) else None,
            "n_layer_types": {x: t["layer_types"].count(x) for x in set(t["layer_types"])} if isinstance(t.get("layer_types"), list) else None,
            "sliding_window": t.get("sliding_window"), "tie": tie,
            "couches_hachees": t.get("num_hash_layers"),
            "engram": {k2: t[k2] for k2 in t if k2.startswith("engram_")} or None,
            "dense_initiales": premier(t, "first_k_dense_replace", "num_dense_layers", "first_k_dense"),
            "moe_intermediate": t.get("moe_intermediate_size"), "intermediate": t.get("intermediate_size"),
        },
        "experts_par_couche_trouves": Es,
        "fp4_empaquetes": len(fp4),
        "couches_moe": len(exp_p),
        "params": {kk: v for kk, v in cat_p.items()},
        "octets": {kk: v for kk, v in cat_o.items()},
        "params_texte_total": texte_p,
        "params_actifs_par_jeton_sans_plongement": toujours_p + actifs_routes_p,
        "params_toujours_actifs": toujours_p,
        "params_experts_routes_actifs": actifs_routes_p,
        "octets_stockes_lus_par_jeton": toujours_o + actifs_routes_o,
        "motifs": {m: v for m, v in sorted(motifs.items(), key=lambda kv: -kv[1][1])[:40]},
    }


if __name__ == "__main__":
    sortie = sys.argv[1]
    try:
        res = json.load(open(sortie, encoding="utf-8"))
    except Exception:
        res = {}
    for depot in sys.argv[2:]:
        if depot in res and "erreur" not in res[depot]:
            continue
        t0 = time.time()
        try:
            r = analyser(depot)
            r["consulte"] = time.strftime("%Y-%m-%d")
            res[depot] = r
            print(f"{depot}: total {r['params_texte_total']/1e9:.1f} G, actifs {r['params_actifs_par_jeton_sans_plongement']/1e9:.2f} G,"
                  f" E={r['experts_par_couche_trouves']} k={r['config']['experts_par_jeton']} ({time.time()-t0:.0f} s)", flush=True)
        except Exception as e:
            res[depot] = {"depot": depot, "erreur": repr(e)}
            print(f"{depot}: ERREUR {e!r}", flush=True)
        json.dump(res, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
