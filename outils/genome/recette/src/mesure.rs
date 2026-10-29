//! Les mesures. Chaque sous-commande écrit un journal JSON sur la sortie standard.

use anyhow::{Context, Result, bail};
use rayon::prelude::*;
use std::fmt::Write as _;
use std::io::Write as _;

use crate::base::{Comptes, base_valeur};
use crate::codons::{self, Code, Forme, Melangeur, Travail};
use crate::donnees::{COUCHES_F1, ExpertMx, FICHIER_20B, Modele, ROLES};
use crate::graine::{Banque, Generateur, Recette};
use crate::hadamard;
use trc_reference::poids::K_MXFP4;

pub const ESSAIS: &str = "~/dev/essais/troncons/genome/genome";
const CSV_F1: &str = "~/dev/active/troncons/decisions/journaux/arbitre/csv/f1-par-tenseur.csv";
/// Médianes de ligne de B (un octet par ligne de 90 blocs) et tables, bits par poids (F1).
const MEDIANES: f64 = 8.0 / 2880.0;
const TABLES_B: f64 = 0.000070;
/// Alignement de chaque matrice d'expert sur 4 096 octets, au pire (32 768 bits / 8 294 400 poids).
const ALIGNEMENT: f64 = 32768.0 / 8294400.0;
/// Erreur publiée de la base sur les 12 tenseurs (07 § 4.2, retrouvée par F1 S4).
const ERREUR_PUBLIEE: f64 = 0.042919745124980;
/// Centres communs de la base (unités E2M1 doublées), refaits par `frontiere` (journal
/// mesures/genome/genome/frontiere.json) ; `codons` vérifie qu'ils retrouvent l'erreur publiée.
pub const CENTRES: [f64; 4] = [0.474331462365, 2.848595670702, 6.837153999339, 12.0];

fn drapeau(args: &[String], nom: &str) -> bool {
    args.iter().any(|a| a == nom)
}
fn option<T: std::str::FromStr>(args: &[String], nom: &str, defaut: T) -> T {
    for i in 0..args.len() {
        if args[i] == nom && i + 1 < args.len() {
            if let Ok(v) = args[i + 1].parse() {
                return v;
            }
        }
    }
    defaut
}

/// La frontière F1 de chaque tenseur : (nom, bits de la base lus sur le disque, erreur publiée,
/// bits sans perte A_ctx).
pub fn frontiere_f1() -> Result<Vec<(String, f64, f64, f64)>> {
    let txt = std::fs::read_to_string(CSV_F1).context("CSV de F1")?;
    let mut v = Vec::new();
    let mut lignes = txt.lines();
    let tete: Vec<&str> = lignes.next().unwrap().split(',').collect();
    let col = |n: &str| tete.iter().position(|&c| c == n).unwrap();
    let (ib, id, ie, ia) = (col("base"), col("delta"), col("erreur_base_centres_communs"), col("codes_a_ctx"));
    for l in lignes {
        let c: Vec<&str> = l.split(',').collect();
        let base: f64 = c[ib].parse()?;
        let delta: f64 = c[id].parse()?;
        let a: f64 = c[ia].parse()?;
        v.push((c[0].to_string(), base + delta + MEDIANES + TABLES_B, c[ie].parse()?, a + delta + MEDIANES + 0.000062));
    }
    Ok(v)
}

fn compter_expert(ex: &ExpertMx) -> Comptes {
    let mut c = Comptes::new();
    let nb = ex.blocs_ligne();
    for r in 0..ex.lignes {
        for b in 0..nb {
            let e = ex.e[r * nb + b] as usize;
            for j in 0..32 {
                c.0[e][ex.codes[r * ex.colonnes + b * 32 + j] as usize] += 1;
            }
        }
    }
    c
}

// ------------------------------------------------------------------------------------------------
// frontiere

pub fn frontiere(args: &[String]) -> Result<()> {
    let casser = drapeau(args, "--casser");
    let m = Modele::ouvrir(FICHIER_20B)?;
    let mut total = Comptes::new();
    let mut par_t = Vec::new();
    for &l in COUCHES_F1.iter() {
        for role in ROLES {
            let t = m.tenseur(l, role)?;
            let ne = m.nb_experts(&t);
            let cs: Vec<Comptes> = (0..ne).into_par_iter().map(|e| compter_expert(&m.expert(&t, e).unwrap())).collect();
            let mut c = Comptes::new();
            for x in &cs {
                c.ajouter(x);
            }
            total.ajouter(&c);
            par_t.push((t.nom.clone(), c));
            eprintln!("{} compté", t.nom);
        }
    }
    let mut centres = total.centres();
    if casser {
        // cassure : chaque classe lit le centre de la suivante
        centres = [centres[1], centres[2], centres[3], centres[0]];
    }
    let (err, en) = total.erreur(&centres);
    let rel = err / en;
    let f1 = frontiere_f1()?;
    let mut s = String::new();
    write!(s, "{{\n  \"centres_doubles\": [{:.12}, {:.12}, {:.12}, {:.12}],\n", centres[0], centres[1], centres[2], centres[3])?;
    write!(s, "  \"centres_e2m1\": [{:.6}, {:.6}, {:.6}, {:.6}],\n", centres[0] / 2.0, centres[1] / 2.0, centres[2] / 2.0, centres[3] / 2.0)?;
    write!(s, "  \"erreur_relative\": {:.15},\n  \"erreur_publiee\": {:.15},\n", rel, ERREUR_PUBLIEE)?;
    let ecart = (rel - ERREUR_PUBLIEE).abs() / ERREUR_PUBLIEE;
    write!(s, "  \"ecart_relatif\": {:.3e},\n  \"temoin_S0\": \"{}\",\n  \"casser\": {},\n  \"par_tenseur\": [\n", ecart, if ecart < 1e-6 { "tient" } else { "tombe" }, casser)?;
    for (i, (nom, c)) in par_t.iter().enumerate() {
        let (e, n) = c.erreur(&centres);
        let pub_ = f1.iter().find(|x| &x.0 == nom).map(|x| x.2).unwrap_or(f64::NAN);
        write!(s, "    {{\"tenseur\": \"{}\", \"erreur\": {:.9}, \"erreur_f1\": {:.6}}}{}\n", nom, e / n, pub_, if i + 1 < par_t.len() { "," } else { "" })?;
    }
    s.push_str("  ]\n}\n");
    print!("{s}");
    Ok(())
}

// ------------------------------------------------------------------------------------------------
// gauss : témoin T1

/// Échantillon gaussien déterministe : quantile de la loi normale d'un tirage uniforme haché.
fn gaussien(i: u64, graine: u32) -> f32 {
    let h1 = codons::hache((i & 0xFFFF_FFFF) as u32, graine) as u64;
    let h2 = codons::hache((i >> 32) as u32 ^ 0x1234_5678, graine.wrapping_add(1)) as u64;
    let u = (((h1 << 21) ^ h2) & ((1u64 << 52) - 1)) as f64;
    codons::quantile_normal((u + 0.5) / (1u64 << 52) as f64) as f32
}

pub fn gauss(args: &[String]) -> Result<()> {
    let l: u32 = args.first().context("L")?.parse()?;
    let kb: u32 = args.get(1).context("KB")?.parse()?;
    let v: u32 = args.get(2).context("V")?.parse()?;
    let q: u32 = args.get(3).context("Q")?.parse()?;
    let casser = drapeau(args, "--casser");
    let court = drapeau(args, "--court");
    let lloyd: usize = option(args, "--lloyd", 0);
    let rangees: usize = option(args, "--rangees", 128);
    let n = 2880usize - 2880 % (v as usize);
    let forme = Forme { l, kb, v, q, melangeur: if court { Melangeur::Court } else { Melangeur::Fort } };
    let mut table = codons::table_gaussienne(q);
    if casser {
        table.iter_mut().for_each(|x| *x = 0.0);
    }
    let xs: Vec<Vec<f32>> = (0..rangees).map(|r| (0..n).map(|i| gaussien((r * n + i) as u64, 99)).collect()).collect();
    let om = vec![1.0f32; n];
    let mut code = Code::nouveau(forme, table);
    let mut historique = Vec::new();
    for it in 0..=lloyd {
        let res: Vec<(f64, Vec<u32>)> = xs
            .par_iter()
            .map_init(Travail::new, |w, x| {
                let b = codons::viterbi(x, &om, &code, w);
                (b.erreur, b.etats)
            })
            .collect();
        let err: f64 = res.iter().map(|r| r.0).sum();
        let mse = err / (rangees * n) as f64;
        historique.push(mse);
        if it < lloyd {
            let nt = 1usize << q;
            let (mut num, mut den) = (vec![0.0; nt], vec![0.0; nt]);
            for (x, r) in xs.iter().zip(res.iter()) {
                codons::accumuler_lloyd(x, &om, &r.1, &code, &mut num, &mut den);
            }
            for i in 0..nt {
                if den[i] > 0.0 {
                    code.table[i] = (num[i] / den[i]) as f32;
                }
            }
            code.deplier();
        }
    }
    let r = forme.debit();
    let borne = (2.0f64).powf(-2.0 * r);
    let mse = *historique.last().unwrap();
    println!(
        "{{\"l\": {l}, \"kb\": {kb}, \"v\": {v}, \"q\": {q}, \"melangeur\": \"{}\", \"debit\": {r:.4}, \"rangees\": {rangees}, \"poids\": {}, \"lloyd\": {lloyd}, \"mse_par_iteration\": {:?}, \"mse\": {mse:.6}, \"borne_shannon\": {borne:.6}, \"ecart_db\": {:.3}, \"casser\": {casser}}}",
        if court { "court" } else { "fort" },
        rangees * n,
        historique.iter().map(|x| (x * 1e6).round() / 1e6).collect::<Vec<_>>(),
        10.0 * (mse / borne).log10()
    );
    Ok(())
}

// ------------------------------------------------------------------------------------------------
// codons : les experts réels

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Norme {
    /// x = K[code] (valeur E2M1 doublée), ω = 4^(e − 128) : l'échelle E8M0 de chaque bloc est gardée
    Brut,
    /// rotation de Hadamard par morceaux de 64, puis x = y / σ_rangée
    Tourne,
}

/// Une rangée préparée : la source x, ses poids ω (relatifs), le facteur qui rend ω absolu,
/// l'énergie absolue Σ w², et l'erreur absolue de la base sur la rangée.
pub struct Rangee {
    pub x: Vec<f32>,
    pub om: Vec<f32>,
    pub facteur: f64,
    pub energie: f64,
    pub err_base: f64,
    pub sigma: f32,
}

fn sigma_f16(s: f32) -> f32 {
    // garde 10 bits de mantisse (représentable en f16 pour les échelles rencontrées)
    f32::from_bits(s.to_bits() & !0x1FFF)
}

pub fn preparer(ex: &ExpertMx, r: usize, norme: Norme, graine: u32, centres: &[f64; 4]) -> Rangee {
    let n = ex.colonnes;
    let nb = ex.blocs_ligne();
    let mut w = vec![0.0f32; n];
    ex.ligne(r, &mut w);
    let energie: f64 = w.iter().map(|&a| (a as f64) * (a as f64)).sum();
    let mut err_base = 0.0f64;
    for c in 0..n {
        let b = base_valeur(ex.codes[r * n + c], ex.e[r * nb + c / 32], centres);
        err_base += ((w[c] - b) as f64).powi(2);
    }
    match norme {
        Norme::Brut => {
            let emax = (0..nb).map(|b| ex.e[r * nb + b]).max().unwrap();
            let facteur = (4.0f64).powi(emax as i32 - 128);
            let mut x = vec![0.0f32; n];
            let mut om = vec![0.0f32; n];
            for c in 0..n {
                x[c] = K_MXFP4[ex.codes[r * n + c] as usize] as f32;
                om[c] = (4.0f64).powi(ex.e[r * nb + c / 32] as i32 - emax as i32) as f32;
            }
            Rangee { x, om, facteur, energie, err_base, sigma: 0.0 }
        }
        Norme::Tourne => {
            hadamard::tourner(&mut w, 64, graine);
            let ms: f64 = w.iter().map(|&a| (a as f64) * (a as f64)).sum::<f64>() / n as f64;
            let sigma = sigma_f16(ms.sqrt() as f32);
            let x: Vec<f32> = w.iter().map(|&a| a / sigma).collect();
            Rangee { x, om: vec![1.0; n], facteur: (sigma as f64) * (sigma as f64), energie, err_base, sigma }
        }
    }
}

/// La reconstruction absolue d'une rangée depuis son brin (dans le domaine d'origine).
pub fn reconstruire(ex: &ExpertMx, r: usize, rg: &Rangee, etats: &[u32], code: &Code, norme: Norme, graine: u32) -> Vec<f32> {
    let n = ex.colonnes;
    let nb = ex.blocs_ligne();
    let v = code.forme.v as usize;
    let mut y = vec![0.0f32; n];
    for (p, &s) in etats.iter().enumerate() {
        for j in 0..v {
            y[p * v + j] = code.valeurs[s as usize * v + j];
        }
    }
    match norme {
        Norme::Brut => {
            for c in 0..n {
                y[c] *= ExpertMx::echelle(ex.e[r * nb + c / 32]);
            }
        }
        Norme::Tourne => {
            for a in y.iter_mut() {
                *a *= rg.sigma;
            }
            hadamard::detourner(&mut y, 64, graine);
        }
    }
    y
}

/// Les formes essayées (débit kb / v) pour une fenêtre l.
pub fn formes(l: u32, q: u32, melangeur: Melangeur) -> Vec<Forme> {
    [(1u32, 1u32), (2, 1), (7, 3), (5, 2), (8, 3), (3, 1), (4, 1)]
        .iter()
        .filter(|&&(kb, _)| kb < l)
        .map(|&(kb, v)| Forme { l, kb, v, q, melangeur })
        .collect()
}

/// Courbe débit-distorsion par allocation lagrangienne rangée par rangée : pour chaque λ, chaque
/// rangée prend la forme qui minimise err + λ · bits. Rend (bits par poids, erreur relative).
pub fn courbe(err: &[Vec<f64>], bits: &[Vec<f64>], poids: f64, energie: f64) -> Vec<(f64, f64)> {
    let mut pts = Vec::new();
    let echelle = energie / poids;
    for i in 0..400 {
        let lambda = echelle * (10.0f64).powf(-9.0 + 12.0 * i as f64 / 399.0);
        let (mut b, mut e) = (0.0, 0.0);
        for (er, bi) in err.iter().zip(bits.iter()) {
            let mut k = 0;
            for c in 1..er.len() {
                if er[c] + lambda * bi[c] < er[k] + lambda * bi[k] {
                    k = c;
                }
            }
            b += bi[k];
            e += er[k];
        }
        pts.push((b / poids, e / energie));
    }
    pts.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
    pts.dedup_by(|a, b| (a.0 - b.0).abs() < 1e-12);
    pts
}

/// Bits par poids nécessaires pour atteindre l'erreur relative `cible` (interpolation linéaire en
/// log(erreur) entre deux points voisins de la courbe ; NaN hors de la courbe).
pub fn bits_a_erreur(pts: &[(f64, f64)], cible: f64) -> f64 {
    for w in pts.windows(2) {
        let (b0, e0) = w[0];
        let (b1, e1) = w[1];
        if (e0 >= cible && e1 <= cible) && e0 > e1 {
            let t = (e0.ln() - cible.ln()) / (e0.ln() - e1.ln());
            return b0 + t * (b1 - b0);
        }
    }
    f64::NAN
}

pub fn codons(args: &[String]) -> Result<()> {
    let norme = match args.first().map(|s| s.as_str()) {
        Some("brut") => Norme::Brut,
        Some("tourne") => Norme::Tourne,
        _ => bail!("NORM = brut | tourne"),
    };
    let experts: Vec<usize> = args.get(1).context("EXPERTS")?.split(',').map(|s| s.parse().unwrap()).collect();
    let l: u32 = option(args, "--l", 12);
    let q: u32 = option(args, "--q", 8);
    let lloyd: usize = option(args, "--lloyd", 2);
    let rangees_max: usize = option(args, "--rangees", usize::MAX);
    let pas_rangees: usize = option(args, "--pas", 1);
    let formes_choisies: String = option(args, "--formes", String::from("2/1,7/3,5/2,8/3,3/1"));
    let entrainement: usize = option(args, "--entrainement", 48);
    let court = drapeau(args, "--court");
    let casser = drapeau(args, "--casser");
    let couches: Vec<usize> = option::<String>(args, "--couches", "0,8,16,23".into()).split(',').map(|s| s.parse().unwrap()).collect();
    let melangeur = if court { Melangeur::Court } else { Melangeur::Fort };
    let fs: Vec<Forme> = formes_choisies
        .split(',')
        .map(|t| {
            let (a, b) = t.split_once('/').unwrap();
            Forme { l, kb: a.parse().unwrap(), v: b.parse().unwrap(), q, melangeur }
        })
        .collect();
    let debut = std::time::Instant::now();
    let centres = CENTRES;
    if centres[3] == 0.0 {
        bail!("CENTRES non posés : lancer frontiere d'abord");
    }
    let f1 = frontiere_f1()?;
    let m = Modele::ouvrir(FICHIER_20B)?;
    std::fs::create_dir_all(ESSAIS)?;
    let mut sortie = String::new();
    write!(sortie, "{{\n  \"norme\": \"{:?}\", \"l\": {l}, \"q\": {q}, \"lloyd\": {lloyd}, \"melangeur\": \"{:?}\", \"experts\": {:?}, \"casser\": {casser},\n", norme, melangeur, experts)?;
    write!(sortie, "  \"formes\": [{}],\n  \"tenseurs\": [\n", fs.iter().map(|f| format!("[{}, {}]", f.kb, f.v)).collect::<Vec<_>>().join(", "))?;
    // agrégats communs
    let mut tous_err: Vec<Vec<f64>> = Vec::new();
    let mut tous_bits: Vec<Vec<f64>> = Vec::new();
    let (mut tous_poids, mut toute_energie, mut tout_err_base) = (0.0f64, 0.0f64, 0.0f64);
    let mut frontiere_ponderee = 0.0f64;
    let mut sans_perte_ponderee = 0.0f64;
    let mut premiers = true;
    let fichier_rangees: String = option(args, "--csv", String::new());
    let mut csv = String::from("tenseur,expert,rangee,energie,err_base");
    for f in &fs {
        write!(csv, ",err_{}_{},bits_{}_{}", f.kb, f.v, f.kb, f.v)?;
    }
    csv.push('\n');
    for &cl in &couches {
        for role in ROLES {
            let t = m.tenseur(cl, role)?;
            let graine = (cl * 3 + ROLES.iter().position(|&r| r == role).unwrap()) as u32 + 1;
            let exs: Vec<ExpertMx> = experts.iter().map(|&e| m.expert(&t, e)).collect::<Result<_>>()?;
            let nl = exs[0].lignes.min(rangees_max);
            // rangées préparées
            let rgs: Vec<(usize, usize, Rangee)> = (0..exs.len())
                .flat_map(|i| (0..nl).step_by(pas_rangees).map(move |r| (i, r)))
                .collect::<Vec<_>>()
                .into_par_iter()
                .map(|(i, r)| (i, r, preparer(&exs[i], r, norme, graine, &centres)))
                .collect();
            // tables apprises (Lloyd) sur les premières rangées de chaque expert de l'échantillon
            let apprendre: Vec<&Rangee> = rgs.iter().filter(|(_, r, _)| *r < entrainement * pas_rangees).map(|x| &x.2).collect();
            let mut codes = Vec::new();
            for f in &fs {
                let xs: Vec<f32> = apprendre.iter().flat_map(|r| r.x.iter().copied()).collect();
                let os: Vec<f32> = apprendre.iter().flat_map(|r| r.om.iter().map(move |&o| o * r.facteur as f32)).collect();
                let mut table = codons::table_empirique(&xs, &os, f.q);
                if casser {
                    table.iter_mut().for_each(|x| *x = 0.0);
                }
                let mut code = Code::nouveau(*f, table);
                for _ in 0..lloyd {
                    if casser {
                        break;
                    }
                    let res: Vec<Vec<u32>> = apprendre.par_iter().map_init(Travail::new, |w, r| codons::viterbi(&r.x, &r.om, &code, w).etats).collect();
                    let nt = 1usize << f.q;
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
            // passe finale : toutes les rangées, toutes les formes ; plus les comptes conjoints
            // (code exact, case de la reconstruction) pour le complément exact
            let nfs = fs.len();
            let res: Vec<(Vec<f64>, Vec<f64>, Vec<[u32; 65 * 16]>)> = rgs
                .par_iter()
                .map_init(Travail::new, |w, (i, r, rg)| {
                    let mut errs = Vec::with_capacity(nfs);
                    let mut bits = Vec::with_capacity(nfs);
                    let mut joints = Vec::with_capacity(nfs);
                    let ex = &exs[*i];
                    for code in &codes {
                        let b = codons::viterbi(&rg.x, &rg.om, code, w);
                        errs.push(b.erreur * rg.facteur);
                        let n = rg.x.len();
                        let mut bi = code.forme.bits_brin(n) as f64;
                        bi += 3.0; // indice de forme de la rangée
                        if norme == Norme::Tourne {
                            bi += 16.0; // σ de la rangée
                        }
                        bits.push(bi);
                        let y = reconstruire(ex, *r, rg, &b.etats, code, norme, graine);
                        let nb = ex.blocs_ligne();
                        let mut joint = [0u32; 65 * 16];
                        for c in 0..n {
                            let s = ExpertMx::echelle(ex.e[*r * nb + c / 32]);
                            let k = ((y[c] / s + 12.0) / 0.375).round().clamp(0.0, 64.0) as usize;
                            joint[k * 16 + ex.codes[*r * n + c] as usize] += 1;
                        }
                        joints.push(joint);
                    }
                    (errs, bits, joints)
                })
                .collect();
            for ((i, r, rg), x) in rgs.iter().zip(res.iter()) {
                write!(csv, "{},{},{},{:.6e},{:.6e}", t.nom, experts[*i], r, rg.energie, rg.err_base)?;
                for c in 0..nfs {
                    write!(csv, ",{:.6e},{}", x.0[c], x.1[c])?;
                }
                csv.push('\n');
            }
            let poids = (rgs.len() * exs[0].colonnes) as f64;
            let energie: f64 = rgs.iter().map(|x| x.2.energie).sum();
            let err_base: f64 = rgs.iter().map(|x| x.2.err_base).sum();
            let mut errs: Vec<Vec<f64>> = res.iter().map(|x| x.0.clone()).collect();
            let mut bits: Vec<Vec<f64>> = res.iter().map(|x| x.1.clone()).collect();
            // côté « brut » : les échelles E8M0 (δ et médianes de F1) sont lues aussi
            let fr = f1.iter().find(|x| x.0 == t.nom).context("tenseur absent de F1")?;
            // tables : 2^q valeurs f16 par forme et par tenseur entier (32 experts)
            let poids_tenseur = (t.ne[0] * t.ne[1] * t.ne[2]) as f64;
            let bits_tables = (16u64 << q) as f64 / poids_tenseur;
            let pts = courbe(&errs, &bits, poids, energie);
            let cible = err_base / energie;
            let mut bits_recette = bits_a_erreur(&pts, cible) + bits_tables + ALIGNEMENT;
            // les échelles E8M0 : le coût mesuré par F1 (δ + médianes) pour « brut »
            let echelles = if norme == Norme::Brut { echelles_f1(&t.nom)? } else { 0.0 };
            bits_recette += echelles;
            // formes fixes (toutes les rangées à la même forme)
            let mut fixes = String::new();
            for c in 0..nfs {
                let e: f64 = errs.iter().map(|x| x[c]).sum::<f64>() / energie;
                let b: f64 = bits.iter().map(|x| x[c]).sum::<f64>() / poids + bits_tables + echelles + ALIGNEMENT;
                // complément exact : H(code | case de la reconstruction)
                let mut joint = vec![0u64; 65 * 16];
                for x in &res {
                    for (a, &bb) in joint.iter_mut().zip(x.2[c].iter()) {
                        *a += bb as u64;
                    }
                }
                let h = entropie_conditionnelle(&joint, 65, 16);
                write!(fixes, "{}{{\"kb\": {}, \"v\": {}, \"bits\": {:.5}, \"erreur\": {:.6}, \"H_code_sachant_recette\": {:.5}, \"sans_perte_total\": {:.5}}}", if c > 0 { ", " } else { "" }, fs[c].kb, fs[c].v, b, e, h, b + h + if norme == Norme::Tourne { echelles_f1(&t.nom)? } else { 0.0 })?;
            }
            write!(
                sortie,
                "{}    {{\"tenseur\": \"{}\", \"rangees\": {}, \"erreur_base_echantillon\": {:.6}, \"erreur_base_f1\": {:.6}, \"bits_frontiere\": {:.5}, \"bits_recette_a_erreur_egale\": {:.5}, \"gain_bits\": {:.5}, \"echelles\": {:.5}, \"tables\": {:.6}, \"fixes\": [{}]}}",
                if premiers { "" } else { ",\n" },
                t.nom,
                rgs.len(),
                cible,
                fr.2,
                fr.1,
                bits_recette,
                fr.1 - bits_recette,
                echelles,
                bits_tables,
                fixes
            )?;
            premiers = false;
            eprint!("[{:.0} s] ", debut.elapsed().as_secs_f64());
            eprintln!("{} : base {:.4} % à {:.4} b ; recette {:.4} b ; gain {:.4}", t.nom, 100.0 * cible, fr.1, bits_recette, fr.1 - bits_recette);
            // agrégat : on ajoute le coût fixe par poids comme bits supplémentaires par rangée
            let fixe_rangee = (bits_tables + echelles + ALIGNEMENT) * exs[0].colonnes as f64;
            for b in bits.iter_mut() {
                for x in b.iter_mut() {
                    *x += fixe_rangee;
                }
            }
            tous_err.append(&mut errs);
            tous_bits.append(&mut bits);
            tous_poids += poids;
            toute_energie += energie;
            tout_err_base += err_base;
            frontiere_ponderee += fr.1 * poids;
            sans_perte_ponderee += fr.3 * poids;
            // les états ne sont pas gardés ici (reconstruction par la sous-commande `decoder`)
            let _ = std::io::stdout().flush();
        }
    }
    let pts = courbe(&tous_err, &tous_bits, tous_poids, toute_energie);
    let cible = tout_err_base / toute_energie;
    let b = bits_a_erreur(&pts, cible);
    write!(sortie, "\n  ],\n  \"global\": {{\"erreur_base\": {:.6}, \"bits_frontiere\": {:.5}, \"bits_sans_perte\": {:.5}, \"bits_recette_a_erreur_egale\": {:.5}, \"gain_bits\": {:.5}}},\n", cible, frontiere_ponderee / tous_poids, sans_perte_ponderee / tous_poids, b, frontiere_ponderee / tous_poids - b)?;
    write!(sortie, "  \"courbe_globale\": [{}]\n}}\n", pts.iter().step_by(4).map(|p| format!("[{:.5}, {:.6}]", p.0, p.1)).collect::<Vec<_>>().join(", "))?;
    print!("{sortie}");
    if !fichier_rangees.is_empty() {
        std::fs::write(&fichier_rangees, csv)?;
    }
    Ok(())
}

pub fn echelles_f1(nom: &str) -> Result<f64> {
    let txt = std::fs::read_to_string(CSV_F1)?;
    let mut lignes = txt.lines();
    let tete: Vec<&str> = lignes.next().unwrap().split(',').collect();
    let id = tete.iter().position(|&c| c == "delta").unwrap();
    for l in lignes {
        let c: Vec<&str> = l.split(',').collect();
        if c[0] == nom {
            return Ok(c[id].parse::<f64>()? + MEDIANES);
        }
    }
    bail!("{nom} absent de F1")
}

pub fn entropie_conditionnelle(joint: &[u64], na: usize, nb: usize) -> f64 {
    let total: f64 = joint.iter().map(|&x| x as f64).sum();
    let mut h = 0.0;
    for a in 0..na {
        let ligne = &joint[a * nb..(a + 1) * nb];
        let s: f64 = ligne.iter().map(|&x| x as f64).sum();
        if s == 0.0 {
            continue;
        }
        for &x in ligne {
            if x > 0 {
                let p = x as f64 / s;
                h -= (s / total) * p * p.log2();
            }
        }
    }
    h
}

// ------------------------------------------------------------------------------------------------
// graines : la recette littérale

pub fn graines(args: &[String]) -> Result<()> {
    let c: usize = args.first().context("C")?.parse()?;
    let p: usize = args.get(1).context("P")?.parse()?;
    let k: u32 = args.get(2).context("K")?.parse()?;
    let generateur = match args.get(3).map(|s| s.as_str()) {
        Some("lfsr") => Generateur::Lfsr,
        Some("hache") => Generateur::Hache,
        _ => bail!("GEN = lfsr | hache"),
    };
    let rangees: usize = args.get(4).context("RANGEES")?.parse()?;
    let expert: usize = option(args, "--expert", 0);
    let r = Recette { c, p, k, generateur };
    let banque = Banque::new(r);
    let m = Modele::ouvrir(FICHIER_20B)?;
    let centres = CENTRES;
    let mut s = String::new();
    write!(s, "{{\"c\": {c}, \"p\": {p}, \"k\": {k}, \"generateur\": \"{:?}\", \"debit\": {:.4}, \"rangees_par_tenseur\": {rangees}, \"expert\": {expert}, \"tenseurs\": [", generateur, r.debit())?;
    let (mut te, mut ten, mut teb) = (0.0, 0.0, 0.0);
    for (it, (&cl, role)) in COUCHES_F1.iter().flat_map(|c| ROLES.iter().map(move |r| (c, *r))).enumerate() {
        let t = m.tenseur(cl, role)?;
        let ex = m.expert(&t, expert)?;
        let n = ex.colonnes;
        let pas_r = ex.lignes / rangees;
        let res: Vec<(f64, f64, f64)> = (0..rangees)
            .into_par_iter()
            .map(|i| {
                let rr = i * pas_r;
                let mut w = vec![0.0f32; n];
                ex.ligne(rr, &mut w);
                let mut err = 0.0;
                let mut rec = vec![0.0f32; c];
                // blocs de C poids (le reste de la rangée, s'il y en a, en blocs plus courts n'est
                // pas codé : on ne compte que les blocs entiers)
                let nbl = n / c;
                let mut en = 0.0;
                let mut eb = 0.0;
                let nb = ex.blocs_ligne();
                err += banque.coder_rangee(&w[..nbl * c]);
                let _ = &mut rec;
                for b in 0..nbl {
                    let bloc = &w[b * c..(b + 1) * c];
                    for j in 0..c {
                        let col = b * c + j;
                        en += (bloc[j] as f64).powi(2);
                        let bv = base_valeur(ex.codes[rr * n + col], ex.e[rr * nb + col / 32], &centres);
                        eb += ((bloc[j] - bv) as f64).powi(2);
                    }
                }
                (err, en, eb)
            })
            .collect();
        let (e, en, eb): (f64, f64, f64) = res.iter().fold((0.0, 0.0, 0.0), |a, x| (a.0 + x.0, a.1 + x.1, a.2 + x.2));
        te += e;
        ten += en;
        teb += eb;
        write!(s, "{}{{\"tenseur\": \"{}\", \"erreur\": {:.6}, \"erreur_base\": {:.6}}}", if it > 0 { ", " } else { "" }, t.nom, e / en, eb / en)?;
        eprintln!("{} : graines {:.4} %, base {:.4} %", t.nom, 100.0 * e / en, 100.0 * eb / en);
    }
    write!(s, "], \"erreur\": {:.6}, \"erreur_base\": {:.6}}}\n", te / ten, teb / ten)?;
    print!("{s}");
    Ok(())
}

/// Débit de transcription sur le processeur : un expert (2 880 rangées) relu depuis ses brins par le
/// seul décodeur, contre la déquantification MXFP4 du même expert ; séries ABBA, 16 fils.
pub fn decoder(args: &[String]) -> Result<()> {
    let repetitions: usize = option(args, "--repetitions", 8);
    let court = drapeau(args, "--court");
    let (kb, v): (u32, u32) = (option(args, "--kb", 5), option(args, "--v", 2));
    let melangeur = if court { Melangeur::Court } else { Melangeur::Fort };
    let forme = Forme { l: 12, kb, v, q: 8, melangeur };
    let m = Modele::ouvrir(FICHIER_20B)?;
    let t = m.tenseur(16, "ffn_up_exps")?;
    let ex = m.expert(&t, 0)?;
    let n = ex.colonnes;
    // brins : chaque rangée codée une fois (table gaussienne sur la source « tourne »)
    let code = Code::nouveau(forme, codons::table_gaussienne(8));
    let brins: Vec<Vec<u64>> = (0..ex.lignes)
        .into_par_iter()
        .map_init(Travail::new, |w, r| {
            let rg = preparer(&ex, r, Norme::Tourne, 1, &CENTRES);
            let b = codons::viterbi(&rg.x, &rg.om, &code, w);
            codons::ecrire_brin(&b.etats, &forme)
        })
        .collect();
    // témoin : la relecture rend les valeurs de la table aux fenêtres du Viterbi (déjà prouvé par les
    // tests) ; ici on vérifie seulement qu'une somme de contrôle est identique d'une passe à l'autre
    let decoder_tout = || -> f64 {
        brins
            .par_iter()
            .map(|mots| {
                let mut y = vec![0.0f32; n];
                codons::lire_brin(mots, n, &forme, &code.table, &mut y);
                y.iter().map(|&a| a as f64).sum::<f64>()
            })
            .sum()
    };
    let dequantifier_tout = || -> f64 {
        (0..ex.lignes)
            .into_par_iter()
            .map(|r| {
                let mut y = vec![0.0f32; n];
                ex.ligne(r, &mut y);
                y.iter().map(|&a| a as f64).sum::<f64>()
            })
            .sum()
    };
    let mut a = Vec::new();
    let mut b = Vec::new();
    let mut controle = Vec::new();
    for i in 0..repetitions {
        let ordre = if i % 4 == 0 || i % 4 == 3 { [0, 1] } else { [1, 0] };
        for &o in &ordre {
            let t0 = std::time::Instant::now();
            let c = if o == 0 { decoder_tout() } else { dequantifier_tout() };
            let dt = t0.elapsed().as_secs_f64();
            if o == 0 {
                a.push(dt);
                controle.push(c);
            } else {
                b.push(dt);
            }
        }
    }
    let poids = (ex.lignes * n) as f64;
    let med = |v: &mut Vec<f64>| -> f64 {
        v.sort_by(|x, y| x.partial_cmp(y).unwrap());
        v[v.len() / 2]
    };
    let (ma, mb) = (med(&mut a.clone()), med(&mut b.clone()));
    let constant = controle.iter().all(|&c| c == controle[0]);
    println!(
        "{{\"forme\": [{kb}, {v}], \"melangeur\": \"{:?}\", \"poids\": {poids}, \"repetitions\": {repetitions}, \"secondes_decodage\": {:?}, \"secondes_mxfp4\": {:?}, \"poids_par_seconde_decodage\": {:.4e}, \"poids_par_seconde_mxfp4\": {:.4e}, \"octets_par_seconde_lus_decodage\": {:.4e}, \"controle_constant\": {constant}}}",
        melangeur, a, b, poids / ma, poids / mb, poids / ma * forme.debit() / 8.0
    );
    Ok(())
}

// ------------------------------------------------------------------------------------------------
// motifs : dictionnaires partagés, combinés étage par étage

pub fn motifs(args: &[String]) -> Result<()> {
    let d: usize = args.first().context("D")?.parse()?;
    let b: u32 = args.get(1).context("B")?.parse()?;
    let etages: usize = args.get(2).context("M")?.parse()?;
    let pas_rangees: usize = option(args, "--pas", 4);
    let entrainement: usize = option(args, "--entrainement", 48);
    let iters: usize = option(args, "--iters", 12);
    let experts = [0usize, 8, 16, 24];
    let k = 1usize << b;
    let m = Modele::ouvrir(FICHIER_20B)?;
    let f1 = frontiere_f1()?;
    let mut s = String::new();
    write!(s, "{{\"d\": {d}, \"b\": {b}, \"etages\": {etages}, \"pas_rangees\": {pas_rangees}, \"entrainement\": {entrainement}, \"iters\": {iters}, \"tenseurs\": [")?;
    let (mut tot_en, mut tot_eb) = (0.0f64, 0.0f64);
    let mut tot_err = vec![0.0f64; etages];
    let mut tot_bits = vec![0.0f64; etages];
    let mut tot_front = 0.0f64;
    let mut tot_poids = 0.0f64;
    for (it, (&cl, role)) in COUCHES_F1.iter().flat_map(|c| ROLES.iter().map(move |r| (c, *r))).enumerate() {
        let t = m.tenseur(cl, role)?;
        let exs: Vec<ExpertMx> = experts.iter().map(|&e| m.expert(&t, e)).collect::<Result<_>>()?;
        let rgs: Vec<(usize, Rangee)> = (0..exs.len())
            .flat_map(|i| (0..exs[0].lignes).step_by(pas_rangees).map(move |r| (i, r)))
            .collect::<Vec<_>>()
            .into_par_iter()
            .map(|(i, r)| (r, preparer(&exs[i], r, Norme::Brut, 0, &CENTRES)))
            .collect();
        // vecteurs (source, poids absolus) ; la source est en unités E2M1 doublées
        let mut x: Vec<f32> = Vec::new();
        let mut om: Vec<f32> = Vec::new();
        let mut appr: Vec<bool> = Vec::new();
        for (r, rg) in &rgs {
            x.extend_from_slice(&rg.x);
            om.extend(rg.om.iter().map(|&o| (o as f64 * rg.facteur) as f32));
            let a = *r < entrainement * pas_rangees;
            appr.extend(std::iter::repeat_n(a, rg.x.len() / d));
        }
        // ω absolus très petits (4^(e−128)) : on les ramène à une échelle commune pour les f32
        let omax = om.iter().cloned().fold(0.0f32, f32::max);
        let om: Vec<f32> = om.iter().map(|&o| o / omax).collect();
        let energie: f64 = rgs.iter().map(|x| x.1.energie).sum();
        let err_base: f64 = rgs.iter().map(|x| x.1.err_base).sum();
        let nvec = x.len() / d;
        let mut reste = x.clone();
        let mut ligne = String::new();
        for e in 0..etages {
            let idx: Vec<usize> = (0..nvec).filter(|&i| appr[i]).collect();
            let xa: Vec<f32> = idx.iter().flat_map(|&i| reste[i * d..(i + 1) * d].iter().copied()).collect();
            let oa: Vec<f32> = idx.iter().flat_map(|&i| om[i * d..(i + 1) * d].iter().copied()).collect();
            let dico = crate::motifs::kmoyennes(&xa, &oa, d, k, iters);
            let nouveaux: Vec<(Vec<f32>, f64)> = (0..nvec)
                .into_par_iter()
                .map(|i| {
                    let (a, _) = crate::motifs::plus_proche(&reste[i * d..(i + 1) * d], &om[i * d..(i + 1) * d], &dico, d);
                    let mut r = vec![0.0f32; d];
                    let mut err = 0.0f64;
                    for j in 0..d {
                        r[j] = reste[i * d + j] - dico[a * d + j];
                        err += om[i * d + j] as f64 * (r[j] as f64).powi(2);
                    }
                    (r, err)
                })
                .collect();
            let mut err = 0.0f64;
            for (i, (r, e2)) in nouveaux.into_iter().enumerate() {
                reste[i * d..(i + 1) * d].copy_from_slice(&r);
                err += e2;
            }
            let err_abs = err * omax as f64;
            let poids_tenseur = (t.ne[0] * t.ne[1] * t.ne[2]) as f64;
            let bits = ((e + 1) as f64 * b as f64) / d as f64 + ((e + 1) * k * d * 16) as f64 / poids_tenseur + echelles_f1(&t.nom)? + ALIGNEMENT;
            tot_err[e] += err_abs;
            tot_bits[e] += bits * x.len() as f64;
            write!(ligne, "{}{{\"etages\": {}, \"bits\": {:.5}, \"erreur\": {:.6}}}", if e > 0 { ", " } else { "" }, e + 1, bits, err_abs / energie)?;
            eprintln!("{} : {} étage(s), {:.4} b, erreur {:.4} % (base {:.4} %)", t.nom, e + 1, bits, 100.0 * err_abs / energie, 100.0 * err_base / energie);
        }
        let fr = f1.iter().find(|x| x.0 == t.nom).context("F1")?;
        tot_en += energie;
        tot_eb += err_base;
        tot_front += fr.1 * x.len() as f64;
        tot_poids += x.len() as f64;
        write!(s, "{}{{\"tenseur\": \"{}\", \"erreur_base\": {:.6}, \"bits_frontiere\": {:.5}, \"points\": [{}]}}", if it > 0 { ", " } else { "" }, t.nom, err_base / energie, fr.1, ligne)?;
    }
    let pts: Vec<(f64, f64)> = (0..etages).map(|e| (tot_bits[e] / tot_poids, tot_err[e] / tot_en)).collect();
    let cible = tot_eb / tot_en;
    write!(s, "], \"global\": {{\"erreur_base\": {:.6}, \"bits_frontiere\": {:.5}, \"points\": [{}], \"bits_a_erreur_egale\": {:.5}}}}}\n", cible, tot_front / tot_poids, pts.iter().map(|p| format!("[{:.5}, {:.6}]", p.0, p.1)).collect::<Vec<_>>().join(", "), bits_a_erreur(&pts, cible))?;
    print!("{s}");
    Ok(())
}

/// Écrit la base de B (reconstruction F32 de gate, up, down) des experts donnés, au format `.f32w`
/// de l'outil KL, pour la comparer à la recette dans la référence f64.
pub fn base_f32w(args: &[String]) -> Result<()> {
    let couches: Vec<usize> = option::<String>(args, "--couches", "0,8,16,23".into()).split(',').map(|s| s.parse().unwrap()).collect();
    let experts: Vec<usize> = option::<String>(args, "--experts", "0,16".into()).split(',').map(|s| s.parse().unwrap()).collect();
    let dossier: String = option(args, "--dossier", String::new());
    if dossier.is_empty() {
        bail!("--dossier manque");
    }
    std::fs::create_dir_all(&dossier)?;
    let m = Modele::ouvrir(FICHIER_20B)?;
    for &l in &couches {
        for &e in &experts {
            let mut o = Vec::new();
            for role in ROLES {
                let ex = m.expert(&m.tenseur(l, role)?, e)?;
                let nb = ex.blocs_ligne();
                for r in 0..ex.lignes {
                    for c in 0..ex.colonnes {
                        let v = crate::base::base_valeur(ex.codes[r * ex.colonnes + c], ex.e[r * nb + c / 32], &CENTRES);
                        o.extend_from_slice(&v.to_le_bytes());
                    }
                }
            }
            std::fs::write(std::path::Path::new(&dossier).join(format!("L{l:02}-E{e:02}.f32w")), o)?;
            eprintln!("base L{l:02}-E{e:02} écrite");
        }
    }
    Ok(())
}
