//! Le fichier de logits de référence de llama-perplexity (`--kl-divergence-base`), lu et écrit.
//!
//! Format, relevé dans `tools/perplexity/perplexity.cpp` de b11515 (MIT ; rien n'est copié) :
//! ```text
//!  u8[8]  « _logits_ »
//!  u32    n_ctx                       (512)
//!  i32    n_vocab                     (201 088 pour gpt-oss)
//!  i32    n_chunk                     (nombre de fenêtres)
//!  i32    jetons[n_chunk · n_ctx]     (les jetons d'origine, sans le BOS éventuel)
//!  puis, pour chaque fenêtre, n_ctx − 1 − n_ctx/2 entrées (255), une par position notée
//!  t = n_ctx/2 … n_ctx − 2 (elle prédit le jeton t + 1) ; une entrée = nv mots u16,
//!  nv = 2 ⌈n_vocab / 2⌉ + 4 :
//!    f32 pas, f32 log_p_min, puis n_vocab codes u16 (et un u16 de bourrage si n_vocab est impair)
//!    log p_i ≈ pas · code_i + log_p_min
//! ```
//! Côté écriture, llama.cpp borne le plus petit logit retenu à max − 16 : tout logit sous cette
//! borne reçoit le code 0 ; pas = (max − min)/65 535 ; code = arrondi((logit − min)/pas).

use std::fs::File;
use std::io::{BufReader, BufWriter, Read, Seek, SeekFrom, Write};
use std::path::Path;

use anyhow::{Context, Result, bail};

pub const MAGIE: &[u8; 8] = b"_logits_";

pub fn mots_par_entree(n_vocab: usize) -> usize {
    2 * n_vocab.div_ceil(2) + 4
}

/// Les positions notées d'une fenêtre de n_ctx jetons : [n_ctx/2, n_ctx − 1).
pub fn positions_notees(n_ctx: usize) -> std::ops::Range<usize> {
    n_ctx / 2..n_ctx - 1
}

pub struct FichierKld {
    lecteur: BufReader<File>,
    pub n_ctx: usize,
    pub n_vocab: usize,
    pub n_chunk: usize,
    pub jetons: Vec<u32>,
    debut: u64,
}

impl FichierKld {
    pub fn ouvrir(chemin: &Path) -> Result<FichierKld> {
        let f = File::open(chemin).with_context(|| format!("ouverture de {}", chemin.display()))?;
        let taille = f.metadata()?.len();
        let mut r = BufReader::with_capacity(1 << 22, f);
        let mut m = [0u8; 8];
        r.read_exact(&mut m)?;
        if &m != MAGIE {
            bail!("{} : pas un fichier de logits de llama-perplexity", chemin.display());
        }
        let mut b4 = [0u8; 4];
        r.read_exact(&mut b4)?;
        let n_ctx = u32::from_le_bytes(b4) as usize;
        r.read_exact(&mut b4)?;
        let n_vocab = i32::from_le_bytes(b4) as usize;
        r.read_exact(&mut b4)?;
        let n_chunk = i32::from_le_bytes(b4) as usize;
        let mut brut = vec![0u8; n_ctx * n_chunk * 4];
        r.read_exact(&mut brut)?;
        let jetons = brut.chunks_exact(4).map(|c| i32::from_le_bytes(c.try_into().unwrap()) as u32).collect();
        let debut = 20 + (n_ctx * n_chunk * 4) as u64;
        let attendu = debut + (n_chunk * positions_notees(n_ctx).len() * mots_par_entree(n_vocab) * 2) as u64;
        if taille != attendu {
            bail!("{} : {taille} octets au lieu de {attendu} (fichier tronqué ou autre format)", chemin.display());
        }
        Ok(FichierKld { lecteur: r, n_ctx, n_vocab, n_chunk, jetons, debut })
    }

    pub fn entrees_par_fenetre(&self) -> usize {
        positions_notees(self.n_ctx).len()
    }

    /// Les entrées de la fenêtre `c` (255 × nv mots).
    pub fn fenetre(&mut self, c: usize) -> Result<Vec<u16>> {
        let nv = mots_par_entree(self.n_vocab);
        let n = self.entrees_par_fenetre() * nv;
        let dec = self.debut + (c * n * 2) as u64;
        self.lecteur.seek(SeekFrom::Start(dec))?;
        let mut brut = vec![0u8; n * 2];
        self.lecteur.read_exact(&mut brut)?;
        Ok(brut.chunks_exact(2).map(|c| u16::from_le_bytes([c[0], c[1]])).collect())
    }

    /// Les jetons de la fenêtre `c`.
    pub fn jetons_fenetre(&self, c: usize) -> &[u32] {
        &self.jetons[c * self.n_ctx..(c + 1) * self.n_ctx]
    }
}

/// Une entrée décodée : log p_i ≈ pas · code_i + log_p_min.
pub struct Entree<'a> {
    pub pas: f32,
    pub log_p_min: f32,
    pub codes: &'a [u16],
}

impl<'a> Entree<'a> {
    pub fn depuis(mots: &'a [u16], n_vocab: usize) -> Entree<'a> {
        let pas = f32::from_bits(mots[0] as u32 | (mots[1] as u32) << 16);
        let log_p_min = f32::from_bits(mots[2] as u32 | (mots[3] as u32) << 16);
        Entree { pas, log_p_min, codes: &mots[4..4 + n_vocab] }
    }

    /// log p_i, calculé comme llama.cpp (en f32 : pas · code + log_p_min).
    #[inline]
    pub fn log_p(&self, i: usize) -> f32 {
        self.pas * self.codes[i] as f32 + self.log_p_min
    }
}

/// Code une rangée de logits en une entrée (nv mots), selon la règle de llama.cpp, les calculs
/// intermédiaires en f64 et les deux réels stockés en f32.
pub fn coder_entree(logits: &[f64], sortie: &mut [u16]) {
    let n = logits.len();
    let mut max = f64::NEG_INFINITY;
    let mut min = f64::INFINITY;
    for &l in logits {
        max = max.max(l);
        min = min.min(l);
    }
    let min = min.max(max - 16.0);
    let mut somme = 0.0;
    for &l in logits {
        somme += (l - max).exp();
    }
    let lse = somme.ln();
    let log_p_min = (min - max - lse) as f32;
    let pas = ((max - min) / 65535.0) as f32;
    let pb = pas.to_bits();
    let mb = log_p_min.to_bits();
    sortie[0] = pb as u16;
    sortie[1] = (pb >> 16) as u16;
    sortie[2] = mb as u16;
    sortie[3] = (mb >> 16) as u16;
    let codes = &mut sortie[4..];
    if pas > 0.0 {
        let inv = 1.0 / pas as f64;
        for i in 0..n {
            codes[i] = if logits[i] > min { ((logits[i] - min) * inv).round().clamp(0.0, 65535.0) as u16 } else { 0 };
        }
    } else {
        codes[..n].iter_mut().for_each(|c| *c = 0);
    }
    for c in codes[n..].iter_mut() {
        *c = 0;
    }
}

/// Écrit un fichier `.kld` au format de llama-perplexity.
pub struct EcrivainKld {
    w: BufWriter<File>,
    n_vocab: usize,
    tampon: Vec<u16>,
    pub entrees_ecrites: usize,
}

impl EcrivainKld {
    pub fn creer(chemin: &Path, n_ctx: usize, n_vocab: usize, jetons: &[u32]) -> Result<EcrivainKld> {
        if jetons.len() % n_ctx != 0 {
            bail!("{} jetons : pas un multiple de n_ctx = {n_ctx}", jetons.len());
        }
        let mut w = BufWriter::with_capacity(1 << 22, File::create(chemin).with_context(|| format!("création de {}", chemin.display()))?);
        w.write_all(MAGIE)?;
        w.write_all(&(n_ctx as u32).to_le_bytes())?;
        w.write_all(&(n_vocab as i32).to_le_bytes())?;
        w.write_all(&((jetons.len() / n_ctx) as i32).to_le_bytes())?;
        for &j in jetons {
            w.write_all(&(j as i32).to_le_bytes())?;
        }
        Ok(EcrivainKld { w, n_vocab, tampon: vec![0; mots_par_entree(n_vocab)], entrees_ecrites: 0 })
    }

    pub fn ecrire(&mut self, logits: &[f64]) -> Result<()> {
        if logits.len() != self.n_vocab {
            bail!("{} logits au lieu de {}", logits.len(), self.n_vocab);
        }
        coder_entree(logits, &mut self.tampon);
        let mut brut = Vec::with_capacity(self.tampon.len() * 2);
        for m in &self.tampon {
            brut.extend_from_slice(&m.to_le_bytes());
        }
        self.w.write_all(&brut)?;
        self.entrees_ecrites += 1;
        Ok(())
    }

    pub fn finir(mut self) -> Result<()> {
        self.w.flush()?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn aller_retour_d_une_entree() {
        let n = 1001;
        let logits: Vec<f64> = (0..n).map(|i| ((i * 37) % 101) as f64 * 0.2 - 10.0).collect();
        let mut mots = vec![0u16; mots_par_entree(n)];
        coder_entree(&logits, &mut mots);
        let e = Entree::depuis(&mots, n);
        let max = logits.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let lse = logits.iter().map(|l| (l - max).exp()).sum::<f64>().ln();
        for i in 0..n {
            let vrai = logits[i] - max - lse;
            if logits[i] > max - 16.0 {
                // erreur ≤ un demi-pas (16/65 535/2 = 1,2e-4) plus l'arrondi f32.
                assert!((e.log_p(i) as f64 - vrai).abs() < 1.3e-4, "i={i}");
            }
        }
    }
}
