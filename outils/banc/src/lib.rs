//! Pièces communes du banc : motif de données vérifiable, statistiques, arguments.
//!
//! Le motif : le fichier de test se découpe en pages de 4 Kio. Le premier mot de 64 bits
//! de la page `p` vaut `p ^ MAGIE`, la suite est un flux xorshift64* graine `p`. Une lecture
//! peut donc vérifier, sans rien garder en mémoire, qu'elle a reçu la bonne page et non
//! une page voisine, une page de zéros ou une page restée dans un tampon d'un tour précédent.

pub const PAGE: usize = 4096;
pub const MOTS_PAR_PAGE: usize = PAGE / 8;
pub const MAGIE: u64 = 0x7472_6f6e_636f_6e73; // « troncons » en ASCII

#[inline]
pub fn xorshift64star(etat: &mut u64) -> u64 {
    let mut x = *etat;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    *etat = x;
    x.wrapping_mul(0x2545_F491_4F6C_DD1D)
}

/// Remplit une page (512 mots) du motif de la page d'indice `p`.
pub fn remplir_page(mots: &mut [u64], p: u64) {
    debug_assert_eq!(mots.len(), MOTS_PAR_PAGE);
    mots[0] = p ^ MAGIE;
    let mut etat = p.wrapping_mul(0x9E37_79B9_7F4A_7C15) | 1;
    for m in mots[1..].iter_mut() {
        *m = xorshift64star(&mut etat);
    }
}

/// Vérification rapide : l'en-tête de chaque page du tampon. Rend le nombre de pages fausses.
pub fn verifier_entetes(tampon: &[u8], premiere_page: u64) -> u64 {
    let mut fausses = 0;
    for (i, page) in tampon.chunks_exact(PAGE).enumerate() {
        let mot = u64::from_le_bytes(page[0..8].try_into().unwrap());
        if mot != (premiere_page + i as u64) ^ MAGIE {
            fausses += 1;
        }
    }
    fausses
}

/// Vérification complète d'une page : les 512 mots.
pub fn verifier_page_complete(page: &[u8], p: u64) -> bool {
    let mut attendu = [0u64; MOTS_PAR_PAGE];
    remplir_page(&mut attendu, p);
    page.chunks_exact(8)
        .zip(attendu.iter())
        .all(|(o, a)| u64::from_le_bytes(o.try_into().unwrap()) == *a)
}

/// Quantile par rang le plus proche sur un vecteur trié.
pub fn quantile(trie: &[f64], q: f64) -> f64 {
    if trie.is_empty() {
        return f64::NAN;
    }
    let r = ((q * trie.len() as f64).ceil() as usize).clamp(1, trie.len());
    trie[r - 1]
}

pub fn moyenne(v: &[f64]) -> f64 {
    v.iter().sum::<f64>() / v.len().max(1) as f64
}

/// Arguments de la forme `--cle valeur` ou `--drapeau`.
pub struct Args {
    paires: Vec<(String, Option<String>)>,
    pub positionnels: Vec<String>,
}

impl Args {
    pub fn lire() -> Self {
        let brut: Vec<String> = std::env::args().skip(1).collect();
        let mut paires = Vec::new();
        let mut positionnels = Vec::new();
        let mut i = 0;
        while i < brut.len() {
            if let Some(cle) = brut[i].strip_prefix("--") {
                if i + 1 < brut.len() && !brut[i + 1].starts_with("--") {
                    paires.push((cle.to_string(), Some(brut[i + 1].clone())));
                    i += 2;
                } else {
                    paires.push((cle.to_string(), None));
                    i += 1;
                }
            } else {
                positionnels.push(brut[i].clone());
                i += 1;
            }
        }
        Args { paires, positionnels }
    }
    pub fn texte(&self, cle: &str, defaut: &str) -> String {
        self.paires
            .iter()
            .find(|(k, _)| k == cle)
            .and_then(|(_, v)| v.clone())
            .unwrap_or_else(|| defaut.to_string())
    }
    pub fn nombre(&self, cle: &str, defaut: f64) -> f64 {
        self.paires
            .iter()
            .find(|(k, _)| k == cle)
            .and_then(|(_, v)| v.as_ref())
            .map(|v| analyser_taille(v))
            .unwrap_or(defaut)
    }
    pub fn drapeau(&self, cle: &str) -> bool {
        self.paires.iter().any(|(k, _)| k == cle)
    }
}

/// « 4K », « 16M », « 32G », « 1.5 » : suffixes binaires (Kio, Mio, Gio).
pub fn analyser_taille(s: &str) -> f64 {
    let s = s.trim();
    let (n, mult) = match s.chars().last() {
        Some('K') | Some('k') => (&s[..s.len() - 1], 1024.0),
        Some('M') | Some('m') => (&s[..s.len() - 1], 1024.0 * 1024.0),
        Some('G') | Some('g') => (&s[..s.len() - 1], 1024.0 * 1024.0 * 1024.0),
        _ => (s, 1.0),
    };
    n.parse::<f64>().expect("nombre illisible") * mult
}

/// Chaîne UTF-16 terminée par un zéro pour l'API Windows.
pub fn large(s: &str) -> Vec<u16> {
    s.encode_utf16().chain(std::iter::once(0)).collect()
}
