//! Banc de la question clé : décoder le flux entropique DANS le produit matrice-vecteur,
//! ou JUSTE AVANT, quand les poids résident en VRAM.
//!
//! Données : les codes MXFP4 réels d'un GGUF (gpt-oss), et leurs échelles E8M0 réelles,
//! regroupés en une matrice de K = 4096 colonnes (les blocs de 32 poids restent entiers
//! et gardent leur échelle ; regrouper les lignes ne change que la forme, pas le travail).
//! Avec `--type 12` (Q4_K), les demi-octets Q4_K sont lus comme des codes MXFP4 et les
//! échelles sont synthétiques : c'est la distribution des codes qui change, pas le calcul.
//!
//! Chemins mesurés, même déquantification (gemv.wgsl) :
//!   brut        : codes bruts en VRAM, 4 bits par poids ;
//!   fusionne    : flux rANS (alphabet octet) décodé en registres et consommé sur place ;
//!   decodage_v4 : le décodeur seul (decodeur.wgsl), qui écrit les codes en VRAM ;
//!   deux_passes : decodage_v4 puis brut sur les codes décodés, dans la même soumission.
//!
//! Vérification exacte : avec des échelles toutes à 2^0 et des x entiers dans [-2, 2],
//! chaque terme est un entier de valeur absolue au plus 24, et toute somme de 4096 termes
//! reste sous 2^17 : elle est exacte en f32 dans n'importe quel ordre. Le résultat de la
//! carte doit donc égaler la référence du processeur bit à bit. Témoins : une fente de la
//! table corrompue (casser = 1), toutes les fentes corrompues (casser = 2) ; ils doivent
//! tomber (lignes fausses > 0).
//!
//! Usage : banc_gemv <fichier.gguf> <sortie.json> [--type 39] [--lot-mo 256] [--passes 5]

use rans_troncons::*;
use std::time::Instant;

const K: usize = 4096;
const MACRO_PAR_TUILE: usize = 256; // 256 macro-pas × 128 o = 32 Kio = 16 lignes de K = 4096

fn arg(args: &[String], nom: &str, defaut: usize) -> usize {
    args.iter().position(|a| a == nom).map(|i| args[i + 1].parse().unwrap()).unwrap_or(defaut)
}

fn mediane(v: &mut Vec<f64>) -> f64 {
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = v.len();
    if n % 2 == 1 { v[n / 2] } else { 0.5 * (v[n / 2 - 1] + v[n / 2]) }
}

/// Générateur pseudo-aléatoire minimal (xorshift64*), pour des entrées reproductibles.
struct Alea(u64);
impl Alea {
    fn suivant(&mut self) -> u64 {
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        self.0.wrapping_mul(0x2545F4914F6CDD1D)
    }
}

const KV2: [f64; 16] = [0., 1., 2., 3., 4., 6., 8., 12., 0., -1., -2., -3., -4., -6., -8., -12.];

/// Référence du processeur : y = W x en f64, disposition MXFP4 (voir gemv.wgsl).
fn reference(qs: &[u8], ech: &[u8], x: &[f32]) -> Vec<f64> {
    let blocs_ligne = K / 32;
    let lignes = qs.len() / (K / 2);
    (0..lignes)
        .map(|r| {
            let mut acc = 0.0f64;
            for b in 0..blocs_ligne {
                let bg = r * blocs_ligne + b;
                let s = 2f64.powi(ech[bg] as i32 - 128);
                let mut part = 0.0f64;
                for i in 0..16 {
                    let o = qs[bg * 16 + i];
                    part += KV2[(o & 15) as usize] * x[b * 32 + i] as f64;
                    part += KV2[(o >> 4) as usize] * x[b * 32 + 16 + i] as f64;
                }
                acc += s * part;
            }
            acc
        })
        .collect()
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let chemin = &args[1];
    let sortie_json = &args[2];
    let type_vise = arg(&args, "--type", 39) as u32;
    let lot_mo = arg(&args, "--lot-mo", 256);
    let passes = arg(&args, "--passes", 5);

    // ---- lot : demi-octets et échelles, en blocs entiers ------------------------------
    let infos = lire_entete_gguf(chemin);
    let choisis: Vec<&InfoTenseur> = infos.iter().filter(|t| t.type_ggml == type_vise).collect();
    let limite = lot_mo << 20;
    let mut lot_qs: Vec<u8> = Vec::with_capacity(limite);
    let mut lot_ech: Vec<u8> = Vec::with_capacity(limite / 16);
    let mut alea = Alea(0x9E3779B97F4A7C15);
    let t0 = Instant::now();
    let mut noms = Vec::new();
    for t in &choisis {
        if lot_qs.len() >= limite {
            break;
        }
        let brut = lire_tenseur(chemin, t);
        let (meta, qs) = separer_blocs(type_vise, &brut);
        if type_vise == 39 {
            assert_eq!(meta.len() * 16, qs.len());
            lot_ech.extend_from_slice(&meta);
        } else {
            // Q4_K : échelles synthétiques dans la plage des E8M0 réels de gpt-oss.
            for _ in 0..qs.len() / 16 {
                lot_ech.push(118 + (alea.suivant() % 8) as u8);
            }
        }
        lot_qs.extend_from_slice(&qs);
        noms.push(t.nom.clone());
    }
    let unite = MACRO_PAR_TUILE * VOIES * 4; // 32 Kio : une tuile pleine = 16 lignes
    let n = (lot_qs.len().min(limite) / unite) * unite;
    lot_qs.truncate(n);
    lot_ech.truncate(n / 16);
    let lignes = n / (K / 2);
    assert_eq!(unite % (K / 2), 0);
    eprintln!("lot : {} Mio de codes ({} lignes de {} poids), {} tenseurs, lecture {:.1} s",
        n >> 20, lignes, K, noms.len(), t0.elapsed().as_secs_f64());

    // ---- codage rANS, alphabet octet ----------------------------------------------------
    let mut comptes = vec![0u64; 256];
    for &o in &lot_qs {
        comptes[o as usize] += 1;
    }
    let table = Table256::depuis_comptes(&comptes);
    let flux = coder_octets(&lot_qs, &table, MACRO_PAR_TUILE);
    let taux = n as f64 / flux.octets_codes() as f64;
    let mut comptes_e = vec![0u64; 256];
    for &e in &lot_ech {
        comptes_e[e as usize] += 1;
    }
    let tot_e = lot_ech.len() as f64;
    let h_ech: f64 = comptes_e.iter().filter(|&&c| c > 0).map(|&c| { let p = c as f64 / tot_e; -p * p.log2() }).sum();
    eprintln!("rANS : {} o -> {} o (taux {:.4}), entropie des échelles {:.3} b sur 8", n, flux.octets_codes(), taux, h_ech);

    // ---- entrées : vérification exacte et mesure ----------------------------------------
    let x_verif: Vec<f32> = (0..K).map(|_| (alea.suivant() % 5) as f32 - 2.0).collect();
    let ech_verif = vec![128u8; lot_ech.len()];
    let x_mesure: Vec<f32> = (0..K).map(|_| (alea.suivant() % 20001) as f32 / 10000.0 - 1.0).collect();
    let t0 = Instant::now();
    let y_ref_verif = reference(&lot_qs, &ech_verif, &x_verif);
    let y_ref_mesure = reference(&lot_qs, &lot_ech, &x_mesure);
    eprintln!("références processeur : {:.1} s", t0.elapsed().as_secs_f64());

    let mut json = String::from("{\n");
    json.push_str(&format!(
        "  \"fichier\": {:?},\n  \"type_ggml\": {},\n  \"k\": {},\n  \"lignes\": {},\n  \"octets_codes_bruts\": {},\n  \"octets_echelles\": {},\n  \"octets_flux_rans\": {},\n  \"taux_rans_codes\": {:.6},\n  \"entropie_echelles_bits\": {:.6},\n  \"tenseurs\": {},\n",
        chemin, type_vise, K, lignes, n, lot_ech.len(), flux.octets_codes(), taux, h_ech, noms.len()));
    let r = pollster::block_on(banc_carte(&flux, &table, &lot_qs, &lot_ech, &ech_verif, &x_verif, &x_mesure,
        &y_ref_verif, &y_ref_mesure, lignes, passes));
    json.push_str(&r);
    json.push_str("}\n");
    std::fs::write(sortie_json, json).unwrap();
}

#[allow(clippy::too_many_arguments)]
async fn banc_carte(flux: &Flux, table: &Table256, lot_qs: &[u8], lot_ech: &[u8], ech_verif: &[u8],
    x_verif: &[f32], x_mesure: &[f32], y_ref_verif: &[f64], y_ref_mesure: &[f64], lignes: usize, passes: usize) -> String {
    use wgpu::util::DeviceExt;
    let mut desc = wgpu::InstanceDescriptor::new_without_display_handle();
    desc.backends = wgpu::Backends::VULKAN;
    let instance = wgpu::Instance::new(desc);
    let adaptateur = instance
        .request_adapter(&wgpu::RequestAdapterOptions {
            power_preference: wgpu::PowerPreference::HighPerformance,
            force_fallback_adapter: false,
            compatible_surface: None,
            apply_limit_buckets: false,
        })
        .await
        .expect("aucun adaptateur Vulkan");
    let info = adaptateur.get_info();
    eprintln!("carte : {} ({:?}), pilote {} {}", info.name, info.backend, info.driver, info.driver_info);
    let (device, queue) = adaptateur
        .request_device(&wgpu::DeviceDescriptor {
            label: Some("banc gemv"),
            required_features: wgpu::Features::SUBGROUP,
            required_limits: adaptateur.limits(),
            experimental_features: wgpu::ExperimentalFeatures::disabled(),
            memory_hints: wgpu::MemoryHints::Performance,
            trace: wgpu::Trace::Off,
        })
        .await
        .expect("création du périphérique");
    let m_gemv = device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: Some("gemv"), source: wgpu::ShaderSource::Wgsl(include_str!("../gemv.wgsl").into()) });
    let m_dec = device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: Some("decodeur"), source: wgpu::ShaderSource::Wgsl(include_str!("../decodeur.wgsl").into()) });
    let st = wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC | wgpu::BufferUsages::COPY_DST;
    let init = |nom: &str, octets: &[u8]| device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some(nom), contents: octets, usage: st });
    let b_lut = init("lut", bytemuck::cast_slice(&table.lut));
    let b_etats = init("etats", bytemuck::cast_slice(&flux.etats));
    let tuiles_plat: Vec<u32> = flux.tuiles.iter().flat_map(|t| t.iter().cloned()).collect();
    let b_tuiles = init("tuiles", bytemuck::cast_slice(&tuiles_plat));
    let mut mots32: Vec<u32> = vec![0; flux.mots.len().div_ceil(2) + 64];
    for (i, &w) in flux.mots.iter().enumerate() {
        mots32[i / 2] |= (w as u32) << (16 * (i % 2));
    }
    let b_mots = init("mots", bytemuck::cast_slice(&mots32));
    let pad4 = |v: &[u8]| { let mut w = v.to_vec(); w.resize(v.len().div_ceil(4) * 4, 0); w };
    let b_ech = init("echelles", &pad4(lot_ech));
    let b_ech_verif = init("echelles verif", &pad4(ech_verif));
    let b_x = init("x", bytemuck::cast_slice(x_mesure));
    let b_x_verif = init("x verif", bytemuck::cast_slice(x_verif));
    let b_brut = init("brut", lot_qs);
    let b_dec = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("codes décodés"), size: lot_qs.len() as u64, usage: st, mapped_at_creation: false });
    let taille_y = (lignes * 4) as u64;
    let b_y = device.create_buffer(&wgpu::BufferDescriptor { label: Some("y"), size: taille_y, usage: st, mapped_at_creation: false });
    let b_y_lu = device.create_buffer(&wgpu::BufferDescriptor { label: Some("y lu"), size: taille_y,
        usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
    let b_controle = init("controle", bytemuck::cast_slice(&[0u32; 4]));
    let b_controle_lu = device.create_buffer(&wgpu::BufferDescriptor { label: Some("controle lu"), size: 16,
        usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
    let nb_tuiles = flux.tuiles.len() as u32;
    let uni = |v: [u32; 4]| device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("params"), contents: bytemuck::cast_slice(&v), usage: wgpu::BufferUsages::UNIFORM });
    let mpl = (K / 8) as u32;
    let p_fus = [uni([nb_tuiles, 0, mpl, lignes as u32]), uni([nb_tuiles, 1, mpl, lignes as u32]), uni([nb_tuiles, 2, mpl, lignes as u32])];
    let p_brut = uni([(lignes / 16) as u32, 0, mpl, lignes as u32]);
    let p_dec = uni([nb_tuiles, 0, 0, 0]);

    let pipeline = |module: &wgpu::ShaderModule, entree: &str| device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
        label: Some(entree), layout: None, module, entry_point: Some(entree), compilation_options: Default::default(), cache: None });
    let pl_brut = pipeline(&m_gemv, "gemv_brut");
    let pl_fus = pipeline(&m_gemv, "gemv_fusionne");
    let pl_dec = pipeline(&m_dec, "decoder_v4");
    fn be(b: u32, buf: &wgpu::Buffer) -> wgpu::BindGroupEntry<'_> {
        wgpu::BindGroupEntry { binding: b, resource: buf.as_entire_binding() }
    }
    let g_brut = |codes: &wgpu::Buffer, ech: &wgpu::Buffer, x: &wgpu::Buffer| device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: Some("brut"), layout: &pl_brut.get_bind_group_layout(0),
        entries: &[be(4, ech), be(5, x), be(6, &b_y), be(7, &p_brut), be(9, codes)] });
    let g_fus = |params: &wgpu::Buffer, ech: &wgpu::Buffer, x: &wgpu::Buffer| device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: Some("fus"), layout: &pl_fus.get_bind_group_layout(0),
        entries: &[be(0, &b_lut), be(1, &b_etats), be(2, &b_tuiles), be(3, &b_mots), be(4, ech), be(5, x),
                   be(6, &b_y), be(7, params), be(8, &b_controle)] });
    let g_dec = device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: Some("dec"), layout: &pl_dec.get_bind_group_layout(0),
        entries: &[be(0, &b_lut), be(1, &b_etats), be(2, &b_tuiles), be(3, &b_mots), be(4, &b_dec), be(5, &p_dec), be(6, &b_controle)] });

    let gt_brut = (lignes / 16) as u32;
    let gt_fus = nb_tuiles.div_ceil(4);
    // Une étape = (pipeline, groupe, groupes de travail). Une mesure = `rep` fois la suite
    // d'étapes, chaque étape dans sa propre passe (barrière entre décodage et produit).
    let lancer = |etapes: &[(&wgpu::ComputePipeline, &wgpu::BindGroup, u32)], rep: usize| -> f64 {
        let mut enc = device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        for _ in 0..rep {
            for (pl, g, n) in etapes {
                let mut passe = enc.begin_compute_pass(&wgpu::ComputePassDescriptor { label: None, timestamp_writes: None });
                passe.set_pipeline(pl);
                passe.set_bind_group(0, *g, &[]);
                passe.dispatch_workgroups(*n, 1, 1);
            }
        }
        let t = Instant::now();
        queue.submit([enc.finish()]);
        device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
        t.elapsed().as_secs_f64()
    };
    let lire = |src: &wgpu::Buffer, dst: &wgpu::Buffer, taille: u64| -> Vec<u32> {
        let mut enc = device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        enc.copy_buffer_to_buffer(src, 0, dst, 0, taille);
        enc.clear_buffer(src, 0, None);
        queue.submit([enc.finish()]);
        dst.map_async(wgpu::MapMode::Read, .., |_| {});
        device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
        let v = { let vue = dst.get_mapped_range(..).unwrap(); bytemuck::cast_slice::<u8, u32>(&vue).to_vec() };
        dst.unmap();
        v
    };
    let lire_y = || -> Vec<f32> { lire(&b_y, &b_y_lu, taille_y).into_iter().map(f32::from_bits).collect() };
    let lire_controle = || -> Vec<u32> { lire(&b_controle, &b_controle_lu, 16) };
    let fausses_exactes = |y: &[f32]| y.iter().zip(y_ref_verif).filter(|(a, b)| **a as f64 != **b).count();
    let ecart_max = |y: &[f32]| y.iter().zip(y_ref_mesure).map(|(a, b)| ((*a as f64) - b).abs())
        .fold(0.0f64, f64::max) / y_ref_mesure.iter().map(|v| v.abs()).fold(0.0f64, f64::max);

    // ---- vérifications -------------------------------------------------------------------
    let mut json = String::new();
    json.push_str(&format!("  \"carte\": {:?},\n  \"pilote\": {:?},\n", info.name, format!("{} {}", info.driver, info.driver_info)));
    let gv_brut = g_brut(&b_brut, &b_ech_verif, &b_x_verif);
    lancer(&[(&pl_brut, &gv_brut, gt_brut)], 1);
    let f_brut = fausses_exactes(&lire_y());
    let gv_fus: Vec<wgpu::BindGroup> = p_fus.iter().map(|p| g_fus(p, &b_ech_verif, &b_x_verif)).collect();
    let mut f_fus = [0usize; 3];
    let mut c_fus = [0u32; 3];
    for c in 0..3 {
        lancer(&[(&pl_fus, &gv_fus[c], gt_fus)], 1);
        f_fus[c] = fausses_exactes(&lire_y());
        c_fus[c] = lire_controle()[0];
    }
    let gv_dec_brut = g_brut(&b_dec, &b_ech_verif, &b_x_verif);
    lancer(&[(&pl_dec, &g_dec, gt_fus), (&pl_brut, &gv_dec_brut, gt_brut)], 1);
    let f_deux = fausses_exactes(&lire_y());
    let c_deux = lire_controle()[0];
    eprintln!("vérification exacte (lignes fausses sur {lignes}) : brut {f_brut}, fondu {} (voies hors de L {}), deux passes {f_deux} (voies {c_deux})", f_fus[0], c_fus[0]);
    eprintln!("témoins : une fente corrompue -> {} lignes fausses (voies {}), toutes les fentes -> {} (voies {})", f_fus[1], c_fus[1], f_fus[2], c_fus[2]);
    json.push_str(&format!(
        "  \"verification_exacte\": {{\"lignes\": {lignes}, \"brut_lignes_fausses\": {f_brut}, \"fondu_lignes_fausses\": {}, \"fondu_voies_hors_L\": {}, \"deux_passes_lignes_fausses\": {f_deux}, \"deux_passes_voies_hors_L\": {c_deux}, \"temoin_une_fente_lignes_fausses\": {}, \"temoin_une_fente_voies_hors_L\": {}, \"temoin_toutes_fentes_lignes_fausses\": {}, \"temoin_toutes_fentes_voies_hors_L\": {}}},\n",
        f_fus[0], c_fus[0], f_fus[1], c_fus[1], f_fus[2], c_fus[2]));

    // Entrées de mesure : écart relatif au maximum de |y| (information ; f32 contre f64).
    let gm_brut = g_brut(&b_brut, &b_ech, &b_x);
    let gm_fus = g_fus(&p_fus[0], &b_ech, &b_x);
    let gm_dec_brut = g_brut(&b_dec, &b_ech, &b_x);
    lancer(&[(&pl_brut, &gm_brut, gt_brut)], 1);
    let e_brut = ecart_max(&lire_y());
    lancer(&[(&pl_fus, &gm_fus, gt_fus)], 1);
    let e_fus = ecart_max(&lire_y());
    eprintln!("entrées réelles : écart relatif max brut {e_brut:.2e}, fondu {e_fus:.2e}");
    json.push_str(&format!("  \"ecart_relatif_max_entrees_reelles\": {{\"brut\": {e_brut:.3e}, \"fondu\": {e_fus:.3e}}},\n"));

    // ---- débits : séries palindromiques --------------------------------------------------
    type Etapes<'a> = Vec<(&'a wgpu::ComputePipeline, &'a wgpu::BindGroup, u32)>;
    let candidats: Vec<(&str, Etapes)> = vec![
        ("brut", vec![(&pl_brut, &gm_brut, gt_brut)]),
        ("fusionne", vec![(&pl_fus, &gm_fus, gt_fus)]),
        ("decodage_v4", vec![(&pl_dec, &g_dec, gt_fus)]),
        ("deux_passes", vec![(&pl_dec, &g_dec, gt_fus), (&pl_brut, &gm_dec_brut, gt_brut)]),
    ];
    let reps: Vec<usize> = candidats.iter().map(|(_, e)| {
        let t = lancer(e, 3) / 3.0;
        ((0.25 / t).ceil() as usize).clamp(3, 2000)
    }).collect();
    let mut temps: Vec<Vec<f64>> = vec![Vec::new(); candidats.len()];
    let ordre: Vec<usize> = (0..candidats.len()).chain((0..candidats.len()).rev()).collect();
    for _ in 0..passes {
        for &i in &ordre {
            temps[i].push(lancer(&candidats[i].1, reps[i]) / reps[i] as f64);
        }
    }
    let poids = (lignes * K) as f64;
    let octets_poids = (lot_qs.len() + lot_ech.len()) as f64;
    json.push_str(&format!("  \"series_par_chemin\": {},\n  \"chemins\": {{", 2 * passes));
    for (i, (nom, _)) in candidats.iter().enumerate() {
        let v = &mut temps[i];
        let mn = v.iter().cloned().fold(f64::MAX, f64::min);
        let mx = v.iter().cloned().fold(0.0, f64::max);
        let md = mediane(v);
        eprintln!("{nom:12} médiane {:8.1} µs : {:6.1} milliards de poids/s, {:6.1} Go/s de poids MXFP4 équivalents (meilleure {:6.1}), dispersion {:.1} %, {} lancements",
            md * 1e6, poids / md / 1e9, octets_poids / md / 1e9, octets_poids / mn / 1e9, 100.0 * (mx - mn) / mn, reps[i]);
        json.push_str(&format!(
            "\"{nom}\": {{\"temps_median_s\": {md:.6e}, \"milliards_poids_s\": {:.3}, \"go_s_poids_mxfp4_equivalents\": {:.3}, \"go_s_meilleure\": {:.3}, \"dispersion\": {:.4}, \"lancements_par_mesure\": {}, \"temps_s\": {:?}}}{}",
            poids / md / 1e9, octets_poids / md / 1e9, octets_poids / mn / 1e9, (mx - mn) / mn, reps[i], v,
            if i + 1 < candidats.len() { ", " } else { "" }));
    }
    json.push_str("}\n");
    json
}
