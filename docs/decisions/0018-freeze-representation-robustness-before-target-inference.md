# ADR 0018: Freeze representation robustness before target inference

## Status

Accepted on 2026-09-01.

## Context

Q-011 showed that official transcription witnesses differ at most loci even
though their token-level similarity is high. Selecting one transcript, forming
a consensus, or tuning measurements after seeing target results would hide how
much any conclusion depends on editorial choices.

## Decision

Run E-010 as a target-side measurement audit, not a classifier. Freeze five
non-synthetic lineage views, two official conversion comparisons, a six-view
uncertainty ensemble, ten interpretable page features, page-level bootstrap,
page-label nulls, and conjunctive gates before calculating results. Use only
common loci and determine page eligibility by the minimum coverage across all
views. Do not use VT or RF as independent evidence and do not create a consensus
transcript.

Only features passing every frozen gate may enter a later manufactured-text
experiment. E-010 cannot itself produce a probability or semantic conclusion.

## Consequences

- Witness disagreement is propagated into the measurement rather than erased.
- Unstable but interesting features are reported and excluded.
- The subsequent control campaign may have a smaller or empty feature panel.
- Any change to the panel or gates requires a new preregistered experiment.
