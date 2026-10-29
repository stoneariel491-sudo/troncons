//! Rotation de Hadamard aléatoire par morceaux, le long des colonnes d'une rangée.
//!
//! y = (1/√n) H_n D x sur chaque morceau de n colonnes, D = diag(±1) tiré d'une graine (aucun bit
//! stocké : la graine est une constante du format). Orthogonale : W x = (W Rᵀ)(R x), donc
//! l'activation se tourne une fois par jeton (n log₂ n additions par morceau) et les poids tournés
//! se quantifient. La rotation mélange les blocs de 32 d'échelles différentes et rend les poids
//! d'un morceau à peu près gaussiens (incohérence, QuIP et QTIP).

use crate::codons::hache;

/// Signe de la colonne c pour la graine g.
#[inline]
pub fn signe(g: u32, c: usize) -> f32 {
    if hache(g ^ 0x5EED_0000, c as u32) & 1 == 0 { 1.0 } else { -1.0 }
}

/// Transformée de Walsh-Hadamard rapide, en place, normalisée (taille puissance de deux).
pub fn fwht(x: &mut [f32]) {
    let n = x.len();
    debug_assert!(n.is_power_of_two());
    let mut h = 1;
    while h < n {
        for i in (0..n).step_by(2 * h) {
            for j in i..i + h {
                let (a, b) = (x[j], x[j + h]);
                x[j] = a + b;
                x[j + h] = a - b;
            }
        }
        h *= 2;
    }
    let s = 1.0 / (n as f32).sqrt();
    for v in x.iter_mut() {
        *v *= s;
    }
}

/// Tourne une rangée (longueur multiple de n) : signes, puis FWHT par morceau.
pub fn tourner(x: &mut [f32], n: usize, graine: u32) {
    for (c, v) in x.iter_mut().enumerate() {
        *v *= signe(graine, c);
    }
    for m in x.chunks_exact_mut(n) {
        fwht(m);
    }
}

/// L'inverse : FWHT (elle est sa propre inverse une fois normalisée), puis signes.
pub fn detourner(x: &mut [f32], n: usize, graine: u32) {
    for m in x.chunks_exact_mut(n) {
        fwht(m);
    }
    for (c, v) in x.iter_mut().enumerate() {
        *v *= signe(graine, c);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn aller_retour_et_norme() {
        let x0: Vec<f32> = (0..2880).map(|i| ((i * 7919) % 1013) as f32 / 1013.0 - 0.5).collect();
        let mut x = x0.clone();
        tourner(&mut x, 64, 3);
        let n0: f64 = x0.iter().map(|&v| (v as f64).powi(2)).sum();
        let n1: f64 = x.iter().map(|&v| (v as f64).powi(2)).sum();
        assert!((n0 - n1).abs() < 1e-4 * n0);
        detourner(&mut x, 64, 3);
        for (a, b) in x.iter().zip(x0.iter()) {
            assert!((a - b).abs() < 1e-5);
        }
    }
}
