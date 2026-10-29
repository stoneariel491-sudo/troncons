//! Coût du décodage dans un shader de calcul portable (wgpu : Vulkan ou DirectX 12) :
//! produit matrice-vecteur 16 384 × 16 384, poids en scalaire 2 bits, en treillis à
//! décalage 2 bits (code calculé « mul1 », L = 16, tuile de 256 poids lue
//! circulairement), et en scalaire 4 bits. Même disposition et même parcours que le banc
//! CUDA `outils/quant-gemv-treillis.cu` (passe 2) : la voie v d'un groupe de 32 prend les
//! poids 8v..8v+7 d'une tuile, ses 8 activations en deux vec4, et les deux mots de 32
//! bits qui portent ses bits.
//!
//! Le treillis est décodé de deux façons : somme des 4 octets écrite à la main, et par
//! `dot4U8Packed` (produit scalaire d'entiers empaquetés, l'équivalent WGSL de `dp4a`).
//! Un noyau « lecture » (somme de vec4<u32> sur tout le tampon 2 bits) donne le plafond de
//! la bande passante sur la même carte et la même API.
//!
//! Témoin : 64 lignes recalculées sur le processeur (f64), erreur relative < 1e-3,
//! seuil déclaré avant ; `--casser` fausse la constante du code côté processeur seul.
//! Séries ABBA : A = scalaire 2 bits, B = chaque autre format.
//!
//! Passe 5 : « treillis-parite », code linéaire par parités sans multiplication
//! (index = parités de 4 masques de l'état, palette de 16 quantiles gaussiens en mémoire
//! partagée) ; `--casser` fausse aussi la palette côté processeur.
//!
//! Usage : quant-vulkan-gemv [--api vulkan|dx12] [--casser] [--series 3] [--reps 50]
//!         [--masques 0x..,0x..,0x..,0x..] [--formats treillis-parite,treillis-mul1-dot4-v2]

use std::time::Instant;

const M: usize = 16384;
const K: usize = 16384;
const TUILES: usize = K / 256;
const MUL1: u32 = 0x83DC_D12D;
const ECH: f32 = 0.02;
/// Palette uniforme renormalisée : (2j - 15) / écart-type de {2j - 15}, j = 0..15.
const ECH_UNIF: f32 = 0.108_465_24; // 1 / sqrt(85)

const ENTETE: &str = r#"
@group(0) @binding(0) var<storage, read> q: array<u32>;
@group(0) @binding(1) var<storage, read> x: array<vec4<f32>>;
@group(0) @binding(2) var<storage, read_write> y: array<f32>;
var<workgroup> part: array<f32, 256>;
const TUILES: u32 = 64u;

fn somme_main(v: u32) -> u32 {
    return (v & 0xffu) + ((v >> 8u) & 0xffu) + ((v >> 16u) & 0xffu) + (v >> 24u);
}
fn mul1(e: u32) -> f32 {
    let v = e * 0x83DCD12Du;
    let s = SOMME;
    return (f32(s) - 510.0) * (1.0 / 147.7);
}
fn fenetre4(w0: u32, w1: u32, off: vec4<u32>) -> vec4<u32> {
    let c = min(off, vec4<u32>(31u));
    let bas = ((vec4<u32>(w0) >> c) | (vec4<u32>(w1) << (vec4<u32>(32u) - c))) & vec4<u32>(0xffffu);
    let d = select(vec4<u32>(0u), off - vec4<u32>(32u), off >= vec4<u32>(32u));
    let haut = (vec4<u32>(w1) >> d) & vec4<u32>(0xffffu);
    return select(bas, haut, off >= vec4<u32>(32u));
}
fn mul1v(e: vec4<u32>) -> vec4<f32> {
    let v = e * vec4<u32>(0x83DCD12Du);
    let s = SOMMEV;
    return (vec4<f32>(s) - vec4<f32>(510.0)) * (1.0 / 147.7);
}
fn fenetre(w0: u32, w1: u32, off: u32) -> u32 {
    if (off >= 32u) { return (w1 >> (off - 32u)) & 0xffffu; }
    if (off <= 16u) { return (w0 >> off) & 0xffffu; }
    return ((w0 >> off) | (w1 << (32u - off))) & 0xffffu;
}
"#;

// Passe 3 : quatre lignes par groupe de 32 voies. Les activations d'une tuile sont lues
// une fois et servent aux quatre lignes : sans cela, chaque ligne relit tout x (64 Kio)
// depuis le cache L2, soit 1 Gio de trafic L2 par produit pour 64 Mio de poids, et le
// 2 bits plafonne sur le cache, pas sur la VRAM (passe 2 : 158 Go/s, journal
// vulkan-gemv-2.json).
const CORPS_2B: &str = r#"
var<workgroup> part4: array<vec4<f32>, 256>;
fn part_ligne(t: u32, i: u32, moitie: u32, xa: vec4<f32>, xb: vec4<f32>) -> f32 {
    let w1 = q[t + i];
    let w0 = q[t + ((i + 15u) & 15u)];
    DECODE
    return dot(va, xa) + dot(vb, xb);
}
@compute @workgroup_size(256)
fn main(@builtin(workgroup_id) wg: vec3<u32>, @builtin(local_invocation_index) li: u32) {
    let voie = li & 31u;
    let l0 = (wg.x * 8u + (li >> 5u)) * 4u;
    let pas = TUILES * 16u;
    let i = voie >> 1u;
    let moitie = voie & 1u;
    CHARGE_PALETTE
    var acc = vec4<f32>(0.0);
    for (var tu = 0u; tu < TUILES; tu++) {
        let xi = (tu * 256u + 8u * voie) / 4u;
        let xa = x[xi];
        let xb = x[xi + 1u];
        let t = l0 * pas + tu * 16u;
        acc.x += part_ligne(t, i, moitie, xa, xb);
        acc.y += part_ligne(t + pas, i, moitie, xa, xb);
        acc.z += part_ligne(t + 2u * pas, i, moitie, xa, xb);
        acc.w += part_ligne(t + 3u * pas, i, moitie, xa, xb);
    }
    part4[li] = acc;
    workgroupBarrier();
    for (var o = 16u; o > 0u; o >>= 1u) {
        if (voie < o) { part4[li] += part4[li + o]; }
        workgroupBarrier();
    }
    if (voie == 0u) {
        let r = part4[li] * 0.02;
        y[l0] = r.x; y[l0 + 1u] = r.y; y[l0 + 2u] = r.z; y[l0 + 3u] = r.w;
    }
}
"#;

// Passe 2 : sans tableau local (la passe 1 indexait un `array<f32, 8>` par une variable
// de boucle ; le 2 bits y tombait à 44 Go/s en Vulkan, sous le 4 bits : journaux
// *-gemv-1-tableau-local.json). Tout est en vec4 ; la fenêtre de 16 bits est extraite
// pour 4 décalages à la fois.
const DECODE_SCALAIRE: &str = r#"
        let b = w1 >> (16u * moitie);
        let va = vec4<f32>(vec4<u32>(b, b >> 2u, b >> 4u, b >> 6u) & vec4<u32>(3u)) - vec4<f32>(1.5);
        let vb = vec4<f32>(vec4<u32>(b >> 8u, b >> 10u, b >> 12u, b >> 14u) & vec4<u32>(3u)) - vec4<f32>(1.5);
"#;
// Passe 4 : extraction sans sélection. Pour une voie, les 8 fenêtres commencent aux
// bits 18..32 du couple (w0, w1) si moitie = 0, et 34..48 (donc 2..16 dans w1 seul) si
// moitie = 1. Avec lo = (moitie ? w1 : w0) et b = (moitie ? 2 : 18) + 2j, la fenêtre
// vaut ((lo >> (b - 1)) >> 1 | w1 << (32 - b)) & 0xffff pour tout b de 2 à 32 (le double
// décalage évite le décalage de 32, réduit modulo 32 en WGSL ; pour moitie = 1, w1 << (32 - b)
// n'a pas de bit sous le 16e car 32 - b >= 16).
const DECODE_TREILLIS_V2: &str = r#"
        let lo = select(w0, w1, moitie == 1u);
        let b0 = select(18u, 2u, moitie == 1u);
        let ba = vec4<u32>(b0, b0 + 2u, b0 + 4u, b0 + 6u);
        let bb = ba + vec4<u32>(8u);
        let ea = (((vec4<u32>(lo) >> (ba - vec4<u32>(1u))) >> vec4<u32>(1u)) | (vec4<u32>(w1) << (vec4<u32>(32u) - ba))) & vec4<u32>(0xffffu);
        let eb = (((vec4<u32>(lo) >> (bb - vec4<u32>(1u))) >> vec4<u32>(1u)) | (vec4<u32>(w1) << (vec4<u32>(32u) - bb))) & vec4<u32>(0xffffu);
        let va = mul1v(ea);
        let vb = mul1v(eb);
"#;
// Passe 5 : code linéaire par parités, sans multiplication (outils/quant-mse-xor.py). Même
// extraction que la passe 4 ; l'index j de chaque fenêtre e est la somme des parité(e & m_q) * 2^q,
// la valeur est pal[j], palette de 16 quantiles gaussiens copiée en mémoire partagée.
const DECODE_PARITE: &str = r#"
        let lo = select(w0, w1, moitie == 1u);
        let b0 = select(18u, 2u, moitie == 1u);
        let ba = vec4<u32>(b0, b0 + 2u, b0 + 4u, b0 + 6u);
        let bb = ba + vec4<u32>(8u);
        let ea = (((vec4<u32>(lo) >> (ba - vec4<u32>(1u))) >> vec4<u32>(1u)) | (vec4<u32>(w1) << (vec4<u32>(32u) - ba))) & vec4<u32>(0xffffu);
        let eb = (((vec4<u32>(lo) >> (bb - vec4<u32>(1u))) >> vec4<u32>(1u)) | (vec4<u32>(w1) << (vec4<u32>(32u) - bb))) & vec4<u32>(0xffffu);
        let ja = indice_parite(ea);
        let jb = indice_parite(eb);
        let va = vec4<f32>(pal[ja.x], pal[ja.y], pal[ja.z], pal[ja.w]);
        let vb = vec4<f32>(pal[jb.x], pal[jb.y], pal[jb.z], pal[jb.w]);
"#;
// Variante sans table : palette uniforme, valeur = 2j - 15 (une somme de ±2^q sur les
// parités), convertie et mise à l'échelle sans lecture de mémoire partagée.
const DECODE_PARITE_UNIF: &str = r#"
        let lo = select(w0, w1, moitie == 1u);
        let b0 = select(18u, 2u, moitie == 1u);
        let ba = vec4<u32>(b0, b0 + 2u, b0 + 4u, b0 + 6u);
        let bb = ba + vec4<u32>(8u);
        let ea = (((vec4<u32>(lo) >> (ba - vec4<u32>(1u))) >> vec4<u32>(1u)) | (vec4<u32>(w1) << (vec4<u32>(32u) - ba))) & vec4<u32>(0xffffu);
        let eb = (((vec4<u32>(lo) >> (bb - vec4<u32>(1u))) >> vec4<u32>(1u)) | (vec4<u32>(w1) << (vec4<u32>(32u) - bb))) & vec4<u32>(0xffffu);
        let va = (vec4<f32>(indice_parite(ea)) * 2.0 - vec4<f32>(15.0)) * ECH_UNIF;
        let vb = (vec4<f32>(indice_parite(eb)) * 2.0 - vec4<f32>(15.0)) * ECH_UNIF;
"#;
const ENTETE_PARITE: &str = r#"
var<workgroup> pal: array<f32, 16>;
const PALETTE = array<f32, 16>(PALVALS);
fn indice_parite(e: vec4<u32>) -> vec4<u32> {
    let u = vec4<u32>(1u);
    return (countOneBits(e & vec4<u32>(M0u)) & u)
        | ((countOneBits(e & vec4<u32>(M1u)) & u) << u)
        | ((countOneBits(e & vec4<u32>(M2u)) & u) << vec4<u32>(2u))
        | ((countOneBits(e & vec4<u32>(M3u)) & u) << vec4<u32>(3u));
}
"#;
const DECODE_TREILLIS: &str = r#"
        let o = 18u + 16u * moitie;
        let va = mul1v(fenetre4(w0, w1, vec4<u32>(o, o + 2u, o + 4u, o + 6u)));
        let vb = mul1v(fenetre4(w0, w1, vec4<u32>(o + 8u, o + 10u, o + 12u, o + 14u)));
"#;

const CORPS_4B: &str = r#"
var<workgroup> part4: array<vec4<f32>, 256>;
fn part_ligne4(t: u32, voie: u32, xa: vec4<f32>, xb: vec4<f32>) -> f32 {
    let w = q[t + voie];
    let n = vec4<f32>(vec4<u32>(w, w >> 8u, w >> 16u, w >> 24u) & vec4<u32>(15u)) - vec4<f32>(7.5);
    let h = vec4<f32>(vec4<u32>(w >> 4u, w >> 12u, w >> 20u, w >> 28u) & vec4<u32>(15u)) - vec4<f32>(7.5);
    return dot(vec4<f32>(n.x, h.x, n.y, h.y), xa) + dot(vec4<f32>(n.z, h.z, n.w, h.w), xb);
}
@compute @workgroup_size(256)
fn main(@builtin(workgroup_id) wg: vec3<u32>, @builtin(local_invocation_index) li: u32) {
    let voie = li & 31u;
    let l0 = (wg.x * 8u + (li >> 5u)) * 4u;
    let pas = TUILES * 32u;
    var acc = vec4<f32>(0.0);
    for (var tu = 0u; tu < TUILES; tu++) {
        let xi = (tu * 256u + 8u * voie) / 4u;
        let xa = x[xi];
        let xb = x[xi + 1u];
        let t = l0 * pas + tu * 32u;
        acc.x += part_ligne4(t, voie, xa, xb);
        acc.y += part_ligne4(t + pas, voie, xa, xb);
        acc.z += part_ligne4(t + 2u * pas, voie, xa, xb);
        acc.w += part_ligne4(t + 3u * pas, voie, xa, xb);
    }
    part4[li] = acc;
    workgroupBarrier();
    for (var o = 16u; o > 0u; o >>= 1u) {
        if (voie < o) { part4[li] += part4[li + o]; }
        workgroupBarrier();
    }
    if (voie == 0u) {
        let r = part4[li] * 0.02;
        y[l0] = r.x; y[l0 + 1u] = r.y; y[l0 + 2u] = r.z; y[l0 + 3u] = r.w;
    }
}
"#;

const LECTURE: &str = r#"
@group(0) @binding(0) var<storage, read> q: array<vec4<u32>>;
@group(0) @binding(1) var<storage, read_write> part: array<u32>;
@compute @workgroup_size(256)
fn main(@builtin(global_invocation_id) gid: vec3<u32>, @builtin(num_workgroups) nw: vec3<u32>) {
    let total = nw.x * 256u;
    let n = arrayLength(&q);
    var acc = vec4<u32>(0u);
    for (var i = gid.x; i < n; i += total) { acc += q[i]; }
    part[gid.x] = acc.x + acc.y + acc.z + acc.w;
}
"#;

struct Gpu {
    device: wgpu::Device,
    queue: wgpu::Queue,
    info: wgpu::AdapterInfo,
    horodatage: bool,
}

fn ouvrir(api: &str) -> Gpu {
    let b = match api {
        "vulkan" => wgpu::Backends::VULKAN,
        "dx12" => wgpu::Backends::DX12,
        _ => panic!("--api vulkan|dx12"),
    };
    let mut d = wgpu::InstanceDescriptor::new_without_display_handle();
    d.backends = b;
    let inst = wgpu::Instance::new(d);
    let adapter = pollster::block_on(inst.enumerate_adapters(b))
        .into_iter()
        .find(|a| a.get_info().vendor == 0x10DE)
        .expect("aucun adaptateur NVIDIA");
    let voulues = wgpu::Features::TIMESTAMP_QUERY;
    let features = adapter.features() & voulues;
    let limites = adapter.limits();
    let (device, queue) = pollster::block_on(adapter.request_device(&wgpu::DeviceDescriptor {
        label: Some("quant-vulkan-gemv"),
        required_features: features,
        required_limits: limites,
        ..Default::default()
    }))
    .expect("request_device");
    Gpu { device, queue, info: adapter.get_info(), horodatage: features.contains(wgpu::Features::TIMESTAMP_QUERY) }
}

fn attendre(g: &Gpu) {
    g.device.poll(wgpu::PollType::wait_indefinitely()).expect("poll");
}

fn tampon_init(g: &Gpu, octets: &[u8], usage: wgpu::BufferUsages) -> wgpu::Buffer {
    let b = g.device.create_buffer(&wgpu::BufferDescriptor {
        label: None,
        size: octets.len() as u64,
        usage: usage | wgpu::BufferUsages::COPY_DST,
        mapped_at_creation: false,
    });
    g.queue.write_buffer(&b, 0, octets);
    b
}

fn lire(g: &Gpu, src: &wgpu::Buffer, taille: u64) -> Vec<u8> {
    let lu = g.device.create_buffer(&wgpu::BufferDescriptor {
        label: None,
        size: taille,
        usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
        mapped_at_creation: false,
    });
    let mut enc = g.device.create_command_encoder(&Default::default());
    enc.copy_buffer_to_buffer(src, 0, &lu, 0, taille);
    g.queue.submit([enc.finish()]);
    let s = lu.slice(..);
    s.map_async(wgpu::MapMode::Read, |r| r.expect("map_async"));
    attendre(g);
    let v = s.get_mapped_range().expect("get_mapped_range").to_vec();
    v
}

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

fn groupe(g: &Gpu, p: &wgpu::ComputePipeline, t: &[&wgpu::Buffer]) -> wgpu::BindGroup {
    let e: Vec<wgpu::BindGroupEntry> = t
        .iter()
        .enumerate()
        .map(|(i, b)| wgpu::BindGroupEntry { binding: i as u32, resource: b.as_entire_binding() })
        .collect();
    g.device.create_bind_group(&wgpu::BindGroupDescriptor { label: None, layout: &p.get_bind_group_layout(0), entries: &e })
}

/// `reps` dispatches dans une passe ; rend le temps par dispatch (carte si horodatage, sinon mur).
fn chrono(g: &Gpu, p: &wgpu::ComputePipeline, bg: &wgpu::BindGroup, groupes: u32, reps: usize) -> f64 {
    let qs = g.horodatage.then(|| {
        g.device.create_query_set(&wgpu::QuerySetDescriptor { label: None, ty: wgpu::QueryType::Timestamp, count: 2 })
    });
    let res = g.device.create_buffer(&wgpu::BufferDescriptor {
        label: None,
        size: 16,
        usage: wgpu::BufferUsages::QUERY_RESOLVE | wgpu::BufferUsages::COPY_SRC,
        mapped_at_creation: false,
    });
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
    }
    let cb = enc.finish();
    attendre(g);
    let t0 = Instant::now();
    g.queue.submit([cb]);
    attendre(g);
    let mur = t0.elapsed().as_secs_f64();
    if qs.is_some() {
        let v = lire(g, &res, 16);
        let a = u64::from_le_bytes(v[0..8].try_into().unwrap());
        let b = u64::from_le_bytes(v[8..16].try_into().unwrap());
        b.wrapping_sub(a) as f64 * g.queue.get_timestamp_period() as f64 * 1e-9 / reps as f64
    } else {
        mur / reps as f64
    }
}

struct Alea(u64);
impl Alea {
    fn u32(&mut self) -> u32 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        (self.0 >> 16) as u32
    }
    fn normal(&mut self) -> f32 {
        let u1 = (self.u32() as f64 + 1.0) / 4294967297.0;
        let u2 = self.u32() as f64 / 4294967296.0;
        ((-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos()) as f32
    }
}

fn mul1_hote(e: u32, mul: u32) -> f64 {
    let v = e.wrapping_mul(mul);
    let s = (v & 0xff) + ((v >> 8) & 0xff) + ((v >> 16) & 0xff) + (v >> 24);
    ((s as f32 - 510.0) * (1.0 / 147.7)) as f64
}

fn parite_hote(e: u32, masques: &[u32; 4], palette: &[f32; 16]) -> f64 {
    let mut j = 0usize;
    for (q, m) in masques.iter().enumerate() {
        j |= (((e & m).count_ones() & 1) as usize) << q;
    }
    palette[j] as f64
}

/// 16 quantiles gaussiens centrés, inverse de Phi en (j + 1/2)/16, renormalisés à
/// l'écart-type 1 (même construction que quant-mse-xor.py), par bissection.
fn palette_quantiles() -> [f32; 16] {
    fn erf(x: f64) -> f64 {
        // Série de Taylor (convergente pour tout x, précise ici car |x| < 2,5).
        let mut s = 0.0;
        let mut t = x;
        let mut n = 0.0;
        while n < 200.0 {
            s += t / (2.0 * n + 1.0);
            n += 1.0;
            t *= -x * x / n;
            if t.abs() < 1e-18 { break; }
        }
        2.0 / std::f64::consts::PI.sqrt() * s
    }
    let phi = |x: f64| 0.5 * (1.0 + erf(x / std::f64::consts::SQRT_2));
    let mut p = [0f64; 16];
    for j in 0..16 {
        let cible = (j as f64 + 0.5) / 16.0;
        let (mut lo, mut hi) = (-5.0f64, 5.0f64);
        for _ in 0..100 {
            let mi = 0.5 * (lo + hi);
            if phi(mi) < cible { lo = mi } else { hi = mi }
        }
        p[j] = 0.5 * (lo + hi);
    }
    let moy = p.iter().sum::<f64>() / 16.0;
    let et = (p.iter().map(|v| (v - moy) * (v - moy)).sum::<f64>() / 16.0).sqrt();
    let mut r = [0f32; 16];
    for j in 0..16 { r[j] = ((p[j] - moy) / et) as f32; }
    r
}

fn etat(t: &[u32], p: usize) -> u32 {
    let debut = ((p + 1) * 2 + 512 - 16) & 511;
    let (i0, s) = (debut >> 5, debut & 31);
    let deux = ((t[(i0 + 1) & 15] as u64) << 32) | t[i0] as u64;
    ((deux >> s) & 0xffff) as u32
}

fn ref_ligne(fmt: &str, q: &[u32], x: &[f32], l: usize, mul: u32, masques: &[u32; 4], palette: &[f32; 16]) -> f64 {
    let mut acc = 0f64;
    for tu in 0..TUILES {
        for p in 0..256 {
            let v = match fmt {
                "scalaire-2b" => {
                    let t = &q[(l * TUILES + tu) * 16..][..16];
                    ((t[p >> 4] >> ((p & 15) * 2)) & 3) as f64 - 1.5
                }
                "scalaire-4b" => {
                    let t = &q[(l * TUILES + tu) * 32..][..32];
                    ((t[p >> 3] >> ((p & 7) * 4)) & 15) as f64 - 7.5
                }
                "parite" | "parite-unif" => parite_hote(etat(&q[(l * TUILES + tu) * 16..][..16], p), masques, palette),
                _ => mul1_hote(etat(&q[(l * TUILES + tu) * 16..][..16], p), mul),
            };
            acc += v * x[tu * 256 + p] as f64;
        }
    }
    acc * ECH as f64
}

fn octets_u32(v: &[u32]) -> Vec<u8> {
    v.iter().flat_map(|w| w.to_le_bytes()).collect()
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let val = |n: &str, d: &str| -> String {
        args.iter().position(|a| a == n).and_then(|i| args.get(i + 1).cloned()).unwrap_or(d.to_string())
    };
    let api = val("--api", "vulkan");
    let casser = args.iter().any(|a| a == "--casser");
    let series: usize = val("--series", "3").parse().unwrap();
    let reps: usize = val("--reps", "50").parse().unwrap();
    // Masques du code par parités : ceux retenus par quant-mse-xor.py (journal mse-xor-P4.json).
    let masques: [u32; 4] = {
        let v: Vec<u32> = val("--masques", "0x81d4,0x25a9,0x3df,0x3389")
            .split(',')
            .map(|h| u32::from_str_radix(h.trim_start_matches("0x"), 16).expect("--masques"))
            .collect();
        [v[0], v[1], v[2], v[3]]
    };
    let palette = palette_quantiles();
    let seulement = val("--formats", "");
    let g = ouvrir(&api);

    let mut r = Alea(0x9E37_79B9_7F4A_7C15);
    let q2: Vec<u32> = (0..M * K / 16).map(|_| r.u32()).collect();
    let q4: Vec<u32> = (0..M * K / 8).map(|_| r.u32()).collect();
    let x: Vec<f32> = (0..K).map(|_| r.normal()).collect();
    let xo: Vec<u8> = x.iter().flat_map(|f| f.to_le_bytes()).collect();
    let st = wgpu::BufferUsages::STORAGE;
    let bq2 = tampon_init(&g, &octets_u32(&q2), st);
    let bq4 = tampon_init(&g, &octets_u32(&q4), st);
    let bx = tampon_init(&g, &xo, st);
    let by = g.device.create_buffer(&wgpu::BufferDescriptor {
        label: None,
        size: (M * 4) as u64,
        usage: st | wgpu::BufferUsages::COPY_SRC,
        mapped_at_creation: false,
    });
    let bpart = g.device.create_buffer(&wgpu::BufferDescriptor {
        label: None,
        size: 4 * 256 * 1024,
        usage: st,
        mapped_at_creation: false,
    });

    let src = |decode: &str, somme: &str| {
        let sv = if somme.starts_with("dot4") {
            "vec4<u32>(dot4U8Packed(v.x, 0x01010101u), dot4U8Packed(v.y, 0x01010101u), dot4U8Packed(v.z, 0x01010101u), dot4U8Packed(v.w, 0x01010101u))"
        } else {
            "(v & vec4<u32>(0xffu)) + ((v >> vec4<u32>(8u)) & vec4<u32>(0xffu)) + ((v >> vec4<u32>(16u)) & vec4<u32>(0xffu)) + (v >> vec4<u32>(24u))"
        };
        let parite = decode.contains("indice_parite");
        let unif = decode.contains("ECH_UNIF");
        let entete = if parite {
            let pv: Vec<String> = palette.iter().map(|v| format!("{:.8}", v)).collect();
            ENTETE_PARITE
                .replace("PALVALS", &pv.join(", "))
                .replace("M0u", &format!("{}u", masques[0]))
                .replace("M1u", &format!("{}u", masques[1]))
                .replace("M2u", &format!("{}u", masques[2]))
                .replace("M3u", &format!("{}u", masques[3]))
        } else {
            String::new()
        };
        let charge = if parite && !unif { "if (li < 16u) { pal[li] = PALETTE[li]; }\n    workgroupBarrier();" } else { "" };
        format!("{}{}{}", ENTETE.replace("SOMMEV", sv).replace("SOMME", somme), entete,
            CORPS_2B.replace("DECODE", decode).replace("CHARGE_PALETTE", charge).replace("ECH_UNIF", &format!("{:.8}", ECH_UNIF)))
    };
    let formats: Vec<(&str, String, &wgpu::Buffer, f64)> = vec![
        ("scalaire-2b", src(DECODE_SCALAIRE, "somme_main(v)"), &bq2, (M * K / 4) as f64),
        ("treillis-mul1-main", src(DECODE_TREILLIS, "somme_main(v)"), &bq2, (M * K / 4) as f64),
        ("treillis-mul1-dot4", src(DECODE_TREILLIS, "dot4U8Packed(v, 0x01010101u)"), &bq2, (M * K / 4) as f64),
        ("treillis-mul1-dot4-v2", src(DECODE_TREILLIS_V2, "dot4U8Packed(v, 0x01010101u)"), &bq2, (M * K / 4) as f64),
        ("treillis-parite", src(DECODE_PARITE, "somme_main(v)"), &bq2, (M * K / 4) as f64),
        ("treillis-parite-unif", src(DECODE_PARITE_UNIF, "somme_main(v)"), &bq2, (M * K / 4) as f64),
        ("scalaire-4b", format!("{}{}", ENTETE.replace("SOMMEV", "v").replace("SOMME", "somme_main(v)"), CORPS_4B), &bq4, (M * K / 2) as f64),
    ];
    let mut pipes = Vec::new();
    for (nom, wgsl, bq, oct) in formats.iter().filter(|f| {
        seulement.is_empty() || f.0 == "scalaire-2b" || seulement.split(',').any(|s| s == f.0)
    }) {
        let p = pipeline(&g, wgsl);
        let bg = groupe(&g, &p, &[bq, &bx, &by]);
        pipes.push((*nom, p, bg, *oct));
    }
    let pl = pipeline(&g, LECTURE);
    let bgl = groupe(&g, &pl, &[&bq2, &bpart]);

    println!("{{\n \"outil\": \"quant-vulkan-gemv\", \"api\": \"{}\", \"adaptateur\": \"{}\", \"pilote\": \"{} {}\",",
        api, g.info.name, g.info.driver, g.info.driver_info);
    println!(" \"M\": {}, \"K\": {}, \"horodatage_carte\": {}, \"casser\": {},", M, K, g.horodatage, casser);
    println!(" \"temoins\": [");
    let mut tout = true;
    for (k, (nom, p, bg, _)) in pipes.iter().enumerate() {
        chrono(&g, p, bg, (M / 32) as u32, 1);
        let yb = lire(&g, &by, (M * 4) as u64);
        let yv: Vec<f32> = yb.chunks_exact(4).map(|c| f32::from_le_bytes(c.try_into().unwrap())).collect();
        let q = if nom.contains("4b") { &q4 } else { &q2 };
        let fmt = if *nom == "treillis-parite-unif" { "parite-unif" } else if *nom == "treillis-parite" { "parite" } else if nom.starts_with("treillis") { "treillis" } else { nom };
        let mut pire = 0f64;
        for i in 0..64usize {
            let l = (i as u64 * 2654435761 % M as u64) as usize;
            let mut pal_ref = if fmt == "parite-unif" {
                let mut pu = [0f32; 16];
                for j in 0..16 { pu[j] = (2.0 * j as f32 - 15.0) * ECH_UNIF; }
                pu
            } else {
                palette
            };
            if casser { pal_ref[0] += 0.5; }
            let rr = ref_ligne(fmt, q, &x, l, if casser { MUL1 + 2 } else { MUL1 }, &masques, &pal_ref);
            let e = (yv[l] as f64 - rr).abs() / (rr.abs() + 1e-3 * (K as f64).sqrt() * ECH as f64);
            pire = pire.max(e);
        }
        let ok = pire < 1e-3;
        tout &= ok;
        println!("  {{\"format\": \"{}\", \"erreur_relative_max\": {:.3e}, \"tient\": {}}}{}", nom, pire, ok,
            if k + 1 < pipes.len() { "," } else { "" });
    }
    println!(" ],\n \"temoin\": \"{}\",", if tout { "tient" } else { "TOMBE" });
    if casser || !tout {
        println!(" \"mesures\": []\n}}");
        std::process::exit(if tout { 0 } else { 2 });
    }
    let groupes_l = 1024u32;
    println!(" \"repetitions\": {}, \"mesures\": [", reps);
    let mut premier = true;
    let mut ecrire = |s: usize, nom: &str, role: &str, sec: f64, oct: f64| {
        print!("{}  {{\"serie\": {}, \"format\": \"{}\", \"role\": \"{}\", \"ms\": {:.4}, \"go_s\": {:.1}}}",
            if premier { "" } else { ",\n" }, s, nom, role, sec * 1e3, oct / sec / 1e9);
        premier = false;
    };
    for s in 0..series {
        for b in 1..pipes.len() {
            for (role, k) in [("A", 0usize), ("B", b), ("B", b), ("A", 0)] {
                let (nom, p, bg, oct) = &pipes[k];
                let t = chrono(&g, p, bg, (M / 32) as u32, reps);
                ecrire(s, nom, role, t, *oct);
            }
        }
        let t = chrono(&g, &pl, &bgl, groupes_l, reps);
        ecrire(s, "lecture-seule", "plafond", t, (M * K / 4) as f64);
    }
    println!("\n ]\n}}");
}
