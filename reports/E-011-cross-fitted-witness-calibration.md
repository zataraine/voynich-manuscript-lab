# E-011 cross-fitted witness calibration

## Outcome

H-011 fails. The frozen median/IQR calibrator passed its recoverable and broken
synthetic controls, but only one of ten manuscript features passed every
held-out witness, fold, conversion, uncertainty, bootstrap, and null gate. The
required totals were four stable features and two order-sensitive features.

The sole passing feature is `symbol_bigram_type_ratio`, which is also
order-sensitive. It may be retained as a representation-robust descriptive
measurement, but one feature is insufficient to return to the manufactured
language versus nonsemantic-text question. All witnesses must remain separate
measurement series in later work unless a separately preregistered method is
validated.

## Controls

The 256-page recoverable control applied five independently seeded offsets,
positive scales, and small measurement noise to one latent sequence. Its worst
held-out pairwise Spearman rho was 0.9957 and its maximum median calibrated
difference was 0.0438, passing thresholds of 0.95 and 0.20. After independently
permuting page identity in four views, median pairwise rho was 0.0122, below the
0.15 negative-control ceiling. Every synthetic calibration IQR was valid.

These results show that the implementation can recover the specific global
offset/scale mechanism it claims to test and does not manufacture agreement
after page identity is destroyed.

## Manuscript results

| Feature | Stable | Worst primary rho | Bootstrap lower | Max primary difference | Passing folds | Worst uncertainty rho | Max uncertainty difference | Failed gate summary |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| adjacent group repeat rate | no | 0.666 | 0.515 | 0.371 | 2/5 | 0.887 | 0.179 | rank, agreement, folds, uncertainty |
| group hapax ratio | no | 0.809 | 0.716 | 0.320 | 3/5 | 0.908 | 0.189 | primary/fold and uncertainty agreement |
| group length CV | no | 0.546 | 0.409 | 0.494 | 0/5 | 0.669 | 0.390 | rank, agreement, folds, uncertainty |
| group length mean | no | 0.855 | 0.795 | 0.298 | 3/5 | 0.923 | 0.162 | primary/fold and uncertainty agreement |
| group type-token ratio | no | 0.921 | 0.872 | 0.218 | 4/5 | 0.951 | 0.156 | uncertainty agreement only |
| symbol bigram type ratio | **yes** | 0.938 | 0.898 | 0.232 | 4/5 | 0.988 | 0.082 | none |
| normalized conditional symbol entropy | no | 0.846 | 0.776 | 0.306 | 3/5 | 0.979 | 0.110 | primary agreement and folds |
| normalized symbol entropy | no | 0.728 | 0.632 | 0.506 | 1/5 | 0.960 | 0.137 | primary rank/agreement/folds; conversion agreement |
| symbol repeat rate | no | undefined required comparisons | undefined | undefined | 4/5 in finite comparisons | undefined | 0.000 in finite comparisons | zero training IQR and resulting non-finite gates |
| 20-group recurrence | no | 0.776 | 0.680 | 0.302 | 3/5 | 0.884 | 0.256 | rank, agreement, folds, uncertainty |

All nine features with finite aligned-page statistics again beat 1,024
page-label permutations after Holm correction (adjusted p = 0.00976). That
supports shared page ordering, not interchangeable magnitudes. The official CD
and GC conversion variants remain highly consistent. The main residual failures
are held-out cross-witness agreement and uncertain-space sensitivity.

`group_type_token_ratio` missed only the frozen uncertainty-agreement gate
(0.156 versus the 0.150 ceiling). This is reported as a near miss, not rounded
into a pass. Conditional entropy also improved materially from E-010 but failed
both its overall primary-difference and four-of-five-fold requirements.

GC's symbol-repeat series had zero training IQR in folds 0 and 2, correctly
triggering the preregistered calibration failure. The original immutable run
serialized the resulting non-finite comparisons as JSON nulls; some subordinate
extrema/null fields were nevertheless finite because Python's extrema can skip
NaN depending on order. `calibration_iqrs=false` already excluded the feature,
so this did not affect the stable subset or H-011. The evaluator was immediately
hardened so any required non-finite comparison fails every dependent gate. A
corrected in-memory evaluation retained exactly the same sole stable feature.

## Provenance and verification

- Preregistration commit: `874775f8e738adefb56151976b22f3fe2513e752`.
- Clean run implementation: `1cfb2f32df2e824d3dd84d3b0c233038b8b817bf`.
- E-010 input result SHA-256: `b93ecb462ca69d71a160d1edad7b6356335d32a8964fe70c24e6ca5cc24ad8c1`.
- E-010 page-feature SHA-256: `0faa913a884a9d0847b03ac4f9e80073bffb1974f8ca059a1768cd3a567a9022`.
- E-011 result SHA-256: `5f0b643f3342bef387dc6b36c4c1aad970b7f04d51fdf69b0571101e95eadf2b`.
- Split SHA-256: `fa1ab8e1794df8cc2e2c9694e09e32a4be312dc5ee12515a347255c4fe403c2f`.
- Calibrated-feature SHA-256: `aa5f3f4595eb28f8a44055e340653ce9c9a394afa24d4fda47ddb63164c40656`.
- Runtime: 47.50 seconds on CPU; five contiguous folds; seeds 20260903,
  20260904, and 20260905.
- A serialized deterministic replay reproduced all 17,030 calibrated records,
  feature results, and controls.
- The pre-run full gate passed 105 tests, all workflow dry-runs, and all machine
  diagnostics. No local LLM review was used.

## Consequence

Do not keep trying calibrators against the same 131 pages. E-010 and E-011 now
show that one global witness correction is insufficient. The efficient next
route is a multi-witness replication design: run each future control-calibrated
test separately for each primary witness, require directionally consistent
held-out results, and treat witness as a replication axis rather than merging
it away. The sole stable bigram-diversity measurement can be included, but it
cannot carry the manufactured-versus-nonsemantic question alone.
