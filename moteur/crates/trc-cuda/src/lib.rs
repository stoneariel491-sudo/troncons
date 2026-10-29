//! `trc-cuda` : l'API du pilote CUDA, enveloppée à la main (couture C, ARCHITECTURE.md § 5.5).
//!
//! Aucune autre crate du moteur n'appelle `nvcuda.dll`. Le pilote est chargé à l'exécution
//! (`LoadLibraryExW` dans System32) ; rien de CUDA n'est lié à la construction.
//!
//! **Le contexte.** On prend le *contexte primaire* de la carte (`cuDevicePrimaryCtxRetain`), celui
//! que partagent toutes les bibliothèques d'un processus, plutôt que `cuCtxCreate` (devenu
//! `cuCtxCreate_v4` en CUDA 13, avec une structure de paramètres) : un seul contexte par carte et par
//! processus, et un appel qui n'a pas changé depuis CUDA 7. L'API du pilote attache un contexte
//! « courant » à chaque fil ; chaque objet le rend courant au besoin avant d'appeler le pilote
//! (une lecture d'une variable locale au fil quand il l'est déjà).
//!
//! **Les durées de vie.** Chaque objet (flux, événement, mémoire, module) garde une référence comptée
//! sur le contexte : le contexte primaire n'est relâché qu'après le dernier objet, quel que soit
//! l'ordre dans lequel l'appelant les abandonne. Une fonction garde de même son module.
//!
//! **Ce que le type ne garantit pas.** Les copies et les lancements sont asynchrones : une tranche
//! de mémoire épinglée rendue par [`HoteEpingle::tranche`] peut être en cours d'écriture par la carte
//! ou par une lecture de disque. L'appelant ordonne ses accès par les événements et les flux ; c'est le
//! contrat de l'API gelée (§ 5.5), dit ici pour qu'il ne se devine pas.

mod api;

use std::cell::Cell;
use std::ffi::{CStr, c_char, c_int, c_uint, c_void};
use std::fmt;
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};

use api::*;

/// L'erreur de `trc-cuda`.
#[derive(Debug, Clone)]
pub enum Erreur {
    /// `nvcuda.dll` absent, incomplet, ou `cuInit` refusé.
    Pilote(String),
    /// Un appel du pilote a rendu un code d'erreur.
    Cuda { appel: &'static str, code: i32, nom: String, texte: String },
    /// Un usage hors contrat (taille nulle, débordement, alignement…), détecté avant le pilote.
    Usage(String),
}

impl fmt::Display for Erreur {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Erreur::Pilote(m) => write!(f, "pilote CUDA : {m}"),
            Erreur::Cuda { appel, code, nom, texte } => write!(f, "{appel} : {nom} ({code}) : {texte}"),
            Erreur::Usage(m) => write!(f, "usage de trc-cuda : {m}"),
        }
    }
}

impl std::error::Error for Erreur {}

pub type Result<T> = std::result::Result<T, Erreur>;

fn table() -> Result<&'static Api> {
    api().map_err(Erreur::Pilote)
}

/// Transforme un code du pilote en `Result`, avec le nom et le texte que le pilote en donne.
fn verifier(a: &Api, appel: &'static str, r: CuResult) -> Result<()> {
    if r == CUDA_SUCCESS {
        return Ok(());
    }
    let mut nom: *const c_char = std::ptr::null();
    let mut texte: *const c_char = std::ptr::null();
    // SAFETY : le pilote rend des chaînes statiques terminées par un zéro, ou laisse null.
    let lire = |p: *const c_char| {
        if p.is_null() { String::from("?") } else { unsafe { CStr::from_ptr(p) }.to_string_lossy().into_owned() }
    };
    unsafe {
        (a.cuGetErrorName)(r, &mut nom);
        (a.cuGetErrorString)(r, &mut texte);
    }
    Err(Erreur::Cuda { appel, code: r, nom: lire(nom), texte: lire(texte) })
}

fn usage<T>(m: impl Into<String>) -> Result<T> {
    Err(Erreur::Usage(m.into()))
}

// ---------------------------------------------------------------------------------------------
// Contexte
// ---------------------------------------------------------------------------------------------

/// Comment le fil hôte attend la carte dans `cuEventSynchronize` et `cuStreamSynchronize`
/// (drapeaux `CU_CTX_SCHED_*` du contexte primaire). Extension de la couture C : l'essai E0(c)
/// mesure ce que coûte chaque mode.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Attente {
    /// `CU_CTX_SCHED_AUTO` : le pilote choisit (attente active si plus de cœurs que de cartes).
    Auto,
    /// `CU_CTX_SCHED_SPIN` : attente active, latence la plus courte, un cœur occupé.
    Active,
    /// `CU_CTX_SCHED_YIELD` : attente active qui cède le fil.
    Cede,
    /// `CU_CTX_SCHED_BLOCKING_SYNC` : le fil dort sur une primitive du système.
    Bloquante,
}

impl Attente {
    fn drapeaux(self) -> c_uint {
        match self {
            Attente::Auto => 0x00,
            Attente::Active => 0x01,
            Attente::Cede => 0x02,
            Attente::Bloquante => 0x04,
        }
    }
}

static GENERATION: AtomicU64 = AtomicU64::new(1);

thread_local! {
    /// (adresse du contexte, génération) rendu courant sur ce fil.
    static COURANT: Cell<(usize, u64)> = const { Cell::new((0, 0)) };
}

struct Interne {
    a: &'static Api,
    dev: CuDevice,
    ctx: Poignee,
    generation: u64,
    nom: String,
    drapeaux_effectifs: c_uint,
}

// Les poignées du pilote se partagent entre fils (l'API du pilote est sûre entre fils).
unsafe impl Send for Interne {}
unsafe impl Sync for Interne {}

impl Interne {
    /// Rend ce contexte courant sur le fil appelant, s'il ne l'est pas déjà.
    fn courant(&self) -> Result<()> {
        let cle = (self.ctx as usize, self.generation);
        if COURANT.with(|c| c.get()) != cle {
            // SAFETY : contexte retenu tant que `self` vit.
            verifier(self.a, "cuCtxSetCurrent", unsafe { (self.a.cuCtxSetCurrent)(self.ctx) })?;
            COURANT.with(|c| c.set(cle));
        }
        Ok(())
    }
}

impl Drop for Interne {
    fn drop(&mut self) {
        // SAFETY : chaque objet qui dépend du contexte tient un Arc ; nous sommes le dernier.
        unsafe { (self.a.cuDevicePrimaryCtxRelease)(self.dev) };
        COURANT.with(|c| {
            if c.get().1 == self.generation {
                c.set((0, 0));
            }
        });
    }
}

/// Le contexte primaire d'une carte.
#[derive(Clone)]
pub struct Contexte {
    i: Arc<Interne>,
}

impl Contexte {
    /// Prend le contexte primaire de la carte `ordinal`, mode d'attente choisi par le pilote.
    pub fn nouveau(ordinal: u32) -> Result<Self> {
        Self::nouveau_avec(ordinal, Attente::Auto)
    }

    /// Extension : choisit le mode d'attente du fil hôte. Si le contexte primaire est déjà actif
    /// dans le processus avec d'autres drapeaux, le pilote garde les siens ;
    /// [`Contexte::attente_effective`] dit lesquels.
    pub fn nouveau_avec(ordinal: u32, attente: Attente) -> Result<Self> {
        let a = table()?;
        let mut dev: CuDevice = 0;
        // SAFETY : pointeurs valides.
        verifier(a, "cuDeviceGet", unsafe { (a.cuDeviceGet)(&mut dev, ordinal as c_int) })?;
        let r = unsafe { (a.cuDevicePrimaryCtxSetFlags)(dev, attente.drapeaux()) };
        if r != CUDA_ERROR_PRIMARY_CONTEXT_ACTIVE {
            verifier(a, "cuDevicePrimaryCtxSetFlags_v2", r)?;
        }
        let mut ctx: Poignee = std::ptr::null_mut();
        verifier(a, "cuDevicePrimaryCtxRetain", unsafe { (a.cuDevicePrimaryCtxRetain)(&mut ctx, dev) })?;
        let mut drapeaux: c_uint = 0;
        let mut actif: c_int = 0;
        unsafe { (a.cuDevicePrimaryCtxGetState)(dev, &mut drapeaux, &mut actif) };
        let mut nom = [0 as c_char; 128];
        unsafe { (a.cuDeviceGetName)(nom.as_mut_ptr(), nom.len() as c_int, dev) };
        let nom = unsafe { CStr::from_ptr(nom.as_ptr()) }.to_string_lossy().into_owned();
        let i = Arc::new(Interne {
            a,
            dev,
            ctx,
            generation: GENERATION.fetch_add(1, Ordering::Relaxed),
            nom,
            drapeaux_effectifs: drapeaux,
        });
        i.courant()?;
        Ok(Contexte { i })
    }

    /// (octets libres, octets totaux) de la VRAM, selon `cuMemGetInfo`. Rend (0, 0) si le pilote
    /// refuse la requête (la signature gelée n'a pas de `Result`).
    pub fn memoire(&self) -> (u64, u64) {
        let (mut libre, mut totale) = (0usize, 0usize);
        if self.i.courant().is_err() {
            return (0, 0);
        }
        // SAFETY : pointeurs valides, contexte courant.
        let r = unsafe { (self.i.a.cuMemGetInfo)(&mut libre, &mut totale) };
        if r != CUDA_SUCCESS { (0, 0) } else { (libre as u64, totale as u64) }
    }

    /// Extension : le nom de la carte.
    pub fn nom(&self) -> &str {
        &self.i.nom
    }

    /// Extension : la version du pilote (13010 pour CUDA 13.1).
    pub fn version_pilote(&self) -> i32 {
        self.i.a.version_pilote
    }

    /// Extension : le mode d'attente que le contexte primaire a vraiment.
    pub fn attente_effective(&self) -> Attente {
        match self.i.drapeaux_effectifs & 0x07 {
            0x01 => Attente::Active,
            0x02 => Attente::Cede,
            0x04 => Attente::Bloquante,
            _ => Attente::Auto,
        }
    }

    /// Extension : un attribut de la carte (`CU_DEVICE_ATTRIBUTE_*`).
    pub fn attribut(&self, attribut: Attribut) -> Result<i32> {
        let mut v: c_int = 0;
        let a = self.i.a;
        verifier(a, "cuDeviceGetAttribute", unsafe { (a.cuDeviceGetAttribute)(&mut v, attribut.code(), self.i.dev) })?;
        Ok(v)
    }

    /// Extension : attend la fin de tout travail du contexte (`cuCtxSynchronize`).
    pub fn synchroniser(&self) -> Result<()> {
        self.i.courant()?;
        verifier(self.i.a, "cuCtxSynchronize", unsafe { (self.i.a.cuCtxSynchronize)() })
    }
}

/// Les attributs de la carte qu'on relève dans les journaux.
#[derive(Clone, Copy, Debug)]
pub enum Attribut {
    CapaciteMajeure,
    CapaciteMineure,
    MoteursDeCopie,
    ProjectionHote,
    AdressageUnifie,
    PiloteTcc,
}

impl Attribut {
    fn code(self) -> c_int {
        match self {
            Attribut::CapaciteMajeure => CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MAJOR,
            Attribut::CapaciteMineure => CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MINOR,
            Attribut::MoteursDeCopie => CU_DEVICE_ATTRIBUTE_ASYNC_ENGINE_COUNT,
            Attribut::ProjectionHote => CU_DEVICE_ATTRIBUTE_CAN_MAP_HOST_MEMORY,
            Attribut::AdressageUnifie => CU_DEVICE_ATTRIBUTE_UNIFIED_ADDRESSING,
            Attribut::PiloteTcc => CU_DEVICE_ATTRIBUTE_TCC_DRIVER,
        }
    }
}

// ---------------------------------------------------------------------------------------------
// Flux
// ---------------------------------------------------------------------------------------------

/// Un flux CUDA, non bloquant envers le flux par défaut (que le moteur n'utilise jamais).
pub struct Flux {
    i: Arc<Interne>,
    s: Poignee,
    priorite: i32,
}

unsafe impl Send for Flux {}
unsafe impl Sync for Flux {}

impl Flux {
    /// `priorite_haute` : la plus haute priorité que la carte donne (le flux de calcul, § 5.1) ;
    /// sinon la plus basse (copie, décodage).
    pub fn nouveau(c: &Contexte, priorite_haute: bool) -> Result<Self> {
        let i = c.i.clone();
        i.courant()?;
        let a = i.a;
        let (mut basse, mut haute) = (0 as c_int, 0 as c_int);
        verifier(a, "cuCtxGetStreamPriorityRange", unsafe { (a.cuCtxGetStreamPriorityRange)(&mut basse, &mut haute) })?;
        let priorite = if priorite_haute { haute } else { basse };
        let mut s: Poignee = std::ptr::null_mut();
        verifier(a, "cuStreamCreateWithPriority", unsafe {
            (a.cuStreamCreateWithPriority)(&mut s, CU_STREAM_NON_BLOCKING, priorite)
        })?;
        Ok(Flux { i, s, priorite })
    }

    /// Le travail soumis ensuite à ce flux attend que `e` soit atteint (sans bloquer l'hôte).
    pub fn attendre(&self, e: &Evenement) -> Result<()> {
        self.i.courant()?;
        verifier(self.i.a, "cuStreamWaitEvent", unsafe { (self.i.a.cuStreamWaitEvent)(self.s, e.e, 0) })
    }

    /// Bloque l'hôte jusqu'à la fin de tout le travail soumis à ce flux.
    pub fn synchroniser(&self) -> Result<()> {
        self.i.courant()?;
        verifier(self.i.a, "cuStreamSynchronize", unsafe { (self.i.a.cuStreamSynchronize)(self.s) })
    }

    /// Extension : vrai si tout le travail soumis est fini (`cuStreamQuery`, sans bloquer). Sous
    /// WDDM, cet appel pousse aussi vers la carte le travail que le pilote retient en tampon.
    pub fn fini(&self) -> Result<bool> {
        self.i.courant()?;
        let r = unsafe { (self.i.a.cuStreamQuery)(self.s) };
        if r == CUDA_ERROR_NOT_READY {
            return Ok(false);
        }
        verifier(self.i.a, "cuStreamQuery", r)?;
        Ok(true)
    }

    /// Extension : la priorité effective du flux (plus petit = plus prioritaire).
    pub fn priorite(&self) -> i32 {
        self.priorite
    }
}

impl Drop for Flux {
    fn drop(&mut self) {
        if self.i.courant().is_ok() {
            // SAFETY : flux créé par nous ; le pilote le détruit après son travail en cours.
            unsafe { (self.i.a.cuStreamDestroy)(self.s) };
        }
    }
}

// ---------------------------------------------------------------------------------------------
// Événements
// ---------------------------------------------------------------------------------------------

/// Un événement CUDA.
pub struct Evenement {
    i: Arc<Interne>,
    e: Poignee,
    horodate: bool,
}

unsafe impl Send for Evenement {}
unsafe impl Sync for Evenement {}

impl Evenement {
    /// `horodate` : l'événement garde l'heure de la carte (pour [`Evenement::ms_depuis`]) ; sans
    /// horodatage, il est plus léger (`CU_EVENT_DISABLE_TIMING`), c'est le cas des événements de
    /// synchronisation du moteur.
    pub fn nouveau(c: &Contexte, horodate: bool) -> Result<Self> {
        Self::creer(c, if horodate { CU_EVENT_DEFAULT } else { CU_EVENT_DISABLE_TIMING }, horodate)
    }

    /// Extension : un événement dont [`Evenement::attendre`] endort le fil hôte sur une primitive du
    /// système au lieu d'attendre activement (`CU_EVENT_BLOCKING_SYNC`), quel que soit le mode du
    /// contexte. Mesuré par E0(c).
    pub fn nouveau_bloquant(c: &Contexte, horodate: bool) -> Result<Self> {
        let d = CU_EVENT_BLOCKING_SYNC | if horodate { 0 } else { CU_EVENT_DISABLE_TIMING };
        Self::creer(c, d, horodate)
    }

    fn creer(c: &Contexte, drapeaux: c_uint, horodate: bool) -> Result<Self> {
        let i = c.i.clone();
        i.courant()?;
        let mut e: Poignee = std::ptr::null_mut();
        verifier(i.a, "cuEventCreate", unsafe { (i.a.cuEventCreate)(&mut e, drapeaux) })?;
        Ok(Evenement { i, e, horodate })
    }

    /// Place l'événement à la fin du travail déjà soumis à `f`.
    pub fn enregistrer(&self, f: &Flux) -> Result<()> {
        self.i.courant()?;
        verifier(self.i.a, "cuEventRecord", unsafe { (self.i.a.cuEventRecord)(self.e, f.s) })
    }

    /// Vrai si le travail qui précède l'événement est fini (sans bloquer).
    pub fn fini(&self) -> Result<bool> {
        self.i.courant()?;
        let r = unsafe { (self.i.a.cuEventQuery)(self.e) };
        if r == CUDA_ERROR_NOT_READY {
            return Ok(false);
        }
        verifier(self.i.a, "cuEventQuery", r)?;
        Ok(true)
    }

    /// Bloque l'hôte jusqu'à l'événement.
    pub fn attendre(&self) -> Result<()> {
        self.i.courant()?;
        verifier(self.i.a, "cuEventSynchronize", unsafe { (self.i.a.cuEventSynchronize)(self.e) })
    }

    /// Millisecondes de la carte entre `debut` et cet événement (tous deux horodatés et atteints ;
    /// résolution annoncée par le pilote : environ 0,5 µs).
    pub fn ms_depuis(&self, debut: &Evenement) -> Result<f32> {
        if !self.horodate || !debut.horodate {
            return usage("ms_depuis demande deux événements horodatés");
        }
        self.i.courant()?;
        let mut ms = 0f32;
        verifier(self.i.a, "cuEventElapsedTime", unsafe { (self.i.a.cuEventElapsedTime)(&mut ms, debut.e, self.e) })?;
        Ok(ms)
    }
}

impl Drop for Evenement {
    fn drop(&mut self) {
        if self.i.courant().is_ok() {
            unsafe { (self.i.a.cuEventDestroy)(self.e) };
        }
    }
}

// ---------------------------------------------------------------------------------------------
// Mémoire de la carte
// ---------------------------------------------------------------------------------------------

/// Une vue sur une plage de VRAM : adresse de la carte et longueur. Ne possède rien ; la
/// [`MemoireCarte`] dont elle vient doit vivre plus longtemps que son usage.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct VueCarte {
    pub adresse: u64,
    pub octets: usize,
}

/// Une allocation de VRAM (`cuMemAlloc` : alignée sur 256 octets au moins).
pub struct MemoireCarte {
    i: Arc<Interne>,
    p: CuDevicePtr,
    octets: usize,
}

unsafe impl Send for MemoireCarte {}
unsafe impl Sync for MemoireCarte {}

impl MemoireCarte {
    pub fn allouer(c: &Contexte, octets: usize) -> Result<Self> {
        if octets == 0 {
            return usage("allocation de VRAM de 0 octet");
        }
        let i = c.i.clone();
        i.courant()?;
        let mut p: CuDevicePtr = 0;
        verifier(i.a, "cuMemAlloc_v2", unsafe { (i.a.cuMemAlloc)(&mut p, octets) })?;
        Ok(MemoireCarte { i, p, octets })
    }

    /// La plage `[decalage, decalage + octets)`. Panique si elle déborde de l'allocation : c'est une
    /// faute de programmation, pas une condition d'exécution.
    pub fn vue(&self, decalage: usize, octets: usize) -> VueCarte {
        assert!(
            decalage.checked_add(octets).is_some_and(|f| f <= self.octets),
            "vue de VRAM [{decalage}, +{octets}) hors de l'allocation de {} octets",
            self.octets
        );
        VueCarte { adresse: self.p + decalage as u64, octets }
    }

    /// Extension : la vue de toute l'allocation.
    pub fn tout(&self) -> VueCarte {
        VueCarte { adresse: self.p, octets: self.octets }
    }

    /// Extension : la longueur allouée.
    pub fn octets(&self) -> usize {
        self.octets
    }

    /// Extension : remplit une vue d'un octet, sur un flux (`cuMemsetD8Async`).
    pub fn remplir(&self, vue: VueCarte, octet: u8, f: &Flux) -> Result<()> {
        if vue.adresse < self.p || vue.adresse + vue.octets as u64 > self.p + self.octets as u64 {
            return usage("remplir : la vue n'appartient pas à cette allocation");
        }
        self.i.courant()?;
        verifier(self.i.a, "cuMemsetD8Async", unsafe { (self.i.a.cuMemsetD8Async)(vue.adresse, octet, vue.octets, f.s) })
    }
}

impl Drop for MemoireCarte {
    fn drop(&mut self) {
        if self.i.courant().is_ok() {
            unsafe { (self.i.a.cuMemFree)(self.p) };
        }
    }
}

// ---------------------------------------------------------------------------------------------
// Mémoire hôte épinglée
// ---------------------------------------------------------------------------------------------

/// Taille de page et de secteur que le moteur exige (§ 4.1, point 3).
pub const ALIGNEMENT_HOTE: usize = 4096;

/// Mémoire hôte verrouillée en RAM (`cuMemHostAlloc`, drapeau `PORTABLE`) : la carte la lit par
/// DMA, et une lecture sans tampon du disque peut y écrire directement. La longueur est arrondie au
/// multiple de 4 096 supérieur ; l'adresse est vérifiée multiple de 4 096 (sinon : erreur).
pub struct HoteEpingle {
    i: Arc<Interne>,
    p: *mut u8,
    octets: usize,
    carte: Option<u64>,
}

unsafe impl Send for HoteEpingle {}
unsafe impl Sync for HoteEpingle {}

impl HoteEpingle {
    /// `projetee` : la mémoire est aussi projetée dans l'espace d'adresses de la carte
    /// (`DEVICEMAP`), pour qu'un noyau y écrive directement (la boîte aux lettres du routeur, § 5.6).
    pub fn allouer(c: &Contexte, octets: usize, projetee: bool) -> Result<Self> {
        if octets == 0 {
            return usage("allocation épinglée de 0 octet");
        }
        let octets = octets.div_ceil(ALIGNEMENT_HOTE) * ALIGNEMENT_HOTE;
        let i = c.i.clone();
        i.courant()?;
        let mut p: *mut c_void = std::ptr::null_mut();
        let drapeaux = CU_MEMHOSTALLOC_PORTABLE | if projetee { CU_MEMHOSTALLOC_DEVICEMAP } else { 0 };
        verifier(i.a, "cuMemHostAlloc", unsafe { (i.a.cuMemHostAlloc)(&mut p, octets, drapeaux) })?;
        if (p as usize) % ALIGNEMENT_HOTE != 0 {
            unsafe { (i.a.cuMemFreeHost)(p) };
            return usage(format!("cuMemHostAlloc a rendu une adresse non alignée sur 4 096 : {p:p}"));
        }
        let mut carte = None;
        if projetee {
            let mut d: CuDevicePtr = 0;
            let r = unsafe { (i.a.cuMemHostGetDevicePointer)(&mut d, p, 0) };
            if let Err(e) = verifier(i.a, "cuMemHostGetDevicePointer_v2", r) {
                unsafe { (i.a.cuMemFreeHost)(p) };
                return Err(e);
            }
            carte = Some(d);
        }
        Ok(HoteEpingle { i, p: p as *mut u8, octets, carte })
    }

    pub fn tranche(&self) -> &[u8] {
        // SAFETY : allocation vivante de `octets` octets ; voir le contrat d'ordre en tête de crate.
        unsafe { std::slice::from_raw_parts(self.p, self.octets) }
    }

    pub fn tranche_mut(&mut self) -> &mut [u8] {
        unsafe { std::slice::from_raw_parts_mut(self.p, self.octets) }
    }

    /// L'adresse de cette mémoire vue par la carte, si elle est projetée.
    pub fn adresse_carte(&self) -> Option<u64> {
        self.carte
    }

    /// Extension : le pointeur hôte, pour une lecture sans tampon (`trc-es`) qui y écrit.
    pub fn pointeur(&self) -> *mut u8 {
        self.p
    }

    /// Extension : la longueur (arrondie au multiple de 4 096).
    pub fn octets(&self) -> usize {
        self.octets
    }

    /// Extension : lecture volatile d'un u32 à `decalage` (multiple de 4), pour sonder une boîte
    /// aux lettres qu'un noyau écrit pendant que l'hôte la lit (une lecture ordinaire pourrait être
    /// hissée hors de la boucle par le compilateur).
    pub fn lire_volatil_u32(&self, decalage: usize) -> u32 {
        assert!(decalage % 4 == 0 && decalage + 4 <= self.octets, "lecture volatile hors limites");
        // SAFETY : adresse alignée et dans l'allocation.
        unsafe { std::ptr::read_volatile(self.p.add(decalage) as *const u32) }
    }
}

impl Drop for HoteEpingle {
    fn drop(&mut self) {
        if self.i.courant().is_ok() {
            unsafe { (self.i.a.cuMemFreeHost)(self.p as *mut c_void) };
        }
    }
}

/// Copie asynchrone de `src[decalage, decalage + octets)` vers le début de `dst`, sur le flux `f`.
pub fn copier_vers_carte(dst: VueCarte, src: &HoteEpingle, decalage: usize, octets: usize, f: &Flux) -> Result<()> {
    if decalage.checked_add(octets).is_none_or(|fin| fin > src.octets) {
        return usage(format!("copie vers la carte : [{decalage}, +{octets}) hors de la source de {} octets", src.octets));
    }
    if octets > dst.octets {
        return usage(format!("copie vers la carte : {octets} octets dans une vue de {}", dst.octets));
    }
    f.i.courant()?;
    // SAFETY : plages vérifiées ; l'ordre des accès est le contrat de l'appelant.
    verifier(f.i.a, "cuMemcpyHtoDAsync_v2", unsafe {
        (f.i.a.cuMemcpyHtoDAsync)(dst.adresse, src.p.add(decalage) as *const c_void, octets, f.s)
    })
}

/// Copie asynchrone de toute la vue `src` vers `dst[decalage, decalage + src.octets)`, sur `f`.
pub fn copier_vers_hote(dst: &mut HoteEpingle, decalage: usize, src: VueCarte, f: &Flux) -> Result<()> {
    if decalage.checked_add(src.octets).is_none_or(|fin| fin > dst.octets) {
        return usage(format!("copie vers l'hôte : [{decalage}, +{}) hors de la destination de {} octets", src.octets, dst.octets));
    }
    f.i.courant()?;
    verifier(f.i.a, "cuMemcpyDtoHAsync_v2", unsafe {
        (f.i.a.cuMemcpyDtoHAsync)(dst.p.add(decalage) as *mut c_void, src.adresse, src.octets, f.s)
    })
}

/// Extension : copie asynchrone carte → carte de `src.octets` octets (`dst` au moins aussi longue).
pub fn copier_carte_carte(dst: VueCarte, src: VueCarte, f: &Flux) -> Result<()> {
    if src.octets > dst.octets {
        return usage("copie carte → carte : la destination est plus courte que la source");
    }
    f.i.courant()?;
    verifier(f.i.a, "cuMemcpyDtoDAsync_v2", unsafe { (f.i.a.cuMemcpyDtoDAsync)(dst.adresse, src.adresse, src.octets, f.s) })
}

// ---------------------------------------------------------------------------------------------
// Modules et fonctions
// ---------------------------------------------------------------------------------------------

struct ModuleInterne {
    i: Arc<Interne>,
    m: Poignee,
}

unsafe impl Send for ModuleInterne {}
unsafe impl Sync for ModuleInterne {}

impl Drop for ModuleInterne {
    fn drop(&mut self) {
        if self.i.courant().is_ok() {
            unsafe { (self.i.a.cuModuleUnload)(self.m) };
        }
    }
}

/// Une image de noyaux chargée (cubin, fatbin ou PTX).
pub struct Module {
    m: Arc<ModuleInterne>,
}

impl Module {
    /// Charge une image. Un PTX (texte) sans zéro final est recopié avec ce zéro, que le pilote
    /// exige ; une erreur de compilation à la volée rend le journal d'erreurs du pilote.
    pub fn charger(c: &Contexte, image: &[u8]) -> Result<Self> {
        if image.is_empty() {
            return usage("image de module vide");
        }
        let est_elf = image.starts_with(b"\x7fELF");
        let est_fatbin = image.len() >= 4 && u32::from_le_bytes([image[0], image[1], image[2], image[3]]) == 0xBA55_ED50;
        let copie;
        let image = if !est_elf && !est_fatbin && *image.last().unwrap() != 0 {
            copie = [image, &[0u8]].concat();
            &copie[..]
        } else {
            image
        };
        let i = c.i.clone();
        i.courant()?;
        let mut journal = vec![0u8; 8192];
        let mut options = [CU_JIT_ERROR_LOG_BUFFER, CU_JIT_ERROR_LOG_BUFFER_SIZE_BYTES];
        let mut valeurs = [journal.as_mut_ptr() as *mut c_void, journal.len() as *mut c_void];
        let mut m: Poignee = std::ptr::null_mut();
        let r = unsafe {
            (i.a.cuModuleLoadDataEx)(&mut m, image.as_ptr() as *const c_void, 2, options.as_mut_ptr(), valeurs.as_mut_ptr())
        };
        if r != CUDA_SUCCESS {
            let fin = journal.iter().position(|&b| b == 0).unwrap_or(journal.len());
            let texte = String::from_utf8_lossy(&journal[..fin]).into_owned();
            return match verifier(i.a, "cuModuleLoadDataEx", r) {
                Err(Erreur::Cuda { appel, code, nom, texte: t }) => {
                    Err(Erreur::Cuda { appel, code, nom, texte: if texte.is_empty() { t } else { format!("{t} ; journal : {texte}") } })
                }
                autre => autre.map(|_| unreachable!()),
            };
        }
        Ok(Module { m: Arc::new(ModuleInterne { i, m }) })
    }

    pub fn fonction(&self, nom: &CStr) -> Result<Fonction> {
        let i = &self.m.i;
        i.courant()?;
        let mut f: Poignee = std::ptr::null_mut();
        let r = unsafe { (i.a.cuModuleGetFunction)(&mut f, self.m.m, nom.as_ptr()) };
        verifier(i.a, "cuModuleGetFunction", r).map_err(|e| match e {
            Erreur::Cuda { appel, code, nom: n, texte } => {
                Erreur::Cuda { appel, code, nom: n, texte: format!("{texte} (fonction {})", nom.to_string_lossy()) }
            }
            autre => autre,
        })?;
        Ok(Fonction { m: self.m.clone(), f })
    }
}

/// Un noyau d'un module.
pub struct Fonction {
    m: Arc<ModuleInterne>,
    f: Poignee,
}

unsafe impl Send for Fonction {}
unsafe impl Sync for Fonction {}

impl Fonction {
    /// Lance le noyau sur `f`. `args` : un pointeur vers chaque argument, dans l'ordre de la
    /// signature du noyau (convention de `cuLaunchKernel`).
    ///
    /// # Safety
    /// Le nombre, l'ordre et le type des arguments doivent être ceux du noyau ; les adresses de la
    /// carte qu'ils portent doivent rester valides jusqu'à la fin du noyau.
    pub unsafe fn lancer(&self, grille: [u32; 3], bloc: [u32; 3], partagee: u32, f: &Flux, args: &mut [*mut c_void]) -> Result<()> {
        let i = &self.m.i;
        i.courant()?;
        let r = unsafe {
            (i.a.cuLaunchKernel)(
                self.f, grille[0], grille[1], grille[2], bloc[0], bloc[1], bloc[2], partagee, f.s,
                args.as_mut_ptr(), std::ptr::null_mut(),
            )
        };
        verifier(i.a, "cuLaunchKernel", r)
    }

    /// Extension : autorise jusqu'à `octets` de mémoire partagée dynamique (au-delà de 48 Kio, la
    /// carte l'exige : `CU_FUNC_ATTRIBUTE_MAX_DYNAMIC_SHARED_SIZE_BYTES`).
    pub fn partagee_max(&self, octets: u32) -> Result<()> {
        let i = &self.m.i;
        i.courant()?;
        verifier(i.a, "cuFuncSetAttribute", unsafe {
            (i.a.cuFuncSetAttribute)(self.f, CU_FUNC_ATTRIBUTE_MAX_DYNAMIC_SHARED_SIZE_BYTES, octets as c_int)
        })
    }
}
