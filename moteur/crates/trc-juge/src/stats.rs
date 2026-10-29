//! Divergence KL, premier choix, perplexité, et leurs incertitudes.
//!
//! Définitions (les mêmes que llama-perplexity, réécrites ici en f64 depuis leur sens) :
//! - P est la base (entrée codée sur 16 bits), Q la distribution jugée (logits bruts ou entrée
//!   décodée, renormalisés par log-somme-exp) ;
//! - KL(P ‖ Q) = Σ_{i : log p_i > −16} p_i (log p_i − log q_i) ; les termes de p < e⁻¹⁶ sont omis,
//!   comme dans llama.cpp (le codage les a de toute façon écrasés) ;
//! - premier choix identique : argmax de P = argmax de Q (premier indice en cas d'égalité) ;
//! - NLL du jeton suivant pour P et pour Q ; PPL = exp(moyenne des NLL) ;
//! - incertitude d'une moyenne : √((⟨x²⟩ − ⟨x⟩²)/(n − 1)) ; d'une proportion : √(p(1 − p)/(n − 1)) ;
//! - rapport des perplexités : ln PPL(Q) − ln PPL(P), incertitude avec la covariance des NLL ;
//! - quantile f : interpolation linéaire entre les valeurs triées d'indices ⌊f(n − 1)⌋ et suivant.

use serde::Serialize;

use crate::kld::Entree;

/// Le résultat d'une position.
#[derive(Clone, Copy, Debug, Serialize)]
pub struct Position {
    pub kl: f64,
    pub meme_premier: bool,
    pub nll_q: f64,
    pub nll_p: f64,
    pub dp: f64,
    pub premier_p: u32,
    pub premier_q: u32,
}

/// KL d'une position : base codée `p`, logits jugés `q` (longueur n_vocab, bruts : normalisés ici
/// par log-somme-exp), jeton suivant `suivant`.
pub fn position<F: Fn(usize) -> f64>(p: &Entree, q: F, n: usize, suivant: usize) -> Position {
    position_avec(p, q, n, suivant, true)
}

/// KL d'une position quand le jugé est **lui-même une entrée décodée** d'un `.kld` : ses valeurs
/// sont déjà des log-probabilités, normalisées par le log-somme-exp exact des logits d'origine
/// (`coder_entree`), et ne se renormalisent pas.
///
/// Pourquoi (trouvé le 2026-10-15 par le témoin d'identité de `juge comparer`) : le codage écrase
/// tous les jetons sous max − 16 sur le code 0, donc sur log_p_min, au lieu de leur vraie valeur,
/// bien plus petite ; renormaliser l'entrée décodée ajoute log Σ p̂ ≈ N₀ · e^{log_p_min}, mesuré
/// 1,11·10⁻³ en moyenne sur les 2 550 positions de gpt-oss-20b (un fichier jugé contre lui-même),
/// 16 fois le seuil de 7·10⁻⁵. Sans renormalisation, un fichier contre lui-même donne 0 exactement.
pub fn position_decodee(p: &Entree, q: &Entree, n: usize, suivant: usize) -> Position {
    position_avec(p, |i| q.log_p(i) as f64, n, suivant, false)
}

fn position_avec<F: Fn(usize) -> f64>(p: &Entree, q: F, n: usize, suivant: usize, normaliser: bool) -> Position {
    let mut max_q = f64::NEG_INFINITY;
    let mut imax_q = 0;
    for i in 0..n {
        let v = q(i);
        if v > max_q {
            max_q = v;
            imax_q = i;
        }
    }
    let lse_q = if normaliser {
        let mut s = 0.0;
        for i in 0..n {
            s += (q(i) - max_q).exp();
        }
        max_q + s.ln()
    } else {
        0.0
    };
    let mut kl = 0.0;
    let mut imax_p = 0;
    let mut lp_max = f64::NEG_INFINITY;
    for i in 0..n {
        let lp = p.log_p(i) as f64;
        if lp > lp_max {
            lp_max = lp;
            imax_p = i;
        }
        if lp > -16.0 {
            kl += lp.exp() * (lp - (q(i) - lse_q));
        }
    }
    let nll_q = lse_q - q(suivant);
    let nll_p = -(p.log_p(suivant) as f64);
    Position { kl, meme_premier: imax_p == imax_q, nll_q, nll_p, dp: (-nll_q).exp() - (-nll_p).exp(), premier_p: imax_p as u32, premier_q: imax_q as u32 }
}

#[derive(Clone, Debug, Serialize)]
pub struct Resume {
    pub n: usize,
    pub kl_moyenne: f64,
    pub kl_incertitude: f64,
    pub kl_mediane: f64,
    pub kl_p90: f64,
    pub kl_p99: f64,
    pub kl_p999: f64,
    pub kl_max: f64,
    pub kl_min: f64,
    pub meme_premier: f64,
    pub meme_premier_incertitude: f64,
    /// Intervalle de Wilson à 95 % du taux de premier choix identique.
    pub meme_premier_wilson95: (f64, f64),
    pub ppl_q: f64,
    pub ppl_p: f64,
    pub ln_rapport_ppl: f64,
    pub ln_rapport_ppl_incertitude: f64,
    pub dp_rms: f64,
}

fn moyenne_incertitude(v: impl Iterator<Item = f64> + Clone) -> (f64, f64) {
    let n = v.clone().count() as f64;
    let s: f64 = v.clone().sum();
    let s2: f64 = v.map(|x| x * x).sum();
    let m = s / n;
    let var = s2 / n - m * m;
    (m, if var > 0.0 && n > 10.0 { (var / (n - 1.0)).sqrt() } else { 0.0 })
}

pub fn quantile(tries: &[f64], f: f64) -> f64 {
    if f <= 0.0 {
        return tries[0];
    }
    if f >= 1.0 {
        return tries[tries.len() - 1];
    }
    let p = f * (tries.len() - 1) as f64;
    let i = p as usize;
    let r = p - i as f64;
    (1.0 - r) * tries[i] + r * tries[(i + 1).min(tries.len() - 1)]
}

/// Intervalle de score de Wilson à 95 % (z = 1,959964) pour k succès sur n.
pub fn wilson95(k: usize, n: usize) -> (f64, f64) {
    let z = 1.959963984540054;
    let (k, n) = (k as f64, n as f64);
    let p = k / n;
    let d = 1.0 + z * z / n;
    let c = (p + z * z / (2.0 * n)) / d;
    let h = z * (p * (1.0 - p) / n + z * z / (4.0 * n * n)).sqrt() / d;
    (c - h, c + h)
}

pub fn resumer(ps: &[Position]) -> Resume {
    let n = ps.len();
    let (kl_m, kl_i) = moyenne_incertitude(ps.iter().map(|p| p.kl));
    let mut tries: Vec<f64> = ps.iter().map(|p| p.kl).collect();
    tries.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let med = if n % 2 == 0 { 0.5 * (tries[n / 2] + tries[n / 2 - 1]) } else { tries[n / 2] };
    let k = ps.iter().filter(|p| p.meme_premier).count();
    let top = k as f64 / n as f64;
    let (lq, lq_i) = moyenne_incertitude(ps.iter().map(|p| p.nll_q));
    let (lp, lp_i) = moyenne_incertitude(ps.iter().map(|p| p.nll_p));
    let cov = if n >= 10 {
        let sab: f64 = ps.iter().map(|p| p.nll_q * p.nll_p).sum();
        (sab / n as f64 - lq * lp) / (n as f64 - 1.0)
    } else {
        0.0
    };
    let dp2: f64 = ps.iter().map(|p| p.dp * p.dp).sum::<f64>() / n as f64;
    Resume {
        n,
        kl_moyenne: kl_m,
        kl_incertitude: kl_i,
        kl_mediane: med,
        kl_p90: quantile(&tries, 0.90),
        kl_p99: quantile(&tries, 0.99),
        kl_p999: quantile(&tries, 0.999),
        kl_max: tries[n - 1],
        kl_min: tries[0],
        meme_premier: top,
        meme_premier_incertitude: (top * (1.0 - top) / (n as f64 - 1.0)).sqrt(),
        meme_premier_wilson95: wilson95(k, n),
        ppl_q: lq.exp(),
        ppl_p: lp.exp(),
        ln_rapport_ppl: lq - lp,
        ln_rapport_ppl_incertitude: (lq_i * lq_i + lp_i * lp_i - 2.0 * cov).max(0.0).sqrt(),
        dp_rms: dp2.sqrt(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::kld::{coder_entree, mots_par_entree};

    #[test]
    fn kl_nulle_contre_soi_meme_et_positive_sinon() {
        let n = 500;
        let a: Vec<f64> = (0..n).map(|i| ((i * 13) % 37) as f64 * 0.3).collect();
        let mut mots = vec![0u16; mots_par_entree(n)];
        coder_entree(&a, &mut mots);
        let e = Entree::depuis(&mots, n);
        let soi = position(&e, |i| a[i], n, 3);
        // Borne dérivée : |KL| ≤ Σ p_i |δ_i| + O(δ²) ≤ max |δ| ≤ pas / 2 (+ arrondis f32), et pas =
        // (max − min)/65 535. Une première borne de 1e-7, posée au jugé, est tombée à 5,7e-6 : le
        // biais d'arrondi ne se moyenne pas sur 37 valeurs distinctes. Barrée, remplacée par le pas.
        assert!(soi.kl.abs() < e.pas as f64, "{} contre pas {}", soi.kl, e.pas);
        assert!(soi.meme_premier);
        let b: Vec<f64> = (0..n).map(|i| a[i] + ((i * 7) % 5) as f64 * 0.4).collect();
        let autre = position(&e, |i| b[i], n, 3);
        assert!(autre.kl > 1e-3, "{}", autre.kl);
    }

    /// Témoin de `position_decodee` : une entrée jugée contre elle-même donne une KL nulle au bit,
    /// même quand le codage a écrasé des jetons sous max − 16 ; cassure : la renormaliser (l'ancien
    /// chemin, `position` sur les valeurs décodées) donne la KL positive de log Σ p̂.
    #[test]
    fn entree_decodee_contre_elle_meme() {
        let n = 20_000;
        // Un jeton dominant, et 19 999 jetons de 18 à 40 sous lui : tous écrasés sur le code 0.
        let a: Vec<f64> = (0..n).map(|i| if i == 7 { 30.0 } else { 12.0 - (i % 23) as f64 }).collect();
        let mut mots = vec![0u16; mots_par_entree(n)];
        coder_entree(&a, &mut mots);
        let e = Entree::depuis(&mots, n);
        let juste = position_decodee(&e, &e, n, 7);
        assert_eq!(juste.kl, 0.0);
        let renormalisee = position(&e, |i| e.log_p(i) as f64, n, 7);
        assert!(renormalisee.kl > 1e-4, "{}", renormalisee.kl);
    }

    #[test]
    fn wilson_connu() {
        // 95 sur 100 : [0,8882 ; 0,9785] (valeurs de référence de la formule).
        let (a, b) = wilson95(95, 100);
        assert!((a - 0.8882).abs() < 1e-3 && (b - 0.9785).abs() < 1e-3, "{a} {b}");
    }
}
