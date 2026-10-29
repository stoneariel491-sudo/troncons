"""Plafonds physiques de la machine de Stone et modèle de coût par jeton (calculé, jamais mesuré).

Sources des plafonds : fondations/journaux/01-machine/00-seuils-declares.md (calculés d'après les
caractéristiques relevées) et fondations/journaux/04-chargement/pcie-1.json (PCIe mesuré).

Hypothèses dites (à remplacer par des mesures) : CARTE_UTILE = 6,5 Go de VRAM pour les poids
(8 188 Mio moins l'écran, le contexte CUDA et un cache KV court) ; RAM_UTILE = 11 Go pour un
cache de poids (15,6 Go moins le système et les applications ouvertes).

Modèle : les toujours-lus résident sur la carte s'ils tiennent, sinon le surplus est lu en RAM par
le processeur. Les experts routés se partagent un cache C (RAM_UTILE + VRAM restante) et le disque.
Routage supposé uniforme et sans mémoire : taux de succès h = C / E (borné à 1) — c'est la borne
pessimiste du cache ; la localité réelle du routage ne peut que l'améliorer, et c'est à mesurer.
Les experts trouvés en RAM sont calculés par le processeur au débit de la RAM ; les manqués sont lus
sur le NVMe. t_opt suppose les trois étages parfaitement recouverts (max), t_pes en série (somme).
Le calcul arithmétique est supposé gratuit : ce sont des plafonds de débit, pas des prévisions.
"""
VRAM_GO_S = 256.0          # GDDR6 16 Gbit/s × 128 bits
RAM_GO_S = 41.6            # un seul module DDR5-5200, 64 bits
NVME_GO_S = 7.877          # PCIe 4.0 ×4
PCIE_MESURE_GO_S = 6.38    # hôte → carte, mémoire épinglée, 256 Mio (étude 04)
CARTE_UTILE = 6.5e9
RAM_UTILE = 11.0e9


def plafonds(A_o, R_o, E_o, table_o=0.0, table_lu_o=0.0):
    """Temps par jeton (s) optimiste et pessimiste, et taux de succès supposé uniforme.

    A_o : octets toujours lus ; R_o : octets d'experts routés lus par jeton ; E_o : octets de tous les
    experts routés ; table_o / table_lu_o : table de recherche (n-grammes, Engram) totale et lue par
    jeton, supposée laissée sur le disque (sa lecture par jeton est minuscule et prévisible).
    """
    if A_o <= CARTE_UTILE:
        t_A = A_o / (VRAM_GO_S * 1e9)
        cache = RAM_UTILE + (CARTE_UTILE - A_o)
    else:
        t_A = CARTE_UTILE / (VRAM_GO_S * 1e9) + (A_o - CARTE_UTILE) / (RAM_GO_S * 1e9)
        cache = max(0.0, RAM_UTILE - (A_o - CARTE_UTILE))
    h = 1.0 if E_o <= 0 else min(1.0, cache / E_o)
    t_ram = h * R_o / (RAM_GO_S * 1e9)
    t_disque = ((1 - h) * R_o + table_lu_o) / (NVME_GO_S * 1e9)
    return max(t_A, t_ram, t_disque), t_A + t_ram + t_disque, h
