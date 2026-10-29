//! Essai E0(b) : lecture sans tampon (`trc-es`) directement dans la mémoire épinglée, puis DMA vers
//! la VRAM ; et les deux débits dont le chemin dépend.
//!
//! 1. **Justesse** (témoin) : `morceaux` intervalles de `taille` octets, à des décalages alignés tirés
//!    d'une graine publiée dans le fichier source ; chaque intervalle va disque → épinglée → VRAM →
//!    épinglée de contrôle, et se compare à une lecture indépendante du même intervalle par
//!    `std::fs` (chemin ordinaire, cache de Windows compris). `--casser` fausse un octet de la
//!    mémoire épinglée du premier morceau entre la lecture et la DMA : exactement 1 écart attendu.
//! 2. **Débit du disque** (seuil E1) : `serie` lectures de `taille` octets, profondeur `profondeur`,
//!    chaque emplacement de la fenêtre réutilisé dès que sa lecture est récoltée.
//! 3. **Débit de la DMA** (seuil E0 b) : copies hôte → carte depuis la mémoire épinglée, deux
//!    tailles (la taille d'un tronçon, 64 Mio comme l'étude 01), série ABBA, chronométrées par les
//!    événements de la carte.

use std::io::{Read, Seek, SeekFrom};
use std::path::Path;
use std::time::Instant;

use serde_json::{Value, json};
use trc_cuda::*;
use trc_es::{Lecteur, Requete};

use crate::machine;

pub struct Options<'a> {
    pub fichier: &'a Path,
    pub taille: usize,
    pub morceaux: usize,
    pub serie: usize,
    pub profondeur: usize,
    pub graine: u64,
    pub casser: bool,
    pub repetitions_dma: usize,
    pub tours_abba: usize,
}

/// xorshift64* : les décalages tirés, reproductibles par la graine.
struct Tirage(u64);
impl Tirage {
    fn suivant(&mut self) -> u64 {
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        self.0.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }
    fn decalage(&mut self, taille_fichier: u64, longueur: u64) -> u64 {
        let pages = (taille_fichier - longueur) / 4096;
        (self.suivant() % pages) * 4096
    }
}

fn erreur_es(e: trc_es::Erreur) -> Erreur {
    Erreur::Usage(format!("trc-es : {e}"))
}

pub fn executer(o: &Options) -> Result<Value> {
    if o.taille % 4096 != 0 {
        return Err(Erreur::Usage("la taille doit être multiple de 4 096".into()));
    }
    let c = Contexte::nouveau(0)?;
    let f = Flux::nouveau(&c, false)?;
    let lecteur = Lecteur::ouvrir(o.fichier, o.profondeur).map_err(erreur_es)?;
    let taille_fichier = lecteur.taille();
    let mut tirage = Tirage(o.graine | 1);

    // ---- 1. Justesse ---------------------------------------------------------------------
    let mut fenetre = HoteEpingle::allouer(&c, o.taille, false)?;
    let mut controle = HoteEpingle::allouer(&c, o.taille, false)?;
    let carte = MemoireCarte::allouer(&c, o.taille.max(64 << 20))?;
    let mut source = std::fs::File::open(o.fichier).map_err(|e| Erreur::Usage(e.to_string()))?;
    let mut reference = vec![0u8; o.taille];
    let mut morceaux = Vec::new();
    let (mut ecarts_disque, mut ecarts_chemin) = (0usize, 0usize);
    for k in 0..o.morceaux {
        let decalage = tirage.decalage(taille_fichier, o.taille as u64);
        lecteur
            .soumettre(Requete { jeton: k as u64, decalage, longueur: o.taille as u32, destination: fenetre.pointeur() })
            .map_err(erreur_es)?;
        let mut a = Vec::new();
        while a.is_empty() {
            lecteur.recolter(10_000, &mut a).map_err(erreur_es)?;
        }
        if a[0].erreur.is_some() || a[0].octets as usize != o.taille {
            return Err(Erreur::Usage(format!("lecture {k} : {:?}", a[0])));
        }
        // La lecture indépendante, après celle du lecteur (elle remplit le cache de Windows, que le
        // lecteur sans tampon ne lit pas de toute façon).
        source.seek(SeekFrom::Start(decalage)).and_then(|_| source.read_exact(&mut reference)).map_err(|e| Erreur::Usage(e.to_string()))?;
        let d = fenetre.tranche()[..o.taille].iter().zip(&reference).filter(|(x, y)| x != y).count();
        if o.casser && k == 0 {
            fenetre.tranche_mut()[o.taille / 2] ^= 0xA5;
        }
        copier_vers_carte(carte.vue(0, o.taille), &fenetre, 0, o.taille, &f)?;
        copier_vers_hote(&mut controle, 0, carte.vue(0, o.taille), &f)?;
        f.synchroniser()?;
        let dc = controle.tranche()[..o.taille].iter().zip(&reference).filter(|(x, y)| x != y).count();
        ecarts_disque += d;
        ecarts_chemin += dc;
        morceaux.push(json!({ "k": k, "decalage": decalage, "ecarts_disque": d, "ecarts_chemin": dc, "duree_lecture_us": a[0].duree_us }));
    }
    eprintln!("justesse : {} morceaux, {ecarts_disque} écart(s) disque, {ecarts_chemin} écart(s) disque → VRAM → hôte", o.morceaux);

    // ---- 2. Débit du disque --------------------------------------------------------------
    let fen_debit = HoteEpingle::allouer(&c, o.taille * o.profondeur, false)?;
    let mut libres: Vec<usize> = (0..o.profondeur).collect();
    let mut emplacement_de = vec![0usize; o.serie];
    let mut durees = Vec::with_capacity(o.serie);
    let mut soumises = 0usize;
    let mut recues = 0usize;
    let mut octets = 0u64;
    let mut erreurs = 0usize;
    let mut sortie = Vec::new();
    let machine_debut_disque = machine::releve(None);
    // Octets lus par toute la machine pendant la série (compteur brut PDH) : la charge étrangère.
    let compteur = crate::disque::CompteurDisque::ouvrir().ok();
    let cpu = machine::TempsProcesseur::maintenant();
    let fenetre_disque = crate::disque::Fenetre::ouvrir(compteur.as_ref());
    let depart = Instant::now();
    while recues < o.serie {
        while soumises < o.serie {
            let Some(e) = libres.pop() else { break };
            emplacement_de[soumises] = e;
            let decalage = tirage.decalage(taille_fichier, o.taille as u64);
            let dest = unsafe { fen_debit.pointeur().add(e * o.taille) };
            lecteur
                .soumettre(Requete { jeton: soumises as u64, decalage, longueur: o.taille as u32, destination: dest })
                .map_err(erreur_es)?;
            soumises += 1;
        }
        sortie.clear();
        lecteur.recolter(10_000, &mut sortie).map_err(erreur_es)?;
        for a in &sortie {
            libres.push(emplacement_de[a.jeton as usize]);
            durees.push(a.duree_us);
            octets += a.octets as u64;
            if a.erreur.is_some() || a.octets as usize != o.taille {
                erreurs += 1;
            }
            recues += 1;
        }
    }
    let secondes = depart.elapsed().as_secs_f64();
    let octets_systeme = fenetre_disque.octets();
    let processeur = machine::TempsProcesseur::maintenant().depuis(&cpu);
    let octets_etrangers = octets_systeme.map(|s| s.saturating_sub(octets));
    let debit_disque = octets as f64 / secondes / 1e9;
    durees.sort_unstable();
    let quantile = |q: f64| durees[((durees.len() - 1) as f64 * q).round() as usize];
    eprintln!(
        "disque : {} lectures de {} o, profondeur {}, {debit_disque:.3} Go/s, médiane {} µs, p90 {} µs, {erreurs} erreur(s)",
        o.serie, o.taille, o.profondeur, quantile(0.5), quantile(0.9)
    );

    // ---- 3. Débit de la DMA, ABBA --------------------------------------------------------
    let grand = 64usize << 20;
    let source_dma = HoteEpingle::allouer(&c, grand, false)?;
    let tailles = [o.taille, grand];
    let e0 = Evenement::nouveau(&c, true)?;
    let e1 = Evenement::nouveau(&c, true)?;
    let mut passes = Vec::new();
    // Chauffe : sort la carte et le lien de leur état de repos (le lien change de génération,
    // étude 04 § pcie-1).
    for _ in 0..8 {
        copier_vers_carte(carte.vue(0, grand), &source_dma, 0, grand, &f)?;
    }
    f.synchroniser()?;
    for tour in 0..o.tours_abba {
        for (rang, &i) in [0usize, 1, 1, 0].iter().enumerate() {
            let t = tailles[i];
            // Second chemin : l'horloge de l'hôte autour des mêmes copies (soumission comprise,
            // donc un débit un peu plus bas que celui des événements de la carte, jamais plus haut).
            let mur = Instant::now();
            e0.enregistrer(&f)?;
            for _ in 0..o.repetitions_dma {
                copier_vers_carte(carte.vue(0, t), &source_dma, 0, t, &f)?;
            }
            e1.enregistrer(&f)?;
            f.synchroniser()?;
            let mur_ms = mur.elapsed().as_secs_f64() * 1e3;
            let ms = e1.ms_depuis(&e0)? as f64;
            let go_s = (t * o.repetitions_dma) as f64 / (ms * 1e-3) / 1e9;
            let go_s_mur = (t * o.repetitions_dma) as f64 / (mur_ms * 1e-3) / 1e9;
            passes.push(json!({ "tour": tour, "rang": rang, "lettre": if i == 0 { "A" } else { "B" }, "octets": t,
                                "copies": o.repetitions_dma, "ms": ms, "go_s": go_s, "mur_ms": mur_ms, "go_s_mur": go_s_mur }));
            eprintln!("DMA tour {tour} {} {t} o × {} : {go_s:.3} Go/s", if i == 0 { "A" } else { "B" }, o.repetitions_dma);
        }
    }

    Ok(json!({
        "fichier": o.fichier.display().to_string(),
        "taille_fichier_o": taille_fichier,
        "taille_morceau_o": o.taille,
        "graine": o.graine,
        "casser": o.casser,
        "justesse": { "morceaux": morceaux, "ecarts_disque": ecarts_disque, "ecarts_chemin": ecarts_chemin },
        "disque": { "lectures": o.serie, "profondeur": o.profondeur, "octets": octets, "secondes": secondes,
                    "go_s": debit_disque, "erreurs": erreurs, "duree_us_mediane": quantile(0.5),
                    "duree_us_p10": quantile(0.1), "duree_us_p90": quantile(0.9), "machine_debut": machine_debut_disque,
                    "octets_systeme": octets_systeme, "octets_etrangers": octets_etrangers,
                    "go_s_etrangers": octets_etrangers.map(|e| e as f64 / secondes / 1e9), "processeur": processeur },
        "dma": { "passes": passes },
        "machine_fin": machine::releve(Some(&c)),
    }))
}
