// Coût du décodage dans le noyau : produit matrice-vecteur (lot de 1) sur la RTX 4060,
// poids stockés en FP16, en scalaire 2 bits, en scalaire 4 bits, et en treillis à décalage
// 2 bits (code calculé « mul1 », L = 16, tuile de 256 poids lue circulairement), écrit de
// zéro d'après la définition mathématique du treillis (QTIP, arXiv 2406.11235) et la
// disposition décrite au § 3.4 de fondations/02-quantification.md.
//
// Les deux noyaux 2 bits ont exactement la même disposition mémoire (tuile de 256 poids =
// 16 mots de 32 bits, une échelle FP16 par ligne) et le même parcours : la différence de
// temps entre eux est le coût du décodage du treillis seul.
//
// Témoin : y calculé par le GPU contre y calculé par le CPU (même décodage écrit une
// seconde fois en C++ hôte) sur 64 lignes ; erreur relative maximale < 1e-3, seuil posé
// avant le lancement d'après la précision FP32 des accumulations sur K = 16384 termes.
// --casser fausse la constante du code sur le CPU seul : le témoin doit tomber.
//
// Séries ABBA : chaque format B est encadré par le FP16 (A) ; journal JSON sur stdout.
//
// Compilation : nvcc -O3 -arch=sm_89 -o quant-gemv-treillis.exe quant-gemv-treillis.cu

#include <cuda_fp16.h>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <cmath>
#include <vector>
#include <random>

#define VERIF(x) do { cudaError_t e = (x); if (e != cudaSuccess) { \
    fprintf(stderr, "CUDA %s ligne %d : %s\n", #x, __LINE__, cudaGetErrorString(e)); exit(1); } } while (0)

static const int M = 16384;          // lignes (sorties)
static const int K = 16384;          // colonnes (entrées)
static const int TUILE = 256;        // poids par tuile
static const uint32_t MUL1 = 0x83DCD12Du;

// ---------- décodage du code « mul1 » : somme des 4 octets de (état * MUL1), centrée ----------
__host__ __device__ inline float mul1_hote(uint32_t etat, uint32_t mul) {
    uint32_t x = etat * mul;
    int s = (x & 0xff) + ((x >> 8) & 0xff) + ((x >> 16) & 0xff) + (x >> 24);
    return (float)(s - 510) * (1.0f / 147.7f);
}

__device__ inline float mul1_dev_u(uint32_t etat) {
    uint32_t x = etat * MUL1;
    unsigned s = __dp4a(x, 0x01010101u, 0u);  // surcharge non signée
    return (float)((int)s - 510) * (1.0f / 147.7f);
}

// état de 16 bits du poids t d'une tuile : les 16 bits qui finissent à la position (t+1)*k,
// lus circulairement dans les 512 bits de la tuile (k = 2)
__host__ __device__ inline uint32_t etat_treillis(const uint32_t* tuile, int t) {
    int fin = (t + 1) * 2;                 // position (exclue) du dernier bit
    int debut = (fin - 16 + 512) & 511;    // premier bit de la fenêtre
    int i0 = debut >> 5, s = debut & 31;
    uint64_t deux = ((uint64_t)tuile[(i0 + 1) & 15] << 32) | tuile[i0];
    return (uint32_t)(deux >> s) & 0xffff;
}

// ---------- noyaux : une chaîne (warp) par ligne, 8 chaînes par bloc ----------
__global__ void gemv_f16(const half* __restrict__ W, const half* __restrict__ x, float* y) {
    int ligne = blockIdx.x * 8 + (threadIdx.x >> 5), voie = threadIdx.x & 31;
    const half2* w = (const half2*)(W + (size_t)ligne * K);
    const half2* xv = (const half2*)x;
    float acc = 0.f;
    for (int i = voie; i < K / 2; i += 32) {
        float2 a = __half22float2(w[i]), b = __half22float2(xv[i]);
        acc += a.x * b.x + a.y * b.y;
    }
    for (int o = 16; o; o >>= 1) acc += __shfl_xor_sync(0xffffffff, acc, o);
    if (!voie) y[ligne] = acc;
}

// Passe 2 de la conception (la passe 1, une voie par tuile, lisait x en accès dispersés et
// plafonnait à 14 Go/s quel que soit le format : journal gemv-1-noyau-mal-concu.json).
// Ici toute la chaîne traite une tuile à la fois : la voie v prend les poids 8v..8v+7,
// lit ses 8 activations d'un seul accès de 16 octets (coalescé sur la chaîne), et les
// deux mots de 32 bits qui portent ses bits (le mot précédent sert à la fenêtre du
// treillis ; pour i = 0 c'est le mot 15 : lecture circulaire de la tuile).
template <int MODE>   // 0 = scalaire 2 bits, 1 = treillis mul1
__global__ void gemv_2b(const uint32_t* __restrict__ Q, const half* __restrict__ ech,
                        const half* __restrict__ x, float* y) {
    int ligne = blockIdx.x * 8 + (threadIdx.x >> 5), voie = threadIdx.x & 31;
    const int tuiles = K / TUILE;
    const uint32_t* q = Q + (size_t)ligne * tuiles * 16;
    const int i = voie >> 1, moitie = voie & 1;
    float acc = 0.f;
    #pragma unroll 2
    for (int tu = 0; tu < tuiles; ++tu) {
        const uint32_t* t = q + tu * 16;
        uint32_t w1 = __ldg(t + i), w0 = __ldg(t + ((i + 15) & 15));
        uint4 xr = __ldg((const uint4*)(x + tu * TUILE + 8 * voie));
        const half2* xh = (const half2*)&xr;
        float v[8];
        if (MODE == 0) {
            uint32_t b = w1 >> (16 * moitie);
            #pragma unroll
            for (int j = 0; j < 8; ++j) v[j] = (float)((b >> (2 * j)) & 3) - 1.5f;
        } else {
            uint64_t deux = ((uint64_t)w1 << 32) | w0;
            #pragma unroll
            for (int j = 0; j < 8; ++j)
                v[j] = mul1_dev_u((uint32_t)(deux >> (18 + 16 * moitie + 2 * j)) & 0xffff);
        }
        #pragma unroll
        for (int j = 0; j < 4; ++j) {
            float2 xf = __half22float2(xh[j]);
            acc += v[2 * j] * xf.x + v[2 * j + 1] * xf.y;
        }
    }
    for (int o = 16; o; o >>= 1) acc += __shfl_xor_sync(0xffffffff, acc, o);
    if (!voie) y[ligne] = acc * __half2float(ech[ligne]);
}

// 4 bits scalaire : tuile = 32 mots, la voie v prend le mot v (poids 8v..8v+7)
__global__ void gemv_4b(const uint32_t* __restrict__ Q, const half* __restrict__ ech,
                        const half* __restrict__ x, float* y) {
    int ligne = blockIdx.x * 8 + (threadIdx.x >> 5), voie = threadIdx.x & 31;
    const int tuiles = K / TUILE;
    const uint32_t* q = Q + (size_t)ligne * tuiles * 32;
    float acc = 0.f;
    #pragma unroll 2
    for (int tu = 0; tu < tuiles; ++tu) {
        uint32_t w = __ldg(q + tu * 32 + voie);
        uint4 xr = __ldg((const uint4*)(x + tu * TUILE + 8 * voie));
        const half2* xh = (const half2*)&xr;
        #pragma unroll
        for (int j = 0; j < 4; ++j) {
            float2 xf = __half22float2(xh[j]);
            acc += ((float)((w >> (8 * j)) & 15) - 7.5f) * xf.x
                 + ((float)((w >> (8 * j + 4)) & 15) - 7.5f) * xf.y;
        }
    }
    for (int o = 16; o; o >>= 1) acc += __shfl_xor_sync(0xffffffff, acc, o);
    if (!voie) y[ligne] = acc * __half2float(ech[ligne]);
}

// ---------- références hôte ----------
static float ref_2b(const std::vector<uint32_t>& Q, const std::vector<half>& ech,
                    const std::vector<float>& xf, int ligne, int mode, uint32_t mul) {
    const int tuiles = K / TUILE;
    double acc = 0;
    for (int tu = 0; tu < tuiles; ++tu) {
        const uint32_t* t = &Q[((size_t)ligne * tuiles + tu) * 16];
        for (int p = 0; p < TUILE; ++p) {
            float v = mode == 0 ? (float)((t[p >> 4] >> ((p & 15) * 2)) & 3) - 1.5f
                                : mul1_hote(etat_treillis(t, p), mul);
            acc += (double)v * xf[tu * TUILE + p];
        }
    }
    return (float)(acc * __half2float(ech[ligne]));
}

static float ref_4b(const std::vector<uint32_t>& Q, const std::vector<half>& ech,
                    const std::vector<float>& xf, int ligne) {
    const int tuiles = K / TUILE;
    double acc = 0;
    for (int tu = 0; tu < tuiles; ++tu) {
        const uint32_t* t = &Q[((size_t)ligne * tuiles + tu) * 32];
        for (int p = 0; p < TUILE; ++p)
            acc += (double)(((t[p >> 3] >> ((p & 7) * 4)) & 15) - 7.5f) * xf[tu * TUILE + p];
    }
    return (float)(acc * __half2float(ech[ligne]));
}

static float ref_f16(const std::vector<half>& W, const std::vector<float>& xf, int ligne) {
    double acc = 0;
    for (int k = 0; k < K; ++k) acc += (double)__half2float(W[(size_t)ligne * K + k]) * xf[k];
    return (float)acc;
}

int main(int argc, char** argv) {
    bool casser = argc > 1 && !strcmp(argv[1], "--casser");
    const int REPET = 50, SERIES = 3;
    std::mt19937_64 gen(1);
    std::normal_distribution<float> nd(0.f, 1.f);
    std::uniform_int_distribution<uint32_t> ud;

    std::vector<half> W((size_t)M * K), x(K), ech(M);
    std::vector<float> xf(K);
    for (auto& w : W) w = __float2half(nd(gen) * 0.02f);
    for (int k = 0; k < K; ++k) { xf[k] = __half2float(__float2half(nd(gen))); x[k] = __float2half(xf[k]); }
    for (auto& e : ech) e = __float2half(0.02f);
    std::vector<uint32_t> Q2((size_t)M * K / 16), Q4((size_t)M * K / 8);
    for (auto& q : Q2) q = ud(gen);
    for (auto& q : Q4) q = ud(gen);

    half *dW, *dx, *dech; uint32_t *dQ2, *dQ4; float* dy;
    VERIF(cudaMalloc(&dW, W.size() * 2)); VERIF(cudaMalloc(&dx, K * 2)); VERIF(cudaMalloc(&dech, M * 2));
    VERIF(cudaMalloc(&dQ2, Q2.size() * 4)); VERIF(cudaMalloc(&dQ4, Q4.size() * 4)); VERIF(cudaMalloc(&dy, M * 4));
    VERIF(cudaMemcpy(dW, W.data(), W.size() * 2, cudaMemcpyHostToDevice));
    VERIF(cudaMemcpy(dx, x.data(), K * 2, cudaMemcpyHostToDevice));
    VERIF(cudaMemcpy(dech, ech.data(), M * 2, cudaMemcpyHostToDevice));
    VERIF(cudaMemcpy(dQ2, Q2.data(), Q2.size() * 4, cudaMemcpyHostToDevice));
    VERIF(cudaMemcpy(dQ4, Q4.data(), Q4.size() * 4, cudaMemcpyHostToDevice));

    const char* noms[4] = {"f16", "scalaire-2b", "treillis-mul1-2b", "scalaire-4b"};
    const double octets[4] = {(double)M * K * 2, (double)M * K / 4 + M * 2, (double)M * K / 4 + M * 2,
                              (double)M * K / 2 + M * 2};
    auto lancer = [&](int f) {
        dim3 g(M / 8), b(256);
        if (f == 0) gemv_f16<<<g, b>>>(dW, dx, dy);
        else if (f == 1) gemv_2b<0><<<g, b>>>(dQ2, dech, dx, dy);
        else if (f == 2) gemv_2b<1><<<g, b>>>(dQ2, dech, dx, dy);
        else gemv_4b<<<g, b>>>(dQ4, dech, dx, dy);
    };

    // Témoin
    printf("{\n \"outil\": \"quant-gemv-treillis.cu\", \"M\": %d, \"K\": %d, \"casser\": %s,\n \"temoins\": [\n",
           M, K, casser ? "true" : "false");
    bool tout_ok = true;
    std::vector<float> y(M);
    for (int f = 0; f < 4; ++f) {
        lancer(f); VERIF(cudaGetLastError()); VERIF(cudaDeviceSynchronize());
        VERIF(cudaMemcpy(y.data(), dy, M * 4, cudaMemcpyDeviceToHost));
        double pire = 0;
        for (int i = 0; i < 64; ++i) {
            int l = (int)((uint64_t)i * 2654435761u % M);
            float r = f == 0 ? ref_f16(W, xf, l) : f == 3 ? ref_4b(Q4, ech, xf, l)
                    : ref_2b(Q2, ech, xf, l, f == 1 ? 0 : 1, casser ? MUL1 + 2 : MUL1);
            double e = fabs(y[l] - r) / (fabs(r) + 1e-3 * sqrt((double)K) * 0.02);
            if (e > pire) pire = e;
        }
        bool ok = pire < 1e-3;
        tout_ok &= ok;
        printf("  {\"format\": \"%s\", \"erreur_relative_max\": %.3e, \"tient\": %s}%s\n", noms[f], pire,
               ok ? "true" : "false", f < 3 ? "," : "");
    }
    printf(" ],\n \"temoin\": \"%s\",\n", tout_ok ? "tient" : "TOMBE");
    if (casser || !tout_ok) { printf(" \"mesures\": []\n}\n"); return tout_ok ? 0 : 2; }

    cudaEvent_t e0, e1; cudaEventCreate(&e0); cudaEventCreate(&e1);
    auto chrono = [&](int f) {
        lancer(f); VERIF(cudaDeviceSynchronize());   // chauffe
        cudaEventRecord(e0);
        for (int r = 0; r < REPET; ++r) lancer(f);
        cudaEventRecord(e1); cudaEventSynchronize(e1);
        float ms; cudaEventElapsedTime(&ms, e0, e1);
        return ms / REPET;
    };
    printf(" \"repetitions\": %d, \"mesures\": [\n", REPET);
    bool premier = true;
    for (int s = 0; s < SERIES; ++s)
        for (int f = 1; f < 4; ++f) {
            int ordre[4] = {0, f, f, 0};
            for (int o = 0; o < 4; ++o) {
                float ms = chrono(ordre[o]);
                printf("%s  {\"serie\": %d, \"format\": \"%s\", \"role\": \"%s\", \"ms\": %.4f, \"go_s\": %.1f}",
                       premier ? "" : ",\n", s, noms[ordre[o]], ordre[o] == 0 ? "A" : "B", ms,
                       octets[ordre[o]] / (ms * 1e6));
                premier = false;
            }
        }
    printf("\n ]\n}\n");
    return 0;
}
