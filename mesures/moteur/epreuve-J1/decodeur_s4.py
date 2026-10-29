"""Épreuve indépendante du jalon J1, geste 1 (decisions/ARCHITECTURE.md § 8.1).

Un décodeur du format .trc écrit à partir du SEUL § 4 de decisions/ARCHITECTURE.md, sans lire
trc-format, trc-codec, ni aucun outil d'un lot. Le GGUF est lu par un lecteur écrit ici depuis la
spécification GGUF v3 (github.com/ggml-org/ggml, docs/gguf.md), lui aussi sans rien importer d'un
lot.

Ce qu'il fait :
  1. lit et vérifie l'en-tête fixe (§ 4.3), champ par champ, et son empreinte ;
  2. vérifie MÉTA (§ 4.4) contre les paires du GGUF, octet pour octet ;
  3. vérifie la table des RÉSIDENTS (§ 4.5) contre les tenseurs du GGUF (nom, type, forme,
     taille), et, avec --residents-complets, chaque tenseur résident octet pour octet ;
  4. lit TABLES (§ 4.6) et RÉPERTOIRE (§ 4.7), leurs empreintes, la somme 4 096 de chaque table ;
  5. tire n tronçons au hasard (graine publiée), décode chacun par le § 4.8 à 4.11, et compare
     l'expert reconstruit (a) à son empreinte d'origine du répertoire, (b) aux octets du GGUF au
     décalage du § 4.11, octet pour octet.

Cassures (le témoin doit pouvoir tomber) : --casser mot | table | mediane | lut, chacune appliquée
en mémoire au premier tronçon tiré ; l'outil doit alors signaler l'écart, et seulement là.

Python 3.13, numpy, bibliothèque standard. Aucun accès réseau.
Commande : python -I -X utf8 decodeur_s4.py <fichier.trc> <source.gguf> <journal.json>
           [--n 20] [--graine 20261016] [--casser …] [--residents-complets]
"""

import argparse
import datetime
import hashlib
import json
import os
import struct
import sys
import time

import numpy as np

L_RANS = 1 << 16          # borne basse de l'état (§ 4.9.2)
M_RANS = 4096             # probabilités sur 12 bits


# ---------------------------------------------------------------------------------------------
# Empreintes (§ 4.12)
# ---------------------------------------------------------------------------------------------

def empreinte64(octets) -> int:
    """Les 8 premiers octets de SHA-256, lus comme un u64 petit-boutiste."""
    return struct.unpack("<Q", hashlib.sha256(octets).digest()[:8])[0]


def lire(f, decalage, longueur) -> bytes:
    f.seek(decalage)
    b = f.read(longueur)
    if len(b) != longueur:
        raise IOError(f"lecture courte à {decalage} : {len(b)} sur {longueur}")
    return b


# ---------------------------------------------------------------------------------------------
# Lecteur GGUF v3, écrit ici depuis la spécification publique
# ---------------------------------------------------------------------------------------------

TAILLES_SCALAIRES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
FORMATS_SCALAIRES = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?",
                     10: "<Q", 11: "<q", 12: "<d"}
# (poids par bloc, octets par bloc) des types ggml rencontrés ici
BLOCS_GGML = {0: (1, 4), 1: (1, 2), 8: (32, 34), 30: (1, 2), 39: (32, 17)}


class Gguf:
    def __init__(self, chemin):
        self.chemin = chemin
        self.f = open(chemin, "rb")
        tete = self.f.read(64 << 20)  # les métadonnées du 120b tiennent en ~13 Mo
        self.tete = tete
        if tete[:4] != b"GGUF":
            raise ValueError("pas un GGUF")
        self.version, self.n_tenseurs, self.n_kv = struct.unpack_from("<IQQ", tete, 4)
        pos = 24
        self.debut_kv = pos
        self.kv = {}
        self.kv_ordre = []
        for _ in range(self.n_kv):
            debut_paire = pos
            (lk,) = struct.unpack_from("<Q", tete, pos); pos += 8
            cle = tete[pos:pos + lk].decode("utf-8"); pos += lk
            (t,) = struct.unpack_from("<I", tete, pos); pos += 4
            val, pos = self._valeur(tete, pos, t)
            self.kv[cle] = val
            self.kv_ordre.append((cle, debut_paire, pos))
        self.fin_kv = pos
        self.tenseurs = {}
        self.tenseurs_ordre = []
        for _ in range(self.n_tenseurs):
            (ln,) = struct.unpack_from("<Q", tete, pos); pos += 8
            nom = tete[pos:pos + ln].decode("utf-8"); pos += ln
            (nd,) = struct.unpack_from("<I", tete, pos); pos += 4
            ne = list(struct.unpack_from(f"<{nd}Q", tete, pos)); pos += 8 * nd
            typ, dec = struct.unpack_from("<IQ", tete, pos); pos += 12
            self.tenseurs[nom] = {"type": typ, "ne": ne, "n_dims": nd, "decalage": dec}
            self.tenseurs_ordre.append(nom)
        al = int(self.kv.get("general.alignment", 32))
        self.alignement = al
        self.debut_donnees = (pos + al - 1) // al * al
        for nom, t in self.tenseurs.items():
            n = 1
            for d in t["ne"]:
                n *= d
            pb, ob = BLOCS_GGML[t["type"]]
            t["octets"] = n // pb * ob
            t["absolu"] = self.debut_donnees + t["decalage"]

    def _valeur(self, b, pos, t):
        if t in FORMATS_SCALAIRES:
            (v,) = struct.unpack_from(FORMATS_SCALAIRES[t], b, pos)
            return v, pos + TAILLES_SCALAIRES[t]
        if t == 8:
            (n,) = struct.unpack_from("<Q", b, pos); pos += 8
            return b[pos:pos + n].decode("utf-8", "replace"), pos + n
        if t == 9:
            te, n = struct.unpack_from("<IQ", b, pos); pos += 12
            if te in TAILLES_SCALAIRES:
                pos += n * TAILLES_SCALAIRES[te]
                return f"<tableau {n}×type {te}>", pos
            for _ in range(n):
                _, pos = self._valeur(b, pos, te)
            return f"<tableau {n}×type {te}>", pos
        raise ValueError(f"type GGUF inconnu {t}")

    def lire(self, decalage, longueur):
        return lire(self.f, decalage, longueur)


# ---------------------------------------------------------------------------------------------
# rANS (§ 4.9) : tables, LUT, décodage vectorisé sur les tuiles (indépendantes par construction)
# ---------------------------------------------------------------------------------------------

def lut_depuis_frequences(freq, geometrie):
    freq = [int(v) for v in freq]
    if sum(freq) != M_RANS:
        raise ValueError(f"somme des fréquences {sum(freq)} ≠ 4096")
    lut = np.zeros(M_RANS, np.uint32)
    c = 0
    for s, f in enumerate(freq):
        if f == 0:
            continue
        i = np.arange(c, c + f, dtype=np.uint32)
        if geometrie == 1:
            lut[c:c + f] = s | ((f - 1) << 8) | ((i - c) << 20)
        else:
            lut[c:c + f] = s | (f << 4) | ((i - c) << 17)
        c += f
    return lut


def decoder_flux(flux: bytes, luts: np.ndarray, kappa=None):
    """Décode un flux sérialisé (§ 4.9.1) ; luts : (n_contextes, 4096) uint32.

    kappa : None (contexte 0 pour tout symbole) ou tableau de la classe d'échelle de chaque bloc
    (table par voie, § 4.9.3 : le mot w appartient au bloc ⌊w/4⌋).
    Rend (sortie, bilan) ; le bilan compte les voies hors de L et les fins de tuile.
    """
    P, N, geo, res, T, W = struct.unpack_from("<IHBBII", flux, 0)
    bilan = {"P": P, "N": N, "geometrie": geo, "reserve": res, "T": T, "W": W}
    if P % 128:
        raise ValueError("P non multiple de 128")
    total_m = P // 128
    if T != -(-total_m // N):
        raise ValueError(f"T = {T} ≠ ⌈{total_m}/{N}⌉")
    off = 16
    debut = np.frombuffer(flux, "<u4", T, off).astype(np.int64); off += 4 * T
    etats = np.frombuffer(flux, "<u4", 32 * T, off).reshape(T, 32).astype(np.uint64); off += 128 * T
    mots = np.frombuffer(flux, "<u2", W, off).astype(np.uint64); off += 2 * W
    bilan["octets_serialises"] = off
    nsous = 4 if geo == 1 else 8
    x = etats.copy()
    p = debut.copy()
    sortie = np.zeros(P, np.uint8)
    voies = np.arange(32, dtype=np.int64)
    tuiles = np.arange(T, dtype=np.int64)
    for ml in range(N):
        m = tuiles * N + ml
        act = np.nonzero(m < total_m)[0]
        if act.size == 0:
            break
        w = m[act, None] * 32 + voies[None, :]
        ctx = np.zeros_like(w) if kappa is None else kappa[w >> 2]
        xa = x[act]
        pa = p[act]
        for k in range(nsous):
            e = luts[ctx, (xa & 4095).astype(np.int64)].astype(np.uint64)
            if geo == 1:
                s = e & 0xFF
                f = ((e >> 8) & 0xFFF) + 1
                b = e >> 20
            else:
                s = e & 0xF
                f = (e >> 4) & 0x1FFF
                b = e >> 17
            y = f * (xa >> 12) + b
            besoin = y < L_RANS
            cs = np.cumsum(besoin, axis=1)
            idx = np.clip(pa[:, None] + cs - 1, 0, max(W - 1, 0))
            xa = np.where(besoin, (y << 16) | mots[idx], y)
            pa = pa + cs[:, -1]
            if geo == 1:
                sortie[4 * w + k] = s.astype(np.uint8)
            else:
                octet = 4 * w + (k >> 1)
                sortie[octet] |= (s.astype(np.uint8) << (4 * (k & 1))).astype(np.uint8)
        x[act] = xa
        p[act] = pa
    hors_L = int(np.count_nonzero(x != L_RANS))
    fins = np.append(debut[1:], W)
    bilan["voies_hors_L"] = hors_L
    bilan["tuiles_fin_differente_du_debut_suivant"] = int(np.count_nonzero(p != fins))
    bilan["mots_lus"] = int((p - debut).sum())
    return sortie, bilan


# ---------------------------------------------------------------------------------------------
# Le fichier .trc
# ---------------------------------------------------------------------------------------------

class Trc:
    def __init__(self, chemin, constats):
        self.chemin = chemin
        self.f = open(chemin, "rb")
        self.constats = constats
        h = lire(self.f, 0, 4096)
        self.h = h
        c = constats
        c["magie"] = h[:8] == b"TRONCONS"
        self.vmaj, self.vmin, self.drapeaux, self.alignement, self.taille_entete = \
            struct.unpack_from("<HHIII", h, 8)
        (self.taille_fichier,) = struct.unpack_from("<Q", h, 24)
        self.sha_source = h[32:64]
        (self.taille_source,) = struct.unpack_from("<Q", h, 64)
        self.L, self.E, self.k, self.n_mat = struct.unpack_from("<HHHH", h, 72)
        self.lignes = struct.unpack_from("<4I", h, 80)
        self.colonnes = struct.unpack_from("<4I", h, 96)
        self.poids_bloc, self.octets_bloc = struct.unpack_from("<II", h, 112)
        self.type_ggml, self.niveaux, self.classes, res123 = struct.unpack_from("<BBBB", h, 120)
        self.partition = list(h[124:132])
        (res132,) = struct.unpack_from("<I", h, 132)
        self.sections = [struct.unpack_from("<QQ", h, 136 + 16 * i) for i in range(8)]
        (emp,) = struct.unpack_from("<Q", h, 4088)
        c["entete"] = {
            "version": [self.vmaj, self.vmin], "drapeaux": self.drapeaux,
            "alignement": self.alignement, "taille_entete": self.taille_entete,
            "taille_fichier_declaree": self.taille_fichier,
            "taille_fichier_reelle": os.path.getsize(chemin),
            "sha256_source": self.sha_source.hex(), "taille_source": self.taille_source,
            "L": self.L, "E": self.E, "k": self.k, "matrices": self.n_mat,
            "lignes": self.lignes, "colonnes": self.colonnes, "poids_bloc": self.poids_bloc,
            "octets_bloc": self.octets_bloc, "type_ggml": self.type_ggml,
            "niveaux": self.niveaux, "classes_echelle": self.classes, "partition": self.partition,
            "reserve_123": res123, "reserve_132": res132, "sections": self.sections,
            "zeros_264_4088": all(v == 0 for v in h[264:4088]),
            "empreinte_lue": f"{emp:016x}", "empreinte_calculee": f"{empreinte64(h[:4088]):016x}",
        }
        e = c["entete"]
        e["empreinte_ok"] = e["empreinte_lue"] == e["empreinte_calculee"]
        e["taille_ok"] = e["taille_fichier_declaree"] == e["taille_fichier_reelle"]
        e["sections_alignees"] = all(d % 4096 == 0 for d, _ in self.sections[:5])
        e["sections_reservees_nulles"] = all(s == (0, 0) for s in self.sections[5:])
        e["drapeaux_connus"] = (self.drapeaux & ~0b111) == 0
        self.brut = bool(self.drapeaux & 4)

    def section(self, i):
        d, n = self.sections[i]
        return lire(self.f, d, n)

    # § 4.4
    def verifier_meta(self, gguf):
        s = self.section(0)
        (n,) = struct.unpack_from("<Q", s, 0)
        pos = 8
        cles = []
        for _ in range(n):
            (lk,) = struct.unpack_from("<Q", s, pos); pos += 8
            cle = s[pos:pos + lk].decode(); pos += lk
            (t,) = struct.unpack_from("<I", s, pos); pos += 4
            v, pos = gguf._valeur(s, pos, t)
            cles.append((cle, v))
        (emp,) = struct.unpack_from("<Q", s, pos)
        r = {"n_paires": n, "n_kv_gguf": gguf.n_kv,
             "empreinte_ok": emp == empreinte64(s[:pos]),
             "zeros_apres": all(v == 0 for v in s[pos + 8:]),
             "longueur_section": len(s), "fin_utile": pos + 8,
             "ajoutees": [[k, v] for k, v in cles[gguf.n_kv:]]}
        brut_gguf = gguf.tete[gguf.debut_kv:gguf.fin_kv]
        r["paires_gguf_octet_pour_octet"] = s[8:8 + len(brut_gguf)] == brut_gguf
        r["section_multiple_4096"] = len(s) % 4096 == 0
        self.meta = dict(cles)
        return r

    # § 4.5
    def verifier_residents(self, gguf, complets):
        d0, n0 = self.sections[1]
        tete = lire(self.f, d0, 8)
        n, res = struct.unpack_from("<II", tete, 0)
        table = lire(self.f, d0, 8 + 128 * n)
        entrees = []
        for i in range(n):
            b = table[8 + 128 * i: 8 + 128 * (i + 1)]
            nom = b[:64].rstrip(b"\0").decode()
            typ, nd = struct.unpack_from("<II", b, 64)
            ne = list(struct.unpack_from("<4Q", b, 72))
            dec, octets, emp = struct.unpack_from("<QQQ", b, 104)
            entrees.append({"nom": nom, "type": typ, "n_dims": nd, "ne": ne, "decalage": dec,
                            "octets": octets, "empreinte": emp,
                            "zeros_nom": all(v == 0 for v in b[len(nom.encode()):64])})
        debut_donnees = d0 + (8 + 128 * n + 4095) // 4096 * 4096
        fin_derniere = max(e["decalage"] + e["octets"] for e in entrees)
        # l'empreinte de la table est « après la zone de données » : on cherche où
        attendu = empreinte64(table)
        positions = {}
        for nomp, rel in (("fin_exacte", fin_derniere),
                          ("aligne_8", (fin_derniere + 7) // 8 * 8),
                          ("aligne_256", (fin_derniere + 255) // 256 * 256)):
            (v,) = struct.unpack_from("<Q", lire(self.f, debut_donnees + rel, 8))
            positions[nomp] = v == attendu
        r = {"n_tenseurs": n, "reserve": res, "debut_donnees_absolu": debut_donnees,
             "longueur_section": n0, "fin_derniere_relative": fin_derniere,
             "empreinte_table_trouvee_a": positions}
        # attendus : tous les tenseurs du GGUF sauf blk.*.ffn_{gate,up,down}_exps.{weight,bias}
        attendus = [t for t in gguf.tenseurs_ordre
                    if not any(t.endswith(f".ffn_{m}_exps.{q}") for m in ("gate", "up", "down")
                               for q in ("weight", "bias"))]
        r["n_attendus"] = len(attendus)
        r["memes_noms_meme_ordre"] = [e["nom"] for e in entrees] == attendus
        r["memes_noms_ensemble"] = sorted(e["nom"] for e in entrees) == sorted(attendus)
        defauts = []
        for e in entrees:
            g = gguf.tenseurs.get(e["nom"])
            if g is None:
                defauts.append([e["nom"], "absent du GGUF"]); continue
            ne_att = g["ne"] + [1] * (4 - len(g["ne"]))
            if (e["type"], e["n_dims"], e["ne"], e["octets"]) != (g["type"], g["n_dims"], ne_att,
                                                                  g["octets"]):
                defauts.append([e["nom"], "forme"])
            if e["decalage"] % 256:
                defauts.append([e["nom"], "décalage non multiple de 256"])
            if not e["zeros_nom"]:
                defauts.append([e["nom"], "nom non complété de zéros"])
        r["defauts_forme"] = defauts
        r["octets_residents"] = sum(e["octets"] for e in entrees)
        if complets:
            faux = []
            for e in entrees:
                g = gguf.tenseurs[e["nom"]]
                a = lire(self.f, debut_donnees + e["decalage"], e["octets"])
                b = gguf.lire(g["absolu"], g["octets"])
                if a != b:
                    faux.append([e["nom"], "octets"])
                elif empreinte64(a) != e["empreinte"]:
                    faux.append([e["nom"], "empreinte"])
            r["complets_verifies"] = len(entrees)
            r["complets_faux"] = faux
        self.residents = entrees
        return r

    # § 4.6
    def lire_tables(self):
        s = self.section(2)
        n, res = struct.unpack_from("<II", s, 0)
        pos = 8
        self.tables = {}
        tailles = {1: 32, 2: 512, 3: 16}
        sommes_fausses = []
        types_vus = {}
        for _ in range(n):
            couche, mat, sorte, ctx, tc, r2 = struct.unpack_from("<HBBBBH", s, pos)
            pos += 8
            charge = s[pos:pos + tailles[tc]]; pos += tailles[tc]
            types_vus[(sorte, ctx, tc)] = types_vus.get((sorte, ctx, tc), 0) + 1
            if tc in (1, 2):
                freq = struct.unpack(f"<{tailles[tc] // 2}H", charge)
                if sum(freq) != 4096:
                    sommes_fausses.append([couche, mat, sorte, ctx])
                self.tables[(couche, mat, sorte, ctx)] = list(freq)
            else:
                self.tables[(couche, mat, sorte, ctx)] = list(struct.unpack("<4f", charge))
        (emp,) = struct.unpack_from("<Q", s, pos)
        return {"n_enregistrements": n, "reserve": res,
                "empreinte_ok": emp == empreinte64(s[:pos]),
                "zeros_apres": all(v == 0 for v in s[pos + 8:]),
                "sommes_differentes_de_4096": sommes_fausses,
                "sortes_contextes_charges": {f"{k[0]:#04x}/{k[1]}/{k[2]}": v
                                             for k, v in sorted(types_vus.items())}}

    # § 4.7
    def lire_repertoire(self):
        s = self.section(3)
        n = self.L * self.E
        self.rep = {}
        defauts = []
        prec_fin = None
        for i in range(n):
            b = s[64 * i: 64 * (i + 1)]
            dec, l0, l1, u0, u1, eo, e0, e1, couche, expert, r52, r56 = \
                struct.unpack("<QIIIIQQQHHIQ", b)
            if (couche, expert) != divmod(i, self.E):
                defauts.append([i, "ordre (couche, expert)"])
            if dec % 4096 or l0 % 4096 or l1 % 4096:
                defauts.append([i, "alignement"])
            if r52 or r56:
                defauts.append([i, "réservé non nul"])
            if prec_fin is not None and dec != prec_fin:
                defauts.append([i, f"trou ou recouvrement : {dec} ≠ {prec_fin}"])
            prec_fin = dec + l0 + l1
            self.rep[(couche, expert)] = dict(decalage=dec, longueur=[l0, l1], utiles=[u0, u1],
                                              empreinte_origine=eo, empreinte_niveau=[e0, e1])
        (emp,) = struct.unpack_from("<Q", s, 64 * n)
        d4 = self.sections[4]
        premier = self.rep[(0, 0)]["decalage"]
        return {"entrees": n, "empreinte_ok": emp == empreinte64(s[:64 * n]),
                "defauts": defauts[:20], "n_defauts": len(defauts),
                "premier_troncon_au_debut_de_TRONCONS": premier == d4[0],
                "fin_dernier_troncon": prec_fin, "fin_section_TRONCONS": d4[0] + d4[1],
                "fin_fichier": self.taille_fichier}

    def luts(self, couche, mat, sorte, contextes, geo, casser_table=False):
        out = []
        for c in contextes:
            f = list(self.tables[(couche, mat, sorte, c)])
            if casser_table:
                # cassure : deux fréquences non nulles échangées (même somme)
                nz = [i for i, v in enumerate(f) if v > 0]
                a, b = nz[0], nz[1]
                f[a], f[b] = f[b], f[a]
                casser_table = False
            out.append(lut_depuis_frequences(f, geo))
        return np.stack(out)


# ---------------------------------------------------------------------------------------------
# Reconstruction d'un expert (§ 4.8 à 4.11) et comparaison au GGUF
# ---------------------------------------------------------------------------------------------

def decoder_expert(trc: Trc, couche, expert, casser=None):
    ent = trc.rep[(couche, expert)]
    t0 = time.perf_counter()
    partie = bytearray(lire(trc.f, ent["decalage"], ent["longueur"][0]))
    magie, c_, x_, niv, nmat, nflux, utiles = struct.unpack_from("<IHHBBHI", partie, 0)
    r = {"couche": couche, "expert": expert, "decalage": ent["decalage"],
         "longueur0": ent["longueur"][0], "utiles0": ent["utiles"][0],
         "entete_partie": {"magie": f"{magie:#010x}", "couche": c_, "expert": x_, "niveau": niv,
                           "n_matrices": nmat, "n_flux": nflux, "utiles": utiles,
                           "reserve_zeros": all(v == 0 for v in partie[16:64])},
         "zeros_apres_utiles": all(v == 0 for v in partie[utiles:])}
    r["entete_ok"] = (magie == 0x30435254 and (c_, x_) == (couche, expert) and niv == 0
                      and nmat == 3 and utiles == ent["utiles"][0])
    r["empreinte_partie_ok"] = empreinte64(bytes(partie[:utiles])) == ent["empreinte_niveau"][0]
    flux = []
    for i in range(nflux):
        so, ma, cf, rr, dec, lon, prod = struct.unpack_from("<BBBBIII", partie, 64 + 16 * i)
        flux.append(dict(sorte=so, matrice=ma, contexte=cf, reserve=rr, decalage=dec,
                         longueur=lon, produits=prod))
    r["flux"] = [[f["sorte"], f["matrice"], f["contexte"], f["decalage"], f["longueur"],
                  f["produits"]] for f in flux]
    r["flux_alignes_16"] = all(f["decalage"] % 16 == 0 for f in flux)
    r["flux_reserves_nuls"] = all(f["reserve"] == 0 for f in flux)
    r["contextes_fixes"] = sorted({(f["sorte"], f["contexte"]) for f in flux})
    attendu = [(s, j) for j in range(3) for s in (1, 2, 3, 4)]
    r["ordre_flux_conforme_4_8"] = [(f["sorte"], f["matrice"]) for f in flux] == attendu

    if casser == "mot":
        # cassure : un bit retourné au milieu des mots du flux CODES_CTX de la matrice 0
        fc = [f for f in flux if f["sorte"] == 4 and f["matrice"] == 0][0]
        partie[fc["decalage"] + fc["longueur"] // 2] ^= 0x10

    def charge(sorte, j):
        f = [f for f in flux if f["sorte"] == sorte and f["matrice"] == j]
        if len(f) != 1:
            raise ValueError(f"flux sorte {sorte} matrice {j} : {len(f)} trouvés")
        f = f[0]
        return f, bytes(partie[f["decalage"]: f["decalage"] + f["longueur"]])

    origine = bytearray()
    biais_tout = bytearray()
    bilans = []
    matrices = []
    for j in range(3):
        R, C = trc.lignes[j], trc.colonnes[j]
        B = C // 32
        fm, med = charge(1, j)
        med = np.frombuffer(med, np.uint8, R).copy()
        if casser == "mediane" and j == 0:
            med[R // 2] ^= 1
        fb, biais = charge(2, j)
        fd, fdelta = charge(3, j)
        luts_d = trc.luts(couche, j, 3, [0], 1)
        delta, bd = decoder_flux(fdelta, luts_d, None)
        delta = delta[: R * B].reshape(R, B)
        e = ((med[:, None].astype(np.int64) + delta.astype(np.int64) - 128) % 256).astype(np.uint8)
        # § 4.10 : la médiane est tri[B/2] des B échelles de la ligne (non requis pour décoder)
        med_recalc = np.sort(e, axis=1)[:, B // 2]
        medianes_conformes = int(np.count_nonzero(med_recalc == med))
        kappa = np.where(delta < 128, 0, np.where(delta == 128, 1, 2)).reshape(-1).astype(np.int64)
        fq, fcodes = charge(4, j)
        luts_q = trc.luts(couche, j, 4, [0, 1, 2], 1,
                          casser_table=(casser == "table" and j == 0))
        if casser == "lut" and j == 0:
            luts_q = luts_q.copy()
            luts_q[1, 2048] ^= np.uint32(1 << 20)   # une fente de LUT corrompue
        qs, bq = decoder_flux(fcodes, luts_q, kappa)
        qs = qs[: R * B * 16].reshape(R * B, 16)
        bloc = np.empty((R * B, 17), np.uint8)
        bloc[:, 0] = e.reshape(-1)
        bloc[:, 1:] = qs
        origine += bloc.tobytes()
        biais_tout += biais[: 4 * R]
        bilans.append({"matrice": j, "delta": bd, "codes": bq,
                       "produits_declares": [fd["produits"], fq["produits"]],
                       "longueur_biais": len(biais), "longueur_medianes": fm["longueur"],
                       "medianes_egales_tri_B_2": medianes_conformes, "lignes": R})
        matrices.append(bloc)
    origine += biais_tout
    r["bilans"] = bilans
    r["voies_hors_L"] = sum(b["delta"]["voies_hors_L"] + b["codes"]["voies_hors_L"] for b in bilans)
    r["empreinte_origine_ok"] = empreinte64(bytes(origine)) == ent["empreinte_origine"]
    r["secondes_decodage"] = round(time.perf_counter() - t0, 3)
    return r, bytes(origine), matrices


def octets_gguf_expert(gguf: Gguf, trc: Trc, couche, expert):
    """§ 4.11, équivalence au GGUF : bloc β de l'expert x à (x·R + r)·B + b blocs du tenseur."""
    parts = []
    biais = []
    for j, nom in enumerate(("gate", "up", "down")):
        R, C = trc.lignes[j], trc.colonnes[j]
        B = C // 32
        t = gguf.tenseurs[f"blk.{couche}.ffn_{nom}_exps.weight"]
        n = R * B * 17
        parts.append(gguf.lire(t["absolu"] + expert * n, n))
        tb = gguf.tenseurs[f"blk.{couche}.ffn_{nom}_exps.bias"]
        biais.append(gguf.lire(tb["absolu"] + expert * R * 4, R * 4))
    return b"".join(parts) + b"".join(biais)


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("trc")
    ap.add_argument("gguf")
    ap.add_argument("journal")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--graine", type=int, default=20261016)
    ap.add_argument("--casser", choices=["mot", "table", "mediane", "lut"])
    ap.add_argument("--residents-complets", action="store_true")
    ap.add_argument("--cibles", help="tronçons nommés « couche:expert,… » au lieu du tirage")
    a = ap.parse_args()

    debut = datetime.datetime.now().isoformat(timespec="seconds")
    j = {"outil": "mesures/moteur/epreuve-J1/decodeur_s4.py", "debut": debut,
         "commande": sys.argv, "graine": a.graine, "casser": a.casser}
    gguf = Gguf(a.gguf)
    j["gguf"] = {"chemin": a.gguf, "version": gguf.version, "n_tenseurs": gguf.n_tenseurs,
                 "n_kv": gguf.n_kv, "alignement": gguf.alignement,
                 "taille": os.path.getsize(a.gguf)}
    trc = Trc(a.trc, j)
    j["entete"]["taille_source_egale_gguf"] = trc.taille_source == j["gguf"]["taille"]
    j["meta"] = trc.verifier_meta(gguf)
    j["residents"] = trc.verifier_residents(gguf, a.residents_complets)
    j["tables"] = trc.lire_tables()
    j["repertoire"] = trc.lire_repertoire()

    rng = np.random.default_rng(a.graine)
    tires = rng.choice(trc.L * trc.E, size=a.n, replace=False)
    if a.cibles:
        tires = [int(c) * trc.E + int(e) for c, e in (x.split(":") for x in a.cibles.split(","))]
        a.n = len(tires)
    j["tires"] = [[int(t) // trc.E, int(t) % trc.E] for t in tires]
    resultats = []
    for i, t in enumerate(tires):
        couche, expert = int(t) // trc.E, int(t) % trc.E
        casser = a.casser if i == 0 else None
        try:
            r, orig, _ = decoder_expert(trc, couche, expert, casser)
        except Exception as ex:  # une erreur de format est une détection, nommée
            r = {"couche": couche, "expert": expert, "erreur_format": repr(ex), "tient": False}
            resultats.append(r)
            print(f"[{i + 1}/{a.n}] couche {couche} expert {expert} : TOMBE (erreur de format : {ex})", flush=True)
            continue
        g = octets_gguf_expert(gguf, trc, couche, expert)
        r["egal_gguf_octet_pour_octet"] = orig == g
        if orig != g:
            ao = np.frombuffer(orig, np.uint8)
            ag = np.frombuffer(g, np.uint8)
            if ao.size == ag.size:
                d = np.nonzero(ao != ag)[0]
                r["octets_differents"] = int(d.size)
                r["premier_octet_different"] = int(d[0])
            else:
                r["tailles"] = [ao.size, ag.size]
        r["tient"] = bool(r["egal_gguf_octet_pour_octet"] and r["empreinte_origine_ok"]
                          and r["voies_hors_L"] == 0 and r["empreinte_partie_ok"]
                          and r["entete_ok"])
        resultats.append(r)
        print(f"[{i + 1}/{a.n}] couche {couche} expert {expert} : "
              f"{'TIENT' if r['tient'] else 'TOMBE'} ({r['secondes_decodage']} s, "
              f"hors L {r['voies_hors_L']}, gguf {r['egal_gguf_octet_pour_octet']}, "
              f"empreinte {r['empreinte_origine_ok']})", flush=True)
    j["troncons"] = resultats
    j["n_tiennent"] = sum(r["tient"] for r in resultats)
    j["fin"] = datetime.datetime.now().isoformat(timespec="seconds")
    with open(a.journal, "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False, indent=1, default=str)
    print(f"{j['n_tiennent']}/{a.n} tronçons égaux au GGUF au bit près")


if __name__ == "__main__":
    principal()
