// Décodeur rANS entrelacé par sous-groupe (format décrit dans lib.rs).
// Un sous-groupe de 32 invocations décode une tuile ; la table de décodage (4096
// entrées de 32 bits, 16 Kio) vit dans la mémoire partagée du groupe de travail.
// Les fonctions de sous-groupe demandent la fonction SUBGROUP de wgpu (naga 30 refuse encore la directive « enable subgroups »).

struct Parametres {
    nb_tuiles: u32,
    casser: u32,   // témoin : 1 corrompt une entrée de la table, le décodage doit tomber
    _r0: u32,
    _r1: u32,
};

@group(0) @binding(0) var<storage, read> lut_globale: array<u32>;
@group(0) @binding(1) var<storage, read> etats: array<u32>;
@group(0) @binding(2) var<storage, read> tuiles: array<vec4<u32>>;
@group(0) @binding(3) var<storage, read> mots: array<u32>;
@group(0) @binding(4) var<storage, read_write> sortie: array<u32>;
@group(0) @binding(5) var<uniform> p: Parametres;
@group(0) @binding(6) var<storage, read_write> controle: array<atomic<u32>>;

var<workgroup> lut: array<u32, 4096>;

@compute @workgroup_size(128)
fn decoder_v1(
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
        lut[7u] = lut[7u] ^ (1u << 17u);
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
    var dest = t.z + voie;
    for (var m = 0u; m < t.y; m++) {
        var mot = 0u;
        for (var k = 0u; k < 8u; k++) {
            let e = lut[x & 4095u];
            x = ((e >> 4u) & 0x1FFFu) * (x >> 12u) + (e >> 17u);
            mot |= (e & 15u) << (4u * k);
            let besoin = select(0u, 1u, x < 65536u);
            let pos = ptr + subgroupExclusiveAdd(besoin);
            if (besoin == 1u) {
                let w = (mots[pos >> 1u] >> ((pos & 1u) * 16u)) & 0xFFFFu;
                x = (x << 16u) | w;
            }
            ptr += subgroupAdd(besoin);
        }
        sortie[dest] = mot;
        dest += 32u;
    }
    if (x != 65536u) {
        atomicAdd(&controle[0], 1u);
    }
}

// Version 2. Deux changements, chacun pour une raison mesurée sur la v1 :
// 1. la position de lecture vient d'un vote (subgroupBallot) et d'un comptage de bits,
//    au lieu d'une somme préfixe du sous-groupe (plusieurs échanges par appel) ;
// 2. le flux est lu par fenêtres de 32 mots de 32 bits chargées d'avance, une par voie,
//    et distribuées par subgroupShuffle : la lecture de renormalisation ne va plus en
//    mémoire globale (des centaines de cycles) au milieu de la chaîne de dépendance.
//    Un sous-pas consomme au plus 32 mots de 16 bits (16 de 32 bits) : la fenêtre
//    suivante a donc toujours été demandée au moins un sous-pas avant d'être lue.
@compute @workgroup_size(128)
fn decoder(
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
        lut[7u] = lut[7u] ^ (1u << 17u);
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
    var ptr = t.x;                 // position courante, en mots de 16 bits
    var base = t.x >> 1u;          // premier mot de 32 bits de la fenêtre courante
    var cour = mots[base + voie];
    var suiv = mots[base + 32u + voie];
    let masque_inf = (1u << voie) - 1u;
    var dest = t.z + voie;
    for (var m = 0u; m < t.y; m++) {
        var mot = 0u;
        for (var k = 0u; k < 8u; k++) {
            let e = lut[x & 4095u];
            x = ((e >> 4u) & 0x1FFFu) * (x >> 12u) + (e >> 17u);
            mot |= (e & 15u) << (4u * k);
            let besoin = x < 65536u;
            let vote = subgroupBallot(besoin).x;
            let pos = ptr + countOneBits(vote & masque_inf);
            let wi = (pos >> 1u) - base;           // 0..47
            let a = subgroupShuffle(cour, wi & 31u);
            let b = subgroupShuffle(suiv, wi & 31u);
            let w32 = select(a, b, wi >= 32u);
            let w = (w32 >> ((pos & 1u) * 16u)) & 0xFFFFu;
            x = select(x, (x << 16u) | w, besoin);
            ptr += countOneBits(vote);
            if ((ptr >> 1u) - base >= 32u) {        // uniforme dans le sous-groupe
                base += 32u;
                cour = suiv;
                suiv = mots[base + 32u + voie];
            }
        }
        sortie[dest] = mot;
        dest += 32u;
    }
    if (x != 65536u) {
        atomicAdd(&controle[0], 1u);
    }
}

// Version 3 : la v2 avec une table compacte. La fente donne le symbole par un octet
// (4096 octets rangés dans 1024 mots), et le symbole donne (f, cumul) par une petite
// table de 16 mots. 4 Kio de mémoire partagée au lieu de 16 Kio : plus de groupes de
// travail résidents par multiprocesseur, au prix d'une seconde lecture dépendante.
var<workgroup> lut_sym: array<u32, 1024>;
var<workgroup> lut_fc: array<u32, 16>;

@compute @workgroup_size(128)
fn decoder_v3(
    @builtin(local_invocation_index) li: u32,
    @builtin(workgroup_id) gt: vec3<u32>,
    @builtin(subgroup_invocation_id) voie: u32,
    @builtin(subgroup_size) taille_sg: u32,
    @builtin(subgroup_id) id_sg: u32,
    @builtin(num_subgroups) nb_sg: u32,
) {
    // Construction depuis la table large : chaque invocation range 4 fentes par mot.
    for (var i = li; i < 1024u; i += 128u) {
        var v = 0u;
        for (var j = 0u; j < 4u; j++) {
            v |= (lut_globale[4u * i + j] & 15u) << (8u * j);
        }
        lut_sym[i] = v;
    }
    if (li < 16u) {
        lut_fc[li] = 0u;
    }
    workgroupBarrier();
    // (f, cumul) de chaque symbole : lus sur la fente où le biais vaut 0.
    for (var i = li; i < 4096u; i += 128u) {
        let e = lut_globale[i];
        if ((e >> 17u) == 0u) {
            lut_fc[e & 15u] = ((e >> 4u) & 0x1FFFu) | (i << 16u);
        }
    }
    if (p.casser == 1u && li == 0u) {
        lut_sym[1u] = lut_sym[1u] ^ 0x0100u;
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
    var dest = t.z + voie;
    for (var m = 0u; m < t.y; m++) {
        var mot = 0u;
        for (var k = 0u; k < 8u; k++) {
            let fente = x & 4095u;
            let s = (lut_sym[fente >> 2u] >> ((fente & 3u) * 8u)) & 15u;
            let fc = lut_fc[s];
            x = (fc & 0xFFFFu) * (x >> 12u) + fente - (fc >> 16u);
            mot |= s << (4u * k);
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
        sortie[dest] = mot;
        dest += 32u;
    }
    if (x != 65536u) {
        atomicAdd(&controle[0], 1u);
    }
}

// Référence : la même géométrie de lecture et d'écriture, sans décodage. Elle lit les
// demi-octets bruts (4,0 bits par code, liés à `mots`) et les recopie : c'est le chemin
// non compressé.

@compute @workgroup_size(128)
fn copier(
    @builtin(local_invocation_index) li: u32,
    @builtin(workgroup_id) gt: vec3<u32>,
    @builtin(subgroup_invocation_id) voie: u32,
    @builtin(subgroup_id) id_sg: u32,
    @builtin(num_subgroups) nb_sg: u32,
) {
    let tuile = gt.x * nb_sg + id_sg;
    if (tuile >= p.nb_tuiles) {
        return;
    }
    let t = tuiles[tuile];
    var dest = t.z + voie;
    for (var m = 0u; m < t.y; m++) {
        sortie[dest] = mots[dest];
        dest += 32u;
    }
}

// Version 4 : alphabet de 256 symboles (l'octet entier), table large de 16 Kio, même
// fenêtre que la v2. 4 sous-pas par mot de sortie au lieu de 8. Elle lit son propre
// flux (codé par coder_octets) : mêmes liaisons, autres contenus.
@compute @workgroup_size(128)
fn decoder_v4(
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
    var dest = t.z + voie;
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
        sortie[dest] = mot;
        dest += 32u;
    }
    if (x != 65536u) {
        atomicAdd(&controle[0], 1u);
    }
}

// Recopie de référence au débit de la mémoire : vec4 par invocation, boucle à pas de grille.
@group(0) @binding(7) var<storage, read> brut4: array<vec4<u32>>;
@group(0) @binding(8) var<storage, read_write> sortie4: array<vec4<u32>>;

@compute @workgroup_size(256)
fn copier_vec4(@builtin(global_invocation_id) gid: vec3<u32>, @builtin(num_workgroups) ng: vec3<u32>) {
    let n = arrayLength(&brut4);
    let pas = ng.x * 256u;
    for (var i = gid.x; i < n; i += pas) {
        sortie4[i] = brut4[i];
    }
}
