"""R1 : la référence f64 de gpt-oss, et son jugement contre llama.cpp (ARCHITECTURE.md § 6.5, lot R).

Ce que l'étape établit : `trc-reference` calcule bien gpt-oss. Critère du § 6.5 :
KL(référence ‖ llama.cpp carte) ≤ max(G_moteurs, 7e-5) sur 10 fenêtres de 512 ; cassure : une erreur
injectée (YaRN sans son échelle de concentration) doit faire tomber le témoin.

SEUILS ET TÉMOINS DÉCLARÉS AVANT LE LANCEMENT (2026-10-15) :
  W1 deux chemins de la référence : `pas` (jeton par jeton, cache KV f64) = `evaluer` (par lots) au
     bit, sur les 24 premiers jetons de la fenêtre 0 ; cassure : `pas` avec l'autre rampe YaRN →
     au moins un logit différent ;
  W2 découpage : les jetons de trc-jetons sur wiki.test.raw égalent ceux du fichier .kld de
     llama-perplexity (les 5 120 premiers) ;
  R1 (§ 6.5) : KL(référence ‖ llama.cpp carte_cmoe) ≤ max(G_moteurs, 7e-5), G_moteurs lu dans
     r0/r0-resume.json ; chemin 1 : llama-perplexity --kl-divergence contre la base écrite par la
     référence ; chemin 2 : `juge kl` entre les deux fichiers .kld ;
  R1-cassure : la référence sans l'échelle de YaRN, même critère : doit tomber ;
  Y (mesure, non jugée) : la référence avec la rampe arrondie de llama.cpp, contre la même base :
     l'écart que fait l'arrondi de ggml_rope_yarn_corr_dims, et laquelle des deux rampes llama.cpp
     approche.
  I (décomposition, ajoutée à la reprise du 2026-10-15 après la première passe, qui donne
     KL(llama processeur ‖ référence) = 0,0255 et 90,4 % de premier choix identique ; déclarée
     AVANT les passes d'imitation) : la référence avec la rampe de llama.cpp, puis avec les
     activations Q8_0 de ggml (q8), puis avec le cache KV en f16 (kv16). Hypothèse : l'écart vient
     des approximations de llama.cpp, pas d'un défaut de la référence. Elle TIENT si la KL de
     ref-llamacpp-imite-q8-kv16 contre la base du processeur tombe à ≤ 2,5e-3 (au moins dix fois
     moins : l'écart expliqué à 90 % au moins) ; sinon un défaut de la référence reste à chercher
     avant tout jugement R1. Ce qui reste après imitation (sommes en f32, softmax f32, requête en
     f16 de l'attention éclair) n'est pas imité.
  RÉSULTAT DE I (16 h 42) : I TOMBE. KL 0,0220 (rampe llama.cpp seule : 0,0273). Puis, entre
     deux références : rampe seule changée, KL 0,0145 (médiane 9,8e-4, premier choix 92,5 %) ;
     imitations seules ajoutées, KL 0,029. Le modèle amplifie toute perturbation de l'ordre de 1e-3
     en une KL de l'ordre de 2e-2 à queue lourde : le seuil de I supposait un régime linéaire.
  D (déclaré à 16 h 50, avant la passe) : la référence rejouée (ref-openai-bis) écrit un .kld
     identique octet pour octet à ref-openai.
  B (déclaré à 16 h 50, avant la passe ; hypothèse des bascules de routage : quand le 4e et le
     5e logit du routeur sont presque égaux, une perturbation infime change d'expert, et l'écart
     se propage par le résidu et le cache KV) : la référence à la rampe de llama.cpp, mais avec les
     experts imposés depuis ref-openai-bis, tombe à KL ≤ 1e-3 contre ref-openai (au moins 14 fois
     moins que 0,0145 sans imposition). Si B tient, le reste est l'effet propre de la rampe.
  RÉSULTAT DE D (17 h 01) : D TIENT (ref-openai-bis = ref-openai octet pour octet).
  RÉSULTAT DE B (17 h 17) : B TOMBE au seuil déclaré : KL 1,68e-3 > 1e-3. Mais l'imposition retire
     88 % de la KL (0,0145 → 0,00168), la médiane passe de 9,8e-4 à 2,2e-4, le 99e centile de 0,29 à
     0,031, le premier choix de 92,5 % à 97,2 %. Les bascules de routage sont le premier
     amplificateur, pas le seul : il reste une queue (max 0,53) que l'effet propre de la rampe ne
     suffit pas à expliquer en régime linéaire.
Les fichiers .kld (≈ 1 Go chacun) restent hors du dépôt, sous ~/dev/essais/troncons/lot-R ;
leurs empreintes SHA-256 et les journaux sont commités ici.

Usage : python -I -X utf8 r1_reference.py <temoins|reference|cassure|yarn-llamacpp|imitation|bis|bis-llamacpp|impose|carte|resume> [--modele 20b|120b]
       [--variante openai|llamacpp --imiter q8[,kv16]]
       [--suffixe -x] [--seul-w1]
"""

import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import time

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import r0_ecart as r0  # noqa: E402  (même verrou, mêmes chemins, même relevé d'environnement)

JOURNAUX = ICI / "r1"
LOURDS = pathlib.Path("~/dev/essais/troncons/lot-R/r1")
MODELES = {"20b": r0.M20, "120b": r0.M120}
FILS = "4"


def lancer(cmd, journal):
    avant = r0.environnement()
    t0 = time.time()
    with open(journal, "w", encoding="utf-8") as f:
        f.write(f"# {r0.horodate()} {' '.join(map(str, cmd))}\n# avant : {json.dumps(avant, ensure_ascii=False)}\n")
        f.flush()
        r = subprocess.run([str(c) for c in cmd], stdout=f, stderr=subprocess.STDOUT)
        f.write(f"\n# fin {r0.horodate()} code {r.returncode} durée {time.time() - t0:.1f} s\n")
    print(f"{journal.name} : code {r.returncode}, {time.time() - t0:.1f} s", flush=True)
    return r.returncode


def base_llama(modele):
    """La base llama.cpp carte_cmoe du modèle (écrite par R0 pour le 20b)."""
    if modele == "20b":
        return r0.LOURDS / "carte_cmoe.kld"
    return LOURDS / f"llama-carte_cmoe-{modele}.kld"


def jetons_de(modele):
    """Un fichier .kld de llama.cpp pour les jetons (le découpage ne dépend pas du moteur ; W2 le
    vérifie). La base du processeur seul existe sans la carte ; celle de la carte la remplace dès
    qu'elle existe."""
    b = base_llama(modele)
    if b.exists():
        return b
    return r0.LOURDS / "processeur.kld"


def temoins(modele, suffixe="", seul_w1=False):
    """`suffixe` : rejouer les témoins après un changement de code sans écraser les journaux
    d'avant (ex. « -pavage » après le pavage de Matrice::produit, reprise du 2026-10-15)."""
    m = MODELES[modele]
    b = jetons_de(modele)
    lancer([r0.JUGE, "temoin-chemins", "--gguf", m, "--kld", b, "--n", "24", "--fils", FILS], JOURNAUX / f"W1-chemins-{modele}{suffixe}.log")
    lancer([r0.JUGE, "temoin-chemins", "--gguf", m, "--kld", b, "--n", "24", "--fils", FILS, "--casser"], JOURNAUX / f"W1-chemins-casse-{modele}{suffixe}.log")
    if not seul_w1:
        lancer([r0.JUGE, "jetons", "--dll", r0.LLAMA / "llama.dll", "--vocab", m, "--texte", r0.DONNEES / "wiki.test.raw", "--kld", b], JOURNAUX / f"W2-jetons-{modele}{suffixe}.log")


def reference(modele, variante="openai", cassure=False, imiter=None, suffixe="", imposer=None):
    """`imiter` (« q8 », « q8,kv16 ») : réintroduit les approximations de llama.cpp dans la référence
    (mesure de décomposition de l'écart, jamais la référence ; voir trc-reference::Imitation)."""
    m = MODELES[modele]
    nom = f"ref-{variante}" + ("-sans-echelle" if cassure else "") + (f"-imite-{imiter.replace(',', '-')}" if imiter else "") + suffixe + f"-{modele}"
    cmd = [r0.JUGE, "reference", "--gguf", m, "--jetons-de", jetons_de(modele), "--sortie", LOURDS / f"{nom}.kld",
           "--fenetres", str(r0.FENETRES), "--yarn", variante, "--fils", FILS, "--journal", JOURNAUX / f"{nom}.json", "--kl-contre-base"]
    if cassure:
        cmd.append("--casser-yarn")
    if imiter:
        cmd += ["--imiter", imiter]
    (JOURNAUX / "routage").mkdir(exist_ok=True)
    cmd += ["--routage", JOURNAUX / "routage" / f"{nom}.bin"]
    if imposer:
        cmd += ["--imposer-routage", JOURNAUX / "routage" / f"{imposer}.bin"]
    return lancer(cmd, JOURNAUX / f"{nom}.log")


def carte(modele):
    """Chemin 1 : llama-perplexity (carte, experts en RAM) jugé contre chaque base de la référence."""
    r0.prendre_verrou()
    try:
        # Chemin 1 pour les seules passes jugées ou mesurées (R1, cassure, rampe de llama.cpp) ; les
        # passes « bis » sont identiques au bit (D), les imitations et le routage imposé sont des
        # expériences entre références (chemin 2 seulement).
        for f in [LOURDS / f"ref-{v}-{modele}.kld" for v in ("openai", "openai-sans-echelle", "llamacpp")]:
            cmd = [r0.LLAMA / "llama-perplexity.exe", "-m", MODELES[modele], "-ngl", "99", "--cpu-moe", *r0.COMMUN,
                   "--kl-divergence-base", f, "--kl-divergence"]
            lancer(cmd, JOURNAUX / f"llama-carte_cmoe-contre-{f.stem}.log")
    finally:
        r0.rendre_verrou()


def role_de(nom, modele):
    """Le rôle d'une passe dans le jugement, par son nom exact (une sous-chaîne ne suffit pas :
    « ref-llamacpp-routage-openai » contient « openai », corrigé le 2026-10-15)."""
    roles = {
        f"ref-openai-{modele}": "R1",
        f"ref-openai-bis-{modele}": "R1 (passe rejouée, identique au bit : D)",
        f"ref-openai-sans-echelle-{modele}": "cassure (doit tomber)",
        f"ref-llamacpp-{modele}": "mesure Y (non jugée)",
        f"ref-llamacpp-bis-{modele}": "mesure Y (passe rejouée, identique au bit)",
        f"ref-llamacpp-routage-openai-{modele}": "expérience B, routage imposé (non jugée contre llama.cpp)",
    }
    if nom in roles:
        return roles[nom]
    if "-imite-" in nom:
        return "imitation de llama.cpp (décomposition, non jugée)"
    return "inconnu"


def resume(modele):
    res = {"date": r0.horodate(), "modele": modele, "environnement": r0.environnement(), "empreintes": {}, "chemin1": {}, "chemin2": {}, "seuils": {}}
    for f in sorted(LOURDS.glob(f"*-{modele}.kld")):
        res["empreintes"][f.name] = r0.sha256(f)
    r0res = json.loads((r0.JOURNAUX / "r0-resume.json").read_text(encoding="utf-8"))
    g = r0res.get("G_moteurs")
    seuil = max(g if g is not None else 0.0, 7e-5)
    res["G_moteurs"] = g
    res["seuil_R1"] = seuil
    b = base_llama(modele)
    for f in sorted(LOURDS.glob(f"ref-*-{modele}.kld")):
        log = JOURNAUX / f"llama-carte_cmoe-contre-{f.stem}.log"
        if log.exists():
            res["chemin1"][f.stem] = r0.lire_stats(log)
        res["chemin2"][f.stem] = r0.juge_kl(f, b, f"llama-carte_cmoe-contre-{f.stem}")
        # sens inverse, KL(llama ‖ référence), pour mémoire
        res["chemin2"][f"inverse-{f.stem}"] = r0.juge_kl(b, f, f"{f.stem}-contre-llama-carte_cmoe")
    for nom, valeurs in res["chemin2"].items():
        if nom.startswith("inverse-"):
            continue
        kl2 = valeurs["kl_moyenne"]
        kl1 = res["chemin1"].get(nom, {}).get("kl_moyenne", [None])[0]
        juge = kl1 if kl1 is not None else kl2
        attendu_tombe = "sans-echelle" in nom
        res["seuils"][nom] = {"kl_chemin1": kl1, "kl_chemin2": kl2, "seuil": seuil, "sous_le_seuil": juge <= seuil,
                              "role": role_de(nom, modele)}
    texte = json.dumps(res, ensure_ascii=False, indent=2)
    (JOURNAUX / f"r1-resume-{modele}.json").write_text(texte, encoding="utf-8")
    print(texte)


if __name__ == "__main__":
    JOURNAUX.mkdir(parents=True, exist_ok=True)
    LOURDS.mkdir(parents=True, exist_ok=True)
    etape = sys.argv[1]
    modele = sys.argv[sys.argv.index("--modele") + 1] if "--modele" in sys.argv else "20b"
    suffixe = sys.argv[sys.argv.index("--suffixe") + 1] if "--suffixe" in sys.argv else ""
    if etape == "temoins":
        temoins(modele, suffixe, seul_w1="--seul-w1" in sys.argv)
    elif etape == "reference":
        reference(modele)
    elif etape == "cassure":
        reference(modele, cassure=True)
    elif etape == "yarn-llamacpp":
        reference(modele, variante="llamacpp")
    elif etape == "imitation":
        # python r1_reference.py imitation --variante llamacpp --imiter q8,kv16
        variante = sys.argv[sys.argv.index("--variante") + 1] if "--variante" in sys.argv else "llamacpp"
        reference(modele, variante=variante, imiter=sys.argv[sys.argv.index("--imiter") + 1])
    elif etape == "bis":
        # Déterminisme de la référence (D) et journal de routage de la rampe d'OpenAI.
        reference(modele, suffixe="-bis")
    elif etape == "bis-llamacpp":
        # D pour la rampe de llama.cpp, et son journal de routage (pour compter les bascules).
        reference(modele, variante="llamacpp", suffixe="-bis")
    elif etape == "impose":
        # Expérience B : la rampe de llama.cpp, le routage de ref-openai-bis imposé.
        reference(modele, variante="llamacpp", suffixe="-routage-openai", imposer=f"ref-openai-bis-{modele}")
    elif etape == "carte":
        carte(modele)
    elif etape == "resume":
        resume(modele)
    else:
        raise SystemExit(f"étape inconnue : {etape}")
