"""Base de comparaison : llama.cpp b11515 (CUDA 12.4) et Qwen3.5-9B Q4_K_M, en VRAM puis avec
une partie des couches sur le processeur, en projection de fichier (mmap) ou en lecture directe.
Configuration : « ngl:mode » ou « ngl:mode:ncmoe » (ncmoe = couches dont les experts restent sur le
processeur, pour un modèle MoE plus gros que la VRAM). Chaque passe note la source d'alimentation
(secteur ou batterie) avant et après : sur batterie, la carte est bridée (plafond de puissance 52,6 W).

Une configuration = un processus llama-bench (génération seule, -p 0) : on relève pendant sa vie
la mémoire de travail de pointe du processus (GetProcessMemoryInfo, PeakWorkingSetSize et
PeakPagefileUsage = mémoire privée engagée) et la VRAM occupée de toute la carte (nvidia-smi, la
carte est partagée : on note la valeur au repos juste avant). Ordre ABBA sur la liste.

Bibliothèque standard seulement. Usage :
  python -I -X utf8 outils/banc/pilote_llama.py --bin ~/dev/modeles/llama.cpp-b11515
         --modele ~/dev/modeles/gguf/Qwen3.5-9B-Q4_K_M.gguf --sortie JOURNAL.jsonl
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import subprocess
import threading
import time


class PMC(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


k32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)
k32.GetSystemPowerStatus.argtypes = [ctypes.c_void_p]
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
psapi.GetProcessMemoryInfo.argtypes = [wt.HANDLE, ctypes.POINTER(PMC), wt.DWORD]


class SPS(ctypes.Structure):
    _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte), ("BatteryLifePercent", ctypes.c_ubyte),
                ("SystemStatusFlag", ctypes.c_ubyte), ("BatteryLifeTime", wt.DWORD), ("BatteryFullLifeTime", wt.DWORD)]


def secteur():
    """(1 sur secteur ou 0 sur batterie, charge en %) par GetSystemPowerStatus."""
    s = SPS()
    k32.GetSystemPowerStatus(ctypes.byref(s))
    return int(s.ACLineStatus), int(s.BatteryLifePercent)


def vram_utilisee():
    p = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True)
    m, u = [float(x) for x in p.stdout.strip().split(",")]
    return m, u


def lancer(cmd):
    vram0, util0 = vram_utilisee()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    h = k32.OpenProcess(0x1000 | 0x0010, False, p.pid)  # QUERY_LIMITED_INFORMATION | VM_READ
    pointe = {"ws": 0, "prive": 0, "vram": vram0, "fautes": 0}
    fini = threading.Event()

    def veille():
        while not fini.is_set():
            c = PMC()
            c.cb = ctypes.sizeof(PMC)
            if psapi.GetProcessMemoryInfo(h, ctypes.byref(c), c.cb):
                pointe["ws"] = max(pointe["ws"], c.PeakWorkingSetSize)
                pointe["prive"] = max(pointe["prive"], c.PeakPagefileUsage)
                pointe["fautes"] = c.PageFaultCount
            try:
                pointe["vram"] = max(pointe["vram"], vram_utilisee()[0])
            except Exception:
                pass
            time.sleep(0.25)

    t = threading.Thread(target=veille, daemon=True)
    t.start()
    out, err = p.communicate()
    fini.set()
    t.join()
    k32.CloseHandle(h)
    return out, err, p.returncode, vram0, util0, pointe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--modele", required=True)
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--n", default="64")
    ap.add_argument("--r", default="3")
    ap.add_argument("--configs", default="99:mmap,99:none,24:mmap,16:mmap,16:none,8:mmap")
    a = ap.parse_args()
    configs = [(c.split(":") + ["0"])[:3] for c in a.configs.split(",")]
    ordre = configs + configs[::-1]
    j = open(a.sortie, "a", encoding="utf-8")
    for rang, (ngl, lm, ncmoe) in enumerate(ordre):
        cmd = [f"{a.bin}/llama-bench.exe", "-m", a.modele, "-p", "0", "-n", a.n, "-r", a.r, "-ngl", ngl,
               "-lm", lm, "-ncmoe", ncmoe, "-o", "jsonl"]
        sect0 = secteur()
        t0 = time.time()
        out, err, rc, vram0, util0, pointe = lancer(cmd)
        res = [json.loads(l) for l in out.splitlines() if l.startswith("{")]
        d = {"ngl": int(ngl), "mode_chargement": lm, "ncmoe": int(ncmoe), "secteur_avant": sect0[0],
             "secteur_apres": secteur()[0], "batterie_pct": sect0[1], "passage": "A" if rang < len(configs) else "B", "code": rc,
             "duree_s": round(time.time() - t0, 1), "vram_repos_mio": vram0, "util_carte_repos": util0,
             "vram_pointe_carte_mio": pointe["vram"], "vram_ajoutee_mio": pointe["vram"] - vram0,
             "ws_pointe_mio": round(pointe["ws"] / 2**20), "prive_pointe_mio": round(pointe["prive"] / 2**20),
             "fautes_de_page": pointe["fautes"], "cmd": cmd}
        if res:
            r = res[-1]
            d.update({"jetons_s": r.get("avg_ts"), "echantillons_ts": r.get("samples_ts"), "ecart_type": r.get("stddev_ts"), "n_gen": r.get("n_gen"),
                      "taille_modele": r.get("model_size"), "params": r.get("model_n_params"), "backends": r.get("backends"),
                      "gpu_info": r.get("gpu_info"), "build": r.get("build_commit"), "build_number": r.get("build_number")})
        else:
            d["erreur"] = err[-1500:]
        j.write(json.dumps(d, ensure_ascii=False) + "\n")
        j.flush()
        print(f"{rang + 1}/{len(ordre)} ngl={ngl} lm={lm} -> {d.get('jetons_s')} j/s, ws {d['ws_pointe_mio']} Mio, "
              f"prive {d['prive_pointe_mio']} Mio, vram +{d['vram_ajoutee_mio']:.0f} Mio (repos {vram0:.0f})", flush=True)
    j.close()


if __name__ == "__main__":
    main()
