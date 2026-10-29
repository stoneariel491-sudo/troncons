//! Témoins de trc-cache. Chacun a sa réponse connue d'avance ; ceux qui peuvent tomber ont été
//! forcés à faux une fois (journal : mesures/moteur/O/journaux/tests-casses.txt).

use super::*;

/// splitmix64 : un générateur sans dépendance, reproductible.
struct Alea(u64);
impl Alea {
    fn suivant(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    fn sous(&mut self, n: u64) -> u64 {
        self.suivant() % n
    }
    fn reel(&mut self) -> f64 {
        (self.suivant() >> 11) as f64 / (1u64 << 53) as f64
    }
}

/// Routage « collant » (celui du témoin T3 de l'étude 04) : chaque place garde son expert avec la
/// probabilité rho, sinon tire un expert absent de l'ensemble courant.
fn trace_collante(t: u32, l: u16, e: u16, k: u16, rho: f64, graine: u64) -> Trace {
    let mut a = Alea(graine);
    let mut etat: Vec<Vec<u16>> = (0..l)
        .map(|_| {
            let mut s = Vec::new();
            while s.len() < k as usize {
                let x = a.sous(e as u64) as u16;
                if !s.contains(&x) {
                    s.push(x);
                }
            }
            s
        })
        .collect();
    let mut choix = Vec::new();
    for _ in 0..t {
        for s in etat.iter_mut() {
            for i in 0..k as usize {
                if a.reel() >= rho {
                    loop {
                        let x = a.sous(e as u64) as u16;
                        if !s.contains(&x) {
                            s[i] = x;
                            break;
                        }
                    }
                }
            }
            choix.extend_from_slice(s);
        }
    }
    Trace { experts: e, couches: l, k, jetons: t, choix, commentaires: vec![] }
}

fn trace_figee(t: u32, l: u16, k: u16) -> Trace {
    let mut choix = Vec::new();
    for _ in 0..t {
        for c in 0..l {
            choix.extend(c..c + k);
        }
    }
    Trace { experts: 32, couches: l, k, jetons: t, choix, commentaires: vec![] }
}

/// G1a de gptoss_localite.py, réponses exactes : routage figé, boucle de L·k clés.
/// N = (L−1)·k → 0 succès ; N = L·k − 1 → (k−1)·L·(T−1) ; N = L·k → L·k·(T−1).
#[test]
fn routage_fige_reponses_exactes() {
    let (t, l, k) = (4000u32, 4u16, 4u16);
    let tr = trace_figee(t, l, k);
    let lk = (l * k) as u32;
    let c0 = rejouer(&tr, lk - k as u32, 0, Lru::default(), Lru::default());
    assert_eq!(c0.succes_vram, 0);
    let c1 = rejouer(&tr, lk - 1, 0, Lru::default(), Lru::default());
    assert_eq!(c1.succes_vram, (k as u64 - 1) * l as u64 * (t as u64 - 1));
    let c2 = rejouer(&tr, lk, 0, Lru::default(), Lru::default());
    assert_eq!(c2.succes_vram, lk as u64 * (t as u64 - 1));
    assert_eq!(c2.evictions, 0);
    for c in [c0, c1, c2] {
        assert_eq!(c.acces(), tr.acces());
    }
}

/// Un cache d'exactement k emplacements sert toute couche : les k experts sont présents ensemble
/// après la demande (aucun épinglé n'est évincé), et le cache n'est jamais trop petit.
/// Une seule couche, pour que les succès soient fréquents : un expert du groupe pas encore servi
/// est alors le plus ancien du LRU, la victime que l'épinglage doit interdire. Réponse connue : avec
/// L = 1 et k emplacements, le cache contient exactement le groupe précédent, donc les succès du
/// groupe t sont |S_t ∩ S_{t−1}|. (Première version : six couches dans quatre emplacements, aucun
/// succès possible ; puis une seule couche mais seul le contenu final vérifié, qui reste juste sans
/// épinglage, car l'expert évincé avant son tour est relu ; la cassure de l'épinglage ne faisait
/// tomber ni l'une ni l'autre ; mesuré par casser_tests.py.)
#[test]
fn epinglage_tient_les_k_experts_ensemble() {
    let tr = trace_collante(2000, 1, 12, 4, 0.5, 7);
    let mut cache = Cache::nouveau(4, 0, Lru::default(), Lru::default());
    let mut precedent: Vec<u16> = Vec::new();
    for t in 0..tr.jetons as usize {
        for c in 0..tr.couches as usize {
            let g = tr.groupe(t, c);
            let d = cache.demander(c as u16, g, 0);
            let succes = d.iter().filter(|x| matches!(x, Decision::Succes { .. })).count();
            assert_eq!(succes, g.iter().filter(|e| precedent.contains(e)).count(), "jeton {t}");
            precedent = g.to_vec();
            for (i, &e) in g.iter().enumerate() {
                let s = cache.emplacement_de((c as u16, e)).expect("expert épinglé évincé");
                let s_d = match d[i] {
                    Decision::Succes { emplacement }
                    | Decision::DefautRam { emplacement, .. }
                    | Decision::DefautDisque { emplacement, .. } => emplacement,
                };
                assert_eq!(s, s_d);
                assert_eq!(cache.occupant(s), Some((c as u16, e)));
            }
            for x in d {
                if let Decision::DefautDisque { emplacement, tiede } = x {
                    assert_eq!(tiede, None);
                    cache.pret(emplacement);
                }
            }
            cache.liberer(c as u16);
        }
    }
}

/// Un emplacement en vol n'est jamais évincé, même désépinglé.
#[test]
#[should_panic(expected = "aucun emplacement VRAM libre ni évinçable")]
fn en_vol_jamais_evince() {
    let mut cache = Cache::nouveau(1, 0, Lru::default(), Lru::default());
    let _ = cache.demander(0, &[3], 0);
    cache.liberer(0); // désépinglé, mais pas « pret »
    let _ = cache.demander(1, &[5], 1);
}

/// Contrôle du précédent : une fois « pret », le même emplacement est évinçable.
#[test]
fn present_desepingle_est_evincable() {
    let mut cache = Cache::nouveau(1, 0, Lru::default(), Lru::default());
    let d = cache.demander(0, &[3], 0);
    assert_eq!(d, vec![Decision::DefautDisque { emplacement: 0, tiede: None }]);
    cache.pret(0);
    cache.liberer(0);
    let d = cache.demander(1, &[5], 1);
    assert_eq!(d, vec![Decision::DefautDisque { emplacement: 0, tiede: None }]);
    assert_eq!(cache.compteurs().evictions, 1);
    assert_eq!(cache.etat(0), Etat::EnVol { niveau: Niveau::Exact });
}

/// Règle 2 du module : avec tiedes ≥ emplacements et une politique à pile, les deux étages
/// égalent deux caches indépendants : succès VRAM = cache(emplacements), succès VRAM + RAM =
/// cache(tiedes).
#[test]
fn deux_etages_egalent_deux_caches_a_pile() {
    for graine in 0..4u64 {
        let tr = trace_collante(800, 5, 32, 4, 0.55, 100 + graine);
        for (v, r) in [(8u32, 8u32), (8, 20), (16, 40), (30, 90), (12, 160)] {
            let lru2 = rejouer(&tr, v, r, Lru::default(), Lru::default());
            let lru_v = rejouer(&tr, v, 0, Lru::default(), Lru::default());
            let lru_r = rejouer(&tr, r, 0, Lru::default(), Lru::default());
            assert_eq!(lru2.succes_vram, lru_v.succes_vram, "LRU, VRAM, {v}/{r}");
            assert_eq!(lru2.succes_vram + lru2.succes_ram, lru_r.succes_vram, "LRU, RAM, {v}/{r}");
            assert_eq!(lru2.acces(), tr.acces());
            let b2 = rejouer(&tr, v, r, Belady::depuis_trace(&tr), Belady::depuis_trace(&tr));
            let b_v = rejouer(&tr, v, 0, Belady::depuis_trace(&tr), Belady::depuis_trace(&tr));
            let b_r = rejouer(&tr, r, 0, Belady::depuis_trace(&tr), Belady::depuis_trace(&tr));
            assert_eq!(b2.succes_vram, b_v.succes_vram, "Belady, VRAM, {v}/{r}");
            assert_eq!(b2.succes_vram + b2.succes_ram, b_r.succes_vram, "Belady, RAM, {v}/{r}");
        }
    }
}

/// Belady est l'optimum hors ligne : jamais sous LRU, à capacité égale.
#[test]
fn belady_jamais_sous_lru() {
    for graine in 0..6u64 {
        let tr = trace_collante(600, 4, 64, 4, 0.3 + 0.1 * graine as f64, graine);
        for n in [4u32, 8, 16, 33, 64, 128] {
            let l = rejouer(&tr, n, 0, Lru::default(), Lru::default());
            let b = rejouer(&tr, n, 0, Belady::depuis_trace(&tr), Belady::depuis_trace(&tr));
            assert!(b.succes_vram >= l.succes_vram, "graine {graine}, N = {n}");
        }
    }
}

/// Cassure de la politique (la même que le témoin O1) : un LRU qui ignore les succès devient FIFO
/// et doit donner un autre compte sur une trace qui a de la localité.
struct Fifo(Lru);
impl Politique for Fifo {
    fn acceder(&mut self, _id: Id, _t: u64) {}
    fn inserer(&mut self, id: Id, t: u64) {
        self.0.inserer(id, t)
    }
    fn retirer(&mut self, id: Id) {
        self.0.retirer(id)
    }
    fn victime(&mut self, e: &dyn Fn(Id) -> bool) -> Option<Id> {
        self.0.victime(e)
    }
}

#[test]
fn politique_faussee_donne_un_autre_compte() {
    let tr = trace_collante(1000, 4, 64, 4, 0.6, 3);
    let l = rejouer(&tr, 32, 0, Lru::default(), Lru::default());
    let f = rejouer(&tr, 32, 0, Fifo(Lru::default()), Fifo(Lru::default()));
    assert_ne!(l.succes_vram, f.succes_vram);
}

#[test]
fn lru_ordre_et_victime() {
    let mut p = Lru::default();
    for e in 0..4u16 {
        p.inserer((0, e), 0);
    }
    p.acceder((0, 1), 1);
    assert_eq!(p.ordre(), vec![(0, 0), (0, 2), (0, 3), (0, 1)]);
    assert_eq!(p.victime(&|_| false), Some((0, 0)));
    assert_eq!(p.victime(&|id| id == (0, 0)), Some((0, 2)));
    p.retirer((0, 2));
    p.inserer((0, 9), 2);
    assert_eq!(p.ordre(), vec![(0, 0), (0, 3), (0, 1), (0, 9)]);
    assert_eq!(p.victime(&|_| true), None);
}

#[test]
fn trace_lue_comme_l_outil_python() {
    let tr = Trace::depuis_texte("# source\nE=32\n3 17 | 5 9\n\n3 31 | 5 2\n").unwrap();
    assert_eq!((tr.experts, tr.couches, tr.k, tr.jetons), (32, 2, 2, 2));
    assert_eq!(tr.groupe(1, 0), &[3, 31]);
    assert_eq!(tr.groupe(1, 1), &[5, 2]);
    assert_eq!(tr.commentaires, vec!["source".to_string()]);
    // sans « E= » : E = plus grand identifiant + 1
    assert_eq!(Trace::depuis_texte("3 17 | 5 9").unwrap().experts, 18);
}

#[test]
fn trace_mal_formee_refusee() {
    assert!(matches!(Trace::depuis_texte("1 2 | 3 4\n1 2\n"), Err(ErreurTrace::Ligne { numero: 2, .. })));
    assert!(matches!(Trace::depuis_texte("1 2 | 3 4\n1 2 | 3\n"), Err(ErreurTrace::Ligne { numero: 2, .. })));
    assert!(matches!(Trace::depuis_texte("E=4\n1 7\n"), Err(ErreurTrace::HorsBornes { expert: 7, experts: 4 })));
    assert!(matches!(Trace::depuis_texte("# rien\n"), Err(ErreurTrace::Vide)));
    assert!(matches!(Trace::depuis_texte("1 x\n"), Err(ErreurTrace::Ligne { numero: 1, .. })));
}

/// Les octets : un défaut disque compte sa taille lue et copiée ; un défaut RAM, copiée seulement.
#[test]
fn octets_comptes_par_etage() {
    let mut cache = Cache::nouveau(1, 2, Lru::default(), Lru::default());
    cache.fixer_tailles(|id| 1000 + id.1 as u64);
    for (c, e) in [(0u16, 1u16), (0, 2), (0, 1)] {
        for d in cache.demander(c, &[e], 0) {
            match d {
                Decision::DefautRam { emplacement, .. } | Decision::DefautDisque { emplacement, .. } => {
                    cache.pret(emplacement)
                }
                _ => {}
            }
        }
        cache.liberer(c);
    }
    let k = cache.compteurs();
    assert_eq!((k.succes_vram, k.succes_ram, k.defauts_disque), (0, 1, 2));
    assert_eq!(k.octets_disque, 1001 + 1002);
    assert_eq!(k.octets_copies, 1001 + 1002 + 1001);
    assert_eq!(k.evictions, 2);
}

/// Belady sur un cas calculé à la main (couche unique, k = 1, C = 2) : suite a b c a. Au défaut
/// de c, a revient au pas 3 et b jamais : MIN évince b, et a est un succès au pas 3. Ce cas fait
/// tomber la première version de `Belady` (prochain usage cherché depuis l'instant du groupe
/// précédent : b semblait redemandé « maintenant », a était évincé, 0 succès).
#[test]
fn belady_cas_calcule_a_la_main() {
    let tr = Trace::depuis_texte("E=3\n0\n1\n2\n0\n").unwrap();
    let b = rejouer(&tr, 2, 0, Belady::depuis_trace(&tr), Belady::depuis_trace(&tr));
    assert_eq!(b.succes_vram, 1);
    let l = rejouer(&tr, 2, 0, Lru::default(), Lru::default());
    assert_eq!(l.succes_vram, 0); // LRU évince a, le plus ancien
}

/// La falaise du LRU global (lemme 3 de moteur/O-pour-le-memoire.md) : dans le flux cyclique des
/// couches, entre deux usages possibles d'un expert de la couche ℓ passent les (L − 1)·k accès des
/// autres couches, tous distincts ; un LRU de N ≤ (L − 1)·k emplacements l'a donc toujours évincé :
/// **0 succès exactement, quel que soit le routage**. Mesuré sur les traces réelles de 20b
/// (N = 38 et 77 < 92 : 0 succès, mesures/moteur/O/csv/succes-20b-rejouer.csv). Au-delà, des succès
/// apparaissent dès qu'un routage réutilise ses experts.
#[test]
fn falaise_du_lru_global() {
    for graine in 0..4u64 {
        let (l, k) = (6u16, 4u16);
        let tr = trace_collante(700, l, 16, k, 0.7, 40 + graine);
        let seuil = ((l - 1) * k) as u32;
        for n in [k as u32, 7, 13, seuil] {
            assert_eq!(rejouer(&tr, n, 0, Lru::default(), Lru::default()).succes_vram, 0, "N = {n}");
        }
        assert!(rejouer(&tr, seuil + 1, 0, Lru::default(), Lru::default()).succes_vram > 0);
        // Belady, lui, garde des experts au-dessous de la falaise.
        assert!(rejouer(&tr, seuil, 0, Belady::depuis_trace(&tr), Belady::depuis_trace(&tr)).succes_vram > 0);
    }
}
