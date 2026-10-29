//! Témoins de l'étape F1 pour `trc-codec` (ARCHITECTURE.md § 6.5).
//!
//! - identité avec l'étude 03 et la mesure F1 : mêmes comptes → mêmes fréquences, et, pour un
//!   flux à une table, exactement les mêmes états et les mêmes mots que le codeur de 03
//!   (`outils/03-entropie/rans/src/lib.rs`, inclus par chemin, sans copie), en géométrie 1 et 2 ;
//! - aller-retour exact de la couture `coder` / `decoder`, avec contextes par voie, par symbole
//!   dépendant de symboles déjà décodés, sauts, bourrage ;
//! - le chemin rapide par voie égale le chemin générique ;
//! - cassures : table faussée (deux fréquences échangées), mot faussé, état faussé, en-tête de
//!   flux faussé : décodage faux ou refus, jamais une sortie fausse déclarée bonne ;
//! - un expert MXFP4 synthétique codé au format v1.0 se reconstruit au bit près.

#[allow(dead_code, clippy::all)]
#[path = "../../../../outils/03-entropie/rans/src/lib.rs"]
mod rans03;

use trc_codec::rans::*;
use trc_codec::*;

struct Alea(u64);
impl Alea {
    fn suivant(&mut self) -> u64 {
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        self.0.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }
    /// Un symbole de loi géométrique tronquée à `n` (loi resserrée, comme les codes MXFP4).
    fn geom(&mut self, n: u32, p: f64) -> u32 {
        let u = (self.suivant() >> 11) as f64 / (1u64 << 53) as f64;
        (((1.0 - u).ln() / (1.0 - p).ln()) as u32).min(n - 1)
    }
}

fn source_octets(a: &mut Alea, n: usize) -> Vec<u8> {
    (0..n).map(|_| (a.geom(16, 0.3) | (a.geom(16, 0.25) << 4)) as u8).collect()
}

fn comptes(v: &[u8], n: usize) -> Vec<u64> {
    let mut c = vec![0u64; n];
    for &x in v {
        c[x as usize] += 1;
    }
    c
}

fn comptes_demi(v: &[u8]) -> Vec<u64> {
    let mut c = vec![0u64; 16];
    for &x in v {
        c[(x & 15) as usize] += 1;
        c[(x >> 4) as usize] += 1;
    }
    c
}

/// Sérialise un flux de 03 au format du § 4.9.1 (ses tuiles portent le premier mot).
fn serialiser_03(f: &rans03::Flux, geometrie: u8) -> Vec<u8> {
    let fr = FluxRans {
        produits: f.octets_source as u32,
        macro_par_tuile: MACRO_PAR_TUILE as u16,
        geometrie,
        debuts: f.tuiles.iter().map(|t| t[0]).collect(),
        etats: f.etats.clone(),
        mots: f.mots.clone(),
    };
    fr.serialiser()
}

#[test]
fn identite_avec_03_geometrie_octet() {
    let mut a = Alea(1);
    let src = source_octets(&mut a, 128 * 700); // 3 tuiles, la dernière partielle
    let c = comptes(&src, 256);
    let t03 = rans03::Table256::depuis_comptes(&c);
    let t = TableRans::depuis_comptes(&c, GEOMETRIE_OCTET);
    assert_eq!(t.freq.iter().map(|&x| x as u32).collect::<Vec<_>>(), t03.freq);
    assert_eq!(t.lut, t03.lut);
    let f03 = rans03::coder_octets(&src, &t03, MACRO_PAR_TUILE);
    let nous = coder(&src, GEOMETRIE_OCTET, &|_| Some(0), std::slice::from_ref(&t));
    assert_eq!(nous, serialiser_03(&f03, GEOMETRIE_OCTET), "flux différent de celui de 03");
    // Et notre décodeur relit le flux de 03.
    let dec = decoder(&serialiser_03(&f03, GEOMETRIE_OCTET), &mut |_, _| Some(0), std::slice::from_ref(&t)).unwrap();
    assert_eq!(dec, src);
}

#[test]
fn identite_avec_03_geometrie_demi() {
    let mut a = Alea(2);
    let src = source_octets(&mut a, 128 * 300);
    let c = comptes_demi(&src);
    let t03 = rans03::Table::depuis_comptes(&c.clone().try_into().unwrap());
    let t = TableRans::depuis_comptes(&c, GEOMETRIE_DEMI);
    assert_eq!(t.freq.iter().map(|&x| x as u32).collect::<Vec<_>>(), t03.freq.to_vec());
    assert_eq!(t.lut, t03.lut);
    let f03 = rans03::coder(&src, &t03, MACRO_PAR_TUILE);
    let nous = coder(&src, GEOMETRIE_DEMI, &|_| Some(0), std::slice::from_ref(&t));
    assert_eq!(nous, serialiser_03(&f03, GEOMETRIE_DEMI));
    let dec = decoder(&nous, &mut |_, _| Some(0), std::slice::from_ref(&t)).unwrap();
    assert_eq!(dec, src);
}

/// Contexte par voie : κ du bloc de 16 octets.
fn kappa_alea(a: &mut Alea, n_blocs: usize) -> Vec<u8> {
    (0..n_blocs).map(|_| [0u8, 1, 1, 2][(a.suivant() % 4) as usize]).collect()
}

fn tables_par_classe(src: &[u8], kappa: &[u8]) -> Vec<TableRans> {
    let mut c = vec![vec![0u64; 256]; 3];
    for (n, &x) in src.iter().enumerate() {
        c[*kappa.get(n / 16).unwrap_or(&0) as usize][x as usize] += 1;
    }
    c.iter().map(|x| TableRans::depuis_comptes(x, GEOMETRIE_OCTET)).collect()
}

#[test]
fn aller_retour_par_voie_et_chemin_rapide() {
    let mut a = Alea(3);
    for n_blocs in [8usize, 1000, 8 * 2025] {
        let mut src = source_octets(&mut a, 16 * n_blocs);
        let kappa = kappa_alea(&mut a, n_blocs);
        // Les octets d'un bloc de classe 2 sont resserrés vers 0 (comme dans MXFP4).
        for (n, x) in src.iter_mut().enumerate() {
            if kappa[n / 16] == 2 {
                *x &= 0x33;
            }
        }
        let t = tables_par_classe(&src, &kappa);
        let flux = coder(&src, GEOMETRIE_OCTET, &|n| Some(*kappa.get(n / 16).unwrap_or(&0)), &t);
        let dec = decoder(&flux, &mut |n, _| Some(*kappa.get(n / 16).unwrap_or(&0)), &t).unwrap();
        assert_eq!(&dec[..src.len()], &src[..]);
        // Chemin rapide : mêmes octets codés, même sortie.
        let rapide = coder_par_voie(&src, &kappa, &t);
        assert_eq!(rapide.serialiser(), flux);
        let luts: Vec<&[u32]> = t.iter().map(|x| &x.lut[..]).collect();
        let (d2, b) = decoder_par_voie(&rapide, &kappa, &luts).unwrap();
        assert!(b.intact());
        assert_eq!(d2, dec);
    }
}

#[test]
fn bourrage_et_sauts_et_contexte_decode() {
    // Géométrie 2, longueur non multiple de 128, symboles sautés, contexte qui dépend du
    // demi-octet précédent déjà décodé (forme du contexte riche de COMPL_CTX).
    let mut a = Alea(4);
    let n_octets = 128 * 37 + 50;
    let mut src: Vec<u8> = (0..n_octets).map(|_| (a.geom(3, 0.5) | (a.geom(3, 0.5) << 4)) as u8).collect();
    // Symboles sautés : ceux dont l'indice est multiple de 7 valent 0.
    let saute = |n: usize| n % 7 == 0;
    for n in 0..2 * n_octets {
        if saute(n) {
            src[n / 2] &= !(15 << (4 * (n % 2)));
        }
    }
    let demi = |b: &[u8], n: usize| (b[n / 2] >> (4 * (n % 2))) & 15;
    let ctx_codeur = |n: usize| -> Option<u8> {
        if saute(n) {
            None
        } else if n % 2 == 1 && n / 2 < n_octets {
            Some(1 + demi(&src, n - 1))
        } else {
            Some(0)
        }
    };
    let mut c = vec![vec![0u64; 16]; 5];
    let padded = bourrer(&src).into_owned();
    for n in 0..2 * padded.len() {
        if let Some(k) = ctx_codeur(n) {
            c[k as usize][demi(&padded, n) as usize] += 1;
        }
    }
    let t: Vec<TableRans> = c.iter().map(|x| TableRans::depuis_comptes(x, GEOMETRIE_DEMI)).collect();
    let flux = coder(&src, GEOMETRIE_DEMI, &ctx_codeur, &t);
    let mut ctx_dec = |n: usize, sortie: &[u8]| -> Option<u8> {
        if saute(n) {
            None
        } else if n % 2 == 1 && n / 2 < n_octets {
            Some(1 + demi(sortie, n - 1))
        } else {
            Some(0)
        }
    };
    let dec = decoder(&flux, &mut ctx_dec, &t).unwrap();
    assert_eq!(dec.len() % 128, 0);
    assert_eq!(&dec[..n_octets], &src[..]);
    assert!(dec[n_octets..].iter().all(|&x| x == 0));
}

#[test]
fn cassures_tombent() {
    let mut a = Alea(5);
    let n_blocs = 4000;
    let src = source_octets(&mut a, 16 * n_blocs);
    let kappa = kappa_alea(&mut a, n_blocs);
    let t = tables_par_classe(&src, &kappa);
    let flux = coder_par_voie(&src, &kappa, &t);
    let luts: Vec<&[u32]> = t.iter().map(|x| &x.lut[..]).collect();
    let (d, b) = decoder_par_voie(&flux, &kappa, &luts).unwrap();
    assert!(b.intact() && d == src, "l'original doit passer");

    // 1. Table faussée : deux fréquences échangées dans la table de la classe 1.
    let mut f1 = t[1].freq.clone();
    let (i, j) = {
        let mut ordre: Vec<usize> = (0..256).collect();
        ordre.sort_by_key(|&s| std::cmp::Reverse(f1[s]));
        (ordre[0], ordre[1])
    };
    f1.swap(i, j);
    let fausse = TableRans::depuis_frequences(&f1, GEOMETRIE_OCTET).unwrap();
    let luts_f: Vec<&[u32]> = vec![&t[0].lut, &fausse.lut, &t[2].lut];
    let (d, b) = decoder_par_voie(&flux, &kappa, &luts_f).unwrap();
    assert!(d != src, "table faussée : sortie identique");
    assert!(b.voies_hors_l > 0, "table faussée : aucune voie hors de L");
    assert!(decoder(&flux.serialiser(), &mut |n, _| Some(kappa[n / 16]), &[t[0].clone(), fausse.clone(), t[2].clone()]).is_err());

    // 2. Un mot faussé, puis un état faussé.
    let mut f = flux.clone();
    let k = f.mots.len() / 2;
    f.mots[k] ^= 0x0100;
    let (d, b) = decoder_par_voie(&f, &kappa, &luts).unwrap();
    assert!(d != src && !b.intact());
    let mut f = flux.clone();
    f.etats[5] ^= 1;
    let (d, b) = decoder_par_voie(&f, &kappa, &luts).unwrap();
    assert!(d != src && b.voies_hors_l > 0);
    // Un mot de trop à la fin de la dernière tuile : la sortie et les voies restent justes ;
    // seul le second contrôle (mots consommés = mots de la tuile) le voit.
    let mut f = flux.clone();
    f.mots.push(0xABCD);
    let (d, b) = decoder_par_voie(&f, &kappa, &luts).unwrap();
    assert!(d == src && b.voies_hors_l == 0 && b.tuiles_mots_faux == 1, "{b:?}");

    // 3. En-tête de flux faussé : refus.
    let s = flux.serialiser();
    for (pos, nom) in [(0usize, "P"), (7, "réservé"), (8, "T"), (6, "géométrie")] {
        let mut q = s.clone();
        q[pos] ^= 0x41;
        assert!(FluxRans::lire(&q).is_err(), "en-tête faussé accepté : {nom}");
    }
    // Flux tronqué : refus.
    assert!(FluxRans::lire(&s[..s.len() - 64]).is_err());
}

#[test]
fn table_depuis_frequences_refuse() {
    assert!(TableRans::depuis_frequences(&[4096u16; 1], GEOMETRIE_OCTET).is_err());
    let mut f = vec![0u16; 16];
    f[0] = 4095;
    assert!(TableRans::depuis_frequences(&f, GEOMETRIE_DEMI).is_err());
    f[1] = 1;
    assert!(TableRans::depuis_frequences(&f, GEOMETRIE_DEMI).is_ok());
    // Comptes nuls : table valide, tout sur le symbole 0.
    let t = TableRans::depuis_comptes(&[0u64; 256], GEOMETRIE_OCTET);
    assert_eq!(t.freq[0], 4096);
}

/// Un expert MXFP4 synthétique : R lignes, B blocs par ligne, échelles autour d'une médiane.
fn blocs_mxfp4(a: &mut Alea, r: usize, b: usize) -> Vec<u8> {
    let mut v = Vec::with_capacity(17 * r * b);
    for _ in 0..r {
        let med = 118 + (a.suivant() % 4) as u8;
        for _ in 0..b {
            let e = (med as i32 + a.geom(5, 0.5) as i32 - 2) as u8;
            v.push(e);
            for _ in 0..16 {
                v.push((a.geom(16, 0.3) | (a.geom(16, 0.3) << 4)) as u8);
            }
        }
    }
    v
}

#[test]
fn matrice_v10_se_reconstruit() {
    let mut a = Alea(6);
    for (r, b) in [(64usize, 2usize), (90, 3), (2880 / 8, 90)] {
        let blocs: Vec<Vec<u8>> = (0..3).map(|_| blocs_mxfp4(&mut a, r, b)).collect();
        let preps: Vec<PrepaMatrice> = blocs.iter().map(|x| preparer_matrice(x, r, b)).collect();
        let mut cm = ComptesMatrice::default();
        for p in &preps {
            cm.ajouter(p);
        }
        let t = cm.tables();
        for (x, p) in preps.iter().enumerate() {
            let biais: Vec<u8> = (0..4 * r).map(|i| (i * 7 + x) as u8).collect();
            let flux = coder_matrice_v10(p, &biais, &t);
            let fe: Vec<trc_format::FluxAEcrire> = a_ecrire(0, &flux).collect();
            let (partie, utiles) = trc_format::assembler_partie(0, x as u16, 0, 1, &fe);
            let lue = trc_format::lire_partie(&partie).unwrap();
            assert_eq!(lue.utiles, utiles);
            let (m, bd, bc) = decoder_matrice_v10(&lue, 0, r, b, &t).unwrap();
            assert!(bd.intact() && bc.intact());
            assert_eq!(m.blocs_origine(), blocs[x], "matrice ({r}, {b}) expert {x}");
            assert_eq!(m.octets_biais(), biais);
            // Cassure : médiane faussée → échelles fausses.
            let mut q = partie.clone();
            let d = lue.trouver(trc_format::Sorte::Medianes, 0).unwrap();
            q[d.decalage as usize] ^= 1;
            let lue_q = trc_format::lire_partie(&q).unwrap();
            let (mq, _, _) = decoder_matrice_v10(&lue_q, 0, r, b, &t).unwrap();
            assert_ne!(mq.blocs_origine(), blocs[x], "médiane faussée non vue");
        }
    }
}

/// Le codon synonyme du zéro (v1.2) : des blocs dont les zéros portent un signe tiré à pile ou
/// face (comme le MXFP4 de gpt-oss) se codent canonisés, se décodent en l'expert canonique au bit
/// près, ne portent plus aucun demi-octet 8, et coûtent moins de bits que la v1.0.
#[test]
fn matrice_canonique_se_reconstruit_et_gagne() {
    let mut a = Alea(20261017);
    let (r, b) = (2880 / 8, 90);
    let blocs: Vec<Vec<u8>> = (0..3)
        .map(|_| {
            let mut v = blocs_mxfp4(&mut a, r, b);
            // Zéros à signe aléatoire : un demi-octet 0 sur deux devient 8.
            for blk in v.chunks_exact_mut(17) {
                for q in &mut blk[1..] {
                    for k in [0u8, 4] {
                        if (*q >> k) & 15 == 0 && a.suivant() & 1 == 1 {
                            *q |= 8 << k;
                        }
                    }
                }
            }
            v
        })
        .collect();
    let n8: u64 = blocs.iter().map(|x| blocs_canoniques(x).1).sum();
    assert!(n8 > 0, "le jeu d'essai doit porter des −0");
    let mut octets = [0usize; 2];
    for (i, canonique) in [false, true].into_iter().enumerate() {
        let preps: Vec<PrepaMatrice> = blocs.iter().map(|x| preparer_matrice_avec(x, r, b, canonique)).collect();
        let mut cm = ComptesMatrice::default();
        preps.iter().for_each(|p| cm.ajouter(p));
        let t = cm.tables();
        if canonique {
            for k in 0..3 {
                assert!((0..=255u8).all(|s| !trc_format::porte_un_8(s) || t.codes[k].freq[s as usize] == 0), "table canonique κ = {k} avec une fente pour un 8");
            }
        }
        for (x, p) in preps.iter().enumerate() {
            let biais: Vec<u8> = (0..4 * r).map(|i| (i * 3 + x) as u8).collect();
            let flux = coder_matrice_v10(p, &biais, &t);
            octets[i] += flux.iter().filter(|f| f.0 == trc_format::Sorte::CodesCtx).map(|f| f.3.len()).sum::<usize>();
            let fe: Vec<trc_format::FluxAEcrire> = a_ecrire(0, &flux).collect();
            let (partie, _) = trc_format::assembler_partie(0, x as u16, 0, 1, &fe);
            let lue = trc_format::lire_partie(&partie).unwrap();
            let (m, bd, bc) = decoder_matrice_v10(&lue, 0, r, b, &t).unwrap();
            assert!(bd.intact() && bc.intact());
            let attendu = if canonique { blocs_canoniques(&blocs[x]).0 } else { blocs[x].clone() };
            assert_eq!(m.blocs_origine(), attendu, "canonique = {canonique}, expert {x}");
            if canonique {
                assert!(m.codes.iter().all(|&o| !trc_format::porte_un_8(o)));
                assert_ne!(m.blocs_origine(), blocs[x], "le canonique doit différer de l'origine (il y a des −0)");
            }
        }
    }
    // Le gain attendu : chaque −0 fondu retire ≈ 1 bit (pile ou face) ; on exige au moins la
    // moitié de n8 bits, pour laisser les tables et l'arrondi des fréquences.
    let gain_bits = (octets[0] as f64 - octets[1] as f64) * 8.0;
    assert!(gain_bits > 0.5 * n8 as f64, "gain {gain_bits} bits pour {n8} −0 fondus ({} contre {} octets)", octets[1], octets[0]);
}
