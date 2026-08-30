# E-002 control calibration

## Result

The surface-statistic ensemble separated held-out meaningful source documents
from human-produced gibberish within the supplied control collection, but it did
not transfer to the known-payload Naibbe ciphertexts and it was not stable across
the six transcription witnesses. The preregistered interpretation gate therefore
failed. No Voynich score from this experiment may be interpreted as evidence of
meaning, language, cipher, constructed language, or hoax.

## Calibration

- 109 source documents produced 368 fixed-length chunks; all chunks from a
  document stayed in one fold and each document had equal total fitting weight.
- Document ROC AUC: 0.9225.
- Document balanced accuracy: 0.8262; bootstrap 95% interval 0.7411–0.8999.
- Document Brier score: 0.1123.
- The 128 document-label permutations had mean balanced accuracy 0.5097;
  one-sided empirical p = 0.00775.

These values show that the selected features distinguish the two supplied
training-control collections. They do not establish what those features detect
outside that domain.

## Failed transfer and sensitivity gates

The withheld Naibbe collection contains meaningful payloads transformed by a
known cipher. Its median meaningful-similarity score was 0.1423, far below the
preregistered 0.60 gate. The plain-text calibration therefore does not survive
this cipher transformation.

Voynich witness medians ranged from approximately 0.189 to 0.718. Only three
physical pages supplied an eligible 100-token sample in all six witnesses. On
those pages the median across-witness score range was 0.4282, exceeding the
0.25 stability gate. This is strong evidence that transcription/unitization
choices dominate part of this particular measurement setup. It is not evidence
that any witness is correct or that leakage occurred.

## Gate outcome

| Gate | Threshold | Observed | Outcome |
|---|---:|---:|---|
| Document balanced accuracy | at least 0.65 | 0.8262 | pass |
| Naibbe median similarity | at least 0.60 | 0.1423 | fail |
| Common-page witness median range | at most 0.25 | 0.4282 | fail |

Overall outcome: **fail; no target interpretation permitted**. The posterior
probability remains null by design.

## Local review

After benchmarking versioned role prompts and a custom GLM profile, both local
reviewers stated the same claim boundary. Qwen assigned target effect strength
`none`; GLM likewise reported no permitted target claim. Their reviews remain
advisory. In particular, an outlying GC2a score is not evidence of leakage.

## Provenance

- Deterministic code commit: `7f34990266d82474e2072bf9b2ec732e0df78bd1`;
  clean working tree.
- Deterministic result SHA-256: `fea9ddd5da96e61653762c5d254614ce6c34580e2de5e319c8c8a84ef786e8cf`.
- Qwen review SHA-256: `1e8754db9d24c8782a80d07ed3e329aefb5098ada89b67e66219be4dbabec701`.
- GLM review SHA-256: `a6a5ccd07c5d4f4d3488fae99950318cfe79b776927a6b55dceb6a01c751fa78`.
- Seed: 20260830; CPU fitting with 12 workers; local GPU review.
- Full machine-readable artifacts are under
  `artifacts/runs/E-002-control-calibration/` and remain uncommitted.

## Next falsifiable step

Build a controlled transformation ladder in which the same payload-bearing and
nonsemantic source documents are measured before and after explicit cipher
families. Measure which features survive monoalphabetic, homophonic,
nomenclator-like, progressive polyalphabetic, and Naibbe transformations. In
parallel, align common physical pages across witnesses with reversible multiple
unitizations. Only features that transfer across held-out cipher families and
remain witness-stable should reach a new Voynich comparison.
