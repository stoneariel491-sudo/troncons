//! Les noyaux CUDA du moteur troncons (lot K) et leurs enveloppes.
//!
//! Les sources sont sous `noyaux/` : `commun.cuh` (partie de tronçon, flux rANS, disposition
//! SoA), `decodeur.cuh` (étape K1), `gemv.cuh` (étape K2), `passe.cuh` (étape K3 : les autres
//! noyaux de la passe avant), réunies dans `noyaux.cu`. `build.rs`
//! les compile par `nvcc` en une image (cubin sm_89 + PTX), embarquée ici ([`IMAGE`]) et chargée
//! par l'API du pilote ([`trc_cuda::Module`]) : aucune DLL d'exécution de CUDA n'est livrée.
//!
//! Le banc `banc/banc_k.cu` inclut les mêmes sources, mot pour mot, avec les mêmes options de
//! compilation : les noyaux qu'il mesure sont ceux que lance cette crate.
//!
//! Interface binaire (couture N, ARCHITECTURE.md § 5.6) : voir [`abi`] pour les structures que
//! partagent l'hôte et la carte, et [`Noyaux`] pour les lancements.

pub mod abi;

use std::ffi::{CStr, c_void};

pub use abi::{DescDecodage, DescGemv, DimsExpert, ParamsAttention, ParamsRope};
use trc_cuda::{Contexte, Erreur, Flux, Fonction, Module, Result, VueCarte};

/// L'image des noyaux (fatbin : cubin sm_89 et PTX compute_89), produite par `build.rs`.
pub static IMAGE: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/noyaux.fatbin"));

/// Les noyaux chargés dans un contexte.
pub struct Noyaux {
    _module: Module,
    decoder_echelles: Fonction,
    decoder_codes: Fonction,
    decoder_echelles_lot: Fonction,
    decoder_codes_lot: Fonction,
    copier_brut: Fonction,
    gemv: Fonction,
    gemv_lot: Fonction,
    /// Lot B (génome synonyme) : le produit du mode rapide, lu par les centres de la base.
    gemv_base: Fonction,
    /// Mode rapide : `Some(c)` (centres en grandeurs doublées, table CENTRES du fichier rapide)
    /// fait servir chaque [`Noyaux::gemv`] par `gemv_base` ; `None` (défaut) : le mode exact,
    /// inchangé. Posé une fois à l'ouverture d'un fichier au drapeau RAPIDE, jamais deviné.
    pub centres_rapides: Option<[f32; 4]>,
    // K3
    gemv_q8_0: Fonction,
    gemv_f32: Fonction,
    rmsnorm: Fonction,
    rope_yarn: Fonction,
    ecrire_kv: Fonction,
    attention: Fonction,
    // essai de la ronde de corrections J1 (constat M5) : cache KV en f32
    ecrire_kv_f32: Fonction,
    attention_kvf32: Fonction,
    routeur_topk: Fonction,
    /// P3 (option `--biais-cache`) : le top-k biaisé par le cache ; `routeur_topk` n'est pas modifié.
    routeur_topk_biais: Fonction,
    swiglu_oai: Fonction,
    combiner: Fonction,
    ligne_q8_0: Fonction,
    argmax: Fonction,
}

/// Adresse d'une vue facultative (0 : absente ; le noyau lit un pointeur nul).
fn adresse(v: Option<VueCarte>) -> u64 {
    v.map_or(0, |v| v.adresse)
}

/// Pointeur vers un argument de noyau (les arguments sont passés par l'adresse de leur valeur).
fn arg<T>(v: &mut T) -> *mut c_void {
    v as *mut T as *mut c_void
}

fn verifier(cond: bool, message: impl FnOnce() -> String) -> Result<()> {
    if cond { Ok(()) } else { Err(Erreur::Usage(message())) }
}

impl Noyaux {
    /// Charge l'image embarquée et résout chaque noyau par son nom (`extern "C"`).
    pub fn charger(c: &Contexte) -> Result<Self> {
        let module = Module::charger(c, IMAGE)?;
        let f = |nom: &CStr| module.fonction(nom);
        Ok(Noyaux {
            decoder_echelles: f(c"decoder_echelles")?,
            decoder_codes: f(c"decoder_codes")?,
            decoder_echelles_lot: f(c"decoder_echelles_lot")?,
            decoder_codes_lot: f(c"decoder_codes_lot")?,
            copier_brut: f(c"copier_brut")?,
            gemv: f(c"gemv_mxfp4")?,
            gemv_lot: f(c"gemv_mxfp4_lot")?,
            gemv_base: f(c"gemv_base")?,
            centres_rapides: None,
            gemv_q8_0: f(c"gemv_q8_0")?,
            gemv_f32: f(c"gemv_f32")?,
            rmsnorm: f(c"rmsnorm")?,
            rope_yarn: f(c"rope_yarn")?,
            ecrire_kv: f(c"ecrire_kv")?,
            attention: f(c"attention")?,
            ecrire_kv_f32: f(c"ecrire_kv_f32")?,
            attention_kvf32: f(c"attention_kvf32")?,
            routeur_topk: f(c"routeur_topk")?,
            routeur_topk_biais: f(c"routeur_topk_biais")?,
            swiglu_oai: f(c"swiglu_oai")?,
            combiner: f(c"combiner")?,
            ligne_q8_0: f(c"ligne_q8_0")?,
            argmax: f(c"argmax")?,
            _module: module,
        })
    }

    /// Étape K1 : décode une partie de niveau 0 (v1.0 : MEDIANES, BIAIS, DELTA, CODES_CTX pour les
    /// trois matrices, § 4.8) dans un emplacement (disposition SoA, § 5.6). Deux lancements sur
    /// `f` : `decoder_echelles` puis `decoder_codes` ; l'emplacement est prêt quand `f` a passé
    /// le second.
    ///
    /// - `partie` : la partie telle qu'elle est arrivée par DMA (en-tête de partie compris) ;
    /// - `luts` : les LUT de la couche, `u32[3][4][4096]` ([`abi::LUTS_PAR_COUCHE`] mots, voir
    ///   [`abi::luts_couche`]) ;
    /// - `controle` : `u32[4]` remis à zéro par l'appelant ; après le décodage, `[0]` voies hors
    ///   de L, `[1]` erreurs de format, `[2]` pointeurs de tuile faux (voir `commun.cuh`). Tout
    ///   compteur non nul est une erreur fatale nommée par l'appelant (§ 4.12).
    pub fn decoder_expert(
        &self,
        partie: VueCarte,
        emplacement: VueCarte,
        luts: VueCarte,
        dims: &DimsExpert,
        controle: VueCarte,
        f: &Flux,
    ) -> Result<()> {
        dims.verifier().map_err(Erreur::Usage)?;
        verifier(partie.octets >= 64, || format!("partie de {} o (en-tête de 64 o au moins)", partie.octets))?;
        verifier(emplacement.octets as u64 >= dims.taille_emplacement(), || {
            format!("emplacement de {} o, {} o demandés", emplacement.octets, dims.taille_emplacement())
        })?;
        verifier(emplacement.adresse % 256 == 0, || "emplacement non aligné sur 256".into())?;
        verifier(luts.octets >= abi::LUTS_PAR_COUCHE * 4, || format!("LUT de {} o", luts.octets))?;
        verifier(controle.octets >= 16, || "contrôle de moins de 16 o".into())?;
        self.decoder_expert_grilles(partie, emplacement, luts, dims, controle, abi::grilles_decodeur(dims), f)
    }

    /// [`Noyaux::decoder_expert`] avec des grilles données (extension), par exemple
    /// [`abi::grilles_depuis_partie`] pour un fichier dont les tuiles ne font pas 256 macro-pas.
    /// Toute grille est juste ; seule la vitesse en dépend.
    #[allow(clippy::too_many_arguments)]
    pub fn decoder_expert_grilles(
        &self,
        partie: VueCarte,
        emplacement: VueCarte,
        luts: VueCarte,
        dims: &DimsExpert,
        controle: VueCarte,
        grilles: ([u32; 3], [u32; 3]),
        f: &Flux,
    ) -> Result<()> {
        dims.verifier().map_err(Erreur::Usage)?;
        verifier(partie.octets >= 64, || format!("partie de {} o (en-tête de 64 o au moins)", partie.octets))?;
        verifier(emplacement.octets as u64 >= dims.taille_emplacement(), || {
            format!("emplacement de {} o, {} o demandés", emplacement.octets, dims.taille_emplacement())
        })?;
        verifier(emplacement.adresse % 256 == 0, || "emplacement non aligné sur 256".into())?;
        verifier(luts.octets >= abi::LUTS_PAR_COUCHE * 4, || format!("LUT de {} o", luts.octets))?;
        verifier(controle.octets >= 16, || "contrôle de moins de 16 o".into())?;
        let (g1, g2) = grilles;
        verifier(g1[1] == 3 && g2[1] == 3 && g1[0] > 0 && g2[0] > 0, || format!("grilles {g1:?} {g2:?}"))?;
        let mut p = partie.adresse;
        let mut e = emplacement.adresse;
        let mut l = luts.adresse;
        let mut d = *dims;
        let mut c = controle.adresse;
        let mut args: [*mut c_void; 5] = [
            &mut p as *mut u64 as *mut c_void,
            &mut e as *mut u64 as *mut c_void,
            &mut l as *mut u64 as *mut c_void,
            &mut d as *mut DimsExpert as *mut c_void,
            &mut c as *mut u64 as *mut c_void,
        ];
        // SAFETY : signatures de decoder_echelles et decoder_codes (decodeur.cuh) : trois
        // pointeurs, DimsExpert par valeur (#[repr(C)], 24 o), un pointeur ; tailles vérifiées.
        unsafe {
            self.decoder_echelles.lancer(g1, [abi::FILS_ECHELLES, 1, 1], 0, f, &mut args)?;
            self.decoder_codes.lancer(g2, [abi::FILS_CODES, 1, 1], 0, f, &mut args)?;
        }
        Ok(())
    }

    /// Étape K1, lot (extension de la couture N) : décode `n` experts de mêmes dimensions en deux
    /// lancements (`decoder_echelles_lot` puis `decoder_codes_lot`, grilles `(X, 3, n)`). `descs`
    /// est `DescDecodage[n]` en VRAM ([`DescDecodage::octets`]) ; chaque expert porte sa partie,
    /// son emplacement, les LUT de sa couche et son tampon de contrôle. Rend, expert par expert,
    /// les mêmes octets que [`Noyaux::decoder_expert`] (mêmes corps de carte, `corps_echelles` et
    /// `corps_codes`). Les adresses des descripteurs ne sont pas vérifiables ici : l'appelant en
    /// répond (tailles et alignements comme pour `decoder_expert`).
    pub fn decoder_lot(&self, descs: VueCarte, n: u32, dims: &DimsExpert, f: &Flux) -> Result<()> {
        dims.verifier().map_err(Erreur::Usage)?;
        verifier(n > 0 && n <= 65_535, || format!("lot de {n} experts"))?;
        verifier(descs.octets >= n as usize * std::mem::size_of::<DescDecodage>(), || "descripteurs trop courts".into())?;
        let (g1, g2) = abi::grilles_decodeur(dims);
        let mut d = descs.adresse;
        let mut dm = *dims;
        let mut args: [*mut c_void; 2] =
            [&mut d as *mut u64 as *mut c_void, &mut dm as *mut DimsExpert as *mut c_void];
        // SAFETY : signatures de decoder_echelles_lot et decoder_codes_lot (decodeur.cuh) : un
        // pointeur vers DescDecodage[n], DimsExpert par valeur (#[repr(C)], 24 o).
        unsafe {
            self.decoder_echelles_lot.lancer([g1[0], 3, n], [abi::FILS_ECHELLES, 1, 1], 0, f, &mut args)?;
            self.decoder_codes_lot.lancer([g2[0], 3, n], [abi::FILS_CODES, 1, 1], 0, f, &mut args)?;
        }
        Ok(())
    }

    /// Chemin brut (fichier brut, drapeau bit 2 ; témoin C3) : ECHELLES_BRUTES, CODES_BRUTS et
    /// BIAIS recopiés dans l'emplacement. `controle[1]` compte les erreurs de format.
    pub fn copier_brut(
        &self,
        partie: VueCarte,
        emplacement: VueCarte,
        dims: &DimsExpert,
        controle: VueCarte,
        f: &Flux,
    ) -> Result<()> {
        dims.verifier().map_err(Erreur::Usage)?;
        verifier(partie.octets >= 64, || "partie trop courte".into())?;
        verifier(emplacement.octets as u64 >= dims.taille_emplacement(), || "emplacement trop court".into())?;
        verifier(controle.octets >= 16, || "contrôle de moins de 16 o".into())?;
        let g = abi::grille_brut(dims);
        let mut p = partie.adresse;
        let mut e = emplacement.adresse;
        let mut d = *dims;
        let mut c = controle.adresse;
        let mut args: [*mut c_void; 4] = [
            &mut p as *mut u64 as *mut c_void,
            &mut e as *mut u64 as *mut c_void,
            &mut d as *mut DimsExpert as *mut c_void,
            &mut c as *mut u64 as *mut c_void,
        ];
        // SAFETY : signature de copier_brut (decodeur.cuh) ; tailles vérifiées.
        unsafe { self.copier_brut.lancer(g, [abi::FILS_BRUT, 1, 1], 0, f, &mut args) }
    }

    /// Étape K2 : y = W x + b pour une matrice de l'emplacement (`matrice` commence à ses codes,
    /// voir [`abi::disposition`]). `x` : f32[colonnes] ; `y` : f32[lignes].
    pub fn gemv(&self, matrice: VueCarte, x: VueCarte, y: VueCarte, lignes: u32, colonnes: u32, f: &Flux) -> Result<()> {
        verifier(lignes > 0 && colonnes > 0 && colonnes % 32 == 0, || format!("forme {lignes} × {colonnes}"))?;
        let pas = abi::disposition_matrice(lignes, colonnes).pas;
        verifier(matrice.octets as u64 >= pas, || format!("matrice de {} o, {pas} o demandés", matrice.octets))?;
        verifier(matrice.adresse % 256 == 0, || "matrice non alignée sur 256".into())?;
        verifier(x.octets >= 4 * colonnes as usize && x.adresse % 16 == 0, || "x trop court ou non aligné sur 16".into())?;
        verifier(y.octets >= 4 * lignes as usize, || "y trop court".into())?;
        let mut m = matrice.adresse;
        let mut xa = x.adresse;
        let mut ya = y.adresse;
        let mut r = lignes;
        let mut cc = colonnes;
        let mut args: [*mut c_void; 5] = [
            &mut m as *mut u64 as *mut c_void,
            &mut xa as *mut u64 as *mut c_void,
            &mut ya as *mut u64 as *mut c_void,
            &mut r as *mut u32 as *mut c_void,
            &mut cc as *mut u32 as *mut c_void,
        ];
        let grille = [lignes.div_ceil(abi::GEMV_LIGNES_PAR_BLOC), 1, 1];
        if let Some(c) = self.centres_rapides {
            let [mut c0, mut c1, mut c2, mut c3] = c;
            let mut args: [*mut c_void; 9] =
                [args[0], args[1], args[2], args[3], args[4], arg(&mut c0), arg(&mut c1), arg(&mut c2), arg(&mut c3)];
            // SAFETY : signature de gemv_base (gemv.cuh) : celle de gemv_mxfp4 et quatre f32.
            return unsafe { self.gemv_base.lancer(grille, [abi::GEMV_FILS, 1, 1], 0, f, &mut args) };
        }
        // SAFETY : signature de gemv_mxfp4 (gemv.cuh) ; tailles et alignements vérifiés.
        unsafe { self.gemv.lancer([lignes.div_ceil(abi::GEMV_LIGNES_PAR_BLOC), 1, 1], [abi::GEMV_FILS, 1, 1], 0, f, &mut args) }
    }

    /// Étape K2, lot : `n` produits indépendants décrits par `descs` (`DescGemv[n]` en VRAM, voir
    /// [`DescGemv`]) en un lancement ; `lignes_max` borne les lignes des matrices du lot. Rend les
    /// mêmes bits que [`Noyaux::gemv`] matrice par matrice (même fonction de carte). Les adresses
    /// des descripteurs ne sont pas vérifiables ici : l'appelant en répond.
    pub fn gemv_lot(&self, descs: VueCarte, n: u32, lignes_max: u32, f: &Flux) -> Result<()> {
        verifier(n > 0 && n <= 65_535, || format!("lot de {n} produits"))?;
        verifier(descs.octets >= n as usize * std::mem::size_of::<DescGemv>(), || "descripteurs trop courts".into())?;
        let mut d = descs.adresse;
        let mut args: [*mut c_void; 1] = [&mut d as *mut u64 as *mut c_void];
        // SAFETY : signature de gemv_mxfp4_lot (gemv.cuh) : un pointeur vers DescGemv[n].
        unsafe {
            self.gemv_lot.lancer([lignes_max.div_ceil(abi::GEMV_LIGNES_PAR_BLOC), n, 1], [abi::GEMV_FILS, 1, 1], 0, f, &mut args)
        }
    }

    // ============================================================== étape K3 : la passe avant

    /// y = W x (+ b), W en Q8_0 (disposition ggml : `lignes` rangées contiguës de `colonnes`/32
    /// blocs de 34 o, adresse paire). `x` : f32[colonnes] aligné sur 16 ; `y` : f32[lignes] ;
    /// `biais` : f32[lignes] ou rien. Projections q, k, v, sortie de l'attention, sortie du modèle.
    #[allow(clippy::too_many_arguments)]
    pub fn gemv_q8_0(&self, w: VueCarte, x: VueCarte, biais: Option<VueCarte>, y: VueCarte, lignes: u32, colonnes: u32, f: &Flux) -> Result<()> {
        verifier(lignes > 0 && colonnes > 0 && colonnes % 32 == 0, || format!("forme {lignes} × {colonnes}"))?;
        let octets = lignes as u64 * (colonnes / 32) as u64 * 34;
        verifier(w.octets as u64 >= octets && w.adresse % 2 == 0, || format!("matrice Q8_0 de {} o, {octets} o demandés (adresse paire)", w.octets))?;
        verifier(x.octets >= 4 * colonnes as usize && x.adresse % 16 == 0, || "x trop court ou non aligné sur 16".into())?;
        verifier(y.octets >= 4 * lignes as usize, || "y trop court".into())?;
        verifier(biais.is_none_or(|b| b.octets >= 4 * lignes as usize), || "biais trop court".into())?;
        let (mut a, mut b, mut c, mut d, mut r, mut cc) = (w.adresse, x.adresse, adresse(biais), y.adresse, lignes, colonnes);
        let mut args = [arg(&mut a), arg(&mut b), arg(&mut c), arg(&mut d), arg(&mut r), arg(&mut cc)];
        // SAFETY : signature de gemv_q8_0 (passe.cuh) ; tailles et alignements vérifiés.
        unsafe { self.gemv_q8_0.lancer([lignes.div_ceil(abi::GEMV_LIGNES_PAR_BLOC), 1, 1], [abi::GEMV_FILS, 1, 1], 0, f, &mut args) }
    }

    /// y = W x (+ b), W en f32 (`lignes` × `colonnes`, rangées contiguës, alignée sur 16) : le
    /// routeur (`ffn_gate_inp`, E × 2 880, biais `ffn_gate_inp.bias`).
    #[allow(clippy::too_many_arguments)]
    pub fn gemv_f32(&self, w: VueCarte, x: VueCarte, biais: Option<VueCarte>, y: VueCarte, lignes: u32, colonnes: u32, f: &Flux) -> Result<()> {
        verifier(lignes > 0 && colonnes > 0 && colonnes % 4 == 0, || format!("forme {lignes} × {colonnes}"))?;
        verifier(w.octets as u64 >= 4 * lignes as u64 * colonnes as u64 && w.adresse % 16 == 0, || "matrice f32 trop courte ou non alignée sur 16".into())?;
        verifier(x.octets >= 4 * colonnes as usize && x.adresse % 16 == 0, || "x trop court ou non aligné sur 16".into())?;
        verifier(y.octets >= 4 * lignes as usize, || "y trop court".into())?;
        verifier(biais.is_none_or(|b| b.octets >= 4 * lignes as usize), || "biais trop court".into())?;
        let (mut a, mut b, mut c, mut d, mut r, mut cc) = (w.adresse, x.adresse, adresse(biais), y.adresse, lignes, colonnes);
        let mut args = [arg(&mut a), arg(&mut b), arg(&mut c), arg(&mut d), arg(&mut r), arg(&mut cc)];
        // SAFETY : signature de gemv_f32 (passe.cuh) ; tailles et alignements vérifiés.
        unsafe { self.gemv_f32.lancer([lignes.div_ceil(abi::GEMV_LIGNES_PAR_BLOC), 1, 1], [abi::GEMV_FILS, 1, 1], 0, f, &mut args) }
    }

    /// RMSNorm de `lignes` vecteurs de `n` éléments : y = x · w / √(moyenne(x²) + ε). En place
    /// permis (`y` = `x`).
    #[allow(clippy::too_many_arguments)]
    pub fn rmsnorm(&self, x: VueCarte, w: VueCarte, y: VueCarte, n: u32, lignes: u32, eps: f32, f: &Flux) -> Result<()> {
        verifier(n > 0 && lignes > 0, || format!("rmsnorm de {lignes} × {n}"))?;
        let o = 4 * n as usize * lignes as usize;
        verifier(x.octets >= o && y.octets >= o && w.octets >= 4 * n as usize, || "rmsnorm : vues trop courtes".into())?;
        let (mut a, mut b, mut c, mut nn, mut e) = (x.adresse, w.adresse, y.adresse, n, eps);
        let mut args = [arg(&mut a), arg(&mut b), arg(&mut c), arg(&mut nn), arg(&mut e)];
        // SAFETY : signature de rmsnorm (passe.cuh) ; tailles vérifiées.
        unsafe { self.rmsnorm.lancer([lignes, 1, 1], [abi::FILS_PASSE, 1, 1], 0, f, &mut args) }
    }

    /// Rotation YaRN de q (`tetes_q` têtes) et k (`tetes_k` têtes), en place, à `position`.
    #[allow(clippy::too_many_arguments)]
    pub fn rope_yarn(&self, q: VueCarte, k: VueCarte, tetes_q: u32, tetes_k: u32, position: u32, p: &ParamsRope, f: &Flux) -> Result<()> {
        verifier(p.dim_tete > 0 && p.dim_tete % 2 == 0 && p.dim_tete <= 128, || format!("dimension de tête {}", p.dim_tete))?;
        verifier(p.variante <= 1, || format!("variante de YaRN {}", p.variante))?;
        let d = p.dim_tete as usize;
        verifier(q.octets >= 4 * d * tetes_q as usize && k.octets >= 4 * d * tetes_k as usize, || "rope : vues trop courtes".into())?;
        let (mut a, mut b, mut tq, mut tk, mut pos, mut pp) = (q.adresse, k.adresse, tetes_q, tetes_k, position, *p);
        let mut args = [arg(&mut a), arg(&mut b), arg(&mut tq), arg(&mut tk), arg(&mut pos), arg(&mut pp)];
        // SAFETY : signature de rope_yarn (passe.cuh) ; ParamsRope #[repr(C)], 48 o.
        unsafe { self.rope_yarn.lancer([tetes_q + tetes_k, 1, 1], [p.dim_tete / 2, 1, 1], 0, f, &mut args) }
    }

    /// Écrit k et v (f32[`dkv`]) dans la case `case_kv` des caches f16 d'une couche
    /// (`[case][tête_kv][d]`, voir [`ParamsAttention::case`]).
    #[allow(clippy::too_many_arguments)]
    pub fn ecrire_kv(&self, k: VueCarte, v: VueCarte, cache_k: VueCarte, cache_v: VueCarte, dkv: u32, case_kv: u32, f: &Flux) -> Result<()> {
        verifier(dkv > 0, || "dkv nul".into())?;
        let fin = 2 * (case_kv as usize + 1) * dkv as usize;
        verifier(k.octets >= 4 * dkv as usize && v.octets >= 4 * dkv as usize, || "k ou v trop court".into())?;
        verifier(cache_k.octets >= fin && cache_v.octets >= fin, || format!("case {case_kv} hors du cache"))?;
        let (mut a, mut b, mut c, mut d, mut n, mut e) = (k.adresse, v.adresse, cache_k.adresse, cache_v.adresse, dkv, case_kv);
        let mut args = [arg(&mut a), arg(&mut b), arg(&mut c), arg(&mut d), arg(&mut n), arg(&mut e)];
        // SAFETY : signature de ecrire_kv (passe.cuh) ; tailles vérifiées.
        unsafe { self.ecrire_kv.lancer([dkv.div_ceil(abi::FILS_PASSE), 1, 1], [abi::FILS_PASSE, 1, 1], 0, f, &mut args) }
    }

    /// Attention de décodage d'une position (toutes ses têtes) sur les cases du cache décrites
    /// par `p` ; `puits` : f32[tetes] (`attn_sinks`) ; `sortie` : f32[tetes · 64].
    #[allow(clippy::too_many_arguments)]
    pub fn attention(&self, q: VueCarte, cache_k: VueCarte, cache_v: VueCarte, puits: VueCarte, sortie: VueCarte, p: &ParamsAttention, f: &Flux) -> Result<()> {
        verifier(p.dim_tete == 64 && p.tetes_kv > 0 && p.tetes % p.tetes_kv == 0, || format!("têtes {} / {} de dimension {}", p.tetes, p.tetes_kv, p.dim_tete))?;
        verifier(p.fin >= p.debut && p.fin - p.debut <= abi::ATTENTION_POSITIONS_MAX, || format!("positions [{}, {})", p.debut, p.fin))?;
        verifier(p.anneau == 0 || p.fin - p.debut <= p.anneau, || "plus de positions que de cases dans l'anneau".into())?;
        let cases = if p.anneau > 0 { p.anneau } else { p.fin } as usize;
        let dkv = (p.tetes_kv * 64) as usize;
        verifier(cache_k.octets >= 2 * cases * dkv && cache_v.octets >= 2 * cases * dkv, || "cache trop court".into())?;
        verifier(cache_k.adresse % 16 == 0, || "cache des clés non aligné sur 16".into())?;
        verifier(
            q.octets >= 4 * 64 * p.tetes as usize && sortie.octets >= 4 * 64 * p.tetes as usize && puits.octets >= 4 * p.tetes as usize,
            || "attention : vues trop courtes".into(),
        )?;
        let (mut a, mut b, mut c, mut d, mut e, mut pp) = (q.adresse, cache_k.adresse, cache_v.adresse, puits.adresse, sortie.adresse, *p);
        let mut args = [arg(&mut a), arg(&mut b), arg(&mut c), arg(&mut d), arg(&mut e), arg(&mut pp)];
        // SAFETY : signature de attention (passe.cuh) ; ParamsAttention #[repr(C)], 32 o ; mémoire
        // partagée dynamique : 4 o par position, sous la limite par défaut (ATTENTION_POSITIONS_MAX).
        unsafe { self.attention.lancer([p.tetes, 1, 1], [abi::FILS_ATTENTION, 1, 1], 4 * (p.fin - p.debut), f, &mut args) }
    }

    /// Essai (constat M5 de l'épreuve J1, hors couture N) : comme [`Noyaux::ecrire_kv`], caches f32.
    #[allow(clippy::too_many_arguments)]
    pub fn ecrire_kv_f32(&self, k: VueCarte, v: VueCarte, cache_k: VueCarte, cache_v: VueCarte, dkv: u32, case_kv: u32, f: &Flux) -> Result<()> {
        verifier(dkv > 0, || "dkv nul".into())?;
        let fin = 4 * (case_kv as usize + 1) * dkv as usize;
        verifier(k.octets >= 4 * dkv as usize && v.octets >= 4 * dkv as usize, || "k ou v trop court".into())?;
        verifier(cache_k.octets >= fin && cache_v.octets >= fin, || format!("case {case_kv} hors du cache f32"))?;
        let (mut a, mut b, mut c, mut d, mut n, mut e) = (k.adresse, v.adresse, cache_k.adresse, cache_v.adresse, dkv, case_kv);
        let mut args = [arg(&mut a), arg(&mut b), arg(&mut c), arg(&mut d), arg(&mut n), arg(&mut e)];
        // SAFETY : signature de ecrire_kv_f32 (passe.cuh) ; tailles vérifiées.
        unsafe { self.ecrire_kv_f32.lancer([dkv.div_ceil(abi::FILS_PASSE), 1, 1], [abi::FILS_PASSE, 1, 1], 0, f, &mut args) }
    }

    /// Essai (constat M5, hors couture N) : comme [`Noyaux::attention`], caches f32.
    #[allow(clippy::too_many_arguments)]
    pub fn attention_kvf32(&self, q: VueCarte, cache_k: VueCarte, cache_v: VueCarte, puits: VueCarte, sortie: VueCarte, p: &ParamsAttention, f: &Flux) -> Result<()> {
        verifier(p.dim_tete == 64 && p.tetes_kv > 0 && p.tetes % p.tetes_kv == 0, || format!("têtes {} / {} de dimension {}", p.tetes, p.tetes_kv, p.dim_tete))?;
        verifier(p.fin >= p.debut && p.fin - p.debut <= abi::ATTENTION_POSITIONS_MAX, || format!("positions [{}, {})", p.debut, p.fin))?;
        verifier(p.anneau == 0 || p.fin - p.debut <= p.anneau, || "plus de positions que de cases dans l'anneau".into())?;
        let cases = if p.anneau > 0 { p.anneau } else { p.fin } as usize;
        let dkv = (p.tetes_kv * 64) as usize;
        verifier(cache_k.octets >= 4 * cases * dkv && cache_v.octets >= 4 * cases * dkv, || "cache f32 trop court".into())?;
        verifier(
            q.octets >= 4 * 64 * p.tetes as usize && sortie.octets >= 4 * 64 * p.tetes as usize && puits.octets >= 4 * p.tetes as usize,
            || "attention : vues trop courtes".into(),
        )?;
        let (mut a, mut b, mut c, mut d, mut e, mut pp) = (q.adresse, cache_k.adresse, cache_v.adresse, puits.adresse, sortie.adresse, *p);
        let mut args = [arg(&mut a), arg(&mut b), arg(&mut c), arg(&mut d), arg(&mut e), arg(&mut pp)];
        // SAFETY : signature de attention_kvf32 (passe.cuh) ; mêmes règles que `attention`.
        unsafe { self.attention_kvf32.lancer([p.tetes, 1, 1], [abi::FILS_ATTENTION, 1, 1], 4 * (p.fin - p.debut), f, &mut args) }
    }

    /// Top-k du routeur sur `experts` logits (biais compris) : `indices` u32[k], `poids` f32[k] ;
    /// `boite` : adresse de carte d'une case de boîte aux lettres projetée, ou 0 ; la case reçoit
    /// les k indices aux mots 1 .. k, les k poids aux mots k + 1 .. 2k, puis `sequence` au mot 0,
    /// écrit en dernier après une barrière système (protocole de l'essai E0 c du lot E).
    #[allow(clippy::too_many_arguments)]
    pub fn routeur_topk(&self, logits: VueCarte, experts: u32, k: u32, indices: VueCarte, poids: VueCarte, boite: u64, sequence: u32, f: &Flux) -> Result<()> {
        verifier(experts > 0 && experts <= abi::ROUTEUR_EXPERTS_MAX && k > 0 && k <= abi::ROUTEUR_K_MAX && k <= experts, || format!("top-{k} sur {experts}"))?;
        verifier(
            logits.octets >= 4 * experts as usize && indices.octets >= 4 * k as usize && poids.octets >= 4 * k as usize,
            || "routeur : vues trop courtes".into(),
        )?;
        let (mut a, mut e, mut kk, mut i, mut p, mut b, mut s) = (logits.adresse, experts, k, indices.adresse, poids.adresse, boite, sequence);
        let mut args = [arg(&mut a), arg(&mut e), arg(&mut kk), arg(&mut i), arg(&mut p), arg(&mut b), arg(&mut s)];
        // SAFETY : signature de routeur_topk (passe.cuh) ; tailles vérifiées ; la boîte, si elle est
        // donnée, est une mémoire projetée de 4 (2k + 1) octets au moins (contrat de l'appelant).
        unsafe { self.routeur_topk.lancer([1, 1, 1], [32, 1, 1], 0, f, &mut args) }
    }

    /// Top-k du routeur **biaisé** (P3, règle de Skliar et al.) : les k experts sont choisis sur
    /// `logits[e] + biais[e]` (`biais` : f32[experts], β pour un expert présent en VRAM, 0 sinon), rendus
    /// dans l'ordre décroissant du logit non biaisé, et leurs poids sont le softmax des logits non
    /// biaisés. Mêmes sorties et même boîte aux lettres que [`Noyaux::routeur_topk`] ; avec un biais nul,
    /// mêmes indices et mêmes poids, au bit.
    #[allow(clippy::too_many_arguments)]
    pub fn routeur_topk_biais(&self, logits: VueCarte, biais: VueCarte, experts: u32, k: u32, indices: VueCarte, poids: VueCarte, boite: u64, sequence: u32, f: &Flux) -> Result<()> {
        verifier(experts > 0 && experts <= abi::ROUTEUR_EXPERTS_MAX && k > 0 && k <= abi::ROUTEUR_K_MAX && k <= experts, || format!("top-{k} sur {experts}"))?;
        verifier(
            logits.octets >= 4 * experts as usize && biais.octets >= 4 * experts as usize && indices.octets >= 4 * k as usize && poids.octets >= 4 * k as usize,
            || "routeur biaisé : vues trop courtes".into(),
        )?;
        let (mut a, mut bb, mut e, mut kk, mut i, mut p, mut b, mut s) = (logits.adresse, biais.adresse, experts, k, indices.adresse, poids.adresse, boite, sequence);
        let mut args = [arg(&mut a), arg(&mut bb), arg(&mut e), arg(&mut kk), arg(&mut i), arg(&mut p), arg(&mut b), arg(&mut s)];
        // SAFETY : signature de routeur_topk_biais (passe.cuh) ; tailles vérifiées ; la boîte, si elle est
        // donnée, est une mémoire projetée de 4 (2k + 1) octets au moins (contrat de l'appelant).
        unsafe { self.routeur_topk_biais.lancer([1, 1, 1], [32, 1, 1], 0, f, &mut args) }
    }

    /// SwiGLU bornée de gpt-oss sur `n` paires (g, u) : y = min(g, 7) σ(1,702 min(g, 7)) (borne(u) + 1).
    pub fn swiglu_oai(&self, g: VueCarte, u: VueCarte, y: VueCarte, n: u32, f: &Flux) -> Result<()> {
        let o = 4 * n as usize;
        verifier(n > 0 && g.octets >= o && u.octets >= o && y.octets >= o, || "swiglu : vues trop courtes".into())?;
        let (mut a, mut b, mut c, mut nn) = (g.adresse, u.adresse, y.adresse, n);
        let mut args = [arg(&mut a), arg(&mut b), arg(&mut c), arg(&mut nn)];
        // SAFETY : signature de swiglu_oai (passe.cuh) ; tailles vérifiées.
        unsafe { self.swiglu_oai.lancer([n.div_ceil(abi::FILS_PASSE), 1, 1], [abi::FILS_PASSE, 1, 1], 0, f, &mut args) }
    }

    /// résidu[i] += Σ_j w_j s_j[i], j = 0 .. n − 1 dans l'ordre (sans fma) ; s_j commence à
    /// `sorties` + j · `pas` flottants ; `poids` : f32[n], ou rien (poids 1).
    #[allow(clippy::too_many_arguments)]
    pub fn combiner(&self, residu: VueCarte, sorties: VueCarte, pas: u32, poids: Option<VueCarte>, n: u32, d: u32, f: &Flux) -> Result<()> {
        verifier(n > 0 && d > 0 && (n == 1 || pas >= d), || format!("combiner {n} sorties de {d} (pas {pas})"))?;
        verifier(
            residu.octets >= 4 * d as usize && sorties.octets >= 4 * ((n as usize - 1) * pas as usize + d as usize),
            || "combiner : vues trop courtes".into(),
        )?;
        verifier(poids.is_none_or(|p| p.octets >= 4 * n as usize), || "poids trop courts".into())?;
        let (mut a, mut b, mut c, mut p, mut nn, mut dd) = (residu.adresse, sorties.adresse, pas, adresse(poids), n, d);
        let mut args = [arg(&mut a), arg(&mut b), arg(&mut c), arg(&mut p), arg(&mut nn), arg(&mut dd)];
        // SAFETY : signature de combiner (passe.cuh) ; tailles vérifiées.
        unsafe { self.combiner.lancer([d.div_ceil(abi::FILS_PASSE), 1, 1], [abi::FILS_PASSE, 1, 1], 0, f, &mut args) }
    }

    /// Ligne `ligne` d'une matrice Q8_0 de `colonnes` colonnes vers f32 (exact) ; `w` peut ne
    /// porter que cette ligne (alors `ligne` = 0).
    pub fn ligne_q8_0(&self, w: VueCarte, ligne: u32, colonnes: u32, y: VueCarte, f: &Flux) -> Result<()> {
        verifier(colonnes > 0 && colonnes % 32 == 0, || format!("{colonnes} colonnes"))?;
        let ol = (colonnes / 32) as u64 * 34;
        verifier(w.octets as u64 >= (ligne as u64 + 1) * ol && y.octets >= 4 * colonnes as usize, || "ligne_q8_0 : vues trop courtes".into())?;
        let (mut a, mut l, mut c, mut b) = (w.adresse, ligne, colonnes, y.adresse);
        let mut args = [arg(&mut a), arg(&mut l), arg(&mut c), arg(&mut b)];
        // SAFETY : signature de ligne_q8_0 (passe.cuh) ; tailles vérifiées.
        unsafe { self.ligne_q8_0.lancer([colonnes.div_ceil(abi::FILS_PASSE), 1, 1], [abi::FILS_PASSE, 1, 1], 0, f, &mut args) }
    }

    /// Indice du plus grand des `n` flottants de `v` (égalité : plus petit indice) dans `sortie`
    /// (u32).
    pub fn argmax(&self, v: VueCarte, n: u32, sortie: VueCarte, f: &Flux) -> Result<()> {
        verifier(n > 0 && v.octets >= 4 * n as usize && sortie.octets >= 4, || "argmax : vues trop courtes".into())?;
        let (mut a, mut nn, mut s) = (v.adresse, n, sortie.adresse);
        let mut args = [arg(&mut a), arg(&mut nn), arg(&mut s)];
        // SAFETY : signature de argmax (passe.cuh) ; tailles vérifiées.
        unsafe { self.argmax.lancer([1, 1, 1], [abi::FILS_ARGMAX, 1, 1], 0, f, &mut args) }
    }
}
