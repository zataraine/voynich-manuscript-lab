# E-015: Uncertainty estimators pass a bounded known-process calibration

## Result

All four construction checks and eight preregistered calibration gates passed
over 288 paired simulations (576 split corpora). This is evidence about two
base-unit estimators on the tested symmetric binary processes, not a manuscript
result, payload classifier, or completion of Phase 4.

The design was committed before execution at
`c307ad6f0b2beb45d3d8f8bec064f7589b990baf`. The run used that clean revision,
the locked environment, CPU, four separate pages per split, and the config in
`config/experiments/E-015-uncertainty-calibration.yaml`. The synthetic generator
manifest is `data/manifests/e015-synthetic-processes.yaml`; there is no acquired
text or manuscript input. See the dedicated protocol for the frozen design.

## Largest tested sample: 8,192 units per split

Each row summarizes 32 held-out replicate corpora. Bounds use the preregistered
approximate Student-t/Bonferroni procedure across eight intervals.

| Flip probability | Population H1, bits | Mean observed H1, bits | Largest mean-error bound across H0/H1, bits |
|---|---:|---:|---:|
| 0.5 | 1.000000 | 0.999820 | 0.000251 |
| 0.1 | 0.468996 | 0.468384 | 0.006383 |
| 0.01 | 0.080793 | 0.081371 | 0.004294 |

All six mean-error bounds were below the fixed 0.05-bit tolerance. Adjacent H1
gap lower bounds were 0.525665 and 0.380148 bits, exceeding the fixed 0.2-bit
requirement. Unigram population entropy was one bit in all three processes;
conditional entropy distinguished their different amounts of local dependence.
Small-length diagnostics are retained but were not primary gates or selected
after observation. No monotonic convergence claim is made from their finite draws.

Construction checks confirmed defined scoped estimates, disjoint split pages,
exact bijective-renaming invariance, and independent arithmetic agreement to
within 5.56e-16 bits. Regenerating all cases from the committed code/config
reproduced the numerical result and its retained JSON bytes exactly when the
original execution provenance was reattached. This replay is not a second
independent experiment or extra calibration sample.

## What this fixes—and does not

The prospectively named `uncertainty-scope-v1` requires record/page identity and
reversible grouping, not unknown production-session or paragraph annotations.
The full-panel availability policy was not weakened. There is no automatic
fallback from a failed full panel to this smaller profile.

The calibration bounds describe mean estimator error across these simulated
corpora, not individual-document accuracy. Student-t intervals are approximate;
Bonferroni allocation does not turn approximate intervals into exact coverage.
The study tests only binary marginals, symmetric first-order dependence, fixed
group widths and three lengths. It does not establish accuracy for manuscript
inventories, uncertain transcriptions, learned units, realistic variable groups,
natural-language/cipher controls or any semantic classification.

Local Qwen reviewed a compact, result-hash-linked summary and retained these
main limitations. Its response is advisory: its wording "well-calibrated" is
not adopted as a general claim, and ordinary passed checks listed under its
"anomalies" field are not numerical anomalies. Confidence and effect labels
from the model are not experiment evidence. No model calculated the statistics.

## Provenance and retained outputs

- Result: `artifacts/runs/E-015-uncertainty-calibration/result.json`.
- Result SHA-256: `c29b0db76a6dfc5c374e8ac3dccf04dd301f0c0f9da0debd5bafcd39d46bbdca`.
- Source-definition SHA-256: `56c62abf62edb3f6c6faeaae2d3bd8171ef7f670a1d3447ac520504834308464`.
- Config SHA-256: `4c966163a78be40fac59884d234efd58a9cd11e447c22b3caec1a3d29f9f108d`.
- Environment-lock SHA-256: `a8ab5fb543e4ae96ace2cb9a657b46729553ed2f5c1286c38056d83955cdbaa2`.
- Review input/output: `qwen-review-input.json`, `qwen-review.json` in that run directory.
- Runner log and hash-chained ledger retain execution and `REVIEW_LOCAL` status.

Generated outputs stay local and immutable. The tracked config, generator and
source definition permit regeneration; model review need not reproduce
byte-for-byte. The pinned local-AI runtime was unchanged.

## Next scientific work

Extend known-truth estimator checks to larger inventories and heterogeneous
group boundaries, and co-develop the published mechanism replications. Do not
expand this pass into a general readiness claim. Manuscript scoring remains
prohibited until the relevant external and representation gates pass.
