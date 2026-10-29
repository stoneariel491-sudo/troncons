"""Témoin des témoins de la lecture sans tampon de trc-codeur (gguf::lire_dans), F3.

Le témoin `gguf::tests::lectures_alignees_et_non_alignees` lit un fichier de contenu connu
(2 × 16 Mio + 5 granules + 1 234 octets) par un descripteur sans tampon et par un descripteur
ordinaire, à des décalages et longueurs alignés ou non, sur une ou plusieurs fenêtres de rebond.
Chaque cassure remplace une chaîne exacte du code (présente une seule fois), relance le test,
note s'il tombe, puis réécrit le fichier d'origine octet pour octet et vérifie son SHA-256.

Usage : python -I -X utf8 mesures/moteur/F/casser_lecture.py
"""
import hashlib, os, re, subprocess, sys
sys.stdout.reconfigure(line_buffering=True)

MOTEUR = "~/dev/active/troncons/moteur"
GGUF = f"{MOTEUR}/bins/trc-codeur/src/gguf.rs"
CODEUR = f"{MOTEUR}/bins/trc-codeur/src/coder.rs"
ENV = dict(os.environ, CARGO_TARGET_DIR="~/dev/cibles/troncons-F", CARGO_INCREMENTAL="1")

CASSURES = [
    (GGUF, "décalage dans la fenêtre faux d'un octet quand d mod 4096 = 17",
     "        let o_t = (de - pos) as usize;\n",
     "        let o_t = (de - pos) as usize + usize::from(d % 4096 == 17 && de - pos < 4000);\n"),
    (GGUF, "seule la première fenêtre est lue (les suivantes recopient l'ancien contenu du rebond)",
     "        while fait < besoin {\n",
     "        while fait < besoin && pos == a {\n"),
    # Première forme essayée (« if k == 0 && false ») : la boucle relit sans fin et le test ne
    # rend jamais la main (arrêté à la main au bout de 10 minutes) ; un témoin qui pend ne tombe
    # pas, il bloque. Forme retenue : la fin de fichier arrête la lecture sans erreur (le reste du
    # tampon garde ses zéros) ; et chaque lancement a un délai de 15 minutes.
    (GGUF, "fin de fichier non vue : une lecture qui rend 0 arrête la boucle sans erreur",
     "            if k == 0 {\n                bail!",
     "            if k == 0 {\n                break;\n            }\n            if false {\n                bail!"),
    # Le défaut réel de la première version (vu au recodage du 20b, erreur 87) : après la lecture
    # courte de la fin, une relecture au décalage non aligné. Le témoin doit le voir.
    (CODEUR, "SHA-256 du fichier : relecture après la lecture courte de la fin (décalage non aligné)",
     "            break;\n        }\n    }\n    Ok((h.finalize().into(), n))",
     "            ensure!(f.seek_read(t.tranche_mut(), n)? == 0, \"lecture courte\");\n            break;\n        }\n    }\n    Ok((h.finalize().into(), n))"),
]

def lancer():
    r = subprocess.run(["cargo", "test", "--release", "--offline", "-j", "4", "-p", "trc-codeur"],
                       cwd=MOTEUR, env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    sortie = r.stdout + r.stderr
    res = sorted(set(re.findall(r"^test (\S+) \.\.\. (ok|FAILED)$", sortie, re.M)))
    if "error[" in sortie or "could not compile" in sortie:
        res.append(("compilation", "ÉCHEC"))
    if not res:
        res.append(("aucun test (délai ou boucle sans fin ?)", "ÉCHEC"))
    return res

def h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

print("=== référence (rien de cassé)")
ref = lancer()
for t, s in ref:
    print(f"  {s:6} {t}")
tout = all(s == "ok" for _, s in ref)
for FICHIER, nom, motif, remplace in CASSURES:
    origine = open(FICHIER, "rb").read()
    h0 = h(FICHIER)
    texte = origine.decode("utf-8")
    n = texte.count(motif)
    print(f"=== cassure : {nom} ({FICHIER.rsplit('/', 1)[-1]})")
    if n != 1:
        print(f"  MOTIF TROUVÉ {n} FOIS : cassure non appliquée")
        tout = False
        continue
    open(FICHIER, "wb").write(texte.replace(motif, remplace).encode("utf-8"))
    try:
        res = lancer()
    finally:
        open(FICHIER, "wb").write(origine)
    tombe = any(s != "ok" for _, s in res)
    for t, s in res:
        print(f"  {s:6} {t}")
    print(f"  -> {'TOMBE' if tombe else 'NE TOMBE PAS'} ; fichier restauré : {h(FICHIER) == h0}")
    tout = tout and tombe and h(FICHIER) == h0
print("=== après restauration")
fin = lancer()
for t, s in fin:
    print(f"  {s:6} {t}")
print(f"VERDICT : {'toutes les cassures tombent, le témoin tient restauré' if tout and all(s == 'ok' for _, s in fin) else 'ÉCHEC'}")
