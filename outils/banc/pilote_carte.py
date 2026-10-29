"""Pilote du banc carte : chaque passe de `carte.exe` encadrée par un relevé nvidia-smi
(utilisation, VRAM occupée, horloges, température, puissance) ; témoins `--fausser` ; ordre ABBA
entre Vulkan et DirectX 12 ; porte d'entrée : on attend que la VRAM libre suffise (la carte est
partagée avec d'autres agents ; sous WDDM, un dépassement déborde en silence vers la RAM et
fausserait tout).

Bibliothèque standard seulement. Usage :
  python -I outils/banc/pilote_carte.py --exe CHEMIN/carte.exe --sortie JOURNAL.jsonl [--etapes transfert,vram,gemv]
"""

import argparse
import json
import subprocess
import sys
import time

CHAMPS = "utilization.gpu,memory.used,memory.total,clocks.sm,clocks.mem,temperature.gpu,power.draw,pcie.link.gen.current,pcie.link.width.current,clocks_throttle_reasons.active"


def etat_carte():
    p = subprocess.run(["nvidia-smi", f"--query-gpu={CHAMPS}", "--format=csv,noheader,nounits"], capture_output=True, text=True)
    v = [x.strip() for x in p.stdout.strip().split(",")]
    return dict(zip(CHAMPS.split(","), v))


def attendre_vram(besoin_mio, plafond_s=900):
    """Attend que memory.total - memory.used >= besoin + 300 Mio de marge. Rend l'attente en s."""
    t0 = time.time()
    while True:
        e = etat_carte()
        libre = float(e["memory.total"]) - float(e["memory.used"])
        if libre >= besoin_mio + 300:
            return time.time() - t0, libre
        if time.time() - t0 > plafond_s:
            return None, libre
        time.sleep(5)


def analyser(ligne):
    d = {}
    for m in ligne.split()[1:]:
        if "=" in m:
            k, v = m.split("=", 1)
            try:
                d[k] = float(v)
            except ValueError:
                d[k] = v.strip('"')
    return d


def lancer(exe, args, besoin_mio):
    attente, libre = attendre_vram(besoin_mio)
    avant = etat_carte()
    t0 = time.time()
    p = subprocess.run([exe] + args, capture_output=True, text=True, encoding="utf-8")
    t1 = time.time()
    apres = etat_carte()
    res = [analyser(l) for l in p.stdout.splitlines() if l.startswith("RESULTAT")]
    if p.returncode != 0:
        res = [{"erreur": (p.stdout[-400:] + p.stderr[-1200:])}]
    for r in res:
        r.update({"args": args, "debut": t0, "fin": t1, "attente_vram_s": attente, "vram_libre_mio_avant": libre,
                  "carte_avant": avant, "carte_apres": apres})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--etapes", default="temoins,transfert,vram,gemv")
    a = ap.parse_args()
    etapes = a.etapes.split(",")
    j = open(a.sortie, "a", encoding="utf-8")

    def noter(genre, liste):
        for r in liste:
            r["genre"] = genre
            j.write(json.dumps(r, ensure_ascii=False) + "\n")
            j.flush()
            court = {k: r.get(k) for k in ("op", "api", "taille", "format", "residence", "lot", "go_s_mur_mediane",
                                           "go_s_carte_mediane", "temoin", "temoin_aller_retour", "temoin_somme", "erreur")
                     if r.get(k) is not None}
            print(genre, court, flush=True)

    if "temoins" in etapes:
        noter("temoin", lancer(a.exe, ["transfert", "--api", "vulkan", "--tailles", "16M", "--passes", "1", "--fausser"], 200))
        noter("temoin", lancer(a.exe, ["vram", "--api", "vulkan", "--taille", "64M", "--passes", "1", "--fausser"], 200))
        noter("temoin", lancer(a.exe, ["gemv", "--api", "vulkan", "--format", "q4", "--m", "4096", "--passes", "1", "--fausser"], 200))
        noter("temoin", lancer(a.exe, ["gemv", "--api", "vulkan", "--format", "f16", "--m", "2048", "--passes", "1", "--fausser"], 200))
    if "transfert" in etapes:
        for api in ["vulkan", "dx12", "dx12", "vulkan"]:
            noter("transfert", lancer(a.exe, ["transfert", "--api", api, "--tailles", "64K,1M,4M,16M,64M,256M", "--passes", "3"], 1200))
    if "vram" in etapes:
        for api in ["vulkan", "dx12", "dx12", "vulkan"]:
            noter("vram", lancer(a.exe, ["vram", "--api", api, "--taille", "512M", "--passes", "5"], 700))
    if "gemv" in etapes:
        cas = [
            ["--format", "f16", "--m", "8192", "--k", "8192"],          # 128 Mio de poids
            ["--format", "q4", "--m", "32768", "--k", "8192"],          # 144 Mio de poids
            ["--format", "q4", "--m", "32768", "--k", "8192", "--lot", "8"],
            ["--format", "f16", "--m", "8192", "--k", "8192", "--lot", "8"],
        ]
        for c in cas:
            for api in ["vulkan", "dx12", "dx12", "vulkan"]:
                noter("gemv", lancer(a.exe, ["gemv", "--api", api] + c + ["--passes", "5", "--reps", "30"], 500))
        # Poids laissés en RAM hôte (hote) ou dans la fenêtre BAR (bar), lus par le shader sans copie.
        for res in ["hote", "bar"]:
            for api in ["vulkan", "dx12", "dx12", "vulkan"]:
                noter("gemv", lancer(a.exe, ["gemv", "--api", api, "--format", "q4", "--m", "32768", "--k", "8192",
                                             "--residence", res, "--passes", "3", "--reps", "5"], 200))
    if "complement" in etapes:
        # Noyau q4 naïf contre q4b (4 lectures en vol par fil), ABBA deux fois.
        for fmt in ["q4", "q4b", "q4b", "q4"] * 2:
            noter("gemv", lancer(a.exe, ["gemv", "--api", "vulkan", "--format", fmt, "--m", "32768", "--k", "8192",
                                         "--passes", "5", "--reps", "30"], 500))
        # Plafonds de calcul.
        for t in ["f32", "f16", "dot4i8", "deq4"]:
            for api in ["vulkan", "dx12", "dx12", "vulkan"]:
                noter("alu", lancer(a.exe, ["alu", "--api", api, "--type", t, "--passes", "5"], 100))
        # Transferts répétés : le meilleur passage borne par en dessous ce que la machine donne au calme.
        for _ in range(3):
            noter("transfert", lancer(a.exe, ["transfert", "--api", "vulkan", "--tailles", "64M,256M", "--passes", "3"], 1200))
    j.close()


if __name__ == "__main__":
    main()
