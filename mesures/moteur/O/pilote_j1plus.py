"""Pilote de la seconde séance du 120b (lot O) : diagnostic D-C7, variante L12, préchargement (J1+),
C12 sur le fichier brut, et la conversation harmony publiée.

Critères déclarés avant le lancement : moteur/REPRISE-O.md (« Diagnostic C7 et variante L12 »,
« J1+ : préchargement »). Chaque passe est un processus neuf ; secteur et absence de llama-*
vérifiés avant chaque passe ; le verrou de la carte est tenu toute la séance.

  0. Témoin F : evaluer --flux sur le 20b (10 fenêtres) contre la boucle de pas, et sa cassure.
  1. D-C7   : generer 1 jeton, invite courte : 120b, 20b, 20b, 120b ; puis la même série avec
              --longueur-lecture 12582912 (C7-bis : fenêtres de même taille).
  2. L12    : mesurer 120b : A B B A (A : J1 tel quel ; B : --longueur-lecture 12582912).
  3. PF     : mesurer 120b : A B B A (A : la meilleure de L12 par médiane ; B : A + --prechargement).
  3 bis. FLUX : mesurer 120b : A B B A (A : meilleure ; B : A + --flux) ; préremplissage.
  4. C12    : mesurer 120b sur gpt-oss-120b-brut.trc (--brut), même invite : texte égal au codé.
  5. harmony : generer 120b, conversation au format harmony, 1 024 jetons au plus, arrêt sur
              <|return|>, meilleure configuration retenue.

Usage : python -I -X utf8 mesures/moteur/O/pilote_j1plus.py --seance <nom> [--sauter d_c7,l12,...]
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

RACINE = pathlib.Path(__file__).resolve().parents[3]
TRONCONS = pathlib.Path("~/dev/cibles/troncons-O/release/troncons.exe")
MODELES = pathlib.Path("~/dev/modeles/trc")
INVITE = pathlib.Path("~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt")
INVITE_SHA256 = "eadbe87e3d3ce6c81035a2a4d83f898d887ce7d76bd4336555d615ee0522ceff"
VERROU = pathlib.Path("~/dev/verrou-carte.txt")
JOURNAUX = RACINE / "mesures/moteur/O/journaux/j1plus"
L12 = "12582912"
QUESTION = ("Explique en français, en quelques paragraphes clairs, comment un modèle de langage à "
            "mélange d'experts de 120 milliards de paramètres peut tourner sur un ordinateur portable "
            "qui n'a que 16 Go de mémoire vive et 8 Go de mémoire graphique, en ne chargeant depuis le "
            "disque que les experts dont chaque jeton a besoin.")


def maintenant() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ps(cmd: str) -> str:
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seance", required=True)
    ap.add_argument("--sauter", default="")
    ap.add_argument("--meilleure", default="", help="configuration retenue d'une séance précédente (options séparées par des virgules)")
    a = ap.parse_args()
    sauter = set(x for x in a.sauter.split(",") if x)
    if hashlib.sha256(INVITE.read_bytes()).hexdigest() != INVITE_SHA256:
        print("invite : empreinte inattendue", file=sys.stderr)
        return 2
    JOURNAUX.mkdir(parents=True, exist_ok=True)
    court = JOURNAUX / "invite-courte.txt"
    court.write_text("The capital of France is", encoding="utf-8")
    fj = open(JOURNAUX / f"pilote-{a.seance}.log", "a", encoding="utf-8")

    def journal(m: str) -> None:
        ligne = f"[{maintenant()}] {m}"
        print(ligne, flush=True)
        fj.write(ligne + "\n")
        fj.flush()

    while VERROU.exists() and time.time() - VERROU.stat().st_mtime < 2 * 3600:
        journal(f"verrou présent : {VERROU.read_text(encoding='utf-8', errors='replace').strip()!r} ; attente")
        time.sleep(60)
    VERROU.write_text(f"lot O, {maintenant()}, pilote_j1plus.py, pid {os.getpid()}\n", encoding="utf-8")
    resume = {"seance": a.seance, "debut": maintenant(), "passes": []}
    compteur = [0]

    def passe(etiquette: str, modele: str, commande: str, extra: list[str], invite: list[str]) -> dict:
        compteur[0] += 1
        al = ps("(Get-CimInstance Win32_Battery).BatteryStatus")
        ll = ps("Get-Process | Where-Object { $_.ProcessName -like 'llama*' } | ForEach-Object { $_.ProcessName }")
        if al != "2":
            raise RuntimeError("pas sur secteur")
        nom = f"{a.seance}-{compteur[0]:02d}-{etiquette}"
        js = JOURNAUX / f"{nom}.json"
        fichier = MODELES / (f"{modele}-brut.trc" if "--brut" in extra else f"{modele}.trc")
        c = [str(TRONCONS), commande, "--modele", str(fichier), "--vocab", str(MODELES / f"{modele}.vocab.gguf"),
             "--journal", str(js), "--sortie", str(JOURNAUX / f"{nom}.txt"), "--trace", str(JOURNAUX / f"{nom}.trace")] + invite + extra
        journal(f"passe {nom} : alimentation {al}, llama [{ll}] ; {' '.join(c[1:])}")
        t0 = time.time()
        with open(JOURNAUX / f"{nom}.log", "w", encoding="utf-8") as f:
            r = subprocess.run(c, stdout=f, stderr=subprocess.STDOUT)
        p = {"nom": nom, "etiquette": etiquette, "code": r.returncode, "secondes": time.time() - t0, "journal": str(js), "commande": c}
        if r.returncode == 0:
            j = json.loads(js.read_text(encoding="utf-8"))
            p |= {"generation_jetons_s": j["generation_jetons_s"], "prefill_jetons_s": j["prefill_jetons_s"],
                  "ram_pointe": j["memoire"]["pointe_ensemble_travail"], "vram_pointe_mio": j["vram"]["pointe_mio"],
                  "texte_sha256": j["texte_sha256"], "h": j["compteurs_total"]["h_vram"],
                  "pf_emis": j["compteurs_total"].get("pf_emis"), "pf_utiles": j["compteurs_total"].get("pf_utiles")}
        resume["passes"].append(p)
        journal(f"  → code {r.returncode}, {p['secondes']:.0f} s, {p.get('generation_jetons_s')} j/s, texte {str(p.get('texte_sha256'))[:12]}")
        if r.returncode != 0:
            raise RuntimeError(f"passe {nom} en échec")
        return p

    wiki = ["--invite", str(INVITE), "-n", "256", "--repos", "10"]
    try:
        if "d_c7" not in sauter:
            for extra, suff in (([], "dc7"), (["--longueur-lecture", L12], "dc7bis")):
                for m in ("gpt-oss-120b", "gpt-oss-20b", "gpt-oss-20b", "gpt-oss-120b"):
                    passe(f"{suff}-{m[8:]}", m, "generer", extra + ["--sans-vram"], ["--invite", str(court), "-n", "1"])
        meilleure: list[str] = [x for x in a.meilleure.split(",") if x]

        def serie_abba(nom: str, a_extra: list[str], b_extra: list[str], cle: str) -> dict:
            vals, textes = {}, []
            for lettre, extra in (("A", a_extra), ("B", b_extra), ("B", b_extra), ("A", a_extra)):
                p = passe(f"{nom}-{lettre}", "gpt-oss-120b", "mesurer", extra, wiki)
                vals.setdefault(lettre, []).append(p[cle])
                textes.append(p["texte_sha256"])
            ma, mb = statistics.median(vals["A"]), statistics.median(vals["B"])
            bruit = max(max(v) - min(v) for v in vals.values()) / min(ma, mb)
            gain = mb / ma - 1
            r = {"grandeur": cle, "A": vals["A"], "B": vals["B"], "gain": gain, "bruit_relatif": bruit,
                 "B_vaut": gain > 2 * bruit and gain > 0.03, "textes_egaux": len(set(textes)) == 1, "a_extra": a_extra, "b_extra": b_extra}
            journal(f"{nom} : A {vals['A']} B {vals['B']} gain {gain:+.3f} bruit {bruit:.3f} → B vaut : {r['B_vaut']} ; textes égaux : {r['textes_egaux']}")
            return r

        # Témoin F (préremplissage par flux = boucle de pas, au bit) sur le 20b, puis sa cassure.
        if "temoin_f" not in sauter:
            ref = RACINE / "mesures/moteur/O/journaux/o3/o3-2026-10-15-s1-code-empreintes.csv"
            base = "~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld"
            ok = True
            for nom, fichier, fen in (("temoin-f", MODELES / "gpt-oss-20b.trc", "10"), ("temoin-f-casse", MODELES / "casse/gpt-oss-20b-casse-O3.trc", "1")):
                compteur[0] += 1
                tag = f"{a.seance}-{compteur[0]:02d}-{nom}"
                csv = JOURNAUX / f"{tag}-empreintes.csv"
                c = [str(TRONCONS), "evaluer", "--flux", "--modele", str(fichier), "--base", base, "--fenetres", fen,
                     "--sortie", f"~/dev/essais/troncons/lot-O/{tag}.kld", "--empreintes", str(csv), "--journal", str(JOURNAUX / f"{tag}.json")]
                journal(f"passe {tag} : {' '.join(c[1:])}")
                with open(JOURNAUX / f"{tag}.log", "w", encoding="utf-8") as f:
                    r = subprocess.run(c, stdout=f, stderr=subprocess.STDOUT)
                x = csv.read_text(encoding="utf-8").splitlines()[1:] if csv.exists() else []
                y = ref.read_text(encoding="utf-8").splitlines()[1:1 + len(x)]
                diff = sum(1 for u, v in zip(x, y) if u != v)
                journal(f"  → code {r.returncode} ; {len(x)} lignes, {diff} différentes de la boucle de pas")
                resume[nom] = {"code": r.returncode, "lignes": len(x), "differentes": diff}
                if nom == "temoin-f":
                    ok = r.returncode == 0 and len(x) == 5120 and diff == 0
                    if ok:
                        kf = pathlib.Path(f"~/dev/essais/troncons/lot-O/{tag}.kld")
                        kp = pathlib.Path("~/dev/essais/troncons/lot-O/o3-2026-10-15-s1-code.kld")
                        h = lambda q: hashlib.sha256(q.read_bytes()).hexdigest()
                        resume[nom]["kld_egaux"] = h(kf) == h(kp)
                        ok = resume[nom]["kld_egaux"]
                else:
                    resume[nom]["tombe"] = diff > 0 or r.returncode != 0
            resume["temoin_f_tient"] = ok
            journal(f"témoin F : {'TIENT' if ok else 'TOMBE'}")
        flux_ok = resume.get("temoin_f_tient", False)
        if "flux" not in sauter and flux_ok:
            resume["FLUX"] = serie_abba("flux", [], ["--flux"], "prefill_jetons_s")
            if resume["FLUX"]["B_vaut"] and resume["FLUX"]["textes_egaux"]:
                meilleure = ["--flux"]
        if "l12" not in sauter:
            resume["L12"] = serie_abba("l12", meilleure, meilleure + ["--longueur-lecture", L12], "generation_jetons_s")
            if resume["L12"]["B_vaut"] and resume["L12"]["textes_egaux"]:
                meilleure = meilleure + ["--longueur-lecture", L12]
        if "pf" not in sauter:
            resume["PF"] = serie_abba("pf", meilleure, meilleure + ["--prechargement"], "generation_jetons_s")
            if resume["PF"]["B_vaut"] and resume["PF"]["textes_egaux"]:
                meilleure = meilleure + ["--prechargement"]
        resume["meilleure"] = meilleure
        if "c12" not in sauter:
            # 13,25 Mo par tronçon brut : pas de L12 ; le flux s'il a tenu (logits égaux au bit, témoin F)
            passe("c12-brut", "gpt-oss-120b", "mesurer", ["--brut"] + (["--flux"] if "--flux" in meilleure else []), wiki)
        if "harmonie" not in sauter:
            passe("harmonie", "gpt-oss-120b", "generer", meilleure + ["--arret-fin"], ["--harmonie", QUESTION, "-n", "1024"])
        resume["fin"] = maintenant()
        return 0
    except RuntimeError as e:
        journal(f"arrêt : {e}")
        return 1
    finally:
        try:
            if VERROU.exists() and "pilote_j1plus.py" in VERROU.read_text(encoding="utf-8", errors="replace"):
                VERROU.unlink()
        except OSError:
            pass
        (JOURNAUX / f"pilote-{a.seance}.json").write_text(json.dumps(resume, ensure_ascii=False, indent=1), encoding="utf-8")
        fj.close()


if __name__ == "__main__":
    sys.exit(main())
