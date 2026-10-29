"""Données des chapitres « Résultats », « L'épreuve » et « Discussion » du Tome II.

Lit les CSV et journaux commités du jalon J1 (lot O), de l'épreuve indépendante et de la ronde de
corrections, et écrit sous memoire/figures/tome2/donnees/ :
  - les CSV que tracent les graphes pgfplots de memoire/figures/tome2/resultats.tex ;
  - res-chiffres.json : chaque nombre dérivé que le texte cite (moyennes, bruits, rapports,
    intervalles de Wilson, tests appariés, planchers en série), recalculé ici par un second chemin
    à partir des passes elles-mêmes, et comparé aux verdicts publiés par les lots.

Aucun nombre n'est écrit à la main : chaque valeur vient d'un fichier nommé dans la fonction qui la
lit. Les seules constantes sont les règles déclarées (06 § 7.5 : 2 × bruit + 3 %) et la formule de
Wilson. Bibliothèque standard seule.
Usage : python -I -X utf8 memoire/outils/tome2_resultats.py   (code non nul si un recalcul s'écarte)
"""
import csv
import json
import math
import sys
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[2]
MES = DEPOT / "mesures"
MOT = MES / "moteur"
SORTIE = DEPOT / "memoire" / "figures" / "tome2" / "donnees"
PLANCHER = 1e-4  # ligne basse des graphes de KL (≈ moitié du pas du format, 2,44·10⁻⁴ nat)
ECARTS = []  # recalculs qui ne redonnent pas le chiffre publié


def lire_csv(chemin):
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def lire_json(chemin):
    with open(chemin, encoding="utf-8-sig") as f:
        return json.load(f)


def ecrire(nom, entetes, lignes):
    SORTIE.mkdir(parents=True, exist_ok=True)
    with open(SORTIE / nom, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(entetes)
        for l in lignes:
            w.writerow(l)


def moyenne(xs):
    return sum(xs) / len(xs)


def bruit(xs):
    """Bruit d'une configuration (06 § 7.5) : (max − min) / moyenne de ses passes."""
    return (max(xs) - min(xs)) / moyenne(xs)


def bruit_paires(xs):
    """Bruit par la règle de 06 § 7.5 quand une série a plusieurs paires (ABBA répétés) : le plus
    grand bruit d'une paire ; les passes sont données dans l'ordre, deux par deux."""
    return max(bruit(xs[i:i + 2]) for i in range(0, len(xs) - 1, 2))


def reel(a, b, ba=None, bb=None):
    """La règle déclarée (ARCHITECTURE § 7.2, 06 § 7.5, telle que l'appliquent les verdicts de la
    ronde) : b diffère de a si |b/a − 1| > 2 × le plus grand des deux bruits + 3 %."""
    ecart = moyenne(b) / moyenne(a) - 1
    seuil = 2 * max(bruit(a) if ba is None else ba, bruit(b) if bb is None else bb) + 0.03
    return ecart, seuil, abs(ecart) > seuil


def wilson(k, n, z=1.959963984540054):
    """Intervalle de Wilson (1927) à 95 % pour k succès sur n."""
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - m, c + m


def verifier(nom, recalcule, publie, tol):
    if abs(recalcule - publie) > tol:
        ECARTS.append(f"{nom} : recalculé {recalcule!r}, publié {publie!r}")


def vitesse():
    """Génération du 120b : J1 (lot O, séance 1), épreuve (séance s1), ronde (séances vitesse et base)."""
    o4 = lire_csv(MOT / "O" / "csv" / "o4-2026-10-15-s1-passes.csv")
    j1 = [float(r["jetons_s_generation"]) for r in o4 if r["modele"] == "gpt-oss-120b.trc"]
    s1 = lire_csv(MOT / "epreuve-J1" / "csv" / "s1-2026-10-16-passes.csv")
    ep = {}
    for r in s1:
        ep.setdefault(r["nom"], []).append(float(r["gen_jetons_s"]))
    vi = lire_csv(MOT / "O" / "corrections" / "csv" / "vitesse-2026-10-16-passes.csv")
    rg = [float(r["gen"]) for r in vi if r["nom"] == "T120g"]
    rs = [float(r["gen"]) for r in vi if r["nom"] == "T120s"]
    rk = [float(r["gen"]) for r in vi if r["nom"] == "T120k"]
    ba = lire_csv(MOT / "O" / "corrections" / "csv" / "base-2026-10-16-passes.csv")
    base = {}
    for r in ba:
        if r["nom"] != "Lw":  # passe d'échauffement jetée (déclaré, bloc 6)
            base.setdefault(r["nom"], []).append(float(r["generation_j_s"]))
    pub = lire_csv(MES / "base-gpt-oss" / "120b" / "resume.csv")
    fit_pub = next(r for r in pub if r["config"] == "fit" and r["grandeur"] == "generation_js")

    # Le graphe : une barre par série, moyenne, min, max.
    series = [
        ("troncons", "J1-O-15oct", j1),
        ("troncons", "epreuve-16oct", ep["T120"]),
        ("troncons", "ronde-sans-garde", rs),
        ("troncons", "ronde-garde", rg),
        ("llama", "fit-t6-publiee", None),
        ("llama", "fit-t6", base["L6"]),
        ("llama", "fit-t10", base["L10"]),
        ("llama", "ncpumoe34-t10", base["Lm"]),
        ("llama", "fit-t12", base["L12"]),
        ("llama", "fit-t16", base["L16"]),
    ]
    lignes = []
    for i, (moteur, nom, xs) in enumerate(series):
        if xs is None:
            m, lo, hi, n = float(fit_pub["moyenne"]), float(fit_pub["min"]), float(fit_pub["max"]), int(fit_pub["n"])
        else:
            m, lo, hi, n = moyenne(xs), min(xs), max(xs), len(xs)
        lignes.append([i, moteur, nom, f"{m:.4f}", f"{hi - m:.4f}", f"{m - lo:.4f}", n])
    ecrire("res-vitesse-120b.csv", ["x", "moteur", "nom", "moyenne", "plus", "moins", "n"], lignes)

    v = lire_json(MOT / "O" / "corrections" / "journaux" / "verdicts-vitesse-2026-10-16.json")
    vb = lire_json(MOT / "O" / "corrections" / "journaux" / "verdicts-base-2026-10-16.json")
    meilleure = max(base, key=lambda k: moyenne(base[k]))
    c6 = moyenne(rg) / moyenne(base[meilleure])
    verifier("C6 rapport", c6, v["C6"]["rapport"] if "C6" in v else vb["C6"]["rapport"], 1e-9)
    # La série ABBA déclarée pour la garde (bloc 3) : passes 02 (A, garde), 03, 04 (B), 05 (A) ;
    # les passes 07 et 08 (garde) sont le A de la série du KV en f32 (bloc 5).
    ga = [float(r["gen"]) for r in vi if r["passe"] in ("02-T120g", "05-T120g")]
    garde = reel(rs, ga)
    verifier("coût de la garde", garde[0], -v["garde"]["ecart_B_sur_A"] / (1 + v["garde"]["ecart_B_sur_A"]), 1e-9)
    duels = {k: reel(base[k], base[meilleure]) for k in base if k != meilleure}
    for k, (e, s_, r) in duels.items():
        verifier(f"duel {k}", e, vb["duels_contre_la_meilleure"][k]["ecart_meilleure_sur_elle"], 1e-9)
        verifier(f"seuil {k}", s_, vb["duels_contre_la_meilleure"][k]["seuil"], 1e-9)
    # À disque égal : les passes 04 (sans garde) et 05 (garde) de la séance vitesse.
    p = {r["passe"]: r for r in vi}
    disque_egal = float(p["05-T120g"]["gen"]) / float(p["04-T120s"]["gen"]) - 1
    return {
        "j1_lot_O": j1, "epreuve_T120": ep["T120"], "epreuve_T20": ep["T20"],
        "epreuve_L6": ep["L120"], "epreuve_L10": ep["L120t10"], "epreuve_tiede": ep["T120tiede1"],
        "ronde_garde": rg, "ronde_sans_garde": rs, "ronde_kv_f32": rk,
        "ronde_garde_moyenne": moyenne(rg), "ronde_garde_bruit": bruit(rg),
        "ronde_sans_garde_moyenne": moyenne(rs), "ronde_sans_garde_bruit": bruit(rs),
        "base": {k: {"passes": xs, "moyenne": moyenne(xs), "bruit": bruit(xs)} for k, xs in base.items()},
        "base_meilleure": meilleure,
        "base_duels": {k: {"ecart": e, "seuil": s, "reel": r} for k, (e, s, r) in duels.items()},
        "base_publiee_fit_t6": float(fit_pub["moyenne"]),
        "C6_garde_contre_meilleure": c6,
        "ronde_garde_bruit_paires": bruit_paires(rg),
        "C6_seuil": 2 * max(bruit_paires(rg), bruit(base[meilleure])) + 0.03,
        "C6_seuil_bruit_sur_quatre": 2 * max(bruit(rg), bruit(base[meilleure])) + 0.03,
        "C6_sans_garde_contre_meilleure": moyenne(rs) / moyenne(base[meilleure]),
        "C6_garde_contre_base_publiee": moyenne(rg) / float(fit_pub["moyenne"]),
        "C6_j1_contre_base_publiee": moyenne(j1) / float(fit_pub["moyenne"]),
        "C6_j1_contre_meilleure": moyenne(j1) / moyenne(base[meilleure]),
        "C6_epreuve_contre_t10_epreuve": moyenne(ep["T120"]) / moyenne(ep["L120t10"]),
        "garde_abba_A": ga, "garde_abba_moyenne": moyenne(ga), "garde_abba_bruit": bruit(ga),
        "garde_quatre_contre_sans": moyenne(rg) / moyenne(rs) - 1,
        "garde_ecart": garde[0], "garde_seuil": garde[1], "garde_reel": garde[2],
        "garde_disque_egal_05_sur_04": disque_egal,
        "garde_attente_ms": [float(r["garde_attente_ms_par_jeton"]) for r in vi if r["nom"] == "T120g"],
        "garde_ouverture_s": v["garde_ouverture_s"],
    }


def plancher():
    """Plancher en série, étage par étage, et temps mesuré par jeton (séance vitesse de la ronde)."""
    vi = lire_csv(MOT / "O" / "corrections" / "csv" / "vitesse-2026-10-16-passes.csv")
    o4 = lire_csv(MOT / "O" / "csv" / "o4-2026-10-15-s1-passes.csv")
    lignes = []
    i = 0
    for r in o4:
        if r["modele"] != "gpt-oss-120b.trc":
            continue
        t = [float(r[c]) for c in ("t_disque_ms", "t_pcie_ms", "t_dec_ms", "t_gemv_ms", "t0_ms")]
        lignes.append([i, f"J1 {r['passe']}", *[f"{x:.2f}" for x in t], f"{sum(t):.2f}",
                       f"{1000 / float(r['jetons_s_generation']):.2f}"])
        i += 1
    for r in vi:
        if r["nom"] == "T120k":
            continue  # autre texte : non comparable (REPRISE-O, recettes de la ronde)
        t = [float(r["t_disque_ms"]), float(r["t_pcie_ms"]), float(r["t_dec_ms"]), float(r["t_gemv_ms"]), 3.5]
        nom = r["passe"].replace("T120g", "garde").replace("T120s", "sans garde")
        lignes.append([i, nom, *[f"{x:.2f}" for x in t], f"{sum(t):.2f}", f"{1000 / float(r['gen']):.2f}"])
        verifier(f"plancher {r['passe']}", 1000 / sum(t), float(r["plancher_serie"]), 1e-6)
        i += 1
    ecrire("res-plancher.csv", ["x", "passe", "disque", "pcie", "dec", "gemv", "t0", "serie", "mesure"], lignes)
    return {"lignes": [l[1:] for l in lignes]}


def memoire():
    """Mémoire de pointe contre taille du modèle : troncons (A0) et llama.cpp (fit, -t 6)."""
    o4 = lire_csv(MOT / "O" / "csv" / "o4-2026-10-15-s1-passes.csv")
    tr = {}
    for r in o4:
        tr.setdefault(r["modele"], []).append(int(r["ram_pointe_o"]))
    tailles = {"gpt-oss-20b.trc": 12109566624, "gpt-oss-120b.trc": 63387346208}  # REPRISE.md (téléchargements)
    ll = {}
    for m in ("20b", "120b"):
        rr = lire_csv(MES / "base-gpt-oss" / m / "resume.csv")
        ll[m] = next(float(r["moyenne"]) for r in rr if r["config"] == "fit" and r["grandeur"] == "ensemble_travail_pointe_go")
    lignes = [
        ["gpt-oss-20b", f"{tailles['gpt-oss-20b.trc'] / 1e9:.3f}", f"{max(tr['gpt-oss-20b.trc']) / 1e6:.2f}", f"{ll['20b'] * 1000:.0f}"],
        ["gpt-oss-120b", f"{tailles['gpt-oss-120b.trc'] / 1e9:.3f}", f"{max(tr['gpt-oss-120b.trc']) / 1e6:.2f}", f"{ll['120b'] * 1000:.0f}"],
    ]
    ecrire("res-memoire.csv", ["modele", "taille_go", "troncons_mo", "llama_mo"], lignes)
    s1 = lire_csv(MOT / "epreuve-J1" / "csv" / "s1-2026-10-16-passes.csv")
    # Séance de l'épreuve, par passe : ensemble de travail, engagée, perte de la machine (Mo).
    seance = []
    sortes = ("T120", "L120", "L120t10", "T120tiede1")
    for i, r in enumerate(s1):
        g = float(r["gen_jetons_s"])
        par = [f"{g:.4f}" if r["nom"] == k else "nan" for k in sortes]
        seance.append([i, r["passe"], r["nom"], f"{g:.4f}", *par, f"{float(r['pointe_et_os_mo']):.2f}",
                       f"{float(r['pointe_engagee_os_mo']):.2f}", f"{float(r['perte_machine_mo']):.2f}", r["vram_pointe_mio"]])
    ecrire("res-epreuve-seance.csv", ["x", "passe", "nom", "gen", "gen_t120", "gen_l6", "gen_l10", "gen_tiede",
                                      "et", "engagee", "perte", "vram"], seance)
    pente_tr = (max(tr["gpt-oss-120b.trc"]) - max(tr["gpt-oss-20b.trc"])) / (tailles["gpt-oss-120b.trc"] - tailles["gpt-oss-20b.trc"])
    pente_ll = (ll["120b"] - ll["20b"]) * 1e9 / (tailles["gpt-oss-120b.trc"] - tailles["gpt-oss-20b.trc"])
    return {"troncons_o": tr, "llama_fit_go": ll, "pente_troncons_o_par_o": pente_tr, "pente_llama_o_par_o": pente_ll,
            "rapport_120b": ll["120b"] * 1e9 / max(tr["gpt-oss-120b.trc"]),
            "modele_sur_fenetre_120b": tailles["gpt-oss-120b.trc"] / max(tr["gpt-oss-120b.trc"])}


def fidelite():
    """C4 sur la fenêtre 0 du 120b contre la vérité numpy f64 (épreuve), et le KV en f32 (ronde)."""
    c4 = lire_csv(MOT / "epreuve-J1" / "csv" / "c4-numpy-120b-f0.csv")
    c20 = lire_csv(MOT / "epreuve-J1" / "csv" / "c4-numpy-20b-f0.csv")
    kv = lire_csv(MOT / "O" / "corrections" / "csv" / "kv-f16-f32-par-position.csv")
    f32 = {int(r["position"]): float(r["kl_f32"]) for r in kv if r["cas"] == "f0-120b"}
    lignes = []
    for r in c4:
        p = int(r["position"])
        a, b = float(r["kl_troncons_120b"]), float(r["kl_llama_carte_120b"])
        # Axe logarithmique : une KL sous PLANCHER (dont les KL ≤ 0, plancher du format) se dessine
        # sur la ligne du plancher ; leur nombre est publié dans res-chiffres.json.
        lignes.append([p, r["kl_troncons_120b"], r["kl_llama_carte_120b"], f"{f32[p]:.10e}",
                       f"{max(a, PLANCHER):.6e}", f"{max(b, PLANCHER):.6e}", f"{max(f32[p], PLANCHER):.6e}"])
    ecrire("res-kl-120b-f0.csv", ["position", "kl_f16", "kl_llama", "kl_f32", "d_f16", "d_llama", "d_f32"], lignes)
    # L'invite : positions 354 à 706 (au-delà de la fenêtre 0), f16 contre f32, coupées à 0,05 pour le dessin.
    inv = {}
    for r in kv:
        if r["cas"].startswith("invite"):
            p = int(r["position"])
            inv.setdefault(p, {})
            if r["kl_f16"]:
                inv[p]["f16"] = float(r["kl_f16"])
            if r["kl_f32"]:
                inv[p]["f32"] = float(r["kl_f32"])
    li = []
    for p in sorted(inv):
        a, b = inv[p]["f16"], inv[p]["f32"]
        li.append([p, f"{a:.6e}", f"{b:.6e}", f"{max(a, PLANCHER):.6e}", f"{max(b, PLANCHER):.6e}"])
    ecrire("res-kl-invite.csv", ["position", "kl_f16", "kl_f32", "d_f16", "d_f32"], li)

    def resume(rows, cle_t, cle_l, cle_pt, cle_pl):
        kt = [float(r[cle_t]) for r in rows]
        kl = [float(r[cle_l]) for r in rows]
        nt = sum(int(r[cle_pt]) for r in rows)
        nl = sum(int(r[cle_pl]) for r in rows)
        n = len(rows)
        d = [a - b for a, b in zip(kt, kl)]
        dm = moyenne(d)
        sd = math.sqrt(sum((x - dm) ** 2 for x in d) / (n - 1))
        return {"n": n, "kl_troncons": moyenne(kt), "kl_llama": moyenne(kl),
                "premier_troncons": nt, "premier_llama": nl,
                "wilson_troncons": wilson(nt, n), "wilson_llama": wilson(nl, n),
                "d_moyen": dm, "d_erreur_type": sd / math.sqrt(n),
                "queue_troncons_kl_sup_0_1": sum(1 for x in kt if x > 0.1) / n,
                "queue_llama_kl_sup_0_1": sum(1 for x in kl if x > 0.1) / n}

    r120 = resume(c4, "kl_troncons_120b", "kl_llama_carte_120b", "meme_premier_troncons_120b", "meme_premier_llama_carte_120b")
    cles20 = list(c20[0].keys())
    r20 = resume(c20, *[c for c in cles20 if c.startswith("kl_t")][:1], *[c for c in cles20 if c.startswith("kl_l")][:1],
                 *[c for c in cles20 if c.startswith("meme_premier_t")][:1], *[c for c in cles20 if c.startswith("meme_premier_l")][:1])
    verifier("KL troncons 120b f0", r120["kl_troncons"], 0.00308, 5e-6)
    verifier("KL llama 120b f0", r120["kl_llama"], 0.0607, 5e-5)
    verifier("d apparié 120b", r120["d_moyen"], -0.0576, 5e-5)
    k32 = [f32[p] for p in sorted(f32)]
    inv16 = [inv[p]["f16"] for p in inv if p >= 512]
    inv32 = [inv[p]["f32"] for p in inv if p >= 512]
    sous = lambda xs: sum(1 for x in xs if x <= PLANCHER)
    nf16 = [float(r["kl_troncons_120b"]) for r in c4]
    nll = [float(r["kl_llama_carte_120b"]) for r in c4]
    return {"plancher_du_dessin": PLANCHER,
            "120b_f0_sous_plancher": {"f16": sous(nf16), "llama": sous(nll), "f32": sous(list(f32.values())),
                                      "f16_non_positives": sum(1 for x in nf16 if x <= 0)},
            "invite_sous_plancher": {"f16": sous([v["f16"] for v in inv.values()]), "f32": sous([v["f32"] for v in inv.values()]),
                                     "n": len(inv)},
            "120b_f0": r120, "20b_f0": r20, "120b_f0_kv_f32_moyenne": moyenne(k32),
            "invite_512_706_f16_moyenne": moyenne(inv16), "invite_512_706_f32_moyenne": moyenne(inv32),
            "invite_512_706_f16_part_kl_sup_0_1": sum(1 for x in inv16 if x > 0.1) / len(inv16),
            "invite_positions": [min(inv), max(inv)], "invite_n_512_plus": len(inv16)}


def routage():
    """Accord de routage moteur / vérité par couche, sur l'invite (épreuve, § 6.1)."""
    rr = lire_csv(MOT / "epreuve-J1" / "csv" / "routage-par-couche-invite.csv")
    t = {}
    for r in rr:
        t[(r["modele"], int(r["couche"]))] = (float(r["accord_256_511"]), float(r["accord_512_plus"]))
    lignes = []
    for c in range(36):
        a = t[("120b", c)]
        b = t.get(("20b", c), ("nan", "nan"))
        lignes.append([c, a[0], a[1], b[0], b[1]])
    ecrire("res-routage.csv", ["couche", "a120_256", "a120_512", "a20_256", "a20_512"], lignes)
    return {"120b_min_512": min(v[1] for k, v in t.items() if k[0] == "120b"),
            "20b_min_512": min(v[1] for k, v in t.items() if k[0] == "20b")}


def principal():
    chiffres = {"vitesse": vitesse(), "plancher": plancher(), "memoire": memoire(),
                "fidelite": fidelite(), "routage": routage(), "ecarts": ECARTS}
    SORTIE.mkdir(parents=True, exist_ok=True)
    with open(SORTIE / "res-chiffres.json", "w", encoding="utf-8") as f:
        json.dump(chiffres, f, ensure_ascii=False, indent=1)
    if ECARTS:
        print("ÉCARTS :", *ECARTS, sep="\n  ", file=sys.stderr)
        return 1
    print("tome2_resultats : CSV écrits sous", SORTIE.relative_to(DEPOT), "; aucun écart aux chiffres publiés")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
