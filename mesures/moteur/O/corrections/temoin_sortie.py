"""Témoin des constats G1 et G2 de l'épreuve J1 : le programme rend-il la main, avec son erreur,
sans laisser d'enfant vivant ?

Trois cas, chacun lancé comme le font les pilotes (sorties en tuyaux, `communicate`) :
  absent    : `generer` sur un fichier .trc qui n'existe pas (erreur après le départ de
              l'échantillonneur de VRAM, avant le moteur) ;
  corrompu  : `generer --flux` sur la copie corrompue du lot E (erreur fatale nommée au milieu du
              préremplissage, travail en file sur la carte, lectures en vol) ;
  tue       : `generer` sain sur le 20b, tué de l'extérieur (TerminateProcess) 3 s après la
              naissance de son enfant nvidia-smi.

Mesures : horloge murale jusqu'au retour de `communicate` (attente des tuyaux fermés), code de
sortie, dernières lignes de la sortie d'erreur, enfants `nvidia-smi` encore vivants dont le parent
est le processus lancé (Win32_Process.ParentProcessId). Les enfants trouvés sont arrêtés ensuite :
ils sont nés d'un processus lancé par ce témoin.

Seuils (déclarés dans seuils-declares.md avant la première passe) : pour « absent » et « corrompu »,
retour en moins de 30 s, code 1, l'erreur écrite ; pour les trois cas, 0 enfant vivant 2 s après le
retour. Le délai d'attente de `communicate` est de 90 s : au-delà, le cas est noté « bloqué ».

Commande : python -I -X utf8 temoin_sortie.py --exe <troncons.exe> --journal <j.json> [--cas a,b,c]
"""
import argparse
import datetime
import json
import pathlib
import subprocess
import sys
import threading
import time

TRC = "~/dev/modeles/trc"
INVITE = "~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt"
DELAI = 90.0


def enfants_smi(pid):
    """Les nvidia-smi vivants dont le parent enregistré est `pid`."""
    cmd = ("Get-CimInstance Win32_Process -Filter \"Name='nvidia-smi.exe'\" | "
           "ForEach-Object { \"$($_.ProcessId) $($_.ParentProcessId) $($_.CommandLine)\" }")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    v = []
    for ligne in r.stdout.splitlines():
        parts = ligne.strip().split(" ", 2)
        if len(parts) >= 2 and parts[1].isdigit() and int(parts[1]) == pid:
            v.append({"pid": int(parts[0]), "ligne": parts[2] if len(parts) > 2 else ""})
    return v


def arreter(pid):
    subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)


def cas(exe, nom):
    if nom == "absent":
        args = [exe, "generer", "--modele", f"{TRC}/n-existe-pas.trc", "--vocab", f"{TRC}/gpt-oss-20b.vocab.gguf",
                "--invite", INVITE, "-n", "4", "--repos", "0"]
    elif nom == "corrompu":
        args = [exe, "generer", "--modele", f"{TRC}/casse/gpt-oss-20b-casse-E2.trc", "--vocab",
                f"{TRC}/gpt-oss-20b.vocab.gguf", "--invite", INVITE, "-n", "32", "--flux", "--repos", "0"]
    elif nom == "tue":
        args = [exe, "generer", "--modele", f"{TRC}/gpt-oss-20b.trc", "--vocab", f"{TRC}/gpt-oss-20b.vocab.gguf",
                "--invite", INVITE, "-n", "256", "--repos", "0"]
    else:
        raise SystemExit(f"cas inconnu {nom}")
    t0 = time.perf_counter()
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Les tuyaux sont vidés par deux fils dès le départ (un tuyau plein bloquerait l'enfant : défaut
    # de la passe 2 du cas « tué », journal gardé) ; chaque fil finit quand son tuyau se ferme,
    # c'est-à-dire quand le DERNIER détenteur de sa poignée d'écriture disparaît.
    recu = {"sortie": bytearray(), "erreur": bytearray()}
    fini = {}

    def vider(nom_t, flux):
        for morceau in iter(lambda: flux.read1(65536), b""):
            recu[nom_t] += morceau
        fini[nom_t] = time.perf_counter() - t0

    fils = [threading.Thread(target=vider, args=("sortie", p.stdout), daemon=True),
            threading.Thread(target=vider, args=("erreur", p.stderr), daemon=True)]
    for f in fils:
        f.start()
    tue_a = None
    if nom == "tue":
        # tué 3 s après la naissance de son enfant nvidia-smi (l'échantillonneur a démarré) ; la
        # passe 1 le tuait à 8 s, avant ce départ : le cas ne prouvait rien (journal gardé)
        while time.perf_counter() - t0 < 120.0 and not enfants_smi(p.pid):
            time.sleep(0.5)
        time.sleep(3.0)
        tue_a = time.perf_counter() - t0
        p.kill()
    code = p.wait()
    sortie_processus = time.perf_counter() - t0
    for f in fils:
        f.join(timeout=max(0.0, DELAI - (time.perf_counter() - t0)))
    bloque = any(f.is_alive() for f in fils)
    mur = time.perf_counter() - t0
    time.sleep(2.0)
    orphelins = enfants_smi(p.pid)
    for o in orphelins:
        arreter(o["pid"])
    for f in fils:
        f.join(timeout=30)
    lignes = bytes(recu["erreur"]).decode("utf-8", "replace").strip().splitlines()
    return {"cas": nom, "commande": " ".join(args), "pid": p.pid, "sortie_processus_s": round(sortie_processus, 3),
            "mur_s": round(mur, 3), "tuyaux_fermes_s": fini, "tue_a_s": tue_a,
            "bloque_au_dela_de_s": DELAI if bloque else None, "code": code,
            "erreur_dernieres_lignes": lignes[-4:], "orphelins_smi": orphelins}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--journal", required=True)
    ap.add_argument("--cas", default="absent,corrompu,tue")
    a = ap.parse_args()
    res = []
    for nom in a.cas.split(","):
        r = cas(a.exe, nom)
        print(json.dumps(r, ensure_ascii=False), flush=True)
        res.append(r)
    verdicts = {}
    for r in res:
        ok = not r["orphelins_smi"] and r["bloque_au_dela_de_s"] is None
        if r["cas"] in ("absent", "corrompu"):
            ok = ok and r["mur_s"] < 30.0 and r["code"] == 1 and any("erreur" in x for x in r["erreur_dernieres_lignes"])
        verdicts[r["cas"]] = "tient" if ok else "tombe"
    j = {"outil": "temoin_sortie.py", "date": datetime.datetime.now().isoformat(timespec="seconds"),
         "exe": a.exe, "cas": res, "verdicts": verdicts}
    pathlib.Path(a.journal).write_text(json.dumps(j, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(verdicts, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
