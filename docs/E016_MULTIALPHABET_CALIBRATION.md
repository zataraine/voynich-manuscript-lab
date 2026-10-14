# E-016: Larger alphabets and heterogeneous group boundaries

Status: preregistered design; not yet executed.
This extends E-015 within `uncertainty-scope-v1`; it does not replace the full
panel, authorize manuscript access or complete Phase 4.

## Question and acceptance test

Do the same H0 and within-group H1 estimators recover known population values
for larger inventories and unequal group widths? Reuse the existing estimators,
independent arithmetic oracle and locked CPU environment, without fitting.

Freeze K={4,16,32}, copy probability r={0,0.5,0.9}, split unit budgets
{512,8192,65536}, and 32 replicates per cell: 864 paired cases. Each split has
four pages. Each page repeats widths {1,2,4,8,16,32}, clipping its last group
to the exact page budget. Groups restart uniform; each subsequent symbol copies
the preceding symbol with probability r, otherwise redraws uniformly from K.
This is deliberately not a manuscript-derived length distribution.

Population H0=log2(K). Each conditional row has probabilities
`r+(1-r)/K` on its diagonal and `(1-r)/K` elsewhere, so H1 is that row's entropy.
r=0 is the independent reference. No process contains intended linguistic payload.

Only the prespecified 65,536-unit split is primary. Eighteen metric/cell gates
require `abs(mean-truth)+critical*SE <= 0.05 bits`. Six adjacent-r H1 gaps
require `mean_left-mean_right-critical*hypot(SE_left,SE_right) >= 0.2 bits`.
Use Student-t with 31 degrees of freedom, two-sided Bonferroni allocation of
alpha=0.05 across all 24 intervals. These approximate intervals address mean
error over simulated corpora, not individual-corpus accuracy or exact coverage.
Retain shorter-length errors even when they exceed tolerance; do not select
a new sample size, estimator or threshold after observation.

Six construction gates require independent joint-minus-context agreement and
bijective-renaming invariance within 1e-12 bits, disjoint split pages, defined
scoped panels, unique split seeds and exact split unit budgets. Small software
fixtures are separate from the research grid. Stop after the fixed 864 cases.
Any failed primary/construction gate prevents a tested-domain pass. Scientific
failures remain valid results; technical failures require a recorded new attempt.

## Execution and provenance

Commit this protocol, config, generator and source definition before execution.
The runner refuses a dirty tree, source-hash mismatch or existing result path.

```bash
./scripts/lab experiment register config/experiments/E-016-multialphabet-calibration.yaml
./scripts/lab experiment execute E-016-multialphabet-calibration -- \
  ./scripts/run python -m manuscript_lab.multialphabet_calibration
```

The immutable local result retains all replicate estimates/support, input hashes,
seeds, truth, summaries and gates plus code/config/source/profile/lock provenance.
No acquired text, target data, learned segmentation or local-model inference is
needed for the arithmetic. Uniform marginals, first-order dependence and a fixed
width cycle limit generalization. Naibbe replication remains separate.
