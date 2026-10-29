//! Coûts unitaires en ensemble de travail (WS) des structures du moteur qui croissent avec le modèle
//! (constat M4 de l'épreuve J1 : le terme de 0,5 Mo de C7 ne comptait que le répertoire). Chaque
//! mesure : WS avant, création de n objets, WS après ; (après − avant) / n. Sert à écrire une borne
//! de C7 à termes nommés, chaque terme = (différence de comptes entre 120b et 20b) × (coût unitaire).
//!
//! `cargo run --release --example memoire_unitaire -- [n=2000]` ; sortie : une ligne JSON par sorte.

fn ws() -> i64 {
    trc_ordo::ensemble_travail() as i64
}

fn main() {
    let n: usize = std::env::args().nth(1).and_then(|s| s.parse().ok()).unwrap_or(2000);
    let ctx = trc_cuda::Contexte::nouveau(0).expect("contexte");
    // échauffement : le pilote paie ses premières structures une fois
    let _e0: Vec<_> = (0..16).map(|_| trc_cuda::Evenement::nouveau(&ctx, true).unwrap()).collect();
    let _m0: Vec<_> = (0..16).map(|_| trc_cuda::MemoireCarte::allouer(&ctx, 4096).unwrap()).collect();
    for (nom, horo) in [("evenement_horodate", true), ("evenement_simple", false)] {
        let a = ws();
        let v: Vec<_> = (0..n).map(|_| trc_cuda::Evenement::nouveau(&ctx, horo).unwrap()).collect();
        let b = ws();
        println!("{{\"sorte\": \"{nom}\", \"n\": {n}, \"octets_par_objet\": {:.1}}}", (b - a) as f64 / n as f64);
        drop(v);
    }
    for taille in [4096usize, 1 << 20] {
        let a = ws();
        let v: Vec<_> = (0..n.min(500)).map(|_| trc_cuda::MemoireCarte::allouer(&ctx, taille).unwrap()).collect();
        let b = ws();
        println!("{{\"sorte\": \"allocation_carte_{taille}\", \"n\": {}, \"octets_par_objet\": {:.1}}}", v.len(), (b - a) as f64 / v.len() as f64);
        drop(v);
    }
    println!(
        "{{\"sorte\": \"taille_EntreeRepertoire\", \"octets\": {}}}\n{{\"sorte\": \"taille_TenseurResident\", \"octets\": {}}}",
        std::mem::size_of::<trc_format::EntreeRepertoire>(),
        std::mem::size_of::<trc_format::TenseurResident>()
    );
}
