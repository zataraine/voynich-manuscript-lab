#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${project_root}"

./scripts/run ruff check .
./scripts/run ruff format --check .
./scripts/run pytest
./scripts/run snakemake --snakefile workflow/Snakefile --dry-run --cores 1
./scripts/run snakemake --snakefile workflow/mechanism-study.smk \
  --dry-run --cores 12 --resources gpu=1 local_ai=1
./scripts/run snakemake --snakefile workflow/control-calibration.smk \
  --dry-run --cores 12 --resources gpu=1 local_ai=1 mem_mb=32768
./scripts/run snakemake --snakefile workflow/transformation-ladder.smk \
  --dry-run --cores 12 --resources gpu=1 local_ai=1 mem_mb=65536
./scripts/run snakemake --snakefile workflow/robust-parameter-ladder.smk \
  --dry-run --cores 12 --resources gpu=1 local_ai=1 mem_mb=65536
./scripts/run snakemake --snakefile workflow/known-payload-retrieval.smk \
  --dry-run --cores 12 --resources gpu=1 local_ai=1 mem_mb=65536
./scripts/run snakemake --snakefile workflow/cipher-relation-representation.smk \
  --dry-run --cores 12 --resources gpu=1 local_ai=1 mem_mb=65536
./scripts/run snakemake --snakefile workflow/blind-adfgx-replication.smk \
  --dry-run --cores 12 --resources mem_mb=8192
./scripts/run snakemake --snakefile workflow/ciphertext-only-structure.smk \
  --dry-run --cores 12 --resources mem_mb=8192
./scripts/run snakemake --snakefile workflow/representation-robustness.smk \
  --dry-run --cores 1 --resources mem_mb=8192
./scripts/run snakemake --snakefile workflow/witness-calibration.smk \
  --dry-run --cores 1 --resources mem_mb=4096
./scripts/run snakemake --snakefile workflow/multi-witness-replication.smk \
  --dry-run --cores 12 --resources mem_mb=16384
./scripts/run snakemake --snakefile workflow/external-signature-calibration.smk \
  --dry-run --cores 12 --resources mem_mb=16384
./scripts/run snakemake --snakefile workflow/external-signature-calibration-r1.smk \
  --dry-run --cores 12 --resources mem_mb=16384
./scripts/lab doctor --strict --output artifacts/diagnostics/latest.json
./scripts/lab local-ai doctor --output artifacts/diagnostics/local-ai.json
./scripts/run python -m compileall -q src tests
echo "Manuscript Lab smoke test: PASS"
