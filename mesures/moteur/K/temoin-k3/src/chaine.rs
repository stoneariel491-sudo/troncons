//! Mode `chaine` : la passe avant entière de gpt-oss enchaînée sur la carte par les seuls noyaux de
//! K1 à K3, contre `Reference::evaluer` (f64), sur des jetons réels.
//!
//! Critères déclarés avant ce code (moteur/REPRISE-K.md, 2026-10-15, 21 h 10) : KL(référence ‖
//! chaîne) moyenne sur les positions ≤ 7·10⁻⁵ ; publiés : KL maximale, premier choix égal, écart
//! relatif des logits. Cassures : `fenetre` (fenêtre sur les couches impaires), `poids` (poids du
//! routeur dans l'ordre inverse) : chacune doit faire dépasser le seuil.
//!
//! Ordre couche par couche, pour toutes les positions : pour la couche ℓ, chaque position p (dans
//! l'ordre) passe norme, q k v, rotation, écriture de sa case, attention, sortie, résidu, norme,
//! routeur ; puis chaque expert demandé est chargé une fois (tranches du GGUF → emplacement SoA,
//! § 5.6) et appliqué aux positions qui l'ont choisi ; puis chaque position combine ses quatre
//! sorties dans l'ordre i = 0..3. Les noyaux, leurs entrées et leur ordre par position sont ceux du
//! décodage jeton par jeton : l'attention est causale, et l'anneau de 128 d'une couche à fenêtre ne
//! contient, au moment où la position p le lit, que les positions p − 127 … p.
//! Aucun arrondi de l'hôte entre deux noyaux : l'hôte ne lit que les indices du routeur (pour
//! charger les experts) et les logits de la fin.

use std::fmt::Write as _;
use std::io::Read;
use std::path::PathBuf;
use std::time::Instant;

use anyhow::{Result, bail};
use trc_noyaux::abi::{DimsExpert, FENETRE_GPT_OSS, ParamsAttention};
use trc_reference::Reference;
use trc_reference::gguf::{GGML_MXFP4, GGML_Q8_0};

use crate::{Carte, Modele, emplacement, f32_depuis, octets_f32, u32_depuis};

/// Les `n` premiers jetons de la fenêtre 0 d'un fichier `.kld` de llama-perplexity (en-tête :
/// « _logits_ », n_ctx u32, n_vocab i32, n_chunk i32, puis les jetons i32 ; format relevé par le
/// lot R, trc-juge/src/kld.rs).
fn jetons_kld(chemin: &std::path::Path, n: usize) -> Result<Vec<u32>> {
    let mut f = std::fs::File::open(chemin)?;
    let mut t = [0u8; 20];
    f.read_exact(&mut t)?;
    if &t[0..8] != b"_logits_" {
        bail!("{} : pas un fichier de logits de llama-perplexity", chemin.display());
    }
    let n_ctx = u32::from_le_bytes(t[8..12].try_into().unwrap()) as usize;
    if n > n_ctx {
        bail!("{n} positions demandées, fenêtres de {n_ctx}");
    }
    let mut o = vec![0u8; 4 * n];
    f.read_exact(&mut o)?;
    Ok(u32_depuis(&o))
}

/// La passe avant sur la carte ; rend les logits f32 des P positions (P × vocab) et les experts que
/// le routeur de la carte a choisis à chaque (couche, position) (couches × P × k, avant toute
/// imposition). `impose` : les experts de la référence, ordre (couche, position), pour D2.
#[allow(clippy::too_many_arguments)]
fn chaine_carte(c: &mut Carte, m: &Modele, jetons: &[u32], couches: usize, casser: &str, impose: Option<&[([u8; 4], f32)]>, journal: &mut String) -> Result<(Vec<f32>, Vec<u32>)> {
    let (d, dt, tq, tk) = (m.d, m.dt, m.tetes, m.tetes_kv);
    let (dq, dkv, ne, k, v) = (tq * dt, tk * dt, m.experts, m.actifs, m.vocab);
    let p_n = jetons.len();
    let f4 = 4usize;
    let emb = m.g.tenseur("token_embd.weight")?.clone();
    if emb.type_ggml != GGML_Q8_0 {
        bail!("token_embd : type {}", emb.type_ggml);
    }
    let ol = (d / 32 * 34) as u64;
    let x = c.allouer(p_n * d * f4)?;
    let xv = |p: usize| x.vue(p * d * f4, d * f4);
    for (p, &t) in jetons.iter().enumerate() {
        let ligne = m.g.lire_plage(emb.decalage + t as u64 * ol, ol)?;
        let cl = c.envoyer(&ligne)?;
        c.k.ligne_q8_0(cl.tout(), 0, d as u32, xv(p), &c.f)?;
        c.f.synchroniser()?;
    }
    let h = c.allouer(d * f4)?;
    let q = c.allouer(dq * f4)?;
    let kk = c.allouer(dkv * f4)?;
    let vv = c.allouer(dkv * f4)?;
    let a = c.allouer(dq * f4)?;
    let o = c.allouer(d * f4)?;
    let h2 = c.allouer(p_n * d * f4)?;
    let h2v = |p: usize| h2.vue(p * d * f4, d * f4);
    let lr = c.allouer(p_n * ne * f4)?;
    let lrv = |p: usize| lr.vue(p * ne * f4, ne * f4);
    let mut choix_carte = Vec::with_capacity(couches * p_n * k);
    let idx = c.allouer(p_n * k * f4)?;
    let pw = c.allouer(p_n * k * f4)?;
    let g = c.allouer(d * f4)?;
    let u = c.allouer(d * f4)?;
    let act = c.allouer(d * f4)?;
    let s = c.allouer(p_n * k * d * f4)?;
    let dims = DimsExpert::GPT_OSS;
    for l in 0..couches {
        let t0 = Instant::now();
        let nl = |x: &str| format!("blk.{l}.{x}");
        let w_attn = c.envoyer(&m.g.lire_tenseur(&nl("attn_norm.weight"))?)?;
        let w_post = c.envoyer(&m.g.lire_tenseur(&nl("post_attention_norm.weight"))?)?;
        let puits = c.envoyer(&m.g.lire_tenseur(&nl("attn_sinks.weight"))?)?;
        let wq = c.envoyer(&m.g.lire_tenseur(&nl("attn_q.weight"))?)?;
        let wk = c.envoyer(&m.g.lire_tenseur(&nl("attn_k.weight"))?)?;
        let wv = c.envoyer(&m.g.lire_tenseur(&nl("attn_v.weight"))?)?;
        let wo = c.envoyer(&m.g.lire_tenseur(&nl("attn_output.weight"))?)?;
        let wr = c.envoyer(&m.g.lire_tenseur(&nl("ffn_gate_inp.weight"))?)?;
        let bq = c.envoyer(&m.g.lire_tenseur(&nl("attn_q.bias"))?)?;
        let bk = c.envoyer(&m.g.lire_tenseur(&nl("attn_k.bias"))?)?;
        let bv = c.envoyer(&m.g.lire_tenseur(&nl("attn_v.bias"))?)?;
        let bo = c.envoyer(&m.g.lire_tenseur(&nl("attn_output.bias"))?)?;
        let br = c.envoyer(&m.g.lire_tenseur(&nl("ffn_gate_inp.bias"))?)?;
        // couche à fenêtre : ℓ pair (OpenAI : layer_idx % 2 == 0) ; cassure : ℓ impair
        let fen = if casser == "fenetre" { l % 2 == 1 } else { l % 2 == 0 };
        let anneau = if fen { FENETRE_GPT_OSS } else { 0 };
        let cases = if fen { FENETRE_GPT_OSS as usize } else { p_n };
        let ck = c.allouer(2 * cases * dkv)?;
        let cv = c.allouer(2 * cases * dkv)?;
        let rp = m.rope;
        for p in 0..p_n {
            let n = &c.k;
            let f = &c.f;
            n.rmsnorm(xv(p), w_attn.tout(), h.tout(), d as u32, 1, m.eps, f)?;
            n.gemv_q8_0(wq.tout(), h.tout(), Some(bq.tout()), q.tout(), dq as u32, d as u32, f)?;
            n.gemv_q8_0(wk.tout(), h.tout(), Some(bk.tout()), kk.tout(), dkv as u32, d as u32, f)?;
            n.gemv_q8_0(wv.tout(), h.tout(), Some(bv.tout()), vv.tout(), dkv as u32, d as u32, f)?;
            n.rope_yarn(q.tout(), kk.tout(), tq as u32, tk as u32, p as u32, &rp, f)?;
            n.ecrire_kv(kk.tout(), vv.tout(), ck.tout(), cv.tout(), dkv as u32, ParamsAttention::case(p as u32, anneau), f)?;
            n.attention(q.tout(), ck.tout(), cv.tout(), puits.tout(), a.tout(), &ParamsAttention::gpt_oss(p as u32, anneau), f)?;
            n.gemv_q8_0(wo.tout(), a.tout(), Some(bo.tout()), o.tout(), d as u32, dq as u32, f)?;
            n.combiner(xv(p), o.tout(), d as u32, None, 1, d as u32, f)?;
            n.rmsnorm(xv(p), w_post.tout(), h2v(p), d as u32, 1, m.eps, f)?;
            n.gemv_f32(wr.tout(), h2v(p), Some(br.tout()), lrv(p), ne as u32, d as u32, f)?;
            n.routeur_topk(lrv(p), ne as u32, k as u32, idx.vue(p * k * f4, k * f4), pw.vue(p * k * f4, k * f4), 0, 0, f)?;
        }
        let mut choix = u32_depuis(&c.recevoir(idx.tout())?);
        choix_carte.extend_from_slice(&choix);
        if let Some(imp) = impose {
            // D2 : les experts de la référence ; poids = softmax, en f64 sur l'hôte, des logits f32
            // du routeur de la carte sur ces quatre experts (forme de l'expérience B du lot R).
            let lh = f32_depuis(&c.recevoir(lr.tout())?);
            let mut w = vec![0f32; p_n * k];
            for p in 0..p_n {
                let e4 = imp[l * p_n + p].0;
                let vals: Vec<f64> = (0..k).map(|i| lh[p * ne + e4[i] as usize] as f64).collect();
                let mx = vals.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
                let ex: Vec<f64> = vals.iter().map(|x| (x - mx).exp()).collect();
                let z: f64 = ex.iter().sum();
                for i in 0..k {
                    choix[p * k + i] = e4[i] as u32;
                    w[p * k + i] = (ex[i] / z) as f32;
                }
            }
            let ci = c.envoyer(&choix.iter().flat_map(|x| x.to_le_bytes()).collect::<Vec<u8>>())?;
            crate::trc_cuda_copie(c, ci.tout(), idx.tout())?;
            let cw = c.envoyer(&octets_f32(&w))?;
            crate::trc_cuda_copie(c, cw.tout(), pw.tout())?;
        }
        if casser == "poids" {
            // faute injectée : poids appliqués aux experts dans l'ordre inverse
            let w = f32_depuis(&c.recevoir(pw.tout())?);
            let mut inv = vec![0f32; w.len()];
            for p in 0..p_n {
                for i in 0..k {
                    inv[p * k + i] = w[p * k + (k - 1 - i)];
                }
            }
            let cw = c.envoyer(&octets_f32(&inv))?;
            crate::trc_cuda_copie(c, cw.tout(), pw.tout())?;
        }
        let mut par_expert: Vec<Vec<(usize, usize)>> = vec![Vec::new(); ne];
        for p in 0..p_n {
            for i in 0..k {
                let e = choix[p * k + i] as usize;
                if e >= ne {
                    bail!("couche {l}, position {p} : expert {e} hors de [0, {ne})");
                }
                par_expert[e].push((p, i));
            }
        }
        let mut charges = 0usize;
        for (e, liste) in par_expert.iter().enumerate() {
            if liste.is_empty() {
                continue;
            }
            let mut tranches: [Vec<u8>; 3] = Default::default();
            let mut biais: [Vec<f32>; 3] = Default::default();
            for (jm, nom) in ["ffn_gate_exps", "ffn_up_exps", "ffn_down_exps"].iter().enumerate() {
                let t = m.g.tenseur(&nl(&format!("{nom}.weight")))?.clone();
                if t.type_ggml != GGML_MXFP4 {
                    bail!("{} : type {}", t.nom, t.type_ggml);
                }
                let tr = t.octets / ne as u64;
                tranches[jm] = m.g.lire_plage(t.decalage + e as u64 * tr, tr)?;
                let tb = m.g.tenseur(&nl(&format!("{nom}.bias")))?.clone();
                let nb = tb.ne[0];
                biais[jm] = f32_depuis(&m.g.lire_plage(tb.decalage + e as u64 * nb * 4, nb * 4)?);
            }
            let em = c.envoyer(&emplacement(&tranches, &biais))?;
            charges += 1;
            let mat = |jm: usize| {
                let dd = dims.disposition(jm);
                em.vue(dd.base as usize, dd.pas as usize)
            };
            for &(p, i) in liste {
                let n = &c.k;
                let f = &c.f;
                n.gemv(mat(0), h2v(p), g.tout(), d as u32, d as u32, f)?;
                n.gemv(mat(1), h2v(p), u.tout(), d as u32, d as u32, f)?;
                n.swiglu_oai(g.tout(), u.tout(), act.tout(), d as u32, f)?;
                n.gemv(mat(2), act.tout(), s.vue((p * k + i) * d * f4, d * f4), d as u32, d as u32, f)?;
            }
            c.f.synchroniser()?;
        }
        for p in 0..p_n {
            c.k.combiner(xv(p), s.vue(p * k * d * f4, k * d * f4), d as u32, Some(pw.vue(p * k * f4, k * f4)), k as u32, d as u32, &c.f)?;
        }
        c.f.synchroniser()?;
        let _ = writeln!(journal, "couche {l} ({}) : {charges} experts chargés, {:.2} s", if fen { "fenêtre" } else { "pleine" }, t0.elapsed().as_secs_f64());
        eprintln!("  carte : couche {l} ({}) : {charges} experts chargés, {:.2} s", if fen { "fenêtre" } else { "pleine" }, t0.elapsed().as_secs_f64());
    }
    let wn = c.envoyer(&m.g.lire_tenseur("output_norm.weight")?)?;
    let wout = c.envoyer(&m.g.lire_tenseur("output.weight")?)?;
    let z = c.allouer(p_n * v * f4)?;
    for p in 0..p_n {
        c.k.rmsnorm(xv(p), wn.tout(), h.tout(), d as u32, 1, m.eps, &c.f)?;
        c.k.gemv_q8_0(wout.tout(), h.tout(), None, z.vue(p * v * f4, v * f4), v as u32, d as u32, &c.f)?;
    }
    Ok((f32_depuis(&c.recevoir(z.tout())?), choix_carte))
}

fn log_softmax(z: &[f64]) -> Vec<f64> {
    let mx = z.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let lse = mx + z.iter().map(|x| (x - mx).exp()).sum::<f64>().ln();
    z.iter().map(|x| x - lse).collect()
}

fn premier(z: &[f64]) -> usize {
    let mut b = 0;
    for i in 1..z.len() {
        if z[i] > z[b] {
            b = i;
        }
    }
    b
}

pub fn lancer(a: &[String]) -> Result<()> {
    if a.len() < 4 {
        bail!("usage : temoin-k3 chaine <modele.gguf> <fichier.kld> <journal.json> <positions.csv> [--positions n] [--casser fenetre|poids]");
    }
    let (gguf, kld, jj, csv) = (PathBuf::from(&a[0]), PathBuf::from(&a[1]), PathBuf::from(&a[2]), PathBuf::from(&a[3]));
    let mut p_n = 160usize;
    let mut casser = String::new();
    let mut imposer = false;
    let mut i = 4;
    while i < a.len() {
        match a[i].as_str() {
            "--positions" => {
                p_n = a[i + 1].parse()?;
                i += 1;
            }
            "--casser" => {
                casser = a[i + 1].clone();
                if casser != "fenetre" && casser != "poids" {
                    bail!("--casser : fenetre ou poids");
                }
                i += 1;
            }
            "--imposer" => imposer = true,
            x => bail!("option inconnue {x}"),
        }
        i += 1;
    }
    let debut = Instant::now();
    let jetons = jetons_kld(&kld, p_n)?;
    let m = Modele::ouvrir(&gguf)?;
    let couches = m.g.entier("gpt-oss.block_count")? as usize;
    let v = m.vocab;
    // la référence d'abord (son journal de routage sert à D1 et D2)
    let t = Instant::now();
    let mut r = Reference::ouvrir(&gguf)?;
    r.journal_routage = Some(Vec::with_capacity(couches * p_n));
    let mut zr = vec![0f64; p_n * v];
    r.evaluer(
        &[jetons.clone()],
        &|_, _| true,
        &mut |_, t, l| {
            zr[t * v..(t + 1) * v].copy_from_slice(l);
            Ok(())
        },
        &mut |s| eprintln!("  référence : {s}"),
    )?;
    let routage_ref = r.journal_routage.take().unwrap();
    drop(r);
    let s_ref = t.elapsed().as_secs_f64();
    let mut c = Carte::nouvelle()?;
    eprintln!("chaîne : {} ; {couches} couches ; {p_n} jetons de {} ; casser « {casser} » ; routage {}", m.nom, kld.display(), if imposer { "imposé (D2)" } else { "libre" });
    let mut journal = String::new();
    let t = Instant::now();
    let (zc, choix_carte) = chaine_carte(&mut c, &m, &jetons, couches, &casser, if imposer { Some(&routage_ref) } else { None }, &mut journal)?;
    let s_carte = t.elapsed().as_secs_f64();
    drop(c);
    // D1 : désaccords de routage (ensemble, ordre) et première bascule de chaque position
    let k = m.actifs;
    let (mut d_ens, mut d_ordre) = (0usize, 0usize);
    let mut premieres: Vec<(usize, usize, f32)> = Vec::new();
    let mut marges_bascule: Vec<f32> = Vec::new();
    // toutes les décisions : (couche, position, marge de la référence, ensemble différent)
    let mut toutes = String::from("couche,position,marge_reference,ensemble_different,ordre_seul_different
");
    for p in 0..p_n {
        let mut vue = false;
        for l in 0..couches {
            let (r4, marge) = routage_ref[l * p_n + p];
            let c4 = &choix_carte[(l * p_n + p) * k..(l * p_n + p + 1) * k];
            let ordre_egal = (0..k).all(|i| c4[i] == r4[i] as u32);
            let mut a: Vec<u32> = c4.to_vec();
            let mut b: Vec<u32> = r4.iter().map(|&x| x as u32).collect();
            a.sort();
            b.sort();
            let _ = writeln!(toutes, "{l},{p},{marge:e},{},{}", (a != b) as u8, (a == b && !ordre_egal) as u8);
            if a != b {
                d_ens += 1;
                marges_bascule.push(marge);
                if !vue {
                    premieres.push((p, l, marge));
                    vue = true;
                }
            } else if !ordre_egal {
                d_ordre += 1;
            }
        }
    }
    let mut txt_bascules = String::new();
    for (i, (p, l, mg)) in premieres.iter().enumerate() {
        let _ = write!(txt_bascules, "{}[{p}, {l}, {mg:e}]", if i == 0 { "" } else { ", " });
    }
    eprintln!("D1 : {d_ens} (couche, position) sur {} à ensemble d'experts différent, {d_ordre} à ordre seul différent ; premières bascules (position, couche, marge de la référence) : {txt_bascules}", couches * p_n);
    let mut lignes = String::from("position,jeton,kl,premier_ref,premier_carte,ecart_relatif_logits\n");
    let (mut kl_somme, mut kl_max, mut egaux, mut e_max) = (0.0f64, 0.0f64, 0usize, 0.0f64);
    for p in 0..p_n {
        let r64 = &zr[p * v..(p + 1) * v];
        let c64: Vec<f64> = zc[p * v..(p + 1) * v].iter().map(|&x| x as f64).collect();
        let (lr, lc) = (log_softmax(r64), log_softmax(&c64));
        let kl: f64 = lr.iter().zip(&lc).map(|(a, b)| a.exp() * (a - b)).sum();
        let (pr, pc) = (premier(r64), premier(&c64));
        let den = r64.iter().fold(0.0f64, |m, x| m.max(x.abs()));
        let e = r64.iter().zip(&c64).fold(0.0f64, |m, (a, b)| m.max((a - b).abs())) / den;
        kl_somme += kl;
        kl_max = kl_max.max(kl);
        egaux += (pr == pc) as usize;
        e_max = e_max.max(e);
        let _ = writeln!(lignes, "{p},{},{kl:e},{pr},{pc},{e:e}", jetons[p]);
    }
    let kl_moy = kl_somme / p_n as f64;
    let seuil = 7e-5;
    let tient = kl_moy <= seuil;
    let verdict = match (casser.is_empty(), tient) {
        (true, true) => "la chaîne tient : KL moyenne sous 7e-5",
        (true, false) => "LA CHAÎNE TOMBE : KL moyenne au-dessus de 7e-5",
        (false, false) => "cassure : la chaîne tombe, comme attendu",
        (false, true) => "CASSURE NON VUE : la chaîne tient malgré la faute",
    };
    let txt = format!(
        "{{\n  \"outil\": \"temoin-k3 chaine\", \"etape\": \"K3\", \"commande\": \"temoin-k3 chaine {}\",\n  \"gguf\": \"{}\", \"kld\": \"{}\", \"positions\": {p_n}, \"couches\": {couches}, \"casser\": \"{casser}\",\n  \"routage\": \"{}\", \"bascules_ensemble\": {d_ens}, \"bascules_ordre_seul\": {d_ordre}, \"decisions\": {},\n  \"premieres_bascules_position_couche_marge\": [{txt_bascules}],\n  \"kl_moyenne\": {kl_moy:e}, \"kl_max\": {kl_max:e}, \"seuil_kl_moyenne\": {seuil:e}, \"premier_choix_egal\": {egaux}, \"ecart_relatif_logits_max\": {e_max:e},\n  \"secondes_carte\": {s_carte:.1}, \"secondes_reference\": {s_ref:.1}, \"secondes\": {:.1},\n  \"journal\": \"{}\",\n  \"tient\": {tient}, \"verdict\": \"{verdict}\"\n}}\n",
        a.join(" ").replace('\\', "/"),
        gguf.display().to_string().replace('\\', "/"),
        kld.display().to_string().replace('\\', "/"),
        if imposer { "impose" } else { "libre" },
        couches * p_n,
        debut.elapsed().as_secs_f64(),
        journal.replace('\n', " ; ")
    );
    std::fs::write(&jj, txt)?;
    std::fs::write(&csv, lignes)?;
    let csv_marges = csv.with_file_name(format!("{}-marges.csv", csv.file_stem().unwrap().to_string_lossy()));
    std::fs::write(&csv_marges, toutes)?;
    let sous = |x: f32| routage_ref.iter().filter(|(_, m)| *m < x).count();
    eprintln!("marges de la référence : < 1e-4 : {}, < 1e-3 : {}, < 1e-2 : {}, sur {} ; marges aux bascules : {:?}", sous(1e-4), sous(1e-3), sous(1e-2), routage_ref.len(), marges_bascule);
    eprintln!("KL moyenne {kl_moy:.3e}, max {kl_max:.3e}, premier choix égal {egaux}/{p_n}, écart des logits {e_max:.2e} : {verdict}");
    Ok(())
}
