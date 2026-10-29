"""P3 étage B à N = 238 : troisième chemin. Relit les .kld avec le lecteur du juge (etageB_juge.py, écrit sans le code de l'étage B),
recalcule KL, premier choix littéral et pondéré par la marge depuis les .kld (marge de la référence relue de ref-openai-20b.kld),
et rejoue les défauts de cache des journaux imposés avec le LRU du juge.
Usage : python -X utf8 p3_etageB_N238_lecteur.py
"""
import json
import pathlib
import sys

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI / "juge"))
import etageB_juge as J  # noqa: E402

DEPOT = J.DEPOT
SORTIE = DEPOT / "mesures/mimetisme/P3/etage-B/N238"
B238 = pathlib.Path("~/dev/essais/troncons/mimetisme/P3/B238")
BETAS = ["0.041", "0.05"]

ref = J.LecteurKld(J.R1 / "ref-openai-20b.kld")
tests = {b: J.LecteurKld(J.R1 / f"ref-openai-p3-N238-b{b}-20b.kld") for b in BETAS}
for t in tests.values():
    assert (t.n_ctx, t.n_vocab, t.n_fen) == (ref.n_ctx, ref.n_vocab, ref.n_fen) and (t.jetons == ref.jetons).all()
kl = {b: [] for b in BETAS}
mp = {b: [] for b in BETAS}
marge = []
i = 0
while i < ref.n:
    k = min(J.PAQUET, ref.n - i)
    tp, cp = ref.paquet(k)
    lp = J.decoder(tp, cp)
    i1p, _, mg, _ = J.top2(lp, cp)
    masque = lp > -16.0
    p = np.exp(lp)
    marge.append(mg)
    for b, lec in tests.items():
        tq, cq = lec.paquet(k)
        lq = J.decoder(tq, cq)
        kl[b].append(np.where(masque, p * (lp - lq), 0.0).sum(axis=1))
        mp[b].append(i1p == lq.argmax(axis=1))
    i += k
marge = np.concatenate(marge)
fen = np.repeat(np.arange(ref.n_fen), ref.notees)
res = {"marge_ref_mediane": float(np.median(marge)), "positions_marge>=0.3": int((marge >= 0.3).sum())}
for b in BETAS:
    k_, m_ = np.concatenate(kl[b]), np.concatenate(mp[b])
    fort = marge >= 0.3
    res[b] = {"kl_moyenne": float(k_.mean()), "premier_choix_litteral": float(m_.mean()), "premier_choix_pondere": float(m_[fort].mean()),
              "desaccords": int((~m_).sum()), "desaccords_pondere": int((~m_[fort]).sum())}
    # défauts rejoués par le LRU du juge, N = 238
    L, T, e, _ = J.lire_journal(B238 / f"routage-impose-V1-b{b}-N31.bin")
    res[b]["defauts_lru_juge_N238"] = J.lru_defauts(e, 238)
L, T, e, _ = J.lire_journal(J.B / "routage-impose-V1-b0.0-N31.bin")
res["beta0_defauts_lru_juge_N238"] = J.lru_defauts(e, 238)
# recoupement des marges avec la colonne du CSV du juge
import csv
m_csv = np.array([float(x["marge_ref"]) for x in csv.DictReader(open(DEPOT / "mesures/mimetisme/P3/juge/etage-B/kl-b0.06-positions.csv", encoding="utf-8"))])
res["ecart_max_marge_csv_vs_kld"] = float(np.abs(m_csv - marge).max())
(SORTIE / "lecteur-N238.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
