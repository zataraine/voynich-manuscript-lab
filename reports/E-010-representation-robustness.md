# E-010 representation robustness

## Outcome

H-010 fails. None of the ten preregistered page features passed every
representation-stability gate, so no feature from this panel is authorized for
the next manufactured-text-versus-hoax experiment as a single witness-invariant
measurement. This is not evidence that the manuscript is meaningless, a hoax,
a language, or a cipher. It is evidence that the present feature values cannot
be treated as interchangeable across the acquired transcription witnesses.

The campaign used 2,185 canonical loci shared by CD2a, FG2a, GC2a, IT2a, and
ZL3b. All minimum-coverage conditions held on 131 pages across 13 views: five
primary STA1 witnesses, two alternate STA1 conversions, and six ZL3b
alternative/uncertain-space views. The code calculated 1,703 page-view records.

## Frozen gates and results

| Feature | Worst primary rho | Bootstrap lower | Max primary difference/IQR | Worst conversion rho | Worst uncertainty rho | Holm p | Failed gates |
|---|---:|---:|---:|---:|---:|---:|---|
| adjacent group repeat rate | 0.720 | 0.600 | 0.050 | 1.000 | 0.922 | 0.0098 | primary rank, bootstrap |
| group hapax ratio | 0.805 | 0.712 | 0.286 | 1.000 | 0.914 | 0.0098 | primary difference, uncertainty difference |
| group length CV | 0.545 | 0.407 | 1.004 | 1.000 | 0.694 | 0.0098 | primary rank, bootstrap, difference; uncertainty rank, difference |
| group length mean | 0.861 | 0.804 | 0.400 | 1.000 | 0.918 | 0.0098 | primary difference, uncertainty difference |
| group type-token ratio | 0.918 | 0.863 | 0.274 | 1.000 | 0.953 | 0.0098 | primary difference, uncertainty difference |
| symbol bigram type ratio | 0.947 | 0.910 | 0.442 | 1.000 | 0.989 | 0.0098 | primary difference |
| normalized conditional symbol entropy | 0.839 | 0.767 | 0.582 | 0.995 | 0.978 | 0.0098 | primary difference |
| normalized symbol entropy | 0.712 | 0.613 | 1.187 | 0.983 | 0.965 | 0.0098 | primary rank, bootstrap, difference |
| symbol repeat rate | 0.552 | 0.395 | 0.000 | 1.000 | 0.830 | 0.0098 | primary rank, bootstrap; uncertainty rank |
| 20-group recurrence | 0.756 | 0.648 | 0.315 | 1.000 | 0.884 | 0.0098 | primary rank, bootstrap, difference; uncertainty rank, difference |

The table reports the preregistered worst-case values. The primary rank gate was
rho >= 0.80, its bootstrap lower-bound gate was >= 0.70, and the maximum
primary difference was <= 0.25 feature IQR. Conversion gates were rho >= 0.95
and difference <= 0.10 IQR. Uncertainty gates were rho >= 0.90 and difference
<= 0.15 IQR. All gates were conjunctive.

## What the failure localizes

The aligned-page null is not the problem. Every feature's median pairwise page
correlation exceeded 1,024 independently permuted page-label controls; all ten
Holm-adjusted p-values are 0.00976. The witnesses therefore retain common page
structure well above the unrelated-page baseline.

The official CD and GC alternate STA1 conversion files are also not the main
problem. Conversion-pair ranks are 0.983-1.000 and their median normalized
differences are zero for all ten features. The few locus-level conversion
differences found in Q-011 do not materially move these page summaries.

The dominant failure is witness-dependent magnitude. Symbol bigram diversity
and conditional entropy preserve page ordering strongly, but their cross-witness
offsets are 0.442 and 0.582 feature IQR, respectively. Several group measures
also depend materially on uncertain-space treatment. The lowest primary ranks
usually involve CD2a versus GC2a; the largest magnitude disagreements usually
involve FG2a versus GC2a or GC2a versus IT2a. This pattern supports modelling
witness-specific measurement error or bias; it does not justify deleting GC,
choosing a preferred witness after inspection, or relaxing the frozen gates.

## Verification and provenance

- Preregistration commit: `fb33894f9c370a4c3e095778596e93391ce25ccc`.
- Clean implementation commit: `e6d987e542b94eacd984bbd77ee491f303558307`.
- Result SHA-256: `b93ecb462ca69d71a160d1edad7b6356335d32a8964fe70c24e6ca5cc24ad8c1`.
- Page-feature SHA-256: `0faa913a884a9d0847b03ac4f9e80073bffb1974f8ca059a1768cd3a567a9022`.
- Runtime: 52.88 seconds on CPU; bootstrap seed 20260901; permutation seed
  20260902.
- A clean in-memory replay reproduced all feature results and 1,703 page-view
  records exactly.
- The full gate passed with 102 tests, all workflow dry-runs, CPU/GPU probes,
  OpenFST/Pynini, Snakemake, and the local-AI health checks.

The local Qwen review is retained at
`artifacts/runs/E-010-representation-robustness/qwen-review.json` (SHA-256
`67fc6b47b8ebaba55036be147e5c6c94b73aa4956655aa0eda27d854ccd08918`).
It agreed with the stop boundary but misassigned the group-length-CV values to
group-length mean and called this audit a classifier. It is therefore advisory
only and supplies no numeric evidence. A second local GLM pass returned
confidence 0.008 and an unsupported transient-noise conjecture; it was not
retained as evidence. The deterministic record and preregistered gates are
authoritative.

## Consequence

The next defensible campaign must calibrate a witness-aware measurement model
on controls before returning to Q-002. Candidate approaches are a hierarchical
latent-page model with explicit witness offsets and uncertainty intervals, or
within-witness standardized page contrasts whose invariance is validated on
held-out pages and synthetic transcription perturbations. Post-hoc threshold
relaxation, consensus transcription, and exclusion of the difficult witness are
not permitted responses to E-010.
