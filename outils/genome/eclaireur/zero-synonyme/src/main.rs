//! FOURCHE de `outils/arbitre/decoupe` (la mesure F1, copiée le 2026-10-16) pour l'éclaireur du
//! génome des poids (genome/01-eclaireur.md § 4) : LE CODON SYNONYME DU ZÉRO.
//! Le code MXFP4 a seize codes pour quinze valeurs : +0 (code 0) et −0 (code 8) se déquantifient tous
//! deux en zéro. Avec `--zero-canonique`, tout demi-octet 8 devient 0 AVANT le codage : les poids
//! restent égaux comme nombres réels (K[8] = −0 = K[0]), et tout produit scalaire qui contient un terme
//! non nul rend le même résultat au bit (x + (±0) = x pour x ≠ 0 en IEEE 754). Seuil, déclaré avant :
//! le codon synonyme bat la frontière sans perte si A_ctx (codeur rANS réel, décodage exact du code
//! canonique) descend d'au moins 0,05 bit par poids sous la valeur de F1 (3,8431), soit plus de dix
//! fois l'écart entre deux variantes de format que F1 jugeait égales (A_flux − A_ctx = 0,0003).
//! Témoin : sans le drapeau, l'outil redonne les chiffres de F1 au bit (même octets) ; avec, chaque
//! flux se décode exactement en code canonique. Rien d'autre n'est changé.
//!
//! Mesure F1 de l'arbitre (decisions/ARCHITECTURE.md) : ce que coûte, en octets réels, la
//! découpe d'un code MXFP4 en base + complément, contre le flux unique de l'architecture A.
//!
//! La question, posée par les deux partisans (decisions/partisan-A.md § 4.3,
//! decisions/partisan-B.md § 1.3 et § 6.4) : à l'ordre 0, base + complément coûtent 3,906
//! bits par poids contre 3,8545 pour le flux unique à trois classes d'échelle (+1,33 %),
//! parce que la base a été mesurée sans la classe d'échelle. Conditionnée par cette classe,
//! la découpe devrait rendre presque tout l'écart (règle de la chaîne). Personne ne l'a
//! mesuré avec un codeur réel. C'est ce que fait cet outil, expert par expert, comme le
//! format de fichier le rangera, avec le codeur rANS de l'étude 03 (inclus par chemin, sans
//! copie) et un décodage exact de chaque flux.
//!
//! Variantes, toutes décodées et comparées octet à octet à l'original :
//!   A_flux  le format mesuré par l'étude 03 : trois flux de codes (un par classe d'échelle
//!           du bloc), chacun bourré à 128 octets, réassemblés par δ ;
//!   A_ctx   un seul flux de codes, la table choisie par voie selon la classe d'échelle du
//!           bloc du mot produit (le décodeur connaît δ avant les codes) : même entropie,
//!           ni réassemblage ni somme préfixe ;
//!   B_cond  base (signe + classe de magnitude, en demi-octets à la place du code) en un flux
//!           à table par voie (classe d'échelle), puis complément en un flux à 8 symboles par
//!           mot, la table choisie par symbole selon (classe d'échelle, classe de magnitude),
//!           la classe {6} ne coûtant aucun pas ;
//!   B_mag   le même, complément conditionné par la seule classe de magnitude (proposition
//!           du partisan de B, § 6.2) ;
//!   B_riche (ajoutée après la première passe, qui donnait +0,41 % sur les codes) : le
//!           complément conditionné en plus par la classe du demi-octet voisin et, pour le
//!           demi-octet fort, par le complément faible déjà décodé ; seuil S1bis = S1 ;
//!   brut    le complément empaqueté sans entropie (1 bit, trit par paquets de 5 dans un
//!           octet, rien), pour le critère « rANS seulement s'il gagne au moins 1 % ».
//! Partition des magnitudes E2M1 (étude 07, meilleure à 4 classes) :
//!   {0 ; 0,5} {1 ; 1,5 ; 2} {3 ; 4} {6}.
//!
//! Comptabilité (celle du format) : par flux, 16 octets d'en-tête, 4 octets par tuile
//! (premier mot), 32 états de 4 octets par tuile, les mots de 16 bits, le tout arrondi à 16
//! octets ; tables par tenseur (256 × u16 par table d'octets, 16 × u16 par table de 16
//! symboles) ; médianes de ligne en clair (1 octet par ligne). Les biais (identiques dans
//! toutes les variantes) ne sont pas comptés dans les taux, seulement dans la taille du
//! tronçon.
//!
//! Seuils, déclarés avant le lancement (raisons dans ARCHITECTURE.md, § 3) :
//!   S1  la découpe B_cond est adoptée comme format unique si ses octets (base + complément +
//!       échelles + médianes + tables) ≤ 1,004 × ceux de A_ctx (0,40 % : le coût d'en-tête
//!       d'un flux de plus, mesuré par l'étude 03) ;
//!   S2  A_ctx remplace A_flux dans le format de la v1 si ses octets ≤ ceux de A_flux ;
//!   S3  le complément est codé par rANS si ses octets ≤ 0,99 × ceux de l'empaquetage brut ;
//!   S4  second chemin de l'étude 07 : l'erreur relative de la base (centres de gravité
//!       communs aux 12 tenseurs) égale 0,042919745124980244 à 1e-6 relatif près.
//! Témoins : décodage exact de tous les flux et retour de chaque voie à L ; identité de la
//! chaîne H(code | c) = H(base | c) + H(complément | base, c) à 1e-9 près par tenseur.
//! Cassure (--casser) : le décodeur du complément lit une table où deux fréquences sont
//! échangées (contexte (1, 1)) ; le témoin d'exactitude de B doit tomber, ceux de A tenir.
//!
//! Usage : decoupe-arbitre <gpt-oss-20b.gguf> <sortie.json> [--fils N] [--casser]

#![allow(dead_code)]

#[path = "../../../../03-entropie/rans/src/lib.rs"]
mod rans;

use rans::*;
use rayon::prelude::*;
use std::time::Instant;

const COUCHES: [u32; 4] = [0, 8, 16, 23];
const ROLES: [&str; 3] = ["ffn_gate_exps", "ffn_up_exps", "ffn_down_exps"];
/// Classe de chaque magnitude E2M1 (indice m = code & 7).
const PART: [u8; 8] = [0, 0, 1, 1, 1, 2, 2, 3];
/// Rang de la magnitude dans sa classe (le symbole du complément).
const RANG: [u8; 8] = [0, 1, 0, 1, 2, 0, 1, 0];
/// Taille de l'alphabet du complément par classe de magnitude.
const ALPH: [u8; 4] = [2, 3, 2, 1];
/// Magnitude (indice m) d'après (classe, rang).
const MEMBRE: [[u8; 3]; 4] = [[0, 1, 0], [2, 3, 4], [5, 6, 0], [7, 0, 0]];
/// Magnitudes E2M1 (unités du format, non doublées).
const MAG: [f64; 8] = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0];
const ERREUR_07: f64 = 0.042919745124980244;
const MACRO_PAR_TUILE: usize = 256;

#[inline]
fn base_nib(code: u8) -> u8 {
    (code & 8) | PART[(code & 7) as usize]
}

/// Octets d'un flux tel que le format le range.
fn octets_flux(f: &Flux) -> usize {
    (16 + f.octets_codes()).div_ceil(16) * 16
}

// ---------------------------------------------------------------------------------------
// rANS à table choisie par contexte, géométrie de la v4 (alphabet octet, 4 sous-pas par mot)
// : la voie `l` du macro-pas `m` produit le mot `m·32 + l` ; sa table est `tables[ctx[mot]]`.

fn coder_octets_ctx(source: &[u8], ctx_mot: &[u8], tables: &[Table256]) -> Flux {
    assert_eq!(source.len() % (VOIES * 4), 0);
    let nb_macro_total = source.len() / (VOIES * 4);
    let (mut tuiles, mut etats, mut mots, mut pile) = (Vec::new(), Vec::new(), Vec::<u16>::new(), Vec::<u16>::new());
    let mut m0 = 0;
    while m0 < nb_macro_total {
        let nb = MACRO_PAR_TUILE.min(nb_macro_total - m0);
        let mut x = [L as u64; VOIES];
        pile.clear();
        for m in (0..nb).rev() {
            for k in (0..OCTETS_PAR_MOT).rev() {
                for v in (0..VOIES).rev() {
                    let mot = (m0 + m) * VOIES + v;
                    let t = &tables[ctx_mot[mot] as usize];
                    let s = source[mot * 4 + k] as usize;
                    let f = t.freq[s] as u64;
                    assert!(f > 0);
                    let mut xv = x[v];
                    if xv >= f << 20 {
                        pile.push((xv & 0xFFFF) as u16);
                        xv >>= 16;
                    }
                    x[v] = ((xv / f) << BITS_PROBA) + (xv % f) + t.cumul[s] as u64;
                }
            }
        }
        tuiles.push([mots.len() as u32, nb as u32, (m0 * VOIES) as u32, 0]);
        etats.extend(x.iter().map(|&v| v as u32));
        mots.extend(pile.iter().rev());
        m0 += nb;
    }
    Flux { tuiles, etats, mots, octets_source: source.len() }
}

/// Décode tout le flux ; rend (octets, voies hors de L).
fn decoder_octets_ctx(flux: &Flux, ctx_mot: &[u8], luts: &[Vec<u32>]) -> (Vec<u8>, u32) {
    let mut sortie = vec![0u8; flux.octets_source];
    let mut hors = 0;
    for (t, &[debut, nb, mot0, _]) in flux.tuiles.iter().enumerate() {
        let mut x = [0u32; VOIES];
        x.copy_from_slice(&flux.etats[t * VOIES..(t + 1) * VOIES]);
        let mots = &flux.mots[debut as usize..];
        let mut p = 0usize;
        for m in 0..nb as usize {
            for k in 0..OCTETS_PAR_MOT {
                for v in 0..VOIES {
                    let mot = mot0 as usize + m * VOIES + v;
                    let lut = &luts[ctx_mot[mot] as usize];
                    let xv = x[v];
                    let e = lut[(xv & (M - 1)) as usize];
                    let y = (((e >> 8) & 0xFFF) + 1) * (xv >> BITS_PROBA) + (e >> 20);
                    sortie[mot * 4 + k] = (e & 0xFF) as u8;
                    let lit = y < L;
                    let w = *mots.get(p).unwrap_or(&0) as u32;
                    x[v] = if lit { (y << 16) | w } else { y };
                    p += lit as usize;
                }
            }
        }
        hors += x.iter().filter(|&&v| v != L).count() as u32;
    }
    (sortie, hors)
}

// ---------------------------------------------------------------------------------------
// rANS à table choisie par symbole, géométrie de la v1 (8 symboles de 4 bits par mot) : le
// sous-pas k de la voie l au macro-pas m porte le symbole n = (m·32 + l)·8 + k, de contexte
// ctx[n] ; un contexte dont l'alphabet n'a qu'un symbole (`saut[ctx]`) ne coûte aucun pas.

fn coder_nib_ctx(sym: &[u8], ctx: &[u8], tables: &[Table], saut: &[bool]) -> Flux {
    assert_eq!(sym.len() % (VOIES * 8), 0);
    let nb_macro_total = sym.len() / (VOIES * 8);
    let (mut tuiles, mut etats, mut mots, mut pile) = (Vec::new(), Vec::new(), Vec::<u16>::new(), Vec::<u16>::new());
    let mut m0 = 0;
    while m0 < nb_macro_total {
        let nb = MACRO_PAR_TUILE.min(nb_macro_total - m0);
        let mut x = [L as u64; VOIES];
        pile.clear();
        for m in (0..nb).rev() {
            for k in (0..8).rev() {
                for v in (0..VOIES).rev() {
                    let n = ((m0 + m) * VOIES + v) * 8 + k;
                    let c = ctx[n] as usize;
                    if saut[c] {
                        continue;
                    }
                    let t = &tables[c];
                    let s = sym[n] as usize;
                    let f = t.freq[s] as u64;
                    assert!(f > 0);
                    let mut xv = x[v];
                    if xv >= f << 20 {
                        pile.push((xv & 0xFFFF) as u16);
                        xv >>= 16;
                    }
                    x[v] = ((xv / f) << BITS_PROBA) + (xv % f) + t.cumul[s] as u64;
                }
            }
        }
        tuiles.push([mots.len() as u32, nb as u32, (m0 * VOIES) as u32, 0]);
        etats.extend(x.iter().map(|&v| v as u32));
        mots.extend(pile.iter().rev());
        m0 += nb;
    }
    Flux { tuiles, etats, mots, octets_source: sym.len() / 2 }
}

fn decoder_nib_ctx(flux: &Flux, ctx: &[u8], luts: &[Vec<u32>], saut: &[bool]) -> (Vec<u8>, u32) {
    let mut sortie = vec![0u8; flux.octets_source * 2];
    let mut hors = 0;
    for (t, &[debut, nb, mot0, _]) in flux.tuiles.iter().enumerate() {
        let mut x = [0u32; VOIES];
        x.copy_from_slice(&flux.etats[t * VOIES..(t + 1) * VOIES]);
        let mots = &flux.mots[debut as usize..];
        let mut p = 0usize;
        for m in 0..nb as usize {
            for k in 0..8 {
                for v in 0..VOIES {
                    let n = (mot0 as usize + m * VOIES + v) * 8 + k;
                    let c = ctx[n] as usize;
                    if saut[c] {
                        sortie[n] = 0;
                        continue;
                    }
                    let xv = x[v];
                    let e = luts[c][(xv & (M - 1)) as usize];
                    let y = ((e >> 4) & 0x1FFF) * (xv >> BITS_PROBA) + (e >> 17);
                    sortie[n] = (e & 15) as u8;
                    let lit = y < L;
                    let w = *mots.get(p).unwrap_or(&0) as u32;
                    x[v] = if lit { (y << 16) | w } else { y };
                    p += lit as usize;
                }
            }
        }
        hors += x.iter().filter(|&&v| v != L).count() as u32;
    }
    (sortie, hors)
}

// ---------------------------------------------------------------------------------------
// Complément à contexte riche (variante B_riche, ajoutée après la première passe ; voir l'en-tête
// du JSON) : le contexte du demi-octet n ajoute à (classe d'échelle, classe de magnitude) la
// classe de magnitude du demi-octet voisin du même octet, et, pour le demi-octet de poids fort,
// le complément de poids faible déjà décodé par la même voie au sous-pas précédent :
//   ctx_base(n) = (classe_échelle · 4 + classe(n)) · 4 + classe(n xor 1)
//   ctx(n)      = ctx_base(n) · 4 + (n impair ? 1 + complément(n − 1) : 0).
// Le décodeur connaît la base entière avant le complément ; il calcule ctx(n) au vol.

const N_CTX_RICHE: usize = 3 * 4 * 4 * 4;

fn coder_nib_riche(sym: &[u8], ctx_base: &[u8], classe: &[u8], tables: &[Table]) -> Flux {
    assert_eq!(sym.len() % (VOIES * 8), 0);
    let nb_macro_total = sym.len() / (VOIES * 8);
    let (mut tuiles, mut etats, mut mots, mut pile) = (Vec::new(), Vec::new(), Vec::<u16>::new(), Vec::<u16>::new());
    let mut m0 = 0;
    while m0 < nb_macro_total {
        let nb = MACRO_PAR_TUILE.min(nb_macro_total - m0);
        let mut x = [L as u64; VOIES];
        pile.clear();
        for m in (0..nb).rev() {
            for k in (0..8).rev() {
                for v in (0..VOIES).rev() {
                    let n = ((m0 + m) * VOIES + v) * 8 + k;
                    if ALPH[classe[n] as usize] == 1 {
                        continue;
                    }
                    let c = ctx_base[n] as usize * 4 + if n % 2 == 1 { 1 + sym[n - 1] as usize } else { 0 };
                    let t = &tables[c];
                    let s = sym[n] as usize;
                    let f = t.freq[s] as u64;
                    assert!(f > 0);
                    let mut xv = x[v];
                    if xv >= f << 20 {
                        pile.push((xv & 0xFFFF) as u16);
                        xv >>= 16;
                    }
                    x[v] = ((xv / f) << BITS_PROBA) + (xv % f) + t.cumul[s] as u64;
                }
            }
        }
        tuiles.push([mots.len() as u32, nb as u32, (m0 * VOIES) as u32, 0]);
        etats.extend(x.iter().map(|&v| v as u32));
        mots.extend(pile.iter().rev());
        m0 += nb;
    }
    Flux { tuiles, etats, mots, octets_source: sym.len() / 2 }
}

fn decoder_nib_riche(flux: &Flux, ctx_base: &[u8], classe: &[u8], luts: &[Vec<u32>]) -> (Vec<u8>, u32) {
    let mut sortie = vec![0u8; flux.octets_source * 2];
    let mut hors = 0;
    for (t, &[debut, nb, mot0, _]) in flux.tuiles.iter().enumerate() {
        let mut x = [0u32; VOIES];
        x.copy_from_slice(&flux.etats[t * VOIES..(t + 1) * VOIES]);
        let mots = &flux.mots[debut as usize..];
        let mut p = 0usize;
        for m in 0..nb as usize {
            for k in 0..8 {
                for v in 0..VOIES {
                    let n = (mot0 as usize + m * VOIES + v) * 8 + k;
                    if ALPH[classe[n] as usize] == 1 {
                        sortie[n] = 0;
                        continue;
                    }
                    let c = ctx_base[n] as usize * 4 + if n % 2 == 1 { 1 + sortie[n - 1] as usize } else { 0 };
                    let xv = x[v];
                    let e = luts[c][(xv & (M - 1)) as usize];
                    let y = ((e >> 4) & 0x1FFF) * (xv >> BITS_PROBA) + (e >> 17);
                    sortie[n] = (e & 15) as u8;
                    let lit = y < L;
                    let w = *mots.get(p).unwrap_or(&0) as u32;
                    x[v] = if lit { (y << 16) | w } else { y };
                    p += lit as usize;
                }
            }
        }
        hors += x.iter().filter(|&&v| v != L).count() as u32;
    }
    (sortie, hors)
}

// ---------------------------------------------------------------------------------------

fn histo256(v: &[u8]) -> Vec<u64> {
    let mut h = vec![0u64; 256];
    for &o in v {
        h[o as usize] += 1;
    }
    h
}

/// Table de 16 symboles qui accepte des comptes nuls partout (alphabet de 1 : jamais lue).
fn table16(c: &[u64; 16]) -> Table {
    let mut c2 = *c;
    if c2.iter().sum::<u64>() == 0 {
        c2[0] = 1;
    }
    Table::depuis_comptes(&c2)
}

fn table256(c: &[u64]) -> Table256 {
    let mut c2 = c.to_vec();
    if c2.iter().sum::<u64>() == 0 {
        c2[0] = 1;
    }
    Table256::depuis_comptes(&c2)
}

fn h(c: &[f64]) -> f64 {
    let t: f64 = c.iter().sum();
    if t == 0.0 {
        return 0.0;
    }
    c.iter().filter(|&&x| x > 0.0).map(|&x| { let p = x / t; -p * p.log2() }).sum()
}

/// Dimensions (ne0, ne1, ne2) de chaque tenseur, relues dans l'en-tête GGUF.
fn lire_dims(chemin: &str) -> std::collections::HashMap<String, Vec<u64>> {
    use std::io::Read;
    let mut f = std::fs::File::open(chemin).unwrap();
    let mut b = vec![0u8; 32 << 20];
    let n = f.read(&mut b).unwrap();
    b.truncate(n);
    fn u32_(b: &[u8], p: &mut usize) -> u32 { let v = u32::from_le_bytes(b[*p..*p + 4].try_into().unwrap()); *p += 4; v }
    fn u64_(b: &[u8], p: &mut usize) -> u64 { let v = u64::from_le_bytes(b[*p..*p + 8].try_into().unwrap()); *p += 8; v }
    fn sauter(b: &[u8], p: &mut usize, t: u32) {
        match t {
            0 | 1 | 7 => *p += 1,
            2 | 3 => *p += 2,
            4 | 5 | 6 => *p += 4,
            10 | 11 | 12 => *p += 8,
            8 => { let n = u64_(b, p) as usize; *p += n; }
            9 => { let t2 = u32_(b, p); let n = u64_(b, p); for _ in 0..n { sauter(b, p, t2); } }
            _ => panic!("type {t}"),
        }
    }
    assert_eq!(&b[0..4], b"GGUF");
    let mut p = 4;
    let _v = u32_(&b, &mut p);
    let nt = u64_(&b, &mut p);
    let nk = u64_(&b, &mut p);
    for _ in 0..nk {
        let n = u64_(&b, &mut p) as usize;
        p += n;
        let t = u32_(&b, &mut p);
        sauter(&b, &mut p, t);
    }
    let mut m = std::collections::HashMap::new();
    for _ in 0..nt {
        let n = u64_(&b, &mut p) as usize;
        let nom = String::from_utf8_lossy(&b[p..p + n]).into_owned();
        p += n;
        let nd = u32_(&b, &mut p);
        let dims: Vec<u64> = (0..nd).map(|_| u64_(&b, &mut p)).collect();
        let _t = u32_(&b, &mut p);
        let _d = u64_(&b, &mut p);
        m.insert(nom, dims);
    }
    m
}

/// Ce que rend un expert d'une matrice, dans chaque variante.
#[derive(Default, Clone, Copy)]
struct Octets {
    delta: usize,
    a_flux: usize,
    a_ctx: usize,
    base: usize,
    compl_cond: usize,
    compl_mag: usize,
    compl_brut: usize,
    compl_riche: usize,
    exact_b_riche: bool,
    exact_a_flux: bool,
    exact_a_ctx: bool,
    exact_b_cond: bool,
    exact_b_mag: bool,
    hors_l: u32,
}

impl std::ops::AddAssign for Octets {
    fn add_assign(&mut self, o: Octets) {
        self.delta += o.delta;
        self.a_flux += o.a_flux;
        self.a_ctx += o.a_ctx;
        self.base += o.base;
        self.compl_cond += o.compl_cond;
        self.compl_mag += o.compl_mag;
        self.compl_brut += o.compl_brut;
        self.compl_riche += o.compl_riche;
        self.exact_b_riche &= o.exact_b_riche;
        self.exact_a_flux &= o.exact_a_flux;
        self.exact_a_ctx &= o.exact_a_ctx;
        self.exact_b_cond &= o.exact_b_cond;
        self.exact_b_mag &= o.exact_b_mag;
        self.hors_l += o.hors_l;
    }
}

struct Tables {
    delta: Table256,
    cls: Vec<Table256>,  // codes par classe d'échelle (A_flux et A_ctx)
    base: Vec<Table256>, // octets de base par classe d'échelle
    cond: Vec<Table>,    // complément par (classe d'échelle × 4 + classe de magnitude)
    mag: Vec<Table>,     // complément par classe de magnitude
    riche: Vec<Table>,   // complément, contexte riche (voir contexte_riche)
    lut_cond_lue: Vec<Vec<u32>>, // tables que lit le décodeur (faussée sous --casser)
}

fn traiter_expert(qs: &[u8], delta: &[u8], cl_bloc: &[u8], t: &Tables) -> Octets {
    let mut o = Octets { exact_a_flux: true, exact_a_ctx: true, exact_b_cond: true, exact_b_mag: true, exact_b_riche: true, ..Default::default() };
    let n_blocs = delta.len();
    // δ
    let fd = coder_octets(delta, &t.delta, MACRO_PAR_TUILE);
    o.delta = octets_flux(&fd);
    let mut sd = vec![0u32; delta.len() / 4];
    let mut hors = 0;
    for ti in 0..fd.tuiles.len() {
        let [_, nb, mot0, _] = fd.tuiles[ti];
        hors += decoder_tuile_octets(&fd, &t.delta.lut, ti, &mut sd[mot0 as usize..(mot0 + nb * VOIES as u32) as usize]);
    }
    let sd8: Vec<u8> = sd.iter().flat_map(|w| w.to_le_bytes()).collect();
    let delta_exact = sd8 == delta;
    // A_flux : trois flux de classe, bourrés à 128 octets.
    let mut flux_cl: Vec<Vec<u8>> = vec![Vec::new(); 3];
    for b in 0..n_blocs {
        flux_cl[cl_bloc[b] as usize].extend_from_slice(&qs[b * 16..b * 16 + 16]);
    }
    let mut decodes: Vec<Vec<u8>> = Vec::new();
    for c in 0..3 {
        let mut f = flux_cl[c].clone();
        if f.is_empty() {
            decodes.push(Vec::new());
            continue;
        }
        f.resize(f.len().div_ceil(128) * 128, 0);
        let fl = coder_octets(&f, &t.cls[c], MACRO_PAR_TUILE);
        o.a_flux += octets_flux(&fl);
        let mut s = vec![0u32; f.len() / 4];
        for ti in 0..fl.tuiles.len() {
            let [_, nb, mot0, _] = fl.tuiles[ti];
            hors += decoder_tuile_octets(&fl, &t.cls[c].lut, ti, &mut s[mot0 as usize..(mot0 + nb * VOIES as u32) as usize]);
        }
        decodes.push(s.iter().flat_map(|w| w.to_le_bytes()).collect());
    }
    let mut pos = [0usize; 3];
    let mut ok = delta_exact;
    for b in 0..n_blocs {
        let c = cl_bloc[b] as usize;
        ok &= decodes[c][pos[c]..pos[c] + 16] == qs[b * 16..b * 16 + 16];
        pos[c] += 16;
    }
    o.exact_a_flux = ok;
    // A_ctx : un flux, table par voie selon la classe du bloc (4 mots par bloc).
    let ctx_mot: Vec<u8> = (0..qs.len() / 4).map(|w| cl_bloc[w / 4]).collect();
    let fa = coder_octets_ctx(qs, &ctx_mot, &t.cls);
    o.a_ctx = octets_flux(&fa);
    let luts_cls: Vec<Vec<u32>> = t.cls.iter().map(|x| x.lut.clone()).collect();
    let (sa, ha) = decoder_octets_ctx(&fa, &ctx_mot, &luts_cls);
    hors += ha;
    o.exact_a_ctx = delta_exact && sa == qs;
    // B : base en demi-octets à la place du code, table par voie (classe d'échelle).
    let base: Vec<u8> = qs.iter().map(|&q| base_nib(q & 15) | (base_nib(q >> 4) << 4)).collect();
    let fb = coder_octets_ctx(&base, &ctx_mot, &t.base);
    o.base = octets_flux(&fb);
    let luts_base: Vec<Vec<u32>> = t.base.iter().map(|x| x.lut.clone()).collect();
    let (sb, hb) = decoder_octets_ctx(&fb, &ctx_mot, &luts_base);
    hors += hb;
    let base_exact = sb == base;
    // Complément : symbole par demi-octet n (ordre de la géométrie v1 : octet n/2, demi n%2).
    let n_nib = qs.len() * 2;
    let mut sym = vec![0u8; n_nib];
    let mut ctx_cond = vec![0u8; n_nib];
    let mut ctx_mag = vec![0u8; n_nib];
    let (mut n_bit, mut n_trit) = (0usize, 0usize);
    for n in 0..n_nib {
        let q = qs[n / 2];
        let code = if n % 2 == 0 { q & 15 } else { q >> 4 };
        let m = (code & 7) as usize;
        let k = PART[m];
        sym[n] = RANG[m];
        ctx_mag[n] = k;
        ctx_cond[n] = cl_bloc[n / 32] * 4 + k;
        match ALPH[k as usize] {
            2 => n_bit += 1,
            3 => n_trit += 1,
            _ => {}
        }
    }
    o.compl_brut = (n_bit.div_ceil(8) + n_trit.div_ceil(5)).div_ceil(16) * 16 + 16;
    let saut_cond: Vec<bool> = (0..12).map(|c| ALPH[c % 4] == 1).collect();
    let saut_mag: Vec<bool> = (0..4).map(|c| ALPH[c] == 1).collect();
    let fc = coder_nib_ctx(&sym, &ctx_cond, &t.cond, &saut_cond);
    o.compl_cond = octets_flux(&fc);
    let fm = coder_nib_ctx(&sym, &ctx_mag, &t.mag, &saut_mag);
    o.compl_mag = octets_flux(&fm);
    // Décodage du complément, contexte lu dans la base décodée (sb), puis reconstruction.
    let ctx_de_base = |sb: &[u8], par_classe: bool| -> Vec<u8> {
        (0..n_nib)
            .map(|n| {
                let b = if n % 2 == 0 { sb[n / 2] & 15 } else { sb[n / 2] >> 4 };
                let k = b & 7;
                if par_classe { cl_bloc[n / 32] * 4 + k } else { k }
            })
            .collect()
    };
    let reconstruire = |sb: &[u8], c: &[u8]| -> Vec<u8> {
        (0..qs.len())
            .map(|i| {
                let f = |nb: u8, r: u8| -> u8 { (nb & 8) | MEMBRE[(nb & 7) as usize][r as usize] };
                f(sb[i] & 15, c[2 * i]) | (f(sb[i] >> 4, c[2 * i + 1]) << 4)
            })
            .collect()
    };
    let cc = ctx_de_base(&sb, true);
    let (dc, hc) = decoder_nib_ctx(&fc, &cc, &t.lut_cond_lue, &saut_cond);
    hors += hc;
    o.exact_b_cond = delta_exact && base_exact && reconstruire(&sb, &dc) == qs;
    let cm = ctx_de_base(&sb, false);
    let luts_mag: Vec<Vec<u32>> = t.mag.iter().map(|x| x.lut.clone()).collect();
    let (dm, hm) = decoder_nib_ctx(&fm, &cm, &luts_mag, &saut_mag);
    hors += hm;
    o.exact_b_mag = delta_exact && base_exact && reconstruire(&sb, &dm) == qs;
    // B_riche : contexte riche, calculé du côté du décodeur depuis la base décodée (sb).
    let classe_dec: Vec<u8> = (0..n_nib).map(|n| { let b = if n % 2 == 0 { sb[n / 2] & 15 } else { sb[n / 2] >> 4 }; b & 7 }).collect();
    let ctx_riche: Vec<u8> = (0..n_nib).map(|n| (cl_bloc[n / 32] * 4 + classe_dec[n]) * 4 + classe_dec[n ^ 1]).collect();
    let fr = coder_nib_riche(&sym, &ctx_riche, &ctx_mag, &t.riche);
    o.compl_riche = octets_flux(&fr);
    let luts_riche: Vec<Vec<u32>> = t.riche.iter().map(|x| x.lut.clone()).collect();
    let (dr, hr) = decoder_nib_riche(&fr, &ctx_riche, &classe_dec, &luts_riche);
    hors += hr;
    o.exact_b_riche = delta_exact && base_exact && reconstruire(&sb, &dr) == qs;
    o.hors_l = hors;
    o
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let chemin = &args[1];
    let sortie = &args[2];
    let fils: usize = args.iter().position(|a| a == "--fils").map(|i| args[i + 1].parse().unwrap()).unwrap_or(2);
    let casser = args.iter().any(|a| a == "--casser");
    let zero_canonique = args.iter().any(|a| a == "--zero-canonique");
    let mut demi_octets_changes: u64 = 0;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(fils).build().unwrap();
    let debut_mur = std::process::Command::new("cmd").args(["/c", "echo %date% %time%"]).output().map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string()).unwrap_or_default();
    let t0 = Instant::now();
    let infos = lire_entete_gguf(chemin);
    let dims = lire_dims(chemin);
    let mut lignes = Vec::new();
    let mut tot = Octets { exact_a_flux: true, exact_a_ctx: true, exact_b_cond: true, exact_b_mag: true, exact_b_riche: true, ..Default::default() };
    let (mut tot_poids, mut tot_medianes, mut tot_tables_a, mut tot_tables_b) = (0usize, 0usize, 0usize, 0usize);
    let mut tot_tables_riche = 0usize;
    let mut chaine_max = 0f64;
    // erreurs de la base : énergie par (magnitude) pondérée par 4^(e−128), sommée sur tout
    let mut wm_tot = [0f64; 8];
    let mut erreurs_par_tenseur = Vec::new();
    let mut troncon_a = Vec::<usize>::new(); // octets par (expert) du niveau unique, 3 matrices
    let mut troncon_b0 = Vec::<usize>::new();
    let mut troncon_b1 = Vec::<usize>::new();
    let mut casse_appliquee = false;
    for &c in &COUCHES {
        let mut par_expert_a: Vec<usize> = Vec::new();
        let mut par_expert_b0: Vec<usize> = Vec::new();
        let mut par_expert_b1: Vec<usize> = Vec::new();
        for r in ROLES {
            let nom = format!("blk.{c}.{r}.weight");
            let t = infos.iter().find(|t| t.nom == nom).expect("tenseur absent");
            assert_eq!(t.type_ggml, 39, "{nom} n'est pas en MXFP4");
            let d = &dims[&nom];
            let (ne0, ne1, ne2) = (d[0] as usize, d[1] as usize, d[2] as usize);
            let blocs_ligne = ne0 / 32;
            let brut = lire_tenseur(chemin, t);
            let (ech, mut qs) = separer_blocs(39, &brut);
            if zero_canonique {
                for q in qs.iter_mut() {
                    let (lo, hi) = (*q & 15, *q >> 4);
                    let lo2 = if lo == 8 { 0 } else { lo };
                    let hi2 = if hi == 8 { 0 } else { hi };
                    demi_octets_changes += (lo != lo2) as u64 + (hi != hi2) as u64;
                    *q = lo2 | (hi2 << 4);
                }
            }
            assert_eq!(ech.len(), ne1 * ne2 * blocs_ligne);
            // médianes, δ, classes
            let mut delta = Vec::with_capacity(ech.len());
            let mut cl = Vec::with_capacity(ech.len());
            for ligne in ech.chunks_exact(blocs_ligne) {
                let mut tri = ligne.to_vec();
                tri.sort_unstable();
                let med = tri[tri.len() / 2];
                for &e in ligne {
                    let dd = e.wrapping_sub(med).wrapping_add(128);
                    delta.push(dd);
                    cl.push(((dd as i32 - 128).clamp(-1, 1) + 1) as u8);
                }
            }
            // comptes du tenseur
            let mut h_cls = vec![vec![0u64; 256]; 3];
            let mut h_base = vec![vec![0u64; 256]; 3];
            let mut c_cond = [[0u64; 16]; 12];
            let mut c_mag = [[0u64; 16]; 4];
            let mut c_riche = vec![[0u64; 16]; N_CTX_RICHE];
            // pour l'identité de la chaîne, au demi-octet : n(c, code)
            let mut n_c_code = [[0f64; 16]; 3];
            for b in 0..ech.len() {
                let k = cl[b] as usize;
                for &q in &qs[b * 16..b * 16 + 16] {
                    h_cls[k][q as usize] += 1;
                    h_base[k][(base_nib(q & 15) | (base_nib(q >> 4) << 4)) as usize] += 1;
                    for code in [q & 15, q >> 4] {
                        let m = (code & 7) as usize;
                        c_cond[k * 4 + PART[m] as usize][RANG[m] as usize] += 1;
                        c_mag[PART[m] as usize][RANG[m] as usize] += 1;
                        n_c_code[k][code as usize] += 1.0;
                    }
                }
                for &q in &qs[b * 16..b * 16 + 16] {
                    let (lo, hi) = ((q & 7) as usize, ((q >> 4) & 7) as usize);
                    let (kl, kh) = (PART[lo] as usize, PART[hi] as usize);
                    if ALPH[kl] > 1 {
                        c_riche[((k * 4 + kl) * 4 + kh) * 4][RANG[lo] as usize] += 1;
                    }
                    if ALPH[kh] > 1 {
                        c_riche[((k * 4 + kh) * 4 + kl) * 4 + 1 + RANG[lo] as usize][RANG[hi] as usize] += 1;
                    }
                }
                // énergie par magnitude, domaine réel
                let w = 2f64.powi(2 * (ech[b] as i32 - 128));
                for &q in &qs[b * 16..b * 16 + 16] {
                    for code in [q & 15, q >> 4] {
                        wm_tot[(code & 7) as usize] += w;
                    }
                }
            }
            // identité de la chaîne : H(code | c) = H(base | c) + H(code | base, c)
            let tot_n: f64 = n_c_code.iter().flatten().sum();
            let (mut h_code_c, mut h_base_c, mut h_cond) = (0f64, 0f64, 0f64);
            for k in 0..3 {
                let nk: f64 = n_c_code[k].iter().sum();
                h_code_c += nk / tot_n * h(&n_c_code[k]);
                let mut nb = [0f64; 16];
                for code in 0..16 {
                    nb[base_nib(code as u8) as usize] += n_c_code[k][code];
                }
                h_base_c += nk / tot_n * h(&nb);
                for b in 0..16 {
                    let membres: Vec<f64> = (0..16).filter(|&q| base_nib(q as u8) as usize == b).map(|q| n_c_code[k][q]).collect();
                    let s: f64 = membres.iter().sum();
                    h_cond += s / tot_n * h(&membres);
                }
            }
            chaine_max = chaine_max.max((h_base_c + h_cond - h_code_c).abs());
            // erreurs de ce tenseur : centres communs (07), centres du tenseur, aimantés
            let mut wm = [0f64; 8];
            for b in 0..ech.len() {
                let w = 2f64.powi(2 * (ech[b] as i32 - 128));
                for &q in &qs[b * 16..b * 16 + 16] {
                    wm[(q & 7) as usize] += w;
                    wm[((q >> 4) & 7) as usize] += w;
                }
            }
            let energie: f64 = (0..8).map(|m| wm[m] * MAG[m] * MAG[m]).sum();
            let err_centres = |cent: [f64; 4]| -> f64 { (0..8).map(|m| wm[m] * (MAG[m] - cent[PART[m] as usize]).powi(2)).sum::<f64>() / energie };
            let mut cent_t = [0f64; 4];
            for k in 0..4 {
                let (mut a, mut s) = (0f64, 0f64);
                for m in 0..8 {
                    if PART[m] as usize == k {
                        a += wm[m] * MAG[m];
                        s += wm[m];
                    }
                }
                cent_t[k] = if s > 0.0 { a / s } else { 0.0 };
            }
            erreurs_par_tenseur.push(format!(
                "{{\"nom\": {:?}, \"centres_communs_07\": {:.6}, \"centres_du_tenseur\": {:.6}, \"aimantes_e2m1\": {:.6}, \"centres\": [{:.5}, {:.5}, {:.5}, {:.5}]}}",
                nom, err_centres([0.23715, 1.4243, 3.4186, 6.0]), err_centres(cent_t), err_centres([0.0, 1.5, 3.0, 6.0]),
                cent_t[0], cent_t[1], cent_t[2], cent_t[3]));
            // tables du tenseur
            let tables_cls: Vec<Table256> = h_cls.iter().map(|x| table256(x)).collect();
            let tables_base: Vec<Table256> = h_base.iter().map(|x| table256(x)).collect();
            let tables_cond: Vec<Table> = c_cond.iter().map(table16).collect();
            let tables_mag: Vec<Table> = c_mag.iter().map(table16).collect();
            let tables_riche: Vec<Table> = c_riche.iter().map(table16).collect();
            tot_tables_riche += 512 * 4 + 32 * c_riche.iter().filter(|c| c.iter().sum::<u64>() > 0).count();
            let mut lut_cond_lue: Vec<Vec<u32>> = tables_cond.iter().map(|x| x.lut.clone()).collect();
            if casser && !casse_appliquee {
                // contexte (classe d'échelle 1, classe de magnitude 1) : fréquences 0 et 1 échangées
                let mut c2 = c_cond[4 + 1];
                c2.swap(0, 1);
                lut_cond_lue[4 + 1] = table16(&c2).lut;
                casse_appliquee = true;
            }
            let tabs = Tables { delta: table256(&histo256(&delta)), cls: tables_cls, base: tables_base, cond: tables_cond, mag: tables_mag, riche: tables_riche, lut_cond_lue };
            // tables comptées : δ + 3 (A) ; δ + 3 base + 9 compléments utiles (B_cond)
            tot_tables_a += 512 * 4;
            tot_tables_b += 512 * 4 + 32 * 9;
            let lignes_expert = ne1;
            let blocs_expert = lignes_expert * blocs_ligne;
            let res: Vec<Octets> = pool.install(|| {
                (0..ne2)
                    .into_par_iter()
                    .map(|e| {
                        let b0 = e * blocs_expert;
                        traiter_expert(&qs[b0 * 16..(b0 + blocs_expert) * 16], &delta[b0..b0 + blocs_expert], &cl[b0..b0 + blocs_expert], &tabs)
                    })
                    .collect()
            });
            let mut somme = Octets { exact_a_flux: true, exact_a_ctx: true, exact_b_cond: true, exact_b_mag: true, exact_b_riche: true, ..Default::default() };
            if par_expert_a.is_empty() {
                par_expert_a = vec![0; ne2];
                par_expert_b0 = vec![0; ne2];
                par_expert_b1 = vec![0; ne2];
            }
            let biais = ne1 * 4;
            for (e, o) in res.iter().enumerate() {
                somme += *o;
                par_expert_a[e] += o.delta + o.a_ctx + lignes_expert + biais;
                par_expert_b0[e] += o.delta + o.base + lignes_expert + biais;
                par_expert_b1[e] += o.compl_cond;
            }
            let poids = ne0 * ne1 * ne2;
            let bpp = |x: usize| x as f64 * 8.0 / poids as f64;
            eprintln!(
                "{nom:28} δ {:.4} | A_flux {:.4} | A_ctx {:.4} | base {:.4} | compl cond {:.4} mag {:.4} riche {:.4} brut {:.4} | exacts {} {} {} {} {} | hors L {} | {:.0} s",
                bpp(somme.delta), bpp(somme.a_flux), bpp(somme.a_ctx), bpp(somme.base), bpp(somme.compl_cond), bpp(somme.compl_mag), bpp(somme.compl_riche), bpp(somme.compl_brut),
                somme.exact_a_flux, somme.exact_a_ctx, somme.exact_b_cond, somme.exact_b_mag, somme.exact_b_riche, somme.hors_l, t0.elapsed().as_secs_f64());
            lignes.push(format!(
                "    {{\"nom\": {:?}, \"poids\": {}, \"bpp_delta\": {:.6}, \"bpp_a_flux\": {:.6}, \"bpp_a_ctx\": {:.6}, \"bpp_base\": {:.6}, \"bpp_compl_cond\": {:.6}, \"bpp_compl_mag\": {:.6}, \"bpp_compl_brut\": {:.6}, \"bpp_compl_riche\": {:.6}, \"exact_b_riche\": {}, \"exact_a_flux\": {}, \"exact_a_ctx\": {}, \"exact_b_cond\": {}, \"exact_b_mag\": {}, \"voies_hors_L\": {}}}",
                nom, poids, bpp(somme.delta), bpp(somme.a_flux), bpp(somme.a_ctx), bpp(somme.base), bpp(somme.compl_cond), bpp(somme.compl_mag), bpp(somme.compl_brut), bpp(somme.compl_riche), somme.exact_b_riche,
                somme.exact_a_flux, somme.exact_a_ctx, somme.exact_b_cond, somme.exact_b_mag, somme.hors_l));
            tot += somme;
            tot_poids += poids;
            tot_medianes += ne1 * ne2;
        }
        // en-tête de tronçon (64 o) et table des flux (16 o par flux) ; alignement 4 Kio
        let aligne = |x: usize| x.div_ceil(4096) * 4096;
        for e in 0..par_expert_a.len() {
            troncon_a.push(aligne(64 + 16 * 3 * 4 + par_expert_a[e]));
            troncon_b0.push(aligne(64 + 16 * 3 * 4 + par_expert_b0[e]));
            troncon_b1.push(aligne(64 + 16 * 3 + par_expert_b1[e]));
        }
    }
    // erreur commune aux 12 tenseurs (second chemin de 07)
    let energie: f64 = (0..8).map(|m| wm_tot[m] * MAG[m] * MAG[m]).sum();
    let mut cent = [0f64; 4];
    for k in 0..4 {
        let (mut a, mut s) = (0f64, 0f64);
        for m in 0..8 {
            if PART[m] as usize == k {
                a += wm_tot[m] * MAG[m];
                s += wm_tot[m];
            }
        }
        cent[k] = a / s;
    }
    let err_commune: f64 = (0..8).map(|m| wm_tot[m] * (MAG[m] - cent[PART[m] as usize]).powi(2)).sum::<f64>() / energie;
    let err_aimantee: f64 = (0..8).map(|m| wm_tot[m] * (MAG[m] - [0.0, 1.5, 3.0, 6.0][PART[m] as usize]).powi(2)).sum::<f64>() / energie;
    let bpp = |x: usize| x as f64 * 8.0 / tot_poids as f64;
    let med_b = tot_medianes;
    let total_a_flux = tot.delta + tot.a_flux + med_b + tot_tables_a;
    let total_a_ctx = tot.delta + tot.a_ctx + med_b + tot_tables_a;
    let total_b_cond = tot.delta + tot.base + tot.compl_cond + med_b + tot_tables_b;
    let total_b_mag = tot.delta + tot.base + tot.compl_mag + med_b + tot_tables_b - 32 * 9 * 12 + 32 * 3 * 12;
    let niveau0_b = tot.delta + tot.base + med_b;
    let s1 = total_b_cond as f64 <= 1.004 * total_a_ctx as f64;
    let total_b_riche = tot.delta + tot.base + tot.compl_riche + med_b + tot_tables_riche;
    let s1bis = total_b_riche as f64 <= 1.004 * total_a_ctx as f64;
    let s2 = total_a_ctx <= total_a_flux;
    let s3 = tot.compl_cond as f64 <= 0.99 * tot.compl_brut as f64;
    let s4 = ((err_commune - ERREUR_07) / ERREUR_07).abs() <= 1e-6;
    let exacts = tot.exact_a_flux && tot.exact_a_ctx && tot.exact_b_cond && tot.exact_b_mag && tot.exact_b_riche && tot.hors_l == 0;
    let moy = |v: &[usize]| v.iter().sum::<usize>() as f64 / v.len() as f64;
    let fin_mur = std::process::Command::new("cmd").args(["/c", "echo %date% %time%"]).output().map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string()).unwrap_or_default();
    eprintln!(
        "TOTAL bits/poids (échelles, médianes, tables comprises) : A_flux {:.4}, A_ctx {:.4}, B_cond {:.4} (base {:.4} + compl {:.4}), B_mag {:.4} ; découpe/A_ctx {:.5} ; exacts {} ; chaîne {:.2e} ; erreur commune {:.9} (07 : {:.9}) aimantée {:.6} ; S1 {} S2 {} S3 {} S4 {} ; {:.0} s",
        bpp(total_a_flux), bpp(total_a_ctx), bpp(total_b_cond), bpp(niveau0_b), bpp(tot.compl_cond), bpp(total_b_mag),
        total_b_cond as f64 / total_a_ctx as f64, exacts, chaine_max, err_commune, ERREUR_07, err_aimantee, s1, s2, s3, s4, t0.elapsed().as_secs_f64());
    let json = format!(
        "{{\n  \"outil\": \"outils/genome/eclaireur/zero-synonyme (fourche de outils/arbitre/decoupe)\",\n  \"fichier\": {:?},\n  \"couches\": [0, 8, 16, 23],\n  \"casser\": {},\n  \"zero_canonique\": {},\n  \"demi_octets_changes\": {},\n  \"fils\": {},\n  \"debut_mur\": {:?},\n  \"fin_mur\": {:?},\n  \"duree_s\": {:.1},\n  \"poids\": {},\n  \"bpp\": {{\"a_flux\": {:.6}, \"a_ctx\": {:.6}, \"b_cond\": {:.6}, \"b_mag\": {:.6}, \"niveau0_base\": {:.6}, \"niveau1_compl_cond\": {:.6}, \"compl_mag\": {:.6}, \"compl_brut\": {:.6}, \"delta\": {:.6}, \"medianes\": {:.6}, \"tables_a\": {:.6}, \"tables_b\": {:.6}, \"codes_a_flux\": {:.6}, \"codes_a_ctx\": {:.6}, \"base_seule\": {:.6}}},\n  \"rapport_decoupe_sur_a_ctx\": {:.6},\n  \"rapport_a_ctx_sur_a_flux\": {:.6},\n  \"rapport_compl_rans_sur_brut\": {:.6},\n  \"erreur_base_commune\": {:.12},\n  \"erreur_base_07\": {:.12},\n  \"erreur_base_aimantee\": {:.9},\n  \"centres_communs\": [{:.6}, {:.6}, {:.6}, {:.6}],\n  \"troncon_niveau_unique_A_octets\": {{\"moyen\": {:.1}, \"min\": {}, \"max\": {}}},\n  \"troncon_B_niveau0_octets\": {{\"moyen\": {:.1}, \"min\": {}, \"max\": {}}},\n  \"troncon_B_niveau1_octets\": {{\"moyen\": {:.1}, \"min\": {}, \"max\": {}}},\n  \"temoins\": {{\"tous_exacts\": {}, \"voies_hors_L\": {}, \"exact_a_flux\": {}, \"exact_a_ctx\": {}, \"exact_b_cond\": {}, \"exact_b_mag\": {}, \"ecart_chaine_max\": {:.3e}, \"chaine_tient\": {}}},\n  \"seuils\": {{\"S1_decoupe_format_unique\": {}, \"S2_a_ctx_remplace_a_flux\": {}, \"S3_complement_rans\": {}, \"S4_second_chemin_07\": {}}},\n  \"erreurs_par_tenseur\": [\n    {}\n  ],\n  \"tenseurs\": [\n{}\n  ]\n}}\n",
        chemin, casser, zero_canonique, demi_octets_changes, fils, debut_mur, fin_mur, t0.elapsed().as_secs_f64(), tot_poids,
        bpp(total_a_flux), bpp(total_a_ctx), bpp(total_b_cond), bpp(total_b_mag), bpp(niveau0_b), bpp(tot.compl_cond), bpp(tot.compl_mag), bpp(tot.compl_brut),
        bpp(tot.delta), bpp(med_b), bpp(tot_tables_a), bpp(tot_tables_b), bpp(tot.a_flux), bpp(tot.a_ctx), bpp(tot.base),
        total_b_cond as f64 / total_a_ctx as f64, total_a_ctx as f64 / total_a_flux as f64, tot.compl_cond as f64 / tot.compl_brut as f64,
        err_commune, ERREUR_07, err_aimantee, cent[0], cent[1], cent[2], cent[3],
        moy(&troncon_a), troncon_a.iter().min().unwrap(), troncon_a.iter().max().unwrap(),
        moy(&troncon_b0), troncon_b0.iter().min().unwrap(), troncon_b0.iter().max().unwrap(),
        moy(&troncon_b1), troncon_b1.iter().min().unwrap(), troncon_b1.iter().max().unwrap(),
        exacts, tot.hors_l, tot.exact_a_flux, tot.exact_a_ctx, tot.exact_b_cond, tot.exact_b_mag, chaine_max, chaine_max < 1e-9,
        s1, s2, s3, s4, erreurs_par_tenseur.join(",\n    "), lignes.join(",\n"));
    let riche = format!(
        "  \"b_riche\": {{\"declare\": \"variante et seuil S1bis (même 1,004) ajoutés après la première passe, avant la seconde ; voir ARCHITECTURE.md § 3\", \"bpp_total\": {:.6}, \"bpp_compl\": {:.6}, \"bpp_tables\": {:.6}, \"rapport_sur_a_ctx\": {:.6}, \"exact\": {}, \"S1bis\": {}}},
  \"temoins\": {{",
        bpp(total_b_riche), bpp(tot.compl_riche), bpp(tot_tables_riche), total_b_riche as f64 / total_a_ctx as f64, tot.exact_b_riche, s1bis);
    let json = json.replacen("  \"temoins\": {", &riche, 1);
    eprintln!("B_riche : {:.4} bits/poids, compl {:.4}, rapport {:.5}, exact {}, S1bis {}", bpp(total_b_riche), bpp(tot.compl_riche), total_b_riche as f64 / total_a_ctx as f64, tot.exact_b_riche, s1bis);
    std::fs::write(sortie, json).unwrap();
}
