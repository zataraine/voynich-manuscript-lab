# 0010: Select invariant features inside the training boundary

Date: 2026-08-30

## Status

Accepted for E-004 before implementation or execution.

## Context

E-003 detected cross-family signal but failed three of four preregistered gates.
It represented most synthetic cipher families with one parameter setting. Using
E-003's observed held-out-family results to hand-pick features would leak the
evaluation families into model design and exaggerate apparent improvement.

## Decision

E-004 treats complete cipher families as the outer domain boundary and complete
source documents as the sample boundary. Within every outer family/document
fold, rank features using only training documents transformed by non-heldout
families. The fixed ranking score is median standardized class separation across
training variants divided by one plus cross-variant instability. Retain exactly
12 features. Report a full 29-feature baseline, but make the nested selected
panel primary.

Use three fixed evaluation seeds and multiple parameter variants. Preserve all
four E-003 thresholds and add a 0.60 floor for the worst seed's mean family
accuracy. Apply identical variant distributions to both control labels. Keep
Naibbe external and keep Voynichese absent.

## Consequences

The selected feature set may differ across folds; selection frequency becomes
an audit output. E-004 will take substantially longer than E-003. A failed gate
is a valid result and cannot be repaired by choosing the full-panel baseline,
another seed, or a favorable transform parameter after execution.
