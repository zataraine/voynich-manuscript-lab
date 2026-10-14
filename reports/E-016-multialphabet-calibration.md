# E-016: Larger-alphabet calibration passes, with substantial short-sample bias

## Result

All six construction checks and 24 preregistered primary gates passed across
864 paired simulations (1,728 split corpora). At the fixed primary length of
65,536 units per split, the largest mean-error bound was 0.020392 bits, below
the 0.05-bit tolerance. All six adjacent conditional-entropy gap lower bounds
exceeded 0.2 bits; the smallest was 0.446902 bits.

This calibrates two existing base-unit uncertainty estimators for the tested
uniform-stationary, first-order copy/redraw processes with unequal group widths.
It is not a manuscript, meaning, cipher-identification or general readiness result.

The complete design was committed and published before execution at
`0a0658bead9ce648610a084a9ccace743d4068a8`. The CPU run used that clean revision,
the locked environment and `config/experiments/E-016-multialphabet-calibration.yaml`.
Four pages per split remained disjoint; no manuscript or external text was read.
See [the frozen protocol](../docs/E016_MULTIALPHABET_CALIBRATION.md).

## Short samples are not reliable by default

Each length includes nine alphabet/process cells and two metrics per cell.
Each mean summarizes 32 independently seeded held-out corpora. The following
diagnostics were retained prospectively, not substituted for primary gates.

| Units per split | Largest mean-error bound, bits | Mean signed error in that cell, bits | Metric/cell bounds above 0.05 |
|---|---:|---:|---:|
| 512 | 1.537040 | -1.521145 | 13/18 |
| 8,192 | 0.125931 | -0.110585 | 3/18 |
| 65,536 (primary) | 0.020392 | -0.013070 | 0/18 |

All three worst cells concern conditional entropy at K=32. The 512-unit cell
is independent (copy probability zero); the other two have copy probability
0.9. These are different cells, not a same-process convergence trajectory.
In particular, a large alphabet and sparse observed transitions can create
apparently low uncertainty even when the source is independent. These results
do not establish a universal minimum manuscript sample size, but they prohibit
treating short-page plug-in estimates as automatically accurate.

Bounds use the frozen approximate Student-t/Bonferroni procedure across 24
primary intervals, applied descriptively also to the shorter lengths. They
describe mean estimator error over simulated corpora, not individual-corpus
accuracy, exact interval coverage or inferential guarantees for the diagnostics.

## Integrity, review and limits

Independent joint-minus-context arithmetic agreed within 3.56e-15 bits.
Bijective renaming, disjoint pages, defined measurements, unique split seeds
and exact unit budgets all passed. A full regeneration reproduced every numeric
result and the original JSON bytes after reattaching original provenance.
This replay is an integrity check, not additional independent observations.

Local Qwen reviewed a compact result-hash-linked packet using 1,998 prompt and
152 completion tokens. Its assertion that three lengths "confirm estimator
consistency" is not adopted: finite simulations do not prove asymptotic
consistency. Its confidence/effect labels and absence of listed confounds are
not evidence that broader limitations were resolved. The deterministic record
and stated restrictions govern the interpretation.

Uniform marginals, first-order dependence and a deterministic width cycle
remain restrictive. No realistic cipher/natural-language corpus, learned units,
transcription uncertainty or payload discrimination was calibrated. The strict
full-panel policy and manuscript-access barrier are unchanged. Phase 4 remains
incomplete; Naibbe software parity and published-statistic replication remain
separate work, described in [the encoder audit](../docs/NAIBBE.md).

## Retained provenance

- Result: `artifacts/runs/E-016-multialphabet-calibration/result.json`.
- Result SHA-256: `af78c71271903299d2594befbb5ad4c9b2d95c1fb68043c99c5e94de40d56107`.
- Config SHA-256: `77549a29964535d8fde5fd410cb5ca4c9da3f515af08030d3604943140385c35`.
- Source-definition SHA-256: `fe2ed99735ee32c631305cccc11ceacf133e365de3c84bc0376af6d3a42c9b66`.
- Environment-lock SHA-256: `a8ab5fb543e4ae96ace2cb9a657b46729553ed2f5c1286c38056d83955cdbaa2`.
- Review packet/response: `qwen-review-input.json`, `qwen-review.json` in the run directory.
- Retained local replay audit: `inspect_replay.py`; execution log: `runner.log`.
- Ledger status: `REVIEW_LOCAL`; all 12 current event-chain links verified.

Generated runs remain local and ignored. Tracked source/config/manifest allow
regeneration. The pinned Qwen runtime was unchanged; its stopped service was
restored through existing controls before the full smoke gate passed (305 tests).

## Next step

Implement bounded, seeded parity with the pinned Naibbe encoder and an independent
implementation, preserving table selection, ambiguity retries, line resets and
space deletion. Validate known plaintext truth before using this mechanism as
a new calibration control. No further classifier or manuscript inference is
justified by E-016 alone.
