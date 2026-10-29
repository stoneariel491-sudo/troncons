//! FOURCHE de `moteur/crates/trc-reference/src/modele.rs` (copie du 2026-10-16, commit 6dd7414) pour
//! l'éclaireur du génome des poids (genome/01-eclaireur.md). Deux ajouts, et rien d'autre :
//! - `capture` : à chaque couche, écrit les entrées des experts (h après la norme, f32) et le routage
//!   (4 experts, 4 poids) de toutes les positions du lot ;
//! - `substitution` : un expert dont le fichier `Lll-Eee.sym` existe est lu comme une **base**
//!   (symboles de 3 bits : classe de magnitude et signe) reconstruite avec les échelles E8M0 d'origine,
//!   au lieu de son MXFP4 exact.
//! Sans ces deux options, la fourche calcule exactement la référence (témoin `temoin-fourche` : logits
//! égaux au bit à ceux de `trc_reference::modele::Reference::evaluer`).
//!
//! La passe avant de gpt-oss en f64.
//!
//! Deux chemins qui calculent la même fonction, avec les mêmes opérations dans le même ordre :
//! - `Reference::pas` : jeton par jeton, avec un cache KV en f64 (l'API du § 5.9) ;
//! - `Reference::evaluer` : couche par couche pour toutes les positions d'un lot de fenêtres.
//!   L'attention étant causale, la sortie d'une position ne dépend que des positions antérieures :
//!   calculer la couche ℓ pour toutes les positions avant la couche ℓ + 1 donne exactement les mêmes
//!   nombres que la boucle jeton par jeton, mais chaque expert n'est lu du disque qu'**une fois par
//!   couche pour tout le lot** au lieu d'une fois par jeton qui le choisit (pour 10 fenêtres de 512
//!   jetons de gpt-oss-120b : 61 Go lus au lieu de ≈ 9,8 To). Le témoin `pas_egal_evaluer` vérifie
//!   l'égalité au bit des deux chemins.
//!
//! Formes du calcul (OpenAI `gpt_oss/torch/model.py`, Apache-2.0 ; comparées à llama.cpp b11515) :
//! ```text
//!  x ← enchâssement[jeton]
//!  pour chaque couche ℓ :
//!    h ← RMSNorm(x)·w_attn ; q, k, v ← h Wqᵀ + bq, h Wkᵀ + bk, h Wvᵀ + bv
//!    q, k ← RoPE-YaRN(q, k, position) ; 64 têtes q, 8 têtes kv (la tête q h lit la tête kv h/8)
//!    a ← attention(q, K, V) avec puits par tête, échelle 1/8, fenêtre de 128 si ℓ est pair
//!    x ← x + a Woᵀ + bo
//!    h ← RMSNorm(x)·w_post ; r ← h Wrᵀ + br ; (i, g) ← top-4(r), softmax des 4 valeurs
//!    x ← x + (((s₀ + s₁) + s₂) + s₃),  s_j = g_j · (SwiGLU-oai(h W_gate,i_jᵀ + b, h W_up,i_jᵀ + b) W_down,i_jᵀ + b)
//!  logits ← RMSNorm(x)·w_sortie Woutᵀ
//! ```

use anyhow::{Context, Result, bail};
use rayon::prelude::*;
use std::path::Path;

use trc_reference::gguf::{GGML_F32, GGML_MXFP4, GGML_Q8_0, Gguf, InfoTenseur, octets_rangee};
use trc_reference::ops::{Rope, VarianteYarn, attention_tete, rmsnorm, routeur_topk, swiglu_oai};
use trc_reference::poids::{Matrice, imiter_q8_0_ggml, rangee_f64};

/// Les hyperparamètres lus dans le GGUF.
#[derive(Clone, Debug)]
pub struct Hyper {
    pub couches: usize,
    pub d_modele: usize,
    pub tetes: usize,
    pub tetes_kv: usize,
    pub dim_tete: usize,
    pub experts: usize,
    pub actifs: usize,
    pub d_ff: usize,
    pub fenetre: usize,
    pub vocab: usize,
    pub eps: f64,
    pub base_rope: f64,
    pub facteur_yarn: f64,
    pub ctx_origine: f64,
    pub beta_rapide: f64,
    pub beta_lent: f64,
}

struct Couche {
    norme_attn: Vec<f64>,
    wq: Matrice,
    bq: Vec<f64>,
    wk: Matrice,
    bk: Vec<f64>,
    wv: Matrice,
    bv: Vec<f64>,
    wo: Matrice,
    bo: Vec<f64>,
    puits: Vec<f64>,
    norme_post: Vec<f64>,
    routeur: Matrice,
    b_routeur: Vec<f64>,
    /// gate, up, down : poids (E matrices à la suite) et biais (E rangées).
    exps: [InfoTenseur; 3],
    exps_biais: [InfoTenseur; 3],
}

/// Les poids d'un expert, lus à la demande.
pub struct Expert {
    pub gate: Matrice,
    pub up: Matrice,
    pub down: Matrice,
    pub b_gate: Vec<f64>,
    pub b_up: Vec<f64>,
    pub b_down: Vec<f64>,
}

/// **Imitations de llama.cpp** : des approximations que llama.cpp fait et que le modèle ne fait
/// pas, réintroduites à la demande pour décomposer l'écart entre la référence et llama.cpp (R1).
/// Toutes à `false` (la valeur par défaut), la référence calcule le modèle.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Imitation {
    /// Activations ramenées en Q8_0 avant chaque produit par des poids MXFP4 ou Q8_0
    /// (`poids::imiter_q8_0_ggml`) ; le routeur (F32) n'est pas touché, comme dans ggml.
    pub q8: bool,
    /// Clés (après rotation) et valeurs arrondies en f16 avant le cache, comme le cache KV f16 de
    /// llama.cpp (type par défaut de `--cache-type-k/v`).
    pub kv16: bool,
}

/// Compteurs d'une évaluation.
#[derive(Clone, Debug, Default)]
pub struct Compteurs {
    pub octets_experts_lus: u64,
    pub lectures_experts: u64,
    /// usages[couche][expert] : nombre de (position, expert) routés.
    pub usages: Vec<Vec<u64>>,
    pub blocs_e255: u64,
}

pub struct Reference {
    pub gguf: Gguf,
    pub hyper: Hyper,
    pub rope: Rope,
    pub variante: VarianteYarn,
    couches: Vec<Couche>,
    norme_sortie: Vec<f64>,
    sortie: Matrice,
    enchassement: InfoTenseur,
    pub compteurs: Compteurs,
    pub imitation: Imitation,
    /// Si `Some`, `evaluer` y ajoute, couche après couche puis position après position (ordre
    /// aplati (séquence, position)), les quatre experts choisis et la marge du routeur.
    pub journal_routage: Option<Vec<([u8; 4], f32)>>,
    /// **Expérience, pas la référence** : si `Some`, `evaluer` prend les experts de chaque (couche,
    /// position) dans cette liste (même ordre que `journal_routage`) au lieu du top-4 du routeur ;
    /// les poids restent le softmax des logits du routeur de ce calcul sur les experts imposés.
    /// Sert à prouver ou réfuter que les écarts viennent des bascules de routage (R1).
    pub routage_impose: Option<Vec<[u8; 4]>>,
    // État de la passe jeton par jeton : cache KV f64 par couche, [position][tête_kv][d].
    cache_k: Vec<Vec<f64>>,
    cache_v: Vec<Vec<f64>>,
    /// Fourche : dossier où écrire les entrées des experts et le routage de chaque couche.
    pub capture: Option<std::path::PathBuf>,
    /// Fourche : dossier des symboles de base substitués aux experts (`Lll-Eee.sym`).
    pub substitution: Option<std::path::PathBuf>,
    /// Fourche : experts substitués (compteur).
    pub experts_substitues: u64,
    /// Fourche : le code (demi-octet) `de` est réécrit en `vers` dans chaque matrice d'expert lue
    /// (8 → 0 : le codon synonyme du zéro, −0 devient +0 ; 1 → 0 : la cassure, la valeur change).
    pub reecrire_code: Option<(u8, u8)>,
    /// Fourche : demi-octets réécrits (compteur).
    pub codes_reecrits: u64,
}

fn vecteur_f32(g: &Gguf, nom: &str) -> Result<Vec<f64>> {
    let t = g.tenseur(nom)?;
    if t.type_ggml != GGML_F32 {
        bail!("{nom} : type {} au lieu de F32", t.type_ggml);
    }
    let o = g.lire_tenseur(nom)?;
    let mut v = vec![0.0; o.len() / 4];
    rangee_f64(GGML_F32, &o, &mut v);
    Ok(v)
}

fn matrice(g: &Gguf, nom: &str) -> Result<Matrice> {
    let t = g.tenseur(nom)?;
    if t.n_dims != 2 {
        bail!("{nom} : {} dimensions au lieu de 2", t.n_dims);
    }
    Matrice::nouvelle(t.type_ggml, t.ne[1] as usize, t.ne[0] as usize, g.lire_tenseur(nom)?)
}

impl Reference {
    pub fn ouvrir(chemin: &Path) -> Result<Reference> {
        Self::ouvrir_variante(chemin, VarianteYarn::OpenAi)
    }

    pub fn ouvrir_variante(chemin: &Path, variante: VarianteYarn) -> Result<Reference> {
        let g = Gguf::ouvrir(chemin)?;
        let arch = g.chaine("general.architecture")?;
        if arch != "gpt-oss" {
            bail!("architecture {arch} : la référence ne connaît que gpt-oss");
        }
        let p = |c: &str| format!("gpt-oss.{c}");
        let enchassement = g.tenseur("token_embd.weight")?.clone();
        let hyper = Hyper {
            couches: g.entier(&p("block_count"))? as usize,
            d_modele: g.entier(&p("embedding_length"))? as usize,
            tetes: g.entier(&p("attention.head_count"))? as usize,
            tetes_kv: g.entier(&p("attention.head_count_kv"))? as usize,
            dim_tete: g.entier(&p("attention.key_length"))? as usize,
            experts: g.entier(&p("expert_count"))? as usize,
            actifs: g.entier(&p("expert_used_count"))? as usize,
            d_ff: g.entier(&p("expert_feed_forward_length"))? as usize,
            fenetre: g.entier(&p("attention.sliding_window"))? as usize,
            vocab: enchassement.ne[1] as usize,
            eps: g.reel(&p("attention.layer_norm_rms_epsilon"))?,
            base_rope: g.reel(&p("rope.freq_base"))?,
            facteur_yarn: g.reel(&p("rope.scaling.factor"))?,
            ctx_origine: g.entier(&p("rope.scaling.original_context_length"))? as f64,
            beta_rapide: g.reel(&p("rope.scaling.yarn_beta_fast"))?,
            beta_lent: g.reel(&p("rope.scaling.yarn_beta_slow"))?,
        };
        if g.chaine(&p("rope.scaling.type"))? != "yarn" {
            bail!("seul le RoPE YaRN est connu");
        }
        if hyper.dim_tete != g.entier(&p("attention.value_length"))? as usize {
            bail!("dimension des valeurs différente de celle des clés");
        }
        let rope = Rope::yarn(hyper.base_rope, hyper.facteur_yarn, hyper.ctx_origine, hyper.beta_rapide, hyper.beta_lent, hyper.dim_tete, variante);
        let mut couches = Vec::with_capacity(hyper.couches);
        for l in 0..hyper.couches {
            let n = |s: &str| format!("blk.{l}.{s}");
            let exps = [g.tenseur(&n("ffn_gate_exps.weight"))?.clone(), g.tenseur(&n("ffn_up_exps.weight"))?.clone(), g.tenseur(&n("ffn_down_exps.weight"))?.clone()];
            let exps_biais = [g.tenseur(&n("ffn_gate_exps.bias"))?.clone(), g.tenseur(&n("ffn_up_exps.bias"))?.clone(), g.tenseur(&n("ffn_down_exps.bias"))?.clone()];
            for t in exps.iter() {
                if t.ne[2] as usize != hyper.experts || t.octets == 0 {
                    bail!("{} : forme {:?}, type {}", t.nom, t.ne, t.type_ggml);
                }
            }
            for t in exps_biais.iter() {
                if t.type_ggml != GGML_F32 || t.ne[1] as usize != hyper.experts {
                    bail!("{} : forme {:?}, type {}", t.nom, t.ne, t.type_ggml);
                }
            }
            couches.push(Couche {
                norme_attn: vecteur_f32(&g, &n("attn_norm.weight"))?,
                wq: matrice(&g, &n("attn_q.weight"))?,
                bq: vecteur_f32(&g, &n("attn_q.bias"))?,
                wk: matrice(&g, &n("attn_k.weight"))?,
                bk: vecteur_f32(&g, &n("attn_k.bias"))?,
                wv: matrice(&g, &n("attn_v.weight"))?,
                bv: vecteur_f32(&g, &n("attn_v.bias"))?,
                wo: matrice(&g, &n("attn_output.weight"))?,
                bo: vecteur_f32(&g, &n("attn_output.bias"))?,
                puits: vecteur_f32(&g, &n("attn_sinks.weight"))?,
                norme_post: vecteur_f32(&g, &n("post_attention_norm.weight"))?,
                routeur: matrice(&g, &n("ffn_gate_inp.weight"))?,
                b_routeur: vecteur_f32(&g, &n("ffn_gate_inp.bias"))?,
                exps,
                exps_biais,
            });
        }
        let h = &hyper;
        let c0 = &couches[0];
        if c0.wq.lignes != h.tetes * h.dim_tete || c0.wk.lignes != h.tetes_kv * h.dim_tete || c0.wq.colonnes != h.d_modele || c0.routeur.lignes != h.experts {
            bail!("formes de la couche 0 incohérentes avec les hyperparamètres");
        }
        let norme_sortie = vecteur_f32(&g, "output_norm.weight")?;
        let sortie = matrice(&g, "output.weight")?;
        let n_couches = hyper.couches;
        let compteurs = Compteurs { usages: vec![vec![0; hyper.experts]; n_couches], ..Default::default() };
        Ok(Reference {
            gguf: g,
            hyper,
            rope,
            variante,
            couches,
            norme_sortie,
            sortie,
            enchassement,
            compteurs,
            imitation: Imitation::default(),
            journal_routage: None,
            routage_impose: None,
            cache_k: vec![Vec::new(); n_couches],
            cache_v: vec![Vec::new(); n_couches],
            capture: None,
            substitution: None,
            experts_substitues: 0,
            reecrire_code: None,
            codes_reecrits: 0,
        })
    }

    /// La couche ℓ est-elle à fenêtre glissante ? (OpenAI : `layer_idx % 2 == 0`.)
    pub fn a_fenetre(&self, couche: usize) -> bool {
        couche % 2 == 0
    }

    /// La ligne d'enchâssement d'un jeton, lue dans le fichier.
    pub fn enchasser(&self, jeton: u32) -> Result<Vec<f64>> {
        let t = &self.enchassement;
        if jeton as usize >= self.hyper.vocab {
            bail!("jeton {jeton} hors du vocabulaire ({})", self.hyper.vocab);
        }
        let ol = octets_rangee(t.type_ggml, t.ne[0])?;
        let o = self.gguf.lire_plage(t.decalage + jeton as u64 * ol, ol)?;
        let mut v = vec![0.0; self.hyper.d_modele];
        rangee_f64(t.type_ggml, &o, &mut v);
        Ok(v)
    }

    /// Lit l'expert `e` de la couche `l` dans le GGUF d'origine.
    pub fn lire_expert(&mut self, l: usize, e: usize) -> Result<Expert> {
        let c = &self.couches[l];
        let mut ms = Vec::with_capacity(3);
        for t in c.exps.iter() {
            let tranche = t.octets / self.hyper.experts as u64;
            let o = self.gguf.lire_plage(t.decalage + e as u64 * tranche, tranche)?;
            ms.push(Matrice::nouvelle(t.type_ggml, t.ne[1] as usize, t.ne[0] as usize, o)?);
            self.compteurs.octets_experts_lus += tranche;
        }
        let mut bs = Vec::with_capacity(3);
        for t in c.exps_biais.iter() {
            let n = t.ne[0];
            let o = self.gguf.lire_plage(t.decalage + e as u64 * n * 4, n * 4)?;
            let mut v = vec![0.0; n as usize];
            rangee_f64(GGML_F32, &o, &mut v);
            bs.push(v);
            self.compteurs.octets_experts_lus += n * 4;
        }
        self.compteurs.lectures_experts += 1;
        for m in ms.iter() {
            self.compteurs.blocs_e255 += m.compter_e255();
        }
        if let Some((de, vers)) = self.reecrire_code {
            for m in ms.iter_mut() {
                for (i, o) in m.octets.iter_mut().enumerate() {
                    if i % 17 == 0 {
                        continue; // l'octet d'échelle E8M0 du bloc
                    }
                    let (lo, hi) = (*o & 15, *o >> 4);
                    let lo2 = if lo == de { vers } else { lo };
                    let hi2 = if hi == de { vers } else { hi };
                    self.codes_reecrits += (lo2 != lo) as u64 + (hi2 != hi) as u64;
                    *o = lo2 | (hi2 << 4);
                }
            }
        }
        if let Some(dossier) = self.substitution.as_ref() {
            let chemin = dossier.join(format!("L{l:02}-E{e:02}.sym"));
            if chemin.exists() {
                ms = substituer(&chemin, ms)?;
                self.experts_substitues += 1;
            }
        }
        let down = ms.pop().unwrap();
        let up = ms.pop().unwrap();
        let gate = ms.pop().unwrap();
        let b_down = bs.pop().unwrap();
        let b_up = bs.pop().unwrap();
        let b_gate = bs.pop().unwrap();
        if gate.lignes != self.hyper.d_ff || down.lignes != self.hyper.d_modele {
            bail!("expert ({l}, {e}) : formes inattendues");
        }
        Ok(Expert { gate, up, down, b_gate, b_up, b_down })
    }

    // ---------------------------------------------------------------- briques communes aux deux chemins

    /// y = W x pour n entrées, avec l'imitation Q8_0 des activations si elle est demandée et que W
    /// est quantifiée (MXFP4 ou Q8_0). Sans imitation : exactement `Matrice::produit`.
    fn mat(&self, w: &Matrice, x: &[f64], n: usize, y: &mut [f64]) {
        if self.imitation.q8 && (w.type_ggml == GGML_MXFP4 || w.type_ggml == GGML_Q8_0) {
            let mut xq = x.to_vec();
            xq.par_chunks_mut(w.colonnes).for_each(imiter_q8_0_ggml);
            w.produit(&xq, n, y);
        } else {
            w.produit(x, n, y);
        }
    }

    /// Normes, projections q k v avec biais, et rotation, pour n positions (positions dans `pos`).
    fn qkv(&self, l: usize, x: &[f64], pos: &[usize]) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
        let h = &self.hyper;
        let c = &self.couches[l];
        let n = pos.len();
        let d = h.d_modele;
        let mut hn = vec![0.0; n * d];
        hn.par_chunks_mut(d).zip(x.par_chunks(d)).for_each(|(y, x)| rmsnorm(x, &c.norme_attn, h.eps, y));
        let (dq, dk) = (h.tetes * h.dim_tete, h.tetes_kv * h.dim_tete);
        let mut q = vec![0.0; n * dq];
        let mut k = vec![0.0; n * dk];
        let mut v = vec![0.0; n * dk];
        self.mat(&c.wq, &hn, n, &mut q);
        self.mat(&c.wk, &hn, n, &mut k);
        self.mat(&c.wv, &hn, n, &mut v);
        let dt = h.dim_tete;
        q.par_chunks_mut(dq).enumerate().for_each(|(p, qp)| {
            for (i, b) in qp.iter_mut().zip(c.bq.iter()) {
                *i += b;
            }
            for t in qp.chunks_mut(dt) {
                self.rope.tourner(t, pos[p]);
            }
        });
        k.par_chunks_mut(dk).enumerate().for_each(|(p, kp)| {
            for (i, b) in kp.iter_mut().zip(c.bk.iter()) {
                *i += b;
            }
            for t in kp.chunks_mut(dt) {
                self.rope.tourner(t, pos[p]);
            }
            if self.imitation.kv16 {
                kp.iter_mut().for_each(|e| *e = half::f16::from_f64(*e).to_f64());
            }
        });
        v.par_chunks_mut(dk).for_each(|vp| {
            for (i, b) in vp.iter_mut().zip(c.bv.iter()) {
                *i += b;
            }
            if self.imitation.kv16 {
                vp.iter_mut().for_each(|e| *e = half::f16::from_f64(*e).to_f64());
            }
        });
        (q, k, v)
    }

    /// x ← x + a Woᵀ + bo, puis la norme d'après l'attention et le routage. Rend (h, choix, poids,
    /// marges) ; la marge d'une position est l'écart entre le 4e et le 5e logit biaisé du routeur,
    /// la distance à un changement d'expert (relevée pour le journal de routage, sans effet sur le
    /// calcul).
    fn apres_attention(&self, l: usize, x: &mut [f64], a: &[f64], n: usize) -> (Vec<f64>, Vec<Vec<usize>>, Vec<Vec<f64>>, Vec<f64>) {
        let h = &self.hyper;
        let c = &self.couches[l];
        let d = h.d_modele;
        let mut o = vec![0.0; n * d];
        self.mat(&c.wo, a, n, &mut o);
        x.par_chunks_mut(d).zip(o.par_chunks(d)).for_each(|(xp, op)| {
            for i in 0..d {
                xp[i] += op[i] + c.bo[i];
            }
        });
        let mut hn = vec![0.0; n * d];
        hn.par_chunks_mut(d).zip(x.par_chunks(d)).for_each(|(y, x)| rmsnorm(x, &c.norme_post, h.eps, y));
        let mut r = vec![0.0; n * h.experts];
        self.mat(&c.routeur, &hn, n, &mut r);
        let impose = self.routage_impose.as_ref().map(|v| &v[l * n..(l + 1) * n]);
        let triples: Vec<(Vec<usize>, Vec<f64>, f64)> = r
            .par_chunks_mut(h.experts)
            .enumerate()
            .map(|(p, rp)| {
                for (i, b) in rp.iter_mut().zip(c.b_routeur.iter()) {
                    *i += b;
                }
                let (choix, poids) = match impose {
                    None => routeur_topk(rp, h.actifs),
                    Some(v) => {
                        let choix: Vec<usize> = v[p].iter().map(|&e| e as usize).collect();
                        let m = choix.iter().map(|&i| rp[i]).fold(f64::NEG_INFINITY, f64::max);
                        let e: Vec<f64> = choix.iter().map(|&i| (rp[i] - m).exp()).collect();
                        let z: f64 = e.iter().sum();
                        (choix, e.iter().map(|x| x / z).collect())
                    }
                };
                let dernier = rp[choix[choix.len() - 1]];
                let suivant = (0..rp.len()).filter(|i| !choix.contains(i)).map(|i| rp[i]).fold(f64::NEG_INFINITY, f64::max);
                (choix, poids, dernier - suivant)
            })
            .collect();
        let mut choix = Vec::with_capacity(n);
        let mut poids = Vec::with_capacity(n);
        let mut marges = Vec::with_capacity(n);
        for (c, p, m) in triples {
            choix.push(c);
            poids.push(p);
            marges.push(m);
        }
        (hn, choix, poids, marges)
    }

    /// Applique l'expert à `m` entrées (m × d_modele) ; rend m × d_modele sorties (biais compris).
    fn appliquer_expert(&self, ex: &Expert, entrees: &[f64], m: usize) -> Vec<f64> {
        let (d, f) = (self.hyper.d_modele, self.hyper.d_ff);
        let mut g = vec![0.0; m * f];
        let mut u = vec![0.0; m * f];
        self.mat(&ex.gate, entrees, m, &mut g);
        self.mat(&ex.up, entrees, m, &mut u);
        let mut a = vec![0.0; m * f];
        a.par_chunks_mut(f).enumerate().for_each(|(p, ap)| {
            for i in 0..f {
                ap[i] = swiglu_oai(g[p * f + i] + ex.b_gate[i], u[p * f + i] + ex.b_up[i]);
            }
        });
        let mut s = vec![0.0; m * d];
        self.mat(&ex.down, &a, m, &mut s);
        s.par_chunks_mut(d).for_each(|sp| {
            for i in 0..d {
                sp[i] += ex.b_down[i];
            }
        });
        s
    }

    /// Les k experts de chaque position, chaque expert lu une fois ; x ← x + (((s₀ + s₁) + s₂) + s₃).
    fn moe(&mut self, l: usize, x: &mut [f64], hn: &[f64], choix: &[Vec<usize>], poids: &[Vec<f64>]) -> Result<()> {
        let (d, k, ne) = (self.hyper.d_modele, self.hyper.actifs, self.hyper.experts);
        let n = choix.len();
        let mut fentes = vec![0.0f64; n * k * d];
        let mut par_expert: Vec<Vec<(usize, usize)>> = vec![Vec::new(); ne];
        for (p, cs) in choix.iter().enumerate() {
            for (j, &e) in cs.iter().enumerate() {
                par_expert[e].push((p, j));
                self.compteurs.usages[l][e] += 1;
            }
        }
        for e in 0..ne {
            let liste = &par_expert[e];
            if liste.is_empty() {
                continue;
            }
            let ex = self.lire_expert(l, e).with_context(|| format!("expert ({l}, {e})"))?;
            let m = liste.len();
            let mut entrees = vec![0.0; m * d];
            for (i, &(p, _)) in liste.iter().enumerate() {
                entrees[i * d..(i + 1) * d].copy_from_slice(&hn[p * d..(p + 1) * d]);
            }
            let s = self.appliquer_expert(&ex, &entrees, m);
            for (i, &(p, j)) in liste.iter().enumerate() {
                let w = poids[p][j];
                let f = &mut fentes[(p * k + j) * d..(p * k + j + 1) * d];
                for t in 0..d {
                    f[t] = w * s[i * d + t];
                }
            }
        }
        x.par_chunks_mut(d).enumerate().for_each(|(p, xp)| {
            for t in 0..d {
                let mut somme = fentes[(p * k) * d + t];
                for j in 1..k {
                    somme += fentes[(p * k + j) * d + t];
                }
                xp[t] += somme;
            }
        });
        Ok(())
    }

    /// Logits de m positions (m × vocab) depuis leurs états x (m × d_modele).
    pub fn logits(&self, x: &[f64], m: usize) -> Vec<f64> {
        let d = self.hyper.d_modele;
        let mut hn = vec![0.0; m * d];
        hn.par_chunks_mut(d).zip(x.par_chunks(d)).for_each(|(y, x)| rmsnorm(x, &self.norme_sortie, self.hyper.eps, y));
        let mut z = vec![0.0; m * self.hyper.vocab];
        self.mat(&self.sortie, &hn, m, &mut z);
        z
    }

    // ---------------------------------------------------------------- chemin 1 : jeton par jeton

    pub fn reinitialiser(&mut self) {
        for c in self.cache_k.iter_mut().chain(self.cache_v.iter_mut()) {
            c.clear();
        }
    }

    /// Un pas de décodage : ajoute `jeton` à la position `position` (qui doit suivre la précédente)
    /// et rend ses logits.
    pub fn pas(&mut self, jeton: u32, position: u32) -> Result<Vec<f64>> {
        let h = self.hyper.clone();
        let dkv = h.tetes_kv * h.dim_tete;
        let attendue = self.cache_k[0].len() / dkv;
        if position as usize != attendue {
            bail!("position {position} : la suivante attendue est {attendue}");
        }
        if self.routage_impose.is_some() {
            bail!("le routage imposé n'existe que pour `evaluer`");
        }
        let mut x = self.enchasser(jeton)?;
        let pos = [position as usize];
        for l in 0..h.couches {
            let (q, k, v) = self.qkv(l, &x, &pos);
            self.cache_k[l].extend_from_slice(&k);
            self.cache_v[l].extend_from_slice(&v);
            let n_cles = position as usize + 1;
            let debut = if self.a_fenetre(l) { n_cles.saturating_sub(h.fenetre) } else { 0 };
            let a = self.attention_une(l, &q, debut, n_cles);
            let (hn, choix, poids, _) = self.apres_attention(l, &mut x, &a, 1);
            self.moe(l, &mut x, &hn, &choix, &poids)?;
        }
        Ok(self.logits(&x, 1))
    }

    /// Attention d'une position (toutes ses têtes) sur les clés [debut, fin) du cache de la couche.
    fn attention_une(&self, l: usize, q: &[f64], debut: usize, fin: usize) -> Vec<f64> {
        let h = &self.hyper;
        let (dt, gk) = (h.dim_tete, h.tetes / h.tetes_kv);
        let dkv = h.tetes_kv * dt;
        let echelle = 1.0 / (dt as f64).sqrt();
        let n = fin - debut;
        let mut sortie = vec![0.0; h.tetes * dt];
        sortie.par_chunks_mut(dt).enumerate().for_each(|(t, o)| {
            let tk = t / gk;
            let mut cles = Vec::with_capacity(n * dt);
            let mut vals = Vec::with_capacity(n * dt);
            for j in debut..fin {
                cles.extend_from_slice(&self.cache_k[l][j * dkv + tk * dt..j * dkv + (tk + 1) * dt]);
                vals.extend_from_slice(&self.cache_v[l][j * dkv + tk * dt..j * dkv + (tk + 1) * dt]);
            }
            let mut sc = Vec::with_capacity(n);
            attention_tete(&q[t * dt..(t + 1) * dt], &cles, &vals, n, self.couches[l].puits[t], echelle, o, &mut sc);
        });
        sortie
    }

    // ---------------------------------------------------------------- chemin 2 : un lot de fenêtres

    /// Évalue chaque séquence de `sequences` depuis la position 0 (cache vide), couche par couche
    /// pour tout le lot. `notee(s, t)` dit si les logits de la position t de la séquence s sont
    /// voulus ; `rendre(s, t, logits)` les reçoit, par paquets, dans l'ordre (s, t) croissant.
    pub fn evaluer(&mut self, sequences: &[Vec<u32>], notee: &dyn Fn(usize, usize) -> bool, rendre: &mut dyn FnMut(usize, usize, &[f64]) -> Result<()>, journal: &mut dyn FnMut(&str)) -> Result<()> {
        let h = self.hyper.clone();
        let d = h.d_modele;
        let mut index = Vec::new(); // (s, t) de chaque position aplatie
        for (s, seq) in sequences.iter().enumerate() {
            for t in 0..seq.len() {
                index.push((s, t));
            }
        }
        let n = index.len();
        let pos: Vec<usize> = index.iter().map(|&(_, t)| t).collect();
        let mut x = vec![0.0; n * d];
        for (p, &(s, t)) in index.iter().enumerate() {
            let e = self.enchasser(sequences[s][t])?;
            x[p * d..(p + 1) * d].copy_from_slice(&e);
        }
        let debuts: Vec<usize> = {
            let mut v = Vec::new();
            let mut acc = 0;
            for seq in sequences {
                v.push(acc);
                acc += seq.len();
            }
            v
        };
        for l in 0..h.couches {
            let t0 = std::time::Instant::now();
            let (q, k, v) = self.qkv(l, &x, &pos);
            let a = self.attention_lot(l, &q, &k, &v, sequences, &debuts);
            let (hn, choix, poids, marges) = self.apres_attention(l, &mut x, &a, n);
            if let Some(j) = self.journal_routage.as_mut() {
                for (c, m) in choix.iter().zip(marges.iter()) {
                    j.push(([c[0] as u8, c[1] as u8, c[2] as u8, c[3] as u8], *m as f32));
                }
            }
            drop((q, k, v, a));
            if let Some(dossier) = self.capture.as_ref() {
                capturer(dossier, l, d, &hn, &choix, &poids)?;
            }
            self.moe(l, &mut x, &hn, &choix, &poids)?;
            journal(&format!("couche {l} : {:.1} s, {:.2} Go d'experts lus en tout", t0.elapsed().as_secs_f64(), self.compteurs.octets_experts_lus as f64 / 1e9));
        }
        // Logits des positions notées, par paquets de 128.
        let notees: Vec<usize> = (0..n).filter(|&p| notee(index[p].0, index[p].1)).collect();
        for paquet in notees.chunks(128) {
            let mut xs = vec![0.0; paquet.len() * d];
            for (i, &p) in paquet.iter().enumerate() {
                xs[i * d..(i + 1) * d].copy_from_slice(&x[p * d..(p + 1) * d]);
            }
            let z = self.logits(&xs, paquet.len());
            for (i, &p) in paquet.iter().enumerate() {
                rendre(index[p].0, index[p].1, &z[i * h.vocab..(i + 1) * h.vocab])?;
            }
        }
        Ok(())
    }

    /// Attention causale de toutes les positions du lot, chaque séquence sur elle-même.
    fn attention_lot(&self, l: usize, q: &[f64], k: &[f64], v: &[f64], sequences: &[Vec<u32>], debuts: &[usize]) -> Vec<f64> {
        let h = &self.hyper;
        let (dt, gk) = (h.dim_tete, h.tetes / h.tetes_kv);
        let (dq, dkv) = (h.tetes * dt, h.tetes_kv * dt);
        let echelle = 1.0 / (dt as f64).sqrt();
        let fenetre = self.a_fenetre(l);
        let n: usize = sequences.iter().map(|s| s.len()).sum();
        // Une tâche par (séquence, tête) ; chacune rend T × dt sorties.
        let taches: Vec<(usize, usize)> = (0..sequences.len()).flat_map(|s| (0..h.tetes).map(move |t| (s, t))).collect();
        let resultats: Vec<(usize, usize, Vec<f64>)> = taches
            .par_iter()
            .map(|&(s, t)| {
                let tk = t / gk;
                let lg = sequences[s].len();
                let b = debuts[s];
                let mut cles = Vec::with_capacity(lg * dt);
                let mut vals = Vec::with_capacity(lg * dt);
                for j in 0..lg {
                    cles.extend_from_slice(&k[(b + j) * dkv + tk * dt..(b + j) * dkv + (tk + 1) * dt]);
                    vals.extend_from_slice(&v[(b + j) * dkv + tk * dt..(b + j) * dkv + (tk + 1) * dt]);
                }
                let mut sortie = vec![0.0; lg * dt];
                let mut sc = Vec::with_capacity(lg);
                for i in 0..lg {
                    let fin = i + 1;
                    let debut = if fenetre { fin.saturating_sub(h.fenetre) } else { 0 };
                    let qi = &q[(b + i) * dq + t * dt..(b + i) * dq + (t + 1) * dt];
                    attention_tete(qi, &cles[debut * dt..fin * dt], &vals[debut * dt..fin * dt], fin - debut, self.couches[l].puits[t], echelle, &mut sortie[i * dt..(i + 1) * dt], &mut sc);
                }
                (s, t, sortie)
            })
            .collect();
        let mut a = vec![0.0; n * dq];
        for (s, t, sortie) in resultats {
            let b = debuts[s];
            for i in 0..sequences[s].len() {
                a[(b + i) * dq + t * dt..(b + i) * dq + (t + 1) * dt].copy_from_slice(&sortie[i * dt..(i + 1) * dt]);
            }
        }
        a
    }
}

// ---------------------------------------------------------------- ajouts de la fourche

/// Écrit `h-Lll.f32` (n × d en f32, petit-boutiste) et `routage-Lll.bin` (par position : 4 octets
/// d'experts puis 4 poids f32).
fn capturer(dossier: &Path, l: usize, d: usize, hn: &[f64], choix: &[Vec<usize>], poids: &[Vec<f64>]) -> Result<()> {
    use std::io::Write;
    let mut o = Vec::with_capacity(hn.len() * 4);
    for v in hn {
        o.extend_from_slice(&(*v as f32).to_le_bytes());
    }
    debug_assert_eq!(hn.len(), choix.len() * d);
    std::fs::File::create(dossier.join(format!("h-L{l:02}.f32")))?.write_all(&o)?;
    let mut r = Vec::with_capacity(choix.len() * 20);
    for (c, p) in choix.iter().zip(poids.iter()) {
        for &e in c {
            r.push(e as u8);
        }
        for &w in p {
            r.extend_from_slice(&(w as f32).to_le_bytes());
        }
    }
    std::fs::File::create(dossier.join(format!("routage-L{l:02}.bin")))?.write_all(&r)?;
    Ok(())
}

/// Fichier `.sym` : « SYM1 », 4 centres f64 (en unités E2M1 doublées, celles de `K_MXFP4`), puis,
/// pour gate, up et down, lignes × colonnes symboles de 4 bits (deux par octet, le faible d'abord) :
/// bits 0-1 la classe de magnitude, bit 2 le signe (1 = négatif). Valeur = ± centre[classe] ·
/// 2^(e − 128), e lu dans le bloc MXFP4 d'origine. Rend trois matrices F32.
fn substituer(chemin: &Path, ms: Vec<Matrice>) -> Result<Vec<Matrice>> {
    let o = std::fs::read(chemin)?;
    if &o[0..4] != b"SYM1" {
        bail!("{} : pas un fichier de symboles", chemin.display());
    }
    let mut centres = [0.0f64; 4];
    for k in 0..4 {
        centres[k] = f64::from_le_bytes(o[4 + 8 * k..12 + 8 * k].try_into()?);
    }
    let mut pos = 36usize;
    let mut sortie = Vec::with_capacity(3);
    for m in ms.into_iter() {
        if m.type_ggml != GGML_MXFP4 {
            bail!("substitution d'une matrice de type {}", m.type_ggml);
        }
        let n = m.lignes * m.colonnes;
        let octets_sym = n.div_ceil(2);
        if o.len() < pos + octets_sym {
            bail!("{} : trop court", chemin.display());
        }
        let sym = &o[pos..pos + octets_sym];
        pos += octets_sym;
        let mut f = vec![0u8; n * 4];
        f.par_chunks_mut(m.colonnes * 4).enumerate().for_each(|(r, ligne)| {
            let blocs = &m.octets[r * m.octets_ligne..(r + 1) * m.octets_ligne];
            for c in 0..m.colonnes {
                let i = r * m.colonnes + c;
                let s = (sym[i / 2] >> (4 * (i % 2))) & 0x0F;
                let e = blocs[(c / 32) * 17];
                let v = centres[(s & 3) as usize] * trc_reference::poids::echelle_e8m0_demi(e);
                let v = if s & 4 != 0 { -v } else { v };
                ligne[c * 4..c * 4 + 4].copy_from_slice(&(v as f32).to_le_bytes());
            }
        });
        sortie.push(Matrice::nouvelle(GGML_F32, m.lignes, m.colonnes, f)?);
    }
    if pos != o.len() {
        bail!("{} : {} octets en trop", chemin.display(), o.len() - pos);
    }
    Ok(sortie)
}
