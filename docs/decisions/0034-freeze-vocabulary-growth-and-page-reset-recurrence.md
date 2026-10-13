# 0034: Ordered vocabulary growth and page-reset recurrence

Date: 2026-10-14
Status: accepted

## Question and acceptance

Can the measurement record distinguish early from late discovery of group types
when final type/token ratios agree, and expose cross-page recurrence separately?
Require exact constant/unique and late-discovery controls, odd/even lengths,
independent prefix/recurrence oracles, renaming invariance, page-order/reset
checks, explicit short/empty missingness, JSON replay across all seven views,
and corrupt-summary rejection. This is software verification, not an experiment.

## Decision

Add optional `vocabulary-growth-v1` panels to control measurement records.
Builders emit training, held-out and the same three single-draw structural
nulls already used by the core. Keep the core vector unchanged and historical
records readable. No additional package, model or learned parameter is needed.

Group identity is exact equality of numeric tuples in the frozen view. Retain
one-based first-discovery positions and distances between successive occurrences
of the same group. These events regenerate every reported summary. They do not
reconstruct the original identities; projections and their provenance remain
the source for full replay.

For N groups let h=floor(N/2) and V(n) count distinct types in the first n groups.
Freeze the second-half novel-type rate as `(V(N)-V(h))/(N-h)`, undefined for N<2.
This counts newly discovered *types*, not every occurrence of a type absent from
the first half. Retain curve checkpoints at powers of two, h and N (unique,
positive, sorted); exact discovery positions also recover unsampled prefixes.
Recurrence uses group-index distances, not glyph counts or elapsed time. No
repeated groups means undefined recurrence, not measured zero distance.

The pooled scope follows supplied record/group order and crosses record/page
boundaries. Page-reset scopes reunite each page's records in supplied relative
order and retain pages in first-appearance order. They are separate panels,
not an average across unequal pages or inferred longitudinal sessions.

## Motivation and limits

[Baayen (1996), pp. 455–458](https://aclanthology.org/J96-4001.pdf) defines
vocabulary growth over token prefixes and discusses bias from clustered lexical
usage. That motivates preserving order and recording curves, not assuming
exchangeable samples or forcing a smooth law. Our half-split endpoint is a lab
design choice, not a replication of that paper's model. Numeric groups are not
assumed to be linguistic words.

Do not fit or claim a Heaps-law exponent, extrapolate unseen vocabulary, or infer
language, payload or hoax status. A constant sequence and a unique sequence have
known extremes, not scientific classification labels. Unequal lengths,
page sizes, missingness, production parameters and broader null ensembles still
need calibration. Existing repeated core-null ensembles do not include this
extension. Missing records remain in the parent coverage report; this module
cannot measure their unobserved groups. Phase 4 remains open.
