# Frozen joint measurement battery

`measurement-battery-v1` is target-independent software for comparing explicit
production mechanisms. It is not an experiment, classifier, target score, or
decipherment method. It accepts only reversible numeric records whose symbols,
groups, separator classes, page, section, and line identities have already been
frozen by the representation contract.

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

Learned units use a deterministic pair-merge tokenizer. Its merge table is fit
only on supplied training records, frozen, then applied to held-out records.
Merge counts are fixed in the config. The units are compression devices, not
assertions about letters, morphemes, or words.

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

## Boundary

The module has no manuscript loader and refuses to infer a direction, threshold,
or compatibility decision. Phase 5 supplies mechanism controls; Phase 6 supplies
external calibration and the sealed target barrier.
