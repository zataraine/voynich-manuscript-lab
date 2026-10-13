# 0037: Consolidate Phase 4 evidence without automatic approval

Date: 2026-10-14
Status: accepted

## Question and acceptance

Can one command report every Phase 4 requirement, freshly verified software
evidence, and reviewed outstanding work without promoting unit tests to a
scientific readiness pass? Require all ten areas, retained logs/JUnit evidence,
failure/skip/missing-evidence handling, before/after provenance checks, new
artifact directories and a readiness mode that refuses to pass while open.

## Decision

Add the versioned acceptance registry and `phase4_acceptance` report command.
Run the union of mapped synthetic software tests once. Record file-level
verified subsets separately from the reviewed open-work inventory. V1 keeps
readiness open; a successor must deliberately review any claim of completion.
No new dependencies, models, source acquisition or manuscript reads are needed.

## Consequences

The report makes remaining work auditable but does not measure its scientific
adequacy. File-level tests establish only the stated subset, not a whole
requirement. Registry content must be maintained during publication review.
The report is not the full smoke gate, the full stress sweep, external
calibration or a sealed-target barrier. See `docs/PHASE4_EXECUTABLE_REPORT.md`.
