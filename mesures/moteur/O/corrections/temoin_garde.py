"""Témoins de la garde de production (constat M1 de l'épreuve J1), sur le 20b, passes courtes.

Cas (seuils dans seuils-declares.md, bloc 3, commités avant la première passe) :
  G-XO3   copie à médiane faussée du lot O, avec la garde        : erreur nommée couche 0, expert 30
  G-XO3s  la même, --sans-garde (cassure)                         : pas d'erreur
  G-T     fichier sain, --casser-garde troncon:5                  : erreur nommée
  G-Ts    la même, --sans-garde (cassure)                         : pas d'erreur
  G-L     fichier sain, --casser-garde ligne:3                    : erreur nommée sur la ligne
  G-Ls    la même, --sans-garde (cassure)                         : pas d'erreur
  G-=a/b  fichier sain, garde puis sans garde                     : même texte au bit ; compteurs
  G-E2    copie E2 du lot E                                       : une erreur nommée (publiée)

Commande : python -I -X utf8 temoin_garde.py --exe <troncons.exe> --journal <j.json> [--cas …]
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

TRC = "~/dev/modeles/trc"
INVITE = "~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt"


def passe(exe, modele, *extra):
    with tempfile.TemporaryDirectory() as d:
        j = pathlib.Path(d) / "j.json"
        args = [exe, "generer", "--modele", modele, "--vocab", f"{TRC}/gpt-oss-20b.vocab.gguf", "--invite", INVITE,
                "-n", "32", "--flux", "--repos", "0", "--sans-vram", "--journal", str(j), *extra]
        r = subprocess.run(args, capture_output=True, timeout=900)
        err = r.stderr.decode("utf-8", "replace").strip().splitlines()
        jj = json.loads(j.read_text(encoding="utf-8")) if j.exists() else None
        je = pathlib.Path(str(j) + ".erreur.json")
        erreur_journal = json.loads(je.read_text(encoding="utf-8"))["erreur"] if je.exists() else None
    v = {"commande": " ".join(args[1:]).replace(str(j), "<journal>"), "code": r.returncode,
         "erreur": next((x for x in reversed(err) if "erreur" in x), None), "erreur_journal": erreur_journal,
         "temoin": [x for x in err if "témoin de la garde" in x]}
    if jj:
        g = jj["compteurs_total"]
        v.update({"texte_sha256": jj["texte_sha256"], "ouverture_s": jj["moteur"]["ouverture_s"],
                  "garde": jj["moteur"].get("garde"), "garde_troncons": g.get("garde_troncons"),
                  "lectures_troncons": g.get("lectures_troncons"), "garde_lignes": g.get("garde_lignes"),
                  "lectures_enchassement": g.get("lectures_enchassement"), "garde_octets": g.get("garde_octets"),
                  "garde_attente_s": g.get("garde_attente_s"), "garde_octets_ouverture": g.get("garde_octets_ouverture"),
                  "octets_lus_processus": jj["disque"].get("processus"), "octets_comptes_moteur": jj["disque"].get("octets_comptes_moteur")})
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--journal", required=True)
    ap.add_argument("--cas", default="G-XO3,G-XO3s,G-T,G-Ts,G-L,G-Ls,G-=a,G-=b,G-E2")
    a = ap.parse_args()
    sain, xo3, e2 = f"{TRC}/gpt-oss-20b.trc", f"{TRC}/casse/gpt-oss-20b-casse-O3.trc", f"{TRC}/casse/gpt-oss-20b-casse-E2.trc"
    plan = {"G-XO3": (xo3,), "G-XO3s": (xo3, "--sans-garde"), "G-T": (sain, "--casser-garde", "troncon:5"),
            "G-Ts": (sain, "--casser-garde", "troncon:5", "--sans-garde"), "G-L": (sain, "--casser-garde", "ligne:3"),
            "G-Ls": (sain, "--casser-garde", "ligne:3", "--sans-garde"), "G-=a": (sain,), "G-=b": (sain, "--sans-garde"),
            "G-E2": (e2,)}
    res = {}
    for c in a.cas.split(","):
        res[c] = passe(a.exe, *plan[c])
        print(c, json.dumps({k: res[c].get(k) for k in ("code", "erreur", "texte_sha256", "garde_troncons", "lectures_troncons", "garde_lignes")}, ensure_ascii=False), flush=True)

    def nomme(c, motif):
        r = res.get(c)
        return r is not None and r["code"] == 1 and r["erreur"] is not None and motif in r["erreur"]

    def libre(c):
        r = res.get(c)
        return r is not None and r["code"] == 0

    v = {}
    if "G-XO3" in res:
        v["G-XO3"] = "tient" if nomme("G-XO3", "garde de production : couche 0, expert 30") else "tombe"
    if "G-XO3s" in res:
        v["G-XO3s (cassure)"] = "tombe comme attendu" if libre("G-XO3s") else "ne tombe pas"
    if "G-T" in res:
        v["G-T"] = "tient" if nomme("G-T", "garde de production : couche") else "tombe"
    if "G-Ts" in res:
        v["G-Ts (cassure)"] = "tombe comme attendu" if libre("G-Ts") else "ne tombe pas"
    if "G-L" in res:
        v["G-L"] = "tient" if nomme("G-L", "ligne d'enchâssement du jeton") else "tombe"
    if "G-Ls" in res:
        v["G-Ls (cassure)"] = "tombe comme attendu" if libre("G-Ls") else "ne tombe pas"
    if "G-=a" in res and "G-=b" in res:
        ra, rb = res["G-=a"], res["G-=b"]
        ok = libre("G-=a") and libre("G-=b") and ra["texte_sha256"] == rb["texte_sha256"] \
            and ra["garde_troncons"] == ra["lectures_troncons"] and ra["garde_lignes"] == ra["lectures_enchassement"] \
            and rb["garde_troncons"] == 0
        v["G-="] = "tient" if ok else "tombe"
    if "G-E2" in res:
        v["G-E2"] = res["G-E2"]["erreur"]
    j = {"outil": "temoin_garde.py", "date": datetime.datetime.now().isoformat(timespec="seconds"), "exe": a.exe,
         "exe_sha256": hashlib.sha256(pathlib.Path(a.exe).read_bytes()).hexdigest(), "cas": res, "verdicts": v}
    pathlib.Path(a.journal).write_text(json.dumps(j, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(v, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
