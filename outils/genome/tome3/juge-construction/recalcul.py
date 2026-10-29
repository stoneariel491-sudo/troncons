# -*- coding: utf-8 -*-
"""Juge des figures du lot « construction » du Tome III (ch. 8 à 10) : les nombres des légendes.

Refait chaque nombre des fichiers memoire/figures/tome3/donnees/{codon,synonyme,juge}-nombres.tex depuis
les fichiers commités sous mesures/ (ou les documents qu'ils citent), par un code écrit sans lire les
scripts du lot (memoire/outils/tome3_codon.py, tome3_synonyme.py, tome3_juge.py). Chaque nombre est
recalculé, mis au même nombre de décimales que le nombre écrit, et comparé à lui comme chaîne.

Chemins indépendants quand il en existe un (le lot lit l'un, le juge lit l'autre) :
- la pièce du signe des zéros : comptée dans l'histogramme des 72 tenseurs (histo-toutes-gptoss20b.npz),
  pas lue dans zero-compte-20b.json ;
- les gains des fichiers : J-T0-fichiers.json (décodeur du juge) et tailles.json (codeur du lot A) ;
- les KL, médianes, centiles, différences appariées, σ par fenêtres : refaits depuis les fichiers par
  position (lot B pour R1, juge de la construction pour les fenêtres neuves), pas lus dans les JSON
  résumés ni dans les CSV par fenêtre.

Usage : python -I -X utf8 recalcul.py [--racine DÉPÔT] [--sortie FICHIER.csv] [--casser]
  --casser : témoin qui doit tomber ; la part des −0 lue dans tailles-par-tenseur.csv est multipliée
             par 1,01 avant le calcul : l'écart à la diagonale de III-8.3 doit alors sortir faux.
Code de sortie : 0 si tout concorde, 1 sinon.
"""
import argparse
import csv
import glob
import json
import math
import os
import re
import sys

import numpy as np


def lire_csv(chemin):
    with open(chemin, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def lire_json(chemin):
    with open(chemin, encoding='utf-8') as f:
        return json.load(f)


def mediane(v):
    return float(np.median(np.asarray(v, dtype=np.float64)))


def sigma_fenetres(moyennes):
    """Écart-type des moyennes de fenêtre divisé par la racine du nombre de fenêtres (ddof = 1)."""
    m = np.asarray(moyennes, dtype=np.float64)
    return float(m.std(ddof=1) / math.sqrt(len(m)))


def entropie_binaire(p):
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def kl_par_position(chemin, colonne='kl'):
    """Rend {fenêtre: [kl des positions]} dans l'ordre du fichier."""
    par = {}
    for r in lire_csv(chemin):
        par.setdefault(int(r['fenetre']), []).append(float(r[colonne]))
    return par


def moyennes_fenetres(par):
    return [float(np.mean(par[f])) for f in sorted(par)]


def toutes(par):
    return [x for f in sorted(par) for x in par[f]]


def lire_nombres(chemin):
    """\\def\\Nom{valeur}% source -> {Nom: (valeur, source)}."""
    motif = re.compile(r'^\\def\\(\w+)\{([^}]*)\}%\s*(.*)$')
    sortie = {}
    with open(chemin, encoding='utf-8') as f:
        for ligne in f:
            m = motif.match(ligne.strip())
            if m:
                sortie[m.group(1)] = (m.group(2), m.group(3))
    return sortie


def au_format(valeur, modele):
    """Écrit valeur avec autant de décimales que la chaîne modele (entier si modele n'a pas de point)."""
    if isinstance(valeur, (int, np.integer)) and '.' not in modele:
        return str(int(valeur))
    if '.' in modele:
        dec = len(modele.split('.')[1])
        texte = f'{valeur:.{dec}f}'
    else:
        texte = f'{valeur:.0f}'
    if texte.startswith('-') and float(texte) == 0.0:
        texte = texte[1:]
    return texte


def principal():
    ap = argparse.ArgumentParser()
    ici = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--racine', default=os.path.normpath(os.path.join(ici, '..', '..', '..', '..')))
    ap.add_argument('--sortie', default=None)
    ap.add_argument('--casser', action='store_true')
    a = ap.parse_args()
    R = a.racine
    M = os.path.join(R, 'mesures')
    C = os.path.join(M, 'genome', 'construction')
    D = os.path.join(R, 'memoire', 'figures', 'tome3', 'donnees')
    N = {}      # nom -> valeur recalculée
    NOTE = {}   # nom -> chemin suivi par le juge

    # ------------------------------------------------------------------ ch. 8, codon
    t = lire_csv(os.path.join(C, 'codon', 'tailles-par-tenseur.csv'))
    facteur = 1.01 if a.casser else 1.0
    ecarts = [float(r['gain_bits']) - 2.0 * facteur * float(r['part_moins_zero']) for r in t]
    N['CodonNEcartMin'] = min(ecarts)
    N['CodonNEcartMax'] = max(ecarts)
    N['CodonNTenseurs'] = len(t)
    NOTE['CodonNEcartMin'] = NOTE['CodonNEcartMax'] = 'gain_bits - 2 part_moins_zero, 180 lignes'

    h12 = np.load(os.path.join(M, 'genome', 'predictif-elagage', 'histo-12-gptoss20b.npz'))
    c12 = h12['comptes'].astype(np.int64)
    par_code12 = c12.sum(axis=(0, 1, 2))
    tot12 = int(par_code12.sum())
    N['CodonNRoueTenseurs'] = int(c12.shape[0])
    N['CodonNRouePoids'] = tot12
    N['CodonNRoueZeroPlus'] = 100.0 * par_code12[0] / tot12
    N['CodonNRoueZeroMoins'] = 100.0 * par_code12[8] / tot12
    NOTE['CodonNRoueZeroPlus'] = 'histo-12 : code 0 / total (dernier axe = code)'

    h72 = np.load(os.path.join(M, 'genome', 'predictif-elagage', 'histo-toutes-gptoss20b.npz'))
    c72 = h72['comptes'].astype(np.int64)
    par_code72 = c72.sum(axis=(0, 1, 2))
    tot72 = int(par_code72.sum())
    p_plus, p_moins = par_code72[0] / tot72, par_code72[8] / tot72
    N['CodonNPiece'] = entropie_binaire(par_code72[0] / (par_code72[0] + par_code72[8]))
    N['CodonNPiecePlus'] = 100.0 * p_plus
    N['CodonNPieceMoins'] = 100.0 * p_moins
    N['CodonNPieceTenseurs'] = int(c72.shape[0])
    pc = par_code72 / tot72
    N['CodonNHCode'] = float(-(pc[pc > 0] * np.log2(pc[pc > 0])).sum())
    valeurs = pc[:8].copy()
    valeurs[0] = pc[0] + pc[8]
    valeurs = np.concatenate([valeurs, pc[9:]])
    N['CodonNHValeur'] = float(-(valeurs[valeurs > 0] * np.log2(valeurs[valeurs > 0])).sum())
    N['CodonNCoutSigne'] = N['CodonNHCode'] - N['CodonNHValeur']
    for k in ('CodonNPiece', 'CodonNPiecePlus', 'CodonNPieceMoins', 'CodonNHCode', 'CodonNHValeur',
              'CodonNCoutSigne', 'CodonNPieceTenseurs'):
        NOTE[k] = 'histo-toutes-gptoss20b.npz (72 tenseurs), autre fichier que zero-compte-20b.json'
    zc = lire_json(os.path.join(M, 'genome', 'etat-de-l-art', 'journaux', 'zero-compte-20b.json'))
    temoin_piece = abs(zc['p_plus0'] - p_plus) < 1e-12 and abs(zc['p_moins0'] - p_moins) < 1e-12

    col = lire_csv(os.path.join(C, 'synthese', 'colonne-par-tenseur.csv'))
    gains_col = {r['tenseur']: float(r['zero_octet_kappa']) - float(r['zero_demi_octet_kappa_colonne'])
                 for r in col}
    poids_tenseur = 32 * 2880 * 2880
    poids_20b = 24 * 3 * poids_tenseur
    retenus = {k: g for k, g in gains_col.items() if g >= 0.015}
    N['CodonNColonneModele'] = sum(retenus.values()) * poids_tenseur / poids_20b
    N['CodonNColonneMo'] = sum(retenus.values()) * poids_tenseur / 8.0 / 1e6
    N['CodonNColonneSeuil'] = 0.015
    NOTE['CodonNColonneModele'] = 'gain = zero_octet_kappa - zero_demi_octet_kappa_colonne, retenus >= 0,015 : ' + \
        ', '.join(sorted(retenus))
    NOTE['CodonNColonneSeuil'] = '05 § 4.3 (règle du choix par matrice) et ARCHITECTURE § 4.16'
    autres = [g for k, g in gains_col.items() if k not in retenus]
    COL_AUTRES_MAX = max(autres)
    COL_AUTRES_MIN = min(autres)

    jt0 = lire_json(os.path.join(C, 'juge', 'J-T0-fichiers.json'))['fichiers']

    def gain_fichier(m):
        a0, a2 = jt0[m + '-v10'], jt0[m + '-v12']
        return (a0['somme_parties_alignees'] - a2['somme_parties_alignees']) * 8.0 / a0['poids_experts']
    N['CodonNZeroGain'] = gain_fichier('20b')
    NOTE['CodonNZeroGain'] = 'J-T0-fichiers.json (décodeur du juge), sommes des parties alignées'

    j1 = lire_csv(os.path.join(C, 'codon', 'j1-s2-passes.csv'))
    va = [float(r['jetons_s']) for r in j1 if r['fichier'] == 'A']
    vb = [float(r['jetons_s']) for r in j1 if r['fichier'] == 'B']
    oa = mediane([float(r['octets_troncons_par_jeton']) for r in j1 if r['fichier'] == 'A'])
    ob = mediane([float(r['octets_troncons_par_jeton']) for r in j1 if r['fichier'] == 'B'])
    med_a, med_b = mediane(va), mediane(vb)
    sig_a = float(np.std(va, ddof=1) / np.mean(va))
    N['CodonNJiMedA'] = med_a
    N['CodonNJiMedB'] = med_b
    N['CodonNJiR'] = med_b / med_a
    N['CodonNJiSigma'] = 100.0 * sig_a
    N['CodonNJiBandeBas'] = med_a * (1.0 - 2.0 * sig_a)
    N['CodonNJiBandeHaut'] = med_a * (1.0 + 2.0 * sig_a)
    N['CodonNJiOctets'] = ob / oa
    N['CodonNJiToit'] = 100.0 * (oa / ob - 1.0)
    N['CodonNJiMoA'] = oa / 1e6
    N['CodonNJiMoB'] = ob / 1e6
    N['CodonNJiPreditB'] = med_a * oa / ob
    NOTE['CodonNJiSigma'] = 'écart-type (ddof = 1) des 4 passes A sur leur moyenne'
    TEXTES_J1 = sorted({r['texte_sha256'] for r in j1})

    seance = os.path.join(M, 'disque', 'placement', 'juge', 'seance')

    def passes(motif_nom):
        sortie = []
        for f in sorted(glob.glob(os.path.join(seance, motif_nom))):
            d = lire_json(f)
            lu = d.get('smart_ecart', {}).get('octets_lus_disque', d['octets']) / d['octets']
            ecartee = bool(d.get('sous_charge')) or (d.get('arret_s') or 0) > 0 or \
                d.get('secteur_apres') is False or lu > 1.02
            sortie.append((d['nom'], d['go_s'], ecartee))
        return sortie
    jb = {k: passes(f'Jb3-*-{k}.json') for k in ('A20-natif', 'A20-croise', 'B20-natif', 'B20-croise')}
    med = {k: mediane([g for _, g, e in v if not e]) for k, v in jb.items()}
    N['CodonNMotifAN'] = med['A20-natif']
    N['CodonNMotifAC'] = med['A20-croise']
    N['CodonNMotifBN'] = med['B20-natif']
    N['CodonNMotifBC'] = med['B20-croise']
    N['CodonNMotifRA'] = med['A20-croise'] / med['A20-natif']
    N['CodonNMotifRB'] = med['B20-croise'] / med['B20-natif']
    N['CodonNMotifEcartees'] = sum(1 for v in jb.values() for _, _, e in v if e)
    MOTIF_RA_ARRONDI = round(med['A20-croise'], 3) / round(med['A20-natif'], 3)
    MOTIF_RA_MOYENNES = np.mean([g for _, g, _ in jb['A20-croise']]) / np.mean([g for _, g, _ in jb['A20-natif']])

    s2 = lire_csv(os.path.join(C, 'codon', 'disque-s2.csv'))
    N['CodonNEncartA'] = float(np.mean([float(r['go_s']) for r in s2 if r['fichier'] == 'A']))
    N['CodonNEncartC'] = float(np.mean([float(r['go_s']) for r in s2 if r['fichier'] == 'C']))
    j6c = [g for _, g, e in passes('J6-*-C120.json') if not e]
    j6a = [g for _, g, e in passes('J6-*-A120.json') if not e]
    j5c = [g for _, g, e in passes('J5-*-C120.json') if not e]
    N['CodonNEncartCun'] = mediane(j6c)
    N['CodonNEncartAun'] = mediane(j6a)
    N['CodonNEncartCsurA'] = mediane(j6c) / mediane(j6a)
    N['CodonNEncartCtire'] = mediane(j5c)
    N['CodonNEncartFrag'] = mediane(j6c) / mediane(j5c)
    NOTE['CodonNEncartCsurA'] = 'médianes J6 (C120 sans J6-12, sur batterie) ; le juge du placement écrit 0,980'
    ENCART_CSURA_MOYENNES = float(np.mean(j6c) / np.mean(j6a))
    cartes = lire_json(os.path.join(seance, 'J1-cartes.json'))
    N['CodonNExtentsA'] = int(cartes['A120']['extents'])
    N['CodonNExtentsC'] = int(cartes['C120']['extents'])
    N['CodonNExtentsB'] = int(cartes['B120']['extents'])

    vp = [r for r in lire_csv(os.path.join(C, 'juge', 'figures', 'vitesse-passes.csv')) if r['modele'] == '120b']
    vit = {L: mediane([float(r['generation_jetons_s']) for r in vp if r['lettre'] == L]) for L in 'ABR'}
    octp = {L: mediane([float(r['octets_troncons_par_pas']) for r in vp if r['lettre'] == L]) for L in 'ABR'}
    N['CodonNCascA'] = vit['A']
    N['CodonNCascB'] = vit['B']
    N['CodonNCascR'] = vit['R']
    N['CodonNCascRBA'] = vit['B'] / vit['A']
    N['CodonNCascToit'] = octp['A'] / octp['B']
    N['CodonNCascMotif'] = (vit['B'] / vit['A']) / (octp['A'] / octp['B'])
    N['CodonNCascRRB'] = vit['R'] / vit['B']
    N['CodonNCascToitR'] = octp['B'] / octp['R']

    # ------------------------------------------------------------------ ch. 9, synonyme
    sp = np.loadtxt(os.path.join(C, 'synonyme', 'figures', 'spectre-L08-E00-gate.csv'), delimiter=',', skiprows=1)
    lam, lev, ef, es = sp[:, 1], sp[:, 2], sp[:, 3], sp[:, 4]
    rang = int((lam > lam.max() * 1e-12).sum())
    N['SynoNRang'] = rang
    N['SynoNDirections'] = len(lam)
    N['SynoNPaquet'] = 60
    NOTE['SynoNPaquet'] = 'choix du script (paquets de 60 directions), rien à refaire'
    N['SynoNEnergieF'] = float(ef.sum())
    N['SynoNEnergieS'] = float(es.sum())
    N['SynoNEnergieHausse'] = 100.0 * (es.sum() / ef.sum() - 1.0)
    N['SynoNCalibF'] = float((lam * ef).sum())
    N['SynoNCalibS'] = float((lam * es).sum())
    N['SynoNCalibRapport'] = float((lam * ef).sum() / (lam * es).sum())
    N['SynoNEvalF'] = float((lev * ef).sum())
    N['SynoNEvalS'] = float((lev * es).sum())
    N['SynoNEvalRapport'] = float((lev * ef).sum() / (lev * es).sum())
    N['SynoNLambdaMax'] = float(lam.max())
    N['SynoNLambdaEvalMin'] = float(lev[rang:].min())
    N['SynoNPartNulleF'] = 100.0 * ef[rang:].sum() / ef.sum()
    N['SynoNPartNulleS'] = 100.0 * es[rang:].sum() / es.sum()
    NOTE['SynoNRang'] = 'nombre de λ > 1e-12 λ_max (saut de 5,8e-3 à 1,6e-14 entre k = 1 328 et 1 329)'
    NOTE['SynoNLambdaEvalMin'] = 'min de u_k^T H_év u_k sur k >= rang'
    SPECTRE = dict(moy_diag=float(lam.sum() / len(lam)), lev_min_tout=float(lev.min()),
                   lev_muet_moy=float(lev[rang:].mean()))

    kl = os.path.join(C, 'synonyme', 'kl')
    r1 = {'f': kl_par_position(os.path.join(kl, 'kl-frontiere-768-positions.csv')),
          'u': kl_par_position(os.path.join(kl, 'kl-synonyme-768-positions.csv')),
          'z': kl_par_position(os.path.join(kl, 'kl-synonyme-l0-768-positions.csv')),
          'q': kl_par_position(os.path.join(C, 'synonyme', 'repere', 'kl-q2_0-positions.csv'))}
    for cle, nom in (('q', 'Q'), ('f', 'F'), ('u', 'Un'), ('z', 'Zero')):
        v = np.asarray(toutes(r1[cle]))
        N[f'SynoNMed{nom}'] = float(np.median(v))
        N[f'SynoNQueue{nom}'] = float(np.percentile(v, 99.9))
        NOTE[f'SynoNQueue{nom}'] = 'centile 99,9 (interpolation linéaire de numpy) sur les positions'
    N['SynoNPositions'] = len(toutes(r1['f']))

    jk = os.path.join(C, 'juge', 'kl')
    neuf = {'f_sub': kl_par_position(os.path.join(jk, 'kl-neuf-sub-frontiere-positions.csv')),
            'z_sub': kl_par_position(os.path.join(jk, 'kl-neuf-sub-l0-positions.csv')),
            'u_mot': kl_par_position(os.path.join(jk, 'kl-neuf-moteur-rapide-l1-positions.csv')),
            'z_mot': kl_par_position(os.path.join(jk, 'kl-neuf-moteur-rapide-l0-positions.csv')),
            'x_mot': kl_par_position(os.path.join(jk, 'kl-neuf-moteur-exact-20b-positions.csv'))}

    def foret(a_par, b_par):
        d = np.asarray(moyennes_fenetres(b_par)) - np.asarray(moyennes_fenetres(a_par))
        s = sigma_fenetres(d)
        return float(d.mean()), s, float(-d.mean() / s), int((d < 0).sum())
    comparaisons = {
        'UnF': ((r1['f'], r1['u']), (neuf['f_sub'], neuf['u_mot'])),
        'ZeroUn': ((r1['u'], r1['z']), (neuf['u_mot'], neuf['z_mot'])),
        'ZeroF': ((r1['f'], r1['z']), (neuf['f_sub'], neuf['z_sub'])),
    }
    for nom, (cr1, cneuf) in comparaisons.items():
        for jeu, (pa, pb) in (('Run', cr1), ('Neuf', cneuf)):
            m, s, z, n = foret(pa, pb)
            N[f'SynoNFor{nom}{jeu}Moy'] = m
            N[f'SynoNFor{nom}{jeu}Sig'] = s
            N[f'SynoNFor{nom}{jeu}Z'] = z
            N[f'SynoNFor{nom}{jeu}Neg'] = n
    NOTE['SynoNForUnFNeufMoy'] = 'λ = 1 par le moteur moins la frontière par la référence substituée (deux chemins)'

    rap = os.path.join(C, 'synonyme', 'rapide')
    bits = {'f': lire_json(os.path.join(rap, 'coder-frontiere.json')),
            'u': lire_json(os.path.join(rap, 'coder-synonyme.json')),
            'z': lire_json(os.path.join(rap, 'coder-synonyme-l0.json'))}

    def bits_utiles(d):
        for k, v in d.items():
            if k == 'bits_par_poids_utiles':
                return v
            if isinstance(v, dict):
                x = bits_utiles(v)
                if x is not None:
                    return x
        return None
    for cle, nom in (('f', 'F'), ('u', 'Un'), ('z', 'Zero')):
        v = np.asarray(toutes(r1[cle]))
        N[f'SynoNVar{nom}Bits'] = bits_utiles(bits[cle])
        N[f'SynoNVar{nom}KL'] = float(v.mean())
        N[f'SynoNVar{nom}Sf'] = sigma_fenetres(moyennes_fenetres(r1[cle]))
        N[f'SynoNVar{nom}Sn'] = float(v.std(ddof=1) / math.sqrt(len(v)))
    vq = np.asarray(toutes(r1['q']))
    N['SynoNVarQBits'] = 2.25
    NOTE['SynoNVarQBits'] = 'Q2_0 : 2 bits + une échelle f16 par groupe de 64 = 2,25 (07 § 4.1, aide de llama-quantize)'
    N['SynoNVarQKL'] = float(vq.mean())
    N['SynoNVarQSf'] = sigma_fenetres(moyennes_fenetres(r1['q']))
    N['SynoNVarQSn'] = float(vq.std(ddof=1) / math.sqrt(len(vq)))
    N['SynoNAchatKL'] = N['SynoNVarUnKL'] - N['SynoNVarZeroKL']
    N['SynoNAchatBits'] = N['SynoNVarZeroBits'] - N['SynoNVarUnBits']
    c4 = lire_csv(os.path.join(M, 'moteur', 'O', 'journaux', 'o3', 'c4-20b-comparer.csv'))
    exact_r1 = {}
    for r in c4:
        exact_r1.setdefault(int(r['fenetre']), []).append(float(r['kl_b']))
    N['SynoNExactKL'] = float(np.mean(toutes(exact_r1)))
    N['SynoNExactBits'] = lire_json(os.path.join(C, 'codon', 'tailles.json'))['totaux']['20b']['bpp_total_03_v10']
    NOTE['SynoNExactBits'] = 'bpp_total_03_v10 de tailles.json ; bits utiles du fichier v1.0 (J-T0) : %.4f' % \
        jt0['20b-v10']['bits_par_poids_utiles']

    # ------------------------------------------------------------------ juge de la construction
    e = lire_csv(os.path.join(C, 'juge', 'J-T1-echantillon.csv'))
    v12 = [r for r in e if r['version'] == 'v12']
    v10 = [r for r in e if r['version'] == 'v10']
    N['JconsNExpertsVingt'] = sum(1 for r in v12 if r['modele'] == '20b')
    N['JconsNExpertsCent'] = sum(1 for r in v12 if r['modele'] == '120b')
    N['JconsNExperts'] = len(v12)
    N['JconsNExpertsTient'] = sum(1 for r in v12 if r['tient'] == '1')
    N['JconsNHuit'] = sum(int(r['huit_dans_le_decode']) for r in v12)
    N['JconsNTemoins'] = len(v10)
    N['JconsNTemoinsTient'] = sum(1 for r in v10 if r['tient'] == '1')
    zc120 = lire_json(os.path.join(M, 'genome', 'etat-de-l-art', 'journaux', 'zero-compte-120b.json'))
    N['JconsNPartVingt'] = 100.0 * p_moins
    N['JconsNPartCent'] = 100.0 * zc120['p_moins0']
    NOTE['JconsNPartVingt'] = 'code 8 de histo-toutes (20b) ; zero-compte-120b.json (120b), autres fichiers que tailles.json'
    N['JconsNGainVingt'] = gain_fichier('20b')
    N['JconsNGainCent'] = gain_fichier('120b')
    N['JconsNOctetsVingt'] = jt0['20b-v10']['somme_parties_alignees'] - jt0['20b-v12']['somme_parties_alignees']
    N['JconsNOctetsCent'] = jt0['120b-v10']['somme_parties_alignees'] - jt0['120b-v12']['somme_parties_alignees']
    N['JconsNGoVingtA'] = jt0['20b-v10']['taille_disque'] / 1e9
    N['JconsNGoVingtB'] = jt0['20b-v12']['taille_disque'] / 1e9
    N['JconsNGoCentA'] = jt0['120b-v10']['taille_disque'] / 1e9
    N['JconsNGoCentB'] = jt0['120b-v12']['taille_disque'] / 1e9
    N['JconsNSeuilCdeux'] = 0.12
    NOTE['JconsNSeuilCdeux'] = '05 § 4.6, critères déclarés avant (A-C2 >= 0,12 bit par poids d\'expert)'
    N['JconsNTablesSansFente'] = sum(jt0[m]['tables']['codes_ctx_avec_fente_pour_un_8'] for m in ('20b-v12', '120b-v12'))
    g = lire_csv(os.path.join(C, 'juge', 'figures', 'routage-grille.csv'))
    a1 = [int(r['appels_r1']) for r in g]
    an = [int(r['appels_neuf']) for r in g]
    N['JconsNVides'] = sum(1 for x, y in zip(a1, an) if x == 0 and y == 0)
    N['JconsNRunSeul'] = sum(1 for x, y in zip(a1, an) if x > 0 and y == 0)
    N['JconsNNeufSeul'] = sum(1 for x, y in zip(a1, an) if x == 0 and y > 0)
    N['JconsNDeux'] = sum(1 for x, y in zip(a1, an) if x > 0 and y > 0)
    # Lu d'abord comme le maximum d'un seul jeu de fenêtres (4 764) : écart. Le nombre écrit est le
    # maximum, sur les experts, des appels des deux jeux réunis (R1 + neuves), celui qui borne
    # l'intensité de la grille (m = 10 sorte + 9,99 log10(1 + appels) / log10(1 + 9 331), juge-grille.csv).
    N['JconsNAppelsMax'] = max(x + y for x, y in zip(a1, an))
    N['JconsNAppelsRun'] = sum(a1)
    N['JconsNAppelsNeuf'] = sum(an)
    NOTE['JconsNAppelsMax'] = 'max sur les experts de R1 + neuves (un seul jeu : R1 %d, neuves %d) ; la légende ne le dit pas' % (
        max(a1), max(an))
    mf = moyennes_fenetres(r1['f'])
    N['JconsNFrontMin'] = min(mf)
    N['JconsNFrontMax'] = max(mf)
    N['JconsNSigmaF'] = sigma_fenetres(mf)
    mx = moyennes_fenetres(exact_r1) + moyennes_fenetres(neuf['x_mot'])
    N['JconsNExactMin'] = min(mx)
    N['JconsNExactMax'] = max(mx)
    NOTE['JconsNExactMin'] = 'mode exact, R1 (c4-20b-comparer.csv) et neuves (kl-neuf-moteur-exact-20b)'

    # ------------------------------------------------------------------ comparaison
    ecrits = {}
    for f in ('codon-nombres.tex', 'synonyme-nombres.tex', 'juge-nombres.tex'):
        ecrits.update(lire_nombres(os.path.join(D, f)))
    lignes = []
    faux = 0
    for nom, (texte, source) in ecrits.items():
        if nom not in N:
            lignes.append((nom, texte, '', '', 'NON REFAIT', source, ''))
            faux += 1
            continue
        v = N[nom]
        mien = au_format(v, texte)
        tient = mien == texte or (texte.startswith('+') and mien == texte[1:])
        if not tient:
            faux += 1
        lignes.append((nom, texte, mien, repr(float(v)), 'tient' if tient else 'ÉCART', source, NOTE.get(nom, '')))
    for nom in N:
        if nom not in ecrits:
            lignes.append((nom, '', au_format(N[nom], '0.0000'), repr(float(N[nom])), 'en plus', '', NOTE.get(nom, '')))
    entete = ('nom', 'ecrit_par_le_lot', 'refait_par_le_juge', 'valeur_brute', 'verdict', 'source_du_lot', 'chemin_du_juge')
    largeur = max(len(l[0]) for l in lignes)
    for l in lignes:
        print(f'{l[0]:<{largeur}}  {l[1]:>14}  {l[2]:>14}  {l[4]:<10}  {l[6]}')
    print()
    print(f'{len(ecrits)} nombres écrits, {sum(1 for l in lignes if l[4] == "tient")} tiennent, {faux} écarts.')
    print('Témoin : la pièce comptée dans histo-toutes égale zero-compte-20b.json à 1e-12 :', temoin_piece)
    print('Textes du J1 s2 (SHA-256 distincts) :', len(TEXTES_J1))
    print('Colonne, tenseurs non retenus : gain de %.6f à %.6f bit' % (COL_AUTRES_MIN, COL_AUTRES_MAX))
    print('Motif A20 : rapport des médianes arrondies à 3 chiffres %.5f ; des moyennes %.5f' % (MOTIF_RA_ARRONDI, MOTIF_RA_MOYENNES))
    print('Encart : C[U]/A[U] des moyennes J6 %.5f' % ENCART_CSURA_MOYENNES)
    print('Spectre : moy(diag H) = %.4f (amortissement δ* = 1) ; u_k^T H_év u_k : min sur tout k %.4f, moyenne sur les muettes %.4f'
          % (SPECTRE['moy_diag'], SPECTRE['lev_min_tout'], SPECTRE['lev_muet_moy']))
    if a.sortie:
        with open(a.sortie, 'w', newline='\n', encoding='utf-8') as f:
            w = csv.writer(f, lineterminator='\n')
            w.writerow(entete)
            w.writerows(lignes)
    return 0 if faux == 0 else 1


if __name__ == '__main__':
    sys.exit(principal())
