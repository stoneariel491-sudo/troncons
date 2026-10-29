//! La cassure du témoin C2 (§ 6.5 E2 : « un bit retourné dans une copie du fichier → détecté »).
//!
//! Recopie le `.trc` entier, puis retourne **un bit** dans chacun de `n` experts tirés d'une
//! graine publiée, un par sorte de région, pour que la cassure couvre tout ce qu'un tronçon
//! contient : les flux bruts (MEDIANES, BIAIS), les trois parties d'un flux rANS (débuts de tuile,
//! états initiaux, mots) de DELTA et de CODES_CTX, l'en-tête d'un flux rANS (P), la table des flux
//! (sorte d'un descripteur), et l'en-tête de partie (magie ; identité couche et expert). Le bit et
//! l'octet sont tirés dans les octets **utiles** de la région (jamais dans un bourrage, qu'aucun
//! décodage ne lit). Les sections de l'en-tête, des tables et du répertoire ne sont pas touchées :
//! la copie s'ouvre comme l'original (vérifié à la fin), et seul le chemin d'un tronçon peut voir
//! la faute.
//!
//! Le journal liste chaque bit retourné (expert, région, décalage dans la partie et dans le
//! fichier, octet avant et après) : `banc-chemin chemin --temoin-seul --attendus <journal>` doit
//! détecter exactement ces experts.

use std::io::{Read, Seek, SeekFrom, Write};
use std::path::Path;

use serde_json::{Value, json};
use trc_format::{Fichier, Partie, Sorte, lire_partie, lu32};

pub struct Options<'a> {
    pub source: &'a Path,
    pub copie: &'a Path,
    pub graine: u64,
    pub n: usize,
}

struct Tirage(u64);
impl Tirage {
    fn suivant(&mut self) -> u64 {
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        self.0.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }
}

/// Les sortes de région, dans l'ordre où les experts tirés les reçoivent.
const REGIONS: [&str; 12] = [
    "medianes",
    "biais",
    "delta_debuts",
    "delta_etats",
    "delta_mots",
    "codes_debuts",
    "codes_etats",
    "codes_mots",
    "codes_entete_P",
    "table_des_flux_sorte",
    "partie_magie",
    "partie_identite",
];

/// [début, fin) de la région dans la partie, pour la matrice j.
fn region(p: &Partie, nom: &str, j: u8) -> Result<(usize, usize), String> {
    let flux = |s: Sorte| p.trouver(s, j).copied().ok_or_else(|| format!("flux {s:?} de la matrice {j} absent"));
    // Les trois zones d'un flux rANS (§ 4.9.1) : débuts u32[T] à 16, états u32[32 T], mots u16[W].
    let rans = |s: Sorte| -> Result<(usize, usize, usize, usize), String> {
        let d = flux(s)?;
        let b = d.decalage as usize;
        let t = lu32(p.octets, b + 8) as usize;
        let w = lu32(p.octets, b + 12) as usize;
        Ok((b, t, w, d.longueur as usize))
    };
    let r = match nom {
        "medianes" | "biais" => {
            let d = flux(if nom == "medianes" { Sorte::Medianes } else { Sorte::Biais })?;
            (d.decalage as usize, (d.decalage + d.longueur) as usize)
        }
        "delta_debuts" | "codes_debuts" => {
            let (b, t, _, _) = rans(if nom.starts_with("delta") { Sorte::Delta } else { Sorte::CodesCtx })?;
            (b + 16, b + 16 + 4 * t)
        }
        "delta_etats" | "codes_etats" => {
            let (b, t, _, _) = rans(if nom.starts_with("delta") { Sorte::Delta } else { Sorte::CodesCtx })?;
            (b + 16 + 4 * t, b + 16 + 132 * t)
        }
        "delta_mots" | "codes_mots" => {
            let (b, t, w, _) = rans(if nom.starts_with("delta") { Sorte::Delta } else { Sorte::CodesCtx })?;
            (b + 16 + 132 * t, b + 16 + 132 * t + 2 * w)
        }
        "codes_entete_P" => {
            let (b, _, _, _) = rans(Sorte::CodesCtx)?;
            (b, b + 4)
        }
        "table_des_flux_sorte" => {
            let i = p.flux.iter().position(|d| d.sorte == Sorte::CodesCtx && d.matrice == j).ok_or("descripteur absent")?;
            (64 + 16 * i, 64 + 16 * i + 1)
        }
        "partie_magie" => (0, 4),
        "partie_identite" => (4, 8),
        _ => return Err(format!("région inconnue : {nom}")),
    };
    if r.0 >= r.1 || r.1 > p.utiles as usize {
        return Err(format!("région {nom} vide ou hors des octets utiles : {r:?}"));
    }
    Ok(r)
}

pub fn executer(o: &Options) -> Result<Value, String> {
    let f = Fichier::ouvrir(o.source).map_err(|e| format!("ouverture de la source : {e}"))?;
    let rep = f.repertoire().to_vec();
    if o.n == 0 || o.n > rep.len() {
        return Err(format!("{} experts à corrompre sur {}", o.n, rep.len()));
    }
    if o.copie.exists() {
        return Err(format!("{} existe déjà : effacer la copie à la main d'abord (ce banc n'efface rien)", o.copie.display()));
    }
    if let Some(d) = o.copie.parent() {
        std::fs::create_dir_all(d).map_err(|e| e.to_string())?;
    }
    let t = std::time::Instant::now();
    let copies = std::fs::copy(o.source, o.copie).map_err(|e| format!("copie : {e}"))?;
    let copie_s = t.elapsed().as_secs_f64();
    eprintln!("copie : {copies} o en {copie_s:.1} s");
    let mut src = std::fs::File::open(o.source).map_err(|e| e.to_string())?;
    let mut dst = std::fs::OpenOptions::new().read(true).write(true).open(o.copie).map_err(|e| e.to_string())?;
    let mut tirage = Tirage(o.graine | 1);
    let mut choisis: Vec<usize> = Vec::new();
    let mut corruptions = Vec::new();
    for k in 0..o.n {
        let g = loop {
            let g = (tirage.suivant() % rep.len() as u64) as usize;
            if !choisis.contains(&g) {
                break g;
            }
        };
        choisis.push(g);
        let r = rep[g];
        let mut partie = vec![0u8; r.longueur[0] as usize];
        src.seek(SeekFrom::Start(r.decalage)).and_then(|_| src.read_exact(&mut partie)).map_err(|e| e.to_string())?;
        let p = lire_partie(&partie).map_err(|e| format!("partie ({}, {}) : {e}", r.couche, r.expert))?;
        let nom = REGIONS[k % REGIONS.len()];
        let j = (k % 3) as u8;
        let (a, b) = region(&p, nom, j)?;
        let dans_partie = a + (tirage.suivant() % (b - a) as u64) as usize;
        let bit = (tirage.suivant() % 8) as u8;
        let absolu = r.decalage + dans_partie as u64;
        let mut octet = [0u8; 1];
        dst.seek(SeekFrom::Start(absolu)).and_then(|_| dst.read_exact(&mut octet)).map_err(|e| e.to_string())?;
        if octet[0] != partie[dans_partie] {
            return Err(format!("la copie diffère de la source avant la cassure, à {absolu}"));
        }
        let nouveau = octet[0] ^ (1 << bit);
        dst.seek(SeekFrom::Start(absolu)).and_then(|_| dst.write_all(&[nouveau])).map_err(|e| e.to_string())?;
        eprintln!("({}, {}) : {nom}, matrice {j}, octet {dans_partie} de la partie, bit {bit} : {:#04x} → {nouveau:#04x}", r.couche, r.expert, octet[0]);
        corruptions.push(json!({
            "indice": g, "couche": r.couche, "expert": r.expert, "region": nom, "matrice": j,
            "region_debut": a, "region_fin": b, "decalage_partie": dans_partie, "decalage_fichier": absolu,
            "bit": bit, "avant": octet[0], "apres": nouveau,
        }));
    }
    dst.sync_all().map_err(|e| e.to_string())?;
    drop(dst);
    // Relecture : chaque bit est bien retourné, et la copie s'ouvre comme l'original.
    let mut relue = std::fs::File::open(o.copie).map_err(|e| e.to_string())?;
    for c in &corruptions {
        let mut b = [0u8; 1];
        relue.seek(SeekFrom::Start(c["decalage_fichier"].as_u64().unwrap())).and_then(|_| relue.read_exact(&mut b)).map_err(|e| e.to_string())?;
        if b[0] as u64 != c["apres"].as_u64().unwrap() {
            return Err(format!("relecture : octet {} non retourné", c["decalage_fichier"]));
        }
    }
    let ouverte = Fichier::ouvrir(o.copie).map(|_| true).map_err(|e| format!("la copie ne s'ouvre plus : {e}"))?;
    Ok(json!({
        "source": o.source.display().to_string(), "copie": o.copie.display().to_string(), "octets": copies,
        "copie_s": copie_s, "graine": o.graine, "n": o.n, "corruptions": corruptions, "copie_ouverte_par_trc_format": ouverte,
    }))
}
