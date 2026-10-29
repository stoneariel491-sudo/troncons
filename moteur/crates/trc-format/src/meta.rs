//! Les paires clé-valeur au format GGUF v3 (spécification publique de GGUF, lue et écrite ici
//! de zéro) : celles de la section MÉTA (§ 4.4) et celles du compagnon `.vocab.gguf` (§ 4.13).
//!
//! Une paire : u64 longueur de la clé, octets de la clé (UTF-8), u32 type, valeur. Types : 0 u8,
//! 1 i8, 2 u16, 3 i16, 4 u32, 5 i32, 6 f32, 7 booléen, 8 chaîne (u64 longueur + octets),
//! 9 tableau (u32 type des éléments, u64 nombre, éléments), 10 u64, 11 i64, 12 f64.

use crate::ErreurFormat;

#[derive(Clone, Debug, PartialEq)]
pub enum ValeurMeta {
    U(u64),
    I(i64),
    F(f64),
    Bool(bool),
    Chaine(String),
    /// Les éléments d'un tableau ne sont pas recopiés (le vocabulaire en compte 201 088) ;
    /// ils restent dans les octets bruts de la paire.
    Tableau { type_elem: u32, n: u64 },
}

#[derive(Clone, Debug, PartialEq)]
pub struct PaireMeta {
    pub cle: String,
    pub type_gguf: u32,
    /// Début et fin de la paire entière dans les octets lus (clé comprise).
    pub debut: usize,
    pub fin: usize,
    pub valeur: ValeurMeta,
}

impl PaireMeta {
    pub fn entier(&self) -> Option<u64> {
        match self.valeur {
            ValeurMeta::U(v) => Some(v),
            ValeurMeta::I(v) if v >= 0 => Some(v as u64),
            _ => None,
        }
    }
    pub fn reel(&self) -> Option<f64> {
        match self.valeur {
            ValeurMeta::F(v) => Some(v),
            _ => None,
        }
    }
    pub fn chaine(&self) -> Option<&str> {
        match &self.valeur {
            ValeurMeta::Chaine(s) => Some(s),
            _ => None,
        }
    }
}

struct Curseur<'a> {
    b: &'a [u8],
    p: usize,
}

impl<'a> Curseur<'a> {
    fn prendre(&mut self, n: usize) -> Result<&'a [u8], ErreurFormat> {
        if self.p.checked_add(n).is_none_or(|f| f > self.b.len()) {
            return Err(ErreurFormat::Limites(format!("paire GGUF tronquée à l'octet {}", self.p)));
        }
        let s = &self.b[self.p..self.p + n];
        self.p += n;
        Ok(s)
    }
    fn u32(&mut self) -> Result<u32, ErreurFormat> {
        Ok(u32::from_le_bytes(self.prendre(4)?.try_into().unwrap()))
    }
    fn u64(&mut self) -> Result<u64, ErreurFormat> {
        Ok(u64::from_le_bytes(self.prendre(8)?.try_into().unwrap()))
    }
    fn chaine(&mut self) -> Result<String, ErreurFormat> {
        let n = self.u64()?;
        let n = usize::try_from(n).map_err(|_| ErreurFormat::Limites("chaîne GGUF trop longue".into()))?;
        let s = self.prendre(n)?;
        String::from_utf8(s.to_vec()).map_err(|_| ErreurFormat::Limites(format!("chaîne GGUF non UTF-8 à l'octet {}", self.p)))
    }
    fn sauter_chaine(&mut self) -> Result<(), ErreurFormat> {
        let n = self.u64()?;
        let n = usize::try_from(n).map_err(|_| ErreurFormat::Limites("chaîne GGUF trop longue".into()))?;
        self.prendre(n)?;
        Ok(())
    }
    fn scalaire(&mut self, t: u32) -> Result<ValeurMeta, ErreurFormat> {
        Ok(match t {
            0 => ValeurMeta::U(self.prendre(1)?[0] as u64),
            1 => ValeurMeta::I(self.prendre(1)?[0] as i8 as i64),
            2 => ValeurMeta::U(u16::from_le_bytes(self.prendre(2)?.try_into().unwrap()) as u64),
            3 => ValeurMeta::I(i16::from_le_bytes(self.prendre(2)?.try_into().unwrap()) as i64),
            4 => ValeurMeta::U(self.u32()? as u64),
            5 => ValeurMeta::I(self.u32()? as i32 as i64),
            6 => ValeurMeta::F(f32::from_le_bytes(self.prendre(4)?.try_into().unwrap()) as f64),
            7 => ValeurMeta::Bool(self.prendre(1)?[0] != 0),
            8 => ValeurMeta::Chaine(self.chaine()?),
            10 => ValeurMeta::U(self.u64()?),
            11 => ValeurMeta::I(self.u64()? as i64),
            12 => ValeurMeta::F(f64::from_le_bytes(self.prendre(8)?.try_into().unwrap())),
            _ => return Err(ErreurFormat::Champ { champ: "type de valeur GGUF".into(), attendu: "0 à 12".into(), lu: t.to_string() }),
        })
    }
    fn valeur(&mut self, t: u32, profondeur: u32) -> Result<ValeurMeta, ErreurFormat> {
        if t != 9 {
            return self.scalaire(t);
        }
        if profondeur > 4 {
            return Err(ErreurFormat::Limites("tableaux GGUF imbriqués trop profondément".into()));
        }
        let te = self.u32()?;
        let n = self.u64()?;
        for _ in 0..n {
            match te {
                8 => self.sauter_chaine()?,
                9 => {
                    self.valeur(9, profondeur + 1)?;
                }
                0 | 1 | 7 => {
                    self.prendre(1)?;
                }
                2 | 3 => {
                    self.prendre(2)?;
                }
                4..=6 => {
                    self.prendre(4)?;
                }
                10..=12 => {
                    self.prendre(8)?;
                }
                _ => return Err(ErreurFormat::Champ { champ: "type d'élément GGUF".into(), attendu: "0 à 12".into(), lu: te.to_string() }),
            }
        }
        Ok(ValeurMeta::Tableau { type_elem: te, n })
    }
}

/// Lit `n` paires à partir du début de `b` ; chaque paire garde son étendue dans `b`.
pub fn lire_paires(b: &[u8], n: u64) -> Result<Vec<PaireMeta>, ErreurFormat> {
    let mut c = Curseur { b, p: 0 };
    let mut v = Vec::new();
    for _ in 0..n {
        let debut = c.p;
        let cle = c.chaine()?;
        let t = c.u32()?;
        let valeur = c.valeur(t, 0)?;
        v.push(PaireMeta { cle, type_gguf: t, debut, fin: c.p, valeur });
    }
    Ok(v)
}

/// Une paire GGUF de type chaîne, sérialisée.
pub fn paire_chaine(cle: &str, valeur: &str) -> Vec<u8> {
    let mut b = Vec::with_capacity(20 + cle.len() + valeur.len());
    b.extend_from_slice(&(cle.len() as u64).to_le_bytes());
    b.extend_from_slice(cle.as_bytes());
    b.extend_from_slice(&8u32.to_le_bytes());
    b.extend_from_slice(&(valeur.len() as u64).to_le_bytes());
    b.extend_from_slice(valeur.as_bytes());
    b
}
