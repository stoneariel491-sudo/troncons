"""Pilote des séances de la ronde de corrections J1 (blocs 3, 5 et 6 de seuils-declares.md).

L'instrument est celui du juge de l'épreuve (`mesures/moteur/epreuve-J1/pilote_epreuve.py`, importé
tel quel, rien n'y est changé) : pointes de mémoire tenues par le système et lues sur la poignée après
la sortie, compteurs d'E/S du processus, mémoire disponible de la machine, VRAM, alimentation avant et
après, processus étrangers. Seuls changent le binaire (copie figée de la ronde), les passes et l'ordre.

Commande : python -I -X utf8 pilote_ronde.py --seance <nom> --ordre vitesse|justesse|base [--seulement i,j]
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import sys

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent.parent / "epreuve-J1"))
import pilote_epreuve as P  # noqa: E402

EXE = "~/dev/cibles/troncons-O/ronde/troncons.exe"
P.TRONCONS = EXE
P.SORTIES = pathlib.Path("~/dev/essais/troncons/lot-O/ronde")
P.JOURNAUX = ICI / "journaux" / "seances"
TRC, GGUF, BASE_KLD = P.TRC, P.GGUF, P.BASE_KLD
INVITE_KLD = "~/dev/essais/troncons/epreuve-J1/base-invite-708.kld"


def troncons(modele, *extra):
    return [EXE, "mesurer", "--modele", f"{TRC}/gpt-oss-{modele}.trc", "--vocab", f"{TRC}/gpt-oss-{modele}.vocab.gguf",
            "--invite", P.INVITE, "-n", "256", "--flux", *extra]


def evaluer(modele, base, positions, *extra):
    return [EXE, "evaluer", "--modele", f"{TRC}/gpt-oss-{modele}.trc", "--base", base, "--fenetres", "1",
            "--positions", str(positions), *extra]


PASSES = {
    "D120": ("disque", [EXE, "disque", "--modele", f"{TRC}/gpt-oss-120b.trc", "--n", "1500", "--graine", "20261016",
                        "--profondeur", "4"]),
    "T120g": ("troncons", troncons("120b")),
    "T120s": ("troncons", troncons("120b", "--sans-garde")),
    "T120k": ("troncons", troncons("120b", "--kv-f32")),
    "E0g120": ("evaluer", evaluer("120b", BASE_KLD, 512, "--flux")),
    "E0k120": ("evaluer", evaluer("120b", BASE_KLD, 512, "--flux", "--kv-f32")),
    "Ig120": ("evaluer", evaluer("120b", INVITE_KLD, 708, "--flux")),
    "Ik120": ("evaluer", evaluer("120b", INVITE_KLD, 708, "--flux", "--kv-f32")),
    "IkB120": ("evaluer", evaluer("120b", INVITE_KLD, 708, "--kv-f32", "--trace",
                                  "~/dev/essais/troncons/lot-O/ronde/ikb120.trace")),
    "E0g20": ("evaluer", evaluer("20b", BASE_KLD, 512, "--flux")),
    "E0k20": ("evaluer", evaluer("20b", BASE_KLD, 512, "--flux", "--kv-f32")),
    "Lw": ("llama", P.llama("-t", "10")),
    "L6": ("llama", P.llama("-t", "6")),
    "L10": ("llama", P.llama("-t", "10")),
    "L12": ("llama", P.llama("-t", "12")),
    "L16": ("llama", P.llama("-t", "16")),
    "Lm": ("llama", P.llama("-ngl", "99", "--n-cpu-moe", "34", "--fit", "off", "-t", "10")),
}
ORDRES = {
    # bloc 3 (garde : A B B A) puis bloc 5 (KV f32 : B A A B), précédés de deux D dont la première est jetée
    "vitesse": ["D120", "D120", "T120g", "T120s", "T120s", "T120g", "T120k", "T120g", "T120g", "T120k"],
    "justesse": ["E0g120", "E0k120", "Ig120", "Ik120", "IkB120", "E0g20", "E0k20"],
    "base": ["Lw", "L6", "L10", "L12", "L16", "Lm", "Lm", "L16", "L12", "L10", "L6"],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seance", required=True)
    ap.add_argument("--ordre", required=True, choices=list(ORDRES))
    ap.add_argument("--seulement")
    a = ap.parse_args()
    if hashlib.sha256(pathlib.Path(P.INVITE).read_bytes()).hexdigest() != P.INVITE_SHA256:
        sys.exit("invite : empreinte inattendue")
    P.PASSES = PASSES
    P.JOURNAUX.mkdir(parents=True, exist_ok=True)
    ordre = ORDRES[a.ordre]
    rangs = range(len(ordre)) if not a.seulement else [int(x) for x in a.seulement.split(",")]
    chemin = P.JOURNAUX / f"{a.seance}.json"
    tout = json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else \
        {"seance": a.seance, "ordre": ordre, "exe": EXE, "exe_sha256": hashlib.sha256(pathlib.Path(EXE).read_bytes()).hexdigest(),
         "passes": PASSES, "passes_faites": []}
    for i in rangs:
        nom = ordre[i]
        print(f"{datetime.datetime.now():%H:%M:%S} passe {i} {nom}", flush=True)
        r = P.une_passe(nom, i, a.seance)
        tout["passes_faites"].append(r)
        chemin.write_text(json.dumps(tout, ensure_ascii=False, indent=1), encoding="utf-8")
        if "echec" in r:
            print(f"   ÉCHEC code {r['code_retour']} mur {r['mur_s']:.0f} s : {r['echec'][-300:]}", flush=True)
            continue
        print(f"   code {r['code_retour']} mur {r['mur_s']:.0f} s gen {r.get('gen_jetons_s')} pre {r.get('prefill_jetons_s')} "
              f"texte {str(r.get('texte_sha256'))[:8]} ET {r['memoire_os'] and r['memoire_os']['pointe_ensemble_travail'] / 1e6:.1f} Mo "
              f"VRAM {r['vram_pointe_mio']} alim {r['alimentation_avant']}/{r['alimentation_apres']} etrangers {r['etrangers_avant']}",
              flush=True)


if __name__ == "__main__":
    main()
