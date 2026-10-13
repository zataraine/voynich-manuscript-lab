# E-015: Known-process uncertainty calibration

Status: preregistered design; no manuscript access. Phase 4 control-only
estimator development, not a payload classifier or Phase 5 mechanism replication.

## Scope correction

The complete-panel availability policy remains unchanged. It requires session
and paragraph annotations for its declared full panel; it cannot be a universal
prerequisite for every question. `uncertainty-scope-v1` prospectively names two
existing base-unit measurements: unigram entropy and within-group first-order
conditional entropy. It requires record/page identity and reversible supplied
grouping, not production chronology, paragraph or section annotations.
Undefined estimates still abstain. This scope never automatically replaces a
failed full panel or authorizes target access. All other panels remain required
for their own questions.

Conditional character entropy is an established comparison topic; see
[Lindemann and Bowern (2021 version)](https://arxiv.org/abs/2010.14697v2).
This campaign is not a replication of their corpus experiment. Its independent
arithmetic oracle uses [SciPy entropy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.entropy.html).

## Frozen design and truth

Every group starts with an independent fair bit, then flips the previous bit
with probability p. Groups reset, matching the estimator. For p={0.5,0.1,0.01},
population H0=1 bit and H1=`-p*log2(p)-(1-p)*log2(1-p)`.
p=0.5 is the independent reference. None of these generators has intended
linguistic payload; no payload classifier is trained.

The experiment config fixes three probabilities, three lengths and 32
independent replicates per cell: 288 paired simulations. Each split has four
disjoint physical pages, with 4/16/64 groups per page and 32 units per group:
512/2,048/8,192 units. Split seeds and input hashes are retained. Training
estimates are diagnostics; there is no fitted model or segmentation.

Only the largest length is used for eight conjunctive primary gates:

- Six probability/metric means require `abs(mean-truth)+critical*SE <= 0.05 bits`.
- Both adjacent H1 mean differences (p=0.5 versus 0.1, then 0.1 versus 0.01)
  require a lower bound of at least 0.2 bits. Difference SE is the square root
  of the sum of squared mean SEs.

The critical value is Student-t with 31 degrees of freedom and two-sided
Bonferroni allocation of family alpha=0.05 over eight intervals. These are
approximate Monte Carlo intervals for mean estimator error across corpora,
not individual-corpus accuracy, exact coverage or a universal sample-size rule.
Smaller lengths are diagnostics, not opportunities to select a favorable result.
Construction gates require independent joint-minus-context arithmetic,
bijective-renaming invariance, disjoint pages and defined scoped panels.
Software tests use separate small/extreme fixtures, not the 288-case campaign.

## Execution and stopping

Commit the design first. The code refuses dirty-tree research execution and
checks its synthetic generator manifest. Use the existing ledger runner:

```bash
./scripts/lab experiment register config/experiments/E-015-uncertainty-calibration.yaml
./scripts/lab experiment execute E-015-uncertainty-calibration -- \
  ./scripts/run python -m manuscript_lab.uncertainty_calibration
```

The immutable result under `artifacts/runs/E-015-uncertainty-calibration/`
retains every replicate, theoretical value, mean/SE/error bound, all gates,
split input hashes and code/config/source/profile/environment provenance.
Stop after the fixed grid; no adaptive extra runs or threshold changes.
Construction failures require investigation; primary failures remain failures
over this tested domain. A completed scientific failure is not a process failure.
A rerun needs a new attempt/protocol. Even full success gives no manuscript
score or Phase 4 completion: broader inventories/scales, mechanism controls,
witness sensitivity and external validation remain separate requirements.
Local Qwen may review a compact summary, not calculate evidence or alter gates.
