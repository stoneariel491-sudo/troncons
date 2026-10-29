"""Lot B, pas S3-V : la vitesse du mode rapide contre le mode exact sur gpt-oss-20b, séance ABBA.

Écrit pour troncons, rôle « synonyme » de la construction, le 2026-10-17, sur le modèle de
mesures/moteur/O/pilote_o4.py (série Y20 : même invite, -n 256, repos 10 s). Règles déclarées dans
mesures/genome/construction/synonyme/00-seuils-declares.md § S3-V.

Séance A B B A A B B A : A le fichier exact (v1.0), B le compagnon rapide (--rapide). Avant chaque
passe : secteur (Win32_Battery BatteryStatus = 2), aucun llama*, VRAM relevée. Verrou de la carte
tenu toute la séance (~/dev/verrou-carte.txt), attendu s'il existe depuis moins de 2 h.

Amendement de la séance s2, déclaré le 2026-10-22 vers 0 h, avant toute passe de s2 (leçon du 2026-10-17 :
une passe prise sous charge ne conclut pas ; s1 a tourné pendant la passe B0, le débit et l'écriture du
compagnon du 120b) :
- **calme** : même critère que le pilote du lot A (outils/genome/construction/codon/pilote_codon.py,
  amendement de son s2), réécrit ici : parmi genome-capture, juge, trc-*, cargo, rustc, python et troncons
  (hors serveurs http et blender-mcp, hors ce pilote et ses enfants), un processus qui prend plus de 5 %
  d'un cœur ou lit plus de 8 Mo en 3 s « travaille ». Avec --attendre-calme, la séance ne part que sur deux
  relevés vides à une minute d'écart ; avant et après chaque passe, le relevé est journalisé et une passe
  qui en a un non vide est marquée « sous_charge » : elle est publiée mais ne conclut pas ; la synthèse
  donne aussi le rapport sur les seules passes calmes ;
- le verrou est rafraîchi avant chaque passe et nomme une séance de vitesse (le flux des pistes se met en
  pause sur les mots « vitesse », « abba », « j1 ») ;
- --vocab pour le 120b (A = gpt-oss-120b.trc, B = son compagnon frontière ; 120b-V des seuils).

Usage : python -I -X utf8 outils/genome/synonyme/pilote_vitesse.py --seance NOM --rapide R.trc
        [--exact E.trc] [--vocab V.gguf] [--n 256] [--plan ABBAABBA] [--attendre-calme]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import statistics
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
RACINE = pathlib.Path(__file__).resolve().parents[3]
TRONCONS = pathlib.Path("~/dev/cibles/troncons-synonyme/release/troncons.exe")
MODELES = pathlib.Path("~/dev/modeles/trc")
INVITE = pathlib.Path("~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt")
INVITE_SHA256 = "eadbe87e3d3ce6c81035a2a4d83f898d887ce7d76bd4336555d615ee0522ceff"
VERROU = pathlib.Path("~/dev/verrou-carte.txt")
JOURNAUX = RACINE / "mesures/genome/construction/synonyme/vitesse"


def maintenant() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ps(cmd: str) -> str:
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True).stdout.strip()


def autres_lourds() -> list[str]:
    """Processus des autres flux qui travaillent (amendement de s2) : plus de 5 % d'un cœur ou plus de
    8 Mo lus pendant 3 s. Un processus en pause n'y figure pas."""
    s = ps(
        "$f = { Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(genome-capture|juge|trc-.*|cargo|rustc|python|troncons)[.]exe$' "
        f"-and $_.ProcessId -ne {os.getpid()} -and $_.ParentProcessId -ne {os.getpid()} "
        "-and $_.CommandLine -notmatch 'http[.]server|blender-mcp' } }; "
        "$a = @{}; & $f | ForEach-Object { $a[$_.ProcessId] = $_ }; Start-Sleep -Seconds 3; "
        "& $f | ForEach-Object { $o = $a[$_.ProcessId]; if ($o) { "
        "$cpu = (($_.KernelModeTime + $_.UserModeTime) - ($o.KernelModeTime + $o.UserModeTime)) / 3e7; "
        "$lu = ($_.ReadTransferCount - $o.ReadTransferCount) / 1e6; "
        "if ($cpu -gt 0.05 -or $lu -gt 8) { $c = ($_.CommandLine -replace '[ ]+', ' '); "
        "'{0}:{1}:cpu {2:N2} coeur:lu {3:N0} Mo:{4}' -f $_.Name, $_.ProcessId, $cpu, $lu, $c.Substring(0, [Math]::Min(100, $c.Length)) } } }")
    return [x for x in s.splitlines() if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seance", required=True)
    ap.add_argument("--rapide", required=True)
    ap.add_argument("--exact", default=str(MODELES / "gpt-oss-20b.trc"))
    ap.add_argument("--n", type=int, default=256)
    ap.add_argument("--plan", default="ABBAABBA")
    ap.add_argument("--vocab", default=str(MODELES / "gpt-oss-20b.vocab.gguf"))
    ap.add_argument("--attendre-calme", action="store_true", help="amendement de s2 : partir sur deux relevés vides")
    a = ap.parse_args()
    if hashlib.sha256(INVITE.read_bytes()).hexdigest() != INVITE_SHA256:
        print("invite : empreinte inattendue", file=sys.stderr)
        return 2
    JOURNAUX.mkdir(parents=True, exist_ok=True)
    fj = open(JOURNAUX / f"pilote-{a.seance}.log", "a", encoding="utf-8")

    def journal(m: str) -> None:
        ligne = f"[{maintenant()}] {m}"
        print(ligne, flush=True)
        fj.write(ligne + "\n")
        fj.flush()

    while VERROU.exists() and time.time() - VERROU.stat().st_mtime < 2 * 3600:
        journal(f"verrou présent : {VERROU.read_text(encoding='utf-8', errors='replace').strip()!r} ; attente")
        time.sleep(60)
    VERROU.write_text(f"lot B synonyme, {maintenant()}, séance de vitesse {a.seance}, pilote_vitesse.py, pid {os.getpid()}\n", encoding="utf-8")
    resume = {"seance": a.seance, "debut": maintenant(), "plan": a.plan, "exact": a.exact, "rapide": a.rapide, "vocab": a.vocab, "passes": []}
    code = 0
    try:
        if a.attendre_calme:
            vides, n = 0, 0
            while vides < 2:
                au = autres_lourds()
                vides = vides + 1 if not au else 0
                if au and n % 5 == 0:
                    journal(f"attente du calme : {au}")
                n += 1
                if vides < 2:
                    os.utime(VERROU)
                    time.sleep(60)
            journal("calme : relevé vide deux fois de suite à une minute d'écart")
            resume["debut"] = maintenant()
        for i, lettre in enumerate(a.plan, 1):
            os.utime(VERROU)
            charge_avant = autres_lourds()
            al = ps("(Get-CimInstance Win32_Battery).BatteryStatus")
            ll = ps("Get-Process | Where-Object { $_.ProcessName -like 'llama*' } | ForEach-Object { $_.ProcessName + ':' + $_.Id }")
            vr = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.strip()
            journal(f"passe {i}/{len(a.plan)} {lettre} : alimentation {al}, llama [{ll}], VRAM {vr} Mio avant, charge {charge_avant}")
            if al != "2":
                journal("pas sur secteur : arrêt")
                code = 2
                break
            nom = f"{a.seance}-{i}-{lettre}"
            js = JOURNAUX / f"{nom}.json"
            modele = a.exact if lettre == "A" else a.rapide
            c = [str(TRONCONS), "mesurer", "--modele", modele, "--vocab", a.vocab, "--invite", str(INVITE),
                 "-n", str(a.n), "--sortie", str(JOURNAUX / f"{nom}.txt"), "--journal", str(js), "--repos", "10"]
            if lettre == "B":
                c.append("--rapide")
            t0 = time.time()
            with open(JOURNAUX / f"{nom}.log", "w", encoding="utf-8") as f:
                r = subprocess.run(c, stdout=f, stderr=subprocess.STDOUT)
            charge_apres = autres_lourds()
            p = {"passe": i, "lettre": lettre, "commande": c, "code": r.returncode, "secondes": time.time() - t0, "alimentation_avant": al,
                 "llama_avant": ll, "vram_avant_mio": vr, "journal": str(js),
                 "charge_avant": charge_avant, "charge_apres": charge_apres, "sous_charge": bool(charge_avant or charge_apres)}
            if r.returncode == 0:
                j = json.loads(js.read_text(encoding="utf-8"))
                p["generation_jetons_s"] = j.get("generation_jetons_s")
            resume["passes"].append(p)
            journal(f"passe {i} {lettre} : code {r.returncode}, {p['secondes']:.0f} s, {p.get('generation_jetons_s')} j/s"
                    + (f", SOUS CHARGE {charge_avant + charge_apres}" if p["sous_charge"] else ""))
            if r.returncode != 0:
                code = 1
                break
        va = [p["generation_jetons_s"] for p in resume["passes"] if p["lettre"] == "A" and p.get("generation_jetons_s")]
        vb = [p["generation_jetons_s"] for p in resume["passes"] if p["lettre"] == "B" and p.get("generation_jetons_s")]
        if len(va) >= 2 and len(vb) >= 2:
            ma = statistics.median(va)
            sigma = statistics.stdev(va) / ma
            rapport = statistics.median(vb) / ma
            resume["synthese"] = {"A_jetons_s": va, "B_jetons_s": vb, "mediane_A": ma, "mediane_B": statistics.median(vb),
                                  "bruit_relatif_A": sigma, "rapport_median_B_sur_A": rapport,
                                  "regle": "gain annoncé si rapport > 1 + 2σ (σ : écart-type relatif des passes A)",
                                  "gain_annonce": rapport > 1 + 2 * sigma,
                                  "passes_sous_charge": [p["passe"] for p in resume["passes"] if p.get("sous_charge")]}
            ca = [p["generation_jetons_s"] for p in resume["passes"] if p["lettre"] == "A" and p.get("generation_jetons_s") and not p.get("sous_charge")]
            cb = [p["generation_jetons_s"] for p in resume["passes"] if p["lettre"] == "B" and p.get("generation_jetons_s") and not p.get("sous_charge")]
            if len(ca) >= 2 and len(cb) >= 2:
                mca = statistics.median(ca)
                sca = statistics.stdev(ca) / mca
                resume["synthese_calme"] = {"A_jetons_s": ca, "B_jetons_s": cb, "bruit_relatif_A": sca,
                                            "rapport_median_B_sur_A": statistics.median(cb) / mca,
                                            "gain_annonce": statistics.median(cb) / mca > 1 + 2 * sca}
        resume["fin"] = maintenant()
        return code
    finally:
        try:
            if VERROU.exists() and "pilote_vitesse.py" in VERROU.read_text(encoding="utf-8", errors="replace"):
                VERROU.unlink()
        except OSError:
            pass
        (JOURNAUX / f"pilote-{a.seance}.json").write_text(json.dumps(resume, ensure_ascii=False, indent=1), encoding="utf-8")
        fj.close()


if __name__ == "__main__":
    sys.exit(main())
