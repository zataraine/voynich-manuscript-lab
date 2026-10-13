# ADR 0031: Retain raw null ensembles and audit Phase-4 gaps

## Status

Accepted on 2026-10-13.

## Context

Single null draws expose neither variability nor replicate-specific missingness.
Plug-in entropy/MI/JS estimates can deviate from population quantities at small
sample sizes. A positive contextual information value can arise mechanically
when group identities are unique. Accumulating successful unit tests must not
hide missing roadmap endpoints or repeat E-013's near-zero-scale failure.

## Decision

Provide a versioned repeated-null diagnostic with domain-separated replicate
seeds, raw samples, defined-replicate counts, means, sample SDs and unscaled
observed-minus-null differences. Preserve undefined replicates as null values
and suppress contrasts for undefined observed metrics. Do not divide by SD or
assign a significance/compatibility label.

Control-record builders opt in explicitly with a replicate budget. Canonical
serialization checks identity/dimensions and recomputes summaries from retained
samples. Add synthetic finite-size and contextual-uniqueness checks and the
requirement-by-requirement audit in `docs/PHASE4_ACCEPTANCE.md`.

## Consequences

- Repeated nulls are diagnostics, not automatic bias corrections.
- Layout-panel ensembles, learned-scale uncertainty, a vocabulary-growth endpoint,
  recurrence/reset decisions and a joint missingness policy remain explicit gaps.
- This implementation remains software verification; it registers no new
  manuscript experiment or claim and does not complete Phase 4.
