//! Le compteur de lecture du disque de toute la machine, pour savoir ce que les autres programmes
//! lisaient pendant une passe (la carte, la RAM et le disque sont partagés entre cinq lots).
//!
//! Compteur PDH « \PhysicalDisk(_Total)\Disk Read Bytes/sec », ajouté par son nom **anglais**
//! (`PdhAddEnglishCounterW` : ce Windows est en français, le nom anglais seul serait refusé par
//! `PdhAddCounterW`). On lit sa valeur **brute** (`PdhGetRawCounterValue`) : pour ce type de
//! compteur (`PERF_COUNTER_BULK_COUNT`), `FirstValue` est le nombre cumulé d'octets lus depuis le
//! démarrage, si bien que la différence de deux relevés donne les octets de l'intervalle exactement,
//! sans intégrer un débit échantillonné (le chemin du lot R, `trc-juge::compteurs`, intègre le débit
//! formaté ; celui-ci en est indépendant).
//!
//! Octets étrangers d'une passe = octets du système − octets livrés par notre lecteur. Le compteur
//! voit aussi les lectures du cache de Windows des autres programmes qui manquent leur cache, et
//! pas celles qui y réussissent : c'est bien la charge du disque, qui seule nous concerne.

use windows_sys::Win32::System::Performance::{
    PDH_HCOUNTER, PDH_HQUERY, PDH_RAW_COUNTER, PdhAddEnglishCounterW, PdhCloseQuery, PdhCollectQueryData,
    PdhGetRawCounterValue, PdhOpenQueryW,
};

pub struct CompteurDisque {
    requete: PDH_HQUERY,
    compteur: PDH_HCOUNTER,
}

impl CompteurDisque {
    pub fn ouvrir() -> Result<CompteurDisque, String> {
        let mut requete: PDH_HQUERY = std::ptr::null_mut();
        let mut compteur: PDH_HCOUNTER = std::ptr::null_mut();
        let chemin: Vec<u16> = "\\PhysicalDisk(_Total)\\Disk Read Bytes/sec\0".encode_utf16().collect();
        // SAFETY : appels PDH documentés, pointeurs de sortie valides, chaîne terminée par un zéro.
        unsafe {
            let e = PdhOpenQueryW(std::ptr::null(), 0, &mut requete);
            if e != 0 {
                return Err(format!("PdhOpenQueryW : {e:#x}"));
            }
            let e = PdhAddEnglishCounterW(requete, chemin.as_ptr(), 0, &mut compteur);
            if e != 0 {
                PdhCloseQuery(requete);
                return Err(format!("PdhAddEnglishCounterW : {e:#x}"));
            }
        }
        Ok(CompteurDisque { requete, compteur })
    }

    /// Octets lus sur le disque par toute la machine depuis le démarrage.
    pub fn cumul(&self) -> Result<u64, String> {
        // SAFETY : requête et compteur ouverts par `ouvrir`.
        unsafe {
            let e = PdhCollectQueryData(self.requete);
            if e != 0 {
                return Err(format!("PdhCollectQueryData : {e:#x}"));
            }
            let mut brut: PDH_RAW_COUNTER = std::mem::zeroed();
            let mut sorte = 0u32;
            let e = PdhGetRawCounterValue(self.compteur, &mut sorte, &mut brut);
            if e != 0 || brut.CStatus != 0 {
                return Err(format!("PdhGetRawCounterValue : {e:#x}, statut {:#x}", brut.CStatus));
            }
            Ok(brut.FirstValue as u64)
        }
    }
}

impl Drop for CompteurDisque {
    fn drop(&mut self) {
        // SAFETY : requête ouverte par `ouvrir`.
        unsafe { PdhCloseQuery(self.requete) };
    }
}

/// Une fenêtre de relevé : le cumul au début, puis les octets de la fenêtre à la fin.
pub struct Fenetre<'a> {
    compteur: Option<&'a CompteurDisque>,
    debut: Option<u64>,
}

impl<'a> Fenetre<'a> {
    pub fn ouvrir(compteur: Option<&'a CompteurDisque>) -> Fenetre<'a> {
        let debut = compteur.and_then(|c| c.cumul().ok());
        Fenetre { compteur, debut }
    }

    /// Octets lus par la machine pendant la fenêtre (None si le compteur manque).
    pub fn octets(&self) -> Option<u64> {
        let fin = self.compteur?.cumul().ok()?;
        Some(fin.saturating_sub(self.debut?))
    }
}
