# Local AI operations

The local stack is the routine review and retrieval tier for this lab. Its
authoritative machine handoff is `/home/nyx/voynich-local-ai/CODEX_HANDOFF.md`.
Project code uses `manuscript_lab.local_ai`; research modules must not call
llama.cpp or Ollama directly.

## Division of labour

| Work | Owner |
|---|---|
| Counts, statistics, nulls, search, optimization, cipher arithmetic | deterministic Python, solvers, or compiled tools |
| Dependencies, retries, incomplete outputs, resource ceilings | Snakemake |
| Experiment identity, leases, results, reviews, transitions | DuckDB ledger |
| Routine result and confound review | Qwen3.6 through `local_ai.review_experiment()` |
| Reference-document embeddings | Qwen3-Embedding through an exclusive auxiliary job |
| Reference-document reranking | Qwen3-Reranker-0.6B through an exclusive auxiliary job |
| Occasional adversarial review | GLM critic through an exclusive auxiliary job |
| Architecture, unexplained controlled effects, hard debugging | Codex escalation |

An LLM does not calculate a statistic, select a winning cipher candidate, alter
raw data, or promote a claim. Its structured review is evidence about review,
not experiment state by itself.

## Normal state and resource control

The normal state is Qwen active at `127.0.0.1:8080` with no Ollama model
resident. The public controls are:

```bash
/home/nyx/voynich-local-ai/bin/ai-status
/home/nyx/voynich-local-ai/bin/ai-qwen-mode
/home/nyx/voynich-local-ai/bin/ai-clear-gpu
/home/nyx/voynich-local-ai/bin/ai-aux-run COMMAND ARG...
/home/nyx/voynich-local-ai/bin/ai-reset
```

Every mode-changing control shares `locks/gpu-control.lock`. `ai-aux-run` stops
Qwen, runs one auxiliary command, unloads Ollama models, and restores Qwen from
an EXIT/INT/TERM trap. Do not call the internal `qwen-start` or `qwen-stop`
scripts from workflows.

The pinned `llama-server-b9553`, Qwen worker parameters, and `ncmoe=26` split
remain the performance baseline. Runtime hashes are verified by:

```bash
sha256sum -c /home/nyx/voynich-local-ai/state/runtime-sha256.txt
./scripts/lab local-ai doctor --live \
  --output artifacts/diagnostics/local-ai.json
```

## Content boundary

Semantic embedding and reranking are allowed only for `reference`, `metadata`,
and `research-note` content. They are prohibited for `manuscript-transcription`,
`voynichese`, and `corpus` content. The public client and auxiliary worker both
enforce this rule.

Exact manuscript identifiers and glyph strings belong in lexical retrieval.
Useful manuscript-derived features are deterministic counts, n-grams, edit
distances, positional distributions, graphs, and manuscript-trained
representations. A pretrained semantic vector is not a reading of Voynichese.

Reference retrieval should preserve two independent paths:

1. lexical/BM25 retrieval for exact folios, Currier labels, hashes, titles, and
   transcription codes;
2. embedding retrieval over external scholarship and lab notes;
3. rank fusion, then local reranking of the selected reference passages;
4. a bounded reference packet for Qwen review.

`manuscript_lab.retrieval` implements the deterministic BM25, cosine, and
reciprocal-rank-fusion stages. Embeddings are generated in batches through the
local-AI boundary and stored as derived reference artifacts; reranking is
limited to the fused candidate set.

## Experiment supervision

Initialize and inspect the ledger:

```bash
./scripts/lab experiment init
./scripts/lab experiment register config/experiments/EXPERIMENT.yaml
./scripts/lab experiment list
./scripts/lab experiment verify
```

Run a registered experiment without a shell interpretation layer:

```bash
./scripts/lab experiment execute EXPERIMENT_ID -- \
  ./scripts/run python path/to/experiment.py --config config/experiments/EXPERIMENT.yaml
```

The runner writes `artifacts/runs/EXPERIMENT_ID/runner.log`, records the exact
argument vector, changes `PENDING` or `REPLICATE` to `RUNNING`, renews a lease,
and records `COMPLETE` or `FAILED`. Event records form a SHA-256 chain so silent
edits are detectable. The chain is tamper-evident, not an externally anchored
signature.

For long DAGs use the local profile:

```bash
./scripts/run snakemake --snakefile workflow/Snakefile \
  --profile workflow/profiles/local
```

The profile leaves four logical processors free, serializes declared `gpu` and
`local_ai` resources, reruns incomplete outputs, and retries once. A rule using
an auxiliary model must declare `resources: local_ai=1, gpu=1` and invoke the
project interface rather than Ollama directly.

Check stale leases without mutating them:

```bash
./scripts/lab experiment stale --hours 6
```

A stale run is inspected before an explicit `RUNNING -> FAILED -> PENDING`
recovery. Never silently requeue it: the prior process may still own an external
resource or be writing an artifact.

## Review and escalation

Qwen output must validate against `schemas/local-review.schema.json`. Review an
immutable result record with:

```bash
./scripts/lab local-ai review artifacts/runs/EXPERIMENT/result.json \
  --output artifacts/runs/EXPERIMENT/qwen-review.json
```

The record is framed as untrusted data and its SHA-256 is stored with model and
token-use provenance. Promote `COMPLETE` to `REVIEW_LOCAL` only after the review
artifact exists. Use GLM sparingly for an adversarial second opinion. Escalate
to Codex for unexplained effects that survive controls and held-out evaluation,
reviewer conflicts, architecture decisions, or difficult failures.

## Failure recovery

1. Run `ai-status` and `./scripts/lab local-ai doctor`.
2. If auxiliary work was interrupted, run `ai-reset`; it waits for the shared
   resource lock before restoring the normal state.
3. Inspect the immutable run log and Snakemake metadata.
4. Mark a stranded run `FAILED` with the reason; do not overwrite its artifacts.
5. Register or requeue a new attempt with the same config and an explicit
   predecessor reference in its notes.
