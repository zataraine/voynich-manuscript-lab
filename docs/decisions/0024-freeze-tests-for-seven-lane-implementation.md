# ADR 0024: Freeze research tests during seven-lane implementation

## Status

Superseded on 2026-09-02 by ADR 0025. The target-facing freeze remains, but
control-only research is required during implementation.

## Context

E-013R1 and E-014 show that short structured controls are insufficient for a
payload-versus-no-payload classification. Continuing to vary classifiers would
spend researcher degrees of freedom without fixing the control limitation.

## Decision

Pause new research experiments while implementing the seven interfaces in
`docs/CONTROL_EXPANSION_ROADMAP.md`. Begin with a prospective long-form human
no-payload control contract. Software unit tests, schema fixtures, workflow
dry-runs, and machine diagnostics remain mandatory and do not inspect research
outcomes.

## Consequences

- Control provenance and rights are fixed before collection.
- Later hierarchical and target interfaces can be tested on synthetic fixtures
  without exposing Voynichese.
- No new E-number is assigned merely for infrastructure work.
- Research resumes only after the implementation readiness review is recorded.
