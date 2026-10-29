//! Les opérations de gpt-oss en f64, chacune seule (les « noyau_* » du § 5.9, contre lesquels le
//! lot K juge ses noyaux). Leur définition vient de l'implémentation de référence publiée par OpenAI
//! (`gpt_oss/torch/model.py`, dépôt openai/gpt-oss, Apache-2.0, lu le 2026-10-15) et de la
//! configuration publiée du modèle (`config.json` de openai/gpt-oss-20b) ; elles ont été comparées à
//! llama.cpp b11515 (MIT). Rien n'est copié ; chaque formule est écrite ici depuis sa définition.

/// RMSNorm : y_i = x_i / √(moyenne(x²) + ε) · w_i.
pub fn rmsnorm(x: &[f64], w: &[f64], eps: f64, y: &mut [f64]) {
    let n = x.len();
    let mut s = 0.0;
    for &v in x {
        s += v * v;
    }
    let r = 1.0 / (s / n as f64 + eps).sqrt();
    for i in 0..n {
        y[i] = x[i] * r * w[i];
    }
}

/// Variante de la rampe de YaRN.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum VarianteYarn {
    /// La définition d'OpenAI (`truncate: false` dans la configuration publiée) : bornes de la
    /// rampe réelles, non arrondies. C'est le modèle.
    OpenAi,
    /// La forme de llama.cpp b11515 (`ggml_rope_yarn_corr_dims`) : borne basse arrondie vers le bas,
    /// borne haute vers le haut, puis bornées à [0, d − 1]. Gardée pour mesurer l'écart.
    LlamaCpp,
}

/// Fréquences de rotation de YaRN, déjà calculées pour une tête.
#[derive(Clone, Debug)]
pub struct Rope {
    pub dim_tete: usize,
    /// inv_freq[i] pour la paire i (i < d/2).
    pub inv_freq: Vec<f64>,
    /// Facteur de concentration de YaRN, appliqué au cosinus et au sinus (donc deux fois au
    /// produit q · k) : 0,1 · ln(s) + 1.
    pub concentration: f64,
    pub bas: f64,
    pub haut: f64,
}

impl Rope {
    /// base θ, facteur s, contexte d'origine L0, β rapide (32), β lent (1), dimension d.
    pub fn yarn(base: f64, facteur: f64, ctx_origine: f64, beta_rapide: f64, beta_lent: f64, d: usize, v: VarianteYarn) -> Rope {
        let demi = d / 2;
        let freq: Vec<f64> = (0..demi).map(|i| base.powf((2 * i) as f64 / d as f64)).collect();
        if facteur <= 1.0 {
            return Rope { dim_tete: d, inv_freq: freq.iter().map(|f| 1.0 / f).collect(), concentration: 1.0, bas: 0.0, haut: 0.0 };
        }
        let concentration = 0.1 * facteur.ln() + 1.0;
        // Dimension de correction : la paire dont la longueur d'onde 2π/inv_freq fait β tours sur L0.
        let corr = |beta: f64| (demi as f64) * (ctx_origine / (beta * 2.0 * std::f64::consts::PI)).ln() / base.ln();
        let (mut bas, mut haut) = (corr(beta_rapide), corr(beta_lent));
        if v == VarianteYarn::LlamaCpp {
            bas = bas.floor().max(0.0);
            haut = haut.ceil().min((d - 1) as f64);
        }
        let inv_freq = (0..demi)
            .map(|i| {
                let interpolation = 1.0 / (facteur * freq[i]);
                let extrapolation = 1.0 / freq[i];
                let rampe = ((i as f64 - bas) / (haut - bas)).clamp(0.0, 1.0);
                let masque = 1.0 - rampe;
                interpolation * (1.0 - masque) + extrapolation * masque
            })
            .collect();
        Rope { dim_tete: d, inv_freq, concentration, bas, haut }
    }

    /// Rotation « par moitiés » (NEOX) d'une tête en place, à la position `pos` :
    /// x1 = x[0..d/2], x2 = x[d/2..d] ; o1 = x1 cos − x2 sin ; o2 = x2 cos + x1 sin.
    pub fn tourner(&self, x: &mut [f64], pos: usize) {
        let demi = self.dim_tete / 2;
        for i in 0..demi {
            let angle = pos as f64 * self.inv_freq[i];
            let (s, c) = angle.sin_cos();
            let (c, s) = (c * self.concentration, s * self.concentration);
            let (a, b) = (x[i], x[i + demi]);
            x[i] = a * c - b * s;
            x[i + demi] = b * c + a * s;
        }
    }
}

/// Attention d'une requête (une tête) sur `n` clés, avec le puits appris de la tête :
/// poids_j = exp(échelle · q·k_j) / (Σ_i exp(échelle · q·k_i) + exp(puits)) ; sortie = Σ poids_j v_j.
/// `cles` et `valeurs` : n vecteurs de longueur d, contigus.
pub fn attention_tete(q: &[f64], cles: &[f64], valeurs: &[f64], n: usize, puits: f64, echelle: f64, sortie: &mut [f64], scores: &mut Vec<f64>) {
    let d = q.len();
    scores.clear();
    let mut m = puits;
    for j in 0..n {
        let k = &cles[j * d..(j + 1) * d];
        let mut s = 0.0;
        for t in 0..d {
            s += q[t] * k[t];
        }
        let s = s * echelle;
        if s > m {
            m = s;
        }
        scores.push(s);
    }
    let mut z = (puits - m).exp();
    for s in scores.iter_mut() {
        *s = (*s - m).exp();
        z += *s;
    }
    sortie.iter_mut().for_each(|o| *o = 0.0);
    for j in 0..n {
        let w = scores[j] / z;
        let v = &valeurs[j * d..(j + 1) * d];
        for t in 0..d {
            sortie[t] += w * v[t];
        }
    }
}

/// Routeur : les k plus grands logits (biais compris), ordre décroissant, égalité : plus petit
/// indice d'abord ; poids = softmax des k valeurs retenues.
pub fn routeur_topk(logits: &[f64], k: usize) -> (Vec<usize>, Vec<f64>) {
    let mut idx: Vec<usize> = (0..logits.len()).collect();
    idx.sort_by(|&a, &b| logits[b].partial_cmp(&logits[a]).unwrap().then(a.cmp(&b)));
    idx.truncate(k);
    let m = logits[idx[0]];
    let e: Vec<f64> = idx.iter().map(|&i| (logits[i] - m).exp()).collect();
    let z: f64 = e.iter().sum();
    (idx, e.iter().map(|v| v / z).collect())
}

/// SwiGLU bornée de gpt-oss : g ← min(g, 7) ; u ← borne(u, −7, 7) ; g · σ(1,702 g) · (u + 1).
pub fn swiglu_oai(g: f64, u: f64) -> f64 {
    const ALPHA: f64 = 1.702;
    const LIMITE: f64 = 7.0;
    let g = g.min(LIMITE);
    let u = u.clamp(-LIMITE, LIMITE);
    g / (1.0 + (-ALPHA * g).exp()) * (u + 1.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bornes_de_la_rampe_gpt_oss() {
        // Calcul posé (64 dimensions, base 150 000, L0 = 4 096) : bas = 32 ln(4096/(64π)) / ln(150000)
        // ≈ 8,0928 ; haut = 32 ln(4096/(2π)) / ln(150000) ≈ 17,3981. llama.cpp : 8 et 18.
        let r = Rope::yarn(150000.0, 32.0, 4096.0, 32.0, 1.0, 64, VarianteYarn::OpenAi);
        assert!((r.bas - 8.0928).abs() < 1e-3, "{}", r.bas);
        assert!((r.haut - 17.3981).abs() < 1e-3, "{}", r.haut);
        let l = Rope::yarn(150000.0, 32.0, 4096.0, 32.0, 1.0, 64, VarianteYarn::LlamaCpp);
        assert_eq!((l.bas, l.haut), (8.0, 18.0));
        assert!((r.concentration - (0.1 * 32f64.ln() + 1.0)).abs() < 1e-15);
        // Hors de la rampe, les deux variantes coïncident.
        for i in (0..8).chain(18..32) {
            assert_eq!(r.inv_freq[i], l.inv_freq[i], "paire {i}");
        }
        assert!(r.inv_freq[12] != l.inv_freq[12]);
    }

    #[test]
    fn rotation_conserve_la_norme_a_la_concentration_pres() {
        let r = Rope::yarn(150000.0, 32.0, 4096.0, 32.0, 1.0, 64, VarianteYarn::OpenAi);
        let mut x: Vec<f64> = (0..64).map(|i| (i as f64 * 0.37).sin()).collect();
        let n0: f64 = x.iter().map(|v| v * v).sum();
        r.tourner(&mut x, 333);
        let n1: f64 = x.iter().map(|v| v * v).sum();
        assert!((n1 / n0 - r.concentration * r.concentration).abs() < 1e-12);
    }

    #[test]
    fn puits_dans_le_denominateur() {
        // Une clé, score 0, puits 0 : poids 1/2.
        let q = [0.0; 4];
        let k = [1.0; 4];
        let v = [2.0, 4.0, 6.0, 8.0];
        let mut o = [0.0; 4];
        let mut s = Vec::new();
        attention_tete(&q, &k, &v, 1, 0.0, 0.125, &mut o, &mut s);
        assert_eq!(o, [1.0, 2.0, 3.0, 4.0]);
    }

    #[test]
    fn topk_egalites_et_poids() {
        let (i, w) = routeur_topk(&[1.0, 3.0, 3.0, 0.0, 2.0], 3);
        assert_eq!(i, vec![1, 2, 4]);
        assert!((w.iter().sum::<f64>() - 1.0).abs() < 1e-15);
        assert!((w[0] - w[1]).abs() < 1e-15);
    }

    #[test]
    fn swiglu_bornes() {
        assert_eq!(swiglu_oai(0.0, 5.0), 0.0);
        let a = swiglu_oai(100.0, 100.0);
        let b = swiglu_oai(7.0, 7.0);
        assert_eq!(a, b);
        assert!((swiglu_oai(1.0, -1.0)).abs() < 1e-300);
    }
}
