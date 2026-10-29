//! Essai E1 (débit du lecteur), **disque seul** : `trc-es` lit des morceaux de la taille d'un
//! tronçon, à des décalages tirés d'une graine publiée, dans une mémoire ordinaire alignée sur la
//! page (`VirtualAlloc`), sans contexte CUDA. Il se lance donc quand la carte est prise par un autre
//! lot ; il ne demande pas le verrou de la carte (consigne : « les essais courts n'en ont pas
//! besoin », et celui-ci ne touche pas la carte du tout).
//!
//! Pourquoi la mémoire n'est pas épinglée ici : une lecture sans tampon verrouille elle-même les
//! pages de sa destination le temps du transfert (le gestionnaire d'E/S construit une MDL) ; le
//! disque ne voit pas la différence. Ce qu'apporte l'épinglage (la DMA vers la carte depuis ces mêmes
//! pages) se mesure dans E0(b), pas ici.
//!
//! Séries ABBA sur la profondeur (A = `profondeurs[0]`, B = `profondeurs[1]`), `tours` fois ; chaque
//! passe relève les octets que **toute la machine** a lus pendant elle (compteur brut PDH,
//! [`crate::disque`]) : octets étrangers = octets du système − nos octets. Avant la série, `repos_s`
//! secondes de repos chiffrent la charge des autres programmes sans nous.
//!
//! Témoin de justesse (sur le vrai fichier), avant la série et hors chronomètre : `verifier`
//! lectures du lecteur comparées à une lecture indépendante par `std::fs` ; `--casser` fausse un
//! octet de la première : exactement 1 écart attendu.

use std::io::{Read, Seek, SeekFrom};
use std::path::Path;
use std::time::Instant;

use serde_json::{Value, json};
use trc_es::{Lecteur, Requete};
use windows_sys::Win32::System::Memory::{MEM_COMMIT, MEM_RELEASE, MEM_RESERVE, PAGE_READWRITE, VirtualAlloc, VirtualFree};

use crate::disque::{CompteurDisque, Fenetre};
use crate::machine;

pub struct Options<'a> {
    pub fichier: &'a Path,
    pub taille: usize,
    pub serie: usize,
    pub profondeurs: [usize; 2],
    pub tours: usize,
    pub graine: u64,
    pub repos_s: f64,
    pub verifier: usize,
    pub casser: bool,
}

/// Mémoire alignée sur la page, rendue au système à la fin.
struct Tampon {
    p: *mut u8,
    octets: usize,
}

impl Tampon {
    fn nouveau(octets: usize) -> Result<Tampon, String> {
        // SAFETY : réservation et engagement d'une plage neuve.
        let p = unsafe { VirtualAlloc(std::ptr::null(), octets, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE) } as *mut u8;
        if p.is_null() {
            return Err(format!("VirtualAlloc de {octets} o refusé"));
        }
        // Les pages sont touchées une fois : la première lecture ne paie pas leur mise à zéro.
        for k in (0..octets).step_by(4096) {
            unsafe { p.add(k).write_volatile(0) };
        }
        Ok(Tampon { p, octets })
    }
    fn tranche(&self, debut: usize, n: usize) -> &[u8] {
        assert!(debut + n <= self.octets);
        unsafe { std::slice::from_raw_parts(self.p.add(debut), n) }
    }
}

impl Drop for Tampon {
    fn drop(&mut self) {
        unsafe { VirtualFree(self.p as _, 0, MEM_RELEASE) };
    }
}

/// xorshift64* : les décalages tirés, reproductibles par la graine (même tirage que l'essai b).
struct Tirage(u64);
impl Tirage {
    fn decalage(&mut self, taille_fichier: u64, longueur: u64) -> u64 {
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        let x = self.0.wrapping_mul(0x2545_F491_4F6C_DD1D);
        (x % ((taille_fichier - longueur) / 4096)) * 4096
    }
}

fn quantile(trie: &[u32], q: f64) -> u32 {
    trie[((trie.len() - 1) as f64 * q).round() as usize]
}

pub fn executer(o: &Options) -> Result<Value, String> {
    if o.taille % 4096 != 0 || o.taille == 0 {
        return Err("la taille doit être un multiple non nul de 4 096".into());
    }
    let compteur = match CompteurDisque::ouvrir() {
        Ok(c) => Some(c),
        Err(e) => {
            eprintln!("compteur du disque indisponible ({e}) : octets étrangers non relevés");
            None
        }
    };
    let qd_max = o.profondeurs[0].max(o.profondeurs[1]);
    let tampon = Tampon::nouveau(o.taille * qd_max)?;
    let mut tirage = Tirage(o.graine | 1);
    let mut source = std::fs::File::open(o.fichier).map_err(|e| e.to_string())?;
    let taille_fichier = source.metadata().map_err(|e| e.to_string())?.len();

    // Repos : ce que lit la machine sans nous.
    let repos = {
        let cpu = machine::TempsProcesseur::maintenant();
        let f = Fenetre::ouvrir(compteur.as_ref());
        let t = Instant::now();
        std::thread::sleep(std::time::Duration::from_secs_f64(o.repos_s));
        let s = t.elapsed().as_secs_f64();
        let cpu = machine::TempsProcesseur::maintenant().depuis(&cpu);
        f.octets().map(|b| json!({ "secondes": s, "octets": b, "go_s": b as f64 / s / 1e9, "processeur": cpu }))
    };
    if let Some(r) = &repos {
        eprintln!("repos : la machine lit {:.3} Go/s sans nous", r["go_s"].as_f64().unwrap_or(0.0));
    }

    // Justesse, hors chronomètre.
    let justesse = {
        let lecteur = Lecteur::ouvrir(o.fichier, 1).map_err(|e| e.to_string())?;
        let mut reference = vec![0u8; o.taille];
        let mut verifs = Vec::new();
        let mut total = 0u64;
        for k in 0..o.verifier {
            let decalage = tirage.decalage(taille_fichier, o.taille as u64);
            lecteur
                .soumettre(Requete { jeton: k as u64, decalage, longueur: o.taille as u32, destination: tampon.p })
                .map_err(|e| e.to_string())?;
            let mut a = Vec::new();
            while a.is_empty() {
                lecteur.recolter(10_000, &mut a).map_err(|e| e.to_string())?;
            }
            if a[0].erreur.is_some() || a[0].octets as usize != o.taille {
                return Err(format!("lecture de justesse {k} : {:?}", a[0]));
            }
            if o.casser && k == 0 {
                unsafe { *tampon.p.add(o.taille / 2) ^= 0xA5 };
            }
            source.seek(SeekFrom::Start(decalage)).and_then(|_| source.read_exact(&mut reference)).map_err(|e| e.to_string())?;
            let d = tampon.tranche(0, o.taille).iter().zip(&reference).filter(|(x, y)| x != y).count() as u64;
            total += d;
            verifs.push(json!({ "k": k, "decalage": decalage, "ecarts": d }));
        }
        eprintln!("justesse : {} lectures comparées à std::fs, {total} écart(s)", o.verifier);
        json!({ "lectures": verifs, "ecarts": total, "casser": o.casser })
    };

    let mut passes = Vec::new();
    for tour in 0..o.tours {
        for (rang, &lettre) in [0usize, 1, 1, 0].iter().enumerate() {
            let qd = o.profondeurs[lettre];
            let lecteur = Lecteur::ouvrir(o.fichier, qd).map_err(|e| e.to_string())?;
            let mut libres: Vec<usize> = (0..qd).collect();
            let mut emplacement_de = vec![0usize; o.serie];
            let mut decalage_de = vec![0u64; o.serie];
            let mut durees = Vec::with_capacity(o.serie);
            let (mut soumises, mut recues, mut octets, mut erreurs) = (0usize, 0usize, 0u64, 0usize);
            let mut sortie = Vec::new();
            let cpu = machine::TempsProcesseur::maintenant();
            let fenetre = Fenetre::ouvrir(compteur.as_ref());
            let depart = Instant::now();
            while recues < o.serie {
                while soumises < o.serie {
                    let Some(e) = libres.pop() else { break };
                    emplacement_de[soumises] = e;
                    decalage_de[soumises] = tirage.decalage(taille_fichier, o.taille as u64);
                    let dest = unsafe { tampon.p.add(e * o.taille) };
                    lecteur
                        .soumettre(Requete { jeton: soumises as u64, decalage: decalage_de[soumises], longueur: o.taille as u32, destination: dest })
                        .map_err(|e| e.to_string())?;
                    soumises += 1;
                }
                sortie.clear();
                lecteur.recolter(10_000, &mut sortie).map_err(|e| e.to_string())?;
                for a in &sortie {
                    let k = a.jeton as usize;
                    durees.push(a.duree_us);
                    octets += a.octets as u64;
                    if a.erreur.is_some() || a.octets as usize != o.taille {
                        erreurs += 1;
                    }
                    libres.push(emplacement_de[k]);
                    recues += 1;
                }
            }
            let secondes = depart.elapsed().as_secs_f64();
            let systeme = fenetre.octets();
            let processeur = machine::TempsProcesseur::maintenant().depuis(&cpu);
            drop(lecteur);
            durees.sort_unstable();
            let go_s = octets as f64 / secondes / 1e9;
            let etrangers = systeme.map(|s| s.saturating_sub(octets));
            let duree_mur = secondes;
            eprintln!(
                "tour {tour} {} QD {qd} : {go_s:.3} Go/s, médiane {} µs, p90 {} µs, {erreurs} erreur(s), étrangers {}, processeur des autres {:.0} %",
                if lettre == 0 { "A" } else { "B" },
                quantile(&durees, 0.5),
                quantile(&durees, 0.9),
                etrangers.map_or("?".into(), |e| format!("{:.3} Go/s", e as f64 / duree_mur / 1e9)),
                processeur["autres"].as_f64().unwrap_or(0.0) * 100.0
            );
            passes.push(json!({
                "tour": tour, "rang": rang, "lettre": if lettre == 0 { "A" } else { "B" }, "profondeur": qd,
                "lectures": o.serie, "octets": octets, "secondes": secondes, "go_s": go_s, "erreurs": erreurs,
                "duree_us_p10": quantile(&durees, 0.1), "duree_us_mediane": quantile(&durees, 0.5),
                "duree_us_p90": quantile(&durees, 0.9), "duree_us_max": *durees.last().unwrap(),
                "octets_systeme": systeme, "octets_etrangers": etrangers, "secondes_mur": duree_mur,
                "go_s_etrangers": etrangers.map(|e| e as f64 / duree_mur / 1e9), "processeur": processeur,
            }));
        }
    }
    Ok(json!({
        "fichier": o.fichier.display().to_string(), "taille_fichier_o": taille_fichier, "taille_morceau_o": o.taille,
        "graine": o.graine, "profondeurs": o.profondeurs, "tours": o.tours, "repos": repos,
        "justesse": justesse, "passes": passes, "machine_fin": machine::releve(None),
    }))
}
