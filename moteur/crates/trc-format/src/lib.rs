//! Le format de fichier `.trc` de troncons, au bit près (decisions/ARCHITECTURE.md § 4).
//!
//! Un fichier autonome par modèle : en-tête fixe de 4 096 octets, puis cinq sections alignées
//! sur 4 096 (MÉTA, RÉSIDENTS, TABLES, RÉPERTOIRE, TRONÇONS). Tout est petit-boutiste. Toute
//! structure porte sa taille, son nombre d'entrées et son empreinte ; ce lecteur refuse une
//! version majeure, une sorte de flux ou un drapeau inconnus, et des octets réservés non nuls.
//!
//! Ce que ce crate fixe, au-delà du texte du § 4 (précisions écrites dans
//! `moteur/REPRISE-F.md`, à porter à l'arbitre ; aucune ne change un octet que le § 4 fixe) :
//! - la longueur d'une section (champ `longueur` de l'en-tête) compte ses octets utiles, son
//!   empreinte finale comprise, et pas le bourrage de zéros qui mène à la section suivante ;
//! - l'empreinte de la table des RÉSIDENTS est rangée juste après le dernier octet de la zone
//!   de données (fin du tenseur qui finit le plus loin), sans alignement ; elle est donc
//!   toujours aux 8 derniers octets de la section ;
//! - les octets utiles d'une partie de tronçon finissent à la fin de son dernier flux ;
//! - le champ « contexte fixe » d'un flux vaut 0 pour DELTA (une seule table) et 0xFF
//!   (« aucun ») pour les flux bruts et pour les flux dont le contexte varie (CODES_CTX,
//!   BASE_CTX, COMPL_CTX) ;
//! - le champ « octets produits » d'un flux rANS vaut P, ce que produit son décodage
//!   (bourrage compris) ; celui d'un flux brut vaut sa longueur.
//!
//! La version 1.2 (lot A de la construction, genome/06-codon-v1-2.md ; décision dans
//! ARCHITECTURE.md § 4.15) ajoute le **codon synonyme du zéro** : drapeau bit 3 CANONIQUE, aucun
//! flux de codes ne porte le demi-octet 8 (−0, que la GEMV lit comme 0), et le champ réservé de 8
//! octets au décalage 56 d'une entrée du répertoire devient l'empreinte de l'expert **canonique**
//! (chaque demi-octet 8 des `qs` remplacé par 0). Ce lecteur refuse le bit 3 sous une version
//! mineure < 2, sur un fichier brut ou à deux niveaux, et vérifie à l'ouverture que toute table
//! CODES_CTX d'un fichier canonique donne la fréquence 0 aux 31 octets qui portent un demi-octet 8.

use sha2::{Digest, Sha256};
use std::io::{BufWriter, Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};

pub mod meta;
pub use meta::{PaireMeta, ValeurMeta, lire_paires, paire_chaine};

// ---------------------------------------------------------------------------------------------
// Constantes du format

pub const MAGIE: [u8; 8] = *b"TRONCONS";
pub const ALIGNEMENT: u64 = 4096;
pub const TAILLE_ENTETE: usize = 4096;
/// Version majeure lue et écrite par ce crate.
pub const VERSION_MAJEURE: u16 = 1;
/// Plus haute version mineure que ce lecteur lit (§ 4.15 : 1.0 en J1, 1.1 en J2, 1.2 pour le
/// codon synonyme du zéro).
pub const VERSION_MINEURE: u16 = 2;
/// Première version mineure qui définit le drapeau CANONIQUE.
pub const VERSION_MINEURE_CANONIQUE: u16 = 2;

/// Bit 0 : tronçons alignés sur 4 096 (toujours 1).
pub const DRAPEAU_ALIGNE: u32 = 1;
/// Bit 1 : au moins deux niveaux de raffinement.
pub const DRAPEAU_NIVEAUX: u32 = 2;
/// Bit 2 : fichier brut (flux non codés, chemin de référence du témoin C3).
pub const DRAPEAU_BRUT: u32 = 4;
/// Bit 3 (v1.2) : codes canoniques. Aucun flux de codes ne contient le demi-octet 8 ; l'expert
/// décodé se compare à `empreinte_canonique` du répertoire.
pub const DRAPEAU_CANONIQUE: u32 = 8;
/// Bit 5 (v1.2, lot B ; genome/07-genome-synonyme.md) : fichier compagnon du **mode rapide**. Les
/// demi-octets des flux CODES_CTX sont des symboles de base (bit 3 le signe, bits 0-1 la classe,
/// bit 2 nul), servis par les centres de la table CENTRES ; le décodeur est celui du mode exact.
/// Refusé sous une version mineure < 2, avec les bits 1 (niveaux), 2 (brut) ou 3 (canonique).
pub const DRAPEAU_RAPIDE: u32 = 32;
const DRAPEAUX_CONNUS: u32 = DRAPEAU_ALIGNE | DRAPEAU_NIVEAUX | DRAPEAU_BRUT | DRAPEAU_CANONIQUE | DRAPEAU_RAPIDE;

/// Le demi-octet canonique : 8 (−0) devient 0 (+0) ; tout autre est inchangé.
#[inline]
pub const fn canoniser_demi(c: u8) -> u8 {
    if c == 8 { 0 } else { c }
}

/// L'octet canonique : ses deux demi-octets canonisés.
#[inline]
pub const fn canoniser_octet(o: u8) -> u8 {
    canoniser_demi(o & 15) | (canoniser_demi(o >> 4) << 4)
}

/// Vrai si l'octet porte un demi-octet 8 (31 octets sur 256).
#[inline]
pub const fn porte_un_8(o: u8) -> bool {
    (o & 15) == 8 || (o >> 4) == 8
}

/// Magie d'une partie de tronçon, par niveau : « TRC0 », « TRC1 ».
pub const MAGIE_PARTIE: [u32; 2] = [0x3043_5254, 0x3143_5254];
pub const TAILLE_ENTETE_PARTIE: usize = 64;
pub const TAILLE_DESC_FLUX: usize = 16;
pub const ALIGNEMENT_FLUX: usize = 16;
pub const TAILLE_ENTREE_REPERTOIRE: usize = 64;
pub const TAILLE_ENTREE_RESIDENT: usize = 128;
pub const ALIGNEMENT_RESIDENT: u64 = 256;
/// « Contexte fixe : aucun » dans la table des flux d'une partie.
pub const CONTEXTE_AUCUN: u8 = 0xFF;

/// Indices des sections dans la table de l'en-tête.
pub const SECTION_META: usize = 0;
pub const SECTION_RESIDENTS: usize = 1;
pub const SECTION_TABLES: usize = 2;
pub const SECTION_REPERTOIRE: usize = 3;
pub const SECTION_TRONCONS: usize = 4;

/// `x` arrondi au multiple de `a` supérieur.
#[inline]
pub fn aligner(x: u64, a: u64) -> u64 {
    x.div_ceil(a) * a
}

/// empreinte64(octets) : les 8 premiers octets de SHA-256(octets), lus comme un u64
/// petit-boutiste (§ 4.12).
pub fn empreinte64(octets: &[u8]) -> u64 {
    let h = Sha256::digest(octets);
    u64::from_le_bytes(h[..8].try_into().unwrap())
}

/// La même empreinte, calculée sur une suite de morceaux (sans les recopier bout à bout).
pub fn empreinte64_morceaux<'a>(morceaux: impl IntoIterator<Item = &'a [u8]>) -> u64 {
    let mut h = Sha256::new();
    for m in morceaux {
        h.update(m);
    }
    let d = h.finalize();
    u64::from_le_bytes(d[..8].try_into().unwrap())
}

// ---------------------------------------------------------------------------------------------
// Erreurs

#[derive(Debug, thiserror::Error)]
pub enum ErreurFormat {
    #[error("lecture ou écriture : {0}")]
    Es(#[from] std::io::Error),
    #[error("magie inconnue : ce n'est pas un fichier .trc")]
    Magie,
    #[error("version {0}.{1} non lue par ce lecteur (1.0 à 1.{VERSION_MINEURE})")]
    Version(u16, u16),
    #[error("drapeaux inconnus ou incohérents : {0:#x}")]
    Drapeaux(u32),
    #[error("sorte de flux inconnue : {0:#04x}")]
    Sorte(u8),
    #[error("champ « {champ} » : attendu {attendu}, lu {lu}")]
    Champ { champ: String, attendu: String, lu: String },
    #[error("empreinte fausse : {0}")]
    Empreinte(String),
    #[error("octets réservés non nuls : {0}")]
    Reserve(String),
    #[error("structure tronquée ou hors limites : {0}")]
    Limites(String),
}

fn champ(champ: &str, attendu: impl std::fmt::Display, lu: impl std::fmt::Display) -> ErreurFormat {
    ErreurFormat::Champ { champ: champ.to_string(), attendu: attendu.to_string(), lu: lu.to_string() }
}

fn limites(s: impl Into<String>) -> ErreurFormat {
    ErreurFormat::Limites(s.into())
}

// ---------------------------------------------------------------------------------------------
// Lecture et écriture petit-boutistes

#[inline]
pub fn lu16(b: &[u8], p: usize) -> u16 {
    u16::from_le_bytes(b[p..p + 2].try_into().unwrap())
}
#[inline]
pub fn lu32(b: &[u8], p: usize) -> u32 {
    u32::from_le_bytes(b[p..p + 4].try_into().unwrap())
}
#[inline]
pub fn lu64(b: &[u8], p: usize) -> u64 {
    u64::from_le_bytes(b[p..p + 8].try_into().unwrap())
}
#[inline]
fn eu16(b: &mut [u8], p: usize, v: u16) {
    b[p..p + 2].copy_from_slice(&v.to_le_bytes());
}
#[inline]
fn eu32(b: &mut [u8], p: usize, v: u32) {
    b[p..p + 4].copy_from_slice(&v.to_le_bytes());
}
#[inline]
fn eu64(b: &mut [u8], p: usize, v: u64) {
    b[p..p + 8].copy_from_slice(&v.to_le_bytes());
}

fn tout_nul(b: &[u8]) -> bool {
    b.iter().all(|&x| x == 0)
}

// ---------------------------------------------------------------------------------------------
// Les sortes de flux (§ 4.10)

#[repr(u8)]
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Sorte {
    Medianes = 0x01,
    Biais = 0x02,
    Delta = 0x03,
    CodesCtx = 0x04,
    CodesBruts = 0x06,
    EchellesBrutes = 0x07,
    BaseCtx = 0x10,
    ComplCtx = 0x11,
    Centres = 0x12,
}

impl TryFrom<u8> for Sorte {
    type Error = ErreurFormat;
    /// 0x05 (trois flux de classe réassemblés) est réservé : « non produit, non lu ».
    fn try_from(v: u8) -> Result<Sorte, ErreurFormat> {
        Ok(match v {
            0x01 => Sorte::Medianes,
            0x02 => Sorte::Biais,
            0x03 => Sorte::Delta,
            0x04 => Sorte::CodesCtx,
            0x06 => Sorte::CodesBruts,
            0x07 => Sorte::EchellesBrutes,
            0x10 => Sorte::BaseCtx,
            0x11 => Sorte::ComplCtx,
            0x12 => Sorte::Centres,
            _ => return Err(ErreurFormat::Sorte(v)),
        })
    }
}

impl Sorte {
    /// Vrai pour les flux codés par rANS (§ 4.9) ; faux pour les flux bruts et CENTRES.
    pub fn est_rans(self) -> bool {
        matches!(self, Sorte::Delta | Sorte::CodesCtx | Sorte::BaseCtx | Sorte::ComplCtx)
    }
}

// ---------------------------------------------------------------------------------------------
// L'en-tête fixe (§ 4.3)

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Section {
    pub decalage: u64,
    pub longueur: u64,
}

impl Section {
    pub fn fin(&self) -> u64 {
        self.decalage + self.longueur
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Entete {
    pub version: (u16, u16),
    pub drapeaux: u32,
    pub taille_fichier: u64,
    pub sha256_source: [u8; 32],
    pub taille_source: u64,
    pub couches: u16,
    pub experts: u16,
    pub k: u16,
    pub matrices: u16,
    pub lignes: [u32; 4],
    pub colonnes: [u32; 4],
    /// Extension de la couture (champs du § 4.3, absents de la structure du § 5.3) : poids par
    /// bloc (32), octets par bloc d'origine (17), type ggml des experts (39, MXFP4).
    pub poids_par_bloc: u32,
    pub octets_par_bloc: u32,
    pub type_ggml: u8,
    pub niveaux: u8,
    pub classes_echelle: u8,
    pub partition: [u8; 8],
    pub sections: [Section; 8],
}

impl Entete {
    pub fn est_brut(&self) -> bool {
        self.drapeaux & DRAPEAU_BRUT != 0
    }

    /// Vrai pour un fichier compagnon du mode rapide (drapeau bit 5, lot B).
    pub fn est_rapide(&self) -> bool {
        self.drapeaux & DRAPEAU_RAPIDE != 0
    }

    /// Vrai pour un fichier v1.2 à codes canoniques (drapeau bit 3).
    pub fn est_canonique(&self) -> bool {
        self.drapeaux & DRAPEAU_CANONIQUE != 0
    }

    /// Les 4 096 octets de l'en-tête, empreinte comprise.
    pub fn vers_octets(&self) -> Vec<u8> {
        let mut b = vec![0u8; TAILLE_ENTETE];
        b[0..8].copy_from_slice(&MAGIE);
        eu16(&mut b, 8, self.version.0);
        eu16(&mut b, 10, self.version.1);
        eu32(&mut b, 12, self.drapeaux);
        eu32(&mut b, 16, ALIGNEMENT as u32);
        eu32(&mut b, 20, TAILLE_ENTETE as u32);
        eu64(&mut b, 24, self.taille_fichier);
        b[32..64].copy_from_slice(&self.sha256_source);
        eu64(&mut b, 64, self.taille_source);
        eu16(&mut b, 72, self.couches);
        eu16(&mut b, 74, self.experts);
        eu16(&mut b, 76, self.k);
        eu16(&mut b, 78, self.matrices);
        for j in 0..4 {
            eu32(&mut b, 80 + 4 * j, self.lignes[j]);
            eu32(&mut b, 96 + 4 * j, self.colonnes[j]);
        }
        eu32(&mut b, 112, self.poids_par_bloc);
        eu32(&mut b, 116, self.octets_par_bloc);
        b[120] = self.type_ggml;
        b[121] = self.niveaux;
        b[122] = self.classes_echelle;
        b[124..132].copy_from_slice(&self.partition);
        for (i, s) in self.sections.iter().enumerate() {
            eu64(&mut b, 136 + 16 * i, s.decalage);
            eu64(&mut b, 144 + 16 * i, s.longueur);
        }
        let e = empreinte64(&b[..4088]);
        eu64(&mut b, 4088, e);
        b
    }

    /// Lit et vérifie l'en-tête (tout sauf la taille réelle du fichier, que vérifie
    /// [`Fichier::ouvrir`]).
    pub fn depuis_octets(b: &[u8]) -> Result<Entete, ErreurFormat> {
        if b.len() < TAILLE_ENTETE {
            return Err(limites(format!("en-tête de {} octets au lieu de 4 096", b.len())));
        }
        if b[0..8] != MAGIE {
            return Err(ErreurFormat::Magie);
        }
        let e_lue = lu64(b, 4088);
        let e_calc = empreinte64(&b[..4088]);
        if e_lue != e_calc {
            return Err(ErreurFormat::Empreinte(format!("en-tête : lue {e_lue:#018x}, calculée {e_calc:#018x}")));
        }
        let version = (lu16(b, 8), lu16(b, 10));
        if version.0 != VERSION_MAJEURE || version.1 > VERSION_MINEURE {
            return Err(ErreurFormat::Version(version.0, version.1));
        }
        let drapeaux = lu32(b, 12);
        if drapeaux & !DRAPEAUX_CONNUS != 0 || drapeaux & DRAPEAU_ALIGNE == 0 {
            return Err(ErreurFormat::Drapeaux(drapeaux));
        }
        if lu32(b, 16) != ALIGNEMENT as u32 {
            return Err(champ("alignement", ALIGNEMENT, lu32(b, 16)));
        }
        if lu32(b, 20) != TAILLE_ENTETE as u32 {
            return Err(champ("taille de l'en-tête", TAILLE_ENTETE, lu32(b, 20)));
        }
        if b[123] != 0 || !tout_nul(&b[132..136]) || !tout_nul(&b[264..4088]) {
            return Err(ErreurFormat::Reserve("en-tête".into()));
        }
        let mut sha256_source = [0u8; 32];
        sha256_source.copy_from_slice(&b[32..64]);
        let mut lignes = [0u32; 4];
        let mut colonnes = [0u32; 4];
        for j in 0..4 {
            lignes[j] = lu32(b, 80 + 4 * j);
            colonnes[j] = lu32(b, 96 + 4 * j);
        }
        let mut partition = [0u8; 8];
        partition.copy_from_slice(&b[124..132]);
        let mut sections = [Section::default(); 8];
        for (i, s) in sections.iter_mut().enumerate() {
            *s = Section { decalage: lu64(b, 136 + 16 * i), longueur: lu64(b, 144 + 16 * i) };
        }
        let e = Entete {
            version,
            drapeaux,
            taille_fichier: lu64(b, 24),
            sha256_source,
            taille_source: lu64(b, 64),
            couches: lu16(b, 72),
            experts: lu16(b, 74),
            k: lu16(b, 76),
            matrices: lu16(b, 78),
            lignes,
            colonnes,
            poids_par_bloc: lu32(b, 112),
            octets_par_bloc: lu32(b, 116),
            type_ggml: b[120],
            niveaux: b[121],
            classes_echelle: b[122],
            partition,
            sections,
        };
        e.verifier_coherence()?;
        Ok(e)
    }

    fn verifier_coherence(&self) -> Result<(), ErreurFormat> {
        if !(1..=2).contains(&self.niveaux) {
            return Err(champ("nombre de niveaux", "1 ou 2", self.niveaux));
        }
        if (self.niveaux >= 2) != (self.drapeaux & DRAPEAU_NIVEAUX != 0) {
            return Err(ErreurFormat::Drapeaux(self.drapeaux));
        }
        if self.version.1 == 0 && self.niveaux != 1 {
            return Err(champ("nombre de niveaux (v1.0)", 1, self.niveaux));
        }
        if self.est_brut() && self.niveaux != 1 {
            return Err(ErreurFormat::Drapeaux(self.drapeaux));
        }
        // Le drapeau CANONIQUE n'existe qu'à partir de la v1.2, sur un fichier codé à un niveau :
        // le fichier brut reste le chemin de référence (octets du GGUF tels quels), et la v1.2 ne
        // définit pas la forme canonique des flux de B (BASE_CTX, COMPL_CTX).
        if self.est_canonique() && (self.version.1 < VERSION_MINEURE_CANONIQUE || self.est_brut() || self.niveaux != 1) {
            return Err(ErreurFormat::Drapeaux(self.drapeaux));
        }
        // Le drapeau RAPIDE (lot B) : un niveau, codé, et pas canonique (le demi-octet 8 y est le
        // symbole « −c₀ », une vraie valeur).
        if self.est_rapide() && (self.version.1 < 2 || self.est_brut() || self.niveaux != 1 || self.est_canonique()) {
            return Err(ErreurFormat::Drapeaux(self.drapeaux));
        }
        if self.matrices == 0 || self.matrices > 4 {
            return Err(champ("matrices par expert", "1 à 4", self.matrices));
        }
        for j in self.matrices as usize..4 {
            if self.lignes[j] != 0 || self.colonnes[j] != 0 {
                return Err(ErreurFormat::Reserve(format!("dimensions de la matrice {j}")));
            }
        }
        if self.couches == 0 || self.experts == 0 || self.k == 0 || self.k > self.experts {
            return Err(champ("couches, experts, k", "non nuls, k ≤ E", format!("{} {} {}", self.couches, self.experts, self.k)));
        }
        for (i, s) in self.sections.iter().enumerate() {
            if i >= 5 {
                if *s != Section::default() {
                    return Err(ErreurFormat::Reserve(format!("section {i}")));
                }
            } else if s.decalage % ALIGNEMENT != 0 || s.decalage < TAILLE_ENTETE as u64 {
                return Err(champ(&format!("décalage de la section {i}"), "multiple de 4 096 après l'en-tête", s.decalage));
            }
        }
        Ok(())
    }
}

// ---------------------------------------------------------------------------------------------
// Le répertoire (§ 4.7)

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct EntreeRepertoire {
    pub decalage: u64,
    pub longueur: [u32; 2],
    pub utiles: [u32; 2],
    pub empreinte_origine: u64,
    pub empreinte_niveau: [u64; 2],
    pub couche: u16,
    pub expert: u16,
    /// v1.2, drapeau CANONIQUE : empreinte64 de l'expert canonique (décalage 56) ; 0 sinon.
    pub empreinte_canonique: u64,
}

impl EntreeRepertoire {
    pub fn vers_octets(&self, b: &mut [u8]) {
        b[..TAILLE_ENTREE_REPERTOIRE].fill(0);
        eu64(b, 0, self.decalage);
        eu32(b, 8, self.longueur[0]);
        eu32(b, 12, self.longueur[1]);
        eu32(b, 16, self.utiles[0]);
        eu32(b, 20, self.utiles[1]);
        eu64(b, 24, self.empreinte_origine);
        eu64(b, 32, self.empreinte_niveau[0]);
        eu64(b, 40, self.empreinte_niveau[1]);
        eu16(b, 48, self.couche);
        eu16(b, 50, self.expert);
        eu64(b, 56, self.empreinte_canonique);
    }

    pub fn depuis_octets(b: &[u8]) -> Result<EntreeRepertoire, ErreurFormat> {
        // Le décalage 56 (empreinte canonique) se contrôle dans `Fichier::ouvrir`, qui connaît le
        // drapeau CANONIQUE : il doit y valoir 0 sans lui.
        if !tout_nul(&b[52..56]) {
            return Err(ErreurFormat::Reserve("entrée du répertoire".into()));
        }
        Ok(EntreeRepertoire {
            decalage: lu64(b, 0),
            longueur: [lu32(b, 8), lu32(b, 12)],
            utiles: [lu32(b, 16), lu32(b, 20)],
            empreinte_origine: lu64(b, 24),
            empreinte_niveau: [lu64(b, 32), lu64(b, 40)],
            couche: lu16(b, 48),
            expert: lu16(b, 50),
            empreinte_canonique: lu64(b, 56),
        })
    }

    /// L'empreinte à laquelle se compare l'expert **décodé** (mode témoin, § 4.12) : la canonique
    /// sur un fichier canonique, celle d'origine sinon.
    pub fn empreinte_du_decode(&self, canonique: bool) -> u64 {
        if canonique { self.empreinte_canonique } else { self.empreinte_origine }
    }

    /// Octets à lire pour avoir les niveaux 0 à `niveaux − 1` (une seule requête).
    pub fn longueur_jusqua(&self, niveaux: usize) -> u64 {
        self.longueur[..niveaux].iter().map(|&x| x as u64).sum()
    }
}

/// Les octets de la section RÉPERTOIRE : les entrées puis l'empreinte64 de ces entrées.
pub fn serialiser_repertoire(entrees: &[EntreeRepertoire]) -> Vec<u8> {
    let mut b = vec![0u8; entrees.len() * TAILLE_ENTREE_REPERTOIRE + 8];
    for (i, e) in entrees.iter().enumerate() {
        e.vers_octets(&mut b[i * TAILLE_ENTREE_REPERTOIRE..]);
    }
    let n = entrees.len() * TAILLE_ENTREE_REPERTOIRE;
    let h = empreinte64(&b[..n]);
    eu64(&mut b, n, h);
    b
}

// ---------------------------------------------------------------------------------------------
// Les tables (§ 4.6)

#[derive(Clone, Debug, PartialEq)]
pub enum Charge {
    /// Type de charge 1 : 16 fréquences u16 (32 o).
    Freq16([u16; 16]),
    /// Type de charge 2 : 256 fréquences u16 (512 o).
    Freq256(Box<[u16; 256]>),
    /// Type de charge 3 : 4 centres f32 (16 o).
    Centres([f32; 4]),
}

impl Charge {
    pub fn type_charge(&self) -> u8 {
        match self {
            Charge::Freq16(_) => 1,
            Charge::Freq256(_) => 2,
            Charge::Centres(_) => 3,
        }
    }
    pub fn octets(type_charge: u8) -> Option<usize> {
        match type_charge {
            1 => Some(32),
            2 => Some(512),
            3 => Some(16),
            _ => None,
        }
    }
    /// Les fréquences, pour les charges 1 et 2.
    pub fn frequences(&self) -> Option<&[u16]> {
        match self {
            Charge::Freq16(f) => Some(&f[..]),
            Charge::Freq256(f) => Some(&f[..]),
            Charge::Centres(_) => None,
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Table {
    pub couche: u16,
    pub matrice: u8,
    pub sorte: Sorte,
    pub contexte: u8,
    pub charge: Charge,
}

/// Les octets de la section TABLES : n, réservé, enregistrements, empreinte64.
pub fn serialiser_tables(tables: &[Table]) -> Vec<u8> {
    let mut b = Vec::new();
    b.extend_from_slice(&(tables.len() as u32).to_le_bytes());
    b.extend_from_slice(&0u32.to_le_bytes());
    for t in tables {
        b.extend_from_slice(&t.couche.to_le_bytes());
        b.push(t.matrice);
        b.push(t.sorte as u8);
        b.push(t.contexte);
        b.push(t.charge.type_charge());
        b.extend_from_slice(&0u16.to_le_bytes());
        match &t.charge {
            Charge::Freq16(f) => f.iter().for_each(|x| b.extend_from_slice(&x.to_le_bytes())),
            Charge::Freq256(f) => f.iter().for_each(|x| b.extend_from_slice(&x.to_le_bytes())),
            Charge::Centres(c) => c.iter().for_each(|x| b.extend_from_slice(&x.to_le_bytes())),
        }
    }
    let h = empreinte64(&b);
    b.extend_from_slice(&h.to_le_bytes());
    b
}

/// Lit la section TABLES (sans son bourrage) ; vérifie l'empreinte, les sortes, les sommes.
pub fn lire_tables(b: &[u8], entete: &Entete) -> Result<Vec<Table>, ErreurFormat> {
    if b.len() < 16 {
        return Err(limites("section TABLES trop courte"));
    }
    let n_corps = b.len() - 8;
    let h = empreinte64(&b[..n_corps]);
    if h != lu64(b, n_corps) {
        return Err(ErreurFormat::Empreinte("section TABLES".into()));
    }
    let n = lu32(b, 0) as usize;
    if lu32(b, 4) != 0 {
        return Err(ErreurFormat::Reserve("en-tête de TABLES".into()));
    }
    let mut p = 8;
    let mut tables = Vec::with_capacity(n);
    for i in 0..n {
        if p + 8 > n_corps {
            return Err(limites(format!("enregistrement de table {i}")));
        }
        let couche = lu16(b, p);
        let matrice = b[p + 2];
        let sorte = Sorte::try_from(b[p + 3])?;
        let contexte = b[p + 4];
        let tc = b[p + 5];
        if lu16(b, p + 6) != 0 {
            return Err(ErreurFormat::Reserve(format!("enregistrement de table {i}")));
        }
        let taille = Charge::octets(tc).ok_or_else(|| champ("type de charge", "1, 2 ou 3", tc))?;
        p += 8;
        if p + taille > n_corps {
            return Err(limites(format!("charge de la table {i}")));
        }
        if couche >= entete.couches || matrice as u16 >= entete.matrices {
            return Err(champ("table : (couche, matrice)", format!("< ({}, {})", entete.couches, entete.matrices), format!("({couche}, {matrice})")));
        }
        let charge = match tc {
            1 => {
                let mut f = [0u16; 16];
                for (s, x) in f.iter_mut().enumerate() {
                    *x = lu16(b, p + 2 * s);
                }
                Charge::Freq16(f)
            }
            2 => {
                let mut f = Box::new([0u16; 256]);
                for (s, x) in f.iter_mut().enumerate() {
                    *x = lu16(b, p + 2 * s);
                }
                Charge::Freq256(f)
            }
            _ => {
                let mut c = [0f32; 4];
                for (s, x) in c.iter_mut().enumerate() {
                    *x = f32::from_le_bytes(b[p + 4 * s..p + 4 * s + 4].try_into().unwrap());
                }
                Charge::Centres(c)
            }
        };
        if let Some(f) = charge.frequences() {
            let somme: u32 = f.iter().map(|&x| x as u32).sum();
            if somme != 4096 || f.iter().any(|&x| x > 4096) {
                return Err(champ(&format!("somme des fréquences de la table {i}"), 4096, somme));
            }
        }
        p += taille;
        tables.push(Table { couche, matrice, sorte, contexte, charge });
    }
    if p != n_corps {
        return Err(limites("octets en trop dans la section TABLES"));
    }
    Ok(tables)
}

/// Refuse une table CODES_CTX qui donne une fréquence non nulle à un octet portant un demi-octet 8
/// (invariant du drapeau CANONIQUE, v1.2).
pub fn verifier_tables_canoniques(tables: &[Table]) -> Result<(), ErreurFormat> {
    for t in tables.iter().filter(|t| t.sorte == Sorte::CodesCtx) {
        match &t.charge {
            Charge::Freq256(f) => {
                if let Some(s) = (0..=255u8).find(|&s| porte_un_8(s) && f[s as usize] != 0) {
                    return Err(champ(
                        &format!("table CODES_CTX ({}, {}, contexte {}) d'un fichier canonique", t.couche, t.matrice, t.contexte),
                        "fréquence 0 pour tout octet portant un demi-octet 8",
                        format!("octet {s:#04x} de fréquence {}", f[s as usize]),
                    ));
                }
            }
            _ => return Err(champ("charge d'une table CODES_CTX", "256 fréquences (type 2)", t.charge.type_charge())),
        }
    }
    Ok(())
}

// ---------------------------------------------------------------------------------------------
// Les tenseurs résidents (§ 4.5)

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TenseurResident {
    pub nom: String,
    pub type_ggml: u32,
    pub ne: [u64; 4],
    pub n_dims: u32,
    /// Depuis le début de la zone de données (multiple de 256).
    pub decalage: u64,
    pub octets: u64,
    pub empreinte: u64,
}

/// Décalages (multiples de 256, depuis le début de la zone de données) de tenseurs rangés à la
/// suite dans l'ordre donné, et la fin de la zone (fin du dernier tenseur).
pub fn disposer_residents(octets: &[u64]) -> (Vec<u64>, u64) {
    let mut d = Vec::with_capacity(octets.len());
    let mut fin = 0u64;
    let mut p = 0u64;
    for &o in octets {
        p = aligner(p, ALIGNEMENT_RESIDENT);
        d.push(p);
        p += o;
        fin = p;
    }
    (d, fin)
}

/// Octets de la table des résidents (8 + 128 n), complétée de zéros jusqu'au multiple de 4 096 :
/// la zone de données commence là, depuis le début de la section.
pub fn debut_zone_residents(n: usize) -> u64 {
    aligner(8 + (TAILLE_ENTREE_RESIDENT * n) as u64, ALIGNEMENT)
}

/// La table des résidents (8 + 128 n octets, sans bourrage).
pub fn serialiser_table_residents(t: &[TenseurResident]) -> Result<Vec<u8>, ErreurFormat> {
    let mut b = vec![0u8; 8 + TAILLE_ENTREE_RESIDENT * t.len()];
    eu32(&mut b, 0, t.len() as u32);
    for (i, r) in t.iter().enumerate() {
        let p = 8 + TAILLE_ENTREE_RESIDENT * i;
        let nom = r.nom.as_bytes();
        if nom.len() > 64 || nom.contains(&0) {
            return Err(champ("nom de tenseur résident", "au plus 64 octets UTF-8 sans zéro", &r.nom));
        }
        b[p..p + nom.len()].copy_from_slice(nom);
        eu32(&mut b, p + 64, r.type_ggml);
        eu32(&mut b, p + 68, r.n_dims);
        for j in 0..4 {
            eu64(&mut b, p + 72 + 8 * j, r.ne[j]);
        }
        eu64(&mut b, p + 104, r.decalage);
        eu64(&mut b, p + 112, r.octets);
        eu64(&mut b, p + 120, r.empreinte);
    }
    Ok(b)
}

fn lire_table_residents(b: &[u8]) -> Result<Vec<TenseurResident>, ErreurFormat> {
    let n = lu32(b, 0) as usize;
    if lu32(b, 4) != 0 {
        return Err(ErreurFormat::Reserve("en-tête de RÉSIDENTS".into()));
    }
    if b.len() < 8 + TAILLE_ENTREE_RESIDENT * n {
        return Err(limites("table des résidents"));
    }
    let mut v = Vec::with_capacity(n);
    for i in 0..n {
        let p = 8 + TAILLE_ENTREE_RESIDENT * i;
        let brut = &b[p..p + 64];
        let lg = brut.iter().position(|&x| x == 0).unwrap_or(64);
        if !tout_nul(&brut[lg..]) {
            return Err(ErreurFormat::Reserve(format!("nom du résident {i}")));
        }
        let nom = std::str::from_utf8(&brut[..lg]).map_err(|_| champ("nom de résident", "UTF-8", i))?.to_string();
        let mut ne = [0u64; 4];
        for (j, x) in ne.iter_mut().enumerate() {
            *x = lu64(b, p + 72 + 8 * j);
        }
        let r = TenseurResident {
            nom,
            type_ggml: lu32(b, p + 64),
            n_dims: lu32(b, p + 68),
            ne,
            decalage: lu64(b, p + 104),
            octets: lu64(b, p + 112),
            empreinte: lu64(b, p + 120),
        };
        if r.decalage % ALIGNEMENT_RESIDENT != 0 || r.n_dims > 4 || r.n_dims == 0 {
            return Err(champ(&format!("résident {}", r.nom), "décalage multiple de 256, 1 à 4 dimensions", format!("{} {}", r.decalage, r.n_dims)));
        }
        v.push(r);
    }
    Ok(v)
}

// ---------------------------------------------------------------------------------------------
// Une partie de tronçon (§ 4.8)

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct DescFlux {
    pub sorte: Sorte,
    pub matrice: u8,
    pub contexte: u8,
    pub decalage: u32,
    pub longueur: u32,
    pub produits: u32,
}

#[derive(Clone, Debug)]
pub struct Partie<'a> {
    pub couche: u16,
    pub expert: u16,
    pub niveau: u8,
    pub flux: Vec<DescFlux>,
    pub octets: &'a [u8],
    /// Extension de la couture : nombre de matrices et octets utiles (en-tête compris).
    pub n_matrices: u8,
    pub utiles: u32,
}

impl<'a> Partie<'a> {
    /// Les octets d'un flux de cette partie.
    pub fn octets_flux(&self, d: &DescFlux) -> &'a [u8] {
        &self.octets[d.decalage as usize..(d.decalage + d.longueur) as usize]
    }
    /// Le premier flux de cette sorte et de cette matrice.
    pub fn trouver(&self, sorte: Sorte, matrice: u8) -> Option<&DescFlux> {
        self.flux.iter().find(|d| d.sorte == sorte && d.matrice == matrice)
    }
}

/// Lit une partie de tronçon (ses octets, bourrage compris ou non) et vérifie sa structure.
pub fn lire_partie(octets: &[u8]) -> Result<Partie<'_>, ErreurFormat> {
    if octets.len() < TAILLE_ENTETE_PARTIE {
        return Err(limites("partie de tronçon plus courte que son en-tête"));
    }
    let magie = lu32(octets, 0);
    let niveau = octets[8];
    if niveau as usize >= MAGIE_PARTIE.len() || magie != MAGIE_PARTIE[niveau as usize] {
        return Err(champ("magie de partie", "TRC0 ou TRC1 selon le niveau", format!("{magie:#010x}, niveau {niveau}")));
    }
    let couche = lu16(octets, 4);
    let expert = lu16(octets, 6);
    let n_matrices = octets[9];
    let n_flux = lu16(octets, 10) as usize;
    let utiles = lu32(octets, 12);
    if !tout_nul(&octets[16..64]) {
        return Err(ErreurFormat::Reserve("en-tête de partie".into()));
    }
    if utiles as usize > octets.len() {
        return Err(limites(format!("partie : {utiles} octets utiles annoncés, {} présents", octets.len())));
    }
    let fin_table = TAILLE_ENTETE_PARTIE + TAILLE_DESC_FLUX * n_flux;
    if fin_table > utiles as usize {
        return Err(limites("table des flux hors de la partie"));
    }
    let mut flux = Vec::with_capacity(n_flux);
    let mut fin_prec = fin_table as u64;
    for i in 0..n_flux {
        let p = TAILLE_ENTETE_PARTIE + TAILLE_DESC_FLUX * i;
        let sorte = Sorte::try_from(octets[p])?;
        let d = DescFlux {
            sorte,
            matrice: octets[p + 1],
            contexte: octets[p + 2],
            decalage: lu32(octets, p + 4),
            longueur: lu32(octets, p + 8),
            produits: lu32(octets, p + 12),
        };
        if octets[p + 3] != 0 {
            return Err(ErreurFormat::Reserve(format!("descripteur du flux {i}")));
        }
        if d.matrice >= n_matrices {
            return Err(champ(&format!("matrice du flux {i}"), format!("< {n_matrices}"), d.matrice));
        }
        if d.decalage as usize % ALIGNEMENT_FLUX != 0 || (d.decalage as u64) < fin_prec || d.decalage as u64 + d.longueur as u64 > utiles as u64 {
            return Err(limites(format!("flux {i} : décalage {}, longueur {}", d.decalage, d.longueur)));
        }
        fin_prec = d.decalage as u64 + d.longueur as u64;
        flux.push(d);
    }
    if !tout_nul(&octets[utiles as usize..]) {
        return Err(ErreurFormat::Reserve("bourrage de la partie".into()));
    }
    Ok(Partie { couche, expert, niveau, flux, octets, n_matrices, utiles })
}

/// Un flux à ranger dans une partie : sa description (sans décalage) et ses octets.
pub struct FluxAEcrire<'a> {
    pub sorte: Sorte,
    pub matrice: u8,
    pub contexte: u8,
    pub produits: u32,
    pub octets: &'a [u8],
}

/// Assemble une partie : en-tête, table des flux, flux alignés sur 16, zéros jusqu'au multiple
/// de 4 096. Rend les octets (longueur multiple de 4 096) et le nombre d'octets utiles.
pub fn assembler_partie(couche: u16, expert: u16, niveau: u8, n_matrices: u8, flux: &[FluxAEcrire]) -> (Vec<u8>, u32) {
    let fin_table = TAILLE_ENTETE_PARTIE + TAILLE_DESC_FLUX * flux.len();
    let mut decalages = Vec::with_capacity(flux.len());
    let mut p = fin_table;
    for f in flux {
        p = p.div_ceil(ALIGNEMENT_FLUX) * ALIGNEMENT_FLUX;
        decalages.push(p);
        p += f.octets.len();
    }
    let utiles = p;
    let mut b = vec![0u8; aligner(utiles as u64, ALIGNEMENT) as usize];
    eu32(&mut b, 0, MAGIE_PARTIE[niveau as usize]);
    eu16(&mut b, 4, couche);
    eu16(&mut b, 6, expert);
    b[8] = niveau;
    b[9] = n_matrices;
    eu16(&mut b, 10, flux.len() as u16);
    eu32(&mut b, 12, utiles as u32);
    for (i, f) in flux.iter().enumerate() {
        let q = TAILLE_ENTETE_PARTIE + TAILLE_DESC_FLUX * i;
        b[q] = f.sorte as u8;
        b[q + 1] = f.matrice;
        b[q + 2] = f.contexte;
        eu32(&mut b, q + 4, decalages[i] as u32);
        eu32(&mut b, q + 8, f.octets.len() as u32);
        eu32(&mut b, q + 12, f.produits);
        b[decalages[i]..decalages[i] + f.octets.len()].copy_from_slice(f.octets);
    }
    (b, utiles as u32)
}

// ---------------------------------------------------------------------------------------------
// La section MÉTA (§ 4.4)

/// Les octets de la section MÉTA : u64 n, les paires brutes du GGUF dans leur ordre, les paires
/// ajoutées, puis l'empreinte64 de tout ce qui précède.
pub fn serialiser_meta(paires_brutes: &[u8], n_paires: u64, ajouts: &[Vec<u8>]) -> Vec<u8> {
    let mut b = Vec::with_capacity(8 + paires_brutes.len() + 256);
    b.extend_from_slice(&(n_paires + ajouts.len() as u64).to_le_bytes());
    b.extend_from_slice(paires_brutes);
    for a in ajouts {
        b.extend_from_slice(a);
    }
    let h = empreinte64(&b);
    b.extend_from_slice(&h.to_le_bytes());
    b
}

// ---------------------------------------------------------------------------------------------
// Le fichier ouvert

pub struct Fichier {
    chemin: PathBuf,
    entete: Entete,
    meta: Vec<u8>,
    paires: Vec<PaireMeta>,
    residents: Vec<TenseurResident>,
    debut_donnees: u64,
    tables: Vec<Table>,
    index_tables: Vec<(usize, usize)>,
    repertoire: Vec<EntreeRepertoire>,
    /// Octets lus par `ouvrir` (lectures tamponnées : en-tête, MÉTA, table des résidents, TABLES,
    /// RÉPERTOIRE) ; extension, pour le compte du critère C8 (constat M3 de l'épreuve J1).
    octets_lus_ouverture: u64,
}

fn lire_a(f: &mut std::fs::File, lus: &mut u64, decalage: u64, n: u64) -> Result<Vec<u8>, ErreurFormat> {
    f.seek(SeekFrom::Start(decalage))?;
    let mut v = vec![0u8; n as usize];
    f.read_exact(&mut v)?;
    *lus += n;
    Ok(v)
}

impl Fichier {
    /// Ouvre et vérifie : en-tête, taille du fichier, MÉTA, table des résidents, TABLES,
    /// RÉPERTOIRE (empreintes, champs réservés, bornes). Ne lit ni les données des résidents ni
    /// les tronçons.
    pub fn ouvrir(chemin: &Path) -> Result<Fichier, ErreurFormat> {
        let mut f = std::fs::File::open(chemin)?;
        let mut lus = 0u64;
        let taille_reelle = f.metadata()?.len();
        let tete = lire_a(&mut f, &mut lus, 0, TAILLE_ENTETE as u64)?;
        let entete = Entete::depuis_octets(&tete)?;
        if entete.taille_fichier != taille_reelle {
            return Err(champ("taille du fichier", entete.taille_fichier, taille_reelle));
        }
        for (i, s) in entete.sections.iter().take(5).enumerate() {
            if s.fin() > taille_reelle {
                return Err(limites(format!("section {i} au-delà de la fin du fichier")));
            }
        }
        // Les sections ne se chevauchent pas.
        let mut ordre: Vec<Section> = entete.sections[..5].to_vec();
        ordre.sort_by_key(|s| s.decalage);
        for w in ordre.windows(2) {
            if w[0].fin() > w[1].decalage {
                return Err(limites("sections qui se chevauchent"));
            }
        }

        // MÉTA
        let sm = entete.sections[SECTION_META];
        let mb = lire_a(&mut f, &mut lus, sm.decalage, sm.longueur)?;
        if mb.len() < 16 {
            return Err(limites("section MÉTA"));
        }
        let n_paires = lu64(&mb, 0);
        let paires = lire_paires(&mb[8..mb.len() - 8], n_paires)?;
        let fin_paires = 8 + paires.last().map(|p| p.fin).unwrap_or(0);
        if fin_paires != mb.len() - 8 {
            return Err(limites("octets en trop dans la section MÉTA"));
        }
        if empreinte64(&mb[..fin_paires]) != lu64(&mb, fin_paires) {
            return Err(ErreurFormat::Empreinte("section MÉTA".into()));
        }
        let meta = mb[..fin_paires].to_vec();

        // RÉSIDENTS : la table, et l'empreinte rangée aux 8 derniers octets de la section.
        let sr = entete.sections[SECTION_RESIDENTS];
        if sr.longueur < 16 {
            return Err(limites("section RÉSIDENTS"));
        }
        let tete_r = lire_a(&mut f, &mut lus, sr.decalage, 8)?;
        let n_res = lu32(&tete_r, 0) as usize;
        let lg_table = 8 + TAILLE_ENTREE_RESIDENT * n_res;
        let debut_zone = debut_zone_residents(n_res);
        if debut_zone + 8 > sr.longueur {
            return Err(limites("table des résidents plus longue que sa section"));
        }
        let table_r = lire_a(&mut f, &mut lus, sr.decalage, lg_table as u64)?;
        let e_table = lu64(&lire_a(&mut f, &mut lus, sr.fin() - 8, 8)?, 0);
        if empreinte64(&table_r) != e_table {
            return Err(ErreurFormat::Empreinte("table des résidents".into()));
        }
        let bourrage = lire_a(&mut f, &mut lus, sr.decalage + lg_table as u64, debut_zone - lg_table as u64)?;
        if !tout_nul(&bourrage) {
            return Err(ErreurFormat::Reserve("bourrage de la table des résidents".into()));
        }
        let residents = lire_table_residents(&table_r)?;
        let fin_zone = residents.iter().map(|r| r.decalage + r.octets).max().unwrap_or(0);
        if debut_zone + fin_zone + 8 != sr.longueur {
            return Err(champ("longueur de RÉSIDENTS", debut_zone + fin_zone + 8, sr.longueur));
        }
        let debut_donnees = sr.decalage + debut_zone;

        // TABLES
        let st = entete.sections[SECTION_TABLES];
        let tables_brutes = lire_a(&mut f, &mut lus, st.decalage, st.longueur)?;
        let mut tables = lire_tables(&tables_brutes, &entete)?;
        tables.sort_by_key(|t| (t.couche, t.matrice, t.sorte, t.contexte));
        let nm = entete.matrices as usize;
        let mut index_tables = vec![(0usize, 0usize); entete.couches as usize * nm];
        let mut i = 0;
        while i < tables.len() {
            let cle = (tables[i].couche, tables[i].matrice);
            let mut j = i;
            while j < tables.len() && (tables[j].couche, tables[j].matrice) == cle {
                j += 1;
            }
            index_tables[cle.0 as usize * nm + cle.1 as usize] = (i, j);
            i = j;
        }
        for w in tables.windows(2) {
            if (w[0].couche, w[0].matrice, w[0].sorte, w[0].contexte) == (w[1].couche, w[1].matrice, w[1].sorte, w[1].contexte) {
                return Err(champ("tables", "une seule par (couche, matrice, sorte, contexte)", format!("({}, {}, {:?}, {})", w[0].couche, w[0].matrice, w[0].sorte, w[0].contexte)));
            }
        }
        // Fichier canonique : une table de codes qui laisserait une fente à un octet portant un
        // demi-octet 8 permettrait à un flux de le produire. Refusée ici, pour le processeur et
        // pour la carte, qui montent les mêmes tables.
        if entete.est_canonique() {
            verifier_tables_canoniques(&tables)?;
        }

        // RÉPERTOIRE
        let sd = entete.sections[SECTION_REPERTOIRE];
        let n_ent = entete.couches as usize * entete.experts as usize;
        if sd.longueur != (n_ent * TAILLE_ENTREE_REPERTOIRE + 8) as u64 {
            return Err(champ("longueur du RÉPERTOIRE", n_ent * TAILLE_ENTREE_REPERTOIRE + 8, sd.longueur));
        }
        let rb = lire_a(&mut f, &mut lus, sd.decalage, sd.longueur)?;
        let n_corps = n_ent * TAILLE_ENTREE_REPERTOIRE;
        if empreinte64(&rb[..n_corps]) != lu64(&rb, n_corps) {
            return Err(ErreurFormat::Empreinte("section RÉPERTOIRE".into()));
        }
        let stc = entete.sections[SECTION_TRONCONS];
        let mut repertoire = Vec::with_capacity(n_ent);
        for i in 0..n_ent {
            let e = EntreeRepertoire::depuis_octets(&rb[i * TAILLE_ENTREE_REPERTOIRE..(i + 1) * TAILLE_ENTREE_REPERTOIRE])?;
            let (c, x) = ((i / entete.experts as usize) as u16, (i % entete.experts as usize) as u16);
            if (e.couche, e.expert) != (c, x) {
                return Err(champ(&format!("entrée {i} du répertoire"), format!("({c}, {x})"), format!("({}, {})", e.couche, e.expert)));
            }
            let total = e.longueur_jusqua(2);
            let ok = e.decalage % ALIGNEMENT == 0
                && e.longueur.iter().all(|&l| l as u64 % ALIGNEMENT == 0)
                && e.utiles[0] <= e.longueur[0]
                && e.utiles[1] <= e.longueur[1]
                && e.longueur[0] > 0
                && e.decalage >= stc.decalage
                && e.decalage + total <= stc.fin()
                && (entete.niveaux >= 2 || (e.longueur[1] == 0 && e.utiles[1] == 0 && e.empreinte_niveau[1] == 0))
                && (entete.est_canonique() || e.empreinte_canonique == 0);
            if !ok {
                return Err(limites(format!("entrée ({c}, {x}) du répertoire : {e:?}")));
            }
            repertoire.push(e);
        }

        Ok(Fichier { chemin: chemin.to_path_buf(), entete, meta, paires, residents, debut_donnees, tables, index_tables, repertoire, octets_lus_ouverture: lus })
    }

    pub fn chemin(&self) -> &Path {
        &self.chemin
    }
    pub fn entete(&self) -> &Entete {
        &self.entete
    }
    /// Les paires GGUF brutes de la section MÉTA (u64 n, puis les paires), sans l'empreinte.
    pub fn meta(&self) -> &[u8] {
        &self.meta
    }
    /// Les paires de la section MÉTA, lues (extension de la couture).
    pub fn paires(&self) -> &[PaireMeta] {
        &self.paires
    }
    /// La paire de clé `cle`, si elle existe (extension de la couture).
    pub fn paire(&self, cle: &str) -> Option<&PaireMeta> {
        self.paires.iter().find(|p| p.cle == cle)
    }
    pub fn residents(&self) -> &[TenseurResident] {
        &self.residents
    }
    /// Décalage absolu du début de la zone de données des résidents.
    pub fn debut_donnees_residentes(&self) -> u64 {
        self.debut_donnees
    }
    /// Les tables d'une (couche, matrice), triées par (sorte, contexte).
    pub fn tables(&self, couche: u16, matrice: u8) -> &[Table] {
        let (a, b) = self.index_tables[couche as usize * self.entete.matrices as usize + matrice as usize];
        &self.tables[a..b]
    }
    /// La table d'une (couche, matrice, sorte, contexte), si elle existe (extension).
    pub fn table(&self, couche: u16, matrice: u8, sorte: Sorte, contexte: u8) -> Option<&Table> {
        self.tables(couche, matrice).iter().find(|t| t.sorte == sorte && t.contexte == contexte)
    }
    /// Toutes les tables (extension).
    pub fn toutes_tables(&self) -> &[Table] {
        &self.tables
    }
    pub fn entree(&self, couche: u16, expert: u16) -> &EntreeRepertoire {
        &self.repertoire[couche as usize * self.entete.experts as usize + expert as usize]
    }
    /// Tout le répertoire, dans l'ordre (couche, expert) (extension).
    pub fn repertoire(&self) -> &[EntreeRepertoire] {
        &self.repertoire
    }
    /// Octets lus à l'ouverture, par lectures tamponnées (extension, critère C8).
    pub fn octets_lus_a_l_ouverture(&self) -> u64 {
        self.octets_lus_ouverture
    }
}

// ---------------------------------------------------------------------------------------------
// L'écrivain

/// Écrit un fichier `.trc` section par section : il tient la position, aligne, réserve des
/// zones à remplir plus tard (TABLES et RÉPERTOIRE ne sont connus qu'après les tronçons) et
/// écrit l'en-tête en dernier.
pub struct Ecrivain {
    f: BufWriter<std::fs::File>,
    position: u64,
    sections: [Section; 8],
    section_ouverte: Option<(usize, u64)>,
}

impl Ecrivain {
    /// Crée le fichier et réserve l'en-tête (4 096 zéros).
    pub fn creer(chemin: &Path) -> Result<Ecrivain, ErreurFormat> {
        let f = std::fs::File::create(chemin)?;
        let mut e = Ecrivain { f: BufWriter::with_capacity(8 << 20, f), position: 0, sections: [Section::default(); 8], section_ouverte: None };
        e.ecrire(&[0u8; TAILLE_ENTETE])?;
        Ok(e)
    }

    pub fn position(&self) -> u64 {
        self.position
    }

    pub fn ecrire(&mut self, octets: &[u8]) -> Result<(), ErreurFormat> {
        self.f.write_all(octets)?;
        self.position += octets.len() as u64;
        Ok(())
    }

    /// Complète de zéros jusqu'au prochain multiple de `a`.
    pub fn aligner_sur(&mut self, a: u64) -> Result<(), ErreurFormat> {
        let cible = aligner(self.position, a);
        let zeros = vec![0u8; (cible - self.position) as usize];
        self.ecrire(&zeros)
    }

    /// Aligne sur 4 096 et ouvre la section `i` ; rend son décalage.
    pub fn ouvrir_section(&mut self, i: usize) -> Result<u64, ErreurFormat> {
        assert!(self.section_ouverte.is_none(), "une section est déjà ouverte");
        self.aligner_sur(ALIGNEMENT)?;
        self.section_ouverte = Some((i, self.position));
        Ok(self.position)
    }

    /// Ferme la section ouverte : sa longueur est ce qui a été écrit depuis son ouverture.
    pub fn fermer_section(&mut self) {
        let (i, d) = self.section_ouverte.take().expect("aucune section ouverte");
        self.sections[i] = Section { decalage: d, longueur: self.position - d };
    }

    /// Déclare une section de position et longueur connues (zone réservée puis remplie).
    pub fn declarer_section(&mut self, i: usize, s: Section) {
        self.sections[i] = s;
    }

    /// Écrit `n` zéros ; rend le décalage de la zone (à remplir par [`Ecrivain::reecrire`]).
    pub fn reserver(&mut self, n: u64) -> Result<u64, ErreurFormat> {
        let d = self.position;
        let bloc = vec![0u8; (n.min(8 << 20)) as usize];
        let mut reste = n;
        while reste > 0 {
            let k = reste.min(bloc.len() as u64) as usize;
            self.ecrire(&bloc[..k])?;
            reste -= k as u64;
        }
        Ok(d)
    }

    /// Réécrit des octets à un décalage déjà écrit, puis revient à la fin.
    pub fn reecrire(&mut self, decalage: u64, octets: &[u8]) -> Result<(), ErreurFormat> {
        assert!(decalage + octets.len() as u64 <= self.position, "réécriture au-delà de la fin");
        self.f.flush()?;
        let f = self.f.get_mut();
        f.seek(SeekFrom::Start(decalage))?;
        f.write_all(octets)?;
        f.seek(SeekFrom::Start(self.position))?;
        Ok(())
    }

    /// Écrit l'en-tête (sections, taille du fichier, empreinte), ferme le fichier ; rend sa
    /// taille. Le fichier se termine à la position courante, qui doit être alignée sur 4 096.
    pub fn terminer(mut self, mut entete: Entete) -> Result<u64, ErreurFormat> {
        assert!(self.section_ouverte.is_none(), "section restée ouverte");
        self.aligner_sur(ALIGNEMENT)?;
        entete.sections = self.sections;
        entete.taille_fichier = self.position;
        entete.verifier_coherence()?;
        let b = entete.vers_octets();
        self.reecrire(0, &b)?;
        self.f.flush()?;
        let f = self.f.into_inner().map_err(|e| e.into_error())?;
        f.sync_all()?;
        Ok(self.position)
    }
}
