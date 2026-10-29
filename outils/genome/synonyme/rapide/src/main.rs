//! trc-rapide : le fichier compagnon du mode rapide (lot B, génome synonyme ;
//! genome/05-synthese.md § 4.8, genome/07-genome-synonyme.md).
//!
//! ```text
//! trc-rapide coder    --exact E.trc --symboles D|frontiere-directe [--centres a,b,c,d] --sortie S.rapide.trc --variante V
//!                     [--lambda L] [--amortissement A] [--calibration TEXTE] [--fils N] [--journal j.json]
//! trc-rapide verifier --rapide S.rapide.trc --exact E.trc --symboles D [--casser COUCHE EXPERT]
//!                     [--fils N] [--journal j.json]
//! ```
//!
//! **Le fichier rapide** est un `.trc` ordinaire, au drapeau RAPIDE (bit 5) : mêmes sections, même
//! MÉTA du GGUF (plus les paires `troncons.rapide.*`), mêmes résidents (recopiés octet pour octet du
//! fichier exact, pour qu'il se lise seul), mêmes échelles (DELTA, MÉDIANES) et mêmes biais ; seuls
//! les demi-octets des `qs` changent : chacun porte le **symbole de base** du poids (bit 3 le
//! signe, bits 0 et 1 la classe k, bit 2 nul), choisi par la mutation synonyme (fichiers `.sym` de
//! `synonyme.py ecrire-sym`). Les flux de codes gardent la sorte CODES_CTX (rANS, géométrie 1,
//! table par voie κ) : **le décodeur ne change pas**, seule la table des valeurs de la GEMV change
//! (`gemv_base`, valeurs ±c_k · 2^(e − 128), les centres c_k en table CENTRES, type 3).
//!
//! *Réponse par délégation du 2026-10-17, réversible* (écarts au cahier § 4.8, chacun pour ne
//! toucher aucun chemin du mode exact) : (1) sorte CODES_CTX au lieu de BASE_CTX (0x10) : le
//! décodeur de la carte et ses LUT restent ceux du mode exact, mot pour mot ; c'est le drapeau
//! RAPIDE qui dit que les demi-octets sont des symboles ; (2) résidents recopiés au lieu d'une
//! section vide : le moteur ouvre le compagnon comme n'importe quel fichier ; (3) l'empreinte
//! d'origine du répertoire est celle de l'**expert rapide** (blocs `[e, demi-octets de base]`,
//! puis biais) : le mode témoin du moteur la vérifie sans changement ; la provenance est dans
//! l'en-tête (SHA-256 du GGUF) et dans la paire `troncons.rapide.exact`.
//!
//! **La vérification** (seconde lecture, indépendante du codage) : chaque expert du fichier rapide
//! est décodé par trc-codec et comparé (a) aux demi-octets recalculés depuis le `.sym` (b) aux
//! échelles et biais de l'expert exact décodé du fichier exact ; et son empreinte à celle du
//! répertoire. `--casser C X` change un symbole de l'expert (C, X) avant la comparaison : il doit
//! être le seul trouvé faux.

use anyhow::{Context, Result, bail, ensure};
use rayon::prelude::*;
use serde_json::{Value, json};
use std::io::{Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use std::time::Instant;
use trc_codec::{ComptesMatrice, TablesFichier, a_ecrire, coder_matrice_v10, decoder_partie, preparer_matrice};
use trc_format::*;

/// Bit 5 des drapeaux : fichier compagnon du mode rapide (lot B ; ARCHITECTURE § 4.3).
const RAPIDE: u32 = DRAPEAU_RAPIDE;

fn valeur<'a>(args: &'a [String], nom: &str) -> Option<&'a str> {
    args.iter().position(|a| a == nom).and_then(|i| args.get(i + 1)).map(|s| s.as_str())
}

fn exiger<'a>(args: &'a [String], nom: &str) -> Result<&'a str> {
    valeur(args, nom).with_context(|| format!("{nom} manque"))
}

/// Un fichier `.sym` : les centres (f64, grandeurs doublées) et, pour gate, up, down, les R·C
/// symboles deux par octet (indice pair dans le demi-octet faible).
struct Sym {
    centres: [f64; 4],
    matrices: Vec<Vec<u8>>,
}

/// La source des symboles : des fichiers `.sym`, ou la frontière calculée directement depuis les
/// codes de l'expert exact (`--symboles frontiere-directe --centres a,b,c,d`), sans fichier : le
/// symbole est alors une fonction du code, (code & 8) | classe(code & 7), partition 0 0 1 1 1 2 2 3.
/// Ajouté le 2026-10-17 pour le 120b, dont aucun `.sym` n'existe ; témoin : sur le 20b, le compagnon
/// frontière écrit des deux façons a les mêmes empreintes d'experts.
enum Source {
    Fichiers(PathBuf),
    FrontiereDirecte([f64; 4]),
}

const CLASSES: [u8; 8] = [0, 0, 1, 1, 1, 2, 2, 3];

/// Les `qs` de la frontière depuis des `qs` MXFP4 : chaque demi-octet c devient (c & 8) | classe(c & 7).
fn qs_frontiere(qs: &[u8]) -> Vec<u8> {
    let f = |c: u8| (c & 8) | CLASSES[(c & 7) as usize];
    qs.iter().map(|&o| f(o & 15) | (f(o >> 4) << 4)).collect()
}

fn source_de(args: &[String]) -> Result<Source> {
    let s = exiger(args, "--symboles")?;
    if s == "frontiere-directe" {
        let c: Vec<f64> = exiger(args, "--centres")?.split(',').map(|x| x.trim().parse()).collect::<Result<_, _>>()?;
        ensure!(c.len() == 4, "--centres a,b,c,d");
        return Ok(Source::FrontiereDirecte([c[0], c[1], c[2], c[3]]));
    }
    Ok(Source::Fichiers(PathBuf::from(s)))
}

fn lire_sym(chemin: &Path, dims: &[(usize, usize); 3]) -> Result<Sym> {
    let o = std::fs::read(chemin).with_context(|| format!("lecture de {}", chemin.display()))?;
    ensure!(o.len() >= 36 && &o[..4] == b"SYM1", "{} : pas un fichier SYM1", chemin.display());
    let mut centres = [0f64; 4];
    for k in 0..4 {
        centres[k] = f64::from_le_bytes(o[4 + 8 * k..12 + 8 * k].try_into().unwrap());
    }
    let mut p = 36;
    let mut matrices = Vec::with_capacity(3);
    for &(r, c) in dims {
        let n = r * c / 2;
        ensure!(o.len() >= p + n, "{} : trop court", chemin.display());
        matrices.push(o[p..p + n].to_vec());
        p += n;
    }
    ensure!(p == o.len(), "{} : {} octets en trop", chemin.display(), o.len() - p);
    Ok(Sym { centres, matrices })
}

/// Le demi-octet de base d'un symbole de synonyme.py (bits 0-1 la classe, bit 2 le signe).
fn demi_de_base(s: u8) -> Result<u8> {
    ensure!(s & 8 == 0, "symbole {s} : bit 3 posé");
    Ok(((s >> 2) & 1) << 3 | (s & 3))
}

/// Les `qs` (R · B · 16 octets, ordre β) des demi-octets de base : l'octet t du bloc (r, b) porte
/// le poids de la colonne 32b + t (demi-octet faible) et celui de la colonne 32b + 16 + t (fort).
fn qs_de_base(sym: &[u8], r: usize, c: usize) -> Result<Vec<u8>> {
    let b = c / 32;
    let lire = |i: usize| (sym[i / 2] >> ((i & 1) * 4)) & 15;
    let mut qs = vec![0u8; r * b * 16];
    for ligne in 0..r {
        for bl in 0..b {
            for t in 0..16 {
                let i = ligne * c + 32 * bl + t;
                qs[(ligne * b + bl) * 16 + t] = demi_de_base(lire(i))? | (demi_de_base(lire(i + 16))? << 4);
            }
        }
    }
    Ok(qs)
}

fn lire_partie_brute(f: &mut std::fs::File, e: &EntreeRepertoire) -> Result<Vec<u8>> {
    f.seek(SeekFrom::Start(e.decalage))?;
    let mut v = vec![0u8; e.longueur[0] as usize];
    f.read_exact(&mut v)?;
    Ok(v)
}

/// L'expert rapide d'une (couche, expert) : pour j = 0, 1, 2 les blocs `[e, qs de base]`, et les
/// biais ; depuis l'expert exact décodé (échelles, biais) et le `.sym`.
struct ExpertRapide {
    blocs: Vec<Vec<u8>>,
    biais: Vec<Vec<u8>>,
}

fn expert_rapide(exact: &Fichier, tables: &TablesFichier, partie: &[u8], sym: Option<&Sym>, dims: &[(usize, usize); 3]) -> Result<ExpertRapide> {
    let p = lire_partie(partie)?;
    let d = decoder_partie(exact, Some(tables), &p, true)?;
    let mut blocs = Vec::with_capacity(3);
    let mut biais = Vec::with_capacity(3);
    for j in 0..3 {
        let (r, c) = dims[j];
        let m = &d.matrices[j];
        let qs = match sym {
            Some(sym) => qs_de_base(&sym.matrices[j], r, c)?,
            None => qs_frontiere(&m.codes),
        };
        let n = r * (c / 32);
        ensure!(m.echelles.len() == n);
        let mut v = Vec::with_capacity(17 * n);
        for beta in 0..n {
            v.push(m.echelles[beta]);
            v.extend_from_slice(&qs[16 * beta..16 * beta + 16]);
        }
        blocs.push(v);
        biais.push(m.octets_biais());
    }
    Ok(ExpertRapide { blocs, biais })
}

fn dims_de(e: &Entete) -> [(usize, usize); 3] {
    std::array::from_fn(|j| (e.lignes[j] as usize, e.colonnes[j] as usize))
}

fn coder(args: &[String]) -> Result<Value> {
    let t0 = Instant::now();
    let chemin_exact = PathBuf::from(exiger(args, "--exact")?);
    let source = source_de(args)?;
    let sortie = PathBuf::from(exiger(args, "--sortie")?);
    let variante = exiger(args, "--variante")?.to_string();
    ensure!(variante == "synonyme" || variante == "frontiere", "--variante synonyme|frontiere");
    let exact = Fichier::ouvrir(&chemin_exact).with_context(|| format!("ouverture de {}", chemin_exact.display()))?;
    let e = exact.entete().clone();
    ensure!(!e.est_brut() && e.niveaux == 1 && e.matrices == 3 && e.drapeaux & RAPIDE == 0, "le fichier exact doit être codé, à un niveau, 3 matrices");
    let tables_exactes = TablesFichier::depuis_fichier(&exact)?;
    let dims = dims_de(&e);
    let (n_c, n_e) = (e.couches as usize, e.experts as usize);
    // Centres : ceux du premier .sym, exigés égaux dans tous ; ou ceux donnés (frontière directe).
    let centres = match &source {
        Source::Fichiers(d) => lire_sym(&d.join("L00-E00.sym"), &dims)?.centres,
        Source::FrontiereDirecte(c) => {
            ensure!(variante == "frontiere", "frontiere-directe exige --variante frontiere");
            *c
        }
    };
    let symboles = match &source {
        Source::Fichiers(d) => d.clone(),
        Source::FrontiereDirecte(_) => PathBuf::from("frontiere-directe"),
    };

    let mut w = Ecrivain::creer(&sortie).with_context(|| format!("création de {}", sortie.display()))?;
    let n_meta = lu64(exact.meta(), 0);
    let mut ajouts = vec![
        meta::paire_chaine("troncons.rapide.codeur", &format!("trc-rapide {}", env!("CARGO_PKG_VERSION"))),
        meta::paire_chaine("troncons.rapide.variante", &variante),
        meta::paire_chaine("troncons.rapide.exact", &format!("{:016x}", empreinte64(&e.vers_octets()))),
        meta::paire_chaine("troncons.rapide.partition", "0 0 1 1 1 2 2 3"),
        meta::paire_chaine("troncons.rapide.centres", &format!("{:.9} {:.9} {:.9} {:.9}", centres[0], centres[1], centres[2], centres[3])),
    ];
    for (cle, nom) in [("troncons.rapide.lambda", "--lambda"), ("troncons.rapide.amortissement", "--amortissement"), ("troncons.rapide.calibration", "--calibration")] {
        if let Some(v) = valeur(args, nom) {
            ajouts.push(meta::paire_chaine(cle, v));
        }
    }
    w.ouvrir_section(SECTION_META)?;
    w.ecrire(&serialiser_meta(&exact.meta()[8..], n_meta, &ajouts))?;
    w.fermer_section();

    // RÉSIDENTS : la section du fichier exact, recopiée octet pour octet (ses décalages sont
    // relatifs à son début, aligné sur 4 096 dans les deux fichiers).
    let sr = e.sections[SECTION_RESIDENTS];
    let mut fe = std::fs::File::open(&chemin_exact)?;
    let d_res = w.ouvrir_section(SECTION_RESIDENTS)?;
    ensure!(d_res % ALIGNEMENT == 0 && sr.decalage % ALIGNEMENT == 0);
    let mut fait = 0u64;
    let mut tampon = vec![0u8; 16 << 20];
    fe.seek(SeekFrom::Start(sr.decalage))?;
    while fait < sr.longueur {
        let n = (sr.longueur - fait).min(tampon.len() as u64) as usize;
        fe.read_exact(&mut tampon[..n])?;
        w.ecrire(&tampon[..n])?;
        fait += n as u64;
    }
    w.fermer_section();

    // TABLES (DELTA, CODES_CTX × 3, CENTRES par (couche, matrice)) et RÉPERTOIRE réservés.
    let n_tables = n_c * 3 * 5;
    let lg_tables = (8 + n_c * 3 * (4 * (8 + 512) + (8 + 16)) + 8) as u64;
    let d_tab = w.ouvrir_section(SECTION_TABLES)?;
    w.reserver(lg_tables)?;
    w.fermer_section();
    let lg_rep = (n_c * n_e * TAILLE_ENTREE_REPERTOIRE + 8) as u64;
    let d_rep = w.ouvrir_section(SECTION_REPERTOIRE)?;
    w.reserver(lg_rep)?;
    w.fermer_section();

    w.ouvrir_section(SECTION_TRONCONS)?;
    let mut tables: Vec<Table> = Vec::with_capacity(n_tables);
    let mut repertoire: Vec<EntreeRepertoire> = Vec::with_capacity(n_c * n_e);
    let mut par_couche = Vec::new();
    let mut hist_demi = [0u64; 16];
    let c32: [f32; 4] = centres.map(|x| x as f32);
    for c in 0..n_c {
        let tc = Instant::now();
        // Les experts rapides de la couche, en mémoire (32 × 12,4 Mo pour le 20b).
        let experts: Vec<ExpertRapide> = (0..n_e)
            .into_par_iter()
            .map(|x| -> Result<ExpertRapide> {
                let sym = match &source {
                    Source::Fichiers(d) => {
                        let s = lire_sym(&d.join(format!("L{c:02}-E{x:02}.sym")), &dims)?;
                        ensure!(s.centres == centres, "L{c:02}-E{x:02}.sym : centres différents de L00-E00");
                        Some(s)
                    }
                    Source::FrontiereDirecte(_) => None,
                };
                let mut f = std::fs::File::open(&chemin_exact)?;
                let partie = lire_partie_brute(&mut f, exact.entree(c as u16, x as u16))?;
                expert_rapide(&exact, &tables_exactes, &partie, sym.as_ref(), &dims).with_context(|| format!("couche {c}, expert {x}"))
            })
            .collect::<Result<_>>()?;
        for ex in &experts {
            for v in &ex.blocs {
                for blk in v.chunks_exact(17) {
                    for &q in &blk[1..] {
                        hist_demi[(q & 15) as usize] += 1;
                        hist_demi[(q >> 4) as usize] += 1;
                    }
                }
            }
        }
        // Passe des comptes : les tables du tenseur entier.
        let mut tm = Vec::with_capacity(3);
        for j in 0..3 {
            let (r, cc) = dims[j];
            let comptes = experts
                .par_iter()
                .map(|ex| preparer_matrice(&ex.blocs[j], r, cc / 32))
                .fold(ComptesMatrice::default, |mut a, p| {
                    a.ajouter(&p);
                    a
                })
                .reduce(ComptesMatrice::default, |mut a, x| {
                    a.fusionner(&x);
                    a
                });
            let t = comptes.tables();
            tables.push(Table { couche: c as u16, matrice: j as u8, sorte: Sorte::Delta, contexte: 0, charge: Charge::Freq256(Box::new(t.delta.freq.clone().try_into().unwrap())) });
            for k in 0..3 {
                tables.push(Table { couche: c as u16, matrice: j as u8, sorte: Sorte::CodesCtx, contexte: k as u8, charge: Charge::Freq256(Box::new(t.codes[k].freq.clone().try_into().unwrap())) });
            }
            tables.push(Table { couche: c as u16, matrice: j as u8, sorte: Sorte::Centres, contexte: 0, charge: Charge::Centres(c32) });
            tm.push(t);
        }
        // Passe du codage, dans l'ordre (couche, expert).
        let parties: Vec<(Vec<u8>, u32, u64)> = experts
            .par_iter()
            .enumerate()
            .map(|(x, ex)| {
                let empreinte = empreinte64_morceaux(ex.blocs.iter().chain(ex.biais.iter()).map(|v| &v[..]));
                let flux: Vec<[(Sorte, u8, u32, Vec<u8>); 4]> = (0..3)
                    .map(|j| {
                        let (r, cc) = dims[j];
                        coder_matrice_v10(&preparer_matrice(&ex.blocs[j], r, cc / 32), &ex.biais[j], &tm[j])
                    })
                    .collect();
                let fe: Vec<FluxAEcrire> = (0..3).flat_map(|j| a_ecrire(j as u8, &flux[j]).collect::<Vec<_>>()).collect();
                let (p, u) = assembler_partie(c as u16, x as u16, 0, 3, &fe);
                (p, u, empreinte)
            })
            .collect();
        for (x, (p, u, empreinte)) in parties.into_iter().enumerate() {
            let decalage = w.position();
            w.ecrire(&p)?;
            // Une entrée nulle puis remplie : les champs que d'autres versions ajoutent restent à 0.
            let mut ent = EntreeRepertoire::depuis_octets(&[0u8; TAILLE_ENTREE_REPERTOIRE])?;
            ent.decalage = decalage;
            ent.longueur = [p.len() as u32, 0];
            ent.utiles = [u, 0];
            ent.empreinte_origine = empreinte;
            ent.empreinte_niveau = [empreinte64(&p[..u as usize]), 0];
            ent.couche = c as u16;
            ent.expert = x as u16;
            repertoire.push(ent);
        }
        let dur = tc.elapsed().as_secs_f64();
        eprintln!("couche {c:>3} : {dur:.1} s ({:.0} s écoulées)", t0.elapsed().as_secs_f64());
        par_couche.push(json!({"couche": c, "duree_s": dur}));
    }
    w.fermer_section();
    let tab = serialiser_tables(&tables);
    ensure!(tab.len() as u64 == lg_tables, "TABLES : {} octets, {lg_tables} réservés", tab.len());
    w.reecrire(d_tab, &tab)?;
    let rep = serialiser_repertoire(&repertoire);
    ensure!(rep.len() as u64 == lg_rep);
    w.reecrire(d_rep, &rep)?;
    let mut entete = e.clone();
    entete.version = (1, 2);
    entete.drapeaux = DRAPEAU_ALIGNE | RAPIDE;
    entete.taille_fichier = 0;
    entete.sections = [Section::default(); 8];
    let taille = w.terminer(entete)?;
    let lg: Vec<u64> = repertoire.iter().map(|x| x.longueur[0] as u64).collect();
    let utiles: u64 = repertoire.iter().map(|x| x.utiles[0] as u64).sum();
    let poids: u64 = (0..3).map(|j| (dims[j].0 * dims[j].1) as u64).sum::<u64>() * (n_c * n_e) as u64;
    Ok(json!({
        "exact": chemin_exact.display().to_string(), "symboles": symboles.display().to_string(),
        "sortie": sortie.display().to_string(), "variante": variante,
        "centres_doubles": centres, "taille_fichier": taille,
        "troncon_octets": {"min": lg.iter().min(), "max": lg.iter().max(), "moyen": lg.iter().sum::<u64>() as f64 / lg.len() as f64, "total_alignes": lg.iter().sum::<u64>(), "total_utiles": utiles},
        "poids_experts": poids,
        "bits_par_poids_utiles": utiles as f64 * 8.0 / poids as f64,
        "bits_par_poids_alignes": lg.iter().sum::<u64>() as f64 * 8.0 / poids as f64,
        "histogramme_demi_octets": hist_demi,
        "duree_s": t0.elapsed().as_secs_f64(), "fils": rayon::current_num_threads(), "par_couche": par_couche,
    }))
}

fn verifier(args: &[String]) -> Result<Value> {
    let t0 = Instant::now();
    let chemin_rapide = PathBuf::from(exiger(args, "--rapide")?);
    let chemin_exact = PathBuf::from(exiger(args, "--exact")?);
    let source = source_de_verif(args)?;
    let symboles = PathBuf::from(exiger(args, "--symboles")?);
    let casser: Option<(usize, usize)> = match args.iter().position(|a| a == "--casser") {
        Some(i) => Some((args.get(i + 1).context("--casser C X")?.parse()?, args.get(i + 2).context("--casser C X")?.parse()?)),
        None => None,
    };
    let rapide = Fichier::ouvrir(&chemin_rapide)?;
    let exact = Fichier::ouvrir(&chemin_exact)?;
    let (er, ee) = (rapide.entete(), exact.entete());
    ensure!(er.drapeaux & RAPIDE != 0, "le fichier rapide n'a pas le drapeau RAPIDE");
    let lien = rapide.paire("troncons.rapide.exact").and_then(|p| p.chaine().map(String::from));
    let lien_tient = lien.as_deref() == Some(format!("{:016x}", empreinte64(&ee.vers_octets())).as_str());
    let tr = TablesFichier::depuis_fichier(&rapide)?;
    let te = TablesFichier::depuis_fichier(&exact)?;
    let dims = dims_de(er);
    let (n_c, n_e) = (er.couches as usize, er.experts as usize);
    let faux: Vec<Value> = (0..n_c * n_e)
        .into_par_iter()
        .map(|i| -> Result<Option<Value>> {
            let (c, x) = (i / n_e, i % n_e);
            let mut sym = match source {
                true => None,
                false => Some(lire_sym(&symboles.join(format!("L{c:02}-E{x:02}.sym")), &dims)?),
            };
            if let Some(sym) = sym.as_mut() {
                if casser == Some((c, x)) {
                    sym.matrices[1][0] ^= 1;
                }
            }
            let mut fr = std::fs::File::open(&chemin_rapide)?;
            let mut fx = std::fs::File::open(&chemin_exact)?;
            let er_ = rapide.entree(c as u16, x as u16);
            let pr = lire_partie_brute(&mut fr, er_)?;
            verifier_partie_simple(&pr, er_)?;
            let dr = decoder_partie(&rapide, Some(&tr), &lire_partie(&pr)?, true)?;
            let px = lire_partie_brute(&mut fx, exact.entree(c as u16, x as u16))?;
            let dx = decoder_partie(&exact, Some(&te), &lire_partie(&px)?, true)?;
            let mut raisons = Vec::new();
            for j in 0..3 {
                let (r, cc) = dims[j];
                let mut attendu = match sym.as_ref() {
                    Some(sym) => qs_de_base(&sym.matrices[j], r, cc)?,
                    None => qs_frontiere(&dx.matrices[j].codes),
                };
                if sym.is_none() && j == 1 && casser == Some((c, x)) {
                    attendu[0] ^= 1;
                }
                if dr.matrices[j].codes != attendu {
                    raisons.push(format!("matrice {j} : demi-octets différents du .sym"));
                }
                if dr.matrices[j].echelles != dx.matrices[j].echelles {
                    raisons.push(format!("matrice {j} : échelles différentes de l'exact"));
                }
                if dr.matrices[j].biais.iter().map(|v| v.to_bits()).ne(dx.matrices[j].biais.iter().map(|v| v.to_bits())) {
                    raisons.push(format!("matrice {j} : biais différents de l'exact"));
                }
            }
            if dr.empreinte() != er_.empreinte_origine {
                raisons.push("empreinte de l'expert rapide différente du répertoire".into());
            }
            Ok(if raisons.is_empty() { None } else { Some(json!({"couche": c, "expert": x, "raisons": raisons})) })
        })
        .collect::<Result<Vec<_>>>()?
        .into_iter()
        .flatten()
        .collect();
    let tient = faux.is_empty() && lien_tient;
    let attendu_casse = casser.is_some_and(|(c, x)| faux.len() == 1 && faux[0]["couche"] == c && faux[0]["expert"] == x);
    Ok(json!({
        "rapide": chemin_rapide.display().to_string(), "exact": chemin_exact.display().to_string(),
        "symboles": symboles.display().to_string(), "casser": casser,
        "lien_exact_tient": lien_tient, "experts": n_c * n_e, "experts_faux": faux.len(), "faux": faux,
        "seuil_declare": "100 % des experts : demi-octets décodés = .sym, échelles et biais = exact, empreinte = répertoire ; lien MÉTA = en-tête exact",
        "tient": tient, "cassure_tombe_sur_l_expert_vise": if casser.is_some() { Some(attendu_casse) } else { None },
        "duree_s": t0.elapsed().as_secs_f64(),
    }))
}

/// Vrai si la vérification compare à la frontière calculée depuis l'expert exact (`--symboles
/// frontiere-directe`) plutôt qu'à des fichiers `.sym`.
fn source_de_verif(args: &[String]) -> Result<bool> {
    Ok(exiger(args, "--symboles")? == "frontiere-directe")
}

/// L'empreinte des octets utiles d'une partie contre le répertoire (§ 4.12).
fn verifier_partie_simple(p: &[u8], e: &EntreeRepertoire) -> Result<()> {
    if empreinte64(&p[..e.utiles[0] as usize]) != e.empreinte_niveau[0] {
        bail!("couche {}, expert {} : empreinte de la partie", e.couche, e.expert);
    }
    Ok(())
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let r = (|| -> Result<i32> {
        let fils: usize = valeur(&args, "--fils").map(|s| s.parse()).transpose()?.unwrap_or(6);
        rayon::ThreadPoolBuilder::new().num_threads(fils).build_global()?;
        let mut v = match args.get(1).map(|s| s.as_str()) {
            Some("coder") => coder(&args)?,
            Some("verifier") => verifier(&args)?,
            _ => bail!("usage : trc-rapide coder|verifier … (voir l'en-tête de main.rs)"),
        };
        let code = match args.get(1).map(|s| s.as_str()) {
            Some("verifier") if args.iter().any(|a| a == "--casser") => (v["cassure_tombe_sur_l_expert_vise"] != json!(true)) as i32,
            Some("verifier") => (v["tient"] != json!(true)) as i32,
            _ => 0,
        };
        if let Value::Object(m) = &mut v {
            m.insert("commande".into(), json!(args.join(" ")));
            m.insert("outil".into(), json!(format!("trc-rapide {}", env!("CARGO_PKG_VERSION"))));
        }
        let texte = serde_json::to_string_pretty(&v)?;
        if let Some(j) = valeur(&args, "--journal") {
            std::fs::write(j, &texte)?;
        }
        println!("{texte}");
        Ok(code)
    })();
    match r {
        Ok(c) => std::process::exit(c),
        Err(e) => {
            eprintln!("erreur : {e:#}");
            std::process::exit(1);
        }
    }
}
