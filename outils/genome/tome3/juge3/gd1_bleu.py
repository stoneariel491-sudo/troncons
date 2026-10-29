# Juge de la troisième passe : GD1, le bleu au rendu. Pour chaque page de figure donnée, rend la zone de la figure
# (du haut de la page au début de la légende, « Figure n.m ») à 200 dpi et compte les pixels à ΔE CIE76 < 10 (CIELAB,
# D65, conversion écrite ici) du bleu 1F5C99 ou d'une de ses teintes (mélange avec le blanc, 8 % à 100 %, comme
# xcolor « !t »). Règle déclarée (JUGEMENT-figures3.md § 1.3) : 0 pixel sur les huit figures de GD1. Témoin : la page
# de III-9.6 (synonyme λ = 1 en bleu, sens du dictionnaire) doit en compter ; cassure : un seuil de ΔE à 0 n'en compte
# aucun nulle part (le témoin tombe).
# Usage : python -I -X utf8 gd1_bleu.py [--casser]
import json, re, sys
from pathlib import Path
import fitz
import numpy as np

DEPOT = Path(__file__).resolve().parents[4]
P = DEPOT / "memoire/essai/juge3/pilotes"
SEUIL = 0.0 if "--casser" in sys.argv else 10.0
PAGES = {"ronde": {6: "III-2.1", 10: "III-4.8", 12: "III-7.2"},
         "construction": {4: "III-8.1", 5: "III-8.2", 7: "III-8.4", 8: "III-8.5", 11: "III-8.7", 16: "III-9.6 (témoin)"}}


def lab(rgb):
    c = np.asarray(rgb, dtype=np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


bleu = np.array([0x1F, 0x5C, 0x99], dtype=np.float64)
teintes = np.array([t * bleu + (1 - t) * 255 for t in np.arange(0.08, 1.0001, 0.02)])
L_t = lab(teintes)
# Classement au plus proche (correction après le premier essai, dite dans le jugement : un fond pâle vert, rouge ou
# orange tombe à ΔE < 10 de la teinte à 8 % du bleu) : un pixel compte comme bleu si la teinte la plus proche, parmi
# celles de toutes les couleurs nommées du préambule et du dictionnaire et parmi les gris, est une teinte de 1F5C99
# (ou du bleu « Expo » 2E6DB4), à ΔE < SEUIL.
NOMMEES = ["1F5C99", "2E6DB4", "C0392B", "A7AFB8", "363D44", "2E8B57", "D68910", "1A1A1A", "B07CC6", "8B5A2B",
           "6C7A89", "8E44AD", "1F7A8C", "B9770E", "F4F6F8", "E6F1EB"]
BLEUS = {"1F5C99", "2E6DB4"}
refs, est_bleu = [], []
for h in NOMMEES:
    c = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)
    for t in np.arange(0.08, 1.0001, 0.02):
        refs.append(t * c + (1 - t) * 255)
        est_bleu.append(h in BLEUS)
for g in range(0, 256, 3):
    refs.append(np.array([g, g, g], dtype=np.float64))
    est_bleu.append(False)
L_refs = lab(np.array(refs))
est_bleu = np.array(est_bleu)
res = {}
for lot, pages in PAGES.items():
    for suf in ("", "-en"):
        D = fitz.open(P / f"pilote-tome3-{lot}{suf}.pdf")
        for n, nom in pages.items():
            pg = D[n - 1]
            hits = [fitz.Rect(b[:4]) for b in pg.get_text("blocks") if b[4].startswith("Figure ")]  # la légende (search_for ignore la casse : « figure 1.2 » d'un renvoi dans la figure la coupait)
            bas = min(h.y0 for h in hits) - 2 if hits else pg.rect.y1
            clip = fitz.Rect(0, 40, pg.rect.x1, bas)
            pm = pg.get_pixmap(dpi=200, clip=clip, alpha=False)
            a = np.frombuffer(pm.samples, np.uint8).reshape(pm.height, pm.width, 3).astype(np.float64)
            px = a.reshape(-1, 3)
            # on ne teste que les pixels non gris (un gris ne peut pas être à ΔE < 10 d'une teinte du bleu au-delà de 8 %)
            sat = px.max(axis=1) - px.min(axis=1)
            cand = px[sat > 6]
            n_bleu = 0
            if len(cand):
                Lc = lab(cand)
                dd = np.sqrt(((Lc[:, None, :] - L_refs[None, :, :]) ** 2).sum(axis=2))
                k = dd.argmin(axis=1)
                n_bleu = int(((dd[np.arange(len(k)), k] < SEUIL) & est_bleu[k]).sum())
            res[f"{nom} {lot}{suf or '-fr'} p.{n}"] = n_bleu
print(json.dumps(res, ensure_ascii=False, indent=1))
temoin = all(v > 0 for k, v in res.items() if "témoin" in k)
print("témoin (III-9.6 voit son bleu) :", "tient" if temoin else "TOMBE")
