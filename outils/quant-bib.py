"""Sources de l'étude 02 en BibTeX (biblatex) pour le mémoire : memoire/sources/quantification.bib.

Les articles arXiv sont relus par l'API export.arxiv.org (titre, auteurs, première et
dernière version, commentaire de publication) ; User-Agent neutre troncons-recherche/1.0.
Les dépôts et pages de projet sont écrits à la main ci-dessous, avec le commit lu et la
licence relevée dans le clone. Chaque entrée porte urldate = date de consultation.

Usage : python -I outils/quant-bib.py [AAAA-MM-JJ]
"""
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, "memoire", "sources", "quantification.bib")
CONSULTATION = sys.argv[1] if len(sys.argv) > 1 else "2026-10-15"

# (clé, identifiant arXiv)
ARXIV = [
    ("mx2023", "2310.10537"), ("aqlm2024", "2401.06118"), ("quipsharp2024", "2402.04396"),
    ("gptvq2024", "2402.15319"), ("bitnet2024", "2402.17764"), ("quarot2024", "2404.00456"),
    ("pvtuning2024", "2405.14852"), ("spinquant2024", "2405.16406"), ("qtip2024", "2406.11235"),
    ("efficientqat2024", "2407.11062"), ("vptq2024", "2409.17066"), ("bitnetcpp2024", "2410.16144"),
    ("precision2024", "2411.04330"), ("undertrained2024", "2411.17691"), ("higgs2024", "2411.17525"),
    ("paretoq2025", "2502.02631"), ("bitnet2b4t2025", "2504.12285"), ("qwen3quant2025", "2505.02214"),
    ("yaqa2025", "2505.22988"), ("ccq2025", "2507.07145"), ("qpalette2025", "2509.20214"),
    ("nvfp4pretrain2025", "2509.25149"), ("d2quant2026", "2602.02546"),
    ("universalite2026", "2602.05790"), ("gsq2026", "2604.18556"), ("bcjrqat2026", "2605.10655"),
    ("harp2026", "2605.29843"), ("tiedtrit2026", "2608.08910"), ("leech2026", "2609.02652"),
    ("bitcos2026", "2609.16338"), ("tetra2026", "2609.35465"), ("xortrellis2026", "2610.00432"),
    ("apexquant2026", "2610.07904"), ("curvetq2026", "2610.09212"), ("sage2026", "2610.14745"),
]

AUTRES = r"""
@inproceedings{proteus2026,
  author = {Yang, Zhengwu and Li, Xunchao and Cheng, Ke and Liu, Kunlong and Yang, Jianfeng and Wang, Haoshuang and Deng, Kaipeng and Dang, Qingqing and Sha, Yanlin and Ma, Yanjun and Yu, Dianhai},
  title = {Proteus: Lookup-free trellis-coded quantization by lattice-breaking compute codes for 2-bit {LLMs}},
  booktitle = {International Conference on Machine Learning (ICML)},
  date = {2026},
  note = {Cité d'après la bibliographie de CurveTQ (arXiv:2610.09212) ; aucune version arXiv trouvée le CONSULTATION},
}
@software{llamacpp,
  author = {{ggml-org}},
  title = {llama.cpp},
  url = {https://github.com/ggml-org/llama.cpp},
  version = {commit 843e7dc ; exécutables b11515 (2026-10-09)},
  date = {2026-10-15},
  urldate = {CONSULTATION},
  note = {Licence MIT},
}
@software{iklamacpp,
  author = {Kawrakow, Iwan},
  title = {ik\_llama.cpp},
  url = {https://github.com/ikawrakow/ik_llama.cpp},
  version = {commit ff29e0a},
  date = {2026-10-14},
  urldate = {CONSULTATION},
  note = {Licence MIT},
}
@software{exllamav3,
  author = {{turboderp-org}},
  title = {ExLlamaV3},
  url = {https://github.com/turboderp-org/exllamav3},
  version = {commit 058b863},
  date = {2026-10-14},
  urldate = {CONSULTATION},
  note = {Licence MIT},
}
@software{qtipcode,
  author = {{Cornell-RelaxML}},
  title = {qtip},
  url = {https://github.com/Cornell-RelaxML/qtip},
  version = {commit e90c668},
  date = {2025-06-21},
  urldate = {CONSULTATION},
  note = {Licence GPL-3.0},
}
@software{quipsharpcode,
  author = {{Cornell-RelaxML}},
  title = {quip-sharp},
  url = {https://github.com/Cornell-RelaxML/quip-sharp},
  version = {commit 1d8f873},
  date = {2024-10-29},
  urldate = {CONSULTATION},
  note = {Licence GPL-3.0},
}
@software{aqlmcode,
  author = {{Vahe1994}},
  title = {AQLM},
  url = {https://github.com/Vahe1994/AQLM},
  version = {commit e79a896},
  date = {2026-02-26},
  urldate = {CONSULTATION},
  note = {Licence Apache-2.0},
}
@software{vptqcode,
  author = {{Microsoft}},
  title = {VPTQ},
  url = {https://github.com/microsoft/VPTQ},
  version = {commit 942c315},
  date = {2025-04-25},
  urldate = {CONSULTATION},
  note = {Licence MIT},
}
@software{efficientqatcode,
  author = {{OpenGVLab}},
  title = {EfficientQAT},
  url = {https://github.com/OpenGVLab/EfficientQAT},
  version = {commit 39f37f3},
  date = {2026-04-10},
  urldate = {CONSULTATION},
  note = {Licence MIT},
}
@software{quarotcode,
  author = {{spcl}},
  title = {QuaRot},
  url = {https://github.com/spcl/QuaRot},
  version = {commit 5008669},
  date = {2024-11-26},
  urldate = {CONSULTATION},
  note = {Licence Apache-2.0},
}
@software{spinquantcode,
  author = {{facebookresearch}},
  title = {SpinQuant},
  url = {https://github.com/facebookresearch/SpinQuant},
  version = {commit 8f47aa3},
  date = {2025-02-14},
  urldate = {CONSULTATION},
  note = {Licence CC BY-NC 4.0 (non commerciale)},
}
@software{bitnetcode,
  author = {{Microsoft}},
  title = {BitNet (bitnet.cpp)},
  url = {https://github.com/microsoft/BitNet},
  version = {commit 0b341e5},
  date = {2026-07-27},
  urldate = {CONSULTATION},
  note = {Licence MIT},
}
@software{flutecode,
  author = {Guo, Han},
  title = {FLUTE},
  url = {https://github.com/HanGuo97/flute},
  version = {commit 9eb83a1},
  date = {2025-04-13},
  urldate = {CONSULTATION},
  note = {Licence Apache-2.0},
}
@software{llvqcode,
  author = {{pjmalandrino}},
  title = {llvq (Tetra)},
  url = {https://github.com/pjmalandrino/llvq},
  date = {2026-10-07},
  urldate = {CONSULTATION},
  note = {Licence Apache-2.0 (API GitHub) ; non cloné},
}
@software{gsqcode,
  author = {{IST-DASLab}},
  title = {GSQ},
  url = {https://github.com/IST-DASLab/GSQ},
  date = {2026-07-11},
  urldate = {CONSULTATION},
  note = {Licence Apache-2.0 (API GitHub) ; non cloné},
}
@software{qpalettecode,
  author = {{snu-mllab}},
  title = {Q-Palette},
  url = {https://github.com/snu-mllab/Q-Palette},
  date = {2026-01-22},
  urldate = {CONSULTATION},
  note = {Licence MIT (API GitHub) ; non cloné},
}
@online{pr4773,
  author = {Kawrakow, Iwan},
  title = {{SOTA} 2-bit quants (llama.cpp PR \#4773)},
  url = {https://github.com/ggml-org/llama.cpp/pull/4773},
  date = {2024-01-08},
  urldate = {CONSULTATION},
  note = {Ouverte le 2024-01-04, fusionnée le 2024-01-08},
}
@online{pr19726,
  title = {Portage des types IQ*\_K dans llama.cpp (PR \#19726)},
  url = {https://github.com/ggml-org/llama.cpp/pull/19726},
  date = {2026-02-23},
  urldate = {CONSULTATION},
  note = {Ouverte le 2026-02-19, fermée sans fusion le 2026-02-23},
}
@online{prismmlformats,
  author = {{PrismML}},
  title = {Bonsai formats ({Q1\_0}, {Q2\_0})},
  url = {https://docs.prismml.com/download/formats},
  urldate = {CONSULTATION},
  note = {Date de publication non affichée},
}
"""


def echapper(t):
    # Les exposants en mode mathématique des titres arXiv (« D$^2$Quant ») deviennent du texte.
    t = re.sub(r"\$\^\{?(\w+)\}?\$", r"@@SUP\1@@", " ".join(t.split()))
    t = re.sub(r"([&%#_$^])", r"\\\1", t)
    return re.sub(r"@@SUP(\w+)@@", r"\\textsuperscript{\1}", t)


def main():
    ids = ",".join(i for _, i in ARXIV)
    url = f"https://export.arxiv.org/api/query?id_list={ids}&max_results={len(ARXIV) + 5}"
    req = urllib.request.Request(url, headers={"User-Agent": "troncons-recherche/1.0"})
    xml = urllib.request.urlopen(req, timeout=60).read()
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    racine = ET.fromstring(xml)
    par_id = {}
    for e in racine.findall("a:entry", ns):
        ident = e.find("a:id", ns).text.rsplit("/", 1)[-1]
        base = ident.split("v")[0]
        par_id[base] = {
            "version": ident,
            "titre": e.find("a:title", ns).text,
            "auteurs": [a.find("a:name", ns).text for a in e.findall("a:author", ns)],
            "premiere": e.find("a:published", ns).text[:10],
            "derniere": e.find("a:updated", ns).text[:10],
            "commentaire": (e.find("x:comment", ns).text if e.find("x:comment", ns) is not None else ""),
        }
    manquants = [i for _, i in ARXIV if i not in par_id]
    if manquants:
        print("MANQUANTS :", manquants)
        sys.exit(1)
    morceaux = [f"% Sources de l'étude 02 (quantification extrême des poids). Produit par outils/quant-bib.py\n"
                f"% le {time.strftime('%Y-%m-%d %H:%M')} ; métadonnées arXiv relues par l'API export.arxiv.org.\n"]
    for cle, i in ARXIV:
        d = par_id[i]
        auteurs = " and ".join(echapper(a) for a in d["auteurs"])
        note = f"Première version {d['premiere']}, dernière {d['derniere']} ({d['version']})"
        if d["commentaire"]:
            note += f". {echapper(d['commentaire'])}"
        morceaux.append(
            f"@online{{{cle},\n  author = {{{auteurs}}},\n  title = {{{{{echapper(d['titre'])}}}}},\n"
            f"  eprint = {{{i}}},\n  eprinttype = {{arxiv}},\n  url = {{https://arxiv.org/abs/{i}}},\n"
            f"  date = {{{d['premiere']}}},\n  urldate = {{{CONSULTATION}}},\n  note = {{{note}}},\n}}\n")
    morceaux.append(AUTRES.replace("CONSULTATION", CONSULTATION))
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    with open(SORTIE, "w", encoding="utf-8") as f:
        f.write("\n".join(morceaux))
    print(f"{SORTIE} : {len(ARXIV)} articles arXiv + entrées manuelles")


if __name__ == "__main__":
    main()
