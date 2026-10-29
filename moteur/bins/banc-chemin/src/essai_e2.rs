//! Essai E2 : le chemin d'un tronçon de bout en bout, disque → VRAM décodé, sans modèle
//! (ARCHITECTURE.md § 5.1, § 6.5 E2, critère C2 du § 7.1). Témoins, cassure et seuils déclarés
//! avant la première ligne de ce fichier : `moteur/REPRISE-E.md`, « E2 ».
//!
//! Le chemin d'un expert, tel que le moteur le suivra :
//!
//! ```text
//!  fil de l'hôte : soumettre ──► (IOCP) achèvement ──► copie + décodage mis en file ──► « prêt » (événement)
//!  disque        : |== lecture sans tampon de longueur0 dans l'emplacement s de la fenêtre épinglée ==|
//!  flux de copie :                                     |== DMA vers le tampon d'arrivée s ==|
//!  flux de décodage :                                          (attend la copie) |decoder_echelles|decoder_codes|
//! ```
//!
//! Chaque emplacement s de la fenêtre porte, ensemble : une tranche épinglée de la taille du plus
//! grand tronçon (arrondie à 4 096), un tampon d'arrivée en VRAM de même taille, un emplacement
//! d'expert décodé (disposition SoA, § 5.6) et quatre événements horodatés (début et fin de la
//! copie, début et fin du décodage). Il redevient libre quand la carte a fini son décodage (et, en
//! passe témoin, son retour vers l'hôte) : une nouvelle lecture peut alors y entrer. Avec
//! `profondeur + 2` emplacements, `profondeur` lectures restent en vol pendant que deux
//! emplacements sont à la carte.
//!
//! Trois modes de passe :
//! - **témoin** (C2) : chaque emplacement décodé redescend vers l'hôte ; l'expert est remis dans
//!   la disposition d'origine (§ 4.11) et son empreinte64 comparée à `empreinte_origine` du
//!   répertoire ; les octets utiles arrivés dans la fenêtre épinglée sont comparés à
//!   `empreinte_niveau[0]` (le transport seul, avant la carte) ;
//! - **production** : rien ne redescend ; les compteurs de contrôle de la carte (un tampon de
//!   16 o par expert, indexé par sa place dans le répertoire) sont relus une fois, en fin de passe ;
//! - **disque** : la même suite de lectures dans la même fenêtre, sans la carte (l'étage disque
//!   seul, mesuré dans la même séance).
//!
//! Étages seuls, dans la même séance : la DMA (une copie par expert, aux longueurs réelles, depuis
//! la fenêtre épinglée) et le décodage (des parties gardées en VRAM, décodées l'une après l'autre
//! comme les défauts d'une couche en J1), chronométrés par les événements de la carte.

use std::io::Write as _;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use serde_json::{Value, json};
use trc_cuda::*;
use trc_es::{Lecteur, Requete};
use trc_format::{EntreeRepertoire, Fichier, Sorte, empreinte64, empreinte64_morceaux};
use trc_noyaux::Noyaux;
use trc_noyaux::abi::{self, DimsExpert};

use crate::disque::{CompteurDisque, Fenetre};
use crate::machine;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Mode {
    Temoin,
    Production,
    Disque,
}

impl Mode {
    fn nom(self) -> &'static str {
        match self {
            Mode::Temoin => "temoin",
            Mode::Production => "production",
            Mode::Disque => "disque",
        }
    }
}

pub struct Options<'a> {
    pub fichier: &'a Path,
    pub profondeur: usize,
    pub emplacements: usize,
    pub graine: u64,
    pub tours: usize,
    /// Passe témoin puis une passe de production seulement (la cassure, sur une copie corrompue).
    pub temoin_seul: bool,
    /// Parties gardées en VRAM pour l'étage « décodage seul ».
    pub residents: usize,
    /// Indices (place dans le répertoire) des experts corrompus à dessein, lus dans le journal de
    /// `casser-copie` : la passe témoin doit les détecter tous, et aucun autre.
    pub attendus: Option<Vec<usize>>,
    /// Dossier des chronogrammes (un CSV par passe à la carte) ; aucun si absent.
    pub chronogrammes: Option<PathBuf>,
    /// Essai court : chaque passe ne sert que les `limite` premiers experts de sa permutation
    /// (jamais pour un verdict : C2 et le seuil portent sur les 768).
    pub limite: Option<usize>,
    /// Variante E2-V : chaque tronçon est lu en une requête de cette longueur depuis son début
    /// (au moins `longueur0` ; les octets en plus appartiennent au tronçon suivant, ni copiés ni
    /// décodés ; la dernière lecture s'arrête à la fin du fichier). Raison : le débit du disque
    /// sans tampon dépend de la seule longueur de la lecture (REPRISE-E, balayage du 2026-10-15).
    pub longueur_lecture: Option<u32>,
}

fn usage_e(m: impl Into<String>) -> Erreur {
    Erreur::Usage(m.into())
}

fn erreur_es(e: trc_es::Erreur) -> Erreur {
    usage_e(format!("trc-es : {e}"))
}

/// xorshift64* : les ordres de passe, reproductibles par la graine (même générateur que les
/// essais b et lecteur).
struct Tirage(u64);
impl Tirage {
    fn nouveau(graine: u64) -> Tirage {
        Tirage(graine | 1)
    }
    fn suivant(&mut self) -> u64 {
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        self.0.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }
}

/// Une permutation de 0..n (Fisher-Yates) tirée de `graine`.
pub fn permutation(n: usize, graine: u64) -> Vec<usize> {
    let mut t = Tirage::nouveau(graine);
    let mut v: Vec<usize> = (0..n).collect();
    for i in (1..n).rev() {
        let j = (t.suivant() % (i as u64 + 1)) as usize;
        v.swap(i, j);
    }
    v
}

/// Octets d'un expert dans la disposition d'origine (§ 4.11) : blocs de 17 o et biais f32.
pub fn octets_origine(d: &DimsExpert) -> u64 {
    (0..3).map(|j| d.blocs(j) * 17 + 4 * d.lignes[j] as u64).sum()
}

/// L'empreinte64 de l'expert d'origine (§ 4.11, § 4.12), recalculée depuis un emplacement SoA
/// (§ 5.6) : pour j = 0, 1, 2 les blocs `[e, qs × 16]` dans l'ordre β, puis pour j = 0, 1, 2 les
/// biais. Écrite ici depuis le seul texte de la spécification (le lot K a la sienne dans son
/// témoin ; les deux ne partagent rien).
pub fn empreinte_emplacement(empl: &[u8], d: &DimsExpert) -> u64 {
    let mut matrices: Vec<Vec<u8>> = Vec::with_capacity(3);
    for j in 0..3 {
        let disp = d.disposition(j);
        let (b, e) = (disp.base as usize, (disp.base + disp.echelles) as usize);
        let n = d.blocs(j) as usize;
        let mut v = vec![0u8; 17 * n];
        for beta in 0..n {
            v[17 * beta] = empl[e + beta];
            v[17 * beta + 1..17 * beta + 17].copy_from_slice(&empl[b + 16 * beta..b + 16 * beta + 16]);
        }
        matrices.push(v);
    }
    let biais: Vec<&[u8]> = (0..3)
        .map(|j| {
            let disp = d.disposition(j);
            let p = (disp.base + disp.biais) as usize;
            &empl[p..p + 4 * d.lignes[j] as usize]
        })
        .collect();
    empreinte64_morceaux(matrices.iter().map(|v| &v[..]).chain(biais))
}

/// Les LUT d'une couche (`u32[3][4][4096]`, disposition des noyaux) depuis les tables du fichier.
fn luts_couche(f: &Fichier, c: u16) -> Result<Vec<u32>> {
    let freq = |j: u8, s: Sorte, ctx: u8| f.table(c, j, s, ctx).and_then(|t| t.charge.frequences());
    let t: [[Option<&[u16]>; 4]; 3] = std::array::from_fn(|j| {
        let j = j as u8;
        [freq(j, Sorte::Delta, 0), freq(j, Sorte::CodesCtx, 0), freq(j, Sorte::CodesCtx, 1), freq(j, Sorte::CodesCtx, 2)]
    });
    abi::luts_couche(&t).map_err(|e| usage_e(format!("tables de la couche {c} : {e}")))
}

fn vers_octets(v: &[u32]) -> Vec<u8> {
    v.iter().flat_map(|x| x.to_le_bytes()).collect()
}

/// Ce que l'on relève sur un expert pendant une passe.
#[derive(Clone, Default)]
struct Ligne {
    indice: usize,
    longueur: u32,
    t_soumis_ms: f64,
    t_lu_ms: f64,
    lecture_us: u32,
    erreur_lecture: bool,
    /// Événements de la carte, en ms depuis l'événement de base de la passe.
    copie_debut_ms: f32,
    copie_fin_ms: f32,
    dec_debut_ms: f32,
    dec_fin_ms: f32,
    t_libere_ms: f64,
    grilles_refusees: bool,
    partie_juste: Option<bool>,
    origine_juste: Option<bool>,
    controle: [u32; 4],
}

#[derive(Clone, Copy)]
enum Etat {
    Libre,
    Lecture,
    Carte(usize),
}

struct Banc {
    entrees: Vec<EntreeRepertoire>,
    /// v1.2 : l'expert décodé se compare à `empreinte_canonique`.
    canonique: bool,
    dims: DimsExpert,
    lal: usize,
    te: usize,
    s: usize,
    c: Contexte,
    copie: Flux,
    dec: Flux,
    noyaux: Noyaux,
    lecteur: Lecteur,
    fen: HoteEpingle,
    retour: HoteEpingle,
    h_ctl: HoteEpingle,
    d_arr: MemoireCarte,
    d_empl: MemoireCarte,
    d_ctl: MemoireCarte,
    d_luts: MemoireCarte,
    ev: Vec<[Evenement; 4]>,
    base: Evenement,
    compteur: Option<CompteurDisque>,
    /// Longueur de chaque requête de lecture (None : `longueur0`, le cas de la spécification).
    lecture: Option<u32>,
}

const LUT_OCTETS: usize = abi::LUTS_PAR_COUCHE * 4;

impl Banc {
    fn nouveau(fichier: &Fichier, chemin: &Path, profondeur: usize, s: usize, lecture: Option<u32>) -> Result<Banc> {
        let e = fichier.entete();
        if e.est_brut() {
            return Err(usage_e("fichier brut : E2 vise le chemin codé"));
        }
        if e.niveaux != 1 {
            return Err(usage_e(format!("{} niveaux : E2 (J1) lit la v1.0 à un niveau", e.niveaux)));
        }
        let dims = DimsExpert { lignes: [e.lignes[0], e.lignes[1], e.lignes[2]], colonnes: [e.colonnes[0], e.colonnes[1], e.colonnes[2]] };
        dims.verifier().map_err(Erreur::Usage)?;
        let entrees: Vec<EntreeRepertoire> = fichier.repertoire().to_vec();
        for (g, r) in entrees.iter().enumerate() {
            let attendu = ((g / e.experts as usize) as u16, (g % e.experts as usize) as u16);
            if (r.couche, r.expert) != attendu || r.longueur[0] as u64 % 4096 != 0 || r.decalage % 4096 != 0 {
                return Err(usage_e(format!("entrée {g} du répertoire : {:?}", r)));
            }
        }
        let lmax = entrees.iter().map(|r| r.longueur[0]).max().unwrap_or(4096);
        if let Some(l) = lecture {
            if l % 4096 != 0 || l < lmax {
                return Err(usage_e(format!("longueur de lecture {l} : multiple de 4 096 et ≥ {lmax} (plus grand tronçon) exigés")));
            }
        }
        let lal = lecture.unwrap_or(lmax).max(lmax) as usize;
        let te = dims.taille_emplacement() as usize;
        let n = entrees.len();
        let c = Contexte::nouveau(0)?;
        let copie = Flux::nouveau(&c, false)?;
        let dec = Flux::nouveau(&c, false)?;
        let noyaux = Noyaux::charger(&c)?;
        let lecteur = Lecteur::ouvrir(chemin, profondeur).map_err(erreur_es)?;
        let fen = HoteEpingle::allouer(&c, s * lal, false)?;
        let retour = HoteEpingle::allouer(&c, s * te, false)?;
        let h_ctl = HoteEpingle::allouer(&c, 16 * n, false)?;
        let d_arr = MemoireCarte::allouer(&c, s * lal)?;
        let d_empl = MemoireCarte::allouer(&c, s * te)?;
        let d_ctl = MemoireCarte::allouer(&c, 16 * n)?;
        let couches = e.couches as usize;
        let d_luts = MemoireCarte::allouer(&c, couches * LUT_OCTETS)?;
        {
            let mut h = HoteEpingle::allouer(&c, couches * LUT_OCTETS, false)?;
            for k in 0..couches {
                let l = vers_octets(&luts_couche(fichier, k as u16)?);
                h.tranche_mut()[k * LUT_OCTETS..(k + 1) * LUT_OCTETS].copy_from_slice(&l);
            }
            copier_vers_carte(d_luts.tout(), &h, 0, couches * LUT_OCTETS, &copie)?;
            copie.synchroniser()?;
        }
        let mut ev = Vec::with_capacity(s);
        for _ in 0..s {
            ev.push([Evenement::nouveau(&c, true)?, Evenement::nouveau(&c, true)?, Evenement::nouveau(&c, true)?, Evenement::nouveau(&c, true)?]);
        }
        let base = Evenement::nouveau(&c, true)?;
        let compteur = CompteurDisque::ouvrir().map_err(|e| eprintln!("compteur du disque indisponible : {e}")).ok();
        Ok(Banc { lecture, entrees, canonique: e.est_canonique(), dims, lal, te, s, c, copie, dec, noyaux, lecteur, fen, retour, h_ctl, d_arr, d_empl, d_ctl, d_luts, ev, base, compteur })
    }

    fn vue_luts(&self, couche: u16) -> VueCarte {
        self.d_luts.vue(couche as usize * LUT_OCTETS, LUT_OCTETS)
    }

    /// Une passe : chaque expert de `ordre` (places dans le répertoire) suit le chemin du mode.
    fn passe(&mut self, ordre: &[usize], mode: Mode) -> Result<(Value, Vec<Ligne>)> {
        let n = ordre.len();
        let s_tot = self.s;
        let mut lignes = vec![Ligne::default(); n];
        let mut emplacement_de = vec![0usize; n];
        let mut etats = vec![Etat::Libre; s_tot];
        let mut libres: Vec<usize> = (0..s_tot).rev().collect();
        if mode != Mode::Disque {
            self.d_ctl.remplir(self.d_ctl.tout(), 0, &self.dec)?;
        }
        self.base.enregistrer(&self.dec)?;
        self.dec.synchroniser()?;
        let machine_debut = machine::releve(None);
        let cpu = machine::TempsProcesseur::maintenant();
        let fenetre_disque = Fenetre::ouvrir(self.compteur.as_ref());
        let t0 = Instant::now();
        let ms = |t: Instant| t.duration_since(t0).as_secs_f64() * 1e3;
        let (mut prochain, mut finis, mut a_la_carte) = (0usize, 0usize, 0usize);
        let (mut octets_lus, mut sommeils) = (0u64, 0u64);
        let mut sortie = Vec::new();
        while finis < n {
            while prochain < n {
                let Some(s) = libres.pop() else { break };
                let g = ordre[prochain];
                let r = self.entrees[g];
                // SAFETY : l'emplacement s de la fenêtre est libre (aucune lecture ni copie ne le
                // touche) jusqu'à l'achèvement de cette requête.
                let dest = unsafe { self.fen.pointeur().add(s * self.lal) };
                let longueur = self.lecture.unwrap_or(r.longueur[0]);
                self.lecteur
                    .soumettre(Requete { jeton: prochain as u64, decalage: r.decalage, longueur, destination: dest })
                    .map_err(erreur_es)?;
                emplacement_de[prochain] = s;
                etats[s] = Etat::Lecture;
                lignes[prochain].indice = g;
                lignes[prochain].longueur = r.longueur[0];
                lignes[prochain].t_soumis_ms = ms(Instant::now());
                prochain += 1;
            }
            let mut progres = false;
            sortie.clear();
            self.lecteur.recolter(if a_la_carte > 0 { 0 } else { 10_000 }, &mut sortie).map_err(erreur_es)?;
            for a in &sortie {
                progres = true;
                let pos = a.jeton as usize;
                let s = emplacement_de[pos];
                let g = ordre[pos];
                let r = self.entrees[g];
                let len = r.longueur[0] as usize;
                let l = &mut lignes[pos];
                l.t_lu_ms = ms(Instant::now());
                l.lecture_us = a.duree_us;
                // Avec une longueur de lecture fixe, la dernière lecture du fichier rend moins que
                // demandé ; seul compte qu'elle couvre le tronçon.
                l.erreur_lecture = a.erreur.is_some() || a.octets < r.longueur[0] || (self.lecture.is_none() && a.octets != r.longueur[0]);
                octets_lus += a.octets as u64;
                if mode == Mode::Disque {
                    etats[s] = Etat::Libre;
                    libres.push(s);
                    l.t_libere_ms = l.t_lu_ms;
                    finis += 1;
                    continue;
                }
                let partie = &self.fen.tranche()[s * self.lal..s * self.lal + len];
                if mode == Mode::Temoin {
                    let u = (r.utiles[0] as usize).min(len);
                    l.partie_juste = Some(empreinte64(&partie[..u]) == r.empreinte_niveau[0]);
                }
                let grilles = match abi::grilles_depuis_partie(partie) {
                    Ok(gr) => gr,
                    Err(_) => {
                        l.grilles_refusees = true;
                        abi::grilles_decodeur(&self.dims)
                    }
                };
                let ev = &self.ev[s];
                ev[0].enregistrer(&self.copie)?;
                copier_vers_carte(self.d_arr.vue(s * self.lal, len), &self.fen, s * self.lal, len, &self.copie)?;
                ev[1].enregistrer(&self.copie)?;
                self.dec.attendre(&ev[1])?;
                ev[2].enregistrer(&self.dec)?;
                self.noyaux.decoder_expert_grilles(
                    self.d_arr.vue(s * self.lal, len),
                    self.d_empl.vue(s * self.te, self.te),
                    self.vue_luts(r.couche),
                    &self.dims,
                    self.d_ctl.vue(16 * g, 16),
                    grilles,
                    &self.dec,
                )?;
                if mode == Mode::Temoin {
                    copier_vers_hote(&mut self.retour, s * self.te, self.d_empl.vue(s * self.te, self.te), &self.dec)?;
                }
                ev[3].enregistrer(&self.dec)?;
                etats[s] = Etat::Carte(pos);
                a_la_carte += 1;
            }
            for s in 0..s_tot {
                let Etat::Carte(pos) = etats[s] else { continue };
                if !self.ev[s][3].fini()? {
                    continue;
                }
                progres = true;
                let ev = &self.ev[s];
                let l = &mut lignes[pos];
                l.copie_debut_ms = ev[0].ms_depuis(&self.base)?;
                l.copie_fin_ms = ev[1].ms_depuis(&self.base)?;
                l.dec_debut_ms = ev[2].ms_depuis(&self.base)?;
                l.dec_fin_ms = ev[3].ms_depuis(&self.base)?;
                if mode == Mode::Temoin {
                    let empl = &self.retour.tranche()[s * self.te..(s + 1) * self.te];
                    l.origine_juste = Some(empreinte_emplacement(empl, &self.dims) == self.entrees[l.indice].empreinte_du_decode(self.canonique));
                }
                l.t_libere_ms = ms(Instant::now());
                etats[s] = Etat::Libre;
                libres.push(s);
                a_la_carte -= 1;
                finis += 1;
            }
            if !progres && a_la_carte > 0 {
                // Rien d'achevé, la carte travaille : un sommeil court (minuterie haute résolution
                // de Windows) plutôt qu'une boucle qui prendrait un cœur au déchiffrement.
                sommeils += 1;
                std::thread::sleep(Duration::from_micros(100));
            }
        }
        self.dec.synchroniser()?;
        self.copie.synchroniser()?;
        let secondes = t0.elapsed().as_secs_f64();
        let octets_systeme = fenetre_disque.octets();
        let processeur = machine::TempsProcesseur::maintenant().depuis(&cpu);
        // Compteurs de la carte, relus une fois (production et témoin).
        if mode != Mode::Disque {
            copier_vers_hote(&mut self.h_ctl, 0, self.d_ctl.vue(0, 16 * self.entrees.len()), &self.dec)?;
            self.dec.synchroniser()?;
            let h = self.h_ctl.tranche();
            for l in lignes.iter_mut() {
                let p = 16 * l.indice;
                l.controle = std::array::from_fn(|k| u32::from_le_bytes(h[p + 4 * k..p + 4 * k + 4].try_into().unwrap()));
            }
        }
        Ok((self.bilan(mode, &lignes, secondes, octets_lus, octets_systeme, processeur, machine_debut, sommeils), lignes))
    }

    #[allow(clippy::too_many_arguments)]
    fn bilan(
        &self,
        mode: Mode,
        lignes: &[Ligne],
        secondes: f64,
        octets_lus: u64,
        octets_systeme: Option<u64>,
        processeur: Value,
        machine_debut: Value,
        sommeils: u64,
    ) -> Value {
        let n = lignes.len() as u64;
        let servis = n * octets_origine(&self.dims);
        let etrangers = octets_systeme.map(|s| s.saturating_sub(octets_lus));
        let mediane_f = |mut v: Vec<f64>| -> f64 {
            if v.is_empty() {
                return f64::NAN;
            }
            v.sort_by(|a, b| a.partial_cmp(b).unwrap());
            v[v.len() / 2]
        };
        let lecture_us = mediane_f(lignes.iter().map(|l| l.lecture_us as f64).collect());
        let lecture_p90 = {
            let mut v: Vec<u32> = lignes.iter().map(|l| l.lecture_us).collect();
            v.sort_unstable();
            v.get(((v.len().max(1) - 1) as f64 * 0.9).round() as usize).copied().unwrap_or(0)
        };
        let a_la_carte = mode != Mode::Disque;
        let copie_ms = mediane_f(lignes.iter().filter(|_| a_la_carte).map(|l| (l.copie_fin_ms - l.copie_debut_ms) as f64).collect());
        let dec_ms = mediane_f(lignes.iter().filter(|_| a_la_carte).map(|l| (l.dec_fin_ms - l.dec_debut_ms) as f64).collect());
        // Temps où la carte décode (union des intervalles de décodage, un seul flux : pas de
        // recouvrement entre eux) et où le moteur de copie copie.
        let occupe_dec: f64 = lignes.iter().filter(|_| a_la_carte).map(|l| (l.dec_fin_ms - l.dec_debut_ms) as f64).sum();
        let occupe_copie: f64 = lignes.iter().filter(|_| a_la_carte).map(|l| (l.copie_fin_ms - l.copie_debut_ms) as f64).sum();
        let ctl_somme: [u64; 4] = std::array::from_fn(|k| lignes.iter().map(|l| l.controle[k] as u64).sum());
        let ctl_experts: Vec<usize> = lignes.iter().filter(|l| l.controle[..3].iter().any(|&x| x != 0)).map(|l| l.indice).collect();
        let erreurs_lecture: Vec<usize> = lignes.iter().filter(|l| l.erreur_lecture).map(|l| l.indice).collect();
        let grilles_refusees: Vec<usize> = lignes.iter().filter(|l| l.grilles_refusees).map(|l| l.indice).collect();
        let parties_fausses: Vec<usize> = lignes.iter().filter(|l| l.partie_juste == Some(false)).map(|l| l.indice).collect();
        let origines_fausses: Vec<usize> = lignes.iter().filter(|l| l.origine_juste == Some(false)).map(|l| l.indice).collect();
        let mut detectes: Vec<usize> = lignes
            .iter()
            .filter(|l| {
                l.erreur_lecture
                    || l.partie_juste == Some(false)
                    || l.origine_juste == Some(false)
                    || l.controle[..3].iter().any(|&x| x != 0)
            })
            .map(|l| l.indice)
            .collect();
        detectes.sort_unstable();
        json!({
            "mode": mode.nom(),
            "experts": n,
            "secondes": secondes,
            "octets_lus": octets_lus,
            "octets_troncons": lignes.iter().map(|l| l.longueur as u64).sum::<u64>(),
            "go_s_utiles": lignes.iter().map(|l| l.longueur as u64).sum::<u64>() as f64 / secondes / 1e9,
            "longueur_lecture": self.lecture,
            "octets_servis_origine": servis,
            "go_s_troncons": octets_lus as f64 / secondes / 1e9,
            "go_s_servis": servis as f64 / secondes / 1e9,
            "experts_par_s": n as f64 / secondes,
            "lecture_us_mediane": lecture_us,
            "lecture_us_p90": lecture_p90,
            "copie_ms_mediane": copie_ms,
            "decodage_ms_mediane": dec_ms,
            "carte_occupee_decodage_s": occupe_dec / 1e3,
            "carte_occupee_copie_s": occupe_copie / 1e3,
            "sommeils_100us": sommeils,
            "erreurs_lecture": erreurs_lecture,
            "grilles_refusees": grilles_refusees,
            "controle": { "voies_hors_L": ctl_somme[0], "format": ctl_somme[1], "pointeurs": ctl_somme[2], "experts_non_nuls": ctl_experts },
            "temoin": if mode == Mode::Temoin {
                json!({ "parties_fausses": parties_fausses, "origines_fausses": origines_fausses,
                        "verifies": lignes.iter().filter(|l| l.origine_juste.is_some()).count() })
            } else { Value::Null },
            "detectes": detectes,
            "octets_systeme": octets_systeme,
            "octets_etrangers": etrangers,
            "go_s_etrangers": etrangers.map(|e| e as f64 / secondes / 1e9),
            "processeur": processeur,
            "machine_debut": machine_debut,
            "machine_fin": machine::releve(None),
        })
    }

    /// Étage DMA seul : une copie par expert de `ordre`, à sa longueur réelle, depuis la fenêtre
    /// épinglée vers les tampons d'arrivée tour à tour ; événements de la carte.
    fn etage_dma(&self, ordre: &[usize]) -> Result<Value> {
        let a = Evenement::nouveau(&self.c, true)?;
        let b = Evenement::nouveau(&self.c, true)?;
        // Chauffe : le lien quitte son état de repos (04 § pcie-1).
        for k in 0..8 {
            let s = k % self.s;
            copier_vers_carte(self.d_arr.vue(s * self.lal, self.lal), &self.fen, s * self.lal, self.lal, &self.copie)?;
        }
        let mut octets = 0u64;
        let mur = Instant::now();
        a.enregistrer(&self.copie)?;
        for (k, &g) in ordre.iter().enumerate() {
            let s = k % self.s;
            let len = self.entrees[g].longueur[0] as usize;
            copier_vers_carte(self.d_arr.vue(s * self.lal, len), &self.fen, s * self.lal, len, &self.copie)?;
            octets += len as u64;
        }
        b.enregistrer(&self.copie)?;
        self.copie.synchroniser()?;
        let mur_s = mur.elapsed().as_secs_f64();
        let s = b.ms_depuis(&a)? as f64 * 1e-3;
        Ok(json!({ "copies": ordre.len(), "octets": octets, "secondes": s, "go_s_troncons": octets as f64 / s / 1e9,
                   "secondes_mur": mur_s, "go_s_troncons_mur": octets as f64 / mur_s / 1e9 }))
    }

    /// Étage décodage seul : `residents` parties lues une fois et gardées en VRAM, puis
    /// `ordre.len()` décodages l'un après l'autre sur le flux de décodage (comme les défauts d'une
    /// couche en J1), en tournant sur les résidents ; compteurs de contrôle relus à la fin.
    fn etage_decodage(&mut self, ordre: &[usize], residents: usize) -> Result<Value> {
        let r_n = residents.min(ordre.len()).max(1);
        let res: Vec<usize> = ordre[..r_n].to_vec();
        let d_res = MemoireCarte::allouer(&self.c, r_n * self.lal)?;
        let d_ctl = MemoireCarte::allouer(&self.c, 16 * r_n)?;
        let mut h_ctl = HoteEpingle::allouer(&self.c, 16 * r_n, false)?;
        let mut grilles = Vec::with_capacity(r_n);
        for (k, &g) in res.iter().enumerate() {
            let r = self.entrees[g];
            let len = r.longueur[0] as usize;
            let dest = self.fen.pointeur();
            self.lecteur.soumettre(Requete { jeton: k as u64, decalage: r.decalage, longueur: r.longueur[0], destination: dest }).map_err(erreur_es)?;
            let mut a = Vec::new();
            while a.is_empty() {
                self.lecteur.recolter(10_000, &mut a).map_err(erreur_es)?;
            }
            if a[0].erreur.is_some() || a[0].octets != r.longueur[0] {
                return Err(usage_e(format!("lecture du résident {k} : {:?}", a[0])));
            }
            grilles.push(abi::grilles_depuis_partie(&self.fen.tranche()[..len]).unwrap_or_else(|_| abi::grilles_decodeur(&self.dims)));
            copier_vers_carte(d_res.vue(k * self.lal, len), &self.fen, 0, len, &self.copie)?;
            self.copie.synchroniser()?;
        }
        d_ctl.remplir(d_ctl.tout(), 0, &self.dec)?;
        let a = Evenement::nouveau(&self.c, true)?;
        let b = Evenement::nouveau(&self.c, true)?;
        // Chauffe : un décodage de chaque résident (horloge de la carte sortie du repos).
        for (k, &g) in res.iter().enumerate() {
            let r = self.entrees[g];
            let s = k % self.s;
            self.noyaux.decoder_expert_grilles(
                d_res.vue(k * self.lal, r.longueur[0] as usize),
                self.d_empl.vue(s * self.te, self.te),
                self.vue_luts(r.couche),
                &self.dims,
                d_ctl.vue(16 * k, 16),
                grilles[k],
                &self.dec,
            )?;
        }
        let mut octets = 0u64;
        a.enregistrer(&self.dec)?;
        for k in 0..ordre.len() {
            let i = k % r_n;
            let r = self.entrees[res[i]];
            let s = k % self.s;
            self.noyaux.decoder_expert_grilles(
                d_res.vue(i * self.lal, r.longueur[0] as usize),
                self.d_empl.vue(s * self.te, self.te),
                self.vue_luts(r.couche),
                &self.dims,
                d_ctl.vue(16 * i, 16),
                grilles[i],
                &self.dec,
            )?;
            octets += r.longueur[0] as u64;
        }
        b.enregistrer(&self.dec)?;
        self.dec.synchroniser()?;
        let s = b.ms_depuis(&a)? as f64 * 1e-3;
        copier_vers_hote(&mut h_ctl, 0, d_ctl.tout(), &self.dec)?;
        self.dec.synchroniser()?;
        let ctl: u64 = h_ctl.tranche()[..16 * r_n].chunks(4).map(|c| u32::from_le_bytes(c.try_into().unwrap()) as u64).sum();
        let n = ordre.len() as u64;
        Ok(json!({ "residents": r_n, "decodages": n, "octets": octets, "secondes": s,
                   "go_s_troncons": octets as f64 / s / 1e9, "go_s_servis": (n * octets_origine(&self.dims)) as f64 / s / 1e9,
                   "ms_par_expert": s * 1e3 / n as f64, "controle_non_nul": ctl }))
    }
}

/// Le chronogramme d'une passe, en CSV (une ligne par expert, dans l'ordre de soumission). Les
/// temps de l'hôte et ceux de la carte partagent leur origine à la latence d'une synchronisation
/// près (l'événement de base est atteint, puis l'horloge de l'hôte part).
fn ecrire_chronogramme(chemin: &Path, lignes: &[Ligne], experts: u16) -> std::io::Result<()> {
    if let Some(d) = chemin.parent() {
        std::fs::create_dir_all(d)?;
    }
    let mut f = std::io::BufWriter::new(std::fs::File::create(chemin)?);
    writeln!(f, "rang,indice,couche,expert,longueur_o,soumis_ms,lu_ms,lecture_us,copie_debut_ms,copie_fin_ms,decodage_debut_ms,decodage_fin_ms,libere_ms")?;
    for (k, l) in lignes.iter().enumerate() {
        writeln!(
            f,
            "{k},{},{},{},{},{:.4},{:.4},{},{:.4},{:.4},{:.4},{:.4},{:.4}",
            l.indice,
            l.indice / experts as usize,
            l.indice % experts as usize,
            l.longueur,
            l.t_soumis_ms,
            l.t_lu_ms,
            l.lecture_us,
            l.copie_debut_ms,
            l.copie_fin_ms,
            l.dec_debut_ms,
            l.dec_fin_ms,
            l.t_libere_ms
        )?;
    }
    f.flush()
}

pub fn executer(o: &Options) -> Result<Value> {
    if o.profondeur == 0 || o.emplacements < o.profondeur {
        return Err(usage_e("il faut une profondeur non nulle et au moins autant d'emplacements"));
    }
    let t_ouvrir = Instant::now();
    let fichier = Fichier::ouvrir(o.fichier).map_err(|e| usage_e(format!("ouverture vérifiée du .trc : {e}")))?;
    let ouvrir_s = t_ouvrir.elapsed().as_secs_f64();
    let mut banc = Banc::nouveau(&fichier, o.fichier, o.profondeur, o.emplacements, o.longueur_lecture)?;
    let n = banc.entrees.len();
    let e = fichier.entete();
    let r_reel = (n as u64 * octets_origine(&banc.dims)) as f64 / banc.entrees.iter().map(|r| r.longueur[0] as u64).sum::<u64>() as f64;
    eprintln!(
        "{} : {n} experts, tronçon le plus long {} o, emplacement {} o, {} emplacements, profondeur {}, r = {r_reel:.5}",
        o.fichier.display(),
        banc.lal,
        banc.te,
        banc.s,
        o.profondeur
    );
    let m = o.limite.unwrap_or(n).min(n);
    let perm = |graine: u64| -> Vec<usize> { permutation(n, graine).into_iter().take(m).collect() };
    let chrono = |nom: &str, lignes: &[Ligne]| {
        if let Some(d) = &o.chronogrammes {
            let p = d.join(format!("chrono-{nom}.csv"));
            if let Err(err) = ecrire_chronogramme(&p, lignes, e.experts) {
                eprintln!("chronogramme {} : {err}", p.display());
            }
        }
    };

    // ---- Passe témoin (C2) ----------------------------------------------------------------
    let ordre_t = perm(o.graine);
    let (temoin, lignes_t) = banc.passe(&ordre_t, Mode::Temoin)?;
    chrono("temoin", &lignes_t);
    let detectes: Vec<usize> = temoin["detectes"].as_array().unwrap().iter().map(|v| v.as_u64().unwrap() as usize).collect();
    eprintln!(
        "témoin : {} experts vérifiés, parties fausses {}, origines fausses {}, compteurs non nuls {}, détectés {} ; {:.3} Go/s servis",
        temoin["temoin"]["verifies"],
        temoin["temoin"]["parties_fausses"].as_array().map_or(0, |v| v.len()),
        temoin["temoin"]["origines_fausses"].as_array().map_or(0, |v| v.len()),
        temoin["controle"]["experts_non_nuls"].as_array().map_or(0, |v| v.len()),
        detectes.len(),
        temoin["go_s_servis"].as_f64().unwrap_or(0.0)
    );
    let cassure = o.attendus.as_ref().map(|att| {
        let mut a = att.clone();
        a.sort_unstable();
        let manques: Vec<usize> = a.iter().copied().filter(|x| !detectes.contains(x)).collect();
        let en_trop: Vec<usize> = detectes.iter().copied().filter(|x| !a.contains(x)).collect();
        eprintln!("cassure : {} corrompus, {} détectés parmi eux, {} détectés en trop", a.len(), a.len() - manques.len(), en_trop.len());
        json!({ "attendus": a, "manques": manques, "en_trop": en_trop })
    });

    let mut passes = Vec::new();
    let mut etages = Vec::new();
    if o.temoin_seul {
        let ordre = perm(o.graine.wrapping_add(1));
        let (p, lignes) = banc.passe(&ordre, Mode::Production)?;
        chrono("production", &lignes);
        eprintln!("production : détectés par les compteurs de la carte {:?}", p["detectes"]);
        passes.push(json!({ "tour": 0, "rang": 0, "lettre": "A", "graine": o.graine.wrapping_add(1), "passe": p }));
    } else {
        for tour in 0..o.tours {
            for (rang, &lettre) in ["A", "B", "B", "A"].iter().enumerate() {
                let graine = o.graine.wrapping_add(1 + 10 * tour as u64 + rang as u64);
                let ordre = perm(graine);
                let mode = if lettre == "A" { Mode::Production } else { Mode::Disque };
                let (p, lignes) = banc.passe(&ordre, mode)?;
                if mode == Mode::Production {
                    chrono(&format!("A-t{tour}-r{rang}"), &lignes);
                }
                eprintln!(
                    "tour {tour} {lettre} ({}) : {:.3} Go/s de tronçons, {:.3} Go/s servis, étrangers {:.3} Go/s, processeur des autres {:.0} %, compteurs non nuls {}",
                    mode.nom(),
                    p["go_s_troncons"].as_f64().unwrap_or(0.0),
                    p["go_s_servis"].as_f64().unwrap_or(0.0),
                    p["go_s_etrangers"].as_f64().unwrap_or(f64::NAN),
                    p["processeur"]["autres"].as_f64().unwrap_or(0.0) * 100.0,
                    p["controle"]["experts_non_nuls"].as_array().map_or(0, |v| v.len())
                );
                passes.push(json!({ "tour": tour, "rang": rang, "lettre": lettre, "graine": graine, "passe": p }));
            }
            let ordre = perm(o.graine.wrapping_add(1000 + tour as u64));
            let dma = banc.etage_dma(&ordre)?;
            let dec = banc.etage_decodage(&ordre, o.residents)?;
            eprintln!(
                "tour {tour} étages : DMA {:.3} Go/s, décodage {:.3} Go/s de tronçons ({:.3} ms par expert)",
                dma["go_s_troncons"].as_f64().unwrap_or(0.0),
                dec["go_s_troncons"].as_f64().unwrap_or(0.0),
                dec["ms_par_expert"].as_f64().unwrap_or(0.0)
            );
            etages.push(json!({ "tour": tour, "dma": dma, "decodage": dec }));
        }
    }

    Ok(json!({
        "fichier": o.fichier.display().to_string(),
        "ouverture_verifiee_s": ouvrir_s,
        "experts": n,
        "experts_par_passe": m,
        "couches": e.couches,
        "experts_par_couche": e.experts,
        "troncon_max_o": banc.lal,
        "octets_troncons": banc.entrees.iter().map(|r| r.longueur[0] as u64).sum::<u64>(),
        "octets_expert_origine": octets_origine(&banc.dims),
        "emplacement_o": banc.te,
        "r_reel": r_reel,
        "profondeur": o.profondeur,
        "emplacements": banc.s,
        "graine": o.graine,
        "residents": o.residents,
        "longueur_lecture": o.longueur_lecture,
        "temoin": temoin,
        "cassure": cassure,
        "passes": passes,
        "etages": etages,
        "machine_fin": machine::releve(Some(&banc.c)),
    }))
}
