//! Taux réel d'un codage MXFP4 par champs, sur tous les tenseurs MXFP4 d'un GGUF.
//!
//! Le bloc MXFP4 (32 poids, 17 octets) a deux champs : l'échelle E8M0 (1 octet) et les
//! codes (16 octets). Mesure d'entropie (mxfp4_contexte.py) : l'échelle porte 0,9 à 2,3
//! bits sur 8 à l'ordre 0, et environ 1 bit sachant la médiane des échelles de sa ligne.
//! D'où le format, décodable en parallèle sans dépendance d'un bloc à l'autre :
//!   - codes : rANS entrelacé, alphabet octet (décodeur v4 de la carte), une table par
//!     tenseur ;
//!   - échelles : la médiane de chaque ligne en clair (1 octet par ligne), puis
//!     δ = e − médiane + 128 (mod 256) par bloc, en rANS, alphabet octet, une table par
//!     tenseur. La reconstruction e = médiane + δ − 128 n'a besoin que de la ligne : aucune
//!     somme préfixe, contrairement à un codage par différence avec le voisin.
//!   - en-têtes : deux tables de 256 fréquences sur 12 bits par tenseur (768 octets),
//!     comptés.
//! Chaque tenseur est décodé sur le processeur et comparé octet à octet à l'original
//! (codes et échelles reconstruites) : le taux n'est publié que si le décodage est exact.
//! Témoin : une médiane de ligne faussée doit rendre la reconstruction inexacte.
//!
//! Option `--classes` : les codes sont aussi codés en trois flux selon la classe de
//! l'échelle de leur bloc (e < médiane, e = médiane, e > médiane), une table par flux. Cela
//! mesure ce que rend l'information mutuelle entre un code et son échelle (0,039 bit
//! d'après mxfp4_contexte.py), au prix de trois tables au lieu d'une. Le réassemblage des
//! blocs depuis les trois flux, guidé par δ, est vérifié octet à octet.
//!
//! Usage : taux_mxfp4 <fichier.gguf> <sortie.json> [--classes [--nb-classes 3|5|7]]

use rans_troncons::*;
use std::time::Instant;

fn histo(v: &[u8]) -> Vec<u64> {
    let mut h = vec![0u64; 256];
    for &o in v {
        h[o as usize] += 1;
    }
    h
}

fn entropie256(h: &[u64]) -> f64 {
    let t: u64 = h.iter().sum();
    h.iter().filter(|&&c| c > 0).map(|&c| { let p = c as f64 / t as f64; -p * p.log2() }).sum()
}

/// Code puis décode `source` (longueur multiple de 128) ; rend (octets codés, exact).
fn coder_verifier(source: &[u8], pool: &rayon::ThreadPool) -> (usize, bool, f64) {
    let h = histo(source);
    let table = Table256::depuis_comptes(&h);
    let flux = coder_octets(source, &table, 256);
    let mut sortie = vec![0u32; source.len() / 4];
    let echecs = decoder_tout_octets(&flux, &table.lut, &mut sortie, pool);
    let exact = echecs == 0 && bytemuck::cast_slice::<u32, u8>(&sortie) == source;
    (flux.octets_codes() + 384, exact, entropie256(&h))
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let chemin = &args[1];
    let sortie_json = &args[2];
    let pool = rayon::ThreadPoolBuilder::new().num_threads(16).build().unwrap();
    let avec_classes = args.iter().any(|a| a == "--classes");
    // --nb-classes N (impair, 3 par défaut) : classe = δ − 128 borné à ±(N − 1)/2.
    let nb_classes: usize = args.iter().position(|a| a == "--nb-classes").map(|i| args[i + 1].parse().unwrap()).unwrap_or(3);
    assert!(nb_classes % 2 == 1 && nb_classes >= 3);
    let demi = (nb_classes / 2) as i32;
    let classe = move |d: u8| -> usize { ((d as i32 - 128).clamp(-demi, demi) + demi) as usize };
    let mut tot_codes_cl = 0usize;
    let mut tout_exact_cl = true;
    let infos = lire_entete_gguf(chemin);
    let mut lignes_json = Vec::new();
    let (mut tot_stocke, mut tot_codes, mut tot_ech, mut tot_poids) = (0usize, 0usize, 0usize, 0usize);
    let mut tout_exact = true;
    let mut temoin_tombe = None;
    let t0 = Instant::now();
    // dimensions : relues dans l'en-tête par un second lecteur minimal (colonnes = ne0)
    let colonnes = lire_ne0(chemin);
    for t in infos.iter().filter(|t| t.type_ggml == 39) {
        let ne0 = *colonnes.get(&t.nom).expect("dimensions du tenseur") as usize;
        let blocs_ligne = ne0 / 32;
        let brut = lire_tenseur(chemin, t);
        let (ech, qs) = separer_blocs(39, &brut);
        let n_lignes = ech.len() / blocs_ligne;
        let mut medianes = Vec::with_capacity(n_lignes);
        let mut delta = Vec::with_capacity(ech.len());
        for ligne in ech.chunks_exact(blocs_ligne) {
            let mut tri = ligne.to_vec();
            tri.sort_unstable();
            let med = tri[tri.len() / 2];
            medianes.push(med);
            delta.extend(ligne.iter().map(|&e| e.wrapping_sub(med).wrapping_add(128)));
        }
        assert_eq!(qs.len() % 128, 0, "{}", t.nom);
        assert_eq!(delta.len() % 128, 0, "{}", t.nom);
        let (o_codes, ex_codes, h_codes) = coder_verifier(&qs, &pool);
        let (o_delta, ex_delta, h_delta) = coder_verifier(&delta, &pool);
        // reconstruction des échelles depuis médianes + δ décodés (ici : δ exact => e exact)
        let reconstruit: Vec<u8> = delta.chunks_exact(blocs_ligne).zip(&medianes)
            .flat_map(|(d, &m)| d.iter().map(move |&x| x.wrapping_sub(128).wrapping_add(m))).collect();
        let ex_ech = reconstruit == ech;
        if temoin_tombe.is_none() {
            // témoin : une médiane fausse doit casser la reconstruction
            let mut fausses = medianes.clone();
            fausses[0] = fausses[0].wrapping_add(1);
            let r2: Vec<u8> = delta.chunks_exact(blocs_ligne).zip(&fausses)
                .flat_map(|(d, &m)| d.iter().map(move |&x| x.wrapping_sub(128).wrapping_add(m))).collect();
            temoin_tombe = Some(r2 != ech);
        }
        // Codes en trois flux selon la classe de l'échelle du bloc.
        let mut o_codes_cl = 0usize;
        if avec_classes {
            let mut flux_cl: Vec<Vec<u8>> = vec![Vec::new(); nb_classes];
            for (b, &d) in delta.iter().enumerate() {
                let k = classe(d);
                flux_cl[k].extend_from_slice(&qs[b * 16..b * 16 + 16]);
            }
            // réassemblage guidé par δ, avant le bourrage
            let mut pos = vec![0usize; nb_classes];
            let mut ok = true;
            for (b, &d) in delta.iter().enumerate() {
                let k = classe(d);
                ok &= flux_cl[k][pos[k]..pos[k] + 16] == qs[b * 16..b * 16 + 16];
                pos[k] += 16;
            }
            for f in flux_cl.iter_mut() {
                if f.is_empty() {
                    continue;
                }
                f.resize(f.len().div_ceil(128) * 128, 0); // bourrage compté dans le taux
                let (o, ex, _) = coder_verifier(f, &pool);
                o_codes_cl += o;
                ok &= ex;
            }
            tout_exact_cl &= ok;
            tot_codes_cl += o_codes_cl;
        }
        let exact = ex_codes && ex_delta && ex_ech;
        tout_exact &= exact;
        let poids = t.nb_poids as usize;
        let o_ech = o_delta + medianes.len();
        tot_stocke += brut.len();
        tot_codes += o_codes;
        tot_ech += o_ech;
        tot_poids += poids;
        let bpp = |o: usize| o as f64 * 8.0 / poids as f64;
        eprintln!("{:30} codes {:.4} b/p (H {:.4} b/octet), échelles {:.4} b/p (H(δ) {:.3} b), total {:.4} / 4,25 -> taux {:.4}, exact {}{}",
            t.nom, bpp(o_codes), h_codes, bpp(o_ech), h_delta, bpp(o_codes + o_ech), brut.len() as f64 / (o_codes + o_ech) as f64, exact,
            if avec_classes { format!(" ; codes par classe {:.4} b/p", bpp(o_codes_cl)) } else { String::new() });
        lignes_json.push(format!(
            "    {{\"nom\": {:?}, \"poids\": {}, \"octets_stockes\": {}, \"octets_codes\": {}, \"octets_echelles\": {}, \"H_octet_codes\": {:.6}, \"H_delta_echelle\": {:.6}, \"bits_par_poids\": {:.6}, \"taux\": {:.6}, \"exact\": {}, \"octets_codes_par_classe\": {}}}",
            t.nom, poids, brut.len(), o_codes, o_ech, h_codes, h_delta, bpp(o_codes + o_ech), brut.len() as f64 / (o_codes + o_ech) as f64, exact, o_codes_cl));
    }
    let bpp = |o: usize| o as f64 * 8.0 / tot_poids as f64;
    eprintln!("TOTAL : codes {:.4} b/p, échelles {:.4} b/p, total {:.4} b/p sur 4,25 stockés, taux {:.4}, tout exact {}, témoin tombé {:?}, {:.0} s",
        bpp(tot_codes), bpp(tot_ech), bpp(tot_codes + tot_ech), tot_stocke as f64 / (tot_codes + tot_ech) as f64, tout_exact, temoin_tombe, t0.elapsed().as_secs_f64());
    if avec_classes {
        eprintln!("CLASSES : codes {:.4} b/p, total {:.4} b/p, taux {:.4}, exact {}",
            bpp(tot_codes_cl), bpp(tot_codes_cl + tot_ech), tot_stocke as f64 / (tot_codes_cl + tot_ech) as f64, tout_exact_cl);
    }
    let json = format!(
        "{{\n  \"fichier\": {:?},\n  \"poids\": {},\n  \"octets_stockes\": {},\n  \"octets_codes\": {},\n  \"octets_echelles\": {},\n  \"bits_par_poids_codes\": {:.6},\n  \"bits_par_poids_echelles\": {:.6},\n  \"bits_par_poids\": {:.6},\n  \"taux\": {:.6},\n  \"tout_exact\": {},\n  \"temoin_mediane_fausse_tombe\": {:?},\n  \"classes\": {},\n  \"bits_par_poids_codes_par_classe\": {:.6},\n  \"taux_avec_classes\": {:.6},\n  \"classes_exactes\": {},\n  \"tenseurs\": [\n{}\n  ]\n}}\n",
        chemin, tot_poids, tot_stocke, tot_codes, tot_ech, bpp(tot_codes), bpp(tot_ech), bpp(tot_codes + tot_ech),
        tot_stocke as f64 / (tot_codes + tot_ech) as f64, tout_exact, temoin_tombe.unwrap_or(false),
        if avec_classes { nb_classes } else { 0 }, bpp(tot_codes_cl), tot_stocke as f64 / (tot_codes_cl + tot_ech).max(1) as f64,
        avec_classes && tout_exact_cl, lignes_json.join(",\n"));
    std::fs::write(sortie_json, json).unwrap();
}

/// ne0 (nombre de colonnes) de chaque tenseur, relu dans l'en-tête GGUF.
fn lire_ne0(chemin: &str) -> std::collections::HashMap<String, u64> {
    use std::io::Read;
    let mut f = std::fs::File::open(chemin).unwrap();
    let mut b = vec![0u8; 32 << 20];
    let n = f.read(&mut b).unwrap();
    b.truncate(n);
    let u32_ = |b: &[u8], p: &mut usize| { let v = u32::from_le_bytes(b[*p..*p + 4].try_into().unwrap()); *p += 4; v };
    let u64_ = |b: &[u8], p: &mut usize| { let v = u64::from_le_bytes(b[*p..*p + 8].try_into().unwrap()); *p += 8; v };
    fn sauter(b: &[u8], p: &mut usize, t: u32) {
        let u32_ = |b: &[u8], p: &mut usize| { let v = u32::from_le_bytes(b[*p..*p + 4].try_into().unwrap()); *p += 4; v };
        let u64_ = |b: &[u8], p: &mut usize| { let v = u64::from_le_bytes(b[*p..*p + 8].try_into().unwrap()); *p += 8; v };
        match t {
            0 | 1 | 7 => *p += 1,
            2 | 3 => *p += 2,
            4 | 5 | 6 => *p += 4,
            10 | 11 | 12 => *p += 8,
            8 => { let n = u64_(b, p) as usize; *p += n; }
            9 => { let t2 = u32_(b, p); let n = u64_(b, p); for _ in 0..n { sauter(b, p, t2); } }
            _ => panic!("type {t}"),
        }
    }
    let mut p = 4;
    let _v = u32_(&b, &mut p);
    let nt = u64_(&b, &mut p);
    let nk = u64_(&b, &mut p);
    for _ in 0..nk {
        let n = u64_(&b, &mut p) as usize;
        p += n;
        let t = u32_(&b, &mut p);
        sauter(&b, &mut p, t);
    }
    let mut m = std::collections::HashMap::new();
    for _ in 0..nt {
        let n = u64_(&b, &mut p) as usize;
        let nom = String::from_utf8_lossy(&b[p..p + n]).into_owned();
        p += n;
        let nd = u32_(&b, &mut p);
        let mut dims = Vec::new();
        for _ in 0..nd {
            dims.push(u64_(&b, &mut p));
        }
        let _t = u32_(&b, &mut p);
        let _d = u64_(&b, &mut p);
        m.insert(nom, dims[0]);
    }
    m
}
