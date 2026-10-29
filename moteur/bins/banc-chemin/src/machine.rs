//! L'état de la machine au moment d'une mesure : heure locale, alimentation, RAM, carte.
//! Chaque journal du banc l'enregistre au début et à la fin d'un essai.

use serde_json::{Value, json};
use windows_sys::Win32::System::Power::{GetSystemPowerStatus, SYSTEM_POWER_STATUS};
use windows_sys::Win32::System::ProcessStatus::{K32GetProcessMemoryInfo, PROCESS_MEMORY_COUNTERS};
use windows_sys::Win32::System::SystemInformation::{GetLocalTime, GlobalMemoryStatusEx, MEMORYSTATUSEX};
use windows_sys::Win32::System::Threading::GetCurrentProcess;

/// Heure locale, AAAA-MM-JJTHH:MM:SS.mmm.
pub fn horodate() -> String {
    let mut t = unsafe { std::mem::zeroed() };
    unsafe { GetLocalTime(&mut t) };
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.{:03}",
        t.wYear, t.wMonth, t.wDay, t.wHour, t.wMinute, t.wSecond, t.wMilliseconds
    )
}

/// (sur secteur ?, pourcentage de batterie). `ACLineStatus` : 0 batterie, 1 secteur, 255 inconnu.
pub fn alimentation() -> (Option<bool>, u8) {
    let mut s: SYSTEM_POWER_STATUS = unsafe { std::mem::zeroed() };
    if unsafe { GetSystemPowerStatus(&mut s) } == 0 {
        return (None, 255);
    }
    let secteur = match s.ACLineStatus {
        0 => Some(false),
        1 => Some(true),
        _ => None,
    };
    (secteur, s.BatteryLifePercent)
}

/// (RAM physique disponible, totale), en octets.
pub fn ram() -> (u64, u64) {
    let mut m: MEMORYSTATUSEX = unsafe { std::mem::zeroed() };
    m.dwLength = std::mem::size_of::<MEMORYSTATUSEX>() as u32;
    if unsafe { GlobalMemoryStatusEx(&mut m) } == 0 {
        return (0, 0);
    }
    (m.ullAvailPhys, m.ullTotalPhys)
}

/// (ensemble de travail, ensemble de travail de pointe) du processus, en octets.
pub fn ensemble_de_travail() -> (u64, u64) {
    let mut c: PROCESS_MEMORY_COUNTERS = unsafe { std::mem::zeroed() };
    c.cb = std::mem::size_of::<PROCESS_MEMORY_COUNTERS>() as u32;
    if unsafe { K32GetProcessMemoryInfo(GetCurrentProcess(), &mut c, c.cb) } == 0 {
        return (0, 0);
    }
    (c.WorkingSetSize as u64, c.PeakWorkingSetSize as u64)
}

/// Le relevé complet, pour un journal.
pub fn releve(c: Option<&trc_cuda::Contexte>) -> Value {
    let (secteur, batterie) = alimentation();
    let (dispo, totale) = ram();
    let (ws, ws_pointe) = ensemble_de_travail();
    let mut v = json!({
        "heure": horodate(),
        "secteur": secteur,
        "batterie_pourcent": batterie,
        "ram_disponible_o": dispo,
        "ram_totale_o": totale,
        "ensemble_de_travail_o": ws,
        "ensemble_de_travail_pointe_o": ws_pointe,
    });
    if let Some(c) = c {
        let (libre, totale) = c.memoire();
        v["carte"] = json!({
            "nom": c.nom(),
            "pilote": c.version_pilote(),
            "vram_libre_o": libre,
            "vram_totale_o": totale,
            "attente": format!("{:?}", c.attente_effective()),
            "moteurs_de_copie": c.attribut(trc_cuda::Attribut::MoteursDeCopie).ok(),
        });
    }
    v
}

/// Les temps de processeur de toute la machine et de ce processus, en unités de 100 ns
/// (`GetSystemTimes` : le temps noyau y comprend le temps inactif ; `GetProcessTimes`).
#[derive(Clone, Copy)]
pub struct TempsProcesseur {
    inactif: u64,
    total: u64,
    nous: u64,
}

fn filetime(f: windows_sys::Win32::Foundation::FILETIME) -> u64 {
    ((f.dwHighDateTime as u64) << 32) | f.dwLowDateTime as u64
}

impl TempsProcesseur {
    pub fn maintenant() -> TempsProcesseur {
        use windows_sys::Win32::Foundation::FILETIME;
        use windows_sys::Win32::System::Threading::{GetProcessTimes, GetSystemTimes};
        let z = FILETIME { dwLowDateTime: 0, dwHighDateTime: 0 };
        let (mut i, mut k, mut u) = (z, z, z);
        let (mut c, mut e, mut pk, mut pu) = (z, z, z, z);
        // SAFETY : pointeurs de sortie valides ; pseudo-poignée du processus courant.
        unsafe {
            GetSystemTimes(&mut i, &mut k, &mut u);
            GetProcessTimes(GetCurrentProcess(), &mut c, &mut e, &mut pk, &mut pu);
        }
        TempsProcesseur { inactif: filetime(i), total: filetime(k) + filetime(u), nous: filetime(pk) + filetime(pu) }
    }

    /// Depuis `debut` : (part occupée de tous les fils logiques, part prise par ce processus, part
    /// prise par les autres), chacune entre 0 et 1.
    pub fn depuis(&self, debut: &TempsProcesseur) -> Value {
        let total = self.total.saturating_sub(debut.total).max(1) as f64;
        let occupe = 1.0 - self.inactif.saturating_sub(debut.inactif) as f64 / total;
        let nous = self.nous.saturating_sub(debut.nous) as f64 / total;
        json!({ "occupe": occupe, "nous": nous, "autres": (occupe - nous).max(0.0) })
    }
}
