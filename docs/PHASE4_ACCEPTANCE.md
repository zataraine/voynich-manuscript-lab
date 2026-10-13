# Phase 4 acceptance audit

Status: **open**, reviewed 2026-10-14. This checklist is software readiness for
the joint measurement battery, not a manuscript result or external calibration.
The roadmap remains authoritative. Passing smoke tests alone does not complete
this phase, and no checklist row grants target access.

| Requirement | Implemented evidence | Remaining work |
|---|---|---|
| Conditional uncertainty at reversible scales | Native/STA1 order-0 and within-group order-1 entropy; learned-scale order-0/order-1 panels with frozen tables, record resets, exact/nested/oracle and IID finite-size checks; seven view inverses and saved-table replay | Broader learned-scale sample-size/sparsity and production-parameter recovery checks; learned-scale null calibration is not supplied. |
| Learned-unit transfer | Training-only pair merges, held-out application, saved-table replay, exact expansion, rename and known-motif controls | Broader recovery controls with matched inventory and varied production parameters; freeze failure semantics. |
| Vocabulary growth/tail/recurrence | Type/token ratio, singleton ratio, global recurrence and fixed record-prefix profiles | Freeze a growth endpoint and resolve recurrence reset scope; a type/token ratio is not a full growth model. |
| Adjacency and separator effects | Within-record identity, true edge-unit MI, separator/identity MI; exact dependence and independence controls | Complete low-count and unbalanced-class sensitivity checks. |
| Line/paragraph effects | Line association and within-paragraph correlations; positive/negative, offsets and missingness controls | Complete sparse/missing annotation stress cases and ensure eligible support is sufficient for later calibration. |
| Page/section/session drift | Ordered page/section JS and explicit-session endpoints; rename/order and stationary/changing controls | Quantify sample-size and unequal-group effects across registered scopes. Physical order remains distinct from chronological order. |
| Compression/context | Pooled and page-reset gains, unique/run/concatenation controls, contextual-domain controls | Contextual MI can be positive solely because every group is unique. Freeze diagnostic handling for sparse/singleton-dominated inputs and broader length/context checks. |
| Finite samples and nulls | Fixed complete-record prefixes; repeated matched-length structural nulls; retained samples, definedness and unscaled contrasts | Null centering is not a universal bias correction. Complete length/sparsity checks for every endpoint, including the layout panel. |
| Missingness | Explicit support, missing loci/pages/annotations, undefined numeric placeholders and null samples | Freeze joint exclusion/abstention policy without converting undefined measurements into measured zeros. |
| Reproducibility | Canonical control records, hashes, split identity, saved merges, null seeds and summary replay | Complete the consolidated executable acceptance report. Source acquisition verification and immutable run creation belong to the run harness. |

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

```bash
./scripts/run pytest tests/test_measurement_battery.py \
  tests/test_measurement_records.py tests/test_layout_measurements.py \
  tests/test_sampling_diagnostics.py tests/test_representation_views.py \
  tests/test_schemas.py
./scripts/smoke.sh
```

The repeated-null interface is `sampling_diagnostics.measure_null_ensemble`.
Control-record callers opt in with `null_replicates=N`; there is no hidden
default ensemble budget. The result retains every replicate seed and raw sample,
observed support, null means/sample SDs and unscaled observed-minus-null means.
These are diagnostic differences, not p-values or compatibility decisions.

## Next implementation order

1. Finish the still-missing vocabulary-growth endpoint, with explicit
   recurrence/reset scope; extend learned-scale uncertainty recovery checks.
2. Complete bias/sparsity and missingness checks for the whole assembled panel.
3. Freeze joint exclusion rules and issue a reproducible acceptance report that
   names every satisfied and failed requirement.

Published mechanism replications can co-develop using these interfaces under
the roadmap, but the final calibration bundle cannot silently substitute a
partially implemented battery for a completed Phase 4.
