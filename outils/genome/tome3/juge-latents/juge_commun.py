"""Juge du lot « espaces latents » du Tome III : lectures communes, écrites de zéro.

Écrit pour troncons le 2026-10-27, rôle « juge indépendant des chiffres du lot espaces latents ».
Aucune ligne n'est reprise de outils/genome/tome3/latents_*.py (non lus avant d'écrire ce fichier),
ni du lecteur GGUF de 03 : le format GGUF v3 est relu ici octet par octet.

  - GGUF v3 : magie, version, nombre de tenseurs, nombre de clés ; clés (chaîne, type, valeur) ;
    fiches des tenseurs (nom, dimensions, type ggml, décalage) ; données alignées sur
    general.alignment (32 par défaut).
  - MXFP4 (type ggml 39) : blocs de 17 octets pour 32 poids, un octet E8M0 puis 16 octets ; le poids t
    du bloc dans le demi-octet faible de l'octet t, le poids 16 + t dans le fort. Valeur réelle :
    E2M1(code) · 2^(e − 127), E2M1 ∈ {0, 0,5, 1, 1,5, 2, 3, 4, 6} et le bit 3 du code pour le signe.
  - .sym (lot B) : « SYM1 », 4 centres f64 en grandeurs E2M1 doublées, puis gate, up, down, deux
    symboles par octet (pair dans le demi-octet faible) ; symbole = classe (bits 0-1) + signe (bit 2).
  - Captures de l'éclaireur : h-Lcc.f32 (positions × 2 880, f32), routage-Lcc.bin (par position 4
    octets d'experts puis 4 f32 de poids).
"""
from __future__ import annotations

import os
import struct

import numpy as np

GGUF = "~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf"
CAPT = "~/dev/essais/troncons/genome/eclaireur"
SYM = "~/dev/essais/troncons/genome/synonyme/sym"
DEPOT = "~/dev/active/troncons"
N = 2880
E2M1 = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0])


class Gguf:
    """Lecteur GGUF v3 minimal : fiches des tenseurs et vue sur leurs octets."""

    def __init__(self, chemin=GGUF):
        self.chemin = chemin
        with open(chemin, "rb") as f:
            self._f = f
            if f.read(4) != b"GGUF":
                raise ValueError("magie GGUF absente")
            (self.version,) = struct.unpack("<I", f.read(4))
            n_t, n_kv = struct.unpack("<QQ", f.read(16))
            self.cles = {}
            for _ in range(n_kv):
                cle = self._chaine()
                (typ,) = struct.unpack("<I", f.read(4))
                self.cles[cle] = self._valeur(typ)
            self.tenseurs = {}
            for _ in range(n_t):
                nom = self._chaine()
                (nd,) = struct.unpack("<I", f.read(4))
                dims = struct.unpack(f"<{nd}Q", f.read(8 * nd))
                typ, dec = struct.unpack("<IQ", f.read(12))
                self.tenseurs[nom] = (dims, typ, dec)
            al = int(self.cles.get("general.alignment", 32))
            pos = f.tell()
            self.debut = (pos + al - 1) // al * al
        self._mm = np.memmap(chemin, dtype=np.uint8, mode="r")

    def _chaine(self):
        (n,) = struct.unpack("<Q", self._f.read(8))
        return self._f.read(n).decode("utf-8")

    def _valeur(self, typ):
        f = self._f
        simples = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}
        if typ in simples:
            fmt = simples[typ]
            return struct.unpack(fmt, f.read(struct.calcsize(fmt)))[0]
        if typ == 8:
            return self._chaine()
        if typ == 9:
            (st,) = struct.unpack("<I", f.read(4))
            (n,) = struct.unpack("<Q", f.read(8))
            return [self._valeur(st) for _ in range(n)]
        raise ValueError(f"type GGUF inconnu {typ}")

    def octets(self, nom, taille):
        dims, typ, dec = self.tenseurs[nom]
        a = self.debut + dec
        return self._mm[a:a + taille]

    def f32(self, nom):
        dims, typ, dec = self.tenseurs[nom]
        if typ != 0:
            raise ValueError(f"{nom} : type {typ}, pas F32")
        n = int(np.prod(dims))
        v = self.octets(nom, 4 * n).view("<f4")
        return np.array(v, dtype=np.float64).reshape(tuple(reversed(dims)))

    def expert_mxfp4(self, nom, e):
        """(codes (R, C) uint8, exposants (R, C/32) int) de l'expert e d'un tenseur *_exps MXFP4."""
        dims, typ, dec = self.tenseurs[nom]
        if typ != 39:
            raise ValueError(f"{nom} : type {typ}, pas MXFP4")
        C, R, E = dims
        nb = C // 32
        par_expert = R * nb * 17
        a = self.debut + dec + e * par_expert
        o = np.asarray(self._mm[a:a + par_expert]).reshape(R, nb, 17)
        ex = o[:, :, 0].astype(np.int64)
        qs = o[:, :, 1:]
        codes = np.empty((R, nb, 32), dtype=np.uint8)
        codes[:, :, :16] = qs & 15
        codes[:, :, 16:] = qs >> 4
        return codes.reshape(R, C), ex


def valeur_e2m1(codes):
    v = E2M1[codes & 7]
    return np.where((codes & 8) != 0, -v, v)


def lire_sym(chemin):
    o = np.fromfile(chemin, dtype=np.uint8)
    if bytes(o[:4]) != b"SYM1":
        raise ValueError("magie SYM1 absente")
    centres_doubles = np.frombuffer(o[4:36].tobytes(), dtype="<f8").copy()
    corps = o[36:]
    m = N * N // 2
    if corps.size != 3 * m:
        raise ValueError("taille du corps")
    sorties = []
    for j in range(3):
        b = corps[j * m:(j + 1) * m]
        s = np.empty(N * N, dtype=np.uint8)
        s[0::2] = b & 15
        s[1::2] = b >> 4
        sorties.append(s.reshape(N, N))
    return centres_doubles / 2.0, sorties   # centres en unités E2M1 (grandeurs réelles)


def valeur_sym(sym, centres):
    v = centres[sym & 3]
    return np.where((sym & 4) != 0, -v, v)


def captures(quoi, couche):
    h = np.memmap(os.path.join(CAPT, quoi, f"h-L{couche:02d}.f32"), dtype="<f4", mode="r").reshape(-1, N)
    r = np.fromfile(os.path.join(CAPT, quoi, f"routage-L{couche:02d}.bin"), dtype=np.uint8).reshape(-1, 20)
    experts = r[:, :4].astype(np.int64)
    poids = np.frombuffer(r[:, 4:].tobytes(), dtype="<f4").reshape(-1, 4).astype(np.float64)
    return h, experts, poids


def lire_csv(chemin):
    import csv
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
