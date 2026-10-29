//! genome-capture : entrées réelles des experts de gpt-oss, et KL d'une base substituée.
//!
//! ```text
//! genome-capture temoin-fourche --gguf M --kld base.kld [--n 24] [--casser]
//!     La fourche (avec capture) rend les logits de trc-reference au bit, sur les n premiers jetons
//!     de la fenêtre 0. --casser : la fourche tourne sans l'échelle de concentration de YaRN ; le
//!     témoin doit tomber.
//! genome-capture capturer --gguf M --dll llama.dll --vocab M --texte T --kld base.kld --de A --a B --sortie D
//!     Découpe T (trc-jetons), vérifie que les fenêtres du .kld en sont le début, puis passe les
//!     fenêtres A..B (511 jetons chacune, la règle de `juge reference`) dans la fourche et écrit, par
//!     couche, les entrées des experts et le routage.
//! genome-capture temoin-zero --gguf M --kld base.kld [--n 24] [--casser]
//!     Le codon synonyme du zéro : la fourche, chaque −0 (code 8) réécrit en +0 (code 0), rend les
//!     logits de trc-reference AU BIT (seuil déclaré : 0 logit différent). --casser : le code 1 (0,5)
//!     réécrit en 0 (la valeur change) ; le témoin doit tomber.
//! genome-capture kl --gguf M --kld base.kld [--sub D] [--zero-canonique] --sortie S.kld [--fenetres N]
//!     Les logits des fenêtres du .kld avec les experts dont D contient une base substituée ; la KL se
//!     lit ensuite par `juge kl --base base.kld --test S.kld`.
//! ```

mod modele;

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
        "temoin-fourche" => temoin_fourche(&args, &brut),
        "capturer" => capturer(&args, &brut),
        "kl" => kl(&args, &brut),
        "temoin-zero" => temoin_zero(&args, &brut),
        c => bail!("sous-commande inconnue : {c}"),
    }
}

fn temoin_fourche(args: &Args, brut: &[String]) -> Result<()> {
    let t0 = Instant::now();
    let gguf = args.chemin("gguf")?;
    let base = FichierKld::ouvrir(&args.chemin("kld")?)?;
    let n = args.nombre("n", 24)?;
    let seq: Vec<u32> = base.jetons_fenetre(0)[..n].to_vec();
    let mut a: Vec<Vec<f64>> = Vec::new();
    let mut r = trc_reference::modele::Reference::ouvrir(&gguf)?;
    r.evaluer(std::slice::from_ref(&seq), &|_, _| true, &mut |_, _, z| { a.push(z.to_vec()); Ok(()) }, &mut |m| journal(m))?;
    drop(r);
    let mut f = modele::Reference::ouvrir(&gguf)?;
    let tmp = std::env::temp_dir().join(format!("genome-capture-temoin-{}", std::process::id()));
    std::fs::create_dir_all(&tmp)?;
    f.capture = Some(tmp.clone());
    let casser = args.a("casser");
    if casser {
        f.rope.concentration = 1.0;
    }
    let mut b: Vec<Vec<f64>> = Vec::new();
    f.evaluer(std::slice::from_ref(&seq), &|_, _| true, &mut |_, _, z| { b.push(z.to_vec()); Ok(()) }, &mut |m| journal(m))?;
    let (mut diff, mut max) = (0usize, 0.0f64);
    for (za, zb) in a.iter().zip(b.iter()) {
        for (x, y) in za.iter().zip(zb.iter()) {
            if x.to_bits() != y.to_bits() {
                diff += 1;
                max = max.max((x - y).abs());
            }
        }
    }
    let captures = std::fs::read_dir(&tmp)?.count();
    let taille_h0 = std::fs::metadata(tmp.join("h-L00.f32"))?.len();
    std::fs::remove_dir_all(&tmp)?;
    let tient = diff == 0 && a.len() == n && captures == 2 * f.hyper.couches && taille_h0 == (n * f.hyper.d_modele * 4) as u64;
    println!("{}", serde_json::to_string_pretty(&json!({
        "outil": "genome-capture temoin-fourche", "commande": brut, "n": n, "casser": casser,
        "logits_compares": a.len() * f.hyper.vocab, "logits_differents_au_bit": diff, "ecart_absolu_max": max,
        "fichiers_captures": captures, "octets_h_L00": taille_h0,
        "seuil_declare": "0 logit différent au bit, 2 fichiers par couche, h-L00 = n × d × 4 octets",
        "tient": tient, "duree_s": t0.elapsed().as_secs_f64(),
    }))?);
    Ok(())
}

fn capturer(args: &Args, brut: &[String]) -> Result<()> {
    let t0 = Instant::now();
    let gguf = args.chemin("gguf")?;
    let base = FichierKld::ouvrir(&args.chemin("kld")?)?;
    let j = trc_jetons::Jetons::ouvrir(&args.chemin("dll")?, &args.chemin("vocab")?)?;
    let texte = std::fs::read_to_string(args.chemin("texte")?)?;
    let jet = j.decouper(&texte, true);
    drop(j);
    let n_ctx = base.n_ctx;
    let egaux = jet.len() >= base.jetons.len() && jet[..base.jetons.len()] == base.jetons[..];
    if !egaux {
        bail!("le découpage ne redonne pas les fenêtres du .kld");
    }
    let (de, a) = (args.nombre("de", 10)?, args.nombre("a", 22)?);
    if (a * n_ctx) > jet.len() || de >= a {
        bail!("fenêtres {de}..{a} : le texte n'a que {} fenêtres", jet.len() / n_ctx);
    }
    let sequences: Vec<Vec<u32>> = (de..a).map(|c| jet[c * n_ctx..(c + 1) * n_ctx][..n_ctx - 1].to_vec()).collect();
    let sortie = args.chemin("sortie")?;
    std::fs::create_dir_all(&sortie)?;
    let mut o = Vec::new();
    for s in &sequences {
        for &t in s {
            o.extend_from_slice(&t.to_le_bytes());
        }
    }
    std::fs::write(sortie.join("jetons.u32"), o)?;
    let mut r = modele::Reference::ouvrir(&gguf)?;
    r.capture = Some(sortie.clone());
    r.evaluer(&sequences, &|_, _| false, &mut |_, _, _| Ok(()), &mut |m| journal(m))?;
    let resume = json!({
        "outil": "genome-capture capturer", "commande": brut,
        "jetons_du_texte": jet.len(), "fenetres_du_kld_egales": egaux,
        "fenetres": [de, a], "positions": sequences.len() * (n_ctx - 1),
        "couches": r.hyper.couches, "d_modele": r.hyper.d_modele,
        "octets_experts_lus": r.compteurs.octets_experts_lus, "duree_s": t0.elapsed().as_secs_f64(),
    });
    std::fs::write(sortie.join("capture.json"), serde_json::to_string_pretty(&resume)?)?;
    println!("{}", serde_json::to_string_pretty(&resume)?);
    Ok(())
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
    if let Ok(d) = args.chemin("sub") {
        r.substitution = Some(d);
    }
    if args.a("zero-canonique") {
        r.reecrire_code = Some((8, 0));
    }
    let notee = |_s: usize, t: usize| notees.contains(&t);
    r.evaluer(&sequences, &notee, &mut |_, _, z| ecrivain.ecrire(z), &mut |m| journal(m))?;
    let ecrites = ecrivain.entrees_ecrites;
    ecrivain.finir()?;
    println!("{}", serde_json::to_string_pretty(&json!({
        "outil": "genome-capture kl", "commande": brut, "fenetres": n_fen, "entrees_ecrites": ecrites,
        "experts_substitues": r.experts_substitues, "demi_octets_reecrits": r.codes_reecrits, "lectures_experts": r.compteurs.lectures_experts,
        "duree_s": t0.elapsed().as_secs_f64(),
    }))?);
    Ok(())
}

fn temoin_zero(args: &Args, brut: &[String]) -> Result<()> {
    let t0 = Instant::now();
    let gguf = args.chemin("gguf")?;
    let base = FichierKld::ouvrir(&args.chemin("kld")?)?;
    let n = args.nombre("n", 24)?;
    let seq: Vec<u32> = base.jetons_fenetre(0)[..n].to_vec();
    let mut a: Vec<Vec<f64>> = Vec::new();
    let mut r = trc_reference::modele::Reference::ouvrir(&gguf)?;
    r.evaluer(std::slice::from_ref(&seq), &|_, _| true, &mut |_, _, z| { a.push(z.to_vec()); Ok(()) }, &mut |m| journal(m))?;
    drop(r);
    let casser = args.a("casser");
    let mut f = modele::Reference::ouvrir(&gguf)?;
    f.reecrire_code = Some(if casser { (1, 0) } else { (8, 0) });
    let mut b: Vec<Vec<f64>> = Vec::new();
    f.evaluer(std::slice::from_ref(&seq), &|_, _| true, &mut |_, _, z| { b.push(z.to_vec()); Ok(()) }, &mut |m| journal(m))?;
    let (mut diff, mut max) = (0usize, 0.0f64);
    for (za, zb) in a.iter().zip(b.iter()) {
        for (x, y) in za.iter().zip(zb.iter()) {
            if x.to_bits() != y.to_bits() {
                diff += 1;
                max = max.max((x - y).abs());
            }
        }
    }
    println!("{}", serde_json::to_string_pretty(&json!({
        "outil": "genome-capture temoin-zero", "commande": brut, "n": n, "casser": casser,
        "reecriture": if casser { "code 1 (0,5) -> 0" } else { "code 8 (-0) -> 0 (+0)" },
        "demi_octets_reecrits": f.codes_reecrits, "lectures_experts": f.compteurs.lectures_experts,
        "logits_compares": a.len() * f.hyper.vocab, "logits_differents_au_bit": diff, "ecart_absolu_max": max,
        "seuil_declare": "0 logit différent au bit", "tient": diff == 0 && f.codes_reecrits > 0,
        "duree_s": t0.elapsed().as_secs_f64(),
    }))?);
    Ok(())
}
