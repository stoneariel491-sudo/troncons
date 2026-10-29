"""Juge de l'étage B de P3 : un second lecteur des .kld et du journal de routage, écrit sans reprendre p3_etageB*.py.

  python -I -X utf8 etageB_juge.py empreintes   → SHA-256 des .kld (témoin au bit) et des journaux imposés
  python -I -X utf8 etageB_juge.py defauts      → défauts du cache LRU (N = 146) rejoués depuis les journaux imposés
  python -I -X utf8 etageB_juge.py kl           → KL, premier choix et marges top-1/top-2 relus des .kld, en flux
  python -I -X utf8 etageB_juge.py comparer     → mes positions contre le CSV de `juge kl` (lu après mon calcul)

Format .kld (llama-perplexity) : "_logits_", u32 n_ctx, i32 n_vocab, i32 n_fenetres, puis i32 jetons (n_ctx × n_fenetres),
puis par position notée (fenêtre f, t de n_ctx/2 à n_ctx − 2) une entrée de nv = 2·⌈n_vocab/2⌉ + 4 mots u16 :
les deux premiers f32 (mots 0 à 3) sont le pas et log p_min, puis n_vocab codes, log p_i = pas · code_i + log p_min.
Une différence de log p entre deux jetons est une différence de logits (le log-softmax ne change que la constante).

KL par position (convention de llama.cpp, que le juge suit) : Σ_{i : log p_i > −16} p_i (log p_i − log q_i), sans renormaliser.
Je calcule aussi la KL renormalisée sur tout le vocabulaire, pour mesurer la sensibilité à la convention.
Premier choix : argmax (premier indice en cas d'égalité de codes, comme le juge) ; je compte aussi les égalités exactes.
Mémoire : PAQUET positions à la fois par fichier (~6 Mo de codes, ~30 Mo décodés), lecture séquentielle.
"""
import csv
import hashlib
import json
import pathlib
import struct
import sys
from collections import OrderedDict

import numpy as np

DEPOT = pathlib.Path(__file__).resolve().parents[4]
SORTIE = DEPOT / "mesures" / "mimetisme" / "P3" / "juge" / "etage-B"
R1 = pathlib.Path("~/dev/essais/troncons/lot-R/r1")
B = pathlib.Path("~/dev/essais/troncons/mimetisme/P3/B")
ROUTAGE_MOTEUR = DEPOT / "mesures" / "moteur" / "R" / "r1" / "routage"
PAQUET = 16

KLD = {
    "ref": "ref-openai-20b.kld",
    "T0": "ref-openai-p3-T0-20b.kld",
    "T1": "ref-openai-p3-T1-20b.kld",
    "b0.06": "ref-openai-p3-b0.06-20b.kld",
    "b0.07": "ref-openai-p3-b0.07-20b.kld",
}
JOURNAUX = {
    "T0": ("routage-impose-V1-b0.0-N19.bin", "p3-T0-N19.bin"),
    "T1": ("routage-impose-CASSURE-1pct.bin", "p3-T1-N19.bin"),
    "b0.06": ("routage-impose-V1-b0.06-N19.bin", "p3-b0.06-N19.bin"),
    "b0.07": ("routage-impose-V1-b0.07-N19.bin", "p3-b0.07-N19.bin"),
}


def sha256(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        while bloc := f.read(1 << 22):
            h.update(bloc)
    return h.hexdigest()


def empreintes():
    res = {"kld": {}, "journaux": {}}
    for nom, fichier in KLD.items():
        p = R1 / fichier
        res["kld"][nom] = {"fichier": str(p), "octets": p.stat().st_size, "sha256": sha256(p)}
        print(nom, res["kld"][nom]["sha256"], flush=True)
    res["T0_identique_au_bit"] = res["kld"]["T0"]["sha256"] == res["kld"]["ref"]["sha256"]
    for nom in ("T1", "b0.06", "b0.07"):
        res[f"{nom}_differe_de_ref"] = res["kld"][nom]["sha256"] != res["kld"]["ref"]["sha256"]
    declares = json.loads((DEPOT / "mesures" / "mimetisme" / "P3" / "fichiers-B.json").read_text(encoding="utf-8"))
    for nom, (fb, fm) in JOURNAUX.items():
        sb, sm = sha256(B / fb), sha256(ROUTAGE_MOTEUR / fm)
        res["journaux"][nom] = {"fichier_B": fb, "sha256_B": sb, "copie_lue_par_le_moteur": fm, "sha256_copie": sm,
                                "copie_egale": sb == sm, "declare_fichiers_B": declares[fb]["sha256"],
                                "egal_au_declare": sb == declares[fb]["sha256"]}
        print(nom, res["journaux"][nom], flush=True)
    ecrire("empreintes.json", res)


def lire_journal(chemin):
    """Le journal de routage : u32 couches, u32 positions, puis (couche, position) en ordre couche-major, 4 × u8 + f32."""
    d = pathlib.Path(chemin).read_bytes()
    L, T = struct.unpack_from("<II", d, 0)
    assert len(d) == 8 + L * T * 8, "taille inattendue"
    rec = np.frombuffer(d, dtype=np.dtype([("e", "u1", 4), ("m", "<f4")]), offset=8).reshape(L, T)
    return L, T, rec["e"], rec["m"]


def lru_defauts(experts, N, ordre="couche-major"):
    """LRU global sur (couche, expert), règle de groupe : les 4 experts du groupe sont épinglés pendant le groupe,
    la victime est le moins récemment servi parmi les non épinglés. Ordre : t croissant, puis l croissant ;
    dans un groupe, l'ordre du fichier. experts : (L, T, 4) si couche-major."""
    if ordre == "couche-major":
        L, T, _ = experts.shape
        acces = lambda t, l: experts[l, t]
    else:  # lecture position-major du même tampon, pour la cassure de lecture
        flat = experts.reshape(-1, 4)
        L, T = experts.shape[0], experts.shape[1]
        acces = lambda t, l: flat[t * L + l]
    cache = OrderedDict()
    defauts = 0
    for t in range(T):
        for l in range(L):
            groupe = [(l, int(e)) for e in acces(t, l)]
            epingles = set(groupe)
            for cle in groupe:
                if cle in cache:
                    cache.move_to_end(cle)
                    continue
                defauts += 1
                if len(cache) >= N:
                    for v in cache:
                        if v not in epingles:
                            break
                    del cache[v]
                cache[cle] = None
    return defauts


def defauts():
    declares = json.loads((DEPOT / "mesures" / "mimetisme" / "P3" / "fichiers-B.json").read_text(encoding="utf-8"))
    res = {}
    base = None
    for nom, (fb, _) in JOURNAUX.items():
        L, T, e, _ = lire_journal(B / fb)
        n = lru_defauts(e, 146)
        res[nom] = {"fichier": fb, "defauts": n, "acces": L * T * 4, "declare": declares[fb].get("defauts")}
        if nom == "T0":
            base = n
            # cassure de lecture : le même tampon lu en position-major doit changer le compte
            res["cassure_ordre_position_major"] = lru_defauts(e, 146, ordre="position-major")
            # cassure d'ordre dans le groupe : l'ordre inverse (règle de groupe : seul l'ordre LRU interne change)
            res["T0_ordre_inverse_dans_le_groupe"] = lru_defauts(e[:, :, ::-1].copy(), 146)
        print(nom, res[nom], flush=True)
    for nom in ("b0.06", "b0.07"):
        res[nom]["variation_relative"] = res[nom]["defauts"] / base - 1
    ecrire("defauts.json", res)


class LecteurKld:
    def __init__(self, chemin):
        self.f = open(chemin, "rb")
        h = self.f.read(20)
        assert h[:8] == b"_logits_", chemin
        self.n_ctx, self.n_vocab, self.n_fen = struct.unpack("<Iii", h[8:])
        self.nv = 2 * ((self.n_vocab + 1) // 2) + 4
        self.jetons = np.frombuffer(self.f.read(4 * self.n_ctx * self.n_fen), dtype="<i4").reshape(self.n_fen, self.n_ctx)
        self.notees = self.n_ctx - 1 - self.n_ctx // 2
        self.n = self.notees * self.n_fen
        attendu = 20 + 4 * self.n_ctx * self.n_fen + 2 * self.nv * self.n
        assert pathlib.Path(chemin).stat().st_size == attendu, "taille inattendue"

    def paquet(self, k):
        brut = np.frombuffer(self.f.read(2 * self.nv * k), dtype="<u2").reshape(k, self.nv)
        tete = brut[:, :4].copy().view("<f4")          # (k, 2) : pas, log p_min
        codes = brut[:, 4:4 + self.n_vocab]
        return tete, codes


def decoder(tete, codes):
    return codes.astype(np.float64) * tete[:, 0:1].astype(np.float64) + tete[:, 1:2].astype(np.float64)


def top2(lp, codes):
    """argmax (premier indice), marge top-1 − top-2 en logits, et égalité exacte de codes au sommet."""
    i1 = lp.argmax(axis=1)
    r = np.arange(len(lp))
    v1 = lp[r, i1]
    tmp = lp.copy()
    tmp[r, i1] = -np.inf
    i2 = tmp.argmax(axis=1)
    v2 = tmp[r, i2]
    egal = codes[r, i1] == codes[r, i2]
    return i1, i2, v1 - v2, egal


def kl():
    ref = LecteurKld(R1 / KLD["ref"])
    tests = {nom: LecteurKld(R1 / KLD[nom]) for nom in ("T1", "b0.06", "b0.07")}
    for t in tests.values():
        assert (t.n_ctx, t.n_vocab, t.n_fen) == (ref.n_ctx, ref.n_vocab, ref.n_fen)
        assert (t.jetons == ref.jetons).all(), "jetons différents"
    lignes = {nom: [] for nom in tests}
    i = 0
    while i < ref.n:
        k = min(PAQUET, ref.n - i)
        tp, cp = ref.paquet(k)
        lp = decoder(tp, cp)
        i1p, i2p, margep, egalp = top2(lp, cp)
        masque = lp > -16.0
        p = np.exp(lp)
        for nom, lec in tests.items():
            tq, cq = lec.paquet(k)
            lq = decoder(tq, cq)
            kl_ = np.where(masque, p * (lp - lq), 0.0).sum(axis=1)
            # renormalisée : P et Q ramenés à une somme de 1 sur tout le vocabulaire
            lpn = lp - np.log(p.sum(axis=1, keepdims=True))
            lqn = lq - np.log(np.exp(lq).sum(axis=1, keepdims=True))
            kl_n = (np.exp(lpn) * (lpn - lqn)).sum(axis=1)
            i1q, i2q, margeq, egalq = top2(lq, cq)
            r = np.arange(k)
            for j in range(k):
                pos = i + j
                f, t = divmod(pos, ref.notees)
                lignes[nom].append({
                    "fenetre": f, "position": ref.n_ctx // 2 + t, "kl": float(kl_[j]), "kl_renorm": float(kl_n[j]),
                    "meme_premier": int(i1p[j] == i1q[j]), "premier_ref": int(i1p[j]), "second_ref": int(i2p[j]),
                    "premier_test": int(i1q[j]), "marge_ref": float(margep[j]), "egalite_ref": int(egalp[j]),
                    "marge_test": float(margeq[j]), "egalite_test": int(egalq[j]),
                    # le premier du test est-il le second de la référence (échange des deux premiers) ?
                    "test_prend_second_ref": int(i1q[j] == i2p[j]),
                    # écart de log p de référence entre le premier de la référence et le premier du test
                    "ecart_ref_premier_test": float(lp[j, i1p[j]] - lp[j, i1q[j]]),
                })
        i += k
        if i % 255 == 0:
            print("positions", i, flush=True)
    resume = {}
    for nom, ls in lignes.items():
        with open(SORTIE / f"kl-{nom}-positions.csv", "w", newline="", encoding="utf-8") as fo:
            w = csv.DictWriter(fo, fieldnames=list(ls[0]))
            w.writeheader()
            w.writerows(ls)
        resume[nom] = analyser(ls, nom)
        print(nom, json.dumps(resume[nom], ensure_ascii=False), flush=True)
    ecrire("kl.json", resume)


def analyser(ls, nom):
    kl_ = np.array([x["kl"] for x in ls])
    kln = np.array([x["kl_renorm"] for x in ls])
    mp = np.array([x["meme_premier"] for x in ls], bool)
    mr = np.array([x["marge_ref"] for x in ls])
    eg = np.array([x["egalite_ref"] for x in ls], bool)
    sec = np.array([x["test_prend_second_ref"] for x in ls], bool)
    ecart = np.array([x["ecart_ref_premier_test"] for x in ls])
    d = ~mp
    out = {
        "n": len(ls), "kl_moyenne": kl_.mean(), "kl_renorm_moyenne": kln.mean(), "kl_mediane": float(np.median(kl_)),
        "meme_premier": mp.mean(), "desaccords": int(d.sum()),
        "egalites_exactes_au_sommet_ref": int(eg.sum()), "desaccords_sur_egalite_ref": int((d & eg).sum()),
        "desaccords_ou_test_prend_le_second_ref": int((d & sec).sum()),
    }
    for s in (0.01, 0.03, 0.1, 0.3, 1.0):
        out[f"part_positions_marge_ref<{s}"] = float((mr < s).mean())
        out[f"part_desaccords_marge_ref<{s}"] = float((mr[d] < s).mean()) if d.any() else None
        # taux de désaccord conditionnel à la marge, et hors quasi-égalités
        out[f"meme_premier_si_marge_ref>={s}"] = float(mp[mr >= s].mean())
        out[f"part_desaccords_ecart_ref<{s}"] = float((ecart[d] < s).mean()) if d.any() else None
    out["marge_ref_mediane_des_desaccords"] = float(np.median(mr[d])) if d.any() else None
    out["marge_ref_mediane_des_accords"] = float(np.median(mr[mp]))
    out["ecart_ref_mediane_des_desaccords"] = float(np.median(ecart[d])) if d.any() else None
    return out


def comparer():
    """Mes positions contre le CSV du juge (lu seulement ici, après mon calcul)."""
    res = {}
    for nom in ("T1", "b0.06", "b0.07"):
        with open(SORTIE / f"kl-{nom}-positions.csv", encoding="utf-8") as f:
            moi = list(csv.DictReader(f))
        with open(DEPOT / "mesures" / "mimetisme" / "P3" / "etage-B" / f"juge-kl-p3-{nom}.csv", encoding="utf-8") as f:
            juge = list(csv.DictReader(f))
        assert [(a["fenetre"], a["position"]) for a in moi] == [(b["fenetre"], b["position"]) for b in juge]
        km = np.array([float(a["kl"]) for a in moi]); kj = np.array([float(b["kl"]) for b in juge])
        mm = np.array([int(a["meme_premier"]) for a in moi]); mj = np.array([int(b["meme_premier"]) for b in juge])
        res[nom] = {"kl_moyenne_moi": km.mean(), "kl_moyenne_juge": kj.mean(), "ecart_abs_max_par_position": float(np.abs(km - kj).max()),
                    "ecart_rel_max_par_position": float((np.abs(km - kj) / np.maximum(kj, 1e-12)).max()),
                    "meme_premier_moi": mm.mean(), "meme_premier_juge": mj.mean(), "positions_premier_different": int((mm != mj).sum())}
        print(nom, res[nom], flush=True)
    ecrire("comparaison-juge.json", res)


def ecrire(nom, obj):
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / nom).write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=float), encoding="utf-8")


if __name__ == "__main__":
    {"empreintes": empreintes, "defauts": defauts, "kl": kl, "comparer": comparer}[sys.argv[1]]()
