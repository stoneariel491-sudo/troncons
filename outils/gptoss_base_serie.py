"""Séries alternées de la base llama.cpp b11515 sur gpt-oss (protocole de fondations/06-modeles.md § 7).

Chaque passe est une exécution de outils/modeles-base.py (llama-completion, invite fixée de l'étude 06,
256 jetons gloutons, mmap), précédée d'un relevé de la source d'alimentation (WMI Win32_Battery,
BatteryStatus : 2 = secteur) : une passe sur batterie est refusée et notée, parce que la machine
y est une autre machine (étude 01, § 5.4 : plafond de puissance de la carte 52,6 W au lieu de 80,
mémoire de carte à 6 001 MHz, PCIe en Gen 3).

L'ordre est un palindrome répété (A B C C B A) × R : la généralisation de ABBA à plusieurs
configurations ; chaque configuration occupe des places symétriques, ce qui annule une dérive
linéaire dans le temps (échauffement, cache de pages qui se remplit), et l'écart d'une
configuration à elle-même donne le bruit de référence.

Règle de décision, déclarée avant la mesure (reprise telle quelle de 06-modeles.md § 7.5, qui la
tient de l'étude 01) : bruit d'une configuration = |X1 - X2| / moyenne sur ses deux passes d'un
même palindrome (le plus grand sur les R palindromes) ; une différence entre deux configurations
n'est réelle que si elle dépasse 2 × le plus grand des deux bruits ET 3 %.

Sorties : <sortie>/<modele>-<config>-<n>.json et .stderr.log (par passe), <sortie>/passes.csv (une
ligne par passe, ajoutée au fil de l'eau), <sortie>/journal.log.

Usage :
  python -I gptoss_base_serie.py --modele <m.gguf> --nom 20b --sortie <dossier> --repetitions 2
         --config cmoe="-ngl 99 --cpu-moe --fit off" --config fit="" ...
"""
import argparse
import csv
import json
import os
import re
import shlex
import subprocess
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
EXE = "~/dev/modeles/llama.cpp-b11515/llama-completion.exe"
INVITE = "~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt"
INVITE_SHA256 = "eadbe87e3d3ce6c81035a2a4d83f898d887ce7d76bd4336555d615ee0522ceff"

CHAMPS = ["date", "modele", "config", "palindrome", "rang", "batterie", "charge_pct", "code_retour",
          "chargement_ms", "prefill_jetons", "prefill_js", "generation_jetons", "generation_js",
          "ensemble_travail_pointe_go", "ensemble_travail_final_go", "engagee_pointe_go",
          "vram_repos_mio", "vram_pointe_mio", "disque_lu_go", "disque_attribuable_go",
          "disque_repos_mo_s", "disque_generation_go", "disque_par_jeton_genere_go", "duree_s", "cache_succes_pct", "cache_succes", "cache_defauts",
          "cache_envoye_mio", "sortie_sha256", "concurrents", "ram_libre_debut_mo", "arguments"]


def batterie():
    """(BatteryStatus, charge %) par WMI ; (None, None) si la lecture échoue."""
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "$b = Get-CimInstance Win32_Battery; \"$($b.BatteryStatus) $($b.EstimatedChargeRemaining)\""],
                             capture_output=True, text=True, timeout=60).stdout.split()
        return int(out[0]), int(out[1])
    except Exception:
        return None, None


def concurrents():
    """Programmes des autres agents qui tournent pendant la passe : tout exécutable lancé depuis
    ~/dev/ (moteurs, bancs, llama.cpp), et la mémoire physique libre. Ajouté le
    2026-10-15 à 13:20, quand trois autres agents se sont mis à lire gpt-oss sur la carte et en RAM
    (banc_k_justesse sur 120b, trc-codeur sur 20b, llama-perplexity sur 20b) : une passe de la base
    mesurée sous cette charge ne vaut pas une passe au calme, et le CSV doit le dire."""
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "$l = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like 'C:?Users?*?dev?*' } | "
                              "ForEach-Object { $_.Name }; ($l | Sort-Object -Unique) -join '+'; "
                              "[int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1024)"],
                             capture_output=True, text=True, timeout=60).stdout.strip().splitlines()
        return (out[0] if len(out) > 1 else ""), int(out[-1])
    except Exception:
        return None, None


def stats_cache(err):
    """Bilan du cache d'experts de llama.cpp (« llama_moe_cache: ubatch <= 8: hits = … »)."""
    m = re.search(r"llama_moe_cache: ubatch <= 8: hits = (\d+), misses = (\d+), hit rate = ([\d.]+)%, uploaded = ([\d.]+) MiB", err)
    if not m:
        return None, None, None, None
    return float(m.group(3)), int(m.group(1)), int(m.group(2)), float(m.group(4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modele", required=True)
    ap.add_argument("--nom", required=True)
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--repetitions", type=int, default=2)
    ap.add_argument("--n", type=int, default=256)
    ap.add_argument("--commun", default="-t 6 -c 2048", help="arguments communs à toutes les passes")
    ap.add_argument("--config", action="append", required=True, help="etiquette=\"arguments llama.cpp\"")
    ap.add_argument("--echauffement", action="store_true", help="une passe jetée avant la série (1re config)")
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)
    configs = []
    for c in a.config:
        nom, _, args = c.partition("=")
        configs.append((nom, shlex.split(args)))
    ordre = [c for c in configs] + [c for c in reversed(configs)]
    plan = []
    if a.echauffement:
        plan.append((0, configs[0], "echauffement"))
    for r in range(1, a.repetitions + 1):
        for c in ordre:
            plan.append((r, c, None))
    journal = open(os.path.join(a.sortie, "journal.log"), "a", encoding="utf-8")
    chemin_csv = os.path.join(a.sortie, "passes.csv")
    nouveau = not os.path.exists(chemin_csv)
    fcsv = open(chemin_csv, "a", newline="", encoding="utf-8")
    w = csv.DictWriter(fcsv, fieldnames=CHAMPS)
    if nouveau:
        w.writeheader()

    def ecrire(texte):
        ligne = time.strftime("%Y-%m-%d %H:%M:%S ") + texte
        print(ligne, flush=True)
        journal.write(ligne + "\n")
        journal.flush()

    ecrire(f"série {a.nom} : {len(plan)} passes, ordre {[p[1][0] for p in plan]}, commun « {a.commun} », invite {INVITE_SHA256[:8]}")
    compteur = {}
    for rang, (palindrome, (nom, args), marque) in enumerate(plan, 1):
        etat, charge = batterie()
        while etat != 2:
            ecrire(f"alimentation : BatteryStatus = {etat} (charge {charge} %) : passe retenue, attente du secteur")
            time.sleep(60)
            etat, charge = batterie()
        autres, libre = concurrents()
        compteur[nom] = compteur.get(nom, 0) + 1
        etiquette = f"{a.nom}-{nom}-{'e' if marque else compteur[nom]}"
        cmd = [sys.executable, "-I", os.path.join(ICI, "modeles-base.py"), "--exe", EXE, "--modele", a.modele,
               "--invite", INVITE, "--n", str(a.n), "--etiquette", etiquette, "--sortie", a.sortie, "--"]
        cmd += shlex.split(a.commun) + args
        ecrire(f"passe {rang}/{len(plan)} {etiquette} (secteur, charge {charge} %, RAM libre {libre} Mo, autres : {autres}) : {' '.join(shlex.split(a.commun) + args)}")
        t0 = time.time()
        subprocess.run(cmd, capture_output=True, text=True)
        d = time.time() - t0
        try:
            res = json.load(open(os.path.join(a.sortie, etiquette + ".json"), encoding="utf-8"))
            err = open(os.path.join(a.sortie, etiquette + ".stderr.log"), encoding="utf-8").read()
        except Exception as e:
            ecrire(f"  échec de lecture du résultat : {e}")
            continue
        m = re.search(r"load time\s*=\s*([\d.]+) ms", err)
        cs = stats_cache(err)
        go = lambda x: round(x / 1e9, 3) if x is not None else None
        pf, ge = res.get("prefill") or {}, res.get("generation") or {}
        ligne = {"date": res["date"], "modele": a.nom, "config": nom, "palindrome": palindrome, "rang": rang,
                 "batterie": etat, "charge_pct": charge, "code_retour": res["code_retour"],
                 "chargement_ms": float(m.group(1)) if m else None,
                 "prefill_jetons": pf.get("n"), "prefill_js": pf.get("jetons_s"),
                 "generation_jetons": ge.get("n"), "generation_js": ge.get("jetons_s"),
                 "ensemble_travail_pointe_go": go(res["memoire_pointe"]["ensemble_travail_octets"]),
                 "ensemble_travail_final_go": go(res["memoire_pointe"]["ensemble_travail_final_octets"]),
                 "engagee_pointe_go": go(res["memoire_pointe"]["engagee_octets"]),
                 "vram_repos_mio": res["vram_mio"]["repos"], "vram_pointe_mio": res["vram_mio"]["pointe"],
                 "disque_lu_go": go(res["disque"]["octets_lus_pendant"]),
                 "disque_attribuable_go": go(res["disque"]["octets_attribuables_estimes"]),
                 "disque_repos_mo_s": round(res["disque"]["debit_repos_moyen_o_s"] / 1e6, 2),
                 "duree_s": round(res["duree_s"], 1), "cache_succes_pct": cs[0], "cache_succes": cs[1],
                 "cache_defauts": cs[2], "cache_envoye_mio": cs[3], "sortie_sha256": res["sortie_sha256"],
                 "concurrents": autres, "ram_libre_debut_mo": libre,
                 "arguments": " ".join(shlex.split(a.commun) + args)}
        # octets lus pendant la génération : la série du compteur sur la fenêtre [fin - durée de la
        # génération, fin] (la génération est la dernière phase ; l'échantillonnage final est compté)
        dg, dpj = None, None
        if ge.get("ms") and res.get("disque_serie"):
            debut = res["fin_s"] - ge["ms"] / 1000.0
            octs, prec = 0.0, None
            for ti, v in res["disque_serie"]:
                if prec is not None and ti > debut:
                    octs += (ti - max(prec, debut)) * v
                prec = ti
            octs -= res["disque"]["debit_repos_moyen_o_s"] * ge["ms"] / 1000.0
            dg, dpj = round(octs / 1e9, 3), round(octs / 1e9 / ge["n"], 4)
        ligne["disque_generation_go"], ligne["disque_par_jeton_genere_go"] = dg, dpj
        if marque:
            ecrire(f"  échauffement (non retenu) : génération {ligne['generation_js']} j/s, préremplissage {ligne['prefill_js']} j/s")
            ligne["config"] = nom + "-echauffement"
        w.writerow(ligne)
        fcsv.flush()
        ecrire(f"  code {ligne['code_retour']} en {d:.0f} s : préremplissage {ligne['prefill_js']} j/s, génération "
               f"{ligne['generation_js']} j/s, pointe {ligne['ensemble_travail_pointe_go']} Go (fin "
               f"{ligne['ensemble_travail_final_go']}), VRAM {ligne['vram_pointe_mio']} Mio, disque "
               f"{ligne['disque_attribuable_go']} Go attribuables ({dpj} Go par jeton généré), cache {ligne['cache_succes_pct']} %, sortie {ligne['sortie_sha256'][:12]}")
    ecrire("série terminée")


if __name__ == "__main__":
    main()
