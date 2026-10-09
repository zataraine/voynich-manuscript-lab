# Frozen joint measurement battery

`measurement-battery-v2` is target-independent software for comparing explicit
production mechanisms. It is not an experiment, classifier, target score, or
decipherment method. It accepts only reversible numeric records whose symbols,
groups, separator classes, page, section, and line identities have already been
frozen by the representation contract.

V2 corrects boundary, metric-definition, ordering, and learned-unit tie handling
found in the synthetic audit. The v1 config remains historical; the current
loader rejects it so that corrected outputs cannot be labelled as v1. Historical
E-001--E-014 experiments use separate modules and are unaffected.

The adapter accepts only one `(registry, view, alphabet, witness)` scope at a
time. It converts retained non-separator observations to deterministic integer
IDs, turns certain and uncertain separators into distinct typed boundaries, and
keeps the projection hash plus the physical record/page/section/line identity.
Loci with no retained group are reported in coverage as missing records.

## Measurements

The battery reports conditional unit uncertainty, group vocabulary and singleton
tails, recurrence distances, adjacent-group identity, separator-edge association,
line-position association, page and section drift, contextual-domain
information, and observed-minus-shuffled compression. Every rule is two-sided
at this stage: a mechanism may be incompatible because a value is either too
high or too low. It does not select a feature or direction from manuscript
results.

Adjacent-group identity counts only pairs within a record. Cross-separator edge
information measures dependence between the last unit of the left group and
the first unit of the right group. The separate `separator_identity_mi_bits`
measures dependence between separator class and whole-group equality; v1 had
reported that quantity under the edge-information name. Page and section drift
compare successive partitions in first-appearance order, following supplied
physical order rather than sorting arbitrary labels.

Recurrence, contextual blocks, and compression currently use the supplied pooled
record order. Their scope differs from within-record adjacency; the remaining
Phase-4 review must evaluate page resets and layout sensitivity before freezing
the final calibration bundle.

Learned units use a deterministic pair-merge tokenizer. Its merge table is fit
only on supplied training records, frozen, then applied to held-out records.
Merge counts are fixed in the config. The units are compression devices, not
assertions about letters, morphemes, or words.

Equal-frequency pair merges break ties by first occurrence, which is invariant
to any bijection of symbol IDs. The training/held-out interface rejects duplicate
record IDs, overlapping IDs, and overlapping physical pages before fitting.
Larger codicological/document grouping remains the caller's responsibility.

## Nulls and finite samples

The supplied structural nulls shuffle group order, shuffle units inside each
group, or draw independent units from the observed global marginal while
preserving every record, group width, and typed boundary sequence. The last is
therefore length-matched and marginal-matched *in expectation*, not a deceptive
claim that every generated sample retains exact symbol totals. These retain only
the aspects named by their labels; they are diagnostic nulls, not universal null
models.

The battery also emits a fixed increasing complete-record profile at sizes named
in its config. It is a finite-sample sensitivity diagnostic, not a correction:
it makes drift attributable to available record count visible without cutting a
physical record or silently changing boundaries. Undefined quantities return the
declared neutral value `0.0`; all output must be finite. Each future calibration
must report coverage, missingness, source manifest, view registry, seed, null
family, finite-sample profile, and the complete vector in config order.

`measurement_support` records transition, edge, recurrence, page, and section
support and names undefined metrics separately from measured zero values. The
training/held-out and finite-sample interfaces attach this support beside the
numeric vector. A caller using the low-level `measure_core` must also call the
support interface; the numeric zero placeholder alone cannot indicate validity.

## Verification status

Synthetic tests now cover exact entropy, vocabulary, recurrence, adjacency,
binary edge and separator dependence, positive/negative line-position and
context-domain controls, finite-size fair-binary entropy, arbitrary learned-unit
renaming, partition-label renaming, unequal-length null invariants, and split
leakage rejection. These are software checks with known answers, not new
manuscript findings or external mechanism calibration.

Phase 4 remains in progress. Remaining work includes full view/scale recovery,
paragraph and longitudinal interfaces, calibrated missingness handling, broader
estimator-bias and compression controls, and the serialized joint result and
acceptance report. Passing the current tests does not mark the phase complete.

## Boundary

The module has no manuscript loader and refuses to infer a direction, threshold,
or compatibility decision. Phase 5 supplies mechanism controls; Phase 6 supplies
external calibration and the sealed target barrier.
