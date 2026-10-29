# -*- coding: utf-8 -*-
"""Juge des figures du lot « construction » : les lectures (ce qui serait faux ou trop beau).

Chaque section chiffre une question que pose une figure du lot, depuis les fichiers commités, par un code
écrit sans lire les scripts du lot. Le jugement (memoire/tome3/JUGEMENT-figures-construction.md) cite ces
sorties ; rien n'y est recopié de mémoire.

  L1  III-9.1 (c) : l'aire entre la part cumulée en calibration et vue par l'évaluation, pour le synonyme
      ET pour la frontière ; est-elle propre au synonyme (« l'aire est le sur-apprentissage ») ?
  L2  III-9.1 : l'amortissement δ* = 1 du codeur (H + δ* moy(diag H) I) contre le poids des directions muettes.
  L3  III-9.2 : le 99,9e centile, sur combien de positions il repose, et ce qu'il devient sur les fenêtres neuves.
  L4  III-9.3 : la différence appariée λ = 1 contre frontière des fenêtres neuves mêle deux chemins (λ = 1 par
      le moteur, la frontière par la référence substituée) ; ce que le mélange déplace, mesuré sur R1, où les
      deux chemins existent pour les deux variantes.
  L5  III-8.6 encart : les rapports écrits dans la légende contre les rapports des barres dessinées.
  L6  III-8.6 (d) : le facteur « motif » est un reste (r(B/A) / toit des octets) ; l'étage disque seul du 120b,
      mesuré dans la même séance, pour comparaison.
  L7  III-8.1 : les parts des codes dans les 12 tenseurs (dessinées) contre les 72 tenseurs (commités).
  L8  III-9.6 : σ par fenêtres sur σ par positions, chaque variante ; bits du point « exact ».
  L9  III-10.1 : jetons routés par fenêtre (appels / (24 couches × 4 experts)).

Usage : python -I -X utf8 lectures.py [--racine DÉPÔT]
"""
import argparse
import csv
import glob
import json
import math
import os

import numpy as np


def lire_csv(chemin):
    with open(chemin, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def lire_json(chemin):
    with open(chemin, encoding='utf-8') as f:
        return json.load(f)


def kl_par_position(chemin):
    par = {}
    for r in lire_csv(chemin):
        par.setdefault(int(r['fenetre']), []).append(float(r['kl']))
    return par


def moy_f(par):
    return np.asarray([np.mean(par[f]) for f in sorted(par)])


def toutes(par):
    return np.asarray([x for f in sorted(par) for x in par[f]])


def sig_f(v):
    v = np.asarray(v, dtype=np.float64)
    return float(v.std(ddof=1) / math.sqrt(len(v)))


def principal():
    ap = argparse.ArgumentParser()
    ici = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--racine', default=os.path.normpath(os.path.join(ici, '..', '..', '..', '..')))
    a = ap.parse_args()
    R = a.racine
    M = os.path.join(R, 'mesures')
    C = os.path.join(M, 'genome', 'construction')

    print('L1  III-9.1 (c) : aires entre calibration et évaluation (moyenne sur k de la différence des parts)')
    sp = np.loadtxt(os.path.join(C, 'synonyme', 'figures', 'spectre-L08-E00-gate.csv'), delimiter=',', skiprows=1)
    lam, lev, ef, es = sp[:, 1], sp[:, 2], sp[:, 3], sp[:, 4]
    rang = int((lam > lam.max() * 1e-12).sum())
    for nom, e in (('frontière', ef), ('synonyme', es)):
        cal = np.cumsum(lam * e) / (lam * e).sum()
        ev = np.cumsum(lev * e) / (lev * e).sum()
        aire = float((cal - ev).mean())
        part_muette_ev = float((lev[rang:] * e[rang:]).sum() / (lev * e).sum())
        print(f'    {nom:<10} aire {aire:.4f} ; part du coût vu par l\'évaluation au-delà du rang {part_muette_ev:.3f} ;'
              f' calibration {float((lam * e).sum()):.2f}, évaluation {float((lev * e).sum()):.2f}')
    cal_f = np.cumsum(lam * ef) / (lam * ef).sum()
    cal_s = np.cumsum(lam * es) / (lam * es).sum()
    ev_f = np.cumsum(lev * ef) / (lev * ef).sum()
    ev_s = np.cumsum(lev * es) / (lev * es).sum()
    print(f'    rapport des coûts évaluation / calibration : frontière {(lev * ef).sum() / (lam * ef).sum():.3f},'
          f' synonyme {(lev * es).sum() / (lam * es).sum():.3f}')
    print(f'    aire du synonyme moins aire de la frontière : {float(((cal_s - ev_s) - (cal_f - ev_f)).mean()):.4f}')

    print('L2  III-9.1 : amortissement du codeur contre poids des directions muettes')
    moy_diag = float(lam.sum() / len(lam))
    print(f'    moy(diag H) = tr(H)/2880 = {moy_diag:.4f} ; δ* = 1 : chaque direction pèse au moins {moy_diag:.4f}'
          f' dans le coût que le codeur minimise')
    print(f'    poids d\'évaluation des {len(lam) - rang} directions muettes : min {lev[rang:].min():.4f},'
          f' médiane {np.median(lev[rang:]):.4f}, max {lev[rang:].max():.4f}')
    print(f'    λ_k de calibration : {int((lam > moy_diag).sum())} directions au-dessus de moy(diag H)')

    print('L3  III-9.2 : le 99,9e centile')
    kl = os.path.join(C, 'synonyme', 'kl')
    jk = os.path.join(C, 'juge', 'kl')
    r1 = {'frontière': toutes(kl_par_position(os.path.join(kl, 'kl-frontiere-768-positions.csv'))),
          'λ = 1': toutes(kl_par_position(os.path.join(kl, 'kl-synonyme-768-positions.csv'))),
          'λ = 0': toutes(kl_par_position(os.path.join(kl, 'kl-synonyme-l0-768-positions.csv')))}
    neuf = {'frontière (sub)': toutes(kl_par_position(os.path.join(jk, 'kl-neuf-sub-frontiere-positions.csv'))),
            'λ = 1 (moteur)': toutes(kl_par_position(os.path.join(jk, 'kl-neuf-moteur-rapide-l1-positions.csv'))),
            'λ = 0 (moteur)': toutes(kl_par_position(os.path.join(jk, 'kl-neuf-moteur-rapide-l0-positions.csv'))),
            'λ = 0 (sub)': toutes(kl_par_position(os.path.join(jk, 'kl-neuf-sub-l0-positions.csv')))}
    for jeu, d in (('R1', r1), ('neuves', neuf)):
        for nom, v in d.items():
            p = float(np.percentile(v, 99.9))
            print(f'    {jeu:<6} {nom:<16} n {len(v)} ; 99,9e {p:.3f} ; positions au-dessus {int((v > p).sum())} ;'
                  f' 99e {np.percentile(v, 99):.3f} ; max {v.max():.3f}')
    pf = float(np.percentile(r1['frontière'], 99.9))
    pn = float(np.percentile(neuf['frontière (sub)'], 99.9))
    for nom_r1, nom_n in (('λ = 1', 'λ = 1 (moteur)'), ('λ = 0', 'λ = 0 (moteur)')):
        print(f'    {nom_r1} contre la frontière, 99,9e : R1 {np.percentile(r1[nom_r1], 99.9) / pf - 1:+.1%},'
              f' neuves {np.percentile(neuf[nom_n], 99.9) / pn - 1:+.1%}')

    print('L4  III-9.3 : deux chemins dans une différence appariée (mesuré sur R1)')
    mo = os.path.join(C, 'synonyme', 'moteur')
    sub_f = kl_par_position(os.path.join(kl, 'kl-frontiere-768-positions.csv'))
    sub_u = kl_par_position(os.path.join(kl, 'kl-synonyme-768-positions.csv'))
    mot_f = kl_par_position(os.path.join(mo, 'kl-moteur-frontiere-positions.csv'))
    mot_u = kl_par_position(os.path.join(mo, 'kl-moteur-synonyme-positions.csv'))
    for nom, (b, aa) in (('λ=1 sub − F sub (un chemin, celui du lot B)', (sub_u, sub_f)),
                         ('λ=1 moteur − F moteur (un chemin)', (mot_u, mot_f)),
                         ('λ=1 moteur − F sub (deux chemins, comme les neuves)', (mot_u, sub_f))):
        d = moy_f(b) - moy_f(aa)
        print(f'    R1 {nom:<52} d̄ {d.mean():+.4f} ; σ_f {sig_f(d):.4f} ; z {-d.mean() / sig_f(d):.2f}')
    ecart = moy_f(mot_f) - moy_f(sub_f)
    print(f'    R1 frontière moteur − frontière sub, par fenêtre : moyenne {ecart.mean():+.4f},'
          f' de {ecart.min():+.4f} à {ecart.max():+.4f}')

    print('L5  III-8.6 encart : rapports écrits et rapports dessinés')
    seance = os.path.join(M, 'disque', 'placement', 'juge', 'seance')

    def go(motif):
        return [d['go_s'] for d in (lire_json(f) for f in sorted(glob.glob(os.path.join(seance, motif))))
                if d.get('secteur_apres') is not False]
    s2 = lire_csv(os.path.join(C, 'codon', 'disque-s2.csv'))
    a_s2 = float(np.mean([float(r['go_s']) for r in s2 if r['fichier'] == 'A']))
    c_s2 = float(np.mean([float(r['go_s']) for r in s2 if r['fichier'] == 'C']))
    c_un = float(np.median(go('J6-*-C120.json')))
    a_un = float(np.median(go('J6-*-A120.json')))
    c_tire = float(np.median(go('J5-*-C120.json')))
    print(f'    dessiné : A120 s2 {a_s2:.3f}, C120 s2 {c_s2:.3f}, C120 un extent J6 {c_un:.3f}')
    print(f'    écrit : C[U]/A[U] (J6, A non dessiné {a_un:.3f}) {c_un / a_un:.3f} ; C[U]/C tiré (J5, non dessiné'
          f' {c_tire:.3f}) {c_un / c_tire:.3f}')
    print(f'    lu sur les barres : C un extent / A s2 {c_un / a_s2:.3f} ; C un extent / C s2 {c_un / c_s2:.3f} ;'
          f' A s2 / C s2 {a_s2 / c_s2:.3f}')

    print('L6  III-8.6 (d) : le motif est un reste ; l\'étage disque seul du 120b dans la même séance')
    dp = [r for r in lire_csv(os.path.join(C, 'juge', 'figures', 'disque-passes.csv')) if r['modele'] == '120b']
    dA = float(np.median([float(r['go_s']) for r in dp if r['lettre'] == 'A']))
    dB = float(np.median([float(r['go_s']) for r in dp if r['lettre'] == 'B']))
    dR = float(np.median([float(r['go_s']) for r in dp if r['lettre'] == 'R']))
    print(f'    étage disque 120b : A {dA:.3f}, B {dB:.3f}, R {dR:.3f} Go/s ; B/A {dB / dA:.3f} ; R/B {dR / dB:.3f}')
    vp = [r for r in lire_csv(os.path.join(C, 'juge', 'figures', 'vitesse-passes.csv')) if r['modele'] == '120b']
    v = {L: float(np.median([float(r['generation_jetons_s']) for r in vp if r['lettre'] == L])) for L in 'ABR'}
    o = {L: float(np.median([float(r['octets_troncons_par_pas']) for r in vp if r['lettre'] == L])) for L in 'ABR'}
    print(f'    r(B/A) {v["B"] / v["A"]:.4f} ; toit des octets {o["A"] / o["B"]:.4f} ; reste (motif) >= '
          f'{v["B"] / v["A"] / (o["A"] / o["B"]):.4f} ; si les octets ne rendaient rien : {v["B"] / v["A"]:.4f}')
    print(f'    écart-type relatif des A de la séance : {np.std([float(r["generation_jetons_s"]) for r in vp if r["lettre"] == "A"], ddof=1) / np.mean([float(r["generation_jetons_s"]) for r in vp if r["lettre"] == "A"]):.3f}')

    print('L7  III-8.1 : parts des codes, 12 tenseurs (dessinés) contre 72 tenseurs (commités)')
    h12 = np.load(os.path.join(M, 'genome', 'predictif-elagage', 'histo-12-gptoss20b.npz'))['comptes'].astype(np.int64)
    h72 = np.load(os.path.join(M, 'genome', 'predictif-elagage', 'histo-toutes-gptoss20b.npz'))['comptes'].astype(np.int64)
    p12 = h12.sum(axis=(0, 1, 2)) / h12.sum()
    p72 = h72.sum(axis=(0, 1, 2)) / h72.sum()
    for c in range(16):
        print(f'    code {c:2d} : 12 tenseurs {100 * p12[c]:6.2f} % ; 72 tenseurs {100 * p72[c]:6.2f} %')
    larg = lambda p: 0.4 + 44 * p  # noqa: E731  (épaisseur dessinée, en pt, codon-figures.tex)
    print(f'    épaisseur du rayon du zéro après / avant : {larg(p12[0] + p12[8]) / larg(p12[0]):.3f}'
          f' (une épaisseur proportionnelle donnerait {(p12[0] + p12[8]) / p12[0]:.3f})')

    print('L8  III-9.6 : σ par fenêtres sur σ par positions ; bits du point exact')
    q = kl_par_position(os.path.join(C, 'synonyme', 'repere', 'kl-q2_0-positions.csv'))
    for nom, par in (('frontière', sub_f), ('λ = 1', sub_u), ('λ = 0', kl_par_position(os.path.join(kl, 'kl-synonyme-l0-768-positions.csv'))),
                     ('Q2_0', q)):
        x = toutes(par)
        sn = float(x.std(ddof=1) / math.sqrt(len(x)))
        print(f'    {nom:<10} σ_f / σ_n = {sig_f(moy_f(par)) / sn:.2f}')
    t = lire_json(os.path.join(C, 'codon', 'tailles.json'))['totaux']['20b']
    j0 = lire_json(os.path.join(C, 'juge', 'J-T0-fichiers.json'))['fichiers']['20b-v10']
    print(f'    v1.0 du 20b : bpp_total_03 {t["bpp_total_03_v10"]:.4f} (tracé) ; bits utiles du fichier'
          f' {j0["bits_par_poids_utiles"]:.4f} (même définition que les compagnons) ; alignés {j0["bits_par_poids_alignes"]:.4f}')

    print('L9  III-10.1 : jetons routés par fenêtre')
    g = lire_csv(os.path.join(C, 'juge', 'figures', 'routage-grille.csv'))
    tot = sum(int(r['appels_r1']) for r in g)
    print(f'    appels R1 {tot} = 10 fenêtres × 24 couches × 4 experts × {tot / (10 * 24 * 4):.1f} jetons'
          f' (255 positions notées par fenêtre)')


if __name__ == '__main__':
    principal()
