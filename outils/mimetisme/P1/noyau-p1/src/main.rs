//! noyau-p1 : copie de outils/mimetisme/physique/noyau-cache (rôle éclaireur physique, 2026-10-26), adaptée
//! pour P1 (rôle expérimentateur, 2026-10-27). Deux changements seulement, tout le reste est inchangé :
//!   1. le départage à score égal se fait par NUMÉRO D'ACCÈS (comme cache_p1.py) et non par indice de groupe ;
//!   2. si la variable d'environnement HITS_DIR est posée, le succès par jeton de chaque noyau est écrit
//!      dans <HITS_DIR>/<nom du noyau>.hits (un entier par jeton, dans l'ordre du fichier).
//! --- en-tête d'origine ---
//! Cache global d'experts à score par noyau de mémoire (rôle éclaireur physique, 2026-10-26).
//!
//! Usage : noyau-cache <trace> <poids> <N> <noyaux.txt> <sortie.jsonl> [graine_melange]
//!   noyaux.txt : une ligne par noyau, "nom<TAB>a1:tau1,a2:tau2,...", K(dt) = somme a_j exp(-dt/tau_j).
//!   La règle est celle de g_lfu (outils/gptoss_localite.py) : un groupe = les k experts d'un
//!   (jeton, couche) ; le temps est l'indice du jeton ; on évince après le groupe, jamais un expert du
//!   groupe ; départage par ancienneté du dernier accès. Avec un seul noyau exponentiel de demi-vie 8
//!   (tau = 8/ln 2) on retrouve donc g_lfu, ce que le témoin W1 vérifie.
//!   Si une graine est donnée, l'ordre des jetons est mélangé (témoin W2).
//! Sortie : par noyau, hits/total, et pour les seuils de poids eps, le nombre d'accès et de défauts
//!   dont le poids de mélange est sous eps (E2).
use std::fs::File;
use std::io::{BufRead, BufReader, Write};

const L: usize = 36;
const E: usize = 128;
const K: usize = 4;
const EPS: [f64; 6] = [0.02, 0.05, 0.10, 0.15, 0.20, 0.25];

fn lire_trace(chemin: &str) -> Vec<[[usize; K]; L]> {
    let f = BufReader::new(File::open(chemin).expect("trace"));
    let mut v = Vec::new();
    for ligne in f.lines() {
        let ligne = ligne.unwrap();
        let l = ligne.trim();
        if l.is_empty() || l.starts_with('#') || l.starts_with("E=") {
            continue;
        }
        let mut t = [[0usize; K]; L];
        for (i, g) in l.split('|').enumerate() {
            for (j, x) in g.split_whitespace().enumerate() {
                t[i][j] = x.parse().unwrap();
            }
        }
        v.push(t);
    }
    v
}

fn lire_poids(chemin: &str) -> Vec<[[f64; K]; L]> {
    let f = BufReader::new(File::open(chemin).expect("poids"));
    let mut v = Vec::new();
    for ligne in f.lines() {
        let ligne = ligne.unwrap();
        let l = ligne.trim();
        if l.is_empty() || l.starts_with('#') {
            continue;
        }
        let mut t = [[0f64; K]; L];
        for (i, g) in l.split('|').enumerate() {
            for (j, x) in g.split_whitespace().enumerate() {
                t[i][j] = x.parse().unwrap();
            }
        }
        v.push(t);
    }
    v
}

struct Xs(u64);
impl Xs {
    fn next(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        self.0 = x;
        x
    }
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let trace = lire_trace(&a[1]);
    let poids = lire_poids(&a[2]);
    assert_eq!(trace.len(), poids.len(), "trace et poids de longueurs différentes");
    let n_cache: usize = a[3].parse().unwrap();
    let noyaux: Vec<(String, Vec<(f64, f64)>)> = BufReader::new(File::open(&a[4]).unwrap())
        .lines()
        .map(|l| l.unwrap())
        .filter(|l| !l.trim().is_empty())
        .map(|l| {
            let mut p = l.split('\t');
            let nom = p.next().unwrap().to_string();
            let comps = p
                .next()
                .unwrap()
                .split(',')
                .map(|c| {
                    let mut q = c.split(':');
                    (q.next().unwrap().parse().unwrap(), q.next().unwrap().parse().unwrap())
                })
                .collect();
            (nom, comps)
        })
        .collect();
    let mut out = File::create(&a[5]).unwrap();
    let t_n = trace.len();
    let mut ordre: Vec<usize> = (0..t_n).collect();
    let melange = a.len() > 6 && a[6] != "-";
    // Variable d'environnement BYPASS=1 : après le calcul d'un groupe, ses experts peuvent être évincés
    // aussitôt (admission par seuil de score : barrière de nucléation) ; le cache atteint alors N + k au
    // plus pendant le calcul, ce que E3 compense en comparant à une base de capacité N + k.
    let bypass = std::env::var("BYPASS").map(|v| v == "1").unwrap_or(false);
    if melange {
        let mut r = Xs(a[6].parse::<u64>().unwrap() | 1);
        for i in (1..t_n).rev() {
            let j = (r.next() % (i as u64 + 1)) as usize;
            ordre.swap(i, j);
        }
    }
    let mut somme_max_ecart = 0f64;
    for p in &poids {
        for c in p.iter() {
            let s: f64 = c.iter().sum();
            somme_max_ecart = somme_max_ecart.max((s - 1.0).abs());
        }
    }
    for (nom, comps) in &noyaux {
        let nc = comps.len();
        let tmax = t_n + 2;
        // table de décroissance d[j][dt]
        let mut d = vec![0f64; nc * tmax];
        for j in 0..nc {
            for dt in 0..tmax {
                d[j * tmax + dt] = (-(dt as f64) / comps[j].1).exp();
            }
        }
        let items = L * E;
        let mut c = vec![0f64; items * nc];
        let mut last_t = vec![0usize; items];
        let mut vu = vec![0u64; items]; // dernier accès (indice de groupe), 0 = jamais
        let mut en_cache = vec![false; items];
        let mut res: Vec<usize> = Vec::new();
        let (mut hits, mut total) = (0u64, 0u64);
        let mut acc_sous = [0u64; EPS.len()];
        let mut def_sous = [0u64; EPS.len()];
        let mut def_masse = [0f64; EPS.len()];
        let mut def_g2 = [0f64; EPS.len()];
        let mut def_g2_tot = 0f64;
        let mut g2_tot = 0f64;
        let mut def_total = 0u64;
        let mut idx_groupe = 0u64;
        let mut seq_acces = 0u64;
        let mut hits_tok = vec![0u32; t_n];
        for (tt, &src) in ordre.iter().enumerate() {
            for l in 0..L {
                idx_groupe += 1;
                let g = &trace[src][l];
                for s in 0..K {
                    let x = l * E + g[s];
                    let w = poids[src][l][s];
                    total += 1;
                    let dt = tt - last_t[x];
                    for j in 0..nc {
                        c[x * nc + j] = c[x * nc + j] * d[j * tmax + dt] + 1.0;
                    }
                    last_t[x] = tt;
                    seq_acces += 1;
                    vu[x] = seq_acces;
                    let hit = en_cache[x];
                    g2_tot += w * w;
                    if !hit {
                        def_g2_tot += w * w;
                    }
                    for (ie, &e) in EPS.iter().enumerate() {
                        if w < e {
                            acc_sous[ie] += 1;
                            if !hit {
                                def_sous[ie] += 1;
                                def_masse[ie] += w;
                                def_g2[ie] += w * w;
                            }
                        }
                    }
                    if hit {
                        hits += 1;
                        hits_tok[tt] += 1;
                    } else {
                        def_total += 1;
                        en_cache[x] = true;
                        res.push(x);
                    }
                }
                while res.len() > n_cache {
                    // victime : plus petit score, départage par plus ancien dernier accès, hors groupe
                    let mut best = usize::MAX;
                    let mut best_s = f64::INFINITY;
                    let mut best_v = u64::MAX;
                    for (pos, &x) in res.iter().enumerate() {
                        if !bypass && (0..K).any(|s| l * E + g[s] == x) {
                            continue;
                        }
                        let dt = tt - last_t[x];
                        let mut sc = 0f64;
                        for j in 0..nc {
                            sc += comps[j].0 * c[x * nc + j] * d[j * tmax + dt];
                        }
                        if sc < best_s || (sc == best_s && vu[x] < best_v) {
                            best_s = sc;
                            best_v = vu[x];
                            best = pos;
                        }
                    }
                    let x = res.swap_remove(best);
                    en_cache[x] = false;
                }
            }
        }
        if let Ok(dir) = std::env::var("HITS_DIR") {
            let mut f = File::create(format!("{}/{}.hits", dir, nom)).unwrap();
            for v in &hits_tok {
                writeln!(f, "{}", v).unwrap();
            }
        }
        writeln!(
            out,
            "{{\"noyau\":\"{}\",\"melange\":{},\"jetons\":{},\"hits\":{},\"total\":{},\"taux\":{:.6},\"defauts\":{},\"eps\":{:?},\"acces_sous\":{:?},\"defauts_sous\":{:?},\"defauts_masse\":{:?},\"defauts_g2\":{:?},\"defauts_g2_total\":{:.6},\"g2_total\":{:.6},\"ecart_somme_poids_max\":{:.6}}}",
            nom, melange, t_n, hits, total, hits as f64 / total as f64, def_total, EPS, acc_sous, def_sous, def_masse, def_g2, def_g2_tot, g2_tot, somme_max_ecart
        )
        .unwrap();
    }
}
