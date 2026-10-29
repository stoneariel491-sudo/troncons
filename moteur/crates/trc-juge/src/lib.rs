//! trc-juge : le juge de qualité du projet (ARCHITECTURE.md § 5.9, lot R).
//!
//! - `kld` : le fichier de logits de llama-perplexity, lu et écrit au même format, pour que la base
//!   llama.cpp, la référence f64 et troncons passent par **le même instrument** (codage sur 16 bits
//!   par logit, critère C4) ;
//! - `stats` : divergence KL, premier choix, perplexité, quantiles, intervalles ;
//! - `compteurs` : octets lus (PDH), mémoire du processus, VRAM (C7, C8, C10) ;
//! - `abba` : la règle de décision des séries alternées (étude 06 § 7.5, reprise telle quelle).

pub mod abba;
pub mod compteurs;
pub mod kld;
pub mod stats;
