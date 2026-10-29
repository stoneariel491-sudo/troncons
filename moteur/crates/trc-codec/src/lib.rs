//! Le codec processeur de troncons (decisions/ARCHITECTURE.md § 4.9 à 4.11, § 5.4) : le rANS à
//! contexte connu du décodeur, le codage d'une matrice d'expert MXFP4 au format v1.0, et **la
//! reconstruction exacte d'un expert**, l'oracle que le décodeur de la carte doit égaler octet
//! pour octet.
//!
//! La reconstruction d'une matrice j (R lignes, C colonnes, B = C / 32 blocs par ligne,
//! bloc β = r · B + b) :
//! 1. MEDIANES_j : `méd[r]`, la médiane E8M0 de la ligne (`tri[B/2]`, tri croissant) ;
//! 2. DELTA_j : `δ[β] = (e[β] − méd[r] + 128) mod 256`, d'où `e[β]` ; la classe d'échelle
//!    `κ(β) = 0, 1, 2` selon que δ est sous, à, au-dessus de 128 ;
//! 3. CODES_CTX_j : les 16 octets `qs` de chaque bloc, table choisie par voie selon κ du bloc ;
//! 4. BIAIS_j : R × f32.
//!
//! Version 1.2 (drapeau CANONIQUE, genome/06-codon-v1-2.md) : le codeur canonise les `qs` avant
//! les comptes et le codage (chaque demi-octet 8, le −0 de E2M1, devient 0) ; le flux, les tables
//! et le décodage sont ceux de la v1.0, et l'expert décodé est l'expert **canonique**.

pub mod rans;

pub use rans::{Bilan, FluxRans, TableRans, coder, decoder};
use trc_format::{
    DescFlux, ErreurFormat, Fichier, FluxAEcrire, Partie, Sorte, canoniser_octet, empreinte64, empreinte64_morceaux,
    lire_partie,
};

#[derive(Debug, thiserror::Error)]
pub enum ErreurCodec {
    #[error("format : {0}")]
    Format(#[from] ErreurFormat),
    #[error("table : {0}")]
    Table(String),
    #[error("flux : {0}")]
    Flux(String),
    #[error("flux corrompu : {voies_hors_l} voies hors de L, {tuiles_mots_faux} tuiles aux mots faux (première tuile fautive : {tuile})")]
    Integrite { tuile: u32, voies_hors_l: u64, tuiles_mots_faux: u64 },
    #[error("empreinte fausse : {0}")]
    Empreinte(String),
    #[error("couche {couche}, expert {expert}, matrice {matrice} : {source}")]
    Expert { couche: u16, expert: u16, matrice: u8, source: Box<ErreurCodec> },
    #[error("non pris en charge : {0}")]
    NonPrisEnCharge(String),
}

/// Partition des magnitudes E2M1 de la v1.1 (§ 4.3, champ 124) : classe de la magnitude m.
pub const PARTITION_V11: [u8; 8] = [0, 0, 1, 1, 1, 2, 2, 3];

/// Classe d'échelle d'un δ (§ 4.9.3).
#[inline]
pub fn classe_echelle(delta: u8) -> u8 {
    match delta {
        0..=127 => 0,
        128 => 1,
        _ => 2,
    }
}

// ---------------------------------------------------------------------------------------------
// L'expert décodé

#[derive(Clone, Debug, PartialEq)]
pub struct MatriceDecodee {
    /// R · B · 16 octets, les `qs` des blocs dans l'ordre β.
    pub codes: Vec<u8>,
    /// R · B octets E8M0.
    pub echelles: Vec<u8>,
    pub biais: Vec<f32>,
}

#[derive(Clone, Debug, PartialEq)]
pub struct ExpertDecode {
    pub matrices: [MatriceDecodee; 3],
}

impl MatriceDecodee {
    /// Les blocs MXFP4 de 17 octets `[e, qs × 16]` dans l'ordre β (disposition du GGUF).
    pub fn blocs_origine(&self) -> Vec<u8> {
        let n = self.echelles.len();
        let mut v = Vec::with_capacity(17 * n);
        for b in 0..n {
            v.push(self.echelles[b]);
            v.extend_from_slice(&self.codes[16 * b..16 * b + 16]);
        }
        v
    }
    pub fn octets_biais(&self) -> Vec<u8> {
        self.biais.iter().flat_map(|x| x.to_le_bytes()).collect()
    }
}

impl ExpertDecode {
    /// L'expert d'origine au sens des empreintes (§ 4.11) : pour j = 0, 1, 2 les blocs de 17
    /// octets, puis pour j = 0, 1, 2 les R biais f32.
    pub fn octets_origine(&self) -> Vec<u8> {
        let mut v = Vec::new();
        for m in &self.matrices {
            v.extend_from_slice(&m.blocs_origine());
        }
        for m in &self.matrices {
            v.extend_from_slice(&m.octets_biais());
        }
        v
    }
    pub fn empreinte(&self) -> u64 {
        let blocs: Vec<Vec<u8>> = self.matrices.iter().map(|m| m.blocs_origine()).collect();
        let biais: Vec<Vec<u8>> = self.matrices.iter().map(|m| m.octets_biais()).collect();
        empreinte64_morceaux(blocs.iter().chain(biais.iter()).map(|v| &v[..]))
    }
}

// ---------------------------------------------------------------------------------------------
// Les tables de décodage d'une (couche, matrice)

/// Les tables v1.0 d'une (couche, matrice) : DELTA et CODES_CTX par classe d'échelle.
#[derive(Clone, Debug)]
pub struct TablesMatrice {
    pub delta: TableRans,
    pub codes: [TableRans; 3],
}

impl TablesMatrice {
    pub fn depuis_fichier(f: &Fichier, couche: u16, matrice: u8) -> Result<TablesMatrice, ErreurCodec> {
        let prendre = |sorte: Sorte, ctx: u8| -> Result<TableRans, ErreurCodec> {
            let t = f.table(couche, matrice, sorte, ctx).ok_or_else(|| ErreurCodec::Table(format!("table ({couche}, {matrice}, {sorte:?}, {ctx}) absente")))?;
            let fr = t.charge.frequences().ok_or_else(|| ErreurCodec::Table(format!("table ({couche}, {matrice}, {sorte:?}, {ctx}) sans fréquences")))?;
            TableRans::depuis_frequences(fr, rans::GEOMETRIE_OCTET)
        };
        Ok(TablesMatrice { delta: prendre(Sorte::Delta, 0)?, codes: [prendre(Sorte::CodesCtx, 0)?, prendre(Sorte::CodesCtx, 1)?, prendre(Sorte::CodesCtx, 2)?] })
    }
}

/// Toutes les tables de décodage d'un fichier v1.0, indexées par (couche, matrice) (extension :
/// construites une fois pour décoder beaucoup d'experts).
pub struct TablesFichier {
    matrices: usize,
    t: Vec<TablesMatrice>,
}

impl TablesFichier {
    pub fn depuis_fichier(f: &Fichier) -> Result<TablesFichier, ErreurCodec> {
        let e = f.entete();
        let mut t = Vec::new();
        if !e.est_brut() {
            for c in 0..e.couches {
                for j in 0..e.matrices {
                    t.push(TablesMatrice::depuis_fichier(f, c, j as u8)?);
                }
            }
        }
        Ok(TablesFichier { matrices: e.matrices as usize, t })
    }
    pub fn de(&self, couche: u16, matrice: u8) -> &TablesMatrice {
        &self.t[couche as usize * self.matrices + matrice as usize]
    }
}

// ---------------------------------------------------------------------------------------------
// La reconstruction

fn dims(f: &Fichier, j: usize) -> Result<(usize, usize), ErreurCodec> {
    let e = f.entete();
    let r = e.lignes[j] as usize;
    let c = e.colonnes[j] as usize;
    let ppb = e.poids_par_bloc as usize;
    if ppb != 32 || e.octets_par_bloc != 17 || e.type_ggml != 39 {
        return Err(ErreurCodec::NonPrisEnCharge(format!("experts de type ggml {} ({} poids, {} octets par bloc) : seul MXFP4 (39, 32, 17) est pris en charge", e.type_ggml, ppb, e.octets_par_bloc)));
    }
    if c % ppb != 0 || r == 0 {
        return Err(ErreurCodec::NonPrisEnCharge(format!("matrice {j} de {r} × {c}")));
    }
    Ok((r, c / ppb))
}

fn flux_exige<'a>(p: &Partie<'a>, sorte: Sorte, j: u8, longueur: Option<usize>) -> Result<(&'a [u8], DescFlux), ErreurCodec> {
    let d = *p.trouver(sorte, j).ok_or_else(|| ErreurCodec::Flux(format!("flux {sorte:?} de la matrice {j} absent")))?;
    let o = p.octets_flux(&d);
    if let Some(n) = longueur {
        if o.len() != n || d.produits as usize != n {
            return Err(ErreurCodec::Flux(format!("flux {sorte:?} de la matrice {j} : {} octets (produits {}), {n} attendus", o.len(), d.produits)));
        }
    }
    Ok((o, d))
}

fn biais_depuis(o: &[u8]) -> Vec<f32> {
    o.chunks_exact(4).map(|c| f32::from_le_bytes(c.try_into().unwrap())).collect()
}

/// Décode une matrice v1.0 depuis une partie de niveau 0 (sans vérifier d'empreinte).
/// Rend aussi les bilans des deux flux rANS (DELTA, CODES_CTX).
pub fn decoder_matrice_v10(p: &Partie, j: u8, r: usize, b: usize, t: &TablesMatrice) -> Result<(MatriceDecodee, Bilan, Bilan), ErreurCodec> {
    let n_blocs = r * b;
    let (med, _) = flux_exige(p, Sorte::Medianes, j, Some(r))?;
    let (bi, _) = flux_exige(p, Sorte::Biais, j, Some(4 * r))?;
    let (fd, dd) = flux_exige(p, Sorte::Delta, j, None)?;
    let (fc, dc) = flux_exige(p, Sorte::CodesCtx, j, None)?;
    let flux_d = FluxRans::lire(fd)?;
    let flux_c = FluxRans::lire(fc)?;
    if flux_d.produits != dd.produits || flux_c.produits != dc.produits {
        return Err(ErreurCodec::Flux("octets produits du descripteur ≠ P du flux".into()));
    }
    let attendu_d = n_blocs.div_ceil(128) * 128;
    let attendu_c = (16 * n_blocs).div_ceil(128) * 128;
    if flux_d.produits as usize != attendu_d || flux_c.produits as usize != attendu_c || flux_d.geometrie != 1 || flux_c.geometrie != 1 {
        return Err(ErreurCodec::Flux(format!("P de DELTA ou de CODES_CTX inattendu ({} et {}, {attendu_d} et {attendu_c} attendus)", flux_d.produits, flux_c.produits)));
    }
    // 2. δ, puis e et κ (les blocs de bourrage, de δ = 0, ont κ = 0).
    let (delta, bd) = rans::decoder_une_table(&flux_d, &t.delta.lut)?;
    let kappa: Vec<u8> = delta.iter().map(|&d| classe_echelle(d)).collect();
    let mut echelles = vec![0u8; n_blocs];
    for (beta, e) in echelles.iter_mut().enumerate() {
        *e = med[beta / b].wrapping_add(delta[beta]).wrapping_sub(128);
    }
    // 3. codes, table par voie.
    let luts: [&[u32]; 3] = [&t.codes[0].lut, &t.codes[1].lut, &t.codes[2].lut];
    let (mut codes, bc) = rans::decoder_par_voie(&flux_c, &kappa, &luts)?;
    codes.truncate(16 * n_blocs);
    Ok((MatriceDecodee { codes, echelles, biais: biais_depuis(bi) }, bd, bc))
}

/// Décode un expert depuis sa partie de niveau 0 déjà lue, sans vérifier son empreinte
/// (extension : la vérification C1 l'appelle pour voir, sous la cassure, que le décodage
/// lui-même est faux, et pas seulement l'empreinte).
pub fn decoder_partie(f: &Fichier, tables: Option<&TablesFichier>, p: &Partie, exact: bool) -> Result<ExpertDecode, ErreurCodec> {
    let e = f.entete();
    if e.matrices != 3 || p.n_matrices != 3 {
        return Err(ErreurCodec::NonPrisEnCharge(format!("{} matrices par expert (3 attendues)", e.matrices)));
    }
    if e.version.1 >= 1 && e.niveaux >= 2 {
        let _ = exact;
        return Err(ErreurCodec::NonPrisEnCharge("format v1.1 à deux niveaux : étape F4 (J2), pas encore écrite".into()));
    }
    let mut m: Vec<MatriceDecodee> = Vec::with_capacity(3);
    for j in 0..3u8 {
        let (r, b) = dims(f, j as usize)?;
        let ctx = |s: ErreurCodec| ErreurCodec::Expert { couche: p.couche, expert: p.expert, matrice: j, source: Box::new(s) };
        if e.est_brut() {
            let (ech, _) = flux_exige(p, Sorte::EchellesBrutes, j, Some(r * b)).map_err(ctx)?;
            let (codes, _) = flux_exige(p, Sorte::CodesBruts, j, Some(16 * r * b)).map_err(ctx)?;
            let (bi, _) = flux_exige(p, Sorte::Biais, j, Some(4 * r)).map_err(ctx)?;
            m.push(MatriceDecodee { codes: codes.to_vec(), echelles: ech.to_vec(), biais: biais_depuis(bi) });
        } else {
            let possedees;
            let t = match tables {
                Some(t) => t.de(p.couche, j),
                None => {
                    possedees = TablesMatrice::depuis_fichier(f, p.couche, j).map_err(ctx)?;
                    &possedees
                }
            };
            let (md, bd, bc) = decoder_matrice_v10(p, j, r, b, t).map_err(ctx)?;
            rans::exiger_intact(bd).map_err(ctx)?;
            rans::exiger_intact(bc).map_err(ctx)?;
            m.push(md);
        }
    }
    let m2 = m.pop().unwrap();
    let m1 = m.pop().unwrap();
    let m0 = m.pop().unwrap();
    Ok(ExpertDecode { matrices: [m0, m1, m2] })
}

/// Vérifie l'empreinte des octets utiles d'une partie contre le répertoire.
pub fn verifier_partie(f: &Fichier, couche: u16, expert: u16, niveau: usize, octets: &[u8]) -> Result<(), ErreurCodec> {
    let ent = f.entree(couche, expert);
    let u = ent.utiles[niveau] as usize;
    if octets.len() < u {
        return Err(ErreurCodec::Flux(format!("partie de niveau {niveau} de ({couche}, {expert}) : {} octets, {u} utiles attendus", octets.len())));
    }
    let h = empreinte64(&octets[..u]);
    if h != ent.empreinte_niveau[niveau] {
        return Err(ErreurCodec::Empreinte(format!("partie de niveau {niveau} de ({couche}, {expert}) : {h:#018x} au lieu de {:#018x}", ent.empreinte_niveau[niveau])));
    }
    Ok(())
}

/// La reconstruction de la couture (§ 5.4) : vérifie l'empreinte de chaque partie fournie
/// contre le répertoire, sa structure, puis décode l'expert. `parties[0]` est la partie de
/// niveau 0 (ses `longueur[0]` octets ou au moins ses octets utiles). `exact` ne sert qu'en
/// v1.1 (mode base contre mode exact).
pub fn reconstruire(fichier: &Fichier, couche: u16, expert: u16, parties: &[&[u8]], exact: bool) -> Result<ExpertDecode, ErreurCodec> {
    reconstruire_avec(fichier, None, couche, expert, parties, exact)
}

/// La même, avec des tables déjà construites (extension).
pub fn reconstruire_avec(fichier: &Fichier, tables: Option<&TablesFichier>, couche: u16, expert: u16, parties: &[&[u8]], exact: bool) -> Result<ExpertDecode, ErreurCodec> {
    let p0 = *parties.first().ok_or_else(|| ErreurCodec::Flux("aucune partie fournie".into()))?;
    verifier_partie(fichier, couche, expert, 0, p0)?;
    let u0 = fichier.entree(couche, expert).utiles[0] as usize;
    let p = lire_partie(&p0[..p0.len().min(aligner_usize(u0))])?;
    if (p.couche, p.expert, p.niveau) != (couche, expert, 0) {
        return Err(ErreurCodec::Flux(format!("la partie porte ({}, {}, niveau {}) au lieu de ({couche}, {expert}, niveau 0)", p.couche, p.expert, p.niveau)));
    }
    if p.utiles as usize != u0 {
        return Err(ErreurCodec::Flux(format!("octets utiles de la partie {} ≠ répertoire {u0}", p.utiles)));
    }
    decoder_partie(fichier, tables, &p, exact)
}

fn aligner_usize(x: usize) -> usize {
    x.div_ceil(4096) * 4096
}

// ---------------------------------------------------------------------------------------------
// Le codage (pour le codeur, lot F)

/// Une matrice d'expert préparée pour le codage v1.0.
pub struct PrepaMatrice {
    pub r: usize,
    pub b: usize,
    pub medianes: Vec<u8>,
    /// δ, bourré de zéros jusqu'au multiple de 128.
    pub delta: Vec<u8>,
    /// `qs`, bourrés de zéros jusqu'au multiple de 128.
    pub qs: Vec<u8>,
}

/// Canonise des `qs` en place : chaque demi-octet 8 (−0) devient 0 (+0). Rend le nombre de
/// demi-octets changés.
pub fn canoniser_qs(qs: &mut [u8]) -> u64 {
    let mut n = 0u64;
    for q in qs.iter_mut() {
        let c = canoniser_octet(*q);
        n += ((*q & 15) == 8) as u64 + ((*q >> 4) == 8) as u64;
        *q = c;
    }
    n
}

/// Les blocs MXFP4 de 17 octets `[e, qs × 16]` canonisés (l'échelle `e` n'est pas touchée), et le
/// nombre de demi-octets changés (les −0 fondus).
pub fn blocs_canoniques(blocs: &[u8]) -> (Vec<u8>, u64) {
    assert_eq!(blocs.len() % 17, 0);
    let mut v = blocs.to_vec();
    let mut n = 0;
    for blk in v.chunks_exact_mut(17) {
        n += canoniser_qs(&mut blk[1..]);
    }
    (v, n)
}

/// Prépare une matrice depuis ses blocs MXFP4 d'origine (R · B blocs de 17 octets, ordre β).
pub fn preparer_matrice(blocs: &[u8], r: usize, b: usize) -> PrepaMatrice {
    preparer_matrice_avec(blocs, r, b, false)
}

/// La même, avec les `qs` canonisés si `canonique` (v1.2). Les médianes et les δ ne dépendent
/// que des échelles : ils sont les mêmes dans les deux cas.
pub fn preparer_matrice_avec(blocs: &[u8], r: usize, b: usize, canonique: bool) -> PrepaMatrice {
    assert_eq!(blocs.len(), 17 * r * b);
    let n_blocs = r * b;
    let mut medianes = Vec::with_capacity(r);
    let mut delta = Vec::with_capacity(n_blocs.div_ceil(128) * 128);
    let mut qs = Vec::with_capacity((16 * n_blocs).div_ceil(128) * 128);
    let mut tri = vec![0u8; b];
    for ligne in blocs.chunks_exact(17 * b) {
        for (i, blk) in ligne.chunks_exact(17).enumerate() {
            tri[i] = blk[0];
        }
        tri.sort_unstable();
        let med = tri[b / 2];
        medianes.push(med);
        for blk in ligne.chunks_exact(17) {
            delta.push(blk[0].wrapping_sub(med).wrapping_add(128));
            qs.extend_from_slice(&blk[1..17]);
        }
    }
    delta.resize(n_blocs.div_ceil(128) * 128, 0);
    qs.resize((16 * n_blocs).div_ceil(128) * 128, 0);
    if canonique {
        canoniser_qs(&mut qs);
    }
    PrepaMatrice { r, b, medianes, delta, qs }
}

/// Les comptes d'une (couche, matrice), sommés sur ses experts : δ, et octets de codes par
/// classe d'échelle. Le bourrage est compté (il est codé).
#[derive(Clone)]
pub struct ComptesMatrice {
    pub delta: Vec<u64>,
    pub codes: [Vec<u64>; 3],
}

impl Default for ComptesMatrice {
    fn default() -> Self {
        ComptesMatrice { delta: vec![0; 256], codes: [vec![0; 256], vec![0; 256], vec![0; 256]] }
    }
}

impl ComptesMatrice {
    pub fn ajouter(&mut self, p: &PrepaMatrice) {
        for &d in &p.delta {
            self.delta[d as usize] += 1;
        }
        for (n, &q) in p.qs.iter().enumerate() {
            let k = classe_echelle(*p.delta.get(n / 16).unwrap_or(&0)) as usize;
            self.codes[k][q as usize] += 1;
        }
    }
    pub fn fusionner(&mut self, o: &ComptesMatrice) {
        for s in 0..256 {
            self.delta[s] += o.delta[s];
            for k in 0..3 {
                self.codes[k][s] += o.codes[k][s];
            }
        }
    }
    pub fn tables(&self) -> TablesMatrice {
        TablesMatrice {
            delta: TableRans::depuis_comptes(&self.delta, rans::GEOMETRIE_OCTET),
            codes: [0, 1, 2].map(|k| TableRans::depuis_comptes(&self.codes[k], rans::GEOMETRIE_OCTET)),
        }
    }
}

/// Les quatre flux v1.0 d'une matrice, dans l'ordre du § 4.8 : MEDIANES, BIAIS, DELTA,
/// CODES_CTX ; chacun (sorte, contexte fixe, octets produits, octets).
pub fn coder_matrice_v10(p: &PrepaMatrice, biais: &[u8], t: &TablesMatrice) -> [(Sorte, u8, u32, Vec<u8>); 4] {
    assert_eq!(biais.len(), 4 * p.r);
    let fd = rans::coder_avec(&p.delta, rans::GEOMETRIE_OCTET, |_| Some(0), std::slice::from_ref(&t.delta));
    let kappa: Vec<u8> = p.delta.iter().map(|&d| classe_echelle(d)).collect();
    let fc = rans::coder_par_voie(&p.qs, &kappa, &t.codes);
    [
        (Sorte::Medianes, trc_format::CONTEXTE_AUCUN, p.r as u32, p.medianes.clone()),
        (Sorte::Biais, trc_format::CONTEXTE_AUCUN, biais.len() as u32, biais.to_vec()),
        (Sorte::Delta, 0, fd.produits, fd.serialiser()),
        (Sorte::CodesCtx, trc_format::CONTEXTE_AUCUN, fc.produits, fc.serialiser()),
    ]
}

/// Les trois flux bruts d'une matrice (fichier brut, drapeau bit 2) : ECHELLES_BRUTES,
/// CODES_BRUTS, BIAIS.
pub fn flux_bruts(blocs: &[u8], biais: &[u8]) -> [(Sorte, u8, u32, Vec<u8>); 3] {
    let n = blocs.len() / 17;
    let mut ech = Vec::with_capacity(n);
    let mut codes = Vec::with_capacity(16 * n);
    for blk in blocs.chunks_exact(17) {
        ech.push(blk[0]);
        codes.extend_from_slice(&blk[1..]);
    }
    [
        (Sorte::EchellesBrutes, trc_format::CONTEXTE_AUCUN, ech.len() as u32, ech),
        (Sorte::CodesBruts, trc_format::CONTEXTE_AUCUN, codes.len() as u32, codes),
        (Sorte::Biais, trc_format::CONTEXTE_AUCUN, biais.len() as u32, biais.to_vec()),
    ]
}

/// Vue d'une liste de flux codés, prête pour [`trc_format::assembler_partie`].
pub fn a_ecrire<'a>(matrice: u8, flux: &'a [(Sorte, u8, u32, Vec<u8>)]) -> impl Iterator<Item = FluxAEcrire<'a>> + 'a {
    flux.iter().map(move |(s, c, p, o)| FluxAEcrire { sorte: *s, matrice, contexte: *c, produits: *p, octets: o })
}
