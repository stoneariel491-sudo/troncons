"""La séance de vitesse du juge : trois fichiers par modèle, ordre équilibré, machine calme relevée.

Seuils : mesures/genome/construction/juge/00-seuils-declares.md, J-V1 à J-V4 (commit 1f5fe0f).

  python -I -X utf8 seance_juge.py 120b [--plan ABRRBAABRRBA] [--sans-disque]
  python -I -X utf8 seance_juge.py 20b
  python -I -X utf8 seance_juge.py analyse <120b|20b>

120b : A = gpt-oss-120b.trc (v1.0), B = gpt-oss-120b-v12.trc, R = compagnon frontière (--rapide) ;
       réglages du J1 : mesurer --flux --emplacements 326, invite wiki-3000, 256 jetons, --repos 10.
20b  : A = gpt-oss-20b.trc (v1.0), B = gpt-oss-20b-v12.trc, R = compagnon synonyme λ = 0 (--rapide) ;
       réglages de la séance s2 du lot B : mesurer, sans --flux, emplacements par défaut, 256 jetons.
Étage disque d'abord (troncons disque --n 1500 --graine 20261017 --repos 5), ordre A B R R B A.
Avant et après chaque passe : secteur, et relevé des autres flux (plus de 5 % d'un cœur ou plus de 8 Mo
lus en 3 s : la passe est « SOUS CHARGE » et ne conclut pas) ; départ sur deux relevés vides à une
minute d'écart. Verrou de la carte pris (« séance de vitesse »), rafraîchi avant chaque passe.
"""
import hashlib
import json
import os
import pathlib
import statistics
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import verrou_juge  # noqa: E402

DEPOT = pathlib.Path(__file__).resolve().parents[4]
JOURNAUX = DEPOT / "mesures" / "genome" / "construction" / "juge" / "vitesse"
TRONCONS = pathlib.Path("~/dev/cibles/troncons-juge/release/troncons.exe")
MODELES = pathlib.Path("~/dev/modeles/trc")
SYN = pathlib.Path("~/dev/essais/troncons/genome/synonyme/trc")
INVITE = pathlib.Path("~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt")
INVITE_SHA = "eadbe87e3d3ce6c81035a2a4d83f898d887ce7d76bd4336555d615ee0522ceff"
FICHIERS = {
    "120b": {"A": MODELES / "gpt-oss-120b.trc", "B": MODELES / "gpt-oss-120b-v12.trc", "R": SYN / "gpt-oss-120b-frontiere.rapide.trc"},
    "20b": {"A": MODELES / "gpt-oss-20b.trc", "B": MODELES / "gpt-oss-20b-v12.trc", "R": SYN / "gpt-oss-20b-synonyme-l0.rapide.trc"},
}
VOCAB = {"120b": MODELES / "gpt-oss-120b.vocab.gguf", "20b": MODELES / "gpt-oss-20b.vocab.gguf"}
EXCLUS = ("http.server", "blender-mcp", "blender_mcp")
NOMS = ("python", "trc-", "cargo", "rustc", "juge", "genome-capture", "troncons", "llama", "nvcc", "banc-")

PS_RELEVE = r"""
$a = Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine,KernelModeTime,UserModeTime,ReadTransferCount
Start-Sleep -Seconds 3
$b = Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine,KernelModeTime,UserModeTime,ReadTransferCount
@{a=$a; b=$b} | ConvertTo-Json -Depth 3 -Compress
"""


def maintenant():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def secteur():
    r = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Battery).BatteryStatus"], capture_output=True, text=True)
    return r.stdout.strip()


def descendants(pids_racines, procs):
    enfants = {}
    for p in procs:
        enfants.setdefault(p["ParentProcessId"], []).append(p["ProcessId"])
    vus = set(pids_racines)
    pile = list(pids_racines)
    while pile:
        x = pile.pop()
        for c in enfants.get(x, []):
            if c not in vus:
                vus.add(c)
                pile.append(c)
    return vus


def autres_lourds():
    """Les processus des autres flux qui prennent plus de 5 % d'un cœur ou lisent plus de 8 Mo en 3 s."""
    r = subprocess.run(["powershell", "-NoProfile", "-Command", PS_RELEVE], capture_output=True, text=True, encoding="utf-8", errors="replace")
    d = json.loads(r.stdout)
    a = {p["ProcessId"]: p for p in d["a"]}
    moi = descendants([os.getpid()], d["b"])
    lourds = []
    for p in d["b"]:
        pid = p["ProcessId"]
        nom = (p.get("Name") or "").lower()
        cmd = p.get("CommandLine") or ""
        if pid in moi or pid not in a or not any(n in nom for n in NOMS) or any(x in cmd for x in EXCLUS):
            continue
        q = a[pid]
        cpu = ((p["KernelModeTime"] or 0) + (p["UserModeTime"] or 0) - (q["KernelModeTime"] or 0) - (q["UserModeTime"] or 0)) * 1e-7 / 3.0
        lu = (p["ReadTransferCount"] or 0) - (q["ReadTransferCount"] or 0)
        if cpu > 0.05 or lu > 8e6:
            lourds.append({"pid": pid, "nom": p["Name"], "coeur": round(cpu, 3), "octets_lus_3s": lu, "commande": cmd[:160]})
    return lourds


def attendre_calme(journal):
    vides = 0
    debut = time.time()
    while vides < 2:
        l = autres_lourds()
        if l:
            vides = 0
            journal(f"pas calme : {[(x['nom'], x['coeur'], x['octets_lus_3s']) for x in l]}")
            if time.time() - debut > 3 * 3600:
                raise RuntimeError("trois heures sans calme")
            time.sleep(60)
        else:
            vides += 1
            journal(f"relevé vide {vides}/2")
            if vides < 2:
                time.sleep(60)


def age_h(ch):
    return (time.time() - pathlib.Path(ch).stat().st_mtime) / 3600


def seance(modele, plan, avec_disque=True):
    JOURNAUX.mkdir(parents=True, exist_ok=True)
    nom_s = f"seance-{modele}"
    log = open(JOURNAUX / f"{nom_s}.log", "a", encoding="utf-8")

    def journal(t):
        ligne = f"[{maintenant()}] {t}"
        print(ligne, flush=True)
        log.write(ligne + "\n")
        log.flush()
    if hashlib.sha256(INVITE.read_bytes()).hexdigest() != INVITE_SHA:
        raise RuntimeError("invite : empreinte inattendue")
    raison = f"séance de vitesse ABBA {nom_s}, seance_juge.py"
    verrou_juge.prendre(raison)
    journal(f"verrou pris : {raison}")
    resume = {"seance": nom_s, "debut": maintenant(), "plan": plan, "fichiers": {k: str(v).replace("\\", "/") for k, v in FICHIERS[modele].items()},
              "age_h_au_depart": {k: age_h(v) for k, v in FICHIERS[modele].items()}, "passes": [], "disque": []}
    try:
        attendre_calme(journal)
        passes = []
        if avec_disque:
            passes += [("disque", i, l) for i, l in enumerate("ABRRBA", 1)]
        passes += [("moteur", i, l) for i, l in enumerate(plan, 1)]
        for sorte, i, l in passes:
            verrou_juge.prendre(raison)
            al = secteur()
            if al != "2":
                journal(f"pas sur secteur ({al}) : arrêt")
                resume["arret"] = "secteur"
                break
            charge_avant = autres_lourds()
            f = FICHIERS[modele][l]
            nom = f"{modele}-{sorte}-{i:02d}-{l}"
            js = JOURNAUX / f"{nom}.json"
            if sorte == "disque":
                c = [str(TRONCONS), "disque", "--modele", str(f), "--n", "1500", "--graine", "20261017", "--repos", "5", "--journal", str(js)]
            else:
                c = [str(TRONCONS), "mesurer", "--modele", str(f), "--vocab", str(VOCAB[modele]), "--invite", str(INVITE), "-n", "256",
                     "--repos", "10", "--sortie", str(JOURNAUX / f"{nom}.txt"), "--journal", str(js)]
                if modele == "120b":
                    c += ["--flux", "--emplacements", "326"]
                if l == "R":
                    c.append("--rapide")
            t0 = time.time()
            with open(JOURNAUX / f"{nom}.log", "w", encoding="utf-8") as fl:
                r = subprocess.run(c, stdout=fl, stderr=subprocess.STDOUT)
            duree = time.time() - t0
            charge_apres = autres_lourds()
            p = {"sorte": sorte, "passe": i, "lettre": l, "fichier": str(f).replace("\\", "/"), "commande": " ".join(c).replace("\\", "/"),
                 "code": r.returncode, "secondes": duree, "secteur": al, "charge_avant": charge_avant, "charge_apres": charge_apres,
                 "sous_charge": bool(charge_avant or charge_apres), "journal": js.name}
            if r.returncode == 0 and js.exists():
                j = json.loads(js.read_text(encoding="utf-8"))
                if sorte == "disque":
                    p["go_s"] = j.get("debit_go_s") or j.get("go_s") or j.get("debit")
                    p["cles"] = sorted(j.keys())[:40]
                else:
                    cg = j.get("compteurs_generation", {})
                    p.update({"generation_jetons_s": j.get("generation_jetons_s"), "prefill_jetons_s": j.get("prefill_jetons_s"),
                              "texte_sha256": j.get("texte_sha256"), "jetons_sha256": hashlib.sha256(json.dumps(j.get("jetons")).encode()).hexdigest(),
                              "octets_troncons_par_pas": cg.get("octets_lus_troncons", 0) / max(cg.get("pas", 1), 1),
                              "h_vram": cg.get("h_vram"), "emplacements": cg.get("emplacements"), "s_lectures": cg.get("s_lectures"),
                              "s_pas": cg.get("s_pas"), "defauts_par_pas": cg.get("defauts_disque", 0) / max(cg.get("pas", 1), 1),
                              "memoire_pointe": j.get("memoire", {}).get("pointe_ensemble_travail"),
                              "octets_lus_pdh": j.get("disque", {}).get("octets_lus_pdh"), "generation_s": j.get("generation_s")})
            (resume["disque"] if sorte == "disque" else resume["passes"]).append(p)
            journal(f"{nom} : code {r.returncode}, {duree:.0f} s, {'SOUS CHARGE' if p['sous_charge'] else 'calme'} ; "
                    + (f"{p.get('go_s')} Go/s" if sorte == "disque" else f"{p.get('generation_jetons_s')} j/s, texte {str(p.get('texte_sha256'))[:12]}"))
            (JOURNAUX / f"{nom_s}.json").write_text(json.dumps(resume, ensure_ascii=False, indent=1), encoding="utf-8")
            if r.returncode != 0:
                journal("passe en échec : arrêt")
                resume["arret"] = f"passe {nom} en échec"
                break
        resume["fin"] = maintenant()
    finally:
        (JOURNAUX / f"{nom_s}.json").write_text(json.dumps(resume, ensure_ascii=False, indent=1), encoding="utf-8")
        verrou_juge.rendre()
        journal("verrou rendu")
    return resume


def ecart_relatif(v):
    return statistics.stdev(v) / statistics.mean(v) if len(v) > 1 else float("nan")


def analyse(modele):
    s = json.loads((JOURNAUX / f"seance-{modele}.json").read_text(encoding="utf-8"))
    out = {"seance": s["seance"], "passes_sous_charge": sum(p["sous_charge"] for p in s["passes"] + s["disque"])}
    par = {}
    for p in s["passes"]:
        if p["code"] == 0:
            par.setdefault(p["lettre"], []).append(p)
    med = {l: statistics.median(x["generation_jetons_s"] for x in v) for l, v in par.items()}
    sig = {l: ecart_relatif([x["generation_jetons_s"] for x in v]) for l, v in par.items()}
    sigma = max(sig.values())
    out["generation"] = {l: [x["generation_jetons_s"] for x in v] for l, v in par.items()}
    out["mediane"] = med
    out["sigma_relatif"] = sig
    out["sigma"] = sigma
    out["prefill"] = {l: statistics.median(x["prefill_jetons_s"] for x in v) for l, v in par.items()}
    out["octets_par_pas"] = {l: statistics.median(x["octets_troncons_par_pas"] for x in v) for l, v in par.items()}
    out["h_vram"] = {l: statistics.median(x["h_vram"] for x in v) for l, v in par.items()}
    out["debit_par_octet_go_s"] = {l: statistics.median(x["octets_troncons_par_pas"] * 255 / x["generation_s"] / 1e9 for x in v) for l, v in par.items()}
    out["textes"] = {l: sorted(set(x["texte_sha256"] for x in v)) for l, v in par.items()}
    out["memoire_pointe"] = {l: statistics.median(x["memoire_pointe"] for x in v) for l, v in par.items()}
    r_ba = med["B"] / med["A"]
    r_rb = med["R"] / med["B"]
    r_ra = med["R"] / med["A"]
    out["r_B_sur_A"] = r_ba
    out["r_R_sur_B"] = r_rb
    out["r_R_sur_A"] = r_ra
    out["J_V1"] = {"pas_de_regression": r_ba >= 1 - 2 * sigma, "gain_annonce": r_ba - 1 > 2 * sigma}
    ref = 2.00 if modele == "120b" else 1.241
    out["J_V2_ou_V3"] = {"rapport_publie_par_le_lot_B": ref, "seuil": ref * (1 - 2 * sigma), "gain_du_mode_tient": r_rb >= ref * (1 - 2 * sigma)}
    out["octets_B_sur_A"] = out["octets_par_pas"]["B"] / out["octets_par_pas"]["A"]
    out["toit_R_sur_B"] = out["octets_par_pas"]["B"] / out["octets_par_pas"]["R"]
    dq = {}
    for p in s["disque"]:
        if p["code"] == 0:
            dq.setdefault(p["lettre"], []).append(p["go_s"])
    out["disque_go_s"] = dq
    if all(len(v) == 2 for v in dq.values()) and dq:
        e_soi = {l: abs(v[0] - v[1]) / statistics.mean(v) for l, v in dq.items()}
        S = max(2 * max(e_soi.values()), 0.118)
        md = {l: statistics.median(v) for l, v in dq.items()}
        out["disque_e_soi"] = e_soi
        out["disque_S"] = S
        out["disque_rapports"] = {"B/A": md["B"] / md["A"], "R/A": md["R"] / md["A"], "R/B": md["R"] / md["B"]}
        out["disque_differents"] = {k: abs(v - 1) > S for k, v in out["disque_rapports"].items()}
    (JOURNAUX / f"analyse-{modele}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 2
    if a[0] == "analyse":
        analyse(a[1])
        return 0
    modele = a[0]
    plan = a[a.index("--plan") + 1] if "--plan" in a else "ABRRBAABRRBA"
    r = seance(modele, plan, avec_disque="--sans-disque" not in a)
    return 0 if "arret" not in r else 1


if __name__ == "__main__":
    sys.exit(main())
