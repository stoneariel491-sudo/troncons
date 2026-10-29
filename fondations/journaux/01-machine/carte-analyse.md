## Témoins (--fausser : doivent ÉCHOUER)
- h2d_hote_dma  : ECHEC
- h2d_bar_cpu  : ECHEC
- write_buffer  : ECHEC
- d2h  : ECHEC
- d2d  : ECHEC
- copie_tampon_envoi  : ECHEC
- vram_lecture  : ECHEC
- gemv q4 : ECHEC
- gemv f16 : ECHEC

## Transferts : Go/s [source du chrono] (passage 1 / passage 2), plafond respecté
| opération | taille | Vulkan | DX12 | Vulkan/DX12 |
|---|---|---|---|---|
| h2d_hote_dma | 64 Kio | 33.30 [carte] (33.03 / 33.57) HORS PLAFOND | 23.41 [carte] (20.05 / 26.77) HORS PLAFOND | 1.42 (dans le bruit) |
| h2d_bar_cpu | 64 Kio | 4.82 [mur] (4.93 / 4.71)  | 11.71 [mur] (11.25 / 12.17)  | 0.41 (réel) |
| write_buffer | 64 Kio | 0.65 [mur] (0.66 / 0.64)  | 0.37 [mur] (0.39 / 0.35)  | 1.75 (réel) |
| d2h | 64 Kio | 9.39 [carte] (9.59 / 9.19)  | 9.06 [carte] (8.83 / 9.28)  | 1.04 (dans le bruit) |
| d2d | 64 Kio | 67.15 [carte] (67.15 / 67.15)  | 60.40 [carte] (60.35 / 60.46)  | 1.11 (réel) |
| copie_tampon_envoi | 64 Kio | 33.13 [carte] (32.97 / 33.30)  | 34.19 [carte] (34.21 / 34.16)  | 0.97 (réel) |
| h2d_hote_dma | 1 Mio | 177.60 [carte] (177.48 / 177.72) HORS PLAFOND | 21.41 [carte] (20.16 / 22.67) HORS PLAFOND | 8.29 (réel) |
| h2d_bar_cpu | 1 Mio | 9.07 [mur] (9.05 / 9.09)  | 18.71 [mur] (18.36 / 19.06) HORS PLAFOND | 0.48 (réel) |
| write_buffer | 1 Mio | 4.64 [mur] (4.63 / 4.66)  | 2.84 [mur] (2.77 / 2.92)  | 1.63 (réel) |
| d2h | 1 Mio | 5.41 [carte] (5.39 / 5.44)  | 12.08 [carte] (12.12 / 12.03)  | 0.45 (réel) |
| d2d | 1 Mio | 379.23 [carte] (379.10 / 379.37)  | 455.61 [carte] (440.58 / 470.64)  | 0.83 (réel) |
| copie_tampon_envoi | 1 Mio | 192.26 [carte] (192.19 / 192.33)  | 26.81 [carte] (25.56 / 28.06)  | 7.17 (réel) |
| h2d_hote_dma | 4 Mio | 96.30 [carte] (173.75 / 18.84) HORS PLAFOND | 7.98 [carte] (8.25 / 7.70)  | 12.07 (dans le bruit) |
| h2d_bar_cpu | 4 Mio | 0.32 [mur] (0.47 / 0.16)  | 0.78 [mur] (0.68 / 0.87)  | 0.41 (dans le bruit) |
| write_buffer | 4 Mio | 0.17 [mur] (0.17 / 0.17)  | 0.18 [mur] (0.19 / 0.18)  | 0.93 (dans le bruit) |
| d2h | 4 Mio | 5.14 [carte] (5.02 / 5.26)  | 8.05 [carte] (4.17 / 11.94)  | 0.64 (dans le bruit) |
| d2d | 4 Mio | 439.01 [carte] (438.92 / 439.10)  | 582.70 [carte] (582.06 / 583.35)  | 0.75 (réel) |
| copie_tampon_envoi | 4 Mio | 223.51 [carte] (223.53 / 223.48)  | 23.27 [carte] (33.53 / 13.01)  | 9.60 (dans le bruit) |
| h2d_hote_dma | 16 Mio | 4.34 [carte] (4.41 / 4.26) HORS PLAFOND | 4.51 [carte] (4.49 / 4.53) HORS PLAFOND | 0.96 (dans le bruit) |
| h2d_bar_cpu | 16 Mio | 1.32 [mur] (2.48 / 0.16)  | 0.68 [mur] (0.74 / 0.62)  | 1.94 (dans le bruit) |
| write_buffer | 16 Mio | 0.33 [mur] (0.42 / 0.23)  | 0.36 [mur] (0.36 / 0.37)  | 0.90 (dans le bruit) |
| d2h | 16 Mio | 3.89 [carte] (4.67 / 3.11)  | 5.64 [carte] (4.70 / 6.59)  | 0.69 (dans le bruit) |
| d2d | 16 Mio | 372.92 [carte] (392.06 / 353.77)  | 534.26 [carte] (537.73 / 530.79)  | 0.70 (réel) |
| copie_tampon_envoi | 16 Mio | 192.65 [carte] (205.28 / 180.01)  | 12.23 [carte] (12.23 / 12.24)  | 15.75 (réel) |
| h2d_hote_dma | 64 Mio | 3.72 [carte] (3.51 / 3.94)  | 4.74 [carte] (4.46 / 5.03)  | 0.78 (réel) |
| h2d_bar_cpu | 64 Mio | 0.31 [mur] (0.45 / 0.17)  | 2.62 [mur] (0.62 / 4.62)  | 0.12 (dans le bruit) |
| write_buffer | 64 Mio | 0.15 [mur] (0.11 / 0.18)  | 0.43 [mur] (0.36 / 0.50)  | 0.34 (réel) |
| d2h | 64 Mio | 5.01 [carte] (6.14 / 3.87)  | 6.83 [carte] (3.77 / 9.89)  | 0.73 (dans le bruit) |
| d2d | 64 Mio | 226.47 [carte] (225.26 / 227.68)  | 221.35 [carte] (229.25 / 213.45)  | 1.02 (dans le bruit) |
| copie_tampon_envoi | 64 Mio | 114.96 [carte] (113.46 / 116.46)  | 12.02 [carte] (11.92 / 12.12)  | 9.57 (réel) |
| h2d_hote_dma | 256 Mio | 5.18 [carte] (6.24 / 4.12)  | 3.95 [carte] (3.98 / 3.91)  | 1.31 (dans le bruit) |
| h2d_bar_cpu | 256 Mio | 0.66 [mur] (0.83 / 0.48)  | 0.69 [mur] (0.68 / 0.70)  | 0.95 (dans le bruit) |
| write_buffer | 256 Mio | 0.43 [mur] (0.49 / 0.36)  | 0.32 [mur] (0.33 / 0.32)  | 1.32 (dans le bruit) |
| d2h | 256 Mio | 3.90 [carte] (3.93 / 3.87)  | 4.44 [carte] (5.37 / 3.52)  | 0.88 (dans le bruit) |
| d2d | 256 Mio | 167.51 [carte] (167.28 / 167.75)  | 228.41 [carte] (229.10 / 227.73)  | 0.73 (réel) |
| copie_tampon_envoi | 256 Mio | 83.69 [carte] (83.68 / 83.70)  | 12.16 [carte] (12.09 / 12.24)  | 6.88 (réel) |

## Lecture de la VRAM (shader)
- vulkan 512 Mio : carte 251.25 Go/s (min 250.52, max 251.26), mur 248.6, témoin ok, sous plafond true, util. avant 0 %
- dx12 512 Mio : carte 251.28 Go/s (min 251.25, max 251.31), mur 248.33, témoin ok, sous plafond true, util. avant 28 %
- dx12 512 Mio : carte 216.48 Go/s (min 216.34, max 247.67), mur 214.16, témoin ok, sous plafond true, util. avant 19 %
- vulkan 512 Mio : carte 251.29 Go/s (min 250.75, max 251.3), mur 248.86, témoin ok, sous plafond true, util. avant 1 %

## GEMV
| format | résidence | lot | API | Go/s carte (méd.) | µs/GEMV | GFLOP/s | écart rel. | témoin | plafond | util. avant |
|---|---|---|---|---|---|---|---|---|---|---|
| f16 | carte | 1 | vulkan | 250.13 | 536.6 | 250.1 | 3.5e-09 | ok | true | 28 % |
| f16 | carte | 1 | dx12 | 216.45 | 620.1 | 216.4 | 5.1e-09 | ok | true | 2 % |
| f16 | carte | 1 | dx12 | 251.4 | 533.9 | 251.4 | 5.1e-09 | ok | true | 0 % |
| f16 | carte | 1 | vulkan | 243.39 | 551.4 | 243.4 | 3.5e-09 | ok | true | 6 % |
| q4 | carte | 1 | vulkan | 95.3 | 1584.4 | 338.8 | 5.0e-09 | ok | true | 0 % |
| q4 | carte | 1 | dx12 | 31.92 | 4730.2 | 113.5 | 3.8e-09 | ok | true | 0 % |
| q4 | carte | 1 | dx12 | 31.92 | 4730.1 | 113.5 | 3.8e-09 | ok | true | 0 % |
| q4 | carte | 1 | vulkan | 112.32 | 1344.4 | 399.3 | 5.0e-09 | ok | true | 0 % |
| q4 | carte | 8 | vulkan | 14.38 | 10499.3 | 409.1 | 6.2e-09 | ok | true | 0 % |
| q4 | carte | 8 | dx12 | 0.56 | 267443.0 | 16.1 | 5.0e-09 | ok | true | 0 % |
| q4 | carte | 8 | dx12 | 1.35 | 112029.4 | 38.3 | 5.0e-09 | ok | true | 0 % |
| q4 | carte | 8 | vulkan | 11.84 | 12753.1 | 336.8 | 6.2e-09 | ok | true | 24 % |
| f16 | carte | 8 | vulkan | 117.63 | 1141.1 | 941.0 | 4.1e-09 | ok | true | 0 % |
| f16 | carte | 8 | dx12 | 48.16 | 2787.2 | 385.2 | 5.1e-09 | ok | true | 22 % |
| f16 | carte | 8 | dx12 | 47.08 | 2851.0 | 376.6 | 5.1e-09 | ok | true | 11 % |
| f16 | carte | 8 | vulkan | 115.29 | 1164.2 | 922.3 | 4.1e-09 | ok | true | 0 % |
| q4 | hote | 1 | vulkan | 11.75 | 12852.7 | 41.8 | 5.0e-09 | ok | true | 1 % |
| q4 | hote | 1 | dx12 | 11.5 | 13126.5 | 40.9 | 3.8e-09 | ok | true | 0 % |
| q4 | hote | 1 | dx12 | 9.44 | 16000.0 | 33.6 | 3.8e-09 | ok | true | 0 % |
| q4 | hote | 1 | vulkan | 11.39 | 13252.0 | 40.5 | 5.0e-09 | ok | true | 100 % |
| q4 | bar | 1 | vulkan | 95.32 | 1584.0 | 338.9 | 5.0e-09 | ok | true | 0 % |
| q4 | bar | 1 | dx12 | 8.82 | 17110.8 | 31.4 | 3.8e-09 | ok | true | 26 % |
| q4 | bar | 1 | dx12 | 11.87 | 12718.3 | 42.2 | 3.8e-09 | ok | true | 0 % |
| q4 | bar | 1 | vulkan | 113.39 | 1331.6 | 403.2 | 5.0e-09 | ok | true | 0 % |
