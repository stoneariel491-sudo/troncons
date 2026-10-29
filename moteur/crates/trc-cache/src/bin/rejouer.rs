//! rejouer : le simulateur du cache en ligne de commande (témoin O1, courbes de succès).
//!
//! ```text
//! rejouer --trace T.trace --emplacements 8,16,32 [--tiedes 0,64] [--politique lru|belady] [--casser]
//! ```
//! Rejoue la trace dans `trc_cache::Cache` (le code du moteur) pour chaque couple
//! (emplacements, tiedes) et écrit un JSON sur la sortie standard : les compteurs à l'unité.
//!
//! `--casser` remplace la politique par une politique faussée : elle ignore les succès (`acceder`
//! ne fait rien), si bien qu'un LRU devient FIFO. Le témoin O1 doit alors tomber.

use std::path::PathBuf;
use std::process::ExitCode;
use trc_cache::{lire_trace, rejouer, Belady, Id, Lru, Politique, Trace};

/// La politique faussée de la cassure.
struct Faussee(Box<dyn Politique>);
impl Politique for Faussee {
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

fn politique(nom: &str, trace: &Trace, casser: bool) -> Box<dyn Politique> {
    let p: Box<dyn Politique> = match nom {
        "lru" => Box::new(Lru::default()),
        "belady" => Box::new(Belady::depuis_trace(trace)),
        _ => unreachable!(),
    };
    if casser { Box::new(Faussee(p)) } else { p }
}

fn liste(v: &str) -> Result<Vec<u32>, String> {
    v.split(',').map(|x| x.trim().parse::<u32>().map_err(|_| format!("nombre illisible : {x:?}"))).collect()
}

fn chaine_json(s: &str) -> String {
    let mut o = String::from("\"");
    for c in s.chars() {
        match c {
            '"' => o.push_str("\\\""),
            '\\' => o.push_str("\\\\"),
            c if (c as u32) < 0x20 => o.push_str(&format!("\\u{:04x}", c as u32)),
            c => o.push(c),
        }
    }
    o.push('"');
    o
}

fn principal() -> Result<(), String> {
    let mut args = std::env::args().skip(1);
    let (mut trace, mut emp, mut tie, mut pol, mut casser) = (None, None, vec![0u32], "lru".to_string(), false);
    while let Some(a) = args.next() {
        let mut valeur = || args.next().ok_or(format!("{a} : valeur manquante"));
        match a.as_str() {
            "--trace" => trace = Some(PathBuf::from(valeur()?)),
            "--emplacements" => emp = Some(liste(&valeur()?)?),
            "--tiedes" => tie = liste(&valeur()?)?,
            "--politique" => pol = valeur()?,
            "--casser" => casser = true,
            _ => return Err(format!("option inconnue : {a}")),
        }
    }
    let chemin = trace.ok_or("--trace manquant")?;
    let emp = emp.ok_or("--emplacements manquant")?;
    if pol != "lru" && pol != "belady" {
        return Err(format!("politique inconnue : {pol} (lru ou belady)"));
    }
    let tr = lire_trace(&chemin).map_err(|e| e.to_string())?;
    let mut lignes = Vec::new();
    for &n in &emp {
        if (n as usize) < tr.k as usize {
            return Err(format!("emplacements = {n} < k = {} : une couche ne tiendrait pas", tr.k));
        }
        for &r in &tie {
            let c = rejouer(&tr, n, r, politique(&pol, &tr, casser), politique(&pol, &tr, casser));
            lignes.push(format!(
                "{{\"emplacements\":{n},\"tiedes\":{r},\"acces\":{},\"succes_vram\":{},\"succes_ram\":{},\
                 \"defauts_disque\":{},\"evictions\":{}}}",
                c.acces(),
                c.succes_vram,
                c.succes_ram,
                c.defauts_disque,
                c.evictions
            ));
        }
    }
    println!(
        "{{\"outil\":\"rejouer (trc-cache {})\",\"trace\":{},\"T\":{},\"L\":{},\"E\":{},\"k\":{},\
         \"politique\":{},\"casser\":{casser},\"resultats\":[{}]}}",
        env!("CARGO_PKG_VERSION"),
        chaine_json(&chemin.display().to_string()),
        tr.jetons,
        tr.couches,
        tr.experts,
        tr.k,
        chaine_json(&pol),
        lignes.join(",")
    );
    Ok(())
}

fn main() -> ExitCode {
    match principal() {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("rejouer : {e}");
            ExitCode::from(2)
        }
    }
}
