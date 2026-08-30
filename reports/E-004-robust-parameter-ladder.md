# E-004 robust parameter ladder

## Result

Training-only invariant feature selection did not make the cipher-family
classifier robust enough for a target comparison. Across 16 fixed transform
variants and three evaluation seeds, four of five preregistered gates failed.
Token-order sensitivity passed. Voynichese was absent, no target was scored, and
no posterior probability was calculated.

## Design

- The same 71 meaningful and 38 human-gibberish source documents supplied 284
  and 84 fixed 100-token chunks. Complete documents remained within one fold.
- Six complete transform families supplied 16 variants: identity, three
  monoalphabetic mappings, three homophonic alphabet sizes, four progressive-key
  settings, three nomenclator/homophonic settings, and two verbose widths.
- Every outer test excluded all variants of one family. Within every document
  fold, the selector used only training documents and nonheldout families to
  choose exactly 12 of 29 features.
- The full 29-feature panel was a nonprimary baseline. Three fixed seeds varied
  document folds, cipher mappings, and model initialization.
- Thirty-two fixed-fold document-label permutations included feature selection.
  Naibbe remained external and token-order destruction retained token inventory.

## Selected-panel transfer

| Seed | Mean family balanced accuracy | Worst family | Progressive family |
|---|---:|---:|---:|
| 20260831 | 0.6305 | 0.5211 | 0.5211 |
| 20260907 | 0.6380 | 0.5211 | 0.5211 |
| 20260913 | 0.5864 | 0.4817 | 0.4817 |

Across all 18 seed-family evaluations, median balanced accuracy was 0.6233,
mean accuracy was 0.6183, and the worst result was 0.4817. The full-panel
baseline had mean 0.6199, median 0.6215, and worst 0.5211. Selection therefore
did not materially improve aggregate transfer and made the single worst result
lower, although the comparison is descriptive rather than a separately powered
model-selection test.

The first seed's observed mean family accuracy was 0.6305 versus permutation
mean 0.4952, with one-sided empirical p = 0.0303. As in E-003, some reproducible
class signal remains, but its magnitude and stability do not meet the frozen
interpretation gates. The experiment does not determine whether the residual
signal is linguistic structure, genre, properties of the supplied controls, or
another surface distinction.

## Feature-selection audit

Selection was recomputed in 90 outer-family/document-fold opportunities. Only
`char_conditional_entropy_bits` and `window20_edit1_copy_rate` appeared in all
90. Six features were never selected. When fitted on the entire synthetic
control set for the external challenges, all three seeds selected the same 12
features. This makes the final selector reproducible, but not sufficiently
transferable.

## External and destruction challenges

The ensemble median for 80 external Naibbe chunks was 0.3638 (interquartile
range 0.3181–0.4222). This improved on E-003's 0.2419 but remained well below
the frozen 0.55 gate.

Token-order destruction produced an ensemble median score drop of 0.0791 and
mean drop of 0.0824; 83.5% of meaningful chunks had a positive drop. The 0.05
gate passed. This demonstrates sequence sensitivity, not semantic recognition.

## Gate outcome

| Gate | Threshold | Observed | Outcome |
|---|---:|---:|---|
| Median seed-family balanced accuracy | at least 0.68 | 0.6233 | fail |
| Worst seed-family balanced accuracy | at least 0.55 | 0.4817 | fail |
| Worst seed mean balanced accuracy | at least 0.60 | 0.5864 | fail |
| Naibbe ensemble median similarity | at least 0.55 | 0.3638 | fail |
| Token-order destruction median drop | at least 0.05 | 0.0791 | pass |

Overall outcome: **fail; no Voynich target comparison permitted**. The posterior
probability remains null by design.

## Local review

The corrected Qwen review assigned effect strength `none`; the GLM critic
assigned `weak`. Both enforced the no-target boundary and highlighted the
Naibbe and seed-stability failures. An initial Qwen summary incorrectly said all
gates failed; it was preserved as `qwen-review-superseded.json`, the fact packet
was made explicit, and the official review was rerun. Reviews remain advisory;
the deterministic preregistered gate controls the decision.

## Provenance

- Preregistration commit: `5ca0f4e`.
- Deterministic implementation commit:
  `e4792deae86c46a458cb51c2a48b107536b93a41`; clean working tree.
- Deterministic result SHA-256:
  `c0e31378df5216aa7841034066dc408c400d5c16a7a825114e82079f008015f0`.
- Official Qwen review SHA-256:
  `66d966d7ca29bf798a570e25d7acb76243e004486254e7440f39cdf164e4a9cd`.
- GLM review SHA-256:
  `1be39be49b2c2f58b9854e45b540eb59671b5256ccb1dfc7727d1b8167958e9b`.
- Source archive SHA-256:
  `553b05807727b81361e127ca04b788d4ea64298527deffdec875db629346bffc`.
- CPU fitting with 12 workers; local GPU review; elapsed workflow time 13:49.
- Machine-readable artifacts are under
  `artifacts/runs/E-004-robust-parameter-ladder/` and remain uncommitted.

## Next falsifiable campaign

The next campaign should stop refining this classifier against the same control
archive. It should assemble a broader, balanced benchmark containing genuinely
paired plaintext and ciphertext from multiple independent historical and modern
cipher systems, with known keys and transformation metadata. The present panel
should be frozen as a baseline while new measurements are developed against
that benchmark. Voynichese remains excluded until external payload transfer is
demonstrated outside Naibbe and the current synthetic ladder.
