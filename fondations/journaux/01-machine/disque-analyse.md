## Témoins
- fausser: 2.004 Go/s, pages fausses 978688/978688, rapport système/outil None, cpu processus 0.44 s, cpu système None, réussi True
- contenu: 1.821 Go/s, pages fausses 0/889344, rapport système/outil 1.182, cpu processus 0.48 s, cpu système 0.9982, réussi True
- cache_tour1: 1.417 Go/s, pages fausses 0/1037824, rapport système/outil 0.68, cpu processus 1.41 s, cpu système 0.9926, réussi None
- cache_tour2: 1.650 Go/s, pages fausses 0/1208320, rapport système/outil 0.034, cpu processus 3.09 s, cpu système 0.9297, réussi True
- verdicts : [['temoin_fausser_tombe', True], ['temoin_contenu', True], ['temoin_cache_visible_compteur', True], ['aucune_lecture_sans_tampon_au_dessus_du_lien', True], ['sans_tampon_vu_par_le_disque', False]] relevés : 565

## alea : Go/s (moyenne A,B) [bruit |A-B|/moy] p50 µs
| bloc | qd 1 | qd 2 | qd 4 | qd 8 | qd 16 | qd 32 | qd 64 |
|---|---|---|---|---|---|---|---|
| 4 Kio | 0.015 [53%] 232 | 0.026 [98%] 228 | 0.059 [44%] 226 | 0.094 [84%] 245 | 0.125 [136%] 385 | 0.131 [134%] 490 | 0.132 [134%] 879 |
| 16 Kio | 0.054 [56%] 267 | 0.109 [52%] 232 | 0.223 [32%] 237 | 0.457 [4%] 253 | 0.678 [17%] 307 | 0.798 [0%] 498 | 0.835 [1%] 841 |
| 64 Kio | 0.205 [11%] 303 | 0.406 [3%] 301 | 0.578 [30%] 409 | 0.726 [6%] 698 | 0.739 [6%] 1386 | 0.728 [4%] 2860 | 0.721 [10%] 5786 |
| 256 Kio | 0.551 [5%] 437 | 0.959 [37%] 464 | 1.340 [23%] 711 | 1.453 [5%] 1423 | 1.249 [35%] 3120 | 1.370 [23%] 5817 | 1.425 [13%] 13636 |
| 1 Mio | 1.307 [18%] 726 | 2.249 [11%] 875 | 2.195 [17%] 1902 | 2.085 [9%] 3840 | 2.327 [3%] 7403 | 2.206 [6%] 14971 | 1.928 [8%] 36336 |
| 4 Mio | 2.314 [5%] 1737 | 2.890 [9%] 2806 | 2.581 [10%] 6357 | 2.691 [8%] 12655 | 2.430 [0%] 27926 | 2.369 [2%] 57196 | 2.418 [2%] 110905 |
| 16 Mio | 2.819 [1%] 5585 | 2.760 [2%] 11704 | 2.533 [0%] 26198 | 2.366 [4%] 56445 | 2.487 [2%] 107691 |  |  |

## seq : Go/s (moyenne A,B) [bruit |A-B|/moy] p50 µs
| bloc | qd 1 | qd 2 | qd 4 | qd 8 | qd 16 | qd 32 | qd 64 |
|---|---|---|---|---|---|---|---|
| 4 Kio | 0.046 [11%] 52 | 0.067 [2%] 145 | 0.086 [8%] 172 | 0.156 [1%] 177 | 0.188 [3%] 232 | 0.215 [7%] 389 | 0.218 [9%] 709 |
| 16 Kio | 0.078 [6%] 193 | 0.153 [6%] 198 | 0.252 [19%] 220 | 0.434 [7%] 282 | 0.647 [3%] 315 | 0.791 [1%] 482 | 0.812 [0%] 821 |
| 64 Kio | 0.390 [16%] 140 | 0.480 [13%] 249 | 0.849 [33%] 266 | 1.602 [25%] 272 | 2.309 [0%] 361 | 2.382 [3%] 630 | 1.599 [103%] 1364 |
| 256 Kio | 0.508 [70%] 353 | 1.553 [4%] 297 | 1.957 [72%] 363 | 2.241 [121%] 698 | 3.014 [54%] 1048 | 2.173 [6%] 3414 | 2.209 [4%] 6105 |
| 1 Mio | 1.599 [8%] 601 | 2.999 [27%] 596 | 3.156 [43%] 1306 | 2.233 [56%] 3788 | 1.900 [40%] 7930 | 2.193 [39%] 13417 | 1.163 [47%] 35174 |
| 4 Mio | 1.041 [13%] 1614 | 2.657 [16%] 2534 | 2.385 [11%] 6602 | 2.339 [16%] 12918 | 1.631 [92%] 34171 | 1.344 [63%] 109604 | 1.626 [97%] 220814 |
| 16 Mio | 2.340 [43%] 5534 | 2.735 [4%] 11565 | 1.468 [73%] 35663 | 1.099 [38%] 126267 | 2.206 [17%] 111334 |  |  |

## Processeur et compteur du système (balayage)
- alea 4096 o, meilleur qd 64: 0.221 Go/s, cpu processus 1.75 s (3.97 s/Go), cpu système moyen 38% (noyau 15%), rapport système/outil 1.356
- alea 16384 o, meilleur qd 64: 0.839 Go/s, cpu processus 1.75 s (1.04 s/Go), cpu système moyen 42% (noyau 21%), rapport système/outil 1.483
- alea 65536 o, meilleur qd 16: 0.760 Go/s, cpu processus 0.62 s (0.41 s/Go), cpu système moyen 39% (noyau 19%), rapport système/outil 1.727
- alea 262144 o, meilleur qd 32: 1.526 Go/s, cpu processus 0.50 s (0.16 s/Go), cpu système moyen 33% (noyau 12%), rapport système/outil 2.065
- alea 1048576 o, meilleur qd 2: 2.378 Go/s, cpu processus 0.36 s (0.08 s/Go), cpu système moyen 34% (noyau 15%), rapport système/outil 1.176
- alea 4194304 o, meilleur qd 2: 3.020 Go/s, cpu processus 0.44 s (0.07 s/Go), cpu système moyen 39% (noyau 18%), rapport système/outil 1.387
- alea 16777216 o, meilleur qd 1: 2.835 Go/s, cpu processus 0.48 s (0.09 s/Go), cpu système moyen 46% (noyau 26%), rapport système/outil 1.432
- seq 4096 o, meilleur qd 64: 0.228 Go/s, cpu processus 1.73 s (3.81 s/Go), cpu système moyen 40% (noyau 20%), rapport système/outil 1.252
- seq 16384 o, meilleur qd 64: 0.814 Go/s, cpu processus 1.61 s (0.99 s/Go), cpu système moyen 44% (noyau 19%), rapport système/outil 1.6
- seq 65536 o, meilleur qd 64: 2.420 Go/s, cpu processus 1.70 s (0.35 s/Go), cpu système moyen 69% (noyau 46%), rapport système/outil 1.038
- seq 262144 o, meilleur qd 16: 3.835 Go/s, cpu processus 0.97 s (0.13 s/Go), cpu système moyen 43% (noyau 18%), rapport système/outil 1.174
- seq 1048576 o, meilleur qd 4: 3.838 Go/s, cpu processus 0.81 s (0.11 s/Go), cpu système moyen 40% (noyau 18%), rapport système/outil 1.19
- seq 4194304 o, meilleur qd 2: 2.867 Go/s, cpu processus 0.58 s (0.10 s/Go), cpu système moyen 51% (noyau 25%), rapport système/outil 1.463
- seq 16777216 o, meilleur qd 1: 2.844 Go/s, cpu processus 0.44 s (0.08 s/Go), cpu système moyen 43% (noyau 20%), rapport système/outil 1.684

## IOCP contre IoRing (ABBA, deux fois)
- ('alea', 4096, 1): iocp 0.019 Go/s (bruit 2%, cpu 0.24 s, p50 202 µs) ; ioring 0.019 Go/s (bruit 3%, cpu 0.28 s, p50 202 µs) ; écart 0% -> pas de différence au-dessus du bruit
- ('alea', 4096, 32): iocp 0.211 Go/s (bruit 5%, cpu 1.61 s, p50 444 µs) ; ioring 0.213 Go/s (bruit 17%, cpu 1.54 s, p50 630 µs) ; écart 1% -> pas de différence au-dessus du bruit
- ('alea', 65536, 16): iocp 0.751 Go/s (bruit 4%, cpu 0.61 s, p50 1376 µs) ; ioring 0.759 Go/s (bruit 0%, cpu 0.53 s, p50 1366 µs) ; écart 1% -> pas de différence au-dessus du bruit
- ('seq', 1048576, 8): iocp 2.824 Go/s (bruit 8%, cpu 0.58 s, p50 2864 µs) ; ioring 2.748 Go/s (bruit 6%, cpu 0.41 s, p50 2943 µs) ; écart 3% -> pas de différence au-dessus du bruit
- ('seq', 16777216, 4): iocp 2.303 Go/s (bruit 15%, cpu 0.33 s, p50 28499 µs) ; ioring 2.194 Go/s (bruit 18%, cpu 0.21 s, p50 28639 µs) ; écart 5% -> pas de différence au-dessus du bruit
