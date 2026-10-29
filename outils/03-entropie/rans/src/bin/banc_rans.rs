//! Banc du rANS entrelacé sur les codes Q4_K d'un GGUF.
//!
//! 1. Histogramme des codes de tous les tenseurs Q4_K, table globale normalisée à 4096.
//! 2. Codage de chaque tenseur Q4_K (taux réel, coût des en-têtes compris).
//! 3. Un lot de `--lot-mo` Mio de demi-octets : décodage processeur (1 fil, 6 fils,
//!    16 fils) contre une recopie mémoire de même taille, en séries ABBA.
//! 4. Le même lot sur la carte (Vulkan, wgpu, sous-groupes) : décodage contre une
//!    recopie de même géométrie, en séries ABBA ; vérification bit à bit ; témoin cassé.
//!
//! Usage : banc_rans <fichier.gguf> <sortie.json> [--lot-mo 256] [--macro 256]
//!         [--passes 5] [--sans-carte] [--sans-processeur] [--type 12|39] [--max-tenseurs N]

use rans_troncons::*;
use std::time::Instant;

fn arg(args: &[String], nom: &str, defaut: usize) -> usize {
    args.iter()
        .position(|a| a == nom)
        .map(|i| args[i + 1].parse().unwrap())
        .unwrap_or(defaut)
}

fn mediane(v: &mut Vec<f64>) -> f64 {
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = v.len();
    if n % 2 == 1 { v[n / 2] } else { 0.5 * (v[n / 2 - 1] + v[n / 2]) }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let chemin = &args[1];
    let sortie_json = &args[2];
    let lot_mo = arg(&args, "--lot-mo", 256);
    let macro_par_tuile = arg(&args, "--macro", 256);
    let passes = arg(&args, "--passes", 5);
    let sans_carte = args.iter().any(|a| a == "--sans-carte");
    // --sans-processeur : saute les débits du processeur (section 3), pour une passe de
    // carte courte, logée dans une fenêtre calme.
    let sans_processeur = args.iter().any(|a| a == "--sans-processeur");
    let mut json = String::new();
    json.push_str("{\n");
    json.push_str(&format!("  \"fichier\": {:?},\n  \"macro_par_tuile\": {},\n", chemin, macro_par_tuile));

    // ---- 1. lecture et histogramme --------------------------------------------------
    let infos = lire_entete_gguf(chemin);
    let type_vise = arg(&args, "--type", 12) as u32; // 12 = Q4_K, 39 = MXFP4
    json.push_str(&format!("  \"type_ggml\": {},\n", type_vise));
    let max_tenseurs = arg(&args, "--max-tenseurs", usize::MAX);
    let q4: Vec<&InfoTenseur> = infos.iter().filter(|t| t.type_ggml == type_vise).take(max_tenseurs).collect();
    let t0 = Instant::now();
    let tenseurs: Vec<(String, Vec<u8>, Vec<u8>)> = q4
        .iter()
        .map(|t| {
            let brut = lire_tenseur(chemin, t);
            let (meta, mut qs) = separer_blocs(type_vise, &brut);
            qs.truncate(qs.len() / 128 * 128); // le codeur veut des macro-pas entiers de 128 o
            (t.nom.clone(), meta, qs)
        })
        .collect();
    eprintln!("lecture de {} tenseurs du type visé : {:.1} s", tenseurs.len(), t0.elapsed().as_secs_f64());
    let mut global = [0u64; 16];
    let mut par_tenseur: Vec<[u64; 16]> = Vec::new();
    for (_, _, qs) in &tenseurs {
        let mut h = [0u64; 16];
        for &o in qs {
            h[(o & 15) as usize] += 1;
            h[(o >> 4) as usize] += 1;
        }
        for i in 0..16 {
            global[i] += h[i];
        }
        par_tenseur.push(h);
    }
    let table = Table::depuis_comptes(&global);
    let mut global_octets = vec![0u64; 256];
    for (_, _, qs) in &tenseurs {
        for &o in qs {
            global_octets[o as usize] += 1;
        }
    }
    let table8 = Table256::depuis_comptes(&global_octets);
    let h_octets = {
        let tot: u64 = global_octets.iter().sum();
        global_octets.iter().filter(|&&c| c > 0).map(|&c| { let p = c as f64 / tot as f64; -p * p.log2() }).sum::<f64>()
    };
    let h_global = entropie(&global);
    let bits_table = table.bits_attendus(&global);
    // coût d'une table unique contre une table par tenseur (entropie conditionnelle)
    let total_codes: u64 = global.iter().sum();
    let h_par_tenseur: f64 = par_tenseur
        .iter()
        .map(|h| entropie(h) * h.iter().sum::<u64>() as f64)
        .sum::<f64>()
        / total_codes as f64;
    json.push_str(&format!(
        "  \"codes_q4k\": {},\n  \"H0_global\": {:.6},\n  \"H0_moyenne_par_tenseur\": {:.6},\n  \"bits_table_quantifiee\": {:.6},\n  \"freq\": {:?},\n",
        total_codes, h_global, h_par_tenseur, bits_table, table.freq
    ));
    eprintln!("H0 global {:.4} b, par tenseur {:.4} b, table 12 bits {:.4} b", h_global, h_par_tenseur, bits_table);

    // ---- 2. codage de tous les tenseurs ---------------------------------------------
    let pool_tous = rayon::ThreadPoolBuilder::new().num_threads(16).build().unwrap();
    let t0 = Instant::now();
    let flux_tous: Vec<Flux> = pool_tous.install(|| {
        use rayon::prelude::*;
        tenseurs.par_iter().map(|(_, _, qs)| coder(qs, &table, macro_par_tuile)).collect()
    });
    let duree_codage = t0.elapsed().as_secs_f64();
    let octets_qs: usize = tenseurs.iter().map(|t| t.2.len()).sum();
    let octets_meta: usize = tenseurs.iter().map(|t| t.1.len()).sum();
    let octets_codes: usize = flux_tous.iter().map(|f| f.octets_codes()).sum();
    let flux_tous8: Vec<Flux> = pool_tous.install(|| {
        use rayon::prelude::*;
        tenseurs.par_iter().map(|(_, _, qs)| coder_octets(qs, &table8, macro_par_tuile)).collect()
    });
    let octets_codes8: usize = flux_tous8.iter().map(|f| f.octets_codes()).sum();
    let taux8 = tenseurs.iter().map(|t| t.2.len()).sum::<usize>() as f64 / octets_codes8 as f64;
    json.push_str(&format!(
        "  \"H0_octet_qs\": {:.6},\n  \"bits_table256_par_octet\": {:.6},\n  \"octets_codes_alphabet256\": {},\n  \"taux_qs_alphabet256\": {:.6},\n",
        h_octets, table8.bits_attendus(&global_octets), octets_codes8, taux8));
    eprintln!("alphabet 256 : H0 {:.4} b/octet, table {:.4} b/octet, taux {:.4}", h_octets, table8.bits_attendus(&global_octets), taux8);
    let octets_mots: usize = flux_tous.iter().map(|f| f.mots.len() * 2).sum();
    let taux_qs = octets_qs as f64 / octets_codes as f64;
    let taux_q4k = (octets_qs + octets_meta) as f64 / (octets_codes + octets_meta) as f64;
    eprintln!(
        "codage {:.2} s ({:.2} Go/s, 16 fils) : demi-octets {} -> {} o (taux {:.4}), Q4_K entier taux {:.4}",
        duree_codage,
        octets_qs as f64 / duree_codage / 1e9,
        octets_qs,
        octets_codes,
        taux_qs,
        taux_q4k
    );
    json.push_str(&format!(
        "  \"octets_qs\": {},\n  \"octets_meta\": {},\n  \"octets_codes\": {},\n  \"octets_mots_seuls\": {},\n  \"bits_par_code_reels\": {:.6},\n  \"taux_qs\": {:.6},\n  \"taux_q4k_meta_brutes\": {:.6},\n  \"codage_go_s_16fils\": {:.4},\n",
        octets_qs, octets_meta, octets_codes, octets_mots, octets_codes as f64 * 8.0 / total_codes as f64,
        taux_qs, taux_q4k, octets_qs as f64 / duree_codage / 1e9
    ));

    // ---- 3. lot pour les débits ------------------------------------------------------
    let limite = lot_mo << 20;
    let mut lot_qs: Vec<u8> = Vec::new();
    for (_, _, qs) in &tenseurs {
        if lot_qs.len() + qs.len() > limite && !lot_qs.is_empty() {
            break;
        }
        lot_qs.extend_from_slice(qs);
    }
    let flux = coder(&lot_qs, &table, macro_par_tuile);
    let flux8 = coder_octets(&lot_qs, &table8, macro_par_tuile);
    let mots_sortie = lot_qs.len() / 4;
    let attendu: Vec<u32> = bytemuck::cast_slice::<u8, u32>(&lot_qs).to_vec();
    eprintln!("lot : {} Mio de demi-octets, {} tuiles, {} o codés", lot_qs.len() >> 20, flux.tuiles.len(), flux.octets_codes());
    json.push_str(&format!(
        "  \"lot_octets_qs\": {},\n  \"lot_tuiles\": {},\n  \"lot_octets_codes\": {},\n",
        lot_qs.len(), flux.tuiles.len(), flux.octets_codes()
    ));

    // Processeur : décodage contre recopie, ABBA, pour 1, 6 et 16 fils.
    json.push_str("  \"processeur\": [\n");
    let mut sortie = vec![0u32; mots_sortie];
    let mut copie = vec![0u32; mots_sortie];
    let configs: Vec<(usize, bool)> = if sans_processeur { Vec::new() } else {
        vec![(1, false), (1, true), (6, false), (6, true), (16, false), (16, true)] };
    for (ic, &(fils, octets)) in configs.iter().enumerate() {
        let pool = rayon::ThreadPoolBuilder::new().num_threads(fils).build().unwrap();
        let (fx, lut) = if octets { (&flux8, &table8.lut) } else { (&flux, &table.lut) };
        let dec = |s: &mut Vec<u32>| if octets { decoder_tout_octets(fx, lut, s, &pool) } else { decoder_tout(fx, lut, s, &pool) };
        let echecs = dec(&mut sortie);
        let exact = sortie == attendu;
        let mut t_dec = Vec::new();
        let mut t_cop = Vec::new();
        for _ in 0..passes {
            for etape in [0, 1, 1, 0] {
                let t = Instant::now();
                if etape == 0 {
                    dec(&mut sortie);
                    t_dec.push(t.elapsed().as_secs_f64());
                } else {
                    pool.install(|| {
                        use rayon::prelude::*;
                        copie.par_chunks_mut(1 << 16).zip(attendu.par_chunks(1 << 16)).for_each(|(d, s)| d.copy_from_slice(s));
                    });
                    t_cop.push(t.elapsed().as_secs_f64());
                }
            }
        }
        let mn = t_dec.iter().cloned().fold(f64::MAX, f64::min);
        let mx = t_dec.iter().cloned().fold(0.0, f64::max);
        let md = mediane(&mut t_dec);
        let mc = mediane(&mut t_cop);
        let go_dec = lot_qs.len() as f64 / md / 1e9;
        let go_max = lot_qs.len() as f64 / mn / 1e9;
        let go_cop = lot_qs.len() as f64 / mc / 1e9;
        eprintln!("processeur {:2} fils, alphabet {:3} : décodage {:.3} Go/s (meilleure {:.3}), recopie {:.2} Go/s, exact={} échecs={} dispersion={:.1}%",
            fils, if octets { 256 } else { 16 }, go_dec, go_max, go_cop, exact, echecs, 100.0 * (mx - mn) / mn);
        json.push_str(&format!(
            "    {{\"fils\": {}, \"alphabet\": {}, \"exact\": {}, \"voies_en_echec\": {}, \"decodage_go_s_sortie\": {:.4}, \"decodage_go_s_meilleure\": {:.4}, \"recopie_go_s\": {:.4}, \"dispersion_relative_decodage\": {:.4}, \"series\": {}}}{}\n",
            fils, if octets { 256 } else { 16 }, exact, echecs, go_dec, go_max, go_cop, (mx - mn) / mn, 2 * passes,
            if ic + 1 < configs.len() { "," } else { "" }));
    }
    json.push_str("  ],\n");

    // ---- 4. carte -------------------------------------------------------------------
    if !sans_carte {
        let r = pollster::block_on(banc_carte(&flux, &table, &flux8, &table8, &attendu, passes));
        json.push_str(&r);
    } else {
        json.push_str("  \"carte\": null\n");
    }
    json.push_str("}\n");
    std::fs::write(sortie_json, json).unwrap();
}

async fn banc_carte(flux: &Flux, table: &Table, flux8: &Flux, table8: &Table256, attendu: &[u32], passes: usize) -> String {
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
    eprintln!("carte : {} ({:?}), pilote {} {}, sous-groupes {}..{}", info.name, info.backend, info.driver, info.driver_info, info.subgroup_min_size, info.subgroup_max_size);
    let limites = adaptateur.limits();
    let (device, queue) = adaptateur
        .request_device(&wgpu::DeviceDescriptor {
            label: Some("banc rANS"),
            required_features: wgpu::Features::SUBGROUP,
            required_limits: limites.clone(),
            experimental_features: wgpu::ExperimentalFeatures::disabled(),
            memory_hints: wgpu::MemoryHints::Performance,
            trace: wgpu::Trace::Off,
        })
        .await
        .expect("création du périphérique");
    let module = device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: Some("decodeur"),
        source: wgpu::ShaderSource::Wgsl(include_str!("../decodeur.wgsl").into()),
    });
    let stockage = wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC | wgpu::BufferUsages::COPY_DST;
    let b_lut = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("lut"), contents: bytemuck::cast_slice(&table.lut), usage: stockage });
    let b_etats = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("etats"), contents: bytemuck::cast_slice(&flux.etats), usage: stockage });
    let tuiles_plat: Vec<u32> = flux.tuiles.iter().flat_map(|t| t.iter().cloned()).collect();
    let b_tuiles = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("tuiles"), contents: bytemuck::cast_slice(&tuiles_plat), usage: stockage });
    // 64 mots de 32 bits de marge : la fenêtre « suivante » de la v2 lit au-delà de la fin.
    let mut mots32: Vec<u32> = vec![0; flux.mots.len().div_ceil(2) + 64];
    for (i, &w) in flux.mots.iter().enumerate() {
        mots32[i / 2] |= (w as u32) << (16 * (i % 2));
    }
    let b_mots = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("mots"), contents: bytemuck::cast_slice(&mots32), usage: stockage });
    let b_lut8 = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("lut8"), contents: bytemuck::cast_slice(&table8.lut), usage: stockage });
    let b_etats8 = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("etats8"), contents: bytemuck::cast_slice(&flux8.etats), usage: stockage });
    let mut mots8: Vec<u32> = vec![0; flux8.mots.len().div_ceil(2) + 64];
    for (i, &w) in flux8.mots.iter().enumerate() {
        mots8[i / 2] |= (w as u32) << (16 * (i % 2));
    }
    let b_mots8 = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("mots8"), contents: bytemuck::cast_slice(&mots8), usage: stockage });
    let tuiles8_plat: Vec<u32> = flux8.tuiles.iter().flat_map(|t| t.iter().cloned()).collect();
    assert_eq!(flux8.tuiles.len(), flux.tuiles.len());
    let b_tuiles8 = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("tuiles8"), contents: bytemuck::cast_slice(&tuiles8_plat), usage: stockage });
    let b_brut = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("brut"), contents: bytemuck::cast_slice(attendu), usage: stockage });
    let taille_sortie = (attendu.len() * 4) as u64;
    let b_sortie = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("sortie"), size: taille_sortie, usage: stockage, mapped_at_creation: false });
    let b_lecture = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("lecture"), size: taille_sortie,
        usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
    let b_controle = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("controle"), contents: bytemuck::cast_slice(&[0u32; 4]), usage: stockage });
    let b_controle_lu = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("controle lu"), size: 16,
        usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
    let nb_tuiles = flux.tuiles.len() as u32;
    let fabrique_params = |casser: u32| {
        device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("params"), contents: bytemuck::cast_slice(&[nb_tuiles, casser, 0, 0]),
            usage: wgpu::BufferUsages::UNIFORM })
    };
    let b_params = fabrique_params(0);
    let b_params_casse = fabrique_params(1);

    let pipeline = |entree: &str| {
        device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some(entree), layout: None, module: &module, entry_point: Some(entree),
            compilation_options: Default::default(), cache: None })
    };
    let p_cop = pipeline("copier");
    let groupe_dec = |pipe: &wgpu::ComputePipeline, params: &wgpu::Buffer| {
        device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("dec"), layout: &pipe.get_bind_group_layout(0),
            entries: &[
                wgpu::BindGroupEntry { binding: 0, resource: b_lut.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 1, resource: b_etats.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 2, resource: b_tuiles.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 3, resource: b_mots.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 4, resource: b_sortie.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 5, resource: params.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 6, resource: b_controle.as_entire_binding() },
            ] })
    };
    // (nom, pipeline, groupe normal, groupe du témoin cassé)
    let variantes: Vec<(&str, wgpu::ComputePipeline)> = ["decoder_v1", "decoder", "decoder_v3"]
        .iter().map(|n| (*n, pipeline(n))).collect();
    let mut groupes: Vec<(wgpu::BindGroup, wgpu::BindGroup)> = variantes.iter()
        .map(|(_, p)| (groupe_dec(p, &b_params), groupe_dec(p, &b_params_casse))).collect();
    let p_v4 = pipeline("decoder_v4");
    let groupe_v4 = |params: &wgpu::Buffer| {
        device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("v4"), layout: &p_v4.get_bind_group_layout(0),
            entries: &[
                wgpu::BindGroupEntry { binding: 0, resource: b_lut8.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 1, resource: b_etats8.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 2, resource: b_tuiles8.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 3, resource: b_mots8.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 4, resource: b_sortie.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 5, resource: params.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 6, resource: b_controle.as_entire_binding() },
            ] })
    };
    groupes.push((groupe_v4(&b_params), groupe_v4(&b_params_casse)));
    let mut variantes = variantes;
    variantes.push(("decoder_v4", p_v4));
    let p_cop4 = pipeline("copier_vec4");
    let g_cop4 = device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: Some("cop4"), layout: &p_cop4.get_bind_group_layout(0),
        entries: &[
            wgpu::BindGroupEntry { binding: 7, resource: b_brut.as_entire_binding() },
            wgpu::BindGroupEntry { binding: 8, resource: b_sortie.as_entire_binding() },
        ] });
    let g_cop = device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: Some("cop"), layout: &p_cop.get_bind_group_layout(0),
        entries: &[
            wgpu::BindGroupEntry { binding: 2, resource: b_tuiles.as_entire_binding() },
            wgpu::BindGroupEntry { binding: 3, resource: b_brut.as_entire_binding() },
            wgpu::BindGroupEntry { binding: 4, resource: b_sortie.as_entire_binding() },
            wgpu::BindGroupEntry { binding: 5, resource: b_params.as_entire_binding() },
        ] });
    let groupes_travail = nb_tuiles.div_ceil(4); // 128 invocations = 4 sous-groupes de 32

    let lancer = |pipe: &wgpu::ComputePipeline, groupe: &wgpu::BindGroup, repetitions: usize| -> f64 {
        // la recopie vec4 a sa propre grille : 24 multiprocesseurs × 32 groupes de 256
        let groupes_travail = if std::ptr::eq(pipe, &p_cop4) { 768 } else { groupes_travail };
        let mut enc = device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        {
            let mut passe = enc.begin_compute_pass(&wgpu::ComputePassDescriptor { label: None, timestamp_writes: None });
            passe.set_pipeline(pipe);
            passe.set_bind_group(0, groupe, &[]);
            for _ in 0..repetitions {
                passe.dispatch_workgroups(groupes_travail, 1, 1);
            }
        }
        let t = Instant::now();
        queue.submit([enc.finish()]);
        device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
        t.elapsed().as_secs_f64()
    };
    let lire_controle = || -> [u32; 4] {
        let mut enc = device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        enc.copy_buffer_to_buffer(&b_controle, 0, &b_controle_lu, 0, 16);
        enc.clear_buffer(&b_controle, 0, None);
        queue.submit([enc.finish()]);
        b_controle_lu.map_async(wgpu::MapMode::Read, .., |_| {});
        device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
        let v: [u32; 4] = {
            let vue = b_controle_lu.get_mapped_range(..).unwrap();
            bytemuck::cast_slice::<u8, u32>(&vue)[..4].try_into().unwrap()
        };
        b_controle_lu.unmap();
        v
    };
    let lire_sortie = || -> Vec<u32> {
        let mut enc = device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        enc.copy_buffer_to_buffer(&b_sortie, 0, &b_lecture, 0, taille_sortie);
        enc.clear_buffer(&b_sortie, 0, None);
        queue.submit([enc.finish()]);
        b_lecture.map_async(wgpu::MapMode::Read, .., |_| {});
        device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
        let v = {
            let vue = b_lecture.get_mapped_range(..).unwrap();
            bytemuck::cast_slice::<u8, u32>(&vue).to_vec()
        };
        b_lecture.unmap();
        v
    };

    // Vérification de chaque variante, puis son témoin cassé (doit tomber).
    let mut json = String::from("  \"carte\": {");
    json.push_str(&format!("\"nom\": {:?}, \"backend\": \"{:?}\", \"pilote\": {:?}, \"sous_groupe_min\": {}, \"sous_groupe_max\": {}, ",
        info.name, info.backend, format!("{} {}", info.driver, info.driver_info), info.subgroup_min_size, info.subgroup_max_size));
    lancer(&p_cop, &g_cop, 1);
    let exact_copie = lire_sortie() == attendu;
    lancer(&p_cop4, &g_cop4, 1);
    let exact_copie = exact_copie && lire_sortie() == attendu;
    json.push_str(&format!("\"recopie_exacte\": {}, \"verifications\": {{", exact_copie));
    for (i, (nom, p)) in variantes.iter().enumerate() {
        lancer(p, &groupes[i].0, 1);
        let c1 = lire_controle();
        let ex1 = lire_sortie() == attendu;
        lancer(p, &groupes[i].1, 1);
        let c2 = lire_controle();
        let ex2 = lire_sortie() == attendu;
        eprintln!("carte : {nom} exact={ex1} (voies en échec {}, sous-groupe≠32 : {}) ; témoin cassé exact={ex2}, voies en échec {}", c1[0], c1[1], c2[0]);
        json.push_str(&format!("\"{nom}\": {{\"exact\": {ex1}, \"voies_en_echec\": {}, \"temoin_casse_exact\": {ex2}, \"temoin_casse_voies_en_echec\": {}}}{}",
            c1[0], c2[0], if i + 1 < variantes.len() { ", " } else { "" }));
    }
    json.push_str("}, ");

    // Débits : séries palindromiques sur toutes les variantes et la recopie
    // (v1 v2 v3 recopie recopie v3 v2 v1) ; chaque mesure est une soumission de `rep`
    // lancements, rapportée à un lancement.
    let calibrer = |pipe: &wgpu::ComputePipeline, g: &wgpu::BindGroup| {
        let e = lancer(pipe, g, 3) / 3.0;
        ((0.25 / e).ceil() as usize).clamp(3, 2000)
    };
    let mut candidats: Vec<(&str, &wgpu::ComputePipeline, &wgpu::BindGroup)> = variantes.iter().enumerate()
        .map(|(i, (n, p))| (*n, p, &groupes[i].0)).collect();
    candidats.push(("recopie", &p_cop, &g_cop));
    candidats.push(("recopie_vec4", &p_cop4, &g_cop4));
    let reps: Vec<usize> = candidats.iter().map(|(_, p, g)| calibrer(p, g)).collect();
    let mut temps: Vec<Vec<f64>> = vec![Vec::new(); candidats.len()];
    let ordre: Vec<usize> = (0..candidats.len()).chain((0..candidats.len()).rev()).collect();
    for _ in 0..passes {
        for &i in &ordre {
            let (_, p, g) = candidats[i];
            temps[i].push(lancer(p, g, reps[i]) / reps[i] as f64);
        }
    }
    let octets = taille_sortie as f64;
    json.push_str(&format!("\"series_par_variante\": {}, \"octets_sortie\": {}, \"octets_entree_codes\": {}, \"debits\": {{", 2 * passes, taille_sortie, flux.octets_codes()));
    for (i, (nom, _, _)) in candidats.iter().enumerate() {
        let v = &mut temps[i];
        let mn = v.iter().cloned().fold(f64::MAX, f64::min);
        let mx = v.iter().cloned().fold(0.0, f64::max);
        let md = mediane(v);
        let (go_md, go_max) = (octets / md / 1e9, octets / mn / 1e9);
        eprintln!("carte : {nom:10} médiane {go_md:6.1} Go/s écrits (meilleure passe {go_max:6.1}), dispersion {:.1} %, {} lancements par mesure", 100.0 * (mx - mn) / mn, reps[i]);
        json.push_str(&format!("\"{nom}\": {{\"go_s_sortie_mediane\": {go_md:.3}, \"go_s_sortie_meilleure\": {go_max:.3}, \"dispersion\": {:.4}, \"lancements_par_mesure\": {}, \"temps_s\": {:?}}}{}",
            (mx - mn) / mn, reps[i], v, if i + 1 < candidats.len() { ", " } else { "" }));
    }
    json.push_str("}}
");
    json
}
