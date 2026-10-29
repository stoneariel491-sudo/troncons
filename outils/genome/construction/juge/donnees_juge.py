"""Les CSV du juge pour le mémoire (Tome III), tirés des journaux commités du juge.

  python -I -X utf8 donnees_juge.py   → mesures/genome/construction/juge/figures/*.csv

- kl-par-fenetre.csv : jeu (r1, neuf), chemin (f64-substituee, moteur), variante, fenêtre, KL moyenne ;
- apparie-par-fenetre.csv : jeu, chemin, comparaison, fenêtre, d (différence appariée moyenne) ;
- routage-grille.csv : couche, expert, appels sur R1, appels sur les fenêtres neuves (référence f64) ;
- vitesse-passes.csv et disque-passes.csv : chaque passe des deux séances du juge ;
- (J-T1-echantillon.csv, déjà écrit par decodeur_juge.py : la part des −0 de chaque expert tiré.)
"""
import json
import pathlib
import struct
import sys

import numpy as np

DEPOT = pathlib.Path(__file__).resolve().parents[4]
J = DEPOT / "mesures" / "genome" / "construction" / "juge"
F = J / "figures"

KL = [("r1", "f64-substituee", "frontiere", "r1-frontiere-768"), ("r1", "f64-substituee", "lambda1", "r1-synonyme-768"),
      ("r1", "f64-substituee", "lambda0", "r1-synonyme-l0-768"), ("r1", "moteur", "lambda0", "r1-moteur-rapide-l0"),
      ("r1", "moteur", "lambda1", "r1-moteur-rapide-l1"), ("neuf", "moteur", "lambda0", "neuf-moteur-rapide-l0"),
      ("neuf", "moteur", "lambda1", "neuf-moteur-rapide-l1"), ("neuf", "moteur", "exact", "neuf-moteur-exact-20b"),
      ("neuf", "f64-substituee", "lambda0", "neuf-sub-l0"), ("neuf", "f64-substituee", "frontiere", "neuf-sub-frontiere"),
      ("neuf", "f64-substituee", "lambda1", "neuf-sub-l1")]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    F.mkdir(parents=True, exist_ok=True)
    lignes = ["jeu,chemin,variante,fenetre,kl"]
    for jeu, ch, var, nom in KL:
        p = J / "kl" / f"kl-{nom}.json"
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            for i, v in enumerate(d["kl_par_fenetre"]):
                lignes.append(f"{jeu},{ch},{var},{i},{v:.9f}")
    (F / "kl-par-fenetre.csv").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    lignes = ["jeu,chemin,comparaison,fenetre,d"]
    for p in sorted((J / "kl").glob("apparie-*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        nom = p.stem.replace("apparie-", "")
        jeu = "r1" if nom.startswith("r1") else "neuf"
        ch = "moteur" if "moteur" in nom else "f64-substituee"
        for i, v in enumerate(d["d_par_fenetre"]):
            lignes.append(f"{jeu},{ch},{nom},{i},{v:.9f}")
    (F / "apparie-par-fenetre.csv").write_text("\n".join(lignes) + "\n", encoding="utf-8")

    def comptes(ch):
        b = pathlib.Path(ch).read_bytes()
        L, P = struct.unpack_from("<II", b, 0)
        e = np.frombuffer(b, dtype=np.uint8, offset=8).reshape(L, P, 8)[:, :, :4]
        c = np.zeros((L, 32), dtype=np.int64)
        for l in range(L):
            u, n = np.unique(e[l], return_counts=True)
            c[l, u] = n
        return c
    r1 = comptes(DEPOT / "mesures/moteur/R/r1/routage/ref-openai-bis-20b.bin")
    nf = comptes(J / "kl" / "routage-ref-juge-20b.bin")
    lignes = ["couche,expert,appels_r1,appels_neuf"]
    for l in range(r1.shape[0]):
        for x in range(32):
            lignes.append(f"{l},{x},{r1[l, x]},{nf[l, x]}")
    (F / "routage-grille.csv").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    lv = ["modele,passe,lettre,fichier,generation_jetons_s,prefill_jetons_s,octets_troncons_par_pas,h_vram,texte_sha256,sous_charge"]
    ld = ["modele,passe,lettre,fichier,go_s,sous_charge"]
    for m in ("120b", "20b"):
        p = J / "vitesse" / f"seance-{m}.json"
        if not p.exists():
            continue
        s = json.loads(p.read_text(encoding="utf-8"))
        for x in s["passes"]:
            lv.append(f"{m},{x['passe']},{x['lettre']},{x['fichier'].split('/')[-1]},{x.get('generation_jetons_s')},{x.get('prefill_jetons_s')},"
                      f"{x.get('octets_troncons_par_pas')},{x.get('h_vram')},{x.get('texte_sha256')},{int(x['sous_charge'])}")
        for x in s["disque"]:
            ld.append(f"{m},{x['passe']},{x['lettre']},{x['fichier'].split('/')[-1]},{x.get('go_s')},{int(x['sous_charge'])}")
    (F / "vitesse-passes.csv").write_text("\n".join(lv) + "\n", encoding="utf-8")
    (F / "disque-passes.csv").write_text("\n".join(ld) + "\n", encoding="utf-8")
    print("écrit :", sorted(x.name for x in F.glob("*.csv")))


if __name__ == "__main__":
    main()
