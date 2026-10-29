//! Témoins synthétiques des noyaux de K3 sur la carte (réponses connues d'avance, sans GGUF), par le
//! chemin du moteur : image embarquée, API du pilote, enveloppes de `Noyaux`.
//!
//! Le témoin de K3 qui fait foi (poids réels, contre `trc-reference`) est
//! `mesures/moteur/K/temoin-k3/` ; ces tests en gardent l'essentiel sous `cargo test`, pour qu'une
//! modification d'un noyau ne passe pas inaperçue : produits exacts au bit sur entiers, arrondi f16
//! au plus proche pair, égalités du routeur et de l'argmax, puits de l'attention et anneau,
//! combinaison sans fma, bornes de SwiGLU, rotation à la position 0.

use trc_cuda::{Contexte, Flux, HoteEpingle, MemoireCarte, copier_vers_carte, copier_vers_hote};
use trc_noyaux::Noyaux;
use trc_noyaux::abi::{ParamsAttention, ParamsRope};

struct Banc {
    c: Contexte,
    f: Flux,
    k: Noyaux,
}

impl Banc {
    fn nouveau() -> Banc {
        let c = Contexte::nouveau(0).expect("contexte CUDA");
        let f = Flux::nouveau(&c, false).unwrap();
        let k = Noyaux::charger(&c).expect("chargement de l'image des noyaux");
        Banc { c, f, k }
    }
    fn monter(&self, o: &[u8]) -> MemoireCarte {
        let mut h = HoteEpingle::allouer(&self.c, o.len(), false).unwrap();
        h.tranche_mut()[..o.len()].copy_from_slice(o);
        let m = MemoireCarte::allouer(&self.c, o.len()).unwrap();
        copier_vers_carte(m.tout(), &h, 0, o.len(), &self.f).unwrap();
        self.f.synchroniser().unwrap();
        m
    }
    fn monter_f32(&self, v: &[f32]) -> MemoireCarte {
        self.monter(&v.iter().flat_map(|x| x.to_le_bytes()).collect::<Vec<u8>>())
    }
    fn zeros(&self, octets: usize) -> MemoireCarte {
        let m = MemoireCarte::allouer(&self.c, octets).unwrap();
        m.remplir(m.tout(), 0, &self.f).unwrap();
        m
    }
    fn descendre(&self, m: &MemoireCarte) -> Vec<u8> {
        self.f.synchroniser().unwrap();
        let mut h = HoteEpingle::allouer(&self.c, m.octets(), false).unwrap();
        copier_vers_hote(&mut h, 0, m.tout(), &self.f).unwrap();
        self.f.synchroniser().unwrap();
        h.tranche()[..m.octets()].to_vec()
    }
    fn descendre_f32(&self, m: &MemoireCarte) -> Vec<f32> {
        self.descendre(m).chunks_exact(4).map(|c| f32::from_le_bytes(c.try_into().unwrap())).collect()
    }
    fn descendre_u32(&self, m: &MemoireCarte) -> Vec<u32> {
        self.descendre(m).chunks_exact(4).map(|c| u32::from_le_bytes(c.try_into().unwrap())).collect()
    }
}

struct Alea(u64);
impl Alea {
    fn suivant(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    fn entre(&mut self, a: i64, b: i64) -> i64 {
        a + (self.suivant() % ((b - a + 1) as u64)) as i64
    }
}

/// Bits f16 de 2^e (e de −14 à 15, nombres normaux).
fn f16_puissance(e: i32) -> u16 {
    ((e + 15) as u16) << 10
}

fn ecart(y: &[f32], r: &[f64]) -> f64 {
    let num = y.iter().zip(r).map(|(a, b)| (*a as f64 - b).abs()).fold(0.0, f64::max);
    let den = r.iter().map(|b| b.abs()).fold(0.0, f64::max);
    num / den
}

#[test]
fn produits_q8_0_et_f32_exacts_au_bit_sur_entiers() {
    let b = Banc::nouveau();
    let mut a = Alea(31);
    // Q8_0 : d = 2^e, e ∈ [−2, 1] ; q ∈ [−127, 127] ; x ∈ {−1, 0, 1} : sommes exactes en f32.
    for (r, c) in [(37usize, 96usize), (2880, 4096)] {
        let nb = c / 32;
        let mut o = vec![0u8; r * nb * 34];
        let mut attendu = vec![0f64; r];
        let x: Vec<f32> = (0..c).map(|_| a.entre(-1, 1) as f32).collect();
        let biais: Vec<f32> = (0..r).map(|_| a.entre(-9, 9) as f32).collect();
        for i in 0..r {
            for j in 0..nb {
                let e = a.entre(-2, 1) as i32;
                let blk = &mut o[(i * nb + j) * 34..(i * nb + j + 1) * 34];
                blk[0..2].copy_from_slice(&f16_puissance(e).to_le_bytes());
                for t in 0..32 {
                    let q = a.entre(-127, 127);
                    blk[2 + t] = q as i8 as u8;
                    attendu[i] += 2f64.powi(e) * q as f64 * x[j * 32 + t] as f64;
                }
            }
            attendu[i] += biais[i] as f64;
        }
        let (w, xv, bv, y) = (b.monter(&o), b.monter_f32(&x), b.monter_f32(&biais), b.zeros(4 * r));
        b.k.gemv_q8_0(w.tout(), xv.tout(), Some(bv.tout()), y.tout(), r as u32, c as u32, &b.f).unwrap();
        let yy = b.descendre_f32(&y);
        for i in 0..r {
            assert_eq!(yy[i].to_bits(), (attendu[i] as f32).to_bits(), "Q8_0 {r} × {c}, ligne {i}");
        }
    }
    // f32 : W, x ∈ [−8, 8] ; |Σ| ≤ 2 880 · 64 : exact.
    let (r, c) = (128usize, 2880usize);
    let w: Vec<f32> = (0..r * c).map(|_| a.entre(-8, 8) as f32).collect();
    let x: Vec<f32> = (0..c).map(|_| a.entre(-8, 8) as f32).collect();
    let (wv, xv, y) = (b.monter_f32(&w), b.monter_f32(&x), b.zeros(4 * r));
    b.k.gemv_f32(wv.tout(), xv.tout(), None, y.tout(), r as u32, c as u32, &b.f).unwrap();
    let yy = b.descendre_f32(&y);
    for i in 0..r {
        let s: f64 = (0..c).map(|t| w[i * c + t] as f64 * x[t] as f64).sum();
        assert_eq!(yy[i], s as f32, "f32, ligne {i}");
    }
}

#[test]
fn ligne_q8_0_exacte_et_ecrire_kv_au_plus_proche_pair() {
    let b = Banc::nouveau();
    let mut a = Alea(7);
    let (lignes, c) = (5usize, 64usize);
    let mut o = vec![0u8; lignes * 2 * 34];
    for blk in o.chunks_exact_mut(34) {
        blk[0..2].copy_from_slice(&f16_puissance(a.entre(-14, 15) as i32).to_le_bytes());
        for q in &mut blk[2..] {
            *q = a.entre(-128, 127) as i8 as u8;
        }
    }
    let w = b.monter(&o);
    let y = b.zeros(4 * c);
    for l in 0..lignes {
        b.k.ligne_q8_0(w.tout(), l as u32, c as u32, y.tout(), &b.f).unwrap();
        let yy = b.descendre_f32(&y);
        for i in 0..c {
            let blk = &o[(l * 2 + i / 32) * 34..];
            let e = (u16::from_le_bytes([blk[0], blk[1]]) >> 10) as i32 - 15;
            assert_eq!(yy[i], 2f32.powi(e) * (blk[2 + i % 32] as i8) as f32, "ligne {l}, élément {i}");
        }
    }
    // f16 : exacts, puis égalités départagées vers le pair (1 + 2^-11 → 1 ; 1 + 3·2^-11 → 1 + 2^-9).
    let k = [1.0f32, -2.5, 0.0, 65504.0, 1.0 + 2f32.powi(-11), 1.0 + 3.0 * 2f32.powi(-11), -0.0, 6.1035156e-5];
    let attendu: [u16; 8] = [0x3C00, 0xC100, 0x0000, 0x7BFF, 0x3C00, 0x3C02, 0x8000, 0x0400];
    let (kv, cache_k, cache_v) = (b.monter_f32(&k), b.zeros(2 * 8 * 3), b.zeros(2 * 8 * 3));
    b.k.ecrire_kv(kv.tout(), kv.tout(), cache_k.tout(), cache_v.tout(), 8, 2, &b.f).unwrap();
    let ck = b.descendre(&cache_k);
    for i in 0..8 {
        assert_eq!(u16::from_le_bytes([ck[32 + 2 * i], ck[33 + 2 * i]]), attendu[i], "f16 de {}", k[i]);
        assert_eq!(&ck[2 * i..2 * i + 2], &[0, 0], "case 0 intacte");
    }
}

#[test]
fn rmsnorm_rope_swiglu_contre_l_hote() {
    let b = Banc::nouveau();
    let mut a = Alea(11);
    let n = 2880usize;
    let x: Vec<f32> = (0..2 * n).map(|_| (a.entre(-1000, 1000) as f32) / 37.0).collect();
    let w: Vec<f32> = (0..n).map(|_| (a.entre(1, 300) as f32) / 100.0).collect();
    let (xv, wv, y) = (b.monter_f32(&x), b.monter_f32(&w), b.zeros(8 * n));
    b.k.rmsnorm(xv.tout(), wv.tout(), y.tout(), n as u32, 2, 1e-5, &b.f).unwrap();
    let yy = b.descendre_f32(&y);
    for l in 0..2 {
        let xs = &x[l * n..(l + 1) * n];
        let s: f64 = xs.iter().map(|v| (*v as f64).powi(2)).sum();
        let r = 1.0 / (s / n as f64 + 1e-5f32 as f64).sqrt();
        let attendu: Vec<f64> = (0..n).map(|i| xs[i] as f64 * r * w[i] as f64).collect();
        assert!(ecart(&yy[l * n..(l + 1) * n], &attendu) <= 1e-6);
    }
    // Rotation à la position 0 : cos = 1, sin = 0, chaque élément multiplié par la concentration.
    let q: Vec<f32> = (0..64 * 64).map(|_| (a.entre(-500, 500) as f32) / 64.0).collect();
    let k: Vec<f32> = (0..8 * 64).map(|_| (a.entre(-500, 500) as f32) / 64.0).collect();
    let (qv, kv) = (b.monter_f32(&q), b.monter_f32(&k));
    b.k.rope_yarn(qv.tout(), kv.tout(), 64, 8, 0, &ParamsRope::GPT_OSS, &b.f).unwrap();
    let m = 0.1 * 32f64.ln() + 1.0;
    let attendu: Vec<f64> = q.iter().map(|v| *v as f64 * m).collect();
    assert!(ecart(&b.descendre_f32(&qv), &attendu) <= 1e-6);
    // Sans YaRN (facteur 1) à la position 1 000 : inv_freq_i = θ^(−2i/d), contre l'hôte en f64.
    let p1 = ParamsRope { facteur: 1.0, ..ParamsRope::GPT_OSS };
    let kv2 = b.monter_f32(&k);
    let qv2 = b.monter_f32(&q[..64]);
    b.k.rope_yarn(qv2.tout(), kv2.tout(), 1, 8, 1000, &p1, &b.f).unwrap();
    let mut attendu = vec![0f64; 8 * 64];
    for h in 0..8 {
        for i in 0..32 {
            let ang = 1000.0 * 150000f64.powf(-((2 * i) as f64) / 64.0);
            let (s, c) = ang.sin_cos();
            let (x1, x2) = (k[h * 64 + i] as f64, k[h * 64 + i + 32] as f64);
            attendu[h * 64 + i] = x1 * c - x2 * s;
            attendu[h * 64 + i + 32] = x2 * c + x1 * s;
        }
    }
    assert!(ecart(&b.descendre_f32(&kv2), &attendu) <= 1e-6);
    // SwiGLU : g et u bornés à 7 (100 ↦ 7), contre l'hôte en f64.
    let g = [100.0f32, 7.0, -3.0, 0.0, 1.5];
    let u = [100.0f32, 7.0, -100.0, 5.0, -0.25];
    let (gv, uv, yv) = (b.monter_f32(&g), b.monter_f32(&u), b.zeros(20));
    b.k.swiglu_oai(gv.tout(), uv.tout(), yv.tout(), 5, &b.f).unwrap();
    let yy = b.descendre_f32(&yv);
    assert_eq!(yy[0].to_bits(), yy[1].to_bits(), "bornes : (100, 100) = (7, 7)");
    for i in 0..5 {
        let (gg, uu) = ((g[i] as f64).min(7.0), (u[i] as f64).clamp(-7.0, 7.0));
        let att = gg / (1.0 + (-1.702 * gg).exp()) * (uu + 1.0);
        assert!((yy[i] as f64 - att).abs() <= 1e-6 * att.abs().max(1e-30), "swiglu {i} : {} contre {att}", yy[i]);
    }
}

#[test]
fn attention_puits_et_anneau() {
    let b = Banc::nouveau();
    let dkv = 8 * 64;
    let un = 0x3C00u16; // 1.0 en f16
    // 1. Une clé, q = 0, puits 0 : poids 1/2 ; v = indice de la dimension.
    let mut ck = vec![0u16; 4096 * dkv];
    let mut cv = vec![0u16; 4096 * dkv];
    let f16_entier = |n: u32| -> u16 { if n == 0 { 0 } else { let e = 31 - n.leading_zeros(); (((e + 15) << 10) | ((n << (10 - e)) & 0x3FF)) as u16 } };
    for t in 0..64 {
        for h in 0..8 {
            cv[h * 64 + t] = f16_entier(t as u32);
            ck[h * 64 + t] = un;
        }
    }
    let monter16 = |v: &[u16]| b.monter(&v.iter().flat_map(|x| x.to_le_bytes()).collect::<Vec<u8>>());
    let (k1, v1) = (monter16(&ck), monter16(&cv));
    let q = b.monter_f32(&vec![0f32; 64 * 64]);
    let puits = b.monter_f32(&vec![0f32; 64]);
    let s = b.zeros(4 * 64 * 64);
    b.k.attention(q.tout(), k1.tout(), v1.tout(), puits.tout(), s.tout(), &ParamsAttention::gpt_oss(0, 0), &b.f).unwrap();
    let o = b.descendre_f32(&s);
    for h in 0..64 {
        for t in 0..64 {
            assert!((o[h * 64 + t] - t as f32 / 2.0).abs() <= 1e-6 * t as f32, "une clé : tête {h}, dimension {t} : {}", o[h * 64 + t]);
        }
    }
    // 2. Anneau de 128 à la position 200 : la case s porte v = s (toutes dimensions) ; q = 0 et puits
    // −∞ : poids égaux sur les 128 positions 73 … 200, qui occupent les 128 cases : moyenne 63,5.
    let mut cv2 = vec![0u16; 128 * dkv];
    for s_ in 0..128 {
        for i in 0..dkv {
            cv2[s_ * dkv + i] = f16_entier(s_ as u32);
        }
    }
    let (k2, v2) = (monter16(&vec![un; 128 * dkv]), monter16(&cv2));
    let puits2 = b.monter_f32(&vec![f32::NEG_INFINITY; 64]);
    let p = ParamsAttention::gpt_oss(200, 128);
    assert_eq!((p.debut, p.fin), (73, 201));
    b.k.attention(q.tout(), k2.tout(), v2.tout(), puits2.tout(), s.tout(), &p, &b.f).unwrap();
    for v in b.descendre_f32(&s) {
        assert!((v - 63.5).abs() <= 1e-4, "anneau : {v}");
    }
    // 3. Cache plein, 4 096 positions, q = 0, puits −∞ : moyenne des v = position mod 2 048.
    for j in 0..4096 {
        for i in 0..dkv {
            cv[j * dkv + i] = f16_entier((j % 2048) as u32);
            ck[j * dkv + i] = un;
        }
    }
    let (k3, v3) = (monter16(&ck), monter16(&cv));
    b.k.attention(q.tout(), k3.tout(), v3.tout(), puits2.tout(), s.tout(), &ParamsAttention::gpt_oss(4095, 0), &b.f).unwrap();
    for v in b.descendre_f32(&s) {
        assert!((v - 1023.5).abs() <= 1e-2, "4 096 positions : {v}");
    }
}

#[test]
fn routeur_argmax_combiner() {
    let b = Banc::nouveau();
    // Routeur : égalités départagées par l'indice croissant ; boîte projetée au protocole E0 c.
    let l = [1.0f32, 3.0, 3.0, 0.0, 2.0, -1.0];
    let (lv, iv, pv) = (b.monter_f32(&l), b.zeros(16), b.zeros(16));
    let boite = HoteEpingle::allouer(&b.c, 4096, true).unwrap();
    b.k.routeur_topk(lv.tout(), 6, 4, iv.tout(), pv.tout(), boite.adresse_carte().unwrap(), 77, &b.f).unwrap();
    let idx = b.descendre_u32(&iv);
    assert_eq!(idx, vec![1, 2, 4, 0]);
    let e: Vec<f64> = [3.0f64, 3.0, 2.0, 1.0].iter().map(|v| (v - 3.0f64).exp()).collect();
    let z: f64 = e.iter().sum();
    let pw = b.descendre_f32(&pv);
    for i in 0..4 {
        assert_eq!(pw[i], (e[i] / z) as f32);
    }
    let mots: Vec<u32> = boite.tranche()[..36].chunks_exact(4).map(|c| u32::from_le_bytes(c.try_into().unwrap())).collect();
    assert_eq!(mots[0], 77);
    assert_eq!(&mots[1..5], &idx[..]);
    assert_eq!(mots[5..9].iter().map(|m| f32::from_bits(*m)).collect::<Vec<_>>(), pw);
    // Argmax : égalité → plus petit indice ; NaN jamais retenu.
    let mut v = vec![0f32; 100_000];
    v[0] = f32::NAN;
    v[70_000] = 5.0;
    v[12_345] = 5.0;
    let (vv, am) = (b.monter_f32(&v), b.zeros(4));
    b.k.argmax(vv.tout(), v.len() as u32, am.tout(), &b.f).unwrap();
    assert_eq!(b.descendre_u32(&am)[0], 12_345);
    // Combiner : égal au bit à la même somme sur l'hôte en f32, ordre j = 0..3, sans fma.
    let mut a = Alea(3);
    let d = 2880usize;
    let x: Vec<f32> = (0..d).map(|_| (a.suivant() as f64 / u64::MAX as f64 - 0.5) as f32 * 1e3).collect();
    let s: Vec<f32> = (0..4 * d).map(|_| (a.suivant() as f64 / u64::MAX as f64 - 0.5) as f32 * 7.0).collect();
    let w = [0.4123f32, 0.3001, 0.2, 0.0876];
    let (xv, sv, wv) = (b.monter_f32(&x), b.monter_f32(&s), b.monter_f32(&w));
    b.k.combiner(xv.tout(), sv.tout(), d as u32, Some(wv.tout()), 4, d as u32, &b.f).unwrap();
    let y = b.descendre_f32(&xv);
    for i in 0..d {
        let mut t = w[0] * s[i];
        for j in 1..4 {
            t += w[j] * s[j * d + i];
        }
        assert_eq!(y[i].to_bits(), (x[i] + t).to_bits(), "combiner, élément {i}");
    }
}

/// P3, routeur biaisé par le cache : `routeur_topk_biais` égale, indices et poids au bit, une version
/// écrite à part sur l'hôte (score = logit + biais en f32, choix par score décroissant puis indice
/// croissant, rendu par logit non biaisé décroissant puis indice croissant, poids = softmax f64 des
/// logits non biaisés) sur des tirages à égalités forcées (logits sur une grille de 0,25 ; E = 6, 32 et
/// 256 ; β = 0, 0,041, 0,3, 1 ; masques aléatoires). Avec un biais nul, il égale `routeur_topk` au bit.
/// Cassure : le même noyau avec le masque inversé ne donne pas la réponse de l'hôte (il doit différer
/// au moins une fois), et le biais fait bien changer au moins un ensemble.
fn oracle_biaise(l: &[f32], b: &[f32], k: usize) -> (Vec<u32>, Vec<f32>) {
    let mut ids: Vec<usize> = (0..l.len()).collect();
    ids.sort_by(|&x, &y| (l[y] + b[y]).partial_cmp(&(l[x] + b[x])).unwrap().then(x.cmp(&y)));
    ids.truncate(k);
    ids.sort_by(|&x, &y| l[y].partial_cmp(&l[x]).unwrap().then(x.cmp(&y)));
    let m = l[ids[0]] as f64;
    let e: Vec<f64> = ids.iter().map(|&i| (l[i] as f64 - m).exp()).collect();
    let z: f64 = e.iter().sum();
    (ids.iter().map(|&i| i as u32).collect(), e.iter().map(|v| (v / z) as f32).collect())
}

#[test]
fn routeur_biaise_egal_a_l_hote_et_au_noyau_sans_biais() {
    let bn = Banc::nouveau();
    let mut a = Alea(20261027);
    let (mut ensembles_changes, mut inverse_differe) = (0usize, 0usize);
    for essai in 0..160 {
        let e = [6usize, 32, 32, 256][essai % 4];
        let beta = [0.0f32, 0.041, 0.3, 1.0][(essai / 4) % 4];
        let l: Vec<f32> = (0..e).map(|_| a.entre(-40, 40) as f32 * 0.25).collect();
        let masque: Vec<bool> = (0..e).map(|_| a.suivant() & 1 == 1).collect();
        let b: Vec<f32> = masque.iter().map(|&m| if m { beta } else { 0.0 }).collect();
        let bi: Vec<f32> = masque.iter().map(|&m| if m { 0.0 } else { beta }).collect();
        let (lv, bv, biv) = (bn.monter_f32(&l), bn.monter_f32(&b), bn.monter_f32(&bi));
        let (iv, pv) = (bn.zeros(16), bn.zeros(16));
        bn.k.routeur_topk_biais(lv.tout(), bv.tout(), e as u32, 4, iv.tout(), pv.tout(), 0, 0, &bn.f).unwrap();
        let (idx, pw) = (bn.descendre_u32(&iv), bn.descendre_f32(&pv));
        let (oi, op) = oracle_biaise(&l, &b, 4);
        assert_eq!(idx[..4], oi[..], "essai {essai} (E = {e}, β = {beta}) : indices");
        for j in 0..4 {
            assert_eq!(pw[j].to_bits(), op[j].to_bits(), "essai {essai} : poids {j}");
        }
        // sans biais : égal au noyau d'origine
        let (i0, p0) = (bn.zeros(16), bn.zeros(16));
        let zero = bn.zeros(4 * e);
        bn.k.routeur_topk_biais(lv.tout(), zero.tout(), e as u32, 4, i0.tout(), p0.tout(), 0, 0, &bn.f).unwrap();
        let (j0, q0) = (bn.zeros(16), bn.zeros(16));
        bn.k.routeur_topk(lv.tout(), e as u32, 4, j0.tout(), q0.tout(), 0, 0, &bn.f).unwrap();
        assert_eq!(bn.descendre_u32(&i0)[..4], bn.descendre_u32(&j0)[..4], "essai {essai} : biais nul, indices");
        let (x, y) = (bn.descendre_f32(&p0), bn.descendre_f32(&q0));
        for j in 0..4 {
            assert_eq!(x[j].to_bits(), y[j].to_bits(), "essai {essai} : biais nul, poids {j}");
        }
        // le biais fait changer des ensembles ; la cassure (masque inversé) ne rend pas la réponse de l'hôte
        if beta > 0.0 {
            let (sans, _) = oracle_biaise(&l, &vec![0.0; e], 4);
            let (mut s1, mut s2) = (sans.clone(), oi.clone());
            s1.sort();
            s2.sort();
            if s1 != s2 {
                ensembles_changes += 1;
            }
            let (ic, pc) = (bn.zeros(16), bn.zeros(16));
            bn.k.routeur_topk_biais(lv.tout(), biv.tout(), e as u32, 4, ic.tout(), pc.tout(), 0, 0, &bn.f).unwrap();
            if bn.descendre_u32(&ic)[..4] != oi[..] {
                inverse_differe += 1;
            }
        }
    }
    assert!(ensembles_changes > 5, "le biais n'a changé que {ensembles_changes} ensembles : le test ne mord pas");
    assert!(inverse_differe > 5, "le masque inversé n'a différé que {inverse_differe} fois : la cassure ne tombe pas");
}

/// Essai de la ronde de corrections J1 (constat M5) : le cache KV en f32 (`ecrire_kv_f32`,
/// `attention_kvf32`) rend, **au bit**, la sortie du chemin f16 de la couture N quand les clés et
/// les valeurs sont exactement représentables en f16 (mêmes produits, même ordre : seule la mémoire
/// change) ; cassure : des valeurs non représentables font différer les deux chemins. Cache plein
/// (position 300) et anneau de 128 (position 300).
#[test]
fn kv_f32_egal_au_bit_au_chemin_f16_sur_valeurs_representables() {
    let b = Banc::nouveau();
    let dkv = 8 * 64usize;
    for (anneau, representable) in [(0u32, true), (128, true), (0, false)] {
        let mut a = Alea(20261016 + anneau as u64 + representable as u64);
        let position = 300u32;
        let cases = if anneau > 0 { anneau as usize } else { position as usize + 1 };
        let (c16k, c16v) = (b.zeros(2 * cases * dkv), b.zeros(2 * cases * dkv));
        let (c32k, c32v) = (b.zeros(4 * cases * dkv), b.zeros(4 * cases * dkv));
        for p in 0..=position {
            // m · 2^-8 avec |m| ≤ 1024 : exact en f16 (11 bits de mantisse) ; sinon un écart de 1e-3.
            let tirer = |a: &mut Alea| -> Vec<f32> {
                (0..dkv).map(|_| a.entre(-1024, 1024) as f32 / 256.0 + if representable { 0.0 } else { 1e-3 }).collect()
            };
            let (k, v) = (b.monter_f32(&tirer(&mut a)), b.monter_f32(&tirer(&mut a)));
            let case = ParamsAttention::case(p, anneau);
            b.k.ecrire_kv(k.tout(), v.tout(), c16k.tout(), c16v.tout(), dkv as u32, case, &b.f).unwrap();
            b.k.ecrire_kv_f32(k.tout(), v.tout(), c32k.tout(), c32v.tout(), dkv as u32, case, &b.f).unwrap();
            b.f.synchroniser().unwrap();
        }
        let q = b.monter_f32(&(0..64 * 64).map(|_| a.entre(-1000, 1000) as f32 / 333.0).collect::<Vec<_>>());
        let puits = b.monter_f32(&(0..64).map(|_| a.entre(-300, 300) as f32 / 100.0).collect::<Vec<_>>());
        let (s16, s32) = (b.zeros(4 * 64 * 64), b.zeros(4 * 64 * 64));
        let p = ParamsAttention::gpt_oss(position, anneau);
        b.k.attention(q.tout(), c16k.tout(), c16v.tout(), puits.tout(), s16.tout(), &p, &b.f).unwrap();
        b.k.attention_kvf32(q.tout(), c32k.tout(), c32v.tout(), puits.tout(), s32.tout(), &p, &b.f).unwrap();
        let (o16, o32) = (b.descendre_f32(&s16), b.descendre_f32(&s32));
        let differents = o16.iter().zip(&o32).filter(|(x, y)| x.to_bits() != y.to_bits()).count();
        if representable {
            assert_eq!(differents, 0, "anneau {anneau} : {differents} sorties différentes au bit");
        } else {
            assert!(differents > 0, "cassure : des valeurs non représentables devraient faire différer les chemins");
        }
    }
}
