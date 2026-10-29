//! Débit de `empreinte64` (préfixe de SHA-256, crate sha2 0.10.9) sur des tampons de la taille d'un
//! tronçon, sur un fil puis sur n fils : la grandeur qui chiffre la garde de production (constat M1 de
//! l'épreuve J1 ; le juge l'estimait à « l'ordre de 2 Go/s par cœur » [est.]).
//!
//! `cargo run --release --example debit_empreinte -- [octets=12000000] [tours=40] [fils=1,2,4]`
//! Sortie : une ligne JSON par nombre de fils (Go/s = octets hachés ÷ horloge murale), et le témoin
//! (l'empreinte d'un tampon connu, égale au préfixe de SHA-256 calculé autrement : « abc »).

use std::time::Instant;

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let octets: usize = a.get(1).and_then(|s| s.parse().ok()).unwrap_or(12_000_000);
    let tours: usize = a.get(2).and_then(|s| s.parse().ok()).unwrap_or(40);
    let fils: Vec<usize> = a.get(3).map(|s| s.split(',').filter_map(|x| x.parse().ok()).collect()).unwrap_or(vec![1, 2, 4]);
    // Témoin : SHA-256("abc") = ba7816bf 8f01cfea …, donc empreinte64 = 0xeacf018fbf1678ba.
    let t = trc_format::empreinte64(b"abc");
    println!("{{\"temoin_abc\": \"{t:016x}\", \"attendu\": \"eacf018fbf1678ba\", \"tient\": {}}}", t == 0xeacf_018f_bf16_78ba);
    let tampons: Vec<Vec<u8>> = (0..8).map(|i| (0..octets).map(|x| ((x * 31 + i * 7) % 251) as u8).collect()).collect();
    for &n in &fils {
        let t0 = Instant::now();
        let mut somme = 0u64;
        std::thread::scope(|s| {
            let mains: Vec<_> = (0..n)
                .map(|f| {
                    let tampons = &tampons;
                    s.spawn(move || {
                        let mut x = 0u64;
                        for k in (f..tours).step_by(n) {
                            x ^= trc_format::empreinte64(&tampons[k % tampons.len()]);
                        }
                        x
                    })
                })
                .collect();
            for m in mains {
                somme ^= m.join().unwrap();
            }
        });
        let s = t0.elapsed().as_secs_f64();
        println!(
            "{{\"fils\": {n}, \"octets_par_tampon\": {octets}, \"tampons\": {tours}, \"secondes\": {s:.4}, \"go_s\": {:.3}, \"go_s_par_fil\": {:.3}, \"xor\": \"{somme:016x}\"}}",
            (octets * tours) as f64 / s / 1e9,
            (octets * tours) as f64 / s / 1e9 / n as f64
        );
    }
}
