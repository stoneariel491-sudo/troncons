//! La sonde de l'étude genome/predictif-elagage, sur la référence f64 de troncons (trc-reference).
//!
//! sonde capture --gguf G --jetons-de B.kld --fenetres N --couches 0,8,16,23 --sortie DOSSIER [--fils F]
//!     Passe avant exacte ; pour chaque couche demandée, écrit `entrees-L.bin` : les entrées réelles
//!     de chaque expert (l'état normé après l'attention des positions routées vers lui).
//!     Format : b"ENTR", u32 couche, u32 d_modele, u32 experts, puis pour chaque expert lu :
//!     u32 e, u32 m, m × u32 positions aplaties, m × d_modele × f32.
//!
//! sonde alterer --gguf G --jetons-de B.kld --fenetres N --plan P.bin --sortie S.kld [--fils F]
//!     Passe avant dont les experts des tenseurs du plan sont remplacés par leur reconstruction
//!     ŵ = T[ctx][code] · 2^(e − 128) (T en grandeurs E2M1 doublées) ; écrit les logits au format
//!     .kld de llama.cpp (jugés ensuite par `juge kl` contre la référence exacte).
//!     Plan : b"PEPL", u32 n ; pour chaque tenseur : u32 couche, u32 rôle (0 gate, 1 up, 2 down),
//!     u32 mode (0 : contexte = δ de ligne ; 1 : contexte = e absolu), i32 a, i32 b, u32 n_col
//!     (1 = pas de classe de colonne), f64 × ((b − a + 1) · n_col · 16), puis si n_col > 1 :
//!     experts × colonnes × u8 (classe de colonne).
//!     ctx = (clamp(x, a, b) − a) · n_col + classe(colonne), x = δ ou e ; δ = e − médiane haute de
//!     la ligne (rang 45 des 90 échelles triées, comme le codeur de 03).
//!
//! Témoin de la chaîne (fait à part) : un plan identité (T = K) doit rendre une KL nulle au bit.

use std::collections::HashMap;
use std::io::Write;
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::Instant;

use anyhow::{Context, Result, bail};
use trc_juge::kld::{EcrivainKld, FichierKld, positions_notees};
use trc_reference::Reference;

struct Args(HashMap<String, String>);

impl Args {
    fn lire(v: &[String]) -> Args {
        let mut m = HashMap::new();
        let mut i = 0;
        while i < v.len() {
            if let Some(c) = v[i].strip_prefix("--") {
                let val = v.get(i + 1).cloned().unwrap_or_default();
                m.insert(c.to_string(), val);
                i += 2;
            } else {
                i += 1;
            }
        }
        Args(m)
    }
    fn chemin(&self, c: &str) -> Result<PathBuf> {
        self.0.get(c).map(PathBuf::from).with_context(|| format!("--{c} manque"))
    }
    fn nombre(&self, c: &str, defaut: usize) -> Result<usize> {
        Ok(match self.0.get(c) {
            Some(v) => v.parse()?,
            None => defaut,
        })
    }
}

fn main() -> Result<()> {
    let brut: Vec<String> = std::env::args().collect();
    if brut.len() < 2 {
        bail!("usage : sonde <capture|alterer> …");
    }
    let args = Args::lire(&brut[2..]);
    rayon::ThreadPoolBuilder::new().num_threads(args.nombre("fils", 4)?).build_global()?;
    match brut[1].as_str() {
        "capture" => capture(&args),
        "alterer" => alterer(&args),
        c => bail!("sous-commande inconnue : {c}"),
    }
}

/// Les séquences d'une base .kld, comme `juge reference` : jetons 0 … n_ctx − 2 de chaque fenêtre.
fn sequences(base: &FichierKld, n_fen: usize) -> Vec<Vec<u32>> {
    (0..n_fen).map(|c| base.jetons_fenetre(c)[..base.n_ctx - 1].to_vec()).collect()
}

fn capture(args: &Args) -> Result<()> {
    let t0 = Instant::now();
    let base = FichierKld::ouvrir(&args.chemin("jetons-de")?)?;
    let n_fen = args.nombre("fenetres", base.n_chunk)?.min(base.n_chunk);
    let couches: Vec<usize> = args.0.get("couches").context("--couches manque")?.split(',').map(|s| s.parse()).collect::<Result<_, _>>()?;
    let dossier = args.chemin("sortie")?;
    std::fs::create_dir_all(&dossier)?;
    let mut r = Reference::ouvrir(&args.chemin("gguf")?)?;
    let (d, ne) = (r.hyper.d_modele, r.hyper.experts);
    let mut fichiers = HashMap::new();
    for &l in &couches {
        let mut f = std::io::BufWriter::with_capacity(1 << 22, std::fs::File::create(dossier.join(format!("entrees-{l}.bin")))?);
        f.write_all(b"ENTR")?;
        for v in [l as u32, d as u32, ne as u32] {
            f.write_all(&v.to_le_bytes())?;
        }
        fichiers.insert(l, f);
    }
    let fichiers = std::sync::Arc::new(Mutex::new(fichiers));
    let fc = fichiers.clone();
    r.capture_entrees = Some(Box::new(move |l, e, entrees, positions| {
        let mut g = fc.lock().unwrap();
        if let Some(f) = g.get_mut(&l) {
            let mut o = Vec::with_capacity(8 + positions.len() * 4 + entrees.len() * 4);
            o.extend_from_slice(&(e as u32).to_le_bytes());
            o.extend_from_slice(&(positions.len() as u32).to_le_bytes());
            for &p in positions {
                o.extend_from_slice(&(p as u32).to_le_bytes());
            }
            for &x in entrees {
                o.extend_from_slice(&(x as f32).to_le_bytes());
            }
            f.write_all(&o).expect("écriture des entrées");
        }
    }));
    let seqs = sequences(&base, n_fen);
    let max_couche = *couches.iter().max().unwrap();
    // On ne veut pas de logits : aucune position notée ; on s'arrête après la dernière couche voulue
    // en tronquant le modèle n'est pas possible sans toucher la référence : la passe va au bout.
    let notee = |_s: usize, _t: usize| false;
    let mut rendre = |_s: usize, _t: usize, _z: &[f64]| -> Result<()> { Ok(()) };
    r.evaluer(&seqs, &notee, &mut rendre, &mut |m| eprintln!("{m}"))?;
    let _ = max_couche;
    r.capture_entrees = None;
    let mut g = fichiers.lock().unwrap();
    for (_, f) in g.iter_mut() {
        f.flush()?;
    }
    println!("{{\"outil\": \"sonde capture\", \"fenetres\": {n_fen}, \"couches\": {couches:?}, \"duree_s\": {:.1}}}", t0.elapsed().as_secs_f64());
    Ok(())
}

/// Un tenseur du plan : tables de reconstruction par contexte.
struct PlanTenseur {
    mode: u32,
    dmin: i32,
    dmax: i32,
    n_col: usize,
    table: Vec<f64>,
    colonnes: Vec<u8>,
    /// n_col = 16 : classes de lignes aussi (classe = 4 · ligne + colonne).
    lignes: Vec<u8>,
}

fn lire_plan(chemin: &PathBuf, experts: usize, colonnes: usize) -> Result<HashMap<(usize, usize), PlanTenseur>> {
    let o = std::fs::read(chemin)?;
    if &o[0..4] != b"PEPL" {
        bail!("{} : pas un plan", chemin.display());
    }
    let mut p = 4;
    let u32_ = |p: &mut usize| -> u32 {
        let v = u32::from_le_bytes(o[*p..*p + 4].try_into().unwrap());
        *p += 4;
        v
    };
    let n = u32_(&mut p) as usize;
    let mut plan = HashMap::new();
    for _ in 0..n {
        let couche = u32_(&mut p) as usize;
        let role = u32_(&mut p) as usize;
        let mode = u32_(&mut p);
        let dmin = u32_(&mut p) as i32;
        let dmax = u32_(&mut p) as i32;
        let n_col = u32_(&mut p) as usize;
        let nt = (dmax - dmin + 1) as usize * n_col * 16;
        let table: Vec<f64> = o[p..p + nt * 8].chunks_exact(8).map(|c| f64::from_le_bytes(c.try_into().unwrap())).collect();
        p += nt * 8;
        let cols = if n_col > 1 {
            let v = o[p..p + experts * colonnes].to_vec();
            p += experts * colonnes;
            v
        } else {
            Vec::new()
        };
        // Les matrices d'experts de gpt-oss sont carrées (2 880 × 2 880) : lignes = colonnes.
        let ligs = if n_col == 16 {
            let v = o[p..p + experts * colonnes].to_vec();
            p += experts * colonnes;
            v
        } else {
            Vec::new()
        };
        plan.insert((couche, role), PlanTenseur { mode, dmin, dmax, n_col, table, colonnes: cols, lignes: ligs });
    }
    if p != o.len() {
        bail!("plan : {} octets lus sur {}", p, o.len());
    }
    Ok(plan)
}

/// ŵ d'une matrice MXFP4 d'expert selon son plan.
fn reconstruire(pt: &PlanTenseur, e: usize, octets: &[u8], lignes: usize, colonnes: usize) -> Vec<f32> {
    let nb = colonnes / 32;
    let mut v = vec![0f32; lignes * colonnes];
    let mut ech = vec![0u8; nb];
    for r in 0..lignes {
        let ligne = &octets[r * nb * 17..(r + 1) * nb * 17];
        for b in 0..nb {
            ech[b] = ligne[b * 17];
        }
        let mut tri = ech.clone();
        tri.sort_unstable();
        let med = tri[nb / 2] as i32;
        for b in 0..nb {
            let e8 = ech[b] as i32;
            let x = if pt.mode == 1 { e8 } else { e8 - med };
            let delta = x.clamp(pt.dmin, pt.dmax) - pt.dmin;
            let echelle = (2f64).powi(e8 - 128);
            for i in 0..32 {
                let octet = ligne[b * 17 + 1 + (i % 16)];
                let code = if i < 16 { octet & 15 } else { octet >> 4 } as usize;
                let col = b * 32 + i;
                let cc = if pt.n_col == 16 {
                    pt.lignes[e * lignes + r] as usize * 4 + pt.colonnes[e * colonnes + col] as usize
                } else if pt.n_col > 1 {
                    pt.colonnes[e * colonnes + col] as usize
                } else {
                    0
                };
                let ctx = delta as usize * pt.n_col + cc;
                v[r * colonnes + col] = (pt.table[ctx * 16 + code] * echelle) as f32;
            }
        }
    }
    v
}

fn alterer(args: &Args) -> Result<()> {
    // La KL se calcule ensuite par `juge kl` (lot R), l'instrument commun du projet. Une première
    // version la calculait ici en renormalisant les log-probabilités décodées du .kld ; elle rendait
    // 4,5·10⁻³ pour le plan identité, dont les entrées sont pourtant identiques octet pour octet à
    // la référence (`juge kl` : 0 exactement) : les ~2·10⁵ jetons écrasés sur log p_min reçoivent,
    // une fois renormalisés, une masse qui n'existe pas (R-pour-le-memoire § 2.5). Retirée.
    let t0 = Instant::now();
    let base = FichierKld::ouvrir(&args.chemin("jetons-de")?)?;
    let n_fen = args.nombre("fenetres", base.n_chunk)?.min(base.n_chunk);
    let mut r = Reference::ouvrir(&args.chemin("gguf")?)?;
    let plan = lire_plan(&args.chemin("plan")?, r.hyper.experts, r.hyper.d_modele)?;
    let n_plan = plan.len();
    r.alterer_expert = Some(Box::new(move |l, e, role, octets, lignes, colonnes| {
        plan.get(&(l, role)).map(|pt| reconstruire(pt, e, octets, lignes, colonnes))
    }));
    let n_ctx = base.n_ctx;
    let notees = positions_notees(n_ctx);
    let seqs = sequences(&base, n_fen);
    let jetons: Vec<u32> = base.jetons[..n_fen * n_ctx].to_vec();
    let mut ecrivain = EcrivainKld::creer(&args.chemin("sortie")?, n_ctx, base.n_vocab, &jetons)?;
    let mut rendre = |_s: usize, _t: usize, z: &[f64]| -> Result<()> { ecrivain.ecrire(z) };
    let notee = |_s: usize, t: usize| notees.contains(&t);
    r.evaluer(&seqs, &notee, &mut rendre, &mut |m| eprintln!("{m}"))?;
    let ecrites = ecrivain.entrees_ecrites;
    ecrivain.finir()?;
    println!("{{\"outil\": \"sonde alterer\", \"plan\": {:?}, \"fenetres\": {n_fen}, \"tenseurs_alteres\": {n_plan}, \"entrees_ecrites\": {ecrites}, \"duree_s\": {:.1}}}",
        args.chemin("plan")?.display().to_string(), t0.elapsed().as_secs_f64());
    Ok(())
}
