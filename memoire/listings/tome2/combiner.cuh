// résidu[i] += ((w₀ s₀[i] + w₁ s₁[i]) + w₂ s₂[i]) + … dans l'ordre j = 0, 1, …, n − 1, chaque
// produit et chaque somme arrondis séparément (__fmul_rn, __fadd_rn : aucune contraction en fma),
// pour égaler au bit la même somme faite sur l'hôte en f32. s_j = sorties + j · pas. `poids` nul :
// tous les poids valent 1 (s_j pris tel quel ; sert à x ← x + a Wo^T + bo). Grille : ceil(d / 256) × 256.
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
