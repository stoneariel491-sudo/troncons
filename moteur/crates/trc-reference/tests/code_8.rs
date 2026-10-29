//! La référence f64 lit le code 8 (−0) comme 0, comme ggml (`kvalues_mxfp4`, table int8
//! `0, 1, 2, 3, 4, 6, 8, 12, 0, −1, …`, ggml/src/ggml-common.h de llama.cpp b11515, MIT) : lot A de
//! la construction (genome/06-codon-v1-2.md, vérification 1).
//!
//! Deux énoncés, mesurés : (1) en valeur, K[8] = −0,0 vaut 0 (comparaison f64) et chaque poids
//! déquantifié d'une matrice égale celui de sa copie canonisée ; (2) au bit, le produit de la
//! référence (huit accumulateurs partis de +0, FMA) rend les mêmes bits sur la matrice et sur sa
//! copie canonisée, pour des x quelconques (zéros des deux signes compris). Cassure : un code 0 de
//! la copie changé en 1, en face d'un x non nul, change la sortie.

use trc_reference::gguf::GGML_MXFP4;
use trc_reference::poids::{K_MXFP4, Matrice};

struct Alea(u64);
impl Alea {
    fn suivant(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
}

fn canoniser(octets: &mut [u8]) -> u64 {
    let mut n = 0;
    for blk in octets.chunks_exact_mut(17) {
        for q in &mut blk[1..] {
            for k in [0u8, 4] {
                if (*q >> k) & 15 == 8 {
                    *q &= !(15 << k);
                    n += 1;
                }
            }
        }
    }
    n
}

#[test]
fn reference_lit_le_code_8_comme_0() {
    assert_eq!(K_MXFP4[8], 0.0, "K[8] doit valoir 0 en valeur");
    assert!(K_MXFP4[8].is_sign_negative(), "K[8] est −0 dans la table de la référence (le signe ne change aucune somme)");
    let (lignes, colonnes) = (64usize, 2880usize);
    let mut a = Alea(20261017);
    let mut octets = Vec::with_capacity(lignes * colonnes / 32 * 17);
    for _ in 0..lignes * colonnes / 32 {
        octets.push(110 + (a.suivant() % 20) as u8);
        for _ in 0..16 {
            // Grandeur 0 une fois sur trois, signe tiré pour toutes.
            let g = |a: &mut Alea| -> u8 { let m = if a.suivant() % 3 == 0 { 0 } else { (a.suivant() % 8) as u8 }; m | (((a.suivant() & 1) as u8) << 3) };
            octets.push(g(&mut a) | (g(&mut a) << 4));
        }
    }
    let mut canon = octets.clone();
    let n8 = canoniser(&mut canon);
    assert!(n8 > 10_000, "le jeu d'essai doit porter des −0 ({n8})");
    let m = Matrice::nouvelle(GGML_MXFP4, lignes, colonnes, octets).unwrap();
    let mc = Matrice::nouvelle(GGML_MXFP4, lignes, colonnes, canon.clone()).unwrap();

    // (1) En valeur.
    let (mut l1, mut l2) = (vec![0f64; colonnes], vec![0f64; colonnes]);
    for r in 0..lignes {
        m.ligne(r, &mut l1);
        mc.ligne(r, &mut l2);
        assert!(l1.iter().zip(&l2).all(|(x, y)| x == y), "ligne {r} différente en valeur");
    }

    // (2) Au bit, sur 5 vecteurs.
    let n = 5;
    let x: Vec<f64> = (0..n * colonnes)
        .map(|i| match i % 89 {
            0 => 0.0,
            1 => -0.0,
            _ => ((a.suivant() >> 11) as f64 / (1u64 << 53) as f64 - 0.5) * 2f64.powi((a.suivant() % 13) as i32 - 6),
        })
        .collect();
    let (mut y1, mut y2) = (vec![0f64; n * lignes], vec![0f64; n * lignes]);
    m.produit(&x, n, &mut y1);
    mc.produit(&x, n, &mut y2);
    let differents = y1.iter().zip(&y2).filter(|(p, q)| p.to_bits() != q.to_bits()).count();
    assert_eq!(differents, 0, "sorties de la référence différentes au bit ({n8} −0 fondus)");

    // Cassure : un code 0 de la ligne 0 changé en 1, en face d'un x non nul.
    let mut casse = canon;
    let t = (0..16).find(|&t| casse[1 + t] & 15 == 0 && x[t] != 0.0).expect("un code 0");
    casse[1 + t] |= 1;
    let mk = Matrice::nouvelle(GGML_MXFP4, lignes, colonnes, casse).unwrap();
    let mut y3 = vec![0f64; n * lignes];
    mk.produit(&x, n, &mut y3);
    assert_ne!(y3[0].to_bits(), y2[0].to_bits(), "la cassure n'a rien changé : le témoin ne voit rien");
}
