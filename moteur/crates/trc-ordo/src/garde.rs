//! La garde de production (constat M1 de l'épreuve J1).
//!
//! # Le trou qu'elle ferme
//!
//! En production, le seul contrôle d'un tronçon était le retour des voies rANS à L (§ 4.12). Il ne
//! garde que les flux codés : les flux bruts d'une partie (MEDIANES, BIAIS : ≈ 43 Ko sur 12 Mo) et,
//! en mode A0, la ligne d'enchâssement lue à chaque jeton n'étaient gardés par rien. Un octet faux y
//! donnait un expert faux sans erreur (copie du lot O : texte identique à celui du fichier sain).
//!
//! # Ce qu'elle fait
//!
//! - **Tronçons** : à chaque lecture achevée, les octets utiles du niveau 0 (`utiles[0]`) sont
//!   hachés par un fil de travail et comparés à `empreinte_niveau[0]`, déjà dans le répertoire
//!   (§ 4.7, § 4.12 : aucune couture touchée). Le hachage court en même temps que la copie vers la
//!   carte et le décodage (les deux ne font que lire le tampon) ; le pas attend tous ses hachages
//!   **avant de rendre son jeton ou ses logits** : un tronçon faux devient une erreur fatale nommée
//!   (couche, expert, empreintes), jamais une sortie.
//! - **Réutilisation d'un tampon** : toute lecture qui va écrire dans un tampon attend d'abord la
//!   fin des hachages qui le lisent encore (`attendre_zone`).
//! - **Lignes d'enchâssement** (mode A0) : une table des empreintes de chaque ligne, bâtie à
//!   l'ouverture en lisant `token_embd` une fois (son empreinte entière vérifiée au passage) ; chaque
//!   ligne lue est comparée à sa case (3 060 o hachés par jeton).
//!
//! # Le coût, mesuré (`examples/debit_empreinte.rs`)
//!
//! `empreinte64` (sha2 0.10.9) : 1,07 à 1,10 Go/s par fil, 4,3 Go/s sur 4 fils [mes., 2026-10-16].
//! Un jeton du 120b lit ≈ 0,71 Go de tronçons : ≈ 0,65 s de calcul, réparties sur les fils, cachées
//! derrière ≈ 0,46 s de pas tant que le disque limite ; ce qui reste sur le chemin critique est le
//! hachage du dernier tronçon d'un pas (≈ 11 ms au plus). La série ABBA de la ronde le chiffre.

use std::collections::HashMap;
use std::sync::mpsc;
use std::sync::{Arc, Mutex};
use std::thread::JoinHandle;
use std::time::Instant;

use anyhow::{Result, bail};

struct Travail {
    ticket: u64,
    adresse: usize,
    octets: usize,
}

struct Fait {
    ticket: u64,
    empreinte: u64,
}

struct Tache {
    adresse: usize,
    octets: usize,
    attendu: u64,
    couche: u16,
    expert: u16,
}

/// Les fils de hachage et les tâches en cours.
pub(crate) struct Garde {
    envoi: Option<mpsc::Sender<Travail>>,
    retour: mpsc::Receiver<Fait>,
    fils: Vec<JoinHandle<()>>,
    en_cours: HashMap<u64, Tache>,
    prochain: u64,
    pub octets: u64,
    pub troncons: u64,
    /// Secondes passées par le fil d'ordonnancement à attendre un hachage.
    pub attente_s: f64,
}

impl Garde {
    pub fn nouvelle(n_fils: usize) -> Garde {
        let (envoi, recu) = mpsc::channel::<Travail>();
        let (rendu, retour) = mpsc::channel::<Fait>();
        let recu = Arc::new(Mutex::new(recu));
        let fils = (0..n_fils.max(1))
            .map(|_| {
                let recu = recu.clone();
                let rendu = rendu.clone();
                std::thread::spawn(move || {
                    loop {
                        let t = { recu.lock().unwrap().recv() };
                        let Ok(t) = t else { break };
                        // SAFETY : le tampon (mémoire épinglée du moteur) a fini de recevoir sa
                        // lecture avant la soumission, et aucune lecture n'y écrit avant que la tâche
                        // ne soit rendue (`attendre_zone`) ; la garde est détruite avant les tampons.
                        let o = unsafe { std::slice::from_raw_parts(t.adresse as *const u8, t.octets) };
                        let e = trc_format::empreinte64(o);
                        if rendu.send(Fait { ticket: t.ticket, empreinte: e }).is_err() {
                            break;
                        }
                    }
                })
            })
            .collect();
        Garde { envoi: Some(envoi), retour, fils, en_cours: HashMap::new(), prochain: 0, octets: 0, troncons: 0, attente_s: 0.0 }
    }

    /// Confie le hachage de `octets` octets à `adresse` ; `attendu` est l'empreinte du répertoire.
    pub fn soumettre(&mut self, adresse: *const u8, octets: usize, attendu: u64, couche: u16, expert: u16) {
        let ticket = self.prochain;
        self.prochain += 1;
        self.en_cours.insert(ticket, Tache { adresse: adresse as usize, octets, attendu, couche, expert });
        self.octets += octets as u64;
        self.troncons += 1;
        self.envoi.as_ref().unwrap().send(Travail { ticket, adresse: adresse as usize, octets }).expect("fils de la garde");
    }

    fn recevoir(&mut self, f: Fait) -> Result<()> {
        let t = self.en_cours.remove(&f.ticket).expect("ticket de la garde");
        if f.empreinte != t.attendu {
            bail!(
                "garde de production : couche {}, expert {} : empreinte des {} octets utiles lus {:016x} au lieu de {:016x} (répertoire)",
                t.couche,
                t.expert,
                t.octets,
                f.empreinte,
                t.attendu
            );
        }
        Ok(())
    }

    /// Rend les hachages finis sans attendre.
    pub fn recolter(&mut self) -> Result<()> {
        while let Ok(f) = self.retour.try_recv() {
            self.recevoir(f)?;
        }
        Ok(())
    }

    /// Attend la fin de tout hachage qui lit encore la zone `[debut, debut + n)`.
    pub fn attendre_zone(&mut self, debut: *const u8, n: usize) -> Result<()> {
        self.recolter()?;
        let (a, b) = (debut as usize, debut as usize + n);
        let t0 = Instant::now();
        let mut attendu = false;
        while self.en_cours.values().any(|t| t.adresse < b && a < t.adresse + t.octets) {
            attendu = true;
            let f = self.retour.recv().expect("fils de la garde");
            self.recevoir(f)?;
        }
        if attendu {
            self.attente_s += t0.elapsed().as_secs_f64();
        }
        Ok(())
    }

    /// Attend et vérifie tous les hachages en cours.
    pub fn attendre_tout(&mut self) -> Result<()> {
        self.recolter()?;
        let t0 = Instant::now();
        let attendu = !self.en_cours.is_empty();
        while !self.en_cours.is_empty() {
            let f = self.retour.recv().expect("fils de la garde");
            self.recevoir(f)?;
        }
        if attendu {
            self.attente_s += t0.elapsed().as_secs_f64();
        }
        Ok(())
    }
}

impl Drop for Garde {
    fn drop(&mut self) {
        // Les fils finissent les travaux en file (les tampons vivent encore : la garde est le premier
        // champ détruit du moteur), puis sortent quand le canal se ferme.
        self.envoi.take();
        for f in self.fils.drain(..) {
            let _ = f.join();
        }
    }
}

/// Les empreintes de chaque ligne de `token_embd`, depuis ses octets lus par morceaux dans l'ordre
/// (`morceaux` rend des tranches contiguës qui, mises bout à bout, font le tenseur entier). Rend
/// aussi l'empreinte64 du tenseur entier, que l'appelant compare à celle de la table des résidents.
pub(crate) struct LignesEnConstruction {
    octets_ligne: usize,
    reste: Vec<u8>,
    pub empreintes: Vec<u64>,
    entier: sha2::Sha256,
}

impl LignesEnConstruction {
    pub fn nouvelles(octets_ligne: usize, lignes: usize) -> Self {
        use sha2::Digest;
        LignesEnConstruction { octets_ligne, reste: Vec::with_capacity(octets_ligne), empreintes: Vec::with_capacity(lignes), entier: sha2::Sha256::new() }
    }

    /// Ajoute le morceau suivant du tenseur.
    pub fn ajouter(&mut self, mut m: &[u8], n_fils: usize) {
        use sha2::Digest;
        self.entier.update(m);
        let ol = self.octets_ligne;
        if !self.reste.is_empty() {
            let k = (ol - self.reste.len()).min(m.len());
            self.reste.extend_from_slice(&m[..k]);
            m = &m[k..];
            if self.reste.len() == ol {
                self.empreintes.push(trc_format::empreinte64(&self.reste));
                self.reste.clear();
            }
        }
        let n = m.len() / ol;
        if n > 0 {
            let pleines = &m[..n * ol];
            let base = self.empreintes.len();
            self.empreintes.resize(base + n, 0);
            let sortie = &mut self.empreintes[base..];
            let par = n.div_ceil(n_fils.max(1));
            std::thread::scope(|s| {
                for (i, part) in sortie.chunks_mut(par).enumerate() {
                    let src = &pleines[i * par * ol..];
                    s.spawn(move || {
                        for (q, e) in part.iter_mut().enumerate() {
                            *e = trc_format::empreinte64(&src[q * ol..(q + 1) * ol]);
                        }
                    });
                }
            });
        }
        self.reste.extend_from_slice(&m[n * ol..]);
    }

    /// Fin : rend (empreintes des lignes, empreinte64 du tenseur entier).
    pub fn finir(self) -> Result<(Vec<u64>, u64)> {
        use sha2::Digest;
        if !self.reste.is_empty() {
            bail!("token_embd : {} octets après la dernière ligne entière", self.reste.len());
        }
        let h = self.entier.finalize();
        Ok((self.empreintes, u64::from_le_bytes(h[..8].try_into().unwrap())))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn la_garde_voit_un_octet_faux_et_attend_sa_zone() {
        let a: Vec<u8> = (0..100_000u32).map(|x| (x % 251) as u8).collect();
        let mut b = a.clone();
        let e = trc_format::empreinte64(&a);
        let mut g = Garde::nouvelle(2);
        g.soumettre(a.as_ptr(), a.len(), e, 1, 2);
        g.attendre_zone(a.as_ptr(), 10).unwrap();
        assert!(g.en_cours.is_empty());
        b[777] ^= 1; // cassure
        g.soumettre(b.as_ptr(), b.len(), e, 3, 4);
        let r = g.attendre_tout();
        assert!(r.is_err());
        assert!(format!("{:#}", r.unwrap_err()).contains("couche 3, expert 4"));
    }

    #[test]
    fn lignes_par_morceaux_quelconques() {
        let ol = 3060;
        let t: Vec<u8> = (0..ol * 37).map(|x| (x * 13 % 256) as u8).collect();
        for coupe in [1usize, 4096, 10_000, 65_536, t.len()] {
            let mut l = LignesEnConstruction::nouvelles(ol, 37);
            for m in t.chunks(coupe) {
                l.ajouter(m, 3);
            }
            let (v, e) = l.finir().unwrap();
            assert_eq!(e, trc_format::empreinte64(&t));
            assert_eq!(v.len(), 37);
            for (i, x) in v.iter().enumerate() {
                assert_eq!(*x, trc_format::empreinte64(&t[i * ol..(i + 1) * ol]), "coupe {coupe}, ligne {i}");
            }
        }
    }
}
