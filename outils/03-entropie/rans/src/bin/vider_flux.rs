//! Écrit sur le disque un lot codé par le rANS v4 (alphabet octet), pour qu'un second
//! décodeur, écrit dans un autre langage (CUDA, `outils/03-entropie/cuda/rans_v4.cu`), le
//! décode et soit comparé au nôtre : même flux, même table, même sortie attendue.
//!
//! Fichiers (petit-boutistes) dans <dossier> :
//!   lut.bin     4 096 × u32 (entrée de table v4) ;
//!   etats.bin   32 × u32 par tuile ;
//!   tuiles.bin  4 × u32 par tuile (premier mot 16 bits, nb macro-pas, premier mot de sortie, 0) ;
//!   mots.bin    mots de 16 bits rangés deux par u32, plus 64 u32 de marge ;
//!   attendu.bin la source (les demi-octets), u32.
//!
//! Usage : vider_flux <fichier.gguf> <dossier> [--type 12] [--lot-mo 256]

use rans_troncons::*;

fn arg(args: &[String], nom: &str, defaut: usize) -> usize {
    args.iter().position(|a| a == nom).map(|i| args[i + 1].parse().unwrap()).unwrap_or(defaut)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let (chemin, dossier) = (&args[1], std::path::Path::new(&args[2]));
    let type_vise = arg(&args, "--type", 12) as u32;
    let limite = arg(&args, "--lot-mo", 256) << 20;
    std::fs::create_dir_all(dossier).unwrap();
    let mut lot: Vec<u8> = Vec::new();
    for t in lire_entete_gguf(chemin).iter().filter(|t| t.type_ggml == type_vise) {
        if lot.len() >= limite {
            break;
        }
        let (_, qs) = separer_blocs(type_vise, &lire_tenseur(chemin, t));
        lot.extend_from_slice(&qs);
    }
    lot.truncate(lot.len().min(limite) / 32768 * 32768);
    let mut h = vec![0u64; 256];
    for &o in &lot {
        h[o as usize] += 1;
    }
    let table = Table256::depuis_comptes(&h);
    let flux = coder_octets(&lot, &table, 256);
    let mut mots32: Vec<u32> = vec![0; flux.mots.len().div_ceil(2) + 64];
    for (i, &w) in flux.mots.iter().enumerate() {
        mots32[i / 2] |= (w as u32) << (16 * (i % 2));
    }
    let tuiles: Vec<u32> = flux.tuiles.iter().flat_map(|t| t.iter().cloned()).collect();
    let ecrire = |nom: &str, v: &[u32]| std::fs::write(dossier.join(nom), bytemuck::cast_slice::<u32, u8>(v)).unwrap();
    ecrire("lut.bin", &table.lut);
    ecrire("etats.bin", &flux.etats);
    ecrire("tuiles.bin", &tuiles);
    ecrire("mots.bin", &mots32);
    std::fs::write(dossier.join("attendu.bin"), &lot).unwrap();
    eprintln!("{} octets source, {} tuiles, {} octets codés (taux {:.4})", lot.len(), flux.tuiles.len(),
        flux.octets_codes(), lot.len() as f64 / flux.octets_codes() as f64);
}
