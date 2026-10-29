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
