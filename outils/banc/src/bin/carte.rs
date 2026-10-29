//! Banc de la carte graphique par wgpu (Vulkan ou DirectX 12), sans boîte à outils CUDA.
//!
//! Sous-commandes :
//!   info                                   adaptateurs, fonctions, limites (Vulkan et DX12)
//!   transfert --api vulkan|dx12 [--tailles 1M,16M,256M] [--passes 3] [--fausser]
//!       hôte → carte par DMA depuis un tampon en RAM hôte (relecture, épinglé par le pilote), par
//!       écriture du processeur dans le tampon d'envoi projeté (BAR), par queue.write_buffer (tampon
//!       paginable), carte → hôte, carte → carte, et la copie depuis le tampon d'envoi (si elle
//!       dépasse la PCIe, ce tampon vit en VRAM). Ordre ABBA à chaque passe.
//!   vram --api vulkan|dx12 [--taille 512M] [--passes 5] [--fausser]
//!       lecture de la VRAM par un shader de calcul (somme vérifiée contre le processeur).
//!   gemv --api vulkan|dx12 --format f16|q4 [--m 8192] [--k 8192] [--lot 1] [--reps 50]
//!        [--residence carte|hote|bar] [--passes 5] [--fausser]
//!       y = W x, une ligne par groupe de 256 fils. q4 : blocs de 32 poids, 16 octets de
//!       demi-octets et une échelle f16 (4,5 bits par poids, la forme de Q4_0).
//!   alu --api vulkan|dx12 --type f32|f16|dot4i8|deq4 [--passes 5] [--fausser]
//!       plafond de calcul : chaînes de FMA (f32, f16) ou de dot4I8Packed, ou décodage de
//!       demi-octets depuis les registres (deq4 : décalage, masque, conversion, FMA), sans mémoire.
//!   thermique --api vulkan --format q4 [--duree 300] [--m 32768]
//!       GEMV en boucle ; une ligne par tranche de 5 s.
//!
//! Témoins : aller-retour octet pour octet ; somme VRAM égale à la somme du processeur ;
//! GEMV comparée à une référence f64 sur 64 lignes. `--fausser` perturbe l'attendu : le témoin
//! doit échouer. Plafonds : PCIe 4.0 ×8 = 15,754 Go/s, GDDR6 128 bits à 16 Gbit/s = 256 Go/s.

use banc::*;
use std::time::Instant;
use wgpu::util::DeviceExt;

const PLAFOND_PCIE: f64 = 15.754;
const PLAFOND_VRAM: f64 = 256.0;
const L2_MAX: u64 = 32 << 20;

struct Gpu {
    device: wgpu::Device,
    queue: wgpu::Queue,
    info: wgpu::AdapterInfo,
    features: wgpu::Features,
    limites: wgpu::Limits,
}

fn backends(api: &str) -> wgpu::Backends {
    match api {
        "vulkan" => wgpu::Backends::VULKAN,
        "dx12" => wgpu::Backends::DX12,
        _ => panic!("--api vulkan|dx12"),
    }
}

fn adaptateurs(api: &str) -> Vec<wgpu::Adapter> {
    let mut d = wgpu::InstanceDescriptor::new_without_display_handle();
    d.backends = backends(api);
    let inst = wgpu::Instance::new(d);
    pollster::block_on(inst.enumerate_adapters(backends(api)))
}

fn ouvrir(api: &str) -> Gpu {
    let liste = adaptateurs(api);
    let adapter = liste
        .into_iter()
        .find(|a| a.get_info().vendor == 0x10DE)
        .expect("aucun adaptateur NVIDIA");
    let voulues = wgpu::Features::TIMESTAMP_QUERY
        | wgpu::Features::TIMESTAMP_QUERY_INSIDE_ENCODERS
        | wgpu::Features::TIMESTAMP_QUERY_INSIDE_PASSES
        | wgpu::Features::SHADER_F16
        | wgpu::Features::MAPPABLE_PRIMARY_BUFFERS;
    let features = adapter.features() & voulues;
    let limites = adapter.limits();
    let (device, queue) = pollster::block_on(adapter.request_device(&wgpu::DeviceDescriptor {
        label: Some("banc"),
        required_features: features,
        required_limits: limites.clone(),
        ..Default::default()
    }))
    .expect("request_device");
    Gpu { device, queue, info: adapter.get_info(), features, limites }
}

fn attendre(g: &Gpu) {
    g.device.poll(wgpu::PollType::wait_indefinitely()).expect("poll");
}

fn lire(g: &Gpu, buf: &wgpu::Buffer) -> Vec<u8> {
    let s = buf.slice(..);
    s.map_async(wgpu::MapMode::Read, |r| r.expect("map_async"));
    attendre(g);
    let v = s.get_mapped_range().expect("get_mapped_range").to_vec();
    buf.unmap();
    v
}

fn tampon(g: &Gpu, taille: u64, usage: wgpu::BufferUsages, projete: bool) -> wgpu::Buffer {
    g.device.create_buffer(&wgpu::BufferDescriptor { label: None, size: taille, usage, mapped_at_creation: projete })
}

/// Chronomètre de la carte : deux horodatages autour d'une suite de commandes d'encodeur.
struct Chrono {
    qs: wgpu::QuerySet,
    res: wgpu::Buffer,
    lu: wgpu::Buffer,
    periode_ns: f64,
}
impl Chrono {
    fn new(g: &Gpu) -> Option<Self> {
        if !g.features.contains(wgpu::Features::TIMESTAMP_QUERY_INSIDE_ENCODERS) {
            return None;
        }
        let qs = g.device.create_query_set(&wgpu::QuerySetDescriptor { label: None, ty: wgpu::QueryType::Timestamp, count: 2 });
        let res = tampon(g, 16, wgpu::BufferUsages::QUERY_RESOLVE | wgpu::BufferUsages::COPY_SRC, false);
        let lu = tampon(g, 16, wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, false);
        Some(Chrono { qs, res, lu, periode_ns: g.queue.get_timestamp_period() as f64 })
    }
    fn fermer(&self, enc: &mut wgpu::CommandEncoder) {
        enc.resolve_query_set(&self.qs, 0..2, &self.res, 0);
        enc.copy_buffer_to_buffer(&self.res, 0, &self.lu, 0, 16);
    }
    fn secondes(&self, g: &Gpu) -> f64 {
        let v = lire(g, &self.lu);
        let t0 = u64::from_le_bytes(v[0..8].try_into().unwrap());
        let t1 = u64::from_le_bytes(v[8..16].try_into().unwrap());
        t1.wrapping_sub(t0) as f64 * self.periode_ns * 1e-9
    }
}

fn main() {
    let a = Args::lire();
    match a.positionnels.first().map(|s| s.as_str()) {
        Some("info") => info(),
        Some("transfert") => transfert(&a),
        Some("vram") => vram(&a),
        Some("gemv") => gemv(&a),
        Some("thermique") => thermique(&a),
        Some("alu") => alu(&a),
        _ => {
            eprintln!("usage : carte info|transfert|vram|gemv|thermique --api vulkan|dx12 ...");
            std::process::exit(2);
        }
    }
}

fn info() {
    for api in ["vulkan", "dx12"] {
        for ad in adaptateurs(api) {
            let i = ad.get_info();
            let f = ad.features();
            let l = ad.limits();
            println!(
                "ADAPTATEUR api={api} nom=\"{}\" type={:?} pilote=\"{}\" info_pilote=\"{}\" vendeur=0x{:04X} \
                 ts={} ts_encodeur={} ts_passe={} f16={} sous_groupes={} projetable_primaire={} \
                 tampon_max={} liaison_stockage_max={} groupes_par_dim_max={}",
                i.name, i.device_type, i.driver, i.driver_info, i.vendor,
                f.contains(wgpu::Features::TIMESTAMP_QUERY),
                f.contains(wgpu::Features::TIMESTAMP_QUERY_INSIDE_ENCODERS),
                f.contains(wgpu::Features::TIMESTAMP_QUERY_INSIDE_PASSES),
                f.contains(wgpu::Features::SHADER_F16),
                f.contains(wgpu::Features::SUBGROUP),
                f.contains(wgpu::Features::MAPPABLE_PRIMARY_BUFFERS),
                l.max_buffer_size, l.max_storage_buffer_binding_size, l.max_compute_workgroups_per_dimension
            );
        }
    }
}

fn motif(n: usize, graine: u64) -> Vec<u8> {
    let mut v = vec![0u8; n];
    let mut e = graine | 1;
    for c in v.chunks_exact_mut(8) {
        c.copy_from_slice(&xorshift64star(&mut e).to_le_bytes());
    }
    v
}

fn stats(v: &[f64]) -> (f64, f64, f64) {
    let mut d = v.to_vec();
    d.sort_by(|x, y| x.partial_cmp(y).unwrap());
    (quantile(&d, 0.5), d[0], d[d.len() - 1])
}

// ---------------------------------------------------------------------------------------
fn transfert(a: &Args) {
    let api = a.texte("api", "vulkan");
    let passes = a.nombre("passes", 3.0) as usize;
    let fausser = a.drapeau("fausser");
    let g = ouvrir(&api);
    let chrono = Chrono::new(&g);
    println!("CARTE api={api} nom=\"{}\" chrono_carte={}", g.info.name, chrono.is_some());
    use wgpu::BufferUsages as U;
    for t in a.texte("tailles", "1M,4M,16M,64M,256M").split(',') {
        let taille = analyser_taille(t) as u64;
        let reps = ((1u64 << 30) / taille).clamp(4, 256) as usize;
        let donnees = motif(taille as usize, taille);
        let dev_a = tampon(&g, taille, U::STORAGE | U::COPY_DST | U::COPY_SRC, false);
        let dev_b = tampon(&g, taille, U::STORAGE | U::COPY_DST | U::COPY_SRC, false);
        let monte = tampon(&g, taille, U::MAP_WRITE | U::COPY_SRC, true);
        monte.slice(..).get_mapped_range_mut().expect("projection").copy_from_slice(&donnees);
        monte.unmap();
        let descend = tampon(&g, taille, U::MAP_READ | U::COPY_DST, false);
        // Mémoire hôte véritable : un tampon de relecture (MAP_READ) est placé par le pilote en RAM
        // hôte, en cache. Avec MAPPABLE_PRIMARY_BUFFERS il peut aussi servir de source de copie :
        // c'est la DMA hôte → carte à travers la PCIe.
        let hote = tampon(&g, taille, U::MAP_READ | U::COPY_SRC | U::COPY_DST, false);
        {
            let mut enc = g.device.create_command_encoder(&Default::default());
            enc.copy_buffer_to_buffer(&monte, 0, &hote, 0, taille);
            g.queue.submit([enc.finish()]);
            attendre(&g);
        }

        // Témoin : hôte projeté → A → B → hôte, octet pour octet.
        let mut enc = g.device.create_command_encoder(&Default::default());
        enc.copy_buffer_to_buffer(&monte, 0, &dev_a, 0, taille);
        enc.copy_buffer_to_buffer(&dev_a, 0, &dev_b, 0, taille);
        enc.copy_buffer_to_buffer(&dev_b, 0, &descend, 0, taille);
        g.queue.submit([enc.finish()]);
        let mut revenu = lire(&g, &descend);
        if fausser {
            revenu[taille as usize / 2] ^= 1;
        }
        let identiques = revenu == donnees;
        drop(revenu);

        // Une opération : rend (secondes au mur, secondes de la carte si chronomètre).
        let mesurer = |op: &str| -> (f64, Option<f64>) {
            let mut enc = g.device.create_command_encoder(&Default::default());
            let t0;
            if op == "write_buffer" {
                // Une écriture par soumission : le tampon de transit interne se recycle, sans quoi
                // reps × taille de transit s'empilent et la RAM libre (≈ 1 Gio) déborde en pagination.
                drop(enc);
                attendre(&g);
                t0 = Instant::now();
                for _ in 0..reps {
                    g.queue.write_buffer(&dev_a, 0, &donnees);
                    g.queue.submit([]);
                    attendre(&g);
                }
                return (t0.elapsed().as_secs_f64(), None);
            }
            if op == "h2d_bar_cpu" {
                // Le processeur écrit lui-même dans le tampon d'envoi projeté (BAR de la carte si le
                // pilote l'y a placé) : projection, copie, retrait, mesurés au mur.
                drop(enc);
                attendre(&g);
                t0 = Instant::now();
                for _ in 0..reps {
                    let s = monte.slice(..);
                    s.map_async(wgpu::MapMode::Write, |r| r.expect("map_async"));
                    attendre(&g);
                    s.get_mapped_range_mut().expect("projection").copy_from_slice(&donnees);
                    monte.unmap();
                }
                return (t0.elapsed().as_secs_f64(), None);
            }
            if let Some(c) = &chrono {
                enc.write_timestamp(&c.qs, 0);
            }
            for _ in 0..reps {
                match op {
                    "copie_tampon_envoi" => enc.copy_buffer_to_buffer(&monte, 0, &dev_a, 0, taille),
                    "h2d_hote_dma" => enc.copy_buffer_to_buffer(&hote, 0, &dev_a, 0, taille),
                    "d2h" => enc.copy_buffer_to_buffer(&dev_a, 0, &descend, 0, taille),
                    "d2d" => enc.copy_buffer_to_buffer(&dev_a, 0, &dev_b, 0, taille),
                    _ => unreachable!(),
                }
            }
            if let Some(c) = &chrono {
                enc.write_timestamp(&c.qs, 1);
                c.fermer(&mut enc);
            }
            let cb = enc.finish();
            attendre(&g);
            t0 = Instant::now();
            g.queue.submit([cb]);
            attendre(&g);
            let mur = t0.elapsed().as_secs_f64();
            (mur, chrono.as_ref().map(|c| c.secondes(&g)))
        };

        // copie_tampon_envoi : si elle dépasse la PCIe, le tampon d'envoi vit en VRAM (BAR redimensionnable).
        let ops = ["h2d_hote_dma", "h2d_bar_cpu", "write_buffer", "d2h", "d2d", "copie_tampon_envoi"];
        let n_ops = ops.len();
        let mut mur: Vec<Vec<f64>> = vec![Vec::new(); n_ops];
        let mut carte: Vec<Vec<f64>> = vec![Vec::new(); n_ops];
        let mut ordre_abba: Vec<Vec<f64>> = vec![Vec::new(); n_ops];
        let aller: Vec<usize> = (0..n_ops).collect();
        let abba: Vec<usize> = aller.iter().copied().chain(aller.iter().rev().copied()).collect();
        for _ in 0..passes {
            // ABBA sur les opérations : 0 1 … n-1 n-1 … 1 0.
            for &i in abba.iter() {
                let (m, c) = mesurer(ops[i]);
                let octets = (taille * reps as u64) as f64 * if ops[i] == "d2d" { 2.0 } else { 1.0 };
                mur[i].push(octets / m / 1e9);
                ordre_abba[i].push(octets / m / 1e9);
                if let Some(c) = c {
                    carte[i].push(octets / c / 1e9);
                }
            }
        }
        for i in 0..n_ops {
            let (med, mn, mx) = stats(&mur[i]);
            let bruit = {
                let v = &ordre_abba[i];
                let n = v.len();
                // A1 contre A2 de chaque bloc ABBA : écart d'un programme à lui-même.
                let mut b: f64 = 0.0;
                for p in 0..n / 2 {
                    let (x, y) = (v[2 * p], v[2 * p + 1]);
                    b = b.max((x - y).abs() / ((x + y) / 2.0));
                }
                b
            };
            let (cmed, _, cmx) = if carte[i].is_empty() { (f64::NAN, f64::NAN, f64::NAN) } else { stats(&carte[i]) };
            let en_vram = ops[i] == "d2d" || ops[i] == "copie_tampon_envoi";
            let plafond = if en_vram { PLAFOND_VRAM } else { PLAFOND_PCIE };
            let applicable = !en_vram || taille > L2_MAX;
            let sous_plafond = !applicable || (mx <= plafond && (cmx.is_nan() || cmx <= plafond));
            println!(
                "RESULTAT op={} api={api} taille={taille} reps={reps} go_s_mur_mediane={med:.3} go_s_mur_min={mn:.3} go_s_mur_max={mx:.3} \
                 go_s_carte_mediane={cmed:.3} bruit_abba={bruit:.3} sous_plafond={} temoin_aller_retour={}",
                ops[i], if applicable { sous_plafond.to_string() } else { "sans_objet(L2)".into() },
                if identiques { "ok" } else { "ECHEC" }
            );
        }
    }
}

// ---------------------------------------------------------------------------------------
const SHADER_VRAM: &str = r#"
@group(0) @binding(0) var<storage, read> src: array<vec4<u32>>;
@group(0) @binding(1) var<storage, read_write> part: array<u32>;
@compute @workgroup_size(256)
fn main(@builtin(global_invocation_id) gid: vec3<u32>, @builtin(num_workgroups) nw: vec3<u32>) {
    let total = nw.x * 256u;
    let n = arrayLength(&src);
    var acc = vec4<u32>(0u);
    for (var i = gid.x; i < n; i += total) {
        acc += src[i];
    }
    part[gid.x] = acc.x + acc.y + acc.z + acc.w;
}
"#;

fn pipeline(g: &Gpu, wgsl: &str) -> wgpu::ComputePipeline {
    let m = g.device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: None,
        source: wgpu::ShaderSource::Wgsl(wgsl.into()),
    });
    g.device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
        label: None,
        layout: None,
        module: &m,
        entry_point: Some("main"),
        compilation_options: Default::default(),
        cache: None,
    })
}

fn groupe(g: &Gpu, p: &wgpu::ComputePipeline, tampons: &[&wgpu::Buffer]) -> wgpu::BindGroup {
    let entrees: Vec<wgpu::BindGroupEntry> = tampons
        .iter()
        .enumerate()
        .map(|(i, b)| wgpu::BindGroupEntry { binding: i as u32, resource: b.as_entire_binding() })
        .collect();
    g.device.create_bind_group(&wgpu::BindGroupDescriptor { label: None, layout: &p.get_bind_group_layout(0), entries: &entrees })
}

/// Lance `reps` dispatches dans une passe ; rend (mur, carte).
fn chronometrer_passe(g: &Gpu, p: &wgpu::ComputePipeline, bg: &wgpu::BindGroup, groupes: u32, reps: usize) -> (f64, Option<f64>) {
    let qs = g.features.contains(wgpu::Features::TIMESTAMP_QUERY).then(|| {
        g.device.create_query_set(&wgpu::QuerySetDescriptor { label: None, ty: wgpu::QueryType::Timestamp, count: 2 })
    });
    let res = tampon(g, 16, wgpu::BufferUsages::QUERY_RESOLVE | wgpu::BufferUsages::COPY_SRC, false);
    let lu = tampon(g, 16, wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, false);
    let mut enc = g.device.create_command_encoder(&Default::default());
    {
        let mut passe = enc.begin_compute_pass(&wgpu::ComputePassDescriptor {
            label: None,
            timestamp_writes: qs.as_ref().map(|q| wgpu::ComputePassTimestampWrites {
                query_set: q,
                beginning_of_pass_write_index: Some(0),
                end_of_pass_write_index: Some(1),
            }),
        });
        passe.set_pipeline(p);
        passe.set_bind_group(0, bg, &[]);
        for _ in 0..reps {
            passe.dispatch_workgroups(groupes, 1, 1);
        }
    }
    if let Some(q) = &qs {
        enc.resolve_query_set(q, 0..2, &res, 0);
        enc.copy_buffer_to_buffer(&res, 0, &lu, 0, 16);
    }
    let cb = enc.finish();
    attendre(g);
    let t0 = Instant::now();
    g.queue.submit([cb]);
    attendre(g);
    let mur = t0.elapsed().as_secs_f64();
    let carte = qs.map(|_| {
        let v = lire(g, &lu);
        let t0 = u64::from_le_bytes(v[0..8].try_into().unwrap());
        let t1 = u64::from_le_bytes(v[8..16].try_into().unwrap());
        t1.wrapping_sub(t0) as f64 * g.queue.get_timestamp_period() as f64 * 1e-9
    });
    (mur, carte)
}

fn vram(a: &Args) {
    let api = a.texte("api", "vulkan");
    let taille = a.nombre("taille", 512.0 * 1048576.0) as u64;
    let passes = a.nombre("passes", 5.0) as usize;
    let fausser = a.drapeau("fausser");
    let g = ouvrir(&api);
    assert!(taille <= g.limites.max_storage_buffer_binding_size as u64, "taille > liaison max");
    let donnees = motif(taille as usize, 7);
    let attendu = donnees
        .chunks_exact(4)
        .fold(0u32, |s, c| s.wrapping_add(u32::from_le_bytes(c.try_into().unwrap())))
        .wrapping_add(if fausser { 1 } else { 0 });
    use wgpu::BufferUsages as U;
    let src = g.device.create_buffer_init(&wgpu::util::BufferInitDescriptor { label: None, contents: &donnees, usage: U::STORAGE });
    drop(donnees);
    let groupes = 24 * 64u32; // 24 multiprocesseurs sur l'AD107 de la 4060 Laptop, 64 groupes chacun
    let part = tampon(&g, groupes as u64 * 256 * 4, U::STORAGE | U::COPY_SRC, false);
    let lu = tampon(&g, groupes as u64 * 256 * 4, U::MAP_READ | U::COPY_DST, false);
    let p = pipeline(&g, SHADER_VRAM);
    let bg = groupe(&g, &p, &[&src, &part]);
    let reps = 20;
    let mut mur = Vec::new();
    let mut carte = Vec::new();
    for _ in 0..passes {
        let (m, c) = chronometrer_passe(&g, &p, &bg, groupes, reps);
        mur.push(taille as f64 * reps as f64 / m / 1e9);
        if let Some(c) = c {
            carte.push(taille as f64 * reps as f64 / c / 1e9);
        }
    }
    let mut enc = g.device.create_command_encoder(&Default::default());
    enc.copy_buffer_to_buffer(&part, 0, &lu, 0, None);
    g.queue.submit([enc.finish()]);
    let v = lire(&g, &lu);
    let somme = v.chunks_exact(4).fold(0u32, |s, c| s.wrapping_add(u32::from_le_bytes(c.try_into().unwrap())));
    let (med, mn, mx) = stats(&mur);
    let (cmed, cmn, cmx) = if carte.is_empty() { (f64::NAN, f64::NAN, f64::NAN) } else { stats(&carte) };
    println!(
        "RESULTAT op=vram_lecture api={api} taille={taille} reps={reps} go_s_mur_mediane={med:.2} go_s_mur_min={mn:.2} go_s_mur_max={mx:.2} \
         go_s_carte_mediane={cmed:.2} go_s_carte_min={cmn:.2} go_s_carte_max={cmx:.2} sous_plafond={} temoin_somme={}",
        mx.max(if cmx.is_nan() { 0.0 } else { cmx }) <= PLAFOND_VRAM,
        if somme == attendu { "ok" } else { "ECHEC" }
    );
}

// ---------------------------------------------------------------------------------------
fn shader_gemv(format: &str, m: u32, k: u32, lot: u32) -> String {
    let tete = format!(
        "const M: u32 = {m}u;\nconst K: u32 = {k}u;\nconst LOT: u32 = {lot}u;\n\
         @group(0) @binding(0) var<storage, read> w: array<vec4<u32>>;\n\
         @group(0) @binding(1) var<storage, read> x: array<vec4<f32>>;\n\
         @group(0) @binding(2) var<storage, read_write> y: array<f32>;\n"
    );
    let corps = match format {
        // f16 : un vec4<u32> porte 8 poids ; K/8 vec4 par ligne.
        "f16" => r#"
var<workgroup> part: array<array<f32, LOT>, 256>;
@compute @workgroup_size(256)
fn main(@builtin(workgroup_id) wg: vec3<u32>, @builtin(local_invocation_index) t: u32) {
    let ligne = wg.x;
    let kv = K / 8u;
    var acc: array<f32, LOT>;
    for (var i = t; i < kv; i += 256u) {
        let q = w[ligne * kv + i];
        let a0 = unpack2x16float(q.x);
        let a1 = unpack2x16float(q.y);
        let a2 = unpack2x16float(q.z);
        let a3 = unpack2x16float(q.w);
        for (var b = 0u; b < LOT; b++) {
            let xb = b * (K / 4u) + i * 2u;
            let x0 = x[xb];
            let x1 = x[xb + 1u];
            acc[b] += dot(vec4<f32>(a0, a1), x0) + dot(vec4<f32>(a2, a3), x1);
        }
    }
    for (var b = 0u; b < LOT; b++) { part[t][b] = acc[b]; }
    workgroupBarrier();
    for (var s = 128u; s > 0u; s >>= 1u) {
        if (t < s) { for (var b = 0u; b < LOT; b++) { part[t][b] += part[t + s][b]; } }
        workgroupBarrier();
    }
    if (t == 0u) { for (var b = 0u; b < LOT; b++) { y[b * M + ligne] = part[0][b]; } }
}
"#,
        // q4b : même format que q4, 64 fils par ligne, chaque fil charge ses 4 blocs d'un coup
        // (4 lectures de 16 octets en vol par fil au lieu d'une) avant de calculer.
        "q4b" => r#"
@group(0) @binding(3) var<storage, read> e: array<u32>;
var<workgroup> part: array<array<f32, LOT>, 64>;
fn deq(m: u32, xv0: vec4<f32>, xv1: vec4<f32>) -> f32 {
    let lo = vec4<f32>(vec4<u32>(m, m >> 4u, m >> 8u, m >> 12u) & vec4<u32>(15u)) - vec4<f32>(8.0);
    let hi = vec4<f32>(vec4<u32>(m >> 16u, m >> 20u, m >> 24u, m >> 28u) & vec4<u32>(15u)) - vec4<f32>(8.0);
    return dot(lo, xv0) + dot(hi, xv1);
}
fn bloc(q: vec4<u32>, d: f32, xb: u32) -> f32 {
    return d * (deq(q.x, x[xb], x[xb + 1u]) + deq(q.y, x[xb + 2u], x[xb + 3u])
              + deq(q.z, x[xb + 4u], x[xb + 5u]) + deq(q.w, x[xb + 6u], x[xb + 7u]));
}
fn echelle(gi: u32) -> f32 {
    let sp = unpack2x16float(e[gi >> 1u]);
    return select(sp.x, sp.y, (gi & 1u) == 1u);
}
@compute @workgroup_size(64)
fn main(@builtin(workgroup_id) wg: vec3<u32>, @builtin(local_invocation_index) t: u32) {
    let ligne = wg.x;
    let nb = K / 32u;
    var acc: array<f32, LOT>;
    for (var base = 0u; base < nb; base += 256u) {
        let g0 = ligne * nb + base + t;
        let q0 = w[g0];
        let q1 = w[g0 + 64u];
        let q2 = w[g0 + 128u];
        let q3 = w[g0 + 192u];
        let d0 = echelle(g0);
        let d1 = echelle(g0 + 64u);
        let d2 = echelle(g0 + 128u);
        let d3 = echelle(g0 + 192u);
        for (var b = 0u; b < LOT; b++) {
            let xb = b * (K / 4u) + (base + t) * 8u;
            acc[b] += bloc(q0, d0, xb) + bloc(q1, d1, xb + 512u) + bloc(q2, d2, xb + 1024u) + bloc(q3, d3, xb + 1536u);
        }
    }
    for (var b = 0u; b < LOT; b++) { part[t][b] = acc[b]; }
    workgroupBarrier();
    for (var s = 32u; s > 0u; s >>= 1u) {
        if (t < s) { for (var b = 0u; b < LOT; b++) { part[t][b] += part[t + s][b]; } }
        workgroupBarrier();
    }
    if (t == 0u) { for (var b = 0u; b < LOT; b++) { y[b * M + ligne] = part[0][b]; } }
}
"#,
        // q4 : un vec4<u32> = 32 demi-octets = un bloc ; échelles f16 par paires dans `e`.
        _ => r#"
@group(0) @binding(3) var<storage, read> e: array<u32>;
var<workgroup> part: array<array<f32, LOT>, 256>;
fn deq(m: u32, xv0: vec4<f32>, xv1: vec4<f32>) -> f32 {
    let lo = vec4<f32>(vec4<u32>(m, m >> 4u, m >> 8u, m >> 12u) & vec4<u32>(15u)) - vec4<f32>(8.0);
    let hi = vec4<f32>(vec4<u32>(m >> 16u, m >> 20u, m >> 24u, m >> 28u) & vec4<u32>(15u)) - vec4<f32>(8.0);
    return dot(lo, xv0) + dot(hi, xv1);
}
@compute @workgroup_size(256)
fn main(@builtin(workgroup_id) wg: vec3<u32>, @builtin(local_invocation_index) t: u32) {
    let ligne = wg.x;
    let nb = K / 32u;
    var acc: array<f32, LOT>;
    for (var blk = t; blk < nb; blk += 256u) {
        let gi = ligne * nb + blk;
        let q = w[gi];
        let sp = unpack2x16float(e[gi >> 1u]);
        let d = select(sp.x, sp.y, (gi & 1u) == 1u);
        for (var b = 0u; b < LOT; b++) {
            let xb = b * (K / 4u) + blk * 8u;
            let s = deq(q.x, x[xb], x[xb + 1u]) + deq(q.y, x[xb + 2u], x[xb + 3u])
                  + deq(q.z, x[xb + 4u], x[xb + 5u]) + deq(q.w, x[xb + 6u], x[xb + 7u]);
            acc[b] += d * s;
        }
    }
    for (var b = 0u; b < LOT; b++) { part[t][b] = acc[b]; }
    workgroupBarrier();
    for (var s = 128u; s > 0u; s >>= 1u) {
        if (t < s) { for (var b = 0u; b < LOT; b++) { part[t][b] += part[t + s][b]; } }
        workgroupBarrier();
    }
    if (t == 0u) { for (var b = 0u; b < LOT; b++) { y[b * M + ligne] = part[0][b]; } }
}
"#,
    };
    tete + corps
}

struct Gemv {
    p: wgpu::ComputePipeline,
    bg: wgpu::BindGroup,
    y: wgpu::Buffer,
    octets_poids: u64,
    m: u32,
    k: u32,
    lot: u32,
    w: Vec<u8>,
    e: Vec<u8>,
    x: Vec<f32>,
    format: String,
}

fn preparer_gemv(g: &Gpu, format: &str, m: u32, k: u32, lot: u32, residence: &str) -> Gemv {
    use wgpu::BufferUsages as U;
    let (w, e) = match format {
        "f16" => {
            let mut et = 0x51u64;
            let mut w = vec![0u8; m as usize * k as usize * 2];
            for c in w.chunks_exact_mut(2) {
                let r = (xorshift64star(&mut et) >> 40) as f32 / (1u64 << 24) as f32 - 0.5; // [-0,5 ; 0,5)
                c.copy_from_slice(&half::f16::from_f32(r * 0.1).to_le_bytes());
            }
            (w, Vec::new())
        }
        _ => {
            let w = motif(m as usize * k as usize / 2, 0x77);
            let nb = m as usize * k as usize / 32;
            let mut et = 0x99u64;
            let mut e = vec![0u8; nb * 2];
            for c in e.chunks_exact_mut(2) {
                let r = 0.001 + (xorshift64star(&mut et) >> 40) as f32 / (1u64 << 24) as f32 * 0.01;
                c.copy_from_slice(&half::f16::from_f32(r).to_le_bytes());
            }
            (w, e)
        }
    };
    let mut ex = 0x1234u64;
    let x: Vec<f32> = (0..(k * lot) as usize).map(|_| (xorshift64star(&mut ex) >> 40) as f32 / (1u64 << 24) as f32 - 0.5).collect();
    let tw = if residence == "bar" {
        // Tampon projeté en écriture : le pilote le place en VRAM visible du processeur (BAR).
        assert!(g.features.contains(wgpu::Features::MAPPABLE_PRIMARY_BUFFERS), "MAPPABLE_PRIMARY_BUFFERS absent");
        let b = tampon(g, w.len() as u64, U::STORAGE | U::MAP_WRITE, true);
        b.slice(..).get_mapped_range_mut().expect("projection").copy_from_slice(&w);
        b.unmap();
        b
    } else if residence == "hote" {
        // Tampon de relecture (MAP_READ) : RAM hôte. Le shader lit les poids à travers la PCIe.
        assert!(g.features.contains(wgpu::Features::MAPPABLE_PRIMARY_BUFFERS), "MAPPABLE_PRIMARY_BUFFERS absent");
        let b = tampon(g, w.len() as u64, U::STORAGE | U::MAP_READ | U::COPY_DST, false);
        let source = g.device.create_buffer_init(&wgpu::util::BufferInitDescriptor { label: None, contents: &w, usage: U::COPY_SRC });
        let mut enc = g.device.create_command_encoder(&Default::default());
        enc.copy_buffer_to_buffer(&source, 0, &b, 0, w.len() as u64);
        g.queue.submit([enc.finish()]);
        attendre(g);
        b
    } else {
        g.device.create_buffer_init(&wgpu::util::BufferInitDescriptor { label: None, contents: &w, usage: U::STORAGE })
    };
    let tx = g.device.create_buffer_init(&wgpu::util::BufferInitDescriptor { label: None, contents: bytemuck::cast_slice(&x), usage: U::STORAGE });
    let y = tampon(g, (m * lot) as u64 * 4, U::STORAGE | U::COPY_SRC, false);
    let p = pipeline(g, &shader_gemv(format, m, k, lot));
    let bg = if format == "f16" {
        groupe(g, &p, &[&tw, &tx, &y])
    } else {
        let te = g.device.create_buffer_init(&wgpu::util::BufferInitDescriptor { label: None, contents: &e, usage: U::STORAGE });
        groupe(g, &p, &[&tw, &tx, &y, &te])
    };
    let octets_poids = (w.len() + e.len()) as u64;
    Gemv { p, bg, y, octets_poids, m, k, lot, w, e, x, format: format.to_string() }
}

/// Référence f64 sur 64 lignes réparties ; rend l'écart relatif maximal.
fn verifier_gemv(g: &Gpu, gm: &Gemv, fausser: bool) -> f64 {
    let lu = tampon(g, gm.y.size(), wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, false);
    let mut enc = g.device.create_command_encoder(&Default::default());
    enc.copy_buffer_to_buffer(&gm.y, 0, &lu, 0, None);
    g.queue.submit([enc.finish()]);
    let v = lire(g, &lu);
    let y: &[f32] = bytemuck::cast_slice(&v);
    let (m, k) = (gm.m as usize, gm.k as usize);
    let mut pire: f64 = 0.0;
    for i in 0..64 {
        let r = i * m / 64;
        for b in 0..gm.lot as usize {
            let xb = &gm.x[b * k..(b + 1) * k];
            let (mut s, mut sa) = (0f64, 0f64);
            for j in 0..k {
                let wv = if gm.format == "f16" {
                    let o = (r * k + j) * 2;
                    half::f16::from_le_bytes([gm.w[o], gm.w[o + 1]]).to_f64()
                } else {
                    let gi = (r * k + j) / 32;
                    let n = (r * k + j) % 32;
                    let mot = u32::from_le_bytes(gm.w[gi * 16 + (n / 8) * 4..gi * 16 + (n / 8) * 4 + 4].try_into().unwrap());
                    let q = ((mot >> (4 * (n % 8))) & 15) as f64 - 8.0;
                    let d = half::f16::from_le_bytes([gm.e[gi * 2], gm.e[gi * 2 + 1]]).to_f64();
                    q * d
                };
                s += wv * xb[j] as f64;
                sa += (wv * xb[j] as f64).abs();
            }
            if fausser {
                s += 0.01 * sa;
            }
            let ecart = (y[b * m + r] as f64 - s).abs() / sa.max(1e-30);
            pire = pire.max(ecart);
        }
    }
    pire
}

fn gemv(a: &Args) {
    let api = a.texte("api", "vulkan");
    let format = a.texte("format", "q4");
    let m = a.nombre("m", 8192.0) as u32;
    let k = a.nombre("k", 8192.0) as u32;
    let lot = a.nombre("lot", 1.0) as u32;
    let reps = a.nombre("reps", 50.0) as usize;
    let passes = a.nombre("passes", 5.0) as usize;
    let residence = a.texte("residence", "carte");
    let fausser = a.drapeau("fausser");
    let g = ouvrir(&api);
    let gm = preparer_gemv(&g, &format, m, k, lot, &residence);
    let (mur0, _) = chronometrer_passe(&g, &gm.p, &gm.bg, m, 1);
    let ecart = verifier_gemv(&g, &gm, fausser);
    let _ = mur0;
    let mut bw = Vec::new();
    let mut bwc = Vec::new();
    for _ in 0..passes {
        let (mm, c) = chronometrer_passe(&g, &gm.p, &gm.bg, m, reps);
        bw.push(gm.octets_poids as f64 * reps as f64 / mm / 1e9);
        if let Some(c) = c {
            bwc.push(gm.octets_poids as f64 * reps as f64 / c / 1e9);
        }
    }
    let (med, mn, mx) = stats(&bw);
    let (cmed, cmn, cmx) = if bwc.is_empty() { (f64::NAN, f64::NAN, f64::NAN) } else { stats(&bwc) };
    let flops = 2.0 * m as f64 * k as f64 * lot as f64;
    let t_carte = gm.octets_poids as f64 / (cmed * 1e9);
    let plafond = if residence == "hote" { PLAFOND_PCIE } else { PLAFOND_VRAM };
    println!(
        "RESULTAT op=gemv api={api} format={format} residence={residence} m={m} k={k} lot={lot} octets_poids={} reps={reps} \
         go_s_mur_mediane={med:.2} go_s_mur_min={mn:.2} go_s_mur_max={mx:.2} go_s_carte_mediane={cmed:.2} go_s_carte_min={cmn:.2} \
         go_s_carte_max={cmx:.2} us_par_gemv_carte={:.1} gflops_carte={:.1} ecart_relatif_max={ecart:.2e} temoin={} sous_plafond={}",
        gm.octets_poids, t_carte * 1e6, flops / t_carte / 1e9,
        if ecart <= 1e-3 { "ok" } else { "ECHEC" },
        gm.octets_poids <= L2_MAX || mx.max(if cmx.is_nan() { 0.0 } else { cmx }) <= plafond
    );
}

fn thermique(a: &Args) {
    let api = a.texte("api", "vulkan");
    let format = a.texte("format", "q4");
    let m = a.nombre("m", 32768.0) as u32;
    let k = a.nombre("k", 8192.0) as u32;
    let duree = a.nombre("duree", 300.0);
    let g = ouvrir(&api);
    let gm = preparer_gemv(&g, &format, m, k, 1, "carte");
    let t0 = Instant::now();
    let mut tranche = Instant::now();
    let (mut octets, mut n) = (0f64, 0u64);
    while t0.elapsed().as_secs_f64() < duree {
        let (_, c) = chronometrer_passe(&g, &gm.p, &gm.bg, m, 20);
        let _ = c;
        octets += gm.octets_poids as f64 * 20.0;
        n += 20;
        if tranche.elapsed().as_secs_f64() >= 5.0 {
            let dt = tranche.elapsed().as_secs_f64();
            println!("THERMIQUE t_s={:.1} go_s={:.2} gemv={n}", t0.elapsed().as_secs_f64(), octets / dt / 1e9);
            octets = 0.0;
            n = 0;
            tranche = Instant::now();
        }
    }
}

// ---------------------------------------------------------------------------------------
const ITER_ALU: u32 = 2048;

fn shader_alu(t: &str) -> String {
    let corps = match t {
        // 4 chaînes vec4 indépendantes : 16 FMA par tour, 32 opérations flottantes.
        "f32" | "f16" => {
            let ty = if t == "f16" { "f16" } else { "f32" };
            format!(
                "{en}@group(0) @binding(0) var<storage, read_write> sortie: array<f32>;\n\
                 @compute @workgroup_size(256)\n\
                 fn main(@builtin(global_invocation_id) gid: vec3<u32>) {{\n\
                   var a = vec4<{ty}>({ty}(f32(gid.x & 1023u) * 0.0009765625), {ty}(0.25), {ty}(0.5), {ty}(0.75));\n\
                   var b = a + vec4<{ty}>({ty}(0.125)); var c = a * {ty}(0.5); var d = a - vec4<{ty}>({ty}(0.0625));\n\
                   let m = vec4<{ty}>({ty}(0.99951171875)); let k = vec4<{ty}>({ty}(0.000244140625));\n\
                   for (var i = 0u; i < {it}u; i++) {{ a = fma(a, m, k); b = fma(b, m, k); c = fma(c, m, k); d = fma(d, m, k); }}\n\
                   sortie[gid.x] = f32(a.x + b.y + c.z + d.w);\n\
                 }}\n",
                en = if t == "f16" { "enable f16;\n" } else { "" },
                it = ITER_ALU
            )
        }
        // 4 chaînes de dot4I8Packed : 4 × 8 opérations entières (4 produits, 4 additions) par tour.
        "dot4i8" => format!(
            "@group(0) @binding(0) var<storage, read_write> sortie: array<f32>;\n\
             @compute @workgroup_size(256)\n\
             fn main(@builtin(global_invocation_id) gid: vec3<u32>) {{\n\
               var x = vec4<u32>(gid.x * 2654435761u, gid.x ^ 0x5bd1e995u, gid.x + 0x01020304u, ~gid.x);\n\
               let y = 0x03fd02feu;\n\
               var acc = vec4<i32>(0);\n\
               for (var i = 0u; i < {it}u; i++) {{\n\
                 acc.x += dot4I8Packed(x.x, y); acc.y += dot4I8Packed(x.y, y);\n\
                 acc.z += dot4I8Packed(x.z, y); acc.w += dot4I8Packed(x.w, y);\n\
                 x = x + vec4<u32>(0x01010101u);\n\
               }}\n\
               sortie[gid.x] = f32(acc.x ^ acc.y ^ acc.z ^ acc.w);\n\
             }}\n",
            it = ITER_ALU
        ),
        // Décodage de 32 poids de 4 bits par tour depuis un registre (comme deq de la GEMV q4),
        // FMA contre un x constant : la part « calcul » d'une décompression de format 4 bits.
        _ => format!(
            "@group(0) @binding(0) var<storage, read_write> sortie: array<f32>;\n\
             fn deq(m: u32, xv0: vec4<f32>, xv1: vec4<f32>) -> f32 {{\n\
               let lo = vec4<f32>(vec4<u32>(m, m >> 4u, m >> 8u, m >> 12u) & vec4<u32>(15u)) - vec4<f32>(8.0);\n\
               let hi = vec4<f32>(vec4<u32>(m >> 16u, m >> 20u, m >> 24u, m >> 28u) & vec4<u32>(15u)) - vec4<f32>(8.0);\n\
               return dot(lo, xv0) + dot(hi, xv1);\n\
             }}\n\
             @compute @workgroup_size(256)\n\
             fn main(@builtin(global_invocation_id) gid: vec3<u32>) {{\n\
               var q = vec4<u32>(gid.x * 2654435761u, gid.x ^ 0x5bd1e995u, gid.x + 0x01020304u, ~gid.x);\n\
               let x0 = vec4<f32>(0.1, 0.2, 0.3, 0.4); let x1 = vec4<f32>(0.5, 0.6, 0.7, 0.8);\n\
               var acc = 0.0;\n\
               for (var i = 0u; i < {it}u; i++) {{\n\
                 acc += deq(q.x, x0, x1) + deq(q.y, x0, x1) + deq(q.z, x0, x1) + deq(q.w, x0, x1);\n\
                 q = q + vec4<u32>(0x11111111u);\n\
               }}\n\
               sortie[gid.x] = acc;\n\
             }}\n",
            it = ITER_ALU
        ),
    };
    corps
}

/// Référence processeur d'un fil (même suite d'opérations), pour le témoin.
fn alu_reference(t: &str, gid: u32) -> f64 {
    match t {
        "f32" => {
            let a0 = (gid & 1023) as f32 * 0.0009765625;
            let mut v = [[a0, 0.25, 0.5, 0.75]; 4];
            for (j, w) in v.iter_mut().enumerate() {
                for l in 0..4 {
                    let base = [a0, 0.25f32, 0.5, 0.75][l];
                    w[l] = match j { 0 => base, 1 => base + 0.125, 2 => base * 0.5, _ => base - 0.0625 };
                }
            }
            for _ in 0..ITER_ALU {
                for w in v.iter_mut() {
                    for l in 0..4 {
                        w[l] = w[l].mul_add(0.99951171875, 0.000244140625);
                    }
                }
            }
            (v[0][0] + v[1][1] + v[2][2] + v[3][3]) as f64
        }
        "dot4i8" => {
            let d4 = |a: u32, b: u32| -> i32 {
                (0..4).map(|k| ((a >> (8 * k)) as u8 as i8 as i32) * ((b >> (8 * k)) as u8 as i8 as i32)).sum()
            };
            let mut x = [gid.wrapping_mul(2654435761), gid ^ 0x5bd1e995, gid.wrapping_add(0x01020304), !gid];
            let y = 0x03fd02feu32;
            let mut acc = [0i32; 4];
            for _ in 0..ITER_ALU {
                for k in 0..4 {
                    acc[k] = acc[k].wrapping_add(d4(x[k], y));
                    x[k] = x[k].wrapping_add(0x01010101);
                }
            }
            (acc[0] ^ acc[1] ^ acc[2] ^ acc[3]) as f32 as f64
        }
        "deq4" => {
            let x0 = [0.1f32, 0.2, 0.3, 0.4];
            let x1 = [0.5f32, 0.6, 0.7, 0.8];
            let deq = |m: u32| -> f32 {
                let mut s = 0f32;
                for k in 0..4 {
                    s += (((m >> (4 * k)) & 15) as f32 - 8.0) * x0[k];
                }
                let mut h = 0f32;
                for k in 0..4 {
                    h += (((m >> (16 + 4 * k)) & 15) as f32 - 8.0) * x1[k];
                }
                s + h
            };
            let mut q = [gid.wrapping_mul(2654435761), gid ^ 0x5bd1e995, gid.wrapping_add(0x01020304), !gid];
            let mut acc = 0f64;
            for _ in 0..ITER_ALU {
                acc += (deq(q[0]) + deq(q[1]) + deq(q[2]) + deq(q[3])) as f64;
                for k in 0..4 {
                    q[k] = q[k].wrapping_add(0x11111111);
                }
            }
            acc
        }
        _ => f64::NAN, // f16 : pas de référence exacte sur le processeur, seul le débit compte
    }
}

fn alu(a: &Args) {
    let api = a.texte("api", "vulkan");
    let t = a.texte("type", "f32");
    let passes = a.nombre("passes", 5.0) as usize;
    let fausser = a.drapeau("fausser");
    let g = ouvrir(&api);
    if t == "f16" && !g.features.contains(wgpu::Features::SHADER_F16) {
        println!("RESULTAT op=alu api={api} type=f16 indisponible=1");
        return;
    }
    let groupes = 24 * 64u32;
    let fils = groupes as u64 * 256;
    let sortie = tampon(&g, fils * 4, wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC, false);
    let lu = tampon(&g, fils * 4, wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, false);
    let p = pipeline(&g, &shader_alu(&t));
    let bg = groupe(&g, &p, &[&sortie]);
    let reps = 10;
    let ops_par_fil_tour = match t.as_str() { "f32" | "f16" => 32.0, "dot4i8" => 32.0, _ => 32.0 * 2.0 };
    let ops = fils as f64 * ITER_ALU as f64 * ops_par_fil_tour * reps as f64;
    let mut tops = Vec::new();
    for _ in 0..passes {
        let (m, c) = chronometrer_passe(&g, &p, &bg, groupes, reps);
        tops.push(ops / c.unwrap_or(m) / 1e12);
    }
    let mut enc = g.device.create_command_encoder(&Default::default());
    enc.copy_buffer_to_buffer(&sortie, 0, &lu, 0, None);
    g.queue.submit([enc.finish()]);
    let v = lire(&g, &lu);
    let y: &[f32] = bytemuck::cast_slice(&v);
    let mut pire: f64 = 0.0;
    let mut verifiable = false;
    for &gid in &[0u32, 1, 777, 123_456, fils as u32 - 1] {
        let r = alu_reference(&t, gid);
        if r.is_nan() {
            continue;
        }
        verifiable = true;
        let r = if fausser { r + 1.0 + r.abs() * 0.01 } else { r };
        pire = pire.max((y[gid as usize] as f64 - r).abs() / r.abs().max(1.0));
    }
    let (med, mn, mx) = stats(&tops);
    // Unités : opérations flottantes (f32, f16), entières (dot4i8 : 4 produits + 4 sommes), poids
    // décodés × 2 (deq4 : une multiplication-addition par poids de 4 bits).
    println!(
        "RESULTAT op=alu api={api} type={t} tops_mediane={med:.3} tops_min={mn:.3} tops_max={mx:.3} ecart_reference={pire:.2e} temoin={}",
        if !verifiable { "sans_reference" } else if pire <= 1e-3 { "ok" } else { "ECHEC" }
    );
}
