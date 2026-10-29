//! Essai E0(c) : ce que coûtent 36 lectures du routeur par l'hôte, une par couche, par jeton.
//!
//! Chaque jeton enchaîne 36 couches simulées sur le flux de calcul (noyaux de `noyaux/essais.cu`) :
//! `routeur_factice` (occupe la carte `ns_routeur`, écrit 4 indices dans la boîte aux lettres
//! projetée), puis `expert_factice` (revérifie les 4 indices sur la carte, occupe `ns_expert`).
//! Variantes (comment l'hôte apprend les indices avant de lancer l'expert) :
//!
//! | variante | geste de l'hôte après le lancement du routeur |
//! |---|---|
//! | `asynchrone` | aucun : l'hôte calcule les indices lui-même (référence : la chaîne sans attente) |
//! | `evenement` | `cuEventRecord` puis `cuEventSynchronize` (mode d'attente du contexte) |
//! | `sondage` | `cuEventRecord` puis `cuEventQuery` en boucle |
//! | `bloquant` | événement `CU_EVENT_BLOCKING_SYNC` : le fil dort jusqu'à l'événement |
//! | `boite` | `cuStreamQuery` une fois (pousse le travail retenu par WDDM), puis sondage du numéro de séquence dans la boîte |
//! | `boite_sans_vidage` | sondage de la boîte sans rien pousser (délai borné ; dit si WDDM retient le lancement) |
//! | `sans_synchro` | cassure : lit la boîte sans attendre |
//!
//! Coût de la synchronisation = temps par jeton d'une variante − temps par jeton d'`asynchrone`,
//! mêmes noyaux, mêmes durées. Témoins : indices lus par l'hôte = attendu (et revérifiés par la
//! carte) ; numéro de séquence présent après l'attente ; temps de la carte ≤ temps du mur.

use std::ffi::c_void;
use std::time::{Duration, Instant};

use serde_json::{Value, json};
use trc_cuda::*;

use crate::machine;

static IMAGE: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/essais.cubin"));

pub const COUCHES: u32 = 36;

/// La même fonction que `indice_attendu` de `essais.cu`.
fn melange(mut x: u32) -> u32 {
    x ^= x >> 16;
    x = x.wrapping_mul(0x7feb_352d);
    x ^= x >> 15;
    x = x.wrapping_mul(0x846c_a68b);
    x ^= x >> 16;
    x
}

pub fn indice_attendu(jeton: u32, couche: u32, i: u32) -> u32 {
    melange(jeton.wrapping_mul(0x9E37_79B9) ^ couche.wrapping_mul(0x85EB_CA6B) ^ (i + 1).wrapping_mul(0xC2B2_AE35)) & 127
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Variante {
    Asynchrone,
    Evenement,
    Sondage,
    Bloquant,
    Boite,
    BoiteSansVidage,
    SansSynchro,
}

impl Variante {
    pub fn depuis(nom: &str) -> Option<Variante> {
        Some(match nom {
            "asynchrone" => Variante::Asynchrone,
            "evenement" => Variante::Evenement,
            "sondage" => Variante::Sondage,
            "bloquant" => Variante::Bloquant,
            "boite" => Variante::Boite,
            "boite_sans_vidage" => Variante::BoiteSansVidage,
            "sans_synchro" => Variante::SansSynchro,
            _ => return None,
        })
    }
    pub fn nom(self) -> &'static str {
        match self {
            Variante::Asynchrone => "asynchrone",
            Variante::Evenement => "evenement",
            Variante::Sondage => "sondage",
            Variante::Bloquant => "bloquant",
            Variante::Boite => "boite",
            Variante::BoiteSansVidage => "boite_sans_vidage",
            Variante::SansSynchro => "sans_synchro",
        }
    }
}

pub struct Options {
    pub variantes: Vec<Variante>,
    pub jetons: u32,
    pub chauffe: u32,
    pub ns_routeur: u64,
    pub ns_expert: u64,
    pub tours_abba: usize,
    pub attente: Attente,
    pub delai_boite_ms: u64,
}

struct Banc {
    c: Contexte,
    f: Flux,
    routeur: Fonction,
    expert: Fonction,
    boite: HoteEpingle,
    erreurs: MemoireCarte,
    retour: HoteEpingle,
    ev: Evenement,
    ev_bloquant: Evenement,
    ev_debut: Evenement,
    ev_fin: Evenement,
    /// Numéro de jeton global, jamais réutilisé : la boîte d'un jeton précédent est toujours fausse
    /// pour le jeton courant (c'est ce qui rend la cassure visible).
    jeton: u32,
}

struct Passe {
    mur_ms: Vec<f64>,
    carte_ms: Vec<f64>,
    faux_hote: u64,
    sequences_absentes: u64,
    boites_expirees: u64,
    erreurs_carte: u32,
}

impl Banc {
    fn lancer_routeur(&self, couche: u32, ns: u64) -> Result<()> {
        let mut boite = self.boite.adresse_carte().unwrap();
        let (mut j, mut c, mut n) = (self.jeton, couche, ns);
        let mut args = [
            &mut boite as *mut u64 as *mut c_void,
            &mut j as *mut u32 as *mut c_void,
            &mut c as *mut u32 as *mut c_void,
            &mut n as *mut u64 as *mut c_void,
        ];
        unsafe { self.routeur.lancer([1, 1, 1], [32, 1, 1], 0, &self.f, &mut args) }
    }

    fn lancer_expert(&self, couche: u32, idx: [u32; 4], ns: u64) -> Result<()> {
        let mut e = self.erreurs.tout().adresse;
        let (mut j, mut c, mut n) = (self.jeton, couche, ns);
        let [mut i0, mut i1, mut i2, mut i3] = idx;
        let mut args = [
            &mut e as *mut u64 as *mut c_void,
            &mut j as *mut u32 as *mut c_void,
            &mut c as *mut u32 as *mut c_void,
            &mut i0 as *mut u32 as *mut c_void,
            &mut i1 as *mut u32 as *mut c_void,
            &mut i2 as *mut u32 as *mut c_void,
            &mut i3 as *mut u32 as *mut c_void,
            &mut n as *mut u64 as *mut c_void,
        ];
        unsafe { self.expert.lancer([1, 1, 1], [32, 1, 1], 0, &self.f, &mut args) }
    }

    fn lire_boite(&self, couche: u32) -> (u32, [u32; 4]) {
        let base = 64 * couche as usize;
        let s = self.boite.lire_volatil_u32(base);
        let idx = [1, 2, 3, 4].map(|k| self.boite.lire_volatil_u32(base + 4 * k));
        (s, idx)
    }

    /// Un jeton : 36 couches. Rend (mur ms, carte ms, indices faux lus par l'hôte, séquences
    /// absentes après l'attente, boîtes expirées).
    fn jeton(&mut self, v: Variante, o: &Options) -> Result<(f64, f64, u64, u64, u64)> {
        self.jeton = self.jeton.wrapping_add(1);
        let (mut faux, mut absentes, mut expirees) = (0u64, 0u64, 0u64);
        let t0 = Instant::now();
        self.ev_debut.enregistrer(&self.f)?;
        for couche in 0..COUCHES {
            self.lancer_routeur(couche, o.ns_routeur)?;
            let attendu_seq = self.jeton.wrapping_mul(64).wrapping_add(couche + 1);
            let attendu = [0, 1, 2, 3].map(|i| indice_attendu(self.jeton, couche, i));
            let idx = match v {
                Variante::Asynchrone => attendu,
                Variante::Evenement | Variante::Sondage | Variante::Bloquant => {
                    let e = if v == Variante::Bloquant { &self.ev_bloquant } else { &self.ev };
                    e.enregistrer(&self.f)?;
                    if v == Variante::Sondage {
                        while !e.fini()? {
                            std::hint::spin_loop();
                        }
                    } else {
                        e.attendre()?;
                    }
                    let (s, idx) = self.lire_boite(couche);
                    if s != attendu_seq {
                        absentes += 1;
                    }
                    idx
                }
                Variante::Boite | Variante::BoiteSansVidage => {
                    if v == Variante::Boite {
                        self.f.fini()?; // pousse le lot retenu par le pilote vers la carte
                    }
                    let limite = Instant::now() + Duration::from_millis(o.delai_boite_ms);
                    loop {
                        let (s, idx) = self.lire_boite(couche);
                        if s == attendu_seq {
                            break idx;
                        }
                        if Instant::now() > limite {
                            // Le pilote n'a pas soumis le noyau : on le pousse pour continuer, et
                            // on compte l'expiration.
                            expirees += 1;
                            self.f.fini()?;
                            while self.lire_boite(couche).0 != attendu_seq {
                                std::hint::spin_loop();
                            }
                            break self.lire_boite(couche).1;
                        }
                        std::hint::spin_loop();
                    }
                }
                Variante::SansSynchro => {
                    let (s, idx) = self.lire_boite(couche);
                    if s != attendu_seq {
                        absentes += 1;
                    }
                    idx
                }
            };
            faux += idx.iter().zip(&attendu).filter(|(a, b)| a != b).count() as u64;
            self.lancer_expert(couche, idx, o.ns_expert)?;
        }
        self.ev_fin.enregistrer(&self.f)?;
        self.f.synchroniser()?;
        let mur = t0.elapsed().as_secs_f64() * 1e3;
        let carte = self.ev_fin.ms_depuis(&self.ev_debut)? as f64;
        Ok((mur, carte, faux, absentes, expirees))
    }

    fn passe(&mut self, v: Variante, o: &Options) -> Result<Passe> {
        // Compteur d'erreurs de la carte remis à zéro, et boîte vidée.
        self.erreurs.remplir(self.erreurs.tout(), 0, &self.f)?;
        self.f.synchroniser()?;
        let mut p = Passe { mur_ms: vec![], carte_ms: vec![], faux_hote: 0, sequences_absentes: 0, boites_expirees: 0, erreurs_carte: 0 };
        for k in 0..(o.chauffe + o.jetons) {
            let (mur, carte, faux, absentes, expirees) = self.jeton(v, o)?;
            if k >= o.chauffe {
                p.mur_ms.push(mur);
                p.carte_ms.push(carte);
            }
            p.faux_hote += faux;
            p.sequences_absentes += absentes;
            p.boites_expirees += expirees;
        }
        copier_vers_hote(&mut self.retour, 0, self.erreurs.tout(), &self.f)?;
        self.f.synchroniser()?;
        p.erreurs_carte = u32::from_le_bytes(self.retour.tranche()[..4].try_into().unwrap());
        Ok(p)
    }
}

fn moyenne(x: &[f64]) -> f64 {
    x.iter().sum::<f64>() / x.len() as f64
}

fn mediane(x: &[f64]) -> f64 {
    let mut y = x.to_vec();
    y.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = y.len();
    if n % 2 == 1 { y[n / 2] } else { (y[n / 2 - 1] + y[n / 2]) / 2.0 }
}

pub fn executer(o: &Options) -> Result<Value> {
    let c = Contexte::nouveau_avec(0, o.attente)?;
    let m = Module::charger(&c, IMAGE)?;
    let mut banc = Banc {
        f: Flux::nouveau(&c, true)?,
        routeur: m.fonction(c"routeur_factice")?,
        expert: m.fonction(c"expert_factice")?,
        boite: HoteEpingle::allouer(&c, 64 * COUCHES as usize, true)?,
        erreurs: MemoireCarte::allouer(&c, 4)?,
        retour: HoteEpingle::allouer(&c, 4096, false)?,
        ev: Evenement::nouveau(&c, false)?,
        ev_bloquant: Evenement::nouveau_bloquant(&c, false)?,
        ev_debut: Evenement::nouveau(&c, true)?,
        ev_fin: Evenement::nouveau(&c, true)?,
        jeton: 0,
        c,
    };
    // Ordre ABBA sur la liste des variantes : la liste, puis la liste à l'envers, `tours_abba` fois.
    let mut ordre = Vec::new();
    for _ in 0..o.tours_abba {
        ordre.extend(o.variantes.iter().copied());
        ordre.extend(o.variantes.iter().rev().copied());
    }
    let mut passes = Vec::new();
    for (rang, &v) in ordre.iter().enumerate() {
        let p = banc.passe(v, o)?;
        let carte_sur_mur = p.carte_ms.iter().zip(&p.mur_ms).filter(|(c, m)| **c > **m + 0.01).count();
        eprintln!(
            "{rang:>3} {:<18} mur {:>8.3} ms/jeton (méd. {:>8.3}), carte {:>8.3}, faux {} absentes {} expirées {} erreurs carte {} incohérences {}",
            v.nom(),
            moyenne(&p.mur_ms),
            mediane(&p.mur_ms),
            moyenne(&p.carte_ms),
            p.faux_hote,
            p.sequences_absentes,
            p.boites_expirees,
            p.erreurs_carte,
            carte_sur_mur
        );
        passes.push(json!({
            "rang": rang, "variante": v.nom(),
            "mur_ms_moyenne": moyenne(&p.mur_ms), "mur_ms_mediane": mediane(&p.mur_ms),
            "carte_ms_moyenne": moyenne(&p.carte_ms),
            "mur_ms": p.mur_ms, "carte_ms": p.carte_ms,
            "faux_hote": p.faux_hote, "sequences_absentes": p.sequences_absentes,
            "boites_expirees": p.boites_expirees, "erreurs_carte": p.erreurs_carte,
            "carte_au_dessus_du_mur": carte_sur_mur,
        }));
    }
    Ok(json!({
        "couches": COUCHES, "jetons": o.jetons, "chauffe": o.chauffe,
        "ns_routeur": o.ns_routeur, "ns_expert": o.ns_expert, "tours_abba": o.tours_abba,
        "attente_demandee": format!("{:?}", o.attente), "attente_effective": format!("{:?}", banc.c.attente_effective()),
        "delai_boite_ms": o.delai_boite_ms,
        "passes": passes,
        "machine_fin": machine::releve(Some(&banc.c)),
    }))
}
