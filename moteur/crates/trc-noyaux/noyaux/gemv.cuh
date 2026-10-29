// Étape K2 : produit matrice-vecteur MXFP4, y = W x + b, sur l'emplacement SoA
// (§ 5.6 de decisions/ARCHITECTURE.md).
//
// Valeur d'un poids : k[code] · 2^(e − 128), k = {0, 1, 2, 3, 4, 6, 8, 12} signé par le
// bit 3 (grandeurs E2M1 doublées ; E8M0 vaut 2^(e − 127), d'où le −128). L'octet i d'un
// bloc porte le poids i (demi-octet bas) et le poids 16 + i (haut) : disposition de
// block_mxfp4 de ggml, redérivée par l'étude 03 (gemv.wgsl) et reprise telle quelle.
//
// Découpage : un warp traite 4 lignes ; la voie l prend les blocs b = l, l + 32,
// l + 64, … de ces lignes, charge une fois les 32 x d'un bloc et les applique aux 4
// lignes (recette du produit brut de l'étude 03, 209 Go/s sous Vulkan). Un bloc de 256
// fils = 8 warps = 32 lignes.
//
// Déterminisme (couture N) : l'ordre des opérations ne dépend que de C (la voie qui
// prend un bloc, l'ordre des blocs d'une voie, l'arbre de réduction papillon sur 32
// voies). Les deux noyaux (`gemv_mxfp4`, `gemv_mxfp4_lot`) partagent la même fonction et
// rendent donc les mêmes bits, quelle que soit la grille. Aucune addition atomique.
// Pas de --use_fast_math : les échelles 2^-127 et 2^-128 sont des sous-normaux exacts.
#pragma once

#include "commun.cuh"

namespace trc {

// 2^(e − 128) en f32, exact pour tout e de 0 à 255 (e = 0 et 1 : sous-normaux).
__device__ __forceinline__ float echelle_e8m0(uint32_t e) {
    const uint32_t bits = e >= 2u ? (e - 1u) << 23 : (0x00200000u << e);
    return __uint_as_float(bits);
}

// Grandeur doublée d'un code E2M1 de 4 bits : les huit grandeurs sont rangées par
// demi-octet dans 0xC8643210 ; le bit 3 est le signe.
__device__ __forceinline__ float valeur_e2m1x2(uint32_t c) {
    const float g = float((0xC8643210u >> ((c & 7u) << 2)) & 15u);
    return (c & 8u) ? -g : g;
}

// Lecteur des valeurs du mode exact : les grandeurs E2M1 doublées.
struct ValeurE2M1 {
    __device__ __forceinline__ float operator()(uint32_t c) const { return valeur_e2m1x2(c); }
};

// Lecteur des valeurs du mode rapide (lot B, génome synonyme ; genome/07-genome-synonyme.md) :
// le demi-octet est un symbole de base, bit 3 le signe, bits 0 et 1 la classe k, bit 2 nul ; sa
// grandeur doublée est le centre c_k du fichier (table CENTRES, en grandeurs doublées). Même
// décodeur, autre table de valeurs ; le choix par sélections évite toute lecture indexée.
struct ValeurBase {
    float c0, c1, c2, c3;
    __device__ __forceinline__ float operator()(uint32_t c) const {
        const uint32_t k = c & 3u;
        const float g = k == 0u ? c0 : (k == 1u ? c1 : (k == 2u ? c2 : c3));
        return (c & 8u) ? -g : g;
    }
};

// Contribution d'un bloc : Σ_i k[code_i] · x_i, dans un ordre fixe (mot t = 0..3,
// octet k = 0..3, demi-octet bas puis haut). xs[0..3] = x[0..15], xs[4..7] = x[16..31].
// Le lecteur des valeurs est un paramètre : l'ordre des opérations ne dépend pas de lui, et le
// mode exact (ValeurE2M1) fait exactement les mêmes fmaf qu'avant l'ajout du mode rapide.
template <typename V>
__device__ __forceinline__ float produit_bloc(const uint4 q, const float4 (&xs)[8], const V val) {
    const uint32_t mots[4] = {q.x, q.y, q.z, q.w};
    float s = 0.0f;
#pragma unroll
    for (int t = 0; t < 4; ++t) {
        const uint32_t w = mots[t];
        const float xa[4] = {xs[t].x, xs[t].y, xs[t].z, xs[t].w};
        const float xb[4] = {xs[4 + t].x, xs[4 + t].y, xs[4 + t].z, xs[4 + t].w};
#pragma unroll
        for (int k = 0; k < 4; ++k) {
            s = fmaf(val((w >> (8 * k)) & 15u), xa[k], s);
            s = fmaf(val((w >> (8 * k + 4)) & 15u), xb[k], s);
        }
    }
    return s;
}

__device__ __forceinline__ float somme_warp_f32(float v) {
#pragma unroll
    for (int d = 16; d > 0; d >>= 1) v += __shfl_xor_sync(0xFFFFFFFFu, v, d);
    return v;
}

constexpr uint32_t GEMV_LIGNES_PAR_WARP = 4;
constexpr uint32_t GEMV_FILS = 256;
constexpr uint32_t GEMV_LIGNES_PAR_BLOC = GEMV_LIGNES_PAR_WARP * (GEMV_FILS / 32);  // 32

// Les 4 lignes r0 .. r0 + 3 d'une matrice (R lignes, C colonnes) dont `mat` est le
// début dans l'emplacement. Appelée par un warp entier (toutes les voies actives).
template <typename V = ValeurE2M1>
__device__ __forceinline__ void gemv_4_lignes(const uint8_t* __restrict__ mat, const float* __restrict__ x,
                                              float* __restrict__ y, uint32_t R, uint32_t C, uint32_t r0,
                                              uint32_t voie, const V val = V{}) {
    const uint32_t B = C / 32u;
    const Disposition d = disposition_matrice(R, C);
    const uint4* codes = reinterpret_cast<const uint4*>(mat);
    const uint8_t* ech = mat + d.echelles;
    const float* biais = reinterpret_cast<const float*>(mat + d.biais);
    const float4* x4 = reinterpret_cast<const float4*>(x);
    float acc[GEMV_LIGNES_PAR_WARP] = {0.0f, 0.0f, 0.0f, 0.0f};
    // Lignes hors de la matrice : lues comme la dernière (adresse valide), jamais écrites.
    uint32_t lig[GEMV_LIGNES_PAR_WARP];
#pragma unroll
    for (uint32_t i = 0; i < GEMV_LIGNES_PAR_WARP; ++i) lig[i] = min(r0 + i, R - 1u);
    for (uint32_t b = voie; b < B; b += 32u) {
        float4 xs[8];
#pragma unroll
        for (int k = 0; k < 8; ++k) xs[k] = __ldg(x4 + b * 8u + k);
        uint4 q[GEMV_LIGNES_PAR_WARP];
        uint32_t e[GEMV_LIGNES_PAR_WARP];
#pragma unroll
        for (uint32_t i = 0; i < GEMV_LIGNES_PAR_WARP; ++i) {
            const uint64_t beta = uint64_t(lig[i]) * B + b;
            q[i] = __ldcs(codes + beta);  // lecture en flux : les poids ne resservent pas
            e[i] = __ldcs(ech + beta);
        }
#pragma unroll
        for (uint32_t i = 0; i < GEMV_LIGNES_PAR_WARP; ++i)
            acc[i] = fmaf(echelle_e8m0(e[i]), produit_bloc(q[i], xs, val), acc[i]);
    }
#pragma unroll
    for (uint32_t i = 0; i < GEMV_LIGNES_PAR_WARP; ++i) {
        const float s = somme_warp_f32(acc[i]);
        if (voie == 0 && r0 + i < R) y[r0 + i] = s + biais[r0 + i];
    }
}

// Descripteur d'un produit du lot (32 octets ; même disposition que `abi::DescGemv`).
struct DescGemv {
    uint64_t matrice;  // adresse de la matrice dans l'emplacement (codes au décalage 0)
    uint64_t x;        // f32[C]
    uint64_t y;        // f32[R]
    uint32_t lignes;
    uint32_t colonnes;
};

}  // namespace trc

// y = W x + b pour une matrice. Grille : ⌈R / 32⌉ blocs de 256 fils.
extern "C" __global__ void __launch_bounds__(256)
gemv_mxfp4(const uint8_t* __restrict__ matrice, const float* __restrict__ x, float* __restrict__ y, uint32_t R,
           uint32_t C) {
    using namespace trc;
    const uint32_t voie = threadIdx.x & 31u;
    const uint32_t r0 = (blockIdx.x * (GEMV_FILS / 32u) + (threadIdx.x >> 5)) * GEMV_LIGNES_PAR_WARP;
    if (r0 >= R || C % 32u != 0) return;
    gemv_4_lignes(matrice, x, y, R, C, r0, voie);
}

// Lot de produits indépendants (par exemple les 12 matrices des 4 experts d'une
// couche) en un lancement. Grille : (⌈R_max / 32⌉, n_desc) blocs de 256 fils.
extern "C" __global__ void __launch_bounds__(256)
gemv_mxfp4_lot(const trc::DescGemv* __restrict__ descs) {
    using namespace trc;
    const DescGemv dsc = descs[blockIdx.y];
    const uint32_t voie = threadIdx.x & 31u;
    const uint32_t r0 = (blockIdx.x * (GEMV_FILS / 32u) + (threadIdx.x >> 5)) * GEMV_LIGNES_PAR_WARP;
    if (r0 >= dsc.lignes || dsc.colonnes % 32u != 0) return;
    gemv_4_lignes(reinterpret_cast<const uint8_t*>(dsc.matrice), reinterpret_cast<const float*>(dsc.x),
                  reinterpret_cast<float*>(dsc.y), dsc.lignes, dsc.colonnes, r0, voie);
}

// Mode rapide (lot B) : y = Ŵ x + b, Ŵ la base synonyme servie par les centres c0..c3 (grandeurs
// doublées). Même découpage, même ordre des opérations, même grille que gemv_mxfp4.
extern "C" __global__ void __launch_bounds__(256)
gemv_base(const uint8_t* __restrict__ matrice, const float* __restrict__ x, float* __restrict__ y, uint32_t R,
          uint32_t C, float c0, float c1, float c2, float c3) {
    using namespace trc;
    const uint32_t voie = threadIdx.x & 31u;
    const uint32_t r0 = (blockIdx.x * (GEMV_FILS / 32u) + (threadIdx.x >> 5)) * GEMV_LIGNES_PAR_WARP;
    if (r0 >= R || C % 32u != 0) return;
    gemv_4_lignes(matrice, x, y, R, C, r0, voie, ValeurBase{c0, c1, c2, c3});
}
