//! trc-modele (lot O) : gpt-oss sur la carte (ARCHITECTURE.md § 5.8).
//!
//! Ce que fait cette crate, et ce qu'elle ne fait pas :
//! - elle lit les **hyperparamètres** dans la section MÉTA du `.trc` (§ 4.4) et les vérifie contre
//!   l'en-tête (§ 4.3) ;
//! - elle **monte les résidents** en VRAM (§ 4.5), sauf l'enchâssement `token_embd`, qui n'y entre
//!   jamais (§ 4.5, dernier alinéa) : lecture sans tampon par `trc-es`, en morceaux de 16 Mio dans
//!   deux tampons épinglés qui alternent, chaque tenseur haché au passage et comparé à son
//!   empreinte64 (§ 4.12) ; aucun tenseur n'est gardé en RAM ;
//! - elle tient le **cache KV** (f16, `[case][tête_kv][64]`, § 5.6 ; anneau de 128 cases sur les
//!   couches à fenêtre, `contexte` cases sur les autres) et les **tampons** de la passe avant ;
//! - elle met en file, sur un flux donné, la **passe avant d'un jeton**, couche par couche, en deux
//!   moitiés que sépare le routeur : [`Modele::debut_couche`] (normes, attention, routeur, boîte aux
//!   lettres) puis [`Modele::fin_couche`] (les k experts et leur combinaison) ;
//! - elle **ne sait pas d'où viennent les experts** : `fin_couche` reçoit les k emplacements décodés
//!   (disposition SoA, § 5.6). C'est l'ordonnanceur (`trc-ordo`) qui les fait lire, copier et
//!   décoder ; le témoin O2 les fabrique, lui, depuis le GGUF d'origine.
//!
//! L'ordre des noyaux d'une couche est celui de la chaîne du lot K
//! (`mesures/moteur/K/temoin-k3/src/chaine.rs`), qui tient sous routage imposé (D2) : il est repris
//! tel quel, noyau pour noyau et argument pour argument, pour que le témoin O2 puisse exiger
//! l'égalité au bit avec cette chaîne (même noyaux, mêmes entrées, règle de déterminisme § 5.6).

use std::collections::HashMap;

use anyhow::{Context, Result, bail};
use sha2::{Digest, Sha256};
use trc_cuda::{Contexte, Evenement, Flux, HoteEpingle, MemoireCarte, VueCarte, copier_vers_carte};
use trc_es::{Achevement, Lecteur, Requete};
use trc_format::{Fichier, TenseurResident};
use trc_noyaux::Noyaux;
use trc_noyaux::abi::{DimsExpert, ParamsAttention, ParamsRope};

/// Types ggml des tenseurs que lit la passe avant.
pub const GGML_F32: u32 = 0;
pub const GGML_Q8_0: u32 = 8;
pub const GGML_MXFP4: u32 = 39;

/// Longueur des morceaux de lecture des résidents (deux tampons épinglés de cette taille).
const MORCEAU: u64 = 16 << 20;
const ALIGNEMENT: u64 = 4096;

fn al4k_bas(x: u64) -> u64 {
    x & !(ALIGNEMENT - 1)
}
fn al4k_haut(x: u64) -> u64 {
    (x + ALIGNEMENT - 1) & !(ALIGNEMENT - 1)
}

/// empreinte64 (§ 4.12) d'un SHA-256 en cours.
fn empreinte_de(h: Sha256) -> u64 {
    let d = h.finalize();
    u64::from_le_bytes(d[..8].try_into().unwrap())
}

// ============================================================================ hyperparamètres

/// Les hyperparamètres de gpt-oss, lus dans la section MÉTA du `.trc` et l'en-tête.
#[derive(Clone, Debug)]
pub struct Hyper {
    pub couches: usize,
    /// Dimension du résidu (`embedding_length`, 2 880).
    pub d: usize,
    pub tetes: usize,
    pub tetes_kv: usize,
    /// Dimension d'une tête (`key_length`, 64).
    pub dt: usize,
    pub experts: usize,
    /// k, experts actifs par couche (`expert_used_count`, 4).
    pub actifs: usize,
    pub vocab: usize,
    pub eps: f32,
    pub rope: ParamsRope,
    /// `attention.sliding_window` (128) : l'anneau des couches à fenêtre.
    pub fenetre: u32,
    /// Cases du cache KV des couches pleines (positions au plus) ; 4 096 en J1 (§ 12, point 8).
    pub contexte: u32,
    /// Formes des trois matrices d'un expert (en-tête, § 4.3).
    pub dims: DimsExpert,
}

impl Hyper {
    pub fn depuis_fichier(f: &Fichier, contexte: u32) -> Result<Hyper> {
        let ent = |c: &str| -> Result<u64> {
            let cle = format!("gpt-oss.{c}");
            f.paire(&cle).and_then(|p| p.entier()).with_context(|| format!("MÉTA : clé entière « {cle} » absente"))
        };
        let reel = |c: &str| -> Result<f64> {
            let cle = format!("gpt-oss.{c}");
            f.paire(&cle).and_then(|p| p.reel()).with_context(|| format!("MÉTA : clé réelle « {cle} » absente"))
        };
        let e = f.entete();
        let emb = f.residents().iter().find(|t| t.nom == "token_embd.weight").context("résident token_embd.weight absent")?;
        let h = Hyper {
            couches: ent("block_count")? as usize,
            d: ent("embedding_length")? as usize,
            tetes: ent("attention.head_count")? as usize,
            tetes_kv: ent("attention.head_count_kv")? as usize,
            dt: ent("attention.key_length")? as usize,
            experts: ent("expert_count")? as usize,
            actifs: ent("expert_used_count")? as usize,
            vocab: emb.ne[1] as usize,
            eps: reel("attention.layer_norm_rms_epsilon")? as f32,
            rope: ParamsRope {
                base: reel("rope.freq_base")?,
                facteur: reel("rope.scaling.factor")?,
                ctx_origine: ent("rope.scaling.original_context_length")? as f64,
                beta_rapide: reel("rope.scaling.yarn_beta_fast")?,
                beta_lent: reel("rope.scaling.yarn_beta_slow")?,
                dim_tete: ent("attention.key_length")? as u32,
                variante: 0,
            },
            fenetre: ent("attention.sliding_window")? as u32,
            contexte,
            dims: DimsExpert { lignes: [e.lignes[0], e.lignes[1], e.lignes[2]], colonnes: [e.colonnes[0], e.colonnes[1], e.colonnes[2]] },
        };
        // Rien ne se devine (§ 4.1, principe 6) : l'en-tête et la MÉTA doivent dire la même chose,
        // et les noyaux ont leurs bornes (§ 5.6).
        if (h.couches, h.experts, h.actifs) != (e.couches as usize, e.experts as usize, e.k as usize) {
            bail!("MÉTA ({}, {}, {}) et en-tête ({}, {}, {}) en désaccord", h.couches, h.experts, h.actifs, e.couches, e.experts, e.k);
        }
        if h.dt != 64 || h.tetes % h.tetes_kv != 0 || h.d % 32 != 0 {
            bail!("forme d'attention non prise en charge : d = {}, têtes {} / {}, dimension {}", h.d, h.tetes, h.tetes_kv, h.dt);
        }
        if h.actifs > 8 || h.experts > 256 || h.actifs == 0 {
            bail!("routeur top-{} sur {} experts hors des bornes du noyau", h.actifs, h.experts);
        }
        if h.dims.lignes[0] != h.dims.lignes[1] || h.dims.colonnes[0] != h.d as u32 || h.dims.colonnes[1] != h.d as u32 || h.dims.lignes[2] != h.d as u32 || h.dims.colonnes[2] != h.dims.lignes[0] {
            bail!("formes d'expert {:?} incompatibles avec d = {}", h.dims, h.d);
        }
        h.dims.verifier().map_err(|e| anyhow::anyhow!(e))?;
        if contexte == 0 || contexte > trc_noyaux::abi::ATTENTION_POSITIONS_MAX {
            bail!("contexte de {contexte} positions (1 à {})", trc_noyaux::abi::ATTENTION_POSITIONS_MAX);
        }
        Ok(h)
    }

    /// L'anneau de la couche `l` : `fenetre` sur les couches paires (couche à fenêtre glissante,
    /// `layer_idx % 2 == 0` dans `gpt_oss/torch/model.py` d'OpenAI, Apache-2.0), 0 sinon.
    pub fn anneau(&self, l: usize) -> u32 {
        if l % 2 == 0 { self.fenetre } else { 0 }
    }

    /// Octets d'un emplacement d'expert décodé (§ 5.6).
    pub fn taille_emplacement(&self) -> u64 {
        self.dims.taille_emplacement()
    }

    /// Octets d'une rangée de `token_embd` (Q8_0 : d / 32 blocs de 34 o).
    pub fn octets_ligne_enchassement(&self) -> u64 {
        (self.d / 32 * 34) as u64
    }
}

// ============================================================================ chargement

/// Ce que le chargement des résidents a lu et vérifié.
#[derive(Clone, Debug, Default)]
pub struct BilanChargement {
    pub tenseurs: usize,
    pub octets_tenseurs: u64,
    pub octets_lus: u64,
    pub lectures: usize,
    pub empreintes_verifiees: usize,
    pub secondes: f64,
}

/// Lit, sans tampon, des plages absolues du fichier et remet chaque morceau à `servir` (décalage
/// absolu du morceau, tampon épinglé qui le porte, longueur). Deux tampons épinglés alternent : la
/// lecture du morceau i + 1 vole pendant que le morceau i est servi. `servir` doit avoir fini
/// d'utiliser le tampon quand elle rend la main (elle synchronise ses copies).
fn lire_plages(
    ctx: &Contexte,
    lecteur: &Lecteur,
    plages: &[(u64, u64)],
    servir: &mut dyn FnMut(u64, &HoteEpingle, usize) -> Result<()>,
) -> Result<(u64, usize)> {
    let taille_fichier = lecteur.taille();
    if taille_fichier % ALIGNEMENT != 0 {
        bail!("fichier de {taille_fichier} octets : pas un multiple de 4 096 (§ 4.1, point 3)");
    }
    let mut lectures: Vec<(u64, u64)> = Vec::new();
    for &(a, b) in plages {
        let (mut x, fin) = (al4k_bas(a), al4k_haut(b).min(taille_fichier));
        while x < fin {
            let n = (fin - x).min(MORCEAU);
            lectures.push((x, n));
            x += n;
        }
    }
    let tampons = [HoteEpingle::allouer(ctx, MORCEAU as usize, false)?, HoteEpingle::allouer(ctx, MORCEAU as usize, false)?];
    let mut ach: Vec<Achevement> = Vec::new();
    let soumettre = |i: usize| -> Result<()> {
        let (dec, n) = lectures[i];
        lecteur
            .soumettre(Requete { jeton: i as u64, decalage: dec, longueur: n as u32, destination: tampons[i % 2].pointeur() })
            .map_err(|e| anyhow::anyhow!("lecture des résidents : {e}"))
    };
    if !lectures.is_empty() {
        soumettre(0)?;
    }
    let mut lus = 0u64;
    for i in 0..lectures.len() {
        if i + 1 < lectures.len() {
            soumettre(i + 1)?;
        }
        // Attendre l'achèvement de la lecture i (deux en vol : l'ordre d'arrivée n'est pas garanti).
        loop {
            if let Some(p) = ach.iter().position(|a| a.jeton == i as u64) {
                let a = ach.remove(p);
                if let Some(e) = a.erreur {
                    bail!("lecture des résidents au décalage {} : erreur Windows {e}", lectures[i].0);
                }
                if a.octets as u64 != lectures[i].1 {
                    bail!("lecture des résidents au décalage {} : {} octets sur {}", lectures[i].0, a.octets, lectures[i].1);
                }
                break;
            }
            lecteur.recolter(u32::MAX, &mut ach).map_err(|e| anyhow::anyhow!("récolte : {e}"))?;
        }
        lus += lectures[i].1;
        servir(lectures[i].0, &tampons[i % 2], lectures[i].1 as usize)?;
    }
    Ok((lus, lectures.len()))
}

/// Monte en VRAM les résidents choisis par `garder`, chacun dans sa propre allocation, et vérifie
/// l'empreinte64 de chacun (§ 4.12) sur les octets mêmes qui partent vers la carte.
fn charger_residents(
    ctx: &Contexte,
    f: &Flux,
    lecteur: &Lecteur,
    fichier: &Fichier,
    garder: &dyn Fn(&TenseurResident) -> bool,
) -> Result<(HashMap<String, MemoireCarte>, BilanChargement)> {
    let t0 = std::time::Instant::now();
    let base = fichier.debut_donnees_residentes();
    let mut choisis: Vec<&TenseurResident> = fichier.residents().iter().filter(|t| garder(t)).collect();
    choisis.sort_by_key(|t| t.decalage);
    let mut memoires: Vec<MemoireCarte> = Vec::with_capacity(choisis.len());
    let mut hachages: Vec<Sha256> = Vec::with_capacity(choisis.len());
    for t in &choisis {
        memoires.push(MemoireCarte::allouer(ctx, t.octets.max(16) as usize).with_context(|| format!("VRAM pour {}", t.nom))?);
        hachages.push(Sha256::new());
    }
    // Plages absolues, fusionnées quand elles se touchent à 4 Kio près (une lecture de plus coûte
    // plus que les quelques octets de bourrage entre deux tenseurs).
    let mut plages: Vec<(u64, u64)> = Vec::new();
    for t in &choisis {
        let (a, b) = (base + t.decalage, base + t.decalage + t.octets);
        match plages.last_mut() {
            Some(p) if al4k_bas(a) <= al4k_haut(p.1) => p.1 = p.1.max(b),
            _ => plages.push((a, b)),
        }
    }
    let (lus, lectures) = lire_plages(ctx, lecteur, &plages, &mut |dec, tampon, n| {
        let fin = dec + n as u64;
        let mut copies = 0;
        for (i, t) in choisis.iter().enumerate() {
            let (a, b) = (base + t.decalage, base + t.decalage + t.octets);
            if a >= fin || b <= dec {
                continue;
            }
            let (x, y) = (a.max(dec), b.min(fin));
            let (dans, long) = ((x - dec) as usize, (y - x) as usize);
            hachages[i].update(&tampon.tranche()[dans..dans + long]);
            copier_vers_carte(memoires[i].vue((x - a) as usize, long), tampon, dans, long, f)?;
            copies += 1;
        }
        if copies > 0 {
            f.synchroniser()?;
        }
        Ok(())
    })?;
    let mut sortie = HashMap::with_capacity(choisis.len());
    let mut bilan = BilanChargement { lectures, octets_lus: lus, ..Default::default() };
    for ((t, m), h) in choisis.iter().zip(memoires).zip(hachages) {
        let e = empreinte_de(h);
        if e != t.empreinte {
            bail!("résident {} : empreinte64 {e:016x} au lieu de {:016x} (fichier corrompu)", t.nom, t.empreinte);
        }
        bilan.tenseurs += 1;
        bilan.octets_tenseurs += t.octets;
        bilan.empreintes_verifiees += 1;
        sortie.insert(t.nom.clone(), m);
    }
    bilan.secondes = t0.elapsed().as_secs_f64();
    Ok((sortie, bilan))
}

// ============================================================================ le modèle sur la carte

/// Les tenseurs d'une couche, en VRAM (vues dans les allocations de [`Modele`]), et son cache KV.
struct Couche {
    anneau: u32,
    attn_norm: VueCarte,
    wq: VueCarte,
    bq: VueCarte,
    wk: VueCarte,
    bk: VueCarte,
    wv: VueCarte,
    bv: VueCarte,
    wo: VueCarte,
    bo: VueCarte,
    puits: VueCarte,
    post_norm: VueCarte,
    wr: VueCarte,
    br: VueCarte,
    ck: MemoireCarte,
    cv: MemoireCarte,
}

/// Les tampons de la passe avant d'un jeton (f32 contigus, § 5.6).
struct Tampons {
    x: MemoireCarte,
    h: MemoireCarte,
    q: MemoireCarte,
    k: MemoireCarte,
    v: MemoireCarte,
    a: MemoireCarte,
    o: MemoireCarte,
    h2: MemoireCarte,
    lr: MemoireCarte,
    idx: MemoireCarte,
    pw: MemoireCarte,
    g: MemoireCarte,
    u: MemoireCarte,
    act: MemoireCarte,
    s: MemoireCarte,
    z: MemoireCarte,
    jeton: MemoireCarte,
    ligne: MemoireCarte,
    // préchargement (J1+) : la prédiction du routeur de la couche suivante, dans ses propres tampons
    h2p: MemoireCarte,
    lrp: MemoireCarte,
    idxp: MemoireCarte,
    pwp: MemoireCarte,
}

/// gpt-oss monté sur la carte. Toutes les méthodes de passe mettent en file sur le flux donné et
/// rendent la main sans attendre.
pub struct Modele {
    pub h: Hyper,
    _tenseurs: HashMap<String, MemoireCarte>,
    couches: Vec<Couche>,
    norme_sortie: VueCarte,
    sortie: VueCarte,
    /// `token_embd` (jamais en VRAM, § 4.5) et le début absolu de la zone des résidents.
    enchassement: TenseurResident,
    debut_donnees: u64,
    t: Tampons,
    pub bilan: BilanChargement,
    octets_vram: u64,
    /// Essai de la ronde de corrections J1 (constat M5) : cache KV en f32 au lieu de f16 (couture N
    /// inchangée par défaut ; noyaux `ecrire_kv_f32` et `attention_kvf32`).
    pub kv_f32: bool,
}

fn somme(m: &[&MemoireCarte]) -> u64 {
    m.iter().map(|x| x.octets() as u64).sum()
}

impl Modele {
    /// Lit les hyperparamètres, monte les résidents (sauf `token_embd`) en VRAM en vérifiant leurs
    /// empreintes, alloue le cache KV de `contexte` positions et les tampons.
    pub fn charger(ctx: &Contexte, f: &Flux, lecteur: &Lecteur, fichier: &Fichier, contexte: u32) -> Result<Modele> {
        Self::charger_kv(ctx, f, lecteur, fichier, contexte, false)
    }

    /// Extension (constat M5) : comme [`Modele::charger`], cache KV en f32 si `kv_f32`.
    pub fn charger_kv(ctx: &Contexte, f: &Flux, lecteur: &Lecteur, fichier: &Fichier, contexte: u32, kv_f32: bool) -> Result<Modele> {
        let h = Hyper::depuis_fichier(fichier, contexte)?;
        let octets_kv_elt = if kv_f32 { 4 } else { 2 };
        let enchassement = fichier.residents().iter().find(|t| t.nom == "token_embd.weight").unwrap().clone();
        if enchassement.type_ggml != GGML_Q8_0 || enchassement.ne[0] as usize != h.d {
            bail!("token_embd : type {} et forme {:?} (Q8_0 de {} colonnes attendu)", enchassement.type_ggml, enchassement.ne, h.d);
        }
        let (tenseurs, bilan) = charger_residents(ctx, f, lecteur, fichier, &|t| t.nom != "token_embd.weight")?;
        let infos: HashMap<&str, &TenseurResident> = fichier.residents().iter().map(|t| (t.nom.as_str(), t)).collect();
        let vue = |nom: &str, type_attendu: u32, elements: usize| -> Result<VueCarte> {
            let t = infos.get(nom).with_context(|| format!("résident {nom} absent"))?;
            if t.type_ggml != type_attendu {
                bail!("{nom} : type ggml {} au lieu de {type_attendu}", t.type_ggml);
            }
            let n: u64 = t.ne[..t.n_dims as usize].iter().product();
            if n as usize != elements {
                bail!("{nom} : {n} éléments au lieu de {elements} (forme {:?})", t.ne);
            }
            Ok(tenseurs[nom].tout())
        };
        let (d, dq, dkv) = (h.d, h.tetes * h.dt, h.tetes_kv * h.dt);
        let mut couches = Vec::with_capacity(h.couches);
        let mut octets_kv = 0u64;
        for l in 0..h.couches {
            let n = |x: &str| format!("blk.{l}.{x}");
            let anneau = h.anneau(l);
            let cases = if anneau > 0 { anneau } else { contexte } as usize;
            let ck = MemoireCarte::allouer(ctx, octets_kv_elt * cases * dkv)?;
            let cv = MemoireCarte::allouer(ctx, octets_kv_elt * cases * dkv)?;
            octets_kv += (ck.octets() + cv.octets()) as u64;
            couches.push(Couche {
                anneau,
                attn_norm: vue(&n("attn_norm.weight"), GGML_F32, d)?,
                wq: vue(&n("attn_q.weight"), GGML_Q8_0, dq * d)?,
                bq: vue(&n("attn_q.bias"), GGML_F32, dq)?,
                wk: vue(&n("attn_k.weight"), GGML_Q8_0, dkv * d)?,
                bk: vue(&n("attn_k.bias"), GGML_F32, dkv)?,
                wv: vue(&n("attn_v.weight"), GGML_Q8_0, dkv * d)?,
                bv: vue(&n("attn_v.bias"), GGML_F32, dkv)?,
                wo: vue(&n("attn_output.weight"), GGML_Q8_0, d * dq)?,
                bo: vue(&n("attn_output.bias"), GGML_F32, d)?,
                puits: vue(&n("attn_sinks.weight"), GGML_F32, h.tetes)?,
                post_norm: vue(&n("post_attention_norm.weight"), GGML_F32, d)?,
                wr: vue(&n("ffn_gate_inp.weight"), GGML_F32, h.experts * d)?,
                br: vue(&n("ffn_gate_inp.bias"), GGML_F32, h.experts)?,
                ck,
                cv,
            });
        }
        let norme_sortie = vue("output_norm.weight", GGML_F32, d)?;
        let sortie = vue("output.weight", GGML_Q8_0, h.vocab * d)?;
        let f4 = 4usize;
        let a = |n: usize| MemoireCarte::allouer(ctx, n.max(16));
        let t = Tampons {
            x: a(d * f4)?,
            h: a(d * f4)?,
            q: a(dq * f4)?,
            k: a(dkv * f4)?,
            v: a(dkv * f4)?,
            a: a(dq * f4)?,
            o: a(d * f4)?,
            h2: a(d * f4)?,
            lr: a(h.experts * f4)?,
            idx: a(h.actifs * f4)?,
            pw: a(h.actifs * f4)?,
            g: a(h.dims.lignes[0] as usize * f4)?,
            u: a(h.dims.lignes[1] as usize * f4)?,
            act: a(h.dims.lignes[0] as usize * f4)?,
            s: a(h.actifs * d * f4)?,
            z: a(h.vocab * f4)?,
            jeton: a(16)?,
            ligne: a(2 * ALIGNEMENT as usize)?,
            h2p: a(d * f4)?,
            lrp: a(h.experts * f4)?,
            idxp: a(h.actifs * f4)?,
            pwp: a(h.actifs * f4)?,
        };
        let tt = &t;
        let octets_tampons = somme(&[&tt.x, &tt.h, &tt.q, &tt.k, &tt.v, &tt.a, &tt.o, &tt.h2, &tt.lr, &tt.idx, &tt.pw, &tt.g, &tt.u, &tt.act, &tt.s, &tt.z, &tt.jeton, &tt.ligne]);
        let octets_vram = tenseurs.values().map(|m| m.octets() as u64).sum::<u64>() + octets_kv + octets_tampons;
        Ok(Modele { h, _tenseurs: tenseurs, couches, norme_sortie, sortie, enchassement, debut_donnees: fichier.debut_donnees_residentes(), t, bilan, octets_vram, kv_f32 })
    }

    /// Octets de VRAM alloués par le modèle (résidents, cache KV, tampons ; sans les emplacements
    /// d'experts, qui sont à l'ordonnanceur).
    pub fn octets_vram(&self) -> u64 {
        self.octets_vram
    }

    /// La rangée `jeton` de `token_embd` : (décalage absolu dans le `.trc`, octets). Le moteur la lit
    /// dans une lecture alignée de 8 Kio (§ 4.5), ou dans sa copie en RAM.
    pub fn ligne_enchassement(&self, jeton: u32) -> Result<(u64, u64)> {
        if jeton as usize >= self.h.vocab {
            bail!("jeton {jeton} hors du vocabulaire ({})", self.h.vocab);
        }
        let ol = self.h.octets_ligne_enchassement();
        Ok((self.debut_donnees + self.enchassement.decalage + jeton as u64 * ol, ol))
    }

    /// Le tenseur `token_embd` et son décalage absolu (pour `--enchassement-en-ram`).
    pub fn tenseur_enchassement(&self) -> (&TenseurResident, u64) {
        (&self.enchassement, self.debut_donnees + self.enchassement.decalage)
    }

    /// Tampon VRAM de 8 Kio où arrive la ligne d'enchâssement (alignée comme dans le fichier).
    pub fn tampon_ligne(&self) -> VueCarte {
        self.t.ligne.tout()
    }

    /// x ← la ligne Q8_0 qui commence à `ligne` (exact, § 5.6 `ligne_q8_0`).
    pub fn enchasser(&self, n: &Noyaux, ligne: VueCarte, f: &Flux) -> Result<()> {
        n.ligne_q8_0(ligne, 0, self.h.d as u32, self.t.x.tout(), f)?;
        Ok(())
    }

    /// Première moitié de la couche `l` à la position `position` : attention, résidu, norme, logits
    /// du routeur, top-k. Les k indices et poids vont dans les tampons du modèle et, si `boite` n'est
    /// pas nulle, dans la boîte aux lettres projetée avec la séquence `sequence` (protocole de E0 c).
    pub fn debut_couche(&self, n: &Noyaux, l: usize, position: u32, boite: u64, sequence: u32, f: &Flux) -> Result<()> {
        self.debut_couche_biais(n, l, position, boite, sequence, None, f)
    }

    /// [`Modele::debut_couche`] avec, si `biais` est donné (f32[experts] sur la carte : β pour un
    /// expert déjà en VRAM, 0 sinon), le routeur biaisé par le cache (P3, `--biais-cache`) : mêmes
    /// noyaux, sauf le dernier, `routeur_topk_biais` à la place de `routeur_topk`. Sans biais, c'est
    /// exactement l'ancienne suite de lancements.
    #[allow(clippy::too_many_arguments)]
    pub fn debut_couche_biais(&self, n: &Noyaux, l: usize, position: u32, boite: u64, sequence: u32, biais: Option<VueCarte>, f: &Flux) -> Result<()> {
        let h = &self.h;
        if position >= h.contexte {
            bail!("position {position} au-delà du contexte de {} positions", h.contexte);
        }
        let (d, dq, dkv) = (h.d as u32, (h.tetes * h.dt) as u32, (h.tetes_kv * h.dt) as u32);
        let c = &self.couches[l];
        let t = &self.t;
        // L'ordre de la chaîne du lot K (chaine.rs, boucle par position), noyau pour noyau.
        n.rmsnorm(t.x.tout(), c.attn_norm, t.h.tout(), d, 1, h.eps, f)?;
        n.gemv_q8_0(c.wq, t.h.tout(), Some(c.bq), t.q.tout(), dq, d, f)?;
        n.gemv_q8_0(c.wk, t.h.tout(), Some(c.bk), t.k.tout(), dkv, d, f)?;
        n.gemv_q8_0(c.wv, t.h.tout(), Some(c.bv), t.v.tout(), dkv, d, f)?;
        n.rope_yarn(t.q.tout(), t.k.tout(), h.tetes as u32, h.tetes_kv as u32, position, &h.rope, f)?;
        if self.kv_f32 {
            n.ecrire_kv_f32(t.k.tout(), t.v.tout(), c.ck.tout(), c.cv.tout(), dkv, ParamsAttention::case(position, c.anneau), f)?;
            n.attention_kvf32(t.q.tout(), c.ck.tout(), c.cv.tout(), c.puits, t.a.tout(), &ParamsAttention::gpt_oss(position, c.anneau), f)?;
        } else {
            n.ecrire_kv(t.k.tout(), t.v.tout(), c.ck.tout(), c.cv.tout(), dkv, ParamsAttention::case(position, c.anneau), f)?;
            n.attention(t.q.tout(), c.ck.tout(), c.cv.tout(), c.puits, t.a.tout(), &ParamsAttention::gpt_oss(position, c.anneau), f)?;
        }
        n.gemv_q8_0(c.wo, t.a.tout(), Some(c.bo), t.o.tout(), d, dq, f)?;
        n.combiner(t.x.tout(), t.o.tout(), d, None, 1, d, f)?;
        n.rmsnorm(t.x.tout(), c.post_norm, t.h2.tout(), d, 1, h.eps, f)?;
        n.gemv_f32(c.wr, t.h2.tout(), Some(c.br), t.lr.tout(), h.experts as u32, d, f)?;
        match biais {
            None => n.routeur_topk(t.lr.tout(), h.experts as u32, h.actifs as u32, t.idx.tout(), t.pw.tout(), boite, sequence, f)?,
            Some(b) => n.routeur_topk_biais(t.lr.tout(), b, h.experts as u32, h.actifs as u32, t.idx.tout(), t.pw.tout(), boite, sequence, f)?,
        }
        Ok(())
    }

    /// Seconde moitié d'une couche : pour chaque i, l'expert de l'emplacement `emplacements[i]` (le
    /// i-ème choisi par le routeur) appliqué à h₂ ; puis x += Σ poidsᵢ · sortieᵢ dans l'ordre
    /// i = 0 .. k − 1 (§ 5.6, `combiner`).
    pub fn fin_couche(&self, n: &Noyaux, emplacements: &[VueCarte], f: &Flux) -> Result<()> {
        let h = &self.h;
        if emplacements.len() != h.actifs {
            bail!("{} emplacements pour k = {}", emplacements.len(), h.actifs);
        }
        let t = &self.t;
        let dims = &h.dims;
        let (d, f4) = (h.d, 4usize);
        for (i, e) in emplacements.iter().enumerate() {
            let mat = |j: usize| {
                let dd = dims.disposition(j);
                VueCarte { adresse: e.adresse + dd.base, octets: dd.pas as usize }
            };
            n.gemv(mat(0), t.h2.tout(), t.g.tout(), dims.lignes[0], dims.colonnes[0], f)?;
            n.gemv(mat(1), t.h2.tout(), t.u.tout(), dims.lignes[1], dims.colonnes[1], f)?;
            n.swiglu_oai(t.g.tout(), t.u.tout(), t.act.tout(), dims.lignes[0], f)?;
            n.gemv(mat(2), t.act.tout(), t.s.vue(i * d * f4, d * f4), dims.lignes[2], dims.colonnes[2], f)?;
        }
        n.combiner(t.x.tout(), t.s.tout(), d as u32, Some(t.pw.tout()), h.actifs as u32, d as u32, f)?;
        Ok(())
    }

    /// La sortie : RMSNorm, logits (Q8_0, `vocab` lignes), jeton glouton (argmax, égalité : plus
    /// petit indice).
    pub fn sortie(&self, n: &Noyaux, f: &Flux) -> Result<()> {
        let (h, t) = (&self.h, &self.t);
        n.rmsnorm(t.x.tout(), self.norme_sortie, t.h.tout(), h.d as u32, 1, h.eps, f)?;
        n.gemv_q8_0(self.sortie, t.h.tout(), None, t.z.tout(), h.vocab as u32, h.d as u32, f)?;
        n.argmax(t.z.tout(), h.vocab as u32, t.jeton.tout(), f)?;
        Ok(())
    }

    /// Préchargement (J1+) : prédit les experts de la couche `l_suivante` en appliquant **son**
    /// routeur (norme d'après attention et `ffn_gate_inp` de `l_suivante`) au résidu courant (celui de
    /// la couche en cours, après son attention). Écrit dans des tampons à part : x et le calcul du
    /// jeton ne sont pas touchés (les logits ne dépendent pas du préchargement). Les k indices vont
    /// dans la boîte `boite` avec la séquence `sequence`.
    pub fn predire(&self, n: &Noyaux, l_suivante: usize, boite: u64, sequence: u32, f: &Flux) -> Result<()> {
        let h = &self.h;
        let c = &self.couches[l_suivante];
        let t = &self.t;
        let d = h.d as u32;
        n.rmsnorm(t.x.tout(), c.post_norm, t.h2p.tout(), d, 1, h.eps, f)?;
        n.gemv_f32(c.wr, t.h2p.tout(), Some(c.br), t.lrp.tout(), h.experts as u32, d, f)?;
        n.routeur_topk(t.lrp.tout(), h.experts as u32, h.actifs as u32, t.idxp.tout(), t.pwp.tout(), boite, sequence, f)?;
        Ok(())
    }

    /// Les logits f32 (`vocab`) de la dernière sortie.
    pub fn logits(&self) -> VueCarte {
        self.t.z.tout()
    }
    /// Le jeton glouton (u32) de la dernière sortie.
    pub fn jeton(&self) -> VueCarte {
        self.t.jeton.vue(0, 4)
    }
    /// Les k indices (u32) du dernier routeur.
    pub fn indices(&self) -> VueCarte {
        self.t.idx.tout()
    }
    /// Les k poids (f32) du dernier routeur.
    pub fn poids(&self) -> VueCarte {
        self.t.pw.tout()
    }
    /// Les logits du routeur (f32[E]) de la dernière couche passée.
    pub fn logits_routeur(&self) -> VueCarte {
        self.t.lr.tout()
    }
    /// Le résidu x (f32[d]).
    pub fn residu(&self) -> VueCarte {
        self.t.x.tout()
    }
}

/// Les tampons d'un préremplissage par flux (J1+) : un résidu, un h₂, k indices, k poids et k
/// sorties d'experts **par position**, pour traiter une couche entière, toutes positions, avant la
/// suivante (l'ordre de la chaîne K3, que la proposition 5 rend égal au bit à l'ordre jeton par
/// jeton).
pub struct Positions {
    pub n: usize,
    x: MemoireCarte,
    h2: MemoireCarte,
    idx: MemoireCarte,
    pw: MemoireCarte,
    s: MemoireCarte,
}

impl Positions {
    pub fn allouer(ctx: &Contexte, h: &Hyper, n: usize) -> Result<Positions> {
        let (d, k, f4) = (h.d, h.actifs, 4usize);
        Ok(Positions {
            n,
            x: MemoireCarte::allouer(ctx, n * d * f4)?,
            h2: MemoireCarte::allouer(ctx, n * d * f4)?,
            idx: MemoireCarte::allouer(ctx, n * k * f4)?,
            pw: MemoireCarte::allouer(ctx, n * k * f4)?,
            s: MemoireCarte::allouer(ctx, n * k * d * f4)?,
        })
    }
    pub fn octets(&self) -> u64 {
        (self.x.octets() + self.h2.octets() + self.idx.octets() + self.pw.octets() + self.s.octets()) as u64
    }
    /// Les indices des k experts de toutes les positions (u32[n · k]).
    pub fn indices(&self) -> VueCarte {
        self.idx.tout()
    }
}

impl Modele {
    fn vx(&self, p: &Positions, i: usize) -> VueCarte {
        p.x.vue(i * self.h.d * 4, self.h.d * 4)
    }
    fn vh2(&self, p: &Positions, i: usize) -> VueCarte {
        p.h2.vue(i * self.h.d * 4, self.h.d * 4)
    }

    /// Préremplissage par flux : x de la position `i` ← la ligne Q8_0 `ligne`.
    pub fn enchasser_pos(&self, n: &Noyaux, ligne: VueCarte, pos: &Positions, i: usize, f: &Flux) -> Result<()> {
        n.ligne_q8_0(ligne, 0, self.h.d as u32, self.vx(pos, i), f)?;
        Ok(())
    }

    /// [`Modele::debut_couche`] pour la position `i` d'un préremplissage par flux : mêmes noyaux,
    /// mêmes arguments, sur le résidu et le h₂ de la position.
    pub fn debut_couche_pos(&self, n: &Noyaux, l: usize, pos: &Positions, i: usize, f: &Flux) -> Result<()> {
        let h = &self.h;
        let position = i as u32;
        if position >= h.contexte {
            bail!("position {position} au-delà du contexte de {} positions", h.contexte);
        }
        let (d, dq, dkv, k) = (h.d as u32, (h.tetes * h.dt) as u32, (h.tetes_kv * h.dt) as u32, h.actifs);
        let c = &self.couches[l];
        let t = &self.t;
        let (x, h2) = (self.vx(pos, i), self.vh2(pos, i));
        n.rmsnorm(x, c.attn_norm, t.h.tout(), d, 1, h.eps, f)?;
        n.gemv_q8_0(c.wq, t.h.tout(), Some(c.bq), t.q.tout(), dq, d, f)?;
        n.gemv_q8_0(c.wk, t.h.tout(), Some(c.bk), t.k.tout(), dkv, d, f)?;
        n.gemv_q8_0(c.wv, t.h.tout(), Some(c.bv), t.v.tout(), dkv, d, f)?;
        n.rope_yarn(t.q.tout(), t.k.tout(), h.tetes as u32, h.tetes_kv as u32, position, &h.rope, f)?;
        if self.kv_f32 {
            n.ecrire_kv_f32(t.k.tout(), t.v.tout(), c.ck.tout(), c.cv.tout(), dkv, ParamsAttention::case(position, c.anneau), f)?;
            n.attention_kvf32(t.q.tout(), c.ck.tout(), c.cv.tout(), c.puits, t.a.tout(), &ParamsAttention::gpt_oss(position, c.anneau), f)?;
        } else {
            n.ecrire_kv(t.k.tout(), t.v.tout(), c.ck.tout(), c.cv.tout(), dkv, ParamsAttention::case(position, c.anneau), f)?;
            n.attention(t.q.tout(), c.ck.tout(), c.cv.tout(), c.puits, t.a.tout(), &ParamsAttention::gpt_oss(position, c.anneau), f)?;
        }
        n.gemv_q8_0(c.wo, t.a.tout(), Some(c.bo), t.o.tout(), d, dq, f)?;
        n.combiner(x, t.o.tout(), d, None, 1, d, f)?;
        n.rmsnorm(x, c.post_norm, h2, d, 1, h.eps, f)?;
        n.gemv_f32(c.wr, h2, Some(c.br), t.lr.tout(), h.experts as u32, d, f)?;
        n.routeur_topk(t.lr.tout(), h.experts as u32, k as u32, pos.idx.vue(i * k * 4, k * 4), pos.pw.vue(i * k * 4, k * 4), 0, 0, f)?;
        Ok(())
    }

    /// L'expert de `emplacement` appliqué au h₂ de la position `i`, sortie dans sa case j.
    pub fn expert_pos(&self, n: &Noyaux, emplacement: VueCarte, pos: &Positions, i: usize, j: usize, f: &Flux) -> Result<()> {
        let h = &self.h;
        let t = &self.t;
        let dims = &h.dims;
        let (d, k) = (h.d, h.actifs);
        let mat = |m: usize| {
            let dd = dims.disposition(m);
            VueCarte { adresse: emplacement.adresse + dd.base, octets: dd.pas as usize }
        };
        let h2 = self.vh2(pos, i);
        n.gemv(mat(0), h2, t.g.tout(), dims.lignes[0], dims.colonnes[0], f)?;
        n.gemv(mat(1), h2, t.u.tout(), dims.lignes[1], dims.colonnes[1], f)?;
        n.swiglu_oai(t.g.tout(), t.u.tout(), t.act.tout(), dims.lignes[0], f)?;
        n.gemv(mat(2), t.act.tout(), pos.s.vue((i * k + j) * d * 4, d * 4), dims.lignes[2], dims.colonnes[2], f)?;
        Ok(())
    }

    /// x de la position `i` += Σ poids · sortie, dans l'ordre j = 0 .. k − 1.
    pub fn combiner_pos(&self, n: &Noyaux, pos: &Positions, i: usize, f: &Flux) -> Result<()> {
        let (d, k) = (self.h.d, self.h.actifs);
        n.combiner(self.vx(pos, i), pos.s.vue(i * k * d * 4, k * d * 4), d as u32, Some(pos.pw.vue(i * k * 4, k * 4)), k as u32, d as u32, f)?;
        Ok(())
    }

    /// Copie le résidu de la position `i` dans x (pour enchaîner la génération jeton par jeton, ou
    /// tirer la sortie d'une position).
    pub fn reprendre_pos(&self, pos: &Positions, i: usize, f: &Flux) -> Result<()> {
        trc_cuda::copier_carte_carte(self.t.x.tout(), self.vx(pos, i), f)?;
        Ok(())
    }
}

/// Un événement horodaté enregistré sur `f` (pour qui veut dater une passe sans tout synchroniser).
pub fn marquer(ctx: &Contexte, f: &Flux) -> Result<Evenement> {
    let e = Evenement::nouveau(ctx, true)?;
    e.enregistrer(f)?;
    Ok(e)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn alignements() {
        assert_eq!(al4k_bas(4095), 0);
        assert_eq!(al4k_bas(4096), 4096);
        assert_eq!(al4k_haut(1), 4096);
        assert_eq!(al4k_haut(8192), 8192);
    }

    #[test]
    fn anneau_des_couches_paires() {
        let h = Hyper {
            couches: 4, d: 2880, tetes: 64, tetes_kv: 8, dt: 64, experts: 32, actifs: 4, vocab: 10, eps: 1e-5,
            rope: ParamsRope::GPT_OSS, fenetre: 128, contexte: 4096, dims: DimsExpert::GPT_OSS,
        };
        assert_eq!((h.anneau(0), h.anneau(1), h.anneau(2), h.anneau(3)), (128, 0, 128, 0));
        assert_eq!(h.octets_ligne_enchassement(), 3060);
        assert_eq!(h.taille_emplacement(), 13_254_144);
    }
}
