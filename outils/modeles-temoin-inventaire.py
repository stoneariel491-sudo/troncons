"""Témoin de l'inventaire : nos comptes de paramètres contre ceux que les éditeurs publient.

Second chemin, indépendant de notre lecture des en-têtes : le chiffre écrit dans la carte du
modèle (README du dépôt officiel, consulté le 2026-10-15) ou dans l'article technique.

Seuils déclarés avant la première exécution (et justifiés) :
  - total : |nous / éditeur − 1| ≤ 3 %. Les éditeurs arrondissent à l'entier de milliards
    (« 397B ») : l'erreur d'arrondi est ≤ 0,5 / 35 = 1,4 % dès 35 G ; 3 % laisse place aux
    définitions (avec ou sans MTP, avec ou sans tour de vision) sans laisser passer un facteur 2
    (FP4 empaqueté mal compté) ni un doublon de fichiers (+100 %).
    On essaie trois définitions (texte ; texte + vision ; texte − MTP) et l'on dit laquelle colle.
  - actifs : |nous − éditeur| ≤ max(0,6 G, 10 % de l'éditeur). « A3B » arrondit 3,5 G à 3 ;
    la tête de sortie (0,3 à 1,2 G) est comptée chez nous et pas toujours chez eux.
Un modèle sans chiffre publié est noté « sans revendication » et ne compte ni pour ni contre.

Le témoin doit pouvoir tomber : la passe 2 de l'inventaire (inventaire-2.json), qui comptait
deux fois les poids de Mistral et une fois seulement les FP4 empaquetés en U8, doit échouer.

Usage : python -I modeles-temoin-inventaire.py <inventaire.json>  (code de sortie 1 si un échec)
"""
import json
import sys

# dépôt : (total en G, actifs en G ou None, source)
EDITEUR = {
    "Qwen/Qwen3-30B-A3B": (30.5, 3.3, "carte HF"),
    "openai/gpt-oss-20b": (21, 3.6, "carte HF ; arXiv 2508.10925"),
    "openai/gpt-oss-120b": (117, 5.1, "carte HF ; arXiv 2508.10925"),
    "Qwen/Qwen3-Next-80B-A3B-Instruct": (80, 3, "carte HF"),
    "Qwen/Qwen3-Coder-Next": (80, 3, "carte HF"),
    "Qwen/Qwen3.6-35B-A3B": (35, 3, "carte HF"),
    "Qwen/Qwen3.5-122B-A10B": (122, 10, "carte HF"),
    "Qwen/Qwen3.5-397B-A17B": (397, 17, "carte HF"),
    "Qwen/Qwen3-235B-A22B-Instruct-2507": (235, 22, "carte HF"),
    "Qwen/Qwen3-Coder-480B-A35B-Instruct": (480, 35, "carte HF"),
    "Qwen/Qwen3.8-Flash-Next": (180, 6, "carte HF : 125 G + 51 G n-grammes + 4 G MTP, 6 G actifs"),
    "Qwen/Qwen3.8-2.4T-A95B": (2400, 95, "carte HF"),
    "zai-org/GLM-4.5-Air": (106, 12, "carte HF ; arXiv 2508.06471"),
    "zai-org/GLM-5.3-Flash": (320, 18, "carte HF"),
    "deepseek-ai/DeepSeek-V3": (685, 37, "carte HF : 671 G + 14 G MTP, 37 G actifs"),
    "deepseek-ai/DeepSeek-V4-Flash-0731": (284, 13, "arXiv 2606.19348 (V4-Flash)"),
    "deepseek-ai/DeepSeek-V4.1-Flash": (748, 16, "carte HF : 552 G + 196 G Engram ; 16 G actifs en décodage"),
    "deepseek-ai/DeepSeek-V4-Pro-0813": (1600, 49, "arXiv 2606.19348 (V4-Pro)"),
    "moonshotai/Kimi-K2-Instruct-0905": (1000, 32, "carte HF ; arXiv 2507.20534"),
    "moonshotai/Kimi-K2-Thinking": (1000, 32, "carte HF"),
    "moonshotai/Kimi-K2.6": (1000, 32, "carte HF"),
    "moonshotai/Kimi-K3": (2800, None, "carte HF (16 experts sur 896, actifs non chiffrés)"),
    "unsloth/Llama-4-Scout-17B-16E-Instruct": (109, 17, "carte HF (copie de la carte Meta)"),
    "unsloth/Llama-4-Maverick-17B-128E-Instruct": (400, 17, "carte HF (copie de la carte Meta)"),
    "MiniMaxAI/MiniMax-M3": (428, 23, "carte HF (« ~ »)"),
    "XiaomiMiMo/MiMo-V2.6-Flash-RL": (309, 15, "carte HF"),
    "inclusionAI/Ling-3.0-flash": (124, 5.1, "carte HF"),
    "inclusionAI/Ling-3.1-flash": (560, 25, "carte HF"),
    "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16": (120, 12, "carte HF"),
    "nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16": (550, 55, "carte HF"),
    "stepfun-ai/Step-3.5-Flash": (196.81, 11, "carte HF"),
    "tencent/Hy3": (295, 21, "carte HF (+ 3,8 G MTP)"),
    "mistralai/Mistral-Small-4-119B-2603": (119, 6.5, "carte HF"),
    "mistralai/Mistral-Medium-3.5-128B": (128, 128, "carte HF (dense)"),
    "mistralai/Mistral-Large-3-675B-Instruct-2512": (675, 41, "carte HF (673 G et 39 G pour le seul modèle de langue)"),
    "meituan-longcat/LongCat-Flash-Lite": (68.5, 4.5, "carte HF (2,9 à 4,5 G actifs selon le jeton)"),
    "mistralai/Mixtral-8x7B-Instruct-v0.1": (46.7, 12.9, "arXiv 2401.04088"),
    "NousResearch/Hermes-3-Llama-3.1-405B": (405, 405, "arXiv 2407.21783 (Llama 3.1 405B, dense)"),
}


def main(chemin):
    inv = json.load(open(chemin, encoding="utf-8"))
    echecs = 0
    for depot, (tot, act, src) in EDITEUR.items():
        r = inv.get(depot)
        if not r or "erreur" in r:
            print(f"ABSENT   {depot}")
            continue
        p = r["params"]
        texte = r["params_texte_total"] / 1e9
        defs = {"texte": texte, "texte+vision": texte + p.get("hors_texte", 0) / 1e9,
                "texte-MTP": texte - p.get("mtp", 0) / 1e9}
        nom_def, val = min(defs.items(), key=lambda kv: abs(kv[1] / tot - 1))
        ok_tot = abs(val / tot - 1) <= 0.03
        nous_act = r["params_actifs_par_jeton_sans_plongement"] / 1e9
        ok_act = True if act is None else abs(nous_act - act) <= max(0.6, 0.10 * act)
        etat = "OK" if ok_tot and ok_act else "ÉCHEC"
        echecs += etat != "OK"
        a = "—" if act is None else f"{act:g}"
        print(f"{etat:6} {depot}: total nous {val:.1f} ({nom_def}) / éditeur {tot:g} ({100*(val/tot-1):+.1f} %) ; "
              f"actifs nous {nous_act:.2f} / éditeur {a} — {src}")
    sans = [d for d in inv if d not in EDITEUR and "erreur" not in inv[d]]
    print(f"sans revendication chiffrée : {', '.join(sans)}")
    print(f"échecs : {echecs}")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
