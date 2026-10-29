"""Profondeur de file et taille des lectures du disque, échantillonnées pendant des passes de la base,
pour trancher l'hypothèse du § 3.2 de mesures/gpt-oss.md : sur gpt-oss-120b, le cache d'experts de
llama.cpp ralentit la génération parce que ses défauts sont lus par fautes de page synchrones (file peu
profonde), alors qu'en `cmoe` six fils de calcul provoquent des fautes en parallèle (file profonde).

Compteurs PDH (noms anglais, PdhAddEnglishCounterW), « PhysicalDisk(_Total) » :
  Avg. Disk Read Queue Length (file moyenne en lecture), Disk Reads/sec, Avg. Disk Bytes/Read,
  Disk Read Bytes/sec ; toutes les 0,5 s, avec l'heure absolue (time.time()).

SEUIL DÉCLARÉ AVANT LA MESURE (2026-10-15, avant toute passe ; l heure est celle du commit dac1ac3) : l'hypothèse tient si, pendant la génération,
la file moyenne en lecture de `cmoe` est au moins le double de celle de `cache` (moyennes sur les
fenêtres de génération des passes de chaque configuration). Elle tombe si le rapport est inférieur à
1,5. Entre les deux : non tranché. La taille moyenne des lectures est publiée à côté (l'hypothèse
prédit des lectures petites dans les deux cas).

Témoin : sur chaque échantillon d'activité (plus de 50 lectures/s), Disk Read Bytes/sec doit valoir
Disk Reads/sec × Avg. Disk Bytes/Read à 10 % près en médiane ; il tomberait si un compteur était mal
lu (mauvais format, mauvais nom). Cassure : --casser multiplie la taille par lecture par 2 avant le
témoin, qui doit tomber.

Usage :
  échantillonner : python -I gptoss_file_disque.py echantillonner <sortie.csv> <fichier d'arrêt>
                   (s'arrête quand le fichier d'arrêt existe)
  analyser       : python -I gptoss_file_disque.py analyser <echantillons.csv> <dossier de la série>
                   <sortie.json> [--casser]
"""
import csv
import ctypes
import glob
import json
import os
import statistics
import sys
import time

COMPTEURS = [r"\PhysicalDisk(_Total)\Avg. Disk Read Queue Length", r"\PhysicalDisk(_Total)\Disk Reads/sec",
             r"\PhysicalDisk(_Total)\Avg. Disk Bytes/Read", r"\PhysicalDisk(_Total)\Disk Read Bytes/sec"]
NOMS = ["file_lecture", "lectures_s", "octets_par_lecture", "octets_s"]


class ValeurPDH(ctypes.Structure):
    _fields_ = [("CStatus", ctypes.c_ulong), ("pad", ctypes.c_ulong), ("doubleValue", ctypes.c_double)]


def echantillonner(sortie, arret):
    pdh = ctypes.windll.pdh
    q = ctypes.c_void_p()
    if pdh.PdhOpenQueryW(None, None, ctypes.byref(q)) != 0:
        raise OSError("PdhOpenQueryW")
    cs = []
    for n in COMPTEURS:
        c = ctypes.c_void_p()
        if pdh.PdhAddEnglishCounterW(q, ctypes.c_wchar_p(n), None, ctypes.byref(c)) != 0:
            raise OSError("PdhAddEnglishCounterW " + n)
        cs.append(c)
    pdh.PdhCollectQueryData(q)
    with open(sortie, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t"] + NOMS)
        while not os.path.exists(arret):
            time.sleep(0.5)
            pdh.PdhCollectQueryData(q)
            ligne = [round(time.time(), 3)]
            for c in cs:
                v = ValeurPDH()
                pdh.PdhGetFormattedCounterValue(c, 0x200, None, ctypes.byref(v))
                ligne.append(v.doubleValue)
            w.writerow(ligne)
            f.flush()
    return 0


def analyser(echantillons, dossier, sortie, casser):
    lignes = [{k: float(v) for k, v in l.items()} for l in csv.DictReader(open(echantillons, encoding="utf-8"))]
    # témoin de cohérence des compteurs
    rapports = []
    for l in lignes:
        if l["lectures_s"] > 50:
            taille = l["octets_par_lecture"] * (2 if casser else 1)
            rapports.append(l["octets_s"] / (l["lectures_s"] * taille))
    med = statistics.median(rapports)
    temoin = {"echantillons_actifs": len(rapports), "mediane_rapport": med, "reussi": abs(med - 1) <= 0.10}
    passes = {}
    for f in sorted(glob.glob(os.path.join(dossier, "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        if not d.get("generation", {}).get("ms"):
            continue
        fin = time.mktime(time.strptime(d["date"], "%Y-%m-%d %H:%M:%S"))
        t0 = fin - d["generation"]["ms"] / 1000.0
        fen = [l for l in lignes if t0 + 2 <= l["t"] <= fin - 2]
        if not fen:
            continue
        passes[d["etiquette"]] = {
            "echantillons": len(fen),
            "file_lecture_moyenne": statistics.fmean(l["file_lecture"] for l in fen),
            "lectures_s_moyennes": statistics.fmean(l["lectures_s"] for l in fen),
            "octets_par_lecture_moyens": (sum(l["octets_s"] for l in fen) / max(1e-9, sum(l["lectures_s"] for l in fen))),
            "debit_go_s": statistics.fmean(l["octets_s"] for l in fen) / 1e9,
            "generation_js": d["generation"]["jetons_s"]}
    par_conf = {}
    for e, v in passes.items():
        conf = e.split("-")[1]
        par_conf.setdefault(conf, []).append(v)
    resume = {c: {k: statistics.fmean(x[k] for x in vs) for k in vs[0]} for c, vs in par_conf.items()}
    verdict = None
    if "cmoe" in resume and "cache" in resume:
        r = resume["cmoe"]["file_lecture_moyenne"] / max(1e-9, resume["cache"]["file_lecture_moyenne"])
        verdict = {"rapport_file_cmoe_sur_cache": r,
                   "hypothese": "tient" if r >= 2 else ("tombe" if r < 1.5 else "non tranchée")}
    out = {"temoin": temoin, "passes": passes, "par_configuration": resume, "verdict": verdict}
    json.dump(out, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if temoin["reussi"] else 2


if __name__ == "__main__":
    if sys.argv[1] == "echantillonner":
        sys.exit(echantillonner(sys.argv[2], sys.argv[3]))
    sys.exit(analyser(sys.argv[2], sys.argv[3], sys.argv[4], "--casser" in sys.argv))
