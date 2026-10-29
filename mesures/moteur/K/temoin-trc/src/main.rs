//! Témoin K1 sur un vrai fichier `.trc` du lot F.
//!
//! Pour chaque expert demandé :
//! 1. la partie de niveau 0 est lue du fichier (décalage et longueur du répertoire, § 4.7) ;
//! 2. le processeur la reconstruit par `trc_codec::reconstruire_avec` (empreinte de la partie
//!    vérifiée contre le répertoire, puis décodage du lot F) : c'est l'oracle de la couture
//!    (§ 5.4) ;
//! 3. la carte la décode par `Noyaux::decoder_expert` (image embarquée, API du pilote) dans un
//!    emplacement mis à zéro ; l'emplacement redescend sur l'hôte ;
//! 4. comparaisons : l'emplacement entier, bourrage compris, contre l'emplacement attendu que
//!    l'on construit depuis la reconstruction du processeur (disposition SoA, § 5.6) ; puis les
//!    octets de la carte remis dans la disposition d'origine (§ 4.11) contre l'empreinte de
//!    l'expert d'origine écrite au répertoire (§ 4.12), donc contre le GGUF à travers C1 ;
//!    enfin les compteurs de contrôle de la carte (voies hors de L, format, pointeurs).
//!
//! Le décodeur de la carte (lot K) et celui du processeur (lot F) ont été écrits séparément,
//! depuis le seul § 4 ; le codeur est celui du lot F : c'est le second codeur du témoin K1, après
//! le codeur indépendant du banc C++ (banc/banc_k.cu).
//!
//! Cassures (`--casser`) : `lut` corrompt une fente de la LUT de CODES_CTX (κ = 1, matrice 0) de
//! chaque couche : la sortie doit être fausse ; `flux` retourne un bit au milieu de CODES_CTX de
//! la matrice 1 de la partie envoyée à la carte (le processeur garde la partie intacte) : les
//! voies doivent sortir de L et la sortie être fausse.
//!
//! Usage : `temoin-trc <fichier.trc> <journal.json> [--couches a-b] [--experts n] [--fils n]
//! [--casser lut|flux]`.

use std::io::{Read, Seek, SeekFrom};
use std::path::PathBuf;
use std::time::Instant;

use trc_codec::{ExpertDecode, TablesFichier};
use trc_cuda::{Contexte, Flux, HoteEpingle, MemoireCarte, copier_vers_carte, copier_vers_hote};
use trc_format::{Fichier, Sorte, empreinte64_morceaux};
use trc_noyaux::Noyaux;
use trc_noyaux::abi::{self, DescDecodage, DimsExpert};

struct Options {
    fichier: PathBuf,
    journal: PathBuf,
    couches: Option<(u16, u16)>,
    experts: Option<u16>,
    fils: usize,
    casser: String,
}

fn options() -> Options {
    let a: Vec<String> = std::env::args().collect();
    if a.len() < 3 {
        eprintln!("usage : temoin-trc <fichier.trc> <journal.json> [--couches a-b] [--experts n] [--fils n] [--casser lut|flux]");
        std::process::exit(2);
    }
    let mut o = Options { fichier: a[1].clone().into(), journal: a[2].clone().into(), couches: None, experts: None, fils: 3, casser: String::new() };
    let mut i = 3;
    while i < a.len() {
        let v = a.get(i + 1).cloned().unwrap_or_default();
        match a[i].as_str() {
            "--couches" => {
                let (x, y) = v.split_once('-').unwrap_or((&v, &v));
                o.couches = Some((x.parse().expect("--couches"), y.parse().expect("--couches")));
            }
            "--experts" => o.experts = Some(v.parse().expect("--experts")),
            "--fils" => o.fils = v.parse().expect("--fils"),
            "--casser" => o.casser = v,
            x => panic!("option inconnue : {x}"),
        }
        i += 2;
    }
    assert!(matches!(o.casser.as_str(), "" | "lut" | "flux"), "--casser lut|flux");
    o
}

/// L'emplacement attendu (disposition SoA, § 5.6) d'un expert reconstruit par le processeur ;
/// bourrage à zéro (la carte écrit dans un emplacement mis à zéro).
fn emplacement_attendu(x: &ExpertDecode, dims: &DimsExpert) -> Vec<u8> {
    let mut v = vec![0u8; dims.taille_emplacement() as usize];
    for (j, m) in x.matrices.iter().enumerate() {
        let d = dims.disposition(j);
        let b = d.base as usize;
        v[b..b + m.codes.len()].copy_from_slice(&m.codes);
        let e = b + d.echelles as usize;
        v[e..e + m.echelles.len()].copy_from_slice(&m.echelles);
        let bi = b + d.biais as usize;
        for (i, f) in m.biais.iter().enumerate() {
            v[bi + 4 * i..bi + 4 * i + 4].copy_from_slice(&f.to_le_bytes());
        }
    }
    v
}

/// L'empreinte de l'expert d'origine (§ 4.11, § 4.12) calculée depuis l'emplacement de la carte :
/// pour j = 0, 1, 2 les blocs [e, qs × 16] dans l'ordre β, puis pour j = 0, 1, 2 les biais.
fn empreinte_depuis_emplacement(empl: &[u8], dims: &DimsExpert) -> u64 {
    let mut blocs: Vec<Vec<u8>> = Vec::new();
    let mut biais: Vec<&[u8]> = Vec::new();
    for j in 0..3 {
        let d = dims.disposition(j);
        let b = d.base as usize;
        let n = dims.blocs(j) as usize;
        let mut v = Vec::with_capacity(17 * n);
        for beta in 0..n {
            v.push(empl[b + d.echelles as usize + beta]);
            v.extend_from_slice(&empl[b + 16 * beta..b + 16 * beta + 16]);
        }
        blocs.push(v);
        let bi = b + d.biais as usize;
        biais.push(&empl[bi..bi + 4 * dims.lignes[j] as usize]);
    }
    empreinte64_morceaux(blocs.iter().map(|v| &v[..]).chain(biais.into_iter()))
}

/// Octets faux par zone de l'emplacement : codes, échelles, biais, bourrage.
fn ecarts(a: &[u8], b: &[u8], dims: &DimsExpert) -> [u64; 4] {
    let mut z = [0u64; 4];
    for j in 0..3 {
        let d = dims.disposition(j);
        let base = d.base as usize;
        let nb = dims.blocs(j) as usize;
        let r = dims.lignes[j] as usize;
        for i in 0..d.pas as usize {
            if a[base + i] != b[base + i] {
                let zone = if i < 16 * nb {
                    0
                } else if i >= d.echelles as usize && i < d.echelles as usize + nb {
                    1
                } else if i >= d.biais as usize && i < d.biais as usize + 4 * r {
                    2
                } else {
                    3
                };
                z[zone] += 1;
            }
        }
    }
    z
}

fn vers_octets(v: &[u32]) -> Vec<u8> {
    v.iter().flat_map(|x| x.to_le_bytes()).collect()
}

/// Les LUT d'une couche dans la disposition des noyaux (`abi::luts_couche`), depuis les tables
/// du fichier : pour la matrice j, DELTA contexte 0, puis CODES_CTX contextes 0, 1, 2.
fn luts_de_la_couche(f: &Fichier, c: u16) -> Vec<u32> {
    let freq = |j: u8, s: Sorte, ctx: u8| f.table(c, j, s, ctx).and_then(|t| t.charge.frequences());
    let t: [[Option<&[u16]>; 4]; 3] = std::array::from_fn(|j| {
        let j = j as u8;
        [freq(j, Sorte::Delta, 0), freq(j, Sorte::CodesCtx, 0), freq(j, Sorte::CodesCtx, 1), freq(j, Sorte::CodesCtx, 2)]
    });
    abi::luts_couche(&t).expect("tables du fichier")
}

#[derive(Default)]
struct Bilan {
    experts: u64,
    faux_contre_codec: u64,
    faux_contre_repertoire: u64,
    erreurs_codec: u64,
    octets_faux: [u64; 4],
    hors_l: u64,
    format: u64,
    pointeurs: u64,
    octets_parties: u64,
    octets_emplacements: u64,
    lot_faux: u64,
    lot_hors_l: u64,
    lot_format: u64,
}

impl Bilan {
    fn ajouter(&mut self, o: &Bilan) {
        self.experts += o.experts;
        self.faux_contre_codec += o.faux_contre_codec;
        self.faux_contre_repertoire += o.faux_contre_repertoire;
        self.erreurs_codec += o.erreurs_codec;
        for i in 0..4 {
            self.octets_faux[i] += o.octets_faux[i];
        }
        self.hors_l += o.hors_l;
        self.format += o.format;
        self.pointeurs += o.pointeurs;
        self.octets_parties += o.octets_parties;
        self.octets_emplacements += o.octets_emplacements;
        self.lot_faux += o.lot_faux;
        self.lot_hors_l += o.lot_hors_l;
        self.lot_format += o.lot_format;
    }
    fn json(&self) -> String {
        format!(
            "\"experts\": {}, \"experts_faux_contre_trc_codec\": {}, \"experts_faux_contre_repertoire\": {}, \"erreurs_trc_codec\": {}, \
             \"octets_faux\": {{\"codes\": {}, \"echelles\": {}, \"biais\": {}, \"bourrage\": {}}}, \"voies_hors_L\": {}, \
             \"erreurs_format\": {}, \"pointeurs_faux\": {}, \"octets_parties\": {}, \"octets_emplacements\": {},              \"lot\": {{\"experts_faux_contre_trc_codec\": {}, \"voies_hors_L\": {}, \"erreurs_format\": {}}}",
            self.experts,
            self.faux_contre_codec,
            self.faux_contre_repertoire,
            self.erreurs_codec,
            self.octets_faux[0],
            self.octets_faux[1],
            self.octets_faux[2],
            self.octets_faux[3],
            self.hors_l,
            self.format,
            self.pointeurs,
            self.octets_parties,
            self.octets_emplacements,
            self.lot_faux,
            self.lot_hors_l,
            self.lot_format
        )
    }
}

fn main() {
    let o = options();
    let t0 = Instant::now();
    let fichier = Fichier::ouvrir(&o.fichier).expect("ouverture du .trc (vérifiée par trc-format)");
    let e = fichier.entete().clone();
    assert!(!e.est_brut(), "fichier brut : ce témoin vise le décodeur");
    let dims = DimsExpert { lignes: [e.lignes[0], e.lignes[1], e.lignes[2]], colonnes: [e.colonnes[0], e.colonnes[1], e.colonnes[2]] };
    dims.verifier().expect("dimensions");
    let tables = TablesFichier::depuis_fichier(&fichier).expect("tables du fichier");
    let (c0, c1) = o.couches.unwrap_or((0, e.couches - 1));
    let n_exp = o.experts.unwrap_or(e.experts).min(e.experts);

    let ctx = Contexte::nouveau(0).expect("contexte CUDA");
    let flux = Flux::nouveau(&ctx, false).unwrap();
    let noyaux = Noyaux::charger(&ctx).expect("image des noyaux");
    let te = dims.taille_emplacement() as usize;
    let lmax = fichier.repertoire().iter().map(|r| r.longueur[0] as usize).max().unwrap();
    let mut h_partie = HoteEpingle::allouer(&ctx, lmax, false).unwrap();
    let mut h_empl = HoteEpingle::allouer(&ctx, te, false).unwrap();
    let mut h_luts = HoteEpingle::allouer(&ctx, abi::LUTS_PAR_COUCHE * 4, false).unwrap();
    let mut h_ctl = HoteEpingle::allouer(&ctx, 16, false).unwrap();
    let d_partie = MemoireCarte::allouer(&ctx, lmax).unwrap();
    let d_empl = MemoireCarte::allouer(&ctx, te).unwrap();
    let d_luts = MemoireCarte::allouer(&ctx, abi::LUTS_PAR_COUCHE * 4).unwrap();
    let d_ctl = MemoireCarte::allouer(&ctx, 16).unwrap();
    let mut lecteur = std::fs::File::open(&o.fichier).unwrap();
    // Lot : les paquets de 8 experts décodés aussi en un lancement par noyau (decoder_lot), et
    // comparés aux mêmes attendus (extension de la couture N, REPRISE-K).
    const PAQUET: usize = 8;
    let mut h_parties_lot = HoteEpingle::allouer(&ctx, PAQUET * lmax, false).unwrap();
    let mut h_empls_lot = HoteEpingle::allouer(&ctx, PAQUET * te, false).unwrap();
    let mut h_ctl_lot = HoteEpingle::allouer(&ctx, PAQUET * 16, false).unwrap();
    let mut h_descs = HoteEpingle::allouer(&ctx, PAQUET * 32, false).unwrap();
    let d_parties_lot = MemoireCarte::allouer(&ctx, PAQUET * lmax).unwrap();
    let d_empls_lot = MemoireCarte::allouer(&ctx, PAQUET * te).unwrap();
    let d_ctl_lot = MemoireCarte::allouer(&ctx, PAQUET * 16).unwrap();
    let d_descs = MemoireCarte::allouer(&ctx, PAQUET * 32).unwrap();

    let mut total = Bilan::default();
    let mut lignes = Vec::new();
    for c in c0..=c1 {
        let tc = Instant::now();
        let mut luts = luts_de_la_couche(&fichier, c);
        if o.casser == "lut" {
            // Matrice 0, table 1 + κ avec κ = 1 (CODES_CTX des blocs à la médiane), fente 2 048.
            luts[(0 * 4 + 2) * 4096 + 2048] ^= 1;
        }
        h_luts.tranche_mut()[..luts.len() * 4].copy_from_slice(&vers_octets(&luts));
        copier_vers_carte(d_luts.tout(), &h_luts, 0, luts.len() * 4, &flux).unwrap();
        let mut bc = Bilan::default();
        // Par paquets de 8 experts : lecture, reconstruction du processeur en parallèle, carte.
        let mut x0 = 0u16;
        while x0 < n_exp {
            let x1 = (x0 + PAQUET as u16).min(n_exp);
            let parties: Vec<Vec<u8>> = (x0..x1)
                .map(|x| {
                    let r = fichier.entree(c, x);
                    let mut v = vec![0u8; r.longueur[0] as usize];
                    lecteur.seek(SeekFrom::Start(r.decalage)).unwrap();
                    lecteur.read_exact(&mut v).unwrap();
                    v
                })
                .collect();
            let attendus: Vec<Option<Vec<u8>>> = std::thread::scope(|s| {
                let morceau = parties.len().div_ceil(o.fils.max(1));
                let poignees: Vec<_> = parties
                    .chunks(morceau)
                    .enumerate()
                    .map(|(k, ps)| {
                        let (fichier, tables, dims) = (&fichier, &tables, &dims);
                        s.spawn(move || {
                            ps.iter()
                                .enumerate()
                                .map(|(i, p)| {
                                    let x = x0 + (k * morceau + i) as u16;
                                    trc_codec::reconstruire_avec(fichier, Some(tables), c, x, &[&p[..]], true)
                                        .map(|d| emplacement_attendu(&d, dims))
                                        .map_err(|err| eprintln!("trc-codec ({c}, {x}) : {err}"))
                                        .ok()
                                })
                                .collect::<Vec<_>>()
                        })
                    })
                    .collect();
                poignees.into_iter().flat_map(|p| p.join().unwrap()).collect()
            });
            for (i, p) in parties.iter().enumerate() {
                let x = x0 + i as u16;
                let mut envoi = p.clone();
                if o.casser == "flux" {
                    let pt = trc_format::lire_partie(&envoi).unwrap();
                    let d = *pt.trouver(Sorte::CodesCtx, 1).unwrap();
                    envoi[(d.decalage + d.longueur / 2) as usize] ^= 0x10;
                }
                h_partie.tranche_mut()[..envoi.len()].copy_from_slice(&envoi);
                h_ctl.tranche_mut()[..16].fill(0);
                copier_vers_carte(d_partie.tout(), &h_partie, 0, envoi.len(), &flux).unwrap();
                copier_vers_carte(d_ctl.tout(), &h_ctl, 0, 16, &flux).unwrap();
                d_empl.remplir(d_empl.tout(), 0, &flux).unwrap();
                noyaux
                    .decoder_expert(d_partie.vue(0, envoi.len()), d_empl.tout(), d_luts.tout(), &dims, d_ctl.tout(), &flux)
                    .unwrap();
                copier_vers_hote(&mut h_empl, 0, d_empl.tout(), &flux).unwrap();
                copier_vers_hote(&mut h_ctl, 0, d_ctl.tout(), &flux).unwrap();
                flux.synchroniser().unwrap();
                let ctl: [u32; 4] = std::array::from_fn(|k| u32::from_le_bytes(h_ctl.tranche()[4 * k..4 * k + 4].try_into().unwrap()));
                let empl = &h_empl.tranche()[..te];
                bc.experts += 1;
                bc.hors_l += ctl[0] as u64;
                bc.format += ctl[1] as u64;
                bc.pointeurs += ctl[2] as u64;
                bc.octets_parties += fichier.entree(c, x).utiles[0] as u64;
                bc.octets_emplacements += te as u64;
                match &attendus[i] {
                    Some(a) => {
                        if a[..] != empl[..] {
                            bc.faux_contre_codec += 1;
                            let z = ecarts(a, empl, &dims);
                            for k in 0..4 {
                                bc.octets_faux[k] += z[k];
                            }
                        }
                    }
                    None => bc.erreurs_codec += 1,
                }
                if empreinte_depuis_emplacement(empl, &dims) != fichier.entree(c, x).empreinte_origine {
                    bc.faux_contre_repertoire += 1;
                }
            }
            // Le même paquet en un lot.
            let n = parties.len();
            h_ctl_lot.tranche_mut()[..16 * n].fill(0);
            for (i, p) in parties.iter().enumerate() {
                let mut envoi = p.clone();
                if o.casser == "flux" {
                    let pt = trc_format::lire_partie(&envoi).unwrap();
                    let d = *pt.trouver(Sorte::CodesCtx, 1).unwrap();
                    envoi[(d.decalage + d.longueur / 2) as usize] ^= 0x10;
                }
                h_parties_lot.tranche_mut()[i * lmax..i * lmax + envoi.len()].copy_from_slice(&envoi);
                let desc = DescDecodage {
                    partie: d_parties_lot.vue(i * lmax, envoi.len()).adresse,
                    emplacement: d_empls_lot.vue(i * te, te).adresse,
                    luts: d_luts.tout().adresse,
                    controle: d_ctl_lot.vue(16 * i, 16).adresse,
                };
                h_descs.tranche_mut()[32 * i..32 * i + 32].copy_from_slice(&desc.octets());
            }
            copier_vers_carte(d_parties_lot.tout(), &h_parties_lot, 0, n * lmax, &flux).unwrap();
            copier_vers_carte(d_ctl_lot.tout(), &h_ctl_lot, 0, 16 * n, &flux).unwrap();
            copier_vers_carte(d_descs.tout(), &h_descs, 0, 32 * n, &flux).unwrap();
            d_empls_lot.remplir(d_empls_lot.tout(), 0, &flux).unwrap();
            noyaux.decoder_lot(d_descs.tout(), n as u32, &dims, &flux).unwrap();
            copier_vers_hote(&mut h_empls_lot, 0, d_empls_lot.tout(), &flux).unwrap();
            copier_vers_hote(&mut h_ctl_lot, 0, d_ctl_lot.tout(), &flux).unwrap();
            flux.synchroniser().unwrap();
            for i in 0..n {
                let empl = &h_empls_lot.tranche()[i * te..(i + 1) * te];
                let ctl: Vec<u32> =
                    (0..4).map(|k| u32::from_le_bytes(h_ctl_lot.tranche()[16 * i + 4 * k..16 * i + 4 * k + 4].try_into().unwrap())).collect();
                bc.lot_hors_l += ctl[0] as u64;
                bc.lot_format += ctl[1] as u64;
                let faux = match &attendus[i] {
                    Some(a) => a[..] != empl[..],
                    None => true,
                };
                bc.lot_faux += faux as u64;
            }
            x0 = x1;
        }
        eprintln!(
            "couche {c} : {} experts, faux contre trc-codec {}, contre le répertoire {}, hors L {}, format {}, pointeurs {} ; lot : faux {}, hors L {} ; {:.1} s",
            bc.experts,
            bc.faux_contre_codec,
            bc.faux_contre_repertoire,
            bc.hors_l,
            bc.format,
            bc.pointeurs,
            bc.lot_faux,
            bc.lot_hors_l,
            tc.elapsed().as_secs_f64()
        );
        lignes.push(format!("    {{\"couche\": {c}, {}, \"secondes\": {:.2}}}", bc.json(), tc.elapsed().as_secs_f64()));
        total.ajouter(&bc);
    }

    let temoin_tient = total.faux_contre_codec == 0
        && total.faux_contre_repertoire == 0
        && total.erreurs_codec == 0
        && total.hors_l == 0
        && total.format == 0
        && total.pointeurs == 0
        && total.lot_faux == 0
        && total.lot_hors_l == 0
        && total.lot_format == 0
        && total.experts > 0;
    let commande: Vec<String> = std::env::args().collect();
    let j = format!(
        "{{\n  \"outil\": \"temoin-trc\", \"etape\": \"K1\", \"commande\": {:?},\n  \"carte\": {:?}, \"pilote\": {}, \"casser\": {:?}, \"fils\": {},\n  \
         \"fichier\": {:?}, \"taille_fichier\": {}, \"version\": \"{}.{}\", \"dims\": {{\"lignes\": {:?}, \"colonnes\": {:?}}},\n  \"couches\": [\n{}\n  ],\n  \"total\": {{{}}},\n  \
         \"temoin_tient\": {},\n  \"secondes\": {:.1}\n}}\n",
        commande.join(" "),
        ctx.nom(),
        ctx.version_pilote(),
        o.casser,
        o.fils,
        o.fichier.display().to_string(),
        e.taille_fichier,
        e.version.0,
        e.version.1,
        dims.lignes,
        dims.colonnes,
        lignes.join(",\n"),
        total.json(),
        temoin_tient,
        t0.elapsed().as_secs_f64()
    );
    std::fs::write(&o.journal, j).expect("écriture du journal");
    eprintln!("total : {} ; témoin {}", total.json(), if temoin_tient { "tient" } else { "TOMBE" });
}
