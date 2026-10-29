//! Les poids, ramenés en f64 sans aucun arrondi, et le produit d'une matrice par un lot de vecteurs.
//!
//! Exactitude de la déquantification (démontrée, pas supposée) :
//! - **Q8_0** : bloc de 34 octets, `d` en f16 puis 32 entiers i8 ; poids = d · q. Un f16 a 11 bits
//!   de mantisse, un i8 en a 7 : le produit tient en 18 bits, donc exact en f64 (53 bits).
//! - **MXFP4** : bloc de 17 octets, `e` (E8M0) puis 16 octets ; le demi-octet faible de l'octet j
//!   porte l'élément j, le fort l'élément j + 16 (`dequantize_row_mxfp4`, ggml-quants.c, lu dans
//!   llama.cpp b11515, MIT). Poids = K[code] · 2^(e − 128), K = {0, 1, 2, 3, 4, 6, 8, 12} signés par
//!   le bit 3 (grandeurs E2M1 doublées, d'où l'exposant −128 et non −127). K tient en 4 bits et
//!   2^(e − 128) est une puissance de deux dans l'étendue normale du f64 pour tout e de 0 à 255 :
//!   le poids est exact. `e = 255` (NaN selon la norme OCP MX) est compté à part par `compter_e255`.
//! - **F32**, **F16** : conversion exacte vers f64.
//!
//! Le produit scalaire est en f64 avec un ordre fixé (huit accumulateurs, réduction en arbre fixe) :
//! le résultat ne dépend ni du nombre de fils ni de l'ordonnancement.

use anyhow::{Result, bail};
use half::f16;
use rayon::prelude::*;

use crate::gguf::{GGML_F16, GGML_F32, GGML_MXFP4, GGML_Q8_0, octets_rangee};

/// Les valeurs E2M1 doublées, indexées par le code de 4 bits (bit 3 = signe).
pub const K_MXFP4: [f64; 16] = [0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, -0.0, -1.0, -2.0, -3.0, -4.0, -6.0, -8.0, -12.0];

/// 2^(e − 128), exact.
#[inline]
pub fn echelle_e8m0_demi(e: u8) -> f64 {
    // exposant f64 non biaisé e − 128 ∈ [−128, 127] : biais 1023, toujours normal.
    f64::from_bits(((e as u64) + 1023 - 128) << 52)
}

/// Une matrice gardée dans ses octets d'origine : `lignes` rangées de `colonnes` éléments.
pub struct Matrice {
    pub type_ggml: u32,
    pub lignes: usize,
    pub colonnes: usize,
    pub octets_ligne: usize,
    pub octets: Vec<u8>,
}

impl Matrice {
    pub fn nouvelle(type_ggml: u32, lignes: usize, colonnes: usize, octets: Vec<u8>) -> Result<Matrice> {
        let octets_ligne = octets_rangee(type_ggml, colonnes as u64)? as usize;
        if octets.len() != octets_ligne * lignes {
            bail!("matrice {lignes} × {colonnes} de type {type_ggml} : {} octets au lieu de {}", octets.len(), octets_ligne * lignes);
        }
        Ok(Matrice { type_ggml, lignes, colonnes, octets_ligne, octets })
    }

    /// Écrit la rangée `r` en f64 dans `dst` (longueur `colonnes`).
    pub fn ligne(&self, r: usize, dst: &mut [f64]) {
        let o = &self.octets[r * self.octets_ligne..(r + 1) * self.octets_ligne];
        rangee_f64(self.type_ggml, o, dst);
    }

    /// y[p · lignes + r] = Σ_c W[r, c] · x[p · colonnes + c], pour p < n (sans biais).
    ///
    /// **Chaque y[p, r] vaut exactement `scalaire(W[r], x[p])`**, au bit : le pavage ci-dessous ne
    /// change que l'ordre dans lequel les produits scalaires sont *calculés*, jamais l'ordre des
    /// opérations à l'intérieur de l'un d'eux (témoin `produit_egal_scalaire_au_bit`).
    ///
    /// Pavage (reprise du 2026-10-15, lot R) : la première version relisait, pour chaque rangée de
    /// W, les n vecteurs d'entrée en entier ; pour les 5 110 positions de R1 (10 fenêtres), x pèse
    /// 5 110 × 2 880 × 8 o = 118 Mo, hors du cache L3 (24 Mo), et la matrice de sortie du 20b
    /// (201 088 rangées) aurait tiré 201 088 × 118 Mo ≈ 23,7 To de la mémoire vive, soit de l'ordre
    /// de 4·10⁵ s à 60 Go/s [calc.]. Ici : les positions par paquets de `SUPER` (256 × 23 Kio ≈
    /// 5,9 Mo, tenus en L3), les rangées par blocs de `BLOC` déquantifiées une fois par paquet
    /// (32 × 23 Kio ≈ 737 Kio, en L2), les positions d'un paquet par tuiles de `TUILE`, et quatre
    /// produits scalaires à la fois (deux rangées × deux positions, huit chaînes de FMA
    /// indépendantes) pour remplir les deux unités FMA d'un cœur.
    pub fn produit(&self, x: &[f64], n: usize, y: &mut [f64]) {
        assert_eq!(x.len(), n * self.colonnes);
        assert_eq!(y.len(), n * self.lignes);
        let (c, l) = (self.colonnes, self.lignes);
        let sortie = PointeurPartage(y.as_mut_ptr());
        for p0 in (0..n).step_by(SUPER) {
            let p1 = (p0 + SUPER).min(n);
            let xs = &x[p0 * c..p1 * c];
            (0..l.div_ceil(BLOC)).into_par_iter().for_each(|b| {
                let r0 = b * BLOC;
                let r1 = (r0 + BLOC).min(l);
                let nr = r1 - r0;
                let mut w = vec![0.0f64; nr * c];
                for r in r0..r1 {
                    self.ligne(r, &mut w[(r - r0) * c..(r - r0 + 1) * c]);
                }
                let ecrire = |p: usize, r: usize, v: f64| {
                    // SAFETY : la tâche b n'écrit que les rangées [r0, r1) de chaque position ; les
                    // blocs sont disjoints, et y vit plus longtemps que la boucle parallèle.
                    unsafe { *sortie.decaler((p0 + p) * l + r) = v };
                };
                for t0 in (0..p1 - p0).step_by(TUILE) {
                    let t1 = (t0 + TUILE).min(p1 - p0);
                    produits_tuile(&w, nr, c, xs, t0, t1, &mut |dr, p, v| ecrire(p, r0 + dr, v));
                }
            });
        }
    }

    /// Nombre de blocs MXFP4 dont l'échelle vaut 255 (NaN selon OCP MX ; 2^127 dans ggml).
    pub fn compter_e255(&self) -> u64 {
        if self.type_ggml != GGML_MXFP4 {
            return 0;
        }
        self.octets.chunks_exact(17).filter(|b| b[0] == 255).count() as u64
    }
}

/// **Imitation de llama.cpp, pas un calcul du modèle** : ramène des activations à ce que voit le
/// produit quantifié de ggml sur le processeur. Pour des poids MXFP4 ou Q8_0, ggml b11515 convertit
/// d'abord le vecteur d'entrée dans le type `vec_dot_type = Q8_0` (`type_traits_cpu` de
/// ggml-cpu.c ; `quantize_row_q8_0`, branche AVX2 de arch/x86/quants.c, MIT, lus le 2026-10-15) :
/// par bloc de 32, amax = max |x| en f32, d = amax / 127 stocké en f16, id = 127 / amax (0 si
/// amax = 0), q = arrondi au plus proche pair de x · id, valeur vue = q · f16(d). Sert à décomposer
/// l'écart entre la référence et llama.cpp (mesure « imitation » de R1) ; jamais dans la référence.
pub fn imiter_q8_0_ggml(x: &mut [f64]) {
    assert_eq!(x.len() % 32, 0, "activations : longueur multiple de 32 attendue");
    for bloc in x.chunks_exact_mut(32) {
        let xf: Vec<f32> = bloc.iter().map(|&v| v as f32).collect();
        let amax = xf.iter().fold(0.0f32, |m, v| m.max(v.abs()));
        let d = f16::from_f32(amax / 127.0).to_f64();
        let id = if amax != 0.0 { 127.0f32 / amax } else { 0.0 };
        for (o, v) in bloc.iter_mut().zip(xf.iter()) {
            *o = (v * id).round_ties_even() as f64 * d;
        }
    }
}

/// Positions par passe sur une matrice (voir `Matrice::produit`).
const SUPER: usize = 256;
/// Rangées déquantifiées ensemble par une tâche.
const BLOC: usize = 32;
/// Positions par tuile.
const TUILE: usize = 8;

/// Un pointeur partagé entre les tâches de `produit`, qui écrivent des indices disjoints.
#[derive(Clone, Copy)]
struct PointeurPartage(*mut f64);
// SAFETY : seules des écritures à des indices disjoints passent par ce pointeur (voir `produit`).
unsafe impl Send for PointeurPartage {}
unsafe impl Sync for PointeurPartage {}
impl PointeurPartage {
    /// # Safety
    /// `i` doit être dans le tampon d'origine et n'être écrit que par une seule tâche.
    unsafe fn decaler(self, i: usize) -> *mut f64 {
        unsafe { self.0.add(i) }
    }
}

/// Les produits scalaires des `nr` rangées de `w` (contiguës, `c` colonnes) par les positions
/// [t0, t1) de `xs` ; `rendre(rangée, position, valeur)`. Chaque valeur égale `scalaire` au bit.
fn produits_tuile(w: &[f64], nr: usize, c: usize, xs: &[f64], t0: usize, t1: usize, rendre: &mut dyn FnMut(usize, usize, f64)) {
    let rangee = |r: usize| &w[r * c..(r + 1) * c];
    let pos = |p: usize| &xs[p * c..(p + 1) * c];
    #[cfg(target_arch = "x86_64")]
    {
        if std::is_x86_feature_detected!("avx2") && std::is_x86_feature_detected!("fma") {
            let (r2, t2) = (nr / 2 * 2, t0 + (t1 - t0) / 2 * 2);
            for r in (0..r2).step_by(2) {
                for p in (t0..t2).step_by(2) {
                    // SAFETY : avx2 et fma présentes, vérifié ci-dessus.
                    let v = unsafe { scalaires_2x2_avx2(rangee(r), rangee(r + 1), pos(p), pos(p + 1)) };
                    rendre(r, p, v[0]);
                    rendre(r, p + 1, v[1]);
                    rendre(r + 1, p, v[2]);
                    rendre(r + 1, p + 1, v[3]);
                }
                for p in t2..t1 {
                    rendre(r, p, scalaire(rangee(r), pos(p)));
                    rendre(r + 1, p, scalaire(rangee(r + 1), pos(p)));
                }
            }
            for r in r2..nr {
                for p in t0..t1 {
                    rendre(r, p, scalaire(rangee(r), pos(p)));
                }
            }
            return;
        }
    }
    for r in 0..nr {
        for p in t0..t1 {
            rendre(r, p, scalaire(rangee(r), pos(p)));
        }
    }
}

/// Convertit une rangée d'octets ggml en f64.
pub fn rangee_f64(type_ggml: u32, o: &[u8], dst: &mut [f64]) {
    match type_ggml {
        GGML_F32 => {
            for (d, s) in dst.iter_mut().zip(o.chunks_exact(4)) {
                *d = f32::from_le_bytes(s.try_into().unwrap()) as f64;
            }
        }
        GGML_F16 => {
            for (d, s) in dst.iter_mut().zip(o.chunks_exact(2)) {
                *d = f16::from_le_bytes(s.try_into().unwrap()).to_f64();
            }
        }
        GGML_Q8_0 => {
            for (bloc, d) in o.chunks_exact(34).zip(dst.chunks_exact_mut(32)) {
                let echelle = f16::from_le_bytes([bloc[0], bloc[1]]).to_f64();
                for j in 0..32 {
                    d[j] = echelle * (bloc[2 + j] as i8) as f64;
                }
            }
        }
        GGML_MXFP4 => {
            for (bloc, d) in o.chunks_exact(17).zip(dst.chunks_exact_mut(32)) {
                let echelle = echelle_e8m0_demi(bloc[0]);
                for j in 0..16 {
                    let q = bloc[1 + j];
                    d[j] = K_MXFP4[(q & 0x0F) as usize] * echelle;
                    d[j + 16] = K_MXFP4[(q >> 4) as usize] * echelle;
                }
            }
        }
        t => panic!("type ggml {t} non lu par la référence"),
    }
}

/// Produit scalaire f64 à ordre fixé : huit accumulateurs (élément i dans l'accumulateur i mod 8),
/// puis ((a0 + a4) + (a2 + a6)) + ((a1 + a5) + (a3 + a7)), puis le reste dans l'ordre.
#[inline]
pub fn scalaire(a: &[f64], b: &[f64]) -> f64 {
    debug_assert_eq!(a.len(), b.len());
    #[cfg(target_arch = "x86_64")]
    {
        if std::is_x86_feature_detected!("avx2") && std::is_x86_feature_detected!("fma") {
            // SAFETY : les fonctions avx2 et fma sont présentes, vérifié ci-dessus.
            return unsafe { scalaire_avx2(a, b) };
        }
    }
    scalaire_portable(a, b)
}

#[inline]
fn scalaire_portable(a: &[f64], b: &[f64]) -> f64 {
    let n8 = a.len() / 8 * 8;
    let mut acc = [0.0f64; 8];
    let mut i = 0;
    while i < n8 {
        for k in 0..8 {
            acc[k] = a[i + k].mul_add(b[i + k], acc[k]);
        }
        i += 8;
    }
    let mut s = ((acc[0] + acc[4]) + (acc[2] + acc[6])) + ((acc[1] + acc[5]) + (acc[3] + acc[7]));
    for j in n8..a.len() {
        s = a[j].mul_add(b[j], s);
    }
    s
}

/// Même ordre et mêmes opérations que `scalaire_portable` (une FMA par terme), en registres AVX2 :
/// le résultat est identique au bit (témoin `scalaire_avx2_egal_portable`).
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
unsafe fn scalaire_avx2(a: &[f64], b: &[f64]) -> f64 {
    use std::arch::x86_64::*;
    let n8 = a.len() / 8 * 8;
    let pa = a.as_ptr();
    let pb = b.as_ptr();
    let mut lo = _mm256_setzero_pd(); // accumulateurs 0..3
    let mut hi = _mm256_setzero_pd(); // accumulateurs 4..7
    let mut i = 0;
    while i < n8 {
        unsafe {
            lo = _mm256_fmadd_pd(_mm256_loadu_pd(pa.add(i)), _mm256_loadu_pd(pb.add(i)), lo);
            hi = _mm256_fmadd_pd(_mm256_loadu_pd(pa.add(i + 4)), _mm256_loadu_pd(pb.add(i + 4)), hi);
        }
        i += 8;
    }
    unsafe { reduire_avx2(lo, hi, a, b, n8) }
}

/// La fin commune d'un produit scalaire AVX2 : les huit accumulateurs réduits dans l'ordre fixé de
/// `scalaire_portable`, puis le reste terme à terme. Partagée par `scalaire_avx2` et
/// `scalaires_2x2_avx2` : une seule écriture de l'ordre, donc une seule fonction calculée.
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
#[inline]
unsafe fn reduire_avx2(lo: std::arch::x86_64::__m256d, hi: std::arch::x86_64::__m256d, a: &[f64], b: &[f64], n8: usize) -> f64 {
    use std::arch::x86_64::*;
    let mut acc = [0.0f64; 8];
    unsafe {
        _mm256_storeu_pd(acc.as_mut_ptr(), lo);
        _mm256_storeu_pd(acc.as_mut_ptr().add(4), hi);
    }
    let mut s = ((acc[0] + acc[4]) + (acc[2] + acc[6])) + ((acc[1] + acc[5]) + (acc[3] + acc[7]));
    for j in n8..a.len() {
        s = a[j].mul_add(b[j], s);
    }
    s
}

/// Quatre produits scalaires à la fois, (a0·b0, a0·b1, a1·b0, a1·b1), chacun par **exactement**
/// la suite d'opérations de `scalaire_avx2` (mêmes FMA dans le même ordre sur ses deux
/// accumulateurs lo et hi, même réduction) : seules les quatre suites sont entrelacées, ce qui
/// donne huit chaînes de FMA indépendantes au lieu de deux. Témoin : `produit_egal_scalaire_au_bit`.
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
unsafe fn scalaires_2x2_avx2(a0: &[f64], a1: &[f64], b0: &[f64], b1: &[f64]) -> [f64; 4] {
    use std::arch::x86_64::*;
    let n = a0.len();
    assert!(a1.len() == n && b0.len() == n && b1.len() == n);
    let n8 = n / 8 * 8;
    let (pa0, pa1, pb0, pb1) = (a0.as_ptr(), a1.as_ptr(), b0.as_ptr(), b1.as_ptr());
    let z = _mm256_setzero_pd();
    let (mut lo00, mut hi00, mut lo01, mut hi01, mut lo10, mut hi10, mut lo11, mut hi11) = (z, z, z, z, z, z, z, z);
    let mut i = 0;
    while i < n8 {
        unsafe {
            let (x0l, x0h) = (_mm256_loadu_pd(pa0.add(i)), _mm256_loadu_pd(pa0.add(i + 4)));
            let (x1l, x1h) = (_mm256_loadu_pd(pa1.add(i)), _mm256_loadu_pd(pa1.add(i + 4)));
            let (y0l, y0h) = (_mm256_loadu_pd(pb0.add(i)), _mm256_loadu_pd(pb0.add(i + 4)));
            let (y1l, y1h) = (_mm256_loadu_pd(pb1.add(i)), _mm256_loadu_pd(pb1.add(i + 4)));
            lo00 = _mm256_fmadd_pd(x0l, y0l, lo00);
            hi00 = _mm256_fmadd_pd(x0h, y0h, hi00);
            lo01 = _mm256_fmadd_pd(x0l, y1l, lo01);
            hi01 = _mm256_fmadd_pd(x0h, y1h, hi01);
            lo10 = _mm256_fmadd_pd(x1l, y0l, lo10);
            hi10 = _mm256_fmadd_pd(x1h, y0h, hi10);
            lo11 = _mm256_fmadd_pd(x1l, y1l, lo11);
            hi11 = _mm256_fmadd_pd(x1h, y1h, hi11);
        }
        i += 8;
    }
    unsafe { [reduire_avx2(lo00, hi00, a0, b0, n8), reduire_avx2(lo01, hi01, a0, b1, n8), reduire_avx2(lo10, hi10, a1, b0, n8), reduire_avx2(lo11, hi11, a1, b1, n8)] }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn echelle_exacte() {
        assert_eq!(echelle_e8m0_demi(128), 1.0);
        assert_eq!(echelle_e8m0_demi(129), 2.0);
        assert_eq!(echelle_e8m0_demi(0), 2f64.powi(-128));
        assert_eq!(echelle_e8m0_demi(255), 2f64.powi(127));
    }

    #[test]
    fn mxfp4_ordre_des_demi_octets() {
        // Bloc : e = 128 (échelle 1), octet 0 = 0x91 : faible 1 → +1 (élément 0), fort 9 → −1 (élément 16).
        let mut bloc = [0u8; 17];
        bloc[0] = 128;
        bloc[1] = 0x91;
        bloc[16] = 0x7F; // octet 15 : faible F → −12 (élément 15), fort 7 → +12 (élément 31)
        let mut d = [0.0; 32];
        rangee_f64(GGML_MXFP4, &bloc, &mut d);
        assert_eq!(d[0], 1.0);
        assert_eq!(d[16], -1.0);
        assert_eq!(d[15], -12.0);
        assert_eq!(d[31], 12.0);
        assert!(d[1..15].iter().all(|&v| v == 0.0));
    }

    #[test]
    fn q8_0_exact() {
        let mut bloc = [0u8; 34];
        bloc[0..2].copy_from_slice(&f16::from_f32(0.5).to_le_bytes());
        bloc[2] = (-128i8) as u8;
        bloc[3] = 127;
        let mut d = [0.0; 32];
        rangee_f64(GGML_Q8_0, &bloc, &mut d);
        assert_eq!(d[0], -64.0);
        assert_eq!(d[1], 63.5);
    }

    #[test]
    fn scalaire_avx2_egal_portable() {
        let n = 2883;
        let a: Vec<f64> = (0..n).map(|i| ((i * 7919) % 1013) as f64 / 37.0 - 13.0).collect();
        let b: Vec<f64> = (0..n).map(|i| ((i * 104729) % 997) as f64 / 91.0 - 5.0).collect();
        assert_eq!(scalaire(&a, &b).to_bits(), scalaire_portable(&a, &b).to_bits());
    }

    /// Témoin du pavage : chaque sortie de `produit` égale `scalaire` au bit, sur des valeurs dont
    /// la somme dépend de l'ordre (réels non dyadiques), avec des bords partout : rangées hors des
    /// blocs de 32 et impaires, positions hors des tuiles de 8 et des paquets de 256, colonnes avec
    /// un reste de 3 après les groupes de 8. Cassures faites à la main le 2026-10-15 : (1) lo et hi
    /// échangés pour le seul produit a1·b1 du noyau 2 × 2 : le témoin TIENT, et c'est juste (la
    /// réduction (a0 + a4) + … est symétrique dans l'échange des deux moitiés : cassure mal choisie,
    /// pas témoin faible) ; (2) a1·b1 accumulé sur la seule chaîne lo (ordre réellement changé) :
    /// le témoin TOMBE, 304 sorties différentes sur 71 × 19.
    #[test]
    fn produit_egal_scalaire_au_bit() {
        for &(l, c, n) in &[(71usize, 2883usize, 19usize), (37, 43, 300), (3, 8, 1), (2, 16, 2)] {
            let w: Vec<u8> = (0..l * c).flat_map(|i| ((((i * 2654435761) % 10007) as f32) / 997.0 - 5.0).to_le_bytes()).collect();
            let m = Matrice::nouvelle(GGML_F32, l, c, w).unwrap();
            let x: Vec<f64> = (0..n * c).map(|i| (((i * 40503) % 9973) as f64 / 101.0 - 49.0) * 1.000_000_1).collect();
            let mut y = vec![0.0; n * l];
            m.produit(&x, n, &mut y);
            let mut ligne = vec![0.0; c];
            let mut differents = 0;
            for r in 0..l {
                m.ligne(r, &mut ligne);
                for p in 0..n {
                    if y[p * l + r].to_bits() != scalaire(&ligne, &x[p * c..(p + 1) * c]).to_bits() {
                        differents += 1;
                    }
                }
            }
            assert_eq!(differents, 0, "l={l} c={c} n={n}");
        }
    }

    /// L'imitation Q8_0 suit ggml : d = amax/127 en f16, q arrondi au plus proche pair. Témoin à
    /// la main : amax = 127 donne d = 1 et des valeurs entières gardées ; 2,5 · (127/127) s'arrondit
    /// à 2 (pair) et 3,5 à 4 ; un bloc nul reste nul.
    #[test]
    fn imitation_q8_0() {
        let mut x = vec![0.0f64; 64];
        x[0] = 127.0;
        x[1] = -63.0;
        x[2] = 2.5;
        x[3] = 3.5;
        x[4] = -2.5;
        imiter_q8_0_ggml(&mut x);
        assert_eq!(&x[..5], &[127.0, -63.0, 2.0, 4.0, -2.0]);
        assert!(x[32..].iter().all(|&v| v == 0.0));
        // amax = 1 : d = f16(1/127), q = round(x · 127).
        let mut y = vec![0.0f64; 32];
        y[0] = 1.0;
        y[1] = 0.5;
        imiter_q8_0_ggml(&mut y);
        let d = f16::from_f32(1.0f32 / 127.0).to_f64();
        assert_eq!(y[0], 127.0 * d);
        assert_eq!(y[1], 64.0 * d); // 63,5 → 64 (pair)
    }

    #[test]
    fn produit_independant_du_decoupage() {
        // 70 lignes (blocs de 32 incomplets), 64 colonnes F32, 5 vecteurs.
        let (l, c, n) = (70, 64, 5);
        let w: Vec<u8> = (0..l * c).flat_map(|i| ((i % 17) as f32 - 8.0).to_le_bytes()).collect();
        let m = Matrice::nouvelle(GGML_F32, l, c, w).unwrap();
        let x: Vec<f64> = (0..n * c).map(|i| (i % 11) as f64 * 0.25).collect();
        let mut y = vec![0.0; n * l];
        m.produit(&x, n, &mut y);
        let mut ligne = vec![0.0; c];
        for r in 0..l {
            m.ligne(r, &mut ligne);
            for p in 0..n {
                let attendu: f64 = (0..c).map(|k| ligne[k] * x[p * c + k]).sum();
                assert_eq!(y[p * l + r], attendu, "r={r} p={p}");
            }
        }
    }
}
