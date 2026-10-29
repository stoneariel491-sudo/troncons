"""Octets par expert et octets toujours lus de gpt-oss, lus dans l'en-tête des fichiers GGUF locaux.

S'appuie sur le lecteur d'en-tête de l'étude 02 (outils/quant-gguf-bits.py, fonction lire, avec son
témoin : la fin du dernier tenseur tombe exactement sur la fin du fichier). Catégories :
  - expert routé : tenseurs blk.<l>.ffn_{gate,up,down}_exps.{weight,bias} ; un expert est la tranche
    e de la dernière dimension (E) de chacun : octets d'un expert de la couche l = somme / E ;
  - toujours lus : tout le reste, sauf la table d'enchâssement dont un jeton ne lit qu'une ligne
    (la tête de sortie output.weight existe dans ces fichiers, elle est lue en entier) ;
  - le routeur (ffn_gate_inp) est compté dans les toujours-lus.
Sortie : un JSON par modèle et un résumé imprimé.

Usage : python -I gptoss_octets.py --sortie <json> <fichier.gguf> [...]
"""
import argparse
import importlib.util
import json
import os
import re

ICI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("quant_gguf_bits", os.path.join(ICI, "quant-gguf-bits.py"))
qgb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qgb)

MOTIF_EXPERT = re.compile(r"^blk\.(\d+)\.ffn_(gate|up|down|gate_up)_exps\.(weight|bias)$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", required=True)
    ap.add_argument("fichiers", nargs="+")
    a = ap.parse_args()
    bilan = {}
    for chemin in a.fichiers:
        # lire() ne rend pas la liste des tenseurs : on relit l'en-tête avec son lecteur (Lecteur)
        taille = os.path.getsize(chemin)
        with open(chemin, "rb") as f:
            L = qgb.Lecteur(f)
            assert f.read(4) == b"GGUF"
            L.u32()
            n_t, n_kv = L.u64(), L.u64()
            meta = {}
            for _ in range(n_kv):
                cle = L.chaine()
                v = L.valeur(L.u32())
                if not (isinstance(v, str) and v.startswith("<tableau")):
                    meta[cle] = v
            tens = []
            for _ in range(n_t):
                nom = L.chaine()
                dims = [L.u64() for _ in range(L.u32())]
                t = L.u32()
                dec = L.u64()
                tens.append((nom, dims, t, dec))
            fin_entete = f.tell()
        al = int(meta.get("general.alignment", 32))
        debut = (fin_entete + al - 1) // al * al
        arch = meta["general.architecture"]
        E = int(meta[f"{arch}.expert_count"])
        k = int(meta[f"{arch}.expert_used_count"])
        Lc = int(meta[f"{arch}.block_count"])
        par_couche = [0] * Lc
        toujours, emb_ligne, emb_total, fin_max = 0, 0, 0, 0
        types_experts = {}
        for nom, dims, t, dec in tens:
            n = 1
            for d in dims:
                n *= d
            tn, bloc, octets = qgb.TYPES[t]
            o = n // bloc * octets
            fin_max = max(fin_max, dec + o)
            m = MOTIF_EXPERT.match(nom)
            if m:
                assert dims[-1] == E, (nom, dims)
                par_couche[int(m.group(1))] += o
                types_experts[tn] = types_experts.get(tn, 0) + o
            elif nom == "token_embd.weight":
                emb_total = o
                emb_ligne = o // dims[1]
            else:
                toujours += o
        temoin = debut + fin_max == taille
        experts_total = sum(par_couche)
        e_couche = [x / E for x in par_couche]
        b = {"fichier": os.path.basename(chemin), "taille_octets": taille, "temoin_fin_de_fichier": temoin,
             "architecture": arch, "couches": Lc, "experts": E, "k": k,
             "experts_total_octets": experts_total, "octets_par_expert_couche": e_couche,
             "octets_par_expert_moyen": experts_total / (E * Lc),
             "toujours_lus_octets": toujours + emb_ligne, "enchassement_total_octets": emb_total,
             "routes_par_jeton_octets": k * experts_total / E,
             "types_des_experts_octets": types_experts}
        bilan[b["fichier"]] = b
        print(f"{b['fichier']}: témoin {'ok' if temoin else 'TOMBÉ'} ; L={Lc} E={E} k={k} ; experts {experts_total/1e9:.3f} Go, "
              f"un expert {b['octets_par_expert_moyen']/1e6:.3f} Mo ; toujours lus {b['toujours_lus_octets']/1e9:.3f} Go ; "
              f"routés par jeton {b['routes_par_jeton_octets']/1e9:.3f} Go ; table d'enchâssement {emb_total/1e9:.3f} Go")
        if not temoin:
            raise SystemExit(2)
    os.makedirs(os.path.dirname(a.sortie) or ".", exist_ok=True)
    json.dump(bilan, open(a.sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
