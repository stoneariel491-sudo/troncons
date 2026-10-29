//! trc-cache (lot O) : le cache d'experts de troncons, ses politiques, et le simulateur.
//!
//! Spécification : `decisions/ARCHITECTURE.md` § 5.7 (couture A). Le cache a deux étages :
//! - **VRAM** : `emplacements` emplacements d'experts **décodés** (13 254 144 o chacun pour
//!   gpt-oss, § 5.6) ; c'est là que la GEMV lit ;
//! - **RAM tiède** : `tiedes` entrées de tronçons **codés** en mémoire épinglée (mode A ; 0 en
//!   mode A0). Un défaut VRAM servi par la RAM coûte une copie et un décodage, pas une lecture.
//!
//! Le **simulateur** ([`rejouer`]) est ce même code, appelé sur une trace de routage : c'est ce
//! qui rend possible le témoin « compte du moteur = compte du simulateur à l'unité » (§ 5.7, O3).
//!
//! # L'automate d'un emplacement VRAM (schéma M5 du mémoire)
//!
//! ```text
//!            demander : défaut                pret (décodage fini)
//!   Libre ─────────────────────────► EnVol ─────────────────────────► Present
//!     ▲                                                                  │
//!     └──────────────────── éviction (jamais épinglé) ◄──────────────────┘
//! ```
//! Un emplacement `EnVol` n'est jamais évincé (le décodeur y écrit) ; un expert demandé par une
//! couche en cours est **épinglé** jusqu'à `liberer(couche)` et n'est jamais évincé non plus.
//!
//! # Les règles qui ne sont pas écrites au § 5.7, et le choix fait ici
//!
//! Chacune : réponse par délégation du 2026-10-15, réversible ; signalée dans
//! `moteur/REPRISE-O.md` pour l'arbitre.
//! 1. **Ordre d'éviction dans un groupe.** Tous les experts d'une demande sont épinglés avant le
//!    premier service ; chaque défaut, s'il n'y a pas d'emplacement libre, évince la victime de la
//!    politique parmi les non-épinglés. Démontré équivalent (même contenu, même ordre de récence,
//!    mêmes succès) à « servir tout le groupe puis évincer » de `g_lru` (outils/gptoss_localite.py)
//!    et à `cache_lru` de l'étude 04 (`outils/chargement_localite.py`) : voir
//!    `moteur/O-pour-le-memoire.md`, lemme 1 ; le témoin O1 le vérifie à l'unité.
//! 2. **L'étage RAM est inclusif et voit tous les accès.** Un succès VRAM touche aussi l'entrée
//!    RAM du même expert si elle existe ; une entrée RAM n'est créée que par une lecture du disque
//!    (on ne peut pas recréer un tronçon codé depuis un expert décodé). Avec `tiedes ≥
//!    emplacements` et une politique à pile (LRU, Belady), c'est exactement le modèle « deux
//!    étages » des plafonds (`h_v = h(f_v)`, `h_r = h(f) − h(f_v)`, gptoss_localite.py § 3) :
//!    `succes_vram + succes_ram` égale le succès d'un cache unique de `tiedes` emplacements.
//!    Témoin : `deux_etages_egalent_deux_caches_a_pile` (tests) et le témoin O1.
//! 3. **`evictions` compte les évictions VRAM** (chacune coûte un futur décodage) ; les sorties de
//!    l'étage RAM se lisent dans [`Cache::evictions_ram`] (extension).
//! 4. **Octets** : le cache ne connaît pas la taille des tronçons ; [`Cache::fixer_tailles`]
//!    (extension) la lui donne. Sans elle, `octets_disque` et `octets_copies` restent à 0 (cas de
//!    [`rejouer`], qui compte en accès).
//! 5. **Une demande qui trouve son expert `EnVol`** (préchargement de J1+) rend `Succes` : l'appelant
//!    lit [`Cache::etat`] et attend l'événement du décodage. Elle compte comme un succès VRAM.

mod politiques;
mod trace;

pub use politiques::{Belady, Lru, Politique};
pub use trace::{lire_trace, ErreurTrace, Result, Trace};

use std::collections::HashMap;

/// Un expert : (couche, expert).
pub type Id = (u16 /*couche*/, u16 /*expert*/);

/// Niveau de raffinement présent dans un emplacement (§ 4.1, principe 5). `Base` sert en J2.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Niveau {
    Base = 0,
    Exact = 1,
}

/// L'état d'un emplacement VRAM.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Etat {
    Libre,
    EnVol { niveau: Niveau },
    Present { niveau: Niveau },
}

/// Ce que le cache décide pour un expert demandé.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Decision {
    /// L'expert est (ou sera, s'il est `EnVol`) dans cet emplacement.
    Succes { emplacement: u32 },
    /// Défaut VRAM ; le tronçon codé est déjà en mémoire épinglée, dans l'entrée `tiede`.
    DefautRam { emplacement: u32, tiede: u32 },
    /// Défaut complet : lire le tronçon du disque (dans l'entrée `tiede` si elle est donnée, sinon
    /// dans un tampon d'arrivée de la fenêtre), le copier, le décoder dans `emplacement`.
    DefautDisque { emplacement: u32, tiede: Option<u32> },
}

/// Les compteurs du cache (§ 5.7). `succes_vram + succes_ram + defauts_disque` = accès.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Compteurs {
    pub succes_vram: u64,
    pub succes_ram: u64,
    pub defauts_disque: u64,
    pub octets_disque: u64,
    pub octets_copies: u64,
    pub evictions: u64,
}

impl Compteurs {
    /// Nombre d'accès servis.
    pub fn acces(&self) -> u64 {
        self.succes_vram + self.succes_ram + self.defauts_disque
    }
}

/// Le cache d'experts à deux étages.
pub struct Cache<P: Politique> {
    vram: P,
    ram: P,
    etats: Vec<Etat>,
    occupant: Vec<Option<Id>>,
    ou_vram: HashMap<Id, u32>,
    libres_vram: Vec<u32>,
    occupant_tiede: Vec<Option<Id>>,
    ou_ram: HashMap<Id, u32>,
    libres_ram: Vec<u32>,
    epingles: Vec<Id>,
    taille: Option<Box<dyn Fn(Id) -> u64>>,
    compteurs: Compteurs,
    evictions_ram: u64,
}

impl<P: Politique> Cache<P> {
    /// `emplacements` emplacements VRAM (il en faut au moins autant que d'experts épinglés à la
    /// fois : k par couche en cours), `tiedes` entrées RAM (0 en mode A0). Les politiques doivent
    /// être vides.
    pub fn nouveau(emplacements: u32, tiedes: u32, vram: P, ram: P) -> Self {
        Cache {
            vram,
            ram,
            etats: vec![Etat::Libre; emplacements as usize],
            occupant: vec![None; emplacements as usize],
            ou_vram: HashMap::with_capacity(emplacements as usize),
            // Les libres sont pris par la fin : on les range à l'envers pour servir 0, 1, 2, …
            libres_vram: (0..emplacements).rev().collect(),
            occupant_tiede: vec![None; tiedes as usize],
            ou_ram: HashMap::with_capacity(tiedes as usize),
            libres_ram: (0..tiedes).rev().collect(),
            epingles: Vec::new(),
            taille: None,
            compteurs: Compteurs::default(),
            evictions_ram: 0,
        }
    }

    /// Extension : la taille en octets du tronçon lu pour un expert (niveaux 0 et 1 en mode exact).
    pub fn fixer_tailles(&mut self, taille: impl Fn(Id) -> u64 + 'static) {
        self.taille = Some(Box::new(taille));
    }

    /// Sert une couche : épingle ses experts, rend une décision par expert, dans l'ordre donné.
    ///
    /// Panique si un défaut ne trouve ni emplacement libre ni victime (tous épinglés ou en vol) :
    /// c'est une erreur de dimensionnement de l'appelant (`emplacements` < experts épinglés).
    pub fn demander(&mut self, couche: u16, experts: &[u16], t: u64) -> Vec<Decision> {
        for &e in experts {
            if !self.epingles.contains(&(couche, e)) {
                self.epingles.push((couche, e));
            }
        }
        let mut sortie = Vec::with_capacity(experts.len());
        for &e in experts {
            let id = (couche, e);
            if let Some(&s) = self.ou_vram.get(&id) {
                self.vram.acceder(id, t);
                if self.ou_ram.contains_key(&id) {
                    self.ram.acceder(id, t);
                }
                self.compteurs.succes_vram += 1;
                sortie.push(Decision::Succes { emplacement: s });
                continue;
            }
            let s = self.emplacement_pour_defaut();
            self.vram.inserer(id, t);
            self.etats[s as usize] = Etat::EnVol { niveau: Niveau::Exact };
            self.occupant[s as usize] = Some(id);
            self.ou_vram.insert(id, s);
            let octets = self.taille.as_ref().map_or(0, |f| f(id));
            self.compteurs.octets_copies += octets;
            if let Some(&r) = self.ou_ram.get(&id) {
                self.ram.acceder(id, t);
                self.compteurs.succes_ram += 1;
                sortie.push(Decision::DefautRam { emplacement: s, tiede: r });
            } else {
                self.compteurs.defauts_disque += 1;
                self.compteurs.octets_disque += octets;
                let tiede = self.entree_tiede_pour(id, t);
                sortie.push(Decision::DefautDisque { emplacement: s, tiede });
            }
        }
        sortie
    }

    /// Un emplacement libre, ou celui de la victime VRAM (évincée ici).
    fn emplacement_pour_defaut(&mut self) -> u32 {
        if let Some(s) = self.libres_vram.pop() {
            return s;
        }
        let Cache { vram, epingles, ou_vram, etats, .. } = self;
        let epingle = |id: Id| {
            epingles.contains(&id)
                || ou_vram.get(&id).is_some_and(|&s| matches!(etats[s as usize], Etat::EnVol { .. }))
        };
        let Some(v) = vram.victime(&epingle) else {
            panic!(
                "trc-cache : aucun emplacement VRAM libre ni évinçable ({} emplacements, {} experts \
                 épinglés) : il faut emplacements ≥ experts épinglés à la fois",
                self.etats.len(),
                self.epingles.len()
            );
        };
        self.vram.retirer(v);
        let s = self.ou_vram.remove(&v).expect("victime VRAM sans emplacement");
        self.occupant[s as usize] = None;
        self.etats[s as usize] = Etat::Libre;
        self.compteurs.evictions += 1;
        s
    }

    /// Une entrée tiède pour un tronçon lu du disque ; `None` en mode A0 ou si toutes sont
    /// épinglées (le tronçon passe alors par un tampon d'arrivée et n'est pas gardé).
    fn entree_tiede_pour(&mut self, id: Id, t: u64) -> Option<u32> {
        if self.occupant_tiede.is_empty() {
            return None;
        }
        let r = match self.libres_ram.pop() {
            Some(r) => r,
            None => {
                let Cache { ram, epingles, .. } = self;
                let epingle = |x: Id| epingles.contains(&x);
                let v = ram.victime(&epingle)?;
                self.ram.retirer(v);
                let r = self.ou_ram.remove(&v).expect("victime RAM sans entrée");
                self.occupant_tiede[r as usize] = None;
                self.evictions_ram += 1;
                r
            }
        };
        self.ram.inserer(id, t);
        self.occupant_tiede[r as usize] = Some(id);
        self.ou_ram.insert(id, r);
        Some(r)
    }

    /// Le décodage de cet emplacement est terminé : `EnVol` → `Present`.
    /// Panique si l'emplacement n'était pas en vol (erreur de l'ordonnanceur).
    pub fn pret(&mut self, emplacement: u32) {
        match self.etats[emplacement as usize] {
            Etat::EnVol { niveau } => self.etats[emplacement as usize] = Etat::Present { niveau },
            autre => panic!("trc-cache : pret({emplacement}) sur un emplacement {autre:?}"),
        }
    }

    /// Fin des GEMV de la couche : ses experts sont désépinglés.
    pub fn liberer(&mut self, couche: u16) {
        self.epingles.retain(|id| id.0 != couche);
    }

    pub fn compteurs(&self) -> Compteurs {
        self.compteurs
    }

    /// Extension : l'état d'un emplacement VRAM.
    pub fn etat(&self, emplacement: u32) -> Etat {
        self.etats[emplacement as usize]
    }

    /// Extension : l'expert qui occupe un emplacement VRAM.
    pub fn occupant(&self, emplacement: u32) -> Option<Id> {
        self.occupant[emplacement as usize]
    }

    /// Extension : l'emplacement VRAM d'un expert, s'il y est.
    pub fn emplacement_de(&self, id: Id) -> Option<u32> {
        self.ou_vram.get(&id).copied()
    }

    /// Extension : l'entrée tiède d'un expert, s'il y est.
    pub fn tiede_de(&self, id: Id) -> Option<u32> {
        self.ou_ram.get(&id).copied()
    }

    /// Extension : les sorties de l'étage RAM.
    pub fn evictions_ram(&self) -> u64 {
        self.evictions_ram
    }

    /// Extension : les experts épinglés en ce moment.
    pub fn epingles(&self) -> &[Id] {
        &self.epingles
    }
}

/// Rejoue une trace dans un cache neuf (le simulateur, § 5.7) : pour chaque jeton, pour chaque
/// couche dans l'ordre du calcul, `demander`, puis `pret` sur chaque défaut, puis `liberer`.
/// L'instant passé aux politiques est `t = jeton · L + couche`. Compte en accès (octets à 0).
pub fn rejouer<P: Politique>(trace: &Trace, emplacements: u32, tiedes: u32, vram: P, ram: P) -> Compteurs {
    let mut cache = Cache::nouveau(emplacements, tiedes, vram, ram);
    rejouer_dans(trace, &mut cache)
}

/// Extension : rejoue une trace dans un cache déjà construit (par exemple muni de ses tailles).
pub fn rejouer_dans<P: Politique>(trace: &Trace, cache: &mut Cache<P>) -> Compteurs {
    let l = trace.couches as usize;
    for t in 0..trace.jetons as usize {
        for c in 0..l {
            let decisions = cache.demander(c as u16, trace.groupe(t, c), (t * l + c) as u64);
            for d in decisions {
                match d {
                    Decision::Succes { .. } => {}
                    Decision::DefautRam { emplacement, .. } | Decision::DefautDisque { emplacement, .. } => {
                        cache.pret(emplacement)
                    }
                }
            }
            cache.liberer(c as u16);
        }
    }
    cache.compteurs()
}

#[cfg(test)]
mod tests;
