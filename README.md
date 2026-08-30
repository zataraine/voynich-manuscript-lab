# Manuscript Lab

A local, reproducible workbench for studying one book written in an otherwise
unattested writing system, including possible relationships between text and
page imagery. The repository begins deliberately neutral: no manuscript
identity, transcription convention, glyph interpretation, language family, or
semantic theory is baked into the code.

## What is ready

- isolated Python 3.12 environment under Ubuntu 24.04 / WSL 2;
- PyTorch inference on CPU and NVIDIA CUDA;
- statistical, corpus, image, PDF, OCR, and transformer tooling;
- lossless byte/code-point/grapheme integer encodings and classical-cipher tooling;
- constraint, integer-optimization, modular-algebra, and seeded search backends;
- Pynini/OpenFST weighted transducers and Snakemake workflow orchestration;
- managed local Qwen review, reference embedding/reranking, and GLM critic tiers;
- DuckDB experiment leases, heartbeats, state transitions, and hash-linked events;
- immutable-source manifests with SHA-256 provenance;
- separate raw, interim, processed, model, run, report, and notebook layers;
- research ledgers and a falsification-first experiment protocol;
- repeatable diagnostics and tests.

## Start here

From WSL, at the repository root:

```bash
./scripts/lab doctor
./scripts/lab local-ai doctor --live
./scripts/smoke.sh
./scripts/run jupyter lab --no-browser
```

From PowerShell, enter the configured distribution first:

```powershell
wsl.exe -d Ubuntu-24.04
cd /mnt/c/Users/adminion/Documents/ChatGPT/Voynich
./scripts/lab doctor
```

The project environment and package/model caches live on the WSL ext4 disk,
not inside the Windows working tree. `./scripts/run` supplies the required paths
automatically. See `INFRASTRUCTURE.md` for the exact layout and recovery steps.

## When the source arrives

1. Copy original book files to `data/raw/books/`, supplied images to
   `data/raw/images/`, and the untouched encoding to
   `data/raw/transcriptions/`.
2. Create a manifest without altering those files:

   ```bash
   ./scripts/lab manifest build SOURCE_ID \
     data/raw/books/book.pdf \
     data/raw/transcriptions/encoding.txt
   ```

3. Fill in acquisition, rights, transcription-system, and page-mapping details
   in the generated manifest.
4. Validate the intake:

   ```bash
   ./scripts/lab manifest verify data/manifests/SOURCE_ID.yaml
   ```

5. Add the source facts to `research/QUESTION_LOG.md`. Do not begin semantic
   interpretation until page IDs, transcription units, uncertainty markers, and
   image/page alignment are specified.

To create a lossless numeric baseline after intake:

```bash
./scripts/lab numeric encode data/raw/transcriptions/encoding.txt \
  --output-prefix data/interim/numeric/source-byte --mode byte
./scripts/lab numeric verify data/interim/numeric/source-byte
./scripts/lab crypt analyze data/interim/numeric/source-byte \
  --output artifacts/runs/source-byte-descriptives.json
```

The byte baseline accepts any source. Code-point and grapheme variants are
available when the supplied encoding and codec are documented. Cipher searches
must follow `docs/CRYPTANALYSIS_PROTOCOL.md`.

## Voynich source intake

The identified source is Beinecke MS 408. The curated intake configuration,
rights boundaries, evidence tiers, and known gaps are documented in
`docs/SOURCE_CATALOG.md`. To reproduce the permitted downloads and validate all
local files from WSL:

```bash
./scripts/acquire-voynich
./scripts/validate-voynich-intake
```

The intake includes Yale's 213 full-resolution IIIF canvases, the complete Yale
PDF, independent IVTFF/STA transcription witnesses, format specifications,
physical reports, and selected computational baselines. It intentionally does
not scrape restricted decipherment sites.

Voynich-specific research notes now include `docs/EVA_CURRIER.md` and
`docs/NAIBBE.md`. Reproducible orchestration starts at `workflow/Snakefile`; the
lab also provides Pynini/OpenFST for weighted, invertible transducer experiments.
The local model boundary and unattended-run operations are documented in
`docs/LOCAL_AI.md`.

The first preregistered mechanism study is documented in
`docs/MANUFACTURED_VS_HOAX.md`. It compares held-out sequence structure with
five seeded nonsemantic/null families, then uses the local embedding, reranking,
and Qwen stack for bounded methodological retrieval and review. It deliberately
does not report a probability of meaning before calibrated control families and
explicit priors exist.

The next control-calibration campaign is documented in
`docs/CONTROL_CALIBRATION.md`. It uses document-grouped meaningful and
human-gibberish controls, withholds Naibbe ciphertext as a known-payload stress
test, and measures sensitivity across six IVTFF witnesses. Run its resumable
deterministic and local-review stages with `./scripts/run-control-calibration`.

## Repository map

| Path | Purpose | Git policy |
|---|---|---|
| `data/raw/` | untouched source files | ignored; immutable |
| `data/interim/` | reversible page, region, and text transforms | ignored |
| `data/processed/` | versioned analysis tables, features, and splits | ignored |
| `data/manifests/` | hashes and source metadata | tracked |
| `config/` | lab and experiment configuration | tracked |
| `models/` | model registry and downloaded weights | registry tracked, weights ignored |
| `artifacts/runs/` | machine-generated experiment records | ignored |
| `research/` | question, hypothesis, experiment, and claim ledgers | tracked |
| `reports/` | reviewed results and selected small figures | tracked |
| `src/` and `tests/` | reusable code and verification | tracked |

The research rules live in `AGENTS.md`, the machine contract in
`INFRASTRUCTURE.md`, and the data/experiment contracts in `docs/`.
