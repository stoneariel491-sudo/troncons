//! `banc-chemin` : le banc du lot E.
//!
//! ```text
//! banc-chemin essai-a --journal J.json [--tailles-go 0.25,1,4,11] [--marge-go 1.5]
//! banc-chemin essai-b --journal J.json --fichier M.gguf [--taille 12582912] [--morceaux 32]
//!                     [--serie 128] [--profondeur 4] [--graine 20261015] [--repetitions-dma 16]
//!                     [--tours-abba 2] [--casser]
//! banc-chemin lecteur --journal J.json --fichier M.gguf [--taille 12582912] [--serie 64]
//!                     [--profondeurs 4,1] [--tours-abba 2] [--graine 20261015] [--repos-s 3]
//!                     [--verifier 4] [--casser]
//! banc-chemin essai-c --journal J.json [--variantes asynchrone,evenement,...] [--jetons 30]
//!                     [--chauffe 3] [--ns-routeur 0] [--ns-expert 0] [--tours-abba 2]
//!                     [--attente auto|active|cede|bloquante] [--delai-boite-ms 200]
//! banc-chemin chemin --journal J.json --fichier M.trc [--profondeur 4] [--emplacements 6]
//!                     [--graine 20261015] [--tours-abba 2] [--residents 48] [--chronogrammes DOSSIER]
//!                     [--temoin-seul] [--attendus JOURNAL_DE_CASSER_COPIE.json] [--experts N (essai court)]
//!                     [--longueur-lecture OCTETS (variante E2-V)]
//! banc-chemin casser-copie --journal J.json --source M.trc --copie COPIE.trc [--graine 20261015] [--n 12]
//! ```
//! Chaque essai écrit un journal JSON : la commande, l'état de la machine au début et à la fin
//! (heure, alimentation, RAM, carte), et ses résultats. Les seuils se jugent dans
//! `mesures/moteur/E/analyse_e0.py`, pas ici : le banc mesure, l'analyse juge.

mod casser_copie;
mod disque;
mod essai_a;
mod essai_b;
mod essai_c;
mod essai_e2;
mod essai_lecteur;
mod machine;

use std::collections::HashMap;
use std::path::PathBuf;

use serde_json::json;

fn usage() -> ! {
    eprintln!("usage : banc-chemin essai-a|essai-b|essai-c|lecteur|chemin|casser-copie --journal J.json [options] (voir src/main.rs)");
    std::process::exit(2);
}

/// Les options `--cle valeur` et les drapeaux `--cle` (valeur « oui »).
fn options(args: &[String]) -> HashMap<String, String> {
    let mut o = HashMap::new();
    let mut i = 0;
    while i < args.len() {
        let Some(cle) = args[i].strip_prefix("--") else { usage() };
        if i + 1 < args.len() && !args[i + 1].starts_with("--") {
            o.insert(cle.to_string(), args[i + 1].clone());
            i += 2;
        } else {
            o.insert(cle.to_string(), "oui".to_string());
            i += 1;
        }
    }
    o
}

fn lire<T: std::str::FromStr>(o: &HashMap<String, String>, cle: &str, defaut: T) -> T {
    match o.get(cle) {
        None => defaut,
        Some(v) => v.parse().unwrap_or_else(|_| {
            eprintln!("--{cle} {v} : valeur illisible");
            std::process::exit(2)
        }),
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        usage();
    }
    let essai = args[1].as_str();
    let o = options(&args[2..]);
    let Some(journal) = o.get("journal").map(PathBuf::from) else { usage() };
    let debut = machine::releve(None);
    let resultat = match essai {
        "essai-a" => {
            let tailles: Vec<u64> = o
                .get("tailles-go")
                .map(String::as_str)
                .unwrap_or("0.25,1,4,11")
                .split(',')
                .map(|t| (t.parse::<f64>().unwrap_or_else(|_| usage()) * 1e9) as u64)
                .collect();
            let marge = (lire(&o, "marge-go", 1.5f64) * 1e9) as u64;
            essai_a::executer(&tailles, marge)
        }
        "essai-b" => {
            let Some(fichier) = o.get("fichier").map(PathBuf::from) else { usage() };
            essai_b::executer(&essai_b::Options {
                fichier: &fichier,
                taille: lire(&o, "taille", 12usize << 20),
                morceaux: lire(&o, "morceaux", 32),
                serie: lire(&o, "serie", 128),
                profondeur: lire(&o, "profondeur", 4),
                graine: lire(&o, "graine", 20_261_015),
                casser: o.contains_key("casser"),
                repetitions_dma: lire(&o, "repetitions-dma", 16),
                tours_abba: lire(&o, "tours-abba", 2),
            })
        }
        "lecteur" => {
            let Some(fichier) = o.get("fichier").map(PathBuf::from) else { usage() };
            let qd: Vec<usize> = o
                .get("profondeurs")
                .map(String::as_str)
                .unwrap_or("4,1")
                .split(',')
                .map(|v| v.parse().unwrap_or_else(|_| usage()))
                .collect();
            if qd.len() != 2 || qd.contains(&0) {
                usage();
            }
            essai_lecteur::executer(&essai_lecteur::Options {
                fichier: &fichier,
                taille: lire(&o, "taille", 12usize << 20),
                serie: lire(&o, "serie", 64),
                profondeurs: [qd[0], qd[1]],
                tours: lire(&o, "tours-abba", 2),
                graine: lire(&o, "graine", 20_261_015),
                repos_s: lire(&o, "repos-s", 3.0),
                verifier: lire(&o, "verifier", 4),
                casser: o.contains_key("casser"),
            })
            .map_err(trc_cuda::Erreur::Usage)
        }
        "essai-c" => {
            let variantes = o
                .get("variantes")
                .map(String::as_str)
                .unwrap_or("asynchrone,evenement,sondage,bloquant,boite")
                .split(',')
                .map(|v| essai_c::Variante::depuis(v).unwrap_or_else(|| usage()))
                .collect();
            let attente = match o.get("attente").map(String::as_str).unwrap_or("auto") {
                "auto" => trc_cuda::Attente::Auto,
                "active" => trc_cuda::Attente::Active,
                "cede" => trc_cuda::Attente::Cede,
                "bloquante" => trc_cuda::Attente::Bloquante,
                _ => usage(),
            };
            essai_c::executer(&essai_c::Options {
                variantes,
                jetons: lire(&o, "jetons", 30),
                chauffe: lire(&o, "chauffe", 3),
                ns_routeur: lire(&o, "ns-routeur", 0),
                ns_expert: lire(&o, "ns-expert", 0),
                tours_abba: lire(&o, "tours-abba", 2),
                attente,
                delai_boite_ms: lire(&o, "delai-boite-ms", 200),
            })
        }
        "chemin" => {
            let Some(fichier) = o.get("fichier").map(PathBuf::from) else { usage() };
            let attendus = o.get("attendus").map(|j| {
                let v: serde_json::Value = std::fs::read_to_string(j)
                    .ok()
                    .and_then(|t| serde_json::from_str(&t).ok())
                    .unwrap_or_else(|| {
                        eprintln!("--attendus {j} : journal illisible");
                        std::process::exit(2)
                    });
                v["resultat"]["corruptions"]
                    .as_array()
                    .unwrap_or_else(|| {
                        eprintln!("--attendus {j} : pas de liste « corruptions »");
                        std::process::exit(2)
                    })
                    .iter()
                    .map(|c| c["indice"].as_u64().unwrap() as usize)
                    .collect::<Vec<usize>>()
            });
            let chronogrammes = o.get("chronogrammes").map(PathBuf::from);
            essai_e2::executer(&essai_e2::Options {
                fichier: &fichier,
                profondeur: lire(&o, "profondeur", 4),
                emplacements: lire(&o, "emplacements", 6),
                graine: lire(&o, "graine", 20_261_015),
                tours: lire(&o, "tours-abba", 2),
                temoin_seul: o.contains_key("temoin-seul"),
                residents: lire(&o, "residents", 48),
                attendus,
                chronogrammes,
                limite: o.get("experts").map(|v| v.parse().unwrap_or_else(|_| usage())),
                longueur_lecture: o.get("longueur-lecture").map(|v| v.parse().unwrap_or_else(|_| usage())),
            })
        }
        "casser-copie" => {
            let (Some(source), Some(copie)) = (o.get("source").map(PathBuf::from), o.get("copie").map(PathBuf::from)) else { usage() };
            casser_copie::executer(&casser_copie::Options {
                source: &source,
                copie: &copie,
                graine: lire(&o, "graine", 20_261_015),
                n: lire(&o, "n", 12),
            })
            .map_err(trc_cuda::Erreur::Usage)
        }
        _ => usage(),
    };
    let (statut, corps) = match resultat {
        Ok(v) => (0, v),
        Err(e) => {
            eprintln!("échec : {e}");
            (1, json!({ "erreur": e.to_string() }))
        }
    };
    let sortie = json!({
        "outil": "banc-chemin",
        "version": env!("CARGO_PKG_VERSION"),
        "essai": essai,
        "commande": args,
        "machine_debut": debut,
        "resultat": corps,
    });
    if let Some(dossier) = journal.parent() {
        std::fs::create_dir_all(dossier).ok();
    }
    std::fs::write(&journal, serde_json::to_string_pretty(&sortie).unwrap()).expect("écriture du journal");
    std::process::exit(statut);
}
