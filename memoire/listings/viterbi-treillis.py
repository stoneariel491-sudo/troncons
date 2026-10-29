# Extrait de outils/quant-mse-gaussien.py (commit 3adf9c3), lignes 119-136, recopié tel quel.
def code_mul1(etats):
    """EXL3 « mul1 » : x <- s * 0x83DCD12D mod 2^32, somme des 4 octets, centrée sur 510."""
    x = (etats.astype(np.uint64) * 0x83DCD12D) & 0xFFFFFFFF
    somme = (x & 0xFF) + ((x >> 8) & 0xFF) + ((x >> 16) & 0xFF) + ((x >> 24) & 0xFF)
    return somme.astype(np.float64) - 510.0


def viterbi_treillis(suite, table, L, k):
    """Coût minimal (somme des erreurs quadratiques) d'une suite sur le treillis à
    décalage : état suivant = ((état << k) | b) mod 2^L ; valeur émise = table[état].
    État initial libre. Les prédécesseurs de s' sont (s' >> k) | (h << (L - k))."""
    n_etats = 1 << L
    cout = (suite[0] - table) ** 2
    for t in range(1, len(suite)):
        # min sur les 2^k bits sortants h, pour chaque valeur de (s' >> k)
        m = cout.reshape(1 << k, n_etats >> k).min(axis=0)
        cout = np.repeat(m, 1 << k) + (suite[t] - table) ** 2
    return float(cout.min())
