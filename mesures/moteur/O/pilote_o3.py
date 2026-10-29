"""Pilote de l'étape O3 du lot O : C3 (codé contre brut, au bit), le compte du cache contre rejouer.

Critères déclarés avant le lancement : moteur/REPRISE-O.md, « O3 ».

Ce que fait le pilote, dans l'ordre :
  1. vérifie l'alimentation (Win32_Battery BatteryStatus = 2 : secteur) et qu'aucun llama-* ne tourne
     sur la carte ; prend le verrou ~/dev/verrou-carte.txt (attend s'il a moins de 2 h) ;
  2. lance `troncons evaluer` sur le fichier codé puis sur le fichier brut (mêmes fenêtres, même
     moteur), chacun avec son .kld, son CSV d'empreintes, sa trace et son journal ;
  3. compare : empreintes des 5 120 pas (CSV) et .kld octet pour octet ;
  4. rejoue la trace du moteur codé dans `rejouer` (même nombre d'emplacements) et compare les
     compteurs à l'unité ; puis la cassure (`rejouer --casser`) ;
  5. écrit le résumé JSON ; retire le verrou.

Usage (depuis la racine du dépôt) :
  python -I -X utf8 mesures/moteur/O/pilote_o3.py --seance <nom> [--fenetres 10] [--positions 512] [--modele gpt-oss-120b]
(--modele : gpt-oss-20b par défaut ; les jetons des fenêtres sont ceux de la base du 20b, même
vocabulaire o200k_harmony pour les deux modèles.)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

RACINE = pathlib.Path(__file__).resolve().parents[3]
CIBLE = pathlib.Path("~/dev/cibles/troncons-O/release")
TRONCONS = CIBLE / "troncons.exe"
REJOUER = CIBLE / "rejouer.exe"
MODELES = pathlib.Path("~/dev/modeles/trc")
BASE = pathlib.Path("~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld")
ESSAIS = pathlib.Path("~/dev/essais/troncons/lot-O")
VERROU = pathlib.Path("~/dev/verrou-carte.txt")
JOURNAUX = RACINE / "mesures/moteur/O/journaux/o3"


def maintenant() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ps(cmd: str) -> str:
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True).stdout.strip()


def alimentation() -> str:
    return ps("(Get-CimInstance Win32_Battery).BatteryStatus")


def llama_sur_la_carte() -> list[str]:
    s = ps("Get-Process | Where-Object { $_.ProcessName -like 'llama*' } | ForEach-Object { $_.ProcessName + ':' + $_.Id }")
    return [x for x in s.splitlines() if x.strip()]


def prendre_verrou(lot: str, journal) -> None:
    while True:
        if VERROU.exists():
            age = time.time() - VERROU.stat().st_mtime
            if age < 2 * 3600:
                journal(f"verrou présent ({VERROU.read_text(encoding='utf-8', errors='replace').strip()!r}, {age/60:.0f} min) : attente")
                time.sleep(60)
                continue
            journal(f"verrou de plus de 2 h ({age/3600:.1f} h) : repris")
        VERROU.write_text(f"lot {lot}, {maintenant()}, pilote_o3.py, pid {os.getpid()}\n", encoding="utf-8")
        return


def rendre_verrou() -> None:
    try:
        if VERROU.exists() and "pilote_o3.py" in VERROU.read_text(encoding="utf-8", errors="replace"):
            VERROU.unlink()
    except OSError:
        pass


def lancer(cmd: list, sortie: pathlib.Path, journal) -> int:
    journal(f"lance : {' '.join(map(str, cmd))}")
    with open(sortie, "w", encoding="utf-8") as f:
        r = subprocess.run([str(c) for c in cmd], stdout=f, stderr=subprocess.STDOUT)
    journal(f"fini (code {r.returncode})")
    return r.returncode


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def lire_csv(p: pathlib.Path) -> list[list[str]]:
    lignes = p.read_text(encoding="utf-8").splitlines()
    return [l.split(",") for l in lignes[1:] if l]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seance", required=True)
    ap.add_argument("--fenetres", type=int, default=10)
    ap.add_argument("--positions", type=int, default=512)
    ap.add_argument("--sans-verrou", action="store_true")
    ap.add_argument("--modele", default="gpt-oss-20b")
    a = ap.parse_args()
    JOURNAUX.mkdir(parents=True, exist_ok=True)
    ESSAIS.mkdir(parents=True, exist_ok=True)
    jl = JOURNAUX / f"pilote-{a.seance}.log"
    fj = open(jl, "a", encoding="utf-8")

    def journal(m: str) -> None:
        ligne = f"[{maintenant()}] {m}"
        print(ligne, flush=True)
        fj.write(ligne + "\n")
        fj.flush()

    resume = {"modele": a.modele, "seance": a.seance, "debut": maintenant(), "fenetres": a.fenetres, "positions": a.positions}
    resume["alimentation_debut"] = alimentation()
    journal(f"alimentation (BatteryStatus) : {resume['alimentation_debut']}")
    if resume["alimentation_debut"] != "2":
        journal("pas sur secteur : arrêt")
        return 2
    if not a.sans_verrou:
        prendre_verrou("O", journal)
    try:
        llama = llama_sur_la_carte()
        resume["llama_au_debut"] = llama
        if llama:
            journal(f"llama-* en cours : {llama} (noté ; les logits n'en dépendent pas, les temps si)")
        passes = {}
        for nom, fichier, brut in (("code", MODELES / f"{a.modele}.trc", False), ("brut", MODELES / f"{a.modele}-brut.trc", True)):
            kld = ESSAIS / f"o3-{a.seance}-{nom}.kld"
            csv = JOURNAUX / f"o3-{a.seance}-{nom}-empreintes.csv"
            tr = ESSAIS / f"o3-{a.seance}-{nom}.trace"
            js = JOURNAUX / f"o3-{a.seance}-{nom}.json"
            cmd = [TRONCONS, "evaluer", "--modele", fichier, "--base", BASE, "--fenetres", a.fenetres,
                   "--positions", a.positions, "--sortie", kld, "--empreintes", csv, "--trace", tr, "--journal", js]
            if brut:
                cmd.append("--brut")
            t0 = time.time()
            code = lancer(cmd, JOURNAUX / f"o3-{a.seance}-{nom}.log", journal)
            passes[nom] = {"code": code, "secondes": time.time() - t0, "kld": str(kld), "csv": str(csv), "trace": str(tr), "journal": str(js),
                           "alimentation_fin": alimentation()}
            if code != 0:
                journal(f"passe {nom} en échec : arrêt")
                resume["passes"] = passes
                return 1
        resume["passes"] = passes
        # C3 : empreintes des pas et .kld
        ec, eb = lire_csv(pathlib.Path(passes["code"]["csv"])), lire_csv(pathlib.Path(passes["brut"]["csv"]))
        diff = [i for i, (x, y) in enumerate(zip(ec, eb)) if x != y]
        c3 = {"pas_code": len(ec), "pas_brut": len(eb), "pas_differents": len(diff) + abs(len(ec) - len(eb)),
              "premiers_differents": [ec[i] + eb[i][-1:] for i in diff[:5]]}
        if a.positions == 512:
            kc, kb = pathlib.Path(passes["code"]["kld"]), pathlib.Path(passes["brut"]["kld"])
            c3["kld_sha256_code"], c3["kld_sha256_brut"] = sha256(kc), sha256(kb)
            c3["kld_egaux"] = c3["kld_sha256_code"] == c3["kld_sha256_brut"]
        c3["tient"] = c3["pas_differents"] == 0 and c3.get("kld_egaux", True) and len(ec) == a.fenetres * a.positions
        resume["C3"] = c3
        journal(f"C3 : {c3['pas_differents']} pas différents sur {len(ec)} ; kld égaux : {c3.get('kld_egaux')} ; tient : {c3['tient']}")
        # Compte du cache contre rejouer
        jc = json.loads(pathlib.Path(passes["code"]["journal"]).read_text(encoding="utf-8"))
        cm = jc["compteurs"]
        n = jc["moteur"]["emplacements"]
        rj = {}
        for casser in (False, True):
            cmd = [str(REJOUER), "--trace", passes["code"]["trace"], "--emplacements", str(n)] + (["--casser"] if casser else [])
            r = subprocess.run(cmd, capture_output=True, text=True)
            v = json.loads(r.stdout)
            rj["casse" if casser else "temoin"] = v
        (JOURNAUX / f"o3-{a.seance}-rejouer.json").write_text(json.dumps(rj, ensure_ascii=False, indent=1), encoding="utf-8")

        def comptes(v):
            x = v["resultats"][0] if "resultats" in v else v
            return x

        t = comptes(rj["temoin"])
        k = comptes(rj["casse"])
        cles = ("succes_vram", "succes_ram", "defauts_disque", "evictions")
        moteur = {c: cm[c] for c in cles}
        sim = {c: t.get(c) for c in cles}
        sim_casse = {c: k.get(c) for c in cles}
        resume["cache"] = {"emplacements": n, "moteur": moteur, "rejouer": sim, "rejouer_casse": sim_casse,
                           "egal": moteur == sim, "cassure_tombe": moteur != sim_casse}
        journal(f"cache : moteur {moteur} ; rejouer {sim} ; égal : {moteur == sim} ; cassure {sim_casse}")
        resume["fin"] = maintenant()
        resume["alimentation_fin"] = alimentation()
        return 0
    finally:
        if not a.sans_verrou:
            rendre_verrou()
        (JOURNAUX / f"o3-{a.seance}-resume.json").write_text(json.dumps(resume, ensure_ascii=False, indent=1), encoding="utf-8")
        fj.close()


if __name__ == "__main__":
    sys.exit(main())
