// Unité de compilation unique des noyaux de troncons : compilée par build.rs en une
// image (cubin sm_89 + PTX compute_89), embarquée dans le binaire Rust et chargée par
// l'API du pilote (cuModuleLoadData). Le banc C++ (banc/banc_k.cu) inclut les mêmes
// en-têtes, si bien que les noyaux mesurés sont, au caractère près, ceux du moteur.
#include "decodeur.cuh"
#include "gemv.cuh"
#include "passe.cuh"
