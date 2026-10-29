//! genome-recette-kl : les logits des fenêtres d'un .kld avec des experts substitués (base `.sym`
//! ou recette `.f32w`) ; la KL se lit ensuite par `juge kl --base base.kld --test S.kld`.
//! Copie de `kl` de `outils/genome/eclaireur/capture/src/main.rs` (sujet genome, 2026-10-16).
//!
//! ```text
//! genome-recette-kl kl --gguf M --kld base.kld --sub D --sortie S.kld [--fenetres N] [--fils F]
//! ```


use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Instant;

use anyhow::{Context, Result, bail};
use serde_json::json;
use trc_juge::kld::{EcrivainKld, FichierKld, positions_notees};

struct Args {
    mots: HashMap<String, String>,
    drapeaux: Vec<String>,
}

impl Args {
    fn lire(brut: &[String]) -> Args {
        let (mut mots, mut drapeaux) = (HashMap::new(), Vec::new());
        let mut i = 0;
        while i < brut.len() {
            if let Some(cle) = brut[i].strip_prefix("--") {
                if i + 1 < brut.len() && !brut[i + 1].starts_with("--") {
                    mots.insert(cle.to_string(), brut[i + 1].clone());
                    i += 2;
                    continue;
                }
                drapeaux.push(cle.to_string());
            }
            i += 1;
        }
        Args { mots, drapeaux }
    }
    fn chemin(&self, c: &str) -> Result<PathBuf> {
        self.mots.get(c).map(PathBuf::from).with_context(|| format!("--{c} manque"))
    }
    fn nombre(&self, c: &str, d: usize) -> Result<usize> {
        Ok(match self.mots.get(c) {
            Some(v) => v.parse()?,
            None => d,
        })
    }
    fn a(&self, d: &str) -> bool {
        self.drapeaux.iter().any(|x| x == d)
    }
}

fn journal(m: &str) {
    let t = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    eprintln!("[{t}] {m}");
}

mod modele;

fn main() -> Result<()> {
    let brut: Vec<String> = std::env::args().collect();
    if brut.len() < 2 {
        bail!("usage : voir l'en-tête de src/main.rs");
    }
    let args = Args::lire(&brut[2..]);
    if let Some(f) = args.mots.get("fils") {
        rayon::ThreadPoolBuilder::new().num_threads(f.parse()?).build_global()?;
    }
    match brut[1].as_str() {
        "kl" => kl(&args, &brut),
        c => bail!("sous-commande inconnue : {c}"),
    }
}

fn kl(args: &Args, brut: &[String]) -> Result<()> {
    let t0 = Instant::now();
    let gguf = args.chemin("gguf")?;
    let base = FichierKld::ouvrir(&args.chemin("kld")?)?;
    let n_fen = args.nombre("fenetres", base.n_chunk)?.min(base.n_chunk);
    let n_ctx = base.n_ctx;
    let notees = positions_notees(n_ctx);
    let sequences: Vec<Vec<u32>> = (0..n_fen).map(|c| base.jetons_fenetre(c)[..n_ctx - 1].to_vec()).collect();
    let jetons_ecrits: Vec<u32> = base.jetons[..n_fen * n_ctx].to_vec();
    let mut ecrivain = EcrivainKld::creer(&args.chemin("sortie")?, n_ctx, base.n_vocab, &jetons_ecrits)?;
    let mut r = modele::Reference::ouvrir(&gguf)?;
    r.substitution = Some(args.chemin("sub")?);
    let notee = |_s: usize, t: usize| notees.contains(&t);
    r.evaluer(&sequences, &notee, &mut |_, _, z| ecrivain.ecrire(z), &mut |m| journal(m))?;
    let ecrites = ecrivain.entrees_ecrites;
    ecrivain.finir()?;
    println!("{}", serde_json::to_string_pretty(&json!({
        "outil": "genome-capture kl", "commande": brut, "fenetres": n_fen, "entrees_ecrites": ecrites,
        "experts_substitues": r.experts_substitues, "lectures_experts": r.compteurs.lectures_experts,
        "duree_s": t0.elapsed().as_secs_f64(),
    }))?);
    Ok(())
}
