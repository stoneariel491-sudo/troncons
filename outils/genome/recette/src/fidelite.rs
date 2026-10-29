//! La fidélité de sortie en fonction du débit : pour chaque expert, la courbe (bits par poids, erreur
//! relative de la sortie de l'expert sur des entrées réelles) de la recette, avec et sans pondération
//! par les entrées, et les bits qu'il faut pour égaler l'erreur de sortie de la base.
//!
//! Pourquoi : au point du critère W (erreur de poids égale), la recette tournée fait une erreur de
//! sortie plus grande que la base (couche 0, expert 0 : 7,63 % contre 6,77 %). La sortie d'une rangée
//! vaut Σ_c Δw_c x_c ; son espérance quadratique, pour une erreur blanche dans le domaine tourné, est
//! Σ_c′ h_c′ E[Δw′_c′²], h = diag(R Σ Rᵀ), Σ = E[x xᵀ] des entrées réelles. Pondérer le Viterbi par h
//! minimise donc l'erreur de sortie attendue (la diagonale de la hessienne de la perte quadratique de
//! couche, le geste d'imatrix ou de GPTQ réduit à ce que le treillis sait faire).
//!
//! Calibration (h et tables) sur la capture « calib » (fenêtres 10 à 21) ; mesure sur la capture
//! « eval » (fenêtres 0 à 9) : aucune entrée de la mesure ne sert au réglage.

use anyhow::Result;
use rayon::prelude::*;
use std::fmt::Write as _;
use std::path::PathBuf;

use crate::base::base_valeur;
use crate::codons::{self, Code, Travail};
use crate::donnees::{ExpertMx, FICHIER_20B, Modele, ROLES};
use crate::hadamard;
use crate::mesure::{CENTRES, Norme, preparer};
use crate::sortie::{apprendre_codes, entrees, sortie_expert};
use trc_reference::gguf::GGML_F32;
use trc_reference::ops::swiglu_oai;
use trc_reference::poids::rangee_f64;

/// Les k = ⌈frac · n⌉ poids de plus grande magnitude de la rangée (avant rotation), gardés exacts à
/// part (« exceptions ») ; la rangée sans eux est tournée et codée par le brin. Coût : 8 bits de
/// compte par rangée, et par exception 12 bits de colonne + 4 bits de code + 8 bits d'échelle E8M0
/// (compté au pire, sans partage avec les autres échelles).
fn preparer_exc(ex: &ExpertMx, r: usize, graine: u32, frac: f64, norme: Norme) -> (crate::mesure::Rangee, Vec<(usize, f32)>) {
    if frac <= 0.0 || norme == Norme::Brut {
        return (preparer(ex, r, norme, graine, &CENTRES), Vec::new());
    }
    let n = ex.colonnes;
    let mut w = vec![0.0f32; n];
    ex.ligne(r, &mut w);
    let k = (frac * n as f64).ceil() as usize;
    let mut idx: Vec<usize> = (0..n).collect();
    idx.sort_by(|&a, &b| w[b].abs().partial_cmp(&w[a].abs()).unwrap());
    let exc: Vec<(usize, f32)> = idx[..k].iter().map(|&c| (c, w[c])).collect();
    let mut rg = preparer(ex, r, Norme::Tourne, graine, &CENTRES);
    // refaire la source sans les exceptions (même σ recalculé)
    for &(c, _) in &exc {
        w[c] = 0.0;
    }
    hadamard::tourner(&mut w, 64, graine);
    let ms: f64 = w.iter().map(|&a| (a as f64) * (a as f64)).sum::<f64>() / n as f64;
    let sigma = f32::from_bits((ms.sqrt() as f32).to_bits() & !0x1FFF);
    rg.x = w.iter().map(|&a| a / sigma).collect();
    rg.sigma = sigma;
    rg.facteur = (sigma as f64) * (sigma as f64);
    (rg, exc)
}

struct Essai {
    err: f64,
    bits: f64,
    etats: Vec<u16>,
}

/// Les essais (erreur pondérée absolue, bits, états) de chaque forme pour chaque rangée d'une matrice.
/// `fixe_rangee` : bits fixes par rangée hors brin (σ et indice en « tourne » ; indice et échelles E8M0
/// en « brut »).
fn essais_matrice(ex: &ExpertMx, codes: &[Code], graine: u32, h: &[f32], frac: f64, norme: Norme, fixe_rangee: f64) -> Vec<Vec<Essai>> {
    let n = ex.colonnes;
    (0..ex.lignes)
        .into_par_iter()
        .map_init(Travail::new, |w, r| {
            let (mut rg, exc) = preparer_exc(ex, r, graine, frac, norme);
            let bits_exc = if exc.is_empty() { 0.0 } else { 8.0 + 24.0 * exc.len() as f64 };
            if !h.is_empty() {
                if norme == Norme::Brut {
                    for (o, &v) in rg.om.iter_mut().zip(h.iter()) {
                        *o *= v;
                    }
                } else {
                    rg.om.copy_from_slice(h);
                }
            }
            codes
                .iter()
                .map(|code| {
                    let b = codons::viterbi(&rg.x, &rg.om, code, w);
                    Essai { err: b.erreur * rg.facteur, bits: code.forme.bits_brin(n) as f64 + fixe_rangee + bits_exc, etats: b.etats.iter().map(|&s| s as u16).collect() }
                })
                .collect()
        })
        .collect()
}

/// Choix par rangée pour λ ; rend (indices, bits totaux).
fn choisir(es: &[Vec<Essai>], lambda: f64) -> (Vec<usize>, f64) {
    let mut ks = Vec::with_capacity(es.len());
    let mut b = 0.0;
    for e in es {
        let mut k = 0;
        for c in 1..e.len() {
            if e[c].err + lambda * e[c].bits < e[k].err + lambda * e[k].bits {
                k = c;
            }
        }
        b += e[k].bits;
        ks.push(k);
    }
    (ks, b)
}

/// λ qui dépense `cible` bits par poids (bissection en log ; bits décroissants en λ).
fn lambda_pour(es: &[Vec<Essai>], cible: f64, poids: f64) -> f64 {
    let (mut lo, mut hi) = ((1e-30f64).ln(), (1e10f64).ln());
    for _ in 0..200 {
        let mid = 0.5 * (lo + hi);
        if choisir(es, mid.exp()).1 / poids > cible {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    hi.exp()
}

fn reconstruire_matrice(ex: &ExpertMx, es: &[Vec<Essai>], ks: &[usize], codes: &[Code], graine: u32, frac: f64, norme: Norme) -> Vec<f32> {
    let n = ex.colonnes;
    let lignes: Vec<Vec<f32>> = (0..ex.lignes)
        .into_par_iter()
        .map(|r| {
            let (rg, exc) = preparer_exc(ex, r, graine, frac, norme);
            let etats: Vec<u32> = es[r][ks[r]].etats.iter().map(|&s| s as u32).collect();
            let mut y = crate::mesure::reconstruire(ex, r, &rg, &etats, &codes[ks[r]], norme, graine);
            for &(c, v) in &exc {
                y[c] = v;
            }
            y
        })
        .collect();
    let mut w = Vec::with_capacity(ex.lignes * n);
    for l in lignes {
        w.extend_from_slice(&l);
    }
    w
}

/// h = diag(Σ) (sans rotation), normalisée à une moyenne de 1.
fn diag_simple(x: &[f64], m: usize, n: usize) -> Vec<f32> {
    let mut h = vec![0.0f64; n];
    for p in 0..m {
        for c in 0..n {
            h[c] += x[p * n + c] * x[p * n + c];
        }
    }
    let moy = h.iter().sum::<f64>() / n as f64;
    h.iter().map(|&v| (v / moy).max(1e-6) as f32).collect()
}

/// h = diag(R Σ Rᵀ) estimée sur des entrées (m × n), normalisée à une moyenne de 1.
fn diag_tournee(x: &[f64], m: usize, n: usize, graine: u32) -> Vec<f32> {
    let mut h = vec![0.0f64; n];
    for p in 0..m {
        let mut v: Vec<f32> = x[p * n..(p + 1) * n].iter().map(|&a| a as f32).collect();
        hadamard::tourner(&mut v, 64, graine);
        for c in 0..n {
            h[c] += (v[c] as f64).powi(2);
        }
    }
    let moy = h.iter().sum::<f64>() / n as f64;
    h.iter().map(|&v| (v / moy) as f32).collect()
}

fn biais(m: &Modele, l: usize, role: &str, e: usize) -> Result<Vec<f64>> {
    let t = m.g.tenseur(&format!("blk.{l}.{role}.bias"))?;
    assert_eq!(t.type_ggml, GGML_F32);
    let n = t.ne[0];
    let o = m.g.lire_plage(t.decalage + e as u64 * n * 4, n * 4)?;
    let mut v = vec![0.0; n as usize];
    rangee_f64(GGML_F32, &o, &mut v);
    Ok(v)
}

fn erreur_rel(a: &[f64], b: &[f64]) -> f64 {
    let n: f64 = a.iter().map(|v| v * v).sum();
    a.iter().zip(b.iter()).map(|(x, y)| (x - y).powi(2)).sum::<f64>() / n
}

pub fn fidelite(args: &[String]) -> Result<()> {
    let opt = |nom: &str, d: &str| -> String { args.iter().position(|a| a == nom).and_then(|i| args.get(i + 1).cloned()).unwrap_or(d.to_string()) };
    let couches: Vec<usize> = opt("--couches", "0,8,16,23").split(',').map(|s| s.parse().unwrap()).collect();
    let experts: Vec<usize> = opt("--experts", "0,16").split(',').map(|s| s.parse().unwrap()).collect();
    let calib = PathBuf::from(opt("--calib", "~/dev/essais/troncons/genome/eclaireur/calib"));
    let eval = PathBuf::from(opt("--eval", "~/dev/essais/troncons/genome/eclaireur/eval"));
    let max_pos: usize = opt("--positions", "512").parse()?;
    let cibles: Vec<f64> = opt("--cibles", "2.0,2.2,2.4,2.64,2.9").split(',').map(|s| s.parse().unwrap()).collect();
    let ecrire = opt("--ecrire", "");
    let frac: f64 = opt("--exceptions", "0").parse()?;
    let norme = if opt("--norme", "tourne") == "brut" { Norme::Brut } else { Norme::Tourne };
    let variantes: Vec<bool> = match opt("--variantes", "up").as_str() {
        "u" => vec![false],
        "p" => vec![true],
        _ => vec![false, true],
    };
    let formes = [(2u32, 1u32), (7, 3), (5, 2), (8, 3), (3, 1)];
    let m = Modele::ouvrir(FICHIER_20B)?;
    let (d, f) = (2880usize, 2880usize);
    let poids_mat = (d * f) as f64;
    let mut s = String::new();
    write!(s, "{{\"cibles\": {:?}, \"experts\": {:?}, \"exceptions\": {frac}, \"norme\": \"{:?}\", \"positions_max\": {max_pos}, \"lignes\": [\n", cibles, experts, norme)?;
    let mut premier = true;
    for &l in &couches {
        let codes: Vec<Vec<Code>> = ROLES.iter().map(|role| apprendre_codes(&m, l, role, norme, 12, 8, &formes, &[0, 8, 16, 24], 4, 48, 2, &[])).collect::<Result<_>>()?;
        let graines: Vec<u32> = (0..3).map(|ir| (l * 3 + ir) as u32 + 1).collect();
        for &e in &experts {
            let t0 = std::time::Instant::now();
            let exs: Vec<ExpertMx> = ROLES.iter().map(|role| m.expert(&m.tenseur(l, role).unwrap(), e)).collect::<Result<_>>()?;
            let bs: Vec<Vec<f64>> = ROLES.iter().map(|role| biais(&m, l, role, e)).collect::<Result<_>>()?;
            let bb: [Vec<f64>; 3] = [bs[0].clone(), bs[1].clone(), bs[2].clone()];
            let mut exacts: Vec<Vec<f32>> = Vec::new();
            let mut bases: Vec<Vec<f32>> = Vec::new();
            for ex in &exs {
                let mut w = vec![0.0f32; d * f];
                let mut b = vec![0.0f32; d * f];
                let nb = ex.blocs_ligne();
                for r in 0..ex.lignes {
                    ex.ligne(r, &mut w[r * f..(r + 1) * f]);
                    for c in 0..ex.colonnes {
                        b[r * f + c] = base_valeur(ex.codes[r * f + c], ex.e[r * nb + c / 32], &CENTRES);
                    }
                }
                exacts.push(w);
                bases.push(b);
            }
            let trio = |v: &Vec<Vec<f32>>| -> [Vec<f32>; 3] { [v[0].clone(), v[1].clone(), v[2].clone()] };
            // entrées de calibration : h, puis l'activation intermédiaire a par les poids exacts
            let (xc32, mc) = entrees(&calib, l, e, d, 1024)?;
            let xc: Vec<f64> = xc32.iter().map(|&v| v as f64).collect();
            let gate_c = produit_simple(&exacts[0], f, d, &xc, mc);
            let up_c = produit_simple(&exacts[1], f, d, &xc, mc);
            let mut a_c = vec![0.0f64; mc * f];
            for p in 0..mc {
                for i in 0..f {
                    a_c[p * f + i] = swiglu_oai(gate_c[p * f + i] + bb[0][i], up_c[p * f + i] + bb[1][i]);
                }
            }
            let h: Vec<Vec<f32>> = if norme == Norme::Brut {
                vec![diag_simple(&xc, mc, d), diag_simple(&xc, mc, d), diag_simple(&a_c, mc, f)]
            } else {
                vec![diag_tournee(&xc, mc, d, graines[0]), diag_tournee(&xc, mc, d, graines[1]), diag_tournee(&a_c, mc, f, graines[2])]
            };
            let fixes: Vec<f64> = ROLES
                .iter()
                .map(|role| -> Result<f64> {
                    Ok(if norme == Norme::Brut { 3.0 + crate::mesure::echelles_f1(&format!("blk.{l}.{role}.weight"))? * f as f64 } else { 3.0 + 16.0 })
                })
                .collect::<Result<_>>()?;
            // entrées de mesure
            let (xe32, me) = entrees(&eval, l, e, d, max_pos)?;
            let xe: Vec<f64> = xe32.iter().map(|&v| v as f64).collect();
            let ye = sortie_expert(&trio(&exacts), &bb, &xe, me, d, f);
            let yb = sortie_expert(&trio(&bases), &bb, &xe, me, d, f);
            let err_sortie_base = erreur_rel(&ye, &yb);
            let en: f64 = exacts.iter().map(|w| w.iter().map(|&v| (v as f64).powi(2)).sum::<f64>()).sum();
            let eb: f64 = exacts.iter().zip(bases.iter()).map(|(w, b)| w.iter().zip(b.iter()).map(|(x, y)| ((x - y) as f64).powi(2)).sum::<f64>()).sum();
            write!(s, "{}  {{\"couche\": {l}, \"expert\": {e}, \"positions_calib\": {mc}, \"positions_eval\": {me}, \"erreur_poids_base\": {:.6}, \"erreur_sortie_base\": {:.6}, \"variantes\": [", if premier { "" } else { ",\n" }, eb / en, err_sortie_base)?;
            premier = false;
            for (iv, pondere) in variantes.iter().enumerate() {
                let es: Vec<Vec<Vec<Essai>>> = (0..3).map(|ir| essais_matrice(&exs[ir], &codes[ir], graines[ir], if *pondere { &h[ir] } else { &[] }, frac, norme, fixes[ir])).collect();
                let mut pts = Vec::new();
                for &c in &cibles {
                    let mut recs: Vec<Vec<f32>> = Vec::new();
                    let mut bits = 0.0;
                    for ir in 0..3 {
                        let lambda = lambda_pour(&es[ir], c, poids_mat);
                        let (ks, b) = choisir(&es[ir], lambda);
                        bits += b;
                        recs.push(reconstruire_matrice(&exs[ir], &es[ir], &ks, &codes[ir], graines[ir], frac, norme));
                    }
                    let ew: f64 = exacts.iter().zip(recs.iter()).map(|(w, r)| w.iter().zip(r.iter()).map(|(x, y)| ((x - y) as f64).powi(2)).sum::<f64>()).sum();
                    let yr = sortie_expert(&trio(&recs), &bb, &xe, me, d, f);
                    let er = erreur_rel(&ye, &yr);
                    // positions où la recette fait mieux que la base
                    let mut gagne = 0;
                    for p in 0..me {
                        let (mut a, mut cc) = (0.0, 0.0);
                        for i in 0..d {
                            a += (ye[p * d + i] - yr[p * d + i]).powi(2);
                            cc += (ye[p * d + i] - yb[p * d + i]).powi(2);
                        }
                        if a < cc {
                            gagne += 1;
                        }
                    }
                    let bpp = bits / (3.0 * poids_mat);
                    if !ecrire.is_empty() && *pondere && (c - 2.64).abs() < 1e-9 {
                        let nom = format!("recette-ponderee{}{}-264", if norme == Norme::Brut { "-brut" } else { "" }, if frac > 0.0 { "-exc" } else { "" });
                        let dossier = PathBuf::from(&ecrire).join(nom);
                        std::fs::create_dir_all(&dossier)?;
                        let mut o = Vec::with_capacity(3 * d * f * 4);
                        for mm in recs.iter() {
                            for v in mm.iter() {
                                o.extend_from_slice(&v.to_le_bytes());
                            }
                        }
                        std::fs::write(dossier.join(format!("L{l:02}-E{e:02}.f32w")), o)?;
                    }
                    eprintln!("[{:.0} s] couche {l} expert {e} {} cible {c} : {bpp:.4} b ; poids {:.4} % ; sortie {:.4} % (base {:.4} %) ; {gagne}/{me}", t0.elapsed().as_secs_f64(), if *pondere { "pondérée" } else { "uniforme" }, 100.0 * ew / en, 100.0 * er, 100.0 * err_sortie_base);
                    pts.push(format!("{{\"bits\": {bpp:.5}, \"erreur_poids\": {:.6}, \"erreur_sortie\": {er:.6}, \"positions_ou_la_recette_gagne\": {gagne}}}", ew / en));
                }
                write!(s, "{}{{\"ponderee\": {pondere}, \"points\": [{}]}}", if iv > 0 { ", " } else { "" }, pts.join(", "))?;
            }
            s.push_str("]}");
            let _ = std::io::Write::flush(&mut std::io::stdout());
        }
    }
    s.push_str("\n]}\n");
    print!("{s}");
    Ok(())
}

/// y = W x en f64 (W rangée par rangée, f32).
fn produit_simple(w: &[f32], lignes: usize, colonnes: usize, x: &[f64], m: usize) -> Vec<f64> {
    let mut y = vec![0.0f64; m * lignes];
    y.par_chunks_mut(lignes).enumerate().for_each(|(p, yp)| {
        let xp = &x[p * colonnes..(p + 1) * colonnes];
        for (r, v) in yp.iter_mut().enumerate() {
            let wr = &w[r * colonnes..(r + 1) * colonnes];
            let mut s = 0.0f64;
            for c in 0..colonnes {
                s += wr[c] as f64 * xp[c];
            }
            *v = s;
        }
    });
    y
}
