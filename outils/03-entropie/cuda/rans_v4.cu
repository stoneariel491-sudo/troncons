// Second chemin pour le débit du décodeur rANS v4 : le même algorithme que
// `decoder_v4` de decodeur.wgsl, écrit en CUDA (intrinsèques de warp : __ballot_sync,
// __popc, __shfl_sync), compilé par nvcc pour sm_89, sur le même flux (écrit par
// vider_flux.rs). Il répond à deux questions :
//   1. la sortie est-elle la même, octet pour octet ? (exactitude indépendante du format)
//   2. le débit de Vulkan/WGSL laisse-t-il de la performance sur la table, face au
//      compilateur de NVIDIA, sur la même carte, dans les mêmes conditions ?
// Mesure : événements CUDA, séries palindromiques décodage / recopie de même géométrie,
// médiane et dispersion ; témoin cassé (une fente corrompue -> sortie fausse).
//
// Construction : vcvars64.bat, CUDA_PATH=~/dev/outils/cuda-13.1.2, puis
//   nvcc -O3 -arch=sm_89 -o rans_v4.exe rans_v4.cu
// Usage : rans_v4.exe <dossier du flux> [passes] [sortie.json]  (sans sortie : stdout)

#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <vector>
#include <algorithm>
#include <cuda_runtime.h>

#define VERIF(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { \
    fprintf(stderr, "CUDA : %s (%s:%d)\n", cudaGetErrorString(e_), __FILE__, __LINE__); exit(1); } } while (0)

static std::vector<uint32_t> lire(const char* dossier, const char* nom) {
    char chemin[1024];
    snprintf(chemin, sizeof chemin, "%s/%s", dossier, nom);
    FILE* f = fopen(chemin, "rb");
    if (!f) { fprintf(stderr, "ouverture %s\n", chemin); exit(1); }
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    std::vector<uint32_t> v(n / 4);
    if (fread(v.data(), 4, v.size(), f) != v.size()) { fprintf(stderr, "lecture %s\n", chemin); exit(1); }
    fclose(f);
    return v;
}

// Un warp décode une tuile ; 4 warps par bloc, la table (16 Kio) en mémoire partagée.
__global__ void decoder_v4(const uint32_t* __restrict__ lut_g, const uint32_t* __restrict__ etats,
                           const uint4* __restrict__ tuiles, const uint32_t* __restrict__ mots,
                           uint32_t* __restrict__ sortie, unsigned nb_tuiles, int casser,
                           unsigned* __restrict__ controle) {
    __shared__ uint32_t lut[4096];
    for (int i = threadIdx.x; i < 4096; i += blockDim.x) lut[i] = lut_g[i];
    if (casser && threadIdx.x == 0) lut[7] ^= 1u;
    __syncthreads();
    const unsigned voie = threadIdx.x & 31, id = threadIdx.x >> 5;
    const unsigned tuile = blockIdx.x * (blockDim.x >> 5) + id;
    if (tuile >= nb_tuiles) return;
    const uint4 t = tuiles[tuile];
    uint32_t x = etats[tuile * 32 + voie];
    uint32_t ptr = t.x, base = t.x >> 1;
    uint32_t cour = mots[base + voie], suiv = mots[base + 32 + voie];
    const uint32_t masque_inf = (1u << voie) - 1u;
    uint32_t dest = t.z + voie;
    for (uint32_t m = 0; m < t.y; m++) {
        uint32_t mot = 0;
#pragma unroll
        for (int k = 0; k < 4; k++) {
            const uint32_t e = lut[x & 4095u];
            x = (((e >> 8) & 0xFFFu) + 1u) * (x >> 12) + (e >> 20);
            mot |= (e & 0xFFu) << (8 * k);
            const bool besoin = x < 65536u;
            const uint32_t vote = __ballot_sync(0xFFFFFFFFu, besoin);
            const uint32_t pos = ptr + __popc(vote & masque_inf);
            const uint32_t wi = (pos >> 1) - base;
            const uint32_t a = __shfl_sync(0xFFFFFFFFu, cour, wi & 31);
            const uint32_t b = __shfl_sync(0xFFFFFFFFu, suiv, wi & 31);
            const uint32_t w32 = wi >= 32 ? b : a;
            const uint32_t w = (w32 >> ((pos & 1) * 16)) & 0xFFFFu;
            x = besoin ? ((x << 16) | w) : x;
            ptr += __popc(vote);
            if ((ptr >> 1) - base >= 32) {
                base += 32;
                cour = suiv;
                suiv = mots[base + 32 + voie];
            }
        }
        sortie[dest] = mot;
        dest += 32;
    }
    if (x != 65536u) atomicAdd(controle, 1u);
}

// Recopie de même géométrie (chemin non compressé).
__global__ void copier(const uint4* __restrict__ tuiles, const uint32_t* __restrict__ brut,
                       uint32_t* __restrict__ sortie, unsigned nb_tuiles) {
    const unsigned voie = threadIdx.x & 31, id = threadIdx.x >> 5;
    const unsigned tuile = blockIdx.x * (blockDim.x >> 5) + id;
    if (tuile >= nb_tuiles) return;
    const uint4 t = tuiles[tuile];
    uint32_t dest = t.z + voie;
    for (uint32_t m = 0; m < t.y; m++) { sortie[dest] = brut[dest]; dest += 32; }
}

int main(int argc, char** argv) {
    if (argc < 2) { fprintf(stderr, "usage : rans_v4 <dossier> [passes]\n"); return 1; }
    const char* d = argv[1];
    const int passes = argc > 2 ? atoi(argv[2]) : 5;
    if (argc > 3 && !freopen(argv[3], "w", stdout)) { fprintf(stderr, "écriture %s\n", argv[3]); return 1; }
    auto lut = lire(d, "lut.bin"), etats = lire(d, "etats.bin"), tuiles = lire(d, "tuiles.bin"),
         mots = lire(d, "mots.bin"), attendu = lire(d, "attendu.bin");
    const unsigned nb_tuiles = (unsigned)(tuiles.size() / 4);
    cudaDeviceProp prop;
    VERIF(cudaGetDeviceProperties(&prop, 0));
    printf("{\n  \"carte\": \"%s\", \"sm\": \"%d.%d\", \"multiprocesseurs\": %d,\n", prop.name, prop.major, prop.minor, prop.multiProcessorCount);
    uint32_t *d_lut, *d_etats, *d_mots, *d_sortie, *d_brut; uint4* d_tuiles; unsigned* d_ctl;
    VERIF(cudaMalloc(&d_lut, lut.size() * 4)); VERIF(cudaMalloc(&d_etats, etats.size() * 4));
    VERIF(cudaMalloc(&d_tuiles, tuiles.size() * 4)); VERIF(cudaMalloc(&d_mots, mots.size() * 4));
    VERIF(cudaMalloc(&d_sortie, attendu.size() * 4)); VERIF(cudaMalloc(&d_brut, attendu.size() * 4));
    VERIF(cudaMalloc(&d_ctl, 4));
    VERIF(cudaMemcpy(d_lut, lut.data(), lut.size() * 4, cudaMemcpyHostToDevice));
    VERIF(cudaMemcpy(d_etats, etats.data(), etats.size() * 4, cudaMemcpyHostToDevice));
    VERIF(cudaMemcpy(d_tuiles, tuiles.data(), tuiles.size() * 4, cudaMemcpyHostToDevice));
    VERIF(cudaMemcpy(d_mots, mots.data(), mots.size() * 4, cudaMemcpyHostToDevice));
    VERIF(cudaMemcpy(d_brut, attendu.data(), attendu.size() * 4, cudaMemcpyHostToDevice));
    const unsigned blocs = (nb_tuiles + 3) / 4;
    std::vector<uint32_t> sortie(attendu.size());
    unsigned ctl;
    // exactitude, puis témoin cassé
    for (int casser = 0; casser < 2; casser++) {
        VERIF(cudaMemset(d_sortie, 0, attendu.size() * 4)); VERIF(cudaMemset(d_ctl, 0, 4));
        decoder_v4<<<blocs, 128>>>(d_lut, d_etats, d_tuiles, d_mots, d_sortie, nb_tuiles, casser, d_ctl);
        VERIF(cudaGetLastError()); VERIF(cudaDeviceSynchronize());
        VERIF(cudaMemcpy(sortie.data(), d_sortie, attendu.size() * 4, cudaMemcpyDeviceToHost));
        VERIF(cudaMemcpy(&ctl, d_ctl, 4, cudaMemcpyDeviceToHost));
        const bool exact = sortie == attendu;
        printf("  \"%s\": {\"exact\": %s, \"voies_hors_L\": %u},\n", casser ? "temoin_casse" : "verification", exact ? "true" : "false", ctl);
        fprintf(stderr, "%s : exact=%d voies hors de L=%u\n", casser ? "témoin cassé" : "vérification", (int)exact, ctl);
    }
    cudaEvent_t e0, e1; VERIF(cudaEventCreate(&e0)); VERIF(cudaEventCreate(&e1));
    auto lancer = [&](int quoi, int rep) -> double {
        VERIF(cudaEventRecord(e0));
        for (int r = 0; r < rep; r++) {
            if (quoi == 0) decoder_v4<<<blocs, 128>>>(d_lut, d_etats, d_tuiles, d_mots, d_sortie, nb_tuiles, 0, d_ctl);
            else copier<<<blocs, 128>>>(d_tuiles, d_brut, d_sortie, nb_tuiles);
        }
        VERIF(cudaEventRecord(e1)); VERIF(cudaEventSynchronize(e1));
        float ms; VERIF(cudaEventElapsedTime(&ms, e0, e1));
        return ms / 1e3 / rep;
    };
    int reps[2];
    for (int q = 0; q < 2; q++) { double t = lancer(q, 3); reps[q] = std::min(2000, std::max(3, (int)(0.25 / t) + 1)); }
    std::vector<double> temps[2];
    const int ordre[4] = {0, 1, 1, 0};
    for (int p = 0; p < passes; p++)
        for (int q : ordre) temps[q].push_back(lancer(q, reps[q]));
    const double octets = (double)attendu.size() * 4;
    const char* noms[2] = {"decoder_v4_cuda", "recopie_cuda"};
    printf("  \"octets_sortie\": %.0f, \"tuiles\": %u, \"debits\": {", octets, nb_tuiles);
    for (int q = 0; q < 2; q++) {
        auto v = temps[q];
        std::sort(v.begin(), v.end());
        const double md = v.size() % 2 ? v[v.size() / 2] : 0.5 * (v[v.size() / 2 - 1] + v[v.size() / 2]);
        printf("\"%s\": {\"go_s_mediane\": %.3f, \"go_s_meilleure\": %.3f, \"dispersion\": %.4f, \"lancements\": %d, \"temps_s\": [",
               noms[q], octets / md / 1e9, octets / v.front() / 1e9, (v.back() - v.front()) / v.front(), reps[q]);
        for (size_t i = 0; i < temps[q].size(); i++) printf("%s%.6e", i ? ", " : "", temps[q][i]);
        printf("]}%s", q ? "" : ", ");
        fprintf(stderr, "%s : médiane %.1f Go/s écrits (meilleure %.1f), dispersion %.1f %%\n", noms[q], octets / md / 1e9, octets / v.front() / 1e9, 100 * (v.back() - v.front()) / v.front());
    }
    printf("}\n}\n");
    return 0;
}
