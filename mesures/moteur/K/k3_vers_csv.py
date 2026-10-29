"""K3 : les CSV des figures du mémoire, tirés des journaux commités sous k3/ (aucun chiffre recopié).

Sorties (csv/) :
- k3-par-noyau.csv : pour chaque modèle et chaque noyau, le pire écart des cas à seuil, le seuil, la
  marge (seuil / pire écart), le nombre de cas et la somme des différences des cas exacts ; une
  ligne par cassure aussi (le témoin visé doit tomber) ;
- k3-chaine-kl.csv : la KL par position de la chaîne de bout en bout (routage libre, imposé, et les
  deux cassures sous routage imposé), pour la figure de la queue lourde et de la fenêtre.
Usage : python -I -X utf8 k3_vers_csv.py (depuis mesures/moteur/K).
"""
import csv
import json
from pathlib import Path

ICI = Path(__file__).resolve().parent
K3 = ICI / "k3"
SORTIE = ICI / "csv"
SEUILS = {"gemv_mxfp4": 1e-5, "gemv_q8_0": 1e-5, "gemv_f32": 1e-5, "attention": 1e-5,
          "rmsnorm": 1e-6, "rope_yarn": 1e-6, "swiglu_oai": 1e-6, "routeur_topk": 1e-6}


def lire(nom):
    return json.loads((K3 / nom).read_text(encoding="utf8"))


def main():
    SORTIE.mkdir(exist_ok=True)
    lignes = []
    for modele in ("20b", "120b"):
        d = lire(f"k3-gptoss{modele}.json")
        for noyau, v in d["par_noyau"].items():
            seuil = SEUILS.get(noyau)
            pire = v["pire_ecart"]
            lignes.append({"modele": f"gpt-oss-{modele}", "essai": "temoin", "noyau": noyau, "cas": v["cas"],
                           "pire_ecart": pire, "seuil": seuil if seuil else "",
                           "marge": (seuil / pire) if (seuil and pire > 0) else "",
                           "differences": v["differences"], "tient": v["tient"], "deterministe": v["deterministe"]})
    for f in sorted(K3.glob("k3-casse-*-gptoss20b.json")):
        d = lire(f.name)
        vise = d["casser"]
        v = d["par_noyau"][vise]
        lignes.append({"modele": "gpt-oss-20b", "essai": f"casse:{vise}", "noyau": vise, "cas": v["cas"],
                       "pire_ecart": v["pire_ecart"], "seuil": SEUILS.get(vise, ""), "marge": "",
                       "differences": v["differences"], "tient": v["tient"], "deterministe": v["deterministe"]})
        assert d["vise_tombe"] and d["autres_tiennent"], f.name
    with open(SORTIE / "k3-par-noyau.csv", "w", newline="", encoding="utf8") as s:
        w = csv.DictWriter(s, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)

    series = {"kl_libre": "k3-chaine-d1-gptoss20b.csv", "kl_impose": "k3-chaine-d2-gptoss20b.csv",
              "kl_impose_casse_fenetre": "k3-chaine-d2-casse-fenetre-gptoss20b.csv",
              "kl_impose_casse_poids": "k3-chaine-d2-casse-poids-gptoss20b.csv"}
    colonnes = {}
    jetons = None
    for nom, fichier in series.items():
        r = list(csv.DictReader(open(K3 / fichier, encoding="utf8")))
        colonnes[nom] = [x["kl"] for x in r]
        jetons = [x["jeton"] for x in r]
    with open(SORTIE / "k3-chaine-kl.csv", "w", newline="", encoding="utf8") as s:
        w = csv.writer(s)
        w.writerow(["position", "jeton", *series.keys()])
        for p in range(len(jetons)):
            w.writerow([p, jetons[p], *(colonnes[n][p] for n in series)])
    print(f"{len(lignes)} lignes dans k3-par-noyau.csv, {len(jetons)} positions dans k3-chaine-kl.csv")


if __name__ == "__main__":
    main()
