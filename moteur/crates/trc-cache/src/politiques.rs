//! Les politiques de remplacement : LRU (le cache du moteur en J1) et Belady (l'optimum hors ligne,
//! pour le simulateur seulement : il lit l'avenir dans la trace).
//!
//! Contrat commun (trait [`Politique`]) : la politique ne possède pas les emplacements, elle ne
//! tient qu'un ordre sur les identifiants présents. Le cache l'informe de chaque accès réussi
//! (`acceder`), de chaque entrée (`inserer`) et de chaque sortie (`retirer`) ; `victime` **désigne**
//! l'identifiant à évincer parmi ceux qui ne sont pas épinglés, **sans le retirer** : le cache
//! appelle ensuite `retirer` lui-même. Ainsi une seule voie fait sortir un identifiant.

use crate::Id;
use std::collections::HashMap;

/// Une politique de remplacement (§ 5.7, couture A).
pub trait Politique {
    /// Un identifiant présent vient d'être servi à l'instant `t`.
    fn acceder(&mut self, id: Id, t: u64);
    /// Un identifiant absent vient d'entrer à l'instant `t`.
    fn inserer(&mut self, id: Id, t: u64);
    /// Un identifiant présent sort (éviction ou effacement).
    fn retirer(&mut self, id: Id);
    /// L'identifiant à évincer parmi les présents non épinglés ; `None` s'il n'y en a aucun.
    /// Ne retire rien.
    fn victime(&mut self, epingle: &dyn Fn(Id) -> bool) -> Option<Id>;
}

/// Extension : une politique choisie à l'exécution (`Box<dyn Politique>`) est une politique.
impl<P: Politique + ?Sized> Politique for Box<P> {
    fn acceder(&mut self, id: Id, t: u64) {
        (**self).acceder(id, t)
    }
    fn inserer(&mut self, id: Id, t: u64) {
        (**self).inserer(id, t)
    }
    fn retirer(&mut self, id: Id) {
        (**self).retirer(id)
    }
    fn victime(&mut self, epingle: &dyn Fn(Id) -> bool) -> Option<Id> {
        (**self).victime(epingle)
    }
}

const NUL: u32 = u32::MAX;

#[derive(Clone, Copy, Debug)]
struct Noeud {
    id: Id,
    prec: u32,
    suiv: u32,
}

/// LRU : on évince le présent non épinglé dont le dernier usage est le plus ancien.
///
/// Liste doublement chaînée dans un tableau (pas d'allocation par accès) et table
/// identifiant → nœud : `acceder`, `inserer`, `retirer` en O(1) ; `victime` parcourt depuis le plus
/// ancien et saute les épinglés (au plus les experts des couches en cours, quelques unités).
///
/// L'ordre ne dépend que de l'ordre des appels, pas de `t` : les k experts d'une même couche
/// partagent le même `t`, et leur rang de récence doit suivre l'ordre de service (celui de
/// `OrderedDict.move_to_end` dans l'outil de l'étude 04).
///
/// Écart dit avec le § 5.7, qui écrit `pub struct Lru;` : une structure unité ne peut pas porter
/// l'état d'un LRU. On construit par `Lru::default()` ou `Lru::nouveau()`.
#[derive(Clone, Debug)]
pub struct Lru {
    noeuds: Vec<Noeud>,
    libres: Vec<u32>,
    index: HashMap<Id, u32>,
    /// Le plus ancien (première victime).
    tete: u32,
    /// Le plus récent.
    queue: u32,
}

impl Default for Lru {
    fn default() -> Self {
        Lru { noeuds: Vec::new(), libres: Vec::new(), index: HashMap::new(), tete: NUL, queue: NUL }
    }
}

impl Lru {
    pub fn nouveau() -> Self {
        Self::default()
    }

    /// Nombre d'identifiants présents.
    pub fn len(&self) -> usize {
        self.index.len()
    }

    pub fn is_empty(&self) -> bool {
        self.index.is_empty()
    }

    /// Les présents, du plus ancien au plus récent (pour les témoins).
    pub fn ordre(&self) -> Vec<Id> {
        let mut v = Vec::with_capacity(self.len());
        let mut i = self.tete;
        while i != NUL {
            v.push(self.noeuds[i as usize].id);
            i = self.noeuds[i as usize].suiv;
        }
        v
    }

    fn detacher(&mut self, i: u32) {
        let Noeud { prec, suiv, .. } = self.noeuds[i as usize];
        if prec == NUL { self.tete = suiv } else { self.noeuds[prec as usize].suiv = suiv }
        if suiv == NUL { self.queue = prec } else { self.noeuds[suiv as usize].prec = prec }
    }

    fn accrocher_en_queue(&mut self, i: u32) {
        self.noeuds[i as usize].prec = self.queue;
        self.noeuds[i as usize].suiv = NUL;
        if self.queue == NUL { self.tete = i } else { self.noeuds[self.queue as usize].suiv = i }
        self.queue = i;
    }
}

impl Politique for Lru {
    fn acceder(&mut self, id: Id, _t: u64) {
        let i = *self.index.get(&id).expect("Lru::acceder : identifiant absent");
        if i != self.queue {
            self.detacher(i);
            self.accrocher_en_queue(i);
        }
    }

    fn inserer(&mut self, id: Id, _t: u64) {
        assert!(!self.index.contains_key(&id), "Lru::inserer : identifiant déjà présent {id:?}");
        let noeud = Noeud { id, prec: NUL, suiv: NUL };
        let i = match self.libres.pop() {
            Some(i) => {
                self.noeuds[i as usize] = noeud;
                i
            }
            None => {
                self.noeuds.push(noeud);
                (self.noeuds.len() - 1) as u32
            }
        };
        self.index.insert(id, i);
        self.accrocher_en_queue(i);
    }

    fn retirer(&mut self, id: Id) {
        let i = self.index.remove(&id).expect("Lru::retirer : identifiant absent");
        self.detacher(i);
        self.libres.push(i);
    }

    fn victime(&mut self, epingle: &dyn Fn(Id) -> bool) -> Option<Id> {
        let mut i = self.tete;
        while i != NUL {
            let n = self.noeuds[i as usize];
            if !epingle(n.id) {
                return Some(n.id);
            }
            i = n.suiv;
        }
        None
    }
}

/// Belady (MIN) : on évince le présent non épinglé dont le prochain usage est le plus lointain ;
/// égalité (même prochain groupe, ou jamais plus) : le plus petit identifiant (couche, expert),
/// soit l'ordre du tas de `g_belady` dans `outils/gptoss_localite.py` (clé `l · E + e`).
///
/// L'instant `t` est l'indice du groupe d'accès dans l'ordre du calcul, `t = jeton · L + couche`,
/// la convention de [`crate::rejouer`]. Construit depuis la trace : il connaît l'avenir, il ne sert
/// qu'au simulateur (borne haute du succès, témoin Belady ≥ LRU).
#[derive(Clone, Debug)]
pub struct Belady {
    /// Pour chaque identifiant, les instants où il est demandé, croissants.
    usages: HashMap<Id, Vec<u64>>,
    presents: Vec<Id>,
    rang: HashMap<Id, usize>,
    /// Pour chaque présent, son prochain usage strictement après son dernier accès.
    prochain: HashMap<Id, u64>,
}

impl Belady {
    /// Construit l'oracle depuis une trace (instants `t = jeton · L + couche`).
    pub fn depuis_trace(trace: &crate::Trace) -> Self {
        let mut usages: HashMap<Id, Vec<u64>> = HashMap::new();
        let l = trace.couches as usize;
        for t in 0..trace.jetons as usize {
            for c in 0..l {
                let instant = (t * l + c) as u64;
                for &e in trace.groupe(t, c) {
                    let v = usages.entry((c as u16, e)).or_default();
                    if v.last() != Some(&instant) {
                        v.push(instant);
                    }
                }
            }
        }
        Belady { usages, presents: Vec::new(), rang: HashMap::new(), prochain: HashMap::new() }
    }

    /// Le premier usage de `id` strictement après `t` ; `u64::MAX` s'il n'y en a plus.
    ///
    /// Correction de la première passe (2026-10-15, témoin O1) : la première version cherchait le
    /// premier usage à partir d'un « maintenant » mis à jour par `acceder` et `inserer`. Or le cache
    /// choisit sa victime AVANT d'insérer le défaut : quand le premier expert d'un groupe manque,
    /// « maintenant » vaut encore l'instant du groupe précédent, et un expert servi à ce groupe-là
    /// (désépinglé depuis) semblait redemandé tout de suite et n'était jamais évincé. Mesuré : 10 à
    /// 6 646 succès de moins que `g_belady` et `cache_belady`, LRU exact partout. Le prochain usage
    /// se calcule désormais au moment de l'accès, comme le fait l'outil Python : un présent non
    /// épinglé n'a pas été servi depuis son dernier accès, donc ce chiffre reste juste.
    fn prochain_apres(&self, id: Id, t: u64) -> u64 {
        match self.usages.get(&id) {
            None => u64::MAX,
            Some(v) => {
                let i = v.partition_point(|&x| x <= t);
                v.get(i).copied().unwrap_or(u64::MAX)
            }
        }
    }
}

impl Politique for Belady {
    fn acceder(&mut self, id: Id, t: u64) {
        debug_assert!(self.rang.contains_key(&id));
        let p = self.prochain_apres(id, t);
        self.prochain.insert(id, p);
    }

    fn inserer(&mut self, id: Id, t: u64) {
        assert!(!self.rang.contains_key(&id), "Belady::inserer : identifiant déjà présent {id:?}");
        self.rang.insert(id, self.presents.len());
        self.presents.push(id);
        let p = self.prochain_apres(id, t);
        self.prochain.insert(id, p);
    }

    fn retirer(&mut self, id: Id) {
        let i = self.rang.remove(&id).expect("Belady::retirer : identifiant absent");
        self.presents.swap_remove(i);
        if i < self.presents.len() {
            self.rang.insert(self.presents[i], i);
        }
        self.prochain.remove(&id);
    }

    fn victime(&mut self, epingle: &dyn Fn(Id) -> bool) -> Option<Id> {
        let mut meilleur: Option<(u64, Id)> = None;
        for &id in &self.presents {
            if epingle(id) {
                continue;
            }
            let p = self.prochain[&id];
            meilleur = match meilleur {
                None => Some((p, id)),
                Some((bp, bid)) if p > bp || (p == bp && id < bid) => Some((p, id)),
                m => m,
            };
        }
        meilleur.map(|(_, id)| id)
    }
}
