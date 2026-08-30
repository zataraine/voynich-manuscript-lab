# Snakemake workflow

`workflow/Snakefile` is the reproducible orchestration entry point. The initial
DAG validates the complete raw intake and its three tracked manifests. Add
derived rules here as the IVTFF parser, canvas/locus alignment, witness lattice,
and cipher null models are implemented. Never make a rule modify `data/raw/`.

Preview or run from WSL:

```bash
./scripts/run snakemake --snakefile workflow/Snakefile --dry-run --cores 1
./scripts/run snakemake --snakefile workflow/Snakefile --cores 4
```

For long local runs use `--profile workflow/profiles/local`. Rules that call an
auxiliary local model declare both `gpu=1` and `local_ai=1`; numerical rules
declare realistic thread and memory resources. Experiment state belongs in the
DuckDB ledger, not in sentinel filenames alone. See `docs/LOCAL_AI.md`.

`workflow/mechanism-study.smk` is the first long sequential experiment. It uses
the preregistered `E-001-manufactured-vs-hoax` config and ends with a locally
retrieved, schema-constrained Qwen review. Run it through `experiment execute`
so leases, heartbeats, logs, and terminal state remain durable.
