# Voynich Manuscript Lab

A reproducible computational research workspace for Beinecke MS 408, commonly
called the Voynich Manuscript. The lab is designed to test properties of the
writing and competing generative mechanisms without assuming that the text is
a natural language, a cipher, a constructed system, or meaningless.

This repository contains the research code, frozen configurations, source
manifests, protocols, tests, ledgers, and reviewed reports. Source scans,
transcription downloads, model weights, caches, and generated run directories
are intentionally not committed.

## Current evidence

As of 2026-09-02, the defensible result is narrower than a decipherment claim:

- The format-2 IVTFF intake can be parsed losslessly and aligned across five
  primary transcription lineages without merging their readings. See
  [Q-010](reports/Q-010-lossless-representation.md) and
  [Q-011](reports/Q-011-witness-alignment.md).
- Eight low-level order and local-copy effects reject four simple shuffle or
  resampling nulls across ten witness and uncertainty views. See
  [E-012](reports/E-012-multi-witness-mechanism-replication.md).
- Those same effects do **not** reliably distinguish intentional payload from
  structured no-payload controls. In the corrected external calibration,
  omitted-family development balanced accuracy was 0.611, its permutation
  p-value was 0.233, and human-gibberish specificity was 0.368. See
  [E-013R1](reports/E-013R1-external-signature-calibration.md).
- A separate 21-feature higher-order panel also fails external calibration:
  development balanced accuracy is 0.638 with permutation p=0.155,
  human-gibberish specificity is 0.289, and Naibbe recall is 0.50. See
  [E-014](reports/E-014-higher-order-external-calibration.md).
- Voynichese was therefore not scored by either classifier. The current evidence
  supports robust low-level non-randomness, but not an inference of meaning,
  language, cipher, hoax, or authorial intent.

The original E-013 fit was invalid because an effectively constant feature was
scaled by floating-point noise. It is retained as a documented
[technical failure](reports/E-013-technical-failure.md); E-013R1 is the
authoritative corrected result.

## Reproduce the workspace

The supported baseline is Ubuntu 24.04 under WSL 2 with Python 3.12. A fresh
clone does not need to be placed at any particular Windows or Linux path.

```bash
git clone https://github.com/zataraine/voynich-manuscript-lab.git
cd voynich-manuscript-lab
./scripts/bootstrap_wsl.sh
./scripts/lab doctor
./scripts/smoke.sh
```

Run project commands through `./scripts/run`; it uses the locked environment
described by `pyproject.toml` and `uv.lock`. CUDA is supplied by the Windows WSL
driver bridge. Do not install a Linux NVIDIA display driver inside WSL.

The deterministic pipeline does not require the author's local language-model
stack. Local Qwen, embedding, reranking, and critic services are optional aids
for bounded review and long unattended runs; they do not supply numeric
evidence. Their machine-specific setup is documented in
[`docs/LOCAL_AI.md`](docs/LOCAL_AI.md). If that stack is present, check it with:

```bash
./scripts/lab local-ai doctor --live
```

## Acquire the source data

The source catalog records provenance, evidence tiers, rights notes, and known
gaps. Review [`docs/SOURCE_CATALOG.md`](docs/SOURCE_CATALOG.md) before download,
then run:

```bash
./scripts/acquire-voynich
./scripts/validate-voynich-intake
```

The acquisition covers the Yale IIIF presentation and PDF, ten acquired
IVTFF/legacy transcription source files, nine derived official STA conversions,
format specifications, physical reports, and selected control resources. These
are not nineteen independent transcription witnesses: some files are derived
views or related lineages, and the tracked metadata preserves those
relationships. Restricted decipherment sites are not scraped.

Because raw source files are excluded from Git, a clone alone cannot reproduce
every published numerical result. The tracked manifests identify expected
files and hashes; network availability, third-party terms, and manually
acquired resources can still affect reconstruction. Generated results are
immutable local artifacts under `artifacts/runs/`; reviewed conclusions and
their provenance hashes are promoted to `reports/`.

## Research trail

The current state is recorded in four separate ledgers:

- [`research/QUESTION_LOG.md`](research/QUESTION_LOG.md) — research questions;
- [`research/HYPOTHESES.md`](research/HYPOTHESES.md) — falsifiable hypotheses;
- [`research/EXPERIMENT_INDEX.md`](research/EXPERIMENT_INDEX.md) — experiment status and outputs;
- [`research/CLAIMS.md`](research/CLAIMS.md) — claims that survived review.

The full sequence runs from E-001 through E-014. Historical protocols and
reports retain their original prospective language, including statements about
what was “next” at the time; the ledgers and the current-evidence section above
give the present status. New research experiments are paused while the seven
interfaces in the
[`control-expansion roadmap`](docs/CONTROL_EXPANSION_ROADMAP.md) are built. Its
first three infrastructure phases are now implemented:

1. the admissible question and failure semantics are fixed by the
   [`mechanism-compatibility estimand`](docs/MECHANISM_COMPATIBILITY_ESTIMAND.md);
2. the prospective
   [`paired human-control pilot`](docs/HUMAN_CONTROL_PILOT_V2.md) has a frozen
   allocation and validated intake packet, but is not an approved confirmatory
   sampling plan and authorizes no recruitment; and
3. all later measurements consume the frozen
   [`reversible representation views`](docs/REPRESENTATION_VIEWS.md), which keep
   witnesses separate and preserve uncertainty and source provenance.

Phases 4--6—the joint measurement battery, literature-anchored mechanism
replications, and external validation barrier—remain to be implemented. Phase 7
is the only new manuscript-facing run and remains prohibited until those gates
pass. None of the three completed infrastructure phases is a new experimental
result.

## Main capabilities

- byte-exact source manifests and reversible numeric encodings;
- lossless IVTFF parsing, Yale canvas mapping, and witness lattices;
- page- or document-grouped statistical evaluation and structured null models;
- classical, homophonic, nomenclator, polyalphabetic, progressive-key,
  transposition, fractionation, and rotor control generators;
- Pynini/OpenFST transducers, constraint solving, optimization, and seeded search;
- CPU/CUDA inference, embeddings, reranking, and optional local-model review;
- Snakemake orchestration and DuckDB experiment leases, heartbeats, and events.

The cipher rules are in
[`docs/CRYPTANALYSIS_PROTOCOL.md`](docs/CRYPTANALYSIS_PROTOCOL.md). No readable
fragment counts as validation: mappings must be frozen before held-out scoring
and compared with structure-preserving nulls.

## Repository map

| Path | Purpose | Git policy |
|---|---|---|
| `data/raw/` | untouched acquired source files | ignored; immutable |
| `data/interim/` | reversible text, page, and region transforms | ignored |
| `data/processed/` | analysis tables, features, and splits | ignored |
| `data/manifests/` | source metadata and expected hashes | tracked |
| `config/` | lab and experiment configuration | tracked |
| `models/` | local-model configuration and registry template | weights ignored |
| `artifacts/runs/` | generated experiment records | ignored |
| `research/` | questions, hypotheses, experiments, and claims | tracked |
| `reports/` | reviewed results and selected small figures | tracked |
| `src/`, `tests/` | reusable code and verification | tracked |
| `workflow/` | Snakemake workflows and local profile | tracked |

Read [`AGENTS.md`](AGENTS.md), [`INFRASTRUCTURE.md`](INFRASTRUCTURE.md),
[`docs/DATA_CONTRACT.md`](docs/DATA_CONTRACT.md), and
[`docs/RESEARCH_PROTOCOL.md`](docs/RESEARCH_PROTOCOL.md) before changing
research code or data.

## Maintainer

This repository is owned and maintained by [@zataraine](https://github.com/zataraine).

## Rights and licensing

The repository is publicly readable but currently has no repository-wide
open-source license. Public visibility alone does not grant reuse rights.
Third-party manuscript images, transcriptions, papers, control texts, and model
assets remain subject to their own terms, recorded where known in the source
catalog and manifests. No Yale manuscript images or downloaded model weights
are committed here.
