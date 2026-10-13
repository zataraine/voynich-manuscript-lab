# Phase 4 acceptance audit

Status: **open**, reviewed 2026-10-14. This checklist is software readiness for
the joint measurement battery, not a manuscript result or external calibration.
The roadmap remains authoritative. Passing smoke tests alone does not complete
this phase, and no checklist row grants target access.

| Requirement | Implemented evidence | Remaining work |
|---|---|---|
| Conditional uncertainty at reversible scales | Native/STA1 order-0 and within-group order-1 entropy; learned-scale order-0/order-1 panels with frozen tables, record resets, exact/nested/oracle and IID finite-size checks; seven view inverses and saved-table replay | Broader learned-scale sample-size/sparsity and production-parameter recovery checks; learned-scale null calibration is not supplied. |
| Learned-unit transfer | Training-only pair merges, held-out application, saved-table replay, exact expansion, rename and known-motif controls | Broader recovery controls with matched inventory and varied production parameters; freeze failure semantics. |
| Vocabulary growth/tail/recurrence | Type/token and singleton ratios; ordered discovery curves and fixed second-half novel-type rate; pooled/page-reset recurrence with retained events, exact/odd/even/oracle controls and serialized replay | Broader length/page-size, production-parameter and sparse-sample calibration; repeated null ensembles do not yet include the extension. No power-law fit or unseen-vocabulary estimate is claimed. |
| Adjacency and separator effects | Within-record identity, true edge-unit MI, separator/identity MI; exact dependence and independence controls | Complete low-count and unbalanced-class sensitivity checks. |
| Line/paragraph effects | Line association and within-paragraph correlations; positive/negative, offsets and missingness controls | Complete sparse/missing annotation stress cases and ensure eligible support is sufficient for later calibration. |
| Page/section/session drift | Ordered page/section JS and explicit-session endpoints; rename/order and stationary/changing controls | Quantify sample-size and unequal-group effects across registered scopes. Physical order remains distinct from chronological order. |
| Compression/context | Pooled/page-reset gains, unique/run/concatenation and contextual-domain controls; availability abstains on all-singleton observed contextual-reuse interpretations | Complete near-singleton/sparse sensitivity and broader length/context checks. The all-singleton guard is not a calibrated reliability cutoff. |
| Finite samples and nulls | Fixed complete-record prefixes; repeated matched-length structural nulls; retained samples, definedness and unscaled contrasts | Null centering is not a universal bias correction. Complete length/sparsity checks for every endpoint, including the layout panel. |
| Missingness | Explicit support, missing loci/pages/annotations, undefined placeholders/null samples; strict complete-panel availability policy with input-bound audits, validating refusal guard, historical-record and canonical positive/negative checks | Calibrate adequate support and any future partial-panel policy on external controls; complete deletion/missing-page recovery and missing-not-at-random sensitivity. Availability is not reliability. |
| Reproducibility | Canonical control records, hashes, split identity, saved merges/null seeds and replay; executable ten-area report with fresh JUnit evidence, logs and before/after provenance checks | Source acquisition verification and immutable research-run creation belong to the run harness. Software evidence subsets do not close broader scientific readiness gaps. |

## Estimator cautions established by synthetic software checks

- Fair independent binary samples have population entropy/conditional entropy
  of one bit and population association/drift of zero. The plug-in estimators
  exhibit finite-size deviations: empirical entropy is depressed and empirical
  MI/JS can be positive. Fixed-seed increasing-size checks exercise these effects;
  they do not estimate manuscript uncertainty or establish a universal correction.
- Unique group identities imply knowledge of their contextual block. Thus a
  positive group/block MI can be inevitable without recurrence or semantic
  organization. This is an estimator property, not evidence of payload.
- Constant metrics under an invariant null have zero sample SD. Report raw
  differences and preserve zero SD; never amplify floating-point noise by dividing
  by it. E-013 is the historical reason for making this explicit.
- Undefined observed metrics have no contrast, and undefined null replicates are
  stored as `null`, not numeric zero. Defined replicate counts must accompany
  summaries.

## Repeatable software checks

The [executable acceptance inventory](PHASE4_EXECUTABLE_REPORT.md) now assembles
fresh test evidence and the reviewed remaining work for every requirement:

```bash
./scripts/run python -m manuscript_lab.phase4_acceptance \
  --output artifacts/diagnostics/phase4-acceptance-NEW-ID
```

It reports verified software subsets separately from open readiness. Add
`--require-ready` for exit 2 while Phase 4 remains open; passing tests do not
enable target access.

```bash
./scripts/run pytest tests/test_measurement_battery.py \
  tests/test_measurement_records.py tests/test_layout_measurements.py \
  tests/test_sampling_diagnostics.py tests/test_representation_views.py \
  tests/test_vocabulary_growth.py tests/test_schemas.py
./scripts/smoke.sh
```

The repeated-null interface is `sampling_diagnostics.measure_null_ensemble`.
Control-record callers opt in with `null_replicates=N`; there is no hidden
default ensemble budget. The result retains every replicate seed and raw sample,
observed support, null means/sample SDs and unscaled observed-minus-null means.
These are diagnostic differences, not p-values or compatibility decisions.

## Next implementation order

[E-015](E015_UNCERTAINTY_CALIBRATION.md) prospectively calibrates a separate
base-unit uncertainty scope on known binary processes, without optional
production-session or paragraph metadata. The full-panel policy is unchanged;
this is not a fallback after an evaluated full-panel failure or a Phase 4 pass.

The [joint synthetic stress suite](MEASUREMENT_STRESS.md) now exercises 54
short/sparse/imbalanced/unequal-page cases, all four learned scales and three
annotation masks, retaining raw records and undefinedness. Its 1,152 software
checks pass, but 42 learned conditional panels and every masked paragraph panel
are undefined in the documented fixtures. These outcomes motivate an explicit
joint abstention policy; they are not a reliability or calibration pass.

1. Extend learned-scale uncertainty and vocabulary-growth recovery checks
   across sample sizes, inventories and production parameters.
2. Complete bias/sparsity, boundary-scope and missingness checks for the whole
   assembled panel, including the optional extensions.
3. Use the consolidated report to review progress and remaining requirements;
   externally calibrate adequate support before any scientific comparison or
   alternative partial-panel policy.

The [strict availability policy](MEASUREMENT_AVAILABILITY.md) now freezes the
complete-panel abstention rules and is attached to new control records. It
cannot grant scientific comparison or target access. The consolidated report
is implemented; external calibration and broader recovery requirements remain open.

Published mechanism replications can co-develop using these interfaces under
the roadmap, but the final calibration bundle cannot silently substitute a
partially implemented battery for a completed Phase 4.
