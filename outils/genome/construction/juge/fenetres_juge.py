"""Les fenêtres neuves du juge : dix fenêtres de 512 jetons de wiki.test que les lots n'ont pas vues.

Seuils : mesures/genome/construction/juge/00-seuils-declares.md, « Les fenêtres neuves » (commit 1f5fe0f).
Les lots ont évalué sur R1 (jetons 0 à 5 119 de wiki.test) et calibré sur les fenêtres 10 à 21 (jetons
5 120 à 11 263). On écarte un préfixe de 120 000 octets, qui doit compter au moins 11 776 jetons
(= 23 × 512) ; dix débuts de ligne de paragraphe sont tirés au-delà ; chaque extrait (9 000 octets
prolongés jusqu'à la fin de ligne) passe par llama-perplexity (processeur seul, options de R0) ; les
dix fichiers .kld d'une fenêtre sont fondus en un seul, au format de llama-perplexity (kld.rs du lot R).

  python -I -X utf8 fenetres_juge.py prefixe
  python -I -X utf8 fenetres_juge.py tirer
  python -I -X utf8 fenetres_juge.py perplexite
  python -I -X utf8 fenetres_juge.py fondre
"""
import hashlib
import json
import os
import pathlib
import struct
import subprocess
import sys
import time

import numpy as np

DEPOT = pathlib.Path(__file__).resolve().parents[4]
JOURNAUX = DEPOT / "mesures" / "genome" / "construction" / "juge"
LOURDS = pathlib.Path("~/dev/essais/troncons/genome/juge")
WIKI = pathlib.Path("~/dev/essais/troncons/modeles/donnees/wiki.test.raw")
LLAMA = pathlib.Path("~/dev/modeles/llama.cpp-b11515")
M20 = pathlib.Path("~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf")
PREFIXE = 120_000
MINIMUM_PREFIXE = 23 * 512
GRAINE = 20261022 + 1
N_FEN = 10
LONGUEUR = 9_000
ECART = 12_000
COMMUN = ["-c", "512", "-b", "512", "-t", "6", "--seed", "1", "--chunks", "1"]   # R0, une fenêtre


def sha(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest()


def env_processeur():
    e = dict(os.environ)
    e["CUDA_VISIBLE_DEVICES"] = "-1"
    return e


def jetons(texte_octets: bytes):
    tmp = LOURDS / "prefixe.txt"
    tmp.write_bytes(texte_octets)
    r = subprocess.run([str(LLAMA / "llama-tokenize.exe"), "-m", str(M20), "-f", str(tmp), "--ids", "--log-disable", "--no-bos"],
                       capture_output=True, env=env_processeur())
    sortie = r.stdout.decode("utf-8", errors="replace").strip().splitlines()
    liste = [l for l in sortie if l.startswith("[")]
    return json.loads(liste[-1])


def prefixe():
    raw = WIKI.read_bytes()
    n = len(jetons(raw[:PREFIXE]))
    d = {"wiki_sha256": sha(WIKI), "octets": len(raw), "prefixe_ecarte": PREFIXE, "jetons_du_prefixe": n,
         "minimum": MINIMUM_PREFIXE, "temoin_tient": n >= MINIMUM_PREFIXE}
    (JOURNAUX / "fenetres-prefixe.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(d)


def tirer():
    raw = WIKI.read_bytes()
    debuts = [i + 1 for i in range(len(raw) - 1) if raw[i] == 0x0A and PREFIXE <= i + 1 < len(raw) - ECART
              and raw[i + 1] == 0x20 and raw[i + 2] not in (0x3D, 0x0A)]       # ligne de paragraphe : « ␣x… », pas « ␣= »
    rng = np.random.Generator(np.random.PCG64(GRAINE))
    choisis = []
    essais = 0
    while len(choisis) < N_FEN:
        essais += 1
        s = debuts[int(rng.integers(len(debuts)))]
        if all(abs(s - c) > ECART for c in choisis):
            choisis.append(s)
    fen = []
    for i, s in enumerate(choisis):
        fin = raw.index(b"\n", s + LONGUEUR) + 1
        ext = raw[s:fin]
        ch = LOURDS / f"extrait-{i:02d}.txt"
        ch.write_bytes(ext)
        fen.append({"fenetre": i, "debut_octet": s, "fin_octet": fin, "sha256": hashlib.sha256(ext).hexdigest(),
                    "debut_texte": ext[:80].decode("utf-8", errors="replace")})
    d = {"graine": GRAINE, "generateur": "numpy.random.Generator(PCG64(20261022 + 1)) ; integers(len(debuts)) jusqu'à 10 débuts à plus de 12 000 octets les uns des autres",
         "debuts_candidats": len(debuts), "tirages": essais, "fenetres": fen}
    (JOURNAUX / "fenetres-tirage.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    for f in fen:
        print(f["fenetre"], f["debut_octet"], f["debut_texte"])


def perplexite():
    journal = []
    for i in range(N_FEN):
        ext = LOURDS / f"extrait-{i:02d}.txt"
        sortie = LOURDS / f"base-{i:02d}.kld"
        log = LOURDS / f"perplexite-{i:02d}.log"
        cmd = [str(LLAMA / "llama-perplexity.exe"), "-m", str(M20), "-f", str(ext), *COMMUN, "--kl-divergence-base", str(sortie)]
        t0 = time.time()
        with open(log, "wb") as f:
            r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=env_processeur())
        texte = log.read_text(encoding="utf-8", errors="replace")
        ppl = [l for l in texte.splitlines() if "Final estimate" in l or "[1]" in l]
        journal.append({"fenetre": i, "code": r.returncode, "secondes": time.time() - t0, "octets": sortie.stat().st_size if sortie.exists() else 0,
                        "lignes_ppl": ppl[-2:], "commande": " ".join(cmd).replace("\\", "/")})
        print(journal[-1], flush=True)
        if r.returncode != 0:
            break
    (JOURNAUX / "fenetres-perplexite.json").write_text(json.dumps(journal, ensure_ascii=False, indent=1), encoding="utf-8")


def lire_kld(chemin):
    b = pathlib.Path(chemin).read_bytes()
    assert b[:8] == b"_logits_"
    n_ctx, n_vocab, n_chunk = struct.unpack_from("<Iii", b, 8)
    tok = b[20:20 + 4 * n_ctx * n_chunk]
    nv = 2 * ((n_vocab + 1) // 2) + 4
    taille_entree = 2 * nv
    n_notees = n_ctx - 1 - n_ctx // 2
    corps = b[20 + 4 * n_ctx * n_chunk:]
    assert len(corps) == n_chunk * n_notees * taille_entree, (len(corps), n_chunk, n_notees, taille_entree)
    return n_ctx, n_vocab, n_chunk, tok, corps


def fondre():
    parts = [lire_kld(LOURDS / f"base-{i:02d}.kld") for i in range(N_FEN)]
    n_ctx, n_vocab = parts[0][0], parts[0][1]
    assert all(p[0] == n_ctx and p[1] == n_vocab and p[2] == 1 for p in parts)
    sortie = LOURDS / "base-juge-20b.kld"
    with open(sortie, "wb") as f:
        f.write(b"_logits_" + struct.pack("<Iii", n_ctx, n_vocab, N_FEN))
        for p in parts:
            f.write(p[3])
        for p in parts:
            f.write(p[4])
    # témoin : chaque fenêtre du fichier fondu redonne, octet pour octet, jetons et entrées de sa source
    n2, v2, c2, tok, corps = lire_kld(sortie)
    nv = 2 * ((n_vocab + 1) // 2) + 4
    n_notees = n_ctx - 1 - n_ctx // 2
    te = n_notees * 2 * nv
    egaux = [tok[4 * n_ctx * i: 4 * n_ctx * (i + 1)] == parts[i][3] and corps[te * i: te * (i + 1)] == parts[i][4] for i in range(N_FEN)]
    attendu = 20 + 4 * n_ctx * N_FEN + N_FEN * n_notees * 2 * nv
    # cassure : la fenêtre 3 lue à la place de la 4 ne doit pas redonner la source 4
    cassure_tombe = corps[te * 3: te * 4] != parts[4][4]
    d = {"sortie": str(sortie).replace("\\", "/"), "octets": sortie.stat().st_size, "octets_attendus": attendu,
         "fenetres_egales_a_leur_source": egaux, "temoin_tient": all(egaux) and sortie.stat().st_size == attendu,
         "cassure_fenetre_decalee_tombe": cassure_tombe, "sha256": sha(sortie),
         "jetons": [list(np.frombuffer(p[3], dtype="<i4")[:8].tolist()) for p in parts]}
    (JOURNAUX / "fenetres-fondre.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print({k: v for k, v in d.items() if k != "jetons"})


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    LOURDS.mkdir(parents=True, exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"prefixe": prefixe, "tirer": tirer, "perplexite": perplexite, "fondre": fondre}.get(cmd, lambda: print(__doc__))()


if __name__ == "__main__":
    main()
