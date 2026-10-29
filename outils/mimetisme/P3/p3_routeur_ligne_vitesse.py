"""P3, routeur biaisé en ligne : génération (jetons par seconde), séries ABBA (06-routeur-ligne-declare.md § 7).

Usage (SANS -I) : python -X utf8 p3_routeur_ligne_vitesse.py [--blocs 2] [--n 256] [--beta 0.041]
Arm A = `troncons mesurer` sans le drapeau ; arm B = avec `--biais-cache <β>` ; tout le reste identique (gpt-oss-20b.trc, 238 emplacements,
invite-wiki-3000.txt de 708 jetons, 256 jetons gloutons, repos de 10 s avant chaque passe pour chiffrer le disque au repos, garde de production
active). Ordre A B B A par bloc, blocs enchaînés. Le verrou « P3 routeur » doit être posé par l'appelant. Mêmes garde-fous que le pilote
d'évaluation (secteur, C:, swap, RAM). Écrit mesures/mimetisme/P3/routeur-ligne/vitesse/<ordre>-<arm>.{json,txt,trace,log}, puis vitesse.json.
Règle de lecture déclarée : l'écart des moyennes B - A n'est un gain que s'il dépasse le plus grand des écarts « bras contre lui-même » et a le
même signe dans chaque bloc ; sinon « non distinguable du bruit ».
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import threading
import time

import psutil

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import p3_routeur_ligne as P  # noqa: E402

MODELES = pathlib.Path("~/dev/modeles/trc")
INVITE = pathlib.Path("~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt")
SORTIE = P.SORTIE / "vitesse"


def passe(ordre, arm, n, beta):
    SORTIE.mkdir(parents=True, exist_ok=True)
    base = SORTIE / f"{ordre:02d}-{arm}"
    cmd = [str(P.NEUF), "mesurer", "--modele", str(MODELES / "gpt-oss-20b.trc"), "--vocab", str(MODELES / "gpt-oss-20b.vocab.gguf"),
           "--invite", str(INVITE), "-n", str(n), "--emplacements", str(P.EMPLACEMENTS), "--repos", "10",
           "--sortie", f"{base}.txt", "--trace", f"{base}.trace", "--journal", f"{base}.json"]
    if arm == "B":
        cmd += ["--biais-cache", str(beta)]
    env = dict(os.environ)
    for v in ("RAYON_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        env[v] = "4"
    etat = {"fin": False, "t0": time.time(), "pic_wset": 0, "dispo_min": 1 << 62, "swap_max": 0, "c_libre_min": 1 << 62, "releves": [], "arret": None}
    th = threading.Thread(target=P.surveiller, args=(etat,), daemon=True)
    th.start()
    with open(f"{base}.log", "w", encoding="utf-8") as f:
        code = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=env).returncode
    etat["fin"] = True
    th.join(timeout=10)
    r = {"ordre": ordre, "arm": arm, "code": code, "arret": etat["arret"], "ram_disponible_min_Go": round(etat["dispo_min"] / P.GO, 2),
         "swap_max_Go": round(etat["swap_max"] / P.GO, 2), "commande": " ".join(cmd).replace("\\", "/")}
    if code == 0 and not etat["arret"]:
        j = json.loads(pathlib.Path(f"{base}.json").read_text(encoding="utf-8"))
        cg = j["compteurs_generation"]
        r.update({"jetons_s": j["generation_jetons_s"], "prefill_jetons_s": j["prefill_jetons_s"], "generation_s": j["generation_s"], "pas_generation": j["pas_generation"],
                  "defauts_par_jeton": cg["defauts_disque"] / j["pas_generation"], "defauts": cg["defauts_disque"], "h_vram": cg["h_vram"],
                  "octets_lus_par_jeton": cg["octets_lus"] / j["pas_generation"], "texte_sha256": j["texte_sha256"], "jetons": j["jetons"],
                  "s_lectures": cg["s_lectures"], "s_pas": cg["s_pas"], "secteur": j["alimentation"].get("secteur"),
                  "disque_repos_octets_s": j["disque"].get("repos_octets_s")})
    print(json.dumps({k: v for k, v in r.items() if k not in ("jetons", "commande")}, ensure_ascii=False), flush=True)
    return r


def resume(passes):
    A = [p for p in passes if p["arm"] == "A" and "jetons_s" in p]
    B = [p for p in passes if p["arm"] == "B" and "jetons_s" in p]
    moy = lambda xs: sum(xs) / len(xs)
    out = {"passes": [{k: v for k, v in p.items() if k not in ("jetons", "commande")} for p in passes]}
    if not A or not B:
        return out
    ma, mb = moy([p["jetons_s"] for p in A]), moy([p["jetons_s"] for p in B])
    bruit_a = max(p["jetons_s"] for p in A) - min(p["jetons_s"] for p in A)
    bruit_b = max(p["jetons_s"] for p in B) - min(p["jetons_s"] for p in B)
    # signe par bloc : passes 4 par 4 (A B B A)
    blocs = []
    for i in range(0, len(passes), 4):
        b = [p for p in passes[i:i + 4] if "jetons_s" in p]
        a_, b_ = [p["jetons_s"] for p in b if p["arm"] == "A"], [p["jetons_s"] for p in b if p["arm"] == "B"]
        if a_ and b_:
            blocs.append(moy(b_) - moy(a_))
    ecart = mb - ma
    out.update({"moyenne_A": ma, "moyenne_B": mb, "rapport_B_sur_A": mb / ma, "ecart": ecart, "bruit_A_max_min": bruit_a, "bruit_B_max_min": bruit_b,
                "ecarts_par_bloc": blocs, "defauts_par_jeton_A": moy([p["defauts_par_jeton"] for p in A]), "defauts_par_jeton_B": moy([p["defauts_par_jeton"] for p in B]),
                "octets_lus_par_jeton_A": moy([p["octets_lus_par_jeton"] for p in A]), "octets_lus_par_jeton_B": moy([p["octets_lus_par_jeton"] for p in B]),
                "h_A": moy([p["h_vram"] for p in A]), "h_B": moy([p["h_vram"] for p in B])})
    meme_signe = all(e > 0 for e in blocs) or all(e < 0 for e in blocs)
    if abs(ecart) > max(bruit_a, bruit_b) and meme_signe:
        out["lecture"] = "écart au-dessus du bruit de référence, même signe dans chaque bloc : " + ("gain" if ecart > 0 else "perte")
    else:
        out["lecture"] = "non distinguable du bruit"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocs", type=int, default=2)
    ap.add_argument("--n", type=int, default=256)
    ap.add_argument("--beta", default="0.041")
    a = ap.parse_args()
    if not P.VERROU.exists() or "P3 routeur" not in P.VERROU.read_text(encoding="utf-8", errors="replace"):
        raise SystemExit("le verrou « P3 routeur » doit être posé par l'appelant")
    bat = psutil.sensors_battery()
    if bat is not None and not bat.power_plugged:
        raise SystemExit("secteur débranché")
    passes = []
    k = 0
    for _ in range(a.blocs):
        for arm in "ABBA":
            k += 1
            r = passe(k, arm, a.n, a.beta)
            passes.append(r)
            if r["code"] != 0 or r["arret"]:
                print("passe en échec ou arrêtée :", r["arret"], flush=True)
                (SORTIE / "vitesse.json").write_text(json.dumps(resume(passes), ensure_ascii=False, indent=1), encoding="utf-8")
                return
    (SORTIE / "vitesse.json").write_text(json.dumps(resume(passes), ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in resume(passes).items() if k != "passes"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
