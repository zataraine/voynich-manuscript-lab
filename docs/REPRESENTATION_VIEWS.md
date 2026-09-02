# Reversible representation and witness contract

## Purpose

Every future measurement or cipher search consumes a named view from
`config/corpora/representation-views-v1.yaml`. A view is an auditable projection
of observed transcription marks, not an assertion that a glyph is a plaintext
letter, a blank-delimited group is a lexical word, or a gap is a word boundary.

The raw diplomatic surface, exact source spans, excluded-unit audit, registry
hash, alphabet and witness remain attached. Integer IDs are deterministic labels
for `(observation kind, surface)` pairs; their numeric magnitude has no meaning.

## Witness policy

The five required primary lineage views are `CD2a`, `FG2a`, `GC2a`, `IT2a`, and
`ZL3b`. They remain separate replications. `VT0e` is a related sensitivity view.
`RF1b-e` and `RF1b-er` are synthetic derivatives and are prohibited as
independent evidence. Official alternate STA1 conversions are mandatory
sensitivity projections, never extra witnesses. No merge, majority vote, or
preferred transcript is permitted.

## Frozen base views

- Native code-point and grapheme projections preserve each alphabet separately.
- STA1 atomic projections treat each registered two-character STA code as one
  observed unit solely because that is the declared STA encoding contract.
- Ligatures are retained as composite structural units in the base view and
  decomposed into their declared STA units in a required sensitivity view.
- Alternative readings are either preserved structurally or use the first
  registered alternative while retaining the complete raw inverse.
- Certain and uncertain separators remain distinct, or a preregistered view
  erases uncertain/all spaces with an explicit span audit.
- Editorial paragraph markers, comments and tags are excluded from analysis but
  retained in the inverse record.

Space erasure does not join observations into proven words. It merely creates a
boundary-free sequence on which phase-4 learned-unit methods may be fitted using
training physical groups only. Merge counts are frozen before held-out use.

## Splits, coverage and failure

All views of one physical page or larger codicological group share the same
split. Locus projections retain physical source-line numbers and the complete
page metadata map, including the section field when supplied by IVTFF. Every
result reports view, witness, source alphabet, included and excluded observation
counts, locus/page coverage, missingness and registry hash.

A method fails representation robustness if it requires choosing a witness,
conversion, alternative policy, separator policy or learned-unit scale after
seeing target results. Failure in one view is reported rather than averaged
away. The later measurement battery must predeclare whether its joint rule is a
worst-view conjunction or another externally calibrated aggregation.

## Reversibility

Some analysis projections deliberately omit separators or editorial units.
They remain reversible artifacts because the exact raw surface and SHA-256 are
part of each record and every projected observation points to its original
span. Verification recomputes the complete projection from the raw inverse and
requires byte-identical observations, exclusion audit and hashes.

This contract defines representation only. It does not measure Voynichese,
select features, score mechanisms, or authorize manuscript inference.
