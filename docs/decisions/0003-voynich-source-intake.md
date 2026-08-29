# 0003: Treat the Voynich corpus as tiered, independent evidence

- Status: accepted
- Date: 2026-08-29

## Context

The manuscript has one physical source but many digital renderings,
transcriptions, encodings, analyses, and claimed decipherments. Combining these
at acquisition time would erase disagreements, create circular validation, and
make later results impossible to audit.

## Decision

Use Yale's IIIF record as the canonical image and canvas-order source. Preserve
every IVTFF/STA transcription witness byte-for-byte and independently. Store
physical reports and scholarly baselines in separate manifests. Treat analysis
pages and decipherment proposals as hypothesis sources, never labels.

Acquisition is configured, atomic, media-type checked, hashed, and constrained to
`data/raw`. The commercial Voynich Research viewer is not scraped because its
published terms prohibit it. Mixed or absent licenses are recorded conservatively.

## Consequences

- Raw intake is larger (about 894 MiB) but folio-level work can use the original
  resolution and canonical IIIF labels.
- A later alignment layer must model witness disagreement explicitly.
- Re-running acquisition does not overwrite existing raw files; tracked manifests
  reveal any out-of-band mutation.
- Tests of published decipherments must use frozen mappings and held-out folios,
  with the claim corpus isolated from discovery data.
