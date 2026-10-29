"""Le décodeur indépendant du juge de la construction : le format .trc (v1.0 et v1.2), lu et décodé
depuis la seule description de decisions/ARCHITECTURE.md §§ 4.2 à 4.12 et 4.16, et le GGUF lu par son
propre lecteur. Aucun code du dépôt n'est importé ni recopié (ni trc-format, ni trc-codec, ni le
décodeur de l'épreuve J1, ni les outils du lot A).

Seuils : mesures/genome/construction/juge/00-seuils-declares.md (J-T0, J-T1), commit 1f5fe0f.

  python -I -X utf8 decodeur_juge.py tirage
      Le tirage des experts (graine 20261022), écrit avant tout décodage.
  python -I -X utf8 decodeur_juge.py fichiers
      J-T0 : en-têtes, sections, empreintes, répertoire, tables, tailles des quatre fichiers.
  python -I -X utf8 decodeur_juge.py echantillon [--n20 32] [--n120 64]
      J-T1 : les experts tirés décodés (v1.2), le témoin (v1.0), les trois cassures.

Le décodage rANS (§ 4.9.2) est vectorisé : toutes les voies de toutes les tuiles d'un flux avancent
ensemble, sous-pas par sous-pas. Le pas d'une voie ne dépend que de son état et de la table de son
contexte ; seuls les mots du flux partagé lient les voies d'une tuile : au sous-pas k, les voies qui
renouvellent (y < L) prennent, dans l'ordre l = 0 … 31, les mots p, p + 1, … de leur tuile. Une somme
préfixe sur l'axe des voies donne à chacune son mot ; c'est exactement l'ordre séquentiel du format.
"""
import hashlib
import json
import pathlib
import struct
import sys
import time

import numpy as np

DEPOT = pathlib.Path(__file__).resolve().parents[4]
JOURNAUX = DEPOT / "mesures" / "genome" / "construction" / "juge"
MODELES = pathlib.Path("~/dev/modeles")
GGUF = {"20b": MODELES / "gguf" / "gpt-oss-20b-MXFP4.gguf", "120b": MODELES / "gguf" / "gpt-oss-120b-MXFP4.gguf"}
TRC = {("20b", "v10"): MODELES / "trc" / "gpt-oss-20b.trc", ("20b", "v12"): MODELES / "trc" / "gpt-oss-20b-v12.trc",
       ("120b", "v10"): MODELES / "trc" / "gpt-oss-120b.trc", ("120b", "v12"): MODELES / "trc" / "gpt-oss-120b-v12.trc"}
GRAINE = 20261022

# Constantes du flux rANS (§ 4.9.2)
M_BITS = 12
M = 1 << M_BITS
L = 1 << 16
SORTES = {1: "MEDIANES", 2: "BIAIS", 3: "DELTA", 4: "CODES_CTX", 6: "CODES_BRUTS", 7: "ECHELLES_BRUTES",
          0x10: "BASE_CTX", 0x11: "COMPL_CTX", 0x12: "CENTRES"}
# Les 31 octets qui portent un demi-octet 8 (§ 4.16).
OCTETS_AVEC_8 = [b for b in range(256) if (b & 15) == 8 or (b >> 4) == 8]
assert len(OCTETS_AVEC_8) == 31
# Valeurs E2M1 des 16 codes (doublées : la valeur exacte importe peu, seule l'égalité compte).
E2M1 = np.array([0, 1, 2, 3, 4, 6, 8, 12, -0.0, -1, -2, -3, -4, -6, -8, -12], dtype=np.float64)


def empreinte64(octets) -> int:
    """§ 4.12 : les 8 premiers octets de SHA-256, lus comme un u64 petit-boutiste."""
    return struct.unpack("<Q", hashlib.sha256(octets).digest()[:8])[0]


# ============================================================================ GGUF (lecteur propre)

class LecteurOctets:
    def __init__(self, f, pos=0):
        self.f = f
        self.f.seek(pos)

    def lire(self, n):
        b = self.f.read(n)
        if len(b) != n:
            raise EOFError("fin de fichier inattendue")
        return b

    def u8(self): return self.lire(1)[0]
    def u32(self): return struct.unpack("<I", self.lire(4))[0]
    def u64(self): return struct.unpack("<Q", self.lire(8))[0]
    def chaine(self): return self.lire(self.u64()).decode("utf-8")

    def pos(self): return self.f.tell()


TAILLE_SCALAIRE_GGUF = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}


def sauter_valeur_gguf(r, t):
    """Lit (et rend, pour les scalaires et les chaînes) une valeur GGUF v3 de type t."""
    if t in TAILLE_SCALAIRE_GGUF:
        b = r.lire(TAILLE_SCALAIRE_GGUF[t])
        fmt = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}[t]
        return struct.unpack(fmt, b)[0]
    if t == 8:
        return r.chaine()
    if t == 9:
        te = r.u32()
        n = r.u64()
        if te in TAILLE_SCALAIRE_GGUF:
            r.f.seek(n * TAILLE_SCALAIRE_GGUF[te], 1)
        else:
            for _ in range(n):
                sauter_valeur_gguf(r, te)
        return None
    raise ValueError(f"type GGUF inconnu {t}")


def lire_paires_gguf(r, n):
    paires = {}
    for _ in range(n):
        cle = r.chaine()
        t = r.u32()
        paires[cle] = sauter_valeur_gguf(r, t)
    return paires


class Gguf:
    def __init__(self, chemin):
        self.chemin = pathlib.Path(chemin)
        self.f = open(self.chemin, "rb")
        r = LecteurOctets(self.f)
        if r.lire(4) != b"GGUF":
            raise ValueError("pas un GGUF")
        self.version = r.u32()
        if self.version != 3:
            raise ValueError(f"GGUF v{self.version}")
        n_t = r.u64()
        n_kv = r.u64()
        self.paires = lire_paires_gguf(r, n_kv)
        self.tenseurs = {}
        for _ in range(n_t):
            nom = r.chaine()
            nd = r.u32()
            ne = [r.u64() for _ in range(nd)]
            typ = r.u32()
            dec = r.u64()
            self.tenseurs[nom] = {"ne": ne, "type": typ, "decalage": dec}
        al = int(self.paires.get("general.alignment", 32))
        p = r.pos()
        self.donnees = (p + al - 1) // al * al

    def tranche(self, nom, debut, n):
        t = self.tenseurs[nom]
        self.f.seek(self.donnees + t["decalage"] + debut)
        b = self.f.read(n)
        if len(b) != n:
            raise EOFError(nom)
        return b

    def expert(self, couche, x, R, C):
        """Les blocs [e, qs] des trois matrices de l'expert x (ordre β, § 4.11) et ses biais f32.
        Équivalence au GGUF (§ 4.11) : le bloc β = r·B + b de l'expert x est au bloc (x·R + r)·B + b."""
        B = C // 32
        blocs, biais = [], []
        for nom in ("gate", "up", "down"):
            tw = f"blk.{couche}.ffn_{nom}_exps.weight"
            t = self.tenseurs[tw]
            assert t["type"] == 39, (tw, t["type"])          # MXFP4
            assert t["ne"][0] == C and t["ne"][1] == R, (tw, t["ne"])
            blocs.append(self.tranche(tw, 17 * x * R * B, 17 * R * B))
            tb = f"blk.{couche}.ffn_{nom}_exps.bias"
            assert self.tenseurs[tb]["type"] == 0 and self.tenseurs[tb]["ne"][0] == R
            biais.append(self.tranche(tb, 4 * x * R, 4 * R))
        return blocs, biais


def canoniser_qs(blocs: bytes, actif=True) -> bytes:
    """Remplace tout demi-octet 8 des qs par 0 ; l'octet e (premier des 17) ne change pas."""
    a = np.frombuffer(blocs, dtype=np.uint8).reshape(-1, 17).copy()
    if actif:
        q = a[:, 1:]
        lo = q & 15
        hi = q >> 4
        lo[lo == 8] = 0
        hi[hi == 8] = 0
        a[:, 1:] = lo | (hi << 4)
    return a.tobytes()


def demi_octets(qs: np.ndarray) -> np.ndarray:
    return np.stack([qs & 15, qs >> 4], axis=-1).reshape(-1)


# ============================================================================ .trc (lecteur propre)

class Trc:
    def __init__(self, chemin):
        self.chemin = pathlib.Path(chemin)
        self.f = open(self.chemin, "rb")
        self.taille_disque = self.chemin.stat().st_size
        h = self.f.read(4096)
        self.entete = h
        self.magie = h[0:8]
        self.v_maj, self.v_min = struct.unpack_from("<HH", h, 8)
        self.drapeaux, self.alignement, self.taille_entete = struct.unpack_from("<III", h, 12)
        self.taille_declaree = struct.unpack_from("<Q", h, 24)[0]
        self.sha_gguf = h[32:64].hex()
        self.taille_gguf = struct.unpack_from("<Q", h, 64)[0]
        self.L, self.E, self.k, self.n_mat = struct.unpack_from("<HHHH", h, 72)
        self.lignes = struct.unpack_from("<4I", h, 80)
        self.colonnes = struct.unpack_from("<4I", h, 96)
        self.poids_bloc, self.octets_bloc = struct.unpack_from("<II", h, 112)
        self.type_ggml, self.niveaux, self.classes, self.reserve123 = h[120], h[121], h[122], h[123]
        self.sections = [struct.unpack_from("<QQ", h, 136 + 16 * i) for i in range(8)]
        self.empreinte_entete = struct.unpack_from("<Q", h, 4088)[0]
        self.reserve_zero = all(b == 0 for b in h[264:4088]) and struct.unpack_from("<I", h, 132)[0] == 0

    def lire(self, pos, n):
        self.f.seek(pos)
        b = self.f.read(n)
        if len(b) != n:
            raise EOFError(f"{self.chemin.name} : {pos}+{n}")
        return b

    # ---------------------------------------------------------------- sections
    def section(self, i):
        d, n = self.sections[i]
        return self.lire(d, n)

    def controler_meta(self):
        s = self.section(0)
        f = _Tampon(s)
        n = f.u64()
        for _ in range(n):
            f.lire(f.u64())          # clé
            t = f.u32()
            f.valeur_gguf(t)
        fin = f.p
        emp = struct.unpack_from("<Q", s, fin)[0]
        zeros = all(b == 0 for b in s[fin + 8:])
        return {"n_paires": n, "empreinte_tient": emp == empreinte64(s[:fin]), "zeros_apres": zeros}

    def controler_residents(self):
        d, n = self.sections[1]
        tete = self.lire(d, 8)
        nt, res = struct.unpack("<II", tete)
        table = self.lire(d, 8 + 128 * nt)
        entrees = []
        for i in range(nt):
            e = table[8 + 128 * i: 8 + 128 * (i + 1)]
            nom = e[:64].rstrip(b"\0").decode("utf-8")
            off, octets, emp = struct.unpack_from("<QQQ", e, 104)
            entrees.append((nom, off, octets, emp))
        zone = d + (8 + 128 * nt + 4095) // 4096 * 4096
        fin_donnees = max(o + b for _, o, b, _ in entrees)
        e_table = empreinte64(table)
        trouve = None
        for cand in (fin_donnees, (fin_donnees + 255) // 256 * 256, (fin_donnees + 7) // 8 * 8):
            if zone + cand + 8 <= d + n and struct.unpack("<Q", self.lire(zone + cand, 8))[0] == e_table:
                trouve = cand
                break
        return {"n_tenseurs": nt, "reserve": res, "empreinte_table_tient": trouve is not None,
                "position_empreinte": None if trouve is None else ("fin des données" if trouve == fin_donnees else f"alignée ({trouve - fin_donnees} o de bourrage)")}

    def tables(self):
        s = self.section(2)
        n, res = struct.unpack_from("<II", s, 0)
        p = 8
        tables = {}
        for _ in range(n):
            couche, mat, sorte, ctx, tc, r2 = struct.unpack_from("<HBBBBH", s, p)
            p += 8
            taille = {1: 32, 2: 512, 3: 16}[tc]
            charge = s[p:p + taille]
            p += taille
            if tc == 1:
                val = np.frombuffer(charge, dtype="<u2").astype(np.int64)
            elif tc == 2:
                val = np.frombuffer(charge, dtype="<u2").astype(np.int64)
            else:
                val = np.frombuffer(charge, dtype="<f4").astype(np.float64)
            tables[(couche, mat, sorte, ctx)] = (tc, val)
        emp = struct.unpack_from("<Q", s, p)[0]
        return tables, emp == empreinte64(s[:p]), n

    def repertoire(self):
        d, n = self.sections[3]
        s = self.lire(d, n)
        ne = self.L * self.E
        rep = []
        for i in range(ne):
            e = s[64 * i: 64 * (i + 1)]
            off, l0, l1, u0, u1 = struct.unpack_from("<QIIII", e, 0)
            e_orig, e_u0, e_u1 = struct.unpack_from("<QQQ", e, 24)
            couche, expert, res = struct.unpack_from("<HHI", e, 48)
            e_can = struct.unpack_from("<Q", e, 56)[0]
            rep.append({"decalage": off, "l0": l0, "l1": l1, "u0": u0, "u1": u1, "e_origine": e_orig, "e_u0": e_u0,
                        "e_u1": e_u1, "couche": couche, "expert": expert, "reserve": res, "e_canonique": e_can})
        emp = struct.unpack_from("<Q", s, 64 * ne)[0]
        return rep, emp == empreinte64(s[:64 * ne])

    # ---------------------------------------------------------------- une partie de tronçon
    def partie(self, entree):
        return self.lire(entree["decalage"], entree["u0"])


class _Tampon:
    def __init__(self, b):
        self.b = b
        self.p = 0

    def lire(self, n):
        r = self.b[self.p:self.p + n]
        self.p += n
        return r

    def u32(self):
        return struct.unpack("<I", self.lire(4))[0]

    def u64(self):
        return struct.unpack("<Q", self.lire(8))[0]

    def valeur_gguf(self, t):
        if t in TAILLE_SCALAIRE_GGUF:
            self.p += TAILLE_SCALAIRE_GGUF[t]
        elif t == 8:
            n = self.u64()          # (lu d'abord : « self.p += self.u64() » perdrait les 8 octets lus)
            self.p += n
        elif t == 9:
            te = self.u32()
            n = self.u64()
            if te in TAILLE_SCALAIRE_GGUF:
                self.p += n * TAILLE_SCALAIRE_GGUF[te]
            else:
                for _ in range(n):
                    self.valeur_gguf(te)
        else:
            raise ValueError(t)


# ============================================================================ rANS (§ 4.9)

class Table:
    """Une table de fréquences (somme 4 096) et sa LUT : pour chaque fente, le symbole."""

    def __init__(self, freq):
        freq = np.asarray(freq, dtype=np.int64)
        if freq.sum() != M:
            raise ValueError(f"somme des fréquences {freq.sum()} ≠ {M}")
        self.freq = freq
        self.cum = np.concatenate([[0], np.cumsum(freq)[:-1]])
        self.sym = np.repeat(np.arange(len(freq)), freq)
        assert len(self.sym) == M


def lire_flux(b: bytes):
    P, N, geo, res, T, W = struct.unpack_from("<IHBBII", b, 0)
    p = 16
    debut = np.frombuffer(b, dtype="<u4", count=T, offset=p).astype(np.int64)
    p += 4 * T
    etats = np.frombuffer(b, dtype="<u4", count=32 * T, offset=p).astype(np.uint64).reshape(T, 32)
    p += 4 * 32 * T
    mots = np.frombuffer(b, dtype="<u2", count=W, offset=p).astype(np.uint64)
    return {"P": P, "N": N, "geo": geo, "T": T, "W": W, "debut": debut, "etats": etats, "mots": mots}


def decoder_flux(flux, tables, contexte_du_mot=None):
    """Décode un flux de géométrie 1 (octets, 4 sous-pas par mot de 32 bits) : § 4.9.2.

    tables : liste de Table (une par contexte) ; contexte_du_mot(w) → indice de table pour le mot w
    (None : une seule table). Rend (octets produits, toutes les voies finissent-elles sur L).
    """
    if flux["geo"] != 1:
        raise ValueError(f"géométrie {flux['geo']} non lue par ce juge (la v1.2 n'en a pas d'autre)")
    P, N, T = flux["P"], flux["N"], flux["T"]
    n_macro = P // 128
    assert P % 128 == 0 and T == -(-n_macro // N), (P, N, T)
    nc = len(tables)
    lut = np.stack([t.sym for t in tables])                      # (nc, 4096)
    fr = np.stack([np.pad(t.freq, (0, 256 - len(t.freq))) for t in tables])
    cu = np.stack([np.pad(t.cum, (0, 256 - len(t.cum))) for t in tables])
    x = flux["etats"].copy()                                     # (T, 32) u64
    p = flux["debut"].copy()                                     # (T,)
    mots = flux["mots"]
    sortie = np.zeros((n_macro, 32, 4), dtype=np.uint8)          # [m, l, k] : octet k du mot m·32 + l
    lignes = np.arange(T)
    voies = np.arange(32, dtype=np.int64)
    for ml in range(N):
        m = lignes * N + ml                                      # macro-pas global de chaque tuile
        actif = m < n_macro
        if not actif.any():
            break
        ma = m[actif]
        if contexte_du_mot is None:
            ctx = np.zeros((actif.sum(), 32), dtype=np.int64)
        else:
            ctx = contexte_du_mot(ma[:, None] * 32 + voies[None, :])
        for k in range(4):
            xa = x[actif]
            fente = (xa & np.uint64(M - 1)).astype(np.int64)
            s = lut[ctx, fente]
            f = fr[ctx, s].astype(np.uint64)
            bb = (fente - cu[ctx, s]).astype(np.uint64)
            y = f * (xa >> np.uint64(M_BITS)) + bb
            renouv = y < np.uint64(L)
            rang = np.cumsum(renouv, axis=1) - 1                  # rang de la voie parmi celles qui renouvellent
            pa = p[actif]
            idx = pa[:, None] + rang
            idx_sur = np.where(renouv, idx, 0)
            if renouv.any() and idx_sur[renouv].max() >= len(mots):
                raise ValueError("flux trop court")
            nouveau = np.where(renouv, (y << np.uint64(16)) | mots[idx_sur], y)
            x[actif] = nouveau
            p[actif] = pa + renouv.sum(axis=1)
            sortie[ma, :, k] = s.astype(np.uint8)
    voies_sur_L = bool((x == np.uint64(L)).all())
    return sortie.reshape(-1)[:P].tobytes(), voies_sur_L


def classes_echelle(delta: np.ndarray) -> np.ndarray:
    return np.where(delta < 128, 0, np.where(delta == 128, 1, 2)).astype(np.int64)


def decoder_partie(trc: Trc, entree, tables, R, C, casser=None):
    """Décode une partie de niveau 0 v1.0/v1.2 : rend les blocs [e, qs] des trois matrices (ordre β),
    les biais, et les contrôles de structure. `casser` : (« mot », j) ou (« biais », j) pour les cassures."""
    b = bytearray(trc.partie(entree))
    magie, couche, expert, niveau, nmat, nflux, utiles = struct.unpack_from("<IHHBBHI", b, 0)
    ctrl = {"magie": magie == 0x30435254, "couche_expert": (couche, expert) == (entree["couche"], entree["expert"]),
            "niveau0": niveau == 0, "n_matrices": nmat == 3, "n_flux": nflux == 12, "utiles": utiles == entree["u0"],
            "reserve_zero": all(v == 0 for v in b[16:64])}
    flux = {}
    for i in range(nflux):
        sorte, mat, ctxf, res, off, lg, prod = struct.unpack_from("<BBBBIII", b, 64 + 16 * i)
        flux[(sorte, mat)] = (off, lg, prod, ctxf)
    B = C // 32
    blocs_tous, biais_tous = [], []
    voies_L = True
    for j in range(3):
        o, lg, prod, _ = flux[(1, j)]
        med = np.frombuffer(bytes(b[o:o + lg]), dtype=np.uint8).astype(np.int64)
        assert lg == R and prod == R
        o, lg, prod, _ = flux[(2, j)]
        if casser == ("biais", j):
            b[o] ^= 0x01                                     # un bit du premier biais
        biais = bytes(b[o:o + lg])
        assert lg == 4 * R and prod == 4 * R
        # DELTA
        o, lg, prod, _ = flux[(3, j)]
        fd = lire_flux(bytes(b[o:o + lg]))
        tc, fq = tables[(entree["couche"], j, 3, 0)]
        dlt, okd = decoder_flux(fd, [Table(fq)])
        delta = np.frombuffer(dlt, dtype=np.uint8)[:R * B].astype(np.int64)
        assert prod == R * B
        e = (np.repeat(med, B) + delta - 128) % 256
        kappa = classes_echelle(delta)
        # CODES_CTX : contexte par voie, κ du bloc ⌊w/4⌋
        o, lg, prod, _ = flux[(4, j)]
        bc = bytearray(b[o:o + lg])
        fc = lire_flux(bytes(bc))
        if casser == ("mot", j):
            fc["mots"] = fc["mots"].copy()
            fc["mots"][len(fc["mots"]) // 2] ^= np.uint64(0x0101)
        tabs = [Table(tables[(entree["couche"], j, 4, c)][1]) for c in range(3)]
        nb = R * B

        def ctx_mot(w, kappa=kappa, nb=nb):
            blk = w // 4
            return kappa[np.minimum(blk, nb - 1)]
        qs, okc = decoder_flux(fc, tabs, ctx_mot)
        assert prod == R * B * 16
        qs = np.frombuffer(qs, dtype=np.uint8)[:R * B * 16].reshape(R * B, 16)
        blocs = np.concatenate([e.astype(np.uint8)[:, None], qs], axis=1)
        blocs_tous.append(blocs.tobytes())
        biais_tous.append(biais)
        voies_L = voies_L and okd and okc
    return blocs_tous, biais_tous, ctrl, voies_L, bytes(b)


# ============================================================================ commandes

def tirage():
    rng = np.random.Generator(np.random.PCG64(GRAINE))
    t20 = sorted(int(i) for i in rng.choice(768, 32, replace=False))
    t120 = rng.choice(4608, 64, replace=False)
    t120_ordre = [int(i) for i in t120]                     # ordre du tirage (les 8 premiers : témoin v1.0)
    d = {"graine": GRAINE, "generateur": "numpy.random.Generator(PCG64(20261022)) ; choice(768, 32) puis choice(4608, 64), sans remise",
         "numpy": np.__version__,
         "20b": [[i // 32, i % 32] for i in t20],
         "120b_ordre_du_tirage": [[i // 128, i % 128] for i in t120_ordre],
         "120b_temoin_v10": [[i // 128, i % 128] for i in t120_ordre[:8]]}
    sortie = JOURNAUX / "tirage-experts.json"
    if sortie.exists():
        ancien = json.loads(sortie.read_text(encoding="utf-8"))
        assert ancien["20b"] == d["20b"] and ancien["120b_ordre_du_tirage"] == d["120b_ordre_du_tirage"], "tirage différent du tirage écrit"
        print("tirage déjà écrit, redonné à l'identique")
        return d
    sortie.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(d, ensure_ascii=False))
    return d


def poids_experts(t: Trc):
    return t.L * t.E * sum(t.lignes[j] * t.colonnes[j] for j in range(t.n_mat))


def fichiers():
    res = {"outil": "decodeur_juge.py fichiers", "date": time.strftime("%Y-%m-%d %H:%M:%S"), "fichiers": {}}
    for (mod, ver), ch in TRC.items():
        t0 = time.time()
        t = Trc(ch)
        fautes = []
        r = {"chemin": str(ch).replace("\\", "/"), "taille_disque": t.taille_disque, "taille_declaree": t.taille_declaree,
             "version": f"{t.v_maj}.{t.v_min}", "drapeaux": t.drapeaux, "L": t.L, "E": t.E, "k": t.k,
             "taille_gguf_declaree": t.taille_gguf, "taille_gguf_disque": GGUF[mod].stat().st_size}
        if t.magie != b"TRONCONS": fautes.append("magie")
        if t.v_maj != 1: fautes.append("version majeure")
        if ver == "v12" and not (t.v_min == 2 and t.drapeaux == 1 | 8): fautes.append("v1.2 : version ou drapeaux")
        if ver == "v10" and not (t.v_min == 0 and t.drapeaux == 1): fautes.append("v1.0 : version ou drapeaux")
        if t.alignement != 4096 or t.taille_entete != 4096: fautes.append("alignement ou taille d'en-tête")
        if t.taille_declaree != t.taille_disque: fautes.append("taille déclarée ≠ taille sur le disque")
        if r["taille_gguf_declaree"] != r["taille_gguf_disque"]: fautes.append("taille du GGUF")
        if t.empreinte_entete != empreinte64(t.entete[:4088]): fautes.append("empreinte de l'en-tête")
        if not t.reserve_zero: fautes.append("réservé non nul")
        if t.type_ggml != 39 or t.niveaux != 1 or t.reserve123 != 0: fautes.append("type, niveaux ou octet 123")
        for i, (d, n) in enumerate(t.sections):
            if i < 5 and (d % 4096 != 0 or n == 0): fautes.append(f"section {i}")
            if i >= 5 and (d, n) != (0, 0): fautes.append(f"section réservée {i}")
        meta = t.controler_meta()
        r["meta"] = meta
        if not (meta["empreinte_tient"] and meta["zeros_apres"]): fautes.append("MÉTA")
        resid = t.controler_residents()
        r["residents"] = resid
        if not resid["empreinte_table_tient"]: fautes.append("RÉSIDENTS")
        tables, emp_tables, n_tab = t.tables()
        r["tables"] = {"enregistrements": n_tab, "empreinte_tient": emp_tables}
        if not emp_tables: fautes.append("TABLES")
        n_ctx_8 = sum(1 for (c, m, s, x), (tc, v) in tables.items() if s == 4 and int(v[OCTETS_AVEC_8].sum()) > 0)
        n_ctx = sum(1 for (c, m, s, x) in tables if s == 4)
        r["tables"]["codes_ctx"] = n_ctx
        r["tables"]["codes_ctx_avec_fente_pour_un_8"] = n_ctx_8
        sommes = all(int(v.sum()) == M for (tc, v) in tables.values() if tc in (1, 2))
        r["tables"]["sommes_4096"] = sommes
        if not sommes: fautes.append("somme des fréquences")
        if ver == "v12" and n_ctx_8 != 0: fautes.append("v1.2 : une table CODES_CTX donne une fente à un 8")
        rep, emp_rep = t.repertoire()
        if not emp_rep: fautes.append("empreinte du RÉPERTOIRE")
        d4, n4 = t.sections[4]
        prec = d4
        f_rep = 0
        for i, e in enumerate(rep):
            ok = (e["decalage"] % 4096 == 0 and e["decalage"] >= prec and e["l0"] % 4096 == 0 and e["l1"] == 0 and e["u1"] == 0
                  and e["u0"] <= e["l0"] and (e["couche"], e["expert"]) == (i // t.E, i % t.E) and e["reserve"] == 0
                  and e["decalage"] + e["l0"] <= d4 + n4)
            ok = ok and ((e["e_canonique"] != 0) if ver == "v12" else (e["e_canonique"] == 0))
            if not ok:
                f_rep += 1
            prec = e["decalage"] + e["l0"]
        if f_rep: fautes.append(f"répertoire : {f_rep} entrées fautives")
        nw = poids_experts(t)
        s_l0 = sum(e["l0"] for e in rep)
        s_u0 = sum(e["u0"] for e in rep)
        r["poids_experts"] = nw
        r["somme_parties_alignees"] = s_l0
        r["somme_octets_utiles"] = s_u0
        r["bits_par_poids_alignes"] = 8 * s_l0 / nw
        r["bits_par_poids_utiles"] = 8 * s_u0 / nw
        r["plus_grand_troncon"] = max(e["l0"] for e in rep)
        r["section_troncons"] = [d4, n4]
        r["fautes"] = fautes
        r["secondes"] = time.time() - t0
        res["fichiers"][f"{mod}-{ver}"] = r
        print(f"{mod}-{ver} : {len(fautes)} faute(s) {fautes} ; fichier {t.taille_disque} ; parties {s_l0} ; utiles {s_u0} ; "
              f"CODES_CTX avec fente pour un 8 : {n_ctx_8}/{n_ctx}", flush=True)
    for mod in ("20b", "120b"):
        a, b = res["fichiers"][f"{mod}-v10"], res["fichiers"][f"{mod}-v12"]
        res[f"gain_{mod}"] = {"bits_alignes": a["bits_par_poids_alignes"] - b["bits_par_poids_alignes"],
                              "bits_utiles": a["bits_par_poids_utiles"] - b["bits_par_poids_utiles"],
                              "octets_fichier": a["taille_disque"] - b["taille_disque"],
                              "octets_parties": a["somme_parties_alignees"] - b["somme_parties_alignees"],
                              "rapport_parties": b["somme_parties_alignees"] / a["somme_parties_alignees"],
                              "A_C2_tient": (a["bits_par_poids_alignes"] - b["bits_par_poids_alignes"]) >= 0.12}
    (JOURNAUX / "J-T0-fichiers.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def controler_expert(trc: Trc, gg: Gguf, rep, tables, couche, x, version, canon_gguf=True, casser=None):
    t = trc
    R, C = t.lignes[0], t.colonnes[0]
    assert all(t.lignes[j] == R and t.colonnes[j] == C for j in range(3))
    e = rep[couche * t.E + x]
    blocs_d, biais_d, ctrl, voies_L, partie = decoder_partie(t, e, tables, R, C, casser=casser)
    blocs_g, biais_g = gg.expert(couche, x, R, C)
    r = {"couche": couche, "expert": x, "version": version}
    r["structure"] = all(ctrl.values())
    r["voies_sur_L"] = voies_L
    dec = b"".join(blocs_d)
    brut = b"".join(blocs_g)
    can = b"".join(canoniser_qs(bg, actif=canon_gguf) for bg in blocs_g)
    bd = b"".join(biais_d)
    bgg = b"".join(biais_g)
    a_dec = np.frombuffer(dec, dtype=np.uint8).reshape(-1, 17)
    a_brut = np.frombuffer(brut, dtype=np.uint8).reshape(-1, 17)
    n_dec = demi_octets(a_dec[:, 1:])
    n_brut = demi_octets(a_brut[:, 1:])
    r["demi_octets"] = int(n_brut.size)
    r["moins_zero_gguf"] = int((n_brut == 8).sum())
    r["huit_dans_le_decode"] = int((n_dec == 8).sum())
    r["echelles_egales"] = bool((a_dec[:, 0] == a_brut[:, 0]).all())
    if version == "v12":
        r["octets_egaux_au_canonise"] = dec == can
        r["n_octets_differents_canonise"] = int((np.frombuffer(dec, np.uint8) != np.frombuffer(can, np.uint8)).sum())
        r["valeurs_egales"] = bool((E2M1[n_dec] == E2M1[n_brut]).all())
        r["empreinte_canonique"] = empreinte64(dec + bd) == e["e_canonique"]
        r["empreinte_canonique_du_gguf_canonise"] = empreinte64(can + bgg) == e["e_canonique"]
    else:
        r["octets_egaux_au_gguf"] = dec == brut
        r["n_octets_differents_gguf"] = int((np.frombuffer(dec, np.uint8) != np.frombuffer(brut, np.uint8)).sum())
        r["empreinte_origine_du_decode"] = empreinte64(dec + bd) == e["e_origine"]
    r["biais_egaux"] = bd == bgg
    r["empreinte_origine_du_gguf"] = empreinte64(brut + bgg) == e["e_origine"]
    r["empreinte_partie"] = empreinte64(partie[:e["u0"]]) == e["e_u0"]
    cles = [k for k, v in r.items() if isinstance(v, bool)]
    if version == "v12":
        cles_seuil = ["structure", "voies_sur_L", "octets_egaux_au_canonise", "biais_egaux", "valeurs_egales",
                      "empreinte_canonique", "empreinte_origine_du_gguf", "empreinte_partie"]
        ok = all(r[k] for k in cles_seuil) and r["huit_dans_le_decode"] == 0
    else:
        cles_seuil = ["structure", "voies_sur_L", "octets_egaux_au_gguf", "biais_egaux", "empreinte_origine_du_decode",
                      "empreinte_origine_du_gguf", "empreinte_partie"]
        ok = all(r[k] for k in cles_seuil)
    r["tient"] = ok
    r["controles_tombes"] = [k for k in cles if not r[k]] + (["huit"] if version == "v12" and r["huit_dans_le_decode"] else [])
    return r, n_dec


def echantillon(n20=32, n120=64):
    tir = json.loads((JOURNAUX / "tirage-experts.json").read_text(encoding="utf-8"))
    res = {"outil": "decodeur_juge.py echantillon", "debut": time.strftime("%Y-%m-%d %H:%M:%S"), "tirage": "tirage-experts.json",
           "experts": [], "temoin_v10": [], "cassures": []}
    lignes_csv = ["modele,version,couche,expert,tient,voies_sur_L,demi_octets,moins_zero_gguf,huit_dans_le_decode,secondes,controles_tombes"]
    for mod, liste, temoin in (("20b", tir["20b"][:n20], tir["20b"][:n20]), ("120b", tir["120b_ordre_du_tirage"][:n120], tir["120b_temoin_v10"])):
        gg = Gguf(GGUF[mod])
        t12 = Trc(TRC[(mod, "v12")])
        t10 = Trc(TRC[(mod, "v10")])
        tab12, _, _ = t12.tables()
        tab10, _, _ = t10.tables()
        rep12, _ = t12.repertoire()
        rep10, _ = t10.repertoire()
        dec12 = {}
        for couche, x in liste:
            t0 = time.time()
            r, nd = controler_expert(t12, gg, rep12, tab12, couche, x, "v12")
            r["secondes"] = time.time() - t0
            r["modele"] = mod
            dec12[(couche, x)] = nd
            res["experts"].append(r)
            lignes_csv.append(f"{mod},v12,{couche},{x},{int(r['tient'])},{int(r['voies_sur_L'])},{r['demi_octets']},{r['moins_zero_gguf']},"
                              f"{r['huit_dans_le_decode']},{r['secondes']:.2f},{'|'.join(r['controles_tombes'])}")
            print(f"{mod} v1.2 L{couche} E{x} : {'tient' if r['tient'] else 'TOMBE ' + str(r['controles_tombes'])} ({r['secondes']:.1f} s)", flush=True)
        for couche, x in temoin:
            t0 = time.time()
            r, nd10 = controler_expert(t10, gg, rep10, tab10, couche, x, "v10")
            r["secondes"] = time.time() - t0
            r["modele"] = mod
            n12 = dec12[(couche, x)]
            r["demi_octets_changes_v10_v12"] = int((nd10 != n12).sum())
            r["changes_egal_moins_zero"] = r["demi_octets_changes_v10_v12"] == r["moins_zero_gguf"] and bool(((nd10 != n12) == (nd10 == 8)).all())
            r["tient"] = r["tient"] and r["changes_egal_moins_zero"]
            res["temoin_v10"].append(r)
            lignes_csv.append(f"{mod},v10,{couche},{x},{int(r['tient'])},{int(r['voies_sur_L'])},{r['demi_octets']},{r['moins_zero_gguf']},"
                              f"{r['huit_dans_le_decode']},{r['secondes']:.2f},{'|'.join(r['controles_tombes'])}")
            print(f"{mod} v1.0 (témoin) L{couche} E{x} : {'tient' if r['tient'] else 'TOMBE ' + str(r['controles_tombes'])} ; "
                  f"changés v1.0→v1.2 {r['demi_octets_changes_v10_v12']} = −0 du GGUF {r['moins_zero_gguf']}", flush=True)
        if mod == "20b":
            couche, x = liste[0]
            for nom, kw in (("mot de CODES_CTX changé (matrice 1)", {"casser": ("mot", 1)}),
                            ("canonisation retirée du lecteur du GGUF", {"canon_gguf": False}),
                            ("un bit du biais (matrice 2)", {"casser": ("biais", 2)})):
                try:
                    r, _ = controler_expert(t12, gg, rep12, tab12, couche, x, "v12", **kw)
                    tombe = not r["tient"]
                    detail = r["controles_tombes"]
                except Exception as ex:          # un flux faussé peut lever (flux trop court) : l'instrument tombe aussi
                    tombe, detail = True, [f"exception : {ex}"]
                res["cassures"].append({"cassure": nom, "expert": [couche, x], "instrument_tombe": tombe, "controles_tombes": detail})
                print(f"cassure « {nom} » : {'tombe' if tombe else 'NE TOMBE PAS'} {detail}", flush=True)
    ex = res["experts"]
    res["bilan"] = {"experts_v12": len(ex), "tiennent": sum(r["tient"] for r in ex),
                    "temoins_v10": len(res["temoin_v10"]), "temoins_tiennent": sum(r["tient"] for r in res["temoin_v10"]),
                    "cassures_tombent": sum(c["instrument_tombe"] for c in res["cassures"]), "cassures": len(res["cassures"])}
    for mod in ("20b", "120b"):
        e = [r for r in ex if r["modele"] == mod]
        parts = np.array([r["moins_zero_gguf"] / r["demi_octets"] for r in e])
        res["bilan"][f"part_moins_zero_{mod}"] = {"moyenne": float(parts.mean()), "ecart_type_moyenne": float(parts.std(ddof=1) / np.sqrt(len(parts))),
                                                   "n": len(parts)}
    res["fin"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (JOURNAUX / "J-T1-echantillon.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    (JOURNAUX / "J-T1-echantillon.csv").write_text("\n".join(lignes_csv) + "\n", encoding="utf-8")
    print(json.dumps(res["bilan"], ensure_ascii=False))
    return res


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "tirage":
        tirage()
    elif cmd == "fichiers":
        fichiers()
    elif cmd == "echantillon":
        a = sys.argv[2:]
        n20 = int(a[a.index("--n20") + 1]) if "--n20" in a else 32
        n120 = int(a[a.index("--n120") + 1]) if "--n120" in a else 64
        echantillon(n20, n120)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
