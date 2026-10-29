# -*- coding: utf-8 -*-
"""Juge des figures du lot « construction » : un point tiré au hasard par série tracée, contrôlé à la source.

Pour chaque série des CSV de memoire/figures/tome3/donnees/ que tracent les figures III-8.1 à III-10.3,
une ligne est tirée par un générateur à graine écrite (numpy default_rng(GRAINE), séries prises dans
l'ordre de la liste SERIES), puis la valeur tracée est recalculée depuis les fichiers commités sous
mesures/ par le code de ce fichier (écrit sans lire les scripts du lot), et comparée à la tolérance de
l'arrondi du CSV (la moitié de la dernière décimale écrite, plus 1e-12).

Usage : python -I -X utf8 points.py [--racine DÉPÔT] [--graine N] [--casser]
  --casser : témoin qui doit tomber ; la valeur recalculée est décalée d'un millième relatif.
Code de sortie : 0 si chaque point tient, 1 sinon.
"""
import argparse
import csv
import glob
import json
import math
import os
import sys

import numpy as np

GRAINE = 20261027


def lire_csv(chemin):
    with open(chemin, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def lire_json(chemin):
    with open(chemin, encoding='utf-8') as f:
        return json.load(f)


def tolerance(texte):
    texte = texte.strip()
    if 'e' in texte.lower():
        mant, exp = texte.lower().split('e')
        dec = len(mant.split('.')[1]) if '.' in mant else 0
        return 0.5 * 10 ** (int(exp) - dec) + 1e-12
    dec = len(texte.split('.')[1]) if '.' in texte else 0
    return 0.5 * 10 ** (-dec) + 1e-12


def kl_par_position(chemin, colonne='kl'):
    par = {}
    for r in lire_csv(chemin):
        par.setdefault(int(r['fenetre']), []).append(float(r[colonne]))
    return par


def principal():
    ap = argparse.ArgumentParser()
    ici = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--racine', default=os.path.normpath(os.path.join(ici, '..', '..', '..', '..')))
    ap.add_argument('--graine', type=int, default=GRAINE)
    ap.add_argument('--casser', action='store_true')
    a = ap.parse_args()
    R = a.racine
    M = os.path.join(R, 'mesures')
    C = os.path.join(M, 'genome', 'construction')
    D = os.path.join(R, 'memoire', 'figures', 'tome3', 'donnees')
    rng = np.random.default_rng(a.graine)
    biais = 1.001 if a.casser else 1.0
    resultats = []

    def controle(serie, cle, texte, refait):
        refait = refait * biais
        ecrit = float(texte)
        if math.isnan(ecrit) and math.isnan(refait):
            tient = True
        else:
            tient = abs(ecrit - refait) <= tolerance(texte)
        resultats.append((serie, cle, texte, f'{refait:.9g}', 'tient' if tient else 'ÉCART'))

    def tirer(lignes):
        i = int(rng.integers(len(lignes)))
        return i, lignes[i]

    # ---- sources
    h12 = np.load(os.path.join(M, 'genome', 'predictif-elagage', 'histo-12-gptoss20b.npz'))['comptes'].astype(np.int64)
    code12 = h12.sum(axis=(0, 1, 2))
    tot12 = code12.sum()
    tailles = lire_csv(os.path.join(C, 'codon', 'tailles-par-tenseur.csv'))
    tables = lire_csv(os.path.join(C, 'codon', 'tables-octets.csv'))
    colonne = lire_csv(os.path.join(C, 'synthese', 'colonne-par-tenseur.csv'))
    j1 = lire_csv(os.path.join(C, 'codon', 'j1-s2-passes.csv'))
    seance = os.path.join(M, 'disque', 'placement', 'juge', 'seance')
    sp = np.loadtxt(os.path.join(C, 'synonyme', 'figures', 'spectre-L08-E00-gate.csv'), delimiter=',', skiprows=1)
    kl = os.path.join(C, 'synonyme', 'kl')
    jk = os.path.join(C, 'juge', 'kl')
    r1 = {'frontiere': kl_par_position(os.path.join(kl, 'kl-frontiere-768-positions.csv')),
          'lambda1': kl_par_position(os.path.join(kl, 'kl-synonyme-768-positions.csv')),
          'lambda0': kl_par_position(os.path.join(kl, 'kl-synonyme-l0-768-positions.csv')),
          'q2_0': kl_par_position(os.path.join(C, 'synonyme', 'repere', 'kl-q2_0-positions.csv'))}
    c4 = {}
    for r in lire_csv(os.path.join(M, 'moteur', 'O', 'journaux', 'o3', 'c4-20b-comparer.csv')):
        c4.setdefault(int(r['fenetre']), []).append(float(r['kl_b']))
    r1['exact'] = c4
    neuf = {'frontiere': kl_par_position(os.path.join(jk, 'kl-neuf-sub-frontiere-positions.csv')),
            'lambda1': kl_par_position(os.path.join(jk, 'kl-neuf-moteur-rapide-l1-positions.csv')),
            'lambda0': kl_par_position(os.path.join(jk, 'kl-neuf-moteur-rapide-l0-positions.csv')),
            'lambda0_sub': kl_par_position(os.path.join(jk, 'kl-neuf-sub-l0-positions.csv')),
            'exact': kl_par_position(os.path.join(jk, 'kl-neuf-moteur-exact-20b-positions.csv'))}

    # ---- III-8.1, la roue
    lignes = lire_csv(os.path.join(D, 'codon-roue.csv'))
    i, l = tirer(lignes)
    K = (0, 1, 2, 3, 4, 6, 8, 12)
    code = int(l['code'])
    controle('codon-roue', f'code {code} part_avant', l['part_avant'], code12[code] / tot12)
    apres = (code12[0] + code12[8]) / tot12 if code == 0 else (0.0 if code == 8 else code12[code] / tot12)
    controle('codon-roue', f'code {code} part_apres', l['part_apres'], apres)
    controle('codon-roue', f'code {code} valeur (ggml : 2 x E2M1)', l['valeur'], (-1) ** (code >> 3) * K[code & 7])

    # ---- III-8.3, le théorème
    for m in ('20b', '120b'):
        lignes = lire_csv(os.path.join(D, f'codon-theoreme-{m}.csv'))
        i, l = tirer(lignes)
        src = [r for r in tailles if r['modele'] == m and r['couche'] == l['couche'] and r['matrice'] == l['matrice']][0]
        controle(f'codon-theoreme-{m}', f'L{l["couche"]} m{l["matrice"]} x', l['x'], 2 * float(src['part_moins_zero']))
        controle(f'codon-theoreme-{m}', f'L{l["couche"]} m{l["matrice"]} y', l['y'], float(src['gain_bits']))

    # ---- III-8.2, la carte des octets (120b, couche 18, up, κ = 1)
    for v, ver in (('v10', '1.0'), ('v12', '1.2')):
        lignes = lire_csv(os.path.join(D, f'codon-octets-{v}.csv'))
        i, l = tirer(lignes)
        octet = 16 * int(l['y']) + int(l['x'])
        f = [r for r in tables if r['modele'] == '120b' and r['version'] == ver and r['couche'] == '18'
             and r['matrice'] == '1' and r['kappa'] == '1' and r['octet'] == str(octet)]
        controle(f'codon-octets-{v}', f'octet {octet:02X}', l['v'], math.log10(1 + int(f[0]['frequence'])))

    # ---- III-8.5, la colonne
    lignes = lire_csv(os.path.join(D, 'codon-colonne.csv'))
    i, l = tirer(lignes)
    nom = {'gate': 'gate', 'up': 'up', 'down': 'down'}[l['matrice']]
    src = [r for r in colonne if r['tenseur'] == f'blk.{l["couche"]}.ffn_{nom}_exps.weight'][0]
    controle('codon-colonne', l['etiquette'], l['gain'],
             float(src['zero_octet_kappa']) - float(src['zero_demi_octet_kappa_colonne']))

    # ---- III-8.6 (a)(b), les passes du J1 s2
    for f in ('codon-j1-passes.csv', 'codon-j1-v10.csv', 'codon-j1-v12.csv'):
        lignes = lire_csv(os.path.join(D, f))
        i, l = tirer(lignes)
        src = [r for r in j1 if r['passe'] == l['passe']][0]
        controle(f[:-4], f'passe {l["passe"]} jetons/s', l['jetons_s'], float(src['jetons_s']))
        controle(f[:-4], f'passe {l["passe"]} Mo/jeton', l['mo_par_jeton'], float(src['octets_troncons_par_jeton']) / 1e6)
    va = [float(r['jetons_s']) for r in j1 if r['fichier'] == 'A']
    oa = float(np.median([float(r['octets_troncons_par_jeton']) for r in j1 if r['fichier'] == 'A'])) / 1e6
    lignes = lire_csv(os.path.join(D, 'codon-j1-iso.csv'))
    i, l = tirer(lignes)
    controle('codon-j1-iso', f'{l["mo_par_jeton"]} Mo', l['jetons_s'], float(np.median(va)) * oa / float(l['mo_par_jeton']))

    # ---- III-8.6 (c), le motif croisé Jb3, et l'encart
    lignes = lire_csv(os.path.join(D, 'codon-j1-motif.csv'))
    i, l = tirer(lignes)
    g = [lire_json(f)['go_s'] for f in sorted(glob.glob(os.path.join(seance, f'Jb3-*-{l["fichier"]}-{l["motif"]}.json')))]
    controle('codon-j1-motif', f'{l["fichier"]} {l["motif"]} médiane', l['mediane'], float(np.median(g)))
    j = int(rng.integers(4))
    controle('codon-j1-motif', f'{l["fichier"]} {l["motif"]} passe p{j + 1}', l[f'p{j + 1}'], g[j])
    lignes = lire_csv(os.path.join(D, 'codon-j1-encart.csv'))
    i, l = tirer(lignes)
    s2 = lire_csv(os.path.join(C, 'codon', 'disque-s2.csv'))
    if l['cas'].endswith('-s2'):
        lettre = 'A' if l['cas'].startswith('A') else 'C'
        refait = float(np.mean([float(r['go_s']) for r in s2 if r['fichier'] == lettre]))
    else:
        refait = float(np.median([d['go_s'] for d in (lire_json(f) for f in sorted(glob.glob(os.path.join(seance, 'J6-*-C120.json'))))
                                  if d.get('secteur_apres') is not False]))
    controle('codon-j1-encart', l['cas'], l['go_s'], refait)

    # ---- III-8.6 (d), la cascade
    vp = [r for r in lire_csv(os.path.join(C, 'juge', 'figures', 'vitesse-passes.csv')) if r['modele'] == '120b']
    v = {L: float(np.median([float(r['generation_jetons_s']) for r in vp if r['lettre'] == L])) for L in 'ABR'}
    o = {L: float(np.median([float(r['octets_troncons_par_pas']) for r in vp if r['lettre'] == L])) for L in 'ABR'}
    bornes = {'v10': (0.0, v['A']), 'motif': (v['A'], v['A'] * (v['B'] / v['A']) / (o['A'] / o['B'])),
              'octets': (v['A'] * (v['B'] / v['A']) / (o['A'] / o['B']), v['B']), 'v12': (0.0, v['B']),
              'rapide': (v['B'], v['R']), 'compagnon': (0.0, v['R'])}
    lignes = lire_csv(os.path.join(D, 'codon-j1-cascade.csv'))
    i, l = tirer(lignes)
    controle('codon-j1-cascade', f'{l["etape"]} bas', l['bas'], bornes[l['etape']][0])
    controle('codon-j1-cascade', f'{l["etape"]} haut', l['haut'], bornes[l['etape']][1])

    # ---- III-9.1, la base propre de H
    lam, lev, ef, es = sp[:, 1], sp[:, 2], sp[:, 3], sp[:, 4]
    lignes = lire_csv(os.path.join(D, 'synonyme-spectre.csv'))
    i, l = tirer(lignes)
    k = int(l['k'])
    # Une valeur propre nulle à l'arrondi (|λ| < 1e-12 λ_max, au-delà du rang) n'a pas de place sur un axe
    # logarithmique : le lot l'écrit nan (non tracée). Le juge refait la même règle.
    lam_k = float('nan') if abs(lam[k]) < 1e-12 * lam.max() else lam[k]
    controle('synonyme-spectre', f'k {k} lambda_calib (nan si nulle à l\'arrondi)', l['lambda_calib'], lam_k)
    controle('synonyme-spectre', f'k {k} lambda_eval', l['lambda_eval'], lev[k])
    lignes = lire_csv(os.path.join(D, 'synonyme-energie.csv'))
    i, l = tirer(lignes)
    deb = int(l['k_milieu']) - 30
    controle('synonyme-energie', f'paquet {deb}-{deb + 59} e_frontiere', l['e_frontiere'], ef[deb:deb + 60].mean())
    controle('synonyme-energie', f'paquet {deb}-{deb + 59} e_synonyme', l['e_synonyme'], es[deb:deb + 60].mean())
    cum = {'frontiere_calib': np.cumsum(lam * ef) / (lam * ef).sum(), 'frontiere_eval': np.cumsum(lev * ef) / (lev * ef).sum(),
           'synonyme_calib': np.cumsum(lam * es) / (lam * es).sum(), 'synonyme_eval': np.cumsum(lev * es) / (lev * es).sum()}
    lignes = lire_csv(os.path.join(D, 'synonyme-cumul.csv'))
    for s in cum:
        i, l = tirer(lignes)
        controle('synonyme-cumul', f'k {l["k"]} {s}', l[s], cum[s][int(l['k'])])
    lignes = lire_csv(os.path.join(D, 'synonyme-cumul-aire.csv'))
    i, l = tirer(lignes)
    kk = int(l['k'])
    cand = min((abs(cum['synonyme_calib'][kk] - float(l['part'])), cum['synonyme_calib'][kk]),
               (abs(cum['synonyme_eval'][kk] - float(l['part'])), cum['synonyme_eval'][kk]))[1]
    controle('synonyme-cumul-aire', f'k {kk} (bord calibration ou évaluation du synonyme)', l['part'], cand)

    # ---- III-9.2, la queue
    lignes = lire_csv(os.path.join(D, 'synonyme-survie.csv'))
    for s in ('q2_0', 'frontiere', 'lambda1', 'lambda0'):
        i, l = tirer(lignes)
        x = np.asarray([y for f in sorted(r1[s]) for y in r1[s][f]])
        controle('synonyme-survie', f't {l["t"]} {s}', l[s], float((x > float(l['t'])).mean()))
    lignes = lire_csv(os.path.join(D, 'synonyme-quantiles.csv'))
    i, l = tirer(lignes)
    s = {'q2_0': 'q2_0', 'frontiere': 'frontiere', 'lambda1': 'lambda1', 'lambda0': 'lambda0'}[l['serie']]
    x = np.asarray([y for f in sorted(r1[s]) for y in r1[s][f]])
    controle('synonyme-quantiles', f'{s} médiane', l['mediane'], float(np.median(x)))
    controle('synonyme-quantiles', f'{s} 99,9e centile', l['p999'], float(np.percentile(x, 99.9)))

    # ---- III-9.3, la forêt
    paires = {'un-frontiere': (('frontiere', 'lambda1'), ('frontiere', 'lambda1')),
              'zero-un': (('lambda1', 'lambda0'), ('lambda1', 'lambda0')),
              'zero-frontiere': (('frontiere', 'lambda0'), ('frontiere', 'lambda0_sub'))}
    for nom, (pr1, pneuf) in paires.items():
        lignes = lire_csv(os.path.join(D, f'synonyme-foret-{nom}.csv'))
        i, l = tirer(lignes)
        f = int(l['fenetre'])
        src, (pa, pb) = (r1, pr1) if l['bande'] == 'r1' else (neuf, pneuf)
        controle(f'synonyme-foret-{nom}', f'{l["bande"]} fenêtre {f} d', l['d'], np.mean(src[pb][f]) - np.mean(src[pa][f]))
        attendu_y = (23 - f) if l['bande'] == 'r1' else (10 - f)
        controle(f'synonyme-foret-{nom}', f'{l["bande"]} fenêtre {f} y', l['y'], attendu_y)

    # ---- III-9.6, les variantes
    lignes = lire_csv(os.path.join(D, 'synonyme-variantes.csv'))
    i, l = tirer(lignes)
    s = {'frontiere': 'frontiere', 'synonyme-l1': 'lambda1', 'synonyme-l0': 'lambda0', 'llama-q2_0': 'q2_0', 'exact': 'exact'}[l['variante']]
    moy = [np.mean(r1[s][f]) for f in sorted(r1[s])]
    x = np.asarray([y for f in sorted(r1[s]) for y in r1[s][f]])
    controle('synonyme-variantes', f'{l["variante"]} kl', l['kl'], x.mean())
    controle('synonyme-variantes', f'{l["variante"]} sigma_f', l['sigma_f'], np.std(moy, ddof=1) / math.sqrt(len(moy)))
    controle('synonyme-variantes', f'{l["variante"]} sigma_n', l['sigma_n'], x.std(ddof=1) / math.sqrt(len(x)))

    # ---- III-8.8, le codon par le décodeur du juge
    e = lire_csv(os.path.join(C, 'juge', 'J-T1-echantillon.csv'))
    lignes = lire_csv(os.path.join(D, 'juge-codon-experts.csv'))
    i, l = tirer(lignes)
    src = [r for r in e if r['version'] == 'v12' and r['modele'] == l['modele'] and r['couche'] == l['couche']
           and r['expert'] == l['expert']][0]
    controle('juge-codon-experts', f'{l["modele"]} L{l["couche"]} E{l["expert"]} part', l['part'],
             100.0 * int(src['moins_zero_gguf']) / int(src['demi_octets']))
    derniere = 23 if l['modele'] == '20b' else 35
    controle('juge-codon-experts', f'{l["modele"]} L{l["couche"]} E{l["expert"]} x', l['x'], int(l['couche']) / derniere)
    jt0 = lire_json(os.path.join(C, 'juge', 'J-T0-fichiers.json'))['fichiers']
    lignes = lire_csv(os.path.join(D, 'juge-codon-fichiers.csv'))
    i, l = tirer(lignes)
    fch = jt0[l['fichier']]
    controle('juge-codon-fichiers', f'{l["fichier"]} Go', l['go'], fch['taille_disque'] / 1e9)
    controle('juge-codon-fichiers', f'{l["fichier"]} bits', l['bits'], fch['somme_parties_alignees'] * 8.0 / fch['poids_experts'])

    # ---- III-10.1, la grille
    grille = lire_csv(os.path.join(C, 'juge', 'figures', 'routage-grille.csv'))
    total_max = max(int(r['appels_r1']) + int(r['appels_neuf']) for r in grille)
    lignes = lire_csv(os.path.join(D, 'juge-grille.csv'))
    i, l = tirer(lignes)
    src = [r for r in grille if r['couche'] == l['couche'] and r['expert'] == l['expert']][0]
    x1, xn = int(src['appels_r1']), int(src['appels_neuf'])
    sorte = (1 if x1 > 0 else 0) + (2 if xn > 0 else 0)
    controle('juge-grille', f'L{l["couche"]} E{l["expert"]} appels_r1', l['appels_r1'], x1)
    controle('juge-grille', f'L{l["couche"]} E{l["expert"]} sorte', l['sorte'], sorte)
    m = 0.0 if sorte == 0 else 10 * sorte + 9.99 * math.log10(1 + x1 + xn) / math.log10(1 + total_max)
    controle('juge-grille', f'L{l["couche"]} E{l["expert"]} m (10 sorte + 9,99 log)', l['m'], m)

    # ---- III-10.3, les fenêtres
    lignes = [r for r in lire_csv(os.path.join(D, 'juge-kl-fenetres.csv')) if r['jeu'] != 'coupure']
    for s in ('frontiere', 'lambda1', 'lambda0', 'exact'):
        i, l = tirer(lignes)
        src = r1 if l['jeu'] == 'r1' else neuf
        controle('juge-kl-fenetres', f'{l["jeu"]} fenêtre {l["fenetre"]} {s}', l[s], np.mean(src[s][int(l['fenetre'])]))

    largeur = max(len(r[0]) for r in resultats)
    for r in resultats:
        print(f'{r[0]:<{largeur}}  {r[1]:<52}  {r[2]:>14}  {r[3]:>14}  {r[4]}')
    faux = sum(1 for r in resultats if r[4] != 'tient')
    print(f'\ngraine {a.graine} : {len(resultats)} points, {len(resultats) - faux} tiennent, {faux} écarts.')
    return 0 if faux == 0 else 1


if __name__ == '__main__':
    sys.exit(principal())
