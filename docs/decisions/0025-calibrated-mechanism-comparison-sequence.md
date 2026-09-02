# ADR 0025: Calibrated mechanism comparison and target-facing freeze

## Status

Accepted on 2026-09-02.

## Context

An external literature audit confirmed the need for long-form human controls
but exposed three problems in ADR 0024: it froze necessary control-only power
and validation work, placed generator design before unitization uncertainty,
and treated visual and cipher infrastructure as global blockers. The manuscript
has no known plaintext verifier, and published mechanisms can reproduce selected
surface statistics without reproducing other structural properties.

## Decision

Adopt `docs/MECHANISM_COMPATIBILITY_ESTIMAND.md` and the ordered phases in
`docs/CONTROL_EXPANSION_ROADMAP.md`.

- Freeze manuscript-facing mechanism inference until phases 1--6 pass.
- Permit and require target-blind power studies, published replications,
  simulations, estimator validation, and negative controls.
- Define reversible representation views before generator targets.
- Replicate literature-anchored mechanisms before adding flexible generators.
- Maintain visual/layout and numerical cryptanalysis as parallel programmes,
  not global blockers for external-control development.

## Consequences

- No result will claim a probability of hoax, language, or cipher from selected
  controls.
- A failed implementation does not reject an unbounded mechanism family.
- Exhaustive numerical search is retained where a bounded keyspace and an
  externally validated score exist.
- `human-pseudotext-v1` is pilot infrastructure and cannot serve as a frozen
  confirmatory sampling plan.
- No new E-number is assigned for software implementation; control-only studies
  receive questions and hypotheses before execution.
