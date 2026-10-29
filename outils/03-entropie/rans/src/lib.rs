//! rANS entrelacé par sous-groupe pour les codes 4 bits des blocs Q4_K.
//!
//! Le format, dérivé ici depuis le principe de l'ANS (Duda, arXiv 1311.2540) et des
//! codeurs entrelacés (Giesen, arXiv 1402.3392), sans reprise de code :
//!
//! - Probabilités sur 12 bits (M = 4096), état 32 bits, borne basse L = 2^16,
//!   renormalisation par mots de 16 bits. Avec ces valeurs, un décodage demande au plus
//!   un mot : après le pas, x >= f·16 >= 16, et x·2^16 >= 2^20 > L.
//! - Une tuile = 32 voies (un sous-groupe de la carte) × `nb_macro` macro-pas × 8 codes.
//!   La voie `l` du macro-pas `m` produit le mot de 32 bits `m·32 + l` de la tuile : ses
//!   8 demi-octets, du poids faible au poids fort, sont les codes des sous-pas 0..7.
//!   Les 32 voies écrivent donc 128 octets contigus à chaque macro-pas.
//! - Les 32 voies partagent un seul flux de mots. À chaque sous-pas, les voies qui
//!   doivent renormaliser lisent des mots consécutifs, dans l'ordre croissant des voies :
//!   position = pointeur + (nombre de voies d'indice inférieur qui lisent aussi). Sur la
//!   carte, c'est une somme préfixe exclusive du sous-groupe ; sur le processeur, une
//!   simple boucle sur les voies.
//! - Le codeur parcourt les symboles dans l'ordre exactement inverse (macro-pas, sous-pas
//!   et voies décroissants), émet avant de coder, puis renverse la pile de mots.
//! - Chaque voie part de L côté codeur ; le décodeur doit donc finir sur L : c'est le
//!   contrôle d'intégrité gratuit de chaque voie.

pub const BITS_PROBA: u32 = 12;
pub const M: u32 = 1 << BITS_PROBA;
pub const L: u32 = 1 << 16;
pub const VOIES: usize = 32;
pub const CODES_PAR_MOT: usize = 8;

/// Table de fréquences normalisée à M, et table de décodage par fente.
#[derive(Clone)]
pub struct Table {
    pub freq: [u32; 16],
    pub cumul: [u32; 16],
    /// Pour chaque fente : symbole (4 bits) | f << 4 (13 bits) | (fente - cumul) << 17.
    pub lut: Vec<u32>,
}

impl Table {
    pub fn depuis_comptes(comptes: &[u64; 16]) -> Table {
        let total: u64 = comptes.iter().sum();
        assert!(total > 0);
        let mut freq = [0u32; 16];
        for i in 0..16 {
            if comptes[i] > 0 {
                let f = ((comptes[i] as f64) * (M as f64) / (total as f64)).round() as i64;
                freq[i] = f.max(1) as u32;
            }
        }
        // Ajuste la somme à M sur le symbole le plus fréquent.
        let somme: i64 = freq.iter().map(|&f| f as i64).sum();
        let imax = (0..16).max_by_key(|&i| freq[i]).unwrap();
        let corrige = freq[imax] as i64 + (M as i64 - somme);
        assert!(corrige >= 1, "table impossible à normaliser");
        freq[imax] = corrige as u32;
        let mut cumul = [0u32; 16];
        let mut c = 0;
        for i in 0..16 {
            cumul[i] = c;
            c += freq[i];
        }
        assert_eq!(c, M);
        let mut lut = vec![0u32; M as usize];
        for s in 0..16 {
            for fente in cumul[s]..cumul[s] + freq[s] {
                lut[fente as usize] = (s as u32) | (freq[s] << 4) | ((fente - cumul[s]) << 17);
            }
        }
        Table { freq, cumul, lut }
    }

    /// Bits par code attendus avec cette table quantifiée, sur ces comptes.
    pub fn bits_attendus(&self, comptes: &[u64; 16]) -> f64 {
        let total: u64 = comptes.iter().sum();
        let mut bits = 0.0;
        for s in 0..16 {
            if comptes[s] > 0 {
                bits -= comptes[s] as f64 * ((self.freq[s] as f64) / (M as f64)).log2();
            }
        }
        bits / total as f64
    }
}

pub fn entropie(comptes: &[u64; 16]) -> f64 {
    let total: u64 = comptes.iter().sum();
    let mut h = 0.0;
    for &c in comptes {
        if c > 0 {
            let p = c as f64 / total as f64;
            h -= p * p.log2();
        }
    }
    h
}

/// Flux codé : en-têtes de tuiles, états initiaux du décodeur, mots de 16 bits.
pub struct Flux {
    /// Par tuile : (premier mot 16 bits, nb_macro, premier mot 32 bits de sortie, 0).
    pub tuiles: Vec<[u32; 4]>,
    pub etats: Vec<u32>,
    pub mots: Vec<u16>,
    pub octets_source: usize,
}

impl Flux {
    /// Octets à stocker : mots + états + en-têtes (le décalage de sortie se déduit).
    pub fn octets_codes(&self) -> usize {
        self.mots.len() * 2 + self.etats.len() * 4 + self.tuiles.len() * 4
    }
}

#[inline]
fn code_a(source: &[u8], base_octet: usize, m: usize, k: usize, voie: usize) -> u32 {
    let octet = source[base_octet + (m * VOIES + voie) * 4 + k / 2];
    if k % 2 == 0 { (octet & 0x0F) as u32 } else { (octet >> 4) as u32 }
}

/// Code une suite d'octets (deux codes 4 bits par octet). Sa longueur doit être un
/// multiple de 128 (un macro-pas). Une tuile couvre au plus `macro_par_tuile` macro-pas.
pub fn coder(source: &[u8], table: &Table, macro_par_tuile: usize) -> Flux {
    assert_eq!(source.len() % (VOIES * 4), 0);
    let nb_macro_total = source.len() / (VOIES * 4);
    let mut tuiles = Vec::new();
    let mut etats = Vec::new();
    let mut mots: Vec<u16> = Vec::new();
    let mut m0 = 0;
    let mut pile: Vec<u16> = Vec::new();
    while m0 < nb_macro_total {
        let nb = macro_par_tuile.min(nb_macro_total - m0);
        let base = m0 * VOIES * 4;
        let mut x = [L as u64; VOIES];
        pile.clear();
        for m in (0..nb).rev() {
            for k in (0..CODES_PAR_MOT).rev() {
                for voie in (0..VOIES).rev() {
                    let s = code_a(source, base, m, k, voie) as usize;
                    let f = table.freq[s] as u64;
                    debug_assert!(f > 0);
                    let x_max = f << 20; // ((L >> 12) << 16) * f
                    let mut xv = x[voie];
                    if xv >= x_max {
                        pile.push((xv & 0xFFFF) as u16);
                        xv >>= 16;
                    }
                    xv = ((xv / f) << BITS_PROBA) + (xv % f) + table.cumul[s] as u64;
                    x[voie] = xv;
                }
            }
        }
        tuiles.push([mots.len() as u32, nb as u32, (m0 * VOIES) as u32, 0]);
        for v in 0..VOIES {
            debug_assert!(x[v] >= L as u64 && x[v] < (1u64 << 32));
            etats.push(x[v] as u32);
        }
        mots.extend(pile.iter().rev());
        m0 += nb;
    }
    Flux { tuiles, etats, mots, octets_source: source.len() }
}

/// Décode une tuile sur le processeur, dans l'ordre exact du décodeur de la carte.
/// Rend le nombre de voies dont l'état final n'est pas L (0 si tout est intègre).
#[inline]
pub fn decoder_tuile(flux: &Flux, lut: &[u32], t: usize, sortie: &mut [u32]) -> u32 {
    let lut: &[u32; M as usize] = lut.try_into().expect("table de 4096 entrées");
    let [debut, nb, _, _] = flux.tuiles[t];
    let mut x = [0u32; VOIES];
    x.copy_from_slice(&flux.etats[t * VOIES..(t + 1) * VOIES]);
    let mots = &flux.mots[debut as usize..];
    let mut p = 0usize;
    for m in 0..nb as usize {
        let mut acc = [0u32; VOIES];
        for k in 0..CODES_PAR_MOT {
            for v in 0..VOIES {
                let xv = x[v];
                let e = lut[(xv & (M - 1)) as usize];
                let y = ((e >> 4) & 0x1FFF) * (xv >> BITS_PROBA) + (e >> 17);
                acc[v] |= (e & 15) << (4 * k);
                // Sans branche : on lit toujours le mot suivant (la fin du flux est
                // bordée), on ne l'avale que si la voie renormalise.
                let lit = (y < L) as usize;
                let w = *mots.get(p).unwrap_or(&0) as u32;
                x[v] = if lit == 1 { (y << 16) | w } else { y };
                p += lit;
            }
        }
        sortie[m * VOIES..(m + 1) * VOIES].copy_from_slice(&acc);
    }
    x.iter().filter(|&&v| v != L).count() as u32
}

/// Décode tout le flux, en parallèle sur `fils` fils (rayon), dans `sortie` (mots u32).
pub fn decoder_tout(flux: &Flux, lut: &[u32], sortie: &mut [u32], pool: &rayon::ThreadPool) -> u32 {
    use rayon::prelude::*;
    // Découpe la sortie selon les tuiles (contiguës, dans l'ordre).
    let mut morceaux: Vec<(usize, &mut [u32])> = Vec::with_capacity(flux.tuiles.len());
    let mut reste = sortie;
    for (t, tu) in flux.tuiles.iter().enumerate() {
        let n = tu[1] as usize * VOIES;
        let (a, b) = reste.split_at_mut(n);
        morceaux.push((t, a));
        reste = b;
    }
    pool.install(|| {
        morceaux
            .into_par_iter()
            .map(|(t, s)| decoder_tuile(flux, lut, t, s))
            .sum()
    })
}

// ----------------------------------------------------------------------------------
// Lecture GGUF minimale (spécification publique GGUF v3), écrite de zéro.

pub struct InfoTenseur {
    pub nom: String,
    pub type_ggml: u32,
    pub nb_poids: u64,
    pub decalage: u64,
    pub octets: u64,
}

fn lire_u32(b: &[u8], p: &mut usize) -> u32 {
    let v = u32::from_le_bytes(b[*p..*p + 4].try_into().unwrap());
    *p += 4;
    v
}
fn lire_u64(b: &[u8], p: &mut usize) -> u64 {
    let v = u64::from_le_bytes(b[*p..*p + 8].try_into().unwrap());
    *p += 8;
    v
}
fn lire_chaine(b: &[u8], p: &mut usize) -> String {
    let n = lire_u64(b, p) as usize;
    let s = String::from_utf8_lossy(&b[*p..*p + n]).into_owned();
    *p += n;
    s
}
fn sauter_valeur(b: &[u8], p: &mut usize, t: u32) {
    match t {
        0 | 1 | 7 => *p += 1,
        2 | 3 => *p += 2,
        4 | 5 | 6 => *p += 4,
        10 | 11 | 12 => *p += 8,
        8 => {
            lire_chaine(b, p);
        }
        9 => {
            let t2 = lire_u32(b, p);
            let n = lire_u64(b, p);
            for _ in 0..n {
                sauter_valeur(b, p, t2);
            }
        }
        _ => panic!("type de métadonnée inconnu {t}"),
    }
}

/// (poids par bloc, octets par bloc) des types utiles.
pub fn geometrie(t: u32) -> (u64, u64) {
    match t {
        0 => (1, 4),
        1 | 30 => (1, 2),
        8 => (32, 34),
        12 => (256, 144),
        39 => (32, 17),
        13 => (256, 176),
        14 => (256, 210),
        _ => panic!("type ggml {t} non pris en charge"),
    }
}

pub fn lire_entete_gguf(chemin: &str) -> Vec<InfoTenseur> {
    use std::io::Read;
    let mut f = std::fs::File::open(chemin).expect("ouverture du GGUF");
    let mut b = vec![0u8; 32 << 20]; // l'en-tête (vocabulaire compris) tient dans 32 Mio
    let n = f.read(&mut b).unwrap();
    b.truncate(n);
    assert_eq!(&b[0..4], b"GGUF");
    let mut p = 4;
    let _version = lire_u32(&b, &mut p);
    let nb_t = lire_u64(&b, &mut p);
    let nb_k = lire_u64(&b, &mut p);
    let mut alignement = 32u64;
    for _ in 0..nb_k {
        let cle = lire_chaine(&b, &mut p);
        let t = lire_u32(&b, &mut p);
        if cle == "general.alignment" && t == 4 {
            let mut q = p;
            alignement = lire_u32(&b, &mut q) as u64;
        }
        sauter_valeur(&b, &mut p, t);
    }
    let mut infos = Vec::new();
    for _ in 0..nb_t {
        let nom = lire_chaine(&b, &mut p);
        let nd = lire_u32(&b, &mut p);
        let mut n = 1u64;
        for _ in 0..nd {
            n *= lire_u64(&b, &mut p);
        }
        let t = lire_u32(&b, &mut p);
        let dec = lire_u64(&b, &mut p);
        infos.push((nom, t, n, dec));
    }
    let debut = (p as u64).div_ceil(alignement) * alignement;
    infos
        .into_iter()
        .map(|(nom, t, n, dec)| {
            let octets = if t == 0 || t == 1 || t == 30 || t == 8 || (12..=14).contains(&t) || t == 39 {
                let (pb, ob) = geometrie(t);
                n / pb * ob
            } else {
                0
            };
            InfoTenseur { nom, type_ggml: t, nb_poids: n, decalage: debut + dec, octets }
        })
        .collect()
}

/// Lit les octets d'un tenseur.
pub fn lire_tenseur(chemin: &str, t: &InfoTenseur) -> Vec<u8> {
    use std::io::{Read, Seek, SeekFrom};
    let mut f = std::fs::File::open(chemin).unwrap();
    f.seek(SeekFrom::Start(t.decalage)).unwrap();
    let mut v = vec![0u8; t.octets as usize];
    f.read_exact(&mut v).unwrap();
    v
}

/// Sépare un tenseur en (métadonnées, demi-octets) selon son type : Q4_K (16 o de
/// métadonnées puis 128 o de demi-octets par bloc de 144) ou MXFP4 (1 o d'échelle E8M0
/// puis 16 o de demi-octets par bloc de 17).
pub fn separer_blocs(type_ggml: u32, brut: &[u8]) -> (Vec<u8>, Vec<u8>) {
    let (taille, meta) = match type_ggml {
        12 => (144usize, 16usize),
        39 => (17, 1),
        _ => panic!("type {type_ggml} non pris en charge par le codeur"),
    };
    assert_eq!(brut.len() % taille, 0);
    let n = brut.len() / taille;
    let mut m = Vec::with_capacity(n * meta);
    let mut qs = Vec::with_capacity(n * (taille - meta));
    for b in brut.chunks_exact(taille) {
        m.extend_from_slice(&b[..meta]);
        qs.extend_from_slice(&b[meta..]);
    }
    (m, qs)
}

/// Sépare un tenseur Q4_K en (métadonnées 16 o/bloc, demi-octets 128 o/bloc).
pub fn separer_q4k(brut: &[u8]) -> (Vec<u8>, Vec<u8>) {
    assert_eq!(brut.len() % 144, 0);
    let n = brut.len() / 144;
    let mut meta = Vec::with_capacity(n * 16);
    let mut qs = Vec::with_capacity(n * 128);
    for b in brut.chunks_exact(144) {
        meta.extend_from_slice(&b[..16]);
        qs.extend_from_slice(&b[16..]);
    }
    (meta, qs)
}

// ----------------------------------------------------------------------------------
// Variante « octets » : l'alphabet est l'octet entier (deux codes 4 bits), 256 symboles.
// Même géométrie de tuile, mais 4 sous-pas par macro-pas (un octet par sous-pas) : deux
// fois moins de pas de décodage par octet produit. Entrée de table sur 32 bits :
// symbole (8 bits) | (f - 1) << 8 (12 bits) | (fente - cumul) << 20 (12 bits).

pub const OCTETS_PAR_MOT: usize = 4;

#[derive(Clone)]
pub struct Table256 {
    pub freq: Vec<u32>,
    pub cumul: Vec<u32>,
    pub lut: Vec<u32>,
}

impl Table256 {
    pub fn depuis_comptes(comptes: &[u64]) -> Table256 {
        assert_eq!(comptes.len(), 256);
        let total: u64 = comptes.iter().sum();
        let mut freq = vec![0u32; 256];
        for i in 0..256 {
            if comptes[i] > 0 {
                let f = ((comptes[i] as f64) * (M as f64) / (total as f64)).round() as i64;
                freq[i] = f.max(1) as u32;
            }
        }
        // Ajuste la somme à M, en retirant ou ajoutant aux symboles les plus fréquents.
        let mut somme: i64 = freq.iter().map(|&f| f as i64).sum();
        let mut ordre: Vec<usize> = (0..256).collect();
        ordre.sort_by_key(|&i| std::cmp::Reverse(freq[i]));
        let mut j = 0;
        while somme != M as i64 {
            let i = ordre[j % 256];
            if somme > M as i64 && freq[i] > 1 {
                freq[i] -= 1;
                somme -= 1;
            } else if somme < M as i64 && freq[i] > 0 {
                freq[i] += 1;
                somme += 1;
            }
            j += 1;
        }
        let mut cumul = vec![0u32; 256];
        let mut c = 0;
        for i in 0..256 {
            cumul[i] = c;
            c += freq[i];
        }
        let mut lut = vec![0u32; M as usize];
        for s in 0..256 {
            for fente in cumul[s]..cumul[s] + freq[s] {
                lut[fente as usize] = (s as u32) | ((freq[s] - 1) << 8) | ((fente - cumul[s]) << 20);
            }
        }
        Table256 { freq, cumul, lut }
    }

    pub fn bits_attendus(&self, comptes: &[u64]) -> f64 {
        let total: u64 = comptes.iter().sum();
        let mut bits = 0.0;
        for s in 0..256 {
            if comptes[s] > 0 {
                bits -= comptes[s] as f64 * ((self.freq[s] as f64) / (M as f64)).log2();
            }
        }
        bits / total as f64
    }
}

pub fn coder_octets(source: &[u8], table: &Table256, macro_par_tuile: usize) -> Flux {
    assert_eq!(source.len() % (VOIES * 4), 0);
    let nb_macro_total = source.len() / (VOIES * 4);
    let mut tuiles = Vec::new();
    let mut etats = Vec::new();
    let mut mots: Vec<u16> = Vec::new();
    let mut pile: Vec<u16> = Vec::new();
    let mut m0 = 0;
    while m0 < nb_macro_total {
        let nb = macro_par_tuile.min(nb_macro_total - m0);
        let base = m0 * VOIES * 4;
        let mut x = [L as u64; VOIES];
        pile.clear();
        for m in (0..nb).rev() {
            for k in (0..OCTETS_PAR_MOT).rev() {
                for voie in (0..VOIES).rev() {
                    let s = source[base + (m * VOIES + voie) * 4 + k] as usize;
                    let f = table.freq[s] as u64;
                    let mut xv = x[voie];
                    if xv >= f << 20 {
                        pile.push((xv & 0xFFFF) as u16);
                        xv >>= 16;
                    }
                    x[voie] = ((xv / f) << BITS_PROBA) + (xv % f) + table.cumul[s] as u64;
                }
            }
        }
        tuiles.push([mots.len() as u32, nb as u32, (m0 * VOIES) as u32, 0]);
        for v in 0..VOIES {
            etats.push(x[v] as u32);
        }
        mots.extend(pile.iter().rev());
        m0 += nb;
    }
    Flux { tuiles, etats, mots, octets_source: source.len() }
}

#[inline]
pub fn decoder_tuile_octets(flux: &Flux, lut: &[u32], t: usize, sortie: &mut [u32]) -> u32 {
    let lut: &[u32; M as usize] = lut.try_into().expect("table de 4096 entrées");
    let [debut, nb, _, _] = flux.tuiles[t];
    let mut x = [0u32; VOIES];
    x.copy_from_slice(&flux.etats[t * VOIES..(t + 1) * VOIES]);
    let mots = &flux.mots[debut as usize..];
    let mut p = 0usize;
    for m in 0..nb as usize {
        let mut acc = [0u32; VOIES];
        for k in 0..OCTETS_PAR_MOT {
            for v in 0..VOIES {
                let xv = x[v];
                let e = lut[(xv & (M - 1)) as usize];
                let y = (((e >> 8) & 0xFFF) + 1) * (xv >> BITS_PROBA) + (e >> 20);
                acc[v] |= (e & 0xFF) << (8 * k);
                let lit = (y < L) as usize;
                let w = *mots.get(p).unwrap_or(&0) as u32;
                x[v] = if lit == 1 { (y << 16) | w } else { y };
                p += lit;
            }
        }
        sortie[m * VOIES..(m + 1) * VOIES].copy_from_slice(&acc);
    }
    x.iter().filter(|&&v| v != L).count() as u32
}

pub fn decoder_tout_octets(flux: &Flux, lut: &[u32], sortie: &mut [u32], pool: &rayon::ThreadPool) -> u32 {
    use rayon::prelude::*;
    let mut morceaux: Vec<(usize, &mut [u32])> = Vec::with_capacity(flux.tuiles.len());
    let mut reste = sortie;
    for (t, tu) in flux.tuiles.iter().enumerate() {
        let n = tu[1] as usize * VOIES;
        let (a, b) = reste.split_at_mut(n);
        morceaux.push((t, a));
        reste = b;
    }
    pool.install(|| morceaux.into_par_iter().map(|(t, s)| decoder_tuile_octets(flux, lut, t, s)).sum())
}
