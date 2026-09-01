# ADR 0020: Treat witnesses as a replication axis

## Status

Accepted on 2026-09-01.

## Context

E-010 found no interchangeable raw feature panel, and E-011 found that one
global held-out location/scale correction leaves only one stable feature.
Continuing to tune consensus or calibration methods against the same pages
would overfit representation choices.

## Decision

Run each fixed E-001 structure effect independently in five primary STA1
witnesses and five additional ZL3b uncertainty views. Use one shared physical
page split. Define each primary p-value as the worst view p-value and correct
only the eight effects fixed from E-001. Require all eight to pass. Keep
copy/mutate as a mandatory ambiguity diagnostic.

## Consequences

- A difficult witness or uncertainty policy can veto an effect.
- No witness is averaged, calibrated, selected, or treated as ground truth.
- Failure closes the fixed E-001 mechanism branch.
- Passing still requires external natural/cipher/nonsemantic control validation.
