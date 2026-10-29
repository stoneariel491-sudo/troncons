// Coût de la passe de réassemblage des codes MXFP4 répartis en trois flux de classe
// (§1.6 de 03-entropie.md) : chaque bloc de 16 octets revient à sa place depuis le flux de
// sa classe. Mesure : débit de cette recopie dispersée, contre une recopie contiguë de
// même volume, événements CUDA, séries palindromiques, vérification octet à octet.
//
// Les classes sont tirées i.i.d. avec les proportions mesurées sur gpt-oss-20b, lues dans
// la ligne de commande (par défaut 0,3 / 0,4 / 0,3 si non données). L'indice source de
// chaque bloc (base de sa classe + rang dans sa classe) est calculé sur l'hôte et lu par
// le noyau : 4 octets de plus par bloc de 16, comptés dans le trafic.
//
// Construction : comme rans_v4.cu (construire.bat), nvcc -O3 -arch=sm_89.
// Usage : dispersion.exe [Mio de codes] [p0 p1 p2] [sortie.json]

#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <vector>
#include <algorithm>
#include <cuda_runtime.h>

#define VERIF(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { \
    fprintf(stderr, "CUDA : %s (%s:%d)\n", cudaGetErrorString(e_), __FILE__, __LINE__); exit(1); } } while (0)

__global__ void disperser(const uint4* __restrict__ src, const uint32_t* __restrict__ idx,
                          uint4* __restrict__ dst, size_t n) {
    size_t b = blockIdx.x * (size_t)blockDim.x + threadIdx.x;
    if (b < n) dst[b] = src[idx[b]];
}

__global__ void recopier(const uint4* __restrict__ src, uint4* __restrict__ dst, size_t n) {
    size_t b = blockIdx.x * (size_t)blockDim.x + threadIdx.x;
    if (b < n) dst[b] = src[b];
}

int main(int argc, char** argv) {
    const size_t mio = argc > 1 ? atoi(argv[1]) : 256;
    double p[3] = {0.3, 0.4, 0.3};
    if (argc > 4) { p[0] = atof(argv[2]); p[1] = atof(argv[3]); p[2] = atof(argv[4]); }
    if (argc > 5 && !freopen(argv[5], "w", stdout)) return 1;
    const size_t n = (mio << 20) / 16;  // blocs de 16 octets de codes
    std::vector<uint8_t> classe(n);
    uint64_t x = 0x9E3779B97F4A7C15ull;
    size_t compte[3] = {0, 0, 0};
    for (size_t b = 0; b < n; b++) {
        x ^= x >> 12; x ^= x << 25; x ^= x >> 27;
        double u = (double)((x * 0x2545F4914F6CDD1Dull) >> 11) / 9007199254740992.0;
        classe[b] = u < p[0] ? 0 : (u < p[0] + p[1] ? 1 : 2);
        compte[classe[b]]++;
    }
    size_t base[3] = {0, compte[0], compte[0] + compte[1]};
    std::vector<uint32_t> idx(n);
    std::vector<uint4> ordre(n), flux(n);  // ordre : le tenseur ; flux : les trois flux bout à bout
    size_t rang[3] = {0, 0, 0};
    for (size_t b = 0; b < n; b++) {
        ordre[b] = make_uint4((uint32_t)b, (uint32_t)(b * 3), (uint32_t)(b * 5), (uint32_t)(b * 7));
        const size_t s = base[classe[b]] + rang[classe[b]]++;
        idx[b] = (uint32_t)s;
        flux[s] = ordre[b];
    }
    uint4 *d_src, *d_dst; uint32_t* d_idx;
    VERIF(cudaMalloc(&d_src, n * 16)); VERIF(cudaMalloc(&d_dst, n * 16)); VERIF(cudaMalloc(&d_idx, n * 4));
    VERIF(cudaMemcpy(d_src, flux.data(), n * 16, cudaMemcpyHostToDevice));
    VERIF(cudaMemcpy(d_idx, idx.data(), n * 4, cudaMemcpyHostToDevice));
    const unsigned fils = 256, grille = (unsigned)((n + fils - 1) / fils);
    disperser<<<grille, fils>>>(d_src, d_idx, d_dst, n);
    VERIF(cudaGetLastError()); VERIF(cudaDeviceSynchronize());
    std::vector<uint4> sortie(n);
    VERIF(cudaMemcpy(sortie.data(), d_dst, n * 16, cudaMemcpyDeviceToHost));
    bool exact = true;
    for (size_t b = 0; b < n && exact; b++)
        exact = sortie[b].x == ordre[b].x && sortie[b].y == ordre[b].y && sortie[b].z == ordre[b].z && sortie[b].w == ordre[b].w;
    // témoin : un indice faussé doit rendre la sortie fausse
    std::vector<uint32_t> idx2 = idx; idx2[n / 2] = idx2[n / 2 + 1];
    VERIF(cudaMemcpy(d_idx, idx2.data(), n * 4, cudaMemcpyHostToDevice));
    disperser<<<grille, fils>>>(d_src, d_idx, d_dst, n);
    VERIF(cudaMemcpy(sortie.data(), d_dst, n * 16, cudaMemcpyDeviceToHost));
    bool temoin_exact = true;
    for (size_t b = 0; b < n && temoin_exact; b++) temoin_exact = sortie[b].x == ordre[b].x;
    VERIF(cudaMemcpy(d_idx, idx.data(), n * 4, cudaMemcpyHostToDevice));
    fprintf(stderr, "exact=%d témoin exact=%d (doit être 0)\n", (int)exact, (int)temoin_exact);
    cudaEvent_t e0, e1; VERIF(cudaEventCreate(&e0)); VERIF(cudaEventCreate(&e1));
    auto lancer = [&](int quoi, int rep) {
        VERIF(cudaEventRecord(e0));
        for (int r = 0; r < rep; r++) {
            if (quoi == 0) disperser<<<grille, fils>>>(d_src, d_idx, d_dst, n);
            else recopier<<<grille, fils>>>(d_src, d_dst, n);
        }
        VERIF(cudaEventRecord(e1)); VERIF(cudaEventSynchronize(e1));
        float ms; VERIF(cudaEventElapsedTime(&ms, e0, e1));
        return ms / 1e3 / rep;
    };
    std::vector<double> t[2];
    const int ordre_abba[4] = {0, 1, 1, 0};
    for (int k = 0; k < 6; k++) for (int q : ordre_abba) t[q].push_back(lancer(q, 50));
    const char* noms[2] = {"dispersion", "recopie_contigue"};
    printf("{\n  \"mio_codes\": %zu, \"proportions\": [%.4f, %.4f, %.4f], \"exact\": %s, \"temoin_exact\": %s,\n  \"debits\": {",
           mio, p[0], p[1], p[2], exact ? "true" : "false", temoin_exact ? "true" : "false");
    for (int q = 0; q < 2; q++) {
        auto v = t[q]; std::sort(v.begin(), v.end());
        const double md = 0.5 * (v[v.size() / 2 - 1] + v[v.size() / 2]);
        printf("\"%s\": {\"go_s_ecrits_mediane\": %.3f, \"dispersion\": %.4f, \"temps_s\": [", noms[q], n * 16.0 / md / 1e9, (v.back() - v.front()) / v.front());
        for (size_t i = 0; i < t[q].size(); i++) printf("%s%.6e", i ? ", " : "", t[q][i]);
        printf("]}%s", q ? "" : ", ");
        fprintf(stderr, "%s : %.1f Go/s écrits (médiane), dispersion %.1f %%\n", noms[q], n * 16.0 / md / 1e9, 100 * (v.back() - v.front()) / v.front());
    }
    printf("}\n}\n");
    return 0;
}
