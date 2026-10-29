// Extrait de outils/03-entropie/rans/src/decodeur.wgsl (fonction decoder_v4), boucle intérieure,
// code inchangé ; seuls les commentaires de fin de ligne sont ajoutés ici.
for (var m = 0u; m < t.y; m++) {              // un macro-pas
    var mot = 0u;
    for (var k = 0u; k < 4u; k++) {           // 4 sous-pas, un octet chacun
        let e = lut[x & 4095u];               // fente = x mod M
        x = (((e >> 8u) & 0xFFFu) + 1u) * (x >> 12u) + (e >> 20u);
        mot |= (e & 0xFFu) << (8u * k);       // symbole : hors de l'état
        let besoin = x < 65536u;              // x < L : lire un mot
        let vote = subgroupBallot(besoin).x;
        let pos = ptr + countOneBits(vote & masque_inf);
        let wi = (pos >> 1u) - base;
        let a = subgroupShuffle(cour, wi & 31u);  // fenêtre en registres
        let b = subgroupShuffle(suiv, wi & 31u);
        let w32 = select(a, b, wi >= 32u);
        let w = (w32 >> ((pos & 1u) * 16u)) & 0xFFFFu;
        x = select(x, (x << 16u) | w, besoin);  // une seule lecture
        ptr += countOneBits(vote);
        if ((ptr >> 1u) - base >= 32u) {      // fenêtre suivante
            base += 32u;
            cour = suiv;
            suiv = mots[base + 32u + voie];
        }
    }
    sortie[dest] = mot;                       // 128 octets contigus
    dest += 32u;
}
