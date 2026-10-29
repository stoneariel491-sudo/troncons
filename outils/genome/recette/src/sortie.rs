//! L'erreur sur la sortie des experts, pour des entrées réelles.
//!
//! Entrées : les états normalisés h (entrée des experts) et le routage capturés par la fourche de
//! l'éclaireur (`outils/genome/eclaireur/capture`, référence f64 arrondie en f32 à l'écriture) :
//! `h-Lll.f32` (n × 2 880, f32 petit-boutiste) et `routage-Lll.bin` (par position : 4 octets
//! d'experts, puis 4 poids f32).
//!
//! Pour un expert e de la couche l et les positions routées vers lui :
//!   y = W_down · SwiGLU-oai(W_gate h + b_gate, W_up h + b_up) + b_down,
//! calculé en f64 avec les poids exacts (MXFP4), la base de B, et la recette. Erreur relative de
//! sortie : Σ‖y − ŷ‖² / Σ‖y‖² sur les positions routées.

use anyhow::{Context, Result, bail};
use rayon::prelude::*;
use std::fmt::Write as _;
use std::path::Path;

use crate::base::base_valeur;
use crate::codons::{self, Code, Forme, Melangeur, Travail};
use crate::donnees::{ExpertMx, FICHIER_20B, Modele, ROLES};
use crate::mesure::{CENTRES, Norme, Rangee, preparer, reconstruire};
use trc_reference::gguf::GGML_F32;
use trc_reference::ops::swiglu_oai;
use trc_reference::poids::rangee_f64;

/// Les positions routées vers l'expert e, et leurs entrées.
pub fn entrees(dossier: &Path, l: usize, e: usize, d: usize, max: usize) -> Result<(Vec<f32>, usize)> {
    let h = std::fs::read(dossier.join(format!("h-L{l:02}.f32"))).with_context(|| format!("h-L{l:02}"))?;
    let r = std::fs::read(dossier.join(format!("routage-L{l:02}.bin")))?;
    let n = r.len() / 20;
    if h.len() != n * d * 4 {
        bail!("h-L{l:02} : {} octets pour {n} positions", h.len());
    }
    let mut x = Vec::new();
    let mut m = 0;
    for p in 0..n {
        let ch = &r[p * 20..p * 20 + 4];
        if ch.iter().any(|&c| c as usize == e) {
            for c in 0..d {
                let o = (p * d + c) * 4;
                x.push(f32::from_le_bytes(h[o..o + 4].try_into().unwrap()));
            }
            m += 1;
            if m == max {
                break;
            }
        }
    }
    Ok((x, m))
}

/// Moments E[x_c²] des entrées de la couche (toutes positions), pour la pondération par les entrées.
pub fn moments(dossier: &Path, l: usize, d: usize) -> Result<Vec<f64>> {
    let h = std::fs::read(dossier.join(format!("h-L{l:02}.f32")))?;
    let n = h.len() / (d * 4);
    let mut m = vec![0.0f64; d];
    for p in 0..n {
        for c in 0..d {
            let o = (p * d + c) * 4;
            let v = f32::from_le_bytes(h[o..o + 4].try_into().unwrap()) as f64;
            m[c] += v * v;
        }
    }
    for v in m.iter_mut() {
        *v /= n as f64;
    }
    Ok(m)
}

fn biais(m: &Modele, l: usize, role: &str, e: usize) -> Result<Vec<f64>> {
    let t = m.g.tenseur(&format!("blk.{l}.{role}.bias"))?;
    if t.type_ggml != GGML_F32 {
        bail!("biais non F32");
    }
    let n = t.ne[0];
    let o = m.g.lire_plage(t.decalage + e as u64 * n * 4, n * 4)?;
    let mut v = vec![0.0; n as usize];
    rangee_f64(GGML_F32, &o, &mut v);
    Ok(v)
}

/// y = W x pour m entrées (W : lignes × colonnes f32 rangée par rangée), en f64.
fn produit(w: &[f32], lignes: usize, colonnes: usize, x: &[f64], m: usize) -> Vec<f64> {
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

/// La sortie de l'expert pour m entrées (biais compris).
pub fn sortie_expert(w: &[Vec<f32>; 3], b: &[Vec<f64>; 3], x: &[f64], m: usize, d: usize, f: usize) -> Vec<f64> {
    let g = produit(&w[0], f, d, x, m);
    let u = produit(&w[1], f, d, x, m);
    let mut a = vec![0.0f64; m * f];
    for p in 0..m {
        for i in 0..f {
            a[p * f + i] = swiglu_oai(g[p * f + i] + b[0][i], u[p * f + i] + b[1][i]);
        }
    }
    let mut y = produit(&w[2], d, f, &a, m);
    for p in 0..m {
        for i in 0..d {
            y[p * d + i] += b[2][i];
        }
    }
    y
}

/// Une recette aux points de fonctionnement : formes, tables, et les (λ, relatif) à servir.
/// relatif = vrai : chaque rangée minimise son erreur **relative** + λ · bits (répartition qui ne
/// privilégie pas les rangées de grande énergie) ; faux : erreur absolue (le point du critère W).
pub struct Point {
    pub norme: Norme,
    pub codes: Vec<Code>,
    pub lambdas: Vec<(f64, bool)>,
    pub graine: u32,
    /// pondération des colonnes (E[x²]) ou vide
    pub om_col: Vec<f32>,
}

/// Code toutes les rangées d'un expert ; un seul Viterbi par (rangée, forme), puis chaque point
/// choisit sa forme. Rend, par point, (reconstruction, bits, erreur absolue).
pub fn coder_expert(ex: &ExpertMx, pt: &Point) -> Vec<(Vec<f32>, f64, f64)> {
    let n = ex.colonnes;
    let np = pt.lambdas.len();
    let res: Vec<Vec<(Vec<f32>, f64, f64)>> = (0..ex.lignes)
        .into_par_iter()
        .map_init(Travail::new, |w, r| {
            let mut rg: Rangee = preparer(ex, r, pt.norme, pt.graine, &CENTRES);
            if !pt.om_col.is_empty() {
                for (o, &c) in rg.om.iter_mut().zip(pt.om_col.iter()) {
                    *o *= c;
                }
            }
            let mut essais: Vec<(f64, f64, Vec<u32>)> = Vec::new();
            for code in pt.codes.iter() {
                let b = codons::viterbi(&rg.x, &rg.om, code, w);
                let mut bits = code.forme.bits_brin(n) as f64 + 3.0;
                if pt.norme == Norme::Tourne {
                    bits += 16.0;
                }
                essais.push((b.erreur * rg.facteur, bits, b.etats));
            }
            let mut w0 = vec![0.0f32; n];
            ex.ligne(r, &mut w0);
            let mut sorties = Vec::with_capacity(np);
            for &(lambda, relatif) in &pt.lambdas {
                let score = |e: f64, b: f64| if relatif { e / rg.energie.max(1e-300) } else { e } + lambda * b;
                let mut k = 0;
                for c in 1..essais.len() {
                    if score(essais[c].0, essais[c].1) < score(essais[k].0, essais[k].1) {
                        k = c;
                    }
                }
                let y = reconstruire(ex, r, &rg, &essais[k].2, &pt.codes[k], pt.norme, pt.graine);
                let e: f64 = w0.iter().zip(y.iter()).map(|(a, b)| ((a - b) as f64).powi(2)).sum();
                sorties.push((y, essais[k].1, e));
            }
            sorties
        })
        .collect();
    let mut tout = Vec::with_capacity(np);
    for i in 0..np {
        let mut rec = Vec::with_capacity(ex.lignes * n);
        let (mut bits, mut err) = (0.0, 0.0);
        for rr in res.iter() {
            rec.extend_from_slice(&rr[i].0);
            bits += rr[i].1;
            err += rr[i].2;
        }
        tout.push((rec, bits, err));
    }
    tout
}

/// Apprend les tables d'un tenseur exactement comme `codons` (mêmes rangées, mêmes itérations).
pub fn apprendre_codes(m: &Modele, couche: usize, role: &str, norme: Norme, l: u32, q: u32, formes: &[(u32, u32)], experts: &[usize], pas: usize, entrainement: usize, lloyd: usize, om_col: &[f32]) -> Result<Vec<Code>> {
    let t = m.tenseur(couche, role)?;
    let graine = (couche * 3 + ROLES.iter().position(|&r| r == role).unwrap()) as u32 + 1;
    let exs: Vec<ExpertMx> = experts.iter().map(|&e| m.expert(&t, e)).collect::<Result<_>>()?;
    let mut apprendre: Vec<Rangee> = Vec::new();
    for ex in &exs {
        for r in (0..ex.lignes).step_by(pas).take(entrainement) {
            let mut rg = preparer(ex, r, norme, graine, &CENTRES);
            if !om_col.is_empty() {
                for (o, &c) in rg.om.iter_mut().zip(om_col.iter()) {
                    *o *= c;
                }
            }
            apprendre.push(rg);
        }
    }
    let mut codes = Vec::new();
    for &(kb, v) in formes {
        let f = Forme { l, kb, v, q, melangeur: Melangeur::Fort };
        let xs: Vec<f32> = apprendre.iter().flat_map(|r| r.x.iter().copied()).collect();
        let os: Vec<f32> = apprendre.iter().flat_map(|r| r.om.iter().map(move |&o| o * r.facteur as f32)).collect();
        let mut code = Code::nouveau(f, codons::table_empirique(&xs, &os, q));
        for _ in 0..lloyd {
            let res: Vec<Vec<u32>> = apprendre.par_iter().map_init(Travail::new, |w, r| codons::viterbi(&r.x, &r.om, &code, w).etats).collect();
            let nt = 1usize << q;
            let (mut num, mut den) = (vec![0.0; nt], vec![0.0; nt]);
            for (r, e) in apprendre.iter().zip(res.iter()) {
                let os: Vec<f32> = r.om.iter().map(|&o| o * r.facteur as f32).collect();
                codons::accumuler_lloyd(&r.x, &os, e, &code, &mut num, &mut den);
            }
            for i in 0..nt {
                if den[i] > 0.0 {
                    code.table[i] = (num[i] / den[i]) as f32;
                }
            }
            code.deplier();
        }
        codes.push(code);
    }
    Ok(codes)
}

/// λ par bissection sur les rangées de l'échantillon (CSV de `codons`) : l'erreur relative de la
/// recette égale celle de la base sur ces rangées.
pub fn lambda_du_csv(csv: &str, tenseur: &str) -> Result<f64> {
    Ok(lambdas_du_csv(csv, tenseur)?.0)
}

/// (λ absolu au critère W, λ relatif qui dépense les mêmes bits sur l'échantillon).
pub fn lambdas_du_csv(csv: &str, tenseur: &str) -> Result<(f64, f64)> {
    let txt = std::fs::read_to_string(csv)?;
    let mut lignes = txt.lines();
    let tete: Vec<&str> = lignes.next().unwrap().split(',').collect();
    let nf = (tete.len() - 5) / 2;
    let (mut errs, mut bits) = (Vec::new(), Vec::new());
    let mut energies: Vec<f64> = Vec::new();
    let (mut en, mut eb) = (0.0, 0.0);
    for l in lignes {
        let c: Vec<&str> = l.split(',').collect();
        if c[0] != tenseur {
            continue;
        }
        en += c[3].parse::<f64>()?;
        energies.push(c[3].parse::<f64>()?);
        eb += c[4].parse::<f64>()?;
        let mut er = Vec::new();
        let mut bi = Vec::new();
        for k in 0..nf {
            er.push(c[5 + 2 * k].parse::<f64>()?);
            bi.push(c[6 + 2 * k].parse::<f64>()?);
        }
        errs.push(er);
        bits.push(bi);
    }
    let cible = eb;
    let erreur_a = |lambda: f64| -> f64 {
        let mut e = 0.0;
        for (er, bi) in errs.iter().zip(bits.iter()) {
            let mut k = 0;
            for c in 1..er.len() {
                if er[c] + lambda * bi[c] < er[k] + lambda * bi[k] {
                    k = c;
                }
            }
            e += er[k];
        }
        e
    };
    // erreur croissante en λ : bissection en log
    let (mut lo, mut hi) = ((en / 1e12).ln(), (en).ln());
    for _ in 0..200 {
        let mid = 0.5 * (lo + hi);
        if erreur_a(mid.exp()) > cible {
            hi = mid;
        } else {
            lo = mid;
        }
    }
    let lambda_a = lo.exp();
    let bits_a = |lambda: f64, rel: bool| -> f64 {
        let mut b = 0.0;
        for ((er, bi), en) in errs.iter().zip(bits.iter()).zip(energies.iter()) {
            let sc = |c: usize| if rel { er[c] / en } else { er[c] } + lambda * bi[c];
            let mut k = 0;
            for c in 1..er.len() {
                if sc(c) < sc(k) {
                    k = c;
                }
            }
            b += bi[k];
        }
        b
    };
    let cible_b = bits_a(lambda_a, false);
    // λ relatif : bits décroissants en λ
    let (mut lo, mut hi) = ((1e-12f64).ln(), (1e3f64).ln());
    for _ in 0..200 {
        let mid = 0.5 * (lo + hi);
        if bits_a(mid.exp(), true) > cible_b {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    Ok((lambda_a, hi.exp()))
}

pub fn sortie(args: &[String]) -> Result<()> {
    let opt = |nom: &str, d: &str| -> String {
        args.iter().position(|a| a == nom).and_then(|i| args.get(i + 1).cloned()).unwrap_or(d.to_string())
    };
    let norme = if opt("--norme", "brut") == "tourne" { Norme::Tourne } else { Norme::Brut };
    let couches: Vec<usize> = opt("--couches", "0,8,16,23").split(',').map(|s| s.parse().unwrap()).collect();
    let experts: Vec<usize> = opt("--experts", "0,16").split(',').map(|s| s.parse().unwrap()).collect();
    let calib = std::path::PathBuf::from(opt("--calib", "~/dev/essais/troncons/genome/eclaireur/calib"));
    let eval = std::path::PathBuf::from(opt("--eval", "~/dev/essais/troncons/genome/eclaireur/eval"));
    let csv = opt("--csv", "");
    let pondere = args.iter().any(|a| a == "--pondere");
    let max_pos: usize = opt("--positions", "512").parse()?;
    // si non vide : écrit Lll-Eee.f32w (gate, up, down en F32) de la recette et de la base, pour la KL
    let ecrire = opt("--ecrire", "");
    let formes = [(2u32, 1u32), (7, 3), (5, 2), (8, 3), (3, 1)];
    let m = Modele::ouvrir(FICHIER_20B)?;
    let (d, f) = (2880usize, 2880usize);
    let mut s = String::new();
    write!(s, "{{\"mode\": \"{}\", \"norme\": \"{:?}\", \"pondere\": {pondere}, \"experts\": {:?}, \"positions_max\": {max_pos}, \"csv\": \"{}\", \"couches\": [", opt("--mode", "energie"), norme, experts, csv.replace('\\', "/"))?;
    for (ic, &l) in couches.iter().enumerate() {
        let mom = if pondere { moments(&calib, l, d)? } else { Vec::new() };
        // pondération des colonnes : gate et up lisent h ; down lit l'activation (non capturée) : 1
        let mut points = Vec::new();
        for role in ROLES {
            let t = m.tenseur(l, role)?;
            let om_col: Vec<f32> = if pondere && role != "ffn_down_exps" {
                let moy = mom.iter().sum::<f64>() / d as f64;
                mom.iter().map(|&v| (v / moy) as f32).collect()
            } else {
                Vec::new()
            };
            let codes = apprendre_codes(&m, l, role, norme, 12, 8, &formes, &[0, 8, 16, 24], 4, 48, 2, &om_col)?;
            let (la, lr) = lambdas_du_csv(&csv, &t.nom)?;
            let lambdas = vec![(la, false), (lr, true)];
            let graine = (l * 3 + ROLES.iter().position(|&r| r == role).unwrap()) as u32 + 1;
            points.push(Point { norme, codes, lambdas, graine, om_col });
        }
        write!(s, "{}{{\"couche\": {l}, \"experts\": [", if ic > 0 { ", " } else { "" })?;
        for (ie, &e) in experts.iter().enumerate() {
            let (x32, mpos) = entrees(&eval, l, e, d, max_pos)?;
            let x: Vec<f64> = x32.iter().map(|&v| v as f64).collect();
            let mut exacts: Vec<Vec<f32>> = Vec::new();
            let mut bases: Vec<Vec<f32>> = Vec::new();
            // recettes[point][rôle]
            let mut recettes: Vec<Vec<Vec<f32>>> = vec![Vec::new(), Vec::new()];
            let mut bits_r = [0.0f64; 2];
            let mut err_r = [0.0f64; 2];
            let mut bs: Vec<Vec<f64>> = Vec::new();
            let (mut err_b, mut en) = (0.0, 0.0);
            for (ir, role) in ROLES.iter().enumerate() {
                let t = m.tenseur(l, role)?;
                let ex = m.expert(&t, e)?;
                let n = ex.lignes * ex.colonnes;
                let mut w = vec![0.0f32; n];
                let mut b = vec![0.0f32; n];
                let nb = ex.blocs_ligne();
                for r in 0..ex.lignes {
                    ex.ligne(r, &mut w[r * ex.colonnes..(r + 1) * ex.colonnes]);
                    for c in 0..ex.colonnes {
                        b[r * ex.colonnes + c] = base_valeur(ex.codes[r * ex.colonnes + c], ex.e[r * nb + c / 32], &CENTRES);
                    }
                }
                let pts = coder_expert(&ex, &points[ir]);
                for (i, (rec, bits, err)) in pts.into_iter().enumerate() {
                    bits_r[i] += bits;
                    err_r[i] += err;
                    recettes[i].push(rec);
                }
                en += w.iter().map(|&v| (v as f64).powi(2)).sum::<f64>();
                err_b += w.iter().zip(b.iter()).map(|(a, c)| ((a - c) as f64).powi(2)).sum::<f64>();
                exacts.push(w);
                bases.push(b);
                bs.push(biais(&m, l, role, e)?);
            }
            if !ecrire.is_empty() {
                for (quoi, ms) in [("recette", &recettes[0]), ("recette-relatif", &recettes[1]), ("base", &bases)] {
                    let dossier = Path::new(&ecrire).join(quoi);
                    std::fs::create_dir_all(&dossier)?;
                    let mut o = Vec::with_capacity(3 * d * f * 4);
                    for mm in ms.iter() {
                        for v in mm.iter() {
                            o.extend_from_slice(&v.to_le_bytes());
                        }
                    }
                    std::fs::write(dossier.join(format!("L{l:02}-E{e:02}.f32w")), o)?;
                }
            }
            let bb: [Vec<f64>; 3] = [bs[0].clone(), bs[1].clone(), bs[2].clone()];
            let trio = |v: &Vec<Vec<f32>>| -> [Vec<f32>; 3] { [v[0].clone(), v[1].clone(), v[2].clone()] };
            let ye = sortie_expert(&trio(&exacts), &bb, &x, mpos, d, f);
            let yb = sortie_expert(&trio(&bases), &bb, &x, mpos, d, f);
            let ny: f64 = ye.iter().map(|v| v * v).sum();
            let eb: f64 = ye.iter().zip(yb.iter()).map(|(a, b)| (a - b).powi(2)).sum();
            write!(s, "{}{{\"expert\": {e}, \"positions\": {mpos}, \"erreur_poids_base\": {:.6}, \"erreur_sortie_base\": {:.6}, \"points\": [", if ie > 0 { ", " } else { "" }, err_b / en, eb / ny)?;
            for i in 0..2 {
                let yr = sortie_expert(&trio(&recettes[i]), &bb, &x, mpos, d, f);
                let er: f64 = ye.iter().zip(yr.iter()).map(|(a, b)| (a - b).powi(2)).sum();
                // erreur de sortie par position, pour le test du signe
                let mut gagne = 0usize;
                for p in 0..mpos {
                    let (mut a, mut c) = (0.0, 0.0);
                    for k in 0..d {
                        a += (ye[p * d + k] - yr[p * d + k]).powi(2);
                        c += (ye[p * d + k] - yb[p * d + k]).powi(2);
                    }
                    if a < c {
                        gagne += 1;
                    }
                }
                let nom = if i == 0 { "energie" } else { "relatif" };
                write!(s, "{}{{\"repartition\": \"{nom}\", \"bits\": {:.5}, \"erreur_poids\": {:.6}, \"erreur_sortie\": {:.6}, \"positions_ou_la_recette_gagne\": {gagne}}}", if i > 0 { ", " } else { "" }, bits_r[i] / (3 * d * f) as f64, err_r[i] / en, er / ny)?;
                eprintln!("couche {l} expert {e} [{nom}] ({mpos} positions) : {:.4} b ; poids recette {:.4} % base {:.4} % ; sortie recette {:.4} % base {:.4} % ; {gagne}/{mpos}", bits_r[i] / (3 * d * f) as f64, 100.0 * err_r[i] / en, 100.0 * err_b / en, 100.0 * er / ny, 100.0 * eb / ny);
            }
            s.push_str("]}");
        }
        s.push_str("]}");
    }
    s.push_str("]}\n");
    print!("{s}");
    Ok(())
}
