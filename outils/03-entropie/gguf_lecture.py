"""Lecteur GGUF minimal, écrit de zéro pour troncons.

Rôle : donner, pour chaque tenseur d'un fichier GGUF, son nom, son type ggml,
sa forme et une vue numpy (memmap, aucune copie) sur ses octets bruts. Il ne
déquantifie rien : la mesure d'entropie travaille sur les octets et les champs
tels qu'ils sont stockés.

Format (spécification publique GGUF v3, dépôt ggml-org/ggml, docs/gguf.md) :
  en-tête   : 'GGUF', version u32, nb_tenseurs u64, nb_clés u64
  clés      : chaîne (u64 longueur + octets), type u32, valeur
  tenseurs  : nom, n_dims u32, dims u64[n], type u32, décalage u64
  données   : alignées sur general.alignment (32 par défaut)
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

import numpy as np

# Types ggml utiles ici : (nom, poids par bloc, octets par bloc).
TYPES_GGML = {
    0: ("F32", 1, 4),
    1: ("F16", 1, 2),
    2: ("Q4_0", 32, 18),
    3: ("Q4_1", 32, 20),
    6: ("Q5_0", 32, 22),
    7: ("Q5_1", 32, 24),
    8: ("Q8_0", 32, 34),
    10: ("Q2_K", 256, 84),
    11: ("Q3_K", 256, 110),
    12: ("Q4_K", 256, 144),
    13: ("Q5_K", 256, 176),
    14: ("Q6_K", 256, 210),
    15: ("Q8_K", 256, 292),
    30: ("BF16", 1, 2),
    39: ("MXFP4", 32, 17),
}

# Taille des scalaires des valeurs de métadonnées, par code de type GGUF.
_SCALAIRES = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i",
              6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}


@dataclass
class Tenseur:
    nom: str
    type_ggml: int
    dims: tuple
    decalage: int          # absolu dans le fichier
    nb_octets: int

    @property
    def nom_type(self) -> str:
        return TYPES_GGML.get(self.type_ggml, (f"type{self.type_ggml}",))[0]

    @property
    def nb_poids(self) -> int:
        n = 1
        for d in self.dims:
            n *= d
        return n


class LecteurGGUF:
    def __init__(self, chemin: str):
        self.chemin = chemin
        self.meta: dict = {}
        self.tenseurs: list[Tenseur] = []
        with open(chemin, "rb") as f:
            self._lire_entete(f)
        self.carte = np.memmap(chemin, dtype=np.uint8, mode="r")

    # --- lecture de l'en-tête -------------------------------------------
    @staticmethod
    def _chaine(f) -> str:
        (n,) = struct.unpack("<Q", f.read(8))
        return f.read(n).decode("utf-8", errors="replace")

    def _valeur(self, f, t: int):
        if t in _SCALAIRES:
            fmt = _SCALAIRES[t]
            return struct.unpack(fmt, f.read(struct.calcsize(fmt)))[0]
        if t == 8:
            return self._chaine(f)
        if t == 9:
            (t2,) = struct.unpack("<I", f.read(4))
            (n,) = struct.unpack("<Q", f.read(8))
            if t2 in _SCALAIRES:   # tableau de scalaires : on le saute vite
                taille = struct.calcsize(_SCALAIRES[t2])
                brut = f.read(taille * n)
                return ("tableau", t2, n) if n > 64 else list(
                    struct.unpack("<" + _SCALAIRES[t2][1] * n, brut))
            elements = [self._valeur(f, t2) for _ in range(n)]
            return elements if n <= 64 else ("tableau", t2, n)
        raise ValueError(f"type de métadonnée inconnu : {t}")

    def _lire_entete(self, f):
        if f.read(4) != b"GGUF":
            raise ValueError("pas un fichier GGUF")
        (self.version,) = struct.unpack("<I", f.read(4))
        nb_t, nb_k = struct.unpack("<QQ", f.read(16))
        for _ in range(nb_k):
            cle = self._chaine(f)
            (t,) = struct.unpack("<I", f.read(4))
            self.meta[cle] = self._valeur(f, t)
        infos = []
        for _ in range(nb_t):
            nom = self._chaine(f)
            (nd,) = struct.unpack("<I", f.read(4))
            dims = struct.unpack("<" + "Q" * nd, f.read(8 * nd))
            t, dec = struct.unpack("<IQ", f.read(12))
            infos.append((nom, t, dims, dec))
        align = int(self.meta.get("general.alignment", 32))
        debut = f.tell()
        debut = (debut + align - 1) // align * align
        self.debut_donnees = debut
        for nom, t, dims, dec in infos:
            n = 1
            for d in dims:
                n *= d
            if t not in TYPES_GGML:
                raise ValueError(f"{nom} : type ggml {t} non pris en charge")
            _, bloc, oct_bloc = TYPES_GGML[t]
            nb_oct = n // bloc * oct_bloc
            self.tenseurs.append(Tenseur(nom, t, tuple(dims), debut + dec, nb_oct))

    def octets(self, t: Tenseur) -> np.ndarray:
        return self.carte[t.decalage: t.decalage + t.nb_octets]
