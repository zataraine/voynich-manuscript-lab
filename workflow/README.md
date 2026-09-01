# Snakemake workflow

`workflow/Snakefile` is the reproducible orchestration entry point. The DAG
validates the raw intake and tracked manifests and exposes the implemented
mechanism, cipher-control, representation, witness, and external-calibration
campaigns. Never make a rule modify `data/raw/`.

Preview or run from WSL:

```bash
./scripts/run snakemake --snakefile workflow/Snakefile --dry-run --cores 1
./scripts/run snakemake --snakefile workflow/Snakefile --cores 4
```

For long local runs use `--profile workflow/profiles/local`. Rules that call an
auxiliary local model declare both `gpu=1` and `local_ai=1`; numerical rules
declare realistic thread and memory resources. Experiment state belongs in the
DuckDB ledger, not in sentinel filenames alone. See `docs/LOCAL_AI.md`.

`workflow/mechanism-study.smk` is the historical E-001 long sequential
experiment. Later campaign entry points are listed in `scripts/run-*` and in
`research/EXPERIMENT_INDEX.md`. Run managed campaigns through their wrapper or
`experiment execute` so leases, heartbeats, logs, and terminal state remain
durable. Local-model review is advisory and never supplies numeric evidence.
