# 0007: Require known-payload and witness-stability gates

- Date: 2026-08-30
- Status: accepted

## Context

E-001 showed that several simple nonsemantic generators fail to reproduce selected
Voynichese sequence measurements, while a copy/mutate generator remains compatible on
important dimensions. That result cannot supply odds for meaning. A supervised control
comparison can also be misleading if document fragments leak across folds, if plain text
is the only meaningful control, or if the conclusion changes with transcription.

## Decision

Build E-002 as a document-grouped calibration campaign. Train only on known meaningful
texts and independently human-produced gibberish. Keep the Naibbe ciphertext collection
outside training as a known-meaningful-payload stress test. Score six IVTFF witnesses as
out-of-distribution targets and require calibration, Naibbe, and cross-witness gates
before reporting even surface similarity.

Use fixed, interpretable feature extraction and two untuned baseline model families.
Aggregate and bootstrap at document level. Run label permutation at document level.
Language models review bounded deterministic summaries but do not compute metrics or
receive corpus text.

## Consequences

The campaign can fail cleanly. In particular, failure on Naibbe demonstrates that the
plain-text calibration cannot transfer through at least one plausible cipher family;
Voynich scores must then remain uninterpreted. Passing all gates still does not identify
language, semantics, cipher family, authorship, or intent and does not create a posterior
probability.
