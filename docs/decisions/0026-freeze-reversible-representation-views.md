# ADR 0026: Freeze reversible representation views before measurements

## Status

Accepted on 2026-09-02.

## Context

EVA and other transliterations encode editorial choices about glyph composition,
alternatives and spaces. Selecting one interpretation after observing a result
would build part of a decipherment into the input and create researcher degrees
of freedom.

## Decision

Adopt `config/corpora/representation-views-v1.yaml` and
`docs/REPRESENTATION_VIEWS.md`. Preserve primary witnesses separately, require
registered uncertainty views, attach exact raw inverses and source spans, and
share physical-page splits across all projections. Integer IDs label observed
units only and carry no arithmetic or linguistic interpretation.

## Consequences

- No model may choose a preferred witness, separator policy, glyph composition,
  or learned-unit scale from target performance.
- Space-erased and first-alternative views are permitted only with an inverse
  audit and joint robustness rule.
- Synthetic and related witnesses cannot inflate independent replication.
- Phase 4 may implement measurements against this interface without renaming
  observed units as letters or words.
