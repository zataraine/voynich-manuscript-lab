# ADR 0030: Measure explicit paragraph/session annotations and page-reset compression

## Status

Accepted on 2026-10-13.

## Context

Phase 4 had page and line fields but no paragraph-relative positions or actual
production-session chronology. Inferring session order from folio order would
silently treat physical layout as time. Pooled compression also permits page
concatenation patterns to contribute to a sequence statistic.

## Decision

Add optional paired paragraph ID/relative-line-index and session ID/order-index
fields to numeric records. Preserve caller-supplied annotations through the
adapter and structural nulls. Measure a versioned `layout-measurements-v1`
extension alongside the unchanged v2 core vector, and serialize it for training,
held-out, and held-out null records.

- Paragraph position uses each record's mean group width, computes Spearman
  correlation within each eligible page-scoped paragraph, then averages those
  correlations equally. Require three distinct positions and variable widths.
- Longitudinal drift compares adjacent annotated sessions using explicit order
  indices and unit-distribution Jensen-Shannon divergence. A separate Spearman
  statistic compares session mean group widths against those indices.
- Page-reset compression compares observed and shuffled canonical group codes
  independently per page, then weights gains by page group counts. Preserve the
  existing pooled statistic as a separate scope.
- Report annotation missingness, ineligible paragraphs and undefined quantities.
  Reject partial/invalid annotation pairs, repeated positions in a paragraph,
  inconsistent session indices and distinct sessions assigned the same index.

## Consequences

- A synthetic concatenation control can have positive pooled compression gain
  and exactly zero page-reset gain; this is a scope difference, not meaning.
- Paragraph/session annotations are externally supplied evidence. Record their
  provenance/version in source manifests; the lab does not infer them from glyphs,
  pictures, page names or line-number resets.
- Callers must isolate contributors/documents and apply larger-unit splits when
  sessions or duplicated content cross pages. This extension does not solve
  Phase-6 leakage control or calibrate statistical decisions.
- All four extension criteria are two-sided. Code revision and panel ID identify
  their definitions; the core battery config/hash and historical reports remain
  unchanged. Phase 4 remains open for its full estimator and acceptance review.
