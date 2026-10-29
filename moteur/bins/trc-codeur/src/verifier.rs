//! La vérification C1 (ARCHITECTURE.md § 6.5 et § 7.1) : chaque expert du `.trc`, décodé par le
//! processeur (`trc-codec`), égal à l'original du GGUF, au bit près et par empreinte ; et tout
//! ce que le fichier recopie (en-tête contre GGUF, méta, résidents) égal à sa source.
//!
//! Par expert, cinq contrôles, tous comptés :
//! 1. l'empreinte des octets utiles de sa partie égale celle du répertoire ;
//! 2. la partie se lit et se décode sans erreur (voies à L, mots consommés) ;
//! 3. les octets d'origine reconstruits (blocs puis biais) égalent, octet pour octet, les
//!    tranches du GGUF (§ 4.11 : le bloc β de l'expert x est au bloc (x · R + r) · B + b) ;
//! 4. l'empreinte de l'expert reconstruit égale celle du répertoire ;
//! 5. l'empreinte des tranches du GGUF égale celle du répertoire (le codeur a haché le bon
//!    expert).
//! La cassure (`--casser C E`) retourne, en mémoire, un bit de la première médiane de la matrice
//! 0 du tronçon (C, E) après sa lecture : la vérification doit trouver exactement cet expert faux.
//!
//! Fichier v1.2 (drapeau CANONIQUE, genome/06-codon-v1-2.md) : le décodé est l'expert canonique.
//! Le contrôle 3 compare alors le décodé aux tranches du GGUF **canonisées** (chaque demi-octet 8
//! des `qs` remplacé par 0), octet pour octet ; le contrôle 4 compare son empreinte à
//! `empreinte_canonique` ; le contrôle 5 reste sur les octets bruts du GGUF (`empreinte_origine`).
//! Trois contrôles de plus : 6. l'empreinte des tranches canonisées ici égale `empreinte_canonique`
//! (second chemin de l'empreinte du codeur) ; 7. le décodé ne porte aucun demi-octet 8 ; 8. chaque
//! poids décodé est égal **en valeur** au poids du GGUF (K[code] en f64, où −0 = +0 ; échelles et
//! biais égaux au bit) : c'est l'énoncé de C1 pour la v1.2. Seconde cassure, `--casser-8 C E` :
//! dans l'expert décodé (C, E), le premier demi-octet 0 de la matrice 0 devient 8 ; le contrôle 8
//! doit tenir (même valeur) et les contrôles 3, 4 et 7 tomber : exactement cet expert faux.
//!
//! Mémoire bornée : les experts d'une couche sont vérifiés par paquets (2 × fils), leurs tranches
//! du GGUF lues d'un seul tenant pour chaque paquet ; la pointe ne dépend pas du nombre d'experts.
//! Les deux fichiers sont lus sans tampon (`gguf::ouvrir_direct`).

use crate::coder::{hex, sha256_fichier};
use crate::gguf::{Gguf, REBOND, est_expert, lire_a, lire_dans, ouvrir_direct};
use anyhow::{Result, ensure};
use rayon::prelude::*;
use sha2::{Digest, Sha256};
use serde_json::{Value, json};
use std::path::Path;
use std::time::Instant;
use trc_codec::{TablesFichier, blocs_canoniques, decoder_partie, verifier_partie};
use trc_format::*;

pub struct Options<'a> {
    pub trc: &'a Path,
    pub gguf: &'a Path,
    pub casser: Option<(u16, u16)>,
    pub casser_8: Option<(u16, u16)>,
    pub sha: bool,
}

/// Les valeurs E2M1 doublées (bit 3 = signe) : la même table que la référence f64
/// (`trc-reference`, `K_MXFP4`), réécrite ici pour un chemin indépendant du codec.
const K_E2M1: [f64; 16] = [0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, -0.0, -1.0, -2.0, -3.0, -4.0, -6.0, -8.0, -12.0];

/// Vrai si les blocs `a` et `b` (17 octets chacun, mêmes positions) ont des échelles égales au bit
/// et des poids égaux en valeur (comparaison f64, où −0 == +0).
fn egaux_en_valeur(a: &[u8], b: &[u8]) -> bool {
    a.len() == b.len()
        && a.chunks_exact(17).zip(b.chunks_exact(17)).all(|(x, y)| {
            x[0] == y[0] && x[1..].iter().zip(&y[1..]).all(|(&p, &q)| K_E2M1[(p & 15) as usize] == K_E2M1[(q & 15) as usize] && K_E2M1[(p >> 4) as usize] == K_E2M1[(q >> 4) as usize])
        })
}

fn porte_des_8(blocs: &[u8]) -> bool {
    blocs.chunks_exact(17).any(|x| x[1..].iter().any(|&o| porte_un_8(o)))
}

#[derive(Default, Clone)]
struct Res {
    partie_empreinte: bool,
    decode: bool,
    octets: bool,
    empreinte_decode: bool,
    empreinte_gguf: bool,
    /// v1.2 : contrôles 6, 7, 8 (vrais d'office sur un fichier non canonique).
    empreinte_canon_gguf: bool,
    sans_8: bool,
    valeur: bool,
    /// v1.2 : demi-octets 8 des tranches du GGUF (comptés par ce chemin), par matrice.
    fondus: [u64; 3],
    erreur: Option<String>,
    longueur: u64,
    utiles: u64,
    /// Par matrice : octets des flux MEDIANES, BIAIS, DELTA, CODES_CTX (ou bruts).
    flux: [[u64; 4]; 3],
}

impl Res {
    fn exact(&self) -> bool {
        self.partie_empreinte && self.decode && self.octets && self.empreinte_decode && self.empreinte_gguf && self.empreinte_canon_gguf && self.sans_8 && self.valeur
    }
}

pub fn verifier(o: &Options) -> Result<Value> {
    let t0 = Instant::now();
    let f = Fichier::ouvrir(o.trc)?;
    let t_ouvrir = t0.elapsed().as_secs_f64();
    let g = Gguf::ouvrir(o.gguf)?;
    let e = f.entete().clone();
    let canonique = e.est_canonique();
    let fil_sha = if o.sha {
        let p = o.gguf.to_path_buf();
        Some(std::thread::spawn(move || sha256_fichier(&p)))
    } else {
        None
    };
    // En-tête contre GGUF.
    let arch = g.architecture()?;
    let (n_c, n_e) = (e.couches as usize, e.experts as usize);
    let dims = crate::coder::dimensions(&g, e.couches as u32, e.experts as u64)?;
    let mut entete_ok = vec![];
    entete_ok.push(("taille_source", e.taille_source == g.taille));
    entete_ok.push(("couches", e.couches as u64 == g.entier(&format!("{arch}.block_count"))?));
    entete_ok.push(("experts", e.experts as u64 == g.entier(&format!("{arch}.expert_count"))?));
    entete_ok.push(("k", e.k as u64 == g.entier(&format!("{arch}.expert_used_count"))?));
    entete_ok.push(("dimensions", (0..3).all(|j| (e.lignes[j], e.colonnes[j]) == dims[j]) && e.lignes[3] == 0 && e.matrices == 3));
    entete_ok.push(("mxfp4", (e.type_ggml, e.poids_par_bloc, e.octets_par_bloc) == (39, 32, 17)));
    // Méta : u64 n + paires du GGUF octet pour octet + les trois paires du codeur.
    let m = f.meta();
    let cles_ajoutees: Vec<&str> = f.paires().iter().skip(g.n_kv as usize).map(|p| p.cle.as_str()).collect();
    let meta_ok = lu64(m, 0) == g.n_kv + 3 && m.len() >= 8 + g.kv_brut.len() && m[8..8 + g.kv_brut.len()] == g.kv_brut[..] && cles_ajoutees == ["troncons.codeur.version", "troncons.codeur.date", "troncons.source.nom"];
    // Résidents : mêmes tenseurs dans le même ordre, mêmes octets, empreintes justes.
    let trc = ouvrir_direct(o.trc)?;
    let src = ouvrir_direct(o.gguf)?;
    let res_g: Vec<_> = g.tenseurs.iter().filter(|t| !est_expert(&t.nom)).collect();
    let mut residents_faux = Vec::new();
    ensure!(res_g.len() == f.residents().len(), "{} résidents dans le .trc, {} dans le GGUF", f.residents().len(), res_g.len());
    for (t, r) in res_g.iter().zip(f.residents()) {
        // Comparaison et empreinte par morceaux de 16 Mio (mémoire indépendante de la taille).
        let mut ok = t.nom == r.nom && t.type_ggml == r.type_ggml && t.ne == r.ne && t.n_dims == r.n_dims && t.octets == r.octets;
        let mut hh = Sha256::new();
        let mut fait = 0u64;
        while ok && fait < t.octets {
            let n = (t.octets - fait).min(REBOND as u64) as usize;
            let a = lire_a(&src, t.decalage + fait, n)?;
            let b = lire_a(&trc, f.debut_donnees_residentes() + r.decalage + fait, n)?;
            ok &= a == b;
            hh.update(&b);
            fait += n as u64;
        }
        ok = ok && u64::from_le_bytes(hh.finalize()[..8].try_into().unwrap()) == r.empreinte;
        if !ok {
            residents_faux.push(r.nom.clone());
        }
    }
    let t_residents = t0.elapsed().as_secs_f64();

    let tables = TablesFichier::depuis_fichier(&f)?;
    let mut res: Vec<Res> = Vec::with_capacity(n_c * n_e);
    let paquet = 2 * rayon::current_num_threads().max(1);
    let taille_j: Vec<usize> = (0..3).map(|j| 17 * e.lignes[j] as usize * (e.colonnes[j] as usize / 32)).collect();
    let mut poids: [Vec<u8>; 3] = Default::default();
    for c in 0..n_c {
        let tc = Instant::now();
        let ec = g.experts_couche(c as u32)?;
        for j in 0..3 {
            ensure!(ec.poids[j].octets as usize == taille_j[j] * n_e, "{} : {} octets, {} attendus", ec.poids[j].nom, ec.poids[j].octets, taille_j[j] * n_e);
        }
        let biais: Vec<Vec<u8>> = (0..3).map(|j| lire_a(&src, ec.biais[j].decalage, ec.biais[j].octets as usize)).collect::<Result<_>>()?;
        let mut r_c: Vec<Res> = Vec::with_capacity(n_e);
        let mut x0 = 0;
        while x0 < n_e {
        let x1 = (x0 + paquet).min(n_e);
        // Les tranches du GGUF des experts [x0, x1), d'un seul tenant par matrice (§ 4.11).
        for j in 0..3 {
            poids[j].resize(taille_j[j] * (x1 - x0), 0);
            lire_dans(&src, ec.poids[j].decalage + (taille_j[j] * x0) as u64, &mut poids[j])?;
        }
        let r_p: Vec<Res> = (x0..x1)
            .into_par_iter()
            .map(|x| {
                let mut r = Res::default();
                let ent = *f.entree(c as u16, x as u16);
                r.longueur = ent.longueur[0] as u64;
                r.utiles = ent.utiles[0] as u64;
                let mut octets = match lire_a(&trc, ent.decalage, ent.longueur[0] as usize) {
                    Ok(v) => v,
                    Err(err) => {
                        r.erreur = Some(format!("lecture : {err}"));
                        return r;
                    }
                };
                if o.casser == Some((c as u16, x as u16)) {
                    if let Ok(p) = lire_partie(&octets) {
                        if let Some(d) = p.trouver(Sorte::Medianes, 0) {
                            let i = d.decalage as usize;
                            octets[i] ^= 1;
                        }
                    }
                }
                r.partie_empreinte = verifier_partie(&f, c as u16, x as u16, 0, &octets).is_ok();
                let p = match lire_partie(&octets) {
                    Ok(p) => p,
                    Err(err) => {
                        r.erreur = Some(format!("partie : {err}"));
                        return r;
                    }
                };
                for d in &p.flux {
                    let k = match d.sorte {
                        Sorte::Medianes | Sorte::EchellesBrutes => 0,
                        Sorte::Biais => 1,
                        Sorte::Delta => 2,
                        _ => 3,
                    };
                    r.flux[d.matrice as usize % 3][k] += d.longueur as u64;
                }
                let mut dec = match decoder_partie(&f, Some(&tables), &p, true) {
                    Ok(d) => d,
                    Err(err) => {
                        r.erreur = Some(format!("décodage : {err}"));
                        return r;
                    }
                };
                r.decode = true;
                if o.casser_8 == Some((c as u16, x as u16)) {
                    let q = &mut dec.matrices[0].codes;
                    if let Some(i) = (0..2 * q.len()).find(|&i| (q[i / 2] >> (4 * (i % 2))) & 15 == 0) {
                        q[i / 2] |= 8 << (4 * (i % 2));
                    }
                }
                let mut ok = true;
                let mut tranches: Vec<&[u8]> = Vec::with_capacity(6);
                for j in 0..3 {
                    let t = taille_j[j];
                    tranches.push(&poids[j][t * (x - x0)..t * (x - x0 + 1)]);
                }
                for j in 0..3 {
                    let rr = e.lignes[j] as usize;
                    tranches.push(&biais[j][4 * rr * x..4 * rr * (x + 1)]);
                }
                // Fichier canonique : les tranches canonisées par ce chemin (pas par le codec du codeur).
                let canon: Vec<Vec<u8>> = if canonique {
                    (0..3)
                        .map(|j| {
                            let (v, n) = blocs_canoniques(tranches[j]);
                            r.fondus[j] = n;
                            v
                        })
                        .collect()
                } else {
                    Vec::new()
                };
                let mut valeur = true;
                let mut sans_8 = true;
                for j in 0..3 {
                    let decode = dec.matrices[j].blocs_origine();
                    let attendu: &[u8] = if canonique { &canon[j] } else { tranches[j] };
                    ok &= decode == attendu;
                    ok &= dec.matrices[j].octets_biais() == tranches[3 + j];
                    if canonique {
                        valeur &= egaux_en_valeur(&decode, tranches[j]) && dec.matrices[j].octets_biais() == tranches[3 + j];
                        sans_8 &= !porte_des_8(&decode);
                    }
                }
                r.octets = ok;
                r.valeur = valeur;
                r.sans_8 = sans_8;
                r.empreinte_decode = dec.empreinte() == ent.empreinte_du_decode(canonique);
                r.empreinte_gguf = empreinte64_morceaux(tranches.iter().copied()) == ent.empreinte_origine;
                r.empreinte_canon_gguf = !canonique || empreinte64_morceaux(canon.iter().map(|v| &v[..]).chain(tranches[3..].iter().copied())) == ent.empreinte_canonique;
                r
            })
            .collect();
        r_c.extend(r_p);
        x0 = x1;
        }
        let faux = r_c.iter().filter(|r| !r.exact()).count();
        eprintln!("couche {c:>3} : {} experts, {faux} faux, {:.1} s ({:.0} s écoulées)", n_e, tc.elapsed().as_secs_f64(), t0.elapsed().as_secs_f64());
        res.extend(r_c);
    }
    let t_experts = t0.elapsed().as_secs_f64();
    let sha = match fil_sha {
        Some(h) => {
            let (s, n) = h.join().map_err(|_| anyhow::anyhow!("fil SHA-256"))??;
            Some((hex(&s), s == e.sha256_source && n == g.taille))
        }
        None => None,
    };

    // Bilan C1.
    let exacts = res.iter().filter(|r| r.exact()).count();
    let mut faux: Vec<Value> = Vec::new();
    for (i, r) in res.iter().enumerate() {
        if !r.exact() && faux.len() < 50 {
            faux.push(json!({"couche": i / n_e, "expert": i % n_e, "empreinte_partie": r.partie_empreinte, "decode": r.decode, "octets": r.octets, "empreinte_decode": r.empreinte_decode, "empreinte_gguf": r.empreinte_gguf, "empreinte_canonique_gguf": r.empreinte_canon_gguf, "sans_8": r.sans_8, "valeur": r.valeur, "erreur": r.erreur}));
        }
    }
    let compte = |p: &dyn Fn(&Res) -> bool| res.iter().filter(|r| p(r)).count();

    // Taux. Original : blocs MXFP4 (17 o par 32 poids) ; codé : MEDIANES + DELTA + CODES_CTX
    // (la comptabilité de l'étude 03) ; et les variantes avec tables, biais, en-têtes, bourrage.
    let blocs_expert: u64 = (0..3).map(|j| 17 * e.lignes[j] as u64 * e.colonnes[j] as u64 / 32).sum();
    let biais_expert: u64 = (0..3).map(|j| 4 * e.lignes[j] as u64).sum();
    let poids_expert: u64 = (0..3).map(|j| e.lignes[j] as u64 * e.colonnes[j] as u64).sum();
    let somme = |k: usize| -> u64 { res.iter().map(|r| r.flux.iter().map(|m| m[k]).sum::<u64>()).sum() };
    let (s_med, s_bia, s_del, s_cod) = (somme(0), somme(1), somme(2), somme(3));
    let n_exp = res.len() as u64;
    let lg: Vec<u64> = res.iter().map(|r| r.longueur).collect();
    let octets_tables = e.sections[SECTION_TABLES].longueur;
    let taux_03 = (blocs_expert * n_exp) as f64 / (s_med + s_del + s_cod) as f64;
    let bpp = |o: u64, poids: u64| o as f64 * 8.0 / poids as f64;
    // Par tenseur (couche, matrice), pour la comparaison à F1.
    let mut par_tenseur = Vec::new();
    for c in 0..n_c {
        for j in 0..3 {
            let poids = e.lignes[j] as u64 * e.colonnes[j] as u64 * n_e as u64;
            let s = |k: usize| -> u64 { res[c * n_e..(c + 1) * n_e].iter().map(|r| r.flux[j][k]).sum() };
            par_tenseur.push(json!({"couche": c, "matrice": j, "poids": poids, "octets_medianes": s(0), "octets_delta": s(2), "octets_codes": s(3), "bpp_codes": bpp(s(3), poids), "bpp_delta": bpp(s(2), poids), "bpp_medianes": bpp(s(0), poids)}));
        }
    }
    let troncons_couche: Vec<Value> = (0..n_c)
        .map(|c| {
            let l = &lg[c * n_e..(c + 1) * n_e];
            json!({"couche": c, "min": l.iter().min(), "max": l.iter().max(), "moyen": l.iter().sum::<u64>() as f64 / l.len() as f64})
        })
        .collect();
    let c1 = exacts == res.len() && residents_faux.is_empty() && meta_ok && entete_ok.iter().all(|x| x.1) && sha.as_ref().is_none_or(|s| s.1);
    Ok(json!({
        "trc": o.trc.display().to_string(),
        "gguf": o.gguf.display().to_string(),
        "brut": e.est_brut(),
        "casser": o.casser.map(|(c, x)| json!([c, x])),
        "version": [e.version.0, e.version.1],
        "taille_trc": e.taille_fichier,
        "C1": c1,
        "experts": res.len(),
        "experts_exacts": exacts,
        "experts_faux": res.len() - exacts,
        "controles_faux": {
            "empreinte_partie": compte(&|r| !r.partie_empreinte),
            "decodage": compte(&|r| !r.decode),
            "octets": compte(&|r| !r.octets),
            "empreinte_decode": compte(&|r| !r.empreinte_decode),
            "empreinte_gguf": compte(&|r| !r.empreinte_gguf),
            "empreinte_canonique_gguf": compte(&|r| !r.empreinte_canon_gguf),
            "porte_un_8": compte(&|r| !r.sans_8),
            "valeur": compte(&|r| !r.valeur),
        },
        "canonique": canonique,
        "casser_8": o.casser_8.map(|(c, x)| json!([c, x])),
        "demi_octets_8_du_gguf": res.iter().map(|r| r.fondus.iter().sum::<u64>()).sum::<u64>(),
        "faux": faux,
        "entete": entete_ok.iter().map(|(k, v)| (k.to_string(), json!(v))).collect::<serde_json::Map<_, _>>(),
        "meta_identique": meta_ok,
        "residents": res_g.len(),
        "residents_faux": residents_faux,
        "sha256_source_recalculee": sha.as_ref().map(|s| &s.0),
        "sha256_egale_entete": sha.as_ref().map(|s| s.1),
        "sha256_entete": hex(&e.sha256_source),
        "taux": {
            "comptabilite": "original = blocs MXFP4 (17 o / 32 poids) ; codé = MEDIANES + DELTA + CODES_CTX, flux sérialisés (en-têtes de flux et bourrage à 16 compris), comme l'étude 03",
            "r_03": taux_03,
            "bpp_total_03": bpp(s_med + s_del + s_cod, poids_expert * n_exp),
            "bpp_codes": bpp(s_cod, poids_expert * n_exp),
            "bpp_delta": bpp(s_del, poids_expert * n_exp),
            "bpp_medianes": bpp(s_med, poids_expert * n_exp),
            "bpp_avec_tables": bpp(s_med + s_del + s_cod + octets_tables, poids_expert * n_exp),
            "r_troncons": ((blocs_expert + biais_expert) * n_exp) as f64 / lg.iter().sum::<u64>() as f64,
            "octets_flux": {"medianes": s_med, "biais": s_bia, "delta": s_del, "codes": s_cod},
            "octets_tables": octets_tables,
        },
        "troncon_octets": {"min": lg.iter().min(), "max": lg.iter().max(), "moyen": lg.iter().sum::<u64>() as f64 / lg.len().max(1) as f64, "total": lg.iter().sum::<u64>(), "origine_par_expert": blocs_expert + biais_expert},
        "troncons_par_couche": troncons_couche,
        "par_tenseur": par_tenseur,
        "duree_ouverture_s": t_ouvrir,
        "duree_residents_s": t_residents,
        "duree_experts_s": t_experts - t_residents,
        "duree_s": t0.elapsed().as_secs_f64(),
        "fils": rayon::current_num_threads(),
        "paquet_experts": 2 * rayon::current_num_threads().max(1),
    }))
}
