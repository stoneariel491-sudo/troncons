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
