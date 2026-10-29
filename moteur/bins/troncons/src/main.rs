//! troncons : le programme (ARCHITECTURE.md § 5.10).
//!
//! ```text
//! troncons generer --modele m.trc --vocab m.vocab.gguf (--invite fichier.txt | --harmonie « question »)
//!                  [-n 256] [--ram-tiede 0] [--temoin] [--brut] [--emplacements N] [--contexte 4096]
//!                  [--longueur-lecture X] [--enchassement-en-ram] [--dll llama.dll]
//!                  [--journal j.json] [--sortie texte.txt] [--trace t.trace] [--chronogramme c.csv]
//!                  [--repos 10] [--sans-vram] [--arret-fin] [--prechargement] [--flux] [--rapide]
//!                  [--biais-cache β]
//!     --biais-cache β : P3, routeur biaisé par le cache (règle de Skliar et al., arXiv 2412.00099) : β
//!     (unités brutes de logit) est ajouté au logit de chaque expert déjà en VRAM pour choisir les k
//!     experts ; les poids restent calculés sur les logits non biaisés. Absent par défaut (le moteur
//!     lance alors les mêmes noyaux qu'avant l'option) ; refusé avec --flux et --prechargement.
//!     --rapide : le modèle est un compagnon du mode rapide (`<nom>.rapide.trc`, lot B, génome
//!     synonyme) ; exigé pour l'ouvrir, refusé pour un fichier exact.
//!     --flux : préremplissage par flux (J1+ : couche par couche, chaque expert lu une fois pour
//!     toutes les positions de l'invite) au lieu de la boucle de pas.
//!     Préremplissage par une boucle de pas (J1), puis n jetons gloutons. Écrit le texte et un journal
//!     JSON (commande, date, alimentation, compteurs, jetons/s, mémoire et VRAM de pointe, octets lus
//!     sur le disque, empreinte du texte).
//! troncons evaluer --modele m.trc --base base.kld [--fenetres 10] --sortie m.kld [--empreintes e.csv]
//!                  [--positions P] [--journal j.json] [--trace t.trace] [mêmes options du moteur]
//!     Les fenêtres du fichier de base (mêmes jetons, 512 par fenêtre, chacune depuis la position 0) ;
//!     les logits des positions notées passent par la quantification à 16 bits de llama-perplexity
//!     (critère C4) ; l'empreinte64 des logits f32 de chaque pas va dans le CSV (critère C3).
//!     --flux : chaque fenêtre par le préremplissage par flux (mêmes logits attendus au bit).
//! troncons mesurer …   (= generer, avec un repos de 10 s avant la passe pour chiffrer le disque)
//! troncons disque --modele m.trc [--n 1000] [--graine 1] [--profondeur 4] [--longueur-lecture X]
//!                 [--journal j.json]
//!     L'étage disque seul, mesuré dans la même séance que le moteur (passe B des séries de C5) :
//!     n tronçons tirés sans remise (graine publiée), lus sans tampon à la longueur du moteur
//!     (`longueur0`, ou `--longueur-lecture`), `profondeur` lectures en vol, dans une fenêtre
//!     épinglée de `profondeur` tampons ; débit = octets / horloge de l'hôte.
//! ```

use std::collections::HashMap;
use std::fmt::Write as _;
use std::io::Write as _;
use std::mem::ManuallyDrop;
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::time::{Instant, SystemTime, UNIX_EPOCH};

use anyhow::{Context, Result, bail};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use trc_juge::compteurs::{EntreesSorties, Echantillonneur, Processus, poignees_standard_non_heritables, repos_disque};
use trc_juge::kld::{EcrivainKld, FichierKld, positions_notees};
use trc_ordo::{CompteursMoteur, Config, Moteur};

const DLL: &str = "~/dev/modeles/llama.cpp-b11515/llama.dll";

// ============================================================================ arguments

struct Args {
    mots: HashMap<String, String>,
    drapeaux: Vec<String>,
    brut: Vec<String>,
}

impl Args {
    fn lire(brut: &[String]) -> Args {
        let mut mots = HashMap::new();
        let mut drapeaux = Vec::new();
        let mut i = 0;
        while i < brut.len() {
            let a = &brut[i];
            let cle = a.strip_prefix("--").or_else(|| a.strip_prefix('-'));
            if let Some(cle) = cle {
                if i + 1 < brut.len() && !brut[i + 1].starts_with("--") {
                    mots.insert(cle.to_string(), brut[i + 1].clone());
                    i += 2;
                    continue;
                }
                drapeaux.push(cle.to_string());
            }
            i += 1;
        }
        Args { mots, drapeaux, brut: brut.to_vec() }
    }
    fn mot(&self, c: &str) -> Option<&str> {
        self.mots.get(c).map(|s| s.as_str())
    }
    fn exige(&self, c: &str) -> Result<&str> {
        self.mot(c).with_context(|| format!("--{c} manque"))
    }
    fn a(&self, c: &str) -> bool {
        self.drapeaux.iter().any(|d| d == c)
    }
    fn nombre<T: std::str::FromStr>(&self, c: &str, defaut: T) -> Result<T> {
        match self.mot(c) {
            None => Ok(defaut),
            Some(s) => s.parse().map_err(|_| anyhow::anyhow!("--{c} : nombre illisible « {s} »")),
        }
    }
}

fn config(a: &Args) -> Result<Config> {
    let mut c = Config::nouvelle(a.exige("modele")?);
    c.ram_tiede_go = a.nombre("ram-tiede", 0.0)?;
    c.enchassement_en_ram = a.a("enchassement-en-ram");
    c.profondeur_es = a.nombre("profondeur", 4usize)?;
    c.couches_d_avance = a.nombre("couches-d-avance", 3usize)?;
    c.contexte = a.nombre("contexte", 4096u32)?;
    c.temoin = a.a("temoin");
    c.brut = a.a("brut");
    c.emplacements = a.mot("emplacements").map(|s| s.parse()).transpose().context("--emplacements")?;
    c.vram_plafond_mio = a.nombre("vram-plafond", c.vram_plafond_mio)?;
    c.longueur_lecture = a.mot("longueur-lecture").map(|s| s.parse()).transpose().context("--longueur-lecture")?;
    c.chronogramme = a.mot("chronogramme").is_some();
    c.prechargement = a.a("prechargement");
    c.battement = !a.a("sans-battement");
    c.garde = !a.a("sans-garde");
    c.kv_f32 = a.a("kv-f32");
    c.rapide = a.a("rapide");
    // P3 : routeur biaisé par le cache, β en unités brutes de logit ; absent par défaut (moteur inchangé).
    c.biais_cache = a.mot("biais-cache").map(|s| s.replace(',', ".").parse::<f32>()).transpose().map_err(|_| anyhow::anyhow!("--biais-cache : nombre illisible"))?;
    if a.a("biais-cache") {
        bail!("--biais-cache : valeur manquante (β en unités de logit, par exemple 0.041)");
    }
    if c.biais_cache.is_some() && a.a("flux") {
        bail!("--biais-cache et --flux ne se combinent pas (voir Config::biais_cache)");
    }
    if let Some(x) = a.mot("casser-garde") {
        let (sorte, n) = x.split_once(':').context("--casser-garde troncon:N | ligne:N")?;
        if sorte != "troncon" && sorte != "ligne" {
            bail!("--casser-garde : sorte « {sorte} » inconnue (troncon, ligne)");
        }
        c.casser = Some((sorte.to_string(), n.parse().context("--casser-garde : N")?));
    }
    Ok(c)
}

// ============================================================================ journal

/// La date locale n'est pas connue sans dépendance : on écrit l'heure UTC (secondes depuis 1970 et
/// date civile, algorithme de Hinnant).
fn date_utc() -> String {
    let s = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0) as i64;
    let (jours, reste) = (s.div_euclid(86_400), s.rem_euclid(86_400));
    let z = jours + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = yoe + era * 400 + if m <= 2 { 1 } else { 0 };
    format!("{y:04}-{m:02}-{d:02}T{:02}:{:02}:{:02}Z", reste / 3600, (reste / 60) % 60, reste % 60)
}

/// L'alimentation (GetSystemPowerStatus) : secteur (1), batterie (0), inconnu (255).
fn alimentation() -> Value {
    use windows_sys::Win32::System::Power::{GetSystemPowerStatus, SYSTEM_POWER_STATUS};
    let mut s: SYSTEM_POWER_STATUS = unsafe { std::mem::zeroed() };
    // SAFETY : structure de sortie, taille fixe.
    if unsafe { GetSystemPowerStatus(&mut s) } == 0 {
        return json!({"connu": false});
    }
    json!({"secteur": s.ACLineStatus == 1, "ACLineStatus": s.ACLineStatus, "BatteryFlag": s.BatteryFlag, "BatteryLifePercent": s.BatteryLifePercent})
}

fn compteurs_json(c: &CompteursMoteur) -> Value {
    json!({
        "pas": c.pas,
        "h_vram": c.h(),
        "succes_vram": c.cache.succes_vram, "succes_ram": c.cache.succes_ram, "defauts_disque": c.cache.defauts_disque,
        "acces": c.cache.acces(), "evictions": c.cache.evictions,
        "octets_disque_cache": c.cache.octets_disque, "octets_copies_cache": c.cache.octets_copies,
        "octets_lus": c.octets_lus, "octets_lus_troncons": c.octets_lus_troncons, "lectures_troncons": c.lectures_troncons,
        "octets_lus_enchassement": c.octets_lus_enchassement, "lectures_enchassement": c.lectures_enchassement,
        "octets_dma": c.octets_dma, "experts_decodes": c.experts_decodes, "experts_verifies": c.experts_verifies,
        "s_pas": c.s_pas, "s_attente_routeur": c.s_attente_routeur, "s_lectures": c.s_lectures, "s_fin_jeton": c.s_fin_jeton,
        "ms_copie_carte": c.ms_copie, "ms_decodage_carte": c.ms_decodage,
        "emplacements": c.emplacements, "tiedes": c.tiedes,
        "pf_emis": c.pf_emis, "pf_utiles": c.pf_utiles, "pf_octets": c.pf_octets,
        "flux_conflits_evites": c.flux_conflits_evites,
        "garde_octets": c.garde_octets, "garde_troncons": c.garde_troncons, "garde_lignes": c.garde_lignes,
        "garde_attente_s": c.garde_attente_s, "garde_octets_ouverture": c.garde_octets_ouverture,
    })
}

/// La différence de deux relevés de compteurs (une phase).
fn moins(a: &CompteursMoteur, b: &CompteursMoteur) -> CompteursMoteur {
    let mut c = *a;
    c.pas -= b.pas;
    c.cache.succes_vram -= b.cache.succes_vram;
    c.cache.succes_ram -= b.cache.succes_ram;
    c.cache.defauts_disque -= b.cache.defauts_disque;
    c.cache.octets_disque -= b.cache.octets_disque;
    c.cache.octets_copies -= b.cache.octets_copies;
    c.cache.evictions -= b.cache.evictions;
    c.octets_lus -= b.octets_lus;
    c.octets_lus_troncons -= b.octets_lus_troncons;
    c.octets_lus_enchassement -= b.octets_lus_enchassement;
    c.lectures_troncons -= b.lectures_troncons;
    c.lectures_enchassement -= b.lectures_enchassement;
    c.octets_dma -= b.octets_dma;
    c.experts_decodes -= b.experts_decodes;
    c.experts_verifies -= b.experts_verifies;
    c.s_pas -= b.s_pas;
    c.s_attente_routeur -= b.s_attente_routeur;
    c.s_lectures -= b.s_lectures;
    c.s_fin_jeton -= b.s_fin_jeton;
    c.ms_copie -= b.ms_copie;
    c.ms_decodage -= b.ms_decodage;
    c.pf_emis -= b.pf_emis;
    c.pf_utiles -= b.pf_utiles;
    c.pf_octets -= b.pf_octets;
    c.flux_conflits_evites -= b.flux_conflits_evites;
    c.garde_octets -= b.garde_octets;
    c.garde_troncons -= b.garde_troncons;
    c.garde_lignes -= b.garde_lignes;
    c.garde_attente_s -= b.garde_attente_s;
    c
}

fn hex(o: &[u8]) -> String {
    o.iter().fold(String::new(), |mut s, b| {
        let _ = write!(s, "{b:02x}");
        s
    })
}

fn sha256_hex(o: &[u8]) -> String {
    hex(&Sha256::digest(o))
}

fn empreinte64_f32(z: &[f32]) -> u64 {
    let mut h = Sha256::new();
    for x in z {
        h.update(x.to_le_bytes());
    }
    u64::from_le_bytes(h.finalize()[..8].try_into().unwrap())
}

fn moteur_json(m: &Moteur, c: &Config, ouverture_s: f64) -> Value {
    let h = m.hyper();
    let b = &m.modele().bilan;
    json!({
        "fichier": c.fichier.display().to_string().replace('\\', "/"),
        "brut": c.brut, "rapide": c.rapide, "temoin": c.temoin, "ram_tiede_go": c.ram_tiede_go, "enchassement_en_ram": c.enchassement_en_ram,
        "profondeur_es": c.profondeur_es, "couches_d_avance": c.couches_d_avance, "contexte": c.contexte,
        "longueur_lecture": c.longueur_lecture, "vram_plafond_mio": c.vram_plafond_mio, "prechargement": c.prechargement, "biais_cache": c.biais_cache,
        "garde": c.garde, "casser_garde": c.casser.as_ref().map(|(s, n)| format!("{s}:{n}")), "kv_f32": c.kv_f32,
        "couches": h.couches, "experts": h.experts, "k": h.actifs, "vocab": h.vocab,
        "emplacements": m.compteurs().emplacements, "tiedes": m.tiedes(), "arrivees": m.arrivees(),
        "octets_emplacement": h.taille_emplacement(), "longueur_arrivee": m.longueur_arrivee(),
        "octets_vram_moteur": m.octets_vram(), "octets_epingles": m.octets_epingles(),
        "chargement": {"tenseurs": b.tenseurs, "octets_tenseurs": b.octets_tenseurs, "octets_lus": b.octets_lus,
                       "lectures": b.lectures, "empreintes_verifiees": b.empreintes_verifiees, "secondes": b.secondes},
        "ouverture_s": ouverture_s,
        "etapes_memoire": m.etapes_memoire.iter().map(|(n, o)| json!({"etape": n, "ensemble_travail": o})).collect::<Vec<_>>(),
        "carte": m.contexte().nom(),
    })
}

/// Les compteurs d'E/S du processus entre deux relevés (constat M3 : l'instrument de C8 qui voit le
/// moteur et lui seul ; publié à côté du compteur PDH, non jugé : décision de l'arbitre).
fn es_json(a: &EntreesSorties, b: &EntreesSorties) -> Value {
    json!({"lectures": b.lectures - a.lectures, "octets_lus": b.octets_lus - a.octets_lus,
           "octets_lus_depuis_le_depart": b.octets_lus, "octets_ecrits": b.octets_ecrits - a.octets_ecrits})
}

/// Les octets que le moteur dit avoir lus sur le disque, dans la fenêtre de `es_json` : lectures par
/// `trc-es` (chargement des résidents, tronçons, lignes, table de la garde : le lecteur compte tout)
/// et lectures tamponnées de l'ouverture du fichier (MÉTA, tables, répertoire). Le chargement des
/// résidents est publié à part, « dont » : il est déjà dans le compte du lecteur (la première
/// version l'ajoutait deux fois, défaut vu sur la séance vitesse-2026-10-16 : +1,69 Go).
fn octets_comptes(m: &Moteur) -> Value {
    let b = &m.modele().bilan;
    let c = m.compteurs();
    let ouv = m.fichier().octets_lus_a_l_ouverture();
    json!({"dont_chargement_residents": b.octets_lus, "lecteur": c.octets_lus, "ouverture_tamponnee": ouv,
           "total": c.octets_lus + ouv})
}

fn ecrire(chemin: &Path, v: &Value) -> Result<()> {
    std::fs::write(chemin, serde_json::to_string_pretty(v)? + "\n").with_context(|| format!("écriture de {}", chemin.display()))
}

// ============================================================================ l'invite

/// Les identifiants des jetons spéciaux du format harmony, retrouvés par leur texte dans le
/// vocabulaire (trc-jetons découpe sans lire les spéciaux : `parse_special = false`).
fn speciaux(j: &trc_jetons::Jetons) -> HashMap<String, u32> {
    let n = j.taille_vocab() as u32;
    let mut m = HashMap::new();
    for id in n.saturating_sub(2000)..n {
        let t = j.texte(id);
        if t.starts_with("<|") && t.ends_with("|>") {
            m.insert(t, id);
        }
    }
    m
}

/// Une conversation au format harmony de gpt-oss (publié par OpenAI, `openai/harmony`) : message
/// système, message de l'utilisateur, puis le début du tour de l'assistant.
fn invite_harmonie(j: &trc_jetons::Jetons, question: &str, systeme: &str) -> Result<(Vec<u32>, Option<u32>)> {
    let s = speciaux(j);
    let id = |n: &str| s.get(n).copied().with_context(|| format!("jeton spécial {n} absent du vocabulaire"));
    let (debut, message, fin) = (id("<|start|>")?, id("<|message|>")?, id("<|end|>")?);
    let mut v = Vec::new();
    for (role, texte) in [("system", systeme), ("user", question)] {
        v.push(debut);
        v.extend(j.decouper(role, false));
        v.push(message);
        v.extend(j.decouper(texte, false));
        v.push(fin);
    }
    v.push(debut);
    v.extend(j.decouper("assistant", false));
    Ok((v, s.get("<|return|>").copied()))
}

// ============================================================================ generer

fn generer(a: &Args, repos_defaut: f64) -> Result<()> {
    let c = config(a)?;
    let n: usize = a.nombre("n", 256usize)?;
    let repos: f64 = a.nombre("repos", repos_defaut)?;
    let dll = PathBuf::from(a.mot("dll").unwrap_or(DLL));
    let vocab = PathBuf::from(a.exige("vocab")?);
    let jetons = trc_jetons::Jetons::ouvrir(&dll, &vocab).with_context(|| format!("découpeur : {} avec {}", dll.display(), vocab.display()))?;
    let (invite, arret, source_invite): (Vec<u32>, Option<u32>, Value) = if let Some(q) = a.mot("harmonie") {
        let systeme = a.mot("systeme").unwrap_or("You are ChatGPT, a large language model trained by OpenAI.\nKnowledge cutoff: 2024-06\nCurrent date: 2026-10-15\n\nReasoning: low\n\n# Valid channels: analysis, commentary, final. Channel must be included for every message.");
        let (v, r) = invite_harmonie(&jetons, q, systeme)?;
        (v, r, json!({"harmonie": q, "systeme": systeme}))
    } else {
        let f = PathBuf::from(a.exige("invite")?);
        let octets = std::fs::read(&f).with_context(|| format!("lecture de {}", f.display()))?;
        let texte = String::from_utf8(octets.clone()).context("invite : UTF-8 attendu")?;
        (jetons.decouper(&texte, true), None, json!({"fichier": f.display().to_string().replace('\\', "/"), "sha256": sha256_hex(&octets), "octets": octets.len()}))
    };
    if invite.is_empty() {
        bail!("invite vide");
    }
    let arret_fin = a.a("arret-fin");
    let avec_vram = !a.a("sans-vram");
    let repos_go_s = if repos > 0.0 { Some(repos_disque(repos)?) } else { None };

    let echant = Echantillonneur::demarrer(None, avec_vram)?;
    let es0 = Processus::courant().es();
    let t_ouv = Instant::now();
    // Constat G1 de l'épreuve J1 : sur une erreur, le moteur n'est PAS détruit (sa destruction a pu
    // tourner sans fin dans le pilote, sous charge, avant que l'erreur ne soit écrite). `main` écrit
    // l'erreur puis termine le processus ; le système et le pilote libèrent tout. Sur le chemin
    // normal, le moteur est détruit à la fin, comme avant.
    let mut m = ManuallyDrop::new(Moteur::nouveau(&c)?);
    let ouverture_s = t_ouv.elapsed().as_secs_f64();
    let contexte = c.contexte as usize;
    if invite.len() + n > contexte {
        bail!("{} jetons d'invite + {n} à produire > contexte de {contexte}", invite.len());
    }
    let c0 = m.compteurs();
    let t0 = Instant::now();
    let mut suivant = 0u32;
    if a.a("flux") {
        suivant = m.preremplir(&invite, None)?;
    } else {
        for (p, &j) in invite.iter().enumerate() {
            suivant = m.pas(j, p as u32, None)?;
        }
    }
    let s_pre = t0.elapsed().as_secs_f64();
    let c1 = m.compteurs();
    let t1 = Instant::now();
    let mut produits: Vec<u32> = Vec::with_capacity(n);
    let mut pos = invite.len() as u32;
    let mut cumul: Vec<f64> = Vec::with_capacity(n);
    for _ in 0..n {
        produits.push(suivant);
        if arret_fin && Some(suivant) == arret {
            break;
        }
        if produits.len() == n {
            break;
        }
        suivant = m.pas(suivant, pos, None)?;
        pos += 1;
        cumul.push(t1.elapsed().as_secs_f64());
    }
    let s_gen = t1.elapsed().as_secs_f64();
    let c2 = m.compteurs();
    let releve = echant.arreter();
    let memoire_fin = Processus::courant().memoire();
    let es1 = Processus::courant().es();

    let texte: String = produits.iter().map(|&t| jetons.texte(t)).collect();
    if let Some(s) = a.mot("sortie") {
        std::fs::write(s, &texte).with_context(|| format!("écriture de {s}"))?;
    }
    if let Some(t) = a.mot("trace") {
        m.ecrire_trace(Path::new(t))?;
    }
    if let Some(ch) = a.mot("chronogramme") {
        let mut s = String::from("pas,couche,expert,source,soumis_ms,lu_ms,copie_debut_ms,copie_fin_ms,dec_debut_ms,dec_fin_ms,routeur_ms,fin_couche_ms\n");
        for d in m.dates() {
            let _ = writeln!(s, "{},{},{},{},{:.4},{:.4},{:.4},{:.4},{:.4},{:.4},{:.4},{:.4}", d.pas, d.couche, d.expert, d.source, d.soumis_ms, d.lu_ms, d.copie_debut_ms, d.copie_fin_ms, d.dec_debut_ms, d.dec_fin_ms, d.routeur_ms, d.fin_couche_ms);
        }
        std::fs::write(ch, s)?;
    }
    let pas_gen = (c2.pas - c1.pas) as f64;
    let v = json!({
        "outil": "troncons generer", "version": env!("CARGO_PKG_VERSION"),
        "commande": a.brut.join(" ").replace('\\', "/"), "date_utc": date_utc(), "alimentation": alimentation(),
        "moteur": moteur_json(&m, &c, ouverture_s),
        "invite": source_invite, "jetons_invite": invite.len(), "jetons_produits": produits.len(), "flux": a.a("flux"),
        "pas_generation": pas_gen,
        "prefill_s": s_pre, "prefill_jetons_s": invite.len() as f64 / s_pre,
        "generation_s": s_gen, "generation_jetons_s": if s_gen > 0.0 { pas_gen / s_gen } else { 0.0 },
        "compteurs_prefill": compteurs_json(&moins(&c1, &c0)),
        "compteurs_generation": compteurs_json(&moins(&c2, &c1)),
        "compteurs_total": compteurs_json(&c2),
        "memoire": {"pointe_ensemble_travail": releve.memoire_pointe.ensemble_travail_pointe, "pointe_engagee": releve.memoire_pointe.engagee_pointe,
                     "fin_ensemble_travail": memoire_fin.ensemble_travail, "fin_pointe_ensemble_travail": memoire_fin.ensemble_travail_pointe},
        "vram": {"pointe_mio": releve.vram_pointe_mio, "premiere_mio": releve.vram_premiere_mio, "echantillons": releve.echantillons_vram},
        "disque": {"octets_lus_pdh": releve.octets_disque_lus, "duree_s": releve.duree_s, "repos_octets_s": repos_go_s,
                   "processus": es_json(&es0, &es1), "octets_comptes_moteur": octets_comptes(&m)},
        "jetons": produits, "texte_sha256": sha256_hex(texte.as_bytes()),
        "texte": texte,
        "temps_cumules_generation_s": cumul,
    });
    if let Some(j) = a.mot("journal") {
        ecrire(Path::new(j), &v)?;
    }
    eprintln!(
        "troncons : {} jetons d'invite en {:.1} s ({:.2} j/s), {} produits en {:.1} s ({:.3} j/s) ; h = {:.3} ; mémoire de pointe {:.1} Mo ; VRAM de pointe {:?} Mio",
        invite.len(),
        s_pre,
        invite.len() as f64 / s_pre,
        produits.len(),
        s_gen,
        if s_gen > 0.0 { pas_gen / s_gen } else { 0.0 },
        c2.h(),
        releve.memoire_pointe.ensemble_travail_pointe as f64 / 1e6,
        releve.vram_pointe_mio
    );
    println!("{texte}");
    drop(ManuallyDrop::into_inner(m));
    Ok(())
}

// ============================================================================ evaluer

fn evaluer(a: &Args) -> Result<()> {
    let c = config(a)?;
    let base = PathBuf::from(a.exige("base")?);
    let sortie = PathBuf::from(a.exige("sortie")?);
    let kb = FichierKld::ouvrir(&base)?;
    let n_f: usize = a.nombre("fenetres", kb.n_chunk)?;
    if n_f > kb.n_chunk {
        bail!("{n_f} fenêtres demandées, {} dans la base", kb.n_chunk);
    }
    let n_ctx = kb.n_ctx;
    let positions: usize = a.nombre("positions", n_ctx)?;
    let jetons_tous: Vec<u32> = kb.jetons[..n_f * n_ctx].to_vec();
    drop(kb);
    let es0 = Processus::courant().es();
    let t_ouv = Instant::now();
    // Constat G1 : jamais détruit sur une erreur (voir `generer`).
    let mut m = ManuallyDrop::new(Moteur::nouveau(&c)?);
    let ouverture_s = t_ouv.elapsed().as_secs_f64();
    let vocab = m.hyper().vocab;
    let mut ecrivain = if positions == n_ctx { Some(EcrivainKld::creer(&sortie, n_ctx, vocab, &jetons_tous)?) } else { None };
    let mut csv = String::from("fenetre,position,jeton,argmax,empreinte64_logits\n");
    let mut z = vec![0f32; vocab];
    let mut z64 = vec![0f64; vocab];
    let notees = positions_notees(n_ctx);
    let flux = a.a("flux");
    let t0 = Instant::now();
    let mut nll = 0.0f64;
    let mut n_nll = 0usize;
    for f in 0..n_f {
        m.reinitialiser();
        let jw = &jetons_tous[f * n_ctx..(f + 1) * n_ctx];
        let mut servir = |p: usize, z: &[f32]| -> Result<()> {
            // argmax (égalité : plus petit indice), comme le noyau `argmax`
            let mut am = 0usize;
            for i in 1..z.len() {
                if z[i] > z[am] {
                    am = i;
                }
            }
            let e = empreinte64_f32(z);
            let _ = writeln!(csv, "{f},{p},{},{am},{e:016x}", jw[p]);
            if notees.contains(&p) {
                for (d, s) in z64.iter_mut().zip(z) {
                    *d = *s as f64;
                }
                if let Some(w) = ecrivain.as_mut() {
                    w.ecrire(&z64)?;
                }
                // PPL au passage (log-softmax en f64 du jeton suivant), pour le journal.
                let mx = z64.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
                let lse = mx + z64.iter().map(|x| (x - mx).exp()).sum::<f64>().ln();
                nll -= z64[jw[p + 1] as usize] - lse;
                n_nll += 1;
            }
            Ok(())
        };
        if flux {
            m.preremplir(&jw[..positions], Some(&mut servir))?;
        } else {
            for p in 0..positions {
                m.pas(jw[p], p as u32, Some(&mut z))?;
                servir(p, &z)?;
            }
        }
        eprintln!("troncons evaluer : fenêtre {}/{n_f} ({:.0} s)", f + 1, t0.elapsed().as_secs_f64());
    }
    if let Some(w) = ecrivain {
        w.finir()?;
    }
    let s = t0.elapsed().as_secs_f64();
    if let Some(e) = a.mot("empreintes") {
        std::fs::write(e, &csv)?;
    }
    if let Some(t) = a.mot("trace") {
        m.ecrire_trace(Path::new(t))?;
    }
    let cpt = m.compteurs();
    let v = json!({
        "outil": "troncons evaluer", "version": env!("CARGO_PKG_VERSION"),
        "commande": a.brut.join(" ").replace('\\', "/"), "date_utc": date_utc(), "alimentation": alimentation(),
        "moteur": moteur_json(&m, &c, ouverture_s),
        "base": base.display().to_string().replace('\\', "/"), "sortie": sortie.display().to_string().replace('\\', "/"),
        "fenetres": n_f, "n_ctx": n_ctx, "positions_par_fenetre": positions, "pas": cpt.pas, "flux": flux, "flux_positions": cpt.flux_positions, "flux_experts": cpt.flux_experts,
        "empreinte_csv_sha256": sha256_hex(csv.as_bytes()),
        "ppl_positions_notees": if n_nll > 0 { (nll / n_nll as f64).exp() } else { 0.0 }, "positions_notees": n_nll,
        "secondes": s, "pas_s": cpt.pas as f64 / s,
        "compteurs": compteurs_json(&cpt),
        "disque": {"processus": es_json(&es0, &Processus::courant().es()), "octets_comptes_moteur": octets_comptes(&m)},
    });
    if let Some(j) = a.mot("journal") {
        ecrire(Path::new(j), &v)?;
    }
    drop(ManuallyDrop::into_inner(m));
    eprintln!("troncons evaluer : {} pas en {s:.0} s ({:.2} pas/s), h = {:.3}, PPL des positions notées {:.3}", cpt.pas, cpt.pas as f64 / s, cpt.h(), if n_nll > 0 { (nll / n_nll as f64).exp() } else { 0.0 });
    Ok(())
}

// ============================================================================ disque

/// xorshift64* (même générateur que les essais du lot E), pour un ordre de lecture reproductible.
struct Tirage(u64);
impl Tirage {
    fn suivant(&mut self) -> u64 {
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        self.0.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }
}

fn disque(a: &Args) -> Result<()> {
    let chemin = PathBuf::from(a.exige("modele")?);
    let n: usize = a.nombre("n", 1000usize)?;
    let graine: u64 = a.nombre("graine", 1u64)?;
    let prof: usize = a.nombre("profondeur", 4usize)?;
    let lg_fixe: Option<u32> = a.mot("longueur-lecture").map(|s| s.parse()).transpose().context("--longueur-lecture")?;
    let repos: f64 = a.nombre("repos", 0.0)?;
    let f = trc_format::Fichier::ouvrir(&chemin)?;
    let rep = f.repertoire().to_vec();
    let lmax = rep.iter().map(|r| r.longueur_jusqua(1)).max().unwrap_or(4096);
    let lal = lg_fixe.map_or(lmax, |x| x as u64).max(lmax) as usize;
    let mut ordre: Vec<usize> = (0..rep.len()).collect();
    let mut t = Tirage(graine | 1);
    for i in (1..ordre.len()).rev() {
        let j = (t.suivant() % (i as u64 + 1)) as usize;
        ordre.swap(i, j);
    }
    ordre.truncate(n.min(rep.len()));
    let repos_go_s = if repos > 0.0 { Some(repos_disque(repos)?) } else { None };
    let ctx = trc_cuda::Contexte::nouveau(0)?;
    let fen = trc_cuda::HoteEpingle::allouer(&ctx, prof * lal, false)?;
    let lecteur = trc_es::Lecteur::ouvrir(&chemin, prof).map_err(|e| anyhow::anyhow!("{e}"))?;
    let taille = lecteur.taille();
    let echant = Echantillonneur::demarrer(None, false)?;
    let t0 = Instant::now();
    let mut libres: Vec<usize> = (0..prof).collect();
    let mut a_ach: Vec<trc_es::Achevement> = Vec::new();
    let mut place_de: HashMap<u64, usize> = HashMap::new();
    let (mut suivant, mut faits, mut octets) = (0usize, 0usize, 0u64);
    let mut durees: Vec<u32> = Vec::with_capacity(ordre.len());
    while faits < ordre.len() {
        while suivant < ordre.len() && !libres.is_empty() {
            let s = libres.pop().unwrap();
            let e = &rep[ordre[suivant]];
            let lg = lg_fixe.map_or(e.longueur_jusqua(1), |x| x as u64).min(taille - e.decalage);
            // SAFETY : tampon s de `lal` octets dans la fenêtre.
            let dst = unsafe { fen.pointeur().add(s * lal) };
            lecteur.soumettre(trc_es::Requete { jeton: suivant as u64, decalage: e.decalage, longueur: lg as u32, destination: dst }).map_err(|e| anyhow::anyhow!("{e}"))?;
            place_de.insert(suivant as u64, s);
            suivant += 1;
        }
        a_ach.clear();
        lecteur.recolter(u32::MAX, &mut a_ach).map_err(|e| anyhow::anyhow!("{e}"))?;
        for x in &a_ach {
            if let Some(e) = x.erreur {
                bail!("lecture {} : erreur Windows {e}", x.jeton);
            }
            octets += x.octets as u64;
            durees.push(x.duree_us);
            libres.push(place_de.remove(&x.jeton).unwrap());
            faits += 1;
        }
    }
    let s = t0.elapsed().as_secs_f64();
    let releve = echant.arreter();
    durees.sort();
    let v = json!({
        "outil": "troncons disque", "version": env!("CARGO_PKG_VERSION"),
        "commande": a.brut.join(" ").replace('\\', "/"), "date_utc": date_utc(), "alimentation": alimentation(),
        "fichier": chemin.display().to_string().replace('\\', "/"), "n": ordre.len(), "graine": graine, "profondeur": prof,
        "longueur_lecture": lg_fixe, "octets": octets, "secondes": s, "go_s": octets as f64 / s / 1e9,
        "duree_us_mediane": durees.get(durees.len() / 2), "duree_us_p90": durees.get(durees.len() * 9 / 10),
        "disque_pdh_octets": releve.octets_disque_lus, "repos_octets_s": repos_go_s,
    });
    if let Some(j) = a.mot("journal") {
        ecrire(Path::new(j), &v)?;
    }
    eprintln!("troncons disque : {} tronçons, {:.3} Go en {s:.2} s : {:.3} Go/s", ordre.len(), octets as f64 / 1e9, octets as f64 / s / 1e9);
    Ok(())
}

// ============================================================================ main

fn principal() -> Result<()> {
    let tout: Vec<String> = std::env::args().collect();
    let commande = tout.get(1).cloned().unwrap_or_default();
    let a = Args::lire(&tout[1.min(tout.len())..]);
    match commande.as_str() {
        "generer" => generer(&a, 0.0),
        "mesurer" => generer(&a, 10.0),
        "evaluer" => evaluer(&a),
        "disque" => disque(&a),
        _ => {
            eprintln!("usage : troncons generer|evaluer|mesurer … (voir l'en-tête de main.rs ; ARCHITECTURE.md § 5.10)");
            std::process::exit(2);
        }
    }
}

/// Termine le processus sans rien détruire (constat G1) : ni le moteur, ni le contexte CUDA, ni les
/// bibliothèques (aucun `DllMain` de sortie : `TerminateProcess` sur soi-même). Le système ferme les
/// poignées (dont la tâche de l'enfant nvidia-smi, qui meurt avec elle) et le pilote libère la carte.
fn terminer_sans_detruire(code: u32) -> ! {
    let _ = std::io::stdout().flush();
    let _ = std::io::stderr().flush();
    use windows_sys::Win32::System::Threading::{GetCurrentProcess, TerminateProcess};
    // SAFETY : pseudo-poignée du processus courant.
    unsafe {
        TerminateProcess(GetCurrentProcess(), code);
    }
    std::process::exit(code as i32)
}

fn main() -> ExitCode {
    // Constat G2 : un enfant ne doit jamais tenir les tuyaux du pilote qui nous a lancés.
    poignees_standard_non_heritables();
    match principal() {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            // L'erreur d'abord, avant toute destruction ; puis un journal d'erreur à côté du journal
            // demandé (`<journal>.erreur.json` : le journal lui-même n'est jamais écrit à moitié).
            eprintln!("troncons : erreur : {e:#}");
            let _ = std::io::stderr().flush();
            let tout: Vec<String> = std::env::args().collect();
            let a = Args::lire(&tout[1.min(tout.len())..]);
            if let Some(j) = a.mot("journal") {
                let v = json!({"outil": "troncons", "version": env!("CARGO_PKG_VERSION"), "commande": a.brut.join(" ").replace('\\', "/"),
                               "date_utc": date_utc(), "alimentation": alimentation(), "erreur": format!("{e:#}")});
                let _ = ecrire(Path::new(&format!("{j}.erreur.json")), &v);
            }
            terminer_sans_detruire(1)
        }
    }
}

#[cfg(test)]
mod tests {
    /// Le programme se lie au cache (l'espace de travail tient ensemble).
    #[test]
    fn lie_au_cache() {
        let tr = trc_cache::Trace::depuis_texte("0 1 | 2 3\n0 1 | 2 3\n").unwrap();
        let c = trc_cache::rejouer(&tr, 4, 0, trc_cache::Lru::default(), trc_cache::Lru::default());
        assert_eq!(c.succes_vram, 4);
    }

    #[test]
    fn date_bien_formee() {
        let d = super::date_utc();
        assert_eq!(d.len(), 20);
        assert!(d.ends_with('Z'));
    }
}
