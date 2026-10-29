//! Banc du disque : lecture NVMe sans tampon (FILE_FLAG_NO_BUFFERING), séquentielle et
//! aléatoire, par port de complétion (IOCP) ou par IoRing, à profondeur de file fixée.
//!
//! Sous-commandes :
//!   preparer  --fichier F --taille 32G          écrit le fichier de test au motif vérifiable
//!   lire      --fichier F --moteur iocp|ioring|tampon --acces seq|alea --bloc 4K --qd 1
//!             [--duree 2] [--chauffe 0.5] [--region 0] [--complet 64] [--fausser]
//!   capacites --fichier F                      IoRing (version, files) et BypassIO
//!
//! Chaque lecture vérifie l'en-tête de chaque page de 4 Kio reçue (et toute la page une
//! fois sur `--complet`). `--fausser` décale l'attente d'une page : le témoin doit alors
//! compter toutes les pages fausses, sinon l'instrument ne vérifie rien.
//! Sortie : une ligne `RESULTAT clé=valeur ...` par passe, lisible par le pilote Python.

use banc::*;
use std::ptr::null_mut;
use std::time::Instant;
use windows_sys::Win32::Foundation::*;
use windows_sys::Win32::Storage::FileSystem::*;
use windows_sys::Win32::System::IO::*;
use windows_sys::Win32::System::Ioctl::*;
use windows_sys::Win32::System::Memory::*;
use windows_sys::Win32::System::Threading::*;

fn main() {
    let a = Args::lire();
    match a.positionnels.first().map(|s| s.as_str()) {
        Some("preparer") => preparer(&a),
        Some("lire") => lire(&a),
        Some("capacites") => capacites(&a),
        _ => {
            eprintln!("usage : disque preparer|lire|capacites --fichier F ...");
            std::process::exit(2);
        }
    }
}

/// Tampon aligné sur la page, alloué par VirtualAlloc (exigence de FILE_FLAG_NO_BUFFERING :
/// adresse et longueur multiples de la taille de secteur).
struct Tampon {
    ptr: *mut u8,
    len: usize,
}
unsafe impl Send for Tampon {}
impl Tampon {
    fn new(len: usize) -> Self {
        let ptr = unsafe { VirtualAlloc(null_mut(), len, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE) } as *mut u8;
        assert!(!ptr.is_null(), "VirtualAlloc a échoué ({len} octets)");
        Tampon { ptr, len }
    }
    fn tranche(&self) -> &[u8] {
        unsafe { std::slice::from_raw_parts(self.ptr, self.len) }
    }
    fn mots_mut(&mut self) -> &mut [u64] {
        unsafe { std::slice::from_raw_parts_mut(self.ptr as *mut u64, self.len / 8) }
    }
}
impl Drop for Tampon {
    fn drop(&mut self) {
        unsafe { VirtualFree(self.ptr as _, 0, MEM_RELEASE) };
    }
}

fn ouvrir(fichier: &str, ecriture: bool, drapeaux: u32) -> HANDLE {
    let nom = large(fichier);
    let h = unsafe {
        CreateFileW(
            nom.as_ptr(),
            if ecriture { GENERIC_WRITE } else { GENERIC_READ },
            FILE_SHARE_READ,
            std::ptr::null(),
            if ecriture { CREATE_ALWAYS } else { OPEN_EXISTING },
            drapeaux,
            null_mut(),
        )
    };
    if h == INVALID_HANDLE_VALUE {
        panic!("CreateFileW({fichier}) : erreur {}", unsafe { GetLastError() });
    }
    h
}

fn taille_fichier(h: HANDLE) -> u64 {
    let mut t: i64 = 0;
    unsafe { GetFileSizeEx(h, &mut t) };
    t as u64
}

fn temps_cpu_s() -> f64 {
    let (mut c, mut e, mut k, mut u) = (FILETIME::default(), FILETIME::default(), FILETIME::default(), FILETIME::default());
    unsafe { GetProcessTimes(GetCurrentProcess(), &mut c, &mut e, &mut k, &mut u) };
    let f = |t: FILETIME| ((t.dwHighDateTime as u64) << 32 | t.dwLowDateTime as u64) as f64 * 1e-7;
    f(k) + f(u)
}

// ---------------------------------------------------------------------------------------
// Préparation : quatre fils produisent les tranches de 16 Mio dans l'ordre, un écrivain les
// écrit en séquence, sans tampon et à écriture directe. Le débit d'écriture se journalise
// par Gio (la falaise du cache SLC s'y voit).
fn preparer(a: &Args) {
    let fichier = a.texte("fichier", "");
    let taille = a.nombre("taille", 0.0) as u64;
    const TRANCHE: usize = 16 << 20;
    assert!(taille % TRANCHE as u64 == 0, "la taille doit être un multiple de 16 Mio");
    let n_tranches = (taille / TRANCHE as u64) as usize;
    const FILS: usize = 4;
    let h = ouvrir(&fichier, true, FILE_FLAG_NO_BUFFERING | FILE_FLAG_WRITE_THROUGH);
    let t0 = Instant::now();
    let mut t_gio = Instant::now();
    std::thread::scope(|s| {
        let mut vers_ecrivain = Vec::new();
        let mut retours = Vec::new();
        for f in 0..FILS {
            let (tx_plein, rx_plein) = std::sync::mpsc::sync_channel::<Tampon>(2);
            let (tx_vide, rx_vide) = std::sync::mpsc::channel::<Tampon>();
            for _ in 0..2 {
                tx_vide.send(Tampon::new(TRANCHE)).unwrap();
            }
            vers_ecrivain.push(rx_plein);
            retours.push(tx_vide);
            s.spawn(move || {
                let mut i = f;
                while i < n_tranches {
                    let mut t = rx_vide.recv().unwrap();
                    let premiere = (i * TRANCHE / PAGE) as u64;
                    for (k, page) in t.mots_mut().chunks_exact_mut(MOTS_PAR_PAGE).enumerate() {
                        remplir_page(page, premiere + k as u64);
                    }
                    tx_plein.send(t).unwrap();
                    i += FILS;
                }
            });
        }
        for i in 0..n_tranches {
            let t = vers_ecrivain[i % FILS].recv().unwrap();
            let mut ecrits = 0u32;
            let ok = unsafe { WriteFile(h, t.ptr, TRANCHE as u32, &mut ecrits, null_mut()) };
            assert!(ok != 0 && ecrits as usize == TRANCHE, "WriteFile : erreur {}", unsafe { GetLastError() });
            let _ = retours[i % FILS].send(t);
            if (i + 1) % 64 == 0 {
                let dt = t_gio.elapsed().as_secs_f64();
                println!("ECRITURE gio={} debit_go_s={:.3}", (i + 1) / 64, (1u64 << 30) as f64 / dt / 1e9);
                t_gio = Instant::now();
            }
        }
        drop(retours);
    });
    unsafe { CloseHandle(h) };
    let dt = t0.elapsed().as_secs_f64();
    println!("RESULTAT op=preparer octets={taille} secondes={dt:.3} debit_go_s={:.3}", taille as f64 / dt / 1e9);
}

// ---------------------------------------------------------------------------------------
struct Plan {
    acces_alea: bool,
    bloc: u64,
    nb_blocs: u64,
    curseur: u64,
    alea: u64,
}
impl Plan {
    fn suivant(&mut self) -> u64 {
        if self.acces_alea {
            (xorshift64star(&mut self.alea) % self.nb_blocs) * self.bloc
        } else {
            let o = self.curseur * self.bloc;
            self.curseur = (self.curseur + 1) % self.nb_blocs;
            o
        }
    }
}

struct Compte {
    octets: u64,
    ios: u64,
    latences_us: Vec<f64>,
    pages_fausses: u64,
    pages_verifiees: u64,
    pages_completes: u64,
    pages_completes_fausses: u64,
    erreurs: u64,
    n_complet: u64,
    fausser: bool,
}
impl Compte {
    fn verifier(&mut self, tampon: &[u8], offset: u64) {
        let premiere = offset / PAGE as u64 + if self.fausser { 1 } else { 0 };
        self.pages_fausses += verifier_entetes(tampon, premiere);
        self.pages_verifiees += (tampon.len() / PAGE) as u64;
        if self.n_complet > 0 && self.ios % self.n_complet == 0 {
            self.pages_completes += 1;
            if !verifier_page_complete(&tampon[..PAGE], premiere) {
                self.pages_completes_fausses += 1;
            }
        }
    }
}

fn lire(a: &Args) {
    let fichier = a.texte("fichier", "");
    let moteur = a.texte("moteur", "iocp");
    let acces = a.texte("acces", "seq");
    let bloc = a.nombre("bloc", 4096.0) as u64;
    let qd = a.nombre("qd", 1.0) as usize;
    let duree = a.nombre("duree", 2.0);
    let chauffe = a.nombre("chauffe", 0.5);
    let region = a.nombre("region", 0.0) as u64;
    let n_complet = a.nombre("complet", 64.0) as u64;
    let fausser = a.drapeau("fausser");
    assert!(bloc % PAGE as u64 == 0);

    let drapeaux = match moteur.as_str() {
        "tampon" => FILE_FLAG_OVERLAPPED, // le cache de Windows reste en jeu : témoin
        _ => FILE_FLAG_NO_BUFFERING | FILE_FLAG_OVERLAPPED,
    };
    let h = ouvrir(&fichier, false, drapeaux);
    let taille = taille_fichier(h);
    let etendue = if region > 0 { region.min(taille) } else { taille };
    let graine = 0x1234_5678_9ABC_DEF1u64 ^ (bloc << 7) ^ qd as u64;
    let mut plan = Plan { acces_alea: acces == "alea", bloc, nb_blocs: etendue / bloc, curseur: 0, alea: graine };
    let mut compte = Compte {
        octets: 0, ios: 0, latences_us: Vec::with_capacity(1 << 20), pages_fausses: 0, pages_verifiees: 0,
        pages_completes: 0, pages_completes_fausses: 0, erreurs: 0, n_complet, fausser,
    };
    let tampons: Vec<Tampon> = (0..qd).map(|_| Tampon::new(bloc as usize)).collect();
    let cpu0 = temps_cpu_s();
    let (debut_mesure, fin_mesure) = match moteur.as_str() {
        "ioring" => boucle_ioring(h, &tampons, &mut plan, &mut compte, chauffe, duree),
        _ => boucle_iocp(h, &tampons, &mut plan, &mut compte, chauffe, duree),
    };
    let cpu = temps_cpu_s() - cpu0;
    unsafe { CloseHandle(h) };
    let fenetre = fin_mesure - debut_mesure;
    let mut lat = std::mem::take(&mut compte.latences_us);
    lat.sort_by(|x, y| x.partial_cmp(y).unwrap());
    println!(
        "RESULTAT op=lire moteur={moteur} acces={acces} bloc={bloc} qd={qd} region={etendue} fenetre_s={fenetre:.3} \
         octets={} ios={} debit_go_s={:.4} iops={:.0} lat_moy_us={:.1} lat_p50_us={:.1} lat_p99_us={:.1} lat_max_us={:.1} \
         cpu_s={cpu:.3} pages_verifiees={} pages_fausses={} pages_completes={} pages_completes_fausses={} erreurs={} fausser={}",
        compte.octets, compte.ios,
        compte.octets as f64 / fenetre / 1e9,
        compte.ios as f64 / fenetre,
        moyenne(&lat), quantile(&lat, 0.5), quantile(&lat, 0.99), lat.last().copied().unwrap_or(f64::NAN),
        compte.pages_verifiees, compte.pages_fausses, compte.pages_completes, compte.pages_completes_fausses,
        compte.erreurs, fausser
    );
}

/// Boucle IOCP : `qd` lectures en vol, chaque complétion relance une lecture tant que la
/// fenêtre n'est pas close. Rend (début, fin) de la fenêtre de mesure en secondes.
fn boucle_iocp(h: HANDLE, tampons: &[Tampon], plan: &mut Plan, c: &mut Compte, chauffe: f64, duree: f64) -> (f64, f64) {
    let qd = tampons.len();
    let port = unsafe { CreateIoCompletionPort(h, null_mut(), 0, 1) };
    assert!(!port.is_null());
    let mut ovs: Vec<OVERLAPPED> = (0..qd).map(|_| OVERLAPPED::default()).collect();
    let mut offs = vec![0u64; qd];
    let mut t_emis = vec![0f64; qd];
    let t0 = Instant::now();
    let base = ovs.as_mut_ptr();
    let emettre = |i: usize, offs: &mut [u64], t_emis: &mut [f64], plan: &mut Plan| {
        let o = plan.suivant();
        offs[i] = o;
        let ov = unsafe { &mut *base.add(i) };
        *ov = OVERLAPPED::default();
        ov.Anonymous.Anonymous.Offset = o as u32;
        ov.Anonymous.Anonymous.OffsetHigh = (o >> 32) as u32;
        t_emis[i] = t0.elapsed().as_secs_f64();
        let ok = unsafe { ReadFile(h, tampons[i].ptr, plan.bloc as u32, null_mut(), ov) };
        if ok == 0 {
            let e = unsafe { GetLastError() };
            assert!(e == ERROR_IO_PENDING, "ReadFile : erreur {e}");
        }
    };
    for i in 0..qd {
        emettre(i, &mut offs, &mut t_emis, plan);
    }
    let mut en_vol = qd;
    let mut entrees = vec![OVERLAPPED_ENTRY::default(); qd.max(1)];
    let fin = chauffe + duree;
    while en_vol > 0 {
        let mut n = 0u32;
        let ok = unsafe { GetQueuedCompletionStatusEx(port, entrees.as_mut_ptr(), entrees.len() as u32, &mut n, INFINITE, 0) };
        assert!(ok != 0, "GetQueuedCompletionStatusEx : erreur {}", unsafe { GetLastError() });
        let maintenant = t0.elapsed().as_secs_f64();
        for e in &entrees[..n as usize] {
            let i = (e.lpOverlapped as usize - base as usize) / std::mem::size_of::<OVERLAPPED>();
            en_vol -= 1;
            let statut = unsafe { (*e.lpOverlapped).Internal };
            if statut != 0 || e.dwNumberOfBytesTransferred as u64 != plan.bloc {
                c.erreurs += 1;
            }
            if maintenant >= chauffe && maintenant <= fin {
                c.octets += e.dwNumberOfBytesTransferred as u64;
                c.ios += 1;
                c.latences_us.push((maintenant - t_emis[i]) * 1e6);
                c.verifier(tampons[i].tranche(), offs[i]);
            }
            if maintenant < fin {
                emettre(i, &mut offs, &mut t_emis, plan);
                en_vol += 1;
            }
        }
    }
    unsafe { CloseHandle(port) };
    (chauffe, fin)
}

fn verifier_hr(hr: i32, quoi: &str) {
    assert!(hr >= 0, "{quoi} : HRESULT 0x{:08X}", hr as u32);
}

/// Boucle IoRing : fichier et tampons enregistrés une fois, puis soumission par lots.
fn boucle_ioring(h: HANDLE, tampons: &[Tampon], plan: &mut Plan, c: &mut Compte, chauffe: f64, duree: f64) -> (f64, f64) {
    let qd = tampons.len();
    let mut anneau: HIORING = null_mut();
    let taille_file = (qd as u32 * 2).next_power_of_two().max(64);
    let drap = IORING_CREATE_FLAGS { Required: IORING_CREATE_REQUIRED_FLAGS_NONE, Advisory: IORING_CREATE_ADVISORY_FLAGS_NONE };
    verifier_hr(unsafe { CreateIoRing(IORING_VERSION_3, drap, taille_file, taille_file * 2, &mut anneau) }, "CreateIoRing");
    // Enregistrement du fichier et des tampons (évite la résolution par opération).
    let poignees = [h];
    verifier_hr(unsafe { BuildIoRingRegisterFileHandles(anneau, 1, poignees.as_ptr(), u64::MAX as usize) }, "RegisterFileHandles");
    let infos: Vec<IORING_BUFFER_INFO> = tampons.iter().map(|t| IORING_BUFFER_INFO { Address: t.ptr as _, Length: t.len as u32 }).collect();
    verifier_hr(unsafe { BuildIoRingRegisterBuffers(anneau, infos.len() as u32, infos.as_ptr(), u64::MAX as usize - 1) }, "RegisterBuffers");
    let mut soumis = 0u32;
    verifier_hr(unsafe { SubmitIoRing(anneau, 2, INFINITE, &mut soumis) }, "SubmitIoRing(enregistrement)");
    let mut cqe = IORING_CQE::default();
    let mut vus = 0;
    while vus < 2 {
        let hr = unsafe { PopIoRingCompletion(anneau, &mut cqe) };
        if hr == 0 {
            verifier_hr(cqe.ResultCode, "enregistrement");
            vus += 1;
        }
    }
    let mut offs = vec![0u64; qd];
    let mut t_emis = vec![0f64; qd];
    let t0 = Instant::now();
    let fichier_ref = IORING_HANDLE_REF { Kind: IORING_REF_REGISTERED, Handle: IORING_HANDLE_REF_0 { Index: 0 } };
    let mut construire = |i: usize, offs: &mut [u64], t_emis: &mut [f64], plan: &mut Plan| {
        let o = plan.suivant();
        offs[i] = o;
        let tref = IORING_BUFFER_REF {
            Kind: IORING_REF_REGISTERED,
            Buffer: IORING_BUFFER_REF_0 { IndexAndOffset: IORING_REGISTERED_BUFFER { BufferIndex: i as u32, Offset: 0 } },
        };
        t_emis[i] = t0.elapsed().as_secs_f64();
        verifier_hr(unsafe { BuildIoRingReadFile(anneau, fichier_ref, tref, plan.bloc as u32, o, i, IOSQE_FLAGS_NONE) }, "BuildIoRingReadFile");
    };
    for i in 0..qd {
        construire(i, &mut offs, &mut t_emis, plan);
    }
    let mut en_vol = qd;
    let fin = chauffe + duree;
    while en_vol > 0 {
        verifier_hr(unsafe { SubmitIoRing(anneau, 1, INFINITE, &mut soumis) }, "SubmitIoRing");
        loop {
            let hr = unsafe { PopIoRingCompletion(anneau, &mut cqe) };
            if hr != 0 {
                break; // S_FALSE : file de complétion vide
            }
            let maintenant = t0.elapsed().as_secs_f64();
            let i = cqe.UserData;
            en_vol -= 1;
            if cqe.ResultCode < 0 || cqe.Information as u64 != plan.bloc {
                c.erreurs += 1;
            }
            if maintenant >= chauffe && maintenant <= fin {
                c.octets += cqe.Information as u64;
                c.ios += 1;
                c.latences_us.push((maintenant - t_emis[i]) * 1e6);
                c.verifier(tampons[i].tranche(), offs[i]);
            }
            if maintenant < fin {
                construire(i, &mut offs, &mut t_emis, plan);
                en_vol += 1;
            }
        }
    }
    unsafe { CloseIoRing(anneau) };
    (chauffe, fin)
}

// ---------------------------------------------------------------------------------------
fn capacites(a: &Args) {
    let mut caps = IORING_CAPABILITIES::default();
    let hr = unsafe { QueryIoRingCapabilities(&mut caps) };
    println!(
        "IORING hr=0x{:08X} version_max={} file_soumission_max={} file_completion_max={} drapeaux=0x{:X} emulation_mode_utilisateur={}",
        hr as u32, caps.MaxVersion, caps.MaxSubmissionQueueSize, caps.MaxCompletionQueueSize, caps.FeatureFlags,
        caps.FeatureFlags & IORING_FEATURE_UM_EMULATION != 0
    );
    let fichier = a.texte("fichier", "");
    if fichier.is_empty() {
        return;
    }
    let h = ouvrir(&fichier, false, FILE_FLAG_NO_BUFFERING);
    for (nom, op) in [("requete", FS_BPIO_OP_QUERY), ("info", FS_BPIO_OP_GET_INFO)] {
        let entree = FS_BPIO_INPUT { Operation: op, InFlags: 0, Reserved1: 0, Reserved2: 0 };
        let mut sortie = FS_BPIO_OUTPUT::default();
        let mut rendu = 0u32;
        let ok = unsafe {
            DeviceIoControl(
                h, FSCTL_MANAGE_BYPASS_IO,
                &entree as *const _ as _, std::mem::size_of::<FS_BPIO_INPUT>() as u32,
                &mut sortie as *mut _ as _, std::mem::size_of::<FS_BPIO_OUTPUT>() as u32,
                &mut rendu, null_mut(),
            )
        };
        let err = if ok == 0 { unsafe { GetLastError() } } else { 0 };
        unsafe {
            if op == FS_BPIO_OP_GET_INFO {
                let i = sortie.Anonymous.GetInfo;
                let nom_pilote = String::from_utf16_lossy(&i.StorageDriverName[..(i.StorageDriverNameLen as usize / 2).min(32)]);
                println!("BYPASSIO op={nom} ok={} erreur={err} pilote_stockage=\"{nom_pilote}\" actifs={}", ok != 0, i.ActiveBypassIoCount);
            } else {
                let r = sortie.Anonymous.Query;
                let pilote = String::from_utf16_lossy(&r.FailingDriverName[..(r.FailingDriverNameLen as usize / 2).min(32)]);
                let raison = String::from_utf16_lossy(&r.FailureReason[..(r.FailureReasonLen as usize / 2).min(128)]);
                println!(
                    "BYPASSIO op={nom} ok={} erreur={err} statut=0x{:08X} pilote_en_echec=\"{pilote}\" raison=\"{raison}\"",
                    ok != 0, r.OpStatus
                );
            }
        }
    }
    unsafe { CloseHandle(h) };
}
