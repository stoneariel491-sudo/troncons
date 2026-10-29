"""Banc de la base de comparaison : llama.cpp tel quel (mmap), sur un texte réel fixé, en glouton.

Ce que mesure une passe (tout « mesuré ici ») :
  - jetons/s du préremplissage et de la génération (compteurs internes de llama.cpp, « --perf ») ;
  - mémoire du processus : ensemble de travail et mémoire engagée, de pointe et au dernier relevé
    avant la fin (API Windows, toutes les 100 ms). La pointe compte aussi les pages lues une seule fois
    au chargement ; le dernier relevé dit ce qui reste résident pendant la génération ;
  - VRAM de pointe : nvidia-smi échantillonné toutes les 250 ms, et la valeur au repos ;
  - octets lus sur le disque : compteur système « PhysicalDisk(_Total) / Disk Read Bytes/sec » lu par
    l'API PDH sous son nom anglais (indépendant de la langue du système) toutes les 0,5 s et intégré,
    avec un repos avant la passe pour chiffrer la charge des autres programmes (biais dit : le
    compteur est global à la machine) ;
  - empreinte SHA-256 du texte produit : en glouton (--temp 0, graine fixée), deux moteurs qui lisent
    les mêmes poids sans perte doivent produire exactement les mêmes jetons. C'est le témoin de
    justesse le plus dur pour un moteur sans perte : une seule différence de jeton le fait tomber.

Pourquoi un texte réel et pas llama-bench : la génération de llama-bench part de jetons sans sens ;
pour un MoE dont les poids ne tiennent pas en mémoire, le choix des experts (donc les octets lus)
dépend du contenu. Le texte fixé est le début de wikitext-2 (test), public.

Pourquoi PDH et pas typeperf : sur ce Windows en français, typeperf refuse le nom anglais du compteur
(« aucun compteur valide », mesuré ici le 2026-10-15) ; PdhAddEnglishCounterW l'accepte partout.

Usage :
  python -I modeles-base.py --exe <llama-completion.exe> --modele <m.gguf> --invite <texte.txt>
         --n 256 --etiquette <nom> --sortie <dossier> -- [arguments llama.cpp en plus]
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import re
import subprocess
import threading
import time

COMPTEUR_DISQUE = "\\PhysicalDisk(_Total)\\Disk Read Bytes/sec"


class PMC(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


class ValeurPDH(ctypes.Structure):
    _fields_ = [("CStatus", wt.DWORD), ("pad", wt.DWORD), ("doubleValue", ctypes.c_double)]


def memoire(handle):
    c = PMC()
    c.cb = ctypes.sizeof(PMC)
    if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(c), c.cb):
        return c.PeakWorkingSetSize, c.PeakPagefileUsage, c.PageFaultCount, c.WorkingSetSize, c.PagefileUsage
    return None


def vram_mio():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout
        return int(out.strip().splitlines()[0])
    except Exception:
        return None


class Echantillonneur(threading.Thread):
    def __init__(self, fn, pas):
        super().__init__(daemon=True)
        self.fn, self.pas, self.valeurs, self.stop = fn, pas, [], threading.Event()

    def run(self):
        while not self.stop.is_set():
            v = self.fn()
            if v is not None:
                self.valeurs.append((time.time(), v))
            time.sleep(self.pas)


class CompteurDisque(threading.Thread):
    """Débit de lecture de tous les disques, intégré dans le temps (octets lus)."""

    def __init__(self, pas=0.5):
        super().__init__(daemon=True)
        self.pas, self.stop, self.points, self.instants = pas, threading.Event(), [], []
        self.pdh = ctypes.windll.pdh
        self.q, self.c = ctypes.c_void_p(), ctypes.c_void_p()
        if self.pdh.PdhOpenQueryW(None, None, ctypes.byref(self.q)) != 0:
            raise OSError("PdhOpenQueryW")
        if self.pdh.PdhAddEnglishCounterW(self.q, ctypes.c_wchar_p(COMPTEUR_DISQUE), None,
                                          ctypes.byref(self.c)) != 0:
            raise OSError("PdhAddEnglishCounterW")
        self.pdh.PdhCollectQueryData(self.q)

    def run(self):
        PDH_FMT_DOUBLE = 0x00000200
        t_prec = time.time()
        while not self.stop.is_set():
            time.sleep(self.pas)
            self.pdh.PdhCollectQueryData(self.q)
            t = time.time()
            v = ValeurPDH()
            if self.pdh.PdhGetFormattedCounterValue(self.c, PDH_FMT_DOUBLE, None, ctypes.byref(v)) == 0:
                self.points.append((t - t_prec, v.doubleValue))
                self.instants.append(t)
            t_prec = t

    def octets(self):
        return sum(dt * v for dt, v in self.points)

    def duree(self):
        return sum(dt for dt, _ in self.points)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--modele", required=True)
    ap.add_argument("--invite", required=True)
    ap.add_argument("--n", type=int, default=256)
    ap.add_argument("--etiquette", required=True)
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--repos", type=int, default=10)
    ap.add_argument("reste", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)
    base = os.path.join(a.sortie, a.etiquette)
    extra = [x for x in a.reste if x != "--"]

    # Repos : charge disque des autres programmes et VRAM au repos.
    cd_repos = CompteurDisque()
    cd_repos.start()
    v0 = []
    for _ in range(a.repos * 2):
        v = vram_mio()
        if v is not None:
            v0.append(v)
        time.sleep(0.5)
    cd_repos.stop.set()
    cd_repos.join()

    cmd = [a.exe, "-m", a.modele, "-f", a.invite, "-n", str(a.n), "--temp", "0", "--seed", "1",
           "-no-cnv", "--no-display-prompt", "--perf", "--ignore-eos"] + extra
    cd = CompteurDisque()
    cd.start()
    t0 = time.time()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    h = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, p.pid)
    derniere = [None]

    def lire_mem():
        m = memoire(h)
        if m:
            derniere[0] = m
        return m
    em = Echantillonneur(lire_mem, 0.1)
    ev = Echantillonneur(vram_mio, 0.25)
    em.start()
    ev.start()
    sortie, err = p.communicate()
    t1 = time.time()
    for e in (em, ev, cd):
        e.stop.set()
    cd.join()
    err_t = err.decode("utf-8", "replace")
    open(base + ".stderr.log", "w", encoding="utf-8").write(err_t)
    open(base + ".sortie.txt", "wb").write(sortie)

    def perf(motif):
        m = re.search(motif + r"\s*=\s*([\d.]+) ms /\s*(\d+) (?:tokens|runs).*?([\d.]+) tokens per second", err_t)
        return {"ms": float(m.group(1)), "n": int(m.group(2)), "jetons_s": float(m.group(3))} if m else None

    repos_moy = cd_repos.octets() / cd_repos.duree() if cd_repos.duree() else 0.0
    res = {
        "etiquette": a.etiquette, "commande": cmd, "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "code_retour": p.returncode, "duree_s": t1 - t0,
        "taille_modele_octets": os.path.getsize(a.modele),
        "prefill": perf("prompt eval time"), "generation": perf(r"(?<!prompt )eval time"),
        "memoire_pointe": {"ensemble_travail_octets": derniere[0][0] if derniere[0] else None,
                           "engagee_octets": derniere[0][1] if derniere[0] else None,
                           "fautes_de_page": derniere[0][2] if derniere[0] else None,
                           # Dernier relevé avant la fin : la mémoire résidente pendant la génération.
                           # La pointe, elle, compte aussi les pages touchées une seule fois au
                           # chargement (copie vers la carte), mesuré ici le 2026-10-15.
                           "ensemble_travail_final_octets": derniere[0][3] if derniere[0] else None,
                           "engagee_finale_octets": derniere[0][4] if derniere[0] else None},
        "vram_mio": {"repos": min(v0) if v0 else None,
                     "pointe": max(v for _, v in ev.valeurs) if ev.valeurs else None},
        "disque": {"octets_lus_pendant": cd.octets(), "secondes": cd.duree(),
                   "debit_repos_moyen_o_s": repos_moy,
                   "octets_attribuables_estimes": cd.octets() - repos_moy * cd.duree()},
        "sortie_sha256": hashlib.sha256(sortie).hexdigest(),
        # Ajout du 2026-10-15 (mesures gpt-oss) : la série du compteur disque, pour séparer les phases
        # (chargement, préremplissage, génération) ; [secondes depuis le lancement, octets/s].
        "disque_serie": [[round(ti - t0, 3), round(v)] for ti, (_, v) in zip(cd.instants, cd.points)],
        "fin_s": t1 - t0,
    }
    json.dump(res, open(base + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ("etiquette", "code_retour", "prefill", "generation", "memoire_pointe",
                                          "vram_mio", "disque", "sortie_sha256")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
