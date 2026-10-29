//! L'interface binaire entre l'hôte et les noyaux (couture N, ARCHITECTURE.md § 5.6), sans rien
//! qui touche la carte : structures `#[repr(C)]` de même disposition que leurs jumelles CUDA
//! (`noyaux/commun.cuh`, `noyaux/gemv.cuh`), disposition SoA de l'emplacement, LUT de décodage et
//! géométries de lancement. Tout se teste sur le processeur.

/// Dimensions des trois matrices d'un expert (en-tête du fichier, § 4.3 : `lignes`, `colonnes`).
/// Passée par valeur aux noyaux du décodeur : 24 octets, alignement 4 (`trc::DimsExpert`).
#[repr(C)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct DimsExpert {
    pub lignes: [u32; 3],
    pub colonnes: [u32; 3],
}

/// Un produit d'un lot de [`crate::Noyaux::gemv_lot`] : 32 octets (`trc::DescGemv`).
#[repr(C)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct DescGemv {
    /// Adresse de la matrice dans l'emplacement (ses codes ; multiple de 256).
    pub matrice: u64,
    /// Adresse de x, f32[colonnes] (multiple de 16).
    pub x: u64,
    /// Adresse de y, f32[lignes].
    pub y: u64,
    pub lignes: u32,
    pub colonnes: u32,
}

/// Un expert d'un lot de [`crate::Noyaux::decoder_lot`] : 32 octets (`trc::DescDecodage`).
/// Extension de la couture N (fonction ajoutée, rien d'existant changé).
#[repr(C)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct DescDecodage {
    /// Adresse de la partie de niveau 0 telle qu'arrivée par DMA.
    pub partie: u64,
    /// Adresse de l'emplacement (multiple de 256).
    pub emplacement: u64,
    /// Adresse des LUT de la couche de cet expert, `u32[3][4][4096]`.
    pub luts: u64,
    /// Adresse du tampon de contrôle de cet expert, `u32[4]`, remis à zéro par l'appelant.
    pub controle: u64,
}

impl DescDecodage {
    /// Les 32 octets petit-boutistes que lit la carte.
    pub fn octets(&self) -> [u8; 32] {
        let mut o = [0u8; 32];
        for (i, v) in [self.partie, self.emplacement, self.luts, self.controle].iter().enumerate() {
            o[8 * i..8 * i + 8].copy_from_slice(&v.to_le_bytes());
        }
        o
    }
}

/// Fils par bloc des noyaux (doivent égaler les `__launch_bounds__` de la source CUDA).
pub const FILS_ECHELLES: u32 = 128;
pub const FILS_CODES: u32 = 256;
pub const FILS_BRUT: u32 = 256;
pub const GEMV_FILS: u32 = 256;
/// Lignes traitées par un bloc de la GEMV (4 lignes par warp, 8 warps).
pub const GEMV_LIGNES_PAR_BLOC: u32 = 32;
/// Mots de 32 bits des LUT d'une couche : `u32[3 matrices][4 tables][4096 fentes]`.
pub const LUTS_PAR_COUCHE: usize = 3 * 4 * 4096;
/// Macro-pas par tuile que le codeur écrit (§ 4.9.1 : N = 256) ; sert seulement à dimensionner
/// la grille, les noyaux lisant N dans chaque flux (toute grille est juste).
pub const MACRO_PAR_TUILE: u32 = 256;

/// x arrondi au multiple de 256 supérieur (`al256`, § 5.6).
pub const fn al256(x: u64) -> u64 {
    (x + 255) & !255
}

/// Disposition SoA d'une matrice dans l'emplacement (§ 5.6). Décalages relatifs au début de la
/// matrice, sauf `base` (début de la matrice dans l'emplacement).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Disposition {
    pub base: u64,
    pub echelles: u64,
    pub biais: u64,
    pub pas: u64,
}

pub fn disposition_matrice(lignes: u32, colonnes: u32) -> Disposition {
    let blocs = lignes as u64 * (colonnes / 32) as u64;
    let echelles = al256(blocs * 16);
    let biais = al256(echelles + blocs);
    Disposition { base: 0, echelles, biais, pas: al256(biais + 4 * lignes as u64) }
}

impl DimsExpert {
    /// Les dimensions de gpt-oss (20b et 120b) : trois matrices de 2 880 × 2 880.
    pub const GPT_OSS: DimsExpert = DimsExpert { lignes: [2880; 3], colonnes: [2880; 3] };

    pub fn verifier(&self) -> Result<(), String> {
        for j in 0..3 {
            let (r, c) = (self.lignes[j], self.colonnes[j]);
            if r == 0 || c == 0 || c % 32 != 0 {
                return Err(format!("matrice {j} : forme {r} × {c} (colonnes multiples de 32 exigées)"));
            }
            if (r as u64) * (c as u64 / 32) * 16 > u32::MAX as u64 {
                return Err(format!("matrice {j} : plus de 4 Gio de codes"));
            }
        }
        Ok(())
    }

    /// Disposition de la matrice `j` dans l'emplacement.
    pub fn disposition(&self, j: usize) -> Disposition {
        let base = (0..j).map(|i| disposition_matrice(self.lignes[i], self.colonnes[i]).pas).sum();
        Disposition { base, ..disposition_matrice(self.lignes[j], self.colonnes[j]) }
    }

    /// Octets d'un emplacement (somme des pas des trois matrices).
    pub fn taille_emplacement(&self) -> u64 {
        (0..3).map(|j| disposition_matrice(self.lignes[j], self.colonnes[j]).pas).sum()
    }

    /// Blocs MXFP4 de la matrice `j`.
    pub fn blocs(&self, j: usize) -> u64 {
        self.lignes[j] as u64 * (self.colonnes[j] / 32) as u64
    }
}

/// Disposition de la matrice `j` (fonction libre, pour l'appelant qui n'a que les dimensions).
pub fn disposition(dims: &DimsExpert, j: usize) -> Disposition {
    dims.disposition(j)
}

fn tuiles(octets: u64) -> u32 {
    let macro_pas = octets.div_ceil(128);
    macro_pas.div_ceil(MACRO_PAR_TUILE as u64) as u32
}

/// Grilles de `decoder_echelles` (un warp par tuile de DELTA, 4 warps par bloc) et de
/// `decoder_codes` (un warp par tuile de CODES_CTX, 8 warps par bloc) ; la dimension y vaut 3
/// (une par matrice).
pub fn grilles_decodeur(dims: &DimsExpert) -> ([u32; 3], [u32; 3]) {
    let td = (0..3).map(|j| tuiles(dims.blocs(j))).max().unwrap_or(1);
    let tc = (0..3).map(|j| tuiles(16 * dims.blocs(j))).max().unwrap_or(1);
    ([td.div_ceil(FILS_ECHELLES / 32).max(1), 3, 1], [tc.div_ceil(FILS_CODES / 32).max(1), 3, 1])
}

/// Grilles du décodeur dimensionnées sur les tuiles **réelles** d'une partie (extension) : le
/// nombre de tuiles T de chaque flux DELTA et CODES_CTX est lu dans son en-tête (§ 4.9.1), si bien
/// qu'un codeur qui choisit un autre N que 256 (variante D du lot K : DELTA en tuiles de 32
/// macro-pas) garde une tuile par warp. `partie` : la copie hôte de la partie (en-tête, table des
/// flux, flux). Erreur si un flux manque ou sort de la partie ; la carte refait ses propres
/// contrôles de format de toute façon.
pub fn grilles_depuis_partie(partie: &[u8]) -> Result<([u32; 3], [u32; 3]), String> {
    let lu16 = |p: usize| -> Option<u32> { partie.get(p..p + 2).map(|b| u16::from_le_bytes([b[0], b[1]]) as u32) };
    let lu32 = |p: usize| -> Option<u32> { partie.get(p..p + 4).map(|b| u32::from_le_bytes([b[0], b[1], b[2], b[3]])) };
    let n_flux = lu16(10).ok_or("partie de moins de 12 o")? as usize;
    let (mut td, mut tc) = (0u32, 0u32);
    let mut vus = [[false; 2]; 3];
    for i in 0..n_flux {
        let e = 64 + 16 * i;
        let sorte = *partie.get(e).ok_or("table des flux tronquée")?;
        let j = *partie.get(e + 1).ok_or("table des flux tronquée")? as usize;
        let k = match sorte {
            0x03 => 0,
            0x04 => 1,
            _ => continue,
        };
        if j > 2 {
            return Err(format!("flux {i} : matrice {j}"));
        }
        let dec = lu32(e + 4).ok_or("table des flux tronquée")? as usize;
        let t = lu32(dec + 8).ok_or_else(|| format!("flux {i} hors de la partie"))?;
        vus[j][k] = true;
        if k == 0 { td = td.max(t) } else { tc = tc.max(t) }
    }
    if vus.iter().any(|v| !v[0] || !v[1]) {
        return Err("DELTA ou CODES_CTX absent pour une matrice".into());
    }
    Ok(([td.div_ceil(FILS_ECHELLES / 32).max(1), 3, 1], [tc.div_ceil(FILS_CODES / 32).max(1), 3, 1]))
}

/// Grille de `copier_brut` (pas de grille sur les blocs, au plus 96 blocs par matrice).
pub fn grille_brut(dims: &DimsExpert) -> [u32; 3] {
    let n = (0..3).map(|j| dims.blocs(j)).max().unwrap_or(1);
    [(n.div_ceil(FILS_BRUT as u64) as u32).clamp(1, 96), 3, 1]
}

/// LUT de géométrie 1 (§ 4.9.2) d'une table de 256 fréquences : pour chaque fente
/// `i ∈ [c[s], c[s] + f[s])`, `lut[i] = s | (f[s] − 1) << 8 | (i − c[s]) << 20`. La somme des
/// fréquences doit valoir exactement 4 096 (§ 4.6).
pub fn lut_geometrie1(freq: &[u16]) -> Result<Vec<u32>, String> {
    if freq.len() != 256 {
        return Err(format!("{} fréquences, 256 attendues", freq.len()));
    }
    let somme: u32 = freq.iter().map(|&f| f as u32).sum();
    if somme != 4096 {
        return Err(format!("somme des fréquences {somme}, 4 096 attendus"));
    }
    let mut lut = vec![0u32; 4096];
    let mut c = 0u32;
    for (s, &f) in freq.iter().enumerate() {
        for i in c..c + f as u32 {
            lut[i as usize] = s as u32 | ((f as u32 - 1) << 8) | ((i - c) << 20);
        }
        c += f as u32;
    }
    Ok(lut)
}

/// Les LUT d'une couche, dans la disposition que lisent les noyaux : pour la matrice j,
/// `[j][0]` DELTA, `[j][1 + κ]` CODES_CTX du contexte κ. `tables[j][t]` donne les 256 fréquences
/// de la table, ou `None` si le fichier ne la porte pas (contexte jamais rencontré : LUT de
/// zéros, qu'aucun flux juste ne lit).
pub fn luts_couche(tables: &[[Option<&[u16]>; 4]; 3]) -> Result<Vec<u32>, String> {
    let mut l = vec![0u32; LUTS_PAR_COUCHE];
    for (j, tj) in tables.iter().enumerate() {
        for (t, ft) in tj.iter().enumerate() {
            if let Some(f) = ft {
                let lut = lut_geometrie1(f).map_err(|e| format!("matrice {j}, table {t} : {e}"))?;
                l[(j * 4 + t) * 4096..(j * 4 + t + 1) * 4096].copy_from_slice(&lut);
            }
        }
    }
    Ok(l)
}

// ------------------------------------------------------------------ étape K3 (extension de la couture N)

/// Paramètres de YaRN passés par valeur à `rope_yarn` : 48 octets, alignement 8
/// (`trc::ParamsRope`, `noyaux/passe.cuh`).
#[repr(C)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ParamsRope {
    /// θ, `rope.freq_base` (150 000 pour gpt-oss).
    pub base: f64,
    /// s, `rope.scaling.factor` (32).
    pub facteur: f64,
    /// L0, `rope.scaling.original_context_length` (4 096).
    pub ctx_origine: f64,
    /// `rope.scaling.yarn_beta_fast` (32).
    pub beta_rapide: f64,
    /// `rope.scaling.yarn_beta_slow` (1).
    pub beta_lent: f64,
    /// d, `attention.key_length` (64).
    pub dim_tete: u32,
    /// 0 : définition d'OpenAI (bornes de la rampe réelles, le modèle) ; 1 : forme de llama.cpp
    /// (bornes arrondies), gardée pour mesurer l'écart, comme `trc_reference::VarianteYarn`.
    pub variante: u32,
}

impl ParamsRope {
    /// gpt-oss (20b et 120b), relevé dans les GGUF de la machine le 2026-10-15 (§ 4.4).
    pub const GPT_OSS: ParamsRope =
        ParamsRope { base: 150_000.0, facteur: 32.0, ctx_origine: 4096.0, beta_rapide: 32.0, beta_lent: 1.0, dim_tete: 64, variante: 0 };
}

/// Paramètres de l'attention d'une position, passés par valeur à `attention` : 32 octets
/// (`trc::ParamsAttention`).
#[repr(C)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ParamsAttention {
    pub tetes: u32,
    pub tetes_kv: u32,
    /// 64, seule valeur admise par le noyau.
    pub dim_tete: u32,
    /// Première position lue (incluse).
    pub debut: u32,
    /// Position courante + 1.
    pub fin: u32,
    /// 0 : cache plein (case = position) ; sinon case = position mod `anneau` (couche à fenêtre).
    pub anneau: u32,
    /// 1/√d (0,125 pour d = 64, exact).
    pub echelle: f32,
    pub reserve: u32,
}

/// Fenêtre glissante de gpt-oss (`attention.sliding_window`) : anneau du cache KV des couches
/// paires (§ 5.6).
pub const FENETRE_GPT_OSS: u32 = 128;

impl ParamsAttention {
    /// Les paramètres de la position `position` (0, 1, …) d'une couche de gpt-oss : couche à
    /// fenêtre (`fenetre` = 128 sur les couches paires) ou pleine (`fenetre` = 0).
    pub fn gpt_oss(position: u32, fenetre: u32) -> ParamsAttention {
        let fin = position + 1;
        let debut = if fenetre > 0 { fin.saturating_sub(fenetre) } else { 0 };
        ParamsAttention { tetes: 64, tetes_kv: 8, dim_tete: 64, debut, fin, anneau: fenetre, echelle: 0.125, reserve: 0 }
    }

    /// Case du cache où s'écrit la position `position` (même règle que le noyau).
    pub fn case(position: u32, anneau: u32) -> u32 {
        if anneau > 0 { position % anneau } else { position }
    }
}

/// Fils par bloc des noyaux de K3 (égaux aux `__launch_bounds__` de `passe.cuh`).
pub const FILS_PASSE: u32 = 256;
pub const FILS_ATTENTION: u32 = 256;
pub const FILS_ARGMAX: u32 = 1024;
/// Positions au plus par appel d'`attention` (mémoire partagée dynamique : 4 o par position, plus
/// 2 304 o fixes, sous les 48 Kio par défaut).
pub const ATTENTION_POSITIONS_MAX: u32 = 8192;
/// Experts au plus et retenus au plus de `routeur_topk` (un warp, huit valeurs par voie).
pub const ROUTEUR_EXPERTS_MAX: u32 = 256;
pub const ROUTEUR_K_MAX: u32 = 8;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tailles_des_structures_partagees() {
        assert_eq!(std::mem::size_of::<DimsExpert>(), 24);
        assert_eq!(std::mem::align_of::<DimsExpert>(), 4);
        assert_eq!(std::mem::size_of::<DescGemv>(), 32);
        assert_eq!(std::mem::size_of::<DescDecodage>(), 32);
        let d = DescDecodage { partie: 1, emplacement: 2 << 8, luts: 3, controle: u64::MAX };
        let o = d.octets();
        assert_eq!(o[0], 1);
        assert_eq!(o[9], 2);
        assert_eq!(o[16], 3);
        assert_eq!(&o[24..32], &[0xFF; 8]);
        // K3 : jumelles de trc::ParamsRope (48 o) et trc::ParamsAttention (32 o).
        assert_eq!(std::mem::size_of::<ParamsRope>(), 48);
        assert_eq!(std::mem::align_of::<ParamsRope>(), 8);
        assert_eq!(std::mem::size_of::<ParamsAttention>(), 32);
        assert_eq!(std::mem::align_of::<ParamsAttention>(), 4);
    }

    #[test]
    fn fenetre_et_cases_de_gpt_oss() {
        let p = ParamsAttention::gpt_oss(0, FENETRE_GPT_OSS);
        assert_eq!((p.debut, p.fin), (0, 1));
        let p = ParamsAttention::gpt_oss(127, FENETRE_GPT_OSS);
        assert_eq!((p.debut, p.fin), (0, 128));
        let p = ParamsAttention::gpt_oss(128, FENETRE_GPT_OSS);
        assert_eq!((p.debut, p.fin), (1, 129));
        let p = ParamsAttention::gpt_oss(4095, 0);
        assert_eq!((p.debut, p.fin, p.anneau), (0, 4096, 0));
        assert_eq!(ParamsAttention::case(129, 128), 1);
        assert_eq!(ParamsAttention::case(129, 0), 129);
    }

    #[test]
    fn disposition_de_gpt_oss_egale_la_specification() {
        // § 5.6 : 4 418 048 o par matrice, 13 254 144 o par emplacement.
        let d = DimsExpert::GPT_OSS;
        let m = disposition_matrice(2880, 2880);
        assert_eq!(m.echelles, 4_147_200);
        assert_eq!(m.biais, 4_406_528);
        assert_eq!(m.pas, 4_418_048);
        assert_eq!(d.taille_emplacement(), 13_254_144);
        assert_eq!(d.disposition(2).base, 2 * 4_418_048);
    }

    #[test]
    fn grilles_de_gpt_oss() {
        // DELTA : 259 200 o = 2 025 macro-pas = 8 tuiles → 2 blocs de 4 warps ;
        // CODES_CTX : 4 147 200 o = 32 400 macro-pas = 127 tuiles → 16 blocs de 8 warps.
        let (g1, g2) = grilles_decodeur(&DimsExpert::GPT_OSS);
        assert_eq!(g1, [2, 3, 1]);
        assert_eq!(g2, [16, 3, 1]);
    }

    #[test]
    fn grilles_lues_dans_la_partie() {
        // Partie minimale : 6 flux (DELTA et CODES_CTX des trois matrices), en-têtes de flux de
        // 16 o dont seul T (décalage 8) compte ici. T(DELTA) = 64 (N = 32), T(CODES) = 127.
        let mut p = vec![0u8; 64 + 16 * 6 + 6 * 16];
        p[10] = 6;
        for (i, (sorte, j, t)) in [(3u8, 0u8, 64u32), (4, 0, 127), (3, 1, 64), (4, 1, 127), (3, 2, 8), (4, 2, 127)].iter().enumerate() {
            let e = 64 + 16 * i;
            let dec = 64 + 16 * 6 + 16 * i;
            p[e] = *sorte;
            p[e + 1] = *j;
            p[e + 4..e + 8].copy_from_slice(&(dec as u32).to_le_bytes());
            p[dec + 8..dec + 12].copy_from_slice(&t.to_le_bytes());
        }
        let (g1, g2) = grilles_depuis_partie(&p).unwrap();
        assert_eq!(g1, [16, 3, 1]); // 64 tuiles, 4 warps par bloc
        assert_eq!(g2, [16, 3, 1]); // 127 tuiles, 8 warps par bloc : comme grilles_decodeur
        assert_eq!(g2, grilles_decodeur(&DimsExpert::GPT_OSS).1);
        // Cassure : un flux manquant est refusé.
        p[64 + 16 * 5] = 0x01;
        assert!(grilles_depuis_partie(&p).is_err());
    }

    #[test]
    fn lut_d_une_table_connue() {
        let mut f = vec![0u16; 256];
        f[3] = 4000;
        f[200] = 96;
        let l = lut_geometrie1(&f).unwrap();
        assert_eq!(l[0], 3 | (3999 << 8));
        assert_eq!(l[3999], 3 | (3999 << 8) | (3999 << 20));
        assert_eq!(l[4000], 200 | (95 << 8));
        assert_eq!(l[4095], 200 | (95 << 8) | (95 << 20));
        // Cassure : une somme fausse est refusée.
        f[3] = 3999;
        assert!(lut_geometrie1(&f).is_err());
    }

    #[test]
    fn symbole_unique_a_frequence_pleine() {
        // f = 4 096 : f − 1 = 4 095 tient dans les 12 bits ; l'état ne bouge pas.
        let mut f = vec![0u16; 256];
        f[7] = 4096;
        let l = lut_geometrie1(&f).unwrap();
        assert_eq!(l[4095], 7 | (4095 << 8) | (4095 << 20));
    }
}
