//! La frontière : la base de l'architecture B (signe + classe de magnitude parmi
//! {0 ; 0,5} {1 ; 1,5 ; 2} {3 ; 4} {6}), centres de classe = centres de gravité pondérés par le
//! carré de l'échelle (étude 07 § 4.2, mesure F1 de l'arbitre). Refaite ici par un second chemin :
//! comptes exacts (e, code) sur les 12 tenseurs de F1, centres recalculés, erreur relative.

/// Classe de magnitude de l'indice m = code & 7 (magnitudes doublées 0, 1, 2, 3, 4, 6, 8, 12).
pub const CLASSE: [usize; 8] = [0, 0, 1, 1, 1, 2, 2, 3];
pub const MAG2: [f64; 8] = [0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0];

/// Comptes C[e][code] d'un ensemble de blocs.
#[derive(Clone)]
pub struct Comptes(pub Vec<[u64; 16]>);

impl Comptes {
    pub fn new() -> Comptes {
        Comptes(vec![[0u64; 16]; 256])
    }
    pub fn ajouter(&mut self, autre: &Comptes) {
        for (a, b) in self.0.iter_mut().zip(autre.0.iter()) {
            for i in 0..16 {
                a[i] += b[i];
            }
        }
    }
    /// Poids par magnitude, pondérés par 4^(e − 128) : Σ_e C[e][m] 4^(e−128), signes confondus.
    fn poids_mag(&self) -> [f64; 8] {
        let mut w = [0.0f64; 8];
        for (e, c) in self.0.iter().enumerate() {
            let p = (4.0f64).powi(e as i32 - 128);
            for q in 0..16 {
                w[q & 7] += c[q] as f64 * p;
            }
        }
        w
    }
    /// Centres de classe (unités doublées) : centres de gravité pondérés.
    pub fn centres(&self) -> [f64; 4] {
        let w = self.poids_mag();
        let mut num = [0.0f64; 4];
        let mut den = [0.0f64; 4];
        for m in 0..8 {
            num[CLASSE[m]] += w[m] * MAG2[m];
            den[CLASSE[m]] += w[m];
        }
        let mut c = [0.0; 4];
        for k in 0..4 {
            c[k] = if den[k] > 0.0 { num[k] / den[k] } else { 0.0 };
        }
        c
    }
    /// (erreur absolue, énergie) de la base aux centres donnés (énergie en unités 4^(e−128)).
    pub fn erreur(&self, centres: &[f64; 4]) -> (f64, f64) {
        let w = self.poids_mag();
        let mut err = 0.0;
        let mut en = 0.0;
        for m in 0..8 {
            err += w[m] * (MAG2[m] - centres[CLASSE[m]]).powi(2);
            en += w[m] * MAG2[m] * MAG2[m];
        }
        (err, en)
    }
}

/// Reconstruction de la base d'un poids : signe · centre[classe] · 2^(e − 128).
#[inline]
pub fn base_valeur(code: u8, e: u8, centres: &[f64; 4]) -> f32 {
    let m = (code & 7) as usize;
    let s = if code & 8 != 0 { -1.0 } else { 1.0 };
    (s * centres[CLASSE[m]] * (2.0f64).powi(e as i32 - 128)) as f32
}
