"""Octets lus par jeton et plafonds physiques, pour chaque modèle de l'inventaire.

Entrées : l'inventaire par en-têtes safetensors (inventaire_modeles.py) et les tailles GGUF
publiées (modeles-gguf-tailles.py). Sortie : un tableau Markdown et un JSON, tous deux calculés,
jamais mesurés.

Le modèle de coût (déclaré ici avant tout usage, et repris dans fondations/06-modeles.md) :

  A  = paramètres toujours lus par jeton (attention, couches denses, experts partagés, routeur,
       normes, tête de sortie) ;
  R  = paramètres des experts routés lus par jeton = somme sur les couches de k/E × experts de
       la couche ;
  E  = paramètres de tous les experts routés (ce qu'il faut stocker quelque part) ;
  b  = bits par poids des experts routés ; les toujours-lus sont comptés à 8,5 bits (Q8_0, le
       choix courant des quantifications « dynamiques ») dans la variante « mixte », à b bits dans
       la variante « uniforme ».

  Octets par jeton (mixte) : O = A × 8,5/8 + R × b/8.

  Plafonds de la machine (fondations/journaux/01-machine/00-seuils-declares.md) :
    VRAM 256 Go/s, RAM 41,6 Go/s (un seul module DDR5-5200), NVMe 7,877 Go/s (PCIe 4.0 ×4),
    PCIe de la carte mesuré 6,38 Go/s en mémoire épinglée (étude 04, pcie-1.json, 256 Mio).

  Répartition : les toujours-lus résident sur la carte s'ils tiennent dans CARTE_UTILE ; les experts
  routés se partagent un cache de capacité C = RAM_UTILE + (CARTE_UTILE − toujours-lus) et le disque.
  Hypothèse pessimiste déclarée : routage uniforme et sans mémoire, donc taux de succès h = C / E_octets
  (borné à 1). Les experts trouvés en RAM sont calculés par le processeur à 41,6 Go/s ; les manqués
  viennent du NVMe à 7,877 Go/s.

  Temps par jeton, borne basse optimiste (recouvrement parfait des étages) :
      t_opt  = max(A_o / 256e9, h·R_o / 41,6e9, (1 − h)·R_o / 7,877e9)
  et borne pessimiste (étages en série) :
      t_pes  = A_o / 256e9 + h·R_o / 41,6e9 + (1 − h)·R_o / 7,877e9
  Le calcul lui-même est supposé gratuit : ce sont des plafonds de débit mémoire, pas des prévisions.

Usage : python -I modeles-octets-par-jeton.py <inventaire.json> <gguf-tailles.json> <sortie.md> <sortie.json>
"""
import json
import sys

import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "modeles_physique", os.path.join(os.path.dirname(os.path.abspath(__file__)), "modeles_physique.py"))
phys = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(phys)
VRAM_GO_S, RAM_GO_S, NVME_GO_S = phys.VRAM_GO_S, phys.RAM_GO_S, phys.NVME_GO_S
CARTE_UTILE, RAM_UTILE = phys.CARTE_UTILE, phys.RAM_UTILE
BITS_TOUJOURS = 8.5

GGUF = {  # dépôt de l'inventaire -> dépôt GGUF de référence (mêmes poids ou même architecture)
    "openai/gpt-oss-20b": "unsloth/gpt-oss-20b-GGUF",
    "openai/gpt-oss-120b": "ggml-org/gpt-oss-120b-GGUF",
    "mistralai/Mixtral-8x22B-Instruct-v0.1": "MaziyarPanahi/Mixtral-8x22B-Instruct-v0.1-GGUF",
    "Qwen/Qwen3-Next-80B-A3B-Instruct": "unsloth/Qwen3-Next-80B-A3B-Instruct-GGUF",
    "Qwen/Qwen3-Coder-Next": "unsloth/Qwen3-Coder-Next-GGUF",
    "Qwen/Qwen3.6-35B-A3B": "unsloth/Qwen3.6-35B-A3B-GGUF",
    "Qwen/Qwen3.5-122B-A10B": "unsloth/Qwen3.5-122B-A10B-GGUF",
    "Qwen/Qwen3.5-397B-A17B": "unsloth/Qwen3.5-397B-A17B-GGUF",
    "Qwen/Qwen3-235B-A22B-Instruct-2507": "unsloth/Qwen3-235B-A22B-Instruct-2507-GGUF",
    "Qwen/Qwen3-Coder-480B-A35B-Instruct": "unsloth/Qwen3-Coder-480B-A35B-Instruct-GGUF",
    "Qwen/Qwen3.8-Flash-Next": "unsloth/Qwen3.8-Flash-Next-GGUF",
    "Qwen/Qwen3.8-2.4T-A95B": "unsloth/Qwen3.8-2.4T-A95B-GGUF",
    "zai-org/GLM-4.5-Air": "unsloth/GLM-4.5-Air-GGUF",
    "zai-org/GLM-4.6": "unsloth/GLM-4.6-GGUF",
    "zai-org/GLM-4.7": "unsloth/GLM-4.7-GGUF",
    "zai-org/GLM-5.1": "unsloth/GLM-5.1-GGUF",
    "zai-org/GLM-5.3-Flash": "unsloth/GLM-5.3-Flash-GGUF",
    "zai-org/GLM-5.3": "unsloth/GLM-5.3-GGUF",
    "deepseek-ai/DeepSeek-V3": "unsloth/DeepSeek-V3.1-GGUF",
    "deepseek-ai/DeepSeek-R1-0528": "unsloth/DeepSeek-V3.1-GGUF",
    "deepseek-ai/DeepSeek-V3.2": "unsloth/DeepSeek-V3.2-GGUF",
    "deepseek-ai/DeepSeek-V4-Flash-0731": "unsloth/DeepSeek-V4-Flash-0731-GGUF",
    "deepseek-ai/DeepSeek-V4-Pro-0813": "unsloth/DeepSeek-V4-Pro-0813-GGUF",
    "moonshotai/Kimi-K2-Instruct-0905": "unsloth/Kimi-K2-Instruct-0905-GGUF",
    "moonshotai/Kimi-K2-Thinking": "unsloth/Kimi-K2-Thinking-GGUF",
    "moonshotai/Kimi-K2.6": "unsloth/Kimi-K2.6-GGUF",
    "moonshotai/Kimi-K3": "unsloth/Kimi-K3-GGUF",
    "unsloth/Llama-4-Scout-17B-16E-Instruct": "unsloth/Llama-4-Scout-17B-16E-Instruct-GGUF",
    "unsloth/Llama-4-Maverick-17B-128E-Instruct": "unsloth/Llama-4-Maverick-17B-128E-Instruct-GGUF",
    "MiniMaxAI/MiniMax-M2.7": "unsloth/MiniMax-M2.7-GGUF",
    "MiniMaxAI/MiniMax-M3": "unsloth/MiniMax-M3-GGUF",
    "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16": "unsloth/NVIDIA-Nemotron-3-Super-120B-A12B-GGUF",
    "nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16": "unsloth/NVIDIA-Nemotron-3-Ultra-550B-A55B-GGUF",
    "mistralai/Mistral-Small-4-119B-2603": "unsloth/Mistral-Small-4-119B-2603-GGUF",
    "mistralai/Mistral-Medium-3.5-128B": "unsloth/Mistral-Medium-3.5-128B-GGUF",
    "mistralai/Mistral-Large-3-675B-Instruct-2512": "unsloth/Mistral-Large-3-675B-Instruct-2512-GGUF",
    "unsloth/Llama-3.3-70B-Instruct": "unsloth/Llama-3.3-70B-Instruct-GGUF",
    "Qwen/Qwen2.5-72B-Instruct": "bartowski/Qwen2.5-72B-Instruct-GGUF",
    "NousResearch/Hermes-3-Llama-3.1-405B": "unsloth/Hermes-4-405B-GGUF",
}
# Étiquettes GGUF représentatives de 2, 3 et 4 bits nominaux, par ordre de préférence.
ETIQ = {2: ["UD-Q2_K_XL", "Q2_K", "UD-IQ2_M", "IQ2_M"], 3: ["UD-Q3_K_XL", "Q3_K_M", "UD-IQ3_XXS"],
        4: ["UD-Q4_K_XL", "Q4_K_M", "MXFP4", "Q4_0"]}


plafonds = phys.plafonds


def ligne(depot, r, g):
    p = r["params"]
    A = r["params_toujours_actifs"]
    R = r["params_experts_routes_actifs"]
    E = p.get("expert", 0)
    texte = r["params_texte_total"]
    dense = E == 0
    out = {"depot": depot, "total_texte_G": texte / 1e9, "actifs_G": (A + R) / 1e9, "toujours_G": A / 1e9,
           "routes_actifs_G": R / 1e9, "experts_G": E / 1e9, "mtp_G": p.get("mtp", 0) / 1e9,
           "recherche_G": p.get("recherche", 0) / 1e9, "hors_texte_G": p.get("hors_texte", 0) / 1e9,
           "licence": r.get("licence_nom") or r.get("licence"), "par_bits": {}}
    for b in (2, 3, 4):
        uni = (A + R) * b / 8
        if dense:  # un modèle dense n'a pas d'experts : tout est « toujours lu », à b bits
            A_o, R_o, E_o = A * b / 8, 0.0, 0.0
            mixte = A_o
            taille = texte * b / 8
        else:
            A_o, R_o, E_o = A * BITS_TOUJOURS / 8, R * b / 8, E * b / 8
            mixte = A_o + R_o
            taille = (texte - E - p.get("recherche", 0)) * BITS_TOUJOURS / 8 + E * b / 8 \
                + p.get("recherche", 0) * 8 / 8
        if dense:
            # le dense : ce qui ne tient pas sur la carte et en RAM vient du disque à chaque jeton
            reste = max(0.0, A_o - CARTE_UTILE - RAM_UTILE)
            t_opt = max(min(A_o, CARTE_UTILE) / (VRAM_GO_S * 1e9),
                        min(max(0.0, A_o - CARTE_UTILE), RAM_UTILE) / (RAM_GO_S * 1e9),
                        reste / (NVME_GO_S * 1e9))
            t_pes = (min(A_o, CARTE_UTILE) / (VRAM_GO_S * 1e9)
                     + min(max(0.0, A_o - CARTE_UTILE), RAM_UTILE) / (RAM_GO_S * 1e9)
                     + reste / (NVME_GO_S * 1e9))
            h = min(1.0, (CARTE_UTILE + RAM_UTILE) / A_o)
        else:
            t_opt, t_pes, h = plafonds(A_o, R_o, E_o)
        pub = None
        if g:
            q = g.get("quantifications", {})
            for e in ETIQ[b]:
                if e in q:
                    pub = {"etiquette": e, "octets": q[e]["octets"], "bpw_moyen": q[e]["octets"] * 8 / texte}
                    break
        out["par_bits"][b] = {"octets_par_jeton_uniforme_Go": uni / 1e9, "octets_par_jeton_mixte_Go": mixte / 1e9,
                              "toujours_lus_Go": A_o / 1e9, "routes_lus_Go": R_o / 1e9,
                              "taille_mixte_Go": taille / 1e9, "succes_cache_uniforme": h,
                              "jetons_s_plafond_optimiste": 1 / t_opt if t_opt else None,
                              "jetons_s_plafond_pessimiste": 1 / t_pes if t_pes else None,
                              "gguf_publie": pub}
    return out


def main(inv, gg, sortie_md, sortie_json):
    inv = json.load(open(inv, encoding="utf-8"))
    gg = json.load(open(gg, encoding="utf-8"))
    lignes = []
    for depot, r in inv.items():
        if "erreur" in r:
            continue
        lignes.append(ligne(depot, r, gg.get(GGUF.get(depot, ""))))
    lignes.sort(key=lambda x: x["total_texte_G"])
    json.dump(lignes, open(sortie_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    md = ["| Modèle | Total texte (G) | Actifs/jeton (G) | Toujours lus (G) | Experts routés lus (G) "
          "| Octets/jeton 2 b / 3 b / 4 b mixte (Go) | Taille mixte 2 b / 4 b (Go) | GGUF publié ~2 b / ~4 b (Go) "
          "| Plafond jetons/s à 4 b (opt. – pess.) |",
          "|---|---:|---:|---:|---:|---|---|---|---|"]
    for x in lignes:
        pb = x["par_bits"]

        def pub(b):
            g = pb[b]["gguf_publie"]
            return f"{g['octets']/1e9:.0f} ({g['etiquette']})" if g else "—"
        md.append(f"| {x['depot']} | {x['total_texte_G']:.1f} | {x['actifs_G']:.2f} | {x['toujours_G']:.2f} | "
                  f"{x['routes_actifs_G']:.2f} | {pb[2]['octets_par_jeton_mixte_Go']:.2f} / "
                  f"{pb[3]['octets_par_jeton_mixte_Go']:.2f} / {pb[4]['octets_par_jeton_mixte_Go']:.2f} | "
                  f"{pb[2]['taille_mixte_Go']:.0f} / {pb[4]['taille_mixte_Go']:.0f} | {pub(2)} / {pub(4)} | "
                  f"{pb[4]['jetons_s_plafond_optimiste']:.1f} – {pb[4]['jetons_s_plafond_pessimiste']:.1f} |")
    open(sortie_md, "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(*sys.argv[1:5])
