//! Les poids réels : un expert d'un tenseur MXFP4 de gpt-oss, rangée par rangée, lu par le lecteur
//! GGUF de trc-reference (chemin indépendant du .trc).
//!
//! Bloc MXFP4 (17 octets) : e (E8M0), puis 16 octets ; le demi-octet faible de l'octet j porte
//! l'élément j, le fort l'élément j + 16. Poids = K[code] · 2^(e − 128), K = {0, 1, 2, 3, 4, 6, 8, 12}
//! signés par le bit 3 (grandeurs E2M1 doublées). Exact en f32 (K tient en 4 bits, l'échelle est
//! une puissance de deux dans l'étendue des f32 normaux pour tous les e rencontrés, vérifié à la
//! lecture).

use anyhow::{Result, bail};
use std::path::Path;
use trc_reference::gguf::{GGML_MXFP4, Gguf, InfoTenseur};
use trc_reference::poids::K_MXFP4;

pub const FICHIER_20B: &str = "~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf";
pub const COUCHES_F1: [usize; 4] = [0, 8, 16, 23];
pub const ROLES: [&str; 3] = ["ffn_gate_exps", "ffn_up_exps", "ffn_down_exps"];

pub struct Modele {
    pub g: Gguf,
}

/// Un expert : `lignes` rangées de `colonnes` poids, avec ses codes et ses exposants.
pub struct ExpertMx {
    pub lignes: usize,
    pub colonnes: usize,
    /// codes de 4 bits, un par poids (ordre naturel des colonnes)
    pub codes: Vec<u8>,
    /// exposant E8M0 de chaque bloc de 32 (lignes · colonnes / 32)
    pub e: Vec<u8>,
}

impl ExpertMx {
    pub fn blocs_ligne(&self) -> usize {
        self.colonnes / 32
    }
    /// 2^(e − 128) en f32.
    #[inline]
    pub fn echelle(e: u8) -> f32 {
        (2.0f64).powi(e as i32 - 128) as f32
    }
    pub fn valeur(&self, r: usize, c: usize) -> f32 {
        let code = self.codes[r * self.colonnes + c];
        let e = self.e[r * self.blocs_ligne() + c / 32];
        K_MXFP4[code as usize] as f32 * Self::echelle(e)
    }
    pub fn ligne(&self, r: usize, dst: &mut [f32]) {
        let nb = self.blocs_ligne();
        for b in 0..nb {
            let s = Self::echelle(self.e[r * nb + b]);
            for j in 0..32 {
                let c = b * 32 + j;
                dst[c] = K_MXFP4[self.codes[r * self.colonnes + c] as usize] as f32 * s;
            }
        }
    }
}

impl Modele {
    pub fn ouvrir(chemin: &str) -> Result<Modele> {
        Ok(Modele { g: Gguf::ouvrir(Path::new(chemin))? })
    }
    pub fn tenseur(&self, couche: usize, role: &str) -> Result<InfoTenseur> {
        let t = self.g.tenseur(&format!("blk.{couche}.{role}.weight"))?.clone();
        if t.type_ggml != GGML_MXFP4 {
            bail!("{} n'est pas en MXFP4", t.nom);
        }
        Ok(t)
    }
    pub fn nb_experts(&self, t: &InfoTenseur) -> usize {
        t.ne[2] as usize
    }
    /// Lit l'expert `e` du tenseur `t`.
    pub fn expert(&self, t: &InfoTenseur, e: usize) -> Result<ExpertMx> {
        let (colonnes, lignes, ne) = (t.ne[0] as usize, t.ne[1] as usize, t.ne[2] as usize);
        let tranche = t.octets / ne as u64;
        let o = self.g.lire_plage(t.decalage + e as u64 * tranche, tranche)?;
        if o.len() != lignes * colonnes / 32 * 17 {
            bail!("{} : tranche de {} octets inattendue", t.nom, o.len());
        }
        let mut codes = vec![0u8; lignes * colonnes];
        let mut ex = vec![0u8; lignes * colonnes / 32];
        for (b, bloc) in o.chunks_exact(17).enumerate() {
            if bloc[0] == 255 || bloc[0] < 20 {
                bail!("{} : exposant E8M0 {} hors de l'étendue prévue", t.nom, bloc[0]);
            }
            ex[b] = bloc[0];
            for j in 0..16 {
                codes[b * 32 + j] = bloc[1 + j] & 0x0F;
                codes[b * 32 + j + 16] = bloc[1 + j] >> 4;
            }
        }
        Ok(ExpertMx { lignes, colonnes, codes, e: ex })
    }
}
