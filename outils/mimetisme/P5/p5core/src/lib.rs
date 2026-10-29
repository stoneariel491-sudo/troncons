//! P5 : noyau du recuit et de l'echange de repliques sur le choix des symboles synonymes.
//!
//! Le probleme. Une rangee w (n poids), une grille par coordonnee lev[j][m] = c[m] * s[j] (k niveaux :
//! les centres c, l'echelle de bloc s), une forme quadratique H (n x n, symetrique definie positive),
//! un cout de code ell[m]. On cherche q (un niveau par coordonnee) qui minimise
//!     E(q) = (w - q)^T H (w - q) + lamp * somme_j ell[q_j]
//! C'est l'energie d'un verre de spin a k etats par site : couplages H_ij entre les residus.
//!
//! Les fonctions. `pt_rows` : echange de repliques (Hukushima et Nemoto 1996) par rangee, bain thermique
//! a une coordonnee, partant d'un etat donne (Babai), suivi d'une trempe a temperature nulle ;
//! `enum_best` : enumeration exhaustive ou decodage par sphere (Fincke et Pohst 1985) par la
//! factorisation de Cholesky, pour les temoins ; `energie` : l'energie recalculee de zero.
//! Aucune dependance. Tout est en f64.

use std::slice;

struct Rng(u64);
impl Rng {
    fn new(seed: u64) -> Rng {
        let mut r = Rng(seed ^ 0x9E37_79B9_7F4A_7C15);
        for _ in 0..4 {
            r.next();
        }
        r
    }
    #[inline]
    fn next(&mut self) -> u64 {
        // splitmix64
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    #[inline]
    fn unif(&mut self) -> f64 {
        (self.next() >> 11) as f64 * (1.0 / 9007199254740992.0)
    }
}

/// Un balayage de bain thermique (T > 0) ou de descente (T = 0) sur toutes les coordonnees.
/// Rend le nombre de changements. `hr` = H r est tenu a jour.
#[allow(clippy::too_many_arguments)]
fn balayage(
    n: usize, k: usize, h: &[f64], s: &[f64], c: &[f64], ell: &[f64], lamp: f64,
    temp: f64, q: &mut [u8], hr: &mut [f64], rng: &mut Rng,
) -> usize {
    let mut changes = 0usize;
    let mut de = [0.0f64; 16];
    for j in 0..n {
        let cur = q[j] as usize;
        let sj = s[j];
        let lc = c[cur] * sj;
        let hj = hr[j];
        let hjj = h[j * n + j];
        let mut mn = 0.0f64;
        let mut arg = cur;
        for m in 0..k {
            if m == cur {
                de[m] = 0.0;
                continue;
            }
            let dr = lc - c[m] * sj;
            let d = 2.0 * dr * hj + dr * dr * hjj + lamp * (ell[m] - ell[cur]);
            de[m] = d;
            if d < mn {
                mn = d;
                arg = m;
            }
        }
        let nouveau = if temp <= 0.0 {
            arg
        } else {
            let mut p = [0.0f64; 16];
            let mut z = 0.0;
            for m in 0..k {
                p[m] = (-(de[m] - mn) / temp).exp();
                z += p[m];
            }
            let mut u = rng.unif() * z;
            let mut ch = k - 1;
            for m in 0..k {
                if u < p[m] {
                    ch = m;
                    break;
                }
                u -= p[m];
            }
            ch
        };
        if nouveau != cur {
            let dr = lc - c[nouveau] * sj;
            let row = &h[j * n..(j + 1) * n];
            for i in 0..n {
                hr[i] += dr * row[i];
            }
            q[j] = nouveau as u8;
            changes += 1;
        }
    }
    changes
}

fn calc_hr(n: usize, h: &[f64], w: &[f64], s: &[f64], c: &[f64], q: &[u8], hr: &mut [f64]) {
    let mut r = vec![0.0f64; n];
    for j in 0..n {
        r[j] = w[j] - c[q[j] as usize] * s[j];
    }
    for i in 0..n {
        let row = &h[i * n..(i + 1) * n];
        let mut a = 0.0;
        for j in 0..n {
            a += row[j] * r[j];
        }
        hr[i] = a;
    }
}

fn energie_de(n: usize, w: &[f64], s: &[f64], c: &[f64], ell: &[f64], lamp: f64, q: &[u8], hr: &[f64]) -> (f64, f64) {
    let mut e = 0.0;
    let mut bits = 0.0;
    for j in 0..n {
        let r = w[j] - c[q[j] as usize] * s[j];
        e += r * hr[j];
        bits += ell[q[j] as usize];
    }
    (e + lamp * bits, e)
}

/// Energie recalculee de zero (pour les temoins) : out = (E totale, partie erreur, bits).
#[no_mangle]
pub unsafe extern "C" fn energie(
    n: usize, k: usize, h: *const f64, w: *const f64, s: *const f64, c: *const f64, ell: *const f64,
    lamp: f64, q: *const u8, out: *mut f64,
) {
    let h = slice::from_raw_parts(h, n * n);
    let w = slice::from_raw_parts(w, n);
    let s = slice::from_raw_parts(s, n);
    let c = slice::from_raw_parts(c, k);
    let ell = slice::from_raw_parts(ell, k);
    let q = slice::from_raw_parts(q, n);
    let mut hr = vec![0.0; n];
    calc_hr(n, h, w, s, c, q, &mut hr);
    let (e, ee) = energie_de(n, w, s, c, ell, lamp, q, &hr);
    let out = slice::from_raw_parts_mut(out, 3);
    out[0] = e;
    out[1] = ee;
    let mut bits = 0.0;
    for j in 0..n {
        bits += ell[q[j] as usize];
    }
    out[2] = bits;
}

/// Echange de repliques sur les rangees [r0, r1). Tableaux plats : w, s, q_in, q_out (rangee x n).
/// temps : nt temperatures croissantes (> 0). nsweeps balayages, echange tous les `every` balayages.
/// trempe : nombre maximal de balayages de descente a T = 0 sur le meilleur etat (0 = aucune).
/// dernier : voir plus bas. stats (8 flottants par rangee) : E initiale, E meilleure avant trempe, E finale, part erreur finale,
///   taux d'echange, taux de changements (froide), taux de changements (chaude), balayages de trempe.
#[no_mangle]
pub unsafe extern "C" fn pt_rows(
    n: usize, k: usize, h: *const f64, w: *const f64, s: *const f64, c: *const f64, ell: *const f64,
    lamp: f64, q_in: *const u8, q_out: *mut u8, r0: usize, r1: usize, temps: *const f64, nt: usize,
    nsweeps: usize, every: usize, trempe: usize, seed: u64, stats: *mut f64, dernier: i32,
) {
    let h = slice::from_raw_parts(h, n * n);
    let c = slice::from_raw_parts(c, k);
    let ell = slice::from_raw_parts(ell, k);
    let temps = slice::from_raw_parts(temps, nt);
    let nrows = r1;
    let wall = slice::from_raw_parts(w, nrows * n);
    let sall = slice::from_raw_parts(s, nrows * n);
    let qin = slice::from_raw_parts(q_in, nrows * n);
    let qout = slice::from_raw_parts_mut(q_out, nrows * n);
    let st = slice::from_raw_parts_mut(stats, nrows * 8);
    for row in r0..r1 {
        let w = &wall[row * n..(row + 1) * n];
        let s = &sall[row * n..(row + 1) * n];
        let mut rng = Rng::new(seed.wrapping_add(row as u64 * 7919));
        // repliques : nt etats, tous partis de q_in
        let mut qs: Vec<Vec<u8>> = (0..nt).map(|_| qin[row * n..(row + 1) * n].to_vec()).collect();
        let mut hrs: Vec<Vec<f64>> = (0..nt).map(|_| vec![0.0; n]).collect();
        for t in 0..nt {
            calc_hr(n, h, w, s, c, &qs[t], &mut hrs[t]);
        }
        let mut es = vec![0.0f64; nt];
        for t in 0..nt {
            es[t] = energie_de(n, w, s, c, ell, lamp, &qs[t], &hrs[t]).0;
        }
        let e0 = es[0];
        let mut meilleur = qs[0].clone();
        let mut emeil = e0;
        let mut slot: Vec<usize> = (0..nt).collect();
        let (mut ech_ok, mut ech_essai) = (0usize, 0usize);
        let (mut chg_froid, mut chg_chaud) = (0usize, 0usize);
        for sw in 0..nsweeps {
            for t in 0..nt {
                let rep = slot[t];
                let (qr, hrr) = (&mut qs[rep], &mut hrs[rep]);
                let ch = balayage(n, k, h, s, c, ell, lamp, temps[t], qr, hrr, &mut rng);
                if t == 0 {
                    chg_froid += ch;
                }
                if t == nt - 1 {
                    chg_chaud += ch;
                }
                es[rep] = energie_de(n, w, s, c, ell, lamp, qr, hrr).0;
                if es[rep] < emeil {
                    emeil = es[rep];
                    meilleur.copy_from_slice(qr);
                }
            }
            if sw % 20 == 19 {
                for t in 0..nt {
                    calc_hr(n, h, w, s, c, &qs[t], &mut hrs[t]);
                    es[t] = energie_de(n, w, s, c, ell, lamp, &qs[t], &hrs[t]).0;
                }
            }
            if nt > 1 && (sw + 1) % every == 0 {
                let par = ((sw + 1) / every) % 2;
                let mut t = par;
                while t + 1 < nt {
                    let (a, b) = (slot[t], slot[t + 1]);
                    let d = (1.0 / temps[t] - 1.0 / temps[t + 1]) * (es[a] - es[b]);
                    ech_essai += 1;
                    if d >= 0.0 || rng.unif() < d.exp() {
                        slot.swap(t, t + 1);
                        ech_ok += 1;
                    }
                    t += 2;
                }
            }
        }
        // dernier != 0 : on rend l'etat final de la replique la plus froide (estimateur de Gibbs, sans trempe)
        // trempe du meilleur etat
        let mut q = if dernier != 0 { qs[slot[0]].clone() } else { meilleur.clone() };
        let trempe = if dernier != 0 { 0 } else { trempe };
        let mut hr = vec![0.0; n];
        calc_hr(n, h, w, s, c, &q, &mut hr);
        let mut nb = 0usize;
        for _ in 0..trempe {
            let ch = balayage(n, k, h, s, c, ell, lamp, 0.0, &mut q, &mut hr, &mut rng);
            nb += 1;
            if ch == 0 {
                break;
            }
        }
        calc_hr(n, h, w, s, c, &q, &mut hr);
        let (ef, ee) = energie_de(n, w, s, c, ell, lamp, &q, &hr);
        qout[row * n..(row + 1) * n].copy_from_slice(&q);
        let o = &mut st[row * 8..(row + 1) * 8];
        o[0] = e0;
        o[1] = emeil;
        o[2] = ef;
        o[3] = ee;
        o[4] = if ech_essai > 0 { ech_ok as f64 / ech_essai as f64 } else { 0.0 };
        o[5] = chg_froid as f64 / (nsweeps.max(1) * n) as f64;
        o[6] = chg_chaud as f64 / (nsweeps.max(1) * n) as f64;
        o[7] = nb as f64;
    }
}

struct Enum<'a> {
    n: usize,
    k: usize,
    l: &'a [f64], // L triangulaire inferieure, H = L L^T
    lev: &'a [f64],
    w: &'a [f64],
    cost: &'a [f64],
    prune: bool,
    best: f64,
    best_idx: Vec<i32>,
    cur: Vec<i32>,
    r: Vec<f64>,
    noeuds: u64,
}
impl<'a> Enum<'a> {
    fn rec(&mut self, i: usize, acc: f64) {
        // choisit la coordonnee i ; les coordonnees j > i sont fixees. (L^T r)_i = sum_{j>=i} L_ji r_j
        let n = self.n;
        let mut base = 0.0;
        for j in (i + 1)..n {
            base += self.l[j * n + i] * self.r[j];
        }
        let lii = self.l[i * n + i];
        for m in 0..self.k {
            let rj = self.w[i] - self.lev[i * self.k + m];
            let t = base + lii * rj;
            let a = acc + t * t + self.cost[i * self.k + m];
            self.noeuds += 1;
            if self.prune && a >= self.best {
                continue;
            }
            self.r[i] = rj;
            self.cur[i] = m as i32;
            if i == 0 {
                if a < self.best {
                    self.best = a;
                    self.best_idx.copy_from_slice(&self.cur);
                }
            } else {
                self.rec(i - 1, a);
            }
        }
    }
}

/// Enumeration par Cholesky (L triangulaire inferieure, H = L L^T). prune = 0 : force brute (k^n feuilles).
/// prune = 1 : decodage par sphere, rayon initial init_best (energie d'un etat connu + marge).
/// Rend l'energie optimale ; out_idx : le niveau choisi par coordonnee. noeuds : noeuds visites.
#[no_mangle]
pub unsafe extern "C" fn enum_best(
    n: usize, k: usize, l: *const f64, lev: *const f64, w: *const f64, cost: *const f64, prune: i32,
    init_best: f64, out_idx: *mut i32, noeuds: *mut u64,
) -> f64 {
    let mut e = Enum {
        n,
        k,
        l: slice::from_raw_parts(l, n * n),
        lev: slice::from_raw_parts(lev, n * k),
        w: slice::from_raw_parts(w, n),
        cost: slice::from_raw_parts(cost, n * k),
        prune: prune != 0,
        best: init_best,
        best_idx: vec![-1; n],
        cur: vec![0; n],
        r: vec![0.0; n],
        noeuds: 0,
    };
    e.rec(n - 1, 0.0);
    let o = slice::from_raw_parts_mut(out_idx, n);
    o.copy_from_slice(&e.best_idx);
    *noeuds = e.noeuds;
    e.best
}
