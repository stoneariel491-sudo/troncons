//! GGUF → `.trc` (decisions/ARCHITECTURE.md § 4) : couche par couche, en mémoire bornée.
//!
//! Pour chaque couche, deux passes sur ses trois tenseurs d'experts, par paquets d'experts :
//! 1. **comptes** : chaque paquet est lu, préparé (médianes, δ, codes) en parallèle, compté,
//!    puis oublié ; les comptes du tenseur entier donnent ses tables (une par (couche, matrice,
//!    sorte, contexte), communes aux experts, comme en 03) ;
//! 2. **codage** : chaque paquet est relu, préparé de nouveau, codé en parallèle, et ses tronçons
//!    écrits dans l'ordre (couche, expert) ; l'empreinte d'origine de chaque expert se calcule
//!    sur les octets de cette seconde lecture.
//! La mémoire de pointe ne dépend donc que de la taille d'un paquet (2 × fils experts), pas du
//! nombre d'experts par couche : le 120b (128 experts) code dans la même fenêtre que le 20b (32).
//! Le prix : les experts sont lus deux fois (de l'ordre de 25 minutes de disque de plus sur le
//! 120b, contre environ 1,7 Go de RAM de pointe en moins sur une machine partagée de 16 Go). Les
//! octets écrits sont ceux de la version à une passe (mêmes comptes, mêmes tables, même ordre) :
//! témoin, le 20b recodé doit être identique octet pour octet au fichier de F2.
//!
//! Les lectures du GGUF se font sans tampon (`gguf::ouvrir_direct`) pour ne pas chasser du cache
//! de fichiers les pages d'autres programmes. TABLES et RÉPERTOIRE, de tailles connues d'avance,
//! sont réservés avant les tronçons et remplis à la fin ; l'en-tête s'écrit en dernier. Pendant
//! ce temps, un fil relit tout le GGUF pour son SHA-256 (second chemin de `telechargements.json`).
//!
//! `--canonique` écrit la v1.2 (genome/06-codon-v1-2.md) : les `qs` de chaque expert sont canonisés
//! (demi-octet 8 → 0) avant les comptes et le codage ; le répertoire porte les deux empreintes,
//! celle des octets du GGUF (d'origine) et celle de l'expert canonique. Sans l'option, les octets
//! écrits sont ceux de la v1.0, inchangés (témoin : le 20b recodé égal octet pour octet à F2).

use crate::gguf::{Gguf, REBOND, TamponAligne, est_expert, lire_a, lire_dans, ouvrir_direct};
use anyhow::{Context, Result, bail, ensure};
use rayon::prelude::*;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::Path;
use std::time::Instant;
use trc_codec::{ComptesMatrice, a_ecrire, blocs_canoniques, coder_matrice_v10, flux_bruts, preparer_matrice_avec};
use trc_format::*;

pub struct Options<'a> {
    pub source: &'a Path,
    pub dest: &'a Path,
    pub brut: bool,
    /// v1.2 : codes canoniques (drapeau CANONIQUE).
    pub canonique: bool,
    pub date: String,
    pub sha256_attendu: Option<[u8; 32]>,
}

/// SHA-256 d'un fichier entier, lu sans tampon par morceaux de 16 Mio alignés.
pub fn sha256_fichier(chemin: &Path) -> Result<([u8; 32], u64)> {
    use std::os::windows::fs::FileExt;
    let f = ouvrir_direct(chemin)?;
    let mut h = Sha256::new();
    let mut t = TamponAligne::nouveau(16 << 20);
    let mut n = 0u64;
    loop {
        // n reste multiple de 16 Mio jusqu'à la dernière lecture, courte, en fin de fichier.
        let k = f.seek_read(t.tranche_mut(), n)?;
        if k == 0 {
            break;
        }
        h.update(&t.tranche()[..k]);
        n += k as u64;
        if k < 16 << 20 {
            // Sans tampon, une lecture n'est courte qu'en fin de fichier. On ne relit pas pour
            // le vérifier : le décalage n n'est plus aligné et le système refuserait la lecture
            // (erreur 87, vue sur le 20b à la première version) ; l'appelant compare n à la
            // taille du fichier.
            break;
        }
    }
    Ok((h.finalize().into(), n))
}

pub fn hex(b: &[u8]) -> String {
    b.iter().map(|x| format!("{x:02x}")).collect()
}

/// Dimensions (R, C) des trois matrices d'experts, vérifiées sur toutes les couches.
pub fn dimensions(g: &Gguf, couches: u32, experts: u64) -> Result<[(u32, u32); 3]> {
    let mut d = [(0u32, 0u32); 3];
    for c in 0..couches {
        let ec = g.experts_couche(c)?;
        for j in 0..3 {
            let (w, b) = (ec.poids[j], ec.biais[j]);
            ensure!(w.type_ggml == 39 && w.n_dims == 3 && w.ne[2] == experts, "{} : type {} dims {:?} (MXFP4 [C, R, {experts}] attendu)", w.nom, w.type_ggml, w.ne);
            ensure!(b.type_ggml == 0 && b.n_dims == 2 && b.ne[0] == w.ne[1] && b.ne[1] == experts, "{} : type {} dims {:?} (F32 [R, E] attendu)", b.nom, b.type_ggml, b.ne);
            let rc = (w.ne[1] as u32, w.ne[0] as u32);
            if c == 0 {
                d[j] = rc;
            }
            ensure!(d[j] == rc, "{} : dimensions différentes de la couche 0", w.nom);
        }
    }
    Ok(d)
}

struct Hyper {
    couches: u32,
    experts: u64,
    k: u64,
    dims: [(u32, u32); 3],
}

fn hyper(g: &Gguf) -> Result<Hyper> {
    let arch = g.architecture()?;
    let couches = g.entier(&format!("{arch}.block_count"))? as u32;
    let experts = g.entier(&format!("{arch}.expert_count"))?;
    let k = g.entier(&format!("{arch}.expert_used_count"))?;
    let dims = dimensions(g, couches, experts)?;
    let n_exp = g.tenseurs.iter().filter(|t| est_expert(&t.nom)).count();
    ensure!(n_exp == 6 * couches as usize, "{n_exp} tenseurs d'experts, {} attendus", 6 * couches);
    Ok(Hyper { couches, experts, k, dims })
}

pub fn coder(o: &Options) -> Result<Value> {
    ensure!(!(o.brut && o.canonique), "--canonique et --brut s'excluent : le fichier brut garde les octets du GGUF");
    let t0 = Instant::now();
    let g = Gguf::ouvrir(o.source)?;
    let h = hyper(&g)?;
    let (n_c, n_e) = (h.couches as usize, h.experts as usize);
    let source = o.source.to_path_buf();
    let fil_sha = std::thread::spawn(move || sha256_fichier(&source));

    let mut w = Ecrivain::creer(o.dest).with_context(|| format!("création de {}", o.dest.display()))?;
    // MÉTA
    let nom_source = o.source.file_name().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default();
    let ajouts = vec![
        paire_chaine("troncons.codeur.version", &format!("trc-codeur {}", env!("CARGO_PKG_VERSION"))),
        paire_chaine("troncons.codeur.date", &o.date),
        paire_chaine("troncons.source.nom", &nom_source),
    ];
    w.ouvrir_section(SECTION_META)?;
    w.ecrire(&serialiser_meta(&g.kv_brut, g.n_kv, &ajouts))?;
    w.fermer_section();

    // RÉSIDENTS : table réservée, données recopiées (empreintes calculées au passage), table
    // réécrite, puis son empreinte au bout de la zone de données.
    let src = ouvrir_direct(o.source)?;
    let res_g: Vec<_> = g.tenseurs.iter().filter(|t| !est_expert(&t.nom)).collect();
    let (dec, _fin) = disposer_residents(&res_g.iter().map(|t| t.octets).collect::<Vec<_>>());
    let d_res = w.ouvrir_section(SECTION_RESIDENTS)?;
    w.reserver(8 + (TAILLE_ENTREE_RESIDENT * res_g.len()) as u64)?;
    w.aligner_sur(ALIGNEMENT)?;
    ensure!(w.position() - d_res == debut_zone_residents(res_g.len()));
    let zone = w.position();
    let mut residents = Vec::with_capacity(res_g.len());
    let mut octets_residents = 0u64;
    for (t, &d) in res_g.iter().zip(&dec) {
        let zeros = vec![0u8; (zone + d - w.position()) as usize];
        w.ecrire(&zeros)?;
        // Recopie par morceaux de 16 Mio : la mémoire ne dépend pas de la taille du tenseur
        // (`token_embd` fait 0,615 Go). L'empreinte64 (préfixe de SHA-256, § 4.12) se calcule au
        // fil des morceaux.
        let mut hh = Sha256::new();
        let mut fait = 0u64;
        while fait < t.octets {
            let n = (t.octets - fait).min(REBOND as u64) as usize;
            let morceau = lire_a(&src, t.decalage + fait, n)?;
            hh.update(&morceau);
            w.ecrire(&morceau)?;
            fait += n as u64;
        }
        let empreinte = u64::from_le_bytes(hh.finalize()[..8].try_into().unwrap());
        octets_residents += t.octets;
        residents.push(TenseurResident { nom: t.nom.clone(), type_ggml: t.type_ggml, ne: t.ne, n_dims: t.n_dims, decalage: d, octets: t.octets, empreinte });
    }
    let table = serialiser_table_residents(&residents)?;
    w.ecrire(&empreinte64(&table).to_le_bytes())?;
    w.reecrire(d_res, &table)?;
    w.fermer_section();
    let t_residents = t0.elapsed().as_secs_f64();

    // TABLES et RÉPERTOIRE réservés.
    let n_tables = if o.brut { 0 } else { n_c * 3 * 4 };
    let lg_tables = (8 + n_tables * (8 + 512) + 8) as u64;
    let d_tab = w.ouvrir_section(SECTION_TABLES)?;
    w.reserver(lg_tables)?;
    w.fermer_section();
    let lg_rep = (n_c * n_e * TAILLE_ENTREE_REPERTOIRE + 8) as u64;
    let d_rep = w.ouvrir_section(SECTION_REPERTOIRE)?;
    w.reserver(lg_rep)?;
    w.fermer_section();

    // TRONÇONS
    w.ouvrir_section(SECTION_TRONCONS)?;
    let mut tables: Vec<Table> = Vec::with_capacity(n_tables);
    let mut repertoire: Vec<EntreeRepertoire> = Vec::with_capacity(n_c * n_e);
    let mut par_couche = Vec::new();
    // Demi-octets 8 fondus en 0, par (couche, matrice) (v1.2 ; 0 sinon).
    let mut fondus = vec![[0u64; 3]; n_c];
    let paquet = 2 * rayon::current_num_threads().max(1);
    let taille_j: Vec<usize> = (0..3).map(|j| 17 * h.dims[j].0 as usize * (h.dims[j].1 as usize / 32)).collect();
    // Les blocs des experts [x0, x1) de la matrice j : d'un seul tenant dans le GGUF (§ 4.11 : le
    // bloc β de l'expert x est au bloc (x · R + r) · B + b du tenseur).
    let lire_experts = |t: &crate::gguf::TenseurGguf, j: usize, x0: usize, x1: usize, v: &mut Vec<u8>| -> Result<()> {
        v.resize(taille_j[j] * (x1 - x0), 0);
        lire_dans(&src, t.decalage + (taille_j[j] * x0) as u64, v)
    };
    let mut lus: [Vec<u8>; 3] = Default::default();
    for c in 0..h.couches {
        let tc = Instant::now();
        let ec = g.experts_couche(c)?;
        for j in 0..3 {
            ensure!(ec.poids[j].octets as usize == taille_j[j] * n_e, "{} : {} octets, {} attendus", ec.poids[j].nom, ec.poids[j].octets, taille_j[j] * n_e);
        }
        let biais: Vec<Vec<u8>> = (0..3).map(|j| lire_a(&src, ec.biais[j].decalage, ec.biais[j].octets as usize)).collect::<Result<_>>()?;
        let mut t_lecture = 0f64;
        // Passe 1 : les comptes de chaque tenseur, paquet par paquet.
        let mut tables_couche = Vec::with_capacity(3);
        if !o.brut {
            for j in 0..3 {
                let (r, b) = (h.dims[j].0 as usize, h.dims[j].1 as usize / 32);
                let mut comptes = ComptesMatrice::default();
                let mut x0 = 0;
                while x0 < n_e {
                    let x1 = (x0 + paquet).min(n_e);
                    let tl = Instant::now();
                    lire_experts(ec.poids[j], j, x0, x1, &mut lus[j])?;
                    t_lecture += tl.elapsed().as_secs_f64();
                    let partiel = lus[j]
                        .par_chunks_exact(taille_j[j])
                        .map(|s| preparer_matrice_avec(s, r, b, o.canonique))
                        .fold(ComptesMatrice::default, |mut a, p| {
                            a.ajouter(&p);
                            a
                        })
                        .reduce(ComptesMatrice::default, |mut a, x| {
                            a.fusionner(&x);
                            a
                        });
                    comptes.fusionner(&partiel);
                    x0 = x1;
                }
                let t = comptes.tables();
                tables.push(Table { couche: c as u16, matrice: j as u8, sorte: Sorte::Delta, contexte: 0, charge: Charge::Freq256(Box::new(t.delta.freq.clone().try_into().unwrap())) });
                for k in 0..3 {
                    tables.push(Table { couche: c as u16, matrice: j as u8, sorte: Sorte::CodesCtx, contexte: k as u8, charge: Charge::Freq256(Box::new(t.codes[k].freq.clone().try_into().unwrap())) });
                }
                tables_couche.push(t);
            }
        }
        let t_prep = tc.elapsed().as_secs_f64();
        // Passe 2 : relecture, codage, écriture dans l'ordre (couche, expert).
        let tcod = Instant::now();
        let mut x0 = 0;
        while x0 < n_e {
            let x1 = (x0 + paquet).min(n_e);
            let tl = Instant::now();
            for j in 0..3 {
                lire_experts(ec.poids[j], j, x0, x1, &mut lus[j])?;
            }
            t_lecture += tl.elapsed().as_secs_f64();
            let parties: Vec<(Vec<u8>, u32, u64, u64, [u64; 3])> = (x0..x1)
                .into_par_iter()
                .map(|x| {
                    let i = x - x0;
                    let blocs: Vec<&[u8]> = (0..3).map(|j| &lus[j][taille_j[j] * i..taille_j[j] * (i + 1)]).collect();
                    let bi: Vec<&[u8]> = (0..3)
                        .map(|j| {
                            let r = h.dims[j].0 as usize;
                            &biais[j][4 * r * x..4 * r * (x + 1)]
                        })
                        .collect();
                    // L'expert d'origine (§ 4.11) : les blocs des trois matrices, puis leurs biais.
                    let empreinte = empreinte64_morceaux(blocs.iter().chain(bi.iter()).copied());
                    // L'expert canonique (v1.2) : les mêmes octets, chaque demi-octet 8 des qs
                    // remplacé par 0 ; c'est lui que le codeur code et que le décodeur rend.
                    let mut n8 = [0u64; 3];
                    let canon: Vec<Vec<u8>> = if o.canonique {
                        (0..3)
                            .map(|j| {
                                let (v, n) = blocs_canoniques(blocs[j]);
                                n8[j] = n;
                                v
                            })
                            .collect()
                    } else {
                        Vec::new()
                    };
                    let empreinte_c = if o.canonique { empreinte64_morceaux(canon.iter().map(|v| &v[..]).chain(bi.iter().copied())) } else { 0 };
                    let mut flux: Vec<Vec<(Sorte, u8, u32, Vec<u8>)>> = Vec::with_capacity(3);
                    for j in 0..3 {
                        if o.brut {
                            flux.push(flux_bruts(blocs[j], bi[j]).into());
                        } else {
                            let (r, b) = (h.dims[j].0 as usize, h.dims[j].1 as usize / 32);
                            let p = if o.canonique { preparer_matrice_avec(&canon[j], r, b, false) } else { preparer_matrice_avec(blocs[j], r, b, false) };
                            flux.push(coder_matrice_v10(&p, bi[j], &tables_couche[j]).into());
                        }
                    }
                    let fe: Vec<FluxAEcrire> = (0..3).flat_map(|j| a_ecrire(j as u8, &flux[j]).collect::<Vec<_>>()).collect();
                    let (p, u) = assembler_partie(c as u16, x as u16, 0, 3, &fe);
                    (p, u, empreinte, empreinte_c, n8)
                })
                .collect();
            for (i, (p, u, empreinte, empreinte_c, n8)) in parties.into_iter().enumerate() {
                for j in 0..3 {
                    fondus[c as usize][j] += n8[j];
                }
                let x = x0 + i;
                let decalage = w.position();
                w.ecrire(&p)?;
                repertoire.push(EntreeRepertoire {
                    decalage,
                    longueur: [p.len() as u32, 0],
                    utiles: [u, 0],
                    empreinte_origine: empreinte,
                    empreinte_niveau: [empreinte64(&p[..u as usize]), 0],
                    couche: c as u16,
                    expert: x as u16,
                    empreinte_canonique: empreinte_c,
                });
            }
            x0 = x1;
        }
        // Durées relevées une seule fois, avant l'écriture du journal (la version à une passe
        // relisait la durée du codage après l'eprintln : elle pouvait dépasser le total).
        let t_cod = tcod.elapsed().as_secs_f64();
        let dur = tc.elapsed().as_secs_f64();
        eprintln!("couche {c:>3} : lecture {t_lecture:.1} s, comptes {t_prep:.1} s, codage {t_cod:.1} s, total {dur:.1} s ({:.0} s écoulées)", t0.elapsed().as_secs_f64());
        par_couche.push(json!({"couche": c, "lecture_s": t_lecture, "comptes_s": t_prep, "codage_s": t_cod, "total_s": dur}));
    }
    w.fermer_section();
    let tab = serialiser_tables(&tables);
    ensure!(tab.len() as u64 == lg_tables, "TABLES : {} octets, {lg_tables} réservés", tab.len());
    w.reecrire(d_tab, &tab)?;
    let rep = serialiser_repertoire(&repertoire);
    ensure!(rep.len() as u64 == lg_rep);
    w.reecrire(d_rep, &rep)?;

    let (sha, n_lus) = fil_sha.join().map_err(|_| anyhow::anyhow!("le fil du SHA-256 a paniqué"))??;
    ensure!(n_lus == g.taille, "SHA-256 sur {n_lus} octets, le GGUF en fait {}", g.taille);
    if let Some(att) = o.sha256_attendu {
        if att != sha {
            bail!("SHA-256 du GGUF {} différente de l'attendue {} : fichier non terminé (en-tête laissé à zéro)", hex(&sha), hex(&att));
        }
    }
    let mut lignes = [0u32; 4];
    let mut colonnes = [0u32; 4];
    for j in 0..3 {
        lignes[j] = h.dims[j].0;
        colonnes[j] = h.dims[j].1;
    }
    let entete = Entete {
        version: (1, if o.canonique { VERSION_MINEURE_CANONIQUE } else { 0 }),
        drapeaux: DRAPEAU_ALIGNE | if o.brut { DRAPEAU_BRUT } else { 0 } | if o.canonique { DRAPEAU_CANONIQUE } else { 0 },
        taille_fichier: 0,
        sha256_source: sha,
        taille_source: g.taille,
        couches: h.couches as u16,
        experts: h.experts as u16,
        k: h.k as u16,
        matrices: 3,
        lignes,
        colonnes,
        poids_par_bloc: 32,
        octets_par_bloc: 17,
        type_ggml: 39,
        niveaux: 1,
        classes_echelle: 3,
        partition: [0; 8],
        sections: [Section::default(); 8],
    };
    let taille = w.terminer(entete)?;
    let lg: Vec<u64> = repertoire.iter().map(|e| e.longueur[0] as u64).collect();
    let poids_tenseur: Vec<u64> = (0..3).map(|j| h.dims[j].0 as u64 * h.dims[j].1 as u64 * h.experts).collect();
    let total_fondus: u64 = fondus.iter().map(|m| m.iter().sum::<u64>()).sum();
    let total_poids: u64 = poids_tenseur.iter().sum::<u64>() * h.couches as u64;
    Ok(json!({
        "source": o.source.display().to_string(),
        "dest": o.dest.display().to_string(),
        "brut": o.brut,
        "canonique": o.canonique,
        "version": format!("1.{}", if o.canonique { VERSION_MINEURE_CANONIQUE } else { 0 }),
        "demi_octets_8_fondus": {"total": total_fondus, "part_des_poids": total_fondus as f64 / total_poids as f64,
            "par_tenseur": fondus.iter().enumerate().flat_map(|(c, m)| (0..3).map(move |j| json!({"couche": c, "matrice": j, "fondus": m[j]}))).collect::<Vec<_>>(),
            "poids_par_tenseur": poids_tenseur},
        "sha256_source": hex(&sha),
        "sha256_attendu": o.sha256_attendu.map(|a| hex(&a)),
        "sha256_egale": o.sha256_attendu.map(|a| a == sha),
        "taille_source": g.taille,
        "gguf_version": g.version, "gguf_alignement": g.alignement, "gguf_debut_donnees": g.debut_donnees,
        "taille_trc": taille,
        "couches": h.couches, "experts": h.experts, "k": h.k,
        "dims": h.dims.iter().map(|d| json!([d.0, d.1])).collect::<Vec<_>>(),
        "residents": residents.len(), "octets_residents": octets_residents,
        "tables": tables.len(),
        "troncon_octets": {"min": lg.iter().min(), "max": lg.iter().max(), "moyen": lg.iter().sum::<u64>() as f64 / lg.len() as f64, "total": lg.iter().sum::<u64>()},
        "duree_residents_s": t_residents,
        "duree_s": t0.elapsed().as_secs_f64(),
        "fils": rayon::current_num_threads(),
        "paquet_experts": paquet,
        "par_couche": par_couche,
    }))
}
