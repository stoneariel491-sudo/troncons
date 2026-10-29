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

