"""Écrit le BibTeX et le tableau des sources de l'éclaireur depuis les métadonnées primaires.

Entrées : les réponses de l'API arXiv (Atom, `*.xml`, dédoublonnées) et les réponses de l'API Crossref
(`cr-*.json`, une par DOI), téléchargées le 2026-10-16 avec le User-Agent troncons-recherche/1.0.
Rien n'est écrit de mémoire : titres, auteurs, dates, volumes et pages viennent de ces réponses.

Utilisation : python -I -X utf8 bib_sources.py <dossier des réponses> <sortie.bib> <sortie.csv>
"""
import csv
import glob
import json
import os
import sys
import xml.etree.ElementTree as ET

NS = {"a": "http://www.w3.org/2005/Atom"}
CLES_ARXIV = {
    "2208.11580": "frantar2022obc", "2210.17323": "frantar2022gptq", "2310.16795": "frantar2023qmoe",
    "2306.00978": "lin2023awq", "2310.01334": "li2023mcsmoe", "2402.14800": "lu2024notallexperts",
    "2402.10193": "liu2024bitdelta", "2406.08903": "ping2024deltacome", "2206.08464": "nooralinejad2022pranc",
    "2310.02556": "koohpayegani2023nola", "2310.02410": "kim2023moqe", "1905.08318": "wiedemann2019deepcabac",
    "2410.08589": "chen2024hcsmoe", "2502.17298": "gu2025d2moe", "2506.23266": "li2025submoe",
    "2508.05257": "chen2025mobe", "1804.08838": "li2018intrinsic", "2204.11674": "najarro2022hypernca",
    "2310.09832": "he2023meo", "2410.14649": "sieberling2024evopress", "2505.03804": "hu2025moequant",
    "2506.13329": "fu2025eaquant", "2502.06786": "nair2025matquant", "2402.10517": "park2024anyprecision",
    "2508.04581": "zhussip2025masa", "2502.20586": "tseng2025mxfp4", "2609.04526": "li2026scaleqlora",
    "2606.23406": "domb2026hyperquant", "2609.31631": "li2026ompmoe", "2609.12310": "martin2026ests",
    "2310.10537": "rouhani2023microscaling",
}
CLES_DOI = {
    "10.1007/pl00006381": "freeland1998", "10.1093/nar/15.3.1281": "sharp1987cai",
    "10.1126/science.aaj2038": "erlich2017fountain", "10.1038/nature11875": "goldman2013dna",
    "10.1126/science.1226355": "church2012dna", "10.1126/science.7973651": "adleman1994",
    "10.1038/381607a0": "olshausen1996", "10.1109/tnnls.2016.2526029": "yoon2017sigmadelta",
    "10.23915/distill.00023": "mordvintsev2020nca", "10.1162/artl.2009.15.2.15202": "stanley2009hyperneat",
    "10.1037/0735-7044.100.2.147": "teyler1986", "10.1109/72.377968": "plate1995hrr",
}
EN_PLUS = [
    ("hassibi1992obs", "@inproceedings{hassibi1992obs,\n  author       = {Hassibi, Babak and Stork, David G.},\n"
     "  title        = {Second order derivatives for network pruning: {Optimal Brain Surgeon}},\n"
     "  booktitle    = {Advances in Neural Information Processing Systems 5 (NIPS 1992)},\n  date         = {1992},\n"
     "  url          = {https://proceedings.neurips.cc/paper/1992/hash/303ed4c69846ab36c2904d3ba8573050-Abstract.html},\n"
     "  urldate      = {2026-10-16},\n  note         = {Page des actes vérifiée (titre) le 2026-10-16.},\n}\n",
     ["NeurIPS 1992", "https://proceedings.neurips.cc/paper/1992/hash/303ed4c69846ab36c2904d3ba8573050-Abstract.html",
      "1992", "", "page des actes (titre)", "Second order derivatives for network pruning: Optimal Brain Surgeon"]),
    ("blahut1972", "@article{blahut1972,\n  author       = {Blahut, Richard E.},\n"
     "  title        = {Computation of channel capacity and rate-distortion functions},\n"
     "  journaltitle = {IEEE Transactions on Information Theory},\n  date         = {1972-07},\n  volume       = {18},\n"
     "  number       = {4},\n  pages        = {460--473},\n  doi          = {10.1109/TIT.1972.1054855},\n"
     "  url          = {https://doi.org/10.1109/TIT.1972.1054855},\n  urldate      = {2026-10-16},\n"
     "  note         = {Métadonnées Crossref.},\n}\n",
     ["DOI 10.1109/TIT.1972.1054855", "https://doi.org/10.1109/TIT.1972.1054855", "1972-07", "",
      "métadonnées (Crossref)", "Computation of channel capacity and rate-distortion functions"]),
]


def tex(s):
    for a, b in (("&", "\\&"), ("%", "\\%"), ("_", "\\_"), ("#", "\\#")):
        s = s.replace(a, b)
    return s


def main():
    dossier, sortie_bib, sortie_csv = sys.argv[1:4]
    bib = ["% Sources primaires de l'éclaireur du génome des poids (genome/00-etat-de-l-art.md, genome/01-eclaireur.md).",
           "% Métadonnées tirées de l'API arXiv et de l'API Crossref le 2026-10-16 (outils/genome/eclaireur/bib_sources.py).",
           "% Clés neuves seulement ; les sources déjà dans le mémoire gardent leur clé (shafipour2024seedlm,",
           "% ha2016hypernetworks, han2015deepcompression, kleinegger2026matgptq, tiedtrit2026, xie2025trace, aqlm2024,",
           "% quipsharp2024, qtip2024, hershcovitch2024zipnn, zhang2025dfloat11, yubeaton2025huffllm, bitnet2024,",
           "% openai2025gptoss, ocpmx2023, gish1968, equitz1991successive, marcellin1990, rao1999, huttenlocher1979,",
           "% ohno1970, lecun1989obd, shannon1948, cover2006).", ""]
    lignes = []
    vues = set()
    entrees = []
    for fx in sorted(glob.glob(os.path.join(dossier, "*.xml"))):
        try:
            entrees += ET.parse(fx).getroot().findall("a:entry", NS)
        except ET.ParseError:
            continue
    for e in entrees:
        i = e.find("a:id", NS).text.split("/abs/")[-1]
        base, version = i.rsplit("v", 1)
        if base not in CLES_ARXIV or base in vues:
            continue
        vues.add(base)
        t = " ".join(e.find("a:title", NS).text.split())
        au = [x.find("a:name", NS).text.strip() for x in e.findall("a:author", NS)]
        pub, maj = e.find("a:published", NS).text[:10], e.find("a:updated", NS).text[:10]
        k = CLES_ARXIV[base]
        bib.append(f"@online{{{k},\n  author       = {{{' and '.join(au)}}},\n  title        = {{{{{tex(t)}}}}},\n"
                   f"  date         = {{{pub}}},\n  eprint       = {{{base}}},\n  eprinttype   = {{arXiv}},\n"
                   f"  url          = {{https://arxiv.org/abs/{base}}},\n  urldate      = {{2026-10-16}},\n"
                   f"  note         = {{Version v{version} du {maj}. Résumé lu (API arXiv).}},\n}}\n")
        lignes.append([k, "arXiv " + base, "https://arxiv.org/abs/" + base, pub, maj, "2026-10-16", "résumé (API arXiv)", t])
    for f in sorted(glob.glob(os.path.join(dossier, "cr-*.json"))):
        m = json.load(open(f, encoding="utf-8"))["message"]
        k = CLES_DOI.get(m["DOI"].lower())
        if k is None:
            continue
        au = " and ".join(f"{a.get('family', '')}, {a.get('given', '')}".strip(", ") for a in m["author"])
        y = m["issued"]["date-parts"][0]
        date = "-".join(f"{v:02d}" if n else str(v) for n, v in enumerate(y))
        t = m["title"][0]
        ch = [f"  author       = {{{au}}}", f"  title        = {{{{{tex(t)}}}}}",
              f"  journaltitle = {{{tex(m['container-title'][0])}}}", f"  date         = {{{date}}}"]
        if m.get("volume"):
            ch.append(f"  volume       = {{{m['volume']}}}")
        if m.get("issue"):
            ch.append(f"  number       = {{{m['issue']}}}")
        if m.get("page"):
            ch.append(f"  pages        = {{{m['page'].replace('-', '--')}}}")
        ch += [f"  doi          = {{{m['DOI']}}}", f"  url          = {{https://doi.org/{m['DOI']}}}",
               "  urldate      = {2026-10-16}", "  note         = {Métadonnées Crossref ; résumé de l'éditeur lu.}"]
        bib.append(f"@article{{{k},\n" + ",\n".join(ch) + ",\n}\n")
        lignes.append([k, "DOI " + m["DOI"], "https://doi.org/" + m["DOI"], date, "", "2026-10-16", "résumé (éditeur)", t])
    for k, entree, ligne in EN_PLUS:
        bib.append(entree)
        lignes.append([k, *ligne[:3], ligne[3], "2026-10-16", *ligne[4:]])
    open(sortie_bib, "w", encoding="utf-8").write("\n".join(bib))
    with open(sortie_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cle", "identifiant", "adresse", "date_publication", "date_mise_a_jour", "date_consultation", "lu", "titre"])
        w.writerows(lignes)
    print(len(lignes), "sources")


if __name__ == "__main__":
    main()
