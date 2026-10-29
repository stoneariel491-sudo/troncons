__device__ __forceinline__ uint32_t pas_octet(EtatVoie& v, const uint32_t* __restrict__ lut,
                                              const EnteteRans& h, uint32_t voie, uint32_t masque_inf) {
    const uint32_t e = lut[v.x & (M - 1u)];
    v.x = (((e >> 8) & 0xFFFu) + 1u) * (v.x >> PROBA_BITS) + (e >> 20);
    const bool besoin = v.x < L;
    const uint32_t vote = __ballot_sync(0xFFFFFFFFu, besoin);
    const uint32_t pos = v.ptr + __popc(vote & masque_inf);
    const uint32_t wi = (pos >> 1) - v.base;  // < 48 : voir la démonstration dans REPRISE-K
    const uint32_t a = __shfl_sync(0xFFFFFFFFu, v.cour, wi & 31u);
    const uint32_t b = __shfl_sync(0xFFFFFFFFu, v.suiv, wi & 31u);
    const uint32_t w32 = wi >= 32u ? b : a;
    const uint32_t w = (w32 >> ((pos & 1u) * 16u)) & 0xFFFFu;
    v.x = besoin ? ((v.x << 16) | w) : v.x;
    v.ptr += __popc(vote);
    if ((v.ptr >> 1) - v.base >= 32u) {
        v.base += 32u;
        v.cour = v.suiv;
        v.suiv = v.apres;
        v.apres = mot32(h, v.base + 64u + voie);
    }
    return e & 0xFFu;
}

__device__ __forceinline__ void debut_tuile(EtatVoie& v, const EnteteRans& h, uint32_t t, uint32_t voie) {
    v.x = h.etats[t * VOIES + voie];
    v.ptr = h.debut[t];
    v.base = v.ptr >> 1;
    v.cour = mot32(h, v.base + voie);
    v.suiv = mot32(h, v.base + 32u + voie);
    v.apres = mot32(h, v.base + 64u + voie);
}
