//! La règle de décision des séries ABBA (étude 01, reprise par 06 § 7.5, telle quelle) :
//! séries A1 B1 B2 A2 répétées au moins deux fois ; bruit d'une configuration = |X1 − X2| / moyenne ;
//! une différence entre A et B n'est réelle que si |moy(B) − moy(A)| / moy(A) dépasse à la fois
//! 2 × le plus grand bruit observé et 3 %.

use serde::Serialize;

/// Une série : les mesures de A et de B dans l'ordre A1 B1 B2 A2 (plusieurs séries à la suite).
#[derive(Clone, Debug, Serialize)]
pub struct Verdict {
    pub moyenne_a: f64,
    pub moyenne_b: f64,
    pub ecart_relatif: f64,
    pub plus_grand_bruit: f64,
    pub seuil: f64,
    pub reel: bool,
}

/// `series` : chaque élément est (a1, b1, b2, a2).
pub fn decider(series: &[(f64, f64, f64, f64)]) -> Verdict {
    assert!(!series.is_empty());
    let mut bruit: f64 = 0.0;
    let (mut sa, mut sb) = (0.0, 0.0);
    for &(a1, b1, b2, a2) in series {
        bruit = bruit.max((a1 - a2).abs() / ((a1 + a2) / 2.0));
        bruit = bruit.max((b1 - b2).abs() / ((b1 + b2) / 2.0));
        sa += a1 + a2;
        sb += b1 + b2;
    }
    let n = 2.0 * series.len() as f64;
    let (ma, mb) = (sa / n, sb / n);
    let ecart = (mb - ma) / ma;
    let seuil = (2.0 * bruit).max(0.03);
    Verdict { moyenne_a: ma, moyenne_b: mb, ecart_relatif: ecart, plus_grand_bruit: bruit, seuil, reel: ecart.abs() > seuil }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bruit_et_seuil() {
        // A stable à 10, B à 11 (+10 %), bruit 2 % : réel.
        let v = decider(&[(10.0, 11.0, 11.0, 10.2), (10.1, 11.1, 10.9, 10.0)]);
        assert!(v.reel, "{v:?}");
        // B à 10,25 (+2,5 %) : sous 3 %, pas réel.
        let v = decider(&[(10.0, 10.25, 10.25, 10.0)]);
        assert!(!v.reel);
        // B à +8 % mais bruit de 5 % (seuil 10 %) : pas réel.
        let v = decider(&[(10.0, 10.8, 10.8, 10.5)]);
        assert!(!v.reel, "{v:?}");
    }
}
