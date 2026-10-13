# 0035: Exercise assembled panels with bounded synthetic stress cases

Date: 2026-10-14
Status: accepted

## Question and acceptance

Can the assembled core, learned-unit, layout and vocabulary panels preserve
their software invariants across short/sparse/imbalanced/unequal-page inputs and
annotation removal? Retain individual cases and failures, known-answer checks,
deterministic fixture replay and explicit undefinedness. This is not the
complete estimator-calibration or Phase 4 acceptance gate.

## Decision

Add the synthetic-only `measurement_stress` runner and a bounded, versioned
configuration. Reuse existing estimators, saved-table restoration and null
implementations. Record generated inputs and execution provenance, write new
immutable artifact paths, and return failure for any failed software check.
No source downloads, dependency changes or local-model numeric evidence are needed.

Core symbol-renaming checks compare with an explicit 1e-12 absolute tolerance:
an initial exact-equality check exposed ~1e-15 JS summation-order roundoff.
Retain maximum differences so numeric tolerance cannot conceal unreported drift.

## Consequences

The suite exposes conditional learned-unit and layout undefinedness alongside
finite placeholders. It does not invent a minimum-support cutoff, infer a
missingness correction, replace MI, or promote the current panel to scientific
readiness. Read `docs/MEASUREMENT_STRESS.md` and the Phase 4 acceptance audit
before designing the joint abstention policy. Generated diagnostic artifacts
stay local; documented summaries are not manuscript claims.
