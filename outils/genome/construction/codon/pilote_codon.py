"""Pilote du lot A (codon synonyme du zéro, format .trc v1.2) : critère A-C1 (logits au bit) et jalon J1
refait sur le 120b en v1.2 contre v1.0 (A-C3 vitesse, octets lus par jeton, mémoire de pointe).

Critères déclarés le 2026-10-17, avant toute passe (genome/05-synthese.md § 4.6 et genome/06-codon-v1-2.md
§ « Critères ») ; rien ne se desserre après coup.

Phase c1-20b (A-C1, 20b) :
  T0  evaluer --flux sur gpt-oss-20b.trc (v1.0), 10 fenêtres de 512 jetons de ref-openai-20b.kld :
      témoin du programme d'aujourd'hui contre le CSV commité du 2026-10-15 (o3-2026-10-15-s1-code-
      empreintes.csv, boucle de pas ; témoin F : flux = boucle au bit). Seuil : 5 120 lignes égales.
  B   la même sur gpt-oss-20b-v12.trc. Seuil : **5 120 empreintes de logits égales** à T0, .kld égaux
      octet pour octet (proposition A1).
  K   cassure : copie de gpt-oss-20b-v12.trc à une médiane faussée (casser_mediane.py du lot O, couche 0,
      expert 30, ligne 100), 1 fenêtre, **--sans-garde** : au moins une ligne doit différer (l'instrument
      peut tomber). Ajout du 2026-10-17 à 09 h 35, après la première passe K : avec la garde de production
      (ajoutée au moteur après O3), la copie est refusée avant tout logit (« empreinte des octets utiles
      lus … au lieu de … ») ; c'est un témoin de la garde, gardé dans le journal, pas celui des logits.
      Le seuil ne change pas.
Phase c1-120b (A-C1, 120b) :
  B   evaluer --flux sur gpt-oss-120b-v12.trc, 10 fenêtres. Seuil : 5 120 empreintes égales au CSV commité
      du 120b v1.0 (o3-120b-2026-10-15-s1-code-empreintes.csv). Si une ligne diffère, la passe v1.0
      d'aujourd'hui (T0 120b) est lancée pour séparer le format du programme.
Phase j1 (A-C3 et J1, 120b, ABBA ABBA) :
  8 processus neufs A B B A A B B A ; A = gpt-oss-120b.trc (v1.0), B = gpt-oss-120b-v12.trc (v1.2) ;
  `troncons mesurer --flux --emplacements 326` (configuration retenue du J1+ ; même nombre d'emplacements
  des deux côtés, pour que seul le format change : un tronçon plus court peut sinon libérer un
  emplacement et changer le cache), invite wiki-3000 (SHA-256 eadbe87e…eff), 256 jetons gloutons,
  repos 10 s. Avant chaque passe : secteur (Win32_Battery = 2), aucun llama-*, VRAM notée ; verrou de la
  carte toute la séance.
  Mesures et seuils :
  - jetons : les 256 identifiants produits **égaux dans les 8 passes** (logits au bit ⇒ mêmes argmax) ;
  - octets lus par jeton (génération, compteur du moteur) : rapport B / A publié ; prédit 0,967 (zéro seul,
    3,7292 / 3,8549 sur les octets de tronçons, ±0,5 % selon les experts touchés) ;
  - jetons/s de génération : r = médiane(B) / médiane(A) ; σ = écart-type relatif des 4 passes A (v1.0
    contre v1.0, même séance) ; **pas de régression** si r ≥ 1 − 2σ ; gain **annoncé** seulement si
    r − 1 > 2σ (prédit +3,4 % si le disque limite) ; publié aussi : les 4 rapports appariés (A1,B2),
    (B3,A4), (A5,B6), (B7,A8) ;
  - mémoire de pointe (ensemble de travail) : médianes A et B publiées ; seuil : |B − A| ≤ 2 × bruit +
    0,5 Mo (bruit = plus grand écart entre passes d'un même fichier ; règle de C7) ;
  - VRAM de pointe et octets PDH : publiés.

Phases ajoutées le 2026-10-17 à 10 h 40, pendant la séance j1 et avant toute passe de ces phases,
parce que les quatre premières passes de j1 montrent un écart de jetons/s (v1.0 1,56 ; v1.2 2,59 et 2,24)
bien au-delà de ce que 3,3 % d'octets en moins peuvent rendre : on soupçonne la **disposition des
fichiers sur le disque** (le v1.0 a été écrit le 2026-10-15, le v1.2 aujourd'hui), pas le format.
Phase disque (l'étage disque seul, par fichier) :
  6 processus `troncons disque --n 1500 --graine 20261017 --repos 5` dans l'ordre A B C C B A ; A = le
  v1.0 d'origine, B = le v1.2, C = une **copie neuve du v1.0** (octet pour octet, SHA-256 vérifiée,
  écrite aujourd'hui juste avant la séance, donc disposée sur le disque comme le v1.2). Publié : Go/s par
  fichier. Lecture : si débit(C) ≈ débit(B) et débit(A) < débit(C) au-delà de 2 × l'écart d'une paire,
  l'écart de jetons/s du j1 vient de la disposition du fichier d'origine, pas du format.
Phase j1-copie (le format seul) :
  la séance j1 refaite à l'identique avec A = C (la copie neuve du v1.0) au lieu du v1.0 d'origine ; mêmes
  seuils que j1 (A-C3) ; c'est cette phase qui juge le format.

Séance s2, déclarée le 2026-10-17 à 11 h 50, avant toute passe de s2 : la copie C de s1 avait 289 545
fragments (fsutil file queryextents : v1.0 d'origine 65, v1.2 233 ; `journaux/s1-fragments.txt`), écrite
à 54 Mo/s pendant que d'autres équipes écrivaient : témoin confondu, phase j1-copie de s1 arrêtée après
deux passes. En s2, C = **le v1.0 recodé aujourd'hui par trc-codeur** (même écrivain, même jour que le
v1.2 ; SHA-256 égale à celle du v1.0 d'origine, 6c7b5f1d…dcce, ce qui est aussi le témoin d'identité du
codeur modifié sur le 120b), passé par `--fichier-c`. Phases disque et j1-copie, mêmes seuils ; le nombre
de fragments de C est relevé avant la séance.

Amendement de s2, déclaré le 2026-10-21 à 23 h 40, avant toute passe de s2 (aucune n'a tourné : le pilote
du 2026-10-17 à 13 h 21 attendait le verrou du lot B quand le flux a été coupé, `pilote-s2.log`) :
- **la phase j1 (A = v1.0 d'origine, B = v1.2) est ajoutée à s2** : le j1 de s1 a été pris sous charge
  (σ = 21,6 %, passes 5 à 7 lentes quel que soit le fichier ; leçon du 2026-10-17 : une mesure de vitesse
  prise sous charge ne conclut pas). C'est le J1 de la consigne ; mêmes seuils A-C3, rien ne se desserre.
- **le témoin C de s2 (le v1.0 recodé) est confondu avant toute passe** : échantillon des fragments
  (`s2-fragments.txt`, 11 fenêtres de 1 Gio) 47 745 fragments contre 26 pour le v1.0 d'origine. La phase
  j1-copie est gardée telle que déclarée, mais elle ne juge plus le format seul : elle mesure, à contenu
  égal au bit, ce que la disposition sur le disque fait aux jetons/s. Le verdict de format vient de j1.
- ordre de s2 : disque (A B C C B A), puis j1, puis j1-copie (ordre du code, inchangé).
- calme : avant et après chaque passe, le pilote relève et journalise les processus des autres flux
  (genome-capture, juge, trc-*, cargo, rustc, python) qui travaillent (plus de 5 % d'un cœur ou 8 Mo lus
  en 3 s) ; une passe ainsi prise est marquée « SOUS CHARGE » dans le journal et ne conclut pas. La séance
  ne part que quand ce relevé est vide deux fois de suite à une minute d'écart. Le verrou est rafraîchi
  avant chaque passe (le flux des pistes se met en pause à ses points d'attente tant que le verrou nomme
  « j1 » et a moins de 2 h).

Usage (racine du dépôt) :
  python -I -X utf8 outils/genome/construction/codon/pilote_codon.py --phases c1-20b,c1-120b,j1 --seance s1
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import statistics
import subprocess
import sys
import time

RACINE = pathlib.Path(__file__).resolve().parents[4]
TRONCONS = pathlib.Path("~/dev/cibles/troncons-codon/release/troncons.exe")
MODELES = pathlib.Path("~/dev/modeles/trc")
ESSAIS = pathlib.Path("~/dev/essais/troncons/codon")
INVITE = pathlib.Path("~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt")
INVITE_SHA256 = "eadbe87e3d3ce6c81035a2a4d83f898d887ce7d76bd4336555d615ee0522ceff"
BASE = "~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld"
REF20 = RACINE / "mesures/moteur/O/journaux/o3/o3-2026-10-15-s1-code-empreintes.csv"
REF120 = RACINE / "mesures/moteur/O/journaux/o3/o3-120b-2026-10-15-s1-code-empreintes.csv"
VERROU = pathlib.Path("~/dev/verrou-carte.txt")
JOURNAUX = RACINE / "mesures/genome/construction/codon/journaux"
MARQUE = "lot A (codon)"


def maintenant() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ps(cmd: str) -> str:
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True).stdout.strip()


def alimentation() -> str:
    return ps("(Get-CimInstance Win32_Battery).BatteryStatus")


def llama() -> list[str]:
    s = ps("Get-Process | Where-Object { $_.ProcessName -like 'llama*' } | ForEach-Object { $_.ProcessName + ':' + $_.Id }")
    return [x for x in s.splitlines() if x.strip()]


def autres_lourds() -> list[str]:
    """Processus des autres flux qui travaillent (amendement de s2) : parmi genome-capture, juge, trc-*,
    cargo, rustc et python (hors serveurs http et blender-mcp, hors ce pilote et ses enfants), ceux qui ont
    pris plus de 5 % d'un cœur ou lu plus de 8 Mo pendant 3 s. Un processus en pause (le flux des pistes
    attend que le verrou se libère) n'y figure pas."""
    s = ps(
        "$f = { Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(genome-capture|juge|trc-.*|cargo|rustc|python)[.]exe$' "
        f"-and $_.ProcessId -ne {os.getpid()} -and $_.ParentProcessId -ne {os.getpid()} "
        "-and $_.CommandLine -notmatch 'http[.]server|blender-mcp' } }; "
        "$a = @{}; & $f | ForEach-Object { $a[$_.ProcessId] = $_ }; Start-Sleep -Seconds 3; "
        "& $f | ForEach-Object { $o = $a[$_.ProcessId]; if ($o) { "
        "$cpu = (($_.KernelModeTime + $_.UserModeTime) - ($o.KernelModeTime + $o.UserModeTime)) / 3e7; "
        "$lu = ($_.ReadTransferCount - $o.ReadTransferCount) / 1e6; "
        "if ($cpu -gt 0.05 -or $lu -gt 8) { $c = ($_.CommandLine -replace '[ ]+', ' '); "
        "'{0}:{1}:cpu {2:N2} coeur:lu {3:N0} Mo:{4}' -f $_.Name, $_.ProcessId, $cpu, $lu, $c.Substring(0, [Math]::Min(100, $c.Length)) } } }")
    return [x for x in s.splitlines() if x.strip()]


def vram_mio() -> int:
    s = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout
    return int(s.strip().splitlines()[0])


def lire_csv(p: pathlib.Path) -> list[tuple[str, ...]]:
    with open(p, newline="", encoding="utf-8") as f:
        return [tuple(r) for r in csv.reader(f)][1:]


def comparer_csv(a: pathlib.Path, b: pathlib.Path) -> dict:
    la, lb = lire_csv(a), lire_csv(b)
    n = min(len(la), len(lb))
    diff = [i for i in range(n) if la[i] != lb[i]]
    return {"a": str(a.relative_to(RACINE)) if a.is_relative_to(RACINE) else str(a), "b": str(b.relative_to(RACINE)) if b.is_relative_to(RACINE) else str(b),
            "lignes_a": len(la), "lignes_b": len(lb), "differentes": len(diff), "premiere": la[diff[0]] if diff else None}


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phases", default="c1-20b,c1-120b,j1")
    ap.add_argument("--seance", required=True)
    ap.add_argument("--n", type=int, default=256)
    ap.add_argument("--emplacements", type=int, default=326)
    ap.add_argument("--fichier-c", default=str(ESSAIS / "gpt-oss-120b-copie-v10.trc"))
    ap.add_argument("--attendre-calme", action="store_true", help="amendement de s2 : partir sur deux relevés vides")
    a = ap.parse_args()
    phases = a.phases.split(",")
    if hashlib.sha256(INVITE.read_bytes()).hexdigest() != INVITE_SHA256:
        print("invite : empreinte inattendue", file=sys.stderr)
        return 2
    JOURNAUX.mkdir(parents=True, exist_ok=True)
    ESSAIS.mkdir(parents=True, exist_ok=True)
    fj = open(JOURNAUX / f"pilote-{a.seance}.log", "a", encoding="utf-8")

    def journal(m: str) -> None:
        ligne = f"[{maintenant()}] {m}"
        print(ligne, flush=True)
        fj.write(ligne + "\n")
        fj.flush()

    while VERROU.exists() and MARQUE not in VERROU.read_text(encoding="utf-8", errors="replace") and time.time() - VERROU.stat().st_mtime < 2 * 3600:
        journal(f"verrou présent : {VERROU.read_text(encoding='utf-8', errors='replace').strip()!r} ; attente")
        time.sleep(60)
    VERROU.write_text(f"{MARQUE}, {maintenant()}, pilote_codon.py {a.phases}, pid {os.getpid()}\n", encoding="utf-8")
    resume: dict = {"seance": a.seance, "phases": phases, "debut": maintenant(), "passes": []}
    if a.attendre_calme:
        vides, n = 0, 0
        while vides < 2:
            au = autres_lourds()
            vides = 0 if au else vides + 1
            if au and n % 5 == 0:
                journal(f"attente du calme : {au}")
            n += 1
            if vides < 2:
                os.utime(VERROU)
                time.sleep(60)
        journal("calme : relevé vide deux fois de suite à une minute d'écart")
        resume["debut"] = maintenant()

    def passe(nom: str, c: list[str]) -> dict:
        try:
            if VERROU.exists() and MARQUE in VERROU.read_text(encoding="utf-8", errors="replace"):
                os.utime(VERROU)
        except OSError:
            pass
        al, ll, vr, au = alimentation(), llama(), vram_mio(), autres_lourds()
        journal(f"{nom} : alimentation {al}, llama {ll}, VRAM {vr} Mio avant ; autres lourds {au if au else 'aucun'}"
                + (" ; SOUS CHARGE" if au else ""))
        if al != "2":
            raise RuntimeError("pas sur secteur : arrêt")
        t0 = time.time()
        with open(JOURNAUX / f"{nom}.log", "w", encoding="utf-8") as f:
            r = subprocess.run(c, stdout=f, stderr=subprocess.STDOUT)
        p = {"nom": nom, "commande": c, "code": r.returncode, "secondes": time.time() - t0, "alimentation_avant": al,
             "llama_avant": ll, "vram_avant_mio": vr, "autres_lourds_avant": au, "autres_lourds_apres": autres_lourds(),
             "alimentation_apres": alimentation()}
        if p["autres_lourds_apres"]:
            journal(f"{nom} : autres lourds après {p['autres_lourds_apres']} ; SOUS CHARGE")
        resume["passes"].append(p)
        journal(f"{nom} : code {r.returncode}, {p['secondes']:.0f} s")
        if r.returncode != 0:
            raise RuntimeError(f"{nom} : code {r.returncode}")
        return p

    def evaluer(nom: str, trc: str, fenetres: int) -> pathlib.Path:
        csvp = JOURNAUX / f"{nom}-empreintes.csv"
        js = JOURNAUX / f"{nom}.json"
        if csvp.exists() and js.exists() and len(lire_csv(csvp)) == 512 * fenetres:
            journal(f"{nom} : déjà mesuré (CSV de {512 * fenetres} lignes et journal présents), repris tel quel")
            return csvp
        passe(nom, [str(TRONCONS), "evaluer", "--flux", "--modele", str(MODELES / trc), "--base", BASE, "--fenetres", str(fenetres),
                    "--positions", "512", "--sortie", str(ESSAIS / f"{nom}.kld"), "--empreintes", str(csvp), "--journal", str(JOURNAUX / f"{nom}.json")])
        return csvp

    try:
        if "c1-20b" in phases:
            t0 = evaluer(f"{a.seance}-c1-20b-T0-v10", "gpt-oss-20b.trc", 10)
            b = evaluer(f"{a.seance}-c1-20b-B-v12", "gpt-oss-20b-v12.trc", 10)
            res = {"T0_contre_commite": comparer_csv(REF20, t0), "B_contre_T0": comparer_csv(t0, b),
                   "kld_T0": sha256(ESSAIS / f"{a.seance}-c1-20b-T0-v10.kld"), "kld_B": sha256(ESSAIS / f"{a.seance}-c1-20b-B-v12.kld")}
            res["kld_egaux"] = res["kld_T0"] == res["kld_B"]
            casse = ESSAIS / "gpt-oss-20b-v12-casse-mediane.trc"
            if not casse.exists():
                r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(RACINE / "mesures/moteur/O/casser_mediane.py"), str(MODELES / "gpt-oss-20b-v12.trc"),
                                    str(casse), "0", "30", "100", str(JOURNAUX / f"{a.seance}-casser-mediane-20b-v12.json")], capture_output=True, text=True)
                journal(f"casser_mediane : code {r.returncode} {r.stdout.strip()[-200:]} {r.stderr.strip()[-200:]}")
            k = JOURNAUX / f"{a.seance}-c1-20b-K-casse-empreintes.csv"
            passe(f"{a.seance}-c1-20b-K-casse", [str(TRONCONS), "evaluer", "--flux", "--sans-garde", "--modele", str(casse), "--base", BASE, "--fenetres", "1",
                                                "--positions", "512", "--sortie", str(ESSAIS / "casse.kld"), "--empreintes", str(k), "--journal", str(JOURNAUX / f"{a.seance}-c1-20b-K-casse.json")])
            res["K_contre_T0"] = comparer_csv(t0, k)
            res["verdict"] = {"temoin_programme": res["T0_contre_commite"]["differentes"] == 0 and res["T0_contre_commite"]["lignes_b"] == 5120,
                              "A_C1_20b": res["B_contre_T0"]["differentes"] == 0 and res["B_contre_T0"]["lignes_b"] == 5120 and res["kld_egaux"],
                              "cassure_tombe": res["K_contre_T0"]["differentes"] > 0}
            resume["c1_20b"] = res
            journal(f"c1-20b : {json.dumps(res['verdict'], ensure_ascii=False)}")
        if "c1-120b" in phases:
            b = evaluer(f"{a.seance}-c1-120b-B-v12", "gpt-oss-120b-v12.trc", 10)
            res = {"B_contre_commite_v10": comparer_csv(REF120, b)}
            if res["B_contre_commite_v10"]["differentes"] != 0 or res["B_contre_commite_v10"]["lignes_b"] != 5120:
                t0 = evaluer(f"{a.seance}-c1-120b-T0-v10", "gpt-oss-120b.trc", 10)
                res["T0_contre_commite"] = comparer_csv(REF120, t0)
                res["B_contre_T0"] = comparer_csv(t0, b)
            res["verdict"] = {"A_C1_120b": (res.get("B_contre_T0") or res["B_contre_commite_v10"])["differentes"] == 0}
            resume["c1_120b"] = res
            journal(f"c1-120b : {json.dumps(res['verdict'], ensure_ascii=False)}")
        copie = pathlib.Path(a.fichier_c)
        if "disque" in phases:
            chemins = {"A": MODELES / "gpt-oss-120b.trc", "B": MODELES / "gpt-oss-120b-v12.trc", "C": copie}
            for i, l in enumerate(["A", "B", "C", "C", "B", "A"], 1):
                nom = f"{a.seance}-disque-{i}-{l}"
                passe(nom, [str(TRONCONS), "disque", "--modele", str(chemins[l]), "--n", "1500", "--graine", "20261017", "--repos", "5",
                            "--journal", str(JOURNAUX / f"{nom}.json")])
        for ph, fa in (("j1", MODELES / "gpt-oss-120b.trc"), ("j1-copie", copie)):
            if ph not in phases:
                continue
            plan = ["A", "B", "B", "A", "A", "B", "B", "A"]
            fichiers = {"A": fa, "B": MODELES / "gpt-oss-120b-v12.trc"}
            for i, l in enumerate(plan, 1):
                nom = f"{a.seance}-{ph}-{i}-{l}"
                passe(nom, [str(TRONCONS), "mesurer", "--modele", str(fichiers[l]), "--vocab", str(MODELES / "gpt-oss-120b.vocab.gguf"),
                            "--invite", str(INVITE), "-n", str(a.n), "--flux", "--emplacements", str(a.emplacements), "--repos", "10",
                            "--sortie", str(JOURNAUX / f"{nom}.txt"), "--journal", str(JOURNAUX / f"{nom}.json")])
            resume[ph] = {"plan": plan, "fichiers": {k: str(v) for k, v in fichiers.items()}}
        resume["fin"] = maintenant()
        return 0
    except RuntimeError as e:
        journal(f"arrêt : {e}")
        resume["arret"] = str(e)
        return 1
    finally:
        try:
            if VERROU.exists() and "pilote_codon.py" in VERROU.read_text(encoding="utf-8", errors="replace"):
                VERROU.unlink()
        except OSError:
            pass
        (JOURNAUX / f"pilote-{a.seance}-{'-'.join(phases)}.json").write_text(json.dumps(resume, ensure_ascii=False, indent=1), encoding="utf-8")
        fj.close()


if __name__ == "__main__":
    sys.exit(main())
