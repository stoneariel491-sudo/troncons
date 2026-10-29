# Juge de la troisième passe : refait à la source, par un troisième chemin, les nombres neufs de la tête de III-9.7
# (rapport ‖ΔW_s x‖ / ‖ΔW_f x‖ sur les 1 329 entrées réelles entières : min, médiane, max, part sous 0,135 ; angle
# médian d'une entrée au plan (u1, u2) ; part de la trace hors des trois axes ; rapport des projections sur (u1, u2)).
# Lectures écrites ici, d'après les formats décrits (GGUF v3 ; MXFP4 de ggml : 17 octets pour 32 poids, un octet
# E8M0 puis 16 octets, le poids t dans le demi-octet faible de l'octet t, le poids 16 + t dans le fort ; .sym du lot B :
# « SYM1 », quatre centres f64 doublés, puis les symboles gate, up, down, deux par octet, le pair dans le faible ;
# symbole : classe k (bits 0-1), signe (bit 2) ; captures : h-L08.f32 positions × 2 880 f32, routage-L08.bin par
# position 4 octets d'experts puis 4 f32 de poids). Aucune ligne reprise d'un outil du lot ni des juges.
# La base frontière n'a pas de fichier : son symbole est une fonction du code ; je la prends comme le centre le plus
# proche de la grandeur E2M1, signe du code gardé (hypothèse de lecture) ; le témoin T1 la juge : ‖W − Ŵ‖²_F doit
# égaler Σ e_k du spectre commité du lot B, pour la frontière comme pour le synonyme.
# Usage : python -I -X utf8 sources_latents.py [--casser]   (--casser : centres du synonyme faux de 1 %)
import json, math, struct, sys
from pathlib import Path
import numpy as np

DEPOT = Path(__file__).resolve().parents[4]
GGUF = Path("~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf")
SYM = Path("~/dev/essais/troncons/genome/synonyme/sym/synonyme-l1-d1-P1/L08-E00.sym")
CAPT = Path("~/dev/essais/troncons/genome/eclaireur/calib")
SPECTRE = DEPOT / "mesures/genome/construction/synonyme/figures/spectre-L08-E00-gate.csv"
NUAGE = DEPOT / "mesures/genome/tome3/latents/nuage-L08-E00-gate.json"
CASSER = "--casser" in sys.argv
N = 2880
E2M1 = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0])


def lire_gguf_tenseur(nom: str):
    with open(GGUF, "rb") as f:
        assert f.read(4) == b"GGUF"
        version, n_t, n_kv = struct.unpack("<IQQ", f.read(20))
        TAILLES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}

        def chaine():
            n, = struct.unpack("<Q", f.read(8))
            return f.read(n).decode("utf-8", "replace")

        def valeur(t):
            if t == 8:
                return chaine()
            if t == 9:
                ta, n = struct.unpack("<IQ", f.read(12))
                return [valeur(ta) for _ in range(n)]
            b = f.read(TAILLES[t])
            return struct.unpack({0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q",
                                  11: "<q", 12: "<d"}[t], b)[0]

        meta = {}
        for _ in range(n_kv):
            k = chaine()
            t, = struct.unpack("<I", f.read(4))
            v = valeur(t)
            if not isinstance(v, list) or len(v) < 50:
                meta[k] = v
        fiches = {}
        for _ in range(n_t):
            nm = chaine()
            nd, = struct.unpack("<I", f.read(4))
            dims = struct.unpack(f"<{nd}Q", f.read(8 * nd))
            ty, off = struct.unpack("<IQ", f.read(12))
            fiches[nm] = (dims, ty, off)
        al = meta.get("general.alignment", 32)
        debut = (f.tell() + al - 1) // al * al
    return version, fiches[nom], debut


def main():
    version, (dims, ty, off), debut = lire_gguf_tenseur("blk.8.ffn_gate_exps.weight")
    assert ty == 39 and dims[0] == N and dims[1] == N, (ty, dims)
    nblocs = N * N // 32
    with open(GGUF, "rb") as f:
        f.seek(debut + off)              # expert 0 : le premier
        brut = np.frombuffer(f.read(nblocs * 17), dtype=np.uint8).reshape(nblocs, 17)
    e = brut[:, 0].astype(np.int64)
    q = brut[:, 1:]
    codes = np.concatenate([q & 0x0F, q >> 4], axis=1)          # (blocs, 32) : t puis 16 + t
    s_b = np.exp2(e - 127.0)
    signe = np.where(codes & 8, -1.0, 1.0)
    W = (signe * E2M1[codes & 7] * s_b[:, None]).reshape(N, N)  # lignes = sorties, colonnes = entrées
    # .sym du synonyme
    s = SYM.read_bytes()
    assert s[:4] == b"SYM1"
    centres = np.array(struct.unpack("<4d", s[4:36])) / 2.0
    if CASSER:
        centres = centres * 1.01
    octets = np.frombuffer(s[36:36 + N * N // 2], dtype=np.uint8)
    sym = np.empty(N * N, dtype=np.uint8)
    sym[0::2] = octets & 0x0F
    sym[1::2] = octets >> 4
    sym = sym.reshape(nblocs, 32)
    Ws = (np.where(sym & 4, -1.0, 1.0) * centres[sym & 3] * s_b[:, None]).reshape(N, N)
    # frontière : centre le plus proche de la grandeur E2M1 du code, signe du code
    k_f = np.abs(E2M1[:, None] - centres[None, :]).argmin(axis=1)    # grandeur 0..7 → classe
    Wf = (signe * centres[k_f[codes & 7]] * s_b[:, None]).reshape(N, N)
    dWf, dWs = W - Wf, W - Ws
    # témoin T1 : énergie de l'erreur contre Σ e_k du spectre commité
    sp = np.genfromtxt(SPECTRE, delimiter=",", names=True)
    T1 = {"frontiere": (float((dWf ** 2).sum()), float(sp["e_frontiere"].sum())),
          "synonyme": (float((dWs ** 2).sum()), float(sp["e_synonyme"].sum()))}
    # les entrées de l'expert 0
    rout = np.fromfile(CAPT / "routage-L08.bin", dtype=np.uint8).reshape(-1, 20)
    exp = rout[:, :4]
    poids = rout[:, 4:].copy().view("<f4").reshape(-1, 4)
    sel = (exp == 0).any(axis=1)
    g = (poids * (exp == 0)).sum(axis=1)[sel].astype(np.float64)
    H_all = np.fromfile(CAPT / "h-L08.f32", dtype="<f4").reshape(-1, N)
    assert H_all.shape[0] == rout.shape[0]
    X = H_all[sel].astype(np.float64)
    n = X.shape[0]
    # le rapport, entrée par entrée, dans les 2 880 dimensions
    rf = np.linalg.norm(X @ dWf.T, axis=1)
    rs = np.linalg.norm(X @ dWs.T, axis=1)
    r = rs / rf
    # H et ses axes ; témoin T2 : λ1..λ3 contre le JSON du lot
    w2 = g ** 2
    Hm = (X * w2[:, None]).T @ X / w2.sum()
    lam, U = np.linalg.eigh(Hm)
    lam, U = lam[::-1], U[:, ::-1]
    nj = json.loads(NUAGE.read_text(encoding="utf-8"))
    T2 = float(max(abs(a - b) / b for a, b in zip(lam[:3], nj["lambda_1_3"])))
    P = X @ U[:, :2]
    cos_plan = np.linalg.norm(P, axis=1) / np.linalg.norm(X, axis=1)
    angle = np.degrees(np.arccos(np.clip(cos_plan, 0, 1)))
    part3 = float(lam[:3].sum() / lam.sum())
    # rapport des projections : direction unité de la projection sur (u1, u2), rapport ‖ΔW_s v‖/‖ΔW_f v‖
    V = P / np.linalg.norm(P, axis=1, keepdims=True) @ U[:, :2].T
    rp = np.linalg.norm(V @ dWs.T, axis=1) / np.linalg.norm(V @ dWf.T, axis=1)
    # rapport quadratique pondéré (témoin E1 refait) : √(Σ g² ‖ΔW_s x‖² / Σ g² ‖ΔW_f x‖²)
    rq = math.sqrt(float((w2 * rs ** 2).sum() / (w2 * rf ** 2).sum()))
    rq_spectre = math.sqrt(float((sp["lambda_calib"] * sp["e_synonyme"]).sum() / (sp["lambda_calib"] * sp["e_frontiere"]).sum()))
    res = {
        "gguf_version": version, "entrees": n, "centres_c_k": centres.tolist(),
        "T1_energie_contre_spectre": {k: {"juge3": a, "spectre": b, "ecart_relatif": abs(a - b) / b} for k, (a, b) in T1.items()},
        "T2_lambda_ecart_relatif_max": T2, "lambda_1_3": lam[:3].tolist(),
        "rapport_par_entree": {"min": float(r.min()), "q10": float(np.quantile(r, 0.1)), "mediane": float(np.median(r)),
                               "q90": float(np.quantile(r, 0.9)), "max": float(r.max()),
                               "part_sous_0_135": float((r < 0.135).mean())},
        "angle_au_plan_u1_u2_deg": {"min": float(angle.min()), "mediane": float(np.median(angle))},
        "part_trace_hors_trois_axes": 1 - part3,
        "projections_u1_u2": {"mediane": float(np.median(rp)), "max": float(rp.max()), "part_sous_0_135": float((rp < 0.135).mean())},
        "rapport_quadratique_pondere": {"entrees": rq, "spectre": rq_spectre},
        "casser": CASSER,
    }
    tient = all(v["ecart_relatif"] < 1e-9 for v in res["T1_energie_contre_spectre"].values()) and T2 < 1e-9 and n == 1329
    res["temoins_tiennent"] = bool(tient)
    print(json.dumps(res, ensure_ascii=False, indent=1))


main()
