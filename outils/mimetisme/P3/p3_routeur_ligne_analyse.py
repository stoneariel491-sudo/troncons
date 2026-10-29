"""P3, routeur biaisé en ligne : analyse des passes d'évaluation du moteur et verdicts aux seuils de 06-routeur-ligne-declare.md.

Usage : python -X utf8 p3_routeur_ligne_analyse.py [--sans-ref]
Lit mesures/mimetisme/P3/routeur-ligne/<passe>{.json,.trace,-empreintes.csv} et les .kld sous essais/.../routeur-ligne/. Écrit
mesures/mimetisme/P3/routeur-ligne/analyse.json (+ juge-kl-<passe>.{json,csv}).

Chemins (deux, indépendants, pour le chiffre principal) :
  A. `juge kl --base P0.kld --test <passe>.kld` (outil du lot R) : KL, premier choix littéral.
  B. lecteur .kld de outils/mimetisme/P3/juge/etageB_juge.py (écrit sans le code de l'étage B ni de `juge kl`) : KL, premier choix, marge de P0 ;
     le premier choix pondéré (marge de P0 >= 0,3) ne se calcule que par B (le CSV du juge n'a pas la marge).
Défauts : compteur du moteur ; `rejouer.exe` sur la trace (O3) ; LRU Python à règle de groupe (etageB_juge.lru_defauts) sur la même trace.
Rien n'est ajusté après lecture : seuils = ceux de 06-routeur-ligne-declare.md § 4.
"""
import csv
import hashlib
import json
import pathlib
import subprocess
import sys

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI / "juge"))
import etageB_juge as J  # noqa: E402

DEPOT = ICI.parents[2]
SORTIE = DEPOT / "mesures/mimetisme/P3/routeur-ligne"
LOURDS = pathlib.Path("~/dev/essais/troncons/mimetisme/P3/routeur-ligne")
BASE_F64 = pathlib.Path("~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld")
JUGE = pathlib.Path("~/dev/cibles/troncons-R/release/juge.exe")
REJOUER = pathlib.Path("~/dev/cibles/troncons-P3/release/rejouer.exe")
N = 238
S_DEFAUTS, S_KL_TIENT, S_KL_MORT, S_PC, S_MARGE = 0.10, 0.038, 0.07, 0.95, 0.3
rng = np.random.default_rng(20261027)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def lire_trace(p):
    """Trace du moteur -> tableau (T, L, 4) d'experts (ordre de la trace)."""
    lignes = [l for l in pathlib.Path(p).read_text(encoding="utf-8").splitlines() if l and not l.startswith("#") and not l.startswith("E=")]
    return np.array([[[int(x) for x in c.split()] for c in l.split("|")] for l in lignes], dtype=np.int16)


def boot(valeurs, fen, masque=None, tirages=20000):
    f = np.unique(fen)
    num = np.array([valeurs[(fen == k) & (True if masque is None else masque)].sum() for k in f], float)
    den = np.array([((fen == k) & (True if masque is None else masque)).sum() for k in f], float)
    idx = rng.integers(0, len(f), size=(tirages, len(f)))
    m = num[idx].sum(1) / den[idx].sum(1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def juge_kl(base, test, etiquette):
    j, c = SORTIE / f"juge-kl-{etiquette}.json", SORTIE / f"juge-kl-{etiquette}.csv"
    r = subprocess.run([str(JUGE), "kl", "--base", str(base), "--test", str(test), "--json", str(j), "--csv", str(c)], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"juge kl {etiquette} : {r.stderr}")
    return json.loads(j.read_text(encoding="utf-8"))["resume"], list(csv.DictReader(open(c, encoding="utf-8")))


def lecteur_kl(base, test):
    """Chemin B : KL (convention de llama.cpp), premier choix de la base et du test, marge de la base, relus des .kld."""
    rb, rt = J.LecteurKld(base), J.LecteurKld(test)
    assert (rb.n_ctx, rb.n_vocab, rb.n_fen) == (rt.n_ctx, rt.n_vocab, rt.n_fen) and (rb.jetons == rt.jetons).all()
    kl, pb, pt, marge = [], [], [], []
    i = 0
    while i < rb.n:
        k = min(J.PAQUET, rb.n - i)
        tp, cp = rb.paquet(k)
        lp = J.decoder(tp, cp)
        i1p, _, mg, _ = J.top2(lp, cp)
        p = np.exp(lp)
        tq, cq = rt.paquet(k)
        lq = J.decoder(tq, cq)
        kl.append(np.where(lp > -16.0, p * (lp - lq), 0.0).sum(axis=1))
        pb.append(i1p)
        pt.append(lq.argmax(axis=1))
        marge.append(mg)
        i += k
    return np.concatenate(kl), np.concatenate(pb), np.concatenate(pt), np.concatenate(marge), rb.notees


def passe_info(nom):
    p = SORTIE / f"{nom}-pilote.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main(avec_ref=True):
    res = {"seuils": {"defauts": S_DEFAUTS, "kl_tient": S_KL_TIENT, "kl_mort": S_KL_MORT, "premier_choix": S_PC, "marge": S_MARGE}, "passes": {}}
    pilotes = {n.stem[:-len("-pilote")]: json.loads(n.read_text(encoding="utf-8")) for n in SORTIE.glob("*-pilote.json")}
    res["pilotes"] = {n: {k: v for k, v in x.items() if k not in ("commande",)} for n, x in pilotes.items()}
    # --- témoin T0
    t0 = {}
    if "P0" in pilotes and "P0b" in pilotes:
        a, b = pilotes["P0"], pilotes["P0b"]
        ligne = lambda n: (SORTIE / f"{n}-empreintes.csv").read_text(encoding="utf-8").splitlines()
        ca, cb = ligne("P0"), ligne("P0b")
        t0["P0b_vs_P0"] = {"empreintes_lignes": len(ca), "lignes_differentes": sum(1 for x, y in zip(ca, cb) if x != y) + abs(len(ca) - len(cb)),
                           "kld_identique": a.get("sha256_kld") == b.get("sha256_kld"), "trace_identique": a.get("sha256_trace") == b.get("sha256_trace"),
                           "defauts": [a.get("defauts_disque"), b.get("defauts_disque")]}
    if "P0" in pilotes and "P-1" in pilotes:
        ca = (SORTIE / "P0-empreintes.csv").read_text(encoding="utf-8").splitlines()
        cb = (SORTIE / "P-1-empreintes.csv").read_text(encoding="utf-8").splitlines()
        n = len(cb)
        ta = lire_trace(SORTIE / "P0.trace")
        tb = lire_trace(SORTIE / "P-1.trace")
        t0["avant_vs_P0_prefixe"] = {"empreintes_comparees": n - 1, "lignes_differentes": sum(1 for x, y in zip(ca[:n], cb) if x != y),
                                      "trace_prefixe_identique": bool((ta[:len(tb)] == tb).all()), "pas_compares": int(len(tb)),
                                      "fenetres_de_P-1": pilotes["P-1"].get("pas", 0) // 512}
    res["T0"] = t0
    # --- passes biaisées
    p0 = pilotes.get("P0")
    if not p0 or p0.get("code") != 0:
        print("P0 manquante : rien à comparer")
        (SORTIE / "analyse.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        return
    kld0 = LOURDS / "P0.kld"
    tr0 = lire_trace(SORTIE / "P0.trace")
    d0 = p0["defauts_disque"]
    res["P0"] = {"defauts": d0, "defauts_par_pas": d0 / p0["pas"], "pas_s": p0["pas_s"], "ppl": p0["ppl_positions_notees"]}
    for nom in sorted(pilotes):
        if nom in ("P0", "P-1") or pilotes[nom].get("code") != 0:
            continue
        pi = pilotes[nom]
        kld = LOURDS / f"{nom}.kld"
        r = {"defauts": pi["defauts_disque"], "defauts_par_pas": pi["defauts_disque"] / pi["pas"], "variation_defauts": pi["defauts_disque"] / d0 - 1,
             "pas_s": pi["pas_s"], "ppl": pi["ppl_positions_notees"]}
        # G5 : cellules changées (ensembles, hors ordre)
        tr = lire_trace(SORTIE / f"{nom}.trace")
        assert tr.shape == tr0.shape, (nom, tr.shape, tr0.shape)
        diff = (np.sort(tr, axis=2) != np.sort(tr0, axis=2)).any(axis=2)
        r["cellules_changees"] = float(diff.mean())
        r["cellules_changees_n"] = int(diff.sum())
        r["cellules_ordre_change_seulement"] = float(((tr != tr0).any(axis=2) & ~diff).mean())
        # défauts : trois chemins
        rj = subprocess.run([str(REJOUER), "--trace", str(SORTIE / f"{nom}.trace"), "--emplacements", str(N)], capture_output=True, text=True)
        rje = json.loads(rj.stdout)["resultats"][0]
        r["defauts_rejouer"] = rje["defauts_disque"]
        e = tr.transpose(1, 0, 2).astype(np.uint8)  # (L, T, 4) couche-major
        r["defauts_lru_python"] = J.lru_defauts(e, N)
        r["defauts_trois_chemins_egaux"] = (r["defauts"] == r["defauts_rejouer"] == r["defauts_lru_python"])
        # chemin A
        resume, lignes = juge_kl(kld0, kld, f"{nom}")
        r["A_juge_kl"] = {"kl_moyenne": resume["kl_moyenne"], "kl_mediane": resume["kl_mediane"], "kl_p99": resume["kl_p99"], "meme_premier": resume["meme_premier"],
                          "kl_incertitude": resume["kl_incertitude"], "n": resume["n"]}
        pa = np.array([int(x["meme_premier"]) for x in lignes], bool)
        # chemin B
        kl, pb, pt, marge, notees = lecteur_kl(kld0, kld)
        fen = np.repeat(np.arange(len(kl) // notees), notees)
        mp = pb == pt
        fort = marge >= S_MARGE
        r["B_lecteur"] = {"kl_moyenne": float(kl.mean()), "kl_mediane": float(np.median(kl)), "kl_p99": float(np.percentile(kl, 99)),
                          "kl_par_fenetre": [float(kl[fen == k].mean()) for k in range(len(kl) // notees)],
                          "kl_bootstrap_fenetres_95": boot(kl, fen),
                          "premier_choix_litteral": float(mp.mean()), "desaccords": int((~mp).sum()),
                          "premier_choix_litteral_bootstrap_95": boot(mp.astype(float), fen),
                          "positions_marge>=0.3": int(fort.sum()), "premier_choix_pondere": float(mp[fort].mean()), "desaccords_pondere": int((~mp[fort]).sum()),
                          "premier_choix_pondere_bootstrap_95": boot(mp.astype(float), fen, masque=fort),
                          "pondere_par_fenetre": [float(mp[(fen == k) & fort].mean()) for k in range(len(kl) // notees)],
                          "desaccords_marge<0.1": float((marge[~mp] < 0.1).mean()) if (~mp).any() else None,
                          "desaccords_marge<0.3": float((marge[~mp] < 0.3).mean()) if (~mp).any() else None}
        r["chemins_A_B_concordent"] = bool(abs(resume["kl_moyenne"] - float(kl.mean())) < 1e-6 and (pa == mp).all())
        r["kl_sur_part_changee"] = r["B_lecteur"]["kl_moyenne"] / r["cellules_changees"] if r["cellules_changees"] > 0 else None
        if avec_ref:
            rr, _ = juge_kl(BASE_F64, kld, f"{nom}-contre-ref-f64")
            r["info_kl_contre_reference_f64"] = rr["kl_moyenne"]
        res["passes"][nom] = r
        print(nom, json.dumps({k: v for k, v in r.items() if k != "B_lecteur"}, ensure_ascii=False), flush=True)
        (SORTIE / "analyse.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    if avec_ref:
        rr, _ = juge_kl(BASE_F64, kld0, "P0-contre-ref-f64")
        res["P0"]["info_kl_contre_reference_f64"] = rr["kl_moyenne"]
    # --- verdicts : le premier β de la grille (0,041 ; 0,05 ; 0,06) qui atteint -10 % décide ; sinon le dernier de la grille passée
    def verdict(lecture):
        cle = "premier_choix_pondere" if lecture == "pondere" else "premier_choix_litteral"
        grille = [b for b in ("B0.041", "B0.05", "B0.06") if b in res["passes"]]
        decisif = next((b for b in grille if res["passes"][b]["variation_defauts"] <= -S_DEFAUTS), None)
        if decisif is None:
            ok5 = [b for b in grille if res["passes"][b]["variation_defauts"] <= -0.05 and res["passes"][b]["B_lecteur"]["kl_moyenne"] <= S_KL_TIENT]
            return {"decisif": None, "verdict": "non concluant" if ok5 else "tombe (aucun β de la grille à -5 % avec KL <= 0,038)" if grille else "pas de passe"}
        r = res["passes"][decisif]
        kl, pc = r["B_lecteur"]["kl_moyenne"], r["B_lecteur"][cle]
        if kl > S_KL_MORT:
            return {"decisif": decisif, "verdict": "tombe (KL > 0,07 au β à -10 %)"}
        if kl <= S_KL_TIENT and pc >= S_PC:
            bas = r["B_lecteur"][cle + "_bootstrap_95"][0]
            return {"decisif": decisif, "verdict": "tient" + ("" if bas >= S_PC else " à l'estimation ; borne basse de l'intervalle %.4f sous 95 %%" % bas)}
        return {"decisif": decisif, "verdict": "non concluant"}
    res["verdict_pondere"], res["verdict_litteral"] = verdict("pondere"), verdict("litteral")
    c = res["passes"].get("B0.3")
    if c:
        res["cassure_beta_0.3"] = {"kl": c["B_lecteur"]["kl_moyenne"], "pondere": c["B_lecteur"]["premier_choix_pondere"], "variation_defauts": c["variation_defauts"],
                                   "la_porte_tombe": bool(c["B_lecteur"]["kl_moyenne"] > S_KL_TIENT or c["B_lecteur"]["premier_choix_pondere"] < S_PC)}
    (SORTIE / "analyse.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("T0", "verdict_pondere", "verdict_litteral", "cassure_beta_0.3") if k in res}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(avec_ref="--sans-ref" not in sys.argv)
