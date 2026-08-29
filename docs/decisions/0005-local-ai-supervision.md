# Decision 0005: Local AI supervision boundary

- Status: accepted
- Date: 2026-08-30

## Context

The machine has a pinned, benchmarked Qwen llama.cpp worker plus Ollama
embedding/critic models and local Transformers rerankers. The RTX 4070 cannot
reliably host the main and auxiliary tiers together. Hours-long experiments
also require durable state that does not depend on an interactive agent session.

An inventory audit found that the path labelled as Qwen3-Reranker-0.6B actually
contained the 4B model. The 4B tree was preserved under its correct name and the
genuine 0.6B revision `e61197ed45024b0ed8a2d74b80b4d909f1255473` was installed
at the documented primary path.

## Decision

- Keep llama.cpp b9553 and the `ncmoe=26` worker as the pinned baseline.
- Expose local models only through `manuscript_lab.local_ai`.
- Use strict JSON Schema for routine and critic reviews.
- Prohibit pretrained semantic embedding and reranking of manuscript text at
  both sides of the auxiliary process boundary.
- Serialize every GPU mode change with one lock and restore Qwen from traps.
- Store experiments in DuckDB with validated transitions, leases, heartbeats,
  complete provenance fields, and a hash-linked event history.
- Let Snakemake own DAG execution; use the ledger-aware runner for explicit
  standalone commands.
- Treat model prose as review material, never as an automatic state mutation.

## Consequences

Routine review and reference retrieval consume local compute. Deterministic
work can run unattended and remain inspectable after an interrupted interactive
session. Auxiliary calls pay the cost of stopping and restoring Qwen, so they
must be batched. The event chain detects mutation but requires an external
signed anchor if adversarial tamper resistance is ever needed.
