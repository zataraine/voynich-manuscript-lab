# ADR 0022: Floor numerically constant robust scales

## Status

Accepted on 2026-09-01 after the E-013 technical failure and before E-013R1.

## Context

E-013's manual robust scaler replaced exact zero IQRs but not floating-point
residue. An IQR of `2.78e-17` amplified one feature by roughly fifteen orders of
magnitude and invalidated classifier fitting.

## Decision

Treat a training IQR <= `1e-12` as constant and replace its divisor with 1.0.
Record which effects were treated as constant. The tolerance equals the frozen
metric-invariance tolerance already used by the lab. Add a regression test with
near-constant input.

## Consequences

- Constant effects cannot acquire influence solely from floating-point noise.
- E-013 remains an immutable technical failure.
- E-013R1 recomputes the entire campaign with no scientific-design changes.
- The retry, not an in-memory reinterpretation, is the only admissible H-013
  result.
