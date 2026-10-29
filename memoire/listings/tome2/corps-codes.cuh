    for (uint32_t t = warp; t < h.T; t += nwarps) {
        EtatVoie v;
        debut_tuile(v, h, t, voie);
        const uint32_t m1 = min(t * h.N + h.N, nmacro);
        // Le mot w = m · 32 + voie appartient au bloc floor(w/4) = 8m + floor(voie/4) (16 octets = 4 mots).
        // Son contexte demande l'échelle du bloc et la médiane de sa ligne : deux lectures
        // globales, faites un macro-pas d'avance pour que leur latence se cache derrière les
        // quatre pas rANS du macro-pas courant (mesure du 2026-10-15). Ligne et reste suivis
        // sans division (le bloc avance de 8 par macro-pas).
        uint32_t bloc = (t * h.N * VOIES + voie) >> 2;
        uint32_t ligne = bloc / B, reste = bloc - ligne * B;
        bool valide = bloc < nblocs;
        uint32_t e_suiv = valide ? __ldg(ech + bloc) : 0u;
        uint32_t m_suiv = valide ? __ldg(med + ligne) : 0u;
        for (uint32_t m = t * h.N; m < m1; ++m) {
            // Au-delà des blocs réels (bourrage du flux), contexte 0 : cas que la
            // spécification ne dit pas (REPRISE-K), sans objet pour gpt-oss.
            const uint32_t ctx = valide ? classe_echelle(e_suiv, m_suiv) : 0u;
            const uint32_t w = m * VOIES + voie;
            bloc += 8u;
            reste += 8u;
            while (reste >= B) { reste -= B; ++ligne; }
            valide = (m + 1u < m1) && bloc < nblocs;
            if (valide) {
                e_suiv = __ldg(ech + bloc);
                m_suiv = __ldg(med + ligne);
            }
            const uint32_t* lt = lut[ctx];
            uint32_t mot = 0;
#pragma unroll
            for (uint32_t k = 0; k < 4; ++k) mot |= pas_octet(v, lt, h, voie, masque_inf) << (8u * k);
            if (w < mots_utiles) codes[w] = mot;
        }
        fin_tuile(v, h, t, voie, hors_l, pointeur);
    }
