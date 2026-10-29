// P2, second chemin : cache LRU à deux étages, inclusif et exclusif, en Rust.
// Indépendant de cache2.py et de cache_exclusif.py : aucune liste ordonnée, des horodatages dans des
// tableaux indexés par l'identifiant global (couche * 128 + expert) et un balayage linéaire pour la victime.
// Même règle de groupe que trc-cache : les 4 experts du groupe (jeton, couche) ne sont jamais victimes.
//
// Compilation : rustc -O -o second_chemin.exe second_chemin.rs
// Usage       : second_chemin.exe <dossier des traces> <csv de sortie>

use std::fs;
use std::io::Write;

const L: usize = 36;
const N: usize = 36 * 128;

fn lire(chemin: &str) -> Vec<[[usize; 4]; L]> {
    let txt = fs::read_to_string(chemin).expect("trace illisible");
    let mut jetons = Vec::new();
    for ligne in txt.lines() {
        let ligne = ligne.trim();
        if ligne.is_empty() || ligne.starts_with('#') || ligne.starts_with("E=") {
            continue;
        }
        let mut j = [[0usize; 4]; L];
        let mut nl = 0;
        for (l, c) in ligne.split('|').enumerate() {
            let v: Vec<usize> = c.split_whitespace().map(|x| x.parse::<usize>().unwrap()).collect();
            assert_eq!(v.len(), 4);
            for k in 0..4 {
                j[l][k] = l * 128 + v[k];
            }
            nl += 1;
        }
        assert_eq!(nl, L);
        jetons.push(j);
    }
    jetons
}

#[derive(Default, Clone, Copy)]
struct Cpt {
    acces: u64,
    sv: u64,
    sr: u64,
    disque: u64,
    demotions: u64,
}

// mode : 0 = seul, 1 = inclusif, 2 = exclusif
fn sim(g: &[[[usize; 4]; L]], v_cap: usize, r_cap: usize, mode: u8) -> Cpt {
    let mut sv_stamp = vec![0u64; N]; // 0 = absent
    let mut sr_stamp = vec![0u64; N];
    let (mut nv, mut nr) = (0usize, 0usize);
    let mut horloge = 0u64;
    let mut c = Cpt::default();
    let avec_ram = mode != 0 && r_cap > 0;
    for jeton in g {
        for l in 0..L {
            let grp = jeton[l];
            for &x in grp.iter() {
                c.acces += 1;
                if sv_stamp[x] != 0 {
                    c.sv += 1;
                    horloge += 1;
                    sv_stamp[x] = horloge;
                    if avec_ram && mode == 1 && sr_stamp[x] != 0 {
                        horloge += 1;
                        sr_stamp[x] = horloge;
                    }
                    continue;
                }
                // défaut VRAM : victime = plus petit horodatage hors groupe
                let mut victime: Option<usize> = None;
                if nv >= v_cap {
                    let mut best = u64::MAX;
                    for y in 0..N {
                        let s = sv_stamp[y];
                        if s != 0 && s < best && !grp.contains(&y) {
                            best = s;
                            victime = Some(y);
                        }
                    }
                    let vv = victime.expect("aucune victime");
                    sv_stamp[vv] = 0;
                    nv -= 1;
                }
                horloge += 1;
                sv_stamp[x] = horloge;
                nv += 1;
                let en_ram = avec_ram && sr_stamp[x] != 0;
                // insertion en RAM (avec éviction du plus ancien si pleine)
                let mut ins = |id: usize, sr_stamp: &mut Vec<u64>, nr: &mut usize, horloge: &mut u64| {
                    if sr_stamp[id] != 0 {
                        *horloge += 1;
                        sr_stamp[id] = *horloge;
                        return;
                    }
                    if *nr >= r_cap {
                        let mut best = u64::MAX;
                        let mut qui = 0;
                        for y in 0..N {
                            let s = sr_stamp[y];
                            if s != 0 && s < best {
                                best = s;
                                qui = y;
                            }
                        }
                        sr_stamp[qui] = 0;
                        *nr -= 1;
                    }
                    *horloge += 1;
                    sr_stamp[id] = *horloge;
                    *nr += 1;
                };
                if en_ram {
                    c.sr += 1;
                    if mode == 1 {
                        horloge += 1;
                        sr_stamp[x] = horloge;
                    } else {
                        sr_stamp[x] = 0;
                        nr -= 1;
                    }
                } else {
                    c.disque += 1;
                    if avec_ram && mode == 1 {
                        ins(x, &mut sr_stamp, &mut nr, &mut horloge);
                    }
                }
                if avec_ram && mode == 2 {
                    if let Some(vv) = victime {
                        c.demotions += 1;
                        ins(vv, &mut sr_stamp, &mut nr, &mut horloge);
                    }
                }
            }
        }
    }
    c
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let dossier = &args[1];
    let sortie = &args[2];
    let fichiers = [
        ("code.lecture", "t120b.code.lecture.trace"),
        ("dialogue.lecture", "t120b.dialogue.lecture.trace"),
        ("prose-en.lecture", "t120b.prose-en.lecture.trace"),
        ("prose-fr.lecture", "t120b.prose-fr.lecture.trace"),
        ("wiki.lecture", "w120b.wiki.lecture.trace"),
        ("prose-en.generation", "t120b.prose-en.generation.trace"),
        ("wiki.generation", "w120b.wiki.generation.trace"),
    ];
    let mut out = fs::File::create(sortie).unwrap();
    writeln!(out, "trace,V,R,mode,acces,part_disque,succes_ram,demotions").unwrap();
    for (nom, f) in fichiers.iter() {
        let g = lire(&format!("{}/{}", dossier, f));
        for &v in &[326usize, 922] {
            let c = sim(&g, v, 0, 0);
            writeln!(out, "{},{},0,seul,{},{:.6},{:.6},{}", nom, v, c.acces,
                c.disque as f64 / c.acces as f64, 0.0, 0).unwrap();
            for &r in &[80usize, 160, 336, 672, 1344] {
                for (m, nm) in [(1u8, "inclusif"), (2u8, "exclusif")] {
                    let c = sim(&g, v, r, m);
                    writeln!(out, "{},{},{},{},{},{:.6},{:.6},{}", nom, v, r, nm, c.acces,
                        c.disque as f64 / c.acces as f64, c.sr as f64 / c.acces as f64, c.demotions).unwrap();
                }
            }
        }
        eprintln!("{}", nom);
    }
}
