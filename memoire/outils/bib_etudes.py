"""Écrit les fichiers biblatex des études 04, 05 et 06 sous memoire/sources/.

Les entrées reprennent les listes de sources des livrables (fondations/04-chargement.md § 10,
05-sparsite.md § 11, 06-modeles.md § 12) : auteur, titre, adresse primaire, date de première
version et de dernière révision. Toutes consultées le 2026-10-15.
Usage : python -I -X utf8 memoire/outils/bib_etudes.py
"""
from pathlib import Path

SOURCES = Path(__file__).resolve().parent.parent / "sources"


def entree(cle, auteurs, titre, adresse, date, derniere=None, lieu=None, note=None):
    lignes = [f"@online{{{cle},", f"  author     = {{{auteurs}}},", f"  title      = {{{titre}}},",
              f"  date       = {{{date}}},"]
    if adresse.startswith("http"):
        lignes.append(f"  url        = {{{adresse}}},")
    else:  # identifiant arXiv
        lignes += [f"  eprint     = {{{adresse}}},", "  eprinttype = {arxiv},",
                   f"  url        = {{https://arxiv.org/abs/{adresse}}},"]
    notes = [n for n in (lieu, f"dernière version {derniere}" if derniere else None, note) if n]
    lignes.append("  urldate    = {2026-10-15}" + ("," if notes else ""))
    if notes:
        lignes.append("  note       = {" + " ; ".join(notes) + "}")
    lignes.append("}")
    return "\n".join(lignes) + "\n\n"


ETUDE_04 = [
    ("flexgen2023", "Sheng, Ying and others", "{FlexGen}: High-Throughput Generative Inference of Large Language Models with a Single {GPU}", "2303.06865", "2023-03-13", "2023-06-12", "ICML 2023"),
    ("llminflash2024", "Alizadeh, Keivan and others", "{LLM} in a Flash: Efficient Large Language Model Inference with Limited Memory", "2312.11514", "2023-12-12", "2024-07-30", "ACL 2024"),
    ("powerinfer2024", "Song, Yixin and others", "{PowerInfer}: Fast Large Language Model Serving with a Consumer-grade {GPU}", "2312.12456", "2023-12-16", "2024-12-12", "SOSP 2024"),
    ("powerinfer2_2024", "Xue, Zhenliang and others", "{PowerInfer-2}: Fast Large Language Model Inference on a Smartphone", "2406.06282", "2024-06-10", "2024-12-12"),
    ("mixtraloffload2023", "Eliseev, Artyom and Mazur, Denis", "Fast Inference of Mixture-of-Experts Language Models with Offloading", "2312.17238", "2023-12-28"),
    ("mixtral2024", "Jiang, Albert Q. and others", "Mixtral of Experts", "2401.04088", "2024-01-08"),
    ("moeinfinity2024", "Xue, Leyang and others", "{MoE-Infinity}: Efficient {MoE} Inference on Personal Machines with Sparsity-Aware Expert Cache", "2401.14361", "2024-01-25", "2025-03-12"),
    ("fiddler2025", "Kamahori, Keisuke and others", "{Fiddler}: {CPU-GPU} Orchestration for Fast Inference of Mixture-of-Experts Models", "2402.07033", "2024-02-10", "2025-05-01", "ICLR 2025"),
    ("promoe2024", "Song, Xiaoniu and others", "{ProMoE}: Fast {MoE}-based {LLM} Serving using Proactive Caching", "2410.22134", "2024-10-29", "2025-09-01"),
    ("hobbit2024", "Tang, Peng and others", "{HOBBIT}: A Mixed Precision Expert Offloading System for Fast {MoE} Inference", "2411.01433", "2024-11-03", "2024-11-06"),
    ("adapmoe2024", "Zhong, Shuzhang and others", "{AdapMoE}: Adaptive Sensitivity-based Expert Gating and Management for Efficient {MoE} Inference", "2408.10284", "2024-08-19"),
    ("expertflow2024", "He, Xin and others", "{ExpertFlow}: Optimized Expert Activation and Token Allocation for Efficient Mixture-of-Experts Inference", "2410.17954", "2024-10-23", "2026-04-02", "DAC 2026"),
    ("pregated2023", "Hwang, Ranggi and others", "Pre-gated {MoE}: An Algorithm-System Co-Design for Fast and Scalable Mixture-of-Expert Inference", "2308.12066", "2023-08-23", "2024-04-27"),
    ("moelightning2024", "Cao, Shiyi and others", "{MoE-Lightning}: High-Throughput {MoE} Inference on Memory-constrained {GPUs}", "2411.11217", "2024-11-18"),
    ("pipo2025", "Liu, Yangyijian and others", "{PIPO}: Pipelined Offloading for Efficient Inference on Consumer Devices", "2504.03664", "2025-03-15", "2025-06-13"),
    ("ktransformers2025", "Chen, Hongtao and others", "{KTransformers}: Unleashing the Full Potential of {CPU/GPU} Hybrid Inference for {MoE} Models", "https://madsys.cs.tsinghua.edu.cn/publication/ktransformers-unleashing-the-full-potential-of-cpu/gpu-hybrid-inference-for-moe-models/SOSP25-chen.pdf", "2025-10", None, "SOSP 2025, DOI 10.1145/3731569.3764843"),
    ("dali2026", "Zhu and others", "{DALI}: Dynamic Expert Allocation for {CPU-GPU} {MoE} Inference", "2602.03495", "2026-02-03"),
    ("seqmoe2026", "Wang and others", "{SeqMoE}: Sequence-level Expert Prefetching for Offloaded {MoE} Inference", "2609.12978", "2026-09-11"),
    ("specmd2026", "Hoang and others", "{SpecMD}: Expert Caching for Mixture-of-Experts Decoding", "2602.03921", "2026-02-03"),
    ("cachecond2024", "Skliar, Andrii and others", "Mixture of Cache-Conditional Experts for Efficient Mobile Device Inference", "2412.00099", "2024-11-27", "2025-06-24", "TMLR"),
    ("lin2025cache", "Lin and others", "In-depth Analysis on Caching and Pre-fetching in Mixture of Experts Offloading", "2511.05814", "2025-11-08"),
    ("cacheable2026", "Suram", "Cacheable by Design? Training Routers for Expert Locality", "2608.18261", "2026-08-18", None, None, "un seul auteur ; incohérences internes relevées par l'étude 04"),
    ("ssdllama2026", "Liang and others", "{SSD-LLaMA}: {SSD}, {RAM} and {VRAM} as One Hierarchy for Trillion-Parameter {MoE} Inference", "2609.18110", "2026-09-16"),
    ("edge0_2026", "Lin and others", "The Other Half of the Memory Wall ({Edge0})", "2609.18063", "2026-09-17"),
    ("flashmoe2026", "Kim and others", "{FlashMoE}: Learned Expert Cache Replacement", "2601.17063", "2026-01-22", "2026-10-05"),
    ("smallthinker2025", "{SmallThinker Team}", "{SmallThinker}: A Family of Efficient Large Language Models Natively Trained for Local Deployment", "2507.20984", "2025-07"),
    ("commitmoe2026", "Li and others", "{CommitMoE}", "https://ojs.aaai.org/index.php/AAAI/article/view/39454", "2026-03-14", None, "AAAI 2026"),
    ("zeroinference2022", "{DeepSpeed Team}", "{ZeRO-Inference}: Democratizing Massive Model Inference", "https://www.deepspeed.ai/2022/09/09/zero-inference.html", "2022-09-09"),
    ("directstorage13", "{Microsoft}", "{DirectStorage} 1.3 is now available", "https://devblogs.microsoft.com/directx/directstorage-1-3-is-now-available", "2025-07-01"),
    ("llamapr25294", "{ggml-org}", "llama.cpp pull request 25294: experts read from disk with an explicit cache", "https://github.com/ggml-org/llama.cpp/pull/25294", "2026-07-04", None, None, "ouverte au 2026-10-15"),
    ("llama20757", "{ggml-org}", "llama.cpp issue 20757: two-level expert cache", "https://github.com/ggml-org/llama.cpp/issues/20757", "2026-03-19", None, None, "communautaire"),
    ("llama24528", "{ggml-org}", "llama.cpp discussion 24528: {VRAM} cache of hot experts", "https://github.com/ggml-org/llama.cpp/discussions/24528", "2026-06-12", None, None, "communautaire"),
    ("llama27149", "{ggml-org}", "llama.cpp discussion 27149: reading only the active experts", "https://github.com/ggml-org/llama.cpp/discussions/27149", "2026-08-15", None, None, "communautaire"),
    ("moestream2026", "{Wok3b}", "moe-stream", "https://github.com/Wok3b/moe-stream", "2026", None, None, "licence MIT d'après la page du dépôt"),
    ("airllm2026", "{lyogavin}", "{AirLLM}", "https://github.com/lyogavin/airllm", "2026-10-14", None, None, "Apache-2.0, commit 0f679cc"),
]

ETUDE_05 = [
    ("leviathan2023", "Leviathan, Yaniv and Kalman, Matan and Matias, Yossi", "Fast Inference from Transformers via Speculative Decoding", "2211.17192", "2022-11-30", "2023-05-18", "ICML 2023"),
    ("chen2023spec", "Chen, Charlie and others", "Accelerating Large Language Model Decoding with Speculative Sampling", "2302.01318", "2023-02-02"),
    ("medusa2024", "Cai, Tianle and others", "{Medusa}: Simple {LLM} Inference Acceleration Framework with Multiple Decoding Heads", "2401.10774", "2024-01-19", "2024-06-14"),
    ("eagle2_2024", "Li, Yuhui and others", "{EAGLE-2}: Faster Inference of Language Models with Dynamic Draft Trees", "2406.16858", "2024-06-24", "2024-06-30"),
    ("eagle3_2025", "Li, Yuhui and others", "{EAGLE-3}: Scaling up Inference Acceleration of Large Language Models via Training-Time Test", "2503.01840", "2025-03-03", "2025-04-23"),
    ("gloeckle2024", "Gloeckle, Fabian and others", "Better and Faster Large Language Models via Multi-token Prediction", "2404.19737", "2024-04-30"),
    ("dflash2026", "Chen and Liang and Liu", "{DFlash}: Block Diffusion Drafting for Speculative Decoding", "2602.06036", "2026-02-05", "2026-05-28", "ICML 2026"),
    ("lookahead2024", "Fu, Yichao and others", "Break the Sequential Dependency of {LLM} Inference Using Lookahead Decoding", "2402.02057", "2024-02-03"),
    ("layerskip2024", "Elhoushi, Mostafa and others", "{LayerSkip}: Enabling Early Exit Inference and Self-Speculative Decoding", "2404.16710", "2024-04-25", "2024-10-18", "ACL 2024"),
    ("qspec2024", "Zhao, Juntao and others", "{QSpec}: Speculative Decoding with Complementary Quantization Schemes", "2410.11305", "2024-10-15", "2025-10-02", "EMNLP 2025"),
    ("subspec2025", "Wang and others", "Substitute Speculative Decoding for Offloaded {LLMs} ({SubSpec})", "2509.18344", "2025-09-22", "2025-10-08", "NeurIPS 2025"),
    ("shadowspec2026", "Chan and others", "{ShadowSpec}", "https://icml.cc/virtual/2026/75131", "2026", None, "ICML 2026, atelier AdaptFM"),
    ("stree2025", "Wu and others", "{STree}: Speculative Tree Decoding for Hybrid State-Space Models", "2505.14969", "2025-05-20", "2025-10-27", "NeurIPS 2025"),
    ("specexec2024", "Svirschevski, Ruslan and others", "{SpecExec}: Massively Parallel Speculative Decoding for Interactive {LLM} Inference on Consumer Devices", "2406.02532", "2024-06-04", "2024-11-30"),
    ("sequoia2024", "Chen, Zhuoming and others", "{Sequoia}: Scalable, Robust, and Hardware-aware Speculative Decoding", "2402.12374", "2024-02-19", "2025-07-05"),
    ("specinfer2023", "Miao, Xupeng and others", "{SpecInfer}: Accelerating Generative Large Language Model Serving with Tree-based Speculative Inference and Verification", "2305.09781", "2023-05-16"),
    ("triforce2024", "Sun, Hanshi and others", "{TriForce}: Lossless Acceleration of Long Sequence Generation with Hierarchical Speculative Decoding", "2404.11912", "2024-04-18", "2024-08-04", "COLM 2024"),
    ("dovetail2024", "Zhang and others", "{Dovetail}: A {CPU/GPU} Heterogeneous Speculative Decoding for {LLM} Inference", "2412.18934", "2024-12-25", "2025-09-09"),
    ("specoffload2025", "Zhuge and others", "{SpecOffload}: Unlocking Latent {GPU} Capacity for {LLM} Inference on Resource-Constrained Devices", "2505.10259", "2025-05-15", "2025-05-21"),
    ("cascade2025", "Saxena and others", "Utility-Driven Speculative Decoding for Mixture-of-Experts ({Cascade})", "2506.20675", "2025-06-17"),
    ("moesd2025", "Huang and others", "{MoESD}: Speculative Decoding for Sparse {MoE}", "2505.19645", "2025-05-26", "2026-02-16", "NeurIPS 2025"),
    ("moespec2026", "McDanel and others", "{MoE-Spec}: Expert Budgeting for Speculative Decoding of Mixture-of-Experts", "2602.16052", "2026-02-17"),
    ("acceptmoe2026", "Liang and others", "{AcceptMoE}: Acceptance-aware Expert Budgets for Offloaded Speculative Decoding", "2608.02989", "2026-08-04"),
    ("ecospec2026", "Xie and others", "Less Experts, Faster Decoding ({EcoSpec})", "2607.12696", "2026-07-14"),
    ("evict2026", "Pan and others", "Making Every Verified Token Count ({EVICT})", "2605.00342", "2026-05-01", "2026-09-05"),
    ("draftexpert2026", "Han", "{DraftExpert}: Distilled Draft Experts for On-Demand {MoE} Inference", "2607.24434", "2026-07-27"),
    ("dejavu2023", "Liu, Zichang and others", "{Deja Vu}: Contextual Sparsity for Efficient {LLMs} at Inference Time", "2310.17157", "2023-10-26", None, "ICML 2023"),
    ("relustrikes2023", "Mirzadeh, Iman and others", "{ReLU} Strikes Back: Exploiting Activation Sparsity in Large Language Models", "2310.04564", "2023-10-06"),
    ("cats2024", "Lee, Je-Yong and others", "{CATS}: Contextually-Aware Thresholding for Sparsity in Large Language Models", "2404.08763", "2024-04-12", "2024-11-03"),
    ("teal2024", "Liu, James and others", "Training-Free Activation Sparsity in Large Language Models ({TEAL})", "2408.14690", "2024-08-26", "2025-02-25", "ICLR 2025"),
    ("rsparse2025", "Zhang and others", "{R-Sparse}: Rank-Aware Activation Sparsity for Efficient {LLM} Inference", "2504.19449", "2025-04-28", None, "ICLR 2025"),
    ("polar2025", "Shrestha and others", "Polar Sparsity: High Throughput Batched {LLM} Inferencing with Scalable Contextual Sparsity", "2505.14884", "2025-05-20", "2025-11-11", "NeurIPS 2025"),
    ("turbosparse2024", "Song, Yixin and others", "Turbo Sparse: Achieving {LLM} {SOTA} Performance with Minimal Activated Parameters", "2406.05955", "2024-06-10", "2024-06-11"),
    ("sparseverif2025", "Wang and others", "Accelerate Speculative Decoding with Sparse Computation in Verification", "2512.21911", "2025-12-26"),
]

ETUDE_06 = [
    ("deepseekv4_2026", "{DeepSeek-AI}", "{DeepSeek-V4}: Towards Highly Efficient Million-Token Context Intelligence", "2606.19348", "2026-04-26"),
    ("engram2026", "{DeepSeek-AI}", "Conditional Memory via Scalable Lookup ({Engram})", "2601.07372", "2026-01-12", "2026-07-12"),
    ("deepseekv3_2024", "{DeepSeek-AI}", "{DeepSeek-V3} Technical Report", "2412.19437", "2024-12-27", "2025-02-18"),
    ("deepseekr1_2025", "{DeepSeek-AI}", "{DeepSeek-R1}: Incentivizing Reasoning Capability in {LLMs} via Reinforcement Learning", "2501.12948", "2025-01-22", "2026-01-04"),
    ("qwen3_2025", "{Qwen Team}", "{Qwen3} Technical Report", "2505.09388", "2025-05-14"),
    ("kimik2_2025", "{Kimi Team}", "{Kimi K2}: Open Agentic Intelligence", "2507.20534", "2025-07-28", "2026-02-03"),
    ("glm45_2025", "{GLM Team}", "{GLM-4.5}: Agentic, Reasoning, and Coding Foundation Models", "2508.06471", "2025-08-08"),
    ("gptoss2025", "{OpenAI}", "gpt-oss-120b and gpt-oss-20b Model Card", "2508.10925", "2025-08-08"),
    ("llama3_2024", "{Llama Team}", "The {Llama 3} Herd of Models", "2407.21783", "2024-07-31", "2024-11-23"),
    ("hfgptoss120b", "{ggml-org}", "gpt-oss-120b-GGUF (gpt-oss-120b-MXFP4.gguf, 63\\,387\\,346\\,208 octets)", "https://huggingface.co/ggml-org/gpt-oss-120b-GGUF", "2025-08", None, None, "Apache-2.0 ; empreinte SHA-256 vérifiée à la réception (REPRISE.md)"),
    ("hfgptoss20b", "{ggml-org}", "gpt-oss-20b-GGUF (gpt-oss-20b-MXFP4.gguf, 12\\,109\\,566\\,624 octets)", "https://huggingface.co/ggml-org/gpt-oss-20b-GGUF", "2025-08", None, None, "Apache-2.0 ; empreinte SHA-256 vérifiée à la réception (REPRISE.md)"),
]

ENTETES = {
    "04-chargement.bib": "% Sources de l'étude 04 (chargement à la demande, déchargement, caches d'experts),\n% reprises de fondations/04-chargement.md § 10. Produit par memoire/outils/bib_etudes.py.\n\n",
    "05-sparsite.bib": "% Sources de l'étude 05 (sparsité, prédiction, décodage spéculatif),\n% reprises de fondations/05-sparsite.md § 11. Produit par memoire/outils/bib_etudes.py.\n\n",
    "06-modeles.bib": "% Sources de l'étude 06 (modèles visés), reprises de fondations/06-modeles.md § 12.\n% Produit par memoire/outils/bib_etudes.py.\n\n",
}

if __name__ == "__main__":
    for nom, liste in (("04-chargement.bib", ETUDE_04), ("05-sparsite.bib", ETUDE_05), ("06-modeles.bib", ETUDE_06)):
        cles = [e[0] for e in liste]
        assert len(cles) == len(set(cles)), f"clé en double dans {nom}"
        texte = ENTETES[nom] + "".join(entree(*e) for e in liste)
        (SOURCES / nom).write_text(texte, encoding="utf-8")
        print(nom, len(liste), "entrées")
