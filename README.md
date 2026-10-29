# troncons

troncons is a research project and an inference engine that runs gpt-oss-120b, a language model
far larger than the memory of the laptop it runs on, **exactly**: the expert weights stay losslessly
entropy-coded on disk and are decoded on the GPU at the moment a computation needs them, and the
logits are, to the bit, those the same engine computes from the uncompressed weights. The work is
reported in three technical volumes and a short article, each in English and French.

The notes, studies and code comments are written in French. The volumes and the article exist in both
languages.

*Résumé en français à la fin de ce fichier.*

## Results

All figures below were measured on one machine (see [Limits](#limits)) and are documented in the
volumes and the article, with their tools and logs committed in this repository.

- **A 63.4 GB model on a 16 GB laptop.** troncons serves gpt-oss-120b (63.4 GB in its native MXFP4
  format) on a laptop with 16 GB of RAM and an 8 GB RTX 4060 Laptop GPU, with a host working set of
  384 MB.
- **The synonym codon of zero.** MXFP4 has two codes for the same zero (+0 and −0). In gpt-oss the
  sign of a zero carries no information, and no computation of the engine depends on it. Folding −0
  into +0 before entropy coding (format `.trc` v1.2) removes 1.80 GB from gpt-oss-120b, 3.26 % of
  the bits of its experts, with no change to the decoder or the kernels; the engine's logits stay
  identical to the bit over 5,120 steps.
- **Speed (milestone J1).** In an ABBA series, the v1.2 file generates 2.890 tokens/s against 1.988
  for v1.0 (×1.454; an independent judge measured ×1.442). The byte saving alone cannot explain
  this: a crossed experiment shows that the gain follows the pattern of read requests the format
  imposes on this particular disk. It is a result of this machine, not a portable one.
- **What did not work** is reported too, each idea against the threshold declared before it was
  measured (Volume III and the article).

## Repository layout

| Path | Content |
|---|---|
| `SOCLE.md` | The base instructions shared by every role in the project: the mission in the author's own words and the rules of the work. Read it first. |
| `fondations/` | Volume I studies: the machine, quantisation, entropy coding, loading, sparsity, models, what is missing; raw logs under `fondations/journaux/`. |
| `decisions/` | The architecture of the engine (`ARCHITECTURE.md`) and the two pleadings it was decided from. |
| `moteur/` | The engine: a Rust workspace (`crates/`, `bins/`) with CUDA kernels; `bins/troncons` is the engine, `bins/trc-codeur` writes `.trc` files. |
| `mesures/` | Measurements and raw logs (engine milestones, disk, gpt-oss baselines, genome studies). |
| `outils/` | Measurement drivers, analysis tools, judges' tools. |
| `genome/` | Volume III studies: the "genome of the weights" (synonym codon, `.trc` v1.2, disk placement, negative results) and their judgements. |
| `idees/` | The idea that started Volume III. |
| `memoire/` | The volumes: Tome I (`memoire/en`, `memoire/fr`), Tome II (`memoire/tome2`), Tome III (`memoire/tome3`), the short article (`memoire/article`), sources, figures, figure data and build tools. The PDF files are committed. |
| `REPRISE*.md`, `SESSION-SUIVANTE.md`, `JUGEMENT*.md` | Resumption notes and judgements, kept as written during the work. |

## Building

**The engine** (Windows only; it was built and measured on Windows 11):

- Rust 1.98 or later (edition 2024), the CUDA 13.1 toolkit with `CUDA_PATH` set to it, and the
  Visual Studio 2022 Build Tools (`cl.exe`, for `nvcc`; run from a `vcvars64.bat` prompt);
- `cd moteur && cargo build --release`. Dependency versions are pinned in `moteur/Cargo.toml`.
- `trc-codeur` turns a gpt-oss GGUF file into `.trc` files (`coder … --canonique` writes v1.2), and
  `troncons generer|evaluer|mesurer` runs the engine; options are documented at the head of each
  `main.rs` and in `decisions/ARCHITECTURE.md` § 5.10. Model weights are not part of this repository.

**The volumes** need MiKTeX or TeX Live (lualatex, biber, latexmk). The committed sources build each
PDF with latexmk from its folder, for example:

```
cd memoire/en         && latexmk -r ../latexmkrc    troncons-memoire-en.tex
cd memoire/tome2/fr   && latexmk -r ../../latexmkrc troncons-tome2-fr.tex
```

Tome III first needs its spectra figures (see the `tome3` branch of `memoire/construire.sh`).
`memoire/construire.sh` also regenerates figure data and annex tables before compiling; the annex
tools (`memoire/outils/annexes.py`, `tome2_*.py`, `tome3_annexes.py`) read specific commits of the
project's working history, which is not part of this public snapshot, so they do not run here; their
outputs are committed. The article builds with `bash memoire/article/construire-article.sh` (pdflatex
and BibTeX, as arXiv accepts).

## Method

- `SOCLE.md` sets the rules every piece of work followed.
- **Declared thresholds.** Every claim is tested against a threshold written and committed before the
  measurement; a claim that misses its threshold is reported as missed.
- **Controls that can fail.** Each tool has a control and a deliberate break (a corrupted input, a
  forced error) that must make it fail.
- **Independent judges.** Results, figures and texts were re-checked by separate judges, from the
  committed logs, with their own tools; their reports are the `JUGEMENT*.md` files.
- **Labels.** Figures are marked as measured on this machine, computed from committed measurements, or
  taken from the literature. A wrong sentence is struck through with what changed, never silently
  removed.

## How it was built

I, Ariel Stone Beti, set the goals, the constraints and the checks, and directed the work. I built it
by directing AI coding agents (Claude Code): agents wrote most of the code, ran most of the
measurements and drafted the reports and the volumes, under the rules of `SOCLE.md`. The judges that
re-checked the results are agents too, run separately from the ones whose work they judged.

## Limits

- **One machine.** Every measurement comes from a single laptop (16 GB of RAM, an 8 GB RTX 4060
  Laptop GPU, one NVMe disk). The speed results in particular depend on that disk and are not claimed
  to carry over to other hardware.
- **One model family.** The work targets gpt-oss-120b and its smaller twin gpt-oss-20b.
- **A snapshot.** This repository is a single-commit snapshot of the project, not its history.
  Commit identifiers cited in the volumes and notes refer to the original working history, which is
  not published.
- **Cleaned for publication.** Absolute paths under the author's home directory were replaced by `~`
  and identifiers of work sessions by `<session>`, in notes, tools and logs alike; usage gauges and
  battery levels were removed from the resumption notes, and compiled Python caches from the tree.
  Tools therefore show paths of the form `~/dev/…` that must be adapted to another machine, and the
  SHA-256 of a log that was cleaned no longer matches a hash of it quoted elsewhere. No measured
  figure was changed.

## License

- **Code**: MIT License, see [`LICENSE`](LICENSE).
- **Texts**: the volumes and the article (`memoire/`), `genome/`, `fondations/`, `decisions/`,
  `idees/` and every Markdown file are licensed under CC BY 4.0, see [`LICENSE-texts`](LICENSE-texts).
- Third-party material (measurement corpora, model-card excerpts) keeps its own license, as listed in
  `LICENSE-texts`.

---

## Résumé en français

troncons est un projet de recherche et un moteur d'inférence qui fait tourner gpt-oss-120b, un modèle
de langue bien plus gros que la mémoire du portable qui l'exécute, **exactement** : les poids des
experts restent codés sans perte sur le disque et sont décodés sur la carte graphique au moment où un
calcul en a besoin ; les logits sont, au bit près, ceux que le même moteur calcule sur les poids non
compressés.

- gpt-oss-120b (63,4 Go) est servi sur un portable de 16 Go de RAM et une RTX 4060 de 8 Go, avec une
  mémoire de travail de 384 Mo sur l'hôte.
- Le codon synonyme du zéro : MXFP4 a deux codes pour le même zéro ; replier −0 sur +0 avant le codage
  (format `.trc` v1.2) retire 1,80 Go au 120b, 3,26 % des bits de ses experts, et les logits du moteur
  restent égaux au bit sur 5 120 pas.
- Le fichier v1.2 génère 2,890 jetons/s contre 1,988 pour la v1.0 (×1,454 ; un juge indépendant :
  ×1,442) ; ce gain suit le motif des lectures que le format impose à ce disque : il est propre à cette
  machine.
- Les trois tomes et l'article (anglais et français) sont sous `memoire/` ; les études sous
  `fondations/` et `genome/` ; le moteur sous `moteur/`. Lire `SOCLE.md` d'abord.
- Méthode : seuils déclarés et commités avant chaque mesure, témoins qui doivent pouvoir tomber,
  juges indépendants.
- J'ai fixé les objectifs, les contraintes et les vérifications, et dirigé le travail ; des agents
  (Claude Code) ont écrit l'essentiel du code, des mesures et des rapports ; les juges sont aussi des
  agents.
- Limites : une seule machine, une seule famille de modèles ; ce dépôt est un instantané à un seul
  commit, nettoyé des chemins personnels et des identifiants de session.
- Licences : MIT pour le code ; CC BY 4.0 pour les tomes, l'article et les textes.
