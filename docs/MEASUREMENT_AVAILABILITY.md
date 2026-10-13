# Joint measurement availability and abstention

`measurement-availability-v1` is a strict complete-panel availability contract
for synthetic/external control records. It does not establish estimator
reliability, calibration, a mechanism comparison, or manuscript access.

## Rules

The versioned policy is `config/research/measurement-availability-v1.yaml`.
Changing its semantics requires a new reviewed policy, not a relaxed value
chosen because a control failed. Its implementation checks:

- current frozen battery identity and declared control-source kind;
- no source loci without retained groups or assigned pages without usable records;
- exact core metric coverage and definedness for training, held-out and all
  three configured single-draw null families;
- complete section, paragraph and session annotations, and no ineligible
  declared paragraphs;
- complete/defined layout and pooled/page-reset growth panels for both splits
  and each single-draw null;
- complete/defined training and held-out uncertainty at every frozen merge budget;
- no all-singleton observed split presented as contextual-reuse evidence.

No-repeat recurrence and no-transition conditional entropy are undefined even
when their stored numeric placeholders are zero. Conversely, an empirically
measured zero with valid support is not automatically a failure. Finite values
are necessary, not sufficient. No population minimum sample size or universal
missing-data correction is inferred from these rules.

This first policy forbids partial panels, including a page-reset recurrence
summary that is undefined on just one required page. It is intentionally
conservative and will abstain on many legitimate corpora and null draws.
That is a policy outcome, not rejection of the underlying production mechanism.
An alternative endpoint-specific or partial-panel protocol would need a new
version fixed and calibrated outside the manuscript, not an automatic fallback.

## Integration and enforcement boundary

New `build_control_measurement_record` outputs include an `availability` audit
after canonical validation. It retains a policy hash, a SHA-256 over the entire
measurement record excluding the audit itself, status and scoped reasons.
Canonical serialization recomputes this audit and rejects mismatches, including
forged status, deleted reasons, changed input or a stale policy hash.

Call the validating guard before handing a control record to a future joint
comparison consumer:

```python
from manuscript_lab.measurement_availability import require_available_measurements

audit = require_available_measurements(record)
```

It raises `MeasurementError` on abstention. If it returns, the status is
`available_not_calibrated`; `joint_comparison_allowed` remains false and
`target_access` remains forbidden. A separate calibrated harness must make the
future scientific authorization decision. The low-level assessor assumes
canonical validation; the guard supplies it.

Historical records without the optional audit remain readable, but the guard
computes a fresh audit. Historical records missing required extensions abstain.
Deleting an extension from an audited record is a change, not a historical
record, and its old audit correctly fails replay. Existing historical E-series
modules and low-level measurement functions are not retroactively rewritten or
access-controlled. This is an explicit interface boundary, not the future
sealed-target barrier or proof of source authenticity.

Repeated-null ensembles, learned-scale null panels, finite-prefix diagnostics,
source acquisition integrity, power and missing-not-at-random corrections are
not certified by this policy. The single-draw null requirement does not imply
that null calibration is complete. Missingness auditing and scientific
calibration remain distinct.

## Verification

```bash
./scripts/run pytest tests/test_measurement_availability.py \
  tests/test_measurement_records.py
./scripts/smoke.sh
```

Synthetic checks cover defined zero versus undefined zero, missing metrics,
scales, extensions, annotations, loci, pages and nulls; input-bound hash replay;
audit tampering; historical-record guards; and a fully defined canonical
24-record control with a positive availability outcome but no calibration or
target permission. Fixtures are software checks, not external research evidence.
