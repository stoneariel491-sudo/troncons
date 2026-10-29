//! La recette littérale : un bloc de C poids = U(graine) · t, U une matrice C × P tirée d'un
//! générateur pseudo-aléatoire par sa graine de K bits, t P coefficients quantifiés (entiers de
//! 4 bits en complément à deux, un exposant partagé de 4 bits). Écrit ici de zéro ; la forme du
//! problème est celle de SeedLM (Shafipour et al., arXiv 2410.10714v2), dont on ne copie rien.
//!
//! Débit : (K + 4 + 4 P) / C bits par poids. Transcription : P multiplications-additions par poids,
//! plus la génération de P éléments de U par poids.
//!
//! Deux générateurs :
//! - `Generateur::Lfsr` : registre à décalage à rétroaction linéaire de 16 bits, forme de Galois,
//!   polynôme x^16 + x^14 + x^13 + x^11 + 1 (masque 0xB400 ; la période maximale 65 535 est vérifiée
//!   par le témoin `periode_maximale`) ; un élément = l'état après un pas, ramené dans [−1, 1) ;
//! - `Generateur::Hache` : un élément = mélange (graine, rang) ; parallèle, un mélange par élément.

use crate::codons::hache;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Generateur {
    Lfsr,
    Hache,
}

#[derive(Clone, Copy, Debug)]
pub struct Recette {
    pub c: usize,
    pub p: usize,
    pub k: u32,
    pub generateur: Generateur,
}

impl Recette {
    pub fn debit(&self) -> f64 {
        (self.k as f64 + 4.0 + 4.0 * self.p as f64) / self.c as f64
    }
}

/// Un pas du LFSR de Galois de 16 bits.
#[inline]
pub fn lfsr_pas(s: u16) -> u16 {
    let bas = s & 1;
    let mut t = s >> 1;
    if bas != 0 {
        t ^= 0xB400;
    }
    t
}

/// La matrice U (C × P, rangée par rangée) de la graine g (g ≥ 1 pour le LFSR).
pub fn matrice(r: &Recette, g: u32, u: &mut [f32]) {
    let n = r.c * r.p;
    match r.generateur {
        Generateur::Lfsr => {
            // graines de K bits : on prend g sur 16 bits (K ≤ 16), non nulle
            let mut s = ((g as u16) | if g == 0 { 1 } else { 0 }).max(1);
            for x in u.iter_mut().take(n) {
                s = lfsr_pas(s);
                *x = (s as f32 - 32768.0) / 32768.0;
            }
        }
        Generateur::Hache => {
            for (i, x) in u.iter_mut().take(n).enumerate() {
                let h = hache(g.wrapping_mul(0x0100_0193) ^ 0xA5A5_0000, i as u32);
                *x = ((h >> 8) as f32) / 8_388_608.0 - 1.0;
            }
        }
    }
}

/// Pseudo-inverse (UᵀU)⁻¹Uᵀ (P × C) par Cholesky ; rend faux si UᵀU est singulière.
pub fn pseudo_inverse(u: &[f32], c: usize, p: usize, pinv: &mut [f32]) -> bool {
    let mut a = vec![0.0f64; p * p];
    for i in 0..p {
        for j in 0..p {
            let mut s = 0.0;
            for r in 0..c {
                s += u[r * p + i] as f64 * u[r * p + j] as f64;
            }
            a[i * p + j] = s;
        }
    }
    // Cholesky a = L Lᵀ
    let mut l = vec![0.0f64; p * p];
    for i in 0..p {
        for j in 0..=i {
            let mut s = a[i * p + j];
            for k in 0..j {
                s -= l[i * p + k] * l[j * p + k];
            }
            if i == j {
                if s <= 1e-12 {
                    return false;
                }
                l[i * p + i] = s.sqrt();
            } else {
                l[i * p + j] = s / l[j * p + j];
            }
        }
    }
    // pinv = a⁻¹ Uᵀ : résoudre a z = colonne r de Uᵀ pour chaque r
    for r in 0..c {
        let mut y = vec![0.0f64; p];
        for i in 0..p {
            let mut s = u[r * p + i] as f64;
            for k in 0..i {
                s -= l[i * p + k] * y[k];
            }
            y[i] = s / l[i * p + i];
        }
        let mut z = vec![0.0f64; p];
        for i in (0..p).rev() {
            let mut s = y[i];
            for k in i + 1..p {
                s -= l[k * p + i] * z[k];
            }
            z[i] = s / l[i * p + i];
        }
        for i in 0..p {
            pinv[i * c + r] = z[i] as f32;
        }
    }
    true
}

/// Toutes les matrices et pseudo-inverses d'une recette (graines 1 .. 2^K − 1 ; la graine 0 est
/// exclue pour le LFSR, gardée hors d'usage pour le mélange afin de comparer à nombre égal).
pub struct Banque {
    pub r: Recette,
    pub u: Vec<f32>,
    pub pinv: Vec<f32>,
    pub valides: Vec<bool>,
}

impl Banque {
    pub fn new(r: Recette) -> Banque {
        let ng = 1usize << r.k;
        let n = r.c * r.p;
        let mut u = vec![0.0f32; ng * n];
        let mut pinv = vec![0.0f32; ng * n];
        let mut valides = vec![false; ng];
        for g in 1..ng {
            let (us, ps) = (&mut u[g * n..(g + 1) * n], &mut pinv[g * n..(g + 1) * n]);
            matrice(&r, g as u32, us);
            valides[g] = pseudo_inverse(us, r.c, r.p, ps);
        }
        Banque { r, u, pinv, valides }
    }

    /// Meilleure (graine, exposant, coefficients) pour le bloc w ; rend l'erreur et la reconstruction.
    pub fn coder(&self, w: &[f32], rec: &mut [f32]) -> (u32, f64) {
        let (c, p) = (self.r.c, self.r.p);
        let n = c * p;
        let mut meilleure = (0u32, f64::INFINITY);
        let mut t = vec![0.0f32; p];
        let mut q = vec![0.0f32; p];
        let mut y = vec![0.0f32; c];
        for g in 1..self.valides.len() {
            if !self.valides[g] {
                continue;
            }
            let (us, ps) = (&self.u[g * n..(g + 1) * n], &self.pinv[g * n..(g + 1) * n]);
            let mut amax = 0.0f32;
            for i in 0..p {
                let mut s = 0.0f32;
                for r in 0..c {
                    s += ps[i * c + r] * w[r];
                }
                t[i] = s;
                amax = amax.max(s.abs());
            }
            // exposant partagé : le plus petit 2^e tel que |t| / 2^e ≤ 7,5 (entiers −8 .. 7)
            let e = if amax > 0.0 { (amax / 7.5).log2().ceil() } else { 0.0 };
            let pas = e.exp2();
            for i in 0..p {
                q[i] = (t[i] / pas).round().clamp(-8.0, 7.0) * pas;
            }
            let mut err = 0.0f64;
            for r in 0..c {
                let mut s = 0.0f32;
                for i in 0..p {
                    s += us[r * p + i] * q[i];
                }
                y[r] = s;
                err += ((w[r] - s) as f64).powi(2);
            }
            if err < meilleure.1 {
                meilleure = (g as u32, err);
                rec[..c].copy_from_slice(&y);
            }
        }
        meilleure
    }
}

impl Banque {
    /// Code tous les blocs d'une rangée ; boucle extérieure sur les graines (chaque matrice reste en
    /// registres et en cache pendant qu'elle essaie tous les blocs). Rend l'erreur totale.
    pub fn coder_rangee(&self, w: &[f32]) -> f64 {
        let (c, p) = (self.r.c, self.r.p);
        assert!(c <= 16 && p <= 8);
        let n = c * p;
        let nbl = w.len() / c;
        let mut meilleur = vec![f32::INFINITY; nbl];
        for g in 1..self.valides.len() {
            if !self.valides[g] {
                continue;
            }
            let (us, ps) = (&self.u[g * n..(g + 1) * n], &self.pinv[g * n..(g + 1) * n]);
            for b in 0..nbl {
                let wb = &w[b * c..(b + 1) * c];
                let mut t = [0.0f32; 8];
                let mut amax = 0.0f32;
                for i in 0..p {
                    let mut s = 0.0f32;
                    for r in 0..c {
                        s += ps[i * c + r] * wb[r];
                    }
                    t[i] = s;
                    amax = amax.max(s.abs());
                }
                // exposant partagé : le plus petit 2^e ≥ amax / 7,5 (par les bits du f32)
                let a = amax / 7.5;
                let pas = if a > 0.0 {
                    let bits = a.to_bits();
                    let ex = ((bits >> 23) & 0xFF) as i32 - 127 + if bits & 0x7F_FFFF != 0 { 1 } else { 0 };
                    f32::from_bits(((ex + 127) as u32) << 23)
                } else {
                    1.0
                };
                for i in 0..p {
                    t[i] = (t[i] / pas).round().clamp(-8.0, 7.0) * pas;
                }
                let mut err = 0.0f32;
                for r in 0..c {
                    let mut s = 0.0f32;
                    for i in 0..p {
                        s += us[r * p + i] * t[i];
                    }
                    let d = wb[r] - s;
                    err += d * d;
                }
                if err < meilleur[b] {
                    meilleur[b] = err;
                }
            }
        }
        meilleur.iter().map(|&e| e as f64).sum()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn periode_maximale() {
        let mut s: u16 = 1;
        let mut n = 0u32;
        loop {
            s = lfsr_pas(s);
            n += 1;
            if s == 1 {
                break;
            }
            assert!(n <= 65535);
        }
        assert_eq!(n, 65535);
    }

    #[test]
    fn bloc_engendre_retrouve_exactement() {
        // témoin : un bloc qui est exactement U(g) · t quantifiable se retrouve à erreur nulle
        let r = Recette { c: 8, p: 3, k: 10, generateur: Generateur::Hache };
        let b = Banque::new(r);
        let g = 417usize;
        let n = r.c * r.p;
        let us = &b.u[g * n..(g + 1) * n];
        let t = [3.0f32 * 0.25, -5.0 * 0.25, 7.0 * 0.25];
        let mut w = vec![0.0f32; 8];
        for row in 0..8 {
            for i in 0..3 {
                w[row] += us[row * 3 + i] * t[i];
            }
        }
        let mut rec = vec![0.0f32; 8];
        let (gg, err) = b.coder(&w, &mut rec);
        assert!(err < 1e-9, "graine {gg}, erreur {err}");
        // la version par rangée rend la même erreur
        let e2 = b.coder_rangee(&w);
        assert!(e2 < 1e-9, "{e2}");
    }
}
