"""P3 étage B : une passe de la référence f64 à routage imposé, sa RAM de pointe, sa KL (chemin 2).

Usage (depuis mesures/moteur/R) : python -I -X utf8 p3_etageB.py <nom> <fichier.bin>
  nom : T0 (β = 0), T1 (cassure 1 %), b0.06, b0.07 ...
Garde-fous : arrêt propre de la passe si le secteur est coupé, si C: libre < 30 Go, ou si la RAM disponible
reste sous 0,4 Go pendant 3 relevés de suite. Le relevé (toutes les 5 s) est écrit dans le journal.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import threading
import time

import psutil

DEPOT = pathlib.Path("~/dev/active/troncons")
R = DEPOT / "mesures/moteur/R"
sys.path.insert(0, str(R))
import r1_reference as r1  # noqa: E402
import r0_ecart as r0  # noqa: E402

SORTIE = DEPOT / "mesures/mimetisme/P3/etage-B"
BASE = r1.LOURDS / "ref-openai-20b.kld"
GO = 1024 ** 3


def surveiller(etat):
    bas = 0
    while not etat["fin"]:
        proc = None
        for p in psutil.process_iter(["name"]):
            if p.info["name"] == "juge.exe":
                proc = p
                break
        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()
        libre_c = shutil.disk_usage("C:/").free
        bat = psutil.sensors_battery()
        secteur = True if bat is None else bat.power_plugged
        pic = 0
        if proc is not None:
            try:
                mi = proc.memory_info()
                pic = getattr(mi, "peak_wset", mi.rss)
                etat["pic_wset"] = max(etat["pic_wset"], pic)
                etat["rss_max"] = max(etat["rss_max"], mi.rss)
            except psutil.Error:
                pass
        etat["dispo_min"] = min(etat["dispo_min"], vm.available)
        etat["swap_max"] = max(etat["swap_max"], sw.used)
        etat["c_libre_min"] = min(etat["c_libre_min"], libre_c)
        etat["releves"].append([round(time.time() - etat["t0"]), round(vm.available / GO, 2), round(sw.used / GO, 2),
                                round(libre_c / GO, 1), round(pic / GO, 2), secteur])
        bas = bas + 1 if vm.available < 0.4 * GO else 0
        raison = None
        if not secteur:
            raison = "secteur coupé"
        elif libre_c < 30 * GO:
            raison = "C: libre sous 30 Go"
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


def passe(nom, fichier):
    cible = r1.JOURNAUX / "routage" / f"p3-{nom}-N19.bin"
    (r1.JOURNAUX / "routage").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(fichier, cible)
    etat = {"fin": False, "t0": time.time(), "pic_wset": 0, "rss_max": 0, "dispo_min": 1 << 62, "swap_max": 0,
            "c_libre_min": 1 << 62, "releves": [], "arret": None}
    th = threading.Thread(target=surveiller, args=(etat,), daemon=True)
    th.start()
    code = r1.reference("20b", variante="openai", suffixe=f"-p3-{nom}", imposer=f"p3-{nom}-N19")
    etat["fin"] = True
    th.join(timeout=10)
    res = {"nom": nom, "fichier": str(fichier), "code": code, "duree_s": round(time.time() - etat["t0"]),
           "pic_wset_Go": round(etat["pic_wset"] / GO, 3), "rss_max_Go": round(etat["rss_max"] / GO, 3),
           "ram_disponible_min_Go": round(etat["dispo_min"] / GO, 2), "swap_utilise_max_Go": round(etat["swap_max"] / GO, 2),
           "c_libre_min_Go": round(etat["c_libre_min"] / GO, 1), "arret": etat["arret"], "releves_s_dispo_swap_c_pic_secteur": etat["releves"]}
    if code == 0 and not etat["arret"]:
        test = r1.LOURDS / f"ref-openai-p3-{nom}-20b.kld"
        res["sha256_kld"] = r0.sha256(test)
        res["kl_chemin2"] = r0.juge_kl(BASE, test, f"p3-{nom}")
        res["identique_octet_a_base"] = res["sha256_kld"] == r0.sha256(BASE)
    (SORTIE / f"passe-{nom}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "releves_s_dispo_swap_c_pic_secteur"}, ensure_ascii=False, indent=1), flush=True)
    return res


if __name__ == "__main__":
    SORTIE.mkdir(parents=True, exist_ok=True)
    passe(sys.argv[1], sys.argv[2])
