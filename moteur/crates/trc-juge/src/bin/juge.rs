//! juge : le programme du lot R.
//!
//! ```text
//! juge reference --gguf M.gguf --jetons-de base.kld --sortie ref.kld [--fenetres N] [--yarn openai|llamacpp]
//!                [--fils F] [--journal j.json] [--kl-contre-base] [--casser-yarn] [--imiter q8,kv16]
//!                [--routage r.bin] [--imposer-routage r.bin]
//!     Logits de la référence f64 sur les fenêtres d'un fichier .kld (mêmes jetons), écrits au même
//!     format. Avec --kl-contre-base : KL(base ‖ référence brute f64) au passage (sans codage côté
//!     référence), dans le journal.
//! juge kl --base P.kld --test Q.kld [--fenetres N] [--csv positions.csv] [--json resume.json]
//!     KL(P ‖ Q) position par position ; Q décodé de son propre codage 16 bits, ses log-probabilités
//!     prises telles quelles (sans renormalisation : voir `stats::position_decodee`).
//! juge comparer --verite V.kld --a A.kld --b B.kld [--fenetres N] [--json j.json] [--csv c.csv]
//!     Le jugement C4 : A et B contre la même vérité V, sur les mêmes positions, différences
//!     appariées ; verdicts littéral et statistique (voir `comparer`).
//! juge rampe [--csv r.csv]
//!     Les fréquences de YaRN de gpt-oss par `Rope::yarn`, pour les deux rampes (données de la
//!     figure R-M3 ; second chemin : mesures/moteur/R/rampe_yarn.py).
//! juge jetons --dll llama.dll --vocab V.gguf --texte T.txt --kld base.kld
//!     Témoin de trc-jetons : le découpage de T égale les jetons enregistrés par llama-perplexity.
//! juge temoin-chemins --gguf M.gguf --kld base.kld --n N [--yarn …] [--casser]
//!     Témoin de trc-reference : `pas` (jeton par jeton) = `evaluer` (par lots) au bit, sur les N
//!     premiers jetons de la première fenêtre. --casser : `pas` tourne avec l'autre variante de
//!     YaRN, le témoin doit tomber.
//! juge temoin-compteurs --fichier F [--mio 256] [--casser]
//!     Témoins des compteurs de R2 (seuils en tête de `temoin_compteurs`).
//! ```

use std::collections::HashMap;
use std::io::Write;
use std::path::PathBuf;
use std::time::{Instant, SystemTime, UNIX_EPOCH};

use anyhow::{Context, Result, bail};
use serde_json::json;

use trc_juge::kld::{Entree, EcrivainKld, FichierKld, mots_par_entree, positions_notees};
use trc_juge::stats::{Position, position, position_decodee, resumer};
use trc_reference::{Reference, VarianteYarn};

struct Args {
    mots: HashMap<String, String>,
    drapeaux: Vec<String>,
}

impl Args {
    fn lire(brut: &[String]) -> Args {
        let mut mots = HashMap::new();
        let mut drapeaux = Vec::new();
        let mut i = 0;
        while i < brut.len() {
            let a = &brut[i];
            if let Some(cle) = a.strip_prefix("--") {
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
    fn chemin(&self, cle: &str) -> Result<PathBuf> {
        self.mots.get(cle).map(PathBuf::from).with_context(|| format!("--{cle} manque"))
    }
    fn nombre(&self, cle: &str, defaut: usize) -> Result<usize> {
        Ok(match self.mots.get(cle) {
            Some(v) => v.parse().with_context(|| format!("--{cle} {v}"))?,
            None => defaut,
        })
    }
    fn a(&self, d: &str) -> bool {
        self.drapeaux.iter().any(|x| x == d)
    }
    fn variante(&self) -> Result<VarianteYarn> {
        Ok(match self.mots.get("yarn").map(|s| s.as_str()) {
            None | Some("openai") => VarianteYarn::OpenAi,
            Some("llamacpp") => VarianteYarn::LlamaCpp,
            Some(v) => bail!("--yarn {v} : openai ou llamacpp"),
        })
    }
}

fn maintenant() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0)
}

fn journal_ligne(texte: &str) {
    eprintln!("[{}] {texte}", maintenant());
}

fn main() -> Result<()> {
    let brut: Vec<String> = std::env::args().collect();
    if brut.len() < 2 {
        bail!("usage : juge <reference|kl|comparer|jetons|temoin-chemins|temoin-compteurs> …");
    }
    let args = Args::lire(&brut[2..]);
    if let Some(f) = args.mots.get("fils") {
        rayon::ThreadPoolBuilder::new().num_threads(f.parse()?).build_global()?;
    }
    match brut[1].as_str() {
        "reference" => reference(&args, &brut),
        "kl" => kl(&args, &brut),
        "comparer" => comparer(&args, &brut),
        "rampe" => rampe(&args),
        "jetons" => jetons(&args, &brut),
        "temoin-chemins" => temoin_chemins(&args, &brut),
        "temoin-compteurs" => temoin_compteurs(&args, &brut),
        c => bail!("sous-commande inconnue : {c}"),
    }
}

fn reference(args: &Args, brut: &[String]) -> Result<()> {
    let t0 = Instant::now();
    let debut = maintenant();
    let gguf = args.chemin("gguf")?;
    let mut base = FichierKld::ouvrir(&args.chemin("jetons-de")?)?;
    let n_fen = args.nombre("fenetres", base.n_chunk)?.min(base.n_chunk);
    let variante = args.variante()?;
    let mut r = Reference::ouvrir_variante(&gguf, variante)?;
    // Cassure de R1 (§ 6.5) : YaRN sans son échelle de concentration ; le témoin R1 doit tomber.
    let casser_yarn = args.a("casser-yarn");
    if casser_yarn {
        r.rope.concentration = 1.0;
    }
    // Imitations de llama.cpp (mesure de décomposition de R1, jamais la référence) : --imiter q8,kv16.
    if let Some(liste) = args.mots.get("imiter") {
        for m in liste.split(',') {
            match m {
                "q8" => r.imitation.q8 = true,
                "kv16" => r.imitation.kv16 = true,
                autre => bail!("--imiter {autre} : q8 ou kv16"),
            }
        }
    }
    if r.hyper.vocab != base.n_vocab {
        bail!("vocabulaire : {} dans le GGUF, {} dans le .kld", r.hyper.vocab, base.n_vocab);
    }
    let fichier_routage = args.chemin("routage").ok();
    // Expérience des bascules de routage : --imposer-routage r.bin (écrit par --routage d'un autre calcul).
    if let Ok(chemin) = args.chemin("imposer-routage") {
        let o = std::fs::read(&chemin)?;
        let couches = u32::from_le_bytes(o[0..4].try_into()?) as usize;
        let n_pos = u32::from_le_bytes(o[4..8].try_into()?) as usize;
        if couches != r.hyper.couches || o.len() != 8 + couches * n_pos * 8 {
            bail!("{} : {couches} couches, {n_pos} positions, {} octets : incompatible", chemin.display(), o.len());
        }
        r.routage_impose = Some(o[8..].chunks_exact(8).map(|c| [c[0], c[1], c[2], c[3]]).collect());
    }
    if fichier_routage.is_some() {
        r.journal_routage = Some(Vec::new());
    }
    journal_ligne(&format!("référence ouverte en {:.1} s : {:?}, rampe [{}, {}]", t0.elapsed().as_secs_f64(), r.hyper, r.rope.bas, r.rope.haut));
    let n_ctx = base.n_ctx;
    let notees = positions_notees(n_ctx);
    // Une séquence par fenêtre : les jetons 0 … n_ctx − 2 (la dernière position notée est n_ctx − 2).
    let sequences: Vec<Vec<u32>> = (0..n_fen).map(|c| base.jetons_fenetre(c)[..n_ctx - 1].to_vec()).collect();
    let jetons_ecrits: Vec<u32> = base.jetons[..n_fen * n_ctx].to_vec();
    let mut ecrivain = EcrivainKld::creer(&args.chemin("sortie")?, n_ctx, base.n_vocab, &jetons_ecrits)?;
    let comparer = args.a("kl-contre-base");
    let nv = mots_par_entree(base.n_vocab);
    let mut positions: Vec<Position> = Vec::new();
    let n_vocab = base.n_vocab;
    // La fenêtre de la base, lue à la demande (les logits arrivent dans l'ordre (s, t) croissant) :
    // une fenêtre (51 Mo) en mémoire au lieu des dix (reprise du 2026-10-15, machine partagée).
    let mut fenetre_base: (usize, Vec<u16>) = (usize::MAX, Vec::new());
    let mut rendre = |s: usize, t: usize, z: &[f64]| -> Result<()> {
        ecrivain.ecrire(z)?;
        if comparer {
            if fenetre_base.0 != s {
                fenetre_base = (s, base.fenetre(s)?);
            }
            let k = t - notees.start;
            let e = Entree::depuis(&fenetre_base.1[k * nv..(k + 1) * nv], n_vocab);
            let suivant = sequences_suivant(&jetons_ecrits, n_ctx, s, t);
            positions.push(position(&e, |i| z[i], n_vocab, suivant));
        }
        Ok(())
    };
    let notee = |_s: usize, t: usize| notees.contains(&t);
    r.evaluer(&sequences, &notee, &mut rendre, &mut |m| journal_ligne(m))?;
    let ecrites = ecrivain.entrees_ecrites;
    ecrivain.finir()?;
    // Journal de routage : u32 couches, u32 positions (aplaties, chaque fenêtre de 0 à n_ctx − 2),
    // puis pour chaque couche et chaque position : 4 × u8 experts (ordre du top-k), f32 marge.
    if let (Some(chemin), Some(j)) = (&fichier_routage, &r.journal_routage) {
        let n_pos = j.len() / r.hyper.couches;
        let mut o = Vec::with_capacity(8 + j.len() * 8);
        o.extend_from_slice(&(r.hyper.couches as u32).to_le_bytes());
        o.extend_from_slice(&(n_pos as u32).to_le_bytes());
        for (e, m) in j {
            o.extend_from_slice(e);
            o.extend_from_slice(&m.to_le_bytes());
        }
        std::fs::write(chemin, o)?;
    }
    let usages_par_couche: Vec<u64> = r.compteurs.usages.iter().map(|u| u.iter().filter(|&&c| c > 0).count() as u64).collect();
    let mut j = json!({
        "outil": "juge reference",
        "commande": brut,
        "debut_unix": debut,
        "fin_unix": maintenant(),
        "duree_s": t0.elapsed().as_secs_f64(),
        "gguf": gguf,
        "variante_yarn": format!("{variante:?}"),
        "rampe_yarn": [r.rope.bas, r.rope.haut],
        "concentration": r.rope.concentration,
        "cassure_yarn_sans_echelle": casser_yarn,
        "imitation_llamacpp": format!("{:?}", r.imitation),
        "routage_impose": args.mots.get("imposer-routage"),
        "fenetres": n_fen,
        "n_ctx": n_ctx,
        "entrees_ecrites": ecrites,
        "octets_experts_lus": r.compteurs.octets_experts_lus,
        "lectures_experts": r.compteurs.lectures_experts,
        "experts_distincts_par_couche": usages_par_couche,
        "blocs_mxfp4_e255": r.compteurs.blocs_e255,
        "fils": rayon::current_num_threads(),
        "avx2_fma": cfg!(target_arch = "x86_64") && std::is_x86_feature_detected!("avx2") && std::is_x86_feature_detected!("fma"),
    });
    if comparer {
        j["kl_base_contre_reference_brute"] = serde_json::to_value(resumer(&positions))?;
    }
    let texte = serde_json::to_string_pretty(&j)?;
    println!("{texte}");
    if let Ok(p) = args.chemin("journal") {
        std::fs::write(p, texte)?;
    }
    Ok(())
}

/// Le jeton qui suit la position t de la fenêtre s (le jeton noté).
fn sequences_suivant(jetons: &[u32], n_ctx: usize, s: usize, t: usize) -> usize {
    jetons[s * n_ctx + t + 1] as usize
}

fn kl(args: &Args, brut: &[String]) -> Result<()> {
    let t0 = Instant::now();
    let mut p = FichierKld::ouvrir(&args.chemin("base")?)?;
    let mut q = FichierKld::ouvrir(&args.chemin("test")?)?;
    if p.n_vocab != q.n_vocab || p.n_ctx != q.n_ctx {
        bail!("bases incompatibles : n_vocab {}/{}, n_ctx {}/{}", p.n_vocab, q.n_vocab, p.n_ctx, q.n_ctx);
    }
    let n_fen = args.nombre("fenetres", p.n_chunk.min(q.n_chunk))?.min(p.n_chunk.min(q.n_chunk));
    for c in 0..n_fen {
        if p.jetons_fenetre(c) != q.jetons_fenetre(c) {
            bail!("fenêtre {c} : les jetons diffèrent entre les deux fichiers");
        }
    }
    let (n, nv, n_ctx) = (p.n_vocab, mots_par_entree(p.n_vocab), p.n_ctx);
    let notees = positions_notees(n_ctx);
    let mut toutes = Vec::new();
    let mut csv = String::from("fenetre,position,kl,meme_premier,nll_test,nll_base,dp,premier_base,premier_test\n");
    for c in 0..n_fen {
        let fp = p.fenetre(c)?;
        let fq = q.fenetre(c)?;
        let jet = p.jetons_fenetre(c).to_vec();
        let res: Vec<Position> = {
            use rayon::prelude::*;
            notees
                .clone()
                .into_par_iter()
                .map(|t| {
                    let k = t - notees.start;
                    let ep = Entree::depuis(&fp[k * nv..(k + 1) * nv], n);
                    let eq = Entree::depuis(&fq[k * nv..(k + 1) * nv], n);
                    position_decodee(&ep, &eq, n, jet[t + 1] as usize)
                })
                .collect()
        };
        for (k, r) in res.iter().enumerate() {
            csv.push_str(&format!("{c},{},{:.9e},{},{:.6},{:.6},{:.6e},{},{}\n", notees.start + k, r.kl, r.meme_premier as u8, r.nll_q, r.nll_p, r.dp, r.premier_p, r.premier_q));
        }
        toutes.extend(res);
    }
    let resume = resumer(&toutes);
    let j = json!({
        "outil": "juge kl",
        "commande": brut,
        "fin_unix": maintenant(),
        "duree_s": t0.elapsed().as_secs_f64(),
        "fenetres": n_fen,
        "resume": resume,
    });
    let texte = serde_json::to_string_pretty(&j)?;
    println!("{texte}");
    if let Ok(chemin) = args.chemin("json") {
        std::fs::write(chemin, &texte)?;
    }
    if let Ok(chemin) = args.chemin("csv") {
        std::fs::File::create(chemin)?.write_all(csv.as_bytes())?;
    }
    Ok(())
}

/// Le jugement C4 (ARCHITECTURE.md § 7.1) : deux moteurs A (la base, llama.cpp carte) et B (le
/// moteur jugé, troncons) comparés **à la même vérité V** (la référence f64), **sur les mêmes
/// positions**, chacun passé par le même codage de 16 bits par logit (les trois sont des `.kld`).
///
/// Par position i : kl_X(i) = KL(V ‖ X) (V en base, X décodé de son codage), t_X(i) = [argmax X =
/// argmax V] ; sens inverse KL(X ‖ V) relevé aussi (la notation « KL(troncons ‖ référence) » du
/// § 7.1 se lit dans les deux sens ; voir REPRISE-R, besoin porté à l'arbitre). Différences
/// appariées d(i) = kl_B(i) − kl_A(i) et e(i) = t_B(i) − t_A(i) ; leur écart-type de la moyenne
/// √(Var(d)/(n − 1)) est celui de la différence, plus petit que la somme des deux incertitudes
/// quand A et B se trompent aux mêmes endroits (dérivation dans R-pour-le-memoire.md § 2.5).
///
/// Verdicts (déclarés avant tout usage, 2026-10-15) :
/// - **littéral** (le texte du § 7.1) : moyenne de kl_B ≤ moyenne de kl_A, et taux t_B ≥ taux t_A ;
/// - **statistique** (proposé à l'arbitre, plus prudent contre le bruit) : d̄ ≤ 2 · σ(d̄) (B pas
///   significativement plus loin de V que A) et ē ≥ −2 · σ(ē) ;
/// - témoin attendu : A = B (même fichier) donne d = e = 0 partout et les quatre verdicts tiennent ;
///   cassure attendue : B d'un modèle faussé (k = 2 experts) fait tomber les quatre.
fn comparer(args: &Args, brut: &[String]) -> Result<()> {
    let t0 = Instant::now();
    let mut v = FichierKld::ouvrir(&args.chemin("verite")?)?;
    let mut a = FichierKld::ouvrir(&args.chemin("a")?)?;
    let mut b = FichierKld::ouvrir(&args.chemin("b")?)?;
    for (nom, f) in [("a", &a), ("b", &b)] {
        if f.n_vocab != v.n_vocab || f.n_ctx != v.n_ctx {
            bail!("--{nom} : n_vocab {}/{}, n_ctx {}/{}", f.n_vocab, v.n_vocab, f.n_ctx, v.n_ctx);
        }
    }
    let n_fen = args.nombre("fenetres", v.n_chunk.min(a.n_chunk).min(b.n_chunk))?.min(v.n_chunk.min(a.n_chunk).min(b.n_chunk));
    for c in 0..n_fen {
        if v.jetons_fenetre(c) != a.jetons_fenetre(c) || v.jetons_fenetre(c) != b.jetons_fenetre(c) {
            bail!("fenêtre {c} : les jetons diffèrent entre les trois fichiers");
        }
    }
    let (n, nv, n_ctx) = (v.n_vocab, mots_par_entree(v.n_vocab), v.n_ctx);
    let notees = positions_notees(n_ctx);
    // (kl_a, kl_b, t_a, t_b, kl_inverse_a, kl_inverse_b) par position.
    let mut lignes: Vec<(usize, usize, Position, Position, f64, f64)> = Vec::new();
    for c in 0..n_fen {
        let (fv, fa, fb) = (v.fenetre(c)?, a.fenetre(c)?, b.fenetre(c)?);
        let jet = v.jetons_fenetre(c).to_vec();
        let res: Vec<(usize, usize, Position, Position, f64, f64)> = {
            use rayon::prelude::*;
            notees
                .clone()
                .into_par_iter()
                .map(|t| {
                    let k = t - notees.start;
                    let ev = Entree::depuis(&fv[k * nv..(k + 1) * nv], n);
                    let ea = Entree::depuis(&fa[k * nv..(k + 1) * nv], n);
                    let eb = Entree::depuis(&fb[k * nv..(k + 1) * nv], n);
                    let suivant = jet[t + 1] as usize;
                    let pa = position_decodee(&ev, &ea, n, suivant);
                    let pb = position_decodee(&ev, &eb, n, suivant);
                    let ia = position_decodee(&ea, &ev, n, suivant).kl;
                    let ib = position_decodee(&eb, &ev, n, suivant).kl;
                    (c, t, pa, pb, ia, ib)
                })
                .collect()
        };
        lignes.extend(res);
    }
    let m = lignes.len() as f64;
    let apparie = |f: &dyn Fn(&(usize, usize, Position, Position, f64, f64)) -> f64| -> (f64, f64) {
        let s: f64 = lignes.iter().map(f).sum();
        let s2: f64 = lignes.iter().map(|l| f(l) * f(l)).sum();
        let moy = s / m;
        let var = (s2 / m - moy * moy).max(0.0);
        (moy, (var / (m - 1.0)).sqrt())
    };
    let (d_kl, sd_kl) = apparie(&|l| l.3.kl - l.2.kl);
    let (d_inv, sd_inv) = apparie(&|l| l.5 - l.4);
    let (d_top, sd_top) = apparie(&|l| l.3.meme_premier as u8 as f64 - l.2.meme_premier as u8 as f64);
    let ra = resumer(&lignes.iter().map(|l| l.2).collect::<Vec<_>>());
    let rb = resumer(&lignes.iter().map(|l| l.3).collect::<Vec<_>>());
    let moy = |f: &dyn Fn(&(usize, usize, Position, Position, f64, f64)) -> f64| lignes.iter().map(f).sum::<f64>() / m;
    let (inv_a, inv_b) = (moy(&|l| l.4), moy(&|l| l.5));
    let j = json!({
        "outil": "juge comparer",
        "commande": brut,
        "fin_unix": maintenant(),
        "duree_s": t0.elapsed().as_secs_f64(),
        "fenetres": n_fen,
        "positions": lignes.len(),
        "a_contre_verite": ra,
        "b_contre_verite": rb,
        "kl_inverse": { "a": inv_a, "b": inv_b, "difference": d_inv, "ecart_type": sd_inv },
        "apparie": { "kl_difference_b_moins_a": d_kl, "kl_ecart_type": sd_kl,
                     "premier_difference_b_moins_a": d_top, "premier_ecart_type": sd_top },
        "verdicts": {
            "litteral_kl": rb.kl_moyenne <= ra.kl_moyenne,
            "litteral_premier": rb.meme_premier >= ra.meme_premier,
            "statistique_kl": d_kl <= 2.0 * sd_kl,
            "statistique_premier": d_top >= -2.0 * sd_top,
        },
        "regle": "littéral : KL_B ≤ KL_A et premier_B ≥ premier_A ; statistique : d̄ ≤ 2σ(d̄) et ē ≥ −2σ(ē) (différences appariées, mêmes positions, même vérité)",
    });
    let texte = serde_json::to_string_pretty(&j)?;
    println!("{texte}");
    if let Ok(chemin) = args.chemin("json") {
        std::fs::write(chemin, &texte)?;
    }
    if let Ok(chemin) = args.chemin("csv") {
        let mut csv = String::from("fenetre,position,kl_a,kl_b,premier_a,premier_b,kl_inverse_a,kl_inverse_b\n");
        for (c, t, pa, pb, ia, ib) in &lignes {
            csv.push_str(&format!("{c},{t},{:.9e},{:.9e},{},{},{:.9e},{:.9e}\n", pa.kl, pb.kl, pa.meme_premier as u8, pb.meme_premier as u8, ia, ib));
        }
        std::fs::File::create(chemin)?.write_all(csv.as_bytes())?;
    }
    Ok(())
}

/// Les 32 paires de gpt-oss (base 150 000, facteur 32, L0 = 4 096, β 32 / 1, d = 64) : la rampe
/// et ω_i/θ_i pour la rampe d'OpenAI et pour celle de llama.cpp, par le code même de la référence.
fn rampe(args: &Args) -> Result<()> {
    let o = trc_reference::ops::Rope::yarn(150000.0, 32.0, 4096.0, 32.0, 1.0, 64, VarianteYarn::OpenAi);
    let l = trc_reference::ops::Rope::yarn(150000.0, 32.0, 4096.0, 32.0, 1.0, 64, VarianteYarn::LlamaCpp);
    let mut csv = format!("# bornes openai {:.17e} {:.17e} ; llamacpp {} {}
paire,theta,omega_openai,omega_llamacpp,rapport_openai,rapport_llamacpp,ecart_phase_par_position
", o.bas, o.haut, l.bas, l.haut);
    for i in 0..32 {
        let theta = 150000f64.powf(-((2 * i) as f64) / 64.0);
        csv.push_str(&format!("{i},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}
", theta, o.inv_freq[i], l.inv_freq[i], o.inv_freq[i] / theta, l.inv_freq[i] / theta, l.inv_freq[i] - o.inv_freq[i]));
    }
    print!("{csv}");
    if let Ok(c) = args.chemin("csv") {
        std::fs::write(c, &csv)?;
    }
    Ok(())
}

fn jetons(args: &Args, brut: &[String]) -> Result<()> {
    let j = trc_jetons::Jetons::ouvrir(&args.chemin("dll")?, &args.chemin("vocab")?)?;
    let texte = std::fs::read_to_string(args.chemin("texte")?)?;
    let base = FichierKld::ouvrir(&args.chemin("kld")?)?;
    let t0 = Instant::now();
    let jet = j.decouper(&texte, true);
    let n = base.jetons.len();
    let egal = jet.len() >= n && jet[..n] == base.jetons[..];
    let premier_ecart = (0..n.min(jet.len())).find(|&i| jet[i] != base.jetons[i]);
    let r = json!({
        "outil": "juge jetons",
        "commande": brut,
        "taille_vocab": j.taille_vocab(),
        "ajoute_bos": j.ajoute_bos(),
        "jetons_du_texte": jet.len(),
        "jetons_du_kld": n,
        "egaux": egal,
        "premier_ecart": premier_ecart,
        "duree_s": t0.elapsed().as_secs_f64(),
        "premiers_jetons": jet.iter().take(12).map(|&t| (t, j.texte(t))).collect::<Vec<_>>(),
    });
    println!("{}", serde_json::to_string_pretty(&r)?);
    if !egal {
        bail!("découpage différent de celui de llama-perplexity");
    }
    Ok(())
}

fn temoin_chemins(args: &Args, brut: &[String]) -> Result<()> {
    let gguf = args.chemin("gguf")?;
    let base = FichierKld::ouvrir(&args.chemin("kld")?)?;
    let n = args.nombre("n", 24)?;
    let variante = args.variante()?;
    let seq: Vec<u32> = base.jetons_fenetre(0)[..n].to_vec();
    let t0 = Instant::now();
    // Chemin 2 : par lots, toutes les positions notées.
    let mut r = Reference::ouvrir_variante(&gguf, variante)?;
    let mut lot: Vec<Vec<f64>> = Vec::new();
    r.evaluer(std::slice::from_ref(&seq), &|_, _| true, &mut |_, _, z| { lot.push(z.to_vec()); Ok(()) }, &mut |m| journal_ligne(m))?;
    let t_lot = t0.elapsed().as_secs_f64();
    // Chemin 1 : jeton par jeton (variante opposée si --casser).
    let casser = args.a("casser");
    let v1 = if casser { if variante == VarianteYarn::OpenAi { VarianteYarn::LlamaCpp } else { VarianteYarn::OpenAi } } else { variante };
    let mut r1 = Reference::ouvrir_variante(&gguf, v1)?;
    let mut ecarts_bits = 0usize;
    let mut ecart_max: f64 = 0.0;
    for (t, &jeton) in seq.iter().enumerate() {
        let z = r1.pas(jeton, t as u32)?;
        for (a, b) in z.iter().zip(lot[t].iter()) {
            if a.to_bits() != b.to_bits() {
                ecarts_bits += 1;
                ecart_max = ecart_max.max((a - b).abs());
            }
        }
    }
    let j = json!({
        "outil": "juge temoin-chemins",
        "commande": brut,
        "n": n,
        "variante_lot": format!("{variante:?}"),
        "variante_pas": format!("{v1:?}"),
        "logits_compares": n * r.hyper.vocab,
        "logits_differents_au_bit": ecarts_bits,
        "ecart_absolu_max": ecart_max,
        "duree_lot_s": t_lot,
        "duree_totale_s": t0.elapsed().as_secs_f64(),
        "seuil_declare": "0 logit différent au bit (mêmes opérations, même ordre)",
        "tient": ecarts_bits == 0,
    });
    println!("{}", serde_json::to_string_pretty(&j)?);
    Ok(())
}

/// Témoins des compteurs (R2), seuils déclarés avant le lancement (2026-10-15) :
/// - M (mémoire) : écrire dans N Mio fraîchement alloués fait monter la pointe de l'ensemble de
///   travail d'au moins 0,95 × N ; cassure (`--casser`) : allouer N Mio de zéros **sans y écrire**
///   (pages à zéro à la demande, jamais touchées) ne la fait monter que de moins de 0,10 × N ;
/// - D (disque) : une lecture sans tampon (`FILE_FLAG_NO_BUFFERING`) de N Mio d'un fichier est vue
///   par le compteur PDH à au moins 0,95 × N au-dessus du repos mesuré juste avant (seuil de
///   l'étude 06 § 7.3) ; cassure : la même lecture, mais le compteur n'est recueilli qu'au début et
///   à la fin du repos (fenêtre d'intégration décalée) : la lecture ne doit plus être vue (< 0,10 × N).
fn temoin_compteurs(args: &Args, brut: &[String]) -> Result<()> {
    use std::os::windows::fs::OpenOptionsExt;
    use std::io::Read;
    use trc_juge::compteurs::{CompteurDisque, Processus, repos_disque};
    let mio = args.nombre("mio", 256)?;
    let n = mio << 20;
    let casser = args.a("casser");
    // M : mémoire.
    let p = Processus::courant();
    let avant = p.memoire().ensemble_travail_pointe;
    let mut v: Vec<u8> = vec![0u8; n];
    if !casser {
        for i in (0..n).step_by(4096) {
            v[i] = 1;
        }
    }
    let apres = p.memoire().ensemble_travail_pointe;
    std::hint::black_box(&v);
    drop(v);
    let hausse = apres.saturating_sub(avant) as f64 / n as f64;
    let m_tient = if casser { hausse < 0.10 } else { hausse >= 0.95 };
    // D : disque.
    let chemin = args.chemin("fichier")?;
    let repos = repos_disque(10.0)?;
    let compteur = CompteurDisque::ouvrir()?;
    std::thread::sleep(std::time::Duration::from_millis(500));
    compteur.debit();
    let t0 = Instant::now();
    let mut f = std::fs::OpenOptions::new().read(true).custom_flags(0x2000_0000).open(&chemin)?;
    let disposition = std::alloc::Layout::from_size_align(1 << 22, 4096)?;
    // SAFETY : tampon aligné sur 4 096 octets exigé par la lecture sans tampon, libéré plus bas.
    let tampon = unsafe { std::slice::from_raw_parts_mut(std::alloc::alloc(disposition), 1 << 22) };
    let mut lus = 0usize;
    while lus < n {
        let k = f.read(tampon)?;
        if k == 0 {
            break;
        }
        lus += k;
    }
    unsafe { std::alloc::dealloc(tampon.as_mut_ptr(), disposition) };
    let duree = t0.elapsed().as_secs_f64();
    let vu = if casser {
        // Fenêtre décalée : on jette le recueil qui couvre la lecture, puis on intègre un repos de même durée.
        compteur.debit();
        std::thread::sleep(std::time::Duration::from_secs_f64(duree.max(0.5)));
        compteur.debit() * duree.max(0.5)
    } else {
        compteur.debit() * duree
    };
    let net = vu - repos * duree.max(0.5);
    let part = net / lus as f64;
    let d_tient = if casser { part < 0.10 } else { part >= 0.95 };
    let j = json!({
        "outil": "juge temoin-compteurs",
        "commande": brut,
        "casser": casser,
        "memoire": { "mio": mio, "hausse_pointe_relative": hausse, "tient": m_tient },
        "disque": { "octets_lus": lus, "duree_s": duree, "repos_octets_s": repos, "vus_bruts": vu, "vus_nets": net, "part_vue": part, "tient": d_tient },
    });
    println!("{}", serde_json::to_string_pretty(&j)?);
    Ok(())
}
