//! La lecture par codons glissants : le « ribosome » des poids.
//!
//! Le vivant lit un brin d'ADN par une fenêtre de trois bases (un codon) qui avance ; chaque codon
//! se traduit, par une table fixe et dégénérée (le code génétique : 64 codons pour 21 sens), en un
//! acide aminé. Ici :
//! - le **brin** est une suite de bits stockée sur le disque ;
//! - la **fenêtre** fait `l` bits et avance de `kb` bits à chaque pas ; chaque pas rend `v` poids ;
//! - le **code génétique** traduit une fenêtre `s` (l bits) en `v` valeurs : un mélangeur de bits
//!   `hache(s, j)` choisit une case d'une petite table de `2^q` valeurs (dégénérée : 2^l fenêtres
//!   pour 2^q sens), table apprise sur l'organisme (les poids d'un tenseur) par Lloyd.
//!
//! Le débit est `kb / v` bits par poids, plus la fenêtre initiale (`l − kb` bits par brin). Deux
//! poids voisins partagent `l − kb` bits de leur fenêtre : le brin est un code en treillis (le
//! treillis « à décalage » de Mao et Gray, repris par QTIP), et le meilleur brin pour une suite de
//! poids donnée se trouve exactement par l'algorithme de Viterbi.
//!
//! Le décodeur ne lit que le brin et la table : c'est ce qui se lit sur le disque.

/// Mélangeur de 32 bits, écrit ici (multiplications impaires et décalages-xor) ; `j` choisit l'une
/// des `v` sorties d'une même fenêtre.
#[inline(always)]
pub fn hache(s: u32, j: u32) -> u32 {
    let mut h = s ^ j.wrapping_mul(0x632B_E5AB);
    h = h.wrapping_mul(0x9E37_79B1);
    h ^= h >> 16;
    h = h.wrapping_mul(0x85EB_CA77);
    h ^= h >> 13;
    h = h.wrapping_mul(0xC2B2_AE3D);
    h ^= h >> 16;
    h
}

/// Mélangeur bon marché (deux opérations) : une multiplication impaire, les bits forts.
#[inline(always)]
pub fn hache_court(s: u32, j: u32) -> u32 {
    (s ^ (j << 20)).wrapping_mul(0x9E37_79B1).wrapping_add(0x7F4A_7C15).wrapping_mul(0x2545_F491)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Melangeur {
    Fort,
    Court,
}

/// La forme du treillis : fenêtre `l`, avance `kb`, `v` poids par pas, table de `2^q` valeurs.
#[derive(Clone, Copy, Debug)]
pub struct Forme {
    pub l: u32,
    pub kb: u32,
    pub v: u32,
    pub q: u32,
    pub melangeur: Melangeur,
}

impl Forme {
    pub fn debit(&self) -> f64 {
        self.kb as f64 / self.v as f64
    }
    /// Bits d'un brin de `n` poids (n multiple de v) : la première fenêtre entière, puis kb par pas.
    pub fn bits_brin(&self, n: usize) -> u64 {
        let pas = (n / self.v as usize) as u64;
        self.l as u64 + (pas - 1) * self.kb as u64
    }
    /// Index de table de la sortie j de la fenêtre s.
    #[inline(always)]
    pub fn index(&self, s: u32, j: u32) -> usize {
        let h = match self.melangeur {
            Melangeur::Fort => hache(s, j),
            Melangeur::Court => hache_court(s, j),
        };
        (h >> (32 - self.q)) as usize
    }
}

/// Le code génétique d'un treillis : la table, et ses valeurs dépliées pour chaque fenêtre.
#[derive(Clone)]
pub struct Code {
    pub forme: Forme,
    pub table: Vec<f32>,
    /// valeurs[s · v + j] = table[index(s, j)]
    pub valeurs: Vec<f32>,
    /// indices[s · v + j] = index(s, j)
    pub indices: Vec<u32>,
}

impl Code {
    pub fn nouveau(forme: Forme, table: Vec<f32>) -> Code {
        assert_eq!(table.len(), 1 << forme.q);
        let ns = 1usize << forme.l;
        let v = forme.v as usize;
        let mut indices = vec![0u32; ns * v];
        for s in 0..ns {
            for j in 0..v {
                indices[s * v + j] = forme.index(s as u32, j as u32) as u32;
            }
        }
        let mut c = Code { forme, table, valeurs: vec![0.0; ns * v], indices };
        c.deplier();
        c
    }
    pub fn deplier(&mut self) {
        for (val, &i) in self.valeurs.iter_mut().zip(self.indices.iter()) {
            *val = self.table[i as usize];
        }
    }
}

/// Mémoire de travail d'un Viterbi (une par fil).
pub struct Travail {
    d: Vec<f32>,
    m: Vec<f32>,
    retour: Vec<u8>,
}

impl Travail {
    pub fn new() -> Travail {
        Travail { d: Vec::new(), m: Vec::new(), retour: Vec::new() }
    }
}

/// Résultat du codage d'un brin.
pub struct Brin {
    /// fenêtre à chaque pas (pas = n / v)
    pub etats: Vec<u32>,
    /// erreur pondérée Σ ω (x − x̂)²
    pub erreur: f64,
}

/// Le meilleur brin (au sens de Σ ω_i (x_i − x̂_i)²) pour la suite `x` : Viterbi exact.
///
/// État = fenêtre de l bits. Transition s → s' ssi les l − kb bits forts de s' sont les l − kb
/// bits faibles de s : s' = ((s << kb) | b) mod 2^l. Les prédécesseurs de s' partagent donc
/// u = s' >> kb, et ce sont les s = (t << (l − kb)) | u, t < 2^kb : le minimum sur les
/// prédécesseurs ne dépend que de u. Coût par pas : 2^l comparaisons et 2^l · v évaluations.
pub fn viterbi(x: &[f32], om: &[f32], code: &Code, w: &mut Travail) -> Brin {
    let f = code.forme;
    let (l, kb, v) = (f.l as usize, f.kb as usize, f.v as usize);
    assert!(kb <= 8 && kb < l);
    let n = x.len();
    assert_eq!(n % v, 0);
    let pas = n / v;
    let ns = 1usize << l;
    let nu = 1usize << (l - kb);
    let nt = 1usize << kb;
    w.d.resize(ns, 0.0);
    w.m.resize(nu, 0.0);
    w.retour.resize(pas * nu, 0);
    let vals = &code.valeurs;
    // pas 0 : toute fenêtre est permise
    {
        let xs = &x[0..v];
        let os = &om[0..v];
        for s in 0..ns {
            let mut e = 0.0f32;
            for j in 0..v {
                let r = xs[j] - vals[s * v + j];
                e += os[j] * r * r;
            }
            w.d[s] = e;
        }
    }
    for p in 1..pas {
        // minimum sur les prédécesseurs, par u : les 2^kb tranches contiguës de d
        let (m, d) = (&mut w.m, &w.d);
        let ret = &mut w.retour[p * nu..(p + 1) * nu];
        m.copy_from_slice(&d[0..nu]);
        ret.fill(0);
        for t in 1..nt {
            let tranche = &d[t * nu..(t + 1) * nu];
            for u in 0..nu {
                let c = tranche[u];
                let plus_petit = c < m[u];
                m[u] = if plus_petit { c } else { m[u] };
                ret[u] = if plus_petit { t as u8 } else { ret[u] };
            }
        }
        let xs = &x[p * v..(p + 1) * v];
        let os = &om[p * v..(p + 1) * v];
        let d = &mut w.d;
        if v == 1 {
            let (x0, o0) = (xs[0], os[0]);
            match nt {
                2 => etendre::<2>(d, m, vals, x0, o0),
                4 => etendre::<4>(d, m, vals, x0, o0),
                8 => etendre::<8>(d, m, vals, x0, o0),
                16 => etendre::<16>(d, m, vals, x0, o0),
                _ => {
                    for u in 0..nu {
                        let base = m[u];
                        for b in 0..nt {
                            let s = (u << kb) | b;
                            let r = x0 - vals[s];
                            d[s] = base + o0 * r * r;
                        }
                    }
                }
            }
        } else {
            for u in 0..nu {
                let base = m[u];
                for b in 0..nt {
                    let s = (u << kb) | b;
                    let mut e = base;
                    for j in 0..v {
                        let r = xs[j] - vals[s * v + j];
                        e += os[j] * r * r;
                    }
                    d[s] = e;
                }
            }
        }
    }
    // fin : la meilleure fenêtre, puis le chemin à rebours
    let mut meilleur = 0usize;
    for s in 1..ns {
        if w.d[s] < w.d[meilleur] {
            meilleur = s;
        }
    }
    let mut etats = vec![0u32; pas];
    etats[pas - 1] = meilleur as u32;
    let mut s = meilleur;
    for p in (1..pas).rev() {
        let u = s >> kb;
        let t = w.retour[p * nu + u] as usize;
        s = (t << (l - kb)) | u;
        etats[p - 1] = s as u32;
    }
    // erreur recalculée en f64 sur le chemin (la somme f32 du Viterbi n'est qu'un guide)
    let mut erreur = 0.0f64;
    for p in 0..pas {
        let s = etats[p] as usize;
        for j in 0..v {
            let r = (x[p * v + j] - vals[s * v + j]) as f64;
            erreur += om[p * v + j] as f64 * r * r;
        }
    }
    Brin { etats, erreur }
}

/// d[u · NT + b] = m[u] + ω (x − vals[u · NT + b])², par paquets de NT (vectorisable).
#[inline(always)]
fn etendre<const NT: usize>(d: &mut [f32], m: &[f32], vals: &[f32], x0: f32, o0: f32) {
    for ((dc, vc), &base) in d.chunks_exact_mut(NT).zip(vals.chunks_exact(NT)).zip(m.iter()) {
        let dc: &mut [f32; NT] = dc.try_into().unwrap();
        let vc: &[f32; NT] = vc.try_into().unwrap();
        for b in 0..NT {
            let r = x0 - vc[b];
            dc[b] = base + o0 * r * r;
        }
    }
}

/// Le brin en bits : la première fenêtre (l bits), puis les kb bits neufs de chaque pas.
pub fn ecrire_brin(etats: &[u32], f: &Forme) -> Vec<u64> {
    let total = f.l as u64 + (etats.len() as u64 - 1) * f.kb as u64;
    let mut mots = vec![0u64; total.div_ceil(64) as usize + 1];
    let mut pos = 0u64;
    let mut pousser = |val: u64, nb: u32, mots: &mut Vec<u64>| {
        for i in (0..nb).rev() {
            let bit = (val >> i) & 1;
            mots[(pos / 64) as usize] |= bit << (63 - pos % 64);
            pos += 1;
        }
    };
    pousser(etats[0] as u64, f.l, &mut mots);
    let masque = (1u64 << f.kb) - 1;
    for &s in &etats[1..] {
        pousser(s as u64 & masque, f.kb, &mut mots);
    }
    mots
}

/// Le décodeur : il ne lit que le brin et la table. Le poids p · v + j vaut
/// table[index(fenêtre_p, j)], fenêtre_p = bits [p · kb, p · kb + l) du brin.
pub fn lire_brin(mots: &[u64], n: usize, f: &Forme, table: &[f32], sortie: &mut [f32]) {
    let v = f.v as usize;
    let pas = n / v;
    let masque = (1u64 << f.l) - 1;
    for p in 0..pas {
        let debut = p as u64 * f.kb as u64;
        let (i, o) = ((debut / 64) as usize, debut % 64);
        // 128 bits à partir du mot i, puis la fenêtre de l bits au rang o
        let fen = if o + f.l as u64 <= 64 {
            (mots[i] >> (64 - o - f.l as u64)) & masque
        } else {
            let haut = mots[i] << (o + f.l as u64 - 64);
            let bas = mots[i + 1] >> (128 - o - f.l as u64);
            (haut | bas) & masque
        } as u32;
        for j in 0..v {
            sortie[p * v + j] = table[f.index(fen, j as u32)];
        }
    }
}

/// Quantile de la loi normale centrée réduite (Acklam, approximation rationnelle, erreur relative
/// < 1,15·10⁻⁹), écrit ici pour initialiser la table sur une source gaussienne.
pub fn quantile_normal(p: f64) -> f64 {
    let a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
    let b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01];
    let c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
    let d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00];
    let pl = 0.02425;
    if p < pl {
        let q = (-2.0 * p.ln()).sqrt();
        (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    } else if p <= 1.0 - pl {
        let q = p - 0.5;
        let r = q * q;
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    } else {
        let q = (-2.0 * (1.0 - p).ln()).sqrt();
        -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    }
}

/// Table gaussienne : les quantiles aux milieux des 2^q cases de probabilité égale.
pub fn table_gaussienne(q: u32) -> Vec<f32> {
    let n = 1usize << q;
    (0..n).map(|i| quantile_normal((i as f64 + 0.5) / n as f64) as f32).collect()
}

/// Table empirique : les quantiles d'un échantillon (pondérés par ω), aux milieux des cases.
pub fn table_empirique(x: &[f32], om: &[f32], q: u32) -> Vec<f32> {
    let mut paires: Vec<(f32, f32)> = x.iter().zip(om.iter()).map(|(&a, &b)| (a, b)).collect();
    paires.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
    let total: f64 = paires.iter().map(|p| p.1 as f64).sum();
    let n = 1usize << q;
    let mut table = vec![0.0f32; n];
    let mut acc = 0.0f64;
    let mut k = 0usize;
    for (i, t) in table.iter_mut().enumerate() {
        let cible = (i as f64 + 0.5) / n as f64 * total;
        while k + 1 < paires.len() && acc + paires[k].1 as f64 <= cible {
            acc += paires[k].1 as f64;
            k += 1;
        }
        *t = paires[k].0;
    }
    table
}

/// Accumulateurs de Lloyd pour la table : Σ ω x et Σ ω par case.
pub fn accumuler_lloyd(x: &[f32], om: &[f32], etats: &[u32], code: &Code, num: &mut [f64], den: &mut [f64]) {
    let v = code.forme.v as usize;
    for (p, &s) in etats.iter().enumerate() {
        for j in 0..v {
            let i = code.indices[s as usize * v + j] as usize;
            num[i] += om[p * v + j] as f64 * x[p * v + j] as f64;
            den[i] += om[p * v + j] as f64;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn brin_ecrit_puis_lu_rend_la_reconstruction() {
        let f = Forme { l: 12, kb: 2, v: 1, q: 8, melangeur: Melangeur::Fort };
        let code = Code::nouveau(f, table_gaussienne(8));
        let x: Vec<f32> = (0..999).map(|i| ((i * 37 % 101) as f32 / 50.0) - 1.0).collect();
        let om = vec![1.0f32; x.len()];
        let mut w = Travail::new();
        let b = viterbi(&x, &om, &code, &mut w);
        let mots = ecrire_brin(&b.etats, &f);
        let mut y = vec![0.0f32; x.len()];
        lire_brin(&mots, x.len(), &f, &code.table, &mut y);
        let mut e = 0.0f64;
        for i in 0..x.len() {
            e += ((x[i] - y[i]) as f64).powi(2);
        }
        assert!((e - b.erreur).abs() < 1e-6 * (1.0 + e), "{e} {}", b.erreur);
        // transitions légales
        for p in 1..b.etats.len() {
            assert_eq!(b.etats[p] >> 2, b.etats[p - 1] & ((1 << 10) - 1));
        }
    }

    #[test]
    fn brin_v2_ecrit_puis_lu() {
        let f = Forme { l: 14, kb: 5, v: 2, q: 9, melangeur: Melangeur::Court };
        let code = Code::nouveau(f, table_gaussienne(9));
        let x: Vec<f32> = (0..1000).map(|i| ((i * 53 % 97) as f32 / 40.0) - 1.2).collect();
        let om: Vec<f32> = (0..1000).map(|i| 1.0 + (i % 3) as f32).collect();
        let mut w = Travail::new();
        let b = viterbi(&x, &om, &code, &mut w);
        let mots = ecrire_brin(&b.etats, &f);
        let mut y = vec![0.0f32; x.len()];
        lire_brin(&mots, x.len(), &f, &code.table, &mut y);
        let mut e = 0.0f64;
        for i in 0..x.len() {
            e += om[i] as f64 * ((x[i] - y[i]) as f64).powi(2);
        }
        assert!((e - b.erreur).abs() < 1e-6 * (1.0 + e));
    }

    #[test]
    fn quantile_symetrique() {
        assert!(quantile_normal(0.5).abs() < 1e-12);
        assert!((quantile_normal(0.975) - 1.959963984540054).abs() < 1e-8);
        assert!((quantile_normal(0.01) + 2.326347874040841).abs() < 1e-8);
    }
}
