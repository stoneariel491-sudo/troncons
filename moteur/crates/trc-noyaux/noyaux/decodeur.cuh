// Étape K1 : le décodeur d'un expert, rANS v4 à table par voie (§ 4.9 et § 4.11 de
// decisions/ARCHITECTURE.md), écrit dans l'emplacement SoA (§ 5.6).
//
// Un expert se décode en deux lancements sur le même flux CUDA, parce que la table de
// CODES_CTX dépend de la classe d'échelle κ, que donne DELTA (« le décodeur décode
// toujours DELTA avant CODES_CTX », § 4.9.3) :
//
//   1. decoder_echelles  grille (X, 3), 128 fils : pour chaque matrice j, décode
//      DELTA_j (table unique), reconstruit e[β] = (méd[r] + δ[β] − 128) mod 256 dans
//      les échelles de l'emplacement, et recopie BIAIS_j dans ses biais ;
//   2. decoder_codes     grille (X, 3), 256 fils, 48 Kio de mémoire partagée : pour
//      chaque matrice j, décode CODES_CTX_j ; la voie qui produit le mot w choisit la
//      table du contexte κ(⌊w/4⌋), recalculé depuis l'échelle déjà écrite et la
//      médiane (δ = (e − méd + 128) mod 256) ; écrit les codes dans l'emplacement.
//
// Les deux noyaux lisent la partie de tronçon telle qu'elle est arrivée par DMA (en-
// tête, table des flux, flux) : l'hôte n'a rien à analyser. Une tuile = un warp ; les
// warps parcourent les tuiles par pas de grille, donc toute grille est juste ; la
// grille conseillée est donnée par l'enveloppe Rust (`abi::grilles_decodeur`).
//
// LUT d'une couche, en VRAM, montées une fois au démarrage : u32[3][4][4096], pour la
// matrice j : [j][0] DELTA, [j][1 + κ] CODES_CTX du contexte κ ; entrée de géométrie 1
// (§ 4.9.2) : s | (f − 1) << 8 | (fente − cumul) << 20. Une table absente du fichier
// (contexte jamais rencontré) est une LUT de zéros, jamais lue par un flux juste.
#pragma once

#include "commun.cuh"

namespace trc {

// Classe d'échelle κ du bloc β (§ 4.9.3), depuis son échelle e et la médiane de sa
// ligne : δ = (e − méd + 128) mod 256 ; κ = 0 si δ < 128, 1 si δ = 128, 2 sinon.
__device__ __forceinline__ uint32_t classe_echelle(uint32_t e, uint32_t med) {
    const uint32_t delta = (e - med + 128u) & 255u;
    return delta < 128u ? 0u : (delta == 128u ? 1u : 2u);
}

}  // namespace trc

// --- 1. DELTA → échelles ; BIAIS → biais -----------------------------------------
// Corps commun à decoder_echelles (un expert) et decoder_echelles_lot (un expert par valeur de
// blockIdx.z) : les deux noyaux rendent donc les mêmes octets.
namespace trc {
__device__ __forceinline__ void corps_echelles(const uint8_t* __restrict__ partie, uint8_t* __restrict__ emplacement,
                                               const uint32_t* __restrict__ luts, const DimsExpert& dims,
                                               uint32_t* __restrict__ controle, uint32_t* lut, uint8_t* med_partagee) {
    const uint32_t j = blockIdx.y;
    const uint32_t* src = luts + (uint64_t(j) * 4u + 0u) * M;
    for (uint32_t i = threadIdx.x; i < M; i += blockDim.x) lut[i] = src[i];
    __syncthreads();

    const uint32_t voie = threadIdx.x & 31u;
    const uint32_t R = choisir(dims.lignes, j), C = choisir(dims.colonnes, j);
    const uint32_t B = C / 32u, nblocs = R * B;
    DescFlux fd, fm, fb;
    EnteteRans h;
    const bool bon = (C % 32u == 0) && B > 0 && R > 0 &&
                     trouver_flux(partie, SORTE_DELTA, j, fd) && trouver_flux(partie, SORTE_MEDIANES, j, fm) &&
                     trouver_flux(partie, SORTE_BIAIS, j, fb) && fm.produits == R && fm.longueur >= R &&
                     fb.produits == 4u * R && fb.longueur >= 4u * R && lire_entete(fd, 1, nblocs, h);
    if (!bon) {
        if (threadIdx.x == 0) atomicAdd(&controle[CTL_FORMAT], 1u);
        return;
    }
    const Disposition disp = disposition(dims, j);
    uint8_t* mat = emplacement + disp.base;

    // Biais : recopie bit à bit (en u32, pour qu'aucune conversion ne touche un NaN).
    {
        const uint32_t* bs = reinterpret_cast<const uint32_t*>(fb.p);
        uint32_t* bd = reinterpret_cast<uint32_t*>(mat + disp.biais);
        for (uint32_t i = blockIdx.x * blockDim.x + threadIdx.x; i < R; i += gridDim.x * blockDim.x) bd[i] = bs[i];
    }

    // Médianes de la matrice en mémoire partagée (R ≤ 8 192, soit 2 880 o pour gpt-oss) : une
    // lecture globale par macro-pas bloquait le warp toute sa latence (mesure du 2026-10-15).
    const uint8_t* med = fm.p;
    if (R <= 8192u) {
        for (uint32_t i = threadIdx.x; i < R; i += blockDim.x) med_partagee[i] = fm.p[i];
        med = med_partagee;
    }
    __syncthreads();

    uint8_t* ech = mat + disp.echelles;
    const uint32_t warp = blockIdx.x * (blockDim.x >> 5) + (threadIdx.x >> 5);
    const uint32_t nwarps = gridDim.x * (blockDim.x >> 5);
    const uint32_t nmacro = h.P / 128u;
    const uint32_t masque_inf = (1u << voie) - 1u;
    uint32_t hors_l = 0, pointeur = 0;
    for (uint32_t t = warp; t < h.T; t += nwarps) {
        EtatVoie v;
        debut_tuile(v, h, t, voie);
        const uint32_t m1 = min(t * h.N + h.N, nmacro);
        // Le mot w = m · 32 + voie porte δ des blocs b0 = 4w .. 4w + 3 ; ligne et reste de b0
        // suivis sans division (b0 avance de 128 par macro-pas).
        uint32_t b0 = 4u * (t * h.N * VOIES + voie);
        uint32_t ligne = b0 / B, reste = b0 - ligne * B;
        for (uint32_t m = t * h.N; m < m1; ++m) {
            uint32_t mot = 0;
#pragma unroll
            for (uint32_t k = 0; k < 4; ++k) mot |= pas_octet(v, lut, h, voie, masque_inf) << (8u * k);
            // e = (méd[r] + δ − 128) mod 256.
            uint32_t sortie = 0;
#pragma unroll
            for (uint32_t k = 0; k < 4; ++k) {
                uint32_t rk = ligne, qk = reste + k;
                while (qk >= B) { qk -= B; ++rk; }  // au plus une fois dès que B ≥ 4
                const uint32_t mk = rk < R ? uint32_t(med[rk]) : 0u;
                sortie |= ((mk + ((mot >> (8u * k)) & 255u) - 128u) & 255u) << (8u * k);
            }
            if (b0 + 3u < nblocs) {
                reinterpret_cast<uint32_t*>(ech)[b0 >> 2] = sortie;  // ech aligné sur 256
            } else {
                for (uint32_t k = 0; k < 4; ++k)
                    if (b0 + k < nblocs) ech[b0 + k] = uint8_t(sortie >> (8u * k));
            }
            b0 += 4u * VOIES;
            reste += 4u * VOIES;
            while (reste >= B) { reste -= B; ++ligne; }
        }
        fin_tuile(v, h, t, voie, hors_l, pointeur);
    }
    verser_controle(controle, voie, hors_l, pointeur);
}
}  // namespace trc

extern "C" __global__ void __launch_bounds__(128)
decoder_echelles(const uint8_t* __restrict__ partie, uint8_t* __restrict__ emplacement,
                 const uint32_t* __restrict__ luts, trc::DimsExpert dims, uint32_t* __restrict__ controle) {
    __shared__ uint32_t lut[trc::M];
    __shared__ uint8_t med_partagee[8192];
    trc::corps_echelles(partie, emplacement, luts, dims, controle, lut, med_partagee);
}

// --- 2. CODES_CTX → codes, table choisie par voie ----------------------------------
namespace trc {
__device__ __forceinline__ void corps_codes(const uint8_t* __restrict__ partie, uint8_t* __restrict__ emplacement,
                                            const uint32_t* __restrict__ luts, const DimsExpert& dims,
                                            uint32_t* __restrict__ controle, uint32_t (*lut)[M]) {
    const uint32_t j = blockIdx.y;
    {
        const uint32_t* src = luts + (uint64_t(j) * 4u + 1u) * M;
        uint32_t* dst = &lut[0][0];
        for (uint32_t i = threadIdx.x; i < 3u * M; i += blockDim.x) dst[i] = src[i];
    }
    __syncthreads();

    const uint32_t voie = threadIdx.x & 31u;
    const uint32_t R = choisir(dims.lignes, j), C = choisir(dims.colonnes, j);
    const uint32_t B = C / 32u, nblocs = R * B;
    DescFlux fc, fm;
    EnteteRans h;
    const bool bon = (C % 32u == 0) && B > 0 && R > 0 &&
                     trouver_flux(partie, SORTE_CODES_CTX, j, fc) && trouver_flux(partie, SORTE_MEDIANES, j, fm) &&
                     fm.produits == R && fm.longueur >= R && lire_entete(fc, 1, nblocs * 16u, h);
    if (!bon) {
        if (threadIdx.x == 0) atomicAdd(&controle[CTL_FORMAT], 1u);
        return;
    }
    const Disposition disp = disposition(dims, j);
    uint8_t* mat = emplacement + disp.base;
    uint32_t* codes = reinterpret_cast<uint32_t*>(mat);
    const uint8_t* __restrict__ ech = mat + disp.echelles;  // écrites par decoder_echelles
    const uint8_t* __restrict__ med = fm.p;

    const uint32_t warp = blockIdx.x * (blockDim.x >> 5) + (threadIdx.x >> 5);
    const uint32_t nwarps = gridDim.x * (blockDim.x >> 5);
    const uint32_t nmacro = h.P / 128u;
    const uint32_t mots_utiles = nblocs * 4u;
    const uint32_t masque_inf = (1u << voie) - 1u;
    uint32_t hors_l = 0, pointeur = 0;
    for (uint32_t t = warp; t < h.T; t += nwarps) {
        EtatVoie v;
        debut_tuile(v, h, t, voie);
        const uint32_t m1 = min(t * h.N + h.N, nmacro);
        // Le mot w = m · 32 + voie appartient au bloc ⌊w/4⌋ = 8m + ⌊voie/4⌋ (16 octets = 4 mots).
        // Son contexte demande l'échelle du bloc et la médiane de sa ligne : deux lectures
        // globales, faites un macro-pas d'avance pour que leur latence se cache derrière les
        // quatre pas rANS du macro-pas courant (mesure du 2026-10-15). Ligne et reste suivis
        // sans division (le bloc avance de 8 par macro-pas).
        uint32_t bloc = (t * h.N * VOIES + voie) >> 2;
        uint32_t ligne = bloc / B, reste = bloc - ligne * B;
        bool valide = bloc < nblocs;
        uint32_t e_suiv = valide ? __ldg(ech + bloc) : 0u;
        uint32_t m_suiv = valide ? __ldg(med + ligne) : 0u;
        for (uint32_t m = t * h.N; m < m1; ++m) {
            // Au-delà des blocs réels (bourrage du flux), contexte 0 : cas que la
            // spécification ne dit pas (REPRISE-K), sans objet pour gpt-oss.
            const uint32_t ctx = valide ? classe_echelle(e_suiv, m_suiv) : 0u;
            const uint32_t w = m * VOIES + voie;
            bloc += 8u;
            reste += 8u;
            while (reste >= B) { reste -= B; ++ligne; }
            valide = (m + 1u < m1) && bloc < nblocs;
            if (valide) {
                e_suiv = __ldg(ech + bloc);
                m_suiv = __ldg(med + ligne);
            }
            const uint32_t* lt = lut[ctx];
            uint32_t mot = 0;
#pragma unroll
            for (uint32_t k = 0; k < 4; ++k) mot |= pas_octet(v, lt, h, voie, masque_inf) << (8u * k);
            if (w < mots_utiles) codes[w] = mot;
        }
        fin_tuile(v, h, t, voie, hors_l, pointeur);
    }
    verser_controle(controle, voie, hors_l, pointeur);
}

// Un expert d'un lot de décodage (32 octets ; même disposition que `abi::DescDecodage`).
// Chaque expert porte ses LUT : un lot peut mêler des couches (préchargement, J1+).
struct DescDecodage {
    uint64_t partie;
    uint64_t emplacement;
    uint64_t luts;
    uint64_t controle;
};
}  // namespace trc

extern "C" __global__ void __launch_bounds__(256)
decoder_codes(const uint8_t* __restrict__ partie, uint8_t* __restrict__ emplacement,
              const uint32_t* __restrict__ luts, trc::DimsExpert dims, uint32_t* __restrict__ controle) {
    __shared__ uint32_t lut[3][trc::M];  // 48 Kio : les trois contextes de la matrice
    trc::corps_codes(partie, emplacement, luts, dims, controle, lut);
}

// --- Lots : n experts de mêmes dimensions en un lancement par noyau ------------------
// Grilles (X, 3, n) : blockIdx.z désigne l'expert. Extension de la couture N (§ 6.2 : fonction
// ajoutée, rien d'existant changé). Raison (mesure du 2026-10-15, REPRISE-K) : un expert seul
// n'occupe qu'un warp par tuile de DELTA (24 warps pour toute la carte) puis une vague de 381
// warps ; le lot fait tourner les DELTA de n experts ensemble.
extern "C" __global__ void __launch_bounds__(128)
decoder_echelles_lot(const trc::DescDecodage* __restrict__ descs, trc::DimsExpert dims) {
    __shared__ uint32_t lut[trc::M];
    __shared__ uint8_t med_partagee[8192];
    const trc::DescDecodage d = descs[blockIdx.z];
    trc::corps_echelles(reinterpret_cast<const uint8_t*>(d.partie), reinterpret_cast<uint8_t*>(d.emplacement),
                        reinterpret_cast<const uint32_t*>(d.luts), dims, reinterpret_cast<uint32_t*>(d.controle), lut,
                        med_partagee);
}

extern "C" __global__ void __launch_bounds__(256)
decoder_codes_lot(const trc::DescDecodage* __restrict__ descs, trc::DimsExpert dims) {
    __shared__ uint32_t lut[3][trc::M];
    const trc::DescDecodage d = descs[blockIdx.z];
    trc::corps_codes(reinterpret_cast<const uint8_t*>(d.partie), reinterpret_cast<uint8_t*>(d.emplacement),
                     reinterpret_cast<const uint32_t*>(d.luts), dims, reinterpret_cast<uint32_t*>(d.controle), lut);
}

// --- Chemin brut (fichier brut, drapeau bit 2 ; témoin C3) -------------------------
// ECHELLES_BRUTES_j, CODES_BRUTS_j, BIAIS_j recopiés dans l'emplacement. Grille (X, 3).
extern "C" __global__ void __launch_bounds__(256)
copier_brut(const uint8_t* __restrict__ partie, uint8_t* __restrict__ emplacement, trc::DimsExpert dims,
            uint32_t* __restrict__ controle) {
    using namespace trc;
    const uint32_t j = blockIdx.y;
    const uint32_t R = choisir(dims.lignes, j), C = choisir(dims.colonnes, j);
    const uint32_t B = C / 32u, nblocs = R * B;
    DescFlux fe, fc, fb;
    const bool bon = (C % 32u == 0) && B > 0 && R > 0 &&
                     trouver_flux(partie, SORTE_ECHELLES_BRUTES, j, fe) &&
                     trouver_flux(partie, SORTE_CODES_BRUTS, j, fc) && trouver_flux(partie, SORTE_BIAIS, j, fb) &&
                     fe.produits == nblocs && fe.longueur >= nblocs && fc.produits == 16u * nblocs &&
                     fc.longueur >= 16u * nblocs && fb.produits == 4u * R && fb.longueur >= 4u * R;
    if (!bon) {
        if (threadIdx.x == 0) atomicAdd(&controle[CTL_FORMAT], 1u);
        return;
    }
    const Disposition disp = disposition(dims, j);
    uint8_t* mat = emplacement + disp.base;
    const uint32_t i0 = blockIdx.x * blockDim.x + threadIdx.x, pas = gridDim.x * blockDim.x;
    const uint4* cs = reinterpret_cast<const uint4*>(fc.p);
    uint4* cd = reinterpret_cast<uint4*>(mat);
    for (uint32_t i = i0; i < nblocs; i += pas) cd[i] = cs[i];
    for (uint32_t i = i0; i < nblocs; i += pas) mat[disp.echelles + i] = fe.p[i];
    const uint32_t* bs = reinterpret_cast<const uint32_t*>(fb.p);
    uint32_t* bd = reinterpret_cast<uint32_t*>(mat + disp.biais);
    for (uint32_t i = i0; i < R; i += pas) bd[i] = bs[i];
}
