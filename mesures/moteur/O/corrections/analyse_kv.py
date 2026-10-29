"""Bloc 5 de seuils-declares.md (M5) : le cache KV en f32 contre f16, jugé contre la vérité f64 du juge.

Outils du juge appelés tels quels (`comparer_kld.py`, `comparer_invite.py`, `comparer_routage.py`), plus
le critère de queue proposé par le juge (part des positions de KL > 0,1, KL au 99ᵉ centile), calculé ici
par position avec la lecture des `.kld` du juge (`comparer_kld.Kld`, `kl`).

Commande : python -I -X utf8 analyse_kv.py <seance justesse.json> <seance vitesse.json> <verdicts.json> --csv <c.csv>
"""
import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
JUGE = ICI.parent.parent / "epreuve-J1"
sys.path.insert(0, str(JUGE))
from comparer_kld import Kld, kl  # noqa: E402

NP = pathlib.Path("~/dev/essais/troncons/epreuve-J1/numpy")
J = ICI / "journaux"


def sortie(p, cle):
    c = p["commande"]
    return c[c.index(cle) + 1]


def outil(*args):
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", *[str(x) for x in args]], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise SystemExit(r.stderr)
    return r.stdout


def queue(kls):
    k = np.asarray(kls)
    return {"n": int(k.size), "kl_moyenne": float(k.mean()), "part_kl_sup_0_1": float((k > 0.1).mean()),
            "kl_p99": float(np.percentile(k, 99)), "kl_max": float(k.max())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("justesse")
    ap.add_argument("vitesse")
    ap.add_argument("verdicts")
    ap.add_argument("--csv")
    a = ap.parse_args()
    s = json.load(open(a.justesse, encoding="utf-8"))
    par = {p["nom"]: p for p in s["passes_faites"]}
    v = {"seance": s["seance"], "exe_sha256": s.get("exe_sha256")}
    lignes = ["cas,position,kl_f16,kl_f32"]
    # 1. Fenêtre 0, 120b et 20b
    for m in ("120b", "20b"):
        g, k = par[f"E0g{m[:-1]}"], par[f"E0k{m[:-1]}"]
        jr = J / f"m5-kl-f0-{m}.json"
        outil(JUGE / "comparer_kld.py", NP / f"np-{m}-f0-openai.npz", jr, "--fichier", f"f16={sortie(g, '--sortie')}",
              "--fichier", f"f32={sortie(k, '--sortie')}")
        r = json.load(open(jr, encoding="utf-8"))
        z = np.load(NP / f"np-{m}-f0-openai.npz")
        pos, lp = z["positions"].tolist(), z["log_p"]
        kf = {n: Kld(sortie(p, "--sortie")) for n, p in (("f16", g), ("f32", k))}
        kls = {n: [kl(lp[i].astype(np.float64), kf[n].log_p(0, p)) for i, p in enumerate(pos)] for n in kf}
        for i, p in enumerate(pos):
            lignes.append(f"f0-{m},{p},{kls['f16'][i]:.10e},{kls['f32'][i]:.10e}")
        v[f"f0_{m}"] = {"comparer_kld": r["fichiers"], "queue_f16": queue(kls["f16"]), "queue_f32": queue(kls["f32"]),
                        "H5c_tient": r["fichiers"]["f32"]["kl_moyenne"] <= r["fichiers"]["f16"]["kl_moyenne"]
                        and r["fichiers"]["f32"]["meme_premier_choix"] >= r["fichiers"]["f16"]["meme_premier_choix"]}
    # 2. Invite de 708 jetons (120b) : argmax de chaque position, KL des positions notées, queue avant et après 512
    zi = np.load(NP / "np-120b-invite-toutes.npz")
    for n, nom in (("f16", "Ig120"), ("f32", "Ik120")):
        p = par[nom]
        jr = J / f"m5-invite-120b-{n}.json"
        outil(JUGE / "comparer_invite.py", NP / "np-120b-invite-toutes.npz", sortie(p, "--empreintes"), sortie(p, "--sortie"), jr)
        r = json.load(open(jr, encoding="utf-8"))
        k = Kld(sortie(p, "--sortie"))
        pos = [int(x) for x in zi["positions"]]
        kls = [(q, kl(zi["log_p"][i].astype(np.float64), k.log_p(0, q))) for i, q in enumerate(pos) if q < k.n_ctx - 1]
        for q, x in kls:
            lignes.append(f"invite-{n},{q},{x if n == 'f16' else ''},{x if n == 'f32' else ''}")
        v[f"invite_{n}"] = {"comparer_invite": r, "queue_avant_512": queue([x for q, x in kls if q < 512]),
                            "queue_512_et_plus": queue([x for q, x in kls if q >= 512])}
    v["H5a"] = {"argmax_707_f32": v["invite_f32"]["comparer_invite"]["derniere_position"]["troncons_argmax"],
                "argmax_707_f16": v["invite_f16"]["comparer_invite"]["derniere_position"]["troncons_argmax"],
                "verite": v["invite_f32"]["comparer_invite"]["derniere_position"]["verite_argmax"]}
    v["H5a"]["tient"] = v["H5a"]["argmax_707_f32"] == v["H5a"]["verite"]
    # 3. Routage sur l'invite (boucle de pas, KV f32) contre la vérité
    jr = J / "m5-routage-120b-f32.json"
    outil(JUGE / "comparer_routage.py", NP / "np-120b-invite-toutes.npz", sortie(par["IkB120"], "--trace"), jr)
    r = json.load(open(jr, encoding="utf-8"))
    t = r["accord_par_tranche"]
    avant = (t["0-256"] * 256 + t["256-512"] * 256) / 512
    apres = (t["512-600"] * 88 + t["600-708"] * 108) / 196
    v["H5b"] = {"accord_0_511": avant, "accord_512_et_plus": apres, "seuils": [0.983, 0.969], "f16_juge": [0.969, 0.931],
                "tient": avant >= 0.983 and apres >= 0.969, "accord_par_tranche": t}
    # 4. Le texte de C12 (séance vitesse) : premier jeton et empreinte
    sv = json.load(open(a.vitesse, encoding="utf-8"))
    textes = {}
    for p in sv["passes_faites"]:
        if p["sorte"] != "troncons":
            continue
        jj = json.load(open(sortie(p, "--journal"), encoding="utf-8"))
        textes.setdefault(p["nom"], set()).add((jj["texte_sha256"][:16], jj["jetons"][0]))
    v["C12_textes"] = {n: sorted(x) for n, x in textes.items()}
    json.dump(v, open(a.verdicts, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if a.csv:
        pathlib.Path(a.csv).write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(json.dumps(v, ensure_ascii=False, indent=1)[:5000])


if __name__ == "__main__":
    main()
