//! Taux réel d'un plan avec perte (élagage, remplissage inverse) : les cellules de chaque poids sont
//! codées par le rANS de l'étude 03, une table par (contexte du plan, κ), choisie **symbole par
//! symbole** (le décodeur connaît e, κ et la classe de colonne avant les codes), puis décodées
//! exactement.
//!
//! Plan : le format `.bin` de la sonde (b"PEPL" ; par tenseur couche, rôle, mode, a, b, n_col,
//! tables f64 [(b − a + 1)·n_col][16], cartes de colonnes si n_col > 1). Le symbole d'un code est le
//! rang de sa valeur reconstruite parmi les valeurs distinctes de la table de son contexte : deux
//! codes de la même cellule ont la même valeur, deux cellules distinctes des centres distincts.
//!
//! Géométrie : celle de la v1 de l'étude 03 (alphabet 16, 8 demi-octets par mot de 32 bits, 32
//! voies, tuiles de 256 macro-pas) ; seul le choix de table par symbole change. Comptabilité : flux
//! codes (16 octets d'en-tête, rangé à 16 octets), flux δ (alphabet octet, comme `taux_reel`),
//! médianes (1 octet par ligne), tables (32 octets par table non vide), cartes (2 bits par colonne
//! et par matrice d'expert si n_col > 1).
//!
//! Témoins : symboles décodés égaux aux symboles codés, voies finissant sur L ; cassure (--casser) :
//! le décodeur lit la table du contexte voisin pour un symbole sur mille ; l'exactitude tombe.
//!
//! Usage : taux_plan <gguf> <plan.bin> <sortie.json> [--fils N] [--casser]

#![allow(dead_code)]

#[path = "../../../../../03-entropie/rans/src/lib.rs"]
mod rans;

use rans::*;
use rayon::prelude::*;
use std::time::Instant;

const MACRO_PAR_TUILE: usize = 256;
const COLONNES: usize = 2880;
const ROLES: [&str; 3] = ["ffn_gate_exps", "ffn_up_exps", "ffn_down_exps"];

struct PlanTenseur {
    couche: usize,
    role: usize,
    mode: u32,
    a: i32,
    b: i32,
    n_col: usize,
    table: Vec<f64>,
    cartes: Vec<u8>,
    /// n_col = 16 : cartes de lignes aussi (classe = 4 · ligne + colonne).
    cartes_lig: Vec<u8>,
}

fn lire_plan(chemin: &str) -> Vec<PlanTenseur> {
    let o = std::fs::read(chemin).unwrap();
    assert_eq!(&o[0..4], b"PEPL");
    let mut p = 4;
    let u = |p: &mut usize| -> u32 {
        let v = u32::from_le_bytes(o[*p..*p + 4].try_into().unwrap());
        *p += 4;
        v
    };
    let n = u(&mut p) as usize;
    let mut v = Vec::new();
    for _ in 0..n {
        let couche = u(&mut p) as usize;
        let role = u(&mut p) as usize;
        let mode = u(&mut p);
        let a = u(&mut p) as i32;
        let b = u(&mut p) as i32;
        let n_col = u(&mut p) as usize;
        let nt = (b - a + 1) as usize * n_col * 16;
        let table: Vec<f64> = o[p..p + nt * 8].chunks_exact(8).map(|c| f64::from_le_bytes(c.try_into().unwrap())).collect();
        p += nt * 8;
        let cartes = if n_col > 1 {
            let c = o[p..p + 32 * COLONNES].to_vec();
            p += 32 * COLONNES;
            c
        } else {
            Vec::new()
        };
        let cartes_lig = if n_col == 16 {
            let c = o[p..p + 32 * COLONNES].to_vec();
            p += 32 * COLONNES;
            c
        } else {
            Vec::new()
        };
        v.push(PlanTenseur { couche, role, mode, a, b, n_col, table, cartes, cartes_lig });
    }
    assert_eq!(p, o.len(), "plan mal lu");
    v
}

fn octets_flux(f: &Flux) -> usize {
    (16 + f.octets_codes()).div_ceil(16) * 16
}

fn table16(c: &[u64; 16]) -> Table {
    let mut c2 = *c;
    if c2.iter().sum::<u64>() == 0 {
        c2[0] = 1;
    }
    Table::depuis_comptes(&c2)
}

fn table256(c: &[u64]) -> Table256 {
    let mut c2 = c.to_vec();
    if c2.iter().sum::<u64>() == 0 {
        c2[0] = 1;
    }
    Table256::depuis_comptes(&c2)
}

/// Code une suite de symboles 4 bits (longueur multiple de 256), table choisie par symbole.
fn coder_ctx(sym: &[u8], ctx: &[u32], tables: &[Table]) -> Flux {
    let nb_macro_total = sym.len() / (VOIES * 8);
    let (mut tuiles, mut etats, mut mots, mut pile) = (Vec::new(), Vec::new(), Vec::<u16>::new(), Vec::<u16>::new());
    let mut m0 = 0;
    while m0 < nb_macro_total {
        let nb = MACRO_PAR_TUILE.min(nb_macro_total - m0);
        let mut x = [L as u64; VOIES];
        pile.clear();
        for m in (0..nb).rev() {
            for k in (0..8).rev() {
                for v in (0..VOIES).rev() {
                    let n = ((m0 + m) * VOIES + v) * 8 + k;
                    let t = &tables[ctx[n] as usize];
                    let s = sym[n] as usize;
                    let f = t.freq[s] as u64;
                    assert!(f > 0, "symbole de fréquence nulle");
                    let mut xv = x[v];
                    if xv >= f << 20 {
                        pile.push((xv & 0xFFFF) as u16);
                        xv >>= 16;
                    }
                    x[v] = ((xv / f) << BITS_PROBA) + (xv % f) + t.cumul[s] as u64;
                }
            }
        }
        tuiles.push([mots.len() as u32, nb as u32, (m0 * VOIES) as u32, 0]);
        etats.extend(x.iter().map(|&v| v as u32));
        mots.extend(pile.iter().rev());
        m0 += nb;
    }
    Flux { tuiles, etats, mots, octets_source: sym.len() / 2 }
}

/// Décode ; rend (symboles, voies hors de L). `casser` : un symbole sur mille lit la table voisine.
fn decoder_ctx(f: &Flux, ctx: &[u32], tables: &[Table], casser: bool) -> (Vec<u8>, u32) {
    let mut sortie = vec![0u8; f.octets_source * 2];
    let mut hors = 0;
    for (t, &[debut, nb, mot0, _]) in f.tuiles.iter().enumerate() {
        let mut x = [0u32; VOIES];
        x.copy_from_slice(&f.etats[t * VOIES..(t + 1) * VOIES]);
        let mots = &f.mots[debut as usize..];
        let mut p = 0usize;
        for m in 0..nb as usize {
            for k in 0..8 {
                for v in 0..VOIES {
                    let n = ((mot0 as usize / VOIES + m) * VOIES + v) * 8 + k;
                    let mut c = ctx[n] as usize;
                    if casser && n % 1000 == 7 {
                        c = (c + 1) % tables.len();
                    }
                    let lut = &tables[c].lut;
                    let xv = x[v];
                    let e = lut[(xv & (M - 1)) as usize];
                    let y = ((e >> 4) & 0x1FFF) * (xv >> BITS_PROBA) + (e >> 17);
                    sortie[n] = (e & 15) as u8;
                    let lit = (y < L) as usize;
                    let w = *mots.get(p).unwrap_or(&0) as u32;
                    x[v] = if lit == 1 { (y << 16) | w } else { y };
                    p += lit;
                }
            }
        }
        hors += x.iter().filter(|&&v| v != L).count() as u32;
    }
    (sortie, hors)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let (chemin, plan_chemin, sortie) = (&args[1], &args[2], &args[3]);
    let fils: usize = args.iter().position(|a| a == "--fils").map(|i| args[i + 1].parse().unwrap()).unwrap_or(4);
    let casser = args.iter().any(|a| a == "--casser");
    let pool = rayon::ThreadPoolBuilder::new().num_threads(fils).build().unwrap();
    let infos = lire_entete_gguf(chemin);
    let plan = lire_plan(plan_chemin);
    let t0 = Instant::now();
    let (mut tot_poids, mut tot_codes, mut tot_delta, mut tot_med, mut tot_tab, mut tot_cartes) = (0u64, 0usize, 0usize, 0usize, 0usize, 0usize);
    let (mut exact, mut tot_hors) = (true, 0u32);
    let mut lignes = Vec::new();
    for pt in &plan {
        let nom = format!("blk.{}.{}.weight", pt.couche, ROLES[pt.role]);
        let info = infos.iter().find(|t| t.nom == nom).expect("tenseur absent");
        let brut = lire_tenseur(chemin, info);
        let (ech, qs) = separer_blocs(39, &brut);
        drop(brut);
        let bl = COLONNES / 32;
        let experts = info.nb_poids as usize / (COLONNES * COLONNES);
        let blocs_exp = ech.len() / experts;
        let nctx_plan = (pt.b - pt.a + 1) as usize * pt.n_col;
        // Rang de chaque code dans la table de son contexte (symbole de cellule).
        let mut rang = vec![[0u8; 16]; nctx_plan];
        for c in 0..nctx_plan {
            let t = &pt.table[c * 16..(c + 1) * 16];
            let mut vals: Vec<f64> = t.to_vec();
            vals.sort_by(|a, b| a.partial_cmp(b).unwrap());
            vals.dedup();
            for code in 0..16 {
                rang[c][code] = vals.iter().position(|&v| v == t[code]).unwrap() as u8;
            }
        }
        // δ, κ, contexte du plan par bloc.
        let mut delta = vec![0u8; ech.len()];
        let mut kappa = vec![0u8; ech.len()];
        let mut ctxp = vec![0u32; ech.len()];
        for (r, ligne) in ech.chunks_exact(bl).enumerate() {
            let mut tri = ligne.to_vec();
            tri.sort_unstable();
            let med = tri[bl / 2];
            for (b, &e) in ligne.iter().enumerate() {
                let i = r * bl + b;
                delta[i] = e.wrapping_sub(med).wrapping_add(128);
                kappa[i] = (e > med) as u8 + (e >= med) as u8;
                let x = if pt.mode == 1 { e as i32 } else { e as i32 - med as i32 };
                ctxp[i] = (x.clamp(pt.a, pt.b) - pt.a) as u32;
            }
        }
        // Contexte de table de chaque demi-octet : (contexte du plan × n_col + colonne) × 3 + κ.
        let ctx_de = |e_idx: usize, b: usize, j: usize| -> (usize, usize) {
            let col = (b % bl) * 32 + j;
            let ligne = (b - e_idx * blocs_exp) / bl;
            let cc = if pt.n_col == 16 {
                pt.cartes_lig[e_idx * COLONNES + ligne] as usize * 4 + pt.cartes[e_idx * COLONNES + col] as usize
            } else if pt.n_col > 1 {
                pt.cartes[e_idx * COLONNES + col] as usize
            } else {
                0
            };
            let cp = ctxp[b] as usize * pt.n_col + cc;
            (cp, cp * 3 + kappa[b] as usize)
        };
        let code_de = |b: usize, j: usize| -> usize { (if j < 16 { qs[b * 16 + j] & 15 } else { qs[b * 16 + j - 16] >> 4 }) as usize };
        let n_tab = nctx_plan * 3;
        let mut h = vec![[0u64; 16]; n_tab];
        for e_idx in 0..experts {
            for b in e_idx * blocs_exp..(e_idx + 1) * blocs_exp {
                for j in 0..32 {
                    let (cp, ct) = ctx_de(e_idx, b, j);
                    h[ct][rang[cp][code_de(b, j)] as usize] += 1;
                }
            }
        }
        let tables: Vec<Table> = h.iter().map(table16).collect();
        let tab_non_vides = h.iter().filter(|x| x.iter().sum::<u64>() > 0).count();
        let mut hd = vec![0u64; 256];
        for &d in &delta {
            hd[d as usize] += 1;
        }
        let td = table256(&hd);
        let res: Vec<(usize, usize, bool, u32)> = pool.install(|| {
            (0..experts)
                .into_par_iter()
                .map(|e_idx| {
                    let b0 = e_idx * blocs_exp;
                    let n = blocs_exp * 32;
                    let mut sym = vec![0u8; n.div_ceil(VOIES * 8) * VOIES * 8];
                    let mut ctx = vec![0u32; sym.len()];
                    for b in b0..b0 + blocs_exp {
                        for j in 0..32 {
                            let (cp, ct) = ctx_de(e_idx, b, j);
                            let i = (b - b0) * 32 + j;
                            sym[i] = rang[cp][code_de(b, j)];
                            ctx[i] = ct as u32;
                        }
                    }
                    // Bourrage : symbole le plus fréquent de la table 0 non vide.
                    for i in n..sym.len() {
                        ctx[i] = ctx[n - 1];
                        sym[i] = sym[n - 1];
                    }
                    let f = coder_ctx(&sym, &ctx, &tables);
                    let (d, hors) = decoder_ctx(&f, &ctx, &tables, casser);
                    let mut ok = d == sym;
                    // δ.
                    let mut ds = delta[b0..b0 + blocs_exp].to_vec();
                    ds.resize(ds.len().div_ceil(128) * 128, 0);
                    let fd = coder_octets(&ds, &td, MACRO_PAR_TUILE);
                    let mut dd = vec![0u32; ds.len() / 4];
                    let mut hd = 0;
                    for ti in 0..fd.tuiles.len() {
                        let [_, nb, mot0, _] = fd.tuiles[ti];
                        hd += decoder_tuile_octets(&fd, &td.lut, ti, &mut dd[mot0 as usize..(mot0 + nb * VOIES as u32) as usize]);
                    }
                    let dd8: Vec<u8> = dd.iter().flat_map(|w| w.to_le_bytes()).collect();
                    ok &= dd8 == ds;
                    (octets_flux(&f), octets_flux(&fd), ok, hors + hd)
                })
                .collect()
        });
        let poids = info.nb_poids;
        let o_c: usize = res.iter().map(|r| r.0).sum();
        let o_d: usize = res.iter().map(|r| r.1).sum();
        let ex = res.iter().all(|r| r.2);
        let hors: u32 = res.iter().map(|r| r.3).sum();
        let med = ech.len() / bl;
        let tab = 32 * tab_non_vides + 384;
        let cartes = if pt.n_col == 16 { 2 * experts * COLONNES / 4 } else if pt.n_col > 1 { experts * COLONNES / 4 } else { 0 };
        tot_poids += poids;
        tot_codes += o_c;
        tot_delta += o_d;
        tot_med += med;
        tot_tab += tab;
        tot_cartes += cartes;
        exact &= ex;
        tot_hors += hors;
        let bpp = |o: usize| o as f64 * 8.0 / poids as f64;
        eprintln!("{nom:28} codes {:.4} | total {:.4} | tables {tab_non_vides} | exact {ex} hors L {hors} | {:.0} s",
            bpp(o_c), bpp(o_c + o_d + med + tab + cartes), t0.elapsed().as_secs_f64());
        lignes.push(format!("    {{\"nom\": {nom:?}, \"poids\": {poids}, \"bpp_codes\": {:.6}, \"bpp_total\": {:.6}, \"tables\": {tab_non_vides}, \"exact\": {ex}, \"voies_hors_L\": {hors}}}",
            bpp(o_c), bpp(o_c + o_d + med + tab + cartes)));
    }
    let bpp = |o: usize| o as f64 * 8.0 / tot_poids as f64;
    let total = tot_codes + tot_delta + tot_med + tot_tab + tot_cartes;
    let json = format!(
        "{{\n  \"outil\": \"outils/genome/predictif-elagage/taux_reel (taux_plan)\",\n  \"fichier\": {chemin:?},\n  \"plan\": {plan_chemin:?},\n  \"casser\": {casser},\n  \"duree_s\": {:.1},\n  \"poids\": {tot_poids},\n  \"bpp\": {{\"codes\": {:.6}, \"delta\": {:.6}, \"medianes\": {:.6}, \"tables\": {:.6}, \"cartes\": {:.6}, \"total\": {:.6}}},\n  \"temoins\": {{\"exact\": {exact}, \"voies_hors_L\": {tot_hors}}},\n  \"tenseurs\": [\n{}\n  ]\n}}\n",
        t0.elapsed().as_secs_f64(), bpp(tot_codes), bpp(tot_delta), bpp(tot_med), bpp(tot_tab), bpp(tot_cartes), bpp(total), lignes.join(",\n"));
    std::fs::write(sortie, json).unwrap();
    eprintln!("TOTAL : {:.4} bits/poids (codes {:.4}) ; exact {exact}, hors L {tot_hors} ; {:.0} s", bpp(total), bpp(tot_codes), t0.elapsed().as_secs_f64());
}
