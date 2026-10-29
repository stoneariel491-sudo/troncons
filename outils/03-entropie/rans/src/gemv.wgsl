// Produit matrice-vecteur (lot 1) sur des poids MXFP4, avec et sans décodage rANS fondu.
//
// Disposition des poids (celle de block_mxfp4 de ggml, ggml-common.h, redérivée) :
//   - un bloc = 32 poids = 16 octets de codes + 1 échelle E8M0 rangée à part ;
//   - l'octet i du bloc porte le poids i (demi-octet bas) et le poids 16 + i (haut) ;
//   - valeur = kv[code] · 2^(e − 128), kv = E2M1 doublé {0,1,2,3,4,6,8,12} et signe.
// Une ligne de K poids = K/32 blocs = K/8 mots de 32 bits. Le mot t (0..3) d'un bloc
// porte, par ses demi-octets bas, les poids 4t..4t+3, et par ses hauts, 16+4t..16+4t+3.
//
// Trois chemins, même arithmétique de déquantification (dot_mot), pour que l'écart de
// temps ne mesure que le décodage :
//   gemv_brut      : codes bruts en VRAM (4 bits par code) ;
//   gemv_fusionne  : flux rANS (alphabet octet, format de lib.rs, décodeur v4) décodé
//                    dans les registres et consommé sur place, sans écrire les codes ;
//   (deux passes)  : decoder_v4 de decodeur.wgsl écrit les codes, puis gemv_brut.

struct Parametres {
    nb_tuiles: u32,        // tuiles rANS (gemv_fusionne) ou groupes de 16 lignes (gemv_brut)
    casser: u32,           // témoin : 1 corrompt une fente de la table, 2 toutes les fentes
    mots_par_ligne: u32,   // K / 8
    nb_lignes: u32,
};

@group(0) @binding(0) var<storage, read> lut_globale: array<u32>;
@group(0) @binding(1) var<storage, read> etats: array<u32>;
@group(0) @binding(2) var<storage, read> tuiles: array<vec4<u32>>;
@group(0) @binding(3) var<storage, read> mots: array<u32>;
@group(0) @binding(4) var<storage, read> echelles: array<u32>;     // E8M0, 4 par mot
@group(0) @binding(5) var<storage, read> xv: array<vec4<f32>>;      // K/4 vec4
@group(0) @binding(6) var<storage, read_write> y: array<f32>;
@group(0) @binding(7) var<uniform> p: Parametres;
@group(0) @binding(8) var<storage, read_write> controle: array<atomic<u32>>;
@group(0) @binding(9) var<storage, read> brut: array<vec4<u32>>;    // codes bruts, un bloc par vec4

var<workgroup> lut: array<u32, 4096>;

// Quatre codes E2M1 -> valeurs doublées. Les 8 grandeurs tiennent dans un mot :
// 0xC8643210 range 0,1,2,3,4,6,8,12 par demi-octet ; le bit 3 est le signe.
fn valeurs4(c: vec4<u32>) -> vec4<f32> {
    let g = (vec4<u32>(0xC8643210u) >> ((c & vec4<u32>(7u)) * 4u)) & vec4<u32>(15u);
    let v = vec4<f32>(g);
    return select(v, -v, (c & vec4<u32>(8u)) != vec4<u32>(0u));
}

// Contribution d'un mot (4 octets d'un bloc, mot t) : xa = poids 4t..4t+3 du bloc,
// xb = poids 16+4t..16+4t+3.
fn dot_mot(w: u32, xa: vec4<f32>, xb: vec4<f32>) -> f32 {
    let dec = vec4<u32>(0u, 8u, 16u, 24u);
    let bas = (vec4<u32>(w) >> dec) & vec4<u32>(15u);
    let haut = (vec4<u32>(w) >> (dec + vec4<u32>(4u))) & vec4<u32>(15u);
    return dot(valeurs4(bas), xa) + dot(valeurs4(haut), xb);
}

fn echelle(bloc: u32) -> f32 {
    let e = (echelles[bloc >> 2u] >> ((bloc & 3u) * 8u)) & 255u;
    return exp2(f32(e) - 128.0);
}

// Chemin brut. Un sous-groupe traite 4 lignes à la fois : chaque voie charge les 32 x
// d'un bloc une fois et les applique aux 4 lignes. Un groupe de 128 = 16 lignes.
@compute @workgroup_size(128)
fn gemv_brut(
    @builtin(workgroup_id) gt: vec3<u32>,
    @builtin(subgroup_invocation_id) voie: u32,
    @builtin(subgroup_id) id_sg: u32,
) {
    let ligne0 = (gt.x * 4u + id_sg) * 4u;
    if (ligne0 >= p.nb_lignes) {
        return;
    }
    let blocs_ligne = p.mots_par_ligne / 4u;
    var acc = vec4<f32>(0.0);
    for (var j = voie; j < blocs_ligne; j += 32u) {
        var xa: array<vec4<f32>, 8>;
        for (var k = 0u; k < 8u; k++) {
            xa[k] = xv[j * 8u + k];
        }
        for (var r = 0u; r < 4u; r++) {
            let b = (ligne0 + r) * blocs_ligne + j;
            let q = brut[b];
            let s = dot_mot(q.x, xa[0], xa[4]) + dot_mot(q.y, xa[1], xa[5])
                  + dot_mot(q.z, xa[2], xa[6]) + dot_mot(q.w, xa[3], xa[7]);
            acc[r] += echelle(b) * s;
        }
    }
    for (var r = 0u; r < 4u; r++) {
        let t = subgroupAdd(acc[r]);
        if (voie == 0u) {
            y[ligne0 + r] = t;
        }
    }
}

// Chemin fondu : le décodeur v4 (alphabet octet, vote de sous-groupe, fenêtre de flux
// distribuée par échange), dont chaque mot de sortie est consommé sur place.
// La tuile t couvre les mots t·32·nb_macro .. de la matrice ; la voie l du macro-pas m
// produit le mot m·32 + l. Avec K = 4096, une ligne = 512 mots = 16 macro-pas, et une
// tuile de 256 macro-pas = 16 lignes entières.
@compute @workgroup_size(128)
fn gemv_fusionne(
    @builtin(local_invocation_index) li: u32,
    @builtin(workgroup_id) gt: vec3<u32>,
    @builtin(subgroup_invocation_id) voie: u32,
    @builtin(subgroup_size) taille_sg: u32,
    @builtin(subgroup_id) id_sg: u32,
    @builtin(num_subgroups) nb_sg: u32,
) {
    for (var i = li; i < 4096u; i += 128u) {
        lut[i] = lut_globale[i];
    }
    if (p.casser == 1u && li == 0u) {
        lut[7u] = lut[7u] ^ 1u;
    }
    workgroupBarrier();
    if (p.casser == 2u) {
        for (var i = li; i < 4096u; i += 128u) {
            lut[i] = lut[i] ^ 1u;
        }
    }
    workgroupBarrier();
    if (taille_sg != 32u) {
        if (li == 0u) { atomicAdd(&controle[1], 1u); }
        return;
    }
    let tuile = gt.x * nb_sg + id_sg;
    if (tuile >= p.nb_tuiles) {
        return;
    }
    let t = tuiles[tuile];
    var x = etats[tuile * 32u + voie];
    var ptr = t.x;
    var base = t.x >> 1u;
    var cour = mots[base + voie];
    var suiv = mots[base + 32u + voie];
    let masque_inf = (1u << voie) - 1u;
    let macro_ligne = p.mots_par_ligne / 32u;     // puissance de 2 (16 pour K = 4096)
    let mot0 = t.z;                               // premier mot de la tuile dans la matrice
    let blocs_ligne = p.mots_par_ligne / 4u;
    var acc = 0.0;
    for (var m = 0u; m < t.y; m++) {
        var mot = 0u;
        for (var k = 0u; k < 4u; k++) {
            let e = lut[x & 4095u];
            x = (((e >> 8u) & 0xFFFu) + 1u) * (x >> 12u) + (e >> 20u);
            mot |= (e & 0xFFu) << (8u * k);
            let besoin = x < 65536u;
            let vote = subgroupBallot(besoin).x;
            let pos = ptr + countOneBits(vote & masque_inf);
            let wi = (pos >> 1u) - base;
            let a = subgroupShuffle(cour, wi & 31u);
            let b = subgroupShuffle(suiv, wi & 31u);
            let w32 = select(a, b, wi >= 32u);
            let w = (w32 >> ((pos & 1u) * 16u)) & 0xFFFFu;
            x = select(x, (x << 16u) | w, besoin);
            ptr += countOneBits(vote);
            if ((ptr >> 1u) - base >= 32u) {
                base += 32u;
                cour = suiv;
                suiv = mots[base + 32u + voie];
            }
        }
        // Consommation du mot : position dans la matrice, bloc, mot dans le bloc.
        let g = mot0 + m * 32u + voie;                 // mot global
        let ligne = g / p.mots_par_ligne;
        let wr = g - ligne * p.mots_par_ligne;         // mot dans la ligne
        let bloc = wr >> 2u;
        let tb = wr & 3u;
        let bg = ligne * blocs_ligne + bloc;           // bloc global (échelle)
        acc += echelle(bg) * dot_mot(mot, xv[bloc * 8u + tb], xv[bloc * 8u + 4u + tb]);
        if ((m & (macro_ligne - 1u)) == macro_ligne - 1u) {   // fin de ligne, uniforme
            let s = subgroupAdd(acc);
            if (voie == 0u) {
                y[ligne] = s;
            }
            acc = 0.0;
        }
    }
    if (x != 65536u) {
        atomicAdd(&controle[0], 1u);
    }
}
