//! Micro-banc du décodeur processeur sur données synthétiques (distribution des codes
//! Q4_K mesurée), pour séparer le coût du code de la contention de la machine.
use rans_troncons::*;
use std::time::Instant;

fn main() {
    let freq: [u64; 16] = [169, 107, 155, 215, 280, 343, 394, 420, 418, 386, 333, 268, 203, 145, 120, 140];
    let table = Table::depuis_comptes(&freq);
    // octets synthétiques tirés selon la table (xorshift déterministe)
    let n = 32 << 20;
    let mut src = vec![0u8; n];
    let mut etat: u64 = 0x9E3779B97F4A7C15;
    let mut tire = || {
        etat ^= etat << 13; etat ^= etat >> 7; etat ^= etat << 17;
        let fente = (etat >> 20) as u32 & 4095;
        (table.lut[fente as usize] & 15) as u8
    };
    for o in src.iter_mut() {
        *o = tire() | (tire() << 4);
    }
    let flux = coder(&src, &table, 256);
    let attendu: Vec<u32> = bytemuck::cast_slice::<u8, u32>(&src).to_vec();
    let mut sortie = vec![0u32; n / 4];
    let pool = rayon::ThreadPoolBuilder::new().num_threads(1).build().unwrap();
    for essai in 0..5 {
        let t = Instant::now();
        let e = decoder_tout(&flux, &table.lut, &mut sortie, &pool);
        let dt = t.elapsed().as_secs_f64();
        let mut c = vec![0u32; n / 4];
        let t2 = Instant::now();
        c.copy_from_slice(&attendu);
        let dc = t2.elapsed().as_secs_f64();
        println!("essai {essai} : décodage {:.3} Go/s ({:.1} Mcodes/s), recopie {:.2} Go/s, exact={} échecs={}",
            n as f64 / dt / 1e9, 2.0 * n as f64 / dt / 1e6, n as f64 / dc / 1e9, sortie == attendu, e);
    }
}
