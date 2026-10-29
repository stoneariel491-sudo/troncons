//! Les motifs partagés, combinés : un bloc de d poids = somme de M motifs, chacun tiré d'un
//! dictionnaire de 2^b motifs partagé par tous les experts d'un tenseur (le « pool de gènes »),
//! choisi étage par étage sur le reste laissé par les étages précédents (quantification
//! résiduelle). Dictionnaires appris par k-moyennes pondérées (Lloyd), écrites ici.
//!
//! Débit : M · b / d bits par poids, plus les dictionnaires (2^b · d valeurs de 16 bits par étage et
//! par tenseur) et les échelles E8M0 (la source est la valeur E2M1 doublée de chaque poids, son
//! poids ω = 4^(e − 128) rend l'erreur absolue).

use rayon::prelude::*;

/// Le plus proche motif (au sens de Σ ω (x − c)²) : rend (indice, erreur).
#[inline]
pub fn plus_proche(x: &[f32], om: &[f32], dico: &[f32], d: usize) -> (usize, f32) {
    let mut meilleur = (0usize, f32::INFINITY);
    for (k, c) in dico.chunks_exact(d).enumerate() {
        let mut e = 0.0f32;
        for j in 0..d {
            let r = x[j] - c[j];
            e += om[j] * r * r;
        }
        if e < meilleur.1 {
            meilleur = (k, e);
        }
    }
    meilleur
}

/// k-moyennes pondérées : n vecteurs de dimension d, k centres, `iters` itérations de Lloyd.
/// Initialisation : k vecteurs pris à pas régulier dans l'échantillon.
pub fn kmoyennes(x: &[f32], om: &[f32], d: usize, k: usize, iters: usize) -> Vec<f32> {
    let n = x.len() / d;
    let mut dico = vec![0.0f32; k * d];
    for i in 0..k {
        let j = (i * n) / k;
        dico[i * d..(i + 1) * d].copy_from_slice(&x[j * d..(j + 1) * d]);
    }
    for _ in 0..iters {
        let affect: Vec<usize> = (0..n).into_par_iter().map(|i| plus_proche(&x[i * d..(i + 1) * d], &om[i * d..(i + 1) * d], &dico, d).0).collect();
        let mut num = vec![0.0f64; k * d];
        let mut den = vec![0.0f64; k * d];
        for (i, &a) in affect.iter().enumerate() {
            for j in 0..d {
                num[a * d + j] += om[i * d + j] as f64 * x[i * d + j] as f64;
                den[a * d + j] += om[i * d + j] as f64;
            }
        }
        for t in 0..k * d {
            if den[t] > 0.0 {
                dico[t] = (num[t] / den[t]) as f32;
            }
        }
    }
    dico
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn lloyd_max_deux_bits_gaussien() {
        // témoin : quantificateur scalaire à 4 niveaux d'une gaussienne → 0,1175 (Max, 1960)
        let n = 200_000;
        let x: Vec<f32> = (0..n).map(|i| crate::codons::quantile_normal((i as f64 + 0.5) / n as f64) as f32).collect();
        let om = vec![1.0f32; n];
        let dico = kmoyennes(&x, &om, 1, 4, 60);
        let mut e = 0.0f64;
        for i in 0..n {
            e += plus_proche(&x[i..i + 1], &om[i..i + 1], &dico, 1).1 as f64;
        }
        let mse = e / n as f64;
        assert!((mse - 0.1175).abs() < 0.002, "{mse}");
    }
}
