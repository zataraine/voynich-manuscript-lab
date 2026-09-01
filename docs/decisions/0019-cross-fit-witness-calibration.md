# ADR 0019: Cross-fit witness calibration instead of choosing a transcript

## Status

Accepted on 2026-09-01.

## Context

E-010 found shared page ordering but witness-dependent feature magnitudes. A
preferred witness or post-hoc consensus would discard observed uncertainty;
fitting a correction on every page and evaluating those same pages would leak
the target into its own calibration.

## Decision

Treat each transcription/uncertainty view as a measurement method. Use one
frozen robust location/scale transform learned on four contiguous page blocks
and applied only to the fifth. Concatenate held-out predictions. Preserve rank
and retain separate rank/agreement gates. Require recoverable and broken
synthetic controls plus aligned-page nulls.

## Consequences

- Global editorial offsets and scales can be corrected only if they transfer to
  physically held-out pages.
- Page-specific disagreement and non-monotone distortions still fail.
- No witness is promoted to ground truth or removed after inspection.
- A different calibrator requires a new preregistered experiment.
