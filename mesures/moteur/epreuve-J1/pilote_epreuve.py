"""Épreuve indépendante de J1 (§ 8.3 à 8.5) : vitesse, RAM, VRAM et base llama.cpp, par mes commandes.

Instrument propre au juge (aucun outil d'un lot importé) :
  - pointe EXACTE de l'ensemble de travail et de la mémoire engagée privée du processus : lues par
    GetProcessMemoryInfo sur la poignée du processus APRÈS sa sortie (le système tient la pointe ;
    pas d'échantillonnage) ;
  - mémoire physique disponible de TOUTE la machine (GlobalMemoryStatusEx), toutes les 100 ms :
    repos médian avant la passe, minimum pendant ; la différence est ce que la machine perd,
    pilote de la carte et cache de fichiers compris (ce que l'ensemble de travail ne voit pas) ;
  - VRAM (nvidia-smi, toutes les 250 ms) : repos et pointe ;
  - alimentation (Win32_Battery BatteryStatus) avant et après chaque passe ; aucun llama-* ni
    troncons étranger avant la passe ;
  - horloge murale de la passe ; jetons/s lus dans le journal du programme (troncons) ou dans
    « --perf » (llama.cpp), recoupés par l'horloge murale.

Ordre : palindrome déclaré en tête (05 le fixe avant toute passe), processus neufs.
Commande : python -I -X utf8 pilote_epreuve.py --seance <nom> [--seulement i,j,…]
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import datetime
import hashlib
import json
import os
import pathlib
import re
import statistics
import subprocess
import sys
import threading
import time

ICI = pathlib.Path(__file__).resolve().parent
JOURNAUX = ICI / "journaux" / "seances"
TRONCONS = "~/dev/cibles/troncons-epreuve/release/troncons.exe"
LLAMA = "~/dev/modeles/llama.cpp-b11515/llama-completion.exe"
TRC = "~/dev/modeles/trc"
GGUF = "~/dev/modeles/gguf"
INVITE = "~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt"
INVITE_SHA256 = "eadbe87e3d3ce6c81035a2a4d83f898d887ce7d76bd4336555d615ee0522ceff"
BASE_KLD = "~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld"
SORTIES = pathlib.Path("~/dev/essais/troncons/epreuve-J1")


def troncons(modele, *extra):
    return [TRONCONS, "mesurer", "--modele", f"{TRC}/gpt-oss-{modele}.trc",
            "--vocab", f"{TRC}/gpt-oss-{modele}.vocab.gguf", "--invite", INVITE, "-n", "256",
            "--flux", *extra]


def llama(*extra):
    # la configuration « fit » de mesures/gpt-oss.md § 3.2, telle quelle (journal 120b-fit-1.json)
    return [LLAMA, "-m", f"{GGUF}/gpt-oss-120b-MXFP4.gguf", "-f", INVITE, "-n", "256", "--temp", "0",
            "--seed", "1", "-no-cnv", "--no-display-prompt", "--perf", "--ignore-eos", "-c", "2048",
            "-lv", "4", *extra]


PASSES = {
    "T120": ("troncons", troncons("120b")),
    "L120": ("llama", llama("-t", "6")),
    "L120t10": ("llama", llama("-t", "10")),
    "T20": ("troncons", troncons("20b")),
    "T120tiede1": ("troncons", troncons("120b", "--ram-tiede", "1")),
    # l'étage disque seul (outil du lot O, à la longueur des tronçons), pour le plancher de C5
    "D120": ("disque", [TRONCONS, "disque", "--modele", f"{TRC}/gpt-oss-120b.trc", "--n", "1500",
                        "--graine", "20261016", "--profondeur", "4"]),
    # C3 et C11 sur le 120b : évaluation des 10 fenêtres par flux, codé puis brut (§ 7.1)
    "E120c": ("evaluer", [TRONCONS, "evaluer", "--modele", f"{TRC}/gpt-oss-120b.trc", "--base", BASE_KLD,
                          "--fenetres", "10", "--positions", "512", "--flux"]),
    "E120b": ("evaluer", [TRONCONS, "evaluer", "--modele", f"{TRC}/gpt-oss-120b-brut.trc", "--base",
                          BASE_KLD, "--fenetres", "10", "--positions", "512", "--flux", "--brut"]),
    # C2 par le moteur : mode témoin, préremplissage par flux (presque chaque expert décodé une fois)
    "W120": ("commande", [TRONCONS, "generer", "--modele", f"{TRC}/gpt-oss-120b.trc", "--vocab",
                          f"{TRC}/gpt-oss-120b.vocab.gguf", "--invite", INVITE, "-n", "4", "--flux",
                          "--temoin", "--repos", "0"]),
    # cassures du moteur sur les copies corrompues des lots E et O (20b)
    "XE2": ("commande", [TRONCONS, "generer", "--modele", f"{TRC}/casse/gpt-oss-20b-casse-E2.trc", "--vocab",
                         f"{TRC}/gpt-oss-20b.vocab.gguf", "--invite", INVITE, "-n", "32", "--flux", "--repos", "0"]),
    "XO3": ("commande", [TRONCONS, "generer", "--modele", f"{TRC}/casse/gpt-oss-20b-casse-O3.trc", "--vocab",
                         f"{TRC}/gpt-oss-20b.vocab.gguf", "--invite", INVITE, "-n", "32", "--flux", "--repos", "0"]),
    "XO3t": ("commande", [TRONCONS, "generer", "--modele", f"{TRC}/casse/gpt-oss-20b-casse-O3.trc", "--vocab",
                          f"{TRC}/gpt-oss-20b.vocab.gguf", "--invite", INVITE, "-n", "32", "--flux", "--temoin",
                          "--repos", "0"]),
    "Y20": ("commande", [TRONCONS, "generer", "--modele", f"{TRC}/gpt-oss-20b.trc", "--vocab",
                         f"{TRC}/gpt-oss-20b.vocab.gguf", "--invite", INVITE, "-n", "32", "--flux", "--repos", "0"]),
    # base llama.cpp « carte » (configuration carte_cmoe du lot R) du 120b, fenêtre 0 seulement
    "K120": ("commande", [LLAMA.replace("llama-completion", "llama-perplexity"), "-m",
                          f"{GGUF}/gpt-oss-120b-MXFP4.gguf", "-ngl", "99", "--cpu-moe", "-c", "512", "-b",
                          "512", "-t", "6", "--seed", "1", "--chunks", "1", "-f",
                          "~/dev/essais/troncons/modeles/donnees/wiki.test.raw"]),
}
ORDRES = {"c3": ["E120c", "E120b"], "c3brut": ["E120b"], "complements": ["W120", "Y20", "XE2", "XO3", "XO3t", "K120"]}
# déclaré avant toute passe : palindrome T L L' L' L T, puis 20b, puis l'épreuve du cache tiède
ORDRE = ["D120", "T120", "L120", "L120t10", "L120t10", "L120", "T120", "D120", "T20", "T20",
         "T120tiede1", "T120"]


class PMC(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


class MEMSTAT(ctypes.Structure):
    _fields_ = [("dwLength", wt.DWORD), ("dwMemoryLoad", wt.DWORD), ("ullTotalPhys", ctypes.c_uint64),
                ("ullAvailPhys", ctypes.c_uint64), ("ullTotalPageFile", ctypes.c_uint64),
                ("ullAvailPageFile", ctypes.c_uint64), ("ullTotalVirtual", ctypes.c_uint64),
                ("ullAvailVirtual", ctypes.c_uint64), ("ullAvailExtendedVirtual", ctypes.c_uint64)]


def dispo_phys():
    m = MEMSTAT()
    m.dwLength = ctypes.sizeof(MEMSTAT)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullAvailPhys, m.ullTotalPageFile - m.ullAvailPageFile


def memoire_processus(h):
    c = PMC()
    c.cb = ctypes.sizeof(PMC)
    if not ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(c), c.cb):
        return None
    return {"pointe_ensemble_travail": c.PeakWorkingSetSize, "pointe_engagee_privee": c.PeakPagefileUsage,
            "fautes_de_page": c.PageFaultCount, "ensemble_travail": c.WorkingSetSize}


class IOC(ctypes.Structure):
    _fields_ = [(n, ctypes.c_uint64) for n in ("ReadOperationCount", "WriteOperationCount",
                                               "OtherOperationCount", "ReadTransferCount",
                                               "WriteTransferCount", "OtherTransferCount")]


def es_processus(h):
    """Compteurs d'E/S du processus (toutes ses lectures ReadFile, tamponnées ou non)."""
    c = IOC()
    if not ctypes.windll.kernel32.GetProcessIoCounters(h, ctypes.byref(c)):
        return None
    return {"lectures": c.ReadOperationCount, "octets_lus": c.ReadTransferCount,
            "octets_ecrits": c.WriteTransferCount, "autres_octets": c.OtherTransferCount}


def vram_mio():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=5).stdout
        return int(o.strip().splitlines()[0])
    except Exception:
        return None


def alimentation():
    o = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "(Get-CimInstance Win32_Battery).BatteryStatus"],
                       capture_output=True, text=True, timeout=30).stdout.strip()
    return o


def etrangers():
    o = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True).stdout.decode("cp850", "replace")
    noms = [l.split('","')[0].strip('"') for l in o.splitlines() if l]
    return sorted({n for n in noms if n.lower().startswith(("llama-", "troncons", "temoin", "banc-"))})


class Echantillons(threading.Thread):
    def __init__(self, f, periode):
        super().__init__(daemon=True)
        self.f, self.periode, self.v, self.stop = f, periode, [], threading.Event()

    def run(self):
        while not self.stop.is_set():
            t = time.time()
            x = self.f()
            if x is not None:
                self.v.append((t, x))
            self.stop.wait(self.periode)


def une_passe(nom, rang, seance):
    sorte, cmd = PASSES[nom]
    base = SORTIES / seance
    base.mkdir(parents=True, exist_ok=True)
    etiq = f"{rang:02d}-{nom}"
    cmd = list(cmd)
    if sorte == "disque":
        cmd += ["--journal", str(base / f"{etiq}.json")]
    if sorte == "commande" and cmd[0] == TRONCONS:
        cmd += ["--journal", str(base / f"{etiq}.json"), "--sortie", str(base / f"{etiq}.txt")]
    if sorte == "commande" and "llama-perplexity" in cmd[0]:
        cmd += ["--kl-divergence-base", str(base / f"{etiq}.kld")]
    if sorte == "evaluer":
        cmd += ["--sortie", str(base / f"{etiq}.kld"), "--empreintes", str(base / f"{etiq}-empreintes.csv"),
                "--journal", str(base / f"{etiq}.json")]
    if sorte == "troncons":
        cmd += ["--journal", str(base / f"{etiq}.json"), "--sortie", str(base / f"{etiq}.txt")]
    r = {"passe": etiq, "nom": nom, "sorte": sorte, "commande": cmd,
         "debut": datetime.datetime.now().isoformat(timespec="seconds"),
         "alimentation_avant": alimentation(), "etrangers_avant": etrangers()}
    # repos : 10 s de mémoire disponible et de VRAM
    rep = [dispo_phys()[0] for _ in range(20) if not time.sleep(0.5)]
    r["dispo_repos_mo"] = statistics.median(rep) / 1e6
    r["vram_repos_mio"] = vram_mio()
    em = Echantillons(lambda: dispo_phys()[0], 0.1)
    ev = Echantillons(vram_mio, 0.25)
    em.start(); ev.start()
    t0 = time.time()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    h = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, p.pid)
    out, err = p.communicate()
    r["mur_s"] = time.time() - t0
    em.stop.set(); ev.stop.set(); em.join(); ev.join()
    r["code_retour"] = p.returncode
    r["memoire_os"] = memoire_processus(h)      # pointes tenues par le système, après la sortie
    r["es_os"] = es_processus(h)
    ctypes.windll.kernel32.CloseHandle(h)
    r["dispo_min_mo"] = min(v for _, v in em.v) / 1e6 if em.v else None
    r["perte_machine_mo"] = r["dispo_repos_mo"] - r["dispo_min_mo"] if em.v else None
    r["vram_pointe_mio"] = max(v for _, v in ev.v) if ev.v else None
    r["n_echantillons_vram"] = len(ev.v)
    r["alimentation_apres"] = alimentation()
    (base / f"{etiq}.stdout.txt").write_bytes(out)
    (base / f"{etiq}.stderr.log").write_bytes(err)
    if p.returncode != 0 and sorte != "commande":
        r["echec"] = err.decode("utf-8", "replace")[-2000:]
        r["fin"] = datetime.datetime.now().isoformat(timespec="seconds")
        return r
    if sorte == "troncons":
        j = json.loads((base / f"{etiq}.json").read_text(encoding="utf-8"))
        r["programme"] = {k: j.get(k) for k in ("prefill_s", "prefill_jetons_s", "generation_s",
                                                 "generation_jetons_s", "pas_generation",
                                                 "texte_sha256", "jetons_produits", "memoire",
                                                 "vram", "disque", "alimentation")}
        r["programme"]["ouverture_s"] = j.get("moteur", {}).get("ouverture_s")
        r["programme"]["h_generation"] = j.get("compteurs_generation", {}).get("h_vram")
        r["programme"]["emplacements"] = j.get("moteur", {}).get("emplacements")
        r["gen_jetons_s"] = j["generation_jetons_s"]
        r["texte_sha256"] = j["texte_sha256"]
    elif sorte == "commande":
        jj = base / f"{etiq}.json"
        r["programme"] = {"stderr_fin": err.decode("utf-8", "replace")[-1500:]}
        if jj.exists():
            j = json.loads(jj.read_text(encoding="utf-8"))
            r["programme"].update({k: j.get(k) for k in ("texte_sha256", "jetons_produits", "generation_jetons_s")})
            r["programme"]["experts_verifies"] = (j.get("compteurs_total") or {}).get("experts_verifies")
            r["programme"]["experts_decodes"] = (j.get("compteurs_total") or {}).get("experts_decodes")
            r["texte_sha256"] = j.get("texte_sha256")
    elif sorte == "evaluer":
        j = json.loads((base / f"{etiq}.json").read_text(encoding="utf-8"))
        r["programme"] = {k: j.get(k) for k in ("pas", "pas_s", "secondes", "ppl_positions_notees",
                                                 "empreinte_csv_sha256", "alimentation")}
        r["programme"]["compteurs"] = j.get("compteurs")
    elif sorte == "disque":
        r["programme"] = json.loads((base / f"{etiq}.json").read_text(encoding="utf-8"))
    else:
        e = err.decode("utf-8", "replace")
        m = re.search(r"prompt eval time =\s*([\d.]+) ms /\s*(\d+) tokens", e)
        g = re.search(r"\s eval time =\s*([\d.]+) ms /\s*(\d+) runs", e)
        r["programme"] = {"prefill_ms": float(m.group(1)) if m else None, "prefill_n": int(m.group(2)) if m else None,
                          "gen_ms": float(g.group(1)) if g else None, "gen_n": int(g.group(2)) if g else None}
        if g:
            r["gen_jetons_s"] = int(g.group(2)) / (float(g.group(1)) / 1000)
        if m:
            r["prefill_jetons_s"] = int(m.group(2)) / (float(m.group(1)) / 1000)
        r["texte_sha256"] = hashlib.sha256(out).hexdigest()
    r["fin"] = datetime.datetime.now().isoformat(timespec="seconds")
    return r


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seance", required=True)
    ap.add_argument("--seulement")
    ap.add_argument("--ordre", default="vitesse")
    a = ap.parse_args()
    if hashlib.sha256(pathlib.Path(INVITE).read_bytes()).hexdigest() != INVITE_SHA256:
        sys.exit("invite : empreinte inattendue")
    JOURNAUX.mkdir(parents=True, exist_ok=True)
    global ORDRE
    if a.ordre != "vitesse":
        ORDRE = ORDRES[a.ordre]
    rangs = range(len(ORDRE)) if not a.seulement else [int(x) for x in a.seulement.split(",")]
    chemin = JOURNAUX / f"{a.seance}.json"
    tout = json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else \
        {"seance": a.seance, "ordre": ORDRE, "passes": PASSES, "passes_faites": []}
    for i in rangs:
        nom = ORDRE[i]
        print(f"{datetime.datetime.now():%H:%M:%S} passe {i} {nom}", flush=True)
        r = une_passe(nom, i, a.seance)
        tout["passes_faites"].append(r)
        chemin.write_text(json.dumps(tout, ensure_ascii=False, indent=1), encoding="utf-8")
        if "echec" in r:
            print(f"   ÉCHEC code {r['code_retour']} mur {r['mur_s']:.0f} s : {r['echec'][-300:]}", flush=True)
            continue
        print(f"   code {r['code_retour']} mur {r['mur_s']:.0f} s gen {r.get('gen_jetons_s')} es {r.get('es_os')} "
              f"pointe ET {r['memoire_os'] and r['memoire_os']['pointe_ensemble_travail'] / 1e6:.1f} Mo "
              f"perte machine {r['perte_machine_mo']:.0f} Mo VRAM {r['vram_pointe_mio']} "
              f"alim {r['alimentation_avant']}/{r['alimentation_apres']} etrangers {r['etrangers_avant']}",
              flush=True)


if __name__ == "__main__":
    principal()
