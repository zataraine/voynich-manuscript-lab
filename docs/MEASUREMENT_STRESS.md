# Joint measurement stress diagnostics

This is synthetic software verification, not E-015, external calibration, a
manuscript result, or the complete Phase 4 acceptance report. The existing
measurement modules are exercised without modifying their estimator definitions.

## Reproduce

```bash
./scripts/run python -m manuscript_lab.measurement_stress \
  --output artifacts/diagnostics/measurement-stress-NEW-ID.json
./scripts/run pytest tests/test_measurement_stress.py
```

The command uses the bounded `config/research/measurement-stress-v1.yaml` and
refuses an existing output path. It has no corpus/text loader. Reports retain
all generated training/held-out records, seeds, split/page identities, metrics,
support, frozen tables, null outputs, annotation masks, individual check results,
configuration/battery/input hashes, code/working-tree provenance and environment
lock hash. The device is CPU. Generated JSON is ignored by Git. Exceptions stop
the job rather than creating a success report; failed boolean checks are saved
and cause a nonzero exit. Future immutable attempt IDs must be distinct.

## Scope

Six scenarios at 4, 16 and 64 records per split, using seeds 211, 223 and 227,
give 54 cases. Each record has eight groups. Widths follow a fixed 1/2/3 cycle
to create a known positive within-paragraph position/width association. These
are deliberately annotated synthetic paragraphs, not inferred layout.

- `constant`: every base symbol is identical; variable group widths still
  create several group types. This is not an all-identical-group fixture.
- `unique`: every base symbol is unique within each split.
- `binary_iid`: independent fair binary base symbols.
- `large_inventory_iid`: independent uniform base symbols over 32 IDs.
- `imbalanced_iid`: independent binary base symbols with 95% probability of zero.
- `unequal_pages`: binary symbols with all but the final record assigned to one
  page. This changes page sizes, not the sequence generator.

Training and held-out records use disjoint physical-page IDs and seeds s and
s+1. No learned table is refitted on held-out or null records. Both split
inventories may share IDs, as ordinary synthetic corpora do; this is not a test
of unseen alphabets. All four frozen merge budgets are exercised. Each of the
three structural null families is measured once per case, including learned
uncertainty with the original training table. This does not extend the existing
repeated core-null ensemble format.

Annotation masks remove all annotations (`none`), alternating records, or the
longest synthetic lines. The latter is deliberately selective missingness,
not a claim of random dropout. Masking must leave core, growth and frozen-unit
measurements unchanged. Layout support and undefinedness are retained; no
annotation or missing sequence is imputed. Removing an annotation is different
from deleting a physical record, which this suite does not test.

Checks cover finite outputs, page isolation, core/growth symbol-renaming
invariance, the known paragraph direction, annotation invariance, explicit
fully missing layout, and the unique-type extreme. Core rename comparisons use
an explicit absolute tolerance of 1e-12; maximum differences are retained.
An initial bitwise-equality assertion failed because JS summation order changed
the unique fixture by about 1.1e-15. The tolerance handles numeric roundoff,
not a change to a scientific acceptance threshold or estimator.

## Verified diagnostic snapshot: 2026-10-14

Local artifact: `artifacts/diagnostics/measurement-stress-20261014.json`.
SHA-256: `070c0d85558186fdbb41f10627e945b8d75d2ddd6e2bb900d2bf0f3c20d6d4d4`.
The artifact records the base revision and dirty-tree digest of the implemented
suite. Exact full-file hashes include that execution provenance; later clean
checkouts need not reproduce the same file hash to reproduce numeric cases.

All 1,152 boolean checks passed across 54 cases. The largest retained rename
difference was about 1e-15. These passes are consistency checks, not a bound on
estimator error or false-positive rates.

Useful limitations exposed by these fixtures:

- 42 of the 216 held-out learned-scale panels had no eligible transition after
  merging. Their conditional entropy is explicitly undefined despite a numeric
  zero placeholder. Any future joint rule must abstain or use a predeclared
  partial-panel policy, never treat those values as measured predictability.
- Each annotation mask left zero eligible three-line paragraphs in all 54 cases.
  This follows from the fixture construction; it does not estimate real-world
  dropout tolerance. It demonstrates why recording missingness without an
  eligibility rule is insufficient.
- Unique groups had contextual MI of roughly 0.95, 2.76 and 4.70 bits at the
  three lengths (seed 211). That increase is mechanical identity/block
  association without recurrence. It is not evidence of organization or payload.

## Remaining gates

Finite does not mean reliable. These cases do not estimate universal bias,
sampling uncertainty, power, family specificity, natural-language compatibility
or missing-not-at-random corrections. The literature likewise distinguishes
raw MI from chance-adjusted measures; see the
[scikit-learn clustering guide](https://scikit-learn.org/stable/modules/clustering.html#mutual-information-based-scores).
This suite does not substitute a new adjusted estimator for the frozen one.

Broader production-parameter recovery, deletion/missing-page cases, explicit
joint exclusion/abstention rules, repeated-null coverage for all extensions,
external controls and a consolidated acceptance report remain required. No
target-access permission follows from this report; Phase 4 remains open.
