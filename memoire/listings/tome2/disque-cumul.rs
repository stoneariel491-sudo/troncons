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
