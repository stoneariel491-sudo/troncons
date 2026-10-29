"""P3, routeur biaisé en ligne : pilote des passes d'évaluation du moteur (gpt-oss-20b, 10 fenêtres de R1, 238 emplacements).

Critères et protocole : mesures/mimetisme/P3/06-routeur-ligne-declare.md (commité avant toute passe).
Usage (SANS -I, psutil est un paquet utilisateur) :
    python -X utf8 p3_routeur_ligne.py P0 B0.041 B0.3 P0b B0.05 P-1:3 [Bm0.041]
Passes :
    P-1    binaire construit depuis le HEAD d'avant l'option (troncons-avant.exe), sans drapeau
    P0     binaire neuf, sans drapeau (base de comparaison)
    P0b    binaire neuf, --biais-cache 0 (témoin T0 : doit égaler P0 au bit)
    B<β>   binaire neuf, --biais-cache <β>   (Bm0.041 : β = -0,041, cassure de signe)
Le verrou de la carte est posé par l'appelant (il doit contenir « P3 routeur »). Garde-fous pendant une passe : secteur (3 relevés de
suite sans), C: libre > 30 Go, swap <= 4 Go, RAM disponible >= 0,4 Go (3 relevés) ; sinon le processus du moteur est tué et la séance
s'arrête. Chaque passe écrit son journal JSON, son CSV d'empreintes et sa trace sous mesures/mimetisme/P3/routeur-ligne/ ; le .kld (lourd)
va sous essais/.
"""
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading
import time

import psutil

DEPOT = pathlib.Path(__file__).resolve().parents[3]
CIBLE = pathlib.Path("~/dev/cibles/troncons-P3/release")
NEUF = CIBLE / "troncons.exe"
AVANT = CIBLE / "troncons-avant.exe"
MODELE = pathlib.Path("~/dev/modeles/trc/gpt-oss-20b.trc")
BASE = pathlib.Path("~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld")
LOURDS = pathlib.Path("~/dev/essais/troncons/mimetisme/P3/routeur-ligne")
SORTIE = DEPOT / "mesures/mimetisme/P3/routeur-ligne"
VERROU = pathlib.Path("~/dev/verrou-carte.txt")
EMPLACEMENTS = 238
GO = 1024 ** 3
SWAP_MAX = 4 * GO
C_MIN = 30 * GO


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def config(nom):
    if nom == "P-1":
        return AVANT, []
    if nom == "P0":
        return NEUF, []
    if nom == "P0b":
        return NEUF, ["--biais-cache", "0"]
    if nom.startswith("Bm"):
        return NEUF, ["--biais-cache", "-" + nom[2:]]
    if nom.startswith("B"):
        return NEUF, ["--biais-cache", nom[1:]]
    raise SystemExit(f"passe inconnue : {nom}")


def surveiller(etat):
    bas = 0
    sans_secteur = 0
    while not etat["fin"]:
        proc = None
        for p in psutil.process_iter(["name"]):
            if (p.info["name"] or "").lower().startswith("troncons"):
                proc = p
                break
        vm, sw = psutil.virtual_memory(), psutil.swap_memory()
        libre_c = shutil.disk_usage("C:/").free
        bat = psutil.sensors_battery()
        secteur = True if bat is None else bat.power_plugged
        pic = 0
        if proc is not None:
            try:
                mi = proc.memory_info()
                pic = getattr(mi, "peak_wset", mi.rss)
                etat["pic_wset"] = max(etat["pic_wset"], pic)
            except psutil.Error:
                pass
        etat["dispo_min"] = min(etat["dispo_min"], vm.available)
        etat["swap_max"] = max(etat["swap_max"], sw.used)
        etat["c_libre_min"] = min(etat["c_libre_min"], libre_c)
        etat["releves"].append([round(time.time() - etat["t0"]), round(vm.available / GO, 2), round(sw.used / GO, 2),
                                round(libre_c / GO, 1), round(pic / GO, 2), secteur])
        bas = bas + 1 if vm.available < 0.4 * GO else 0
        sans_secteur = 0 if secteur else sans_secteur + 1
        raison = None
        if sans_secteur >= 3:
            raison = "secteur coupé"
        elif libre_c < C_MIN:
            raison = "C: libre sous 30 Go"
        elif sw.used > SWAP_MAX:
            raison = "swap au-dessus de 4 Go"
        elif bas >= 3:
            raison = "RAM disponible sous 0,4 Go (3 relevés)"
        if raison and proc is not None:
            etat["arret"] = raison
            try:
                proc.kill()
            except psutil.Error:
                pass
            break
        time.sleep(5)


def passe(nom, fenetres=10):
    exe, extra = config(nom)
    LOURDS.mkdir(parents=True, exist_ok=True)
    SORTIE.mkdir(parents=True, exist_ok=True)
    kld = LOURDS / f"{nom}.kld"  # pour une passe partielle (fenetres < 10), le .kld n'est pas écrit si positions != n_ctx : ici il l'est toujours
    csv = SORTIE / f"{nom}-empreintes.csv"
    trace = SORTIE / f"{nom}.trace"
    js = SORTIE / f"{nom}.json"
    log = SORTIE / f"{nom}.log"
    cmd = [str(exe), "evaluer", "--modele", str(MODELE), "--base", str(BASE), "--fenetres", str(fenetres), "--positions", "512",
           "--emplacements", str(EMPLACEMENTS), "--sortie", str(kld), "--empreintes", str(csv), "--trace", str(trace), "--journal", str(js)] + extra
    env = dict(os.environ)
    for v in ("RAYON_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        env[v] = "4"
    etat = {"fin": False, "t0": time.time(), "pic_wset": 0, "dispo_min": 1 << 62, "swap_max": 0, "c_libre_min": 1 << 62, "releves": [], "arret": None}
    th = threading.Thread(target=surveiller, args=(etat,), daemon=True)
    th.start()
    debut = datetime.datetime.now().isoformat(timespec="seconds")
    with open(log, "w", encoding="utf-8") as f:
        code = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=env).returncode
    etat["fin"] = True
    th.join(timeout=10)
    res = {"passe": nom, "commande": " ".join(cmd).replace("\\", "/"), "debut": debut, "code": code, "duree_s": round(time.time() - etat["t0"]),
           "pic_wset_Go": round(etat["pic_wset"] / GO, 3), "ram_disponible_min_Go": round(etat["dispo_min"] / GO, 2),
           "swap_max_Go": round(etat["swap_max"] / GO, 2), "c_libre_min_Go": round(etat["c_libre_min"] / GO, 1), "arret": etat["arret"], "fils": 4}
    if code == 0 and not etat["arret"]:
        res["sha256_kld"] = sha(kld)
        res["sha256_trace"] = sha(trace)
        res["sha256_csv"] = sha(csv)
        j = json.loads(js.read_text(encoding="utf-8"))
        res["defauts_disque"] = j["compteurs"]["defauts_disque"]
        res["acces"] = j["compteurs"]["acces"]
        res["pas"] = j["pas"]
        res["pas_s"] = j["pas_s"]
        res["ppl_positions_notees"] = j["ppl_positions_notees"]
    (SORTIE / f"{nom}-pilote.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False), flush=True)
    return res


def main(noms):
    bat = psutil.sensors_battery()
    if bat is not None and not bat.power_plugged:
        raise SystemExit("secteur débranché")
    if shutil.disk_usage("C:/").free < C_MIN:
        raise SystemExit("C: libre sous 30 Go")
    if not VERROU.exists() or "P3 routeur" not in VERROU.read_text(encoding="utf-8", errors="replace"):
        raise SystemExit("le verrou « P3 routeur » doit être posé par l'appelant")
    for arg in noms:
        # « P-1:3 » : les trois premières fenêtres seulement (le cache n'influe pas sur les logits ; empreintes et trace se comparent en préfixe)
        nom, _, fen = arg.partition(":")
        res = passe(nom, int(fen) if fen else 10)
        if res["code"] != 0 or res["arret"]:
            print("passe en échec ou arrêtée, séance interrompue :", res["arret"], flush=True)
            break


if __name__ == "__main__":
    main(sys.argv[1:])
