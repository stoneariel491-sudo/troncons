//! trc-codeur : le codeur GGUF → `.trc` de troncons et la vérification C1 (lot F).
//!
//! ```text
//! trc-codeur coder    <source.gguf> <dest.trc> [--brut | --canonique] [--fils N] [--date AAAA-MM-JJ]
//!                     [--sha256-attendu HEX] [--journal j.json]
//! trc-codeur vocab    <source.gguf> <dest.vocab.gguf> [--journal j.json]
//! trc-codeur verifier <m.trc> <source.gguf> [--fils N] [--casser COUCHE EXPERT]
//!                     [--casser-8 COUCHE EXPERT] [--sans-sha] [--journal j.json]
//! ```
//! `--canonique` écrit la v1.2 (codon synonyme du zéro, genome/06-codon-v1-2.md).
//! `verifier` sort avec le code 0 si C1 tient (et, sous `--casser`, si exactement l'expert visé
//! est trouvé faux), 1 sinon.

mod coder;
mod gguf;
mod verifier;
mod vocab;

use anyhow::{Context, Result, bail};
use serde_json::{Value, json};
use std::path::{Path, PathBuf};

fn valeur<'a>(args: &'a [String], nom: &str) -> Option<&'a str> {
    args.iter().position(|a| a == nom).and_then(|i| args.get(i + 1)).map(|s| s.as_str())
}

fn drapeau(args: &[String], nom: &str) -> bool {
    args.iter().any(|a| a == nom)
}

/// La date UTC du jour, AAAA-MM-JJ (jours depuis 1970 → date civile, algorithme de Hinnant).
fn date_utc() -> String {
    let s = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0) as i64;
    let z = s.div_euclid(86_400) + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = yoe + era * 400 + if m <= 2 { 1 } else { 0 };
    format!("{y:04}-{m:02}-{d:02}")
}

fn hex32(s: &str) -> Result<[u8; 32]> {
    if s.len() != 64 {
        bail!("empreinte SHA-256 de {} caractères (64 attendus)", s.len());
    }
    let mut b = [0u8; 32];
    for i in 0..32 {
        b[i] = u8::from_str_radix(&s[2 * i..2 * i + 2], 16).context("empreinte SHA-256 non hexadécimale")?;
    }
    Ok(b)
}

fn ecrire_journal(args: &[String], mut v: Value) -> Result<()> {
    if let Value::Object(m) = &mut v {
        m.insert("commande".into(), json!(args.join(" ")));
        m.insert("outil".into(), json!(format!("trc-codeur {}", env!("CARGO_PKG_VERSION"))));
        m.insert("date_utc".into(), json!(date_utc()));
    }
    let texte = serde_json::to_string_pretty(&v)?;
    if let Some(j) = valeur(args, "--journal") {
        std::fs::write(j, &texte).with_context(|| format!("écriture du journal {j}"))?;
    }
    println!("{texte}");
    Ok(())
}

fn principal() -> Result<i32> {
    let args: Vec<String> = std::env::args().collect();
    let pos: Vec<&String> = args.iter().skip(1).filter(|a| !a.starts_with("--")).collect();
    let fils: usize = valeur(&args, "--fils").map(|s| s.parse()).transpose()?.unwrap_or(6);
    rayon::ThreadPoolBuilder::new().num_threads(fils).build_global()?;
    let usage = "usage : trc-codeur coder|vocab|verifier … (voir l'en-tête de main.rs)";
    match pos.first().map(|s| s.as_str()) {
        Some("coder") if pos.len() >= 3 => {
            let o = coder::Options {
                source: Path::new(pos[1].as_str()),
                dest: Path::new(pos[2].as_str()),
                brut: drapeau(&args, "--brut"),
                canonique: drapeau(&args, "--canonique"),
                date: valeur(&args, "--date").map(String::from).unwrap_or_else(date_utc),
                sha256_attendu: valeur(&args, "--sha256-attendu").map(hex32).transpose()?,
            };
            let v = coder::coder(&o)?;
            ecrire_journal(&args, v)?;
            Ok(0)
        }
        Some("vocab") if pos.len() >= 3 => {
            let v = vocab::ecrire(Path::new(pos[1].as_str()), Path::new(pos[2].as_str()))?;
            ecrire_journal(&args, v)?;
            Ok(0)
        }
        Some("verifier") if pos.len() >= 3 => {
            let paire = |nom: &str| -> Result<Option<(u16, u16)>> {
                Ok(match args.iter().position(|a| a == nom) {
                    Some(i) => Some((args.get(i + 1).with_context(|| format!("{nom} COUCHE EXPERT"))?.parse()?, args.get(i + 2).with_context(|| format!("{nom} COUCHE EXPERT"))?.parse()?)),
                    None => None,
                })
            };
            let casser = paire("--casser")?;
            let casser_8 = paire("--casser-8")?;
            if casser.is_some() && casser_8.is_some() {
                bail!("une seule cassure à la fois");
            }
            // Les positions qui suivent --casser ne sont pas des chemins.
            let chemins: Vec<PathBuf> = pos[1..3].iter().map(|s| PathBuf::from(s.as_str())).collect();
            let o = verifier::Options { trc: &chemins[0], gguf: &chemins[1], casser, casser_8, sha: !drapeau(&args, "--sans-sha") };
            let v = verifier::verifier(&o)?;
            let c1 = v["C1"].as_bool() == Some(true);
            let vise = casser.or(casser_8);
            let un_seul = |(c, x): (u16, u16)| {
                v["experts_faux"].as_u64() == Some(1) && v["faux"][0]["couche"].as_u64() == Some(c as u64) && v["faux"][0]["expert"].as_u64() == Some(x as u64)
            };
            // Sous --casser-8, l'expert visé doit tomber par ses octets et garder sa valeur.
            let attendu_casse = vise.is_some_and(un_seul)
                && (casser_8.is_none() || (v["faux"][0]["valeur"].as_bool() == Some(true) && v["faux"][0]["sans_8"].as_bool() == Some(false) && v["faux"][0]["octets"].as_bool() == Some(false)));
            ecrire_journal(&args, v)?;
            Ok(if vise.is_some() { if attendu_casse { 0 } else { 1 } } else if c1 { 0 } else { 1 })
        }
        _ => {
            eprintln!("{usage}");
            Ok(2)
        }
    }
}

fn main() {
    match principal() {
        Ok(code) => std::process::exit(code),
        Err(e) => {
            eprintln!("erreur : {e:#}");
            std::process::exit(1);
        }
    }
}
