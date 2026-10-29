"""Témoin des témoins de F1 (SOCLE : « force sa condition à faux, relance, vérifie que
l'instrument tombe, puis restaure »).

Chaque cassure remplace une chaîne exacte du code (elle doit y figurer une seule fois),
relance les tests de trc-format et trc-codec, note lesquels tombent, puis réécrit le fichier
d'origine octet pour octet et vérifie son SHA-256.

Usage : python -I -X utf8 mesures/moteur/F/casser_temoins_f1.py <espace cargo qui dépend de trc-codec>
"""
import hashlib, os, re, subprocess, sys

ESPACE = sys.argv[1]
M = "~/dev/active/troncons/moteur/crates"
ENV = dict(os.environ, CARGO_TARGET_DIR="~/dev/cibles/troncons-F", CARGO_INCREMENTAL="1")

CASSURES = [
    ("LUT de géométrie 1 : f au lieu de f − 1", "trc-codec/src/rans.rs", "((f - 1) << 8)", "(f << 8)"),
    ("codeur : renormalise à f << 19 au lieu de f << 20", "trc-codec/src/rans.rs", "if xv >= f << 20 {", "if xv >= f << 19 {"),
    ("décodeur par voie : bloc n / 8 au lieu de n / 16", "trc-codec/src/rans.rs",
     "decoder_avec(flux, |n, _| Some(*kappa.get(n / 16).unwrap_or(&0)), luts)",
     "decoder_avec(flux, |n, _| Some(*kappa.get(n / 8).unwrap_or(&0)), luts)"),
    ("décodeur : ne compte pas les voies hors de L", "trc-codec/src/rans.rs",
     "let hors = x.iter().filter(|&&v| v != L).count() as u64;", "let hors = 0u64;"),
    ("décodeur : ne vérifie pas les mots consommés", "trc-codec/src/rans.rs",
     "let mots_faux = deborde || p != fin;", "let mots_faux = false;"),
    ("en-tête : colonnes écrites à 100 au lieu de 96", "trc-format/src/lib.rs",
     "eu32(&mut b, 96 + 4 * j, self.colonnes[j]);", "eu32(&mut b, 100 + 4 * j, self.colonnes[j]);"),
    ("lecture : empreinte de l'en-tête non vérifiée", "trc-format/src/lib.rs", "if e_lue != e_calc {", "if e_lue != e_calc && false {"),
    ("lecture : sorte 0x05 acceptée comme CODES_CTX", "trc-format/src/lib.rs", "0x04 => Sorte::CodesCtx,", "0x04 | 0x05 => Sorte::CodesCtx,"),
    ("reconstruction : e = méd + δ − 127", "trc-codec/src/lib.rs", "wrapping_add(delta[beta]).wrapping_sub(128)", "wrapping_add(delta[beta]).wrapping_sub(127)"),
]

def lancer():
    r = subprocess.run(["cargo", "test", "--offline", "-j", "4", "-p", "trc-format", "-p", "trc-codec"],
                       cwd=ESPACE, env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace")
    sortie = r.stdout + r.stderr
    res = sorted(set(re.findall(r"^test (\S+) \.\.\. (ok|FAILED)$", sortie, re.M)))
    if "error[" in sortie or "could not compile" in sortie:
        res.append(("compilation", "ÉCHEC"))
    return res

def h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]

print("=== référence (rien de cassé)")
ref = lancer()
for t, s in ref:
    print(f"  {s:6} {t}")
tous_tombent = all(s == "ok" for _, s in ref)
for nom, f, motif, remplace in CASSURES:
    p = f"{M}/{f}"
    origine = open(p, "rb").read()
    texte = origine.decode("utf-8")
    n = texte.count(motif)
    print(f"=== cassure : {nom} ({f}, {h(p)})")
    if n != 1:
        print(f"  MOTIF TROUVÉ {n} FOIS : cassure non appliquée")
        tous_tombent = False
        continue
    open(p, "wb").write(texte.replace(motif, remplace).encode("utf-8"))
    try:
        res = lancer()
    finally:
        open(p, "wb").write(origine)
    tombes = [t for t, s in res if s != "ok"]
    print(f"  tombent : {', '.join(tombes) if tombes else 'AUCUN'}")
    print(f"  restauré : {'oui' if h(p) == hashlib.sha256(origine).hexdigest()[:16] else 'NON'} ({h(p)})")
    tous_tombent &= bool(tombes)
print("=== référence après restauration")
fin = lancer()
print(f"  identique à la première : {fin == ref}")
print(f"BILAN : chaque cassure fait tomber au moins un témoin : {tous_tombent}")
