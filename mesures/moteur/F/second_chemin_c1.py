"""Second chemin de C1 (lot F), sur le fichier .trc et son GGUF source.

Écrit depuis le seul § 4 de decisions/ARCHITECTURE.md et la spécification GGUF v3, sans lire
trc-format, trc-codec ni le lecteur GGUF du codeur : aucune ligne commune avec le premier chemin
(`trc-codeur verifier`). Bibliothèque standard seule ; SHA-256 par hashlib (OpenSSL), pas par sha2.

Ce qu'il vérifie (seuils : 00-seuils-declares.md, ajout de 20 h 50) :
  1. le GGUF lu par un lecteur Python, puis une troisième fois par celui de llama.cpp
     (gguf_init_from_file de ggml-base.dll), pavage de la zone de données ;
  2. la SHA-256 du GGUF entier (lecture sans tampon) contre telechargements.json et l'en-tête ;
  3. l'en-tête, MÉTA, TABLES, RÉPERTOIRE et RÉSIDENTS du .trc, champ par champ ;
  4. pour chaque expert : l'empreinte64 de l'expert d'origine refaite depuis le GGUF (§ 4.11)
     contre le répertoire ; les flux bruts BIAIS_j octet pour octet contre le GGUF ; les flux
     MEDIANES_j contre les médianes refaites ; l'empreinte64 de la partie ; sa structure.

Il ne décode pas le rANS : c'est l'épreuve du § 8, réservée à un juge.

Usage :
  python -I -X utf8 second_chemin_c1.py <source.gguf> <fichier.trc> <journal.json>
      [--sha256-attendue HEX] [--fils 4] [--couches a-b] [--sans-sha] [--sans-residents]
      [--casser-expert C,X] [--casser-mediane C,X] [--casser-biais C,X]
      [--casser-parseur] [--casser-sha] [--casser-decalage]
Code de sortie : 0 si tout est égal, 1 sinon.
"""
import argparse
import concurrent.futures as cf
import ctypes
import ctypes.wintypes as wt
import datetime
import hashlib
import json
import os
import struct
import subprocess
import sys
import threading
import time

# ---------------------------------------------------------------------------------------------
# Lecture sans tampon (FILE_FLAG_NO_BUFFERING) : décalage, longueur et adresse multiples de 4 096.
# Chaque fil ouvre son propre descripteur et garde son propre tampon aligné.
# ---------------------------------------------------------------------------------------------
SECTEUR = 4096
_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
_k32.CreateFileW.restype = wt.HANDLE
_k32.ReadFile.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
_k32.ReadFile.restype = wt.BOOL
_k32.SetFilePointerEx.argtypes = [wt.HANDLE, ctypes.c_longlong, ctypes.POINTER(ctypes.c_longlong), wt.DWORD]
_k32.SetFilePointerEx.restype = wt.BOOL
_k32.CloseHandle.argtypes = [wt.HANDLE]
INVALIDE = ctypes.c_void_p(-1).value


class LecteurSansTampon:
    def __init__(self, chemin):
        h = _k32.CreateFileW(chemin, 0x80000000, 1 | 2 | 4, None, 3, 0x20000000, None)
        if h is None or h == INVALIDE:
            raise OSError(ctypes.get_last_error(), f"CreateFileW {chemin}")
        self.h, self.cap, self.adr = h, 0, None
        self.taille = os.path.getsize(chemin)

    def _tampon(self, n):
        # Un bytearray de Python, dont on prend la première adresse multiple de 4 096 : la vue
        # rendue est alors un memoryview natif d'octets, sans copie.
        if n > self.cap:
            self.cap = (n + (1 << 20) - 1) // (1 << 20) * (1 << 20)
            self.ba = bytearray(self.cap + SECTEUR)
            base = ctypes.addressof((ctypes.c_char * len(self.ba)).from_buffer(self.ba))
            self.off = (-base) % SECTEUR
            self.adr = base + self.off

    def lire(self, dec, n):
        """Rend un memoryview des octets [dec, dec + n) du fichier (valide jusqu'à la lecture suivante)."""
        a0 = dec // SECTEUR * SECTEUR
        a1 = (dec + n + SECTEUR - 1) // SECTEUR * SECTEUR
        self._tampon(a1 - a0)
        if not _k32.SetFilePointerEx(self.h, a0, None, 0):
            raise OSError(ctypes.get_last_error(), "SetFilePointerEx")
        fait, lu = 0, wt.DWORD()
        while fait < a1 - a0:
            m = min(a1 - a0 - fait, 64 << 20)
            if not _k32.ReadFile(self.h, self.adr + fait, m, ctypes.byref(lu), None):
                raise OSError(ctypes.get_last_error(), f"ReadFile à {a0 + fait}")
            fait += lu.value
            if lu.value < m:
                break  # fin du fichier
        if a0 + fait < dec + n:
            raise EOFError(f"lecture courte : {dec}+{n}, fichier de {self.taille}")
        return memoryview(self.ba)[self.off + dec - a0: self.off + dec - a0 + n]

    def fermer(self):
        _k32.CloseHandle(self.h)


def empreinte64(*morceaux):
    """§ 4.12 : les 8 premiers octets de SHA-256, lus comme un u64 petit-boutiste."""
    h = hashlib.sha256()
    for m in morceaux:
        h.update(m)
    return int.from_bytes(h.digest()[:8], "little")


# ---------------------------------------------------------------------------------------------
# Lecteur GGUF v3 (spécification de ggml/docs/gguf.md), sur les octets de tête du fichier.
# ---------------------------------------------------------------------------------------------
# type ggml → (poids par bloc, octets par bloc) ; un type absent d'ici est refusé.
TYPES_GGML = {0: (1, 4), 1: (1, 2), 2: (32, 18), 3: (32, 20), 6: (32, 22), 7: (32, 24),
              8: (32, 34), 9: (32, 36), 10: (256, 84), 11: (256, 110), 12: (256, 144),
              13: (256, 176), 14: (256, 210), 15: (256, 292), 30: (1, 2), 39: (32, 17)}
TAILLE_SCALAIRE = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
FMT_SCALAIRE = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<B",
                10: "<Q", 11: "<q", 12: "<d"}


class Curseur:
    def __init__(self, b, p=0):
        self.b, self.p = b, p

    def u(self, fmt):
        v = struct.unpack_from(fmt, self.b, self.p)[0]
        self.p += struct.calcsize(fmt)
        return v

    def chaine(self):
        n = self.u("<Q")
        s = bytes(self.b[self.p:self.p + n])
        if len(s) != n:
            raise EOFError
        self.p += n
        return s.decode("utf-8")

    def valeur(self, t):
        if t in TAILLE_SCALAIRE:
            return self.u(FMT_SCALAIRE[t])
        if t == 8:
            return self.chaine()
        if t == 9:
            te, n = self.u("<I"), self.u("<Q")
            if te in TAILLE_SCALAIRE:  # tableau de scalaires : sauté d'un bloc
                if self.p + n * TAILLE_SCALAIRE[te] > len(self.b):
                    raise EOFError
                self.p += n * TAILLE_SCALAIRE[te]
                return ("tableau", te, n)
            for _ in range(n):
                self.valeur(te)
            return ("tableau", te, n)
        raise ValueError(f"type GGUF inconnu {t}")


def paires_gguf(b, p, n):
    """Lit n paires depuis p ; rend (dict clé → (type, valeur), liste des clés, position de fin)."""
    c = Curseur(b, p)
    d, cles = {}, []
    for _ in range(n):
        k = c.chaine()
        t = c.u("<I")
        d[k] = (t, c.valeur(t))
        cles.append(k)
    return d, cles, c.p


def lire_gguf(chemin):
    taille = os.path.getsize(chemin)
    n_tete = 1 << 24
    while True:
        with open(chemin, "rb") as f:
            b = f.read(n_tete)
        try:
            c = Curseur(b, 4)
            if b[:4] != b"GGUF":
                raise ValueError("magie GGUF")
            version = c.u("<I")
            n_t, n_kv = c.u("<Q"), c.u("<Q")
            kv_debut = c.p
            kv, cles, c.p = paires_gguf(b, c.p, n_kv)
            kv_fin = c.p
            tenseurs = []
            for _ in range(n_t):
                nom = c.chaine()
                nd = c.u("<I")
                ne = [c.u("<Q") for _ in range(nd)]
                t = c.u("<I")
                dec = c.u("<Q")
                tenseurs.append({"nom": nom, "n_dims": nd, "ne": ne, "type": t, "decalage": dec})
            fin_infos = c.p
            break
        except (EOFError, struct.error):
            # Métadonnées plus longues que la tête lue : on relit plus grand, jamais plus de
            # 256 Mio (le vocabulaire de gpt-oss en fait 13) : au-delà, le fichier est faux.
            if n_tete >= min(taille, 1 << 28):
                raise
            n_tete *= 4
    align = kv.get("general.alignment", (4, 32))[1]
    debut = (fin_infos + align - 1) // align * align
    for t in tenseurs:
        if t["type"] not in TYPES_GGML:
            raise ValueError(f"type ggml {t['type']} non pris en charge ({t['nom']})")
        ppb, opb = TYPES_GGML[t["type"]]
        n = 1
        for x in t["ne"]:
            n *= x
        if n % ppb:
            raise ValueError(f"{t['nom']} : {n} poids, pas un multiple de {ppb}")
        t["octets"] = n // ppb * opb
    return {"chemin": chemin, "taille": taille, "version": version, "n_tenseurs": n_t, "n_kv": n_kv,
            "kv": kv, "cles": cles, "kv_octets": bytes(b[kv_debut:kv_fin]), "alignement": align,
            "debut_donnees": debut, "tenseurs": tenseurs, "par_nom": {t["nom"]: t for t in tenseurs}}


def pavage(g):
    """Les tenseurs, triés par décalage, se suivent au bourrage près ; le dernier finit au bout."""
    ecarts = []
    ts = sorted(g["tenseurs"], key=lambda t: t["decalage"])
    pos = 0
    for t in ts:
        attendu = (pos + g["alignement"] - 1) // g["alignement"] * g["alignement"]
        if t["decalage"] != attendu:
            ecarts.append({"tenseur": t["nom"], "decalage": t["decalage"], "attendu": attendu})
        pos = t["decalage"] + t["octets"]
    if g["debut_donnees"] + pos != g["taille"]:
        ecarts.append({"fin_des_donnees": g["debut_donnees"] + pos, "taille_fichier": g["taille"]})
    return ecarts


def croiser_llama(g, dll, casser):
    """Troisième lecture des métadonnées : le lecteur de llama.cpp (gguf.cpp, ggml-base.dll)."""
    d = ctypes.CDLL(dll)

    class Params(ctypes.Structure):
        _fields_ = [("no_alloc", ctypes.c_bool), ("ctx", ctypes.c_void_p)]

    d.gguf_init_from_file.argtypes = [ctypes.c_char_p, Params]
    d.gguf_init_from_file.restype = ctypes.c_void_p
    for n, r in [("gguf_get_n_tensors", ctypes.c_int64), ("gguf_get_n_kv", ctypes.c_int64),
                 ("gguf_get_data_offset", ctypes.c_size_t), ("gguf_get_alignment", ctypes.c_size_t),
                 ("gguf_get_version", ctypes.c_uint32)]:
        getattr(d, n).argtypes = [ctypes.c_void_p]
        getattr(d, n).restype = r
    for n, r in [("gguf_get_tensor_name", ctypes.c_char_p), ("gguf_get_tensor_offset", ctypes.c_size_t),
                 ("gguf_get_tensor_type", ctypes.c_int), ("gguf_get_tensor_size", ctypes.c_size_t)]:
        getattr(d, n).argtypes = [ctypes.c_void_p, ctypes.c_int64]
        getattr(d, n).restype = r
    d.gguf_free.argtypes = [ctypes.c_void_p]
    ctx = d.gguf_init_from_file(g["chemin"].encode("mbcs"), Params(True, None))
    if not ctx:
        raise RuntimeError("gguf_init_from_file a échoué")
    ecarts = []
    try:
        def cmp(champ, a, b):
            if a != b:
                ecarts.append({"champ": champ, "python": a, "llama.cpp": b})
        cmp("version", g["version"], d.gguf_get_version(ctx))
        cmp("n_tenseurs", g["n_tenseurs"], d.gguf_get_n_tensors(ctx))
        cmp("n_kv", g["n_kv"], d.gguf_get_n_kv(ctx))
        cmp("alignement", g["alignement"], d.gguf_get_alignment(ctx))
        cmp("debut_donnees", g["debut_donnees"], d.gguf_get_data_offset(ctx))
        for i, t in enumerate(g["tenseurs"]):
            dec = t["decalage"] + (g["alignement"] if casser and i == 0 else 0)
            nom = d.gguf_get_tensor_name(ctx, i).decode("utf-8")
            ll = [nom, d.gguf_get_tensor_type(ctx, i), d.gguf_get_tensor_offset(ctx, i), d.gguf_get_tensor_size(ctx, i)]
            py = [t["nom"], t["type"], dec, t["octets"]]
            if py != ll:
                ecarts.append({"tenseur": i, "python": py, "llama.cpp": ll})
    finally:
        d.gguf_free(ctx)
    return ecarts


def sha256_entiere(chemin, casser):
    lec = LecteurSansTampon(chemin)
    h, pos, morceau = hashlib.sha256(), 0, 64 << 20
    try:
        while pos < lec.taille:
            n = min(morceau, lec.taille - pos)
            v = lec.lire(pos, n)
            if casser and pos == 0:
                b = bytearray(v)
                b[0] ^= 1
                h.update(b)
            else:
                h.update(v)
            pos += n
    finally:
        lec.fermer()
    return h.hexdigest()


# ---------------------------------------------------------------------------------------------
# Le fichier .trc, lu par le seul § 4.
# ---------------------------------------------------------------------------------------------
def lire_trc_tete(chemin, g, ecarts):
    def e(champ, obtenu, attendu):
        if obtenu != attendu:
            ecarts.append({"champ": champ, "obtenu": obtenu, "attendu": attendu})

    with open(chemin, "rb") as f:
        h = f.read(4096)
    U = lambda fmt, o: struct.unpack_from(fmt, h, o)[0]
    t = {"magie": h[:8], "version": (U("<H", 8), U("<H", 10)), "drapeaux": U("<I", 12),
         "alignement": U("<I", 16), "taille_entete": U("<I", 20), "taille_fichier": U("<Q", 24),
         "sha256": h[32:64].hex(), "taille_source": U("<Q", 64), "L": U("<H", 72), "E": U("<H", 74),
         "k": U("<H", 76), "matrices": U("<H", 78), "lignes": list(struct.unpack_from("<4I", h, 80)),
         "colonnes": list(struct.unpack_from("<4I", h, 96)), "ppb": U("<I", 112), "opb": U("<I", 116),
         "type": h[120], "niveaux": h[121], "classes": h[122], "res123": h[123],
         "partition": list(h[124:132]), "res132": U("<I", 132),
         "sections": [struct.unpack_from("<QQ", h, 136 + 16 * i) for i in range(8)]}
    e("magie", t["magie"], b"TRONCONS")
    e("version", t["version"], (1, 0))
    e("drapeaux", t["drapeaux"], 1)
    e("alignement", t["alignement"], 4096)
    e("taille_entete", t["taille_entete"], 4096)
    e("taille_fichier", t["taille_fichier"], os.path.getsize(chemin))
    e("taille_source", t["taille_source"], g["taille"])
    kv = g["kv"]
    arch = kv["general.architecture"][1]
    e("L", t["L"], kv[f"{arch}.block_count"][1])
    e("E", t["E"], kv[f"{arch}.expert_count"][1])
    e("k", t["k"], kv[f"{arch}.expert_used_count"][1])
    e("matrices", t["matrices"], 3)
    dims = []
    for j, m in enumerate(("gate", "up", "down")):
        w = g["par_nom"][f"blk.0.ffn_{m}_exps.weight"]
        dims.append((w["ne"][1], w["ne"][0]))  # (R lignes, C colonnes) : ne[0] est la ligne
    e("lignes", t["lignes"], [r for r, _ in dims] + [0])
    e("colonnes", t["colonnes"], [c for _, c in dims] + [0])
    e("ppb", t["ppb"], 32)
    e("opb", t["opb"], 17)
    e("type", t["type"], 39)
    e("niveaux", t["niveaux"], 1)
    e("classes", t["classes"], 3)
    e("res123", t["res123"], 0)
    e("partition (v1.0)", t["partition"], [0] * 8)
    e("res132", t["res132"], 0)
    for i in range(5, 8):
        e(f"section {i}", t["sections"][i], (0, 0))
    for i in range(5):
        if t["sections"][i][0] % 4096:
            ecarts.append({"champ": f"section {i} non alignée", "obtenu": t["sections"][i][0]})
    for i in range(4):
        if t["sections"][i][0] + t["sections"][i][1] > t["sections"][i + 1][0]:
            ecarts.append({"champ": f"section {i} chevauche {i + 1}"})
    if t["sections"][4][0] + t["sections"][4][1] > t["taille_fichier"]:
        ecarts.append({"champ": "TRONÇONS au-delà du fichier"})
    e("réservé 264..4088 à zéro", any(h[264:4088]), False)
    e("empreinte de l'en-tête", U("<Q", 4088), empreinte64(h[:4088]))
    t["dims"] = dims
    return t


def lire_section(chemin, sec):
    with open(chemin, "rb") as f:
        f.seek(sec[0])
        return f.read(sec[1])


def verifier_meta(chemin, t, g, ecarts):
    b = lire_section(chemin, t["sections"][0])
    n = struct.unpack_from("<Q", b, 0)[0]
    if n != g["n_kv"] + 3:
        ecarts.append({"meta": "n_paires", "obtenu": n, "attendu": g["n_kv"] + 3})
    kv, cles, fin = paires_gguf(b, 8, n)
    if bytes(b[8:8 + len(g["kv_octets"])]) != g["kv_octets"]:
        ecarts.append({"meta": "paires du GGUF non identiques octet pour octet"})
    ajout = cles[g["n_kv"]:]
    if ajout != ["troncons.codeur.version", "troncons.codeur.date", "troncons.source.nom"] or \
            any(kv[k][0] != 8 for k in ajout):
        ecarts.append({"meta": "paires du codeur", "obtenu": ajout})
    if struct.unpack_from("<Q", b, fin)[0] != empreinte64(b[:fin]):
        ecarts.append({"meta": "empreinte64"})
    return {"n_paires": n, "ajout": {k: kv[k][1] for k in ajout}, "fin_utile": fin + 8,
            "longueur_section": t["sections"][0][1], "bourrage_a_zero": not any(b[fin + 8:])}


def verifier_tables(chemin, t, ecarts):
    b = lire_section(chemin, t["sections"][2])
    n = struct.unpack_from("<I", b, 0)[0]
    if struct.unpack_from("<I", b, 4)[0]:
        ecarts.append({"tables": "réservé"})
    p, vus = 8, set()
    taille_charge = {1: 32, 2: 512, 3: 16}
    for _ in range(n):
        couche, mat, sorte, ctx, tc, res = struct.unpack_from("<HBBBBH", b, p)
        ch = b[p + 8:p + 8 + taille_charge[tc]]
        if tc in (1, 2) and sum(struct.unpack(f"<{len(ch) // 2}H", ch)) != 4096:
            ecarts.append({"tables": "somme des fréquences", "enregistrement": (couche, mat, sorte, ctx)})
        if res:
            ecarts.append({"tables": "réservé d'enregistrement"})
        vus.add((couche, mat, sorte, ctx, tc))
        p += 8 + taille_charge[tc]
    attendus = {(c, j, 3, 0, 2) for c in range(t["L"]) for j in range(3)} | \
               {(c, j, 4, k, 2) for c in range(t["L"]) for j in range(3) for k in range(3)}
    if vus != attendus or n != len(attendus):
        ecarts.append({"tables": "ensemble des enregistrements", "n": n, "attendus": len(attendus)})
    if struct.unpack_from("<Q", b, p)[0] != empreinte64(b[:p]):
        ecarts.append({"tables": "empreinte64"})
    return {"n_enregistrements": n, "fin_utile": p + 8, "longueur_section": t["sections"][2][1]}


def lire_repertoire(chemin, t, ecarts):
    b = lire_section(chemin, t["sections"][3])
    n = t["L"] * t["E"]
    if struct.unpack_from("<Q", b, 64 * n)[0] != empreinte64(b[:64 * n]):
        ecarts.append({"repertoire": "empreinte64"})
    rep = []
    debut4, fin4 = t["sections"][4][0], t["sections"][4][0] + t["sections"][4][1]
    for i in range(n):
        dec, l0, l1, u0, u1, eo, e0, e1, c, x, r52, r56 = struct.unpack_from("<QIIIIQQQHHIQ", b, 64 * i)
        r = {"decalage": dec, "l0": l0, "u0": u0, "orig": eo, "e0": e0, "c": c, "x": x}
        def f(m):
            ecarts.append({"repertoire": m, "entree": i})
        if (c, x) != (i // t["E"], i % t["E"]):
            f("(couche, expert) hors de leur rang")
        if dec % 4096 or l0 % 4096 or not (0 < u0 <= l0):
            f("alignement ou longueurs")
        if (l1, u1, e1, r52, r56) != (0, 0, 0, 0, 0):
            f("niveau 1 ou réservés non nuls (v1.0)")
        if not (debut4 <= dec and dec + l0 <= fin4):
            f("tronçon hors de la section TRONÇONS")
        if rep and rep[-1]["decalage"] + rep[-1]["l0"] != dec:
            f("tronçons non contigus")
        rep.append(r)
    return rep


def verifier_residents(chemin_trc, t, g, ecarts, fils):
    with open(chemin_trc, "rb") as f:
        f.seek(t["sections"][1][0])
        tete = f.read(8)
        n = struct.unpack_from("<I", tete, 0)[0]
        f.seek(t["sections"][1][0])
        table = f.read(8 + 128 * n)
    zone = t["sections"][1][0] + (8 + 128 * n + 4095) // 4096 * 4096
    attendus = sorted(x["nom"] for x in g["tenseurs"] if not x["nom"].endswith(("_exps.weight", "_exps.bias")))
    entrees = []
    for i in range(n):
        o = 8 + 128 * i
        nom = table[o:o + 64].rstrip(b"\0").decode("utf-8")
        ty, nd = struct.unpack_from("<II", table, o + 64)
        ne = list(struct.unpack_from("<4Q", table, o + 72))
        dec, octets, emp = struct.unpack_from("<QQQ", table, o + 104)
        entrees.append((nom, ty, nd, ne, dec, octets, emp))
    if sorted(e[0] for e in entrees) != attendus:
        ecarts.append({"residents": "ensemble des noms", "n": n, "attendus": len(attendus)})
    fin_donnees = max(e[4] + e[5] for e in entrees)
    with open(chemin_trc, "rb") as f:
        f.seek(zone + fin_donnees)
        emp_table = struct.unpack("<Q", f.read(8))[0]
    if emp_table != empreinte64(table):
        ecarts.append({"residents": "empreinte64 de la table (après la zone de données)"})
    faux = []
    loc = threading.local()

    def un(e):
        nom, ty, nd, ne, dec, octets, emp = e
        if not hasattr(loc, "a"):
            loc.a, loc.b = LecteurSansTampon(chemin_trc), LecteurSansTampon(g["chemin"])
        gt = g["par_nom"].get(nom)
        if gt is None:
            return {"nom": nom, "pourquoi": "absent du GGUF"}
        if (ty, nd, ne, octets) != (gt["type"], gt["n_dims"], gt["ne"] + [1] * (4 - gt["n_dims"]), gt["octets"]) or dec % 256:
            return {"nom": nom, "pourquoi": "type, dimensions, octets ou alignement"}
        h, pos = hashlib.sha256(), 0
        egal = True
        while pos < octets:
            m = min(16 << 20, octets - pos)
            va = loc.a.lire(zone + dec + pos, m)
            vb = loc.b.lire(g["debut_donnees"] + gt["decalage"] + pos, m)
            if va != vb:
                egal = False
            h.update(vb)
            pos += m
        if not egal:
            return {"nom": nom, "pourquoi": "octets"}
        if int.from_bytes(h.digest()[:8], "little") != emp:
            return {"nom": nom, "pourquoi": "empreinte64"}
        return None

    with cf.ThreadPoolExecutor(fils) as ex:
        for r in ex.map(un, entrees):
            if r:
                faux.append(r)
    return {"n": n, "faux": faux, "position_empreinte_table": zone + fin_donnees - t["sections"][1][0],
            "longueur_section": t["sections"][1][1]}


# ---------------------------------------------------------------------------------------------
# Les experts.
# ---------------------------------------------------------------------------------------------
SORTES_ATTENDUES = []  # (sorte, matrice, contexte fixe) dans l'ordre du § 4.8, v1.0, niveau 0
for _j in range(3):
    SORTES_ATTENDUES += [(0x01, _j, 0xFF), (0x02, _j, 0xFF), (0x03, _j, 0x00), (0x04, _j, 0xFF)]


def medianes(echelles, R, B):
    """§ 4.10 : tri[B/2] des B échelles de chaque ligne, tri croissant."""
    return bytes(sorted(echelles[r * B:(r + 1) * B])[B // 2] for r in range(R))


def verifier_expert(c, x, t, g, chemin_trc, rep, loc, opts):
    if not hasattr(loc, "g"):
        loc.g, loc.t = LecteurSansTampon(g["chemin"]), LecteurSansTampon(chemin_trc)
    E = t["E"]
    controles = {"empreinte_origine": True, "biais": True, "medianes": True,
                 "empreinte_partie": True, "structure": True}
    pourquoi = []
    # 1. L'expert d'origine depuis le GGUF (§ 4.11) : blocs des matrices 0, 1, 2 puis biais.
    blocs, biais = [], []
    for j, m in enumerate(("gate", "up", "down")):
        R, C = t["dims"][j]
        B = C // 32
        w = g["par_nom"][f"blk.{c}.ffn_{m}_exps.weight"]
        b = g["par_nom"][f"blk.{c}.ffn_{m}_exps.bias"]
        xs = (x + 1) % E if opts.casser_decalage else x
        n_w = R * B * 17
        vw = bytes(loc.g.lire(g["debut_donnees"] + w["decalage"] + xs * n_w, n_w))
        vb = bytes(loc.g.lire(g["debut_donnees"] + b["decalage"] + x * R * 4, R * 4))
        if opts.casser_expert == (c, x) and j == 0:
            vw = bytearray(vw); vw[1] ^= 1; vw = bytes(vw)
        if opts.casser_biais == (c, x) and j == 2:
            vb = bytearray(vb); vb[0] ^= 1; vb = bytes(vb)
        blocs.append(vw)
        biais.append(vb)
    e_orig = empreinte64(*blocs, *biais)
    ent = rep[c * E + x]
    if e_orig != ent["orig"]:
        controles["empreinte_origine"] = False
    # 2. La partie de niveau 0, lue en entier jusqu'à longueur0 (bourrage compris).
    p = bytes(loc.t.lire(ent["decalage"], ent["l0"]))
    u0 = ent["u0"]
    if empreinte64(p[:u0]) != ent["e0"]:
        controles["empreinte_partie"] = False
    magie, pc, px, niv, nmat, nflux, utiles = struct.unpack_from("<IHHBBHI", p, 0)
    if (magie, pc, px, niv, nmat, nflux, utiles) != (0x30435254, c, x, 0, 3, 12, u0) or any(p[16:64]):
        pourquoi.append("en-tête de partie")
    if any(p[u0:]):
        pourquoi.append("bourrage non nul après les octets utiles")
    flux, fin = [], 64 + 16 * nflux
    for i in range(min(nflux, 12)):
        so, ma, cx, rs, dec, lon, prod = struct.unpack_from("<BBBBIII", p, 64 + 16 * i)
        flux.append((so, ma, cx, dec, lon, prod))
        if (so, ma, cx) != SORTES_ATTENDUES[i] or rs or dec % 16 or dec < fin or dec + lon > u0:
            pourquoi.append(f"table des flux, entrée {i}")
        fin = dec + lon
    if fin != u0:
        pourquoi.append("octets utiles ≠ fin du dernier flux")
    for (so, ma, cx, dec, lon, prod) in flux:
        R, C = t["dims"][ma]
        B = C // 32
        f = p[dec:dec + lon]
        if so == 0x01:
            ok_l = (lon, prod) == (R, R)
            echelles = blocs[ma][0::17]
            med = bytearray(medianes(echelles, R, B))
            if opts.casser_mediane == (c, x) and ma == 0:
                med[0] ^= 1
            if f != med:
                controles["medianes"] = False
        elif so == 0x02:
            ok_l = (lon, prod) == (4 * R, 4 * R)
            if f != biais[ma]:
                controles["biais"] = False
        else:
            P_att = (R * B + 127) // 128 * 128 if so == 0x03 else R * B * 16
            P, N, geo, res, T, W = struct.unpack_from("<IHBBII", f, 0)
            T_att = ((P // 128) + N - 1) // N if N else -1
            lon_att = (16 + 4 * T + 128 * T + 2 * W + 15) // 16 * 16
            debuts = struct.unpack_from(f"<{T}I", f, 16) if T == T_att else ()
            ok_l = (prod, P, N, geo, res, T, lon) == (P_att, P_att, 256, 1, 0, T_att, lon_att) and \
                P % 128 == 0 and bool(debuts) and debuts[0] == 0 and \
                all(debuts[i] <= debuts[i + 1] for i in range(T - 1)) and debuts[-1] <= W and \
                not any(f[16 + 132 * T + 2 * W:])
        if not ok_l:
            pourquoi.append(f"flux sorte {so} matrice {ma}")
    if pourquoi:
        controles["structure"] = False
    return {"c": c, "x": x, "controles": controles, "pourquoi": pourquoi}


def alimentation():
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "(Get-CimInstance Win32_Battery).BatteryStatus"],
                           capture_output=True, text=True, timeout=60)
        return r.stdout.strip()
    except Exception as ex:  # l'instrument d'alimentation ne doit pas arrêter la vérification
        return f"inconnue ({ex})"


def couple(s):
    a, b = s.split(",")
    return (int(a), int(b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gguf"); ap.add_argument("trc"); ap.add_argument("journal")
    ap.add_argument("--sha256-attendue", default=None)
    ap.add_argument("--fils", type=int, default=4)
    ap.add_argument("--couches", default=None)
    ap.add_argument("--sans-sha", action="store_true")
    ap.add_argument("--sans-residents", action="store_true")
    ap.add_argument("--dll", default=r"~\dev\modeles\llama.cpp-b11515\ggml-base.dll")
    ap.add_argument("--casser-expert", type=couple, default=None)
    ap.add_argument("--casser-mediane", type=couple, default=None)
    ap.add_argument("--casser-biais", type=couple, default=None)
    ap.add_argument("--casser-parseur", action="store_true")
    ap.add_argument("--casser-sha", action="store_true")
    ap.add_argument("--casser-decalage", action="store_true")
    o = ap.parse_args()
    j = {"outil": "second_chemin_c1.py", "commande": sys.argv, "debut": datetime.datetime.now().isoformat(timespec="seconds"),
         "alimentation_debut": alimentation(), "python": sys.version.split()[0],
         "openssl": __import__("ssl").OPENSSL_VERSION, "lecture": "sans tampon (FILE_FLAG_NO_BUFFERING)"}
    duree = {}
    t0 = time.time()
    g = lire_gguf(o.gguf)
    j["gguf"] = {"taille": g["taille"], "version": g["version"], "n_tenseurs": g["n_tenseurs"], "n_kv": g["n_kv"],
                 "alignement": g["alignement"], "debut_donnees": g["debut_donnees"]}
    j["pavage_ecarts"] = pavage(g)
    j["llama_cpp_ecarts"] = croiser_llama(g, o.dll, o.casser_parseur)
    duree["metadonnees_s"] = round(time.time() - t0, 2)
    tete_ecarts = []
    t = lire_trc_tete(o.trc, g, tete_ecarts)
    j["entete"] = {"version": t["version"], "drapeaux": t["drapeaux"], "L": t["L"], "E": t["E"], "k": t["k"],
                   "dims": t["dims"], "sha256": t["sha256"], "sections": t["sections"][:5]}
    j["entete_ecarts"] = tete_ecarts
    if o.sha256_attendue and t["sha256"] != o.sha256_attendue:
        tete_ecarts.append({"champ": "sha256 de l'en-tête", "obtenu": t["sha256"], "attendu": o.sha256_attendue})
    if not o.sans_sha:
        t1 = time.time()
        s = sha256_entiere(o.gguf, o.casser_sha)
        duree["sha256_s"] = round(time.time() - t1, 2)
        j["sha256_gguf_hashlib"] = s
        j["sha256_egale_attendue"] = (s == o.sha256_attendue) if o.sha256_attendue else None
        j["sha256_egale_entete"] = s == t["sha256"]
    meta_ecarts, tab_ecarts, rep_ecarts = [], [], []
    j["meta"] = verifier_meta(o.trc, t, g, meta_ecarts); j["meta_ecarts"] = meta_ecarts
    j["tables"] = verifier_tables(o.trc, t, tab_ecarts); j["tables_ecarts"] = tab_ecarts
    rep = lire_repertoire(o.trc, t, rep_ecarts); j["repertoire_ecarts"] = rep_ecarts
    if not o.sans_residents:
        t1 = time.time()
        res_ecarts = []
        j["residents"] = verifier_residents(o.trc, t, g, res_ecarts, o.fils)
        j["residents_ecarts"] = res_ecarts
        duree["residents_s"] = round(time.time() - t1, 2)
    couches = range(t["L"])
    if o.couches:
        a, b = map(int, o.couches.split("-"))
        couches = range(a, b + 1)
    t1 = time.time()
    loc = threading.local()
    taches = [(c, x) for c in couches for x in range(t["E"])]
    faux, par_couche = [], {}
    with cf.ThreadPoolExecutor(o.fils) as ex:
        for r in ex.map(lambda cx: verifier_expert(cx[0], cx[1], t, g, o.trc, rep, loc, o), taches):
            pc = par_couche.setdefault(r["c"], {"experts": 0, **{k: 0 for k in r["controles"]}})
            pc["experts"] += 1
            for k, v in r["controles"].items():
                pc[k] += (not v)
            if not all(r["controles"].values()):
                faux.append(r)
    duree["experts_s"] = round(time.time() - t1, 2)
    j["experts_lus"] = len(taches)
    j["experts_faux"] = len(faux)
    j["controles_faux"] = {k: sum(pc[k] for pc in par_couche.values())
                           for k in ("empreinte_origine", "biais", "medianes", "empreinte_partie", "structure")}
    j["faux"] = faux[:50]
    j["par_couche"] = [{"couche": c, **par_couche[c]} for c in sorted(par_couche)]
    j["durees"] = duree
    j["fin"] = datetime.datetime.now().isoformat(timespec="seconds")
    j["alimentation_fin"] = alimentation()
    tout_juste = not (faux or j["pavage_ecarts"] or j["llama_cpp_ecarts"] or tete_ecarts or meta_ecarts
                      or tab_ecarts or rep_ecarts or j.get("residents_ecarts") or
                      (j.get("residents") or {}).get("faux") or
                      (not o.sans_sha and (j["sha256_egale_entete"] is False or j["sha256_egale_attendue"] is False)))
    j["verdict"] = "tout égal" if tout_juste else "écart"
    with open(o.journal, "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: j[k] for k in ("verdict", "experts_lus", "experts_faux", "controles_faux", "durees")}, ensure_ascii=False))
    sys.exit(0 if tout_juste else 1)


if __name__ == "__main__":
    main()
