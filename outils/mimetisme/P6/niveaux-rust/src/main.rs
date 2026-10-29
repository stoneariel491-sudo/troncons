//! Second chemin de P6, étape 0 : cache d'experts à niveaux (exact / rapide), écrit à part de tiers.py.
//!
//! Usage : niveaux-rust <trace> <poids> <L> <E> <N> <demi_vie> <rho> <theta> <theta_p> <sortie.json>
//!   theta_p = 0 : règle « accepter » ; theta_p > 0 : « remonter à theta_p ».
//! Politique : celle de `noyau-cache` (LFU à décroissance exponentielle, groupe (t, l) servi entier,
//! éviction après lui, jamais un expert du groupe, départage par ancienneté du dernier accès).
//! Ici le calcul est un automate à étiquettes, accès après accès (pas de séjours triés ni de cumuls) :
//! c'est ce qui le rend indépendant du calcul vectorisé de tiers.py.
//! Sortie : défauts, octets (en unités d'un expert exact), énergie servie rapide, énergie totale.
use std::fs::File;
use std::io::{BufRead, BufReader, Write};

const K: usize = 4;

fn lire<T: std::str::FromStr>(chemin: &str) -> Vec<Vec<Vec<T>>>
where
    T::Err: std::fmt::Debug,
{
    let f = BufReader::new(File::open(chemin).expect("fichier"));
    let mut v = Vec::new();
    for ligne in f.lines() {
        let ligne = ligne.unwrap();
        let l = ligne.trim();
        if l.is_empty() || l.starts_with('#') || l.starts_with("E=") {
            continue;
        }
        v.push(
            l.split('|')
                .map(|g| g.split_whitespace().map(|x| x.parse::<T>().unwrap()).collect())
                .collect(),
        );
    }
    v
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let trace: Vec<Vec<Vec<usize>>> = lire(&a[1]);
    let poids: Vec<Vec<Vec<f64>>> = lire(&a[2]);
    let (l_n, e_n): (usize, usize) = (a[3].parse().unwrap(), a[4].parse().unwrap());
    let n_cache: usize = a[5].parse().unwrap();
    let demi_vie: f64 = a[6].parse().unwrap();
    let rho: f64 = a[7].parse().unwrap();
    let theta: f64 = a[8].parse().unwrap();
    let theta_p: f64 = a[9].parse().unwrap();
    assert_eq!(trace.len(), poids.len());
    let tau = demi_vie / std::f64::consts::LN_2;
    let t_n = trace.len();
    let items = l_n * e_n;
    let d: Vec<f64> = (0..t_n + 2).map(|dt| (-(dt as f64) / tau).exp()).collect();
    let mut c = vec![0f64; items];
    let mut last_t = vec![0usize; items];
    let mut vu = vec![0u64; items];
    let mut en_cache = vec![false; items];
    let mut rapide = vec![false; items]; // étiquette du séjour en cours : true = F
    let mut res: Vec<usize> = Vec::new();
    let (mut defauts, mut total, mut relectures) = (0u64, 0u64, 0u64);
    let (mut octets, mut energie, mut energie_tout) = (0f64, 0f64, 0f64);
    let mut idx_groupe = 0u64;
    for tt in 0..t_n {
        for l in 0..l_n {
            idx_groupe += 1;
            let g = &trace[tt][l];
            for s in 0..K {
                let x = l * e_n + g[s];
                let w = poids[tt][l][s];
                total += 1;
                energie_tout += w * w;
                c[x] = c[x] * d[tt - last_t[x]] + 1.0;
                last_t[x] = tt;
                vu[x] = idx_groupe;
                if en_cache[x] {
                    if rapide[x] {
                        if theta_p > 0.0 && w >= theta_p {
                            octets += 1.0; // relecture de l'exact entier ; l'accès est servi exact
                            relectures += 1;
                            rapide[x] = false;
                        } else {
                            energie += w * w;
                        }
                    }
                } else {
                    defauts += 1;
                    en_cache[x] = true;
                    res.push(x);
                    if w < theta {
                        rapide[x] = true;
                        octets += rho;
                        energie += w * w;
                    } else {
                        rapide[x] = false;
                        octets += 1.0;
                    }
                }
            }
            while res.len() > n_cache {
                let mut best = usize::MAX;
                let mut best_s = f64::INFINITY;
                let mut best_v = u64::MAX;
                for (pos, &x) in res.iter().enumerate() {
                    if (0..K).any(|s| l * e_n + g[s] == x) {
                        continue;
                    }
                    let sc = c[x] * d[tt - last_t[x]];
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
    let s = (defauts as f64 - octets) / defauts as f64;
    let e_rel = energie / energie_tout;
    let r = e_rel / (s / (1.0 - rho));
    let mut out = File::create(&a[10]).unwrap();
    writeln!(
        out,
        "{{\"defauts\":{},\"acces\":{},\"relectures\":{},\"octets\":{:.6},\"S\":{:.9},\"E_rel\":{:.9},\"r\":{:.9}}}",
        defauts, total, relectures, octets, s, e_rel, r
    )
    .unwrap();
}
