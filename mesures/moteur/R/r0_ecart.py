"""R0 : l'écart entre moteurs sur gpt-oss-20b (ARCHITECTURE.md § 6.5, lot R).

Ce que l'étape publie : G_cfg (llama.cpp sur la carte, experts en RAM `--cpu-moe`, contre la
répartition choisie par `--fit on`) et G_moteurs (processeur seul, `CUDA_VISIBLE_DEVICES=-1`, contre
la carte). C'est la grandeur dont dépendent R1 (« KL(référence ‖ llama.cpp carte) ≤ max(G_moteurs,
7e-5) ») et le seuil Q1 de J2 (0,0055 mesuré sur Qwen3.5-4B, à remplacer par G_moteurs de gpt-oss).

Protocole : llama-perplexity b11515, wikitext-2 test (wiki.test.raw, empreinte dans
juge/donnees-sha256.txt de l'étude 06), fenêtres de 512 jetons, lots de 512, 10 fenêtres (les 255
dernières positions de chacune sont notées : 2 550 positions), --seed 1, 6 fils.

Chaque configuration X est passée deux fois en mode « base » (X.kld et X-bis.kld) : l'égalité des
octets dit si le moteur est déterministe. Les KL se calculent par deux chemins indépendants :
  1. llama-perplexity --kl-divergence, logits bruts de la configuration jugée contre la base X.kld ;
  2. `juge kl` (trc-juge, écrit ici) entre deux fichiers .kld (le jugé passe aussi par le codage
     16 bits : c'est l'instrument de C4).

SEUILS DÉCLARÉS AVANT LE LANCEMENT (2026-10-15) :
  T1 plancher de l'instrument (même configuration, deux passes) : KL moyenne ≤ 7e-5 et premier
     choix 100 % (plancher mesuré par l'étude 06 § 7.3 : 99,9e centile 5,5e-5, maximum 6,8e-5) ;
  T2 cassure (« autre modèle ») : la même base jugée par gpt-oss-20b à k = 2 experts actifs au lieu
     de 4 (--override-kv gpt-oss.expert_used_count=int:2) doit sortir nettement : KL moyenne
     ≥ 100 × 7e-5 = 7e-3 et premier choix < 99 % ; sinon l'instrument ne voit rien ;
  T3 accord des deux chemins : sur chaque paire mesurée par les deux, KL moyennes à 10 % relatifs
     près ou à 2e-5 absolus près (le chemin 2 ajoute le codage du jugé, d'erreur ≤ pas/2 ≈ 1,2e-4 par
     logit, d'où une KL de l'ordre de 1e-5 en plus au plus) ;
  G_cfg et G_moteurs : publiés, pas jugés (ce sont des mesures, pas des critères).

Usage : python -I -X utf8 r0_ecart.py <étape> [...]  (étapes : processeur, processeur-bis, carte,
cassure-120b, resume). Les étapes « carte » prennent le verrou ~/dev/verrou-carte.txt.
"""

import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

DEPOT = pathlib.Path(__file__).resolve().parents[3]
ICI = pathlib.Path(__file__).resolve().parent
JOURNAUX = ICI / "r0"
LOURDS = pathlib.Path("~/dev/essais/troncons/lot-R/r0")
LLAMA = pathlib.Path("~/dev/modeles/llama.cpp-b11515")
DONNEES = pathlib.Path("~/dev/essais/troncons/modeles/donnees")
M20 = pathlib.Path("~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf")
M120 = pathlib.Path("~/dev/modeles/gguf/gpt-oss-120b-MXFP4.gguf")
JUGE = pathlib.Path("~/dev/cibles/troncons-R/release/juge.exe")
VERROU = pathlib.Path("~/dev/verrou-carte.txt")
FENETRES = 10
COMMUN = ["-c", "512", "-b", "512", "-t", "6", "--seed", "1", "--chunks", str(FENETRES)]

CONFIGS = {
    # nom : (modèle, arguments, environnement en plus)
    "carte_cmoe": (M20, ["-ngl", "99", "--cpu-moe"], {}),
    # ~~« carte_fit » : la répartition choisie par --fit~~ Corrigé le 2026-10-15 (20 h 05) : avec
    # -ngl 99, llama.cpp b11515 abandonne l'ajustement (« failed to fit params to free device
    # memory: n_gpu_layers already set by user to 99, abort ») : cette configuration met toutes les
    # couches, experts compris, sur la carte (12 Go de poids pour 8 Go de VRAM : débordement du
    # pilote dans la mémoire partagée probable, non vérifié). Gardée, sous ce nom, comme troisième
    # configuration ; G_cfg se mesure avec « carte_fitauto ».
    "carte_fit": (M20, ["-ngl", "99", "--fit", "on"], {}),
    # La vraie répartition de --fit : aucun -ngl (comme la configuration « fit » de l'agent gpt-oss).
    "carte_fitauto": (M20, ["--fit", "on"], {}),
    "processeur": (M20, ["-ngl", "0"], {"CUDA_VISIBLE_DEVICES": "-1"}),
    "cassure_k2": (M20, ["-ngl", "99", "--cpu-moe", "--override-kv", "gpt-oss.expert_used_count=int:2"], {}),
    "cassure_120b": (M120, ["-ngl", "99", "--cpu-moe"], {}),
}


def horodate():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def ps(commande):
    r = subprocess.run(["powershell", "-NoProfile", "-Command", commande], capture_output=True, text=True)
    return r.stdout.strip()


def environnement():
    nv = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
    proc = ps("Get-Process | Where-Object { $_.ProcessName -like 'llama*' -or $_.ProcessName -like 'traceur*' } | ForEach-Object { $_.ProcessName + ':' + $_.Id }")
    return {
        "date": horodate(),
        "batterie_statut": ps("(Get-CimInstance Win32_Battery).BatteryStatus"),
        "carte": nv,
        "processus_llama_ou_traceur": proc,
    }


def sha256(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def prendre_verrou():
    while True:
        if VERROU.exists():
            age = time.time() - VERROU.stat().st_mtime
            if age < 2 * 3600:
                print(f"verrou présent ({VERROU.read_text(encoding='utf-8', errors='replace').strip()}), âge {age:.0f} s : attente", flush=True)
                time.sleep(120)
                continue
        env = environnement()
        proc = env["processus_llama_ou_traceur"]
        if proc:
            print(f"processus sur la carte : {proc} : attente", flush=True)
            time.sleep(120)
            continue
        # Reprise du 2026-10-15 : `--fit on` choisit sa répartition selon la VRAM libre, donc G_cfg
        # dépend de ce que les autres lots tiennent sur la carte. Seuil : 1 500 Mio occupés au plus,
        # soit le repos relevé à 10 h 15 (909 Mio, mesures/REPRISE-gpt-oss.md) plus une marge de
        # 591 Mio [hyp., non mesurée : l'affichage et les applications varient] ; l'occupation exacte
        # avant chaque passe est écrite dans son journal (« avant »), pour qu'on puisse juger après.
        try:
            occupe = int(env["carte"].split(",")[0].split()[0])
        except (ValueError, IndexError):
            occupe = 10 ** 9
        if occupe > 1500:
            print(f"carte occupée ({env['carte']}) : attente", flush=True)
            time.sleep(120)
            continue
        VERROU.write_text(f"lot R (r0_ecart.py), pris le {horodate()}\n", encoding="utf-8")
        return


def rendre_verrou():
    if VERROU.exists() and VERROU.read_text(encoding="utf-8", errors="replace").startswith("lot R"):
        VERROU.unlink()


def perplexite(nom, mode, base=None, sortie=None):
    """mode « base » : écrit `sortie` ; mode « kl » : juge contre `base`. Rend le chemin du journal."""
    modele, args, env_plus = CONFIGS[nom]
    etiquette = f"{nom}-{mode}" + (f"-contre-{pathlib.Path(base).stem}" if base else "") + (f"-{pathlib.Path(sortie).stem}" if sortie else "")
    log = JOURNAUX / f"{etiquette}.log"
    cmd = [str(LLAMA / "llama-perplexity.exe"), "-m", str(modele), *args, *COMMUN]
    if mode == "base":
        cmd += ["-f", str(DONNEES / "wiki.test.raw"), "--kl-divergence-base", str(sortie)]
    else:
        cmd += ["--kl-divergence-base", str(base), "--kl-divergence"]
    env = dict(os.environ, **env_plus)
    avant = environnement()
    t0 = time.time()
    with open(log, "w", encoding="utf-8") as f:
        f.write(f"# {horodate()} {' '.join(cmd)}  env+={env_plus}\n# avant : {json.dumps(avant, ensure_ascii=False)}\n")
        f.flush()
        # Priorité « sous la normale » : R0 ne mesure aucun temps (seulement des logits) et la machine
        # est partagée avec quatre autres lots. (La passe processeur-bis du 2026-10-15 15 h 08 est
        # partie avant ce changement, en priorité normale, comme la passe 1.)
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=env, creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
        f.write(f"\n# fin {horodate()} code {r.returncode} durée {time.time() - t0:.1f} s\n")
    if r.returncode != 0:
        raise SystemExit(f"{etiquette} : code {r.returncode}, voir {log}")
    print(f"{etiquette} : {time.time() - t0:.1f} s", flush=True)
    return log


STATS = {
    "kl_moyenne": r"Mean\s+KLD:\s+(-?[\d.]+)\s+±\s+([\d.]+)",
    "kl_max": r"Maximum KLD:\s+(-?[\d.]+)",
    "kl_p999": r"99\.9%\s+KLD:\s+(-?[\d.]+)",
    "kl_p99": r"99\.0%\s+KLD:\s+(-?[\d.]+)",
    "kl_mediane": r"Median\s+KLD:\s+(-?[\d.]+)",
    "meme_premier_pct": r"Same top p:\s+([\d.]+)\s+±\s+([\d.]+)",
    "ppl_q": r"Mean PPL\(Q\)\s+:\s+([\d.]+)\s+±\s+([\d.]+)",
    "ppl_base": r"Mean PPL\(base\)\s+:\s+([\d.]+)\s+±\s+([\d.]+)",
    "ln_rapport": r"Mean ln\(PPL\(Q\)/PPL\(base\)\)\s+:\s+(-?[\d.]+)\s+±\s+([\d.]+)",
}


def lire_stats(log):
    t = pathlib.Path(log).read_text(encoding="utf-8", errors="replace")
    out = {}
    for k, motif in STATS.items():
        m = re.search(motif, t)
        if m:
            out[k] = [float(g) for g in m.groups()]
    return out


def juge_kl(base, test, etiquette):
    j = JOURNAUX / f"juge-kl-{etiquette}.json"
    c = JOURNAUX / f"juge-kl-{etiquette}.csv"
    r = subprocess.run([str(JUGE), "kl", "--base", str(base), "--test", str(test), "--json", str(j), "--csv", str(c)], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"juge kl {etiquette} : {r.stderr}")
    return json.loads(j.read_text(encoding="utf-8"))["resume"]


def etape_processeur():
    """Sans la carte : les deux bases du processeur seul (déterminisme du moteur processeur)."""
    for suffixe in ("", "-bis"):
        perplexite("processeur", "base", sortie=LOURDS / f"processeur{suffixe}.kld")


def etape_processeur_bis():
    """Seconde base du processeur seul, quand la première existe déjà (la passe bis du premier agent
    est morte à la fenêtre 7 avec lui : fichier tronqué de 717 918 208 octets, réécrit ici)."""
    perplexite("processeur", "base", sortie=LOURDS / "processeur-bis.kld")


def etape_carte():
    prendre_verrou()
    try:
        for nom in ("carte_cmoe", "carte_fit"):
            for suffixe in ("", "-bis"):
                perplexite(nom, "base", sortie=LOURDS / f"{nom}{suffixe}.kld")
        b = LOURDS / "carte_cmoe.kld"
        perplexite("carte_cmoe", "kl", base=b)          # T1, chemin 1
        perplexite("carte_fit", "kl", base=b)           # G_cfg, chemin 1
        perplexite("processeur", "kl", base=b)          # G_moteurs, chemin 1
        perplexite("cassure_k2", "kl", base=b)          # T2
        perplexite("carte_cmoe", "kl", base=LOURDS / "processeur.kld")  # sens inverse
    finally:
        rendre_verrou()


def etape_carte_fitauto():
    prendre_verrou()
    try:
        for suffixe in ("", "-bis"):
            perplexite("carte_fitauto", "base", sortie=LOURDS / f"carte_fitauto{suffixe}.kld")
        perplexite("carte_fitauto", "kl", base=LOURDS / "carte_cmoe.kld")   # G_cfg, chemin 1
    finally:
        rendre_verrou()


def etape_cassure_120b():
    prendre_verrou()
    try:
        perplexite("cassure_120b", "kl", base=LOURDS / "carte_cmoe.kld")
    finally:
        rendre_verrou()


def etape_resume():
    res = {"date": horodate(), "environnement": environnement(), "empreintes": {}, "chemin1": {}, "chemin2": {}, "seuils": {}}
    for f in sorted(LOURDS.glob("*.kld")):
        res["empreintes"][f.name] = sha256(f)
    for log in sorted(JOURNAUX.glob("*-kl-contre-*.log")):
        res["chemin1"][log.stem] = lire_stats(log)
    paires = [("carte_cmoe", "carte_cmoe-bis"), ("carte_cmoe", "carte_fit"), ("carte_cmoe", "processeur"),
              ("processeur", "processeur-bis"), ("processeur", "carte_cmoe"), ("carte_fit", "carte_fit-bis"),
              ("carte_cmoe", "carte_fitauto"), ("carte_fitauto", "carte_fitauto-bis")]
    for b, t in paires:
        if (LOURDS / f"{b}.kld").exists() and (LOURDS / f"{t}.kld").exists():
            res["chemin2"][f"{t}-contre-{b}"] = juge_kl(LOURDS / f"{b}.kld", LOURDS / f"{t}.kld", f"{t}-contre-{b}")
    c1 = res["chemin1"]
    def kl1(cle):
        return c1.get(cle, {}).get("kl_moyenne", [None])[0]
    def top1(cle):
        return c1.get(cle, {}).get("meme_premier_pct", [None])[0]
    e = res["empreintes"]
    res["deterministe"] = {n: (e.get(f"{n}.kld") is not None and e.get(f"{n}.kld") == e.get(f"{n}-bis.kld")) for n in ("carte_cmoe", "carte_fit", "carte_fitauto", "processeur")}
    t1 = "carte_cmoe-kl-contre-carte_cmoe"
    if kl1(t1) is not None:
        res["seuils"]["T1_plancher"] = {"kl": kl1(t1), "premier_pct": top1(t1), "tient": kl1(t1) <= 7e-5 and top1(t1) >= 100.0}
    t2 = "cassure_k2-kl-contre-carte_cmoe"
    if kl1(t2) is not None:
        res["seuils"]["T2_cassure_k2"] = {"kl": kl1(t2), "premier_pct": top1(t2), "tient": kl1(t2) >= 7e-3 and top1(t2) < 99.0}
    t2b = "cassure_120b-kl-contre-carte_cmoe"
    if kl1(t2b) is not None:
        res["seuils"]["T2bis_cassure_120b"] = {"kl": kl1(t2b), "premier_pct": top1(t2b), "tient": kl1(t2b) >= 7e-3 and top1(t2b) < 99.0}
    accords = {}
    for cle2, r2 in res["chemin2"].items():
        t, b = cle2.split("-contre-")
        cle1 = f"{t.replace('-bis', '')}-kl-contre-{b}"
        if t.endswith("-bis") and t.replace("-bis", "") == b:
            cle1 = f"{b}-kl-contre-{b}"
        if kl1(cle1) is not None:
            a, d = kl1(cle1), r2["kl_moyenne"]
            accords[cle2] = {"chemin1": a, "chemin2": d, "tient": abs(a - d) <= max(0.10 * abs(a), 2e-5)}
    res["seuils"]["T3_deux_chemins"] = accords
    res["G_cfg"] = kl1("carte_fitauto-kl-contre-carte_cmoe")
    res["G_tout_sur_la_carte"] = kl1("carte_fit-kl-contre-carte_cmoe")
    res["G_moteurs"] = kl1("processeur-kl-contre-carte_cmoe")
    texte = json.dumps(res, ensure_ascii=False, indent=2)
    (JOURNAUX / "r0-resume.json").write_text(texte, encoding="utf-8")
    print(texte)


if __name__ == "__main__":
    JOURNAUX.mkdir(parents=True, exist_ok=True)
    LOURDS.mkdir(parents=True, exist_ok=True)
    {"processeur": etape_processeur, "processeur-bis": etape_processeur_bis, "carte": etape_carte, "carte-fitauto": etape_carte_fitauto, "cassure-120b": etape_cassure_120b, "resume": etape_resume}[sys.argv[1]]()
