# 0036: Fail closed on unavailable joint measurements

Date: 2026-10-14
Status: accepted

## Question and acceptance

Can undefined/missing measurements be prevented from silently entering a joint
comparison as observed zeros or a selected partial vector? Require explicit
reasons, complete-panel semantics, a validating refusal guard, replayable
input-bound audits, and positive/negative canonical control checks. No
availability outcome may authorize calibration or manuscript access.

## Decision

Freeze the conservative `measurement-availability-v1` policy described in
`docs/MEASUREMENT_AVAILABILITY.md`. Attach it to new control measurement records
and verify it during canonical serialization. Legacy records remain readable;
the guard recomputes availability instead of treating a missing audit as a pass.

Require complete observed and single-draw-null core/layout/growth panels and
both split panels at all frozen learned scales. Block missing source/page or
required annotations, ineligible declared paragraphs, undefined metrics and
all-singleton observed contextual-reuse interpretations. Never infer an
arbitrary calibrated minimum support from the current synthetic cases.

## Consequences

Legitimate inputs can abstain under this strict policy. Abstention is not a
mechanism rejection. A less strict endpoint-specific policy requires a new
prospective version and external calibration, not an automatic fallback.
Available means only available: the status remains `available_not_calibrated`,
joint scientific comparison stays unauthorized and target access stays forbidden.
The guard is not a global filesystem barrier or source-authenticity guarantee.
