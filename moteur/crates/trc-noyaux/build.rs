//! Compile `noyaux/noyaux.cu` en une image fatbin (cubin sm_89 + PTX compute_89) par `nvcc`
//! 13.1, à la construction (ARCHITECTURE.md § 2.2) ; l'image est embarquée par
//! `include_bytes!` et chargée par `trc_cuda::Module::charger`.
//!
//! Options : exactement celles du banc (`banc/construire.bat`) : `-O3 -std=c++17`, sans
//! `--use_fast_math` (les échelles E8M0 sous-normales doivent rester exactes, et la règle de
//! déterminisme veut le même code que le banc a mesuré).
//!
//! Environnement : `nvcc` a besoin de `cl.exe` pour le prétraitement. Si `cl.exe` est déjà dans
//! le `PATH` (fenêtre où `vcvars64.bat` a tourné), `nvcc` est appelé directement ; sinon un petit
//! script lance d'abord `vcvars64.bat` (chemin de Visual Studio 2022 Build Tools, ou la variable
//! `TRC_VCVARS`). `CUDA_PATH` vaut par défaut `~/dev/outils/cuda-13.1.2` (SOCLE).
//! Sans `nvcc`, la construction échoue avec un message qui dit quoi poser.

use std::path::{Path, PathBuf};
use std::process::Command;

const CUDA_PAR_DEFAUT: &str = r"~\dev\outils\cuda-13.1.2";
const VCVARS_PAR_DEFAUT: &str =
    r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat";

fn cl_dans_le_path() -> bool {
    std::env::var_os("PATH")
        .map(|p| std::env::split_paths(&p).any(|d| d.join("cl.exe").is_file()))
        .unwrap_or(false)
}

fn main() {
    let ici = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR"));
    let dossier = ici.join("noyaux");
    for f in ["noyaux.cu", "commun.cuh", "decodeur.cuh", "gemv.cuh", "passe.cuh"] {
        println!("cargo:rerun-if-changed={}", dossier.join(f).display());
    }
    println!("cargo:rerun-if-env-changed=CUDA_PATH");
    println!("cargo:rerun-if-env-changed=TRC_VCVARS");

    let cuda = std::env::var("CUDA_PATH").unwrap_or_else(|_| CUDA_PAR_DEFAUT.to_string());
    let nvcc = Path::new(&cuda).join("bin").join("nvcc.exe");
    if !nvcc.is_file() {
        panic!(
            "nvcc introuvable ({}). Poser CUDA_PATH sur la boîte à outils CUDA 13.1 \
             (~/dev/outils/cuda-13.1.2 sur la machine de Stone).",
            nvcc.display()
        );
    }
    let out = PathBuf::from(std::env::var("OUT_DIR").expect("OUT_DIR"));
    let sortie = out.join("noyaux.fatbin");
    let source = dossier.join("noyaux.cu");
    let options = format!(
        "-O3 -std=c++17 -gencode arch=compute_89,code=[sm_89,compute_89] --fatbin -o \"{}\" \"{}\"",
        sortie.display(),
        source.display()
    );

    let statut = if cl_dans_le_path() {
        // nvcc appelé directement, sans `cmd` : la ligne `cmd /C ""nvcc" …"` que construisait la
        // version précédente sortait de `Command::arg` avec ses guillemets protégés par des barres
        // obliques inverses, que cmd ne comprend pas (« '\"\"C:\…\nvcc.exe\"' n'est pas reconnu »,
        // constat m2 de l'épreuve J1, reproduit par mesures/moteur/O/corrections/construire-avec-vcvars.bat).
        Command::new(&nvcc)
            .args(["-O3", "-std=c++17", "-gencode", "arch=compute_89,code=[sm_89,compute_89]", "--fatbin", "-o"])
            .arg(&sortie)
            .arg(&source)
            .status()
    } else {
        let vcvars = std::env::var("TRC_VCVARS").unwrap_or_else(|_| VCVARS_PAR_DEFAUT.to_string());
        if !Path::new(&vcvars).is_file() {
            panic!(
                "cl.exe absent du PATH et vcvars64.bat introuvable ({vcvars}). Lancer la construction \
                 depuis un environnement vcvars64, ou poser TRC_VCVARS."
            );
        }
        let script = out.join("nvcc-noyaux.bat");
        let texte = format!(
            "@echo off\r\ncall \"{vcvars}\" >nul\r\nset \"CUDA_PATH={cuda}\"\r\nset \"PATH={cuda}\\bin;%PATH%\"\r\n\"{}\" {options}\r\n",
            nvcc.display()
        );
        std::fs::write(&script, texte).expect("écriture du script nvcc");
        Command::new("cmd").arg("/C").arg(&script).status()
    };
    match statut {
        Ok(s) if s.success() && sortie.is_file() => {}
        Ok(s) => panic!("nvcc a échoué ({s}) sur {}", source.display()),
        Err(e) => panic!("impossible de lancer cmd pour nvcc : {e}"),
    }
}
