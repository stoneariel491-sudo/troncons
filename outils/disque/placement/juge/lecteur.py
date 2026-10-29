"""Lecteur du juge : le motif de lecture du moteur, par un port de complétion (00-seuils-declares.md § 2).

Écrit pour le juge, sans rien importer de lire.py ni de commun.py. Comme `trc-es` : une seule poignée ouverte
avec FILE_FLAG_NO_BUFFERING | FILE_FLAG_OVERLAPPED, un port de complétion, au plus q lectures confiées au
système ; une requête ReadFile par tronçon ; la durée d'une lecture va de sa remise au système à sa récolte ;
le débit d'une passe est octets / (dernière récolte − première remise).

`frein_ms` (cassure du témoin) : attente imposée avant chaque nouvelle remise qui suit une récolte.
"""
import ctypes
import ctypes.wintypes as wt
import hashlib
import time

_k = ctypes.WinDLL("kernel32", use_last_error=True)
_k.CreateFileW.restype = ctypes.c_void_p
_k.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, ctypes.c_void_p]
_k.CreateIoCompletionPort.restype = ctypes.c_void_p
_k.CreateIoCompletionPort.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD]
_k.ReadFile.restype = wt.BOOL
_k.ReadFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, ctypes.c_void_p]
_k.GetQueuedCompletionStatus.restype = wt.BOOL
_k.GetQueuedCompletionStatus.argtypes = [ctypes.c_void_p, ctypes.POINTER(wt.DWORD), ctypes.POINTER(ctypes.c_size_t),
                                         ctypes.POINTER(ctypes.c_void_p), wt.DWORD]
_k.CloseHandle.argtypes = [ctypes.c_void_p]
_k.VirtualAlloc.restype = ctypes.c_void_p
_k.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, wt.DWORD]
_k.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wt.DWORD]
_INVALIDE = ctypes.c_void_p(-1).value
SANS_TAMPON, CHEVAUCHE = 0x20000000, 0x40000000
ALIGN = 4096


class _Chevauche(ctypes.Structure):
    _fields_ = [("Internal", ctypes.c_size_t), ("InternalHigh", ctypes.c_size_t),
                ("Offset", wt.DWORD), ("OffsetHigh", wt.DWORD), ("hEvent", ctypes.c_void_p)]


def _ouvrir(chemin):
    h = _k.CreateFileW(str(chemin), 0x80000000, 0x1, None, 3, SANS_TAMPON | CHEVAUCHE, None)
    if h in (None, _INVALIDE):
        raise OSError(ctypes.get_last_error(), f"ouverture sans tampon de {chemin}")
    return h


def passe(chemin, lectures, q=4, frein_ms=0.0, garder=None, pas_tampon=None):
    """lectures : liste de (indice, décalage, longueur), alignés sur 4 096. Rend (résultats, secondes, octets).

    résultats : liste de (indice, décalage, longueur, remise_ns, recolte_ns, octets_rendus), dans l'ordre de
    la liste. `garder` : ensemble d'indices dont on rend aussi le SHA-256 des octets lus (témoin).
    `pas_tampon` : écart entre les places de la fenêtre (par défaut la plus longue lecture, comme le moteur,
    `HoteEpingle::allouer(prof * lal)`) ; un pas plus grand change l'alignement des destinations (J9)."""
    for i, d, l in lectures:
        if d % ALIGN or l % ALIGN or l == 0:
            raise ValueError(f"lecture {i} non alignée : {d}, {l}")
    lmax = max(l for _, _, l in lectures)
    if pas_tampon:
        if pas_tampon < lmax or pas_tampon % ALIGN:
            raise ValueError(f"pas de tampon {pas_tampon} trop court ou non aligné")
        lmax = pas_tampon
    h = _ouvrir(chemin)
    port = _k.CreateIoCompletionPort(h, None, 0, 1)
    if not port:
        _k.CloseHandle(h)
        raise OSError(ctypes.get_last_error(), "CreateIoCompletionPort")
    base = _k.VirtualAlloc(None, q * lmax, 0x3000, 0x04)
    if not base:
        raise MemoryError(q * lmax)
    ov = [_Chevauche() for _ in range(q)]
    adresse = {ctypes.addressof(o): s for s, o in enumerate(ov)}
    en_cours = {}  # place → (position dans la liste, remise_ns)
    res = [None] * len(lectures)
    empreintes = {}
    libres = list(range(q - 1, -1, -1))
    suivant = 0
    faits = 0
    nb = wt.DWORD()
    cle = ctypes.c_size_t()
    pov = ctypes.c_void_p()
    t_premier = None
    try:
        while faits < len(lectures):
            while libres and suivant < len(lectures):
                s = libres.pop()
                i, d, l = lectures[suivant]
                o = ov[s]
                o.Internal = o.InternalHigh = 0
                o.Offset, o.OffsetHigh = d & 0xFFFFFFFF, d >> 32
                o.hEvent = None
                t = time.perf_counter_ns()
                if t_premier is None:
                    t_premier = t
                if not _k.ReadFile(h, base + s * lmax, l, None, ctypes.byref(o)):
                    e = ctypes.get_last_error()
                    if e != 997:  # ERROR_IO_PENDING
                        raise OSError(e, f"ReadFile {i} à {d}")
                en_cours[s] = (suivant, t)
                suivant += 1
            ok = _k.GetQueuedCompletionStatus(port, ctypes.byref(nb), ctypes.byref(cle), ctypes.byref(pov), 0xFFFFFFFF)
            t = time.perf_counter_ns()
            if not pov.value:
                raise OSError(ctypes.get_last_error(), "GetQueuedCompletionStatus")
            s = adresse[pov.value]
            pos, t0 = en_cours.pop(s)
            if not ok:
                raise OSError(ctypes.get_last_error(), f"lecture {lectures[pos][0]} échouée")
            i, d, l = lectures[pos]
            res[pos] = (i, d, l, t0, t, nb.value)
            if garder and i in garder:
                empreintes[i] = hashlib.sha256(ctypes.string_at(base + s * lmax, nb.value)).hexdigest()
            faits += 1
            libres.append(s)
            if frein_ms and suivant < len(lectures):
                time.sleep(frein_ms / 1000)
    finally:
        _k.VirtualFree(base, 0, 0x8000)
        _k.CloseHandle(port)
        _k.CloseHandle(h)
    fin = max(r[4] for r in res)
    octets = sum(r[5] for r in res)
    return res, (fin - t_premier) / 1e9, octets, t_premier, empreintes


def empreintes_tamponnees(chemin, lectures, decale=0):
    """Chemin indépendant : open/seek/read ordinaire de Python (tamponné), au décalage (+ `decale`)."""
    r = {}
    with open(chemin, "rb") as f:
        for i, d, l in lectures:
            f.seek(d + decale)
            r[i] = hashlib.sha256(f.read(l)).hexdigest()
    return r
