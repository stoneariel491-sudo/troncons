//! Banc de la RAM : débit de lecture, d'écriture et de copie, de 1 à N fils, et latence
//! d'un accès dépendant (chasse de pointeurs sur un cycle aléatoire).
//!
//! Usage : memoire [--taille 256M] [--fils 1,2,4,8,16] [--passes 5] [--fausser] [--sans-verrou] [--neuf]
//!   --sans-verrou : ne verrouille pas les tampons en RAM ; --neuf : tampon neuf à chaque passe de
//!   lecture (témoin des fautes de page forcé à faux).
//!
//! Témoin : le tampon lu porte un motif dont la somme est connue d'avance
//! (mot i = i, somme = n(n-1)/2 modulo 2^64). `--fausser` décale l'attendu d'une unité :
//! le témoin doit alors échouer. Chaque débit se compare au plafond du module (41,6 Go/s) :
//! un dépassement veut dire que le tampon tient en cache, et l'instrument tombe.
//! Sortie : lignes `RESULTAT clé=valeur`.

use banc::*;
use std::time::Instant;

const PLAFOND_GO_S: f64 = 41.6;

fn main() {
    let a = Args::lire();
    let taille = a.nombre("taille", 256.0 * 1024.0 * 1024.0) as usize;
    let passes = a.nombre("passes", 5.0) as usize;
    let fausser = a.drapeau("fausser");
    let fils: Vec<usize> = a.texte("fils", "1,2,4,8,16").split(',').map(|s| s.parse().unwrap()).collect();
    let n = taille / 8;

    let sans_verrou = a.drapeau("sans-verrou");
    let neuf = a.drapeau("neuf");
    let mut src: Vec<u64> = (0..n as u64).collect();
    let mut dst: Vec<u64> = vec![0u64; n];
    let attendu = (n as u64).wrapping_mul(n as u64 - 1) / 2 + if fausser { 1 } else { 0 };

    // Verrou des pages. Quand la RAM libre est maigre, Windows retire des pages de l'ensemble de
    // travail et les compresse (magasin de compression) : une lecture « de RAM » paie alors une
    // faute de page et une décompression. Mesure 1 du 2026-10-15 : latence 1,2 µs au lieu de
    // ~0,1 µs. On relève donc le plancher de l'ensemble de travail et on verrouille les deux tampons.
    let verrou = if sans_verrou { false } else { verrouiller(&[&src[..], &dst[..]], taille) };
    println!("VERROU pages_verrouillees={verrou}");

    for &f in &fils {
        // Lecture : somme des mots, découpée en f tranches.
        let mut debits = Vec::new();
        let mut temoin_ok = true;
        let fautes0 = fautes_de_page();
        for _ in 0..passes {
            if neuf {
                // Témoin des fautes, forcé à faux : un tampon neuf à chaque passe (pages jamais
                // touchées, donc une faute par page) ; le témoin des fautes doit alors tomber.
                src = (0..n as u64).collect();
            }
            let t0 = Instant::now();
            let s = somme_parallele(&src, f);
            let dt = t0.elapsed().as_secs_f64();
            temoin_ok &= s == attendu;
            debits.push(taille as f64 / dt / 1e9);
        }
        let fautes = fautes_de_page() - fautes0;
        // Seuil déclaré : moins de 1 % des pages lues pendant les passes ont fauté.
        let pages_lues = (taille / 4096 * passes) as u64;
        println!(
            "FAUTES op=lecture fils={f} fautes={fautes} pages_lues={pages_lues} temoin_fautes={}",
            if (fautes as f64) < 0.01 * pages_lues as f64 { "ok" } else { "ECHEC" }
        );
        rapporter("lecture", f, taille, &debits, Some(temoin_ok));

        // Écriture : remplissage, f tranches.
        let mut debits = Vec::new();
        for p in 0..passes {
            let t0 = Instant::now();
            remplir_parallele(&mut dst, f, p as u64);
            let dt = t0.elapsed().as_secs_f64();
            debits.push(taille as f64 / dt / 1e9);
        }
        let ok = dst[n / 2] == (passes as u64 - 1);
        rapporter("ecriture", f, taille, &debits, Some(ok));

        // Copie : memcpy, f tranches. Octets comptés : lus + écrits.
        let mut debits = Vec::new();
        for _ in 0..passes {
            let t0 = Instant::now();
            copier_parallele(&src, &mut dst, f);
            let dt = t0.elapsed().as_secs_f64();
            debits.push(2.0 * taille as f64 / dt / 1e9);
        }
        let ok = dst[n - 1] == n as u64 - 1 && dst[7] == 7;
        rapporter("copie_lu+ecrit", f, taille, &debits, Some(ok));
    }

    // Latence : cycle aléatoire unique (permutation de Sattolo) sur tout le tampon, pas de 64 o.
    let lignes = taille / 64;
    let pas = 8; // un mot sur huit : une ligne de cache par saut
    let mut ordre: Vec<usize> = (0..lignes).collect();
    let mut etat = 0x9E37_79B9_7F4A_7C15u64;
    for i in (1..lignes).rev() {
        let j = (xorshift64star(&mut etat) % i as u64) as usize;
        ordre.swap(i, j);
    }
    for k in 0..lignes {
        src[ordre[k] * pas] = (ordre[(k + 1) % lignes] * pas) as u64;
    }
    let sauts = 20_000_000usize;
    let mut lat = Vec::new();
    let mut p = 0usize;
    for _ in 0..3 {
        let t0 = Instant::now();
        for _ in 0..sauts {
            p = src[p] as usize;
        }
        lat.push(t0.elapsed().as_secs_f64() / sauts as f64 * 1e9);
    }
    std::hint::black_box(p);
    let mut l = lat.clone();
    l.sort_by(|x, y| x.partial_cmp(y).unwrap());
    println!(
        "RESULTAT op=latence taille={taille} sauts={sauts} ns_mediane={:.1} ns_min={:.1} ns_max={:.1}",
        quantile(&l, 0.5), l[0], l[l.len() - 1]
    );
    drop(dst);
}

/// Relève le plancher de l'ensemble de travail puis verrouille chaque tampon en RAM.
fn verrouiller(tampons: &[&[u64]], taille: usize) -> bool {
    use windows_sys::Win32::System::Memory::VirtualLock;
    use windows_sys::Win32::System::Threading::{GetCurrentProcess, SetProcessWorkingSetSize};
    let marge = 256usize << 20;
    let min = tampons.len() * taille + marge;
    unsafe {
        if SetProcessWorkingSetSize(GetCurrentProcess(), min, min + marge) == 0 {
            return false;
        }
        tampons.iter().all(|t| VirtualLock(t.as_ptr() as *const _, std::mem::size_of_val(*t)) != 0)
    }
}

/// Fautes de page cumulées du processus (douces et dures).
fn fautes_de_page() -> u64 {
    use windows_sys::Win32::System::ProcessStatus::{K32GetProcessMemoryInfo, PROCESS_MEMORY_COUNTERS};
    use windows_sys::Win32::System::Threading::GetCurrentProcess;
    unsafe {
        let mut c: PROCESS_MEMORY_COUNTERS = std::mem::zeroed();
        c.cb = std::mem::size_of::<PROCESS_MEMORY_COUNTERS>() as u32;
        K32GetProcessMemoryInfo(GetCurrentProcess(), &mut c, c.cb);
        c.PageFaultCount as u64
    }
}

fn rapporter(op: &str,fils: usize, taille: usize, debits: &[f64], temoin: Option<bool>) {
    let mut d = debits.to_vec();
    d.sort_by(|x, y| x.partial_cmp(y).unwrap());
    let med = quantile(&d, 0.5);
    let plafond_ok = d[d.len() - 1] <= PLAFOND_GO_S * if op.starts_with("copie") { 1.0 } else { 1.0 };
    println!(
        "RESULTAT op={op} fils={fils} taille={taille} go_s_mediane={med:.3} go_s_min={:.3} go_s_max={:.3} temoin={} sous_plafond={}",
        d[0], d[d.len() - 1], temoin.map(|t| if t { "ok" } else { "ECHEC" }).unwrap_or("-"), plafond_ok
    );
}

fn somme_parallele(v: &[u64], f: usize) -> u64 {
    let morceau = v.len().div_ceil(f);
    std::thread::scope(|s| {
        let h: Vec<_> = v
            .chunks(morceau)
            .map(|c| {
                s.spawn(move || {
                    // Quatre accumulateurs : la dépendance d'addition ne borne pas le débit.
                    let (mut a, mut b, mut cc, mut d) = (0u64, 0u64, 0u64, 0u64);
                    let mut it = c.chunks_exact(4);
                    for q in &mut it {
                        a = a.wrapping_add(q[0]);
                        b = b.wrapping_add(q[1]);
                        cc = cc.wrapping_add(q[2]);
                        d = d.wrapping_add(q[3]);
                    }
                    let mut r = a.wrapping_add(b).wrapping_add(cc).wrapping_add(d);
                    for x in it.remainder() {
                        r = r.wrapping_add(*x);
                    }
                    r
                })
            })
            .collect();
        h.into_iter().map(|j| j.join().unwrap()).fold(0u64, |x, y| x.wrapping_add(y))
    })
}

fn remplir_parallele(v: &mut [u64], f: usize, val: u64) {
    let morceau = v.len().div_ceil(f);
    std::thread::scope(|s| {
        for c in v.chunks_mut(morceau) {
            s.spawn(move || c.fill(val));
        }
    });
}

fn copier_parallele(src: &[u64], dst: &mut [u64], f: usize) {
    let morceau = src.len().div_ceil(f);
    std::thread::scope(|s| {
        for (a, b) in src.chunks(morceau).zip(dst.chunks_mut(morceau)) {
            s.spawn(move || b.copy_from_slice(a));
        }
    });
}
