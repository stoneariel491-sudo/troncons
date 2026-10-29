//! genome : mesures du génome des poids sur gpt-oss (sujet genome). Processeur seul.
//!
//! Sous-commandes :
//!   frontiere [--casser]          la base de B refaite sur les 12 tenseurs de F1 (témoin S0)
//!   gauss L KB V Q [--casser]     le treillis sur une source gaussienne i.i.d. (témoin T1)
//!   codons NORM EXPERTS...        la lecture par codons glissants sur les experts réels
//!   graines C P K GEN RANGEES     la recette graine + coefficients sur un échantillon de rangées
//!
//! Les journaux sortent en JSON sur la sortie standard ; les fichiers lourds sous
//! ~/dev/essais/troncons/genome/genome/.

mod base;
mod codons;
mod donnees;
mod graine;
mod hadamard;
mod mesure;
mod motifs;
mod sortie;
mod fidelite;

use anyhow::{Result, bail};

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        bail!("usage : genome <frontiere|gauss|codons|graines|...> …");
    }
    let reste = &args[2..];
    match args[1].as_str() {
        "frontiere" => mesure::frontiere(reste),
        "gauss" => mesure::gauss(reste),
        "codons" => mesure::codons(reste),
        "graines" => mesure::graines(reste),
        "decoder" => mesure::decoder(reste),
        "sortie" => sortie::sortie(reste),
        "fidelite" => fidelite::fidelite(reste),
        "motifs" => mesure::motifs(reste),
        "base-f32w" => mesure::base_f32w(reste),
        c => bail!("sous-commande inconnue : {c}"),
    }
}
