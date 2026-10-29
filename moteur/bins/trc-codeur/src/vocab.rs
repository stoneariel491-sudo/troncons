//! Le compagnon `<nom>.vocab.gguf` (§ 4.13) : un GGUF v3 valide, aucun tenseur, toutes les paires
//! clé-valeur du source recopiées octet pour octet, complété de zéros jusqu'à l'alignement GGUF
//! (la zone de données, vide, commence là ; un lecteur qui s'y place ne sort pas du fichier).

use crate::gguf::Gguf;
use anyhow::{Result, ensure};
use serde_json::{Value, json};
use std::path::Path;
use trc_format::lire_paires;

pub fn ecrire(source: &Path, dest: &Path) -> Result<Value> {
    let g = Gguf::ouvrir(source)?;
    let mut b = Vec::with_capacity(24 + g.kv_brut.len() + 64);
    b.extend_from_slice(b"GGUF");
    b.extend_from_slice(&3u32.to_le_bytes());
    b.extend_from_slice(&0u64.to_le_bytes());
    b.extend_from_slice(&g.n_kv.to_le_bytes());
    b.extend_from_slice(&g.kv_brut);
    let fin_entete = b.len();
    b.resize((b.len() as u64).div_ceil(g.alignement) as usize * g.alignement as usize, 0);
    std::fs::write(dest, &b)?;
    // Relecture : mêmes paires, aucun tenseur.
    let relu = std::fs::read(dest)?;
    ensure!(&relu[0..4] == b"GGUF" && u64::from_le_bytes(relu[8..16].try_into().unwrap()) == 0);
    let p = lire_paires(&relu[24..], g.n_kv).map_err(|e| anyhow::anyhow!("relecture du compagnon : {e}"))?;
    ensure!(p.len() as u64 == g.n_kv && relu[24..24 + g.kv_brut.len()] == g.kv_brut[..], "compagnon relu différent du source");
    Ok(json!({
        "source": source.display().to_string(),
        "dest": dest.display().to_string(),
        "paires": g.n_kv,
        "octets": relu.len(),
        "fin_entete": fin_entete,
        "alignement": g.alignement,
    }))
}
