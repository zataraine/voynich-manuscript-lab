# ADR 0027: Make finite-size and length-matched nulls explicit in the measurement battery

## Status

Accepted on 2026-09-02.

## Context

Short samples can make entropy, vocabulary, recurrence, and compression values
appear to differ because of available material rather than production process.
Likewise, a null that destroys group layout can confound sequence organisation
with group-length or separator structure. The Phase-4 measurement battery needs
these assumptions to be visible before mechanism controls are introduced.

## Decision

`measurement-battery-v1` names three deterministic diagnostic nulls and fixed
complete-record profile sizes. The `iid_symbol_length_matched` null retains
record IDs, group widths, and typed boundary sequence, then samples observed
units independently from the pooled marginal distribution. It matches the
marginal in expectation, not exactly; that limitation is reported rather than
hidden. Independent seed derivation isolates every null family's random stream.

The finite-sample profile measures only configured whole-record prefixes. It is
a sensitivity diagnostic, not an estimator correction or a decision rule.

## Consequences

- Future calibrations must serialize null family and finite-sample output.
- Metrics that move with record count remain visible for later calibration;
  this change does not declare them biased or correct them post hoc.
- No target corpus is accessed, no threshold is selected, and Phase 4 remains
  incomplete until its complete estimator, length, rename, round-trip, and
  synthetic-recovery gates are met.
