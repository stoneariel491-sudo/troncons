"""Juge des chiffres du lot « espaces latents », second flux : les lectures à la source, écrites de zéro.

Écrit pour troncons le 2026-10-27. Aucune ligne n'est reprise des outils du lot (outils/genome/tome3/
latents_*.py, memoire/outils/tome3_latents.py) ni du juge du premier flux (outils/genome/tome3/
juge-latents/) : les formats sont relus d'après leur description (GGUF v3, MXFP4 de ggml, .sym du lot B,
captures de l'éclaireur), et chaque lecture est vérifiée contre un fichier commité dans les outils qui
l'emploient.

  GGUF v3   : « GGUF », version u32, nombre de tenseurs u64, nombre de clés u64 ; clés (chaîne u64 +
              octets, type u32, valeur) ; fiches (nom, n_dims u32, dims u64, type u32, décalage u64) ;
              données alignées sur general.alignment (32 si absent), décalages relatifs à leur début.
  MXFP4     : type ggml 39, 17 octets pour 32 poids : un octet E8M0 (e), puis 16 octets ; le poids t du
              bloc est le demi-octet faible de l'octet t, le poids 16 + t le demi-octet fort. Code c : bit 3
              le signe, bits 0-2 la grandeur E2M1 {0, ½, 1, 3/2, 2, 3, 4, 6} ; valeur = E2M1 · 2^(e − 127).
  .sym      : « SYM1 », quatre centres f64 (grandeurs E2M1 doublées, donc c_k = centre / 2), puis les
              symboles de gate, up, down, deux par octet (le poids pair dans le demi-octet faible) ;
              symbole : classe k (bits 0-1), signe (bit 2) ; valeur = ± c_k · s_b, s_b l'échelle du bloc.
  captures  : h-Lcc.f32 (positions × 2 880, f32) ; routage-Lcc.bin (par position : 4 octets d'experts,
              puis 4 f32 de poids).
"""
from __future__ import annotations

import struct

import numpy as np

GGUF = "~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf"
CAPT = "~/dev/essais/troncons/genome/eclaireur/calib"
SYM = "~/dev/essais/troncons/genome/synonyme/sym"
N = 2880
GRANDEUR = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0])
VALEUR_CODE = np.concatenate([GRANDEUR, -GRANDEUR])        # code 0..15 -> valeur en unités de s_b


class LecteurGguf:
    def __init__(self, chemin: str = GGUF):
        self.chemin = chemin
        with open(chemin, "rb") as f:
            assert f.read(4) == b"GGUF", "pas un GGUF"
            self.version, = struct.unpack("<I", f.read(4))
            nt, nk = struct.unpack("<QQ", f.read(16))
            self.meta = {}
            for _ in range(nk):
                cle = self._ch(f)
                t, = struct.unpack("<I", f.read(4))
                self.meta[cle] = self._val(f, t)
            self.fiches = {}
            for _ in range(nt):
                nom = self._ch(f)
                nd, = struct.unpack("<I", f.read(4))
                dims = list(struct.unpack(f"<{nd}Q", f.read(8 * nd)))
                typ, dec = struct.unpack("<IQ", f.read(12))
                self.fiches[nom] = {"dims": dims, "type": typ, "decalage": dec}
            a = int(self.meta.get("general.alignment", 32))
            self.base = -(-f.tell() // a) * a

    @staticmethod
    def _ch(f) -> str:
        n, = struct.unpack("<Q", f.read(8))
        return f.read(n).decode("utf-8", errors="replace")

    def _val(self, f, t):
        fmt = {0: "B", 1: "b", 2: "H", 3: "h", 4: "I", 5: "i", 6: "f", 7: "?", 10: "Q", 11: "q", 12: "d"}
        if t in fmt:
            s = struct.calcsize("<" + fmt[t])
            return struct.unpack("<" + fmt[t], f.read(s))[0]
        if t == 8:
            return self._ch(f)
        if t == 9:
            st, = struct.unpack("<I", f.read(4))
            n, = struct.unpack("<Q", f.read(8))
            return [self._val(f, st) for _ in range(n)]
        raise ValueError(t)

    def lire(self, nom: str, debut: int, taille: int) -> bytes:
        with open(self.chemin, "rb") as f:
            f.seek(self.base + self.fiches[nom]["decalage"] + debut)
            return f.read(taille)

    def f32(self, nom: str) -> np.ndarray:
        fi = self.fiches[nom]
        n = int(np.prod(fi["dims"]))
        if fi["type"] == 0:
            a = np.frombuffer(self.lire(nom, 0, 4 * n), dtype="<f4").astype(np.float64)
        elif fi["type"] == 30:     # bf16
            u = np.frombuffer(self.lire(nom, 0, 2 * n), dtype="<u2").astype(np.uint32) << 16
            a = u.view(np.float32).astype(np.float64)
        elif fi["type"] == 1:
            a = np.frombuffer(self.lire(nom, 0, 2 * n), dtype="<f2").astype(np.float64)
        else:
            raise ValueError(f"type {fi['type']}")
        return a.reshape(list(reversed(fi["dims"])))

    def expert_mxfp4(self, nom: str, expert: int):
        """(codes, exposants) de la matrice d'un expert : codes (lignes × colonnes) en 0..15, exposants
        (lignes × blocs) E8M0."""
        fi = self.fiches[nom]
        assert fi["type"] == 39, fi
        ne0, ne1 = fi["dims"][0], fi["dims"][1]
        blocs = ne0 // 32
        octets_ligne = blocs * 17
        brut = np.frombuffer(self.lire(nom, expert * ne1 * octets_ligne, ne1 * octets_ligne), dtype=np.uint8)
        b = brut.reshape(ne1, blocs, 17)
        e = b[:, :, 0].copy()
        q = b[:, :, 1:]
        codes = np.empty((ne1, blocs, 32), dtype=np.uint8)
        codes[:, :, :16] = q & 0x0F
        codes[:, :, 16:] = q >> 4
        return codes.reshape(ne1, ne0), e


def poids(codes: np.ndarray, e: np.ndarray) -> np.ndarray:
    s = np.ldexp(1.0, e.astype(np.int64) - 127)                 # échelle de chaque bloc
    return VALEUR_CODE[codes] * np.repeat(s, 32, axis=1)


def lire_sym(chemin: str, n_poids: int = N * N):
    """(centres c_k, symboles de gate en lignes × colonnes)."""
    with open(chemin, "rb") as f:
        assert f.read(4) == b"SYM1"
        centres = np.array(struct.unpack("<4d", f.read(32))) / 2.0
        brut = np.frombuffer(f.read(n_poids // 2), dtype=np.uint8)
    sym = np.empty(n_poids, dtype=np.uint8)
    sym[0::2] = brut & 0x0F
    sym[1::2] = brut >> 4
    return centres, sym.reshape(N, N)


def reconstruit(centres: np.ndarray, sym: np.ndarray, e: np.ndarray) -> np.ndarray:
    s = np.repeat(np.ldexp(1.0, e.astype(np.int64) - 127), 32, axis=1)
    v = centres[sym & 3]
    v = np.where(sym & 4, -v, v)
    return v * s


def captures(couche: int):
    h = np.fromfile(f"{CAPT}/h-L{couche:02d}.f32", dtype="<f4").reshape(-1, N)
    r = np.fromfile(f"{CAPT}/routage-L{couche:02d}.bin", dtype=np.uint8).reshape(-1, 20)
    experts = r[:, :4].copy()
    poids_r = r[:, 4:].copy().view("<f4").reshape(-1, 4)
    return h, experts, poids_r
