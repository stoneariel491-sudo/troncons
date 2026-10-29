"""Le toit (roofline) de troncons : plafond de jetons par seconde selon l'étage d'où viennent les
poids, et facteur de compression qui rend la lecture disque aussi rapide que la PCIe.

Les débits viennent de fondations/journaux/01-machine/debits-mesures.json (chaque valeur y porte le
journal qui la produit). Rien n'est saisi à la main ici.

Modèle physique (dérivé dans 01-machine.md, § 7) : un jeton lit B octets de poids. Une fraction f_V
réside en VRAM, f_R en RAM hôte (lue par la carte à travers la PCIe, sans copie), f_D sur le disque
(disque -> RAM -> PCIe -> carte), stockée compressée d'un facteur r (octets servis / octets stockés).
Octets qui traversent chaque étage par jeton :
  VRAM : f_V B        PCIe : (f_R + f_D) B        disque : f_D B / r
Avec recouvrement parfait des étages : t = max_i(O_i / D_i) ; sans recouvrement : t = somme.
Le décodage d'un flux compressé ajoute un étage de calcul : f_D B / D_dec (débit de sortie du
décodeur). Le plafond est 1/t.

Bibliothèque standard seulement. Usage :
  python -I -X utf8 outils/banc/toit.py [--debits JSON] [--csv-dossier DOSSIER]
"""
import argparse
import json
import os

ICI = os.path.dirname(os.path.abspath(__file__))
DEFAUT = os.path.join(ICI, "..", "..", "fondations", "journaux", "01-machine", "debits-mesures.json")


def temps(B, fV, fR, fD, r, D, recouvrement=True, D_dec=None, decode_carte=False):
    """Temps par jeton (s) ; D : débits en o/s (vram, pcie, disque).

    decode_carte=False (architecture A) : le processeur décompresse, la PCIe porte les octets servis.
    decode_carte=True (architecture B) : la carte décompresse, la PCIe porte les octets compressés.
    """
    pcie = (fR + (fD / r if decode_carte else fD)) * B
    t = [fV * B / D["vram"], pcie / D["pcie"], fD * B / (r * D["disque"])]
    if D_dec and fD > 0:
        t.append(fD * B / D_dec)
    return max(t) if recouvrement else sum(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debits", default=DEFAUT)
    ap.add_argument("--csv-dossier")
    a = ap.parse_args()
    J = json.load(open(a.debits, encoding="utf-8"))
    D = {k: J[k]["go_s"] * 1e9 for k in ("vram", "pcie", "disque")}
    print("Débits retenus (Go/s) :", {k: J[k]["go_s"] for k in D})
    r_croise = D["pcie"] / D["disque"]
    print(f"\nFacteur de compression qui rend le disque aussi rapide que la PCIe : r* = {r_croise:.2f}")
    print(f"Avec le débit annoncé du disque ({J['disque_annonce']['go_s']} Go/s) : "
          f"{D['pcie'] / (J['disque_annonce']['go_s'] * 1e9):.2f}")
    alu = J["decodage_carte"]["t_op_s"] * 1e12
    print(f"Budget de calcul de la carte par octet compressé, à l'entrée r* x disque = PCIe : "
          f"{alu / D['pcie']:.0f} opérations par octet")

    lignes = []
    print("\nPlafonds de jetons/s par modèle (recouvrement parfait) :")
    print(f"{'modèle':42s} {'B Go':>6s} {'VRAM':>7s} {'PCIe':>7s} {'disque':>7s} {'disque r*':>9s}")
    for m in J["modeles"]:
        B = m["octets_par_jeton_go"] * 1e9
        v = 1 / temps(B, 1, 0, 0, 1, D)
        p = 1 / temps(B, 0, 1, 0, 1, D)
        d = 1 / temps(B, 0, 0, 1, 1, D)
        dr = 1 / temps(B, 0, 0, 1, r_croise, D)
        print(f"{m['nom']:42s} {m['octets_par_jeton_go']:6.2f} {v:7.2f} {p:7.2f} {d:7.2f} {dr:9.2f}")
        lignes.append((m["nom"], m["octets_par_jeton_go"], v, p, d, dr))

    # Placement réel du 9B sur cette machine : VRAM utile V, RAM utile R (hypothèses dans le JSON).
    cap = J["capacites"]
    print(f"\nPlacement glouton (VRAM {cap['vram_poids_go']} Go, RAM {cap['ram_poids_go']} Go pour les poids) : "
          "les toujours-lus d'abord en VRAM, puis RAM, puis disque ; les experts (fichier restant) remplissent "
          "le reste dans le même ordre, routage uniforme, aucun cache dynamique :")
    placements = []
    for m in J["modeles"]:
        F, A, E = m["fichier_go"], m["toujours_go"], m["experts_go"]
        V, R = cap["vram_poids_go"], cap["ram_poids_go"]
        aV = min(A, V); aR = min(A - aV, R); aD = A - aV - aR          # toujours-lus, en Go par jeton
        Ef = max(F - A, 1e-9)                                            # fichier des experts (et reste)
        eV = min(Ef, V - aV); eR = min(Ef - eV, R - aR); eD = Ef - eV - eR
        # Octets par jeton venant de chaque étage :
        bV = aV + E * eV / Ef; bR = aR + E * eR / Ef; bD = aD + E * eD / Ef
        B = bV + bR + bD
        for r in (1, 2, r_croise, 8):
            t1 = temps(B * 1e9, bV / B, bR / B, bD / B, r, D)
            t0 = temps(B * 1e9, bV / B, bR / B, bD / B, r, D, recouvrement=False)
            print(f"  {m['nom']:34s} VRAM {bV:5.2f} RAM {bR:5.2f} disque {bD:5.2f} Go/jeton, r={r:4.2f} : "
                  f"{1 / t1:6.2f} j/s (recouvert) ; {1 / t0:6.2f} j/s (en série)")
            placements.append((m["nom"], bV, bR, bD, r, 1 / t1, 1 / t0))
    courbe = []
    # Courbe pour la figure : plafond tout-disque du 9B contre r.
    # Architecture B : le décodeur de la carte borne la sortie. D_dec = décodage 4 bits mesuré depuis
    # les registres (poids/s) x 5,08 bits servis par poids / 8 : borne haute, sans décodage entropique.
    B9 = J["modeles"][0]["octets_par_jeton_go"] * 1e9
    D_dec = J["decodage_carte"]["t_poids_s"] * 1e12 * 5.08 / 8
    print(f"\nArchitecture B (la carte décompresse) : borne du décodeur {D_dec / 1e9:.0f} Go/s servis "
          "(1,31 T poids/s x 5,08 bits / 8, borne haute)")
    print(f"Budget de calcul par octet compressé, au débit du disque : {alu / D['disque']:.0f} opérations")
    for r in (1, 2, r_croise, 8, 16):
        ja = 1 / temps(B9, 0, 0, 1, r, D)
        jb = 1 / temps(B9, 0, 0, 1, r, D, D_dec=D_dec, decode_carte=True)
        print(f"  9B tout sur disque, r={r:5.2f} : A {ja:5.2f} j/s ; B {jb:5.2f} j/s")
    for i in range(1, 161):
        r = i / 10
        courbe.append((r, 1 / temps(B9, 0, 0, 1, r, D),
                       1 / temps(B9, 0, 0, 1, r, D, D_dec=D_dec, decode_carte=True)))
    if a.csv_dossier:
        with open(os.path.join(a.csv_dossier, "toit-modeles.csv"), "w", encoding="utf-8") as f:
            f.write("modele,octets_par_jeton_go,js_vram,js_pcie,js_disque,js_disque_rstar\n")
            for l in lignes:
                f.write(f"\"{l[0]}\",{l[1]},{l[2]:.4f},{l[3]:.4f},{l[4]:.4f},{l[5]:.4f}\n")
        with open(os.path.join(a.csv_dossier, "toit-9b-compression.csv"), "w", encoding="utf-8") as f:
            f.write("r,jetons_s_A,jetons_s_B\n")
            for r, ja, jb in courbe:
                f.write(f"{r:.1f},{ja:.4f},{jb:.4f}\n")
        with open(os.path.join(a.csv_dossier, "toit-placements.csv"), "w", encoding="utf-8") as f:
            f.write("modele,go_vram,go_ram,go_disque,r,js_recouvert,js_serie\n")
            for p in placements:
                f.write(f"\"{p[0]}\",{p[1]:.3f},{p[2]:.3f},{p[3]:.3f},{p[4]:.2f},{p[5]:.4f},{p[6]:.4f}\n")
        print("\nCSV écrits dans", a.csv_dossier)


if __name__ == "__main__":
    main()
