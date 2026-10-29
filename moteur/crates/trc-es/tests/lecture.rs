//! Témoins de `trc-es` (étape E1 ; critères déclarés dans `moteur/REPRISE-E.md` avant le premier
//! lancement). Un fichier de motif connu est écrit dans le dossier temporaire, puis relu par le
//! lecteur sans tampon ; chaque page est comparée au motif recalculé. Cassure : l'attendu décalé
//! d'une page (ou un octet faussé) doit faire tomber la comparaison.

use std::io::Write;
use std::path::PathBuf;

use trc_es::*;
use windows_sys::Win32::System::Memory::{MEM_COMMIT, MEM_RELEASE, MEM_RESERVE, PAGE_READWRITE, VirtualAlloc, VirtualFree};

/// Tampon aligné sur la page (VirtualAlloc), comme la mémoire épinglée du moteur.
struct Tampon {
    p: *mut u8,
    octets: usize,
}

impl Tampon {
    fn nouveau(octets: usize) -> Tampon {
        let p = unsafe { VirtualAlloc(std::ptr::null(), octets, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE) } as *mut u8;
        assert!(!p.is_null());
        Tampon { p, octets }
    }
    fn tranche(&self) -> &[u8] {
        unsafe { std::slice::from_raw_parts(self.p, self.octets) }
    }
}

impl Drop for Tampon {
    fn drop(&mut self) {
        unsafe { VirtualFree(self.p as _, 0, MEM_RELEASE) };
    }
}

/// L'octet d'indice absolu `i` du fichier de motif : un mélange de l'indice (sans période courte).
fn octet_motif(i: u64) -> u8 {
    let mut x = i.wrapping_add(0x9E37_79B9_7F4A_7C15);
    x = (x ^ (x >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    (x ^ (x >> 31)) as u8
}

/// Témoin des témoins : `TRC_E_CASSER=<nom>` force à faux la condition du témoin `<nom>` (le test
/// doit alors échouer ; `mesures/moteur/E/temoins_des_temoins.py` le vérifie, un nom à la fois).
fn casser(nom: &str) -> bool {
    std::env::var("TRC_E_CASSER").is_ok_and(|v| v == nom)
}

fn ecarts(tampon: &[u8], debut: u64) -> usize {
    tampon.iter().enumerate().filter(|&(k, &b)| b != octet_motif(debut + k as u64)).count()
}

/// Taille volontairement non multiple de 4 096 : la dernière page est partielle.
const TAILLE: u64 = (24 << 20) + 1234;

fn fichier_de_motif(nom: &str) -> PathBuf {
    let chemin = std::env::temp_dir().join(format!("trc-es-{nom}-{}.bin", std::process::id()));
    let mut f = std::io::BufWriter::new(std::fs::File::create(&chemin).unwrap());
    let mut page = vec![0u8; 1 << 16];
    let mut i = 0u64;
    while i < TAILLE {
        let n = ((TAILLE - i) as usize).min(page.len());
        for (k, b) in page[..n].iter_mut().enumerate() {
            *b = octet_motif(i + k as u64);
        }
        f.write_all(&page[..n]).unwrap();
        i += n as u64;
    }
    f.flush().unwrap();
    chemin
}

fn tout_recolter(l: &Lecteur, sortie: &mut Vec<Achevement>) {
    while l.en_vol() > 0 {
        l.recolter(10_000, sortie).unwrap();
    }
}

#[test]
fn lectures_alignees_profondeur_et_file() {
    let chemin = fichier_de_motif("file");
    let l = Lecteur::ouvrir(&chemin, 2).unwrap();
    assert_eq!(l.taille(), TAILLE);
    // 12 lectures de 1 Mio à des décalages mélangés, profondeur 2 : 10 attendent dans la file.
    let bloc = 1u32 << 20;
    let tampons: Vec<Tampon> = (0..12).map(|_| Tampon::nouveau(bloc as usize)).collect();
    let decalages: Vec<u64> = (0..12u64).map(|k| ((k * 7) % 23) * bloc as u64).collect();
    for (k, t) in tampons.iter().enumerate() {
        l.soumettre(Requete { jeton: 100 + k as u64, decalage: decalages[k], longueur: bloc, destination: t.p }).unwrap();
    }
    assert_eq!(l.en_vol(), 12, "confiées + en attente");
    let mut sortie = Vec::new();
    tout_recolter(&l, &mut sortie);
    assert_eq!(sortie.len(), 12);
    let mut jetons: Vec<u64> = sortie.iter().map(|a| a.jeton).collect();
    jetons.sort();
    assert_eq!(jetons, (100..112).collect::<Vec<_>>());
    for a in &sortie {
        assert_eq!(a.erreur, None);
        assert_eq!(a.octets, bloc);
        let k = (a.jeton - 100) as usize;
        let attendu = decalages[k] + if casser("lecture") && k == 5 { 4096 } else { 0 };
        assert_eq!(ecarts(tampons[k].tranche(), attendu), 0, "lecture {k}");
    }
    assert_eq!(l.octets_lus(), 12 * bloc as u64);

    // Cassure : l'attendu décalé d'une page doit tomber sur presque tous les octets ; un octet
    // faussé dans le tampon doit donner exactement un écart.
    let t0 = &tampons[0];
    assert!(ecarts(t0.tranche(), decalages[0] + 4096) > (bloc as usize) * 99 / 100);
    unsafe { *t0.p.add(777) ^= 0x5A };
    assert_eq!(ecarts(t0.tranche(), decalages[0]), 1);
    drop(l);
    std::fs::remove_file(chemin).ok();
}

#[test]
fn derniere_page_partielle_et_refus() {
    let chemin = fichier_de_motif("fin");
    let l = Lecteur::ouvrir(&chemin, 4).unwrap();
    let t = Tampon::nouveau(1 << 20);
    let debut = (TAILLE / 4096) * 4096 - 8192; // deux pages pleines, puis la page partielle
    l.soumettre(Requete { jeton: 1, decalage: debut, longueur: 1 << 20, destination: t.p }).unwrap();
    let mut sortie = Vec::new();
    tout_recolter(&l, &mut sortie);
    assert_eq!(sortie[0].octets as u64, TAILLE - debut, "lecture au-delà de la fin : octets réellement présents");
    let fin_attendue = TAILLE - debut + if casser("fin") { 1 } else { 0 };
    assert_eq!(ecarts(&t.tranche()[..fin_attendue.min(1 << 20) as usize], debut), 0, "dernière page partielle");

    // Refus avant le système : décalage, longueur, destination non alignés, longueur nulle.
    for r in [
        Requete { jeton: 2, decalage: 512, longueur: 4096, destination: t.p },
        Requete { jeton: 3, decalage: 0, longueur: 4000, destination: t.p },
        Requete { jeton: 4, decalage: 0, longueur: 4096, destination: unsafe { t.p.add(16) } },
        Requete { jeton: 5, decalage: 0, longueur: 0, destination: t.p },
    ] {
        assert!(matches!(l.soumettre(r), Err(Erreur::Usage(_))), "requête {} acceptée", r.jeton);
    }
    assert_eq!(l.en_vol(), 0);
    // Lecture qui commence au-delà de la fin : erreur du système (immédiate ou à l'achèvement).
    let loin = Requete { jeton: 6, decalage: TAILLE.div_ceil(4096) * 4096 + (1 << 20), longueur: 4096, destination: t.p };
    match l.soumettre(loin) {
        Err(Erreur::Systeme { .. }) => {}
        Ok(()) => {
            let mut s = Vec::new();
            tout_recolter(&l, &mut s);
            assert!(s[0].erreur.is_some() || s[0].octets == 0, "{:?}", s[0]);
        }
        Err(e) => panic!("{e}"),
    }
    assert!(matches!(Lecteur::ouvrir(&chemin, 0), Err(Erreur::Usage(_))));
    assert!(matches!(Lecteur::ouvrir(&chemin.with_extension("absent"), 1), Err(Erreur::Systeme { appel: "CreateFileW", .. })));
    drop(l);
    std::fs::remove_file(chemin).ok();
}

/// Abandonner un lecteur avec des lectures en vol : il annule et attend avant de libérer.
#[test]
fn abandon_en_vol() {
    let chemin = fichier_de_motif("abandon");
    let t: Vec<Tampon> = (0..8).map(|_| Tampon::nouveau(1 << 20)).collect();
    {
        let l = Lecteur::ouvrir(&chemin, 3).unwrap();
        for (k, b) in t.iter().enumerate() {
            l.soumettre(Requete { jeton: k as u64, decalage: (k as u64) << 20, longueur: 1 << 20, destination: b.p }).unwrap();
        }
    }
    std::fs::remove_file(chemin).ok();
}

/// Deux fils : l'un soumet pendant que l'autre récolte (le verrou n'est pas tenu pendant l'attente).
#[test]
fn soumission_et_recolte_concurrentes() {
    let chemin = fichier_de_motif("fils");
    let l = Lecteur::ouvrir(&chemin, 4).unwrap();
    let t: Vec<Tampon> = (0..20).map(|_| Tampon::nouveau(1 << 20)).collect();
    let adresses: Vec<usize> = t.iter().map(|b| b.p as usize).collect();
    let mut sortie = Vec::new();
    std::thread::scope(|s| {
        s.spawn(|| {
            for (k, &a) in adresses.iter().enumerate() {
                l.soumettre(Requete { jeton: k as u64, decalage: ((k as u64) % 24) << 20, longueur: 1 << 20, destination: a as *mut u8 }).unwrap();
            }
        });
        while sortie.len() < 20 {
            l.recolter(50, &mut sortie).unwrap();
        }
    });
    for a in &sortie {
        let decale = if casser("fils") && a.jeton == 7 { 1 } else { 0 };
        assert_eq!(ecarts(t[a.jeton as usize].tranche(), (((a.jeton) % 24) << 20) + decale), 0);
    }
    drop(l);
    std::fs::remove_file(chemin).ok();
}
