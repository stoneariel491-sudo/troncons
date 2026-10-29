//! trc-ordo (lot O) : le moteur troncons et son ordonnanceur de couche (ARCHITECTURE.md § 5.1,
//! § 5.2, § 5.8). Étape J1 : **à la demande**, sans préchargement.
//!
//! # Le chemin d'un jeton (figure M1 du mémoire)
//!
//! ```text
//!  fil de l'hôte : ligne d'enchâssement lue (8 Kio, sans tampon) ─► pour chaque couche ℓ :
//!     calcul   : |norme|q k v|rotation|KV|attention|sortie|résidu|norme|routeur|top-k → boîte|
//!     hôte     :                                                    attend l'événement « routeur ℓ »,
//!                lit les k indices dans la boîte aux lettres projetée, cache.demander(ℓ, indices, t)
//!     disque   : défauts : une requête IOCP par tronçon, dans la fenêtre épinglée (ou l'entrée tiède)
//!     copie    :                    |DMA tronçon → tampon d'arrivée VRAM| (attend : arrivée libre)
//!     décodage :                                      |décodeur → emplacement| (attend : DMA)
//!     calcul   : (attend chaque « prêt ») |expert 0|expert 1|expert 2|expert 3|combiner|  → ℓ + 1
//!  puis : norme, logits, argmax ; l'hôte lit le jeton (et les logits si on les demande).
//! ```
//!
//! # Pourquoi l'ordre est sûr (aucun emplacement lu pendant qu'on l'écrit)
//!
//! Les trois flux ne se rencontrent que par des événements, et l'hôte ne décide la couche ℓ qu'après
//! avoir vu fini le routeur ℓ sur le flux de calcul. Le flux de calcul étant ordonné, les experts de
//! la couche ℓ − 1 ont alors fini d'être lus. Donc :
//! - un emplacement évincé à la couche ℓ (jamais un épinglé : `trc-cache`) n'est plus lu par la
//!   carte quand son nouveau décodage est mis en file ;
//! - un tampon d'arrivée (épinglé ou VRAM) réutilisé à la couche ℓ a fini sa copie et son décodage
//!   de la couche où il a servi (le flux de calcul les a attendus avant la fin de cette couche).
//! Les attentes par événement qui restent (copie après décodage précédent du même tampon, lecture
//! après copie du même tampon épinglé) ne coûtent rien et gardent l'ordre sûr si le préchargement
//! (J1+) avance un jour les défauts.
//!
//! # Le compte du cache
//!
//! Le moteur appelle `trc-cache` exactement comme le simulateur `rejouer` : pour chaque jeton,
//! pour chaque couche, `demander(ℓ, indices, t = pas · L + ℓ)`, `pret` sur chaque défaut, puis
//! `liberer(ℓ)`. Le témoin « compte du moteur = `rejouer` sur la trace du moteur, à l'unité » (O3)
//! découle de ce que c'est le même code ; il se vérifie quand même (`Moteur::ecrire_trace`).

use std::path::{Path, PathBuf};
use std::time::Instant;

use anyhow::{Context, Result, bail};
use trc_cache::{Cache, Compteurs, Decision, Lru};
use trc_cuda::{Contexte, Evenement, Flux, HoteEpingle, MemoireCarte, VueCarte, copier_vers_carte, copier_vers_hote};
use trc_es::{Achevement, Lecteur, Requete};
use trc_format::{Charge, EntreeRepertoire, Fichier, Sorte, empreinte64_morceaux};
use trc_modele::{Modele, Positions};
use trc_noyaux::Noyaux;
use trc_noyaux::abi::{self, DimsExpert};

pub use trc_modele::Hyper;

mod garde;
use garde::{Garde, LignesEnConstruction};

const ALIGNEMENT: u64 = 4096;
/// Fils de hachage de la garde de production (4 : 4,3 Go/s mesurés, plus que le disque).
const FILS_GARDE: usize = 4;

// ============================================================================ configuration

/// La configuration du moteur (§ 5.8). Les champs après `brut` sont des extensions (rien
/// d'existant ne change, § 6.2).
#[derive(Clone, Debug)]
pub struct Config {
    pub fichier: PathBuf,
    /// Go de cache tiède (tronçons codés en mémoire épinglée) ; 0 : mode A0.
    pub ram_tiede_go: f64,
    /// Garder `token_embd` en mémoire épinglée (0,6 Go) au lieu d'en lire une ligne par jeton.
    pub enchassement_en_ram: bool,
    /// Lectures confiées au système à la fois.
    pub profondeur_es: usize,
    /// d : couches dont les tampons d'arrivée tournent (fenêtre de d · k tampons, § 5.8).
    pub couches_d_avance: usize,
    /// J1+ : prédire les experts de la couche ℓ + 1 par son routeur appliqué au résidu de ℓ et
    /// lire d'avance les tronçons prédits absents de la VRAM (lecture anticipée seulement : le
    /// cache n'en sait rien, son compte reste celui de `rejouer`).
    pub prechargement: bool,
    /// Positions au plus (cache KV des couches pleines).
    pub contexte: u32,
    /// Chaque expert décodé redescend vers l'hôte et son empreinte est comparée au répertoire.
    pub temoin: bool,
    /// Le fichier attendu est un fichier brut (drapeau bit 2) : il doit l'être (rien ne se devine).
    pub brut: bool,
    // ---- extensions
    /// Emplacements VRAM d'experts ; `None` : autant que le plafond de VRAM le permet.
    pub emplacements: Option<u32>,
    /// Plafond de la VRAM **totale** occupée de la carte (Mio), pour le calcul automatique des
    /// emplacements : 8 188 − 909 (critère C10, § 7.1), moins une marge.
    pub vram_plafond_mio: u64,
    /// Longueur de chaque lecture de tronçon (multiple de 4 096, ≥ le plus grand tronçon) ; `None`
    /// : `longueur0 + longueur1`, le cas de la spécification (§ 4.7). Variante E2-V du lot E.
    pub longueur_lecture: Option<u32>,
    /// Garder les dates de chaque étage de chaque défaut (chronogramme).
    pub chronogramme: bool,
    /// Un battement par couche du préremplissage par flux sur la sortie d'erreur (constat G1 de
    /// l'épreuve J1 : dater un blocage ; une passe figée n'écrivait rien).
    pub battement: bool,
    /// Garde de production (constat M1) : empreinte des octets utiles de chaque tronçon lu contre le
    /// répertoire, et de chaque ligne d'enchâssement lue contre une table bâtie à l'ouverture. Vrai
    /// par défaut ; faux seulement pour chiffrer son coût (série ABBA) ou rejouer l'ancien moteur.
    pub garde: bool,
    /// Témoin de la garde : « troncon:N » retourne un bit du premier flux brut (MEDIANES ou BIAIS)
    /// du N-ième tronçon lu, « ligne:N » un bit de la N-ième ligne d'enchâssement lue, juste après la
    /// lecture (une erreur du disque que rien d'autre ne verrait). Rien en production.
    pub casser: Option<(String, u64)>,
    /// Essai (constat M5 de l'épreuve J1) : cache KV en f32 (hors couture N ; défaut : faux).
    pub kv_f32: bool,
    /// Lot B (génome synonyme) : le fichier attendu est un compagnon du mode rapide (drapeau bit 5)
    /// et il doit l'être, comme `brut` : rien ne se devine, et un fichier rapide ouvert sans le
    /// demander est refusé (le mode exact ne change jamais en silence).
    pub rapide: bool,
    /// P3 (routeur biaisé par le cache, `--biais-cache <β>`) : `Some(β)` ajoute β (unités brutes de
    /// logit) au logit de chaque expert déjà en VRAM pour le **choix** des k experts ; les poids de
    /// mélange restent calculés sur les logits non biaisés (règle de Skliar et al., arXiv 2412.00099).
    /// `None` (défaut) : le moteur lance les mêmes noyaux dans le même ordre qu'avant l'option.
    /// Refusé avec `prechargement` (qui prédit sans biais) et par `preremplir` (par couche, le biais
    /// d'une position dépendrait de l'état du cache après la précédente).
    pub biais_cache: Option<f32>,
}

impl Config {
    pub fn nouvelle(fichier: impl Into<PathBuf>) -> Config {
        Config {
            fichier: fichier.into(),
            ram_tiede_go: 0.0,
            enchassement_en_ram: false,
            profondeur_es: 4,
            couches_d_avance: 3,
            prechargement: false,
            contexte: 4096,
            temoin: false,
            brut: false,
            emplacements: None,
            vram_plafond_mio: 8188 - 909 - 100,
            longueur_lecture: None,
            chronogramme: false,
            battement: false,
            garde: true,
            casser: None,
            kv_f32: false,
            rapide: false,
            biais_cache: None,
        }
    }
}

// ============================================================================ compteurs

/// Les compteurs du moteur (§ 5.8) : `h` compté, octets, temps par étage.
#[derive(Clone, Copy, Debug, Default)]
pub struct CompteursMoteur {
    pub pas: u64,
    pub cache: Compteurs,
    /// Octets livrés par le lecteur (tronçons, lignes d'enchâssement ; sans le chargement).
    pub octets_lus: u64,
    pub octets_lus_troncons: u64,
    pub octets_lus_enchassement: u64,
    pub lectures_troncons: u64,
    pub lectures_enchassement: u64,
    /// Octets copiés vers la carte pour les défauts.
    pub octets_dma: u64,
    pub experts_decodes: u64,
    pub experts_verifies: u64,
    /// Secondes d'horloge de l'hôte : total des pas, attente du routeur, attente des lectures
    /// (de la première soumission à la dernière récolte d'une couche), fin du jeton.
    pub s_pas: f64,
    pub s_attente_routeur: f64,
    pub s_lectures: f64,
    pub s_fin_jeton: f64,
    /// Millisecondes de carte : copies et décodages des défauts (événements horodatés).
    pub ms_copie: f64,
    pub ms_decodage: f64,
    pub emplacements: u32,
    pub tiedes: u32,
    /// Préchargement (J1+) : lectures anticipées émises, servies à un défaut, octets.
    pub pf_emis: u64,
    pub pf_utiles: u64,
    pub pf_octets: u64,
    /// Préremplissage par flux (J1+) : positions servies, experts chargés (une fois par couche).
    pub flux_positions: u64,
    pub flux_experts: u64,
    /// Préremplissage par flux : lectures dont le tampon d'arrivée du tourniquet portait encore une
    /// lecture en vol, et qui ont pris le tampon libre suivant (cause de G1, ronde de corrections ;
    /// avant elle, la nouvelle lecture écrasait la précédente).
    pub flux_conflits_evites: u64,
    /// Garde de production : octets hachés, tronçons et lignes vérifiés, secondes d'attente du fil
    /// d'ordonnancement, octets lus à l'ouverture pour bâtir la table des lignes.
    pub garde_octets: u64,
    pub garde_troncons: u64,
    pub garde_lignes: u64,
    pub garde_attente_s: f64,
    pub garde_octets_ouverture: u64,
}

impl CompteursMoteur {
    /// h : la part des accès servis par la VRAM.
    pub fn h(&self) -> f64 {
        let a = self.cache.acces();
        if a == 0 { 0.0 } else { self.cache.succes_vram as f64 / a as f64 }
    }
}

/// Une ligne du chronogramme : les dates d'un défaut, en ms depuis le début de son jeton.
#[derive(Clone, Debug)]
pub struct Date {
    pub pas: u64,
    pub couche: u16,
    pub expert: u16,
    pub source: &'static str,
    pub soumis_ms: f64,
    pub lu_ms: f64,
    pub copie_debut_ms: f32,
    pub copie_fin_ms: f32,
    pub dec_debut_ms: f32,
    pub dec_fin_ms: f32,
    pub routeur_ms: f32,
    pub fin_couche_ms: f32,
}

// ============================================================================ outils

/// L'ensemble de travail du processus (octets), pour décomposer la mémoire de l'ouverture (C7).
pub fn ensemble_travail() -> u64 {
    use windows_sys::Win32::System::ProcessStatus::{GetProcessMemoryInfo, PROCESS_MEMORY_COUNTERS};
    use windows_sys::Win32::System::Threading::GetCurrentProcess;
    let mut c: PROCESS_MEMORY_COUNTERS = unsafe { std::mem::zeroed() };
    c.cb = std::mem::size_of::<PROCESS_MEMORY_COUNTERS>() as u32;
    // SAFETY : structure de sortie de la bonne taille ; pseudo-poignée du processus courant.
    if unsafe { GetProcessMemoryInfo(GetCurrentProcess(), &mut c, c.cb) } == 0 {
        return 0;
    }
    c.WorkingSetSize as u64
}

fn es(e: trc_es::Erreur) -> anyhow::Error {
    anyhow::anyhow!("trc-es : {e}")
}

/// L'empreinte64 de l'expert d'origine (§ 4.11, § 4.12) recalculée depuis un emplacement SoA
/// (§ 5.6) : pour j = 0, 1, 2 les blocs `[e, qs[16]]` dans l'ordre β, puis pour j = 0, 1, 2 les
/// biais f32. Écrite ici depuis le texte de la spécification.
pub fn empreinte_emplacement(empl: &[u8], d: &DimsExpert) -> u64 {
    let mut blocs: Vec<Vec<u8>> = Vec::with_capacity(3);
    for j in 0..3 {
        let disp = d.disposition(j);
        let (b, e) = (disp.base as usize, (disp.base + disp.echelles) as usize);
        let n = d.blocs(j) as usize;
        let mut v = vec![0u8; 17 * n];
        for beta in 0..n {
            v[17 * beta] = empl[e + beta];
            v[17 * beta + 1..17 * beta + 17].copy_from_slice(&empl[b + 16 * beta..b + 16 * beta + 16]);
        }
        blocs.push(v);
    }
    let biais: Vec<&[u8]> = (0..3)
        .map(|j| {
            let disp = d.disposition(j);
            let p = (disp.base + disp.biais) as usize;
            &empl[p..p + 4 * d.lignes[j] as usize]
        })
        .collect();
    empreinte64_morceaux(blocs.iter().map(|v| &v[..]).chain(biais))
}

/// Les LUT d'une couche (`u32[3][4][4096]`, disposition des noyaux, § 4.9.2) depuis les tables.
fn luts_couche(f: &Fichier, c: u16) -> Result<Vec<u32>> {
    let freq = |j: u8, s: Sorte, ctx: u8| f.table(c, j, s, ctx).and_then(|t| t.charge.frequences());
    let t: [[Option<&[u16]>; 4]; 3] = std::array::from_fn(|j| {
        let j = j as u8;
        [freq(j, Sorte::Delta, 0), freq(j, Sorte::CodesCtx, 0), freq(j, Sorte::CodesCtx, 1), freq(j, Sorte::CodesCtx, 2)]
    });
    abi::luts_couche(&t).map_err(|e| anyhow::anyhow!("tables de la couche {c} : {e}"))
}

// ============================================================================ le moteur

/// Un défaut en cours dans une couche.
struct Defaut {
    j: usize,
    emplacement: u32,
    entree: EntreeRepertoire,
    /// Source épinglée : 0 fenêtre d'arrivée, 1 entrée tiède, 2 tampon de préchargement (J1+).
    source: u8,
    decalage_hote: usize,
    arrivee: usize,
    lu: bool,
    /// Défaut servi par la RAM tiède (aucune lecture).
    ram: bool,
    /// Tampon de préchargement qui porte (ou portera) ce tronçon.
    pf: Option<usize>,
    soumis: f64,
    lu_ms: f64,
}

pub struct Moteur {
    /// Premier champ : détruit le premier (ses fils lisent les tampons épinglés).
    garde: Garde,
    /// Empreintes des lignes de `token_embd` (mode A0 avec garde).
    lignes: Option<Vec<u64>>,
    /// Lectures vues par le témoin de la garde (`Config::casser`).
    vus_casser: u64,
    pub config: Config,
    fichier: Fichier,
    // l'ordre des champs est celui de la destruction : tout ce qui tient de la mémoire de carte
    // avant le contexte.
    modele: Modele,
    noyaux: Noyaux,
    lecteur: Lecteur,
    cache: Cache<Lru>,
    emplacements: MemoireCarte,
    te: usize,
    luts: Option<MemoireCarte>,
    lal: usize,
    n_arrivees: usize,
    arrivee_hote: HoteEpingle,
    arrivee_carte: MemoireCarte,
    tiede: Option<HoteEpingle>,
    n_tiedes: u32,
    controle_carte: MemoireCarte,
    controle_hote: HoteEpingle,
    boite: HoteEpingle,
    ligne_hote: HoteEpingle,
    enchassement_ram: Option<(HoteEpingle, u64)>,
    sortie_hote: HoteEpingle,
    retour: Option<HoteEpingle>,
    ev_copie: Vec<Evenement>,
    ev_dec: Vec<Evenement>,
    ev_routeur: Evenement,
    // dates (chronogramme et temps de carte)
    ev_base: Evenement,
    ev_temps: Vec<[Evenement; 4]>,
    ev_couche: Vec<[Evenement; 2]>,
    dates: Vec<Date>,
    calcul: Flux,
    copie: Flux,
    decodage: Flux,
    ctx: Contexte,
    brut: bool,
    /// v1.2, drapeau CANONIQUE : le témoin compare l'expert décodé à `empreinte_canonique`.
    canonique: bool,
    sequence: u32,
    trace: Vec<u16>,
    compteurs: CompteursMoteur,
    /// Défauts du pas en cours : (couche, j, entrée) pour nommer une erreur de décodage.
    decodes_du_pas: Vec<(u16, usize, u16)>,
    /// Ensemble de travail relevé après chaque étape de l'ouverture (extension, critère C7).
    pub etapes_memoire: Vec<(&'static str, u64)>,
    /// Préchargement (J1+) : 2 · k tampons épinglés ; l'ensemble (cible % 2) sert les prédictions
    /// de la couche cible.
    pf_hote: Option<HoteEpingle>,
    pf: Vec<Prechargement>,
    /// Préremplissage par flux : l'expert dont le contrôle attend dans la case de chaque arrivée.
    flux_controle: Vec<Option<(u16, u16)>>,
    /// Achèvements récoltés pendant un vidage des préchargements, à rendre à la boucle de la couche.
    en_attente: Vec<Achevement>,
    /// P3 : le vecteur de biais de la couche en cours (f32[experts]), tampon épinglé puis copie sur la
    /// carte ; `None` sans `--biais-cache`. L'hôte ne réécrit le tampon qu'après avoir vu fini le
    /// routeur de la couche précédente (`ev_routeur`), donc après la fin de la copie qui le lisait.
    biais_hote: Option<HoteEpingle>,
    biais_carte: Option<MemoireCarte>,
}

/// Un tampon de préchargement.
#[derive(Clone, Copy, Debug, Default)]
struct Prechargement {
    /// (couche cible, expert) lu d'avance, s'il y en a un.
    id: Option<(u16, u16)>,
    en_vol: bool,
}

/// Jetons du lecteur : défauts de la couche (0 .. k), ligne d'enchâssement, préchargements.
const JETON_LIGNE: u64 = u64::MAX;
const JETON_PF: u64 = 1 << 32;

impl Moteur {
    pub fn nouveau(c: &Config) -> Result<Moteur> {
        if c.profondeur_es == 0 || c.couches_d_avance == 0 {
            bail!("profondeur d'E/S et couches d'avance : au moins 1");
        }
        if let Some(b) = c.biais_cache {
            if !b.is_finite() {
                bail!("--biais-cache : β = {b} n'est pas un nombre fini");
            }
            if c.prechargement {
                bail!("--biais-cache et --prechargement ne se combinent pas : le préchargement prédit les experts de la couche suivante sans biais");
            }
        }
        let mut etapes: Vec<(&'static str, u64)> = vec![("avant", ensemble_travail())];
        let fichier = Fichier::ouvrir(&c.fichier).with_context(|| format!("ouverture de {}", c.fichier.display()))?;
        etapes.push(("fichier", ensemble_travail()));
        let e = fichier.entete().clone();
        if e.est_brut() != c.brut {
            bail!("{} : fichier {} alors que la configuration dit {}", c.fichier.display(), if e.est_brut() { "brut" } else { "codé" }, if c.brut { "brut" } else { "codé" });
        }
        if e.niveaux != 1 {
            bail!("{} niveaux : J1 lit la v1.0 à un niveau", e.niveaux);
        }
        let ctx = Contexte::nouveau(0)?;
        let calcul = Flux::nouveau(&ctx, true)?;
        let copie = Flux::nouveau(&ctx, false)?;
        let decodage = Flux::nouveau(&ctx, false)?;
        etapes.push(("contexte_flux", ensemble_travail()));
        if e.est_rapide() != c.rapide {
            bail!("{} : fichier {} alors que la configuration dit {} (option --rapide)", c.fichier.display(), if e.est_rapide() { "du mode rapide" } else { "exact" }, if c.rapide { "rapide" } else { "exact" });
        }
        let mut noyaux = Noyaux::charger(&ctx)?;
        if e.est_rapide() {
            // Les centres de la base (table CENTRES, type 3) : un seul jeu pour tout le fichier,
            // exigé identique dans chaque (couche, matrice).
            let mut centres: Option<[f32; 4]> = None;
            for couche in 0..e.couches {
                for j in 0..e.matrices as u8 {
                    let t = fichier.table(couche, j, Sorte::Centres, 0).with_context(|| format!("fichier rapide : table CENTRES de ({couche}, {j}) absente"))?;
                    let Charge::Centres(cs) = &t.charge else { bail!("table CENTRES de ({couche}, {j}) : charge de type {}", t.charge.type_charge()) };
                    if centres.is_some_and(|x| x.map(f32::to_bits) != cs.map(f32::to_bits)) {
                        bail!("fichier rapide : centres de ({couche}, {j}) différents de ceux de (0, 0)");
                    }
                    centres = Some(*cs);
                }
            }
            noyaux.centres_rapides = centres;
        }
        etapes.push(("noyaux", ensemble_travail()));
        let lecteur = Lecteur::ouvrir(&c.fichier, c.profondeur_es).map_err(es)?;
        let modele = Modele::charger_kv(&ctx, &calcul, &lecteur, &fichier, c.contexte, c.kv_f32)?;
        etapes.push(("modele", ensemble_travail()));
        let h = modele.h.clone();
        let (l, k) = (h.couches, h.actifs);
        let te = h.taille_emplacement() as usize;

        // LUT de toutes les couches (fichier codé), montées une fois (§ 4.6).
        let luts = if e.est_brut() {
            None
        } else {
            let mut tout: Vec<u8> = Vec::with_capacity(l * abi::LUTS_PAR_COUCHE * 4);
            for couche in 0..l {
                for m in luts_couche(&fichier, couche as u16)? {
                    tout.extend_from_slice(&m.to_le_bytes());
                }
            }
            let d = MemoireCarte::allouer(&ctx, tout.len())?;
            let mut tampon = HoteEpingle::allouer(&ctx, tout.len(), false)?;
            tampon.tranche_mut()[..tout.len()].copy_from_slice(&tout);
            copier_vers_carte(d.tout(), &tampon, 0, tout.len(), &calcul)?;
            calcul.synchroniser()?;
            Some(d)
        };

        etapes.push(("luts", ensemble_travail()));
        // La fenêtre épinglée : d · k tampons d'arrivée de la taille de la plus longue lecture.
        let lmax = fichier.repertoire().iter().map(|r| r.longueur_jusqua(1)).max().unwrap_or(ALIGNEMENT);
        let lal = match c.longueur_lecture {
            Some(x) => {
                if x as u64 % ALIGNEMENT != 0 || (x as u64) < lmax {
                    bail!("longueur de lecture {x} : multiple de 4 096 et ≥ {lmax} (plus grand tronçon) exigés");
                }
                x as u64
            }
            None => lmax,
        } as usize;
        let n_arrivees = c.couches_d_avance * k;
        if n_arrivees > l * k {
            bail!("{n_arrivees} tampons d'arrivée pour {l} couches de k = {k} : d ≤ L exigé");
        }
        let arrivee_hote = HoteEpingle::allouer(&ctx, n_arrivees * lal, false)?;
        let arrivee_carte = MemoireCarte::allouer(&ctx, n_arrivees * lal)?;
        let n_tiedes = ((c.ram_tiede_go * 1e9) / lal as f64).floor().max(0.0) as u32;
        let tiede = if n_tiedes > 0 { Some(HoteEpingle::allouer(&ctx, n_tiedes as usize * lal, false)?) } else { None };
        let controle_carte = MemoireCarte::allouer(&ctx, l * k * 16)?;
        let controle_hote = HoteEpingle::allouer(&ctx, l * k * 16, false)?;
        let mut boite = HoteEpingle::allouer(&ctx, 4096, true)?;
        boite.tranche_mut().fill(0);
        let ligne_hote = HoteEpingle::allouer(&ctx, 2 * ALIGNEMENT as usize, false)?;
        let sortie_hote = HoteEpingle::allouer(&ctx, 4 * h.vocab + 4096, false)?;
        let retour = if c.temoin { Some(HoteEpingle::allouer(&ctx, te, false)?) } else { None };
        let enchassement_ram = if c.enchassement_en_ram { Some(charger_enchassement(&ctx, &lecteur, &modele)?) } else { None };
        // Garde (M1) : la table des empreintes des lignes, lue dans la fenêtre d'arrivée (aucune
        // mémoire de plus que la table elle-même : 8 o par jeton du vocabulaire).
        let (lignes, garde_ouverture) = if c.garde && !c.enchassement_en_ram {
            let (v, n) = table_des_lignes(&lecteur, &modele, &arrivee_hote)?;
            (Some(v), n)
        } else {
            (None, 0)
        };

        etapes.push(("fenetre_et_tampons", ensemble_travail()));
        // Les emplacements : autant que le plafond de VRAM totale le permet (critère C10).
        let (libre, totale) = ctx.memoire();
        let occupee = totale - libre;
        let plafond = c.vram_plafond_mio << 20;
        let auto = (plafond.saturating_sub(occupee) / te as u64) as u32;
        let n_empl = c.emplacements.unwrap_or(auto).min((l * h.experts) as u32);
        if (n_empl as usize) < k {
            bail!("{n_empl} emplacements d'experts : il en faut au moins k = {k} (VRAM occupée {} Mio, plafond {} Mio)", occupee >> 20, c.vram_plafond_mio);
        }
        let emplacements = MemoireCarte::allouer(&ctx, n_empl as usize * te).with_context(|| format!("{n_empl} emplacements de {te} o"))?;
        let mut cache = Cache::nouveau(n_empl, n_tiedes, Lru::default(), Lru::default());
        let entrees: Vec<EntreeRepertoire> = fichier.repertoire().to_vec();
        let ne = h.experts;
        cache.fixer_tailles(move |(cc, x)| entrees[cc as usize * ne + x as usize].longueur_jusqua(1));

        let ev = |horo: bool| Evenement::nouveau(&ctx, horo);
        let ev_copie = (0..n_arrivees).map(|_| ev(false)).collect::<trc_cuda::Result<Vec<_>>>()?;
        let ev_dec = (0..n_arrivees).map(|_| ev(false)).collect::<trc_cuda::Result<Vec<_>>>()?;
        let ev_routeur = ev(false)?;
        let ev_base = ev(true)?;
        let mut ev_temps = Vec::with_capacity(l * k);
        for _ in 0..l * k {
            ev_temps.push([ev(true)?, ev(true)?, ev(true)?, ev(true)?]);
        }
        let mut ev_couche = Vec::with_capacity(l);
        for _ in 0..l {
            ev_couche.push([ev(true)?, ev(true)?]);
        }
        etapes.push(("emplacements_cache_evenements", ensemble_travail()));
        let compteurs = CompteursMoteur { emplacements: n_empl, tiedes: n_tiedes, garde_octets_ouverture: garde_ouverture, ..Default::default() };
        let pf_hote = if c.prechargement { Some(HoteEpingle::allouer(&ctx, 2 * k * lal, false)?) } else { None };
        let pf = if c.prechargement { vec![Prechargement::default(); 2 * k] } else { Vec::new() };
        let (biais_hote, biais_carte) = if c.biais_cache.is_some() {
            (Some(HoteEpingle::allouer(&ctx, 4 * h.experts, false)?), Some(MemoireCarte::allouer(&ctx, 4 * h.experts)?))
        } else {
            (None, None)
        };
        Ok(Moteur {
            garde: Garde::nouvelle(FILS_GARDE),
            lignes,
            vus_casser: 0,
            config: c.clone(),
            fichier,
            modele,
            noyaux,
            lecteur,
            cache,
            emplacements,
            te,
            luts,
            lal,
            n_arrivees,
            arrivee_hote,
            arrivee_carte,
            tiede,
            n_tiedes,
            controle_carte,
            controle_hote,
            boite,
            ligne_hote,
            enchassement_ram,
            sortie_hote,
            retour,
            ev_copie,
            ev_dec,
            ev_routeur,
            ev_base,
            ev_temps,
            ev_couche,
            dates: Vec::new(),
            calcul,
            copie,
            decodage,
            ctx,
            brut: e.est_brut(),
            canonique: e.est_canonique(),
            sequence: 0,
            trace: Vec::new(),
            compteurs,
            decodes_du_pas: Vec::new(),
            etapes_memoire: etapes,
            pf_hote,
            pf,
            flux_controle: vec![None; n_arrivees],
            en_attente: Vec::new(),
            biais_hote,
            biais_carte,
        })
    }

    pub fn hyper(&self) -> &Hyper {
        &self.modele.h
    }
    pub fn fichier(&self) -> &Fichier {
        &self.fichier
    }
    pub fn modele(&self) -> &Modele {
        &self.modele
    }
    pub fn compteurs(&self) -> CompteursMoteur {
        let mut c = self.compteurs;
        c.cache = self.cache.compteurs();
        c.octets_lus = self.lecteur.octets_lus();
        c.garde_octets = self.garde.octets;
        c.garde_troncons = self.garde.troncons;
        c.garde_attente_s = self.garde.attente_s;
        c
    }
    /// Octets de VRAM alloués par le moteur (modèle, emplacements, LUT, tampons d'arrivée).
    pub fn octets_vram(&self) -> u64 {
        self.modele.octets_vram()
            + self.emplacements.octets() as u64
            + self.luts.as_ref().map_or(0, |m| m.octets() as u64)
            + self.arrivee_carte.octets() as u64
            + self.controle_carte.octets() as u64
    }
    /// Octets de mémoire épinglée tenus par le moteur (fenêtre, tiède, petits tampons).
    pub fn octets_epingles(&self) -> u64 {
        (self.arrivee_hote.octets()
            + self.tiede.as_ref().map_or(0, |t| t.octets())
            + self.controle_hote.octets()
            + self.boite.octets()
            + self.ligne_hote.octets()
            + self.sortie_hote.octets()
            + self.retour.as_ref().map_or(0, |t| t.octets())
            + self.pf_hote.as_ref().map_or(0, |t| t.octets())
            + self.enchassement_ram.as_ref().map_or(0, |t| t.0.octets())) as u64
    }
    pub fn longueur_arrivee(&self) -> usize {
        self.lal
    }
    /// Tampons d'arrivée de la fenêtre (d · k).
    pub fn arrivees(&self) -> usize {
        self.n_arrivees
    }
    /// Entrées du cache tiède (0 en mode A0).
    pub fn tiedes(&self) -> u32 {
        self.n_tiedes
    }
    pub fn contexte(&self) -> &Contexte {
        &self.ctx
    }
    pub fn dates(&self) -> &[Date] {
        &self.dates
    }
    /// La trace de routage du moteur (format de `trc_cache::lire_trace`).
    pub fn texte_trace(&self) -> String {
        let h = &self.modele.h;
        let (l, k) = (h.couches, h.actifs);
        let mut s = format!("# trace du moteur troncons : {}\nE={}\n", self.config.fichier.display(), h.experts);
        for t in 0..self.compteurs.pas as usize {
            let mut ligne = String::new();
            for c in 0..l {
                if c > 0 {
                    ligne.push_str(" | ");
                }
                let g = &self.trace[(t * l + c) * k..(t * l + c + 1) * k];
                ligne.push_str(&g.iter().map(|x| x.to_string()).collect::<Vec<_>>().join(" "));
            }
            s.push_str(&ligne);
            s.push('\n');
        }
        s
    }
    pub fn ecrire_trace(&self, chemin: &Path) -> Result<()> {
        std::fs::write(chemin, self.texte_trace()).with_context(|| format!("écriture de {}", chemin.display()))
    }

    /// Reprend à la position 0 (nouvelle fenêtre). Le cache d'experts est gardé (même modèle) ; le
    /// cache KV n'a rien à effacer : l'attention ne lit que des cases écrites depuis la position 0.
    pub fn reinitialiser(&mut self) {}

    /// Soumet une lecture après la fin des hachages de la garde qui lisent encore sa destination.
    fn soumettre(&mut self, r: Requete) -> Result<()> {
        self.garde.attendre_zone(r.destination, r.longueur as usize)?;
        self.lecteur.soumettre(r).map_err(es)
    }

    /// Après la lecture d'un tronçon dans `adresse` : octets livrés suffisants, témoin de la garde
    /// (`Config::casser`), puis hachage confié à la garde.
    fn apres_lecture(&mut self, adresse: *mut u8, entree: &EntreeRepertoire, octets: u32, couche: u16, expert: u16) -> Result<()> {
        if (octets as u64) < entree.utiles[0] as u64 {
            bail!("couche {couche}, expert {expert} : {octets} octets lus, {} utiles attendus", entree.utiles[0]);
        }
        if let Some((sorte, n)) = &self.config.casser
            && sorte == "troncon"
        {
            self.vus_casser += 1;
            if self.vus_casser == *n {
                // SAFETY : la lecture est achevée, rien d'autre n'écrit ce tampon ; `utiles` octets.
                let o = unsafe { std::slice::from_raw_parts_mut(adresse, entree.utiles[0] as usize) };
                casser_premier_flux_brut(o);
                eprintln!("troncons : témoin de la garde : un bit retourné dans un flux brut de couche {couche}, expert {expert}");
            }
        }
        if self.config.garde {
            self.garde.soumettre(adresse, entree.utiles[0] as usize, entree.empreinte_niveau[0], couche, expert);
        }
        Ok(())
    }

    /// Garde de la ligne d'enchâssement du jeton `jeton`, lue dans `ligne_hote` à `dans`.
    fn garder_ligne(&mut self, jeton: u32, dans: usize, ol: usize) -> Result<()> {
        if let Some((sorte, n)) = &self.config.casser
            && sorte == "ligne"
        {
            self.vus_casser += 1;
            if self.vus_casser == *n {
                self.ligne_hote.tranche_mut()[dans] ^= 1;
                eprintln!("troncons : témoin de la garde : un bit retourné dans la ligne d'enchâssement du jeton {jeton}");
            }
        }
        if let Some(t) = &self.lignes {
            let e = trc_format::empreinte64(&self.ligne_hote.tranche()[dans..dans + ol]);
            if e != t[jeton as usize] {
                bail!("garde de production : ligne d'enchâssement du jeton {jeton} : empreinte {e:016x} au lieu de {:016x}", t[jeton as usize]);
            }
            self.compteurs.garde_lignes += 1;
        }
        Ok(())
    }

    /// Lit `n` octets à `decalage` (alignés) dans `tampon[dec_tampon..]` et attend la fin.
    fn lire_sync(&mut self, jeton: u64, decalage: u64, n: u32, destination: *mut u8) -> Result<()> {
        self.soumettre(Requete { jeton, decalage, longueur: n, destination })?;
        let mut a: Vec<Achevement> = Vec::new();
        loop {
            a.clear();
            self.recolter_route(&mut a)?;
            if let Some(x) = a.iter().find(|x| x.jeton == jeton) {
                if let Some(e) = x.erreur {
                    bail!("lecture de {n} o au décalage {decalage} : erreur Windows {e}");
                }
                if x.octets != n {
                    bail!("lecture de {n} o au décalage {decalage} : {} o livrés", x.octets);
                }
                return Ok(());
            }
        }
    }

    /// Récolte des achèvements ; ceux des préchargements sont rangés ici (tampon marqué lu), les
    /// autres rendus dans `sortie`.
    fn recolter_route(&mut self, sortie: &mut Vec<Achevement>) -> Result<()> {
        // Achèvements mis de côté pendant un vidage des préchargements : rendus d'abord, sans attendre.
        if !self.en_attente.is_empty() {
            sortie.append(&mut self.en_attente);
            return Ok(());
        }
        let mut a: Vec<Achevement> = Vec::new();
        self.lecteur.recolter(u32::MAX, &mut a).map_err(es)?;
        for x in a {
            if x.jeton >= JETON_PF && x.jeton != JETON_LIGNE {
                let s = (x.jeton - JETON_PF) as usize;
                if let Some(e) = x.erreur {
                    bail!("préchargement {:?} : erreur Windows {e}", self.pf[s].id);
                }
                self.pf[s].en_vol = false;
                if let Some((c, e)) = self.pf[s].id {
                    let en = *self.fichier.entree(c, e);
                    // SAFETY : tampon s de `lal` octets dans les tampons de préchargement.
                    let adr = unsafe { self.pf_hote.as_ref().unwrap().pointeur().add(s * self.lal) };
                    self.apres_lecture(adr, &en, x.octets, c, e)?;
                }
            } else {
                sortie.push(x);
            }
        }
        Ok(())
    }

    /// Attend que les préchargements de l'ensemble `ens` soient achevés (avant de les réutiliser).
    fn vider_ensemble(&mut self, ens: usize) -> Result<()> {
        let k = self.modele.h.actifs;
        while (ens * k..(ens + 1) * k).any(|s| self.pf[s].en_vol) {
            // Les lectures des défauts de la couche en cours peuvent s'achever pendant ce vidage
            // (défaut trouvé le 2026-10-16 à 01 h 41 : la passe tombait) : on les garde de côté.
            let mut a = Vec::new();
            let attente = std::mem::take(&mut self.en_attente);
            self.recolter_route(&mut a)?;
            self.en_attente = attente;
            self.en_attente.append(&mut a);
        }
        Ok(())
    }

    /// Préremplissage par flux (J1+, § 5.8) : les positions 0 .. n − 1 de `jetons`, couche par
    /// couche ; dans une couche, toutes les positions passent l'attention et le routeur, puis chaque
    /// expert demandé est lu, copié, décodé **une fois** et appliqué à toutes les positions qui
    /// l'ont choisi, puis chaque position combine ses k sorties dans l'ordre j = 0 .. k − 1. Mêmes
    /// noyaux, mêmes entrées que la boucle de pas : logits égaux au bit (proposition 5). Le cache
    /// sert les experts (demander par paquets de la couche, liberer à la fin de la couche) ; ces
    /// accès ne vont pas dans la trace (elle reste celle des pas, pour `rejouer`). Rend le jeton qui
    /// suit la dernière position ; `logits(i, z)` reçoit, si on le donne, les logits de chaque
    /// position (une sortie par position, à la fin).
    pub fn preremplir(&mut self, jetons: &[u32], mut logits: Option<&mut dyn FnMut(usize, &[f32]) -> Result<()>>) -> Result<u32> {
        if self.config.biais_cache.is_some() {
            bail!("--biais-cache et le préremplissage par flux (--flux) ne se combinent pas : par couche, le biais d'une position dépendrait de l'état du cache après la précédente");
        }
        let t_pas = Instant::now();
        let h = self.modele.h.clone();
        let (l_n, k, d) = (h.couches, h.actifs, h.d);
        let n = jetons.len();
        if n == 0 || n > h.contexte as usize {
            bail!("préremplissage de {n} positions (contexte {})", h.contexte);
        }
        let pos = Positions::allouer(&self.ctx, &h, n)?;
        // Enchâssement de chaque position (lecture sans tampon de sa ligne, ou copie depuis la RAM).
        let ligne = self.modele.tampon_ligne();
        for (i, &j) in jetons.iter().enumerate() {
            let (abs, ol) = self.modele.ligne_enchassement(j)?;
            if let Some((ram, base)) = &self.enchassement_ram {
                copier_vers_carte(ligne.vue_debut(ol as usize), ram, (abs - base) as usize, ol as usize, &self.calcul)?;
                self.modele.enchasser_pos(&self.noyaux, ligne.vue_debut(ol as usize), &pos, i, &self.calcul)?;
            } else {
                let a0 = abs & !(ALIGNEMENT - 1);
                let nl = (2 * ALIGNEMENT).min(self.lecteur.taille() - a0) as u32;
                self.calcul.synchroniser()?; // la ligne précédente a fini de servir
                let dest = self.ligne_hote.pointeur();
                self.lire_sync(JETON_LIGNE, a0, nl, dest)?;
                self.garder_ligne(j, (abs - a0) as usize, ol as usize)?;
                copier_vers_carte(ligne, &self.ligne_hote, 0, nl as usize, &self.calcul)?;
                self.modele.enchasser_pos(&self.noyaux, VueCarte { adresse: ligne.adresse + (abs - a0), octets: ol as usize }, &pos, i, &self.calcul)?;
                self.compteurs.octets_lus_enchassement += nl as u64;
                self.compteurs.lectures_enchassement += 1;
            }
        }
        let mut idx_hote = HoteEpingle::allouer(&self.ctx, n * k * 4, false)?;
        let n_empl = self.compteurs.emplacements as usize;
        let mut prochaine_arrivee = 0usize;
        for l in 0..l_n {
            for i in 0..n {
                self.modele.debut_couche_pos(&self.noyaux, l, &pos, i, &self.calcul)?;
            }
            copier_vers_hote(&mut idx_hote, 0, pos.indices(), &self.calcul)?;
            self.calcul.synchroniser()?;
            let idx: Vec<u16> = idx_hote.tranche()[..n * k * 4].chunks_exact(4).map(|c| u32::from_le_bytes(c.try_into().unwrap()) as u16).collect();
            let mut par_expert: Vec<Vec<(usize, usize)>> = vec![Vec::new(); h.experts];
            for i in 0..n {
                for j in 0..k {
                    let e = idx[i * k + j] as usize;
                    if e >= h.experts {
                        bail!("couche {l}, position {i} : expert {e} hors de [0, {})", h.experts);
                    }
                    par_expert[e].push((i, j));
                }
            }
            let demandes: Vec<u16> = (0..h.experts).filter(|&e| !par_expert[e].is_empty()).map(|e| e as u16).collect();
            // Par paquets qui tiennent dans les emplacements (épinglés jusqu'à la fin du paquet).
            let paquet = n_empl.saturating_sub(1).max(1);
            for morceau in demandes.chunks(paquet) {
                let decisions = self.cache.demander(l as u16, morceau, self.compteurs.pas * l_n as u64 + l as u64);
                // Défauts : lectures en file (au plus `profondeur` en vol par le lecteur), puis copie et
                // décodage de chacun dès qu'il est lu ; chaque expert présent part tout de suite.
                let mut a_faire: Vec<(usize, u32, u64)> = Vec::new(); // (indice dans morceau, emplacement, jeton de lecture)
                let mut emplacement_de = vec![0u32; morceau.len()];
                for (m, dcs) in decisions.iter().enumerate() {
                    match *dcs {
                        Decision::Succes { emplacement } => emplacement_de[m] = emplacement,
                        Decision::DefautRam { emplacement, .. } | Decision::DefautDisque { emplacement, .. } => {
                            emplacement_de[m] = emplacement;
                            a_faire.push((m, emplacement, 0));
                        }
                    }
                }
                // Les experts présents : appliqués tout de suite.
                for (m, dcs) in decisions.iter().enumerate() {
                    if let Decision::Succes { .. } = dcs {
                        let v = self.emplacements.vue(emplacement_de[m] as usize * self.te, self.te);
                        for &(i, j) in &par_expert[morceau[m] as usize] {
                            self.modele.expert_pos(&self.noyaux, v, &pos, i, j, &self.calcul)?;
                        }
                    }
                }
                // Les défauts (mode A0 : tout passe par la fenêtre d'arrivée ; les entrées tièdes ne
                // servent pas au préremplissage par flux).
                let mut soumis = 0usize;
                let mut faits = 0usize;
                let mut en_vol: Vec<(usize, usize)> = Vec::new(); // (indice dans a_faire, arrivée)
                let mut a: Vec<Achevement> = Vec::new();
                while faits < a_faire.len() {
                    while soumis < a_faire.len() && en_vol.len() < self.n_arrivees.min(self.config.profondeur_es.max(1) * 2) {
                        let (m, _, _) = a_faire[soumis];
                        // Le tampon du tourniquet, sauf s'il porte encore une lecture en vol : les
                        // lectures s'achèvent dans le désordre (sous une charge concurrente, une lecture
                        // peut rester en vol pendant que les onze suivantes passent) ; avant la ronde de
                        // corrections, la nouvelle lecture écrasait alors l'ancienne dans le même
                        // tampon (cause probable de G1). Il y a toujours un tampon libre : au plus
                        // min(d · k, 2 · profondeur) − 1 < d · k lectures sont en vol ici.
                        let candidat = prochaine_arrivee % self.n_arrivees;
                        let mut i_arr = candidat;
                        while en_vol.iter().any(|&(_, b)| b == i_arr) {
                            i_arr = (i_arr + 1) % self.n_arrivees;
                        }
                        if i_arr != candidat {
                            self.compteurs.flux_conflits_evites += 1;
                        }
                        prochaine_arrivee = i_arr + 1;
                        self.ev_copie[i_arr].attendre()?;
                        let en = *self.fichier.entree(l as u16, morceau[m]);
                        let long = (self.config.longueur_lecture.map_or(en.longueur_jusqua(1), |x| x as u64)).min(self.lecteur.taille() - en.decalage);
                        // SAFETY : tampon d'arrivée i_arr de `lal` octets.
                        let dest = unsafe { self.arrivee_hote.pointeur().add(i_arr * self.lal) };
                        self.soumettre(Requete { jeton: soumis as u64, decalage: en.decalage, longueur: long as u32, destination: dest })?;
                        self.compteurs.octets_lus_troncons += long;
                        self.compteurs.lectures_troncons += 1;
                        en_vol.push((soumis, i_arr));
                        soumis += 1;
                    }
                    a.clear();
                    self.recolter_route(&mut a)?;
                    for x in &a {
                        if let Some(e) = x.erreur {
                            bail!("préremplissage, couche {l} : lecture, erreur Windows {e}");
                        }
                        let q = en_vol.iter().position(|&(s, _)| s as u64 == x.jeton).context("achèvement inconnu au préremplissage")?;
                        let (s, i_arr) = en_vol.remove(q);
                        let (m, empl, _) = a_faire[s];
                        let en = *self.fichier.entree(l as u16, morceau[m]);
                        // SAFETY : tampon d'arrivée i_arr de `lal` octets.
                        let adr = unsafe { self.arrivee_hote.pointeur().add(i_arr * self.lal) };
                        self.apres_lecture(adr, &en, x.octets, l as u16, morceau[m])?;
                        let df = Defaut {
                            j: 0,
                            emplacement: empl,
                            entree: *self.fichier.entree(l as u16, morceau[m]),
                            source: 0,
                            decalage_hote: i_arr * self.lal,
                            arrivee: i_arr,
                            lu: true,
                            ram: false,
                            pf: None,
                            soumis: 0.0,
                            lu_ms: 0.0,
                        };
                        self.envoyer_et_decoder_flux(l, &df, morceau[m])?;
                        self.cache.pret(empl);
                        let v = self.emplacements.vue(empl as usize * self.te, self.te);
                        for &(i, j) in &par_expert[morceau[m] as usize] {
                            self.modele.expert_pos(&self.noyaux, v, &pos, i, j, &self.calcul)?;
                        }
                        faits += 1;
                    }
                }
                self.compteurs.flux_experts += morceau.len() as u64;
                if morceau.len() < demandes.len() {
                    // Paquet suivant : les GEMV de celui-ci doivent avoir lu leurs emplacements avant
                    // qu'une éviction ne les rende au décodeur.
                    self.calcul.synchroniser()?;
                }
                self.cache.liberer(l as u16);
            }
            for i in 0..n {
                self.modele.combiner_pos(&self.noyaux, &pos, i, &self.calcul)?;
            }
            if self.config.battement {
                eprintln!(
                    "troncons : préremplissage par flux, couche {}/{l_n} ({:.1} s ; {} lectures de tronçons ; {} conflits d'arrivée évités)",
                    l + 1,
                    t_pas.elapsed().as_secs_f64(),
                    self.compteurs.lectures_troncons,
                    self.compteurs.flux_conflits_evites
                );
            }
        }
        // Garde (M1) : tous les tronçons lus sont vérifiés avant la première sortie.
        self.garde.attendre_tout()?;
        // Sorties : chaque position si on demande ses logits, sinon la dernière seule.
        let vocab = h.vocab;
        let premiere = if logits.is_some() { 0 } else { n - 1 };
        let mut z = vec![0f32; vocab];
        let mut suivant = 0u32;
        for i in premiere..n {
            self.modele.reprendre_pos(&pos, i, &self.calcul)?;
            self.modele.sortie(&self.noyaux, &self.calcul)?;
            copier_vers_hote(&mut self.sortie_hote, 0, self.modele.jeton(), &self.calcul)?;
            if logits.is_some() {
                copier_vers_hote(&mut self.sortie_hote, 4096, self.modele.logits(), &self.calcul)?;
            }
            self.calcul.synchroniser()?;
            suivant = u32::from_le_bytes(self.sortie_hote.tranche()[0..4].try_into().unwrap());
            if let Some(f) = logits.as_mut() {
                for (q, c) in self.sortie_hote.tranche()[4096..4096 + 4 * vocab].chunks_exact(4).enumerate() {
                    z[q] = f32::from_le_bytes(c.try_into().unwrap());
                }
                f(i, &z)?;
            }
        }
        self.decodage.synchroniser()?;
        self.verifier_controles_flux()?;
        let _ = d;
        self.compteurs.flux_positions += n as u64;
        self.compteurs.s_pas += t_pas.elapsed().as_secs_f64();
        Ok(suivant)
    }

    /// Copie et décodage d'un défaut du préremplissage par flux : comme `envoyer_et_decoder`, avec un
    /// tampon de contrôle par tampon d'arrivée (les contrôles sont vérifiés à la fin de chaque
    /// paquet de lectures qui réutilise le tampon, et à la fin du préremplissage).
    fn envoyer_et_decoder_flux(&mut self, l: usize, df: &Defaut, expert: u16) -> Result<()> {
        let i = df.arrivee;
        let k = self.modele.h.actifs;
        // Le tampon de contrôle de l'arrivée i a peut-être servi : on vérifie l'ancien avant d'écraser.
        if let Some(prec) = self.flux_controle[i].take() {
            self.ev_dec[i].attendre()?;
            self.verifier_un_controle(i, prec)?;
        }
        let n_copie = df.entree.longueur_jusqua(1) as usize;
        let arr = self.arrivee_carte.vue(i * self.lal, n_copie);
        let empl = self.emplacements.vue(df.emplacement as usize * self.te, self.te);
        self.copie.attendre(&self.ev_dec[i])?;
        copier_vers_carte(arr, &self.arrivee_hote, df.decalage_hote, n_copie, &self.copie)?;
        self.ev_copie[i].enregistrer(&self.copie)?;
        self.compteurs.octets_dma += n_copie as u64;
        self.decodage.attendre(&self.ev_copie[i])?;
        // tampons de contrôle : on prend la zone (couche 0, j = i) … du tableau L · k × 16 o, assez grand
        // dès que n_arrivees ≤ L · k (vérifié à l'ouverture).
        let ctl = self.controle_carte.vue(i * 16, 16);
        self.controle_carte.remplir(ctl, 0, &self.decodage)?;
        let dims = self.modele.h.dims;
        if self.brut {
            self.noyaux.copier_brut(arr, empl, &dims, ctl, &self.decodage)?;
        } else {
            let partie = &self.arrivee_hote.tranche()[df.decalage_hote..df.decalage_hote + n_copie];
            let grilles = abi::grilles_depuis_partie(partie).map_err(|e| anyhow::anyhow!("couche {l}, expert {expert} : {e}"))?;
            let lv = self.luts.as_ref().unwrap().vue(l * abi::LUTS_PAR_COUCHE * 4, abi::LUTS_PAR_COUCHE * 4);
            self.noyaux.decoder_expert_grilles(arr, empl, lv, &dims, ctl, grilles, &self.decodage)?;
        }
        copier_vers_hote(&mut self.controle_hote, i * 16, ctl, &self.decodage)?;
        self.ev_dec[i].enregistrer(&self.decodage)?;
        self.calcul.attendre(&self.ev_dec[i])?;
        self.flux_controle[i] = Some((l as u16, expert));
        self.compteurs.experts_decodes += 1;
        let _ = k;
        if let Some(retour) = self.retour.as_mut() {
            copier_vers_hote(retour, 0, empl, &self.decodage)?;
            self.decodage.synchroniser()?;
            let e = empreinte_emplacement(&retour.tranche()[..self.te], &dims);
            let attendue = df.entree.empreinte_du_decode(self.canonique);
            if e != attendue {
                bail!("témoin : couche {l}, expert {expert} : empreinte {e:016x} au lieu de {attendue:016x}");
            }
            self.compteurs.experts_verifies += 1;
        }
        Ok(())
    }

    fn verifier_un_controle(&self, i: usize, (couche, expert): (u16, u16)) -> Result<()> {
        let ctl = self.controle_hote.tranche();
        let w = |q: usize| u32::from_le_bytes(ctl[i * 16 + 4 * q..i * 16 + 4 * q + 4].try_into().unwrap());
        if w(0) != 0 || w(1) != 0 || w(2) != 0 {
            bail!("couche {couche}, expert {expert} : décodage faux ({} voies hors de L, {} erreurs de format, {} pointeurs de tuile faux)", w(0), w(1), w(2));
        }
        Ok(())
    }

    fn verifier_controles_flux(&mut self) -> Result<()> {
        for i in 0..self.flux_controle.len() {
            if let Some(c) = self.flux_controle[i].take() {
                self.verifier_un_controle(i, c)?;
            }
        }
        Ok(())
    }

    /// Un pas de décodage glouton : `jeton` à `position`. Rend le jeton suivant (argmax) ; écrit les
    /// logits f32 dans `logits` si on les demande.
    pub fn pas(&mut self, jeton: u32, position: u32, logits: Option<&mut [f32]>) -> Result<u32> {
        let t_pas = Instant::now();
        let h = self.modele.h.clone();
        let (l_n, k) = (h.couches, h.actifs);
        let pas = self.compteurs.pas;
        if self.config.chronogramme {
            self.ev_base.enregistrer(&self.calcul)?;
        }
        self.decodes_du_pas.clear();

        // 1. La ligne d'enchâssement (§ 4.5).
        let (abs, ol) = self.modele.ligne_enchassement(jeton)?;
        let ligne = self.modele.tampon_ligne();
        if let Some((ram, base)) = &self.enchassement_ram {
            let dans = (abs - base) as usize;
            copier_vers_carte(ligne.vue_debut(ol as usize), ram, dans, ol as usize, &self.calcul)?;
            self.modele.enchasser(&self.noyaux, ligne.vue_debut(ol as usize), &self.calcul)?;
        } else {
            let a0 = abs & !(ALIGNEMENT - 1);
            let n = (2 * ALIGNEMENT).min(self.lecteur.taille() - a0) as u32;
            let dest = self.ligne_hote.pointeur();
            self.lire_sync(JETON_LIGNE, a0, n, dest)?;
            self.garder_ligne(jeton, (abs - a0) as usize, ol as usize)?;
            copier_vers_carte(ligne, &self.ligne_hote, 0, n as usize, &self.calcul)?;
            let dans = abs - a0;
            self.modele.enchasser(&self.noyaux, VueCarte { adresse: ligne.adresse + dans, octets: ol as usize }, &self.calcul)?;
            self.compteurs.octets_lus_enchassement += n as u64;
            self.compteurs.lectures_enchassement += 1;
        }

        // 2. Les couches.
        let carte_boite = self.boite.adresse_carte().context("boîte aux lettres non projetée")?;
        for l in 0..l_n {
            self.sequence = self.sequence.wrapping_add(1).max(1);
            let seq = self.sequence;
            if let Some(beta) = self.config.biais_cache {
                // P3 : β sur chaque expert de la couche l déjà en VRAM juste avant `demander(l, …)` (le
                // contenu du cache après la couche l − 1 de ce pas, causal), monté sur la carte avant le routeur.
                let hote = self.biais_hote.as_mut().context("biais_cache sans tampon de biais")?;
                let octets = hote.tranche_mut();
                for e in 0..h.experts {
                    let b = if self.cache.emplacement_de((l as u16, e as u16)).is_some() { beta } else { 0.0f32 };
                    octets[4 * e..4 * e + 4].copy_from_slice(&b.to_le_bytes());
                }
                let carte = self.biais_carte.as_ref().context("biais_cache sans vecteur de biais sur la carte")?;
                copier_vers_carte(carte.tout(), &*hote, 0, 4 * h.experts, &self.calcul)?;
                self.modele.debut_couche_biais(&self.noyaux, l, position, carte_boite, seq, Some(carte.tout()), &self.calcul)?;
            } else {
                self.modele.debut_couche(&self.noyaux, l, position, carte_boite, seq, &self.calcul)?;
            }
            let predire = self.config.prechargement && l + 1 < l_n;
            if predire {
                self.modele.predire(&self.noyaux, l + 1, carte_boite + 256, seq, &self.calcul)?;
            }
            self.ev_routeur.enregistrer(&self.calcul)?;
            if self.config.chronogramme {
                self.ev_couche[l][0].enregistrer(&self.calcul)?;
            }
            // Variante « evenement » de l'essai E0 c du lot E (la plus rapide sous charge,
            // 18,5 µs par synchronisation) : on attend l'événement, puis on lit la boîte.
            let t0 = Instant::now();
            self.ev_routeur.attendre()?;
            let lu = self.boite.lire_volatil_u32(0);
            if lu != seq {
                bail!("couche {l} : boîte aux lettres à la séquence {lu}, {seq} attendue (routeur non écrit)");
            }
            let mut experts = [0u16; 8];
            for i in 0..k {
                let x = self.boite.lire_volatil_u32(4 * (1 + i));
                if x as usize >= h.experts {
                    bail!("couche {l} : expert {x} hors de [0, {})", h.experts);
                }
                experts[i] = x as u16;
            }
            let mut predits = [0u16; 8];
            if predire {
                if self.boite.lire_volatil_u32(256) != seq {
                    bail!("couche {l} : boîte de prédiction à une séquence fausse");
                }
                for i in 0..k {
                    predits[i] = self.boite.lire_volatil_u32(256 + 4 * (1 + i)) as u16;
                }
            }
            self.compteurs.s_attente_routeur += t0.elapsed().as_secs_f64();
            self.trace.extend_from_slice(&experts[..k]);
            let decisions = self.cache.demander(l as u16, &experts[..k], pas * l_n as u64 + l as u64);
            let mut vues = [VueCarte { adresse: 0, octets: 0 }; 8];
            let mut defauts: Vec<Defaut> = Vec::with_capacity(k);
            for (j, d) in decisions.iter().enumerate() {
                let (empl, tiede, deja) = match *d {
                    Decision::Succes { emplacement } => {
                        vues[j] = self.emplacements.vue(emplacement as usize * self.te, self.te);
                        continue;
                    }
                    Decision::DefautRam { emplacement, tiede } => (emplacement, Some(tiede), true),
                    Decision::DefautDisque { emplacement, tiede } => (emplacement, tiede, false),
                };
                vues[j] = self.emplacements.vue(empl as usize * self.te, self.te);
                let entree = *self.fichier.entree(l as u16, experts[j]);
                let arrivee = (l % self.config.couches_d_avance) * k + j;
                // Un tronçon lu d'avance pour cette couche (préchargement, mode A0 seulement).
                let pf = if tiede.is_none() && self.config.prechargement {
                    let ens = l % 2;
                    (ens * k..(ens + 1) * k).find(|&s| self.pf[s].id == Some((l as u16, experts[j])))
                } else {
                    None
                };
                let (source, dec_hote) = match (tiede, pf) {
                    (Some(r), _) => (1u8, r as usize * self.lal),
                    (None, Some(s)) => (2u8, s * self.lal),
                    (None, None) => (0u8, arrivee * self.lal),
                };
                let lu = deja || pf.is_some_and(|s| !self.pf[s].en_vol);
                if pf.is_some() {
                    self.compteurs.pf_utiles += 1;
                }
                defauts.push(Defaut { j, emplacement: empl, entree, source, decalage_hote: dec_hote, arrivee, lu, ram: deja, pf, soumis: 0.0, lu_ms: 0.0 });
            }
            // Les lectures des défauts disque, toutes soumises d'un coup (au plus k).
            let t_es = Instant::now();
            let mut en_vol = 0usize;
            for (n, df) in defauts.iter_mut().enumerate() {
                if df.lu || df.pf.is_some() {
                    continue;
                }
                // Le tampon épinglé a fini sa copie précédente (sûr par l'ordre ; attente gratuite).
                if df.source == 0 {
                    self.ev_copie[df.arrivee].attendre()?;
                }
                let long = (self.config.longueur_lecture.map_or(df.entree.longueur_jusqua(1), |x| x as u64)).min(self.lecteur.taille() - df.entree.decalage);
                let base = if df.source == 1 { self.tiede.as_ref().unwrap().pointeur() } else { self.arrivee_hote.pointeur() };
                // SAFETY : décalage dans le tampon (entrée ou arrivée, chacune de `lal` octets).
                let dest = unsafe { base.add(df.decalage_hote) };
                self.soumettre(Requete { jeton: n as u64, decalage: df.entree.decalage, longueur: long as u32, destination: dest })?;
                df.soumis = t_pas.elapsed().as_secs_f64() * 1e3;
                self.compteurs.octets_lus_troncons += long;
                self.compteurs.lectures_troncons += 1;
                en_vol += 1;
            }
            // Les lectures anticipées de la couche ℓ + 1 (après celles de ℓ, qui passent devant).
            if predire {
                let ens = (l + 1) % 2;
                self.vider_ensemble(ens)?;
                for (i, &e) in predits[..k].iter().enumerate() {
                    let s = ens * k + i;
                    self.pf[s] = Prechargement::default();
                    let id = ((l + 1) as u16, e);
                    if e as usize >= h.experts || self.cache.emplacement_de(id).is_some() || self.cache.tiede_de(id).is_some() {
                        continue;
                    }
                    let en = *self.fichier.entree(id.0, id.1);
                    let long = (self.config.longueur_lecture.map_or(en.longueur_jusqua(1), |x| x as u64)).min(self.lecteur.taille() - en.decalage);
                    // SAFETY : tampon s de `lal` octets dans les tampons de préchargement.
                    let dest = unsafe { self.pf_hote.as_ref().unwrap().pointeur().add(s * self.lal) };
                    self.soumettre(Requete { jeton: JETON_PF + s as u64, decalage: en.decalage, longueur: long as u32, destination: dest })?;
                    self.pf[s] = Prechargement { id: Some(id), en_vol: true };
                    self.compteurs.pf_emis += 1;
                    self.compteurs.pf_octets += long;
                    self.compteurs.octets_lus_troncons += long;
                    self.compteurs.lectures_troncons += 1;
                }
            }
            // Chaque défaut prêt (lu, ou déjà en RAM) part vers la carte dès qu'il l'est.
            let mut a: Vec<Achevement> = Vec::new();
            let mut partis = vec![false; defauts.len()];
            loop {
                for n in 0..defauts.len() {
                    if let Some(s) = defauts[n].pf
                        && !defauts[n].lu
                        && !self.pf[s].en_vol
                    {
                        defauts[n].lu = true;
                        defauts[n].lu_ms = t_pas.elapsed().as_secs_f64() * 1e3;
                    }
                    if defauts[n].lu && !partis[n] {
                        self.envoyer_et_decoder(l, &defauts[n], experts[defauts[n].j])?;
                        partis[n] = true;
                    }
                }
                let attend_pf = defauts.iter().any(|d| !d.lu && d.pf.is_some());
                if en_vol == 0 && !attend_pf {
                    break;
                }
                a.clear();
                self.recolter_route(&mut a)?;
                for x in &a {
                    let df = &mut defauts[x.jeton as usize];
                    if let Some(e) = x.erreur {
                        bail!("couche {l}, expert {} : lecture du tronçon, erreur Windows {e}", experts[df.j]);
                    }
                    df.lu = true;
                    df.lu_ms = t_pas.elapsed().as_secs_f64() * 1e3;
                    en_vol -= 1;
                    let (en, ex, dh, src) = (df.entree, experts[df.j], df.decalage_hote, df.source);
                    let base = if src == 1 { self.tiede.as_ref().unwrap().pointeur() } else { self.arrivee_hote.pointeur() };
                    // SAFETY : décalage dans le tampon (entrée tiède ou arrivée, chacune de `lal` octets).
                    let adr = unsafe { base.add(dh) };
                    self.apres_lecture(adr, &en, x.octets, l as u16, ex)?;
                }
            }
            if defauts.iter().any(|d| !d.lu) || partis.iter().any(|p| !p) {
                bail!("couche {l} : défaut non servi");
            }
            if !defauts.is_empty() {
                self.compteurs.s_lectures += t_es.elapsed().as_secs_f64();
            }
            for df in &defauts {
                self.cache.pret(df.emplacement);
            }
            self.modele.fin_couche(&self.noyaux, &vues[..k], &self.calcul)?;
            if self.config.chronogramme {
                self.ev_couche[l][1].enregistrer(&self.calcul)?;
            }
            self.cache.liberer(l as u16);
        }

        // 3. La sortie.
        let t_fin = Instant::now();
        self.modele.sortie(&self.noyaux, &self.calcul)?;
        let vocab = h.vocab;
        copier_vers_hote(&mut self.sortie_hote, 0, self.modele.jeton(), &self.calcul)?;
        if logits.is_some() {
            copier_vers_hote(&mut self.sortie_hote, 4096, self.modele.logits(), &self.calcul)?;
        }
        self.calcul.synchroniser()?;
        self.decodage.synchroniser()?;
        // Garde (M1) : tous les tronçons lus pendant ce pas sont vérifiés avant d'en rendre le jeton.
        self.garde.attendre_tout()?;
        self.compteurs.s_fin_jeton += t_fin.elapsed().as_secs_f64();
        let suivant = u32::from_le_bytes(self.sortie_hote.tranche()[0..4].try_into().unwrap());
        if let Some(z) = logits {
            if z.len() != vocab {
                bail!("{} logits demandés, vocabulaire de {vocab}", z.len());
            }
            for (i, c) in self.sortie_hote.tranche()[4096..4096 + 4 * vocab].chunks_exact(4).enumerate() {
                z[i] = f32::from_le_bytes(c.try_into().unwrap());
            }
        }
        // 4. Les contrôles de la carte (§ 4.12) : toute voie hors de L est une erreur fatale nommée.
        let ctl = self.controle_hote.tranche();
        for &(couche, j, expert) in &self.decodes_du_pas {
            let o = (couche as usize * k + j) * 16;
            let w = |i: usize| u32::from_le_bytes(ctl[o + 4 * i..o + 4 * i + 4].try_into().unwrap());
            if w(0) != 0 || w(1) != 0 || w(2) != 0 {
                bail!("couche {couche}, expert {expert} : décodage faux ({} voies hors de L, {} erreurs de format, {} pointeurs de tuile faux)", w(0), w(1), w(2));
            }
        }
        // 5. Les temps de carte des défauts (événements horodatés, lus après la synchronisation).
        let mut i_date = if self.config.chronogramme { self.dates.len() - self.decodes_du_pas.len() } else { 0 };
        for &(couche, j, _) in &self.decodes_du_pas {
            let ev = &self.ev_temps[couche as usize * k + j];
            let cp = ev[1].ms_depuis(&ev[0])? as f64;
            let dc = ev[3].ms_depuis(&ev[2])? as f64;
            self.compteurs.ms_copie += cp;
            self.compteurs.ms_decodage += dc;
            if self.config.chronogramme {
                let b = &self.ev_base;
                let d = &mut self.dates[i_date];
                d.copie_debut_ms = ev[0].ms_depuis(b)?;
                d.copie_fin_ms = ev[1].ms_depuis(b)?;
                d.dec_debut_ms = ev[2].ms_depuis(b)?;
                d.dec_fin_ms = ev[3].ms_depuis(b)?;
                d.routeur_ms = self.ev_couche[couche as usize][0].ms_depuis(b)?;
                d.fin_couche_ms = self.ev_couche[couche as usize][1].ms_depuis(b)?;
                i_date += 1;
            }
        }
        self.compteurs.pas += 1;
        self.compteurs.s_pas += t_pas.elapsed().as_secs_f64();
        Ok(suivant)
    }

    /// Copie le tronçon d'un défaut vers son tampon d'arrivée en VRAM (flux de copie), le décode
    /// dans son emplacement (flux de décodage), et fait attendre le flux de calcul.
    fn envoyer_et_decoder(&mut self, l: usize, df: &Defaut, expert: u16) -> Result<()> {
        let h = &self.modele.h;
        let k = h.actifs;
        let i = df.arrivee;
        let n_copie = df.entree.longueur_jusqua(1) as usize;
        let arr = self.arrivee_carte.vue(i * self.lal, n_copie);
        let empl = self.emplacements.vue(df.emplacement as usize * self.te, self.te);
        let ev = &self.ev_temps[l * k + df.j];
        // copie : attend que le décodage précédent depuis ce tampon VRAM soit fini
        self.copie.attendre(&self.ev_dec[i])?;
        ev[0].enregistrer(&self.copie)?;
        let src = match df.source {
            1 => self.tiede.as_ref().unwrap(),
            2 => self.pf_hote.as_ref().unwrap(),
            _ => &self.arrivee_hote,
        };
        copier_vers_carte(arr, src, df.decalage_hote, n_copie, &self.copie)?;
        ev[1].enregistrer(&self.copie)?;
        self.ev_copie[i].enregistrer(&self.copie)?;
        self.compteurs.octets_dma += n_copie as u64;
        // décodage
        self.decodage.attendre(&self.ev_copie[i])?;
        ev[2].enregistrer(&self.decodage)?;
        let ctl = self.controle_carte.vue((l * k + df.j) * 16, 16);
        self.controle_carte.remplir(ctl, 0, &self.decodage)?;
        let dims = h.dims;
        if self.brut {
            self.noyaux.copier_brut(arr, empl, &dims, ctl, &self.decodage)?;
        } else {
            let partie = &src.tranche()[df.decalage_hote..df.decalage_hote + n_copie];
            let grilles = abi::grilles_depuis_partie(partie).map_err(|e| anyhow::anyhow!("couche {l}, expert {expert} : {e}"))?;
            let luts = self.luts.as_ref().unwrap();
            let lv = luts.vue(l * abi::LUTS_PAR_COUCHE * 4, abi::LUTS_PAR_COUCHE * 4);
            self.noyaux.decoder_expert_grilles(arr, empl, lv, &dims, ctl, grilles, &self.decodage)?;
        }
        copier_vers_hote(&mut self.controle_hote, (l * k + df.j) * 16, ctl, &self.decodage)?;
        ev[3].enregistrer(&self.decodage)?;
        self.ev_dec[i].enregistrer(&self.decodage)?;
        self.calcul.attendre(&self.ev_dec[i])?;
        self.decodes_du_pas.push((l as u16, df.j, expert));
        self.compteurs.experts_decodes += 1;
        if self.config.chronogramme {
            // Dans l'ordre de `decodes_du_pas` : les dates de carte s'y rangent à la fin du pas.
            self.dates.push(Date {
                pas: self.compteurs.pas,
                couche: l as u16,
                expert,
                source: if df.ram { "ram" } else { "disque" },
                soumis_ms: df.soumis,
                lu_ms: df.lu_ms,
                copie_debut_ms: 0.0,
                copie_fin_ms: 0.0,
                dec_debut_ms: 0.0,
                dec_fin_ms: 0.0,
                routeur_ms: 0.0,
                fin_couche_ms: 0.0,
            });
        }
        if let Some(retour) = self.retour.as_mut() {
            // Mode témoin (§ 4.12) : l'expert redescend et son empreinte d'origine (canonique en
            // v1.2) est refaite.
            copier_vers_hote(retour, 0, empl, &self.decodage)?;
            self.decodage.synchroniser()?;
            let e = empreinte_emplacement(&retour.tranche()[..self.te], &dims);
            let attendue = df.entree.empreinte_du_decode(self.canonique);
            if e != attendue {
                bail!("témoin : couche {l}, expert {expert} : empreinte {e:016x} au lieu de {attendue:016x}");
            }
            self.compteurs.experts_verifies += 1;
        }
        Ok(())
    }
}

/// Garde (M1) : les empreintes de chaque ligne de `token_embd`, lu une fois par morceaux dans
/// `tampon` (la fenêtre d'arrivée), et son empreinte entière vérifiée contre la table des résidents.
/// Rend (empreintes, octets lus).
fn table_des_lignes(lecteur: &Lecteur, m: &Modele, tampon: &HoteEpingle) -> Result<(Vec<u64>, u64)> {
    let (t, abs) = m.tenseur_enchassement();
    let ol = m.h.octets_ligne_enchassement() as usize;
    if t.octets as usize != ol * m.h.vocab {
        bail!("token_embd : {} octets pour {} lignes de {ol}", t.octets, m.h.vocab);
    }
    let a0 = abs & !(ALIGNEMENT - 1);
    let fin = ((abs + t.octets + ALIGNEMENT - 1) & !(ALIGNEMENT - 1)).min(lecteur.taille());
    let cap = (tampon.octets() as u64) & !(ALIGNEMENT - 1);
    if cap == 0 {
        bail!("garde : fenêtre d'arrivée vide");
    }
    let par_requete = 16u64 << 20;
    let mut l = LignesEnConstruction::nouvelles(ol, m.h.vocab);
    let (mut x, mut lus) = (a0, 0u64);
    let mut a: Vec<Achevement> = Vec::new();
    while x < fin {
        let n = (fin - x).min(cap);
        let mut y = 0u64;
        while y < n {
            let lg = (n - y).min(par_requete);
            // SAFETY : dans le tampon de `cap` octets.
            let dest = unsafe { tampon.pointeur().add(y as usize) };
            lecteur.soumettre(Requete { jeton: y, decalage: x + y, longueur: lg as u32, destination: dest }).map_err(es)?;
            y += lg;
        }
        a.clear();
        while lecteur.en_vol() > 0 {
            lecteur.recolter(u32::MAX, &mut a).map_err(es)?;
        }
        if let Some(e) = a.iter().find(|e| e.erreur.is_some()) {
            bail!("garde : lecture de token_embd : erreur Windows {:?}", e.erreur);
        }
        let livres: u64 = a.iter().map(|e| e.octets as u64).sum();
        if livres != n {
            bail!("garde : lecture de token_embd : {livres} octets livrés sur {n}");
        }
        lus += n;
        let o = tampon.tranche();
        let debut = abs.saturating_sub(x) as usize;
        let fin_utile = ((abs + t.octets).min(x + n) - x) as usize;
        if debut < fin_utile {
            l.ajouter(&o[debut..fin_utile], FILS_GARDE);
        }
        x += n;
    }
    let (v, e) = l.finir()?;
    if e != t.empreinte {
        bail!("garde : token_embd : empreinte {e:016x} au lieu de {:016x}", t.empreinte);
    }
    if v.len() != m.h.vocab {
        bail!("garde : {} lignes hachées pour {}", v.len(), m.h.vocab);
    }
    Ok((v, lus))
}

/// Témoin de la garde : retourne le bit 0 du premier octet du premier flux brut (MEDIANES ou BIAIS)
/// d'une partie de tronçon (§ 4.8 : table des flux à partir de l'octet 64, 16 o par flux).
fn casser_premier_flux_brut(o: &mut [u8]) {
    let n_flux = u16::from_le_bytes([o[10], o[11]]) as usize;
    for i in 0..n_flux {
        let d = 64 + 16 * i;
        if o[d] == Sorte::Medianes as u8 || o[d] == Sorte::Biais as u8 {
            let dec = u32::from_le_bytes(o[d + 4..d + 8].try_into().unwrap()) as usize;
            o[dec] ^= 1;
            return;
        }
    }
}

/// `token_embd` entier en mémoire épinglée (mode `--enchassement-en-ram`), lu sans tampon.
fn charger_enchassement(ctx: &Contexte, lecteur: &Lecteur, m: &Modele) -> Result<(HoteEpingle, u64)> {
    let (t, abs) = m.tenseur_enchassement();
    let a0 = abs & !(ALIGNEMENT - 1);
    let fin = ((abs + t.octets + ALIGNEMENT - 1) & !(ALIGNEMENT - 1)).min(lecteur.taille());
    let n = (fin - a0) as usize;
    let tampon = HoteEpingle::allouer(ctx, n, false)?;
    let morceau = 16usize << 20;
    let mut a: Vec<Achevement> = Vec::new();
    let mut x = 0usize;
    while x < n {
        let lg = (n - x).min(morceau);
        // SAFETY : dans le tampon de n octets.
        lecteur.soumettre(Requete { jeton: x as u64, decalage: a0 + x as u64, longueur: lg as u32, destination: unsafe { tampon.pointeur().add(x) } }).map_err(es)?;
        x += lg;
    }
    while lecteur.en_vol() > 0 {
        lecteur.recolter(u32::MAX, &mut a).map_err(es)?;
    }
    if let Some(e) = a.iter().find(|e| e.erreur.is_some()) {
        bail!("lecture de token_embd : erreur Windows {:?}", e.erreur);
    }
    let e = trc_format::empreinte64(&tampon.tranche()[(abs - a0) as usize..(abs - a0 + t.octets) as usize]);
    if e != t.empreinte {
        bail!("token_embd : empreinte {e:016x} au lieu de {:016x}", t.empreinte);
    }
    Ok((tampon, a0))
}

/// Une vue raccourcie à ses `n` premiers octets.
trait VueDebut {
    fn vue_debut(&self, n: usize) -> VueCarte;
}
impl VueDebut for VueCarte {
    fn vue_debut(&self, n: usize) -> VueCarte {
        VueCarte { adresse: self.adresse, octets: n.min(self.octets) }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empreinte_d_un_emplacement_synthetique() {
        // Un petit expert : 3 matrices de 2 × 64 ; l'empreinte refaite depuis le SoA doit égaler
        // celle des octets d'origine écrits à la main (§ 4.11).
        let d = DimsExpert { lignes: [2, 2, 2], colonnes: [64, 64, 64] };
        let mut empl = vec![0u8; d.taille_emplacement() as usize];
        let mut origine: Vec<u8> = Vec::new();
        let mut biais: Vec<u8> = Vec::new();
        for j in 0..3 {
            let disp = d.disposition(j);
            for beta in 0..d.blocs(j) as usize {
                let e = (j * 10 + beta) as u8;
                empl[(disp.base + disp.echelles) as usize + beta] = e;
                origine.push(e);
                for q in 0..16 {
                    let v = (j * 31 + beta * 7 + q) as u8;
                    empl[disp.base as usize + 16 * beta + q] = v;
                    origine.push(v);
                }
            }
            for r in 0..2 {
                let b = ((j * 2 + r) as f32 + 0.5).to_le_bytes();
                empl[(disp.base + disp.biais) as usize + 4 * r..(disp.base + disp.biais) as usize + 4 * r + 4].copy_from_slice(&b);
                biais.extend_from_slice(&b);
            }
        }
        origine.extend_from_slice(&biais);
        assert_eq!(empreinte_emplacement(&empl, &d), trc_format::empreinte64(&origine));
        // Cassure : un octet de code changé.
        empl[3] ^= 1;
        assert_ne!(empreinte_emplacement(&empl, &d), trc_format::empreinte64(&origine));
    }
}
