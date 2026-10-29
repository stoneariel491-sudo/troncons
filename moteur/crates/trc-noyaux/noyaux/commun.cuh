// Définitions communes aux noyaux de troncons (lot K).
//
// Ce fichier est la traduction, côté carte, de deux coutures gelées de
// decisions/ARCHITECTURE.md :
//   - couture F (§ 4) : la partie de tronçon (§ 4.8) et le flux rANS (§ 4.9) ;
//   - couture N (§ 5.6) : la disposition SoA de l'emplacement d'expert.
// Rien ici ne dépend de l'API d'exécution de CUDA : les noyaux sont chargés par
// l'API du pilote (cuModuleLoadData) depuis l'image embarquée dans le binaire Rust,
// et le banc C++ (banc/banc_k.cu) inclut les mêmes sources, mot pour mot.
//
// Règle de déterminisme (couture N) : aucune addition atomique en virgule
// flottante ; les seuls atomiques sont des compteurs entiers de contrôle.
#pragma once

#include <stdint.h>

namespace trc {

// Constantes du flux rANS (§ 4.9.2).
constexpr uint32_t PROBA_BITS = 12;
constexpr uint32_t M = 1u << PROBA_BITS;  // 4 096 fentes
constexpr uint32_t L = 1u << 16;           // borne basse de l'état
constexpr uint32_t VOIES = 32;

// Magie d'une partie de niveau 0 (« TRC0 », § 4.8).
constexpr uint32_t MAGIE_PARTIE0 = 0x30435254u;

// Sortes de flux (§ 4.10).
constexpr uint8_t SORTE_MEDIANES = 0x01;
constexpr uint8_t SORTE_BIAIS = 0x02;
constexpr uint8_t SORTE_DELTA = 0x03;
constexpr uint8_t SORTE_CODES_CTX = 0x04;
constexpr uint8_t SORTE_CODES_BRUTS = 0x06;
constexpr uint8_t SORTE_ECHELLES_BRUTES = 0x07;

// Cases du tampon de contrôle (u32[4], remis à zéro par l'appelant) :
//   [0] voies qui ne finissent pas sur L (§ 4.9.2) : erreur fatale du flux ;
//   [1] erreurs de format (magie, sorte absente, tailles incohérentes) ;
//   [2] tuiles dont le pointeur de mots final diffère du début de la tuile
//       suivante (contrôle en plus de la spécification, informatif) ;
//   [3] réservé.
constexpr int CTL_HORS_L = 0;
constexpr int CTL_FORMAT = 1;
constexpr int CTL_POINTEUR = 2;

// Dimensions des trois matrices d'un expert (en-tête du fichier, § 4.3).
// Passée par valeur aux noyaux : 24 octets, alignement 4, même disposition que
// `abi::DimsExpert` côté Rust (#[repr(C)]).
struct DimsExpert {
    uint32_t lignes[3];
    uint32_t colonnes[3];
};

__host__ __device__ __forceinline__ uint64_t al256(uint64_t x) { return (x + 255u) & ~uint64_t(255); }

// Disposition SoA d'une matrice dans l'emplacement (§ 5.6) : codes au décalage 0
// (R·B·16 o, ordre β), échelles à al256(R·B·16), biais à al256(al256(R·B·16) + R·B),
// pas de matrice al256(décalage des biais + 4R). Décalages relatifs au début de la
// matrice ; `base` est le début de la matrice dans l'emplacement.
struct Disposition {
    uint64_t base;
    uint64_t echelles;
    uint64_t biais;
    uint64_t pas;
};

__host__ __device__ inline Disposition disposition_matrice(uint32_t lignes, uint32_t colonnes) {
    const uint64_t blocs = uint64_t(lignes) * (colonnes / 32u);
    Disposition d;
    d.base = 0;
    d.echelles = al256(blocs * 16u);
    d.biais = al256(d.echelles + blocs);
    d.pas = al256(d.biais + 4ull * lignes);
    return d;
}

// Élément j (0, 1, 2) d'un tableau de trois, sans indice variable : un indice qui
// dépend de blockIdx forcerait le tableau en mémoire locale (pile de 24 o relevée par
// ptxas dans la première version).
__host__ __device__ __forceinline__ uint32_t choisir(const uint32_t (&a)[3], uint32_t j) {
    return j == 0 ? a[0] : (j == 1 ? a[1] : a[2]);
}

__host__ __device__ inline Disposition disposition(const DimsExpert& dims, uint32_t j) {
    uint64_t base = 0;
#pragma unroll
    for (uint32_t i = 0; i < 3; ++i)
        if (i < j) base += disposition_matrice(dims.lignes[i], dims.colonnes[i]).pas;
    Disposition d = disposition_matrice(choisir(dims.lignes, j), choisir(dims.colonnes, j));
    d.base = base;
    return d;
}

// Lecture petit-boutiste non alignée (l'en-tête de partie et la table des flux sont
// alignés sur 4 en pratique, mais rien ne coûte de le supposer moins).
__device__ __forceinline__ uint32_t lire_u32(const uint8_t* p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}
__device__ __forceinline__ uint32_t lire_u16(const uint8_t* p) { return uint32_t(p[0]) | (uint32_t(p[1]) << 8); }

// Un flux trouvé dans la table des flux d'une partie (§ 4.8).
struct DescFlux {
    const uint8_t* p;    // début du flux (aligné sur 16 dans la partie)
    uint32_t longueur;   // octets du flux
    uint32_t produits;   // octets produits par son décodage (table des flux)
};

// Cherche le flux (sorte, matrice) dans la partie. Faux si la partie n'est pas une
// partie de niveau 0 bien formée ou si le flux est absent. Lu par chaque fil : la
// table tient en 256 octets et reste dans le cache.
__device__ inline bool trouver_flux(const uint8_t* partie, uint8_t sorte, uint32_t matrice, DescFlux& f) {
    if (lire_u32(partie) != MAGIE_PARTIE0) return false;
    if (partie[8] != 0) return false;  // niveau 0 seulement en v1.0
    const uint32_t n_flux = lire_u16(partie + 10);
    const uint32_t utiles = lire_u32(partie + 12);
    if (n_flux > 64 || 64u + 16u * n_flux > utiles) return false;
    for (uint32_t i = 0; i < n_flux; ++i) {
        const uint8_t* e = partie + 64 + 16 * i;
        if (e[0] == sorte && e[1] == matrice) {
            const uint32_t dec = lire_u32(e + 4), lon = lire_u32(e + 8);
            if ((dec & 15u) != 0 || uint64_t(dec) + lon > utiles) return false;
            f.p = partie + dec;
            f.longueur = lon;
            f.produits = lire_u32(e + 12);
            return true;
        }
    }
    return false;
}

// En-tête d'un flux rANS sérialisé (§ 4.9.1), validé.
struct EnteteRans {
    uint32_t P;             // octets produits (multiple de 128, bourrage compris)
    uint32_t N;             // macro-pas par tuile
    uint32_t T;             // tuiles
    uint32_t W;             // mots de 16 bits
    const uint32_t* debut;  // T indices de mot
    const uint32_t* etats;  // 32·T états
    const uint32_t* mots32; // mots lus deux par deux (adresse alignée sur 4)
    uint32_t n32;           // ⌈W / 2⌉
};

// `besoin` : octets utiles attendus. Le flux en produit P ≥ besoin, avec moins de 128
// octets de bourrage ; la table des flux peut annoncer P ou `besoin` (la spécification
// ne tranche pas : voir moteur/REPRISE-K.md).
__device__ inline bool lire_entete(const DescFlux& f, uint32_t geometrie, uint32_t besoin, EnteteRans& h) {
    if (f.longueur < 16) return false;
    h.P = lire_u32(f.p);
    h.N = lire_u16(f.p + 4);
    const uint32_t geo = f.p[6];
    h.T = lire_u32(f.p + 8);
    h.W = lire_u32(f.p + 12);
    if (geo != geometrie || h.N == 0 || (h.P & 127u) != 0) return false;
    if (h.P < besoin || h.P - besoin >= 128u) return false;
    if (f.produits != h.P && f.produits != besoin) return false;
    const uint32_t macro = h.P / 128u;
    if (h.T != (macro + h.N - 1) / h.N) return false;
    const uint64_t fin = 16ull + 132ull * h.T + 2ull * h.W;
    if (fin > f.longueur) return false;
    h.debut = reinterpret_cast<const uint32_t*>(f.p + 16);
    h.etats = reinterpret_cast<const uint32_t*>(f.p + 16 + 4ull * h.T);
    h.mots32 = reinterpret_cast<const uint32_t*>(f.p + 16 + 132ull * h.T);
    h.n32 = (h.W + 1u) / 2u;
    return true;
}

// Mot de 32 bits (deux mots de 16 du flux) d'indice i, borné : au-delà du flux, 0.
// Les fenêtres de lecture d'une tuile débordent de 64 mots de 32 bits au plus ; ce
// garde empêche toute lecture hors de la partie, même sur un flux corrompu.
__device__ __forceinline__ uint32_t mot32(const EnteteRans& h, uint32_t i) {
    return i < h.n32 ? h.mots32[i] : 0u;
}

// Un pas de décodage, géométrie 1 (octet ; § 4.9.2), pour les 32 voies d'un warp à la
// fois. L'entrée de LUT porte s | (f − 1) << 8 | (fente − cumul) << 20. Les voies qui
// renormalisent lisent des mots consécutifs dans l'ordre croissant des voies : la
// position de la voie est le pointeur plus le nombre de voies d'indice inférieur qui
// lisent aussi (vote et comptage de bits). Les mots sont distribués par une fenêtre de
// 64 mots de 32 bits (cour, suiv) tenue une par voie et échangée par __shfl_sync.
// Algorithme de l'étude 03 (outils/03-entropie/cuda/rans_v4.cu, même auteur), la LUT
// étant désormais choisie par la voie.
//
// Fenêtre à trois registres (mesure du 2026-10-15, banc_k, décomposition par événements) :
// avec deux registres (cour, suiv), le mot chargé quand la fenêtre avance sert dès le pas
// suivant, et le warp attend toute la latence d'une lecture globale tous les ≈ 8 pas. Le
// troisième registre (apres) est chargé une fenêtre d'avance : sa valeur ne sert qu'à l'avance
// suivante, ≈ 8 pas plus tard, ce qui couvre la latence.
struct EtatVoie {
    uint32_t x;      // état rANS de la voie
    uint32_t ptr;    // indice (mots de 16) du prochain mot du flux de la tuile
    uint32_t base;   // indice (mots de 32) du premier mot de la fenêtre
    uint32_t cour;   // mot de 32 bits base + voie
    uint32_t suiv;   // mot de 32 bits base + 32 + voie
    uint32_t apres;  // mot de 32 bits base + 64 + voie (lecture d'avance)
};

__device__ __forceinline__ uint32_t pas_octet(EtatVoie& v, const uint32_t* __restrict__ lut,
                                              const EnteteRans& h, uint32_t voie, uint32_t masque_inf) {
    const uint32_t e = lut[v.x & (M - 1u)];
    v.x = (((e >> 8) & 0xFFFu) + 1u) * (v.x >> PROBA_BITS) + (e >> 20);
    const bool besoin = v.x < L;
    const uint32_t vote = __ballot_sync(0xFFFFFFFFu, besoin);
    const uint32_t pos = v.ptr + __popc(vote & masque_inf);
    const uint32_t wi = (pos >> 1) - v.base;  // < 48 : voir la démonstration dans REPRISE-K
    const uint32_t a = __shfl_sync(0xFFFFFFFFu, v.cour, wi & 31u);
    const uint32_t b = __shfl_sync(0xFFFFFFFFu, v.suiv, wi & 31u);
    const uint32_t w32 = wi >= 32u ? b : a;
    const uint32_t w = (w32 >> ((pos & 1u) * 16u)) & 0xFFFFu;
    v.x = besoin ? ((v.x << 16) | w) : v.x;
    v.ptr += __popc(vote);
    if ((v.ptr >> 1) - v.base >= 32u) {
        v.base += 32u;
        v.cour = v.suiv;
        v.suiv = v.apres;
        v.apres = mot32(h, v.base + 64u + voie);
    }
    return e & 0xFFu;
}

__device__ __forceinline__ void debut_tuile(EtatVoie& v, const EnteteRans& h, uint32_t t, uint32_t voie) {
    v.x = h.etats[t * VOIES + voie];
    v.ptr = h.debut[t];
    v.base = v.ptr >> 1;
    v.cour = mot32(h, v.base + voie);
    v.suiv = mot32(h, v.base + 32u + voie);
    v.apres = mot32(h, v.base + 64u + voie);
}

// Somme entière sur le warp (arbre fixe ; entiers, donc exacte et déterministe).
__device__ __forceinline__ uint32_t somme_warp_u32(uint32_t v) {
#pragma unroll
    for (int d = 16; d > 0; d >>= 1) v += __shfl_xor_sync(0xFFFFFFFFu, v, d);
    return v;
}

// Contrôle de fin de tuile : x = L sur chaque voie, et pointeur final égal au début de
// la tuile suivante (ou à W pour la dernière). Le pointeur est le même sur les 32
// voies : seule la voie 0 le compte.
__device__ __forceinline__ void fin_tuile(const EtatVoie& v, const EnteteRans& h, uint32_t t, uint32_t voie,
                                          uint32_t& hors_l, uint32_t& pointeur) {
    hors_l += (v.x != L) ? 1u : 0u;
    const uint32_t attendu = (t + 1 < h.T) ? h.debut[t + 1] : h.W;
    pointeur += (voie == 0 && v.ptr != attendu) ? 1u : 0u;
}

// Verse les compteurs d'un warp dans le tampon de contrôle (un atomique entier par
// warp et par case non nulle).
__device__ __forceinline__ void verser_controle(uint32_t* controle, uint32_t voie, uint32_t hors_l, uint32_t pointeur) {
    hors_l = somme_warp_u32(hors_l);
    pointeur = somme_warp_u32(pointeur);
    if (voie == 0) {
        if (hors_l) atomicAdd(&controle[CTL_HORS_L], hors_l);
        if (pointeur) atomicAdd(&controle[CTL_POINTEUR], pointeur);
    }
}

}  // namespace trc
