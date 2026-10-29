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
