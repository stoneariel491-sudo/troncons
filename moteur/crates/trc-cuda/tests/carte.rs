//! Témoins de `trc-cuda` sur la carte (étape E1, ARCHITECTURE.md § 6.5, critères déclarés dans
//! `moteur/REPRISE-E.md` avant le premier lancement). Essais de justesse courts : sans le verrou
//! de la carte. Chaque témoin a sa cassure dans le même test : on fausse la condition, on vérifie
//! que l'instrument la voit, puis on vérifie qu'il tient sans elle.

use std::ffi::c_void;

use trc_cuda::*;

/// Deux noyaux PTX écrits à la main (aucune dépendance à nvcc pour les témoins de la crate) :
/// `remplir_affine` : `sortie[i] = a · i + b` pour `i < n`, en arithmétique modulo 2³² ;
/// `copier_mots` : `dst[i] = src[i]` pour `i < n` mots de 32 bits.
const PTX_AFFINE: &str = r#"
.version 8.0
.target sm_89
.address_size 64

.visible .entry remplir_affine(
    .param .u64 p_sortie,
    .param .u32 p_n,
    .param .u32 p_a,
    .param .u32 p_b
)
{
    .reg .pred %p<2>;
    .reg .b32 %r<8>;
    .reg .b64 %rd<4>;

    ld.param.u64 %rd1, [p_sortie];
    ld.param.u32 %r1, [p_n];
    ld.param.u32 %r2, [p_a];
    ld.param.u32 %r3, [p_b];
    mov.u32 %r4, %ctaid.x;
    mov.u32 %r5, %ntid.x;
    mov.u32 %r6, %tid.x;
    mad.lo.u32 %r4, %r4, %r5, %r6;
    setp.ge.u32 %p1, %r4, %r1;
    @%p1 bra FIN;
    mad.lo.u32 %r7, %r4, %r2, %r3;
    cvta.to.global.u64 %rd2, %rd1;
    mul.wide.u32 %rd3, %r4, 4;
    add.s64 %rd2, %rd2, %rd3;
    st.global.u32 [%rd2], %r7;
FIN:
    ret;
}

.visible .entry copier_mots(
    .param .u64 p_dst,
    .param .u64 p_src,
    .param .u32 p_n
)
{
    .reg .pred %p<2>;
    .reg .b32 %r<6>;
    .reg .b64 %rd<6>;

    ld.param.u64 %rd1, [p_dst];
    ld.param.u64 %rd2, [p_src];
    ld.param.u32 %r1, [p_n];
    mov.u32 %r2, %ctaid.x;
    mov.u32 %r3, %ntid.x;
    mov.u32 %r4, %tid.x;
    mad.lo.u32 %r2, %r2, %r3, %r4;
    setp.ge.u32 %p1, %r2, %r1;
    @%p1 bra FIN_COPIE;
    mul.wide.u32 %rd3, %r2, 4;
    cvta.to.global.u64 %rd4, %rd2;
    add.s64 %rd4, %rd4, %rd3;
    ld.global.u32 %r5, [%rd4];
    cvta.to.global.u64 %rd5, %rd1;
    add.s64 %rd5, %rd5, %rd3;
    st.global.u32 [%rd5], %r5;
FIN_COPIE:
    ret;
}
"#;

fn motif(graine: u64, octets: usize) -> Vec<u8> {
    // xorshift64* : un motif sans période courte, pour qu'un décalage d'octets se voie.
    let mut x = graine | 1;
    (0..octets)
        .map(|_| {
            x ^= x >> 12;
            x ^= x << 25;
            x ^= x >> 27;
            (x.wrapping_mul(0x2545_F491_4F6C_DD1D) >> 56) as u8
        })
        .collect()
}

/// Témoin des témoins : `TRC_E_CASSER=<nom>` force à faux la condition du témoin `<nom>` (le test
/// doit alors échouer ; `mesures/moteur/E/temoins_des_temoins.py` le vérifie, un nom à la fois).
fn casser(nom: &str) -> bool {
    std::env::var("TRC_E_CASSER").is_ok_and(|v| v == nom)
}

fn ecarts(a: &[u8], b: &[u8]) -> usize {
    a.iter().zip(b).filter(|(x, y)| x != y).count() + a.len().abs_diff(b.len())
}

#[test]
fn contexte_et_attributs() {
    let c = Contexte::nouveau(0).expect("contexte");
    let (libre, totale) = c.memoire();
    assert!(totale > 0 && libre <= totale, "mémoire ({libre}, {totale})");
    let maj = c.attribut(Attribut::CapaciteMajeure).unwrap();
    let min = c.attribut(Attribut::CapaciteMineure).unwrap();
    assert!(maj >= 5, "capacité {maj}.{min}");
    assert_eq!(c.attribut(Attribut::ProjectionHote).unwrap(), 1, "la carte doit pouvoir projeter la mémoire hôte");
    assert!(c.version_pilote() >= 12000, "pilote {}", c.version_pilote());
    eprintln!(
        "carte {} {maj}.{min}, pilote {}, VRAM {} / {} Mio, moteurs de copie {}, TCC {}",
        c.nom(),
        c.version_pilote(),
        libre >> 20,
        totale >> 20,
        c.attribut(Attribut::MoteursDeCopie).unwrap(),
        c.attribut(Attribut::PiloteTcc).unwrap()
    );
}

/// Aller-retour hôte → carte → hôte, tailles non rondes, décalages non nuls.
/// Cassure : un octet de la VRAM faussé entre les deux copies doit apparaître à l'arrivée.
#[test]
fn aller_retour_et_cassure() {
    let c = Contexte::nouveau(0).unwrap();
    let f = Flux::nouveau(&c, false).unwrap();
    for &(octets, decalage) in &[(1usize, 0usize), (4097, 4096), (1 << 20, 12_288), ((3 << 20) + 17, 8192)] {
        let source = motif(octets as u64 * 31 + 7, octets);
        let mut h = HoteEpingle::allouer(&c, decalage + octets, false).unwrap();
        assert_eq!(h.pointeur() as usize % 4096, 0, "adresse épinglée non alignée");
        assert_eq!(h.octets() % 4096, 0, "longueur non arrondie");
        h.tranche_mut()[decalage..decalage + octets].copy_from_slice(&source);
        let d = MemoireCarte::allouer(&c, octets).unwrap();
        copier_vers_carte(d.vue(0, octets), &h, decalage, octets, &f).unwrap();
        let mut retour = HoteEpingle::allouer(&c, octets + 4096, false).unwrap();
        if casser("aller_retour") {
            d.remplir(d.vue(0, 1), !source[0], &f).unwrap();
        }
        copier_vers_hote(&mut retour, 4096, d.vue(0, octets), &f).unwrap();
        f.synchroniser().unwrap();
        assert_eq!(ecarts(&retour.tranche()[4096..4096 + octets], &source), 0, "aller-retour de {octets} octets");

        // Cassure : on retourne l'octet du milieu dans la VRAM.
        let milieu = octets / 2;
        d.remplir(d.vue(milieu, 1), !source[milieu], &f).unwrap();
        copier_vers_hote(&mut retour, 4096, d.vue(0, octets), &f).unwrap();
        f.synchroniser().unwrap();
        assert_eq!(ecarts(&retour.tranche()[4096..4096 + octets], &source), 1, "la cassure doit se voir ({octets} octets)");
    }
}

/// Deux flux ordonnés par un événement : un noyau du flux B lit la VRAM qu'une copie du flux A
/// remplit, et n'y lit l'aller entier que s'il l'attend. Cassure : sans l'attente, le noyau part
/// pendant la copie et lit des zéros (au moins en partie).
///
/// Pourquoi un noyau et pas une copie de retour : la carte de la machine n'a qu'**un** moteur de
/// copie sous WDDM (`CU_DEVICE_ATTRIBUTE_ASYNC_ENGINE_COUNT` = 1, relevé le 2026-10-15) ; deux copies
/// de sens opposés y passent l'une après l'autre dans l'ordre de soumission, si bien qu'une course
/// entre copies ne se voit jamais (première version de ce témoin : la cassure n'est pas tombée en
/// 20 essais). Le noyau, lui, tourne sur les unités de calcul, en même temps que la copie.
#[test]
fn evenements_et_ordre_entre_flux() {
    let c = Contexte::nouveau(0).unwrap();
    let a = Flux::nouveau(&c, false).unwrap();
    let b = Flux::nouveau(&c, true).unwrap();
    assert!(b.priorite() <= a.priorite(), "le flux prioritaire doit avoir le plus petit nombre");
    let m = Module::charger(&c, PTX_AFFINE.as_bytes()).unwrap();
    let copie = m.fonction(c"copier_mots").unwrap();
    let octets = 64usize << 20;
    let mots = (octets / 4) as u32;
    let source = motif(99, octets);
    let mut h = HoteEpingle::allouer(&c, octets, false).unwrap();
    h.tranche_mut().copy_from_slice(&source);
    let d = MemoireCarte::allouer(&c, octets).unwrap();
    let d2 = MemoireCarte::allouer(&c, octets).unwrap();
    let mut retour = HoteEpingle::allouer(&c, octets, false).unwrap();
    let lancer_copie = |f: &Flux| {
        let (mut dst, mut src, mut n) = (d2.tout().adresse, d.tout().adresse, mots);
        let mut args = [
            &mut dst as *mut u64 as *mut c_void,
            &mut src as *mut u64 as *mut c_void,
            &mut n as *mut u32 as *mut c_void,
        ];
        unsafe { copie.lancer([mots.div_ceil(256), 1, 1], [256, 1, 1], 0, f, &mut args).unwrap() };
    };

    let debut = Evenement::nouveau(&c, true).unwrap();
    let fin = Evenement::nouveau(&c, true).unwrap();
    let pret = Evenement::nouveau(&c, false).unwrap();
    d.remplir(d.tout(), 0, &a).unwrap();
    debut.enregistrer(&a).unwrap();
    copier_vers_carte(d.tout(), &h, 0, octets, &a).unwrap();
    fin.enregistrer(&a).unwrap();
    pret.enregistrer(&a).unwrap();
    if !casser("ordre") {
        b.attendre(&pret).unwrap();
    }
    lancer_copie(&b);
    copier_vers_hote(&mut retour, 0, d2.tout(), &b).unwrap();
    b.synchroniser().unwrap();
    assert!(fin.fini().unwrap() && pret.fini().unwrap());
    assert_eq!(ecarts(retour.tranche(), &source), 0, "le noyau ordonné doit voir l'aller entier");
    let ms = fin.ms_depuis(&debut).unwrap();
    let debit = octets as f64 / (ms as f64 * 1e-3) / 1e9;
    eprintln!("aller de 64 Mio : {ms:.3} ms, {debit:.2} Go/s (essai de justesse, pas une mesure)");
    assert!(ms > 0.0 && debit < 15.754 * 1.05, "débit {debit} Go/s au-dessus du lien PCIe 4.0 ×8");
    assert!(pret.ms_depuis(&debut).is_err(), "ms_depuis doit refuser un événement non horodaté");

    // Cassure : même chose sans l'attente entre flux. Un ordre accidentellement juste reste
    // possible : on répète jusqu'à 20 fois et on exige qu'au moins une fois l'écart se voie.
    let mut vu = 0;
    for _ in 0..20 {
        d.remplir(d.tout(), 0, &a).unwrap();
        a.synchroniser().unwrap();
        copier_vers_carte(d.tout(), &h, 0, octets, &a).unwrap();
        lancer_copie(&b);
        b.synchroniser().unwrap();
        a.synchroniser().unwrap();
        copier_vers_hote(&mut retour, 0, d2.tout(), &b).unwrap();
        b.synchroniser().unwrap();
        vu = ecarts(retour.tranche(), &source);
        if vu > 0 {
            break;
        }
    }
    eprintln!("cassure : {vu} octets faux sans l'attente");
    assert!(vu > 0, "sans attente entre flux, la course doit se voir au moins une fois sur 20");
}

/// Un module PTX chargé, un noyau lancé, résultat relu ; puis le même noyau écrit dans une
/// mémoire hôte projetée (le mécanisme de la boîte aux lettres du routeur).
#[test]
fn module_lancement_et_memoire_projetee() {
    let c = Contexte::nouveau(0).unwrap();
    let f = Flux::nouveau(&c, true).unwrap();
    let m = Module::charger(&c, PTX_AFFINE.as_bytes()).unwrap();
    let k = m.fonction(c"remplir_affine").unwrap();
    let n: u32 = 100_003;
    let (a, b) = (2_654_435_761u32, 12_345u32);
    let attendu: Vec<u32> = (0..n).map(|i| i.wrapping_mul(a).wrapping_add(b)).collect();

    let d = MemoireCarte::allouer(&c, n as usize * 4).unwrap();
    let mut adresse = d.tout().adresse;
    let (mut nn, mut aa, mut bb) = (n, a, if casser("module") { b ^ 1 } else { b });
    let mut args = [
        &mut adresse as *mut u64 as *mut c_void,
        &mut nn as *mut u32 as *mut c_void,
        &mut aa as *mut u32 as *mut c_void,
        &mut bb as *mut u32 as *mut c_void,
    ];
    unsafe { k.lancer([n.div_ceil(256), 1, 1], [256, 1, 1], 0, &f, &mut args).unwrap() };
    let mut h = HoteEpingle::allouer(&c, n as usize * 4, false).unwrap();
    copier_vers_hote(&mut h, 0, d.tout(), &f).unwrap();
    f.synchroniser().unwrap();
    let lu: Vec<u32> = h.tranche()[..n as usize * 4].as_chunks::<4>().0.iter().map(|x| u32::from_le_bytes(*x)).collect();
    assert_eq!(lu, attendu, "sortie du noyau");

    // Mémoire projetée : le noyau écrit directement dans la RAM de l'hôte.
    let p = HoteEpingle::allouer(&c, n as usize * 4, true).unwrap();
    let mut adresse = p.adresse_carte().expect("adresse projetée");
    bb = if casser("projetee") { b } else { b + 1 };
    let mut args = [
        &mut adresse as *mut u64 as *mut c_void,
        &mut nn as *mut u32 as *mut c_void,
        &mut aa as *mut u32 as *mut c_void,
        &mut bb as *mut u32 as *mut c_void,
    ];
    let e = Evenement::nouveau(&c, false).unwrap();
    unsafe { k.lancer([n.div_ceil(256), 1, 1], [256, 1, 1], 0, &f, &mut args).unwrap() };
    e.enregistrer(&f).unwrap();
    e.attendre().unwrap();
    for i in [0usize, 1, 4095, n as usize - 1] {
        assert_eq!(p.lire_volatil_u32(4 * i), attendu[i].wrapping_add(1), "mémoire projetée, indice {i}");
    }
}

#[test]
fn erreurs_nommees() {
    let c = Contexte::nouveau(0).unwrap();
    // Une image fausse : le pilote refuse, l'erreur porte l'appel et le nom du code.
    match Module::charger(&c, b"ceci n'est pas un module") {
        Err(Erreur::Cuda { appel, nom, .. }) => {
            assert_eq!(appel, "cuModuleLoadDataEx");
            assert!(nom.starts_with("CUDA_ERROR"), "{nom}");
        }
        autre => panic!("attendu une erreur du pilote, reçu {:?}", autre.err()),
    }
    let m = Module::charger(&c, PTX_AFFINE.as_bytes()).unwrap();
    assert!(matches!(m.fonction(c"absente"), Err(Erreur::Cuda { .. })));
    let f = Flux::nouveau(&c, false).unwrap();
    let h = HoteEpingle::allouer(&c, 4096, false).unwrap();
    let d = MemoireCarte::allouer(&c, 4096).unwrap();
    assert!(matches!(copier_vers_carte(d.tout(), &h, 1, 4096, &f), Err(Erreur::Usage(_))));
    assert!(matches!(MemoireCarte::allouer(&c, 0), Err(Erreur::Usage(_))));
    assert!(std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| d.vue(4000, 97))).is_err(), "une vue hors de l'allocation doit paniquer");
}

/// Les objets gardent le contexte : abandonner le contexte avant eux ne doit rien casser.
#[test]
fn duree_de_vie_du_contexte() {
    let c = Contexte::nouveau(0).unwrap();
    let f = Flux::nouveau(&c, false).unwrap();
    let d = MemoireCarte::allouer(&c, 1 << 16).unwrap();
    drop(c);
    d.remplir(d.tout(), 7, &f).unwrap();
    f.synchroniser().unwrap();
    // Un autre fil utilise le même flux : le contexte y devient courant de lui-même.
    std::thread::scope(|s| {
        s.spawn(|| {
            d.remplir(d.vue(0, 16), 9, &f).unwrap();
            f.synchroniser().unwrap();
        });
    });
}
