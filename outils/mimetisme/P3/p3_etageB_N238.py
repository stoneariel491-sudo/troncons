"""P3 étage B à N = 238 : deux passes de la référence f64 à routage imposé (β₁ puis β₂), l'une après l'autre.

Usage (depuis n'importe où, SANS -I pour psutil) : python -X utf8 p3_etageB_N238.py 0.041 0.05
Pose le verrou de la carte, le retire à la fin ou en cas d'échec. Garde-fous : secteur, C: libre > 30 Go, swap <= 4 Go,
RAM disponible >= 0,4 Go (3 relevés de suite). Après chaque passe : KL (juge kl, chemin 2), empreintes, et contrôle que le
routage enregistré par la passe porte, cellule par cellule, les quatre experts imposés (ce contrôle peut échouer : la passe est alors invalide).
"""
import datetime
import hashlib
import json
import pathlib
import shutil
import struct
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

SORTIE = DEPOT / "mesures/mimetisme/P3/etage-B/N238"
ENTREES = pathlib.Path("~/dev/essais/troncons/mimetisme/P3/B238")
VERROU = pathlib.Path("~/dev/verrou-carte.txt")
BASE = r1.LOURDS / "ref-openai-20b.kld"
GO = 1024 ** 3
SWAP_MAX = 4 * GO
C_MIN = 30 * GO


def sha(p):
    return r0.sha256(p)


def surveiller(etat):
    bas = 0
    sans_secteur = 0
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
        sans_secteur = 0 if secteur else sans_secteur + 1  # un relevé isolé sans secteur (08:37, basculement bref) ne tue plus la passe : 3 de suite (15 s)
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


def lire_experts(p):
    """Experts (u8 x 4) par (couche, position) d'un journal de routage : u32 L, u32 T, puis par couche et position 4 u8 + f32."""
    b = pathlib.Path(p).read_bytes()
    L, T = struct.unpack("<II", b[:8])
    out = []
    o = 8
    for _ in range(L * T):
        out.append(b[o:o + 4])
        o += 8
    return L, T, out


def passe(beta):
    nom = f"N238-b{beta}"
    imposé = ENTREES / f"routage-impose-V1-b{beta}-N31.bin"
    cible = r1.JOURNAUX / "routage" / f"p3-{nom}-N31.bin"
    (r1.JOURNAUX / "routage").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(imposé, cible)
    ok_copie = sha(cible) == sha(imposé)
    etat = {"fin": False, "t0": time.time(), "pic_wset": 0, "rss_max": 0, "dispo_min": 1 << 62, "swap_max": 0,
            "c_libre_min": 1 << 62, "releves": [], "arret": None}
    th = threading.Thread(target=surveiller, args=(etat,), daemon=True)
    th.start()
    debut = datetime.datetime.now().isoformat(timespec="seconds")
    code = r1.reference("20b", variante="openai", suffixe=f"-p3-{nom}", imposer=f"p3-{nom}-N31") if ok_copie else -1
    etat["fin"] = True
    th.join(timeout=10)
    res = {"nom": nom, "beta": beta, "fichier": str(imposé), "sha256_imposé": sha(imposé), "copie_lue_par_le_moteur_identique": ok_copie,
           "debut": debut, "code": code, "duree_s": round(time.time() - etat["t0"]),
           "pic_wset_Go": round(etat["pic_wset"] / GO, 3), "rss_max_Go": round(etat["rss_max"] / GO, 3),
           "ram_disponible_min_Go": round(etat["dispo_min"] / GO, 2), "swap_utilise_max_Go": round(etat["swap_max"] / GO, 2),
           "c_libre_min_Go": round(etat["c_libre_min"] / GO, 1), "arret": etat["arret"],
           "releves_s_dispo_swap_c_pic_secteur": etat["releves"]}
    if code == 0 and not etat["arret"]:
        test = r1.LOURDS / f"ref-openai-p3-{nom}-20b.kld"
        res["sha256_kld"] = sha(test)
        res["identique_octet_a_base"] = res["sha256_kld"] == sha(BASE)
        # contrôle de la chaîne d'imposition : le routage enregistré par la passe égale l'imposé, cellule par cellule
        L1, T1, a = lire_experts(imposé)
        L2, T2, b = lire_experts(r1.JOURNAUX / "routage" / f"ref-openai-p3-{nom}-20b.bin")
        res["imposition_cellules_egales"] = sum(1 for x, y in zip(a, b) if x == y)
        res["imposition_cellules_total"] = len(a)
        res["imposition_dims"] = [[L1, T1], [L2, T2]]
        res["kl_chemin2"] = r0.juge_kl(BASE, test, f"p3-{nom}")
        for ext in ("json", "csv"):
            shutil.copyfile(r0.JOURNAUX / f"juge-kl-p3-{nom}.{ext}", SORTIE / f"juge-kl-p3-{nom}.{ext}")
        shutil.copyfile(r1.JOURNAUX / f"ref-openai-p3-{nom}-20b.json", SORTIE / f"ref-openai-p3-{nom}-20b.json")
        shutil.copyfile(r1.JOURNAUX / f"ref-openai-p3-{nom}-20b.log", SORTIE / f"ref-openai-p3-{nom}-20b.log")
    (SORTIE / f"passe-{nom}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "releves_s_dispo_swap_c_pic_secteur"}, ensure_ascii=False, indent=1), flush=True)
    return res


def main(betas):
    SORTIE.mkdir(parents=True, exist_ok=True)
    bat = psutil.sensors_battery()
    if bat is not None and not bat.power_plugged:
        raise SystemExit("secteur débranché")
    if shutil.disk_usage("C:/").free < C_MIN:
        raise SystemExit("C: libre sous 30 Go")
    if VERROU.exists():
        raise SystemExit(f"verrou présent : {VERROU.read_text(encoding='utf-8', errors='replace')}")
    VERROU.write_text(f"P3 N=238, agent, {datetime.datetime.now().isoformat(timespec='seconds')}\n", encoding="utf-8")
    try:
        for b in betas:
            res = passe(b)
            if res["code"] != 0 or res["arret"]:
                print("passe en échec ou arrêtée, séance interrompue :", res["arret"], flush=True)
                break
    finally:
        VERROU.unlink(missing_ok=True)


if __name__ == "__main__":
    main(sys.argv[1:])
