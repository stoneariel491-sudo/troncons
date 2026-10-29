"""Bloc 4 de seuils-declares.md : la passe figée de l'épreuve (G1) rejouée sous la même charge.

Charge : la passe numpy f64 du juge sur le 120b (`mesures/moteur/epreuve-J1/gptoss_numpy.py`,
fenêtre 0, 511 positions ; ≈ 17 min, 61 Go lus), lancée d'abord ; 60 s après, `troncons evaluer --flux
--brut` sur les 10 fenêtres du 120b brut. La sortie d'erreur du moteur est écrite au fil de l'eau dans
un fichier (battements, erreur). Au-delà de `--delai` minutes, le moteur est déclaré figé et arrêté
(processus lancé par ce script) ; la passe numpy est attendue jusqu'au bout.

Commande : python -I -X utf8 rejouer_g1.py --exe <troncons.exe> --nom <étiquette> --journal <j.json> [--delai 30]
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import time

ICI = pathlib.Path(__file__).resolve().parent
NUMPY = ICI.parent.parent / "epreuve-J1" / "gptoss_numpy.py"
GGUF120 = "~/dev/modeles/gguf/gpt-oss-120b-MXFP4.gguf"
BASE_KLD = "~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld"
TRC = "~/dev/modeles/trc"
SORTIES = pathlib.Path("~/dev/essais/troncons/lot-O/ronde/g1")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for m in iter(lambda: f.read(1 << 24), b""):
            h.update(m)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--nom", required=True)
    ap.add_argument("--journal", required=True)
    ap.add_argument("--delai", type=float, default=30.0)
    a = ap.parse_args()
    SORTIES.mkdir(parents=True, exist_ok=True)
    b = SORTIES / a.nom
    r = {"outil": "rejouer_g1.py", "exe": a.exe, "exe_sha256": sha(a.exe), "debut": datetime.datetime.now().isoformat(timespec="seconds")}
    alim = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Battery).BatteryStatus"],
                          capture_output=True, text=True).stdout.strip()
    r["alimentation_avant"] = alim
    t0 = time.time()
    np_cmd = [sys.executable, "-I", "-X", "utf8", str(NUMPY), GGUF120, BASE_KLD, str(b) + "-numpy.npz", "--fenetre", "0", "--positions", "511"]
    charge = subprocess.Popen(np_cmd, stdout=open(str(b) + "-numpy.out", "wb"), stderr=open(str(b) + "-numpy.err", "wb"))
    r["charge"] = {"commande": np_cmd, "pid": charge.pid}
    time.sleep(60)
    m_cmd = [a.exe, "evaluer", "--modele", f"{TRC}/gpt-oss-120b-brut.trc", "--base", BASE_KLD, "--fenetres", "10", "--positions", "512",
             "--flux", "--brut", "--sortie", str(b) + ".kld", "--empreintes", str(b) + "-empreintes.csv", "--journal", str(b) + ".json"]
    err = open(str(b) + ".stderr.log", "wb")
    t1 = time.time()
    moteur = subprocess.Popen(m_cmd, stdout=open(str(b) + ".stdout.txt", "wb"), stderr=err)
    r["moteur"] = {"commande": m_cmd, "pid": moteur.pid, "depart_apres_charge_s": round(t1 - t0, 1)}
    fige = False
    try:
        moteur.wait(timeout=a.delai * 60)
    except subprocess.TimeoutExpired:
        fige = True
        subprocess.run(["taskkill", "/PID", str(moteur.pid), "/F"], capture_output=True)
        moteur.wait()
    err.close()
    r["moteur"].update({"mur_s": round(time.time() - t1, 1), "code": moteur.returncode, "fige_arrete": fige})
    lignes = pathlib.Path(str(b) + ".stderr.log").read_bytes().decode("utf-8", "replace").splitlines()
    r["moteur"]["battements"] = sum("préremplissage par flux, couche" in x for x in lignes)
    r["moteur"]["fenetres_finies"] = sum("troncons evaluer : fenêtre" in x for x in lignes)
    r["moteur"]["erreur"] = next((x for x in reversed(lignes) if "troncons : erreur" in x), None)
    r["moteur"]["dernieres_lignes"] = lignes[-6:]
    jj = pathlib.Path(str(b) + ".json")
    if jj.exists():
        j = json.loads(jj.read_text(encoding="utf-8"))
        r["moteur"]["compteurs"] = {k: j["compteurs"].get(k) for k in ("flux_conflits_evites", "garde_troncons", "lectures_troncons", "garde_attente_s")}
        r["moteur"]["ppl"] = j.get("ppl_positions_notees")
        r["moteur"]["kld_sha256"] = sha(str(b) + ".kld")
        r["moteur"]["kld_egal_lot_O"] = r["moteur"]["kld_sha256"].startswith("5b212fe9")
    charge.wait()
    r["charge"].update({"mur_s": round(time.time() - t0, 1), "code": charge.returncode})
    r["fin"] = datetime.datetime.now().isoformat(timespec="seconds")
    r["alimentation_apres"] = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Battery).BatteryStatus"],
                                             capture_output=True, text=True).stdout.strip()
    pathlib.Path(a.journal).write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(r["moteur"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
