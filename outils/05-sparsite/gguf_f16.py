"""Lecteur GGUF réduit au nécessaire de l'étude 05 : métadonnées et tenseurs
F32 / F16 en tableaux numpy (memmap, sans copie).

Format suivi : spécification GGUF v3 publique (ggml-org/ggml, docs/gguf.md).
Une forme GGUF [ne0, ne1] (ne0 = dimension contiguë) devient un tableau numpy
de forme (ne1, ne0) : pour une matrice de poids, (sorties, entrées), et
y = W @ x.
"""
from __future__ import annotations

import struct

import numpy as np

_SCAL = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i",
         6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}
_DTYPE = {0: np.float32, 1: np.float16}


class Lecteur:
    def __init__(self, chemin: str):
        self.chemin = chemin
        self.meta: dict = {}
        self.tenseurs: dict = {}
        with open(chemin, "rb") as f:
            if f.read(4) != b"GGUF":
                raise ValueError("pas un fichier GGUF")
            version, n_t, n_kv = struct.unpack("<IQQ", f.read(20))
            if version != 3:
                raise ValueError(f"version GGUF {version} non prise en charge")
            for _ in range(n_kv):
                cle = self._chaine(f)
                t = struct.unpack("<I", f.read(4))[0]
                self.meta[cle] = self._valeur(f, t)
            infos = []
            for _ in range(n_t):
                nom = self._chaine(f)
                nd = struct.unpack("<I", f.read(4))[0]
                dims = struct.unpack(f"<{nd}Q", f.read(8 * nd))
                typ, dec = struct.unpack("<IQ", f.read(12))
                infos.append((nom, dims, typ, dec))
            align = int(self.meta.get("general.alignment", 32))
            debut = f.tell()
            debut += (-debut) % align
        self._mm = np.memmap(chemin, dtype=np.uint8, mode="r")
        for nom, dims, typ, dec in infos:
            self.tenseurs[nom] = (dims, typ, debut + dec)

    @staticmethod
    def _chaine(f) -> str:
        n = struct.unpack("<Q", f.read(8))[0]
        return f.read(n).decode("utf-8", errors="replace")

    def _valeur(self, f, t):
        if t in _SCAL:
            fmt = _SCAL[t]
            return struct.unpack(fmt, f.read(struct.calcsize(fmt)))[0]
        if t == 8:
            return self._chaine(f)
        if t == 9:
            st = struct.unpack("<I", f.read(4))[0]
            n = struct.unpack("<Q", f.read(8))[0]
            return [self._valeur(f, st) for _ in range(n)]
        raise ValueError(f"type de valeur GGUF inconnu : {t}")

    def tableau(self, nom: str, dtype=np.float32) -> np.ndarray:
        dims, typ, dec = self.tenseurs[nom]
        if typ not in _DTYPE:
            raise ValueError(f"{nom} : type ggml {typ} non pris en charge ici")
        n = int(np.prod(dims))
        brut = self._mm[dec: dec + n * np.dtype(_DTYPE[typ]).itemsize]
        a = brut.view(_DTYPE[typ]).reshape(tuple(reversed(dims)))
        return a.astype(dtype)
