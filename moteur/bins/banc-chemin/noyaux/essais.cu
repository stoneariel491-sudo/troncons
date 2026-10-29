// Noyaux des essais E0 du lot E (ARCHITECTURE.md § 6.5). Compilés par build.rs :
// nvcc -cubin -arch=sm_89 -O3. Ce ne sont pas des noyaux du moteur (lot K) : ils simulent la forme
// d'une couche de gpt-oss vue par le fil d'ordonnancement, pour mesurer ce que coûte la lecture du
// routeur par l'hôte, une fois par couche (essai c).
//
// Une couche, telle que l'hôte la voit :
//   flux de calcul : [routeur_factice ℓ] ---------------------> [expert_factice ℓ (4 indices)]
//                     écrit 4 indices                ▲ l'hôte lit les indices et lance
//                     dans la boîte aux lettres ─────┘ (événement ou sondage de la boîte)
//
// La boîte aux lettres est une mémoire hôte épinglée et projetée (cuMemHostAlloc + DEVICEMAP) :
// le noyau y écrit par le bus PCIe, l'hôte la lit sans copie. Une case de 64 octets par couche :
//   mot 0 : numéro de séquence s = jeton · 64 + couche + 1 (écrit en dernier)
//   mots 1 à 4 : les 4 indices d'experts ; mots 5 à 8 : les 4 poids (bits de f32) ; 9 à 15 : 0.

#include <stdint.h>

// Mélange de 32 bits (constantes de « lowbias32 », C. Wellons, domaine public) ; l'hôte calcule la
// même fonction (src/essai_c.rs) pour connaître l'attendu de chaque couche de chaque jeton.
__device__ __forceinline__ uint32_t melange(uint32_t x) {
    x ^= x >> 16; x *= 0x7feb352dU;
    x ^= x >> 15; x *= 0x846ca68bU;
    x ^= x >> 16;
    return x;
}

__device__ __forceinline__ uint32_t indice_attendu(uint32_t jeton, uint32_t couche, uint32_t i) {
    return melange(jeton * 0x9E3779B9u ^ couche * 0x85EBCA6Bu ^ (i + 1) * 0xC2B2AE35u) & 127u;
}

// Horloge globale de la carte, en nanosecondes (registre %globaltimer). L'attente active se règle
// en temps, pas en cycles : elle ne dépend pas de l'horloge du moment de la puce.
__device__ __forceinline__ uint64_t horloge_ns() {
    uint64_t t;
    asm volatile("mov.u64 %0, %%globaltimer;" : "=l"(t));
    return t;
}

__device__ __forceinline__ void occuper(uint64_t ns) {
    if (ns == 0) return;
    const uint64_t t0 = horloge_ns();
    while (horloge_ns() - t0 < ns) { }
}

// Le routeur simulé : occupe la carte `ns` nanosecondes (attention + routeur d'une couche), puis
// écrit les 4 indices et les 4 poids de la couche, une barrière système, et enfin le numéro de
// séquence. La barrière garantit qu'un hôte qui voit le numéro voit aussi les indices.
extern "C" __global__ void routeur_factice(uint32_t* boite, uint32_t jeton, uint32_t couche, uint64_t ns) {
    if (threadIdx.x != 0 || blockIdx.x != 0) return;
    occuper(ns);
    volatile uint32_t* c = boite + 16u * couche;
    float somme = 0.0f;
    float p[4];
    for (uint32_t i = 0; i < 4; ++i) {
        p[i] = 1.0f + (float)(indice_attendu(jeton, couche, i) & 7u);
        somme += p[i];
    }
    for (uint32_t i = 0; i < 4; ++i) {
        c[1 + i] = indice_attendu(jeton, couche, i);
        c[5 + i] = __float_as_uint(p[i] / somme);
    }
    __threadfence_system();
    c[0] = jeton * 64u + couche + 1u;
}

// L'expert simulé : revérifie sur la carte les 4 indices que l'hôte lui passe (une erreur est
// comptée dans `erreurs[0]`, addition atomique entière : la règle de déterminisme du § 5.6 ne vise
// que la virgule flottante), puis occupe la carte `ns` nanosecondes (les 4 GEMV de la couche).
extern "C" __global__ void expert_factice(uint32_t* erreurs, uint32_t jeton, uint32_t couche,
                                          uint32_t i0, uint32_t i1, uint32_t i2, uint32_t i3,
                                          uint64_t ns) {
    if (threadIdx.x != 0 || blockIdx.x != 0) return;
    const uint32_t lus[4] = {i0, i1, i2, i3};
    for (uint32_t i = 0; i < 4; ++i) {
        if (lus[i] != indice_attendu(jeton, couche, i)) atomicAdd(erreurs, 1u);
    }
    occuper(ns);
}
