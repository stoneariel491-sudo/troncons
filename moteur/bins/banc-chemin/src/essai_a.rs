//! Essai E0(a) : peut-on épingler 0,25 / 1 / 4 / 11 Go de RAM sous WDDM sur cette machine ?
//!
//! Pour chaque taille : la RAM disponible d'abord ; la taille n'est tentée que si elle laisse au
//! moins `marge` octets disponibles (choix prudent déclaré dans REPRISE-E.md : cinq lots compilent
//! sur 16 Go). Puis `cuMemHostAlloc` chronométré, un aller-retour de 64 Mio par DMA depuis la
//! **fin** de l'allocation (la mémoire épinglée doit être vraie jusqu'au bout, pas seulement
//! réservée), la libération chronométrée, et la RAM disponible après chaque geste.

use std::time::Instant;

use serde_json::{Value, json};
use trc_cuda::*;

use crate::machine;

pub fn executer(tailles: &[u64], marge: u64) -> Result<Value> {
    let c = Contexte::nouveau(0)?;
    let f = Flux::nouveau(&c, false)?;
    let essai = 64usize << 20;
    let carte = MemoireCarte::allouer(&c, essai)?;
    let mut verif = HoteEpingle::allouer(&c, essai, false)?;
    let mut lignes = Vec::new();
    for &octets in tailles {
        let (dispo_avant, _) = machine::ram();
        if octets.saturating_add(marge) > dispo_avant {
            eprintln!("{octets} o : non tentée ({dispo_avant} o disponibles, marge {marge})");
            lignes.push(json!({ "octets": octets, "tentee": false, "ram_disponible_avant_o": dispo_avant,
                                "raison": "taille + marge au-dessus de la RAM disponible" }));
            continue;
        }
        let t0 = Instant::now();
        let r = HoteEpingle::allouer(&c, octets as usize, false);
        let duree_allocation_ms = t0.elapsed().as_secs_f64() * 1e3;
        let mut h = match r {
            Ok(h) => h,
            Err(e) => {
                eprintln!("{octets} o : refusée ({e})");
                lignes.push(json!({ "octets": octets, "tentee": true, "reussie": false, "erreur": e.to_string(),
                                    "duree_allocation_ms": duree_allocation_ms, "ram_disponible_avant_o": dispo_avant }));
                continue;
            }
        };
        let (dispo_apres, _) = machine::ram();
        // Aller-retour depuis la fin de l'allocation : motif, DMA vers la carte, retour, comparaison.
        let fin = h.octets() - essai;
        for (k, b) in h.tranche_mut()[fin..].iter_mut().enumerate() {
            *b = (k as u32).wrapping_mul(2_654_435_761).to_le_bytes()[3];
        }
        let e0 = Evenement::nouveau(&c, true)?;
        let e1 = Evenement::nouveau(&c, true)?;
        e0.enregistrer(&f)?;
        copier_vers_carte(carte.tout(), &h, fin, essai, &f)?;
        e1.enregistrer(&f)?;
        copier_vers_hote(&mut verif, 0, carte.tout(), &f)?;
        f.synchroniser()?;
        let ecarts = verif.tranche()[..essai].iter().zip(&h.tranche()[fin..]).filter(|(a, b)| a != b).count();
        let ms = e1.ms_depuis(&e0)?;
        let t1 = Instant::now();
        drop(h);
        let duree_liberation_ms = t1.elapsed().as_secs_f64() * 1e3;
        let (dispo_libere, _) = machine::ram();
        eprintln!(
            "{octets} o : épinglée en {duree_allocation_ms:.1} ms, DMA de la fin {:.2} Go/s, {ecarts} écart(s), libérée en {duree_liberation_ms:.1} ms",
            essai as f64 / (ms as f64 * 1e-3) / 1e9
        );
        lignes.push(json!({
            "octets": octets, "tentee": true, "reussie": true,
            "duree_allocation_ms": duree_allocation_ms, "duree_liberation_ms": duree_liberation_ms,
            "ram_disponible_avant_o": dispo_avant, "ram_disponible_apres_allocation_o": dispo_apres,
            "ram_disponible_apres_liberation_o": dispo_libere,
            "dma_fin_octets": essai, "dma_fin_ms": ms, "dma_fin_go_s": essai as f64 / (ms as f64 * 1e-3) / 1e9,
            "dma_fin_ecarts": ecarts,
        }));
    }
    Ok(json!({ "marge_o": marge, "tailles": lignes, "machine_fin": machine::releve(Some(&c)) }))
}
