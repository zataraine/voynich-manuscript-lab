# ADR 0023: Test higher-order controls before returning to the target

## Status

Accepted on 2026-09-02.

## Context

E-013R1 showed that E-012's eight low-level effects are robust across
transcriptions but not specific to intentional payload. Structured generators
and human-produced gibberish frequently occupy the same feature space. Retuning
that panel or inspecting Voynichese for replacement features would spend target
degrees of freedom without improving calibration.

## Decision

E-014 will exclude Voynichese and test one fixed higher-order panel on the same
document-disjoint, mechanism-held-out controls. The panel measures vocabulary
growth, length dynamics, recurrence, contextual-domain information,
order-sensitive compression, and co-occurrence topology. It excludes semantic
models and sparse long-lag token mutual information.

The E-013R1 model remains a published baseline and is not refit as part of the
new panel. All family, independent-source, human-gibberish, and Naibbe gates are
retained.

## Consequences

- The next compute spend can improve specificity or falsify a concrete panel.
- No manuscript score can influence feature choice or thresholds.
- A pass still requires a separate witness-robustness experiment before any
  target classification.
- A failure closes this panel rather than triggering post-hoc feature removal.

