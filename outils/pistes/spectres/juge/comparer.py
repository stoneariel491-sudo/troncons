"""Juge de la piste « spectres » : comparaison du chemin du juge au tableau publié (ajustements.out).

Seuils J1 à J4 : genome/pistes/spectres/juge-seuil.md.
Usage : python comparer.py [juge-csn.csv | juge-csn-rapide.csv]
"""
import csv
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
PUBLIE = RACINE / "mesures/pistes/spectres/ajustements.out"
JUGE = RACINE / "mesures/pistes/spectres/juge"


def vrai(s):
    return str(s).strip() == "True"


def main():
    nom = sys.argv[1] if len(sys.argv) > 1 else "juge-csn.csv"
    with open(PUBLIE, encoding="utf-8") as fh:
        pub = {r["id"]: r for r in csv.DictReader(fh)}
    with open(JUGE / nom, encoding="utf-8") as fh:
        lignes = list(csv.DictReader(fh))
    reel = {r["id"]: r for r in lignes if r["groupe"] == "réel"}
    perm = {r["id"]: r for r in lignes if r["groupe"] == "permuté"}
    assert set(reel) == set(pub) and len(reel) == 48, "ensembles de matrices différents"
    avec_gof = reel[next(iter(reel))]["p_gof"] not in ("", "None")
    out = []

    def dire(s):
        print(s)
        out.append(s)

    # J1
    n_pl = sum(r["verdict"] == "loi de puissance" for r in reel.values())
    n_pl_pub = sum(r["verdict"] == "loi de puissance" for r in pub.values())
    rmax = max(float(r["R_ln"]) for r in lignes)
    dire(f"J1 verdict principal : juge {n_pl}/48, publié {n_pl_pub}/48 ; R_ln max (toutes lignes du juge) {rmax:.3e}"
         f" -> {'TIENT' if n_pl == 0 and rmax <= 1e-6 else 'TOMBE'}")
    dv = [i for i in reel if reel[i]["verdict"] != pub[i]["verdict"]]
    dire(f"   verdicts principaux différents : {len(dv)} {dv}")

    # J3
    eg, dmax, ecarts = 0, 0.0, []
    for i in reel:
        xj, xp = float(reel[i]["x_min"]), float(pub[i]["x_min"])
        aj, ap = float(reel[i]["alpha"]), float(pub[i]["alpha"])
        e = abs(aj - ap) / ap
        ecarts.append(e)
        if abs(xj - xp) <= 1e-9 * abs(xp):
            eg += 1
            dmax = max(dmax, e)
    ecarts.sort()
    dire(f"J3 lambda_min égaux {eg}/48 ; écart relatif max de alpha là où égaux {dmax:.2e} ; "
         f"médian sur 48 {ecarts[24]:.2e}, max {ecarts[-1]:.2e} -> {'TIENT' if eg >= 40 and dmax <= 1e-6 else 'TOMBE'}")
    # contrôle des permutés publiés
    dpm = max(abs(float(perm[i]["alpha"]) - float(pub[i]["perm_alpha"])) / float(pub[i]["perm_alpha"]) for i in perm)
    dire(f"   alpha des permutés : écart relatif max au publié {dpm:.2e}")

    # J4
    plus = [i for i in reel if float(reel[i]["alpha"]) < float(perm[i]["alpha"])]
    dire(f"J4 alpha réel < alpha permuté : {len(plus)}/48 -> {'TIENT' if len(plus) == 48 else 'TOMBE'}")
    ratio = sorted(float(perm[i]["alpha"]) / float(reel[i]["alpha"]) for i in reel)
    dire(f"   rapport alpha permuté / réel : min {ratio[0]:.2f}, médian {ratio[24]:.2f}, max {ratio[-1]:.2f}")

    # J2
    if avec_gof:
        cj = {i for i in reel if vrai(reel[i]["compatible"])}
        cp = {i for i in pub if vrai(pub[i]["compatible"])}
        accord = sum((i in cj) == (i in cp) for i in reel)
        des = sorted(cj ^ cp)

        def au_bord(i):
            for src, kexp, kln, kg in ((reel[i], "p_exp", "p_ln", "p_gof"), (pub[i], "p_exp", "p_lognormale", "p_gof")):
                pe, pl, pg = float(src[kexp]), float(src[kln]), float(src[kg])
                if 0.01 <= pe <= 0.1 or 0.03 <= pg <= 0.25 or 0.01 <= pl <= 0.1:
                    return True
            return False

        bord = all(au_bord(i) for i in des)
        ok = abs(len(cj) - 9) <= 1 and len(cj) < 32 and accord >= 45 and bord
        dire(f"J2 compatibles : juge {len(cj)}/48, publié {len(cp)}/48 ; accord {accord}/48 ; désaccords {des} "
             f"(tous au bord : {bord}) -> {'TIENT' if ok else 'TOMBE'}")
        for i in des:
            dire(f"   {i}: juge p_exp={float(reel[i]['p_exp']):.4f} p_ln={float(reel[i]['p_ln']):.4f} "
                 f"p_gof={float(reel[i]['p_gof']):.2f} | publié p_exp={float(pub[i]['p_exp']):.4f} "
                 f"p_ln={float(pub[i]['p_lognormale']):.4f} p_gof={float(pub[i]['p_gof']):.2f}")
        pc = sum(vrai(r["compatible"]) for r in perm.values())
        dire(f"   permutés compatibles : juge {pc}/48, publié {sum(vrai(r['perm_compatible']) for r in pub.values())}/48")
        for fam, test in (("gate", lambda i: ".gate." in i), ("up", lambda i: ".up." in i),
                          ("down", lambda i: ".down." in i), ("attention", lambda i: ".attn_" in i)):
            dire(f"   famille {fam}: juge {sum(test(i) for i in cj)}/12, publié {sum(test(i) for i in cp)}/12")
        gofd = sorted(abs(float(reel[i]["p_gof"]) - float(pub[i]["p_gof"])) for i in reel)
        dire(f"   |p_gof juge - publié| : médian {gofd[24]:.2f}, max {gofd[-1]:.2f}")
    else:
        dire("J2 : pas de p_gof dans ce fichier (passe sans répliques), non jugé ici")

    (JUGE / ("comparaison-" + nom.replace(".csv", ".txt"))).write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
