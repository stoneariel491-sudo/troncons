"""Juge indépendant de la garde tropicale : le chiffre principal refait par un autre chemin.

Ce script n'importe rien de la piste (routage.py, garde.py, second_chemin.py) ni du lot R
(bascules.py). Il relit les trois journaux de routage à partir du format déclaré dans
genome/pistes/tropicale/seuil-declare.md § 1 (u32 couches, u32 positions, puis 8 octets par
cellule : 4 × u8 experts, f32 marge, petit-boutiste, couche par couche) avec struct seul,
sans numpy.

Différences de chemin avec la piste :
- le point τ₁₀ n'est pas un seuil interpolé : on classe les 122 640 cellules par marge de B
  (clé secondaire : l'indice de la cellule) et on garde les 12 264 premières ; les ex aequo à la
  frontière sont comptés et rapportés ;
- le coût de 80 % est le plus petit nombre de cellules en tête du classement qui contient
  ceil(0,8 × bascules) bascules ;
- les racines de cascade sont recomptées par une boucle sur les positions.

Cohabitation : priorité « sous la normale » demandée au système, un seul fil, aucune carte,
aucun verrou pris ; si le verrou de la carte existe, le script attend sa disparition.
"""

import ctypes
import hashlib
import json
import math
import os
import random
import struct
import sys
import time

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
ROUTAGE = os.path.join(RACINE, "mesures", "moteur", "R", "r1", "routage")
SORTIE = os.path.join(RACINE, "mesures", "pistes", "tropicale", "juge")
VERROU = os.path.join(os.path.dirname(RACINE), "..", "verrou-carte.txt")

JOURNAUX = {
    "A": ("ref-openai-bis-20b.bin", "f0a19c1182a3db507c7ade3d49734f765372bd6d1e101e3f4d0cb9be785b8d3c"),
    "B": ("ref-llamacpp-bis-20b.bin", "07a9d4f974fd00ea8e56330865021f139025741fd63afe5b45c562336fd549d0"),
    "C": ("ref-llamacpp-routage-openai-20b.bin", "3e77be12bed8bc8be6123bdc81ccd654ca1169494dab27ae79307c2bd9a0f609"),
}

PART_CELLULES = 0.10
PART_BASCULES = 0.80


def baisser_priorite():
    if os.name != "nt":
        os.nice(10)
        return "nice 10"
    k32 = ctypes.windll.kernel32
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    ok = k32.SetPriorityClass(k32.GetCurrentProcess(), 0x00004000)  # BELOW_NORMAL
    return "BELOW_NORMAL" if ok else "échec SetPriorityClass"


def attendre_verrou():
    attendu = 0
    while os.path.exists(os.path.normpath(VERROU)):
        time.sleep(30)
        attendu += 30
    return attendu


def lire(nom, sha_attendu):
    with open(os.path.join(ROUTAGE, nom), "rb") as f:
        brut = f.read()
    sha = hashlib.sha256(brut).hexdigest()
    if sha != sha_attendu:
        raise SystemExit(f"{nom} : empreinte {sha} différente de la déclarée")
    return decoder(brut, nom)


def decoder(brut, nom="?"):
    couches, positions = struct.unpack_from("<II", brut, 0)
    if len(brut) != 8 + couches * positions * 8:
        raise SystemExit(f"{nom} : taille {len(brut)} incompatible avec {couches} × {positions} × 8")
    experts, marges = [], []
    for e0, e1, e2, e3, m in struct.iter_unpack("<4Bf", brut[8:]):
        experts.append((e0, e1, e2, e3))
        marges.append(m)
    return couches, positions, experts, marges


def bascules(exp_x, exp_y):
    return [frozenset(a) != frozenset(b) for a, b in zip(exp_x, exp_y)]


def tete_du_classement(marges, k):
    ordre = sorted(range(len(marges)), key=lambda i: (marges[i], i))
    return ordre, set(ordre[:k])


def main():
    prio = baisser_priorite()
    os.environ["OMP_NUM_THREADS"] = "1"
    attente = attendre_verrou()
    os.makedirs(SORTIE, exist_ok=True)
    res = {"outil": "outils/pistes/tropicale/juge/juge.py", "priorite": prio, "attente_verrou_s": attente}

    L, P, eA, mA = lire(*JOURNAUX["A"])
    L2, P2, eB, mB = lire(*JOURNAUX["B"])
    L3, P3, eC, mC = lire(*JOURNAUX["C"])
    assert (L, P) == (L2, P2) == (L3, P3)
    N = L * P
    res["couches"], res["positions"], res["cellules"] = L, P, N

    # Santé des journaux.
    sante = {}
    for nom, e, m in (("A", eA, mA), ("B", eB, mB), ("C", eC, mC)):
        sante[nom] = {
            "experts_hors_0_31": sum(1 for t in e if max(t) > 31),
            "experts_doubles_dans_un_top4": sum(1 for t in e if len(set(t)) != 4),
            "marges_nan": sum(1 for x in m if x != x),
            "marges_negatives": sum(1 for x in m if x < 0),
            "marges_nulles": sum(1 for x in m if x == 0),
        }
    res["sante"] = sante

    bAB = bascules(eA, eB)
    nb = sum(bAB)
    res["bascules_ensemble"] = nb
    res["bascules_liste_ordonnee"] = sum(1 for a, b in zip(eA, eB) if a != b)
    res["bascules_A_contre_C"] = sum(bascules(eA, eC))

    # Point principal : les 12 264 cellules de plus petite marge de B.
    k = round(PART_CELLULES * N)
    ordre, tete = tete_du_classement(mB, k)
    attrapees = sum(1 for i in tete if bAB[i])
    m_k = mB[ordre[k - 1]]
    m_k1 = mB[ordre[k]]
    egaux_frontiere = sum(1 for x in mB if x == m_k)
    strict_sous_mk1 = sum(1 for x in mB if x < m_k1)
    res["point_principal"] = {
        "cellules_signalees": k,
        "part_cellules": k / N,
        "bascules_attrapees": attrapees,
        "part_bascules": attrapees / nb,
        "marge_de_la_k_ieme": m_k,
        "marge_de_la_k_plus_1_ieme": m_k1,
        "cellules_egales_a_la_frontiere": egaux_frontiere,
        "cellules_strictement_sous_la_suivante": strict_sous_mk1,
        "passe_le_seuil": attrapees / nb >= PART_BASCULES,
    }

    # Coût de 80 % : plus petit préfixe du classement qui contient ceil(0,8 nb) bascules.
    cible = math.ceil(PART_BASCULES * nb)
    vu = 0
    for rang, i in enumerate(ordre, 1):
        vu += bAB[i]
        if vu >= cible:
            break
    res["cout_80"] = {"bascules_visees": cible, "cellules": rang, "part_cellules": rang / N}

    # Par couche, au même classement global.
    par_couche = []
    for c in range(L):
        idx = range(c * P, (c + 1) * P)
        bc = sum(1 for i in idx if bAB[i])
        ac = sum(1 for i in idx if bAB[i] and i in tete)
        par_couche.append({"couche": c, "bascules": bc, "attrapees": ac,
                           "part": (ac / bc) if bc else None})
    res["par_couche"] = par_couche

    # Variante avec la marge de A (même chemin).
    _, teteA = tete_du_classement(mA, k)
    res["variante_marge_A"] = sum(1 for i in teteA if bAB[i]) / nb

    # Cascades : P(bascule en ℓ+1 | bascule en ℓ) contre sinon, même position.
    n11 = n10 = n01 = n00 = 0
    for c in range(L - 1):
        for p in range(P):
            x, y = bAB[c * P + p], bAB[(c + 1) * P + p]
            if x and y:
                n11 += 1
            elif x:
                n10 += 1
            elif y:
                n01 += 1
            else:
                n00 += 1
    res["cascades"] = {"p_suite_si_bascule": n11 / (n11 + n10), "p_suite_sinon": n01 / (n01 + n00)}

    # Racines : première couche qui bascule, par position.
    racines = attr_r = 0
    for p in range(P):
        for c in range(L):
            i = c * P + p
            if bAB[i]:
                racines += 1
                attr_r += i in tete
                break
    res["racines"] = {"positions_avec_bascule": racines, "attrapees": attr_r, "part": attr_r / racines}

    # Témoins du juge, chacun capable de tomber.
    t = {}
    # J1 : un octet d'expert changé dans une copie de B, sur une cellule sans bascule, doit faire +1.
    with open(os.path.join(ROUTAGE, JOURNAUX["B"][0]), "rb") as f:
        brut = bytearray(f.read())
    cible_i = next(i for i in range(N) if not bAB[i] and mB[i] > 1.0)
    autre = next(e for e in range(32) if e not in eA[cible_i])
    brut[8 + cible_i * 8] = autre
    _, _, eBc, _ = decoder(bytes(brut))
    t["J1_octet_change"] = {"bascules": sum(bascules(eA, eBc)), "attendu": nb + 1}
    # J2 : mauvais pas (7 octets) refusé.
    try:
        couches, positions = struct.unpack_from("<II", brut, 0)
        if len(brut) != 8 + couches * positions * 7:
            raise ValueError
        t["J2_mauvais_pas"] = "accepté (TÉMOIN MORT)"
    except ValueError:
        t["J2_mauvais_pas"] = "refusé"
    # J3 : marges de B permutées (graine fixée) : le compte doit tomber vers 10 %.
    rng = random.Random(20261022)
    perm = mB[:]
    rng.shuffle(perm)
    _, tp = tete_du_classement(perm, k)
    t["J3_marges_permutees"] = sum(1 for i in tp if bAB[i]) / nb
    # J4 : marges oracles (0 aux bascules) : le même instrument doit rendre 100 % ; le verdict
    # « passe » était donc atteignable par cet instrument.
    orac = [0.0 if bAB[i] else mB[i] for i in range(N)]
    _, to = tete_du_classement(orac, k)
    t["J4_marges_oracles"] = sum(1 for i in to if bAB[i]) / nb
    # J5 : cassure du chiffre principal : 600 bascules non attrapées reçoivent une marge nulle ;
    # elles entrent en tête et en chassent les 600 dernières cellules du classement, dont certaines
    # sont des bascules. Attendu exact : attrapées + 600 − (bascules parmi les rangs k−599 à k).
    # (Première écriture de ce témoin : « attrapées + 600 », oubli des bascules chassées ; corrigé.)
    nonatt = [i for i in range(N) if bAB[i] and i not in tete][:600]
    chassees = sum(1 for i in ordre[k - 600:k] if bAB[i])
    mod = mB[:]
    for i in nonatt:
        mod[i] = 0.0
    _, tm = tete_du_classement(mod, k)
    t["J5_cassure_600"] = {"attrapees": sum(1 for i in tm if bAB[i]),
                           "attendu": attrapees + 600 - chassees, "bascules_chassees": chassees}
    res["temoins_du_juge"] = t

    # Théorème (κ* = 0,1079) : quadrature indépendante (Simpson), sans la forme close.
    def phi_bar(x):
        return 0.5 * math.erfc(x / math.sqrt(2))

    def integ(a, b, kap, n=20000):
        h = (b - a) / n
        s = 0.0
        for j in range(n + 1):
            x = a + j * h
            w = 1 if j in (0, n) else (4 if j % 2 else 2)
            s += w * phi_bar(x / kap) * math.exp(-x)
        return s * h / 3

    kap = 0.1079
    tau = math.log(10 / 9)
    pB = integ(0, 3.0, kap)
    num = integ(0, tau, kap)
    res["theoreme_quadrature"] = {"kappa": kap, "P_B": pB, "b_tau10": num / pB}

    with open(os.path.join(SORTIE, "juge.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
