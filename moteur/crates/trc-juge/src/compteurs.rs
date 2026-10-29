//! Les compteurs d'une mesure (§ 5.9, critères C7, C8, C10) : octets lus sur le disque, mémoire du
//! processus, VRAM.
//!
//! - **Disque** : compteur PDH « \PhysicalDisk(_Total)\Disk Read Bytes/sec », ajouté par son nom
//!   **anglais** (`PdhAddEnglishCounterW` : sur ce Windows en français, le nom traduit seul est
//!   reconnu par typeperf, mesuré par l'étude 06 § 7.2), lu toutes les 0,5 s et intégré. Le compteur
//!   est global à la machine : `repos_disque` chiffre d'abord la charge des autres programmes.
//! - **Mémoire** : `GetProcessMemoryInfo` ; la pointe de l'ensemble de travail est tenue par le
//!   système lui-même (`PeakWorkingSetSize`), donc exacte, pas échantillonnée ; le dernier relevé
//!   et la mémoire engagée sont échantillonnés toutes les 0,1 s.
//! - **VRAM** : un seul processus `nvidia-smi --query-gpu=memory.used -lms 250` dont on lit les lignes
//!   (une mesure toutes les 250 ms sans relancer nvidia-smi à chaque fois).

use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

use anyhow::{Result, bail};
use serde::Serialize;
use windows_sys::Win32::Foundation::{CloseHandle, HANDLE};
use windows_sys::Win32::System::Performance::{PDH_FMT_COUNTERVALUE, PDH_FMT_DOUBLE, PDH_HCOUNTER, PDH_HQUERY, PdhAddEnglishCounterW, PdhCloseQuery, PdhCollectQueryData, PdhGetFormattedCounterValue, PdhOpenQueryW};
use windows_sys::Win32::System::ProcessStatus::{GetProcessMemoryInfo, PROCESS_MEMORY_COUNTERS};
use windows_sys::Win32::System::Threading::{GetCurrentProcess, OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION, PROCESS_VM_READ};

fn large(s: &str) -> Vec<u16> {
    s.encode_utf16().chain(std::iter::once(0)).collect()
}

/// Le compteur de lecture du disque, intégré.
pub struct CompteurDisque {
    requete: PDH_HQUERY,
    compteur: PDH_HCOUNTER,
}

unsafe impl Send for CompteurDisque {}

impl CompteurDisque {
    pub fn ouvrir() -> Result<CompteurDisque> {
        let mut requete: PDH_HQUERY = std::ptr::null_mut();
        let mut compteur: PDH_HCOUNTER = std::ptr::null_mut();
        // SAFETY : appels PDH documentés, pointeurs de sortie valides.
        unsafe {
            let e = PdhOpenQueryW(std::ptr::null(), 0, &mut requete);
            if e != 0 {
                bail!("PdhOpenQueryW : {e:#x}");
            }
            let chemin = large("\\PhysicalDisk(_Total)\\Disk Read Bytes/sec");
            let e = PdhAddEnglishCounterW(requete, chemin.as_ptr(), 0, &mut compteur);
            if e != 0 {
                PdhCloseQuery(requete);
                bail!("PdhAddEnglishCounterW : {e:#x}");
            }
            PdhCollectQueryData(requete);
        }
        Ok(CompteurDisque { requete, compteur })
    }

    /// Recueille et rend le débit moyen (octets/s) depuis le recueil précédent.
    pub fn debit(&self) -> f64 {
        unsafe {
            PdhCollectQueryData(self.requete);
            let mut v = PDH_FMT_COUNTERVALUE::default();
            let mut t = 0u32;
            if PdhGetFormattedCounterValue(self.compteur, PDH_FMT_DOUBLE, &mut t, &mut v) != 0 {
                return 0.0;
            }
            v.Anonymous.doubleValue
        }
    }
}

impl Drop for CompteurDisque {
    fn drop(&mut self) {
        unsafe {
            PdhCloseQuery(self.requete);
        }
    }
}

/// Mémoire d'un processus (le processus courant si `pid` est absent).
#[derive(Clone, Copy, Debug, Default, Serialize)]
pub struct Memoire {
    pub ensemble_travail: u64,
    pub ensemble_travail_pointe: u64,
    pub engagee: u64,
    pub engagee_pointe: u64,
}

pub struct Processus {
    poignee: HANDLE,
    a_fermer: bool,
}

unsafe impl Send for Processus {}

impl Processus {
    pub fn courant() -> Processus {
        Processus { poignee: unsafe { GetCurrentProcess() }, a_fermer: false }
    }
    pub fn ouvrir(pid: u32) -> Result<Processus> {
        let h = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, 0, pid) };
        if h.is_null() {
            bail!("OpenProcess({pid}) refusé");
        }
        Ok(Processus { poignee: h, a_fermer: true })
    }
    pub fn memoire(&self) -> Memoire {
        let mut c = PROCESS_MEMORY_COUNTERS { cb: std::mem::size_of::<PROCESS_MEMORY_COUNTERS>() as u32, ..Default::default() };
        unsafe {
            if GetProcessMemoryInfo(self.poignee, &mut c, c.cb) == 0 {
                return Memoire::default();
            }
        }
        Memoire { ensemble_travail: c.WorkingSetSize as u64, ensemble_travail_pointe: c.PeakWorkingSetSize as u64, engagee: c.PagefileUsage as u64, engagee_pointe: c.PeakPagefileUsage as u64 }
    }
}

/// Les compteurs d'E/S d'un processus (`GetProcessIoCounters`) : toutes ses lectures `ReadFile`,
/// tamponnées ou non, et les fautes de page sur fichier projeté n'y entrent pas. Critère C8 refait
/// par le juge de l'épreuve (constat M3) : c'est l'instrument du moteur, là où le compteur PDH est
/// celui de la machine.
#[derive(Clone, Copy, Debug, Default, Serialize)]
pub struct EntreesSorties {
    pub lectures: u64,
    pub octets_lus: u64,
    pub ecritures: u64,
    pub octets_ecrits: u64,
    pub autres_octets: u64,
}

impl Processus {
    pub fn es(&self) -> EntreesSorties {
        use windows_sys::Win32::System::Threading::{GetProcessIoCounters, IO_COUNTERS};
        let mut c = IO_COUNTERS::default();
        // SAFETY : structure de sortie de taille fixe ; poignée valide tant que `self` vit.
        if unsafe { GetProcessIoCounters(self.poignee, &mut c) } == 0 {
            return EntreesSorties::default();
        }
        EntreesSorties { lectures: c.ReadOperationCount, octets_lus: c.ReadTransferCount, ecritures: c.WriteOperationCount, octets_ecrits: c.WriteTransferCount, autres_octets: c.OtherTransferCount }
    }
}

impl Drop for Processus {
    fn drop(&mut self) {
        if self.a_fermer {
            unsafe {
                CloseHandle(self.poignee);
            }
        }
    }
}

/// Débit de repos du disque (octets/s) sur `secondes`, avant une mesure.
pub fn repos_disque(secondes: f64) -> Result<f64> {
    let c = CompteurDisque::ouvrir()?;
    let t0 = Instant::now();
    let mut octets = 0.0;
    let mut dernier = Instant::now();
    while t0.elapsed().as_secs_f64() < secondes {
        std::thread::sleep(Duration::from_millis(500));
        let dt = dernier.elapsed().as_secs_f64();
        dernier = Instant::now();
        octets += c.debit() * dt;
    }
    Ok(octets / t0.elapsed().as_secs_f64())
}

#[derive(Clone, Debug, Default, Serialize)]
pub struct Releve {
    pub duree_s: f64,
    pub octets_disque_lus: f64,
    pub memoire_pointe: Memoire,
    pub ensemble_travail_dernier: u64,
    pub vram_pointe_mio: Option<u64>,
    pub vram_premiere_mio: Option<u64>,
    pub echantillons_vram: usize,
}

/// Rend les poignées standard du processus (entrée, sortie, erreur) non héritables.
///
/// Raison (constat G2 de l'épreuve J1, reproduit par `mesures/moteur/O/corrections/temoin_sortie.py`) :
/// `std::process::Command` crée l'enfant avec l'héritage des poignées permis ; l'enfant reçoit alors
/// TOUTES les poignées héritables du parent, dont ses sorties standard quand un pilote les a
/// branchées sur des tuyaux. Un `nvidia-smi` survivant tenait ainsi ouverts les tuyaux du pilote, qui
/// attendait sans fin. Les poignées que `Command` donne à un enfant (`Stdio::inherit`, tuyaux) sont
/// des copies héritables faites par la bibliothèque standard : elles ne dépendent pas de ce drapeau.
pub fn poignees_standard_non_heritables() {
    use windows_sys::Win32::Foundation::{HANDLE_FLAG_INHERIT, INVALID_HANDLE_VALUE, SetHandleInformation};
    use windows_sys::Win32::System::Console::{GetStdHandle, STD_ERROR_HANDLE, STD_INPUT_HANDLE, STD_OUTPUT_HANDLE};
    for n in [STD_INPUT_HANDLE, STD_OUTPUT_HANDLE, STD_ERROR_HANDLE] {
        // SAFETY : poignées du processus courant ; un échec (poignée absente) est sans effet.
        unsafe {
            let h = GetStdHandle(n);
            if !h.is_null() && h != INVALID_HANDLE_VALUE {
                SetHandleInformation(h, HANDLE_FLAG_INHERIT, 0);
            }
        }
    }
}

/// Un objet tâche (job) du système dont les processus meurent quand sa dernière poignée se ferme
/// (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`). Le parent tient la seule poignée : s'il meurt de quelque
/// façon que ce soit (erreur, `TerminateProcess` de l'extérieur, sortie sans destruction), le
/// système la ferme et l'enfant meurt avec lui.
struct Tache(HANDLE);

unsafe impl Send for Tache {}

impl Tache {
    fn pour(enfant: &Child) -> Option<Tache> {
        use std::os::windows::io::AsRawHandle;
        use windows_sys::Win32::System::JobObjects::{
            AssignProcessToJobObject, CreateJobObjectW, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
            JobObjectExtendedLimitInformation, SetInformationJobObject,
        };
        // SAFETY : appels documentés ; structure d'entrée de la bonne taille ; poignée de l'enfant
        // valide tant que `enfant` vit.
        unsafe {
            let t = CreateJobObjectW(std::ptr::null(), std::ptr::null());
            if t.is_null() {
                return None;
            }
            let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            let ok = SetInformationJobObject(
                t,
                JobObjectExtendedLimitInformation,
                &info as *const _ as *const std::ffi::c_void,
                std::mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
            );
            if ok == 0 || AssignProcessToJobObject(t, enfant.as_raw_handle() as HANDLE) == 0 {
                CloseHandle(t);
                return None;
            }
            Some(Tache(t))
        }
    }
}

impl Drop for Tache {
    fn drop(&mut self) {
        // SAFETY : poignée possédée ; sa fermeture tue ce qui reste dans la tâche.
        unsafe {
            CloseHandle(self.0);
        }
    }
}

/// Échantillonne disque, mémoire et VRAM pendant une mesure, dans un fil à part.
///
/// L'enfant `nvidia-smi` ne survit jamais à l'échantillonneur ni au processus (constat G2) :
/// `arreter` le tue et l'attend ; `Drop` fait de même si `arreter` n'a pas été appelé (erreur entre
/// les deux) ; et l'enfant est placé dans une tâche tuée à la fermeture, pour le cas où le parent
/// meurt sans rien détruire. Son entrée et sa sortie d'erreur ne sont pas celles du parent
/// (`Stdio::null`), et les poignées standard du parent ne sont plus héritables.
pub struct Echantillonneur {
    arret: Arc<AtomicBool>,
    fil: Option<JoinHandle<Releve>>,
    smi: Option<Child>,
    tache: Option<Tache>,
    fil_smi: Option<JoinHandle<(Option<u64>, Option<u64>, usize)>>,
}

impl Drop for Echantillonneur {
    fn drop(&mut self) {
        self.arret.store(true, Ordering::Relaxed);
        if let Some(mut e) = self.smi.take() {
            let _ = e.kill(); // seul processus tué : celui que ce code a lancé
            let _ = e.wait();
        }
        self.tache.take();
        if let Some(f) = self.fil.take() {
            let _ = f.join();
        }
        if let Some(f) = self.fil_smi.take() {
            let _ = f.join();
        }
    }
}

impl Echantillonneur {
    pub fn demarrer(pid: Option<u32>, avec_vram: bool) -> Result<Echantillonneur> {
        let arret = Arc::new(AtomicBool::new(false));
        let disque = CompteurDisque::ouvrir()?;
        let proc = match pid {
            Some(p) => Processus::ouvrir(p)?,
            None => Processus::courant(),
        };
        let a = arret.clone();
        let fil = std::thread::spawn(move || {
            let t0 = Instant::now();
            let mut r = Releve::default();
            let mut dernier_disque = Instant::now();
            let mut tour = 0u64;
            while !a.load(Ordering::Relaxed) {
                std::thread::sleep(Duration::from_millis(100));
                tour += 1;
                let m = proc.memoire();
                r.ensemble_travail_dernier = m.ensemble_travail;
                r.memoire_pointe = m;
                if tour % 5 == 0 {
                    let dt = dernier_disque.elapsed().as_secs_f64();
                    dernier_disque = Instant::now();
                    r.octets_disque_lus += disque.debit() * dt;
                }
            }
            let dt = dernier_disque.elapsed().as_secs_f64();
            r.octets_disque_lus += disque.debit() * dt;
            r.memoire_pointe = proc.memoire();
            r.duree_s = t0.elapsed().as_secs_f64();
            r
        });
        let (mut smi, mut fil_smi, mut tache) = (None, None, None);
        if avec_vram {
            poignees_standard_non_heritables();
            let mut enfant = Command::new("nvidia-smi")
                .args(["--query-gpu=memory.used", "--format=csv,noheader,nounits", "-lms", "250"])
                .stdin(Stdio::null())
                .stdout(Stdio::piped())
                .stderr(Stdio::null())
                .spawn()?;
            tache = Tache::pour(&enfant);
            let sortie = enfant.stdout.take().unwrap();
            fil_smi = Some(std::thread::spawn(move || {
                let (mut pointe, mut premiere, mut n) = (None::<u64>, None::<u64>, 0usize);
                for ligne in BufReader::new(sortie).lines().map_while(|l| l.ok()) {
                    if let Ok(v) = ligne.trim().parse::<u64>() {
                        premiere.get_or_insert(v);
                        pointe = Some(pointe.map_or(v, |p: u64| p.max(v)));
                        n += 1;
                    }
                }
                (pointe, premiere, n)
            }));
            smi = Some(enfant);
        }
        Ok(Echantillonneur { arret, fil: Some(fil), smi, tache, fil_smi })
    }

    /// Vrai si l'enfant nvidia-smi a bien été placé dans sa tâche (journal du témoin G2).
    pub fn enfant_dans_une_tache(&self) -> bool {
        self.tache.is_some()
    }

    pub fn arreter(mut self) -> Releve {
        self.arret.store(true, Ordering::Relaxed);
        let mut r = self.fil.take().unwrap().join().unwrap_or_default();
        if let Some(mut e) = self.smi.take() {
            let _ = e.kill(); // seul processus tué : celui que ce code a lancé
            let _ = e.wait();
        }
        self.tache.take();
        if let Some(f) = self.fil_smi.take()
            && let Ok((p, q, n)) = f.join()
        {
            r.vram_pointe_mio = p;
            r.vram_premiere_mio = q;
            r.echantillons_vram = n;
        }
        r
    }
}
