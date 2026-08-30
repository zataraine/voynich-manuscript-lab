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
./scripts/lab doctor --strict --output artifacts/diagnostics/latest.json
./scripts/lab local-ai doctor --output artifacts/diagnostics/local-ai.json
./scripts/run python -m compileall -q src tests
echo "Manuscript Lab smoke test: PASS"
