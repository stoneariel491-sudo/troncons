//! Témoin K3 : les douze noyaux de la passe avant, chacun contre `trc-reference`.
//!
//! Critères déclarés avant tout code de K3 (moteur/REPRISE-K.md, 2026-10-15, 20 h 45) :
//! - poids **réels** lus dans le GGUF d'origine par `trc_reference::gguf` (chemin indépendant du
//!   `.trc`), couches 0 (à fenêtre) et 1 (pleine) ;
//! - entrées réelles : des jetons tirés (graine publiée) passés par les opérations de la référence
//!   en f64 ; **chaque noyau est jugé seul** : son entrée est la sortie f64 de la référence
//!   arrondie en f32, sa référence l'opération de `trc-reference` appliquée en f64 aux mêmes f32 ;
//! - écart e = max_i |y_i − y64_i| / max_i |y64_i| sur le vecteur de sortie de l'appel ; seuils du
//!   § 5.6 ; égalité au bit ou octet pour octet là où le § 5.6 la demande ;
//! - déterminisme : chaque appel est fait deux fois, les deux sorties doivent être égales au bit ;
//! - cassures (`--casser <noyau>`) : une vraie faute plausible injectée dans la référence du seul
//!   noyau visé ; son témoin doit tomber, les onze autres tenir.
//!
//! Le flux d'une couche (ℓ = 0 à fenêtre, ℓ = 1 pleine), pour des positions de test p :
//!   x ← enchâssement (ligne_q8_0) ; h ← RMSNorm (rmsnorm) ; q, k, v (gemv_q8_0) ; rotation
//!   (rope_yarn) ; cache f16 (ecrire_kv) ; attention aux longueurs déclarées (attention) ;
//!   o = a Woᵀ + bo (gemv_q8_0) ; x₁ = x + o (combiner, n = 1) ; h₂ = RMSNorm(x₁) (rmsnorm) ;
//!   logits du routeur (gemv_f32) ; top-4 (routeur_topk) ; experts gate, up (gemv_mxfp4), SwiGLU
//!   (swiglu_oai), down (gemv_mxfp4) ; x₂ = x₁ + Σ g_j s_j (combiner, n = 4) ; puis la sortie du
//!   modèle : RMSNorm (rmsnorm), logits (gemv_q8_0, 201 088 lignes), jeton (argmax).
//! Pour ℓ = 1, l'entrée est l'enchâssement normé et non l'état réel après la couche 0 : les poids,
//! leurs formes et leurs échelles sont réels, les activations plausibles (dit dans le journal).
//!
//! Plus des cas synthétiques : produits exacts au bit sur entiers (Q8_0, f32, MXFP4), égalités du
//! routeur et de l'argmax, combinaison de valeurs tirées.
//!
//! Usage : `temoin-k3 <modele.gguf> <journal.json> <ecarts.csv> [--casser <noyau>] [--sans-synthetique]`,
//! ou `temoin-k3 chaine …` (la passe avant entière, voir `chaine.rs`).

mod chaine;

use std::fmt::Write as _;
use std::path::PathBuf;
use std::time::Instant;

use anyhow::{Context, Result, bail};
use half::f16;
use trc_cuda::{Contexte, Evenement, Flux, HoteEpingle, MemoireCarte, VueCarte, copier_carte_carte, copier_vers_carte, copier_vers_hote};
use trc_noyaux::Noyaux;
use trc_noyaux::abi::{DimsExpert, FENETRE_GPT_OSS, ParamsAttention, ParamsRope};
use trc_reference::gguf::{GGML_F32, GGML_MXFP4, GGML_Q8_0, Gguf};
use trc_reference::ops::{self, Rope, VarianteYarn};
use trc_reference::poids::{Matrice, rangee_f64};

const NOYAUX: [&str; 12] = [
    "gemv_mxfp4", "gemv_q8_0", "gemv_f32", "rmsnorm", "rope_yarn", "ecrire_kv", "attention", "routeur_topk", "swiglu_oai", "combiner",
    "ligne_q8_0", "argmax",
];
const GRAINE: u64 = 0x4B33_2026_1015;

// ---------------------------------------------------------------------------------------- outils

struct Alea(u64);
impl Alea {
    fn suivant(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    fn sous(&mut self, n: u64) -> u64 {
        self.suivant() % n
    }
    /// Entier de [a, b].
    fn entre(&mut self, a: i64, b: i64) -> i64 {
        a + (self.suivant() % ((b - a + 1) as u64)) as i64
    }
    fn reel(&mut self) -> f64 {
        (self.suivant() >> 11) as f64 / (1u64 << 53) as f64
    }
}

fn octets_f32(v: &[f32]) -> Vec<u8> {
    v.iter().flat_map(|x| x.to_le_bytes()).collect()
}
fn f32_depuis(o: &[u8]) -> Vec<f32> {
    o.chunks_exact(4).map(|c| f32::from_le_bytes(c.try_into().unwrap())).collect()
}
fn u32_depuis(o: &[u8]) -> Vec<u32> {
    o.chunks_exact(4).map(|c| u32::from_le_bytes(c.try_into().unwrap())).collect()
}
fn en_f64(v: &[f32]) -> Vec<f64> {
    v.iter().map(|&x| x as f64).collect()
}
fn en_f32(v: &[f64]) -> Vec<f32> {
    v.iter().map(|&x| x as f32).collect()
}

/// e = max|y − r| / max|r| ; un écart non fini compte pour l'infini.
fn ecart(y: &[f32], r: &[f64]) -> f64 {
    assert_eq!(y.len(), r.len());
    let (mut num, mut den) = (0.0f64, 0.0f64);
    for (&a, &b) in y.iter().zip(r) {
        let d = (a as f64 - b).abs();
        if !d.is_finite() {
            return f64::INFINITY;
        }
        num = num.max(d);
        den = den.max(b.abs());
    }
    if den == 0.0 { if num == 0.0 { 0.0 } else { f64::INFINITY } } else { num / den }
}

/// Éléments dont les bits diffèrent.
fn bits_differents(a: &[f32], b: &[f32]) -> u64 {
    assert_eq!(a.len(), b.len());
    a.iter().zip(b).filter(|(x, y)| x.to_bits() != y.to_bits()).count() as u64
}

// ---------------------------------------------------------------------------------------- la carte

struct Carte {
    ctx: Contexte,
    f: Flux,
    k: Noyaux,
    tampon: HoteEpingle,
}

impl Carte {
    fn nouvelle() -> Result<Carte> {
        let ctx = Contexte::nouveau(0)?;
        let f = Flux::nouveau(&ctx, true)?;
        let k = Noyaux::charger(&ctx)?;
        let tampon = HoteEpingle::allouer(&ctx, 32 << 20, false)?;
        Ok(Carte { ctx, f, k, tampon })
    }

    fn allouer(&self, octets: usize) -> Result<MemoireCarte> {
        Ok(MemoireCarte::allouer(&self.ctx, octets.max(4))?)
    }

    fn envoyer(&mut self, o: &[u8]) -> Result<MemoireCarte> {
        let m = self.allouer(o.len())?;
        let t = self.tampon.octets();
        let mut dec = 0;
        while dec < o.len() {
            let n = (o.len() - dec).min(t);
            self.tampon.tranche_mut()[..n].copy_from_slice(&o[dec..dec + n]);
            copier_vers_carte(m.vue(dec, n), &self.tampon, 0, n, &self.f)?;
            self.f.synchroniser()?;
            dec += n;
        }
        Ok(m)
    }

    fn envoyer_f32(&mut self, v: &[f32]) -> Result<MemoireCarte> {
        self.envoyer(&octets_f32(v))
    }

    fn recevoir(&mut self, v: VueCarte) -> Result<Vec<u8>> {
        self.f.synchroniser()?;
        let mut o = vec![0u8; v.octets];
        let t = self.tampon.octets();
        let mut dec = 0;
        while dec < v.octets {
            let n = (v.octets - dec).min(t);
            copier_vers_hote(&mut self.tampon, 0, VueCarte { adresse: v.adresse + dec as u64, octets: n }, &self.f)?;
            self.f.synchroniser()?;
            o[dec..dec + n].copy_from_slice(&self.tampon.tranche()[..n]);
            dec += n;
        }
        Ok(o)
    }

    fn recevoir_f32(&mut self, v: VueCarte) -> Result<Vec<f32>> {
        Ok(f32_depuis(&self.recevoir(v)?))
    }

    /// Lance `quoi` entre deux événements horodatés ; rend sa durée (ms), flux synchronisé.
    fn lancer(&self, quoi: impl FnOnce(&Noyaux, &Flux) -> trc_cuda::Result<()>) -> Result<f32> {
        let a = Evenement::nouveau(&self.ctx, true)?;
        let b = Evenement::nouveau(&self.ctx, true)?;
        a.enregistrer(&self.f)?;
        quoi(&self.k, &self.f)?;
        b.enregistrer(&self.f)?;
        b.attendre()?;
        Ok(b.ms_depuis(&a)?)
    }
}

// ---------------------------------------------------------------------------------------- verdicts

struct Cas {
    noyau: &'static str,
    modele: String,
    couche: i32,
    cas: String,
    mesure: f64,
    seuil: f64,
    /// Égalité exigée (mesure = nombre d'éléments ou d'octets différents, seuil 0).
    exact: bool,
    deterministe: bool,
    ms: f32,
}

impl Cas {
    fn tient(&self) -> bool {
        self.deterministe && if self.exact { self.mesure == 0.0 } else { self.mesure <= self.seuil }
    }
}

struct Juge {
    casser: String,
    cas: Vec<Cas>,
    modele: String,
    couche: i32,
}

impl Juge {
    fn casse(&self, noyau: &str) -> bool {
        self.casser == noyau
    }
    #[allow(clippy::too_many_arguments)]
    fn noter(&mut self, noyau: &'static str, cas: String, mesure: f64, seuil: f64, exact: bool, deterministe: bool, ms: f32) {
        let c = Cas { noyau, modele: self.modele.clone(), couche: self.couche, cas, mesure, seuil, exact, deterministe, ms };
        eprintln!(
            "  {:<13} {:<44} {} {:>11.3e} (seuil {}{:.0e}) {}{}",
            c.noyau,
            c.cas,
            if c.exact { "diff" } else { "e   " },
            c.mesure,
            if c.exact { "= " } else { "≤ " },
            c.seuil,
            if c.tient() { "tient" } else { "TOMBE" },
            if c.deterministe { "" } else { " (NON DÉTERMINISTE)" }
        );
        self.cas.push(c);
    }
}

// ---------------------------------------------------------------------------------------- le modèle

struct Modele {
    g: Gguf,
    nom: String,
    d: usize,
    tetes: usize,
    tetes_kv: usize,
    dt: usize,
    experts: usize,
    actifs: usize,
    vocab: usize,
    eps: f32,
    rope: ParamsRope,
}

impl Modele {
    fn ouvrir(chemin: &std::path::Path) -> Result<Modele> {
        let g = Gguf::ouvrir(chemin)?;
        let p = |c: &str| format!("gpt-oss.{c}");
        let vocab = g.tenseur("token_embd.weight")?.ne[1] as usize;
        let m = Modele {
            nom: chemin.file_name().unwrap().to_string_lossy().into_owned(),
            d: g.entier(&p("embedding_length"))? as usize,
            tetes: g.entier(&p("attention.head_count"))? as usize,
            tetes_kv: g.entier(&p("attention.head_count_kv"))? as usize,
            dt: g.entier(&p("attention.key_length"))? as usize,
            experts: g.entier(&p("expert_count"))? as usize,
            actifs: g.entier(&p("expert_used_count"))? as usize,
            vocab,
            eps: g.reel(&p("attention.layer_norm_rms_epsilon"))? as f32,
            rope: ParamsRope {
                base: g.reel(&p("rope.freq_base"))?,
                facteur: g.reel(&p("rope.scaling.factor"))?,
                ctx_origine: g.entier(&p("rope.scaling.original_context_length"))? as f64,
                beta_rapide: g.reel(&p("rope.scaling.yarn_beta_fast"))?,
                beta_lent: g.reel(&p("rope.scaling.yarn_beta_slow"))?,
                dim_tete: g.entier(&p("attention.key_length"))? as u32,
                variante: 0,
            },
            g,
        };
        if m.dt != 64 || m.tetes != 64 || m.tetes_kv != 8 || m.d != 2880 || g_fenetre(&m)? != FENETRE_GPT_OSS as usize {
            bail!("hyperparamètres inattendus pour gpt-oss : {} {} {} {}", m.d, m.tetes, m.tetes_kv, m.dt);
        }
        Ok(m)
    }

    fn vecteur(&self, nom: &str) -> Result<Vec<f32>> {
        let t = self.g.tenseur(nom)?;
        if t.type_ggml != GGML_F32 {
            bail!("{nom} : type {}", t.type_ggml);
        }
        Ok(f32_depuis(&self.g.lire_tenseur(nom)?))
    }

    /// (octets, matrice f64 de la référence) d'un tenseur 2D.
    fn matrice(&self, nom: &str) -> Result<(Vec<u8>, Matrice)> {
        let t = self.g.tenseur(nom)?.clone();
        let o = self.g.lire_tenseur(nom)?;
        let m = Matrice::nouvelle(t.type_ggml, t.ne[1] as usize, t.ne[0] as usize, o.clone())?;
        Ok((o, m))
    }
}

fn g_fenetre(m: &Modele) -> Result<usize> {
    Ok(m.g.entier("gpt-oss.attention.sliding_window")? as usize)
}

/// y64 = W x (+ b) par la référence, pour n vecteurs.
fn produit(w: &Matrice, x: &[f64], n: usize, b: Option<&[f32]>) -> Vec<f64> {
    let mut y = vec![0.0; n * w.lignes];
    w.produit(x, n, &mut y);
    if let Some(b) = b {
        for p in 0..n {
            for r in 0..w.lignes {
                y[p * w.lignes + r] += b[r] as f64;
            }
        }
    }
    y
}

fn rmsnorm64(x: &[f32], w: &[f32], eps: f32, casse: bool) -> Vec<f64> {
    let (x, w) = (en_f64(x), en_f64(w));
    let mut y = vec![0.0; x.len()];
    if casse {
        // Faute injectée : la moyenne divisée par n − 1.
        let s: f64 = x.iter().map(|v| v * v).sum();
        let r = 1.0 / (s / (x.len() - 1) as f64 + eps as f64).sqrt();
        for i in 0..x.len() {
            y[i] = x[i] * r * w[i];
        }
    } else {
        ops::rmsnorm(&x, &w, eps as f64, &mut y);
    }
    y
}

fn topk_ref(l: &[f64], k: usize, casse: bool) -> (Vec<usize>, Vec<f64>) {
    if !casse {
        return ops::routeur_topk(l, k);
    }
    // Faute injectée : égalité départagée au plus grand indice.
    let mut idx: Vec<usize> = (0..l.len()).collect();
    idx.sort_by(|&a, &b| l[b].partial_cmp(&l[a]).unwrap().then(b.cmp(&a)));
    idx.truncate(k);
    let m = l[idx[0]];
    let e: Vec<f64> = idx.iter().map(|&i| (l[i] - m).exp()).collect();
    let z: f64 = e.iter().sum();
    (idx, e.iter().map(|v| v / z).collect())
}

fn argmax_hote(v: &[f32], casse: bool) -> u32 {
    let mut b: Option<(f32, u32)> = None;
    for (i, &x) in v.iter().enumerate() {
        if x.is_nan() {
            continue;
        }
        b = match b {
            None => Some((x, i as u32)),
            Some((bv, bi)) => {
                if x > bv || (x == bv && casse) { Some((x, i as u32)) } else { Some((bv, bi)) }
            }
        };
    }
    b.map_or(u32::MAX, |(_, i)| i)
}

/// f16 arrondi vers zéro (faute injectée pour ecrire_kv).
fn f16_vers_zero(x: f32) -> u16 {
    let h = f16::from_f32(x);
    if h.is_finite() && h.to_f32().abs() > x.abs() { h.to_bits() - 1 } else { h.to_bits() }
}

/// L'emplacement SoA (§ 5.6) d'un expert, depuis ses tranches du GGUF.
fn emplacement(tranches: &[Vec<u8>; 3], biais: &[Vec<f32>; 3]) -> Vec<u8> {
    let dims = DimsExpert::GPT_OSS;
    let mut o = vec![0u8; dims.taille_emplacement() as usize];
    for j in 0..3 {
        let d = dims.disposition(j);
        let (base, ech, bia) = (d.base as usize, d.echelles as usize, d.biais as usize);
        for beta in 0..dims.blocs(j) as usize {
            let b = &tranches[j][beta * 17..beta * 17 + 17];
            o[base + ech + beta] = b[0];
            o[base + 16 * beta..base + 16 * beta + 16].copy_from_slice(&b[1..17]);
        }
        for (r, v) in biais[j].iter().enumerate() {
            o[base + bia + 4 * r..base + bia + 4 * r + 4].copy_from_slice(&v.to_le_bytes());
        }
    }
    o
}

// ---------------------------------------------------------------------------------------- les cas

/// Les cas d'un modèle. `etats` reçoit les x₂ (f32) des positions de la couche 1, pour la sortie.
fn juger_modele(c: &mut Carte, j: &mut Juge, m: &Modele, alea: &mut Alea, journal: &mut String) -> Result<()> {
    j.modele = m.nom.clone();
    let (d, dt, tq, tk) = (m.d, m.dt, m.tetes, m.tetes_kv);
    let (dq, dkv) = (tq * dt, tk * dt);
    let t0 = Instant::now();

    // ------------------------------------------------ enchâssement : ligne_q8_0
    j.couche = -1;
    let emb = m.g.tenseur("token_embd.weight")?.clone();
    if emb.type_ggml != GGML_Q8_0 {
        bail!("token_embd : type {}", emb.type_ggml);
    }
    let emb_o = m.g.lire_tenseur("token_embd.weight")?;
    let ol = (d / 32) * 34;
    let ligne64 = |t: usize| -> Vec<f64> {
        let mut v = vec![0.0; d];
        rangee_f64(GGML_Q8_0, &emb_o[t * ol..(t + 1) * ol], &mut v);
        v
    };
    let n_max = 4096usize;
    let jetons: Vec<usize> = (0..n_max).map(|_| alea.sous(m.vocab as u64) as usize).collect();
    let x32: Vec<Vec<f32>> = jetons.iter().map(|&t| en_f32(&ligne64(t))).collect();
    {
        let carte_emb = c.envoyer(&emb_o)?;
        let y = c.allouer(4 * d)?;
        let y2 = c.allouer(4 * d)?;
        let mut faux = 0u64;
        let mut determ = true;
        let mut ms = 0.0;
        let mut essais: Vec<usize> = jetons[..62].to_vec();
        essais.push(0);
        essais.push(m.vocab - 1);
        for &t in &essais {
            ms = c.lancer(|k, f| k.ligne_q8_0(carte_emb.tout(), t as u32, d as u32, y.vue(0, 4 * d), f))?;
            c.lancer(|k, f| k.ligne_q8_0(carte_emb.tout(), t as u32, d as u32, y2.vue(0, 4 * d), f))?;
            let a = c.recevoir_f32(y.vue(0, 4 * d))?;
            let b = c.recevoir_f32(y2.vue(0, 4 * d))?;
            determ &= bits_differents(&a, &b) == 0;
            let tr = if j.casse("ligne_q8_0") { (t + 1) % m.vocab } else { t };
            faux += bits_differents(&a, &en_f32(&ligne64(tr)));
        }
        j.noter("ligne_q8_0", format!("{} lignes réelles (dont 0 et {})", essais.len(), m.vocab - 1), faux as f64, 0.0, true, determ, ms);
    }
    let _ = writeln!(journal, "{} : enchâssement lu et jugé en {:.1} s", m.nom, t0.elapsed().as_secs_f64());

    // états x₂ de la couche 1 (pour la sortie du modèle)
    let mut etats_sortie: Vec<Vec<f32>> = Vec::new();

    for couche in 0..2usize {
        j.couche = couche as i32;
        let fen = couche % 2 == 0;
        let n = if fen { 300 } else { 4096 };
        let nl = |s: &str| format!("blk.{couche}.{s}");
        let w_attn = m.vecteur(&nl("attn_norm.weight"))?;
        let w_post = m.vecteur(&nl("post_attention_norm.weight"))?;
        let puits = m.vecteur(&nl("attn_sinks.weight"))?;
        let (oq, wq) = m.matrice(&nl("attn_q.weight"))?;
        let (ok_, wk) = m.matrice(&nl("attn_k.weight"))?;
        let (ov, wv) = m.matrice(&nl("attn_v.weight"))?;
        let (oo, wo) = m.matrice(&nl("attn_output.weight"))?;
        let (or, wr) = m.matrice(&nl("ffn_gate_inp.weight"))?;
        let (bq, bk, bv, bo, br) = (
            m.vecteur(&nl("attn_q.bias"))?,
            m.vecteur(&nl("attn_k.bias"))?,
            m.vecteur(&nl("attn_v.bias"))?,
            m.vecteur(&nl("attn_output.bias"))?,
            m.vecteur(&nl("ffn_gate_inp.bias"))?,
        );
        if wq.type_ggml != GGML_Q8_0 || wo.type_ggml != GGML_Q8_0 || wr.type_ggml != GGML_F32 {
            bail!("couche {couche} : types {} {} {}", wq.type_ggml, wo.type_ggml, wr.type_ggml);
        }
        let carte_wq = c.envoyer(&oq)?;
        let carte_wk = c.envoyer(&ok_)?;
        let carte_wv = c.envoyer(&ov)?;
        let carte_wo = c.envoyer(&oo)?;
        let carte_wr = c.envoyer(&or)?;
        let (cbq, cbk, cbv, cbo, cbr) = (c.envoyer_f32(&bq)?, c.envoyer_f32(&bk)?, c.envoyer_f32(&bv)?, c.envoyer_f32(&bo)?, c.envoyer_f32(&br)?);
        let (cw_attn, cw_post, cpuits) = (c.envoyer_f32(&w_attn)?, c.envoyer_f32(&w_post)?, c.envoyer_f32(&puits)?);

        // ------------------------------------------------ rmsnorm (attn_norm), 64 lignes en un appel
        {
            let lignes = 64usize;
            let x: Vec<f32> = x32[..lignes].concat();
            let cx = c.envoyer_f32(&x)?;
            let cy = c.allouer(4 * d * lignes)?;
            let cy2 = c.allouer(4 * d * lignes)?;
            let ms = c.lancer(|k, f| k.rmsnorm(cx.tout(), cw_attn.tout(), cy.tout(), d as u32, lignes as u32, m.eps, f))?;
            c.lancer(|k, f| k.rmsnorm(cx.tout(), cw_attn.tout(), cy2.tout(), d as u32, lignes as u32, m.eps, f))?;
            let y = c.recevoir_f32(cy.tout())?;
            let determ = bits_differents(&y, &c.recevoir_f32(cy2.tout())?) == 0;
            let mut e = 0.0f64;
            for l in 0..lignes {
                e = e.max(ecart(&y[l * d..(l + 1) * d], &rmsnorm64(&x32[l], &w_attn, m.eps, j.casse("rmsnorm"))));
            }
            j.noter("rmsnorm", format!("attn_norm, {lignes} lignes, un appel"), e, 1e-6, false, determ, ms);
            // en place
            c.lancer(|k, f| k.rmsnorm(cx.tout(), cw_attn.tout(), cx.tout(), d as u32, lignes as u32, m.eps, f))?;
            let yp = c.recevoir_f32(cx.tout())?;
            j.noter("rmsnorm", "attn_norm, en place, égal au bit à l'appel hors place".into(), bits_differents(&yp, &y) as f64, 0.0, true, true, 0.0);
        }

        // ------------------------------------------------ h = RMSNorm(x) en f64 (référence), puis f32
        let h32: Vec<Vec<f32>> = (0..n).map(|p| en_f32(&rmsnorm64(&x32[p], &w_attn, m.eps, false))).collect();
        let h64: Vec<f64> = h32.iter().flat_map(|v| en_f64(v)).collect();

        // ------------------------------------------------ gemv_q8_0 : q, k, v sur 8 positions
        let positions_gemv: Vec<usize> = vec![0, 1, 2, 3, n / 2, n - 3, n - 2, n - 1];
        {
            let cy = c.allouer(4 * dq)?;
            let cy2 = c.allouer(4 * dq)?;
            for (nom, w, ow, b, cb, lignes) in [
                ("q", &wq, &carte_wq, &bq, &cbq, dq),
                ("k", &wk, &carte_wk, &bk, &cbk, dkv),
                ("v", &wv, &carte_wv, &bv, &cbv, dkv),
            ] {
                let (mut e, mut determ, mut ms) = (0.0f64, true, 0.0f32);
                for &p in &positions_gemv {
                    let cxv = c.envoyer_f32(&h32[p])?;
                    let ms1 = c.lancer(|k, f| k.gemv_q8_0(ow.tout(), cxv.tout(), Some(cb.tout()), cy.vue(0, 4 * lignes), lignes as u32, d as u32, f))?;
                    c.lancer(|k, f| k.gemv_q8_0(ow.tout(), cxv.tout(), Some(cb.tout()), cy2.vue(0, 4 * lignes), lignes as u32, d as u32, f))?;
                    ms = ms.max(ms1);
                    let y = c.recevoir_f32(cy.vue(0, 4 * lignes))?;
                    determ &= bits_differents(&y, &c.recevoir_f32(cy2.vue(0, 4 * lignes))?) == 0;
                    let r = produit(w, &h64[p * d..(p + 1) * d], 1, if j.casse("gemv_q8_0") { None } else { Some(b) });
                    e = e.max(ecart(&y, &r));
                }
                j.noter("gemv_q8_0", format!("attn_{nom} {lignes} × {d} + biais, 8 positions"), e, 1e-5, false, determ, ms);
            }
        }

        // ------------------------------------------------ q, k, v de la référence (f64) pour toutes les positions
        let kraw = produit(&wk, &h64, n, Some(&bk));
        let vraw = produit(&wv, &h64, n, Some(&bv));
        let rope_ref = Rope::yarn(m.rope.base, m.rope.facteur, m.rope.ctx_origine, m.rope.beta_rapide, m.rope.beta_lent, dt, VarianteYarn::OpenAi);
        // k tourné (f64 → f32 → f16), v (f32 → f16) : le cache tel que les noyaux l'écriraient
        let mut k32 = vec![0f32; n * dkv];
        let mut v32 = vec![0f32; n * dkv];
        for p in 0..n {
            let mut kp = en_f64(&en_f32(&kraw[p * dkv..(p + 1) * dkv]));
            for t in kp.chunks_mut(dt) {
                rope_ref.tourner(t, p);
            }
            k32[p * dkv..(p + 1) * dkv].copy_from_slice(&en_f32(&kp));
            v32[p * dkv..(p + 1) * dkv].copy_from_slice(&en_f32(&vraw[p * dkv..(p + 1) * dkv]));
        }
        let k16: Vec<u16> = k32.iter().map(|&x| f16::from_f32(x).to_bits()).collect();
        let v16: Vec<u16> = v32.iter().map(|&x| f16::from_f32(x).to_bits()).collect();

        // ------------------------------------------------ rope_yarn : positions de 0 à 131 071
        {
            let qraw = produit(&wq, &h64[..10 * d], 10, Some(&bq));
            let pos_rope: [u32; 10] = [0, 1, 7, 127, 128, 1000, 4095, 4096, 65535, 131071];
            for variante in [0u32, 1] {
                let mut rp = m.rope;
                rp.variante = variante;
                let mut rr = Rope::yarn(m.rope.base, m.rope.facteur, m.rope.ctx_origine, m.rope.beta_rapide, m.rope.beta_lent, dt, if variante == 0 { VarianteYarn::OpenAi } else { VarianteYarn::LlamaCpp });
                if j.casse("rope_yarn") {
                    rr.concentration = 1.0; // faute injectée : YaRN sans son échelle d'attention
                }
                let (mut e, mut determ, mut ms) = (0.0f64, true, 0.0f32);
                for (i, &pos) in pos_rope.iter().enumerate() {
                    let q = en_f32(&qraw[i * dq..(i + 1) * dq]);
                    let k = en_f32(&kraw[i * dkv..(i + 1) * dkv]);
                    let (cq, ck) = (c.envoyer_f32(&q)?, c.envoyer_f32(&k)?);
                    let (cq2, ck2) = (c.envoyer_f32(&q)?, c.envoyer_f32(&k)?);
                    ms = ms.max(c.lancer(|kk, f| kk.rope_yarn(cq.tout(), ck.tout(), tq as u32, tk as u32, pos, &rp, f))?);
                    c.lancer(|kk, f| kk.rope_yarn(cq2.tout(), ck2.tout(), tq as u32, tk as u32, pos, &rp, f))?;
                    let mut y = c.recevoir_f32(cq.tout())?;
                    y.extend(c.recevoir_f32(ck.tout())?);
                    let mut y2 = c.recevoir_f32(cq2.tout())?;
                    y2.extend(c.recevoir_f32(ck2.tout())?);
                    determ &= bits_differents(&y, &y2) == 0;
                    let mut r = en_f64(&q);
                    r.extend(en_f64(&k));
                    for t in r.chunks_mut(dt) {
                        rr.tourner(t, pos as usize);
                    }
                    e = e.max(ecart(&y, &r));
                }
                j.noter("rope_yarn", format!("q et k, 10 positions de 0 à 131071, {}", if variante == 0 { "OpenAI" } else { "llama.cpp" }), e, 1e-6, false, determ, ms);
            }
        }

        // ------------------------------------------------ ecrire_kv : 256 positions, cases pleines puis anneau
        {
            let cases = 256usize.min(n);
            for anneau in [0u32, FENETRE_GPT_OSS] {
                let nc = if anneau > 0 { anneau as usize } else { cases };
                let ck_cache = c.allouer(2 * nc * dkv)?;
                let cv_cache = c.allouer(2 * nc * dkv)?;
                let ck_cache2 = c.allouer(2 * nc * dkv)?;
                let cv_cache2 = c.allouer(2 * nc * dkv)?;
                let mut ms = 0.0f32;
                for p in 0..cases {
                    let (ck, cv) = (c.envoyer_f32(&k32[p * dkv..(p + 1) * dkv])?, c.envoyer_f32(&v32[p * dkv..(p + 1) * dkv])?);
                    let case = ParamsAttention::case(p as u32, anneau);
                    ms = ms.max(c.lancer(|k, f| k.ecrire_kv(ck.tout(), cv.tout(), ck_cache.tout(), cv_cache.tout(), dkv as u32, case, f))?);
                    c.lancer(|k, f| k.ecrire_kv(ck.tout(), cv.tout(), ck_cache2.tout(), cv_cache2.tout(), dkv as u32, case, f))?;
                }
                let kk = c.recevoir(ck_cache.tout())?;
                let vv = c.recevoir(cv_cache.tout())?;
                let determ = kk == c.recevoir(ck_cache2.tout())? && vv == c.recevoir(cv_cache2.tout())?;
                let mut faux = 0u64;
                for slot in 0..nc {
                    // dernière position écrite dans cette case
                    let p = if anneau > 0 { (0..cases).rev().find(|&p| p % nc == slot).unwrap() } else { slot };
                    for i in 0..dkv {
                        let (a, b) = (k32[p * dkv + i], v32[p * dkv + i]);
                        let (ra, rb) = if j.casse("ecrire_kv") { (f16_vers_zero(a), f16_vers_zero(b)) } else { (f16::from_f32(a).to_bits(), f16::from_f32(b).to_bits()) };
                        let o = 2 * (slot * dkv + i);
                        faux += (u16::from_le_bytes([kk[o], kk[o + 1]]) != ra) as u64 + (u16::from_le_bytes([vv[o], vv[o + 1]]) != rb) as u64;
                    }
                }
                j.noter("ecrire_kv", format!("{cases} positions, {}", if anneau > 0 { "anneau de 128" } else { "cases pleines" }), faux as f64, 0.0, true, determ, ms);
            }
        }

        // ------------------------------------------------ attention, puis tout ce qui suit, par position de test
        let longueurs: Vec<usize> = if fen { vec![1, 127, 128, 129, 300] } else { vec![1, 300, 4096] };
        let cache_plein = if fen { None } else { Some((c.envoyer(&k16.iter().flat_map(|x| x.to_le_bytes()).collect::<Vec<u8>>())?, c.envoyer(&v16.iter().flat_map(|x| x.to_le_bytes()).collect::<Vec<u8>>())?)) };
        for &lg in &longueurs {
            let p = lg - 1;
            let pa = ParamsAttention::gpt_oss(p as u32, if fen { FENETRE_GPT_OSS } else { 0 });
            // q de la position p, tourné par la référence
            let mut q = en_f64(&en_f32(&produit(&wq, &h64[p * d..(p + 1) * d], 1, Some(&bq))));
            for t in q.chunks_mut(dt) {
                rope_ref.tourner(t, p);
            }
            let q32 = en_f32(&q);
            let (ck_c, cv_c) = match &cache_plein {
                Some(_) => (None, None),
                None => {
                    // l'anneau tel qu'après l'écriture des positions 0..=p dans l'ordre
                    let mut ak = vec![0u16; 128 * dkv];
                    let mut av = vec![0u16; 128 * dkv];
                    for jj in 0..=p {
                        let s = jj % 128;
                        ak[s * dkv..(s + 1) * dkv].copy_from_slice(&k16[jj * dkv..(jj + 1) * dkv]);
                        av[s * dkv..(s + 1) * dkv].copy_from_slice(&v16[jj * dkv..(jj + 1) * dkv]);
                    }
                    (
                        Some(c.envoyer(&ak.iter().flat_map(|x| x.to_le_bytes()).collect::<Vec<u8>>())?),
                        Some(c.envoyer(&av.iter().flat_map(|x| x.to_le_bytes()).collect::<Vec<u8>>())?),
                    )
                }
            };
            let (vk, vv) = match &cache_plein {
                Some((a, b)) => (a.tout(), b.tout()),
                None => (ck_c.as_ref().unwrap().tout(), cv_c.as_ref().unwrap().tout()),
            };
            let cq = c.envoyer_f32(&q32)?;
            let (cs, cs2) = (c.allouer(4 * dq)?, c.allouer(4 * dq)?);
            let ms = c.lancer(|k, f| k.attention(cq.tout(), vk, vv, cpuits.tout(), cs.vue(0, 4 * dq), &pa, f))?;
            c.lancer(|k, f| k.attention(cq.tout(), vk, vv, cpuits.tout(), cs2.vue(0, 4 * dq), &pa, f))?;
            let a32 = c.recevoir_f32(cs.vue(0, 4 * dq))?;
            let determ = bits_differents(&a32, &c.recevoir_f32(cs2.vue(0, 4 * dq))?) == 0;
            // référence : ops::attention_tete sur les clés f64(f16) de [debut, fin)
            let (deb, fin) = (pa.debut as usize, pa.fin as usize);
            let mut a64 = vec![0.0f64; dq];
            let mut e_tete = 0.0f64;
            for h in 0..tq {
                let hk = h / (tq / tk);
                let mut cles = Vec::with_capacity((fin - deb) * dt);
                let mut vals = Vec::with_capacity((fin - deb) * dt);
                for jj in deb..fin {
                    for t in 0..dt {
                        cles.push(f16::from_bits(k16[jj * dkv + hk * dt + t]).to_f64());
                        vals.push(f16::from_bits(v16[jj * dkv + hk * dt + t]).to_f64());
                    }
                }
                let pu = if j.casse("attention") { f64::NEG_INFINITY } else { puits[h] as f64 };
                let mut sc = Vec::new();
                ops::attention_tete(&q[h * dt..(h + 1) * dt], &cles, &vals, fin - deb, pu, 1.0 / (dt as f64).sqrt(), &mut a64[h * dt..(h + 1) * dt], &mut sc);
                e_tete = e_tete.max(ecart(&a32[h * dt..(h + 1) * dt], &a64[h * dt..(h + 1) * dt]));
            }
            let e = ecart(&a32, &a64).max(e_tete);
            j.noter("attention", format!("{} positions [{deb}, {fin}){}", fin - deb, if fen { ", anneau 128" } else { "" }), e, 1e-5, false, determ, ms);

            // -------------------------------------------- o = a Woᵀ + bo (gemv_q8_0), entrée = la sortie de la référence
            let a_ref32 = en_f32(&a64);
            let ca = c.envoyer_f32(&a_ref32)?;
            let (co, co2) = (c.allouer(4 * d)?, c.allouer(4 * d)?);
            let ms = c.lancer(|k, f| k.gemv_q8_0(carte_wo.tout(), ca.tout(), Some(cbo.tout()), co.tout(), d as u32, dq as u32, f))?;
            c.lancer(|k, f| k.gemv_q8_0(carte_wo.tout(), ca.tout(), Some(cbo.tout()), co2.tout(), d as u32, dq as u32, f))?;
            let o32 = c.recevoir_f32(co.tout())?;
            let determ = bits_differents(&o32, &c.recevoir_f32(co2.tout())?) == 0;
            let o64 = produit(&wo, &en_f64(&a_ref32), 1, if j.casse("gemv_q8_0") { None } else { Some(&bo) });
            j.noter("gemv_q8_0", format!("attn_output {d} × {dq} + biais, position {p}"), ecart(&o32, &o64), 1e-5, false, determ, ms);

            // -------------------------------------------- x₁ = x + o (combiner, n = 1, poids 1)
            let o_ref32 = en_f32(&o64_sans_casse(&wo, &a_ref32, &bo));
            let cx1 = c.envoyer_f32(&x32[p])?;
            let cx1b = c.envoyer_f32(&x32[p])?;
            let co_ref = c.envoyer_f32(&o_ref32)?;
            let ms = c.lancer(|k, f| k.combiner(cx1.tout(), co_ref.tout(), d as u32, None, 1, d as u32, f))?;
            c.lancer(|k, f| k.combiner(cx1b.tout(), co_ref.tout(), d as u32, None, 1, d as u32, f))?;
            let x1_carte = c.recevoir_f32(cx1.tout())?;
            let determ = bits_differents(&x1_carte, &c.recevoir_f32(cx1b.tout())?) == 0;
            let x1_32: Vec<f32> = x32[p].iter().zip(&o_ref32).map(|(a, b)| a + b).collect();
            j.noter("combiner", format!("x + (a Woᵀ + bo), n = 1, position {p}"), bits_differents(&x1_carte, &x1_32) as f64, 0.0, true, determ, ms);

            // -------------------------------------------- h₂ = RMSNorm(x₁) (post_attention_norm)
            let cx = c.envoyer_f32(&x1_32)?;
            let (ch, ch2) = (c.allouer(4 * d)?, c.allouer(4 * d)?);
            let ms = c.lancer(|k, f| k.rmsnorm(cx.tout(), cw_post.tout(), ch.tout(), d as u32, 1, m.eps, f))?;
            c.lancer(|k, f| k.rmsnorm(cx.tout(), cw_post.tout(), ch2.tout(), d as u32, 1, m.eps, f))?;
            let hy = c.recevoir_f32(ch.tout())?;
            let determ = bits_differents(&hy, &c.recevoir_f32(ch2.tout())?) == 0;
            j.noter("rmsnorm", format!("post_attention_norm, position {p}"), ecart(&hy, &rmsnorm64(&x1_32, &w_post, m.eps, j.casse("rmsnorm"))), 1e-6, false, determ, ms);
            let h2_32 = en_f32(&rmsnorm64(&x1_32, &w_post, m.eps, false));

            // -------------------------------------------- routeur : gemv_f32 + biais, puis top-4
            let e = m.experts;
            let ch2v = c.envoyer_f32(&h2_32)?;
            let (cl, cl2) = (c.allouer(4 * e)?, c.allouer(4 * e)?);
            let ms = c.lancer(|k, f| k.gemv_f32(carte_wr.tout(), ch2v.tout(), Some(cbr.tout()), cl.tout(), e as u32, d as u32, f))?;
            c.lancer(|k, f| k.gemv_f32(carte_wr.tout(), ch2v.tout(), Some(cbr.tout()), cl2.tout(), e as u32, d as u32, f))?;
            let lg32 = c.recevoir_f32(cl.tout())?;
            let determ = bits_differents(&lg32, &c.recevoir_f32(cl2.tout())?) == 0;
            let l64 = produit(&wr, &en_f64(&h2_32), 1, if j.casse("gemv_f32") { None } else { Some(&br) });
            j.noter("gemv_f32", format!("routeur {e} × {d} + biais, position {p}"), ecart(&lg32, &l64), 1e-5, false, determ, ms);
            let l_ref64 = produit(&wr, &en_f64(&h2_32), 1, Some(&br));
            let l_ref32 = en_f32(&l_ref64);
            let (choix, poids64) = ops::routeur_topk(&en_f64(&l_ref32), m.actifs);
            juger_topk(c, j, &l_ref32, m.actifs, &format!("logits réels, position {p}"))?;

            // -------------------------------------------- les 4 experts : gate, up, SwiGLU, down
            let mut sorties32 = Vec::with_capacity(m.actifs * d);
            let mut g_ref = Vec::new();
            let mut u_ref = Vec::new();
            let (mut e_gu, mut e_down, mut det_mx, mut ms_mx) = (0.0f64, 0.0f64, true, 0.0f32);
            let mut empls = Vec::new();
            let mut experts_ref = Vec::new();
            for &ex in &choix {
                let mut tranches: [Vec<u8>; 3] = Default::default();
                let mut biais: [Vec<f32>; 3] = Default::default();
                let mut mats = Vec::new();
                for (jm, nom) in ["ffn_gate_exps", "ffn_up_exps", "ffn_down_exps"].iter().enumerate() {
                    let t = m.g.tenseur(&nl(&format!("{nom}.weight")))?.clone();
                    if t.type_ggml != GGML_MXFP4 {
                        bail!("{} : type {}", t.nom, t.type_ggml);
                    }
                    let tr = t.octets / m.experts as u64;
                    tranches[jm] = m.g.lire_plage(t.decalage + ex as u64 * tr, tr)?;
                    let tb = m.g.tenseur(&nl(&format!("{nom}.bias")))?.clone();
                    let nb = tb.ne[0];
                    biais[jm] = f32_depuis(&m.g.lire_plage(tb.decalage + ex as u64 * nb * 4, nb * 4)?);
                    mats.push(Matrice::nouvelle(GGML_MXFP4, t.ne[1] as usize, t.ne[0] as usize, tranches[jm].clone())?);
                }
                empls.push(c.envoyer(&emplacement(&tranches, &biais))?);
                experts_ref.push((mats, biais));
            }
            let dims = DimsExpert::GPT_OSS;
            let vue_mat = |em: &MemoireCarte, jm: usize| {
                let dd = dims.disposition(jm);
                em.vue(dd.base as usize, dd.pas as usize)
            };
            let facteur_casse = if j.casse("gemv_mxfp4") { 2.0 } else { 1.0 }; // faute : 2^(e − 127)
            for (i, (mats, biais)) in experts_ref.iter().enumerate() {
                let (cy, cy2) = (c.allouer(4 * d)?, c.allouer(4 * d)?);
                for jm in 0..2 {
                    let ms1 = c.lancer(|k, f| k.gemv(vue_mat(&empls[i], jm), ch2v.tout(), cy.tout(), d as u32, d as u32, f))?;
                    c.lancer(|k, f| k.gemv(vue_mat(&empls[i], jm), ch2v.tout(), cy2.tout(), d as u32, d as u32, f))?;
                    ms_mx = ms_mx.max(ms1);
                    let y = c.recevoir_f32(cy.tout())?;
                    det_mx &= bits_differents(&y, &c.recevoir_f32(cy2.tout())?) == 0;
                    let r = produit(&mats[jm], &en_f64(&h2_32), 1, Some(&biais[jm]));
                    let rc: Vec<f64> = r.iter().zip(biais[jm].iter()).map(|(v, b)| (v - *b as f64) * facteur_casse + *b as f64).collect();
                    e_gu = e_gu.max(ecart(&y, &rc));
                    if jm == 0 { g_ref.extend(en_f32(&r)) } else { u_ref.extend(en_f32(&r)) }
                }
            }
            j.noter("gemv_mxfp4", format!("gate et up de 4 experts {:?} + biais, position {p}", choix), e_gu, 1e-5, false, det_mx, ms_mx);
            // SwiGLU, les 4 experts en un appel
            let nn = m.actifs * d;
            let (cg, cu) = (c.envoyer_f32(&g_ref)?, c.envoyer_f32(&u_ref)?);
            let (ca, ca2) = (c.allouer(4 * nn)?, c.allouer(4 * nn)?);
            let ms = c.lancer(|k, f| k.swiglu_oai(cg.tout(), cu.tout(), ca.tout(), nn as u32, f))?;
            c.lancer(|k, f| k.swiglu_oai(cg.tout(), cu.tout(), ca2.tout(), nn as u32, f))?;
            let act = c.recevoir_f32(ca.tout())?;
            let determ = bits_differents(&act, &c.recevoir_f32(ca2.tout())?) == 0;
            let act64: Vec<f64> = g_ref
                .iter()
                .zip(&u_ref)
                .map(|(&g, &u)| {
                    if j.casse("swiglu_oai") {
                        let (g, u) = ((g as f64).min(7.0), (u as f64).clamp(-7.0, 7.0));
                        g / (1.0 + (-g).exp()) * (u + 1.0) // faute : α = 1
                    } else {
                        ops::swiglu_oai(g as f64, u as f64)
                    }
                })
                .collect();
            j.noter("swiglu_oai", format!("4 × {d} paires en un appel, position {p}"), ecart(&act, &act64), 1e-6, false, determ, ms);
            let act_ref32: Vec<f32> = g_ref.iter().zip(&u_ref).map(|(&g, &u)| ops::swiglu_oai(g as f64, u as f64) as f32).collect();
            // down
            let (mut e_d, mut det_d, mut ms_d) = (0.0f64, true, 0.0f32);
            for (i, (mats, biais)) in experts_ref.iter().enumerate() {
                let cx = c.envoyer_f32(&act_ref32[i * d..(i + 1) * d])?;
                let (cy, cy2) = (c.allouer(4 * d)?, c.allouer(4 * d)?);
                ms_d = ms_d.max(c.lancer(|k, f| k.gemv(vue_mat(&empls[i], 2), cx.tout(), cy.tout(), d as u32, d as u32, f))?);
                c.lancer(|k, f| k.gemv(vue_mat(&empls[i], 2), cx.tout(), cy2.tout(), d as u32, d as u32, f))?;
                let y = c.recevoir_f32(cy.tout())?;
                det_d &= bits_differents(&y, &c.recevoir_f32(cy2.tout())?) == 0;
                let r = produit(&mats[2], &en_f64(&act_ref32[i * d..(i + 1) * d]), 1, Some(&biais[2]));
                let rc: Vec<f64> = r.iter().zip(biais[2].iter()).map(|(v, b)| (v - *b as f64) * facteur_casse + *b as f64).collect();
                e_d = e_d.max(ecart(&y, &rc));
                sorties32.extend(en_f32(&r));
            }
            e_down = e_down.max(e_d);
            j.noter("gemv_mxfp4", format!("down de 4 experts + biais, position {p}"), e_down, 1e-5, false, det_d, ms_d);

            // -------------------------------------------- x₂ = x₁ + Σ g_j s_j (combiner, n = 4)
            let poids32: Vec<f32> = poids64.iter().map(|&w| w as f32).collect();
            let (cs4, cw4) = (c.envoyer_f32(&sorties32)?, c.envoyer_f32(&poids32)?);
            let (cr, cr2) = (c.envoyer_f32(&x1_32)?, c.envoyer_f32(&x1_32)?);
            let ms = c.lancer(|k, f| k.combiner(cr.tout(), cs4.tout(), d as u32, Some(cw4.tout()), m.actifs as u32, d as u32, f))?;
            c.lancer(|k, f| k.combiner(cr2.tout(), cs4.tout(), d as u32, Some(cw4.tout()), m.actifs as u32, d as u32, f))?;
            let x2 = c.recevoir_f32(cr.tout())?;
            let determ = bits_differents(&x2, &c.recevoir_f32(cr2.tout())?) == 0;
            let x2_hote = combiner_hote(&x1_32, &sorties32, &poids32, d, j.casse("combiner"));
            j.noter("combiner", format!("x₁ + Σ g_j s_j, n = 4, position {p}"), bits_differents(&x2, &x2_hote) as f64, 0.0, true, determ, ms);
            if !fen {
                etats_sortie.push(combiner_hote(&x1_32, &sorties32, &poids32, d, false));
            }
        }
        let _ = writeln!(journal, "{} : couche {couche} jugée ({:.1} s depuis le début)", m.nom, t0.elapsed().as_secs_f64());
    }

    // ------------------------------------------------ sortie du modèle : rmsnorm, gemv_q8_0 (201 088), argmax
    j.couche = -2;
    let w_out_norm = m.vecteur("output_norm.weight")?;
    let (o_out, w_out) = m.matrice("output.weight")?;
    let carte_out = c.envoyer(&o_out)?;
    drop(o_out);
    let cwn = c.envoyer_f32(&w_out_norm)?;
    let v = m.vocab;
    for (i, x2) in etats_sortie.iter().enumerate() {
        let cx = c.envoyer_f32(x2)?;
        let (ch, ch2) = (c.allouer(4 * d)?, c.allouer(4 * d)?);
        let ms = c.lancer(|k, f| k.rmsnorm(cx.tout(), cwn.tout(), ch.tout(), d as u32, 1, m.eps, f))?;
        c.lancer(|k, f| k.rmsnorm(cx.tout(), cwn.tout(), ch2.tout(), d as u32, 1, m.eps, f))?;
        let hy = c.recevoir_f32(ch.tout())?;
        let determ = bits_differents(&hy, &c.recevoir_f32(ch2.tout())?) == 0;
        j.noter("rmsnorm", format!("output_norm, état {i}"), ecart(&hy, &rmsnorm64(x2, &w_out_norm, m.eps, j.casse("rmsnorm"))), 1e-6, false, determ, ms);
        let h32 = en_f32(&rmsnorm64(x2, &w_out_norm, m.eps, false));
        let chv = c.envoyer_f32(&h32)?;
        let (cz, cz2) = (c.allouer(4 * v)?, c.allouer(4 * v)?);
        let ms = c.lancer(|k, f| k.gemv_q8_0(carte_out.tout(), chv.tout(), None, cz.tout(), v as u32, d as u32, f))?;
        c.lancer(|k, f| k.gemv_q8_0(carte_out.tout(), chv.tout(), None, cz2.tout(), v as u32, d as u32, f))?;
        let z = c.recevoir_f32(cz.tout())?;
        let determ = bits_differents(&z, &c.recevoir_f32(cz2.tout())?) == 0;
        let z64 = produit(&w_out, &en_f64(&h32), 1, None);
        // la cassure « biais omis » ne touche pas la sortie (elle n'a pas de biais) : la sortie la
        // subit par un biais fictif de 1 % du plus grand logit, pour que le cas tombe aussi
        let z64c: Vec<f64> = if j.casse("gemv_q8_0") {
            let mx = z64.iter().fold(0.0f64, |a, b| a.max(b.abs()));
            z64.iter().map(|x| x + 0.01 * mx).collect()
        } else {
            z64.clone()
        };
        j.noter("gemv_q8_0", format!("output {v} × {d}, état {i}"), ecart(&z, &z64c), 1e-5, false, determ, ms);
        // argmax de la carte sur les logits de la carte, contre l'hôte sur les mêmes f32
        let (cam, cam2) = (c.allouer(4)?, c.allouer(4)?);
        let ms = c.lancer(|k, f| k.argmax(cz.tout(), v as u32, cam.vue(0, 4), f))?;
        c.lancer(|k, f| k.argmax(cz.tout(), v as u32, cam2.vue(0, 4), f))?;
        let am = u32_depuis(&c.recevoir(cam.vue(0, 4))?)[0];
        let determ_am = am == u32_depuis(&c.recevoir(cam2.vue(0, 4))?)[0];
        let ah = argmax_hote(&z, j.casse("argmax"));
        let a64 = (0..v).max_by(|&a, &b| z64[a].partial_cmp(&z64[b]).unwrap().then(b.cmp(&a))).unwrap();
        j.noter("argmax", format!("logits réels {v}, état {i} (f64 : {a64}, carte : {am})"), (am != ah) as u64 as f64, 0.0, true, determ_am, ms);
    }
    let _ = writeln!(journal, "{} : sortie jugée ({:.1} s depuis le début)", m.nom, t0.elapsed().as_secs_f64());
    Ok(())
}

/// o = a Woᵀ + bo par la référence, toujours sans cassure (l'entrée des cas qui suivent).
fn o64_sans_casse(wo: &Matrice, a: &[f32], bo: &[f32]) -> Vec<f64> {
    produit(wo, &en_f64(a), 1, Some(bo))
}

/// La somme de `combiner` faite sur l'hôte en f32, dans l'ordre du noyau et de trc-reference :
/// s = w₀s₀ ; s = s + w₁s₁ ; … ; x + s. Cassure : ordre inversé.
fn combiner_hote(x: &[f32], sorties: &[f32], poids: &[f32], d: usize, casse: bool) -> Vec<f32> {
    let n = poids.len();
    let ordre: Vec<usize> = if casse { (0..n).rev().collect() } else { (0..n).collect() };
    (0..d)
        .map(|i| {
            let mut s = poids[ordre[0]] * sorties[ordre[0] * d + i];
            for &jj in &ordre[1..] {
                s += poids[jj] * sorties[jj * d + i];
            }
            x[i] + s
        })
        .collect()
}

/// Un cas du routeur : indices égaux, poids à 10⁻⁶, boîte aux lettres projetée égale.
fn juger_topk(c: &mut Carte, j: &mut Juge, logits: &[f32], k: usize, nom: &str) -> Result<()> {
    let e = logits.len();
    let cl = c.envoyer_f32(logits)?;
    let (ci, cp, ci2, cp2) = (c.allouer(4 * k)?, c.allouer(4 * k)?, c.allouer(4 * k)?, c.allouer(4 * k)?);
    let boite = HoteEpingle::allouer(&c.ctx, 4096, true)?;
    let adr = boite.adresse_carte().context("boîte non projetée")?;
    let sequence = 0x5EC0_0000 + e as u32;
    let ms = c.lancer(|kk, f| kk.routeur_topk(cl.tout(), e as u32, k as u32, ci.tout(), cp.tout(), adr, sequence, f))?;
    c.lancer(|kk, f| kk.routeur_topk(cl.tout(), e as u32, k as u32, ci2.tout(), cp2.tout(), 0, 0, f))?;
    let idx = u32_depuis(&c.recevoir(ci.tout())?);
    let pw = c.recevoir_f32(cp.tout())?;
    let determ = idx == u32_depuis(&c.recevoir(ci2.tout())?) && bits_differents(&pw, &c.recevoir_f32(cp2.tout())?) == 0;
    let b = boite.tranche();
    // case de la boîte (protocole E0 c) : mot 0 = séquence, 1 .. k indices, k + 1 .. 2k poids
    let bseq = u32_depuis(&b[..4])[0];
    let bidx = u32_depuis(&b[4..4 + 4 * k]);
    let bp = f32_depuis(&b[4 + 4 * k..4 + 8 * k]);
    let (ri, rp) = topk_ref(&en_f64(logits), k, j.casse("routeur_topk"));
    let faux_idx = idx.iter().zip(&ri).filter(|(a, b)| **a as usize != **b).count() + (bidx != idx) as usize + bits_differents(&bp, &pw) as usize + (bseq != sequence) as usize;
    j.noter("routeur_topk", format!("indices et boîte, {nom}"), faux_idx as f64, 0.0, true, determ, ms);
    j.noter("routeur_topk", format!("poids, {nom}"), ecart(&pw, &rp), 1e-6, false, determ, ms);
    Ok(())
}

// ---------------------------------------------------------------------------------------- synthétiques

fn juger_synthetiques(c: &mut Carte, j: &mut Juge, alea: &mut Alea) -> Result<()> {
    j.modele = "synthetique".into();
    j.couche = -1;
    // gemv_q8_0 exacte au bit sur entiers : d ∈ {2^-2 … 2^1}, q ∈ [−127, 127], x ∈ {−1, 0, 1} ;
    // |Σ| ≤ 90 · 32 · 127 · 2 = 731 520 en multiples de 2^-2 : 22 bits, exact en f32 dans tout ordre.
    for (r, cc) in [(37usize, 96usize), (5, 32), (2880, 2880), (2880, 4096), (513, 2880)] {
        let b = cc / 32;
        let mut o = vec![0u8; r * b * 34];
        for blk in o.chunks_exact_mut(34) {
            let d = f16::from_f32(2f32.powi(alea.entre(-2, 1) as i32));
            blk[0..2].copy_from_slice(&d.to_bits().to_le_bytes());
            for q in &mut blk[2..34] {
                *q = alea.entre(-127, 127) as i8 as u8;
            }
        }
        let x: Vec<f32> = (0..cc).map(|_| alea.entre(-1, 1) as f32).collect();
        let w = Matrice::nouvelle(GGML_Q8_0, r, cc, o.clone())?;
        let mut y64 = vec![0.0; r];
        w.produit(&en_f64(&x), 1, &mut y64);
        let (cw, cx, cy, cy2) = (c.envoyer(&o)?, c.envoyer_f32(&x)?, c.allouer(4 * r)?, c.allouer(4 * r)?);
        let ms = c.lancer(|k, f| k.gemv_q8_0(cw.tout(), cx.tout(), None, cy.tout(), r as u32, cc as u32, f))?;
        c.lancer(|k, f| k.gemv_q8_0(cw.tout(), cx.tout(), None, cy2.tout(), r as u32, cc as u32, f))?;
        let y = c.recevoir_f32(cy.tout())?;
        let determ = bits_differents(&y, &c.recevoir_f32(cy2.tout())?) == 0;
        let mut attendu = en_f32(&y64);
        if j.casse("gemv_q8_0") {
            attendu.iter_mut().for_each(|v| *v += 1.0); // faute : un biais de 1 compté à tort
        }
        j.noter("gemv_q8_0", format!("entiers {r} × {cc}, exact au bit"), bits_differents(&y, &attendu) as f64, 0.0, true, determ, ms);
    }
    // gemv_f32 exacte au bit sur entiers : W, x ∈ [−8, 8] ; |Σ| ≤ 2 880 · 64 = 184 320 : exact.
    for (r, cc) in [(128usize, 2880usize), (32, 2880), (5, 32)] {
        let w: Vec<f32> = (0..r * cc).map(|_| alea.entre(-8, 8) as f32).collect();
        let x: Vec<f32> = (0..cc).map(|_| alea.entre(-8, 8) as f32).collect();
        let b: Vec<f32> = (0..r).map(|_| alea.entre(-100, 100) as f32).collect();
        // cassure : biais omis dans l'attendu
        let attendu: Vec<f32> = (0..r).map(|i| (0..cc).map(|t| w[i * cc + t] as f64 * x[t] as f64).sum::<f64>() as f32 + if j.casse("gemv_f32") { 0.0 } else { b[i] }).collect();
        let (cw, cx, cb, cy, cy2) = (c.envoyer_f32(&w)?, c.envoyer_f32(&x)?, c.envoyer_f32(&b)?, c.allouer(4 * r)?, c.allouer(4 * r)?);
        let ms = c.lancer(|k, f| k.gemv_f32(cw.tout(), cx.tout(), Some(cb.tout()), cy.tout(), r as u32, cc as u32, f))?;
        c.lancer(|k, f| k.gemv_f32(cw.tout(), cx.tout(), Some(cb.tout()), cy2.tout(), r as u32, cc as u32, f))?;
        let y = c.recevoir_f32(cy.tout())?;
        let determ = bits_differents(&y, &c.recevoir_f32(cy2.tout())?) == 0;
        j.noter("gemv_f32", format!("entiers {r} × {cc} + biais entier, exact au bit"), bits_differents(&y, &attendu) as f64, 0.0, true, determ, ms);
    }
    // gemv_mxfp4 exacte au bit sur entiers, contre Matrice::produit de la référence (poids MXFP4
    // lus par rangee_f64) : e ∈ [127, 129], x ∈ [−2, 2] ; |Σ| ≤ 90 · 32 · 12 · 2 · 2 = 138 240 en
    // multiples de 2^-1 : exact.
    {
        let (r, cc) = (2880usize, 2880usize);
        let b = cc / 32;
        let mut gg = vec![0u8; r * b * 17];
        for blk in gg.chunks_exact_mut(17) {
            blk[0] = alea.entre(127, 129) as u8;
            for q in &mut blk[1..17] {
                *q = alea.sous(256) as u8;
            }
        }
        let biais: Vec<f32> = (0..r).map(|_| alea.entre(-50, 50) as f32).collect();
        let x: Vec<f32> = (0..cc).map(|_| alea.entre(-2, 2) as f32).collect();
        let w = Matrice::nouvelle(GGML_MXFP4, r, cc, gg.clone())?;
        let mut y64 = vec![0.0; r];
        w.produit(&en_f64(&x), 1, &mut y64);
        let fac = if j.casse("gemv_mxfp4") { 2.0 } else { 1.0 };
        let attendu: Vec<f32> = (0..r).map(|i| (y64[i] * fac + biais[i] as f64) as f32).collect();
        let tr = [gg.clone(), gg.clone(), gg];
        let bs = [biais.clone(), biais.clone(), biais];
        let em = c.envoyer(&emplacement(&tr, &bs))?;
        let dd = DimsExpert::GPT_OSS.disposition(1);
        let (cx, cy, cy2) = (c.envoyer_f32(&x)?, c.allouer(4 * r)?, c.allouer(4 * r)?);
        let ms = c.lancer(|k, f| k.gemv(em.vue(dd.base as usize, dd.pas as usize), cx.tout(), cy.tout(), r as u32, cc as u32, f))?;
        c.lancer(|k, f| k.gemv(em.vue(dd.base as usize, dd.pas as usize), cx.tout(), cy2.tout(), r as u32, cc as u32, f))?;
        let y = c.recevoir_f32(cy.tout())?;
        let determ = bits_differents(&y, &c.recevoir_f32(cy2.tout())?) == 0;
        j.noter("gemv_mxfp4", "entiers 2880 × 2880 + biais, contre Matrice::produit, exact au bit".into(), bits_differents(&y, &attendu) as f64, 0.0, true, determ, ms);
    }
    // routeur : égalités (score décroissant, puis indice croissant)
    let mut cas: Vec<(Vec<f32>, &str)> = vec![
        (vec![0.0; 128], "128 zéros"),
        ((0..32).map(|i| [1.0f32, 3.0, 3.0, 0.0, 2.0][i % 5]).collect(), "32 valeurs à égalités répétées"),
        ((0..128).map(|i| if i % 37 == 5 { 4.5 } else { -1.0 }).collect(), "128, quatre maxima égaux aux indices 5, 42, 79, 116"),
        ((0..128).map(|i| if i == 127 || i == 64 { 2.0 } else { (i as f32) * 1e-3 }).collect(), "128, maxima égaux aux indices 64 et 127"),
        ((0..256).map(|i| (i % 7) as f32).collect(), "256 experts, 7 valeurs"),
    ];
    let mut tir: Vec<f32> = (0..128).map(|_| (alea.reel() * 8.0 - 4.0) as f32).collect();
    tir[17] = tir[3];
    cas.push((tir, "128 tirés, une égalité forcée"));
    for (l, nom) in &cas {
        juger_topk(c, j, l, 4, nom)?;
    }
    // argmax : égalités, −∞, NaN
    let v = 201_088usize;
    let mut ag: Vec<(Vec<f32>, String)> = Vec::new();
    let mut a: Vec<f32> = (0..v).map(|_| (alea.reel() * 20.0 - 10.0) as f32).collect();
    a[150_000] = 50.0;
    a[7] = 50.0;
    a[200_000] = 50.0;
    ag.push((a, "201 088, trois maxima égaux (7, 150 000, 200 000)".into()));
    ag.push((vec![f32::NEG_INFINITY; v], "201 088 fois −∞".into()));
    let mut b: Vec<f32> = vec![1.0; v];
    b[0] = f32::NAN;
    b[1000] = f32::NAN;
    ag.push((b, "201 088 égaux à 1, NaN en 0 et 1 000".into()));
    let mut cmax: Vec<f32> = (0..v).map(|i| (i % 1000) as f32).collect();
    cmax[v - 1] = 2000.0;
    ag.push((cmax, "maximum seul au dernier indice".into()));
    for (vv, nom) in &ag {
        let cv = c.envoyer_f32(vv)?;
        let (cam, cam2) = (c.allouer(4)?, c.allouer(4)?);
        let ms = c.lancer(|k, f| k.argmax(cv.tout(), v as u32, cam.vue(0, 4), f))?;
        c.lancer(|k, f| k.argmax(cv.tout(), v as u32, cam2.vue(0, 4), f))?;
        let am = u32_depuis(&c.recevoir(cam.vue(0, 4))?)[0];
        let determ = am == u32_depuis(&c.recevoir(cam2.vue(0, 4))?)[0];
        let ah = argmax_hote(vv, j.casse("argmax"));
        j.noter("argmax", format!("{nom} (carte : {am}, hôte : {ah})"), (am != ah) as u64 as f64, 0.0, true, determ, ms);
    }
    // combiner : valeurs tirées sur 25 ordres de grandeur, n = 4 et n = 3 (pas de 3 000)
    for n in [4usize, 3] {
        let d = 2880usize;
        let pas = 3000usize;
        let x: Vec<f32> = (0..d).map(|_| ((alea.reel() - 0.5) * 2f64.powi(alea.entre(-12, 12) as i32)) as f32).collect();
        let mut s = vec![0f32; (n - 1) * pas + d];
        for v in s.iter_mut() {
            *v = ((alea.reel() - 0.5) * 2f64.powi(alea.entre(-12, 12) as i32)) as f32;
        }
        let w: Vec<f32> = (0..n).map(|_| alea.reel() as f32).collect();
        let mut sd = vec![0f32; n * d];
        for jj in 0..n {
            sd[jj * d..(jj + 1) * d].copy_from_slice(&s[jj * pas..jj * pas + d]);
        }
        let attendu = combiner_hote(&x, &sd, &w, d, j.casse("combiner"));
        let (cr, cr2, cs, cw) = (c.envoyer_f32(&x)?, c.envoyer_f32(&x)?, c.envoyer_f32(&s)?, c.envoyer_f32(&w)?);
        let ms = c.lancer(|k, f| k.combiner(cr.tout(), cs.tout(), pas as u32, Some(cw.tout()), n as u32, d as u32, f))?;
        c.lancer(|k, f| k.combiner(cr2.tout(), cs.tout(), pas as u32, Some(cw.tout()), n as u32, d as u32, f))?;
        let y = c.recevoir_f32(cr.tout())?;
        let determ = bits_differents(&y, &c.recevoir_f32(cr2.tout())?) == 0;
        j.noter("combiner", format!("tirés sur 2^±12, n = {n}, pas {pas}"), bits_differents(&y, &attendu) as f64, 0.0, true, determ, ms);
    }
    Ok(())
}

// ---------------------------------------------------------------------------------------- programme

/// Copie carte → carte, flux synchronisé.
fn trc_cuda_copie(c: &Carte, src: VueCarte, dst: VueCarte) -> Result<()> {
    copier_carte_carte(dst, src, &c.f)?;
    c.f.synchroniser()?;
    Ok(())
}

fn main() -> Result<()> {
    let a: Vec<String> = std::env::args().collect();
    if a.get(1).map(String::as_str) == Some("chaine") {
        return chaine::lancer(&a[2..]);
    }
    if a.len() < 4 {
        eprintln!("usage : temoin-k3 <modele.gguf> <journal.json> <ecarts.csv> [--casser <noyau>] [--sans-synthetique]");
        std::process::exit(2);
    }
    let gguf = PathBuf::from(&a[1]);
    let (journal_json, csv) = (PathBuf::from(&a[2]), PathBuf::from(&a[3]));
    let mut casser = String::new();
    let mut synthetique = true;
    let mut i = 4;
    while i < a.len() {
        match a[i].as_str() {
            "--casser" => {
                casser = a.get(i + 1).cloned().unwrap_or_default();
                if !NOYAUX.contains(&casser.as_str()) {
                    bail!("--casser : noyau inconnu « {casser} »");
                }
                i += 1;
            }
            "--sans-synthetique" => synthetique = false,
            x => bail!("option inconnue {x}"),
        }
        i += 1;
    }
    let debut = Instant::now();
    let mut c = Carte::nouvelle()?;
    let mut j = Juge { casser: casser.clone(), cas: Vec::new(), modele: String::new(), couche: 0 };
    let mut alea = Alea(GRAINE);
    let mut journal = String::new();
    eprintln!("carte : {} ; pilote {} ; casser : « {casser} »", c.ctx.nom(), c.ctx.version_pilote());
    if synthetique {
        juger_synthetiques(&mut c, &mut j, &mut alea)?;
    }
    let m = Modele::ouvrir(&gguf)?;
    juger_modele(&mut c, &mut j, &m, &mut alea, &mut journal)?;

    // ------------------------------------------------ verdicts par noyau
    let mut par_noyau = String::new();
    let mut tous = true;
    let mut vise_tombe = casser.is_empty();
    let mut autres_tiennent = true;
    for nk in NOYAUX {
        let cs: Vec<&Cas> = j.cas.iter().filter(|c| c.noyau == nk).collect();
        let tient = !cs.is_empty() && cs.iter().all(|c| c.tient());
        let pire = cs.iter().filter(|c| !c.exact).map(|c| c.mesure).fold(0.0f64, f64::max);
        let diff = cs.iter().filter(|c| c.exact).map(|c| c.mesure).sum::<f64>();
        let _ = write!(
            par_noyau,
            "{}\n    \"{nk}\": {{\"cas\": {}, \"tient\": {tient}, \"pire_ecart\": {pire:e}, \"differences\": {diff}, \"deterministe\": {}}}",
            if par_noyau.is_empty() { "" } else { "," },
            cs.len(),
            cs.iter().all(|c| c.deterministe)
        );
        tous &= tient;
        if nk == casser {
            vise_tombe = !tient;
        } else {
            autres_tiennent &= tient;
        }
    }
    let mut lignes = String::new();
    let mut csv_txt = String::from("modele,couche,noyau,cas,mesure,seuil,exact,deterministe,tient,ms\n");
    for (i, c) in j.cas.iter().enumerate() {
        let _ = write!(
            lignes,
            "{}\n    {{\"noyau\": \"{}\", \"modele\": \"{}\", \"couche\": {}, \"cas\": \"{}\", \"mesure\": {:e}, \"seuil\": {:e}, \"exact\": {}, \"deterministe\": {}, \"tient\": {}, \"ms\": {:.4}}}",
            if i == 0 { "" } else { "," },
            c.noyau,
            c.modele,
            c.couche,
            c.cas.replace('"', "'"),
            c.mesure,
            c.seuil,
            c.exact,
            c.deterministe,
            c.tient(),
            c.ms
        );
        let _ = writeln!(csv_txt, "{},{},{},\"{}\",{:e},{:e},{},{},{},{:.4}", c.modele, c.couche, c.noyau, c.cas.replace('"', "'"), c.mesure, c.seuil, c.exact, c.deterministe, c.tient(), c.ms);
    }
    let verdict = if casser.is_empty() {
        if tous { "les douze témoins tiennent" } else { "AU MOINS UN TÉMOIN TOMBE" }
    } else if vise_tombe && autres_tiennent {
        "cassure : le témoin visé tombe, les onze autres tiennent"
    } else {
        "CASSURE MAL VISÉE : le témoin visé tient, ou un autre tombe"
    };
    let txt = format!(
        "{{\n  \"outil\": \"temoin-k3\", \"etape\": \"K3\", \"commande\": \"{}\",\n  \"carte\": \"{}\", \"pilote\": {}, \"graine\": {GRAINE}, \"casser\": \"{casser}\",\n  \"gguf\": \"{}\", \"modele\": \"{}\", \"experts_par_couche\": {}, \"vocab\": {}, \"eps\": {:e},\n  \"note\": \"couche 1 : entrée = enchâssement normé (pas l'état réel après la couche 0) ; poids réels, activations plausibles\",\n  \"journal\": \"{}\",\n  \"par_noyau\": {{{par_noyau}\n  }},\n  \"cas\": [{lignes}\n  ],\n  \"secondes\": {:.1}, \"tous_tiennent\": {tous}, \"vise_tombe\": {vise_tombe}, \"autres_tiennent\": {autres_tiennent},\n  \"verdict\": \"{verdict}\"\n}}\n",
        a.join(" ").replace('\\', "/"),
        c.ctx.nom(),
        c.ctx.version_pilote(),
        gguf.display().to_string().replace('\\', "/"),
        m.nom,
        m.experts,
        m.vocab,
        m.eps,
        journal.replace('\n', " ; "),
        debut.elapsed().as_secs_f64()
    );
    std::fs::write(&journal_json, txt)?;
    std::fs::write(&csv, csv_txt)?;
    eprintln!("{verdict} ({:.1} s)", debut.elapsed().as_secs_f64());
    Ok(())
}
