"""Mesure des étages RAM -> PCIe -> VRAM de la machine, sans boîte à outils CUDA.

On appelle directement le runtime CUDA livré avec llama.cpp (cudart64_12.dll) par
ctypes : aucune compilation, aucun noyau. Ce que l'on mesure :

  1. hôte -> carte (H2D) et carte -> hôte (D2H), mémoire hôte épinglée et paginable,
     pour des tailles de bloc de 64 Kio à 256 Mio ;
  2. carte -> carte (D2D), qui lit et écrit la VRAM : débit VRAM utile = 2 x octets / temps ;
  3. le recouvrement : un H2D sur un flux pendant un D2D sur un autre flux, pour voir
     si le transfert PCIe ralentit les accès VRAM (et l'inverse).

Témoins (chacun peut tomber, voir --temoin-casse) :
  - aller-retour H2D puis D2H : les octets revenus doivent être identiques à l'envoi ;
  - aucun débit H2D ou D2H ne doit dépasser le plafond théorique du lien,
    PCIe 4.0 x8 = 8 voies x 16 GT/s x 128/130 / 8 = 15,754 Go/s ;
  - aucun débit D2D (compté lecture + écriture) ne doit dépasser le plafond GDDR6
    de la carte, 128 bits x 16 Gbit/s / 8 = 256 Go/s.

Séries alternées ABBA : chaque paire de configurations comparées se mesure dans
l'ordre A B B A, plusieurs fois ; on rapporte la médiane et l'étendue.

Ajouts du 2026-10-15 (deuxième passe), après que la première passe a montré deux choses :
  - le témoin VRAM est tombé à 16 Mio (719 Go/s > 256) : la copie tenait dans le cache L2
    de la puce. Le plafond GDDR6 ne s'applique donc qu'aux tailles n >= 2 x L2 (seuil
    déclaré avant la deuxième passe, L2 lu sur la carte par cudaDeviceGetAttribute) ; en
    dessous, la mesure est étiquetée « L2 » ;
  - le lien PCIe change de génération pendant la mesure (relevé nvidia-smi : Gen1 au repos,
    Gen3 la plupart du temps pendant les copies seules, Gen4 sous charge). On lit donc la
    génération et la largeur du lien par NVML (nvml.dll du pilote) avant et après chaque
    mesure, et le plafond du témoin devient celui de la génération la plus haute observée ;
  - une phase « sous charge » mesure H2D pendant que la carte copie en VRAM sur un autre
    flux, ce qui la tient dans un état de performance haut, comme pendant une inférence.

Usage : python -I outils/chargement_pcie.py [--dll CHEMIN] [--sortie JOURNAL.json]
"""

import argparse
import ctypes
import json
import os
import platform
import statistics
import sys
import time
from ctypes import byref, c_float, c_int, c_size_t, c_void_p

PLAFOND_PCIE_GO_S = 8 * 16e9 * 128 / 130 / 8 / 1e9  # 15,754 Go/s, Gen4 x8
# Débit brut par voie et par sens, en Go/s, après codage de ligne (8b/10b puis 128b/130b).
PAR_VOIE_GO_S = {1: 2.5 * 8 / 10 / 8, 2: 5.0 * 8 / 10 / 8, 3: 8.0 * 128 / 130 / 8,
                 4: 16.0 * 128 / 130 / 8, 5: 32.0 * 128 / 130 / 8}
CUDA_ATTR_L2 = 38  # cudaDevAttrL2CacheSize (driver_types.h)
PLAFOND_VRAM_GO_S = 128 * 16e9 / 8 / 1e9  # 256 Go/s, GDDR6 16 Gbit/s sur 128 bits

H2D, D2H, D2D = 1, 2, 3


class Nvml:
    """Génération et largeur courantes du lien PCIe, état de performance. Sans NVML : None."""

    def __init__(self):
        try:
            self.lib = ctypes.WinDLL(r"C:\Windows\System32\nvml.dll")
            if self.lib.nvmlInit_v2() != 0:
                raise OSError("nvmlInit_v2")
            self.h = c_void_p()
            if self.lib.nvmlDeviceGetHandleByIndex_v2(0, byref(self.h)) != 0:
                raise OSError("handle")
        except OSError:
            self.lib = None

    def lien(self):
        if self.lib is None:
            return None
        g, w, p = ctypes.c_uint(), ctypes.c_uint(), c_int()
        self.lib.nvmlDeviceGetCurrPcieLinkGeneration(self.h, byref(g))
        self.lib.nvmlDeviceGetCurrPcieLinkWidth(self.h, byref(w))
        self.lib.nvmlDeviceGetPerformanceState(self.h, byref(p))
        return {"gen": g.value, "largeur": w.value, "pstate": p.value}

    def occupation(self):
        """Taux d'occupation de la carte et nombre de processus de calcul : si d'autres
        programmes calculent sur la carte, les débits mesurés sont partagés et le journal le dit."""
        if self.lib is None:
            return None

        class Util(ctypes.Structure):
            _fields_ = [("gpu", ctypes.c_uint), ("memoire", ctypes.c_uint)]
        u = Util()
        self.lib.nvmlDeviceGetUtilizationRates(self.h, byref(u))
        n = ctypes.c_uint(0)
        self.lib.nvmlDeviceGetComputeRunningProcesses_v3(self.h, byref(n), None)
        return {"gpu_pct": u.gpu, "memoire_pct": u.memoire, "processus_calcul": n.value}


def plafond_lien(etats, defaut):
    """Plafond du lien pour la génération la plus haute vue autour d'une mesure."""
    vus = [e for e in etats if e]
    if not vus:
        return defaut
    gen = max(e["gen"] for e in vus)
    larg = max(e["largeur"] for e in vus)
    return PAR_VOIE_GO_S[gen] * larg


class Cuda:
    def __init__(self, chemin):
        self.lib = ctypes.WinDLL(chemin)
        for nom in (
            "cudaSetDevice", "cudaMalloc", "cudaMallocHost", "cudaFree", "cudaFreeHost",
            "cudaMemcpy", "cudaMemcpyAsync", "cudaEventCreate", "cudaEventRecord",
            "cudaEventSynchronize", "cudaEventElapsedTime", "cudaStreamCreate",
            "cudaStreamSynchronize", "cudaDeviceSynchronize", "cudaMemset",
            "cudaHostRegister", "cudaHostUnregister", "cudaRuntimeGetVersion",
            "cudaDriverGetVersion", "cudaMemGetInfo",
        ):
            getattr(self.lib, nom).restype = c_int
        self.lib.cudaMemcpy.argtypes = [c_void_p, c_void_p, c_size_t, c_int]
        self.lib.cudaMemcpyAsync.argtypes = [c_void_p, c_void_p, c_size_t, c_int, c_void_p]
        self.lib.cudaEventRecord.argtypes = [c_void_p, c_void_p]
        self.lib.cudaEventSynchronize.argtypes = [c_void_p]
        self.lib.cudaEventElapsedTime.argtypes = [ctypes.POINTER(c_float), c_void_p, c_void_p]
        self.lib.cudaMalloc.argtypes = [ctypes.POINTER(c_void_p), c_size_t]
        self.lib.cudaMallocHost.argtypes = [ctypes.POINTER(c_void_p), c_size_t]
        self.lib.cudaFree.argtypes = [c_void_p]
        self.lib.cudaFreeHost.argtypes = [c_void_p]
        self.lib.cudaMemset.argtypes = [c_void_p, c_int, c_size_t]
        self.lib.cudaStreamSynchronize.argtypes = [c_void_p]
        self.lib.cudaHostRegister.argtypes = [c_void_p, c_size_t, ctypes.c_uint]
        self.lib.cudaHostUnregister.argtypes = [c_void_p]
        self.lib.cudaMemGetInfo.argtypes = [ctypes.POINTER(c_size_t), ctypes.POINTER(c_size_t)]

    def ok(self, code, quoi):
        if code != 0:
            raise RuntimeError(f"{quoi} : erreur CUDA {code}")

    def appel(self, nom, *args):
        self.ok(getattr(self.lib, nom)(*args), nom)

    def malloc(self, n):
        p = c_void_p()
        self.appel("cudaMalloc", byref(p), n)
        return p

    def malloc_hote(self, n):
        p = c_void_p()
        self.appel("cudaMallocHost", byref(p), n)
        return p

    def evenement(self):
        e = c_void_p()
        self.appel("cudaEventCreate", byref(e))
        return e

    def flux(self):
        s = c_void_p()
        self.appel("cudaStreamCreate", byref(s))
        return s


def chronometre(cuda, fonction, repetitions, flux=None):
    """Temps moyen d'un appel, en secondes, mesuré par événements CUDA sur le flux donné."""
    debut, fin = cuda.evenement(), cuda.evenement()
    fonction()  # chauffe
    cuda.appel("cudaDeviceSynchronize")
    cuda.appel("cudaEventRecord", debut, flux)
    for _ in range(repetitions):
        fonction()
    cuda.appel("cudaEventRecord", fin, flux)
    cuda.appel("cudaEventSynchronize", fin)
    ms = c_float()
    cuda.appel("cudaEventElapsedTime", byref(ms), debut, fin)
    return ms.value / 1e3 / repetitions


def temoin_aller_retour(cuda, n, casse):
    """Envoie n octets connus, les rapatrie, compare. Retourne (réussi, détail)."""
    hote_a = cuda.malloc_hote(n)
    hote_b = cuda.malloc_hote(n)
    carte = cuda.malloc(n)
    motif = bytes((i * 131 + 7) & 0xFF for i in range(4096)) * (n // 4096)
    ctypes.memmove(hote_a, motif, n)
    ctypes.memset(hote_b, 0, n)
    cuda.appel("cudaMemcpy", carte, hote_a, n, H2D)
    if casse:
        # On abîme un octet sur la carte : l'instrument doit le voir.
        cuda.appel("cudaMemset", c_void_p(carte.value + n // 2), 0xAB, 1)
    cuda.appel("cudaMemcpy", hote_b, carte, n, D2H)
    revenu = ctypes.string_at(hote_b, n)
    egal = revenu == motif
    cuda.appel("cudaFree", carte)
    cuda.appel("cudaFreeHost", hote_a)
    cuda.appel("cudaFreeHost", hote_b)
    return egal, f"{n} octets, identiques={egal}"


def abba(mesure_a, mesure_b, tours):
    a, b = [], []
    for _ in range(tours):
        a.append(mesure_a())
        b.append(mesure_b())
        b.append(mesure_b())
        a.append(mesure_a())
    return a, b


def resume(valeurs):
    return {
        "mediane": statistics.median(valeurs),
        "min": min(valeurs),
        "max": max(valeurs),
        "n": len(valeurs),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dll", default=r"~\dev\modeles\llama.cpp-b11515\cudart64_12.dll")
    ap.add_argument("--sortie", default=None)
    ap.add_argument("--tours", type=int, default=3)
    ap.add_argument("--temoin-casse", action="store_true",
                    help="abîme volontairement le témoin et abaisse les plafonds : l'instrument doit tomber")
    args = ap.parse_args()

    cuda = Cuda(args.dll)
    cuda.appel("cudaSetDevice", 0)
    nvml = Nvml()
    l2 = c_int()
    cuda.lib.cudaDeviceGetAttribute.restype = c_int
    cuda.lib.cudaDeviceGetAttribute.argtypes = [ctypes.POINTER(c_int), c_int, c_int]
    cuda.appel("cudaDeviceGetAttribute", byref(l2), CUDA_ATTR_L2, 0)
    vr, vd = c_int(), c_int()
    cuda.appel("cudaRuntimeGetVersion", byref(vr))
    cuda.appel("cudaDriverGetVersion", byref(vd))
    libre, total = c_size_t(), c_size_t()
    cuda.appel("cudaMemGetInfo", byref(libre), byref(total))

    plafond_pcie = PLAFOND_PCIE_GO_S if not args.temoin_casse else 1.0
    plafond_vram = PLAFOND_VRAM_GO_S if not args.temoin_casse else 1.0

    journal = {
        "outil": "chargement_pcie.py",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "machine": platform.platform(),
        "cudart": vr.value, "pilote_cuda": vd.value,
        "vram_libre_octets": libre.value, "vram_totale_octets": total.value,
        "l2_octets": l2.value, "lien_depart": nvml.lien(), "occupation_depart": nvml.occupation(),
        "plafonds_go_s": {"pcie_gen4_x8": plafond_pcie, "gddr6_128b_16gbps": plafond_vram},
        "temoin_casse": args.temoin_casse,
        "temoins": [], "transferts": [], "d2d": [], "h2d_sous_charge": [], "recouvrement": [],
    }
    echecs = []

    ok, det = temoin_aller_retour(cuda, 64 << 20, args.temoin_casse)
    journal["temoins"].append({"nom": "aller-retour 64 Mio", "reussi": ok, "detail": det})
    if not ok:
        echecs.append("aller-retour : octets différents")

    plus_grand = 256 << 20
    hote_epingle = cuda.malloc_hote(plus_grand)
    ctypes.memset(hote_epingle, 1, plus_grand)
    paginable = ctypes.create_string_buffer(plus_grand)
    hote_paginable = c_void_p(ctypes.addressof(paginable))
    carte_a = cuda.malloc(plus_grand)
    carte_b = cuda.malloc(plus_grand)

    tailles = [64 << 10, 256 << 10, 1 << 20, 4 << 20, 16 << 20, 64 << 20, 256 << 20]
    for n in tailles:
        rep = max(3, min(200, (1 << 30) // n))
        for sens, nom_sens in ((H2D, "H2D"), (D2H, "D2H")):
            def copie(hote):
                if sens == H2D:
                    return lambda: cuda.appel("cudaMemcpy", carte_a, hote, n, H2D)
                return lambda: cuda.appel("cudaMemcpy", hote, carte_a, n, D2H)
            fa = copie(hote_epingle)
            fb = copie(hote_paginable)
            avant = nvml.lien()
            ta, tb = abba(lambda: chronometre(cuda, fa, rep), lambda: chronometre(cuda, fb, rep), args.tours)
            apres = nvml.lien()
            plafond_ici = plafond_pcie if args.temoin_casse else min(plafond_pcie, plafond_lien([avant, apres], plafond_pcie))
            for memoire, temps in (("epinglee", ta), ("paginable", tb)):
                debits = [n / t / 1e9 for t in temps]
                r = resume(debits)
                journal["transferts"].append({"sens": nom_sens, "memoire": memoire, "octets": n,
                                              "repetitions": rep, "go_s": r,
                                              "latence_us_mediane": statistics.median(temps) * 1e6,
                                              "lien_avant": avant, "lien_apres": apres,
                                              "plafond_lien_go_s": plafond_ici})
                # Le plafond du lien courant est indicatif (la génération peut monter entre deux
                # lectures NVML) ; le témoin dur reste le plafond Gen4 x8.
                if r["max"] > plafond_pcie:
                    echecs.append(f"{nom_sens} {memoire} {n} o : {r['max']:.2f} Go/s > plafond {plafond_pcie:.2f}")
                print(f"{nom_sens} {memoire:9s} {n >> 10:7d} Kio : {r['mediane']:6.2f} Go/s "
                      f"[{r['min']:.2f}-{r['max']:.2f}]  latence {statistics.median(temps) * 1e6:9.1f} us")

    for n in (16 << 20, 64 << 20, 256 << 20):
        rep = max(5, (4 << 30) // n)
        f = lambda: cuda.appel("cudaMemcpy", carte_b, carte_a, n, D2D)
        temps = [chronometre(cuda, f, rep) for _ in range(4 * args.tours)]
        debits = [2 * n / t / 1e9 for t in temps]
        r = resume(debits)
        regime = "VRAM" if n >= 2 * l2.value else "L2"
        journal["d2d"].append({"octets": n, "regime": regime, "go_s_lecture_plus_ecriture": r})
        if regime == "VRAM" and r["max"] > plafond_vram:
            echecs.append(f"D2D {n} o : {r['max']:.1f} Go/s > plafond {plafond_vram:.1f}")
        print(f"D2D {n >> 20:4d} Mio [{regime}] : {r['mediane']:6.1f} Go/s (lecture+écriture) [{r['min']:.1f}-{r['max']:.1f}]")

    # H2D sous charge : chaque copie H2D (flux 1) est accompagnée d'une copie D2D de 128 Mio
    # (flux 2), ce qui tient la carte dans un état de performance haut. Le temps H2D est lu
    # par événements sur le flux 1 seul.
    fc1, fc2 = cuda.flux(), cuda.flux()
    n_charge = 128 << 20
    for n in (1 << 20, 4 << 20, 16 << 20, 64 << 20):
        rep = max(8, min(200, (1 << 30) // n))
        temps, etats = [], []
        for _ in range(2 * args.tours):
            debut, fin = cuda.evenement(), cuda.evenement()
            for _ in range(20):  # chauffe : la carte monte d'état avant la mesure
                cuda.appel("cudaMemcpyAsync", carte_b, carte_a, n_charge, D2D, fc2)
            cuda.appel("cudaEventRecord", debut, fc1)
            for _ in range(rep):
                cuda.appel("cudaMemcpyAsync", carte_a, hote_epingle, n, H2D, fc1)
                cuda.appel("cudaMemcpyAsync", carte_b, carte_a, n_charge, D2D, fc2)
            cuda.appel("cudaEventRecord", fin, fc1)
            etats.append(nvml.lien())
            cuda.appel("cudaEventSynchronize", fin)
            ms = c_float()
            cuda.appel("cudaEventElapsedTime", byref(ms), debut, fin)
            temps.append(ms.value / 1e3 / rep)
            cuda.appel("cudaDeviceSynchronize")
        debits = [n / t / 1e9 for t in temps]
        r = resume(debits)
        plafond_ici = plafond_pcie if args.temoin_casse else min(plafond_pcie, plafond_lien(etats, plafond_pcie))
        journal["h2d_sous_charge"].append({"octets": n, "repetitions": rep, "go_s": r, "liens": etats,
                                           "plafond_lien_go_s": plafond_ici})
        if r["max"] > plafond_pcie:
            echecs.append(f"H2D sous charge {n} o : {r['max']:.2f} Go/s > plafond {plafond_pcie:.2f}")
        gens = sorted({e["gen"] for e in etats if e})
        print(f"H2D sous charge {n >> 10:7d} Kio : {r['mediane']:6.2f} Go/s [{r['min']:.2f}-{r['max']:.2f}] gen vues {gens}")

    # Recouvrement : H2D 64 Mio sur le flux 1 pendant des D2D 64 Mio sur le flux 2.
    n = 64 << 20
    f1, f2 = cuda.flux(), cuda.flux()
    carte_c = cuda.malloc(n)
    carte_d = cuda.malloc(n)
    reps_h2d, reps_d2d = 16, 64

    def seul_h2d():
        return chronometre(cuda, lambda: cuda.appel("cudaMemcpyAsync", carte_a, hote_epingle, n, H2D, f1), reps_h2d, f1)

    def seul_d2d():
        return chronometre(cuda, lambda: cuda.appel("cudaMemcpyAsync", carte_d, carte_c, n, D2D, f2), reps_d2d, f2)

    def ensemble():
        cuda.appel("cudaDeviceSynchronize")
        t0 = time.perf_counter()
        e1d, e1f, e2d, e2f = (cuda.evenement() for _ in range(4))
        cuda.appel("cudaEventRecord", e1d, f1)
        cuda.appel("cudaEventRecord", e2d, f2)
        for i in range(reps_d2d):
            if i % (reps_d2d // reps_h2d) == 0:
                cuda.appel("cudaMemcpyAsync", carte_a, hote_epingle, n, H2D, f1)
            cuda.appel("cudaMemcpyAsync", carte_d, carte_c, n, D2D, f2)
        cuda.appel("cudaEventRecord", e1f, f1)
        cuda.appel("cudaEventRecord", e2f, f2)
        cuda.appel("cudaDeviceSynchronize")
        mur = time.perf_counter() - t0
        m1, m2 = c_float(), c_float()
        cuda.appel("cudaEventElapsedTime", byref(m1), e1d, e1f)
        cuda.appel("cudaEventElapsedTime", byref(m2), e2d, e2f)
        return m1.value / 1e3, m2.value / 1e3, mur

    for tour in range(args.tours):
        lien_seul = nvml.lien()
        th = seul_h2d() * reps_h2d
        td = seul_d2d() * reps_d2d
        t1, t2, mur = ensemble()
        lien_ensemble = nvml.lien()
        res = {
            "tour": tour,
            "h2d_seul_s": th, "d2d_seul_s": td, "somme_s": th + td,
            "h2d_ensemble_s": t1, "d2d_ensemble_s": t2, "mur_ensemble_s": mur,
            "h2d_seul_go_s": n * reps_h2d / th / 1e9,
            "h2d_ensemble_go_s": n * reps_h2d / t1 / 1e9,
            "d2d_seul_go_s": 2 * n * reps_d2d / td / 1e9,
            "d2d_ensemble_go_s": 2 * n * reps_d2d / t2 / 1e9,
            "part_cachee": (th + td - max(t1, t2)) / min(th, td),
            "lien_seul": lien_seul, "lien_ensemble": lien_ensemble,
        }
        journal["recouvrement"].append(res)
        print(f"recouvrement tour {tour}: H2D seul {res['h2d_seul_go_s']:.2f} -> ensemble {res['h2d_ensemble_go_s']:.2f} Go/s ; "
              f"D2D seul {res['d2d_seul_go_s']:.1f} -> ensemble {res['d2d_ensemble_go_s']:.1f} Go/s ; "
              f"part du plus court cachée {res['part_cachee']:.2f}")

    journal["occupation_fin"] = nvml.occupation()
    journal["echecs"] = echecs
    journal["verdict"] = "INSTRUMENT VALIDE" if not echecs else "TEMOIN TOMBE"
    print(journal["verdict"], *echecs, sep="\n  ")
    if args.sortie:
        os.makedirs(os.path.dirname(args.sortie), exist_ok=True)
        with open(args.sortie, "w", encoding="utf-8") as f:
            json.dump(journal, f, ensure_ascii=False, indent=1)
    return 0 if not echecs else 2


if __name__ == "__main__":
    sys.exit(main())
