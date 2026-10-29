// Extrait de outils/quant-vulkan-gemv/src/main.rs (commit 89b509c), lignes 50-61 :
// le décodeur du treillis à décalage, code « mul1 », dans le shader WGSL de la GEMV.
// Le gabarit SOMMEV du dépôt est remplacé ici par sa valeur dans la variante retenue
// (dot4U8Packed, ligne 509 du même fichier) ; rien d'autre n'est changé.
fn fenetre4(w0: u32, w1: u32, off: vec4<u32>) -> vec4<u32> {
    let c = min(off, vec4<u32>(31u));
    let bas = ((vec4<u32>(w0) >> c) | (vec4<u32>(w1) << (vec4<u32>(32u) - c))) & vec4<u32>(0xffffu);
    let d = select(vec4<u32>(0u), off - vec4<u32>(32u), off >= vec4<u32>(32u));
    let haut = (vec4<u32>(w1) >> d) & vec4<u32>(0xffffu);
    return select(bas, haut, off >= vec4<u32>(32u));
}
fn mul1v(e: vec4<u32>) -> vec4<f32> {
    let v = e * vec4<u32>(0x83DCD12Du);
    let s = vec4<u32>(dot4U8Packed(v.x, 0x01010101u), dot4U8Packed(v.y, 0x01010101u),
                      dot4U8Packed(v.z, 0x01010101u), dot4U8Packed(v.w, 0x01010101u));
    return (vec4<f32>(s) - vec4<f32>(510.0)) * (1.0 / 147.7);
}
