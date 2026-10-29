//! trc-reference : la passe avant de gpt-oss en f64 sur le processeur (ARCHITECTURE.md § 5.9, lot R).
//!
//! Rôle : dire ce que vaut **exactement** le modèle stocké dans le GGUF d'origine, pour juger
//! llama.cpp (étape R1) puis troncons (critère C4) contre la même vérité. Chemin indépendant : le
//! GGUF est lu par un lecteur écrit ici, les poids sont ramenés en f64 sans arrondi, toutes les
//! activations, le cache KV et les sommes sont en f64.
//!
//! Le seul choix de modélisation : la rampe de YaRN suit la définition d'OpenAI
//! (`"truncate": false`) ; la forme arrondie de llama.cpp reste disponible (`VarianteYarn`) pour
//! chiffrer l'écart entre les deux.

pub mod gguf;
pub mod modele;
pub mod ops;
pub mod poids;

pub use modele::{Compteurs, Expert, Hyper, Imitation, Reference};
pub use ops::VarianteYarn;
