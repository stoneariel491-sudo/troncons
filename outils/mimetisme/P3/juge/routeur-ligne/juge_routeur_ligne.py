"""Juge du routeur biaisé EN LIGNE de P3 : mon propre chemin, sans importer p3_*.py, le `juge kl`, `rejouer`, ni le juge de N = 238.

  python -I -X utf8 juge_routeur_ligne.py empreintes  → SHA-256 des .kld, traces, CSV ; T0 (P0 contre P0b) et P-1 en préfixe, octet par octet
  python -I -X utf8 juge_routeur_ligne.py defauts     → défauts par MON LRU sur les traces ; variantes d'ordre dans le groupe,
                                                         d'initialisation et de budget ; cassures du LRU
  python -I -X utf8 juge_routeur_ligne.py cellules    → part de cellules changées par couche ; séparation échanges voulus /
                                                         bascules naturelles (référence ouverte, marges z4 − z5, cache réel de la passe)
  python -I -X utf8 juge_routeur_ligne.py kl          → KL excédentaire contre P0 et premiers choix, relus des .kld en flux (paquets de 8)
  python -I -X utf8 juge_routeur_ligne.py analyse     → verdicts aux seuils déclarés (06-), intervalles par fenêtres, bornes
  python -I -X utf8 juge_routeur_ligne.py comparer    → mes positions contre les CSV de `juge kl` (lus seulement ici, après mon calcul)

Trace du moteur : texte, deux lignes d'en-tête (« # trace … », « E=32 »), puis une ligne par pas, 24 groupes « a b c d » séparés par
« | », dans l'ordre de service (logit non biaisé décroissant). Le pas t de la fenêtre w est la ligne 512 w + t.

LRU écrit depuis la définition de `trc-cache` (lue : `demander`, `emplacement_pour_defaut`, `Lru::victime`) : global sur 24 × 32,
accès t croissant puis l croissant, dans le groupe l'ordre de service ; les 4 experts du groupe sont épinglés pendant le groupe ;
défaut = absent ; si plein, la victime est le résident non épinglé de plus petit horodatage. Horodatage par accès (pas par liste).
La présence d'un expert de la couche l juste avant le groupe (t, l) est ce que le moteur lit par `Cache::emplacement_de`
pour monter le biais : je l'enregistre en même temps.

Lecteur .kld écrit de nouveau depuis le format (en-tête « _logits_ », u32 n_ctx, i32 n_vocab, i32 n_fenêtres, jetons i32, puis par
position notée 2·⌈n_vocab/2⌉ + 4 mots u16 : f32 pas, f32 log p_min, n_vocab codes). Contrôle : Σ exp(log p) ≈ 1.
Fils : au plus deux (variables posées avant l'import de numpy).
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "2"

import csv
import hashlib
import json
import pathlib
import struct
import sys

import numpy as np

DEPOT = pathlib.Path(__file__).resolve().parents[5]
MES = DEPOT / "mesures" / "mimetisme" / "P3" / "routeur-ligne"
SORTIE = DEPOT / "mesures" / "mimetisme" / "P3" / "juge" / "routeur-ligne"
KLD = pathlib.Path("~/dev/essais/troncons/mimetisme/P3/routeur-ligne")
REF = pathlib.Path("~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld")
P3 = pathlib.Path("~/dev/essais/troncons/mimetisme/P3")
L, E, K = 24, 32, 4
N = 238
PASSES = ("P0", "P0b", "B0.041", "B0.05", "B0.3")
BETA = {"B0.041": 0.041, "B0.05": 0.05, "B0.3": 0.3}
PAQUET = 8


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while b := f.read(1 << 22):
            h.update(b)
    return h.hexdigest()


def ecrire(nom, obj):
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / nom).write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=float), encoding="utf-8")


def lire_json(p):
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- traces
def trace(nom):
    """(T, L, 4) uint8, ordre de service."""
    lignes = (MES / f"{nom}.trace").read_text(encoding="utf-8").splitlines()
    assert lignes[0].startswith("#") and lignes[1] == "E=32", nom
    out = []
    for s in lignes[2:]:
        g = [list(map(int, x.split())) for x in s.split("|")]
        assert len(g) == L and all(len(x) == K for x in g), nom
        out.append(g)
    return np.array(out, dtype=np.uint8)


def journal(p):
    """Journal de routage de la référence : (T, L, 4) experts, (T, L) marge z4 − z5 enregistrée."""
    d = pathlib.Path(p).read_bytes()
    Lj, T = struct.unpack_from("<II", d, 0)
    assert len(d) == 8 + 8 * Lj * T
    a = np.frombuffer(d, dtype=np.uint8, offset=8).reshape(Lj, T, 8)
    return a[:, :, :4].transpose(1, 0, 2).copy(), a[:, :, 4:8].copy().view("<f4")[..., 0].T.copy()


def aligner(tr, par_fen_journal=511):
    """Pas du moteur (512 par fenêtre) → positions du journal (511 par fenêtre : les 511 premières)."""
    T = tr.shape[0]
    idx = [w * 512 + j for w in range(T // 512) for j in range(par_fen_journal)]
    return tr[idx]


# ---------------------------------------------------------------- empreintes
def empreintes():
    r = {"kld": {}, "trace": {}, "csv": {}, "pilote": {}}
    for nom in PASSES + ("P-1",):
        pil = lire_json(MES / f"{nom}-pilote.json")
        r["pilote"][nom] = {k: pil.get(k) for k in ("sha256_kld", "sha256_trace", "sha256_csv", "defauts_disque", "pas", "debut")}
        r["trace"][nom] = sha256(MES / f"{nom}.trace")
        r["csv"][nom] = sha256(MES / f"{nom}-empreintes.csv")
        k = KLD / f"{nom}.kld"
        r["kld"][nom] = sha256(k) if k.exists() else None
        r["pilote"][nom]["trace_egale"] = r["trace"][nom] == pil["sha256_trace"]
        r["pilote"][nom]["csv_egal"] = r["csv"][nom] == pil["sha256_csv"]
        r["pilote"][nom]["kld_egal"] = None if r["kld"][nom] is None else r["kld"][nom] == pil["sha256_kld"]
        print(nom, r["pilote"][nom], flush=True)
    # T0 : P0 contre P0b, octet par octet (trace et empreintes), compte de lignes différentes
    def lignes_diff(a, b, n=None):
        la = (MES / a).read_text(encoding="utf-8").splitlines()
        lb = (MES / b).read_text(encoding="utf-8").splitlines()
        if n is not None:
            la, lb = la[:n], lb[:n]
        return {"lignes_a": len(la), "lignes_b": len(lb), "differentes": sum(x != y for x, y in zip(la, lb)) + abs(len(la) - len(lb))}
    r["T0_trace"] = lignes_diff("P0.trace", "P0b.trace")
    r["T0_empreintes"] = lignes_diff("P0-empreintes.csv", "P0b-empreintes.csv")
    r["T0_kld_par_pilote"] = r["pilote"]["P0"]["sha256_kld"] == r["pilote"]["P0b"]["sha256_kld"]
    # P-1 (binaire d'avant l'option) : 3 fenêtres = 1 536 pas, en préfixe de P0
    r["P-1_trace_prefixe"] = lignes_diff("P0.trace", "P-1.trace", 2 + 1536)
    r["P-1_empreintes_prefixe"] = lignes_diff("P0-empreintes.csv", "P-1-empreintes.csv", 1 + 1536)
    # cassure du comparateur : B0.041 contre P0 doit différer
    r["cassure_comparateur_B0.041"] = lignes_diff("P0-empreintes.csv", "B0.041-empreintes.csv")
    print(json.dumps({k: v for k, v in r.items() if k not in ("pilote",)}, indent=1), flush=True)
    ecrire("empreintes.json", r)


# ---------------------------------------------------------------- LRU
def lru(tr, n=N, ordre="service", init="vide", reinit_fenetre=False, graine=0, presence=False):
    """tr : (T, L, 4). Rend (défauts, présence (T, L, 32) bool ou None).
    ordre : service | inverse | indice | hasard ; init : vide | chaud (état final d'un premier passage) | premiers (0..n-1)."""
    T = tr.shape[0]
    g = tr.astype(np.int64) + (np.arange(L, dtype=np.int64) * E)[None, :, None]
    if ordre == "inverse":
        g = g[:, :, ::-1]
    elif ordre == "indice":
        g = np.sort(g, -1)
    elif ordre == "hasard":
        rng = np.random.default_rng(graine)
        g = np.take_along_axis(g, rng.permuted(np.tile(np.arange(K), (T, L, 1)), axis=-1), -1)
    stamp = np.full(L * E, -1, np.int64)
    res = np.zeros(L * E, bool)
    horloge = 0
    if init == "chaud":
        _, etat = _passage(g, n, stamp.copy(), res.copy(), 0, False, None)
        stamp, res, horloge = etat
        stamp = stamp - horloge  # mêmes rangs, horloge repartie de 0
        horloge = 0
    elif init == "premiers":
        res[:n] = True
        stamp[:n] = np.arange(n) - n
    pres = np.zeros((T, L, E), bool) if presence else None
    d, _ = _passage(g, n, stamp, res, horloge, reinit_fenetre, pres)
    return d, pres


def _passage(g, n, stamp, res, horloge, reinit_fenetre, pres):
    T = g.shape[0]
    occ = int(res.sum())
    defauts = 0
    grand = np.iinfo(np.int64).max
    for t in range(T):
        if reinit_fenetre and t % 512 == 0:
            res[:] = False
            stamp[:] = -1
            occ = 0
        for l in range(L):
            if pres is not None:
                pres[t, l] = res[l * E:(l + 1) * E]
            grp = g[t, l]
            for x in grp:
                if not res[x]:
                    defauts += 1
                    if occ >= n:
                        s = np.where(res, stamp, grand)
                        s[grp] = grand
                        v = int(s.argmin())
                        res[v] = False
                        occ -= 1
                    res[x] = True
                    occ += 1
                stamp[x] = horloge
                horloge += 1
    return defauts, (stamp, res, horloge)


def defauts():
    tr = {nom: trace(nom) for nom in PASSES}
    r = {"N": N, "passes": {}}
    for nom in PASSES:
        d, _ = lru(tr[nom])
        pil = lire_json(MES / f"{nom}.json")
        r["passes"][nom] = {"moi": d, "pilote": lire_json(MES / f"{nom}-pilote.json")["defauts_disque"]}
        print(nom, r["passes"][nom], flush=True)
    d0 = r["passes"]["P0"]["moi"]
    r["seuil_10pct"] = 0.9 * d0
    for nom in BETA:
        x = r["passes"][nom]["moi"]
        r["passes"][nom].update({"variation": x / d0 - 1, "marge_au_seuil": 0.9 * d0 - x})
    # cassures du LRU : chacune doit changer le compte
    rng = np.random.default_rng(31)
    tp = tr["P0"].copy()
    for c in rng.choice(tp.shape[0] * L, 1000, replace=False):
        t, l = divmod(int(c), L)
        tp[t, l] = rng.choice(E, K, replace=False)
    r["cassures"] = {"1000_cellules_au_hasard_P0": lru(tp)[0], "budget_237_P0": lru(tr["P0"], 237)[0]}
    print("cassures", r["cassures"], flush=True)
    # robustesse de la marge de 31 défauts (comptage seulement : la trajectoire reste celle produite par le cache du moteur)
    variantes = [("service", "vide", False), ("inverse", "vide", False), ("indice", "vide", False),
                 ("hasard", "vide", False), ("service", "chaud", False), ("service", "premiers", False),
                 ("service", "vide", True)]
    rob = {}
    for ordre, init, reinit in variantes:
        cle = f"{ordre}/{init}" + ("/reinit-fenetre" if reinit else "")
        graines = range(5) if ordre == "hasard" else (0,)
        for gr in graines:
            c = cle + (f"/graine{gr}" if ordre == "hasard" else "")
            p0 = lru(tr["P0"], ordre=ordre, init=init, reinit_fenetre=reinit, graine=gr)[0]
            b1 = lru(tr["B0.041"], ordre=ordre, init=init, reinit_fenetre=reinit, graine=gr)[0]
            b2 = lru(tr["B0.05"], ordre=ordre, init=init, reinit_fenetre=reinit, graine=gr)[0]
            rob[c] = {"P0": p0, "B0.041": b1, "B0.05": b2, "variation_B0.041": b1 / p0 - 1, "marge_B0.041": 0.9 * p0 - b1,
                      "variation_B0.05": b2 / p0 - 1}
            print(c, rob[c], flush=True)
    r["robustesse"] = rob
    # budget voisin (informatif : la trajectoire a été produite à 238)
    r["budget_voisin"] = {str(n): {"P0": lru(tr["P0"], n)[0], "B0.041": lru(tr["B0.041"], n)[0]} for n in (230, 234, 242, 246)}
    for n, v in r["budget_voisin"].items():
        v["variation"] = v["B0.041"] / v["P0"] - 1
    print("budget", r["budget_voisin"], flush=True)
    # par fenêtre (le cache traverse les fenêtres ; défauts comptés dans chaque tranche de 512 pas)
    ecrire("defauts.json", r)


# ---------------------------------------------------------------- cellules
def ensembles_differents(a, b):
    return (np.sort(a, -1) != np.sort(b, -1)).any(-1)


def cellules():
    tr = {nom: trace(nom) for nom in ("P0", "B0.041", "B0.05", "B0.3")}
    j0, m0 = journal(P3 / "B" / "routage-impose-V1-b0.0-N31.bin")              # référence ouverte (modèle exact), marge z4 − z5
    jb = {"B0.041": journal(P3 / "B238" / "routage-impose-V1-b0.041-N31.bin")[0],
          "B0.05": journal(P3 / "B238" / "routage-impose-V1-b0.05-N31.bin")[0],
          "B0.3": journal(P3 / "B238" / "routage-impose-V1-b0.3-N31.bin")[0]}
    r = {"alignement": {}, "passes": {}}
    p0a = aligner(tr["P0"])
    # alignement : P0 aligné doit égaler la référence ouverte sur la grande majorité des cellules ; décalé d'un pas, non
    r["alignement"]["P0_egal_ref_ouverte"] = float((~ensembles_differents(p0a, j0)).mean())
    dec = aligner(np.roll(tr["P0"], 1, axis=0))
    r["alignement"]["cassure_decalage_1"] = float((~ensembles_differents(dec, j0)).mean())
    print("alignement", r["alignement"], flush=True)
    nat = ensembles_differents(p0a, j0)                     # bascules naturelles du moteur sans biais contre la référence ouverte
    r["P0_contre_ref_par_couche"] = nat.mean(0).tolist()
    for nom, beta in BETA.items():
        b = tr[nom]
        _, pres = lru(b, presence=True)                    # présence réelle vue par le moteur biaisé (ce que lit emplacement_de)
        chg = ensembles_differents(b, tr["P0"])            # boucle fermée : B contre P0, sur les 5 120 pas
        # cohérence avec le biais seul (logits de P0 inchangés) : entrants présents, sortants absents
        sb = np.zeros((b.shape[0], L, E), bool)
        s0 = np.zeros_like(sb)
        np.put_along_axis(sb, b.astype(np.int64), True, -1)
        np.put_along_axis(s0, tr["P0"].astype(np.int64), True, -1)
        entrants = sb & ~s0
        sortants = s0 & ~sb
        incoherent = (entrants & ~pres).any(-1) | (sortants & pres).any(-1)
        incoherent &= chg
        # cassure du test de cohérence : la présence d'un autre pas (997 plus tôt : un cache faux) doit rendre des cellules
        # incohérentes en couche 0
        pf = np.roll(pres, 997, axis=0)
        cassure_c0 = int((((entrants & ~pf).any(-1) | (sortants & pf).any(-1)) & chg)[:, 0].sum())
        # couche 0 : logits identiques à P0 (entrée = enchâssement, KV de la couche 0 sans expert). Le rendu suit le logit
        # NON biaisé : à ensemble égal, l'ordre doit être le même ; à ensemble changé, les experts communs gardent leur ordre relatif.
        b0, p0c = b[:, 0], tr["P0"][:, 0]
        meme = ~chg[:, 0]
        ordre_diff_c0 = int((meme & (b0 != p0c).any(-1)).sum())
        rel = 0
        for t in np.nonzero(chg[:, 0])[0]:
            com_b = [x for x in b0[t] if x in p0c[t]]
            com_p = [x for x in p0c[t] if x in b0[t]]
            rel += com_b != com_p
        ordre_diff_ailleurs = float((~chg & (b != tr["P0"]).any(-1)).sum() / chg.size)
        # sur les 5 110 cellules alignées : marge de la référence ouverte, bascule naturelle, ensemble ouvert biaisé
        ca = aligner(chg)
        inc_a = aligner(incoherent)
        marge_sous_beta = m0 < beta
        ouvert = ensembles_differents(jb[nom], j0)         # boucle ouverte, même β, trajectoire exacte
        egal_ouvert = ~ensembles_differents(aligner(b), jb[nom])
        d = {
            "beta": beta,
            "part_changee": float(chg.mean()), "cellules_changees": int(chg.sum()),
            "par_couche": chg.mean(0).tolist(),
            "ouverte_par_couche": ouvert.mean(0).tolist(), "ouverte_part": float(ouvert.mean()),
            "incoherentes_part_des_changees": float(incoherent.sum() / chg.sum()),
            "incoherentes_par_couche": (incoherent.sum(0) / np.maximum(chg.sum(0), 1)).tolist(),
            "incoherentes_couche0": int(incoherent[:, 0].sum()), "cassure_presence_decalee_couche0": cassure_c0,
            "couche0_meme_ensemble_autre_ordre": ordre_diff_c0, "couche0_changees_ordre_relatif_rompu": int(rel),
            "meme_ensemble_autre_ordre_toutes_couches": ordre_diff_ailleurs,
            # partition des changées alignées
            "alignees_changees": int(ca.sum()),
            "chg_et_nat": int((ca & nat).sum()),
            "chg_marge_ref_sous_beta": int((ca & marge_sous_beta).sum()),
            "chg_coherent_marge_sous_beta_non_nat": int((ca & ~inc_a & marge_sous_beta & ~nat).sum()),
            "chg_incoherent": int(inc_a.sum()),
            "chg_coherent_marge_ge_beta": int((ca & ~inc_a & ~marge_sous_beta).sum()),
            "chg_egal_ensemble_ouvert": int((ca & egal_ouvert).sum()),
            "par_couche_detail": [],
        }
        for l in range(L):
            c = ca[:, l]
            d["par_couche_detail"].append({
                "couche": l, "changees": float(c.mean()), "ouverte": float(ouvert[:, l].mean()), "nat_P0_ref": float(nat[:, l].mean()),
                "marge_ref_sous_beta": float(marge_sous_beta[:, l].mean()),
                "chg_incoherent": float((c & inc_a[:, l]).mean()),
                "chg_coherent_sous_beta": float((c & ~inc_a[:, l] & marge_sous_beta[:, l]).mean()),
                "chg_coherent_ge_beta": float((c & ~inc_a[:, l] & ~marge_sous_beta[:, l]).mean()),
                "chg_nat": float((c & nat[:, l]).mean()),
                "chg_egal_ouvert": float((c & egal_ouvert[:, l]).mean()),
            })
        # d'où vient la dérive : une cellule incohérente (dérive certaine) a-t-elle une couche amont changée AU MÊME PAS
        # (résidu de ce pas) ou aucune (seul l'historique KV des positions précédentes a pu la déplacer) ?
        amont = np.zeros_like(chg)
        amont[:, 1:] = np.logical_or.accumulate(chg[:, :-1], axis=1)
        d["derive_source"] = {
            "incoherentes": int(incoherent.sum()),
            "incoherentes_avec_amont_change_meme_pas": int((incoherent & amont).sum()),
            "incoherentes_sans_amont_change": int((incoherent & ~amont).sum()),
            "taux_incoherent_si_amont_change": float(incoherent[amont].mean()),
            "taux_incoherent_si_amont_intact_couches_1_23": float(incoherent[:, 1:][~amont[:, 1:]].mean()),
            "cellules_amont_intact_couches_1_23": int((~amont[:, 1:]).sum()),
        }
        r["passes"][nom] = d
        print(nom, {k: v for k, v in d.items() if not isinstance(v, list)}, flush=True)
        print("  couches", [round(x, 3) for x in d["par_couche"]], flush=True)
        print("  ouverte", [round(x, 3) for x in d["ouverte_par_couche"]], flush=True)
        print("  incoher", [round(x, 3) for x in d["incoherentes_par_couche"]], flush=True)
    print("nat P0/ref", [round(x, 3) for x in r["P0_contre_ref_par_couche"]], flush=True)
    ecrire("cellules.json", r)


# ---------------------------------------------------------------- .kld
class Kld:
    def __init__(self, p):
        self.f = open(p, "rb", buffering=1 << 20)
        h = self.f.read(20)
        assert h[:8] == b"_logits_", p
        self.n_ctx, self.n_vocab, self.n_fen = struct.unpack("<Iii", h[8:20])
        self.mots = 2 * ((self.n_vocab + 1) // 2) + 4
        self.jetons = np.frombuffer(self.f.read(4 * self.n_ctx * self.n_fen), "<i4").reshape(self.n_fen, self.n_ctx)
        self.par_fen = self.n_ctx - 1 - self.n_ctx // 2
        self.n = self.par_fen * self.n_fen
        assert os.path.getsize(p) == 20 + 4 * self.n_ctx * self.n_fen + 2 * self.mots * self.n

    def lire(self, k):
        u = np.frombuffer(self.f.read(2 * self.mots * k), "<u2").reshape(k, self.mots)
        tete = np.ascontiguousarray(u[:, :4]).view("<f4")
        return u[:, 4:4 + self.n_vocab].astype(np.float64) * tete[:, :1].astype(np.float64) + tete[:, 1:2].astype(np.float64)


def deux(lp):
    i1 = lp.argmax(1)
    r = np.arange(len(lp))
    v1 = lp[r, i1].copy()
    lp[r, i1] = -np.inf
    i2 = lp.argmax(1)
    v2 = lp[r, i2].copy()
    lp[r, i1] = v1
    return i1, v1 - v2


def kl():
    base = Kld(KLD / "P0.kld")
    tests = {nom: Kld(KLD / f"{nom}.kld") for nom in BETA}
    tests["ref"] = Kld(REF)                                 # information : KL(ref ‖ P0) se calcule à part, base = ref
    for nom, x in tests.items():
        assert (x.n_ctx, x.n_vocab, x.n_fen) == (base.n_ctx, base.n_vocab, base.n_fen), nom
        assert (x.jetons == base.jetons).all(), nom
    n = base.n
    R = {"i1": np.zeros(n, np.int64), "marge": np.zeros(n), "somme": np.zeros(n)}
    S = {nom: {"kl16": np.zeros(n), "kl_tout": np.zeros(n), "kl_renorm": np.zeros(n), "i1": np.zeros(n, np.int64), "somme": np.zeros(n)}
         for nom in tests}
    S["ref"]["kl_ref_P0"] = np.zeros(n)                      # KL(ref ‖ P0), sens du juge contre la référence f64
    i = 0
    while i < n:
        k = min(PAQUET, n - i)
        lp = base.lire(k)
        p = np.exp(lp)
        sp = p.sum(1)
        i1, mg = deux(lp)
        sl = slice(i, i + k)
        R["i1"][sl], R["marge"][sl], R["somme"][sl] = i1, mg, sp
        lpn = lp - np.log(sp)[:, None]
        pn = np.exp(lpn)
        for nom, x in tests.items():
            lq = x.lire(k)
            dd = p * (lp - lq)
            S[nom]["kl16"][sl] = np.where(lp > -16.0, dd, 0.0).sum(1)
            S[nom]["kl_tout"][sl] = dd.sum(1)
            sq = np.exp(lq).sum(1)
            S[nom]["kl_renorm"][sl] = (pn * (lpn - (lq - np.log(sq)[:, None]))).sum(1)
            S[nom]["somme"][sl] = sq
            S[nom]["i1"][sl] = lq.argmax(1)
            if nom == "ref":
                q = np.exp(lq)
                S[nom]["kl_ref_P0"][sl] = np.where(lq > -16.0, q * (lq - lp), 0.0).sum(1)
        i += k
        if i % 400 == 0:
            print("positions", i, flush=True)
    SORTIE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(SORTIE / "positions.npz", **{f"P0_{a}": b for a, b in R.items()},
                        **{f"{nom}__{a}": b for nom, d in S.items() for a, b in d.items()}, par_fen=base.par_fen)
    print("fini", flush=True)


# ---------------------------------------------------------------- analyse
def boot(num, den, fen, nfen=10, tirages=20000, graine=1):
    a = np.bincount(fen, weights=num, minlength=nfen)
    m = np.bincount(fen, weights=den, minlength=nfen)
    rng = np.random.default_rng(graine)
    idx = rng.integers(0, nfen, size=(tirages, nfen))
    v = a[idx].sum(1) / m[idx].sum(1)
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))], v


def analyse():
    z = np.load(SORTIE / "positions.npz")
    pf = int(z["par_fen"])
    n = len(z["P0_i1"])
    fen = np.arange(n) // pf
    marge = z["P0_marge"]
    msk = marge >= 0.3
    D = lire_json(SORTIE / "defauts.json")
    d0 = D["passes"]["P0"]["moi"]
    out = {"n": n, "par_fen": pf, "positions_marge>=0.3": int(msk.sum()),
           "somme_p_P0_min_max": [float(z["P0_somme"].min()), float(z["P0_somme"].max())], "passes": {}}
    for nom in list(BETA) + ["ref"]:
        acc = z["P0_i1"] == z[f"{nom}__i1"]
        k16 = z[f"{nom}__kl16"]
        d = {"kl16": float(k16.mean()), "kl_tout": float(z[f"{nom}__kl_tout"].mean()), "kl_renorm": float(z[f"{nom}__kl_renorm"].mean()),
             "litteral": float(acc.mean()), "desaccords": int((~acc).sum()),
             "pondere": float(acc[msk].mean()), "desaccords_ponderes": int((~acc & msk).sum())}
        d["kl_ic"], vk = boot(k16, np.ones(n), fen)
        d["litteral_ic"], _ = boot(acc.astype(float), np.ones(n), fen)
        d["pondere_ic"], vp = boot((acc & msk).astype(float), msk.astype(float), fen)
        d["part_tirages_kl_>0.038"] = float((vk > 0.038).mean())
        d["part_tirages_pondere_<0.95"] = float((vp < 0.95).mean())
        d["kl_par_fenetre"] = [float(k16[fen == w].mean()) for w in range(10)]
        d["pondere_par_fenetre"] = [float(acc[(fen == w) & msk].mean()) for w in range(10)]
        d["kl_mediane"], d["kl_p99"] = float(np.median(k16)), float(np.quantile(k16, 0.99))
        if nom == "ref":
            d["kl_ref_P0"] = float(z["ref__kl_ref_P0"].mean())
        else:
            dfx = D["passes"][nom]["moi"]
            d["defauts"], d["variation"] = dfx, dfx / d0 - 1
            g1, g2, g3, g3l = d["variation"] <= -0.10, d["kl16"] <= 0.038, d["pondere"] >= 0.95, d["litteral"] >= 0.95
            d["verdict_pondere"] = "TIENT" if (g1 and g2 and g3) else ("TOMBE" if d["kl16"] > 0.07 else "NON CONCLUANT")
            d["verdict_litteral"] = "TIENT" if (g1 and g2 and g3l) else ("TOMBE" if d["kl16"] > 0.07 else "NON CONCLUANT")
            # bornes : verdict pondéré à la borne défavorable de chaque intervalle
            d["verdict_pondere_bornes_defavorables"] = "TIENT" if (g1 and d["kl_ic"][1] <= 0.038 and d["pondere_ic"][0] >= 0.95) else "NE TIENT PAS"
        out["passes"][nom] = d
        print(nom, {k: (round(v, 6) if isinstance(v, float) else v) for k, v in d.items() if not isinstance(v, list)}, flush=True)
    # cassure d'instrument : décalage d'une position
    acc_dec = z["P0_i1"][1:] == z["B0.041__i1"][:-1]
    out["cassure_decalage_1_pondere"] = float(acc_dec[msk[1:]].mean())
    # sensibilité au seuil de marge (post hoc, aucun seuil changé)
    out["sensibilite_marge"] = {}
    for s in (0.1, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5):
        m_ = marge >= s
        out["sensibilite_marge"][str(s)] = {nom: float((z["P0_i1"] == z[f"{nom}__i1"])[m_].mean()) for nom in BETA} | {"n": int(m_.sum())}
    print("sensibilite", out["sensibilite_marge"], flush=True)
    ecrire("analyse.json", out)


def graines():
    """Les bornes au bord du seuil dépendent-elles de la graine du rééchantillonnage ? 20 graines, et blocs de 51 positions."""
    z = np.load(SORTIE / "positions.npz")
    pf = int(z["par_fen"])
    n = len(z["P0_i1"])
    fen = np.arange(n) // pf
    m = z["P0_marge"] >= 0.3
    out = {}
    for nom in ("B0.041", "B0.05"):
        acc = z["P0_i1"] == z[f"{nom}__i1"]
        k = z[f"{nom}__kl16"]
        lo = [boot((acc & m).astype(float), m.astype(float), fen, graine=g)[0][0] for g in range(1, 21)]
        hi = [boot(k, np.ones(n), fen, graine=g)[0][1] for g in range(1, 21)]
        b = np.arange(n) // 51
        out[nom] = {"pondere_borne_basse_min_max": [min(lo), max(lo)], "graines_sous_95": sum(x < 0.95 for x in lo),
                    "kl_borne_haute_min_max": [min(hi), max(hi)], "graines_kl_au_dessus_0.038": sum(x > 0.038 for x in hi),
                    "blocs51_pondere": boot((acc & m).astype(float), m.astype(float), b, nfen=n // 51)[0],
                    "blocs51_kl": boot(k, np.ones(n), b, nfen=n // 51)[0]}
        print(nom, out[nom], flush=True)
    ecrire("graines.json", out)


def comparer():
    z = np.load(SORTIE / "positions.npz")
    res = {}
    for nom in BETA:
        with open(MES / f"juge-kl-{nom}.csv", encoding="utf-8") as f:
            j = list(csv.DictReader(f))
        assert len(j) == len(z["P0_i1"]), (nom, len(j))
        cles = list(j[0].keys())
        kj = np.array([float(x["kl"]) for x in j])
        mj = np.array([int(x["meme_premier"]) for x in j])
        km = z[f"{nom}__kl16"]
        mm = (z["P0_i1"] == z[f"{nom}__i1"]).astype(int)
        res[nom] = {"colonnes": cles, "kl_moi": float(km.mean()), "kl_juge": float(kj.mean()), "ecart_abs_max": float(np.abs(km - kj).max()),
                    "positions_premier_different": int((mm != mj).sum())}
        print(nom, res[nom], flush=True)
    ecrire("comparaison-juge-kl.json", res)


# ---------------------------------------------------------------- noyau (sans carte)
def emule_noyau(z, b, k=K, poids_biaises=False):
    """Lecture ligne à ligne de `routeur_topk_biais` (passe.cuh) : score f32 z + b, k tours de « meilleur » (plus grande
    valeur, puis plus petit indice), puis tri par insertion sur le logit NON biaisé, poids softmax f64 des logits non biaisés.
    `poids_biaises` : variante fautive (fuite du biais dans les poids), pour la cassure."""
    v = (z.astype(np.float32) + b.astype(np.float32)).astype(np.float32)
    pris = np.zeros(len(z), bool)
    ch = []
    for _ in range(k):
        cand = [(float(v[e]), -e) for e in range(len(z)) if not pris[e]]
        _, me = max(cand)
        pris[-me] = True
        ch.append(-me)
    u = z.astype(np.float32)[ch] if not poids_biaises else v[ch]
    ordre = sorted(range(k), key=lambda r: (-float(z[ch[r]]), ch[r]))
    ch = [ch[r] for r in ordre]
    u = np.array([u[r] for r in ordre], np.float64)
    e = np.exp(u - u[0])
    return ch, (e / e.sum()).astype(np.float32)


def noyau():
    rng = np.random.default_rng(2026)
    r = {"tirages": 0, "theoreme_viole": 0, "ordre_depend_du_biais": 0, "poids_hors_logits_non_biaises": 0, "beta0_different": 0,
         "cassure_fuite_poids_detectee": 0, "egalites_f32_creees": 0}
    for it in range(20000):
        z = (rng.normal(0, 1.5, E) * (4 if it % 2 else 1)).astype(np.float32)
        if it % 5 == 0:                                     # égalités forcées
            z = (np.round(z * 4) / 4).astype(np.float32)
        pres = rng.random(E) < 0.31
        beta = float(rng.choice([0.041, 0.05, 0.3, 1.0]))
        b = np.where(pres, beta, 0.0).astype(np.float32)
        s0, w0 = emule_noyau(z, np.zeros(E, np.float32))
        sb, wb = emule_noyau(z, b)
        r["tirages"] += 1
        S0, Sb = set(s0), set(sb)
        if not (Sb >= (S0 & set(np.nonzero(pres)[0])) and all(pres[x] for x in Sb - S0) and all(not pres[x] for x in S0 - Sb)):
            r["theoreme_viole"] += 1
        if sb != sorted(sb, key=lambda e: (-float(z[e]), e)):
            r["ordre_depend_du_biais"] += 1
        zz = z.astype(np.float64)[sb]
        ref = np.exp(zz - zz.max())
        if not np.allclose(wb, (ref / ref.sum()).astype(np.float32), rtol=0, atol=1e-7):
            r["poids_hors_logits_non_biaises"] += 1
        s00, w00 = emule_noyau(z, np.zeros(E, np.float32))
        top = sorted(range(E), key=lambda e: (-float(z[e]), e))[:K]
        if s00 != top:
            r["beta0_different"] += 1
        _, wf = emule_noyau(z, b, poids_biaises=True)
        if not np.array_equal(wf, wb):
            r["cassure_fuite_poids_detectee"] += 1
        vb = z + b
        if len(set(vb.tolist())) < len(set(z.tolist())):
            r["egalites_f32_creees"] += 1
    print(r, flush=True)
    ecrire("noyau.json", r)


if __name__ == "__main__":
    {"graines": graines, "noyau": noyau, "empreintes": empreintes, "defauts": defauts, "cellules": cellules, "kl": kl, "analyse": analyse, "comparer": comparer}[sys.argv[1]]()
