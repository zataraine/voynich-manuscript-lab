# ADR 0017: Lineage-aware, locus-keyed witness lattice

## Status

Accepted on 2026-08-31.

## Context

IVTFF defines a manuscript-wide page name and sequence number for each locus,
but the acquired witnesses use several incompatible transliteration alphabets.
Their provenance is also dependent: IT and VT share Takahashi/LSI ancestry, and
RF is an automatically generated combination of ZL and GC with separate full
and basic EVA renderings. Counting byte agreement across alphabets, or counting
derived witnesses as independent votes, would be invalid.

## Decision

Align witnesses only on `(IVTFF page name, locus number)`. Preserve zero, one,
or several readings per witness in each cell. Distinguish a page outside a
witness's coverage from a locus omitted on a covered page. Retain the complete
Q-010 reading record and structural units.

Record witness alphabet, lineage group, comparison group, independence role,
and derivation edges in a tracked registry. Native strings are not compared
across alphabets. Compare exact or markup-excluded reading surfaces through the
official STA1 conversion files among members of the shared STA1 group.
Markup exclusion removes paragraph markers, free comments, and text tags only;
uncertainty, alternatives, separators, ligatures, and drawing interruptions
remain evidence. Cross-alphabet comparison is limited to locus presence and
structural locus codes unless a registered STA1 view exists. CD and GC each have
two supplied conversion variants; one is the primary view and the other is
retained as a sensitivity view, never as an additional witness.

Order lattice cells using the complete ZL3b witness's IVTFF page order and locus
number, appending any otherwise unseen page deterministically. The output is
JSON Lines with a provenance header and one auditable record per canonical
locus.

## Consequences

- No consensus reading is created.
- Missingness and transcription disagreement become measurable.
- Derived witnesses remain useful for sensitivity analysis but cannot inflate
  independent support.
- Glyph-level equivalence across alphabets remains a separate, explicit
  conversion problem.
