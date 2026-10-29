//! Témoins des enveloppes de trc-noyaux sur la carte, par le chemin du moteur : image embarquée,
//! chargée par l'API du pilote (trc-cuda), lancée par `Noyaux`.
//!
//! Un expert synthétique aux dimensions de gpt-oss (trois matrices de 2 880 × 2 880) est codé ici
//! par un petit codeur écrit depuis le seul § 4.9 (troisième codeur du projet après celui du lot F
//! et celui du banc C++), décodé sur la carte, et comparé octet à octet à l'emplacement attendu.
//! Les échelles sont tirées dans [117, 123] et les x dans {−2, …, 2} : chaque terme de la GEMV
//! est alors un multiple de 2^-11 d'au plus 0,75, et une ligne de 2 880 termes reste sous 2^12 :
//! 23 bits, la somme est exacte en f32 dans n'importe quel ordre, donc la carte doit égaler au
//! bit la référence du processeur.
//!
//! Cassures : une fente de LUT corrompue → emplacement faux ; un bit retourné dans le flux →
//! voies hors de L.

use trc_cuda::{Contexte, Flux, HoteEpingle, MemoireCarte, copier_vers_carte, copier_vers_hote};
use trc_noyaux::abi::{self, DescDecodage, DescGemv, DimsExpert};
use trc_noyaux::Noyaux;

const M: u64 = 4096;
const L: u64 = 1 << 16;

struct Alea(u64);
impl Alea {
    fn suivant(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
}

/// Fréquences sur 12 bits (somme 4 096) depuis des comptes : arrondi, puis l'écart porté par le
/// symbole le plus fréquent.
fn normaliser(c: &[u64; 256]) -> Option<Vec<u16>> {
    let total: u64 = c.iter().sum();
    if total == 0 {
        return None;
    }
    let mut f: Vec<i64> = c.iter().map(|&n| if n == 0 { 0 } else { ((n as f64 * 4096.0 / total as f64).round() as i64).max(1) }).collect();
    let somme: i64 = f.iter().sum();
    let imax = (0..256).max_by_key(|&i| f[i]).unwrap();
    f[imax] += 4096 - somme;
    assert!(f[imax] >= 1);
    Some(f.iter().map(|&x| x as u16).collect())
}

/// Codeur de géométrie 1 (§ 4.9.2), contexte choisi par le mot de sortie. Rend le flux sérialisé
/// (§ 4.9.1), N = 256.
fn coder_g1(src: &[u8], tables: &[Option<Vec<u16>>], ctx: impl Fn(usize) -> usize) -> Vec<u8> {
    const N: usize = 256;
    let p = src.len();
    assert_eq!(p % 128, 0);
    let cumuls: Vec<Option<Vec<u64>>> = tables
        .iter()
        .map(|t| t.as_ref().map(|f| f.iter().scan(0u64, |a, &x| { let c = *a; *a += x as u64; Some(c) }).collect()))
        .collect();
    let nmacro = p / 128;
    let nt = nmacro.div_ceil(N);
    let (mut debut, mut etats, mut mots) = (Vec::new(), Vec::new(), Vec::<u16>::new());
    for t in 0..nt {
        let (m0, m1) = (t * N, ((t + 1) * N).min(nmacro));
        let mut x = [L; 32];
        let mut pile = Vec::new();
        for m in (m0..m1).rev() {
            for k in (0..4).rev() {
                for v in (0..32).rev() {
                    let w = m * 32 + v;
                    let c = ctx(w);
                    let f = tables[c].as_ref().unwrap();
                    let s = src[w * 4 + k] as usize;
                    let (fs, cs) = (f[s] as u64, cumuls[c].as_ref().unwrap()[s]);
                    assert!(fs > 0);
                    let mut xv = x[v];
                    if xv >= fs << 20 {
                        pile.push((xv & 0xFFFF) as u16);
                        xv >>= 16;
                    }
                    x[v] = (xv / fs) * M + xv % fs + cs;
                }
            }
        }
        debut.push(mots.len() as u32);
        etats.extend(x.iter().map(|&e| e as u32));
        mots.extend(pile.iter().rev());
    }
    let mut o = Vec::new();
    o.extend((p as u32).to_le_bytes());
    o.extend((N as u16).to_le_bytes());
    o.extend([1u8, 0]);
    o.extend((nt as u32).to_le_bytes());
    o.extend((mots.len() as u32).to_le_bytes());
    debut.iter().for_each(|d| o.extend(d.to_le_bytes()));
    etats.iter().for_each(|e| o.extend(e.to_le_bytes()));
    mots.iter().for_each(|w| o.extend(w.to_le_bytes()));
    o.resize(o.len().div_ceil(16) * 16, 0);
    o
}

/// Partie de niveau 0 (§ 4.8) : flux (sorte, matrice, contexte fixe, octets, produits).
fn partie(flux: &[(u8, u8, u8, Vec<u8>, u32)]) -> Vec<u8> {
    let n = flux.len();
    let mut p = (64 + 16 * n).div_ceil(16) * 16;
    let mut dec = Vec::new();
    for f in flux {
        dec.push(p);
        p = (p + f.3.len()).div_ceil(16) * 16;
    }
    let mut o = vec![0u8; p.div_ceil(4096) * 4096];
    o[0..4].copy_from_slice(&0x3043_5254u32.to_le_bytes());
    o[9] = 3;
    o[10..12].copy_from_slice(&(n as u16).to_le_bytes());
    o[12..16].copy_from_slice(&(p as u32).to_le_bytes());
    for (i, f) in flux.iter().enumerate() {
        let e = 64 + 16 * i;
        o[e] = f.0;
        o[e + 1] = f.1;
        o[e + 2] = f.2;
        o[e + 4..e + 8].copy_from_slice(&(dec[i] as u32).to_le_bytes());
        o[e + 8..e + 12].copy_from_slice(&(f.3.len() as u32).to_le_bytes());
        o[e + 12..e + 16].copy_from_slice(&f.4.to_le_bytes());
        o[dec[i]..dec[i] + f.3.len()].copy_from_slice(&f.3);
    }
    o
}

struct Expert {
    attendu: Vec<u8>,
    partie: Vec<u8>,
    partie_brute: Vec<u8>,
    luts: Vec<u32>,
}

fn expert_synthetique(dims: &DimsExpert, graine: u64) -> Expert {
    let mut a = Alea(graine);
    let mut attendu = vec![0u8; dims.taille_emplacement() as usize];
    let (mut flux, mut brut) = (Vec::new(), Vec::new());
    let mut tables_luts: Vec<[Option<Vec<u16>>; 4]> = Vec::new();
    for j in 0..3 {
        let (r, c) = (dims.lignes[j] as usize, dims.colonnes[j] as usize);
        let b = c / 32;
        let nb = r * b;
        // Échelles dans [117, 123], codes de loi inégale (les petites grandeurs plus fréquentes).
        let e: Vec<u8> = (0..nb).map(|_| (117 + a.suivant() % 7) as u8).collect();
        let qs: Vec<u8> = (0..16 * nb)
            .map(|_| {
                let g = |a: &mut Alea| -> u8 { let u = a.suivant() % 100; (if u < 40 { u % 2 } else if u < 80 { 2 + u % 3 } else { 5 + u % 3 }) as u8 | ((a.suivant() & 1) as u8) << 3 };
                g(&mut a) | (g(&mut a) << 4)
            })
            .collect();
        let biais: Vec<u8> = (0..r)
            .flat_map(|_| (((a.suivant() % 2001) as f32 - 1000.0) / 2048.0).to_le_bytes())
            .collect();
        let mut med = vec![0u8; r];
        let (mut delta, mut kappa) = (vec![0u8; nb], vec![0u8; nb]);
        for i in 0..r {
            let mut t = e[i * b..(i + 1) * b].to_vec();
            t.sort();
            med[i] = t[b / 2];
            for k in 0..b {
                let d = e[i * b + k].wrapping_sub(med[i]).wrapping_add(128);
                delta[i * b + k] = d;
                kappa[i * b + k] = if d < 128 { 0 } else if d == 128 { 1 } else { 2 };
            }
        }
        let mut comptes = [[0u64; 256]; 4];
        delta.iter().for_each(|&d| comptes[0][d as usize] += 1);
        for beta in 0..nb {
            for k in 0..16 {
                comptes[1 + kappa[beta] as usize][qs[16 * beta + k] as usize] += 1;
            }
        }
        let tables: [Option<Vec<u16>>; 4] = std::array::from_fn(|t| normaliser(&comptes[t]));
        let fd = coder_g1(&delta, &tables[0..1], |_| 0);
        let fc = coder_g1(&qs, &tables[1..4], |w| kappa[w / 4] as usize);
        let d = dims.disposition(j);
        let base = d.base as usize;
        attendu[base..base + qs.len()].copy_from_slice(&qs);
        attendu[base + d.echelles as usize..base + d.echelles as usize + nb].copy_from_slice(&e);
        attendu[base + d.biais as usize..base + d.biais as usize + 4 * r].copy_from_slice(&biais);
        flux.push((0x01, j as u8, 0xFF, med, r as u32));
        flux.push((0x02, j as u8, 0xFF, biais.clone(), 4 * r as u32));
        flux.push((0x03, j as u8, 0, fd, nb as u32));
        flux.push((0x04, j as u8, 0xFF, fc, 16 * nb as u32));
        brut.push((0x07, j as u8, 0xFF, e, nb as u32));
        brut.push((0x06, j as u8, 0xFF, qs, 16 * nb as u32));
        brut.push((0x02, j as u8, 0xFF, biais, 4 * r as u32));
        tables_luts.push(tables);
    }
    let refs: [[Option<&[u16]>; 4]; 3] =
        std::array::from_fn(|j| std::array::from_fn(|t| tables_luts[j][t].as_deref()));
    Expert { attendu, partie: partie(&flux), partie_brute: partie(&brut), luts: abi::luts_couche(&refs).unwrap() }
}

fn vers_octets(v: &[u32]) -> Vec<u8> {
    v.iter().flat_map(|x| x.to_le_bytes()).collect()
}

struct Banc {
    c: Contexte,
    f: Flux,
    k: Noyaux,
}

impl Banc {
    fn nouveau() -> Banc {
        let c = Contexte::nouveau(0).expect("contexte CUDA");
        let f = Flux::nouveau(&c, false).unwrap();
        let k = Noyaux::charger(&c).expect("chargement de l'image des noyaux");
        Banc { c, f, k }
    }
    fn monter(&self, octets: &[u8]) -> MemoireCarte {
        let mut h = HoteEpingle::allouer(&self.c, octets.len(), false).unwrap();
        h.tranche_mut()[..octets.len()].copy_from_slice(octets);
        let m = MemoireCarte::allouer(&self.c, octets.len()).unwrap();
        copier_vers_carte(m.tout(), &h, 0, octets.len(), &self.f).unwrap();
        self.f.synchroniser().unwrap();
        m
    }
    fn descendre(&self, m: &MemoireCarte, octets: usize) -> Vec<u8> {
        let mut h = HoteEpingle::allouer(&self.c, octets, false).unwrap();
        copier_vers_hote(&mut h, 0, m.vue(0, octets), &self.f).unwrap();
        self.f.synchroniser().unwrap();
        h.tranche()[..octets].to_vec()
    }
}

/// Décode `partie` (ou la copie brute) et rend (emplacement, contrôle).
fn decoder(b: &Banc, partie: &[u8], luts: &[u32], brut: bool) -> (Vec<u8>, [u32; 4]) {
    let dims = DimsExpert::GPT_OSS;
    let te = dims.taille_emplacement() as usize;
    let p = b.monter(partie);
    let l = b.monter(&vers_octets(luts));
    let e = MemoireCarte::allouer(&b.c, te).unwrap();
    e.remplir(e.tout(), 0, &b.f).unwrap();
    let ctl = b.monter(&[0u8; 16]);
    if brut {
        b.k.copier_brut(p.tout(), e.tout(), &dims, ctl.tout(), &b.f).unwrap();
    } else {
        b.k.decoder_expert(p.tout(), e.tout(), l.tout(), &dims, ctl.tout(), &b.f).unwrap();
    }
    b.f.synchroniser().unwrap();
    let c = b.descendre(&ctl, 16);
    (b.descendre(&e, te), std::array::from_fn(|i| u32::from_le_bytes(c[4 * i..4 * i + 4].try_into().unwrap())))
}

#[test]
fn decodeur_exact_et_cassures() {
    let b = Banc::nouveau();
    let ex = expert_synthetique(&DimsExpert::GPT_OSS, 2026_10_15);
    let (empl, ctl) = decoder(&b, &ex.partie, &ex.luts, false);
    assert_eq!(ctl, [0, 0, 0, 0], "contrôle du décodage");
    assert!(empl == ex.attendu, "emplacement décodé différent de l'attendu");

    let (empl, ctl) = decoder(&b, &ex.partie_brute, &ex.luts, true);
    assert_eq!(ctl[1], 0, "format du chemin brut");
    assert!(empl == ex.attendu, "chemin brut différent de l'attendu");

    // Cassure 1 : une fente de la LUT de CODES_CTX (κ = 1, matrice 0) corrompue.
    let mut luts = ex.luts.clone();
    let fente = 4096 + 4096 / 2;
    luts[fente] ^= 1;
    let (empl, _) = decoder(&b, &ex.partie, &luts, false);
    assert!(empl != ex.attendu, "la LUT corrompue n'a rien changé : le témoin ne voit rien");

    // Cassure 2 : un bit retourné au milieu des mots de CODES_CTX de la matrice 1 (flux 7).
    let mut p = ex.partie.clone();
    let e = 64 + 16 * 7;
    let dec = u32::from_le_bytes(p[e + 4..e + 8].try_into().unwrap()) as usize;
    let lon = u32::from_le_bytes(p[e + 8..e + 12].try_into().unwrap()) as usize;
    p[dec + lon / 2] ^= 0x10;
    let (empl, ctl) = decoder(&b, &p, &ex.luts, false);
    assert!(ctl[0] > 0, "un bit de flux retourné doit sortir des voies de L");
    assert!(empl != ex.attendu);

    // Cassure 3 : une partie sans sa magie → erreur de format, rien n'est décodé.
    let mut p = ex.partie.clone();
    p[0] ^= 0xFF;
    let (_, ctl) = decoder(&b, &p, &ex.luts, false);
    assert!(ctl[1] > 0, "une magie fausse doit compter une erreur de format");
}

#[test]
fn decodeur_en_lot_egal_au_seul() {
    // Trois experts de graines différentes, chacun avec ses LUT, décodés en un lot ; le deuxième
    // porte un bit de flux retourné : son contrôle, et lui seul, doit voir des voies hors de L.
    let b = Banc::nouveau();
    let dims = DimsExpert::GPT_OSS;
    let te = dims.taille_emplacement() as usize;
    let ex: Vec<Expert> = (0..3).map(|i| expert_synthetique(&dims, 100 + i)).collect();
    let mut parties: Vec<Vec<u8>> = ex.iter().map(|e| e.partie.clone()).collect();
    let e7 = 64 + 16 * 7;
    let dec = u32::from_le_bytes(parties[1][e7 + 4..e7 + 8].try_into().unwrap()) as usize;
    let lon = u32::from_le_bytes(parties[1][e7 + 8..e7 + 12].try_into().unwrap()) as usize;
    parties[1][dec + lon / 2] ^= 0x10;
    let p: Vec<MemoireCarte> = parties.iter().map(|x| b.monter(x)).collect();
    let l: Vec<MemoireCarte> = ex.iter().map(|e| b.monter(&vers_octets(&e.luts))).collect();
    let empl = MemoireCarte::allouer(&b.c, 3 * te).unwrap();
    empl.remplir(empl.tout(), 0, &b.f).unwrap();
    let ctl = b.monter(&[0u8; 48]);
    let descs: Vec<u8> = (0..3)
        .flat_map(|i| {
            DescDecodage {
                partie: p[i].tout().adresse,
                emplacement: empl.vue(i * te, te).adresse,
                luts: l[i].tout().adresse,
                controle: ctl.vue(16 * i, 16).adresse,
            }
            .octets()
        })
        .collect();
    let dd = b.monter(&descs);
    b.k.decoder_lot(dd.tout(), 3, &dims, &b.f).unwrap();
    b.f.synchroniser().unwrap();
    let tout = b.descendre(&empl, 3 * te);
    let c = b.descendre(&ctl, 48);
    let ctl_de = |i: usize| -> [u32; 4] { std::array::from_fn(|k| u32::from_le_bytes(c[16 * i + 4 * k..16 * i + 4 * k + 4].try_into().unwrap())) };
    for i in [0usize, 2] {
        assert_eq!(ctl_de(i), [0, 0, 0, 0], "contrôle de l'expert {i} du lot");
        assert!(tout[i * te..(i + 1) * te] == ex[i].attendu[..], "expert {i} du lot différent de l'attendu");
        let (seul, _) = decoder(&b, &parties[i], &ex[i].luts, false);
        assert!(seul == tout[i * te..(i + 1) * te], "expert {i} : lot différent du décodage seul");
    }
    assert!(ctl_de(1)[0] > 0, "le bit retourné de l'expert 1 doit sortir des voies de L");
    assert!(tout[te..2 * te] != ex[1].attendu[..]);
    let (seul1, c1) = decoder(&b, &parties[1], &ex[1].luts, false);
    assert!(seul1 == tout[te..2 * te] && c1 == ctl_de(1), "expert corrompu : lot et seul doivent rendre les mêmes octets et compteurs");
}

#[test]
fn gemv_exacte_au_bit_et_lot_egal_au_seul() {
    let b = Banc::nouveau();
    let dims = DimsExpert::GPT_OSS;
    let ex = expert_synthetique(&dims, 7);
    let empl = b.monter(&ex.attendu);
    let mut a = Alea(11);
    let (r, c) = (2880usize, 2880usize);
    let xs: Vec<f32> = (0..3 * c).map(|_| (a.suivant() % 5) as f32 - 2.0).collect();
    let x = b.monter(&xs.iter().flat_map(|v| v.to_le_bytes()).collect::<Vec<u8>>());
    let y = MemoireCarte::allouer(&b.c, 3 * 4 * r).unwrap();
    let y_lot = MemoireCarte::allouer(&b.c, 3 * 4 * r).unwrap();
    let mut descs = Vec::new();
    for j in 0..3 {
        let d = dims.disposition(j);
        let m = empl.vue(d.base as usize, d.pas as usize);
        b.k.gemv(m, x.vue(4 * c * j, 4 * c), y.vue(4 * r * j, 4 * r), r as u32, c as u32, &b.f).unwrap();
        descs.push(DescGemv {
            matrice: m.adresse,
            x: x.vue(4 * c * j, 4 * c).adresse,
            y: y_lot.vue(4 * r * j, 4 * r).adresse,
            lignes: r as u32,
            colonnes: c as u32,
        });
    }
    let octets_desc: Vec<u8> = descs
        .iter()
        .flat_map(|d| {
            let mut v = Vec::new();
            v.extend(d.matrice.to_le_bytes());
            v.extend(d.x.to_le_bytes());
            v.extend(d.y.to_le_bytes());
            v.extend(d.lignes.to_le_bytes());
            v.extend(d.colonnes.to_le_bytes());
            v
        })
        .collect();
    let dd = b.monter(&octets_desc);
    b.k.gemv_lot(dd.tout(), 3, r as u32, &b.f).unwrap();
    b.f.synchroniser().unwrap();
    let ys = b.descendre(&y, 12 * r);
    let yl = b.descendre(&y_lot, 12 * r);
    assert!(ys == yl, "gemv_mxfp4_lot doit rendre les mêmes bits que gemv_mxfp4");

    // Référence exacte (f64, exacte ici ; voir l'en-tête du fichier).
    // Cassure rejouable (juge, § 8 point 2) : TRC_K_CASSER=gemv décale la référence de 1 %.
    let decalage = if std::env::var("TRC_K_CASSER").as_deref() == Ok("gemv") { 1.01 } else { 1.0 };
    let k =[0.0f64, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0];
    let val = |code: u8, e: u8| -> f64 {
        let v = k[(code & 7) as usize] * 2f64.powi(e as i32 - 128);
        if code & 8 != 0 { -v } else { v }
    };
    let mut faux = 0;
    for j in 0..3 {
        let d = dims.disposition(j);
        let mat = &ex.attendu[d.base as usize..];
        for i in 0..r {
            let mut s = 0.0f64;
            for bl in 0..c / 32 {
                let beta = i * (c / 32) + bl;
                let e = mat[d.echelles as usize + beta];
                for t in 0..16 {
                    let q = mat[16 * beta + t];
                    s += val(q & 15, e) * xs[j * c + 32 * bl + t] as f64;
                    s += val(q >> 4, e) * xs[j * c + 32 * bl + 16 + t] as f64;
                }
            }
            let bo = d.biais as usize + 4 * i;
            s += f32::from_le_bytes(mat[bo..bo + 4].try_into().unwrap()) as f64;
            let o = 4 * (j * r + i);
            let g = f32::from_le_bytes(ys[o..o + 4].try_into().unwrap());
            if g.to_bits() != ((s * decalage) as f32).to_bits() {
                faux += 1;
            }
        }
    }
    assert_eq!(faux, 0, "lignes de la GEMV différentes au bit de la référence exacte");
}

/// Lot B (génome synonyme) : `gemv` en mode rapide (`centres_rapides`) sert `gemv_base`, qui lit
/// chaque demi-octet comme symbole de base (bit 3 le signe, bits 0-1 la classe ; le bit 2 n'est
/// pas lu). Centres multiples de 0,5 : chaque terme est un multiple de 2^-12 d'au plus 0,75 et une
/// ligne reste sous 2^12, la somme est exacte en f32 dans tout ordre et la carte doit égaler au bit
/// la référence du processeur. Cassure : le même emplacement en mode exact doit différer ; et
/// retour au mode exact : les bits du mode exact sont ceux d'avant (même fonction de carte).
#[test]
fn gemv_base_exacte_au_bit_et_mode_exact_inchange() {
    let mut b = Banc::nouveau();
    let dims = DimsExpert::GPT_OSS;
    let ex = expert_synthetique(&dims, 7);
    let empl = b.monter(&ex.attendu);
    let mut a = Alea(13);
    let (r, c) = (2880usize, 2880usize);
    let xs: Vec<f32> = (0..c).map(|_| (a.suivant() % 5) as f32 - 2.0).collect();
    let x = b.monter(&xs.iter().flat_map(|v| v.to_le_bytes()).collect::<Vec<u8>>());
    let y = MemoireCarte::allouer(&b.c, 4 * r).unwrap();
    let centres = [0.5f32, 2.5, 6.5, 12.0];
    let d = dims.disposition(1);
    let m = empl.vue(d.base as usize, d.pas as usize);
    let lancer = |b: &Banc| -> Vec<u8> {
        b.k.gemv(m, x.vue(0, 4 * c), y.vue(0, 4 * r), r as u32, c as u32, &b.f).unwrap();
        b.f.synchroniser().unwrap();
        b.descendre(&y, 4 * r)
    };
    let exact_avant = lancer(&b);
    b.k.centres_rapides = Some(centres);
    let rapide = lancer(&b);
    b.k.centres_rapides = None;
    let exact_apres = lancer(&b);
    assert!(exact_avant == exact_apres, "le mode exact doit rendre les mêmes bits avant et après le mode rapide");
    assert!(rapide != exact_avant, "cassure : le mode rapide doit différer du mode exact sur les mêmes octets");
    let val = |code: u8, e: u8| -> f64 {
        let v = centres[(code & 3) as usize] as f64 * 2f64.powi(e as i32 - 128);
        if code & 8 != 0 { -v } else { v }
    };
    let mat = &ex.attendu[d.base as usize..];
    let mut faux = 0;
    for i in 0..r {
        let mut s = 0.0f64;
        for bl in 0..c / 32 {
            let beta = i * (c / 32) + bl;
            let e = mat[d.echelles as usize + beta];
            for t in 0..16 {
                let q = mat[16 * beta + t];
                s += val(q & 15, e) * xs[32 * bl + t] as f64;
                s += val(q >> 4, e) * xs[32 * bl + 16 + t] as f64;
            }
        }
        let bo = d.biais as usize + 4 * i;
        s += f32::from_le_bytes(mat[bo..bo + 4].try_into().unwrap()) as f64;
        let g = f32::from_le_bytes(rapide[4 * i..4 * i + 4].try_into().unwrap());
        if g.to_bits() != (s as f32).to_bits() {
            faux += 1;
        }
    }
    assert_eq!(faux, 0, "lignes de gemv_base différentes au bit de la référence exacte");
}

#[test]
fn enveloppes_refusent_les_tailles_fausses() {
    let b = Banc::nouveau();
    let dims = DimsExpert::GPT_OSS;
    let petit = MemoireCarte::allouer(&b.c, 4096).unwrap();
    let r = b.k.decoder_expert(petit.tout(), petit.tout(), petit.tout(), &dims, petit.tout(), &b.f);
    assert!(r.is_err(), "un emplacement de 4 Kio doit être refusé");
    let r = b.k.gemv(petit.tout(), petit.tout(), petit.tout(), 2880, 2880, &b.f);
    assert!(r.is_err());
    let faux = DimsExpert { lignes: [2880; 3], colonnes: [2880, 2880, 100] };
    assert!(faux.verifier().is_err());
}

/// Proposition A1 du lot A (genome/05-synthese.md § 4.2), mesurée sur la carte : la GEMV lit le
/// code 8 (−0) et le code 0 (+0) en rendant les mêmes bits, pour des x quelconques (mantisses
/// pleines, zéros des deux signes, sommes non exactes). Témoin : l'expert synthétique porte des −0
/// (signe tiré pour toute grandeur, la grandeur 0 comprise) ; on compare l'emplacement d'origine et
/// sa copie canonisée. Cassure : un code 0 de la copie changé en 1, en face d'un x non nul → la
/// ligne diffère.
#[test]
fn gemv_lit_le_code_8_comme_0() {
    let b = Banc::nouveau();
    let dims = DimsExpert::GPT_OSS;
    let ex = expert_synthetique(&dims, 2026_10_17);
    let (r, c) = (2880usize, 2880usize);
    let nb = r * (c / 32);
    let mut canon = ex.attendu.clone();
    let mut n8 = 0u64;
    for j in 0..3 {
        let base = dims.disposition(j).base as usize;
        for q in &mut canon[base..base + 16 * nb] {
            for k in [0u8, 4] {
                if (*q >> k) & 15 == 8 {
                    *q &= !(15 << k);
                    n8 += 1;
                }
            }
        }
    }
    assert!(n8 > 1_000_000, "l'expert synthétique doit porter des −0 ({n8})");
    let mut a = Alea(17);
    let xs: Vec<f32> = (0..3 * c)
        .map(|i| match i % 97 {
            0 => 0.0,
            1 => -0.0,
            _ => {
                let m = (a.suivant() >> 40) as f32 / (1u64 << 24) as f32 + 0.5;
                let e = (a.suivant() % 21) as i32 - 10;
                let s = if a.suivant() & 1 == 1 { -1.0 } else { 1.0 };
                s * m * 2f32.powi(e)
            }
        })
        .collect();
    let x = b.monter(&xs.iter().flat_map(|v| v.to_le_bytes()).collect::<Vec<u8>>());
    let gemv = |octets: &[u8]| -> Vec<u8> {
        let empl = b.monter(octets);
        let y = MemoireCarte::allouer(&b.c, 3 * 4 * r).unwrap();
        for j in 0..3 {
            let d = dims.disposition(j);
            let m = empl.vue(d.base as usize, d.pas as usize);
            b.k.gemv(m, x.vue(4 * c * j, 4 * c), y.vue(4 * r * j, 4 * r), r as u32, c as u32, &b.f).unwrap();
        }
        b.f.synchroniser().unwrap();
        b.descendre(&y, 12 * r)
    };
    let y_origine = gemv(&ex.attendu);
    let y_canon = gemv(&canon);
    let differentes = (0..3 * r).filter(|&i| y_origine[4 * i..4 * i + 4] != y_canon[4 * i..4 * i + 4]).count();
    assert_eq!(differentes, 0, "lignes de la GEMV différentes au bit entre codes d'origine et canoniques ({n8} −0 fondus)");

    // Cassure : premier demi-octet 0 de la ligne 0 de la matrice 0, en face d'un x non nul, mis à 1.
    let mut casse = canon.clone();
    let base = dims.disposition(0).base as usize;
    let i = (0..32usize)
        .find(|&i| {
            let (t, haut) = (i % 16, i >= 16);
            let q = casse[base + t];
            let code = if haut { q >> 4 } else { q & 15 };
            let col = if haut { 16 + t } else { t };
            code == 0 && xs[col] != 0.0
        })
        .expect("un code 0 dans le premier bloc");
    casse[base + i % 16] |= if i >= 16 { 0x10 } else { 0x01 };
    let y_casse = gemv(&casse);
    assert_ne!(y_casse[0..4], y_canon[0..4], "la cassure (un 0 changé en 1) n'a rien changé : le témoin ne voit rien");
    eprintln!("A1 sur la carte : {n8} demi-octets 8 fondus, {} lignes comparées, 0 différente ; cassure vue", 3 * r);
}
