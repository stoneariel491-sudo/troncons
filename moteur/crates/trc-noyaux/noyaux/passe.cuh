// Étape K3 : les noyaux de la passe avant de gpt-oss (§ 5.6 de decisions/ARCHITECTURE.md),
// en plus du décodeur (K1, decodeur.cuh) et de la GEMV MXFP4 (K2, gemv.cuh).
//
// Formes du calcul (celles de trc-reference, lot R, qui les a écrites depuis la définition
// publiée par OpenAI et validées contre llama.cpp, R1) :
//
//   x ← enchâssement[jeton]                                   ligne_q8_0
//   pour chaque couche ℓ :
//     h ← RMSNorm(x)·w_attn                                    rmsnorm
//     q, k, v ← h Wqᵀ + bq, h Wkᵀ + bk, h Wvᵀ + bv             gemv_q8_0 (biais)
//     q, k ← RoPE-YaRN(q, k, position)                         rope_yarn
//     cache ← k, v en f16                                      ecrire_kv
//     a ← attention(q, K, V), puits par tête, fenêtre 128      attention
//     x ← x + (a Woᵀ + bo)                                     gemv_q8_0 (biais), combiner (n = 1)
//     h ← RMSNorm(x)·w_post ; r ← h Wrᵀ + br                   rmsnorm, gemv_f32 (biais)
//     (i, g) ← top-4(r), softmax des 4                         routeur_topk
//     s_j ← (SwiGLU(h W_gate,jᵀ + b, h W_up,jᵀ + b)) W_down,jᵀ + b   gemv_mxfp4, swiglu_oai
//     x ← x + (((g₀s₀ + g₁s₁) + g₂s₂) + g₃s₃)                 combiner
//   logits ← RMSNorm(x)·w_sortie Woutᵀ                         rmsnorm, gemv_q8_0
//   jeton ← argmax(logits)                                      argmax
//
// Précision. Les produits matrice-vecteur (la quasi-totalité des octets) sont en f32, comme
// tout moteur ; les opérations sur un seul vecteur (normes, rotation, SwiGLU, softmax du routeur)
// sont faites en f64 sur la carte et arrondies une fois en f32 : leur coût est nul devant le
// disque (07 § 1.7), et chaque arrondi évité rapproche le moteur de la référence f64 (critère C4).
// L'attention garde ses produits scalaires et ses sommes en f32 (seuil 10⁻⁵).
//
// Déterminisme (couture N) : aucune addition atomique ; toute réduction suit un arbre fixe qui
// ne dépend que des tailles (pas de la grille, ni de l'ordre d'exécution des blocs).
// Pas de --use_fast_math : expf, sqrt, sin et cos gardent leur précision documentée.
#pragma once

#include <cuda_fp16.h>

#include "commun.cuh"
#include "gemv.cuh"

namespace trc {

// ------------------------------------------------------------------ outils communs

// f16 (bits) → f32, exact.
__device__ __forceinline__ float f16_vers_f32(uint32_t bits) {
    return __half2float(__ushort_as_half(static_cast<unsigned short>(bits)));
}

// Octets d'un bloc Q8_0 (ggml) : f16 d, puis 32 × i8.
constexpr uint32_t Q8_OCTETS_BLOC = 34;

// ------------------------------------------------------------------ gemv_q8_0

// Les 4 lignes r0 .. r0 + 3 de y = W x (+ b) pour une matrice Q8_0 (R lignes, C colonnes, lignes
// contiguës de C/32 blocs de 34 o, disposition ggml). Appelée par un warp entier.
// Ordre fixe : la voie l prend les blocs b = l, l + 32, … ; dans un bloc, s = Σ_i q_i · x_i pour
// i = 0..31 (une chaîne de fmaf), puis acc ← fmaf(d, s, acc) ; réduction papillon sur 32 voies.
// Les adresses de bloc sont paires (34 · b, lignes de 34 · C/32 o) : lecture par mots de 16 bits.
__device__ __forceinline__ void gemv_q8_0_4_lignes(const uint8_t* __restrict__ W, const float* __restrict__ x,
                                                   const float* __restrict__ biais, float* __restrict__ y,
                                                   uint32_t R, uint32_t C, uint32_t r0, uint32_t voie) {
    const uint32_t B = C / 32u;
    const uint64_t octets_ligne = uint64_t(B) * Q8_OCTETS_BLOC;
    const float4* x4 = reinterpret_cast<const float4*>(x);
    float acc[GEMV_LIGNES_PAR_WARP] = {0.0f, 0.0f, 0.0f, 0.0f};
    uint32_t lig[GEMV_LIGNES_PAR_WARP];
#pragma unroll
    for (uint32_t i = 0; i < GEMV_LIGNES_PAR_WARP; ++i) lig[i] = min(r0 + i, R - 1u);
    for (uint32_t b = voie; b < B; b += 32u) {
        float xv[32];
#pragma unroll
        for (int k = 0; k < 8; ++k) {
            const float4 t = __ldg(x4 + b * 8u + k);
            xv[4 * k] = t.x;
            xv[4 * k + 1] = t.y;
            xv[4 * k + 2] = t.z;
            xv[4 * k + 3] = t.w;
        }
#pragma unroll
        for (uint32_t i = 0; i < GEMV_LIGNES_PAR_WARP; ++i) {
            const unsigned short* blk =
                reinterpret_cast<const unsigned short*>(W + uint64_t(lig[i]) * octets_ligne + uint64_t(b) * Q8_OCTETS_BLOC);
            const float d = f16_vers_f32(__ldcs(blk));
            float s = 0.0f;
#pragma unroll
            for (int t = 0; t < 16; ++t) {
                const uint32_t w = __ldcs(blk + 1 + t);
                s = fmaf(float(int8_t(w & 0xFFu)), xv[2 * t], s);
                s = fmaf(float(int8_t(w >> 8)), xv[2 * t + 1], s);
            }
            acc[i] = fmaf(d, s, acc[i]);
        }
    }
#pragma unroll
    for (uint32_t i = 0; i < GEMV_LIGNES_PAR_WARP; ++i) {
        const float s = somme_warp_f32(acc[i]);
        if (voie == 0 && r0 + i < R) y[r0 + i] = biais != nullptr ? s + biais[r0 + i] : s;
    }
}

// ------------------------------------------------------------------ gemv_f32

// Les 4 lignes r0 .. r0 + 3 de y = W x (+ b), W en f32 (lignes contiguës de C flottants, C
// multiple de 4, début aligné sur 16). Ordre fixe : la voie l prend les quadruplets c = l, l + 32,
// … ; dans un quadruplet, x, y, z, w ; réduction papillon.
__device__ __forceinline__ void gemv_f32_4_lignes(const float* __restrict__ W, const float* __restrict__ x,
                                                  const float* __restrict__ biais, float* __restrict__ y,
                                                  uint32_t R, uint32_t C, uint32_t r0, uint32_t voie) {
    const uint32_t C4 = C / 4u;
    const float4* x4 = reinterpret_cast<const float4*>(x);
    const float4* W4 = reinterpret_cast<const float4*>(W);
    float acc[GEMV_LIGNES_PAR_WARP] = {0.0f, 0.0f, 0.0f, 0.0f};
    uint32_t lig[GEMV_LIGNES_PAR_WARP];
#pragma unroll
    for (uint32_t i = 0; i < GEMV_LIGNES_PAR_WARP; ++i) lig[i] = min(r0 + i, R - 1u);
    for (uint32_t c = voie; c < C4; c += 32u) {
        const float4 xv = __ldg(x4 + c);
#pragma unroll
        for (uint32_t i = 0; i < GEMV_LIGNES_PAR_WARP; ++i) {
            const float4 w = __ldcs(W4 + uint64_t(lig[i]) * C4 + c);
            acc[i] = fmaf(w.x, xv.x, acc[i]);
            acc[i] = fmaf(w.y, xv.y, acc[i]);
            acc[i] = fmaf(w.z, xv.z, acc[i]);
            acc[i] = fmaf(w.w, xv.w, acc[i]);
        }
    }
#pragma unroll
    for (uint32_t i = 0; i < GEMV_LIGNES_PAR_WARP; ++i) {
        const float s = somme_warp_f32(acc[i]);
        if (voie == 0 && r0 + i < R) y[r0 + i] = biais != nullptr ? s + biais[r0 + i] : s;
    }
}

// ------------------------------------------------------------------ rope_yarn

// Paramètres de YaRN (48 o, alignement 8 ; même disposition que `abi::ParamsRope`).
struct ParamsRope {
    double base;         // θ (150 000)
    double facteur;      // s (32)
    double ctx_origine;  // L0 (4 096)
    double beta_rapide;  // 32
    double beta_lent;    // 1
    uint32_t dim_tete;   // d (64)
    uint32_t variante;   // 0 : OpenAI (bornes réelles, le modèle) ; 1 : llama.cpp (bornes arrondies)
};

// inv_freq de la paire i et facteur de concentration, en f64 (définition : trc-reference,
// ops::Rope::yarn, depuis la configuration publiée de gpt-oss).
__device__ inline double inv_freq_yarn(const ParamsRope& p, uint32_t i, double& concentration) {
    const uint32_t demi = p.dim_tete / 2u;
    const double freq = pow(p.base, double(2u * i) / double(p.dim_tete));
    if (p.facteur <= 1.0) {
        concentration = 1.0;
        return 1.0 / freq;
    }
    concentration = 0.1 * log(p.facteur) + 1.0;
    const double deux_pi = 6.283185307179586476925286766559;
    double bas = double(demi) * log(p.ctx_origine / (p.beta_rapide * deux_pi)) / log(p.base);
    double haut = double(demi) * log(p.ctx_origine / (p.beta_lent * deux_pi)) / log(p.base);
    if (p.variante == 1u) {
        bas = fmax(floor(bas), 0.0);
        haut = fmin(ceil(haut), double(p.dim_tete - 1u));
    }
    const double interpolation = 1.0 / (p.facteur * freq);
    const double extrapolation = 1.0 / freq;
    const double rampe = fmin(fmax((double(i) - bas) / (haut - bas), 0.0), 1.0);
    const double masque = 1.0 - rampe;
    return interpolation * (1.0 - masque) + extrapolation * masque;
}

// ------------------------------------------------------------------ attention

// Paramètres de l'attention d'une position (32 o ; même disposition que `abi::ParamsAttention`).
struct ParamsAttention {
    uint32_t tetes;     // têtes de requête (64)
    uint32_t tetes_kv;  // têtes de clé et de valeur (8)
    uint32_t dim_tete;  // 64 (seule valeur admise)
    uint32_t debut;     // première position lue (incluse)
    uint32_t fin;       // dernière position lue + 1 (= position courante + 1)
    uint32_t anneau;    // 0 : cache plein (case = position) ; sinon case = position mod anneau
    float echelle;      // 1/√d
    uint32_t reserve;   // 0
};

constexpr uint32_t ATTENTION_FILS = 256;
constexpr uint32_t ATTENTION_DIM = 64;

// Arbre fixe de réduction sur ATTENTION_FILS valeurs en mémoire partagée (max ou somme).
template <bool MAX>
__device__ __forceinline__ float reduire_bloc(float* part, float v) {
    const uint32_t t = threadIdx.x;
    part[t] = v;
    __syncthreads();
#pragma unroll
    for (uint32_t k = ATTENTION_FILS / 2; k > 0; k >>= 1) {
        if (t < k) part[t] = MAX ? fmaxf(part[t], part[t + k]) : part[t] + part[t + k];
        __syncthreads();
    }
    const float r = part[0];
    __syncthreads();
    return r;
}

// Meilleur de deux (valeur, indice) : plus grande valeur, puis plus petit indice. Ordre total sur
// les valeurs non NaN : le résultat d'une réduction ne dépend pas de l'arbre. Un NaN n'est jamais
// meilleur.
__device__ __forceinline__ bool meilleur(float va, uint32_t ia, float vb, uint32_t ib) {
    return va > vb || (va == vb && ia < ib);
}

}  // namespace trc

// ================================================================== les noyaux (extern "C")

// y = W x (+ b), W en Q8_0. `biais` peut être nul. Grille : ⌈R / 32⌉ blocs de 256 fils.
extern "C" __global__ void __launch_bounds__(256)
gemv_q8_0(const uint8_t* __restrict__ W, const float* __restrict__ x, const float* __restrict__ biais,
          float* __restrict__ y, uint32_t R, uint32_t C) {
    using namespace trc;
    const uint32_t voie = threadIdx.x & 31u;
    const uint32_t r0 = (blockIdx.x * (GEMV_FILS / 32u) + (threadIdx.x >> 5)) * GEMV_LIGNES_PAR_WARP;
    if (r0 >= R || C % 32u != 0) return;
    gemv_q8_0_4_lignes(W, x, biais, y, R, C, r0, voie);
}

// y = W x (+ b), W en f32 (le routeur). `biais` peut être nul. Grille : ⌈R / 32⌉ blocs de 256 fils.
extern "C" __global__ void __launch_bounds__(256)
gemv_f32(const float* __restrict__ W, const float* __restrict__ x, const float* __restrict__ biais,
         float* __restrict__ y, uint32_t R, uint32_t C) {
    using namespace trc;
    const uint32_t voie = threadIdx.x & 31u;
    const uint32_t r0 = (blockIdx.x * (GEMV_FILS / 32u) + (threadIdx.x >> 5)) * GEMV_LIGNES_PAR_WARP;
    if (r0 >= R || C % 4u != 0) return;
    gemv_f32_4_lignes(W, x, biais, y, R, C, r0, voie);
}

// RMSNorm de `lignes` vecteurs de n éléments (grille : lignes blocs de 256 fils) :
// y_i = x_i · r · w_i, r = 1/√(Σx²/n + ε). Somme des carrés en f64 : chaque fil t accumule
// i = t, t + 256, … dans l'ordre (fma), puis arbre fixe sur 256 ; y calculé en f64 puis arrondi.
// En place permis (y = x) : x est entièrement lu avant la première écriture.
extern "C" __global__ void __launch_bounds__(256)
rmsnorm(const float* __restrict__ x, const float* __restrict__ w, float* y, uint32_t n, float eps) {
    __shared__ double part[256];
    const uint32_t t = threadIdx.x;
    const float* xr = x + uint64_t(blockIdx.x) * n;
    float* yr = y + uint64_t(blockIdx.x) * n;
    double s = 0.0;
    for (uint32_t i = t; i < n; i += 256u) {
        const double v = xr[i];
        s = fma(v, v, s);
    }
    part[t] = s;
    __syncthreads();
#pragma unroll
    for (uint32_t k = 128; k > 0; k >>= 1) {
        if (t < k) part[t] += part[t + k];
        __syncthreads();
    }
    const double r = 1.0 / sqrt(part[0] / double(n) + double(eps));
    for (uint32_t i = t; i < n; i += 256u) yr[i] = float(double(xr[i]) * r * double(w[i]));
}

// Rotation YaRN « par moitiés » (NEOX) de q (tetes_q têtes) et k (tetes_k têtes), en place, à
// `position` : pour la paire i < d/2, x1 = x[i], x2 = x[i + d/2] ; o1 = x1 c − x2 s ; o2 = x2 c + x1 s,
// avec c = cos(position · inv_freq_i) · m, s = sin(…) · m, m la concentration de YaRN (appliquée à q
// et à k, donc m² sur q·k). Angle, sinus, cosinus et rotation en f64.
// Grille : tetes_q + tetes_k blocs de d/2 fils (32 pour gpt-oss).
extern "C" __global__ void __launch_bounds__(64)
rope_yarn(float* __restrict__ q, float* __restrict__ k, uint32_t tetes_q, uint32_t tetes_k, uint32_t position,
          trc::ParamsRope p) {
    using namespace trc;
    const uint32_t demi = p.dim_tete / 2u;
    const uint32_t i = threadIdx.x;
    if (i >= demi || blockIdx.x >= tetes_q + tetes_k) return;
    double m;
    const double inv = inv_freq_yarn(p, i, m);
    double s, c;
    sincos(double(position) * inv, &s, &c);
    c *= m;
    s *= m;
    float* x = blockIdx.x < tetes_q ? q + uint64_t(blockIdx.x) * p.dim_tete
                                    : k + uint64_t(blockIdx.x - tetes_q) * p.dim_tete;
    const double a = x[i], b = x[i + demi];
    x[i] = float(a * c - b * s);
    x[i + demi] = float(b * c + a * s);
}

// Écrit k et v (f32[dkv]) dans la case `case_kv` du cache de la couche (f16, [case][tête_kv][d]),
// arrondis au plus proche pair. Grille : ⌈dkv / 256⌉ blocs de 256 fils.
extern "C" __global__ void __launch_bounds__(256)
ecrire_kv(const float* __restrict__ k, const float* __restrict__ v, unsigned short* __restrict__ cache_k,
          unsigned short* __restrict__ cache_v, uint32_t dkv, uint32_t case_kv) {
    const uint32_t i = blockIdx.x * 256u + threadIdx.x;
    if (i >= dkv) return;
    const uint64_t o = uint64_t(case_kv) * dkv + i;
    cache_k[o] = __half_as_ushort(__float2half_rn(k[i]));
    cache_v[o] = __half_as_ushort(__float2half_rn(v[i]));
}

// Attention de décodage d'une position, une tête de requête par bloc (grille : tetes blocs de
// 256 fils ; mémoire partagée dynamique : 4 · (fin − debut) octets).
//   score_j = échelle · q · k_j (f32, produit sur d = 0..63 dans l'ordre), j ∈ [debut, fin) ;
//   m = max(max_j score_j, puits) ; e_j = exp(score_j − m) ; z = Σ_j e_j (arbre fixe) + exp(puits − m) ;
//   sortie[t] = (Σ_j e_j v_j[t]) / z, la somme par quatre groupes (j ≡ g mod 4, dans l'ordre),
//   combinés ((g0 + g1) + (g2 + g3)).
// La tête de requête h lit la tête kv h / (tetes / tetes_kv). Case d'une position : position, ou
// position mod anneau pour une couche à fenêtre.
extern "C" __global__ void __launch_bounds__(256)
attention(const float* __restrict__ q, const unsigned short* __restrict__ cache_k,
          const unsigned short* __restrict__ cache_v, const float* __restrict__ puits, float* __restrict__ sortie,
          trc::ParamsAttention p) {
    using namespace trc;
    extern __shared__ float scores[];
    __shared__ float qs[ATTENTION_DIM];
    __shared__ float part[ATTENTION_FILS];
    __shared__ float groupes[4][ATTENTION_DIM];
    const uint32_t t = threadIdx.x;
    const uint32_t h = blockIdx.x;
    if (p.dim_tete != ATTENTION_DIM || p.tetes_kv == 0 || p.tetes % p.tetes_kv != 0 || h >= p.tetes || p.fin < p.debut)
        return;
    const uint32_t hk = h / (p.tetes / p.tetes_kv);
    const uint32_t dkv = p.tetes_kv * ATTENTION_DIM;
    const uint32_t n = p.fin - p.debut;
    if (t < ATTENTION_DIM) qs[t] = q[uint64_t(h) * ATTENTION_DIM + t];
    __syncthreads();

    // 1. scores
    for (uint32_t j = t; j < n; j += ATTENTION_FILS) {
        const uint32_t pos = p.debut + j;
        const uint32_t c = p.anneau ? pos % p.anneau : pos;
        const uint4* kr = reinterpret_cast<const uint4*>(cache_k + uint64_t(c) * dkv + uint64_t(hk) * ATTENTION_DIM);
        float s = 0.0f;
#pragma unroll
        for (int b = 0; b < 8; ++b) {
            const uint4 w = kr[b];
            const uint32_t mots[4] = {w.x, w.y, w.z, w.w};
#pragma unroll
            for (int u = 0; u < 4; ++u) {
                s = fmaf(qs[8 * b + 2 * u], f16_vers_f32(mots[u] & 0xFFFFu), s);
                s = fmaf(qs[8 * b + 2 * u + 1], f16_vers_f32(mots[u] >> 16), s);
            }
        }
        scores[j] = s * p.echelle;
    }
    __syncthreads();

    // 2. softmax avec le puits dans le dénominateur
    float m = -INFINITY;
    for (uint32_t j = t; j < n; j += ATTENTION_FILS) m = fmaxf(m, scores[j]);
    const float puits_h = puits[h];
    m = fmaxf(reduire_bloc<true>(part, m), puits_h);
    float z = 0.0f;
    for (uint32_t j = t; j < n; j += ATTENTION_FILS) {
        const float e = expf(scores[j] - m);
        scores[j] = e;
        z += e;
    }
    z = reduire_bloc<false>(part, z) + expf(puits_h - m);

    // 3. somme pondérée des valeurs
    const uint32_t dd = t & (ATTENTION_DIM - 1u);
    const uint32_t g = t / ATTENTION_DIM;  // 0..3
    float a = 0.0f;
    for (uint32_t j = g; j < n; j += 4u) {
        const uint32_t pos = p.debut + j;
        const uint32_t c = p.anneau ? pos % p.anneau : pos;
        a = fmaf(scores[j], f16_vers_f32(cache_v[uint64_t(c) * dkv + uint64_t(hk) * ATTENTION_DIM + dd]), a);
    }
    groupes[g][dd] = a;
    __syncthreads();
    if (t < ATTENTION_DIM)
        sortie[uint64_t(h) * ATTENTION_DIM + t] = ((groupes[0][t] + groupes[1][t]) + (groupes[2][t] + groupes[3][t])) / z;
}

// ---- Variante d'essai (ronde de corrections J1, constat M5) : cache KV en f32. -----------------
// Mêmes calculs, dans le même ordre, que `ecrire_kv` et `attention` ci-dessus, à ceci près que les
// clés et les valeurs sont gardées en f32 (aucun arrondi) au lieu de f16. Ajoutées sans toucher aux
// deux noyaux de la couture N : elles ne servent qu'à mesurer ce que coûte l'arrondi f16 (décision de
// l'arbitre, couture N).
extern "C" __global__ void __launch_bounds__(256)
ecrire_kv_f32(const float* __restrict__ k, const float* __restrict__ v, float* __restrict__ cache_k,
              float* __restrict__ cache_v, uint32_t dkv, uint32_t case_kv) {
    const uint32_t i = blockIdx.x * 256u + threadIdx.x;
    if (i >= dkv) return;
    const uint64_t o = uint64_t(case_kv) * dkv + i;
    cache_k[o] = k[i];
    cache_v[o] = v[i];
}

extern "C" __global__ void __launch_bounds__(256)
attention_kvf32(const float* __restrict__ q, const float* __restrict__ cache_k,
                const float* __restrict__ cache_v, const float* __restrict__ puits, float* __restrict__ sortie,
                trc::ParamsAttention p) {
    using namespace trc;
    extern __shared__ float scores[];
    __shared__ float qs[ATTENTION_DIM];
    __shared__ float part[ATTENTION_FILS];
    __shared__ float groupes[4][ATTENTION_DIM];
    const uint32_t t = threadIdx.x;
    const uint32_t h = blockIdx.x;
    if (p.dim_tete != ATTENTION_DIM || p.tetes_kv == 0 || p.tetes % p.tetes_kv != 0 || h >= p.tetes || p.fin < p.debut)
        return;
    const uint32_t hk = h / (p.tetes / p.tetes_kv);
    const uint32_t dkv = p.tetes_kv * ATTENTION_DIM;
    const uint32_t n = p.fin - p.debut;
    if (t < ATTENTION_DIM) qs[t] = q[uint64_t(h) * ATTENTION_DIM + t];
    __syncthreads();

    // 1. scores (produit sur d = 0..63 dans l'ordre, comme `attention`)
    for (uint32_t j = t; j < n; j += ATTENTION_FILS) {
        const uint32_t pos = p.debut + j;
        const uint32_t c = p.anneau ? pos % p.anneau : pos;
        const float* kr = cache_k + uint64_t(c) * dkv + uint64_t(hk) * ATTENTION_DIM;
        float s = 0.0f;
#pragma unroll
        for (int d = 0; d < 64; ++d) s = fmaf(qs[d], kr[d], s);
        scores[j] = s * p.echelle;
    }
    __syncthreads();

    // 2. softmax avec le puits dans le dénominateur
    float m = -INFINITY;
    for (uint32_t j = t; j < n; j += ATTENTION_FILS) m = fmaxf(m, scores[j]);
    const float puits_h = puits[h];
    m = fmaxf(reduire_bloc<true>(part, m), puits_h);
    float z = 0.0f;
    for (uint32_t j = t; j < n; j += ATTENTION_FILS) {
        const float e = expf(scores[j] - m);
        scores[j] = e;
        z += e;
    }
    z = reduire_bloc<false>(part, z) + expf(puits_h - m);

    // 3. somme pondérée des valeurs
    const uint32_t dd = t & (ATTENTION_DIM - 1u);
    const uint32_t g = t / ATTENTION_DIM;  // 0..3
    float a = 0.0f;
    for (uint32_t j = g; j < n; j += 4u) {
        const uint32_t pos = p.debut + j;
        const uint32_t c = p.anneau ? pos % p.anneau : pos;
        a = fmaf(scores[j], cache_v[uint64_t(c) * dkv + uint64_t(hk) * ATTENTION_DIM + dd], a);
    }
    groupes[g][dd] = a;
    __syncthreads();
    if (t < ATTENTION_DIM)
        sortie[uint64_t(h) * ATTENTION_DIM + t] = ((groupes[0][t] + groupes[1][t]) + (groupes[2][t] + groupes[3][t])) / z;
}

// Routeur : les k plus grands des E logits (biais déjà ajouté par gemv_f32), ordre : score
// décroissant, puis indice croissant ; poids = softmax des k valeurs retenues, en f64 (m = la
// première, exp, somme dans l'ordre, division), arrondis en f32. Un warp (grille : 1 bloc de 32
// fils) ; E ≤ 256, k ≤ 8. Sorties : indices u32[k] et poids f32[k]. Si `boite` n'est pas nul
// (boîte aux lettres projetée en mémoire hôte, § 5.1), la case suit le protocole mesuré par le lot E
// (essai E0 c, banc-chemin/noyaux/essais.cu) : mots 1 .. k les indices, mots k + 1 .. 2k les poids
// (bits de f32), une barrière système, puis le mot 0 = `sequence`, écrit en dernier : un hôte qui
// voit le numéro voit aussi les indices. Pour gpt-oss (k = 4), une case de 64 o par couche.
extern "C" __global__ void __launch_bounds__(32)
routeur_topk(const float* __restrict__ logits, uint32_t E, uint32_t k, uint32_t* __restrict__ indices,
             float* __restrict__ poids, uint32_t* boite, uint32_t sequence) {
    using namespace trc;
    const uint32_t voie = threadIdx.x;
    if (E == 0 || E > 256u || k == 0 || k > 8u || k > E) return;
    float v[8];
    bool pris[8];
#pragma unroll
    for (uint32_t i = 0; i < 8; ++i) {
        const uint32_t e = voie + 32u * i;
        v[i] = e < E ? logits[e] : -INFINITY;
        pris[i] = e >= E;
    }
    float choisi_v[8];
    uint32_t choisi_i[8];
    for (uint32_t r = 0; r < k; ++r) {
        float bv = -INFINITY;
        uint32_t bi = 0xFFFFFFFFu;
#pragma unroll
        for (uint32_t i = 0; i < 8; ++i)
            if (!pris[i] && meilleur(v[i], voie + 32u * i, bv, bi)) {
                bv = v[i];
                bi = voie + 32u * i;
            }
#pragma unroll
        for (int d = 16; d > 0; d >>= 1) {
            const float ov = __shfl_xor_sync(0xFFFFFFFFu, bv, d);
            const uint32_t oi = __shfl_xor_sync(0xFFFFFFFFu, bi, d);
            if (meilleur(ov, oi, bv, bi)) {
                bv = ov;
                bi = oi;
            }
        }
        if (bi != 0xFFFFFFFFu && (bi & 31u) == voie) pris[bi >> 5] = true;
        choisi_v[r] = bv;
        choisi_i[r] = bi;
    }
    if (voie != 0) return;
    double e[8];
    const double m = choisi_v[0];
    double z = 0.0;
    for (uint32_t r = 0; r < k; ++r) {
        e[r] = exp(double(choisi_v[r]) - m);
        z += e[r];
    }
    for (uint32_t r = 0; r < k; ++r) {
        const float w = float(e[r] / z);
        indices[r] = choisi_i[r];
        poids[r] = w;
        if (boite != nullptr) {
            reinterpret_cast<volatile uint32_t*>(boite)[1 + r] = choisi_i[r];
            reinterpret_cast<volatile uint32_t*>(boite)[1 + k + r] = __float_as_uint(w);
        }
    }
    if (boite != nullptr) {
        __threadfence_system();
        reinterpret_cast<volatile uint32_t*>(boite)[0] = sequence;
    }
}

// Routeur biaisé par le cache (P3, option `--biais-cache`, règle de Skliar et al., arXiv 2412.00099) :
// les k experts sont CHOISIS sur le score logit[e] + biais[e] (biais[e] = β pour un expert déjà en
// VRAM, 0 sinon, vecteur monté par l'hôte), mais ils sont RENDUS dans l'ordre décroissant du logit
// NON biaisé (égalité : indice croissant) et leurs poids sont le softmax des logits NON biaisés, en
// f64 comme `routeur_topk`. Avec un biais nul, l'ensemble, l'ordre et les poids sont ceux de
// `routeur_topk`, au bit (la sélection est la même boucle ; le tri final ne permute rien quand le score
// d'ordre est le logit lui-même). Même grille et mêmes sorties (boîte aux lettres comprise) que
// `routeur_topk`, plus `biais` : f32[E]. `routeur_topk` lui-même n'est pas modifié.
extern "C" __global__ void __launch_bounds__(32)
routeur_topk_biais(const float* __restrict__ logits, const float* __restrict__ biais, uint32_t E, uint32_t k,
                   uint32_t* __restrict__ indices, float* __restrict__ poids, uint32_t* boite, uint32_t sequence) {
    using namespace trc;
    const uint32_t voie = threadIdx.x;
    if (E == 0 || E > 256u || k == 0 || k > 8u || k > E) return;
    float v[8];
    bool pris[8];
#pragma unroll
    for (uint32_t i = 0; i < 8; ++i) {
        const uint32_t e = voie + 32u * i;
        v[i] = e < E ? logits[e] + biais[e] : -INFINITY;
        pris[i] = e >= E;
    }
    uint32_t choisi_i[8];
    for (uint32_t r = 0; r < k; ++r) {
        float bv = -INFINITY;
        uint32_t bi = 0xFFFFFFFFu;
#pragma unroll
        for (uint32_t i = 0; i < 8; ++i)
            if (!pris[i] && meilleur(v[i], voie + 32u * i, bv, bi)) {
                bv = v[i];
                bi = voie + 32u * i;
            }
#pragma unroll
        for (int d = 16; d > 0; d >>= 1) {
            const float ov = __shfl_xor_sync(0xFFFFFFFFu, bv, d);
            const uint32_t oi = __shfl_xor_sync(0xFFFFFFFFu, bi, d);
            if (meilleur(ov, oi, bv, bi)) {
                bv = ov;
                bi = oi;
            }
        }
        if (bi != 0xFFFFFFFFu && (bi & 31u) == voie) pris[bi >> 5] = true;
        choisi_i[r] = bi;
    }
    if (voie != 0) return;
    // Les logits non biaisés des choisis, puis tri par insertion (k ≤ 8) : logit décroissant, indice croissant.
    float u[8];
    for (uint32_t r = 0; r < k; ++r) u[r] = logits[choisi_i[r]];
    for (uint32_t r = 1; r < k; ++r) {
        for (uint32_t j = r; j > 0 && meilleur(u[j], choisi_i[j], u[j - 1], choisi_i[j - 1]); --j) {
            const float tv = u[j];
            u[j] = u[j - 1];
            u[j - 1] = tv;
            const uint32_t ti = choisi_i[j];
            choisi_i[j] = choisi_i[j - 1];
            choisi_i[j - 1] = ti;
        }
    }
    double e[8];
    const double m = u[0];
    double z = 0.0;
    for (uint32_t r = 0; r < k; ++r) {
        e[r] = exp(double(u[r]) - m);
        z += e[r];
    }
    for (uint32_t r = 0; r < k; ++r) {
        const float w = float(e[r] / z);
        indices[r] = choisi_i[r];
        poids[r] = w;
        if (boite != nullptr) {
            reinterpret_cast<volatile uint32_t*>(boite)[1 + r] = choisi_i[r];
            reinterpret_cast<volatile uint32_t*>(boite)[1 + k + r] = __float_as_uint(w);
        }
    }
    if (boite != nullptr) {
        __threadfence_system();
        reinterpret_cast<volatile uint32_t*>(boite)[0] = sequence;
    }
}

// SwiGLU bornée de gpt-oss, élément par élément, en f64 : g ← min(g, 7) ; u ← borne(u, −7, 7) ;
// y = g / (1 + exp(−1,702 g)) · (u + 1). Grille : ⌈n / 256⌉ blocs de 256 fils.
extern "C" __global__ void __launch_bounds__(256)
swiglu_oai(const float* __restrict__ g, const float* __restrict__ u, float* __restrict__ y, uint32_t n) {
    const uint32_t i = blockIdx.x * 256u + threadIdx.x;
    if (i >= n) return;
    const double gv = fmin(double(g[i]), 7.0);
    const double uv = fmin(fmax(double(u[i]), -7.0), 7.0);
    y[i] = float(gv / (1.0 + exp(-1.702 * gv)) * (uv + 1.0));
}

// résidu[i] += ((w₀ s₀[i] + w₁ s₁[i]) + w₂ s₂[i]) + … dans l'ordre j = 0, 1, …, n − 1, chaque
// produit et chaque somme arrondis séparément (__fmul_rn, __fadd_rn : aucune contraction en fma),
// pour égaler au bit la même somme faite sur l'hôte en f32. s_j = sorties + j · pas. `poids` nul :
// tous les poids valent 1 (s_j pris tel quel ; sert à x ← x + a Woᵀ + bo). Grille : ⌈d / 256⌉ × 256.
extern "C" __global__ void __launch_bounds__(256)
combiner(float* __restrict__ residu, const float* __restrict__ sorties, uint32_t pas, const float* __restrict__ poids,
         uint32_t n, uint32_t d) {
    const uint32_t i = blockIdx.x * 256u + threadIdx.x;
    if (i >= d || n == 0) return;
    float s = poids != nullptr ? __fmul_rn(poids[0], sorties[i]) : sorties[i];
    for (uint32_t j = 1; j < n; ++j) {
        const float sj = sorties[uint64_t(j) * pas + i];
        s = __fadd_rn(s, poids != nullptr ? __fmul_rn(poids[j], sj) : sj);
    }
    residu[i] = __fadd_rn(residu[i], s);
}

// Ligne `ligne` d'une matrice Q8_0 de C colonnes (l'enchâssement) → f32[C], exact (d en f16 a 11
// bits de mantisse, q en a 7 : le produit tient en 18 bits). Grille : ⌈C / 256⌉ blocs de 256 fils.
extern "C" __global__ void __launch_bounds__(256)
ligne_q8_0(const uint8_t* __restrict__ W, uint32_t ligne, uint32_t C, float* __restrict__ y) {
    using namespace trc;
    const uint32_t i = blockIdx.x * 256u + threadIdx.x;
    if (i >= C || C % 32u != 0) return;
    const uint8_t* b = W + uint64_t(ligne) * (C / 32u) * Q8_OCTETS_BLOC + uint64_t(i / 32u) * Q8_OCTETS_BLOC;
    const float d = f16_vers_f32(uint32_t(b[0]) | (uint32_t(b[1]) << 8));
    y[i] = d * float(int8_t(b[2 + (i & 31u)]));
}

// Indice du plus grand des n logits ; égalité : plus petit indice ; un NaN n'est jamais retenu
// (si tous sont NaN : 0xFFFFFFFF). Un bloc de 1 024 fils : le fil t parcourt i = t, t + 1 024, … ,
// puis arbre fixe. Le résultat ne dépend pas de l'arbre (ordre total), l'arbre est fixe quand même.
extern "C" __global__ void __launch_bounds__(1024)
argmax(const float* __restrict__ v, uint32_t n, uint32_t* __restrict__ sortie) {
    using namespace trc;
    __shared__ float pv[1024];
    __shared__ uint32_t pi[1024];
    const uint32_t t = threadIdx.x;
    float bv = -INFINITY;
    uint32_t bi = 0xFFFFFFFFu;
    for (uint32_t i = t; i < n; i += 1024u) {
        const float x = v[i];
        if (meilleur(x, i, bv, bi)) {
            bv = x;
            bi = i;
        }
    }
    pv[t] = bv;
    pi[t] = bi;
    __syncthreads();
    for (uint32_t k = 512; k > 0; k >>= 1) {
        if (t < k && meilleur(pv[t + k], pi[t + k], pv[t], pi[t])) {
            pv[t] = pv[t + k];
            pi[t] = pi[t + k];
        }
        __syncthreads();
    }
    if (t == 0) sortie[0] = pi[0];
}
