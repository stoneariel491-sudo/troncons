"""Résumé d'une échelle de quantification produite par quant-echelle.sh.

Lit, dans un dossier de journaux, pour chaque type : <nom>-<type>-bits.json (bits réels,
octets lus par jeton), <nom>-<type>-kld.log (perplexité, rapport à la base, divergence
KL moyenne, accord du premier jeton) et <nom>-durees.txt (temps de quantification).
Rend un tableau Markdown et un JSON.

Usage : python quant-resume-echelle.py <dossier_journaux> <nom> [--json sortie.json]
"""
import glob
import json
import os
import re
import sys


def lire_kld(chemin):
    t = open(chemin, encoding="utf-8", errors="replace").read()
    def num(motif):
        m = re.search(motif, t)
        return (float(m.group(1)), float(m.group(2))) if m else (None, None)
    return {
        "ppl": num(r"Mean PPL\(Q\)\s*:\s*([\d.]+)\s*±\s*([\d.]+)"),
        "ppl_base": num(r"Mean PPL\(base\)\s*:\s*([\d.]+)\s*±\s*([\d.]+)"),
        "rapport": num(r"Mean PPL\(Q\)/PPL\(base\)\s*:\s*([\d.]+)\s*±\s*([\d.]+)"),
        "kld": num(r"Mean\s+KLD:\s*([\d.]+)\s*±\s*([\d.]+)"),
        "meme_premier": num(r"Same top p:\s*([\d.]+)\s*±\s*([\d.]+)"),
    }


def main():
    dossier, nom = sys.argv[1], sys.argv[2]
    sortie_json = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    durees = {}
    fd = os.path.join(dossier, f"{nom}-durees.txt")
    if os.path.exists(fd):
        for ligne in open(fd, encoding="utf-8"):
            p = ligne.split()
            if p and p[0] == "quantize":
                durees[p[2]] = float(p[-1])
            elif p and p[0] == "imatrix":
                durees["imatrix"] = float(p[-1])
    lignes = []
    for fb in sorted(glob.glob(os.path.join(dossier, f"{nom}-*-bits.json"))):
        typ = os.path.basename(fb)[len(nom) + 1:-len("-bits.json")]
        d = json.load(open(fb, encoding="utf-8"))
        d = d[0] if isinstance(d, list) else d
        fk = os.path.join(dossier, f"{nom}-{typ}-kld.log")
        k = lire_kld(fk) if os.path.exists(fk) else {}
        lignes.append({"type": typ, "bpp_tenseurs": d["bpp_tenseurs"], "bpp_fichier": d["bpp_fichier"],
                       "octets_lus_par_jeton": d["octets_lus_par_jeton"],
                       "quantize_s": durees.get(typ), **k})
    lignes.sort(key=lambda r: -r["bpp_tenseurs"])
    print(f"| type | bits/poids (tenseurs) | Go lus/jeton | PPL | PPL/base | KLD moyenne | même 1er jeton % | quantif. s |")
    print("|---|---|---|---|---|---|---|---|")
    for r in lignes:
        f = lambda v, n=3: "—" if not v or v[0] is None else f"{v[0]:.{n}f} ± {v[1]:.{n}f}"
        print(f"| {r['type']} | {r['bpp_tenseurs']:.3f} | {r['octets_lus_par_jeton']/1e9:.3f} | "
              f"{f(r.get('ppl'), 3)} | {f(r.get('rapport'), 4)} | {f(r.get('kld'), 4)} | "
              f"{f(r.get('meme_premier'), 2)} | {r['quantize_s'] or '—'} |")
    if "imatrix" in durees:
        print(f"\nimatrix : {durees['imatrix']} s")
    if sortie_json:
        json.dump({"nom": nom, "durees": durees, "types": lignes}, open(sortie_json, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
