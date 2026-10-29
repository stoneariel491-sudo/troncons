//! `trc-es` : lectures sans tampon par port de complétion (ARCHITECTURE.md § 5.5).
//!
//! Le fichier s'ouvre avec `FILE_FLAG_NO_BUFFERING | FILE_FLAG_OVERLAPPED` : chaque lecture va du
//! disque à la mémoire de l'appelant sans passer par le cache de Windows (qui coûterait une copie
//! par un fil à 1,65–3,1 Go/s, étude 01 § 2.3, et de la RAM qui croîtrait avec le modèle). Le
//! système exige alors que le décalage, la longueur et l'adresse de destination soient des
//! multiples du secteur ; on exige 4 096 (§ 4.1, point 3), et on le vérifie avant d'appeler.
//!
//! **Profondeur.** Au plus `profondeur` lectures sont confiées au système à la fois. Une requête
//! soumise au-delà attend dans une file interne, dans l'ordre de soumission, et part dès qu'une
//! lecture s'achève (dans [`Lecteur::recolter`]). [`Lecteur::en_vol`] compte les deux : confiées et
//! en attente. Raison du choix : l'ordonnanceur soumet tous les défauts d'une couche sans avoir à
//! compter, et la profondeur mesurée utile (QD 4 pour des blocs de 4 Mio, étude 01 § 2.4) reste
//! un réglage du lecteur.
//!
//! **Contrat.** La mémoire de destination doit rester valide et ne pas être lue jusqu'à
//! l'achèvement de sa requête (la signature gelée de `soumettre` est sûre ; le contrat se dit ici).
//! Une lecture qui finit au-delà de la fin du fichier rend moins d'octets que demandé : l'appelant
//! compare `Achevement::octets` à sa longueur.

use std::collections::{HashMap, VecDeque};
use std::fmt;
use std::os::windows::ffi::OsStrExt;
use std::path::Path;
use std::sync::Mutex;
use std::time::Instant;

use windows_sys::Win32::Foundation::{
    CloseHandle, ERROR_IO_PENDING, GetLastError, HANDLE, INVALID_HANDLE_VALUE, WAIT_TIMEOUT,
};
use windows_sys::Win32::Storage::FileSystem::{
    CreateFileW, FILE_FLAG_NO_BUFFERING, FILE_FLAG_OVERLAPPED, FILE_SHARE_READ, GetFileSizeEx,
    OPEN_EXISTING, ReadFile,
};
use windows_sys::Win32::System::IO::{
    CancelIoEx, CreateIoCompletionPort, GetOverlappedResult, GetQueuedCompletionStatusEx, OVERLAPPED,
    OVERLAPPED_ENTRY,
};

/// L'alignement exigé du décalage, de la longueur et de la destination.
pub const ALIGNEMENT: u64 = 4096;

const GENERIC_READ: u32 = 0x8000_0000;

/// L'erreur de `trc-es`.
#[derive(Debug, Clone)]
pub enum Erreur {
    /// Un appel du système a échoué ; `code` est celui de `GetLastError`.
    Systeme { appel: &'static str, code: u32 },
    /// Un usage hors contrat, détecté avant le système.
    Usage(String),
}

impl fmt::Display for Erreur {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Erreur::Systeme { appel, code } => write!(f, "{appel} : erreur Windows {code}"),
            Erreur::Usage(m) => write!(f, "usage de trc-es : {m}"),
        }
    }
}

impl std::error::Error for Erreur {}

pub type Result<T> = std::result::Result<T, Erreur>;

fn derniere(appel: &'static str) -> Erreur {
    // SAFETY : lecture de l'erreur du fil.
    Erreur::Systeme { appel, code: unsafe { GetLastError() } }
}

/// Une lecture : `longueur` octets à `decalage` dans le fichier, écrits à `destination`.
/// `jeton` est rendu tel quel dans l'achèvement.
#[derive(Clone, Copy, Debug)]
pub struct Requete {
    pub jeton: u64,
    pub decalage: u64,
    pub longueur: u32,
    pub destination: *mut u8,
}

/// L'achèvement d'une lecture. `erreur` : le code Windows si la lecture a échoué ; `duree_us` : de
/// la remise au système (pas de la soumission, si la requête a attendu dans la file) à la récolte.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Achevement {
    pub jeton: u64,
    pub octets: u32,
    pub erreur: Option<u32>,
    pub duree_us: u32,
}

/// Une lecture confiée au système. `ov` en premier : le système rend l'adresse de l'OVERLAPPED,
/// qui est aussi celle de la structure.
#[repr(C)]
struct Vol {
    ov: OVERLAPPED,
    jeton: u64,
    depart: Instant,
}

struct Etat {
    vols: HashMap<usize, Box<Vol>>,
    attente: VecDeque<Requete>,
    /// Achèvements nés hors du port (une requête de la file refusée au lancement).
    refus: Vec<Achevement>,
    octets_lus: u64,
}

// Les pointeurs que contient l'état (destinations, OVERLAPPED) ne sont touchés que sous le verrou
// ou par le système ; le contrat de destination est celui de l'appelant.
unsafe impl Send for Etat {}

/// Un fichier ouvert pour des lectures sans tampon, et son port de complétion.
pub struct Lecteur {
    fichier: HANDLE,
    port: HANDLE,
    profondeur: usize,
    taille: u64,
    etat: Mutex<Etat>,
}

unsafe impl Send for Lecteur {}
unsafe impl Sync for Lecteur {}

impl Lecteur {
    /// Ouvre `chemin` en lecture sans tampon (partage en lecture), avec au plus `profondeur`
    /// lectures confiées au système à la fois.
    pub fn ouvrir(chemin: &Path, profondeur: usize) -> Result<Self> {
        if profondeur == 0 {
            return Err(Erreur::Usage("profondeur nulle".into()));
        }
        let large: Vec<u16> = chemin.as_os_str().encode_wide().chain(std::iter::once(0)).collect();
        // SAFETY : chemin terminé par un zéro.
        let fichier = unsafe {
            CreateFileW(
                large.as_ptr(),
                GENERIC_READ,
                FILE_SHARE_READ,
                std::ptr::null(),
                OPEN_EXISTING,
                FILE_FLAG_NO_BUFFERING | FILE_FLAG_OVERLAPPED,
                std::ptr::null_mut(),
            )
        };
        if fichier == INVALID_HANDLE_VALUE {
            return Err(derniere("CreateFileW"));
        }
        let mut taille: i64 = 0;
        if unsafe { GetFileSizeEx(fichier, &mut taille) } == 0 {
            let e = derniere("GetFileSizeEx");
            unsafe { CloseHandle(fichier) };
            return Err(e);
        }
        // Un fil de récolte à la fois : concurrence 1 (le moteur récolte sur son fil d'ordonnancement).
        let port = unsafe { CreateIoCompletionPort(fichier, std::ptr::null_mut(), 0, 1) };
        if port.is_null() {
            let e = derniere("CreateIoCompletionPort");
            unsafe { CloseHandle(fichier) };
            return Err(e);
        }
        Ok(Lecteur {
            fichier,
            port,
            profondeur,
            taille: taille as u64,
            etat: Mutex::new(Etat { vols: HashMap::new(), attente: VecDeque::new(), refus: Vec::new(), octets_lus: 0 }),
        })
    }

    /// Soumet une lecture. Refuse (sans rien lancer) un décalage, une longueur ou une destination
    /// qui ne sont pas multiples de 4 096, ou une longueur nulle.
    pub fn soumettre(&self, r: Requete) -> Result<()> {
        if r.decalage % ALIGNEMENT != 0 || r.longueur as u64 % ALIGNEMENT != 0 || r.longueur == 0 || r.destination as u64 % ALIGNEMENT != 0 {
            return Err(Erreur::Usage(format!(
                "requête {} non alignée sur 4 096 : décalage {}, longueur {}, destination {:p}",
                r.jeton, r.decalage, r.longueur, r.destination
            )));
        }
        let mut etat = self.etat.lock().unwrap();
        if etat.vols.len() < self.profondeur && etat.attente.is_empty() {
            self.lancer(&mut etat, r)
        } else {
            etat.attente.push_back(r);
            Ok(())
        }
    }

    /// Confie une requête au système. Sous le verrou.
    fn lancer(&self, etat: &mut Etat, r: Requete) -> Result<()> {
        let mut vol = Box::new(Vol { ov: unsafe { std::mem::zeroed() }, jeton: r.jeton, depart: Instant::now() });
        vol.ov.Anonymous.Anonymous.Offset = r.decalage as u32;
        vol.ov.Anonymous.Anonymous.OffsetHigh = (r.decalage >> 32) as u32;
        let cle = &mut vol.ov as *mut OVERLAPPED;
        // SAFETY : OVERLAPPED à adresse stable (boîte gardée jusqu'à la récolte) ; destination selon
        // le contrat de l'appelant.
        let ok = unsafe { ReadFile(self.fichier, r.destination, r.longueur, std::ptr::null_mut(), cle) };
        if ok == 0 {
            let code = unsafe { GetLastError() };
            if code != ERROR_IO_PENDING {
                // Échec immédiat : aucun paquet de complétion ne viendra.
                return Err(Erreur::Systeme { appel: "ReadFile", code });
            }
        }
        // Succès immédiat ou en attente : dans les deux cas un paquet arrivera sur le port (le
        // drapeau FILE_SKIP_COMPLETION_PORT_ON_SUCCESS n'est pas posé).
        etat.vols.insert(cle as usize, vol);
        Ok(())
    }

    /// Récolte les lectures achevées, en attendant au plus `attente_ms` la première (0 : sans
    /// attendre ; `u32::MAX` : sans limite). Ajoute les achèvements à `sortie` et relance la file.
    /// Rend tout de suite si rien n'est en vol.
    pub fn recolter(&self, attente_ms: u32, sortie: &mut Vec<Achevement>) -> Result<()> {
        {
            let mut etat = self.etat.lock().unwrap();
            sortie.append(&mut etat.refus);
            if etat.vols.is_empty() {
                return Ok(());
            }
        }
        let mut entrees: Vec<OVERLAPPED_ENTRY> = vec![unsafe { std::mem::zeroed() }; self.profondeur];
        let mut n: u32 = 0;
        // Attente hors du verrou : un autre fil peut soumettre pendant ce temps.
        let ok = unsafe { GetQueuedCompletionStatusEx(self.port, entrees.as_mut_ptr(), entrees.len() as u32, &mut n, attente_ms, 0) };
        if ok == 0 {
            let code = unsafe { GetLastError() };
            if code == WAIT_TIMEOUT {
                return Ok(());
            }
            return Err(Erreur::Systeme { appel: "GetQueuedCompletionStatusEx", code });
        }
        let mut etat = self.etat.lock().unwrap();
        for e in &entrees[..n as usize] {
            let cle = e.lpOverlapped as usize;
            let Some(vol) = etat.vols.remove(&cle) else {
                return Err(Erreur::Usage(format!("paquet de complétion inconnu ({cle:#x})")));
            };
            let duree_us = vol.depart.elapsed().as_micros().min(u32::MAX as u128) as u32;
            let mut erreur = None;
            // `Internal` porte le NTSTATUS de la lecture ; s'il n'est pas nul, on demande au
            // système le code Windows correspondant.
            if vol.ov.Internal != 0 {
                let mut lus: u32 = 0;
                let r = unsafe { GetOverlappedResult(self.fichier, &vol.ov, &mut lus, 0) };
                erreur = Some(if r == 0 { unsafe { GetLastError() } } else { vol.ov.Internal as u32 });
            }
            let octets = e.dwNumberOfBytesTransferred;
            etat.octets_lus += octets as u64;
            sortie.push(Achevement { jeton: vol.jeton, octets, erreur, duree_us });
        }
        while etat.vols.len() < self.profondeur {
            let Some(r) = etat.attente.pop_front() else { break };
            if let Err(e) = self.lancer(&mut etat, r) {
                let code = match e {
                    Erreur::Systeme { code, .. } => code,
                    Erreur::Usage(_) => u32::MAX,
                };
                sortie.push(Achevement { jeton: r.jeton, octets: 0, erreur: Some(code), duree_us: 0 });
            }
        }
        Ok(())
    }

    /// Lectures confiées au système et pas encore récoltées, plus celles qui attendent dans la file.
    pub fn en_vol(&self) -> usize {
        let etat = self.etat.lock().unwrap();
        etat.vols.len() + etat.attente.len()
    }

    /// Octets livrés par les lectures récoltées depuis l'ouverture.
    pub fn octets_lus(&self) -> u64 {
        self.etat.lock().unwrap().octets_lus
    }

    /// Extension : la taille du fichier, en octets.
    pub fn taille(&self) -> u64 {
        self.taille
    }

    /// Extension : la profondeur (lectures confiées au système à la fois, au plus).
    pub fn profondeur(&self) -> usize {
        self.profondeur
    }
}

impl Drop for Lecteur {
    fn drop(&mut self) {
        // Les OVERLAPPED en vol appartiennent au système jusqu'à leur paquet : on annule, puis on
        // attend chaque paquet avant de libérer quoi que ce soit.
        let etat = self.etat.get_mut().unwrap();
        etat.attente.clear();
        if !etat.vols.is_empty() {
            unsafe { CancelIoEx(self.fichier, std::ptr::null()) };
            let mut entrees: Vec<OVERLAPPED_ENTRY> = vec![unsafe { std::mem::zeroed() }; self.profondeur];
            while !etat.vols.is_empty() {
                let mut n: u32 = 0;
                let ok = unsafe { GetQueuedCompletionStatusEx(self.port, entrees.as_mut_ptr(), entrees.len() as u32, &mut n, 10_000, 0) };
                if ok == 0 {
                    // Aucun paquet en 10 s après annulation : on fuit les OVERLAPPED plutôt que de
                    // libérer une mémoire que le système pourrait encore écrire.
                    std::mem::forget(std::mem::take(&mut etat.vols));
                    break;
                }
                for e in &entrees[..n as usize] {
                    etat.vols.remove(&(e.lpOverlapped as usize));
                }
            }
        }
        unsafe {
            CloseHandle(self.port);
            CloseHandle(self.fichier);
        }
    }
}
