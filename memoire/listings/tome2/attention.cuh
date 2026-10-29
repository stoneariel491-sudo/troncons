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
