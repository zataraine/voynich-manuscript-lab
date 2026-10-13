# ADR 0029: Serialize reversible control measurements before mechanism campaigns

## Status

Accepted on 2026-10-13.

## Context

The Phase-4 battery returned merge-table hashes without the tables themselves.
That was insufficient for replaying held-out unitization without refitting.
Measurements, support, split assignments, and representation provenance also
needed a common record before external mechanism campaigns could consume them.

## Decision

Add a control measurement record over one verified representation scope. Retain
the complete training-only merge tables as nested pair JSON, hash their canonical
array bytes, and expose application, restoration, and expansion interfaces.
Expansion recovers the space-erased numeric sequence per record; original groups
and separators remain in the supplied representation and its inverse audit.

The record includes the battery/config identity, ordered metric names, source
manifest and code/environment declarations, complete input-projection digest
(including physical metadata), symbol table, source projection hashes, split
assignments, missing loci/pages, measurement support, fixed finite-size profiles,
and three seeded held-out diagnostic nulls. Canonical serialization validates the
schema, finite complete metric vectors, consistent battery identity, and saved
merge-table hashes. The only decision label is `not_calibrated`.

## Consequences

- Synthetic checks cover all seven registered views and four learned-unit
  budgets, raw projection replay, numeric expansion, JSON round-trip, saved-table
  reapplication, expected separator/ligature/grapheme differences, and a known
  motif transfer control with an unseen-inventory negative control.
- V2 merge-table hashes now use explicitly named `nested-pair-json-v1` encoding
  instead of Python `repr`; Git preserves the previous development implementation.
- The builder verifies supplied projections, not external source acquisitions.
  Provenance values and control-source declarations remain caller assertions;
  this interface is not Phase 6's sealed-target access barrier.
- These records are intermediate measurements, not scientific calibration or
  Phase-4 completion. Full layout, longitudinal, bias/compression, and calibrated
  missingness gates remain open.
