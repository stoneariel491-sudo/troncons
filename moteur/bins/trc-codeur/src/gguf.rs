//! Lecture d'un GGUF v3 (spécification publique de GGUF, écrite ici de zéro) : en-tête, paires
//! clé-valeur brutes, descriptions des tenseurs, et taille de chaque tenseur, vérifiée contre la
//! disposition du fichier (second chemin de la table des tailles par type).

use anyhow::{Context, Result, anyhow, bail, ensure};
use std::io::Read;
use std::path::Path;
use trc_format::{PaireMeta, lire_paires};

#[derive(Clone, Debug)]
pub struct TenseurGguf {
    pub nom: String,
    pub n_dims: u32,
    pub ne: [u64; 4],
    pub type_ggml: u32,
    /// Décalage absolu dans le fichier.
    pub decalage: u64,
    pub octets: u64,
}

pub struct Gguf {
    pub taille: u64,
    pub version: u32,
    pub n_kv: u64,
    /// Les paires brutes, octet pour octet, dans leur ordre.
    pub kv_brut: Vec<u8>,
    pub paires: Vec<PaireMeta>,
    pub alignement: u64,
    pub debut_donnees: u64,
    pub tenseurs: Vec<TenseurGguf>,
}

/// (poids par bloc, octets par bloc) des types ggml pris en charge.
pub fn geometrie_type(t: u32) -> Option<(u64, u64)> {
    Some(match t {
        0 => (1, 4),     // F32
        1 => (1, 2),     // F16
        2 => (32, 18),   // Q4_0
        3 => (32, 20),   // Q4_1
        6 => (32, 22),   // Q5_0
        7 => (32, 24),   // Q5_1
        8 => (32, 34),   // Q8_0
        9 => (32, 36),   // Q8_1
        10 => (256, 84), // Q2_K
        11 => (256, 110),
        12 => (256, 144),
        13 => (256, 176),
        14 => (256, 210),
        15 => (256, 292), // Q8_K
        24 => (1, 1),     // I8
        25 => (1, 2),
        26 => (1, 4),
        27 => (1, 8),
        28 => (1, 8),   // F64
        30 => (1, 2),   // BF16
        39 => (32, 17), // MXFP4
        _ => return None,
    })
}

fn u32_(b: &[u8], p: &mut usize) -> Result<u32> {
    ensure!(*p + 4 <= b.len(), "en-tête GGUF tronqué");
    let v = u32::from_le_bytes(b[*p..*p + 4].try_into().unwrap());
    *p += 4;
    Ok(v)
}
fn u64_(b: &[u8], p: &mut usize) -> Result<u64> {
    ensure!(*p + 8 <= b.len(), "en-tête GGUF tronqué");
    let v = u64::from_le_bytes(b[*p..*p + 8].try_into().unwrap());
    *p += 8;
    Ok(v)
}

impl Gguf {
    pub fn ouvrir(chemin: &Path) -> Result<Gguf> {
        let mut f = std::fs::File::open(chemin).with_context(|| format!("ouverture de {}", chemin.display()))?;
        let taille = f.metadata()?.len();
        let mut lu = (64u64 << 20).min(taille) as usize;
        loop {
            let mut b = vec![0u8; lu];
            f.read_exact(&mut b)?;
            match Gguf::analyser(&b, chemin, taille) {
                Ok(g) => return Ok(g),
                Err(e) if lu as u64 >= taille => return Err(e),
                Err(_) => {
                    lu = (lu as u64 * 2).min(taille) as usize;
                    use std::io::Seek;
                    f.seek(std::io::SeekFrom::Start(0))?;
                }
            }
        }
    }

    fn analyser(b: &[u8], chemin: &Path, taille: u64) -> Result<Gguf> {
        ensure!(b.len() >= 24 && &b[0..4] == b"GGUF", "{} n'est pas un GGUF", chemin.display());
        let mut p = 4;
        let version = u32_(b, &mut p)?;
        ensure!(version == 3, "GGUF version {version} (3 attendue)");
        let n_t = u64_(b, &mut p)?;
        let n_kv = u64_(b, &mut p)?;
        let debut_kv = p;
        let paires = lire_paires(&b[debut_kv..], n_kv).map_err(|e| anyhow!("paires GGUF : {e}"))?;
        let fin_kv = debut_kv + paires.last().map(|x| x.fin).unwrap_or(0);
        let kv_brut = b[debut_kv..fin_kv].to_vec();
        let alignement = paires.iter().find(|x| x.cle == "general.alignment").and_then(|x| x.entier()).unwrap_or(32);
        ensure!(alignement > 0 && alignement.is_power_of_two(), "alignement GGUF {alignement}");
        p = fin_kv;
        let mut infos = Vec::with_capacity(n_t as usize);
        for _ in 0..n_t {
            let n = u64_(b, &mut p)? as usize;
            ensure!(p + n <= b.len(), "en-tête GGUF tronqué");
            let nom = String::from_utf8(b[p..p + n].to_vec()).context("nom de tenseur non UTF-8")?;
            p += n;
            let n_dims = u32_(b, &mut p)?;
            ensure!((1..=4).contains(&n_dims), "{nom} : {n_dims} dimensions");
            let mut ne = [1u64; 4];
            for x in ne.iter_mut().take(n_dims as usize) {
                *x = u64_(b, &mut p)?;
            }
            let type_ggml = u32_(b, &mut p)?;
            let dec = u64_(b, &mut p)?;
            infos.push((nom, n_dims, ne, type_ggml, dec));
        }
        let debut_donnees = (p as u64).div_ceil(alignement) * alignement;
        let mut tenseurs = Vec::with_capacity(infos.len());
        for (nom, n_dims, ne, type_ggml, dec) in infos {
            let (pb, ob) = geometrie_type(type_ggml).ok_or_else(|| anyhow!("{nom} : type ggml {type_ggml} non pris en charge"))?;
            let n: u64 = ne.iter().product();
            ensure!(ne[0] % pb == 0, "{nom} : {} poids par ligne, pas un multiple de {pb}", ne[0]);
            tenseurs.push(TenseurGguf { nom, n_dims, ne, type_ggml, decalage: debut_donnees + dec, octets: n / pb * ob });
        }
        // Second chemin des tailles : rangés par décalage, deux tenseurs voisins sont séparés
        // par moins d'un alignement, et le dernier finit à moins d'un alignement de la fin.
        let mut ordre: Vec<&TenseurGguf> = tenseurs.iter().collect();
        ordre.sort_by_key(|t| t.decalage);
        for (i, t) in ordre.iter().enumerate() {
            let suivant = ordre.get(i + 1).map(|s| s.decalage).unwrap_or(taille);
            let fin = t.decalage + t.octets;
            ensure!(fin <= suivant && suivant - fin < alignement, "{} : taille {} incohérente avec la disposition (fin {fin}, suivant {suivant})", t.nom, t.octets);
        }
        Ok(Gguf { taille, version, n_kv, kv_brut, paires, alignement, debut_donnees, tenseurs })
    }

    pub fn tenseur(&self, nom: &str) -> Result<&TenseurGguf> {
        self.tenseurs.iter().find(|t| t.nom == nom).ok_or_else(|| anyhow!("tenseur {nom} absent du GGUF"))
    }

    pub fn paire(&self, cle: &str) -> Option<&PaireMeta> {
        self.paires.iter().find(|p| p.cle == cle)
    }

    pub fn entier(&self, cle: &str) -> Result<u64> {
        self.paire(cle).and_then(|p| p.entier()).ok_or_else(|| anyhow!("clé entière {cle} absente du GGUF"))
    }

    pub fn architecture(&self) -> Result<String> {
        Ok(self.paire("general.architecture").and_then(|p| p.chaine()).ok_or_else(|| anyhow!("general.architecture absente"))?.to_string())
    }
}

/// Granule des lectures sans tampon : décalage, longueur et adresse du tampon multiples de
/// 4 096 (le secteur du NVMe de la machine est de 512 ou 4 096 octets ; 4 096 couvre les deux).
pub const GRANULE: usize = 4096;

/// `FILE_FLAG_NO_BUFFERING` (winbase.h) : la lecture va du disque au tampon de l'appelant sans
/// passer par le cache de fichiers du système. Raison : la machine est partagée (16 Go de RAM,
/// d'autres agents lisent gpt-oss-120b par projection en mémoire) ; une passe séquentielle de
/// 63 Go par le cache en chasserait leurs pages chaudes. Le codeur ne relit jamais deux fois les
/// mêmes octets dans une passe : le cache ne lui rapporte rien.
const SANS_TAMPON: u32 = 0x2000_0000;

/// Ouvre un fichier en lecture sans tampon (voir `SANS_TAMPON`). Toute lecture doit passer par
/// `lire_a` / `lire_dans`, qui alignent.
pub fn ouvrir_direct(chemin: &Path) -> Result<std::fs::File> {
    use std::os::windows::fs::OpenOptionsExt;
    std::fs::OpenOptions::new().read(true).custom_flags(SANS_TAMPON).open(chemin).with_context(|| format!("ouverture sans tampon de {}", chemin.display()))
}

/// Un tampon dont la tranche utile commence à une adresse multiple de `GRANULE` (code sûr :
/// on sur-alloue d'un granule et l'on décale le début).
pub struct TamponAligne {
    v: Vec<u8>,
    debut: usize,
    n: usize,
}

impl TamponAligne {
    pub fn nouveau(n: usize) -> TamponAligne {
        let v = vec![0u8; n + GRANULE];
        let debut = (GRANULE - (v.as_ptr() as usize) % GRANULE) % GRANULE;
        TamponAligne { v, debut, n }
    }
    pub fn tranche(&self) -> &[u8] {
        &self.v[self.debut..self.debut + self.n]
    }
    pub fn tranche_mut(&mut self) -> &mut [u8] {
        &mut self.v[self.debut..self.debut + self.n]
    }
}

/// Taille du tampon de rebond d'une lecture : 16 Mio (un multiple du granule). La mémoire d'une
/// lecture est ainsi la destination plus 16 Mio, quelle que soit sa longueur (la copie entière de
/// `token_embd`, 0,615 Go, aurait sinon doublé la pointe du codeur).
pub const REBOND: usize = 16 << 20;

/// Lit exactement `n` octets au décalage `d` (lecture positionnelle : plusieurs fils peuvent
/// partager le même fichier). Marche sur un fichier ouvert avec ou sans tampon.
pub fn lire_a(f: &std::fs::File, d: u64, n: usize) -> Result<Vec<u8>> {
    let mut v = vec![0u8; n];
    lire_dans(f, d, &mut v)?;
    Ok(v)
}

/// Remplit `v` avec les octets `[d, d + v.len())`. On lit l'intervalle aligné `[⌊d⌋, ⌈d + n⌉)`
/// (multiples de `GRANULE`) par fenêtres d'au plus `REBOND` octets dans un tampon aligné, et l'on
/// recopie de chaque fenêtre la part demandée.
pub fn lire_dans(f: &std::fs::File, d: u64, v: &mut [u8]) -> Result<()> {
    use std::os::windows::fs::FileExt;
    if v.is_empty() {
        return Ok(());
    }
    let g = GRANULE as u64;
    let fin = d + v.len() as u64;
    let a = d / g * g;
    let b = fin.div_ceil(g) * g;
    let mut t = TamponAligne::nouveau(((b - a) as usize).min(REBOND));
    let mut pos = a; // début de la fenêtre courante, toujours multiple du granule
    while pos < fin {
        let lg = ((b - pos) as usize).min(REBOND);
        // Octets utiles de cette fenêtre : jusqu'à `fin`, pas jusqu'à `b` (le dernier granule
        // peut dépasser la fin du fichier).
        let besoin = ((fin - pos) as usize).min(lg);
        let mut fait = 0usize;
        while fait < besoin {
            // Sans tampon, une lecture n'est courte qu'en fin de fichier, où elle couvre `besoin`
            // (sinon la suivante rend 0). Sur un fichier avec tampon, une lecture courte au milieu
            // reprend simplement au décalage atteint ; sans tampon, un tel décalage non aligné
            // serait refusé par le système (erreur explicite, jamais un octet faux).
            let k = f.seek_read(&mut t.tranche_mut()[fait..lg], pos + fait as u64)?;
            if k == 0 {
                bail!("fin de fichier inattendue à {} ({} octets demandés depuis {d})", pos + fait as u64, v.len());
            }
            fait += k;
        }
        // Part de la fenêtre [pos, pos + besoin) qui tombe dans [d, fin).
        let de = d.max(pos);
        let o_t = (de - pos) as usize;
        let o_v = (de - d) as usize;
        let n = (pos + besoin as u64 - de) as usize;
        v[o_v..o_v + n].copy_from_slice(&t.tranche()[o_t..o_t + n]);
        pos += lg as u64;
    }
    Ok(())
}

/// Les tenseurs d'experts d'une couche : (poids, biais) pour gate, up, down.
pub struct ExpertsCouche<'a> {
    pub poids: [&'a TenseurGguf; 3],
    pub biais: [&'a TenseurGguf; 3],
}

pub const ROLES: [&str; 3] = ["ffn_gate_exps", "ffn_up_exps", "ffn_down_exps"];

/// Vrai pour un nom de tenseur d'experts (`blk.N.ffn_{gate,up,down}_exps.{weight,bias}`).
pub fn est_expert(nom: &str) -> bool {
    let Some(reste) = nom.strip_prefix("blk.") else { return false };
    let Some((n, suite)) = reste.split_once('.') else { return false };
    n.chars().all(|c| c.is_ascii_digit()) && ROLES.iter().any(|r| suite == format!("{r}.weight") || suite == format!("{r}.bias"))
}

impl Gguf {
    pub fn experts_couche(&self, c: u32) -> Result<ExpertsCouche<'_>> {
        let p = |r: &str, s: &str| self.tenseur(&format!("blk.{c}.{r}.{s}"));
        Ok(ExpertsCouche { poids: [p(ROLES[0], "weight")?, p(ROLES[1], "weight")?, p(ROLES[2], "weight")?], biais: [p(ROLES[0], "bias")?, p(ROLES[1], "bias")?, p(ROLES[2], "bias")?] })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Témoin de `lire_dans` : sur un fichier de contenu connu (pseudo-aléatoire, taille non
    /// multiple du granule), toute lecture (décalage et longueur alignés ou non, à cheval sur un
    /// granule, jusqu'au dernier octet) rend exactement les octets attendus, par un descripteur
    /// sans tampon comme par un descripteur ordinaire. Cassure : une lecture au-delà de la fin
    /// est refusée.
    #[test]
    fn lectures_alignees_et_non_alignees() {
        let n = 2 * REBOND + 5 * GRANULE + 1234;
        let mut x = 0x9E37_79B9u32;
        let contenu: Vec<u8> = (0..n)
            .map(|_| {
                x ^= x << 13;
                x ^= x >> 17;
                x ^= x << 5;
                x as u8
            })
            .collect();
        let chemin = std::env::temp_dir().join(format!("trc-codeur-temoin-lecture-{}.bin", std::process::id()));
        std::fs::write(&chemin, &contenu).unwrap();
        let direct = ouvrir_direct(&chemin).unwrap();
        let ordinaire = std::fs::File::open(&chemin).unwrap();
        let cas: Vec<(usize, usize)> = vec![(0, 1), (0, GRANULE), (1, GRANULE), (GRANULE - 1, 2), (GRANULE, 3 * GRANULE), (17, 2 * GRANULE + 5), (n - 1, 1), (n - 1234, 1234), (n - 5000, 5000), (0, n), (3, n - 3), (2 * GRANULE + 7, 0), (REBOND - 5, 10), (REBOND, REBOND), (REBOND - 1, REBOND + 2), (1, 2 * REBOND + 7)];
        for (d, l) in cas {
            for f in [&direct, &ordinaire] {
                let v = lire_a(f, d as u64, l).unwrap();
                assert_eq!(v, &contenu[d..d + l], "décalage {d}, longueur {l}");
            }
        }
        assert!(lire_a(&direct, (n - 10) as u64, 11).is_err(), "une lecture au-delà de la fin doit être refusée");
        // L'empreinte d'un fichier entier, lu sans tampon par morceaux de 16 Mio (taille non
        // multiple du granule : la dernière lecture est courte), égale celle de son contenu.
        {
            use sha2::{Digest, Sha256};
            let (h, lus) = crate::coder::sha256_fichier(&chemin).unwrap();
            assert_eq!(lus, n as u64);
            assert_eq!(h, <[u8; 32]>::from(Sha256::digest(&contenu)));
        }
        assert!(lire_a(&ordinaire, n as u64, 1).is_err());
        drop((direct, ordinaire));
        let _ = std::fs::remove_file(&chemin);
    }
}
