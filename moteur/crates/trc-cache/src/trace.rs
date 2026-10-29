//! La trace de routage : pour chaque jeton et chaque couche, les k experts choisis par le routeur.
//!
//! Format (celui de `outils/chargement_localite.py`, étude 04, que produit le traceur de
//! `outils/gptoss-routage/`) : un jeton par ligne, les couches séparées par « | », les experts d'une
//! couche séparés par des blancs ; une ligne qui commence par « # » est un commentaire ; une ligne
//! « E=128 » déclare le nombre d'experts par couche (sinon E = plus grand identifiant + 1, comme
//! l'outil Python). Exemple pour deux couches et k = 2 :
//!
//! ```text
//! # commentaire
//! E=32
//! 3 17 | 5 9
//! 3 40 | 5 2
//! ```
//!
//! Écart voulu avec l'outil Python, qui accepte tout : ici, rien ne se devine (§ 4.1, principe 6).
//! Une ligne qui n'a pas le même nombre de couches que la première, une couche qui n'a pas k
//! experts, un identifiant hors de [0, E) ou une trace vide sont refusés avec la ligne fautive.

use std::fmt;
use std::path::Path;

/// Une trace de routage rangée à plat : `choix[(t · L + l) · k + i]` est le i-ème expert choisi
/// par la couche l au jeton t, dans l'ordre où le traceur l'a écrit.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Trace {
    /// E, experts par couche.
    pub experts: u16,
    /// L, couches.
    pub couches: u16,
    /// k, experts choisis par couche et par jeton.
    pub k: u16,
    /// T, jetons.
    pub jetons: u32,
    /// Les choix, T · L · k identifiants.
    pub choix: Vec<u16>,
    /// Les lignes de commentaire, sans le « # » (provenance de la trace).
    pub commentaires: Vec<String>,
}

impl Trace {
    /// Les k experts de la couche `couche` au jeton `jeton`.
    pub fn groupe(&self, jeton: usize, couche: usize) -> &[u16] {
        let k = self.k as usize;
        let debut = (jeton * self.couches as usize + couche) * k;
        &self.choix[debut..debut + k]
    }

    /// Nombre total d'accès : T · L · k.
    pub fn acces(&self) -> u64 {
        self.choix.len() as u64
    }

    /// Lit une trace depuis son texte.
    pub fn depuis_texte(texte: &str) -> Result<Trace> {
        let mut e_declare: Option<u16> = None;
        let mut commentaires = Vec::new();
        let mut choix: Vec<u16> = Vec::new();
        let (mut couches, mut k) = (0usize, 0usize);
        let mut jetons = 0u32;
        for (n, brute) in texte.lines().enumerate() {
            let ligne = brute.trim();
            let numero = n + 1;
            if ligne.is_empty() {
                continue;
            }
            if let Some(c) = ligne.strip_prefix('#') {
                commentaires.push(c.trim().to_string());
                continue;
            }
            if let Some(v) = ligne.strip_prefix("E=") {
                let e: u16 = v.trim().parse().map_err(|_| ErreurTrace::Ligne {
                    numero,
                    raison: format!("« E= » illisible : {v:?}"),
                })?;
                if e == 0 {
                    return Err(ErreurTrace::Ligne { numero, raison: "E = 0".into() });
                }
                e_declare = Some(e);
                continue;
            }
            let parts: Vec<&str> = ligne.split('|').collect();
            if jetons == 0 {
                couches = parts.len();
            } else if parts.len() != couches {
                return Err(ErreurTrace::Ligne {
                    numero,
                    raison: format!("{} couches au lieu de {couches}", parts.len()),
                });
            }
            for (l, p) in parts.iter().enumerate() {
                let avant = choix.len();
                for mot in p.split_whitespace() {
                    let x: u16 = mot.parse().map_err(|_| ErreurTrace::Ligne {
                        numero,
                        raison: format!("identifiant d'expert illisible : {mot:?}"),
                    })?;
                    choix.push(x);
                }
                let n_couche = choix.len() - avant;
                if jetons == 0 && l == 0 {
                    k = n_couche;
                    if k == 0 {
                        return Err(ErreurTrace::Ligne { numero, raison: "couche vide".into() });
                    }
                } else if n_couche != k {
                    return Err(ErreurTrace::Ligne {
                        numero,
                        raison: format!("couche {l} : {n_couche} experts au lieu de {k}"),
                    });
                }
            }
            jetons += 1;
        }
        if jetons == 0 {
            return Err(ErreurTrace::Vide);
        }
        let max = *choix.iter().max().expect("trace non vide");
        let experts = match e_declare {
            Some(e) => {
                if max >= e {
                    return Err(ErreurTrace::HorsBornes { expert: max, experts: e });
                }
                e
            }
            None => max.checked_add(1).ok_or(ErreurTrace::HorsBornes { expert: max, experts: u16::MAX })?,
        };
        if couches > u16::MAX as usize || k > u16::MAX as usize {
            return Err(ErreurTrace::Ligne { numero: 0, raison: "dimensions hors de u16".into() });
        }
        Ok(Trace { experts, couches: couches as u16, k: k as u16, jetons, choix, commentaires })
    }
}

/// Lit une trace de routage (format de `outils/chargement_localite.py`).
pub fn lire_trace(chemin: &Path) -> Result<Trace> {
    let texte = std::fs::read_to_string(chemin)
        .map_err(|e| ErreurTrace::Lecture { chemin: chemin.display().to_string(), message: e.to_string() })?;
    Trace::depuis_texte(&texte)
}

/// Les erreurs de lecture d'une trace.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ErreurTrace {
    /// Le fichier n'a pas pu être lu.
    Lecture { chemin: String, message: String },
    /// Une ligne est mal formée.
    Ligne { numero: usize, raison: String },
    /// Un identifiant d'expert dépasse le E déclaré.
    HorsBornes { expert: u16, experts: u16 },
    /// Aucune ligne de jeton.
    Vide,
}

impl fmt::Display for ErreurTrace {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ErreurTrace::Lecture { chemin, message } => write!(f, "trace illisible ({chemin}) : {message}"),
            ErreurTrace::Ligne { numero, raison } => write!(f, "trace, ligne {numero} : {raison}"),
            ErreurTrace::HorsBornes { expert, experts } => {
                write!(f, "trace : expert {expert} hors de [0, {experts})")
            }
            ErreurTrace::Vide => write!(f, "trace vide (aucune ligne de jeton)"),
        }
    }
}

impl std::error::Error for ErreurTrace {}

/// Le résultat des fonctions de ce module (§ 5.7 : `lire_trace(…) -> Result<Trace>`).
pub type Result<T> = std::result::Result<T, ErreurTrace>;
