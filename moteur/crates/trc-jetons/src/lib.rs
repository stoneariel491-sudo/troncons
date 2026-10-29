//! trc-jetons : le découpage en jetons par `llama.dll` b11515, vocabulaire seul (§ 5.9, lot R).
//!
//! On ne réécrit pas le découpeur BPE de gpt-oss (o200k_harmony, prédécoupage « gpt-4o ») : le juge
//! doit voir **exactement** les jetons de la base llama.cpp. On charge donc `llama.dll` par son API
//! publique (`include/llama.h` de b11515, MIT), modèle ouvert avec `vocab_only = true` : aucun poids
//! n'est lu. Les signatures et la disposition de `llama_model_params` ci-dessous sont écrites depuis
//! cet en-tête ; un écart de disposition se verrait au témoin (jetons égaux à ceux d'un fichier
//! `.kld` écrit par llama-perplexity sur le même texte).

use std::ffi::{CString, c_char, c_void};
use std::path::Path;

use anyhow::{Context, Result, bail};
use libloading::{Library, Symbol};

/// `struct llama_model_params` de b11515 (x86-64, Windows) : 8 + 8 + 4·5 (+4 de bourrage) + 8·4,
/// puis 6 booléens, arrondi à 80 octets.
#[repr(C)]
#[derive(Clone, Copy)]
struct ParamsModele {
    devices: *mut c_void,
    tensor_buft_overrides: *const c_void,
    n_gpu_layers: i32,
    split_mode: i32,
    load_mode: i32,
    lazy_mode: i32,
    main_gpu: i32,
    tensor_split: *const f32,
    progress_callback: *const c_void,
    progress_callback_user_data: *mut c_void,
    kv_overrides: *const c_void,
    vocab_only: bool,
    check_tensors: bool,
    use_extra_bufts: bool,
    no_host: bool,
    no_alloc: bool,
    load_mtp: bool,
}

const _: () = assert!(std::mem::size_of::<ParamsModele>() == 80);

type FnInit = unsafe extern "C" fn();
type FnParams = unsafe extern "C" fn() -> ParamsModele;
type FnCharger = unsafe extern "C" fn(*const c_char, ParamsModele) -> *mut c_void;
type FnLiberer = unsafe extern "C" fn(*mut c_void);
type FnVocab = unsafe extern "C" fn(*const c_void) -> *const c_void;
type FnNJetons = unsafe extern "C" fn(*const c_void) -> i32;
type FnAjoutBos = unsafe extern "C" fn(*const c_void) -> bool;
type FnDecouper = unsafe extern "C" fn(*const c_void, *const c_char, i32, *mut i32, i32, bool, bool) -> i32;
type FnMorceau = unsafe extern "C" fn(*const c_void, i32, *mut c_char, i32, i32, bool) -> i32;

pub struct Jetons {
    _dll: Library,
    modele: *mut c_void,
    vocab: *const c_void,
    liberer: FnLiberer,
    n_jetons: FnNJetons,
    ajout_bos: FnAjoutBos,
    decouper_fn: FnDecouper,
    morceau: FnMorceau,
}

// Le vocabulaire est en lecture seule après le chargement ; llama.cpp ne le modifie pas.
unsafe impl Send for Jetons {}

impl Jetons {
    /// `dll` : chemin de `llama.dll` (son dossier doit contenir `ggml*.dll`) ; `vocab` : un GGUF
    /// (le compagnon `.vocab.gguf` ou le GGUF d'origine).
    pub fn ouvrir(dll: &Path, vocab: &Path) -> Result<Jetons> {
        // SAFETY : chargement d'une bibliothèque de confiance (binaire officiel b11515, empreinte
        // vérifiée par l'étude 06) ; chaque symbole est typé depuis llama.h.
        unsafe {
            // LOAD_WITH_ALTERED_SEARCH_PATH (0x8) : les dépendances (ggml*.dll) se cherchent dans le
            // dossier de llama.dll ; sans lui, Windows refuse (« module introuvable », mesuré ici).
            let chemin_absolu = std::path::absolute(dll)?;
            let biblio: Library = libloading::os::windows::Library::load_with_flags(&chemin_absolu, 0x0000_0008)
                .with_context(|| format!("chargement de {}", dll.display()))?
                .into();
            let init: Symbol<FnInit> = biblio.get(b"llama_backend_init\0")?;
            let params: Symbol<FnParams> = biblio.get(b"llama_model_default_params\0")?;
            let charger: Symbol<FnCharger> = biblio.get(b"llama_model_load_from_file\0")?;
            let liberer: FnLiberer = *biblio.get::<FnLiberer>(b"llama_model_free\0")?;
            let vocab_de: Symbol<FnVocab> = biblio.get(b"llama_model_get_vocab\0")?;
            let n_jetons: FnNJetons = *biblio.get::<FnNJetons>(b"llama_vocab_n_tokens\0")?;
            let ajout_bos: FnAjoutBos = *biblio.get::<FnAjoutBos>(b"llama_vocab_get_add_bos\0")?;
            let decouper_fn: FnDecouper = *biblio.get::<FnDecouper>(b"llama_tokenize\0")?;
            let morceau: FnMorceau = *biblio.get::<FnMorceau>(b"llama_token_to_piece\0")?;
            init();
            let mut p = params();
            p.vocab_only = true;
            p.n_gpu_layers = 0;
            let c = CString::new(vocab.to_string_lossy().as_bytes())?;
            let modele = charger(c.as_ptr(), p);
            if modele.is_null() {
                bail!("llama.dll refuse de charger le vocabulaire de {}", vocab.display());
            }
            let v = vocab_de(modele);
            Ok(Jetons { _dll: biblio, modele, vocab: v, liberer, n_jetons, ajout_bos, decouper_fn, morceau })
        }
    }

    pub fn taille_vocab(&self) -> usize {
        unsafe { (self.n_jetons)(self.vocab) as usize }
    }

    /// Le vocabulaire demande-t-il un BOS en tête (llama-perplexity le met en tête de chaque fenêtre) ?
    pub fn ajoute_bos(&self) -> bool {
        unsafe { (self.ajout_bos)(self.vocab) }
    }

    /// Découpe `texte` comme `common_tokenize(…, add_special = special, parse_special = false)`.
    pub fn decouper(&self, texte: &str, special: bool) -> Vec<u32> {
        let octets = texte.as_bytes();
        let mut v = vec![0i32; octets.len() + 2];
        unsafe {
            let mut n = (self.decouper_fn)(self.vocab, octets.as_ptr() as *const c_char, octets.len() as i32, v.as_mut_ptr(), v.len() as i32, special, false);
            if n < 0 {
                v.resize((-n) as usize, 0);
                n = (self.decouper_fn)(self.vocab, octets.as_ptr() as *const c_char, octets.len() as i32, v.as_mut_ptr(), v.len() as i32, special, false);
            }
            v.truncate(n.max(0) as usize);
        }
        v.into_iter().map(|j| j as u32).collect()
    }

    /// Le texte d'un jeton (octets bruts du morceau, rendus en UTF-8 avec remplacement).
    pub fn texte(&self, jeton: u32) -> String {
        let mut buf = vec![0u8; 256];
        unsafe {
            let mut n = (self.morceau)(self.vocab, jeton as i32, buf.as_mut_ptr() as *mut c_char, buf.len() as i32, 0, true);
            if n < 0 {
                buf.resize((-n) as usize, 0);
                n = (self.morceau)(self.vocab, jeton as i32, buf.as_mut_ptr() as *mut c_char, buf.len() as i32, 0, true);
            }
            buf.truncate(n.max(0) as usize);
        }
        String::from_utf8_lossy(&buf).into_owned()
    }
}

impl Drop for Jetons {
    fn drop(&mut self) {
        unsafe { (self.liberer)(self.modele) }
    }
}
