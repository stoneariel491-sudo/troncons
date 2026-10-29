//! Compile les noyaux des essais du lot E (`noyaux/essais.cu`) en image cubin pour sm_89, par
//! `nvcc` 13.1, à la construction (ARCHITECTURE.md § 2.2) ; l'image est embarquée dans le binaire
//! par `include_bytes!` et chargée par `trc_cuda::Module::charger`.
//!
//! Recette (SOCLE, « La machine ») : `nvcc` a besoin de `cl.exe` (Visual Studio 2022 Build Tools)
//! et de `CUDA_PATH = ~/dev/outils/cuda-13.1.2`. Deux cas :
//! - `cl.exe` est dans le PATH (construction lancée depuis `vcvars64.bat`) : `nvcc` est lancé
//!   directement ;
//! - sinon, un petit script `.bat` écrit dans `OUT_DIR` appelle `vcvars64.bat` (chemin par défaut,
//!   ou `TRC_VCVARS`) puis `nvcc`. C'est le cas quand banc-chemin se construit avec trc-noyaux
//!   (lot K), dont le build.rs fait de même : construire hors de vcvars sert alors les deux.
//! Sans `nvcc`, la construction échoue avec ce message, plutôt que de produire un binaire sans
//! noyaux.

use std::path::{Path, PathBuf};
use std::process::Command;

const CUDA_PAR_DEFAUT: &str = r"~\dev\outils\cuda-13.1.2";
const VCVARS_PAR_DEFAUT: &str = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat";

fn cl_dans_le_path() -> bool {
    std::env::var_os("PATH").is_some_and(|p| std::env::split_paths(&p).any(|d| d.join("cl.exe").is_file()))
}

fn main() {
    // Le source se trouve à côté de ce build.rs. Quand le paquet est celui de ce dossier, c'est
    // `CARGO_MANIFEST_DIR` ; quand un autre paquet emprunte ce build.rs (les espaces de
    // construction privés du lot E), `file!()` est absolu et donne le dossier. `file!()` relatif ne
    // sert pas : il est relatif à la racine de l'espace de travail, pas au paquet (défaut trouvé le
    // 2026-10-15, chemin doublé « bins/banc-chemin/bins/banc-chemin/noyaux »).
    let manifeste = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
    let ici = Path::new(file!()).parent().unwrap_or(Path::new(""));
    let ici = if ici.is_absolute() { ici.to_path_buf() } else { manifeste };
    let source = ici.join("noyaux").join("essais.cu");
    assert!(source.is_file(), "source des noyaux introuvable : {}", source.display());
    println!("cargo:rerun-if-changed={}", source.display());
    println!("cargo:rerun-if-env-changed=CUDA_PATH");
    println!("cargo:rerun-if-env-changed=TRC_VCVARS");
    let out = PathBuf::from(std::env::var("OUT_DIR").unwrap());
    let sortie = out.join("essais.cubin");
    let cuda = std::env::var("CUDA_PATH").unwrap_or_else(|_| CUDA_PAR_DEFAUT.to_string());
    let nvcc = Path::new(&cuda).join("bin").join("nvcc.exe");
    if !nvcc.is_file() {
        panic!(
            "nvcc introuvable ({}). Poser CUDA_PATH sur la boîte à outils CUDA 13.1 \
             (~/dev/outils/cuda-13.1.2 sur la machine de Stone).",
            nvcc.display()
        );
    }
    let statut = if cl_dans_le_path() {
        Command::new(&nvcc).args(["-cubin", "-arch=sm_89", "-O3", "-std=c++17", "-o"]).arg(&sortie).arg(&source).status()
    } else {
        let vcvars = std::env::var("TRC_VCVARS").unwrap_or_else(|_| VCVARS_PAR_DEFAUT.to_string());
        if !Path::new(&vcvars).is_file() {
            panic!("cl.exe absent du PATH et vcvars64.bat introuvable ({vcvars}) : poser TRC_VCVARS");
        }
        let script = out.join("nvcc-essais.bat");
        let texte = format!(
            "@echo off\r\ncall \"{vcvars}\" >nul\r\nset \"CUDA_PATH={cuda}\"\r\nset \"PATH={cuda}\\bin;%PATH%\"\r\n\"{}\" -cubin -arch=sm_89 -O3 -std=c++17 -o \"{}\" \"{}\"\r\n",
            nvcc.display(),
            sortie.display(),
            source.display()
        );
        std::fs::write(&script, texte).expect("écriture du script nvcc");
        Command::new("cmd").arg("/C").arg(&script).status()
    };
    match statut {
        Ok(s) if s.success() && sortie.is_file() => {}
        Ok(s) => panic!("nvcc a échoué ({s}) sur {}", source.display()),
        Err(e) => panic!("impossible de lancer nvcc ({}) : {e}", nvcc.display()),
    }
}
