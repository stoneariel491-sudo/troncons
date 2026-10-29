//! Le flux rANS de troncons (decisions/ARCHITECTURE.md § 4.9) : codeur et décodeur sur le
//! processeur, contexte connu du décodeur.
//!
//! Le principe (ANS de Duda, arXiv 1311.2540 ; entrelacement de Giesen, arXiv 1402.3392), posé
//! ici pour ce format, sans reprise de code :
//! - probabilités sur 12 bits (M = 4 096), état x sur 32 bits, borne basse L = 2¹⁶, mots de
//!   16 bits. Après un pas de décodage, x ≥ f · 2⁴ ≥ 16 ; une seule lecture de mot suffit donc
//!   toujours à revenir dans [L, 2³²) ;
//! - 32 voies par tuile, qui partagent un seul flux de mots ; la voie l du macro-pas m produit le
//!   mot de sortie de 32 bits w = m · 32 + l (128 octets contigus par macro-pas) ; ses sous-pas
//!   k produisent, du poids faible au poids fort, l'octet k (géométrie 1, k < 4) ou le
//!   demi-octet k (géométrie 2, k < 8) de ce mot ;
//! - à chaque sous-pas, les voies sont parcourues dans l'ordre 0 à 31 et celles qui
//!   renormalisent lisent des mots consécutifs ;
//! - le codeur parcourt les symboles dans l'ordre exactement inverse, part de x = L sur chaque
//!   voie et renverse sa pile de mots ; le décodeur doit donc finir sur L (contrôle gratuit) et
//!   avoir consommé exactement les mots de sa tuile (second contrôle gratuit, ajouté ici) ;
//! - le contexte d'un symbole (l'indice de sa table) est une fonction connue du décodeur avant
//!   qu'il ne décode ce symbole : la classe d'échelle du bloc (table par voie), ou la base et le
//!   complément déjà décodés (table par symbole). Un contexte `None` est un symbole sauté :
//!   sortie 0, aucun pas, aucun mot.

use crate::ErreurCodec;

pub const BITS_PROBA: u32 = 12;
pub const M: u32 = 1 << BITS_PROBA;
pub const L: u32 = 1 << 16;
pub const VOIES: usize = 32;
/// Octets produits par un macro-pas (32 voies × un mot de 32 bits).
pub const OCTETS_PAR_MACRO: usize = 128;
/// Macro-pas par tuile, N (§ 4.9.1).
pub const MACRO_PAR_TUILE: usize = 256;
/// Géométrie 1 : alphabet octet, 4 sous-pas par mot (v4 de l'étude 03).
pub const GEOMETRIE_OCTET: u8 = 1;
/// Géométrie 2 : alphabet demi-octet, 8 sous-pas par mot (v1 de l'étude 03).
pub const GEOMETRIE_DEMI: u8 = 2;
/// Taille de l'en-tête fixe d'un flux sérialisé.
pub const ENTETE_FLUX: usize = 16;

/// Sous-pas par mot et taille de l'alphabet d'une géométrie.
pub fn sous_pas(geometrie: u8) -> usize {
    match geometrie {
        GEOMETRIE_OCTET => 4,
        GEOMETRIE_DEMI => 8,
        _ => panic!("géométrie {geometrie} inconnue"),
    }
}
pub fn n_symboles(geometrie: u8) -> usize {
    match geometrie {
        GEOMETRIE_OCTET => 256,
        GEOMETRIE_DEMI => 16,
        _ => panic!("géométrie {geometrie} inconnue"),
    }
}

// ---------------------------------------------------------------------------------------------
// La table

/// Une table de fréquences normalisée à M = 4 096, son cumul et sa LUT de décodage (§ 4.9.2).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TableRans {
    pub freq: Vec<u16>,
    pub cumul: Vec<u32>,
    pub lut: Vec<u32>,
    pub geometrie: u8,
}

impl TableRans {
    /// Normalise des comptes à M. Des comptes tous nuls donnent la table où le symbole 0 a
    /// toute la masse (une table jamais lue, mais valide).
    ///
    /// La règle d'arrondi est celle des codeurs de l'étude 03 et de la mesure F1 (le format ne
    /// la fixe pas : les fréquences sont stockées) : chaque compte non nul donne
    /// `max(1, arrondi(c · M / total))`, puis l'écart à M est absorbé :
    /// - géométrie 1 (256 symboles) : une unité à la fois, en parcourant les symboles par
    ///   fréquence décroissante (tri stable), sans descendre sous 1 ;
    /// - géométrie 2 (16 symboles) : en entier par le symbole de plus grande fréquence (le
    ///   dernier en cas d'égalité) ; si cela le ferait descendre sous 1, par la règle de la
    ///   géométrie 1.
    ///
    /// Les mêmes comptes donnent ainsi les mêmes tables, et donc les mêmes octets, que les
    /// outils de 03 et de F1 (témoin d'identité, `tests/identite_03.rs`).
    pub fn depuis_comptes(c: &[u64], geometrie: u8) -> TableRans {
        let n = n_symboles(geometrie);
        assert_eq!(c.len(), n, "{} comptes pour une géométrie à {n} symboles", c.len());
        let mut comptes = c.to_vec();
        if comptes.iter().sum::<u64>() == 0 {
            comptes[0] = 1;
        }
        let total: u64 = comptes.iter().sum();
        let mut freq = vec![0u32; n];
        for i in 0..n {
            if comptes[i] > 0 {
                let f = ((comptes[i] as f64) * (M as f64) / (total as f64)).round() as i64;
                freq[i] = f.max(1) as u32;
            }
        }
        let somme: i64 = freq.iter().map(|&f| f as i64).sum();
        let mut fait = false;
        if geometrie == GEOMETRIE_DEMI {
            let imax = (0..n).max_by_key(|&i| freq[i]).unwrap();
            let corrige = freq[imax] as i64 + (M as i64 - somme);
            if corrige >= 1 {
                freq[imax] = corrige as u32;
                fait = true;
            }
        }
        if !fait {
            let mut somme = somme;
            let mut ordre: Vec<usize> = (0..n).collect();
            ordre.sort_by_key(|&i| std::cmp::Reverse(freq[i]));
            let mut j = 0;
            while somme != M as i64 {
                let i = ordre[j % n];
                if somme > M as i64 && freq[i] > 1 {
                    freq[i] -= 1;
                    somme -= 1;
                } else if somme < M as i64 && freq[i] > 0 {
                    freq[i] += 1;
                    somme += 1;
                }
                j += 1;
            }
        }
        let freq: Vec<u16> = freq.iter().map(|&f| f as u16).collect();
        TableRans::construire(freq, geometrie)
    }

    /// Reprend des fréquences stockées (charge d'une table du fichier) ; refuse une somme
    /// différente de M, une fréquence au-delà de M ou un alphabet de mauvaise taille.
    pub fn depuis_frequences(f: &[u16], geometrie: u8) -> Result<TableRans, ErreurCodec> {
        if geometrie != GEOMETRIE_OCTET && geometrie != GEOMETRIE_DEMI {
            return Err(ErreurCodec::Table(format!("géométrie {geometrie} inconnue")));
        }
        let n = n_symboles(geometrie);
        if f.len() != n {
            return Err(ErreurCodec::Table(format!("{} fréquences pour une géométrie à {n} symboles", f.len())));
        }
        let somme: u32 = f.iter().map(|&x| x as u32).sum();
        if somme != M || f.iter().any(|&x| x as u32 > M) {
            return Err(ErreurCodec::Table(format!("somme des fréquences {somme} au lieu de {M}")));
        }
        Ok(TableRans::construire(f.to_vec(), geometrie))
    }

    fn construire(freq: Vec<u16>, geometrie: u8) -> TableRans {
        let n = freq.len();
        let mut cumul = vec![0u32; n];
        let mut c = 0u32;
        for s in 0..n {
            cumul[s] = c;
            c += freq[s] as u32;
        }
        debug_assert_eq!(c, M);
        let mut lut = vec![0u32; M as usize];
        for s in 0..n {
            let f = freq[s] as u32;
            for i in cumul[s]..cumul[s] + f {
                lut[i as usize] = match geometrie {
                    GEOMETRIE_OCTET => (s as u32) | ((f - 1) << 8) | ((i - cumul[s]) << 20),
                    _ => (s as u32) | (f << 4) | ((i - cumul[s]) << 17),
                };
            }
        }
        TableRans { freq, cumul, lut, geometrie }
    }

    /// Bits par symbole qu'on attend de cette table sur ces comptes.
    pub fn bits_attendus(&self, c: &[u64]) -> f64 {
        let total: u64 = c.iter().sum();
        let mut bits = 0.0;
        for (s, &n) in c.iter().enumerate() {
            if n > 0 {
                bits -= n as f64 * (self.freq[s] as f64 / M as f64).log2();
            }
        }
        bits / total as f64
    }
}

// ---------------------------------------------------------------------------------------------
// Le flux sérialisé (§ 4.9.1)

/// Un flux rANS en mémoire.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FluxRans {
    /// Octets produits P (multiple de 128).
    pub produits: u32,
    pub macro_par_tuile: u16,
    pub geometrie: u8,
    /// Par tuile : indice, dans `mots`, de son premier mot.
    pub debuts: Vec<u32>,
    /// Par tuile : les 32 états initiaux.
    pub etats: Vec<u32>,
    pub mots: Vec<u16>,
}

impl FluxRans {
    pub fn n_tuiles(&self) -> usize {
        self.debuts.len()
    }

    /// Octets du flux sérialisé, bourrage compris.
    pub fn longueur_serialisee(&self) -> usize {
        (ENTETE_FLUX + 4 * self.debuts.len() + 4 * self.etats.len() + 2 * self.mots.len()).div_ceil(16) * 16
    }

    pub fn serialiser(&self) -> Vec<u8> {
        let mut b = Vec::with_capacity(self.longueur_serialisee());
        b.extend_from_slice(&self.produits.to_le_bytes());
        b.extend_from_slice(&self.macro_par_tuile.to_le_bytes());
        b.push(self.geometrie);
        b.push(0);
        b.extend_from_slice(&(self.debuts.len() as u32).to_le_bytes());
        b.extend_from_slice(&(self.mots.len() as u32).to_le_bytes());
        for d in &self.debuts {
            b.extend_from_slice(&d.to_le_bytes());
        }
        for e in &self.etats {
            b.extend_from_slice(&e.to_le_bytes());
        }
        for m in &self.mots {
            b.extend_from_slice(&m.to_le_bytes());
        }
        b.resize(b.len().div_ceil(16) * 16, 0);
        b
    }

    /// Lit un flux sérialisé ; vérifie la cohérence de son en-tête (T = ⌈(P / 128) / N⌉,
    /// longueurs, débuts croissants dans [0, W], réservé nul, bourrage nul).
    pub fn lire(b: &[u8]) -> Result<FluxRans, ErreurCodec> {
        let err = |s: String| ErreurCodec::Flux(s);
        if b.len() < ENTETE_FLUX {
            return Err(err("flux plus court que son en-tête".into()));
        }
        let produits = u32::from_le_bytes(b[0..4].try_into().unwrap());
        let macro_par_tuile = u16::from_le_bytes(b[4..6].try_into().unwrap());
        let geometrie = b[6];
        let n_t = u32::from_le_bytes(b[8..12].try_into().unwrap()) as usize;
        let n_w = u32::from_le_bytes(b[12..16].try_into().unwrap()) as usize;
        if b[7] != 0 {
            return Err(err("octet réservé de l'en-tête de flux non nul".into()));
        }
        if geometrie != GEOMETRIE_OCTET && geometrie != GEOMETRIE_DEMI {
            return Err(err(format!("géométrie {geometrie} inconnue")));
        }
        if produits as usize % OCTETS_PAR_MACRO != 0 || macro_par_tuile == 0 {
            return Err(err(format!("P = {produits} non multiple de 128, ou N = {macro_par_tuile}")));
        }
        let attendu_t = (produits as usize / OCTETS_PAR_MACRO).div_ceil(macro_par_tuile as usize);
        if n_t != attendu_t {
            return Err(err(format!("{n_t} tuiles annoncées, {attendu_t} attendues")));
        }
        let fin = ENTETE_FLUX + 4 * n_t + 4 * VOIES * n_t + 2 * n_w;
        if fin > b.len() {
            return Err(err(format!("flux tronqué : {fin} octets annoncés, {} présents", b.len())));
        }
        if b[fin..].iter().any(|&x| x != 0) {
            return Err(err("bourrage du flux non nul".into()));
        }
        let mut p = ENTETE_FLUX;
        let mut debuts = Vec::with_capacity(n_t);
        for _ in 0..n_t {
            debuts.push(u32::from_le_bytes(b[p..p + 4].try_into().unwrap()));
            p += 4;
        }
        let mut etats = Vec::with_capacity(VOIES * n_t);
        for _ in 0..VOIES * n_t {
            etats.push(u32::from_le_bytes(b[p..p + 4].try_into().unwrap()));
            p += 4;
        }
        let mut mots = Vec::with_capacity(n_w);
        for i in 0..n_w {
            mots.push(u16::from_le_bytes([b[p + 2 * i], b[p + 2 * i + 1]]));
        }
        if debuts.first().is_some_and(|&d| d != 0) || debuts.windows(2).any(|w| w[0] > w[1]) || debuts.last().is_some_and(|&d| d as usize > n_w) {
            return Err(err("débuts de tuile non croissants ou hors du flux".into()));
        }
        Ok(FluxRans { produits, macro_par_tuile, geometrie, debuts, etats, mots })
    }
}

// ---------------------------------------------------------------------------------------------
// Le codeur

#[inline]
fn symbole(source: &[u8], n: usize, geometrie: u8) -> usize {
    if geometrie == GEOMETRIE_OCTET {
        source[n] as usize
    } else {
        ((source[n / 2] >> (4 * (n % 2))) & 15) as usize
    }
}

/// Le cœur du codeur : `source` (P octets, P multiple de 128), contexte du symbole n.
pub fn coder_avec<F: FnMut(usize) -> Option<u8>>(source: &[u8], geometrie: u8, mut contexte: F, tables: &[TableRans]) -> FluxRans {
    assert_eq!(source.len() % OCTETS_PAR_MACRO, 0, "la source doit être bourrée à un multiple de 128 octets");
    assert!(tables.iter().all(|t| t.geometrie == geometrie), "table d'une autre géométrie");
    let spm = sous_pas(geometrie);
    let n_macro = source.len() / OCTETS_PAR_MACRO;
    let n_t = n_macro.div_ceil(MACRO_PAR_TUILE);
    let mut debuts = Vec::with_capacity(n_t);
    let mut etats = Vec::with_capacity(VOIES * n_t);
    let mut mots: Vec<u16> = Vec::new();
    let mut pile: Vec<u16> = Vec::new();
    for t in 0..n_t {
        let m0 = t * MACRO_PAR_TUILE;
        let nb = MACRO_PAR_TUILE.min(n_macro - m0);
        let mut x = [L as u64; VOIES];
        pile.clear();
        for m in (0..nb).rev() {
            for k in (0..spm).rev() {
                for l in (0..VOIES).rev() {
                    let n = ((m0 + m) * VOIES + l) * spm + k;
                    let Some(c) = contexte(n) else { continue };
                    let tb = &tables[c as usize];
                    let s = symbole(source, n, geometrie);
                    let f = tb.freq[s] as u64;
                    assert!(f > 0, "symbole {s} absent de la table du contexte {c} (symbole n° {n})");
                    let mut xv = x[l];
                    if xv >= f << 20 {
                        pile.push((xv & 0xFFFF) as u16);
                        xv >>= 16;
                    }
                    x[l] = ((xv / f) << BITS_PROBA) + (xv % f) + tb.cumul[s] as u64;
                }
            }
        }
        debuts.push(mots.len() as u32);
        etats.extend(x.iter().map(|&v| v as u32));
        mots.extend(pile.iter().rev());
    }
    FluxRans { produits: source.len() as u32, macro_par_tuile: MACRO_PAR_TUILE as u16, geometrie, debuts, etats, mots }
}

/// `source` complétée de zéros jusqu'au multiple de 128 (sans copie si elle l'est déjà).
pub fn bourrer(source: &[u8]) -> std::borrow::Cow<'_, [u8]> {
    if source.len() % OCTETS_PAR_MACRO == 0 {
        std::borrow::Cow::Borrowed(source)
    } else {
        let mut v = source.to_vec();
        v.resize(source.len().div_ceil(OCTETS_PAR_MACRO) * OCTETS_PAR_MACRO, 0);
        std::borrow::Cow::Owned(v)
    }
}

/// Le codeur de la couture (§ 5.4) : rend le flux sérialisé. La source est bourrée de zéros
/// jusqu'au multiple de 128 ; `contexte(n)` donne la table du symbole n (octet n en
/// géométrie 1, demi-octet n en géométrie 2), ou `None` pour un symbole sauté.
/// Panique si un symbole est absent de sa table (erreur du programme appelant).
pub fn coder(source: &[u8], geometrie: u8, contexte: &dyn Fn(usize) -> Option<u8>, tables: &[TableRans]) -> Vec<u8> {
    let s = bourrer(source);
    coder_avec(&s, geometrie, contexte, tables).serialiser()
}

/// Codage à table par voie (CODES_CTX, BASE_CTX) : le contexte de l'octet n est
/// `kappa[n / 16]` (le mot w appartient au bloc ⌊w / 4⌋). Un octet de bourrage au-delà de
/// `kappa` prend le contexte 0 (le δ de bourrage vaut 0, donc κ = 0).
pub fn coder_par_voie(source: &[u8], kappa: &[u8], tables: &[TableRans]) -> FluxRans {
    let s = bourrer(source);
    coder_avec(&s, GEOMETRIE_OCTET, |n| Some(*kappa.get(n / 16).unwrap_or(&0)), tables)
}

// ---------------------------------------------------------------------------------------------
// Le décodeur

/// Ce que le décodage a vu de faux, tuile par tuile (zéro partout pour un flux intègre).
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Bilan {
    /// Voies dont l'état final n'est pas L.
    pub voies_hors_l: u64,
    /// Tuiles dont le nombre de mots consommés diffère du nombre de mots qu'elles portent.
    pub tuiles_mots_faux: u64,
    /// Première tuile fautive, s'il y en a une.
    pub premiere_tuile: Option<u32>,
}

impl Bilan {
    pub fn intact(&self) -> bool {
        self.voies_hors_l == 0 && self.tuiles_mots_faux == 0
    }
}

/// Le cœur du décodeur (§ 4.9.2, normatif) : décode tout le flux dans un tampon de P octets.
/// `contexte(n, sortie)` voit la sortie déjà écrite (pour un contexte qui dépend de symboles
/// déjà décodés). Ne panique sur aucun flux : un contexte sans table est une erreur, un mot
/// manquant se lit 0 et se compte dans le bilan.
pub fn decoder_avec<C: FnMut(usize, &[u8]) -> Option<u8>>(flux: &FluxRans, mut contexte: C, luts: &[&[u32]]) -> Result<(Vec<u8>, Bilan), ErreurCodec> {
    let g = flux.geometrie;
    let spm = sous_pas(g);
    if luts.iter().any(|l| l.len() != M as usize) {
        return Err(ErreurCodec::Table("LUT de taille différente de 4 096".into()));
    }
    let p_octets = flux.produits as usize;
    let n_macro = p_octets / OCTETS_PAR_MACRO;
    let n_t = flux.n_tuiles();
    if flux.etats.len() != VOIES * n_t {
        return Err(ErreurCodec::Flux("nombre d'états différent de 32 × tuiles".into()));
    }
    let mut sortie = vec![0u8; p_octets];
    let mut bilan = Bilan::default();
    let n_par_tuile = flux.macro_par_tuile as usize;
    for t in 0..n_t {
        let m0 = t * n_par_tuile;
        let nb = n_par_tuile.min(n_macro - m0);
        let mut p = flux.debuts[t] as usize;
        let fin = if t + 1 < n_t { flux.debuts[t + 1] as usize } else { flux.mots.len() };
        let mut deborde = false;
        let mut x = [0u32; VOIES];
        x.copy_from_slice(&flux.etats[t * VOIES..(t + 1) * VOIES]);
        for m in 0..nb {
            for k in 0..spm {
                for l in 0..VOIES {
                    let w = (m0 + m) * VOIES + l;
                    let n = w * spm + k;
                    let Some(c) = contexte(n, &sortie) else { continue };
                    let lut = luts.get(c as usize).ok_or_else(|| ErreurCodec::Table(format!("contexte {c} sans table")))?;
                    let xv = x[l];
                    let e = lut[(xv & (M - 1)) as usize];
                    let (s, f, b) = if g == GEOMETRIE_OCTET { (e & 0xFF, ((e >> 8) & 0xFFF) + 1, e >> 20) } else { (e & 0xF, (e >> 4) & 0x1FFF, e >> 17) };
                    let y = f * (xv >> BITS_PROBA) + b;
                    if y < L {
                        let mot = if p < fin {
                            flux.mots[p] as u32
                        } else {
                            deborde = true;
                            0
                        };
                        x[l] = (y << 16) | mot;
                        p += 1;
                    } else {
                        x[l] = y;
                    }
                    if g == GEOMETRIE_OCTET {
                        sortie[n] = s as u8;
                    } else {
                        sortie[n / 2] |= (s as u8) << (4 * (n % 2));
                    }
                }
            }
        }
        let hors = x.iter().filter(|&&v| v != L).count() as u64;
        let mots_faux = deborde || p != fin;
        if hors > 0 || mots_faux {
            bilan.voies_hors_l += hors;
            bilan.tuiles_mots_faux += mots_faux as u64;
            bilan.premiere_tuile.get_or_insert(t as u32);
        }
    }
    Ok((sortie, bilan))
}

fn bilan_en_erreur(b: Bilan) -> Result<(), ErreurCodec> {
    if b.intact() {
        Ok(())
    } else {
        Err(ErreurCodec::Integrite { tuile: b.premiere_tuile.unwrap_or(0), voies_hors_l: b.voies_hors_l, tuiles_mots_faux: b.tuiles_mots_faux })
    }
}

fn verifier_geometries(flux: &FluxRans, tables: &[TableRans]) -> Result<(), ErreurCodec> {
    if tables.iter().any(|t| t.geometrie != flux.geometrie) {
        return Err(ErreurCodec::Table(format!("table d'une autre géométrie que le flux ({})", flux.geometrie)));
    }
    Ok(())
}

/// Le décodeur de la couture (§ 5.4) : lit un flux sérialisé, rend ses P octets. Une voie hors
/// de L, ou une tuile qui ne consomme pas exactement ses mots, est une erreur.
pub fn decoder(flux: &[u8], contexte: &mut dyn FnMut(usize, &[u8]) -> Option<u8>, tables: &[TableRans]) -> Result<Vec<u8>, ErreurCodec> {
    let f = FluxRans::lire(flux)?;
    verifier_geometries(&f, tables)?;
    let luts: Vec<&[u32]> = tables.iter().map(|t| &t.lut[..]).collect();
    let (s, b) = decoder_avec(&f, contexte, &luts)?;
    bilan_en_erreur(b)?;
    Ok(s)
}

/// Décodage à table par voie (CODES_CTX, BASE_CTX), contexte `kappa[n / 16]` (0 au-delà) ; rend
/// aussi le bilan au lieu d'une erreur (pour compter les voies d'une cassure).
pub fn decoder_par_voie(flux: &FluxRans, kappa: &[u8], luts: &[&[u32]]) -> Result<(Vec<u8>, Bilan), ErreurCodec> {
    if flux.geometrie != GEOMETRIE_OCTET {
        return Err(ErreurCodec::Flux("table par voie sur un flux de géométrie 2".into()));
    }
    decoder_avec(flux, |n, _| Some(*kappa.get(n / 16).unwrap_or(&0)), luts)
}

/// Décodage à une seule table (DELTA).
pub fn decoder_une_table(flux: &FluxRans, lut: &[u32]) -> Result<(Vec<u8>, Bilan), ErreurCodec> {
    decoder_avec(flux, |_, _| Some(0), &[lut])
}

pub(crate) fn exiger_intact(b: Bilan) -> Result<(), ErreurCodec> {
    bilan_en_erreur(b)
}
