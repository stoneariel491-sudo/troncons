//! Lecture d'un fichier GGUF v3, écrite depuis la spécification publique du format (dépôt ggml,
//! `docs/gguf.md`, MIT) et vérifiée sur les fichiers gpt-oss de la machine. Aucun code repris.
//!
//! Disposition (petit-boutiste) :
//! ```text
//!  u8[4] « GGUF » | u32 version (3) | u64 n_tenseurs | u64 n_paires
//!  n_paires × (chaîne clé, u32 type, valeur)
//!  n_tenseurs × (chaîne nom, u32 n_dims, u64 ne[n_dims], u32 type ggml, u64 décalage relatif)
//!  bourrage jusqu'au multiple de `general.alignment` (32 par défaut) : début des données
//! ```
//! Une chaîne est `u64 longueur` puis ses octets UTF-8. Un tableau est `u32 type, u64 n, valeurs`.

use std::collections::HashMap;
use std::fs::File;
use std::io::{BufReader, Read};
use std::os::windows::fs::FileExt;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, anyhow, bail};

/// Types ggml que la référence sait lire (les seuls présents dans les fichiers gpt-oss).
pub const GGML_F32: u32 = 0;
pub const GGML_F16: u32 = 1;
pub const GGML_Q8_0: u32 = 8;
pub const GGML_MXFP4: u32 = 39;

/// Octets d'une rangée de `n` éléments d'un type ggml.
pub fn octets_rangee(type_ggml: u32, n: u64) -> Result<u64> {
    Ok(match type_ggml {
        GGML_F32 => 4 * n,
        GGML_F16 => 2 * n,
        GGML_Q8_0 => {
            if n % 32 != 0 {
                bail!("Q8_0 : rangée de {n} éléments, non multiple de 32");
            }
            n / 32 * 34
        }
        GGML_MXFP4 => {
            if n % 32 != 0 {
                bail!("MXFP4 : rangée de {n} éléments, non multiple de 32");
            }
            n / 32 * 17
        }
        t => bail!("type ggml {t} inconnu de la référence"),
    })
}

/// Valeur de métadonnée. Les tableaux ne gardent que leur type et leur taille, sauf les tableaux
/// d'entiers ou de réels courts (moins de 4 096 éléments), gardés en entier.
#[derive(Clone, Debug)]
pub enum Meta {
    Entier(i64),
    Naturel(u64),
    Reel(f64),
    Booleen(bool),
    Chaine(String),
    Tableau { type_elem: u32, n: u64, nombres: Option<Vec<f64>> },
}

#[derive(Clone, Debug)]
pub struct InfoTenseur {
    pub nom: String,
    pub n_dims: u32,
    /// ne[0] est la dimension contiguë (colonnes d'une matrice), 1 au-delà de n_dims.
    pub ne: [u64; 4],
    pub type_ggml: u32,
    /// Décalage absolu dans le fichier.
    pub decalage: u64,
    pub octets: u64,
}

pub struct Gguf {
    pub chemin: PathBuf,
    fichier: File,
    pub version: u32,
    pub meta: HashMap<String, Meta>,
    pub tenseurs: Vec<InfoTenseur>,
    index: HashMap<String, usize>,
    pub alignement: u64,
    pub debut_donnees: u64,
    pub taille: u64,
}

struct Lecteur<R: Read> {
    r: R,
    pos: u64,
}

impl<R: Read> Lecteur<R> {
    fn octets(&mut self, n: usize) -> Result<Vec<u8>> {
        let mut v = vec![0u8; n];
        self.r.read_exact(&mut v)?;
        self.pos += n as u64;
        Ok(v)
    }
    fn u8(&mut self) -> Result<u8> {
        Ok(self.octets(1)?[0])
    }
    fn u16(&mut self) -> Result<u16> {
        Ok(u16::from_le_bytes(self.octets(2)?.try_into().unwrap()))
    }
    fn u32(&mut self) -> Result<u32> {
        Ok(u32::from_le_bytes(self.octets(4)?.try_into().unwrap()))
    }
    fn u64(&mut self) -> Result<u64> {
        Ok(u64::from_le_bytes(self.octets(8)?.try_into().unwrap()))
    }
    fn chaine(&mut self) -> Result<String> {
        let n = self.u64()?;
        if n > (1 << 30) {
            bail!("chaîne de {n} octets : fichier corrompu");
        }
        let v = self.octets(n as usize)?;
        Ok(String::from_utf8_lossy(&v).into_owned())
    }
    /// Lit une valeur scalaire du type GGUF `t`.
    fn scalaire(&mut self, t: u32) -> Result<Meta> {
        Ok(match t {
            0 => Meta::Naturel(self.u8()? as u64),
            1 => Meta::Entier(self.u8()? as i8 as i64),
            2 => Meta::Naturel(self.u16()? as u64),
            3 => Meta::Entier(self.u16()? as i16 as i64),
            4 => Meta::Naturel(self.u32()? as u64),
            5 => Meta::Entier(self.u32()? as i32 as i64),
            6 => Meta::Reel(f32::from_bits(self.u32()?) as f64),
            7 => Meta::Booleen(self.u8()? != 0),
            8 => Meta::Chaine(self.chaine()?),
            10 => Meta::Naturel(self.u64()?),
            11 => Meta::Entier(self.u64()? as i64),
            12 => Meta::Reel(f64::from_bits(self.u64()?)),
            _ => bail!("type de métadonnée {t} inconnu"),
        })
    }
    fn valeur(&mut self, t: u32) -> Result<Meta> {
        if t != 9 {
            return self.scalaire(t);
        }
        let type_elem = self.u32()?;
        let n = self.u64()?;
        let garder = n < 4096 && type_elem != 8 && type_elem != 9;
        let mut nombres = Vec::new();
        for _ in 0..n {
            let v = self.valeur(type_elem)?;
            if garder {
                nombres.push(match v {
                    Meta::Entier(x) => x as f64,
                    Meta::Naturel(x) => x as f64,
                    Meta::Reel(x) => x,
                    Meta::Booleen(b) => b as u8 as f64,
                    _ => f64::NAN,
                });
            }
        }
        Ok(Meta::Tableau { type_elem, n, nombres: garder.then_some(nombres) })
    }
}

impl Gguf {
    pub fn ouvrir(chemin: &Path) -> Result<Gguf> {
        let fichier = File::open(chemin).with_context(|| format!("ouverture de {}", chemin.display()))?;
        let taille = fichier.metadata()?.len();
        let mut l = Lecteur { r: BufReader::with_capacity(1 << 20, fichier.try_clone()?), pos: 0 };
        if l.octets(4)? != b"GGUF" {
            bail!("{} : magie GGUF absente", chemin.display());
        }
        let version = l.u32()?;
        if version != 3 {
            bail!("GGUF version {version} : seule la 3 est lue");
        }
        let n_tenseurs = l.u64()?;
        let n_paires = l.u64()?;
        let mut meta = HashMap::new();
        for _ in 0..n_paires {
            let cle = l.chaine()?;
            let t = l.u32()?;
            let v = l.valeur(t)?;
            meta.insert(cle, v);
        }
        let alignement = match meta.get("general.alignment") {
            Some(Meta::Naturel(a)) => *a,
            Some(Meta::Entier(a)) => *a as u64,
            _ => 32,
        };
        let mut bruts = Vec::with_capacity(n_tenseurs as usize);
        for _ in 0..n_tenseurs {
            let nom = l.chaine()?;
            let n_dims = l.u32()?;
            if n_dims == 0 || n_dims > 4 {
                bail!("{nom} : {n_dims} dimensions");
            }
            let mut ne = [1u64; 4];
            for d in ne.iter_mut().take(n_dims as usize) {
                *d = l.u64()?;
            }
            let type_ggml = l.u32()?;
            let rel = l.u64()?;
            bruts.push((nom, n_dims, ne, type_ggml, rel));
        }
        let debut_donnees = l.pos.div_ceil(alignement) * alignement;
        let mut tenseurs = Vec::with_capacity(bruts.len());
        let mut index = HashMap::new();
        for (nom, n_dims, ne, type_ggml, rel) in bruts {
            let rangees = ne[1] * ne[2] * ne[3];
            let octets = match octets_rangee(type_ggml, ne[0]) {
                Ok(o) => o * rangees,
                Err(_) => 0, // type inconnu : le tenseur reste listé, sa lecture échouera
            };
            let decalage = debut_donnees + rel;
            if decalage + octets > taille {
                bail!("{nom} dépasse la fin du fichier");
            }
            index.insert(nom.clone(), tenseurs.len());
            tenseurs.push(InfoTenseur { nom, n_dims, ne, type_ggml, decalage, octets });
        }
        Ok(Gguf { chemin: chemin.to_path_buf(), fichier, version, meta, tenseurs, index, alignement, debut_donnees, taille })
    }

    pub fn tenseur(&self, nom: &str) -> Result<&InfoTenseur> {
        self.index.get(nom).map(|&i| &self.tenseurs[i]).ok_or_else(|| anyhow!("tenseur absent : {nom}"))
    }

    /// Lit `longueur` octets au décalage absolu `decalage` (lecture positionnelle, sans état).
    pub fn lire_plage(&self, decalage: u64, longueur: u64) -> Result<Vec<u8>> {
        let mut v = vec![0u8; longueur as usize];
        let mut fait = 0usize;
        while fait < v.len() {
            let n = self.fichier.seek_read(&mut v[fait..], decalage + fait as u64)?;
            if n == 0 {
                bail!("fin de fichier inattendue à {}", decalage + fait as u64);
            }
            fait += n;
        }
        Ok(v)
    }

    pub fn lire_tenseur(&self, nom: &str) -> Result<Vec<u8>> {
        let t = self.tenseur(nom)?;
        if t.octets == 0 {
            bail!("{nom} : type ggml {} non lu par la référence", t.type_ggml);
        }
        self.lire_plage(t.decalage, t.octets)
    }

    pub fn entier(&self, cle: &str) -> Result<u64> {
        match self.meta.get(cle) {
            Some(Meta::Naturel(x)) => Ok(*x),
            Some(Meta::Entier(x)) if *x >= 0 => Ok(*x as u64),
            Some(m) => bail!("{cle} : {m:?} n'est pas un entier naturel"),
            None => bail!("métadonnée absente : {cle}"),
        }
    }

    pub fn reel(&self, cle: &str) -> Result<f64> {
        match self.meta.get(cle) {
            Some(Meta::Reel(x)) => Ok(*x),
            Some(Meta::Naturel(x)) => Ok(*x as f64),
            Some(Meta::Entier(x)) => Ok(*x as f64),
            Some(m) => bail!("{cle} : {m:?} n'est pas un réel"),
            None => bail!("métadonnée absente : {cle}"),
        }
    }

    pub fn chaine(&self, cle: &str) -> Result<String> {
        match self.meta.get(cle) {
            Some(Meta::Chaine(s)) => Ok(s.clone()),
            Some(m) => bail!("{cle} : {m:?} n'est pas une chaîne"),
            None => bail!("métadonnée absente : {cle}"),
        }
    }
}
