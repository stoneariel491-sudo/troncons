//! Témoins de l'étape F1 pour `trc-format` (ARCHITECTURE.md § 6.5) :
//! - aller-retour : un fichier écrit par `Ecrivain` se relit par `Fichier::ouvrir` à
//!   l'identique (en-tête, méta, résidents et leurs données, tables, répertoire, parties) ;
//! - cassure : un octet faussé dans l'en-tête, dans une section ou dans une partie est refusé,
//!   avec l'erreur qui le nomme ; un fichier tronqué est refusé ;
//! - témoin du témoin : la comparaison octet à octet voit un seul octet changé.
//! - v1.2 (codon synonyme du zéro) : un fichier canonique se relit à l'identique, empreinte
//!   canonique comprise ; le drapeau CANONIQUE est refusé sous la v1.1, sur un fichier brut, avec
//!   une table CODES_CTX qui donne une fente à un octet portant un demi-octet 8 ; l'empreinte
//!   canonique non nulle est refusée sans le drapeau ; la v1.3 et le bit 4 sont refusés.

use std::path::{Path, PathBuf};
use trc_format::*;

struct Alea(u64);
impl Alea {
    fn suivant(&mut self) -> u64 {
        // xorshift64* (Vigna), pour des octets reproductibles.
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        self.0.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }
    fn octets(&mut self, n: usize) -> Vec<u8> {
        (0..n).map(|_| (self.suivant() >> 56) as u8).collect()
    }
}

fn dossier() -> PathBuf {
    let d = std::env::temp_dir().join(format!("trc-format-essais-{}", std::process::id()));
    std::fs::create_dir_all(&d).unwrap();
    d
}

struct Construit {
    entete: Entete,
    meta_brute: Vec<u8>,
    residents: Vec<TenseurResident>,
    donnees: Vec<Vec<u8>>,
    tables: Vec<Table>,
    repertoire: Vec<EntreeRepertoire>,
    parties: Vec<Vec<u8>>,
}

fn entete_type() -> Entete {
    Entete {
        version: (1, 0),
        drapeaux: DRAPEAU_ALIGNE,
        taille_fichier: 0,
        sha256_source: [7u8; 32],
        taille_source: 123_456_789,
        couches: 2,
        experts: 3,
        k: 2,
        matrices: 3,
        lignes: [64, 64, 32, 0],
        colonnes: [64, 64, 64, 0],
        poids_par_bloc: 32,
        octets_par_bloc: 17,
        type_ggml: 39,
        niveaux: 1,
        classes_echelle: 3,
        partition: [0; 8],
        sections: [Section::default(); 8],
    }
}

/// Écrit un petit fichier complet et rend ce qui y a été mis.
fn ecrire(chemin: &Path) -> Construit {
    ecrire_avec(chemin, false, false)
}

/// En-tête v1.2 à codes canoniques.
fn entete_canonique() -> Entete {
    let mut e = entete_type();
    e.version = (1, 2);
    e.drapeaux |= DRAPEAU_CANONIQUE;
    e
}

/// Le même fichier, en v1.2 canonique si `canonique` (empreintes canoniques tirées), et avec une
/// fréquence non nulle à l'octet 0x08 dans les tables CODES_CTX si `table_8`.
fn ecrire_avec(chemin: &Path, canonique: bool, table_8: bool) -> Construit {
    let mut a = Alea(0x9E37_79B9_7F4A_7C15);
    let mut w = Ecrivain::creer(chemin).unwrap();
    // MÉTA : une chaîne, un u32, un tableau de chaînes, plus une paire ajoutée.
    let mut brute = paire_chaine("general.architecture", "essai");
    brute.extend_from_slice(&(15u64).to_le_bytes());
    brute.extend_from_slice(b"essai.couches_x");
    brute.extend_from_slice(&4u32.to_le_bytes());
    brute.extend_from_slice(&2u32.to_le_bytes());
    brute.extend_from_slice(&(6u64).to_le_bytes());
    brute.extend_from_slice(b"jetons");
    brute.extend_from_slice(&9u32.to_le_bytes());
    brute.extend_from_slice(&8u32.to_le_bytes());
    brute.extend_from_slice(&2u64.to_le_bytes());
    for s in ["a", "été"] {
        brute.extend_from_slice(&(s.len() as u64).to_le_bytes());
        brute.extend_from_slice(s.as_bytes());
    }
    let ajout = paire_chaine("troncons.codeur.version", "essai");
    w.ouvrir_section(SECTION_META).unwrap();
    w.ecrire(&serialiser_meta(&brute, 3, &[ajout.clone()])).unwrap();
    w.fermer_section();
    let mut meta_brute = (4u64).to_le_bytes().to_vec();
    meta_brute.extend_from_slice(&brute);
    meta_brute.extend_from_slice(&ajout);

    // RÉSIDENTS : trois tenseurs de tailles non alignées.
    let tailles = [1000u64, 34 * 5, 4 * 3];
    let (dec, _fin) = disposer_residents(&tailles);
    let donnees: Vec<Vec<u8>> = tailles.iter().map(|&t| a.octets(t as usize)).collect();
    let residents: Vec<TenseurResident> = (0..3)
        .map(|i| TenseurResident {
            nom: format!("blk.{i}.essai.weight"),
            type_ggml: [0, 8, 0][i],
            ne: [tailles[i] / 4, 1, 1, 1],
            n_dims: 1 + (i as u32 % 2),
            decalage: dec[i],
            octets: tailles[i],
            empreinte: empreinte64(&donnees[i]),
        })
        .collect();
    let d = w.ouvrir_section(SECTION_RESIDENTS).unwrap();
    let table = serialiser_table_residents(&residents).unwrap();
    w.ecrire(&table).unwrap();
    w.aligner_sur(ALIGNEMENT).unwrap();
    assert_eq!(w.position() - d, debut_zone_residents(3));
    let zone = w.position();
    for (r, o) in residents.iter().zip(&donnees) {
        let cible = zone + r.decalage;
        let z = vec![0u8; (cible - w.position()) as usize];
        w.ecrire(&z).unwrap();
        w.ecrire(o).unwrap();
    }
    w.ecrire(&empreinte64(&table).to_le_bytes()).unwrap();
    w.fermer_section();

    // TABLES : DELTA et CODES_CTX par (couche, matrice), dans le désordre exprès.
    let mut tables = Vec::new();
    for c in (0..2u16).rev() {
        for j in 0..3u8 {
            for (sorte, ctx) in [(Sorte::CodesCtx, 2u8), (Sorte::Delta, 0), (Sorte::CodesCtx, 0), (Sorte::CodesCtx, 1)] {
                let mut f = Box::new([0u16; 256]);
                f[(c as usize + j as usize + ctx as usize) % 256] = 4000;
                f[255] = 96;
                if table_8 && sorte == Sorte::CodesCtx {
                    f[255] = 95;
                    f[0x08] = 1;
                }
                tables.push(Table { couche: c, matrice: j, sorte, contexte: ctx, charge: Charge::Freq256(f) });
            }
        }
    }
    tables.push(Table { couche: 1, matrice: 2, sorte: Sorte::ComplCtx, contexte: 17, charge: Charge::Freq16([256; 16]) });
    tables.push(Table { couche: 0, matrice: 1, sorte: Sorte::Centres, contexte: 0, charge: Charge::Centres([0.25, 1.4, 3.4, 6.0]) });
    w.ouvrir_section(SECTION_TABLES).unwrap();
    w.ecrire(&serialiser_tables(&tables)).unwrap();
    w.fermer_section();

    // RÉPERTOIRE réservé, TRONÇONS, puis répertoire réécrit.
    let n_ent = 6;
    let d_rep = w.ouvrir_section(SECTION_REPERTOIRE).unwrap();
    w.reserver((n_ent * TAILLE_ENTREE_REPERTOIRE + 8) as u64).unwrap();
    w.fermer_section();
    let d_tr = w.ouvrir_section(SECTION_TRONCONS).unwrap();
    let mut repertoire = Vec::new();
    let mut parties = Vec::new();
    for c in 0..2u16 {
        for x in 0..3u16 {
            let flux: Vec<(Sorte, Vec<u8>)> = (0..3)
                .flat_map(|_| [(Sorte::Medianes, a.octets(64)), (Sorte::Biais, a.octets(256)), (Sorte::Delta, a.octets(160 + (x as usize) * 16)), (Sorte::CodesCtx, a.octets(5000 + 37 * x as usize))])
                .collect();
            let fe: Vec<FluxAEcrire> = flux.iter().enumerate().map(|(i, (s, o))| FluxAEcrire { sorte: *s, matrice: (i / 4) as u8, contexte: if *s == Sorte::Delta { 0 } else { CONTEXTE_AUCUN }, produits: o.len() as u32, octets: o }).collect();
            let (p, utiles) = assembler_partie(c, x, 0, 3, &fe);
            let decalage = w.position();
            w.ecrire(&p).unwrap();
            repertoire.push(EntreeRepertoire {
                decalage,
                longueur: [p.len() as u32, 0],
                utiles: [utiles, 0],
                empreinte_origine: a.suivant(),
                empreinte_niveau: [empreinte64(&p[..utiles as usize]), 0],
                couche: c,
                expert: x,
                empreinte_canonique: if canonique { a.suivant() } else { 0 },
            });
            parties.push(p);
        }
    }
    w.fermer_section();
    assert!(d_tr > d_rep);
    w.reecrire(d_rep, &serialiser_repertoire(&repertoire)).unwrap();
    let entete = if canonique { entete_canonique() } else { entete_type() };
    w.terminer(entete.clone()).unwrap();
    Construit { entete, meta_brute, residents, donnees, tables, repertoire, parties }
}

#[test]
fn aller_retour_identique() {
    let chemin = dossier().join("aller_retour.trc");
    let c = ecrire(&chemin);
    let f = Fichier::ouvrir(&chemin).expect("le fichier écrit doit se relire");
    let e = f.entete();
    let mut attendu = c.entete.clone();
    attendu.sections = e.sections;
    attendu.taille_fichier = std::fs::metadata(&chemin).unwrap().len();
    assert_eq!(*e, attendu);
    assert_eq!(e.taille_fichier % ALIGNEMENT, 0);
    assert_eq!(f.meta(), &c.meta_brute[..]);
    let cles: Vec<&str> = f.paires().iter().map(|p| p.cle.as_str()).collect();
    assert_eq!(cles, ["general.architecture", "essai.couches_x", "jetons", "troncons.codeur.version"]);
    assert_eq!(f.paire("essai.couches_x").unwrap().entier(), Some(2));
    assert_eq!(f.paire("jetons").unwrap().valeur, ValeurMeta::Tableau { type_elem: 8, n: 2 });
    assert_eq!(f.residents(), &c.residents[..]);
    let octets = std::fs::read(&chemin).unwrap();
    for (r, d) in f.residents().iter().zip(&c.donnees) {
        let a = (f.debut_donnees_residentes() + r.decalage) as usize;
        assert_eq!(&octets[a..a + r.octets as usize], &d[..]);
        assert_eq!(empreinte64(d), r.empreinte);
    }
    let mut tables_attendues = c.tables.clone();
    tables_attendues.sort_by_key(|t| (t.couche, t.matrice, t.sorte, t.contexte));
    assert_eq!(f.toutes_tables(), &tables_attendues[..]);
    assert_eq!(f.tables(1, 2).len(), 5);
    assert!(f.table(0, 1, Sorte::Centres, 0).is_some());
    assert_eq!(f.repertoire(), &c.repertoire[..]);
    for (i, ent) in f.repertoire().iter().enumerate() {
        let a = ent.decalage as usize;
        let p = &octets[a..a + ent.longueur[0] as usize];
        assert_eq!(p, &c.parties[i][..]);
        let lue = lire_partie(p).unwrap();
        assert_eq!((lue.couche, lue.expert, lue.niveau, lue.n_matrices), (ent.couche, ent.expert, 0, 3));
        assert_eq!(lue.flux.len(), 12);
        assert_eq!(lue.utiles, ent.utiles[0]);
        assert_eq!(empreinte64(&p[..lue.utiles as usize]), ent.empreinte_niveau[0]);
        for d in &lue.flux {
            assert_eq!(d.decalage % 16, 0);
            assert_eq!(lue.octets_flux(d).len(), d.produits as usize);
        }
    }
}

/// Copie le fichier avec un octet changé, et rend l'erreur d'ouverture.
fn ouvrir_fausse(source: &Path, nom: &str, position: u64, xor: u8) -> Option<ErreurFormat> {
    let mut b = std::fs::read(source).unwrap();
    b[position as usize] ^= xor;
    let c = dossier().join(nom);
    std::fs::write(&c, &b).unwrap();
    Fichier::ouvrir(&c).err()
}

#[test]
fn cassures_refusees() {
    let chemin = dossier().join("cassures.trc");
    let _c = ecrire(&chemin);
    let f = Fichier::ouvrir(&chemin).unwrap();
    let s = f.entete().sections;
    // En-tête : magie, version, un octet réservé, l'empreinte elle-même, un décalage de section.
    assert!(matches!(ouvrir_fausse(&chemin, "c1.trc", 0, 0x20), Some(ErreurFormat::Magie)));
    for (pos, nom) in [(8u64, "version"), (300, "réservé"), (4090, "empreinte"), (136, "section"), (72, "couches")] {
        let e = ouvrir_fausse(&chemin, &format!("c-{nom}.trc"), pos, 0x01);
        assert!(matches!(e, Some(ErreurFormat::Empreinte(_))), "{nom} : {e:?}");
    }
    // Un en-tête faussé puis ré-empreint est refusé par le contrôle qui le concerne.
    let mut b = std::fs::read(&chemin).unwrap();
    b[10] = 9; // version mineure 9
    let h = empreinte64(&b[..4088]);
    b[4088..4096].copy_from_slice(&h.to_le_bytes());
    let c = dossier().join("c-version-9.trc");
    std::fs::write(&c, &b).unwrap();
    assert!(matches!(Fichier::ouvrir(&c), Err(ErreurFormat::Version(1, 9))));
    let mut b = std::fs::read(&chemin).unwrap();
    b[12] |= 8; // drapeau CANONIQUE sous la v1.0 : refusé
    let h = empreinte64(&b[..4088]);
    b[4088..4096].copy_from_slice(&h.to_le_bytes());
    std::fs::write(&c, &b).unwrap();
    assert!(matches!(Fichier::ouvrir(&c), Err(ErreurFormat::Drapeaux(_))));
    // Sections : MÉTA, table des résidents, TABLES, RÉPERTOIRE.
    for (i, nom) in [(SECTION_META, "méta"), (SECTION_RESIDENTS, "résidents"), (SECTION_TABLES, "tables"), (SECTION_REPERTOIRE, "répertoire")] {
        let e = ouvrir_fausse(&chemin, &format!("s-{i}.trc"), s[i].decalage + 9, 0x10);
        assert!(e.is_some(), "section {nom} faussée acceptée");
    }
    // Fichier tronqué.
    let b = std::fs::read(&chemin).unwrap();
    std::fs::write(&c, &b[..b.len() - 4096]).unwrap();
    assert!(matches!(Fichier::ouvrir(&c), Err(ErreurFormat::Champ { .. })));
    // Partie : magie, sorte inconnue, octet réservé, bourrage non nul.
    let ent = f.entree(1, 2);
    let p = &b[ent.decalage as usize..(ent.decalage + ent.longueur[0] as u64) as usize];
    assert!(lire_partie(p).is_ok());
    for (pos, val, nom) in [(0usize, 0x55u8, "magie"), (64, 0x05, "sorte 0x05 réservée"), (67, 1, "réservé du descripteur"), (40, 1, "réservé de l'en-tête"), (p.len() - 1, 1, "bourrage")] {
        let mut q = p.to_vec();
        q[pos] = val;
        assert!(lire_partie(&q).is_err(), "partie : {nom} accepté");
    }
}

/// Récrit l'en-tête d'une copie (octets changés par `f`, empreinte refaite) et rend l'erreur.
fn ouvrir_entete_change(source: &Path, nom: &str, f: impl Fn(&mut [u8])) -> Result<Fichier, ErreurFormat> {
    let mut b = std::fs::read(source).unwrap();
    f(&mut b[..4096]);
    let h = empreinte64(&b[..4088]);
    b[4088..4096].copy_from_slice(&h.to_le_bytes());
    let c = dossier().join(nom);
    std::fs::write(&c, &b).unwrap();
    Fichier::ouvrir(&c)
}

#[test]
fn aller_retour_v12_canonique() {
    let chemin = dossier().join("canonique.trc");
    let c = ecrire_avec(&chemin, true, false);
    let f = Fichier::ouvrir(&chemin).expect("le fichier v1.2 écrit doit se relire");
    let e = f.entete();
    assert_eq!(e.version, (1, 2));
    assert!(e.est_canonique() && !e.est_brut());
    assert_eq!(f.repertoire(), &c.repertoire[..]);
    for ent in f.repertoire() {
        assert_ne!(ent.empreinte_canonique, 0);
        assert_eq!(ent.empreinte_du_decode(true), ent.empreinte_canonique);
        assert_eq!(ent.empreinte_du_decode(false), ent.empreinte_origine);
    }
    // L'empreinte canonique est bien au décalage 56 de l'entrée.
    let b = std::fs::read(&chemin).unwrap();
    let d = f.entete().sections[SECTION_REPERTOIRE].decalage as usize;
    assert_eq!(lu64(&b, d + 56), c.repertoire[0].empreinte_canonique);
    // Le même fichier en v1.0 garde ses 8 octets à zéro et rend l'empreinte d'origine.
    let chemin0 = dossier().join("non-canonique.trc");
    let c0 = ecrire(&chemin0);
    let f0 = Fichier::ouvrir(&chemin0).unwrap();
    assert!(!f0.entete().est_canonique());
    assert!(f0.repertoire().iter().all(|e| e.empreinte_canonique == 0));
    assert_eq!(f0.repertoire()[0].empreinte_du_decode(false), c0.repertoire[0].empreinte_origine);
}

#[test]
fn cassures_v12_refusees() {
    let chemin = dossier().join("canonique-cassures.trc");
    let _c = ecrire_avec(&chemin, true, false);
    assert!(Fichier::ouvrir(&chemin).is_ok());
    // CANONIQUE sous la v1.1.
    let e = ouvrir_entete_change(&chemin, "v12-sous-11.trc", |h| h[10] = 1);
    assert!(matches!(e, Err(ErreurFormat::Drapeaux(_))), "{:?}", e.err());
    // CANONIQUE sur un fichier brut.
    let e = ouvrir_entete_change(&chemin, "v12-brut.trc", |h| h[12] |= DRAPEAU_BRUT as u8);
    assert!(matches!(e, Err(ErreurFormat::Drapeaux(_))), "{:?}", e.err());
    // Bit 4, inconnu de la v1.2.
    let e = ouvrir_entete_change(&chemin, "v12-bit4.trc", |h| h[12] |= 16);
    assert!(matches!(e, Err(ErreurFormat::Drapeaux(_))), "{:?}", e.err());
    // Version 1.3.
    let e = ouvrir_entete_change(&chemin, "v13.trc", |h| h[10] = 3);
    assert!(matches!(e, Err(ErreurFormat::Version(1, 3))), "{:?}", e.err());
    // Le drapeau retiré (v1.2 sans CANONIQUE) : les empreintes canoniques non nulles sont refusées.
    let e = ouvrir_entete_change(&chemin, "v12-sans-drapeau.trc", |h| h[12] &= !(DRAPEAU_CANONIQUE as u8));
    assert!(matches!(e, Err(ErreurFormat::Limites(_))), "{:?}", e.err());
    // Une table CODES_CTX qui donne une fente à l'octet 0x08 : refusée sur un fichier canonique…
    let c8 = dossier().join("canonique-table-8.trc");
    let _ = ecrire_avec(&c8, true, true);
    let e = Fichier::ouvrir(&c8);
    assert!(matches!(e, Err(ErreurFormat::Champ { .. })), "{:?}", e.err());
    // … et acceptée sur un fichier v1.0 (c'est le drapeau qui déclenche le contrôle).
    let c80 = dossier().join("v10-table-8.trc");
    let _ = ecrire_avec(&c80, false, true);
    assert!(Fichier::ouvrir(&c80).is_ok());
    // Les fonctions de canonisation.
    assert_eq!((0..=255u8).filter(|&o| porte_un_8(o)).count(), 31);
    assert_eq!(canoniser_octet(0x88), 0x00);
    assert_eq!(canoniser_octet(0x8F), 0x0F);
    assert_eq!(canoniser_octet(0x78), 0x70);
    assert!((0..=255u8).all(|o| !porte_un_8(canoniser_octet(o)) && (porte_un_8(o) || canoniser_octet(o) == o)));
}

/// Lot B (genome/07-genome-synonyme.md) : le drapeau RAPIDE (bit 5) est lu en v1.2 sur un fichier
/// codé à un niveau non canonique, et refusé ailleurs.
#[test]
fn drapeau_rapide_v12() {
    let chemin = dossier().join("rapide-base.trc");
    let _c = ecrire(&chemin);
    let ok = ouvrir_entete_change(&chemin, "rapide-ok.trc", |h| {
        h[10] = 2;
        h[12] |= DRAPEAU_RAPIDE as u8;
    });
    assert!(ok.as_ref().is_ok_and(|f| f.entete().est_rapide()), "{:?}", ok.err());
    let e = ouvrir_entete_change(&chemin, "rapide-sous-10.trc", |h| h[12] |= DRAPEAU_RAPIDE as u8);
    assert!(matches!(e, Err(ErreurFormat::Drapeaux(_))), "{:?}", e.err());
    let e = ouvrir_entete_change(&chemin, "rapide-brut.trc", |h| {
        h[10] = 2;
        h[12] |= (DRAPEAU_RAPIDE | DRAPEAU_BRUT) as u8;
    });
    assert!(matches!(e, Err(ErreurFormat::Drapeaux(_))), "{:?}", e.err());
    let e = ouvrir_entete_change(&chemin, "rapide-canonique.trc", |h| {
        h[10] = 2;
        h[12] |= (DRAPEAU_RAPIDE | DRAPEAU_CANONIQUE) as u8;
    });
    assert!(matches!(e, Err(ErreurFormat::Drapeaux(_))), "{:?}", e.err());
}

#[test]
fn temoin_du_temoin() {
    // La comparaison qui juge l'aller-retour doit voir un seul octet changé.
    let chemin = dossier().join("temoin.trc");
    let c = ecrire(&chemin);
    let mut p = c.parties[3].clone();
    assert_eq!(p, c.parties[3]);
    p[100] ^= 1;
    assert_ne!(p, c.parties[3]);
    assert_ne!(empreinte64(&p[..c.repertoire[3].utiles[0] as usize]), c.repertoire[3].empreinte_niveau[0]);
}

#[test]
fn empreinte64_connue() {
    // SHA-256("abc") = ba7816bf 8f01cfea … ; ses 8 premiers octets lus en petit-boutiste.
    assert_eq!(empreinte64(b"abc"), u64::from_le_bytes([0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea]));
    assert_eq!(empreinte64_morceaux([&b"a"[..], b"bc"]), empreinte64(b"abc"));
}
