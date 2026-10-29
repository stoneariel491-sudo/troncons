//! Taux réel des codes MXFP4 de gpt-oss, codés par le rANS de l'étude 03 et décodés exactement.
//!
//! Deux variantes, mêmes flux, mêmes tables, même comptabilité que l'arbitre (F1, A_flux) :
//!   - `identite` : les octets du fichier, tels quels (sans perte au bit) ;
//!   - `zero` : chaque demi-octet 8 (−0) remplacé par 0 (+0) avant le codage. Les deux codes valent
//!     exactement zéro (K[8] = −0, et ggml les lit tous deux comme l'entier 0 dans `kvalues_mxfp4`) :
//!     ce sont des **codons synonymes**. La reconstruction est exacte en valeur, poids par poids ;
//!     seul le signe d'un zéro est perdu, qui ne change aucun produit ni aucune somme.
//!
//!   - `nib_k` et `nib_kq` (zéro fondu aussi) : demi-octets en flux séparés par contexte, alphabet de
//!     16 ; contexte κ seul, puis κ × q où q est le quartile de l'énergie de la colonne d'entrée
//!     (v = K · 2^δ, sommée sur les lignes et les experts du tenseur ; carte de 2 bits par colonne,
//!     720 octets par tenseur, comptée). Les tables de 16 fréquences comptent 32 octets.
//!
//! Comptabilité (celle de `outils/arbitre/decoupe`, variante A_flux) : par matrice d'expert, trois
//! flux de codes, un par classe d'échelle κ (sous, égale, au-dessus de la médiane haute de la ligne),
//! chacun bourré à 128 octets et rangé à 16 octets près avec 16 octets d'en-tête ; un flux δ ;
//! par tenseur, une table de 384 octets par flux distinct et un octet de médiane par ligne.
//!
//! Témoins : chaque flux est décodé et comparé octet à octet à sa source ; toutes les voies finissent
//! sur L ; la variante `zero` rend, demi-octet par demi-octet, la valeur d'origine (d == o, ou o == 8
//! et d == 0). Cassure (--casser) : la variante `zero` envoie 8 sur 1 ; le témoin de valeur tombe.
//!
//! Usage : taux_reel <gguf> <sortie.json> [--couches 0,8,16,23 | --toutes] [--fils N] [--casser]

#![allow(dead_code)]

#[path = "../../../../03-entropie/rans/src/lib.rs"]
mod rans;

use rans::*;
use rayon::prelude::*;
use std::time::Instant;

const MACRO_PAR_TUILE: usize = 256;
const COLONNES: usize = 2880;
const ROLES: [&str; 3] = ["ffn_gate_exps", "ffn_up_exps", "ffn_down_exps"];

fn octets_flux(f: &Flux) -> usize {
    (16 + f.octets_codes()).div_ceil(16) * 16
}

fn table256(c: &[u64]) -> Table256 {
    let mut c2 = c.to_vec();
    if c2.iter().sum::<u64>() == 0 {
        c2[0] = 1;
    }
    Table256::depuis_comptes(&c2)
}

/// Code puis décode un flux d'octets ; rend (octets rangés, exact, voies hors de L).
fn aller_retour(src: &[u8], t: &Table256) -> (usize, bool, u32) {
    if src.is_empty() {
        return (0, true, 0);
    }
    let mut s = src.to_vec();
    s.resize(s.len().div_ceil(128) * 128, 0);
    let f = coder_octets(&s, t, MACRO_PAR_TUILE);
    let mut d = vec![0u32; s.len() / 4];
    let mut hors = 0;
    for ti in 0..f.tuiles.len() {
        let [_, nb, mot0, _] = f.tuiles[ti];
        hors += decoder_tuile_octets(&f, &t.lut, ti, &mut d[mot0 as usize..(mot0 + nb * VOIES as u32) as usize]);
    }
    let d8: Vec<u8> = d.iter().flat_map(|w| w.to_le_bytes()).collect();
    (octets_flux(&f), d8 == s, hors)
}

/// Code puis décode des demi-octets (alphabet 16, table `t`) ; rend (octets rangés, exact, hors L).
fn aller_retour_nib(nibs: &[u8], t: &Table) -> (usize, bool, u32) {
    if nibs.is_empty() {
        return (0, true, 0);
    }
    let mut s: Vec<u8> = nibs.chunks(2).map(|c| c[0] | (c.get(1).copied().unwrap_or(0) << 4)).collect();
    s.resize(s.len().div_ceil(128) * 128, 0);
    let f = coder(&s, t, MACRO_PAR_TUILE);
    let mut d = vec![0u32; s.len() / 4];
    let mut hors = 0;
    for ti in 0..f.tuiles.len() {
        let [_, nb, mot0, _] = f.tuiles[ti];
        hors += decoder_tuile(&f, &t.lut, ti, &mut d[mot0 as usize..(mot0 + nb * VOIES as u32) as usize]);
    }
    let d8: Vec<u8> = d.iter().flat_map(|w| w.to_le_bytes()).collect();
    (octets_flux(&f), d8 == s, hors)
}

fn table16(c: &[u64; 16]) -> Table {
    let mut c2 = *c;
    if c2.iter().sum::<u64>() == 0 {
        c2[0] = 1;
    }
    Table::depuis_comptes(&c2)
}

/// Quantile à interpolation linéaire (celui de numpy par défaut).
fn quantile(tri: &[f64], p: f64) -> f64 {
    let h = p * (tri.len() - 1) as f64;
    let i = h.floor() as usize;
    let f = h - i as f64;
    if i + 1 < tri.len() { tri[i] + f * (tri[i + 1] - tri[i]) } else { tri[i] }
}

const MAGV: [f64; 8] = [0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0];

fn canon(o: u8, casser: bool) -> u8 {
    let c = |n: u8| if n == 8 { if casser { 1 } else { 0 } } else { n };
    c(o & 15) | (c(o >> 4) << 4)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let chemin = &args[1];
    let sortie = &args[2];
    let fils: usize = args.iter().position(|a| a == "--fils").map(|i| args[i + 1].parse().unwrap()).unwrap_or(4);
    let casser = args.iter().any(|a| a == "--casser");
    let pool = rayon::ThreadPoolBuilder::new().num_threads(fils).build().unwrap();
    let infos = lire_entete_gguf(chemin);
    let n_couches = infos.iter().filter(|t| t.nom.ends_with("ffn_gate_exps.weight")).count();
    let couches: Vec<usize> = if args.iter().any(|a| a == "--toutes") {
        (0..n_couches).collect()
    } else {
        let s = args.iter().position(|a| a == "--couches").map(|i| args[i + 1].clone()).unwrap_or("0,8,16,23".into());
        s.split(',').map(|x| x.parse().unwrap()).collect()
    };
    let t0 = Instant::now();
    let mut lignes_json = Vec::new();
    let (mut tot_poids, mut tot_id, mut tot_z, mut tot_delta, mut tot_med, mut tot_tab_id, mut tot_tab_z) = (0u64, 0usize, 0usize, 0usize, 0usize, 0usize, 0usize);
    let (mut tous_exacts, mut valeur_ok, mut tot_hors) = (true, true, 0u32);
    let (mut tot_nk, mut tot_nkq) = (0usize, 0usize);
    for &l in &couches {
        for role in ROLES {
            let nom = format!("blk.{l}.{role}.weight");
            let info = infos.iter().find(|t| t.nom == nom).expect("tenseur absent");
            assert_eq!(info.type_ggml, 39, "{nom} n'est pas en MXFP4");
            let brut = lire_tenseur(chemin, info);
            let (ech, qs) = separer_blocs(39, &brut);
            drop(brut);
            let blocs_ligne = COLONNES / 32;
            let lignes_tot = ech.len() / blocs_ligne;
            let experts = (info.nb_poids as usize) / (COLONNES * COLONNES).max(1);
            let lignes_exp = lignes_tot / experts;
            // δ et κ de chaque bloc (médiane haute de la ligne, comme taux_mxfp4.rs).
            let mut delta = vec![0u8; ech.len()];
            let mut kappa = vec![0u8; ech.len()];
            for (r, ligne) in ech.chunks_exact(blocs_ligne).enumerate() {
                let mut tri = ligne.to_vec();
                tri.sort_unstable();
                let med = tri[blocs_ligne / 2];
                for (b, &e) in ligne.iter().enumerate() {
                    delta[r * blocs_ligne + b] = e.wrapping_sub(med).wrapping_add(128);
                    kappa[r * blocs_ligne + b] = (e > med) as u8 + (e >= med) as u8;
                }
            }
            let qz: Vec<u8> = qs.iter().map(|&o| canon(o, casser)).collect();
            // Classe de colonne : quartile de l'énergie relative v = K · 2^δ sur le tenseur.
            let mut energie = vec![0f64; COLONNES];
            for b in 0..ech.len() {
                let d = delta[b] as i32 - 128;
                let w = (2f64).powi(2 * d);
                let c0 = (b % blocs_ligne) * 32;
                for j in 0..16 {
                    let o = qs[b * 16 + j];
                    energie[c0 + j] += w * MAGV[(o & 7) as usize].powi(2);
                    energie[c0 + j + 16] += w * MAGV[((o >> 4) & 7) as usize].powi(2);
                }
            }
            let mut tri = energie.clone();
            tri.sort_by(|a, b| a.partial_cmp(b).unwrap());
            let qv = [quantile(&tri, 0.25), quantile(&tri, 0.5), quantile(&tri, 0.75)];
            let classe_col: Vec<u8> = energie.iter().map(|&e| qv.iter().filter(|&&q| q < e).count() as u8).collect();
            // Demi-octet j d'un bloc b : j < 16 = faible de l'octet j, j ≥ 16 = fort de l'octet j − 16.
            let ctx_nib = |b: usize, j: usize| -> usize { kappa[b] as usize * 4 + classe_col[(b % blocs_ligne) * 32 + j] as usize };
            let nib = |b: usize, j: usize| -> u8 { if j < 16 { qz[b * 16 + j] & 15 } else { qz[b * 16 + j - 16] >> 4 } };
            let mut h_k = [[0u64; 16]; 3];
            let mut h_kq = [[0u64; 16]; 12];
            for b in 0..ech.len() {
                for j in 0..32 {
                    let c = nib(b, j) as usize;
                    h_k[kappa[b] as usize][c] += 1;
                    h_kq[ctx_nib(b, j)][c] += 1;
                }
            }
            let t_k: Vec<Table> = h_k.iter().map(table16).collect();
            let t_kq: Vec<Table> = h_kq.iter().map(table16).collect();
            // Tables par tenseur.
            let mut h_id = vec![vec![0u64; 256]; 3];
            let mut h_z = vec![vec![0u64; 256]; 3];
            for b in 0..ech.len() {
                let k = kappa[b] as usize;
                for j in 0..16 {
                    h_id[k][qs[b * 16 + j] as usize] += 1;
                    h_z[k][qz[b * 16 + j] as usize] += 1;
                }
            }
            let mut h_d = vec![0u64; 256];
            for &d in &delta {
                h_d[d as usize] += 1;
            }
            let t_id: Vec<Table256> = h_id.iter().map(|h| table256(h)).collect();
            let t_z: Vec<Table256> = h_z.iter().map(|h| table256(h)).collect();
            let t_d = table256(&h_d);
            let blocs_exp = lignes_exp * blocs_ligne;
            let res: Vec<(usize, usize, usize, bool, bool, u32, usize, usize)> = pool.install(|| {
                (0..experts)
                    .into_par_iter()
                    .map(|e| {
                        let b0 = e * blocs_exp;
                        let mut par_k_id: Vec<Vec<u8>> = vec![Vec::new(); 3];
                        let mut par_k_z: Vec<Vec<u8>> = vec![Vec::new(); 3];
                        for b in b0..b0 + blocs_exp {
                            let k = kappa[b] as usize;
                            par_k_id[k].extend_from_slice(&qs[b * 16..b * 16 + 16]);
                            par_k_z[k].extend_from_slice(&qz[b * 16..b * 16 + 16]);
                        }
                        let (mut o_id, mut o_z, mut ex, mut hors) = (0, 0, true, 0);
                        for k in 0..3 {
                            let (o, x, h) = aller_retour(&par_k_id[k], &t_id[k]);
                            o_id += o;
                            ex &= x;
                            hors += h;
                            let (o, x, h) = aller_retour(&par_k_z[k], &t_z[k]);
                            o_z += o;
                            ex &= x;
                            hors += h;
                        }
                        let mut nk: Vec<Vec<u8>> = vec![Vec::new(); 3];
                        let mut nkq: Vec<Vec<u8>> = vec![Vec::new(); 12];
                        for b in b0..b0 + blocs_exp {
                            for j in 0..32 {
                                let c = nib(b, j);
                                nk[kappa[b] as usize].push(c);
                                nkq[ctx_nib(b, j)].push(c);
                            }
                        }
                        let (mut o_nk, mut o_nkq) = (0, 0);
                        for k in 0..3 {
                            let (o, x, h) = aller_retour_nib(&nk[k], &t_k[k]);
                            o_nk += o;
                            ex &= x;
                            hors += h;
                        }
                        for k in 0..12 {
                            let (o, x, h) = aller_retour_nib(&nkq[k], &t_kq[k]);
                            o_nkq += o;
                            ex &= x;
                            hors += h;
                        }
                        let (o_d, x, h) = aller_retour(&delta[b0..b0 + blocs_exp], &t_d);
                        ex &= x;
                        hors += h;
                        // Témoin de valeur : la source de la variante zéro rend la valeur d'origine.
                        let mut val = true;
                        for b in b0 * 16..(b0 + blocs_exp) * 16 {
                            for (o, d) in [(qs[b] & 15, qz[b] & 15), (qs[b] >> 4, qz[b] >> 4)] {
                                val &= d == o || (o == 8 && d == 0);
                            }
                        }
                        (o_id, o_z, o_d, ex, val, hors, o_nk, o_nkq)
                    })
                    .collect()
            });
            let poids = info.nb_poids;
            let o_id: usize = res.iter().map(|r| r.0).sum();
            let o_z: usize = res.iter().map(|r| r.1).sum();
            let o_d: usize = res.iter().map(|r| r.2).sum();
            let ex = res.iter().all(|r| r.3);
            let val = res.iter().all(|r| r.4);
            let hors: u32 = res.iter().map(|r| r.5).sum();
            let o_nk: usize = res.iter().map(|r| r.6).sum();
            let o_nkq: usize = res.iter().map(|r| r.7).sum();
            let tab_nk = 32 * 3 + 384;
            let tab_nkq = 32 * 12 + 384 + COLONNES / 4;
            tot_nk += o_nk + tab_nk;
            tot_nkq += o_nkq + tab_nkq;
            let tab_id = 384 * h_id.iter().filter(|h| h.iter().sum::<u64>() > 0).count() + 384;
            let tab_z = 384 * h_z.iter().filter(|h| h.iter().sum::<u64>() > 0).count() + 384;
            let med = lignes_tot;
            tot_poids += poids;
            tot_id += o_id;
            tot_z += o_z;
            tot_delta += o_d;
            tot_med += med;
            tot_tab_id += tab_id;
            tot_tab_z += tab_z;
            tous_exacts &= ex;
            valeur_ok &= val;
            tot_hors += hors;
            let bpp = |o: usize| o as f64 * 8.0 / poids as f64;
            eprintln!("{nom:28} codes {:.4} -> zéro fondu {:.4} ; demi-octets κ {:.4}, κ×colonne {:.4} | δ {:.4} | exacts {ex} valeur {val} hors L {hors} | {:.0} s",
                bpp(o_id), bpp(o_z), bpp(o_nk), bpp(o_nkq), bpp(o_d), t0.elapsed().as_secs_f64());
            lignes_json.push(format!(
                "    {{\"nom\": {nom:?}, \"poids\": {poids}, \"bpp_codes_identite\": {:.6}, \"bpp_codes_zero_fondu\": {:.6}, \"bpp_delta\": {:.6}, \"bpp_total_identite\": {:.6}, \"bpp_total_zero_fondu\": {:.6}, \"bpp_total_nib_kappa\": {:.6}, \"bpp_total_nib_kappa_colonne\": {:.6}, \"exacts\": {ex}, \"valeur_exacte\": {val}, \"voies_hors_L\": {hors}}}",
                bpp(o_id), bpp(o_z), bpp(o_d), bpp(o_id + o_d + med + tab_id), bpp(o_z + o_d + med + tab_z),
                bpp(o_nk + tab_nk + o_d + med), bpp(o_nkq + tab_nkq + o_d + med)));
        }
    }
    let bpp = |o: usize| o as f64 * 8.0 / tot_poids as f64;
    let total_id = tot_id + tot_delta + tot_med + tot_tab_id;
    let total_z = tot_z + tot_delta + tot_med + tot_tab_z;
    let json = format!(
        "{{\n  \"outil\": \"outils/genome/predictif-elagage/taux_reel\",\n  \"fichier\": {chemin:?},\n  \"couches\": {couches:?},\n  \"casser\": {casser},\n  \"duree_s\": {:.1},\n  \"poids\": {tot_poids},\n  \"bpp\": {{\"codes_identite\": {:.6}, \"codes_zero_fondu\": {:.6}, \"delta\": {:.6}, \"medianes\": {:.6}, \"tables_identite\": {:.6}, \"tables_zero_fondu\": {:.6}, \"total_identite\": {:.6}, \"total_zero_fondu\": {:.6}, \"total_nib_kappa_zero\": {:.6}, \"total_nib_kappa_colonne_zero\": {:.6}}},\n  \"gain_bits_par_poids\": {:.6},\n  \"rapport_zero_sur_identite\": {:.6},\n  \"temoins\": {{\"tous_exacts\": {tous_exacts}, \"valeur_exacte\": {valeur_ok}, \"voies_hors_L\": {tot_hors}}},\n  \"tenseurs\": [\n{}\n  ]\n}}\n",
        t0.elapsed().as_secs_f64(), bpp(tot_id), bpp(tot_z), bpp(tot_delta), bpp(tot_med), bpp(tot_tab_id), bpp(tot_tab_z), bpp(total_id), bpp(total_z),
        bpp(tot_nk + tot_delta + tot_med), bpp(tot_nkq + tot_delta + tot_med),
        bpp(total_id) - bpp(total_z), total_z as f64 / total_id as f64, lignes_json.join(",\n"));
    std::fs::write(sortie, &json).unwrap();
    eprintln!("TOTAL : identité {:.4}, zéro fondu {:.4} bits/poids (gain {:.4}) ; demi-octets κ {:.4}, κ×colonne {:.4} ; exacts {tous_exacts}, valeur {valeur_ok}, hors L {tot_hors} ; {:.0} s",
        bpp(total_id), bpp(total_z), bpp(total_id) - bpp(total_z), bpp(tot_nk + tot_delta + tot_med), bpp(tot_nkq + tot_delta + tot_med), t0.elapsed().as_secs_f64());
}
