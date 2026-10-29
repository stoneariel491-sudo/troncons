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

// Contribution d'un bloc : sum_i k[code_i] · x_i, dans un ordre fixe (mot t = 0..3,
// octet k = 0..3, demi-octet bas puis haut). xs[0..3] = x[0..15], xs[4..7] = x[16..31].
__device__ __forceinline__ float produit_bloc(const uint4 q, const float4 (&xs)[8]) {
    const uint32_t mots[4] = {q.x, q.y, q.z, q.w};
    float s = 0.0f;
#pragma unroll
    for (int t = 0; t < 4; ++t) {
        const uint32_t w = mots[t];
        const float xa[4] = {xs[t].x, xs[t].y, xs[t].z, xs[t].w};
        const float xb[4] = {xs[4 + t].x, xs[4 + t].y, xs[4 + t].z, xs[4 + t].w};
#pragma unroll
        for (int k = 0; k < 4; ++k) {
            s = fmaf(valeur_e2m1x2((w >> (8 * k)) & 15u), xa[k], s);
            s = fmaf(valeur_e2m1x2((w >> (8 * k + 4)) & 15u), xb[k], s);
        }
    }
    return s;
}
