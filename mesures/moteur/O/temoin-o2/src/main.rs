//! Témoin O2 : la passe avant de `trc-modele` contre la chaîne du lot K, ligne pour ligne.
//!
//! Critères déclarés avant ce code (moteur/REPRISE-O.md, 2026-10-15, 22 h 10) :
//! - les 160 premiers jetons de la fenêtre 0 d'un `.kld` (ceux de la chaîne K3), référence f64
//!   (`Reference::evaluer` sur le GGUF d'origine) refaite ici ;
//! - chemin **T** : le moteur entier (`trc_ordo::Moteur`, fichier `.trc` codé, jeton par jeton) ;
//!   chemin **G** : `trc_modele::Modele` seul, les experts tirés du GGUF d'origine et posés en
//!   emplacement SoA par l'hôte (ni `trc-ordo`, ni décodeur), sur les premières positions ;
//! - par position : KL(référence ‖ chemin), premier choix des deux, écart relatif des logits, écrits
//!   comme la chaîne K3 les écrit (`{:e}` d'un f64 : la plus courte écriture exacte) ;
//! - seuil : **égalité exacte** de chaque ligne avec le CSV de la chaîne K3, et KL moyenne de T égale
//!   à celle de son journal ;
//! - cassures : T `--casser position` (le moteur reçoit p + 1) ; G `--casser experts` (couche 5 :
//!   emplacements 0 et 1 échangés). Chacune doit faire différer au moins une ligne.
//!
//! Usage : `temoin-o2 <gguf> <trc> <kld> <k3.csv> <k3.json> <journal.json> <lignes.csv>
//!          [--chemins T,G] [--positions 160] [--positions-g 16] [--casser position|experts]`

use std::fmt::Write as _;
use std::io::{Read, Seek, SeekFrom};
use std::path::PathBuf;
use std::time::Instant;

use anyhow::{Context, Result, bail};
use trc_cuda::{Contexte, Flux, HoteEpingle, MemoireCarte, VueCarte, copier_vers_carte, copier_vers_hote};
use trc_es::Lecteur;
use trc_format::Fichier;
use trc_modele::Modele;
use trc_noyaux::Noyaux;
use trc_reference::Reference;
use trc_reference::gguf::{GGML_MXFP4, Gguf};

/// Les `n` premiers jetons de la fenêtre 0 d'un `.kld` de llama-perplexity (« _logits_ », n_ctx u32,
/// n_vocab i32, n_chunk i32, puis les jetons i32).
fn jetons_kld(chemin: &std::path::Path, n: usize) -> Result<Vec<u32>> {
    let mut f = std::fs::File::open(chemin)?;
    let mut t = [0u8; 20];
    f.read_exact(&mut t)?;
    if &t[0..8] != b"_logits_" {
        bail!("{} : pas un fichier de logits", chemin.display());
    }
    let n_ctx = u32::from_le_bytes(t[8..12].try_into().unwrap()) as usize;
    if n > n_ctx {
        bail!("{n} positions demandées, fenêtres de {n_ctx}");
    }
    let mut o = vec![0u8; 4 * n];
    f.read_exact(&mut o)?;
    Ok(o.chunks_exact(4).map(|c| u32::from_le_bytes(c.try_into().unwrap())).collect())
}

fn log_softmax(z: &[f64]) -> Vec<f64> {
    let mx = z.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let lse = mx + z.iter().map(|x| (x - mx).exp()).sum::<f64>().ln();
    z.iter().map(|x| x - lse).collect()
}

/// Indice du plus grand (égalité : le premier).
fn premier(z: &[f64]) -> usize {
    let mut b = 0;
    for i in 1..z.len() {
        if z[i] > z[b] {
            b = i;
        }
    }
    b
}

/// La ligne d'une position, au format de la chaîne K3 : position, jeton, KL, premier choix de la
/// référence, premier choix du chemin, écart relatif des logits.
fn ligne(p: usize, jeton: u32, r64: &[f64], z: &[f32]) -> (String, f64) {
    let c64: Vec<f64> = z.iter().map(|&x| x as f64).collect();
    let (lr, lc) = (log_softmax(r64), log_softmax(&c64));
    let kl: f64 = lr.iter().zip(&lc).map(|(a, b)| a.exp() * (a - b)).sum();
    let (pr, pc) = (premier(r64), premier(&c64));
    let den = r64.iter().fold(0.0f64, |m, x| m.max(x.abs()));
    let e = r64.iter().zip(&c64).fold(0.0f64, |m, (a, b)| m.max((a - b).abs())) / den;
    (format!("{p},{jeton},{kl:e},{pr},{pc},{e:e}"), kl)
}

/// L'emplacement SoA (§ 5.6) d'un expert, construit sur l'hôte depuis ses tranches du GGUF : codes
/// (16 o par bloc, ordre β), échelles E8M0, biais f32, aux décalages de `DimsExpert::disposition`.
fn emplacement(dims: &trc_noyaux::abi::DimsExpert, tranches: &[Vec<u8>; 3], biais: &[Vec<u8>; 3]) -> Vec<u8> {
    let mut o = vec![0u8; dims.taille_emplacement() as usize];
    for j in 0..3 {
        let d = dims.disposition(j);
        let (base, ech, bia) = (d.base as usize, d.echelles as usize, d.biais as usize);
        for beta in 0..dims.blocs(j) as usize {
            let b = &tranches[j][beta * 17..beta * 17 + 17];
            o[base + ech + beta] = b[0];
            o[base + 16 * beta..base + 16 * beta + 16].copy_from_slice(&b[1..17]);
        }
        o[base + bia..base + bia + biais[j].len()].copy_from_slice(&biais[j]);
    }
    o
}

/// Chemin G : trc-modele seul, experts du GGUF.
fn chemin_g(gguf: &Gguf, trc: &std::path::Path, jetons: &[u32], casser_experts: bool) -> Result<Vec<Vec<f32>>> {
    let fichier = Fichier::ouvrir(trc)?;
    let ctx = Contexte::nouveau(0)?;
    let f = Flux::nouveau(&ctx, true)?;
    let n = Noyaux::charger(&ctx)?;
    let lecteur = Lecteur::ouvrir(trc, 2).map_err(|e| anyhow::anyhow!("{e}"))?;
    let m = Modele::charger(&ctx, &f, &lecteur, &fichier, 4096)?;
    let h = m.h.clone();
    let te = h.taille_emplacement() as usize;
    let mut tampon = HoteEpingle::allouer(&ctx, te.max(1 << 20), false)?;
    let mut retour = HoteEpingle::allouer(&ctx, 4 * h.vocab + 4096, false)?;
    let slots: Vec<MemoireCarte> = (0..h.actifs).map(|_| MemoireCarte::allouer(&ctx, te)).collect::<trc_cuda::Result<_>>()?;
    let mut fic = std::fs::File::open(trc)?;
    let mut sortie = Vec::with_capacity(jetons.len());
    for (p, &jt) in jetons.iter().enumerate() {
        let t0 = Instant::now();
        let (abs, ol) = m.ligne_enchassement(jt)?;
        let mut l = vec![0u8; ol as usize];
        fic.seek(SeekFrom::Start(abs))?;
        fic.read_exact(&mut l)?;
        tampon.tranche_mut()[..l.len()].copy_from_slice(&l);
        let lv = m.tampon_ligne();
        copier_vers_carte(lv, &tampon, 0, l.len(), &f)?;
        m.enchasser(&n, VueCarte { adresse: lv.adresse, octets: ol as usize }, &f)?;
        f.synchroniser()?;
        for c in 0..h.couches {
            m.debut_couche(&n, c, p as u32, 0, 0, &f)?;
            copier_vers_hote(&mut retour, 0, m.indices(), &f)?;
            f.synchroniser()?;
            let idx: Vec<u32> = retour.tranche()[..4 * h.actifs].chunks_exact(4).map(|x| u32::from_le_bytes(x.try_into().unwrap())).collect();
            for (i, &e) in idx.iter().enumerate() {
                let mut tranches: [Vec<u8>; 3] = Default::default();
                let mut biais: [Vec<u8>; 3] = Default::default();
                for (j, nom) in ["ffn_gate_exps", "ffn_up_exps", "ffn_down_exps"].iter().enumerate() {
                    let t = gguf.tenseur(&format!("blk.{c}.{nom}.weight"))?.clone();
                    if t.type_ggml != GGML_MXFP4 {
                        bail!("{} : type {}", t.nom, t.type_ggml);
                    }
                    let tr = t.octets / h.experts as u64;
                    tranches[j] = gguf.lire_plage(t.decalage + e as u64 * tr, tr)?;
                    let tb = gguf.tenseur(&format!("blk.{c}.{nom}.bias"))?.clone();
                    let nb = tb.ne[0];
                    biais[j] = gguf.lire_plage(tb.decalage + e as u64 * nb * 4, nb * 4)?;
                }
                let o = emplacement(&h.dims, &tranches, &biais);
                tampon.tranche_mut()[..o.len()].copy_from_slice(&o);
                copier_vers_carte(slots[i].tout(), &tampon, 0, o.len(), &f)?;
                f.synchroniser()?;
            }
            let mut vues: Vec<VueCarte> = slots.iter().map(|s| s.tout()).collect();
            if casser_experts && c == 5 {
                vues.swap(0, 1);
            }
            m.fin_couche(&n, &vues, &f)?;
        }
        m.sortie(&n, &f)?;
        copier_vers_hote(&mut retour, 4096, m.logits(), &f)?;
        f.synchroniser()?;
        let z: Vec<f32> = retour.tranche()[4096..4096 + 4 * h.vocab].chunks_exact(4).map(|x| f32::from_le_bytes(x.try_into().unwrap())).collect();
        sortie.push(z);
        eprintln!("  G : position {p} ({:.1} s)", t0.elapsed().as_secs_f64());
    }
    Ok(sortie)
}

fn main() -> Result<()> {
    let a: Vec<String> = std::env::args().collect();
    if a.len() < 8 {
        eprintln!("usage : temoin-o2 <gguf> <trc> <kld> <k3.csv> <k3.json> <journal.json> <lignes.csv> [--chemins T,G] [--positions 160] [--positions-g 16] [--casser position|experts]");
        std::process::exit(2);
    }
    let (gguf_p, trc, kld, k3csv, k3json, jj, csv) =
        (PathBuf::from(&a[1]), PathBuf::from(&a[2]), PathBuf::from(&a[3]), PathBuf::from(&a[4]), PathBuf::from(&a[5]), PathBuf::from(&a[6]), PathBuf::from(&a[7]));
    let (mut chemins, mut n_p, mut n_g, mut casser) = ("T,G".to_string(), 160usize, 16usize, String::new());
    let mut i = 8;
    while i < a.len() {
        match a[i].as_str() {
            "--chemins" => chemins = a[i + 1].clone(),
            "--positions" => n_p = a[i + 1].parse()?,
            "--positions-g" => n_g = a[i + 1].parse()?,
            "--casser" => casser = a[i + 1].clone(),
            x => bail!("option inconnue {x}"),
        }
        i += 2;
    }
    if !casser.is_empty() && casser != "position" && casser != "experts" {
        bail!("--casser : position ou experts");
    }
    let debut = Instant::now();
    let jetons = jetons_kld(&kld, n_p)?;
    // La chaîne K3 : ses lignes et sa KL moyenne publiées.
    let k3: Vec<String> = std::fs::read_to_string(&k3csv)?.lines().skip(1).map(String::from).collect();
    let k3j = std::fs::read_to_string(&k3json)?;
    let kl_k3: String = k3j.split("\"kl_moyenne\": ").nth(1).context("kl_moyenne absente du journal K3")?.split(',').next().unwrap().trim().to_string();
    // La référence f64 (comme la chaîne K3 : Reference::evaluer, une séquence de 160 jetons).
    let t = Instant::now();
    let mut r = Reference::ouvrir(&gguf_p)?;
    let v = r.hyper.vocab;
    let mut zr = vec![0f64; n_p * v];
    r.evaluer(
        &[jetons.clone()],
        &|_, _| true,
        &mut |_, t, l| {
            zr[t * v..(t + 1) * v].copy_from_slice(l);
            Ok(())
        },
        &mut |s| eprintln!("  référence : {s}"),
    )?;
    drop(r);
    let s_ref = t.elapsed().as_secs_f64();
    let mut journal = String::from("{\n  \"outil\": \"temoin-o2\", \"etape\": \"O2\",\n");
    let _ = writeln!(journal, "  \"commande\": \"{}\",", a[1..].join(" ").replace('\\', "/"));
    let _ = writeln!(journal, "  \"positions\": {n_p}, \"positions_g\": {n_g}, \"casser\": \"{casser}\", \"secondes_reference\": {s_ref:.1},");
    let _ = writeln!(journal, "  \"kl_moyenne_k3\": {kl_k3},");
    let mut lignes = String::from("chemin,position,jeton,kl,premier_ref,premier_chemin,ecart_relatif_logits,egale_k3\n");
    let mut verdicts = Vec::new();
    let gguf = Gguf::ouvrir(&gguf_p)?;
    for ch in chemins.split(',') {
        let t = Instant::now();
        let z: Vec<Vec<f32>> = match ch {
            "T" => {
                let mut m = trc_ordo::Moteur::nouveau(&trc_ordo::Config::nouvelle(&trc))?;
                let mut tout = Vec::with_capacity(n_p);
                let mut zz = vec![0f32; v];
                for (p, &j) in jetons.iter().enumerate() {
                    let pos = if casser == "position" { p as u32 + 1 } else { p as u32 };
                    m.pas(j, pos, Some(&mut zz))?;
                    tout.push(zz.clone());
                }
                tout
            }
            "G" => chemin_g(&gguf, &trc, &jetons[..n_g.min(n_p)], casser == "experts")?,
            x => bail!("chemin inconnu {x}"),
        };
        let s = t.elapsed().as_secs_f64();
        let (mut egales, mut somme) = (0usize, 0.0f64);
        let mut premiere_difference = None;
        for (p, zp) in z.iter().enumerate() {
            let (l, kl) = ligne(p, jetons[p], &zr[p * v..(p + 1) * v], zp);
            let eg = k3.get(p).is_some_and(|x| *x == l);
            if eg {
                egales += 1;
            } else if premiere_difference.is_none() {
                premiere_difference = Some(format!("{l} | K3 : {}", k3.get(p).cloned().unwrap_or_default()));
            }
            somme += kl;
            let _ = writeln!(lignes, "{ch},{l},{}", eg as u8);
        }
        let kl_moy = somme / z.len() as f64;
        let moy_egale = ch == "T" && z.len() == 160 && format!("{kl_moy:e}") == kl_k3;
        let tient = egales == z.len() && (ch != "T" || z.len() != 160 || moy_egale);
        let _ = writeln!(
            journal,
            "  \"{ch}\": {{\"positions\": {}, \"lignes_egales_k3\": {egales}, \"kl_moyenne\": {kl_moy:e}, \"kl_moyenne_egale_k3\": {moy_egale}, \"secondes\": {s:.1}, \"premiere_difference\": \"{}\", \"tient\": {tient}}},",
            z.len(),
            premiere_difference.clone().unwrap_or_default()
        );
        eprintln!("chemin {ch} : {egales} lignes sur {} égales à la chaîne K3 ; KL moyenne {kl_moy:e} (K3 {kl_k3}) ; {s:.1} s", z.len());
        if let Some(d) = &premiere_difference {
            eprintln!("  première différence : {d}");
        }
        verdicts.push((ch.to_string(), tient));
    }
    let tous = verdicts.iter().all(|(_, t)| *t);
    let verdict = match (casser.is_empty(), tous) {
        (true, true) => "O2 TIENT : chaque ligne égale à la chaîne K3",
        (true, false) => "O2 TOMBE : au moins une ligne diffère de la chaîne K3",
        (false, false) => "cassure : le témoin tombe, comme attendu",
        (false, true) => "CASSURE NON VUE : le témoin tient malgré la faute",
    };
    let _ = writeln!(journal, "  \"secondes\": {:.1}, \"tient\": {tous}, \"verdict\": \"{verdict}\"\n}}", debut.elapsed().as_secs_f64());
    std::fs::write(&jj, journal)?;
    std::fs::write(&csv, lignes)?;
    eprintln!("{verdict}");
    Ok(())
}
