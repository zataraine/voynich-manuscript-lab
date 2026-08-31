# E-006 cipher-relation representation

## Result

The preregistered fused character-relation representation made a large and
stable improvement over E-005, but it did not satisfy the family-general claim.
Six of eight gates passed. Eight cipher families showed substantial exact-
payload retrieval, including Enigma, while ADFGX remained near chance and
caused both magnitude-gate failures. Voynichese was absent, no manuscript
target was scored, and no posterior probability was calculated.

## Design

- The E-005 sources, 48 fixed 600-character segments, document folds, nine
  cipher families and keys, candidate sets, normalization, and six original
  gates were frozen by config and result hashes.
- The single primary representation was named before implementation. Its 885
  dimensions concatenate the 29 E-005 surface relations, 410 symbol-renaming-
  invariant frequency/recurrence features, 434 modular aligned-relation
  features, and 12 normalized compression distances.
- Every primary fit excluded the complete evaluated cipher family and one
  complete four-document fold. The complete evaluation was repeated over three
  fixed classifier seeds.
- Each component was scored separately as a diagnostic and could not replace
  the fusion. Same-family/new-document fitting localized transfer failures;
  exact decryption supplied a mechanical ceiling.
- A 256-replicate identity permutation supplied the null. Fixed independent
  position destruction tested whether retrieval depended on sequential order.

## Family-blind transfer

| Held-out family | Mean normalized MRR | Mean top-1 lift | Mean pair ROC AUC |
|---|---:|---:|---:|
| Affine | 1.0000 | 16.00 | 1.0000 |
| Vigenere | 1.0000 | 16.00 | 1.0000 |
| Autokey | 0.9956 | 15.89 | 0.9975 |
| Beaufort | 0.9956 | 15.89 | 0.9998 |
| Bifid | 0.8318 | 12.22 | 0.9566 |
| Columnar | 0.8051 | 11.67 | 0.9503 |
| Rail fence | 0.6631 | 9.78 | 0.9363 |
| Enigma | 0.6225 | 8.56 | 0.9193 |
| ADFGX | 0.0472 | 1.78 | 0.5078 |

The mean normalized MRR across all family/fold/seed cases was 0.7734 versus a
permutation-null mean of -0.00082 (one-sided empirical p = 0.00389). Seed means
were 0.7656, 0.7801, and 0.7745, so the aggregate result was not dependent on a
favorable fit seed.

The position-destruction control reduced normalized MRR by a median 0.6170 and
a mean 0.4918; 81.5% of cases declined. This establishes that the fusion uses
sequential relationships rather than only length or symbol inventory. It does
not establish semantics or a cipher family for the manuscript.

## Representation diagnosis

The component results explain the improvement without permitting post-hoc
substitution. The modular relation bank achieved normalized MRR 1.0 on
Vigenere, autokey, and Beaufort; 0.9120 on Bifid; and 0.4768 on Enigma. The
invariant signature achieved 1.0 on affine and rail fence and 0.9765 on
columnar. Their preregistered fusion therefore covers complementary mechanism
classes rather than relying on the old surface panel alone.

No component solved ADFGX: component normalized MRR ranged from -0.0413 to
0.0375. More importantly, the same-family/new-document fusion also failed for
ADFGX (normalized MRR -0.0234; AUC 0.4640), while the other eight same-family
results were essentially perfect. This localizes the remaining problem to the
representation or unitization of the combined fractionation/transposition
pipeline, not merely leave-family-out transfer. All 432 cipher roundtrips and
the exact-decryption MRR ceiling were 1.0, so the underlying cipher generation
and inversion audit passed.

## Gate outcome

| Gate | Threshold | Observed | Outcome |
|---|---:|---:|---|
| Median family normalized MRR | at least 0.20 | 0.8318 | pass |
| Worst family normalized MRR | at least 0.05 | 0.0472 | **fail** |
| Median family top-1 lift | at least 2.5 | 12.22 | pass |
| Worst family pair ROC AUC | at least 0.55 | 0.5078 | **fail** |
| Identity-permutation p-value | at most 0.05 | 0.00389 | pass |
| Exact roundtrip fraction | exactly 1.0 | 1.0 (432/432) | pass |
| Worst-seed mean normalized MRR | at least 0.15 | 0.7656 | pass |
| Exact-decryption ceiling MRR | exactly 1.0 | 1.0 | pass |

Overall outcome: **fail; no Voynich target comparison permitted**. The
family-general hypothesis requires every gate, so the size of the improvement
and the narrow numerical MRR miss do not authorize moving the boundary.

## Local review

The corrected Qwen review accurately identified both ADFGX-driven failures,
Enigma's strong result, the significant permutation result, sequence
dependence, and the no-target boundary; it assigned effect strength `none` and
requested escalation. Its first output was preserved as superseded after it
incorrectly described Enigma and the same-family results.

The final GLM critic identified the ADFGX same-family anomaly and assigned
effect strength `weak`, but its assessment emphasized the strong families and
its suggested follow-up also named positive Enigma and rail-fence results. Two
earlier GLM outputs were preserved after factual or wording problems. These
reviews are advisory; the deterministic preregistered gate controls the claim.

## Provenance

- Preregistration commit: `0f09229`.
- Deterministic implementation commit:
  `6a20d13e6c74bdc8bc91bc79bb0619d2e9cc807a`; clean working tree.
- Deterministic result SHA-256:
  `922176b82ef359dc2e3d2941a4e1a1fb085016a3a2ad53070b2a5965bb5af2d1`.
- Corrected Qwen review SHA-256:
  `cc1776b65582c99eeb6c909dd6f04c5aa12fb35f0c78d88ed165fb819a86cc44`.
- Final GLM review SHA-256:
  `4e9c592d862deefeaf0803d0e9daf447fed50abc8267f346a9459ed767dcfa26`.
- Reference-packet SHA-256:
  `23f097add71c57653127cb05a050d500f5607abf3b06df3833b1c10ff1e48859`.
- E-006 config SHA-256:
  `4364bf21cce141a86ecec2782c87853589c49e11bbad4afeb009c5a9af76354c`.
- Source-manifest SHA-256:
  `ae6a26ac04a22bc20bcf746d852cb4d394707ee3fa13126e0d2fb5f8870842c1`.
- Frozen E-005 result SHA-256:
  `3dbbacc53cb0df616ce9f5921a70e12489a207b99dbbc4f8f5efd24e509d0e4d`.
- CPU feature extraction and fitting with 12 workers; local Qwen and GLM GPU
  review. Machine-readable artifacts remain under
  `artifacts/runs/E-006-cipher-relation-representation/` and are uncommitted.

## Next falsifiable campaign

E-007 should not tune E-006 thresholds or immediately add a high-capacity neural
encoder. It should factor ADFGX into explicit Polybius-fractionation and
columnar-transposition stages using an independently verified implementation,
retain exact intermediate truth, and test stage-aware unitizations before
recombination. Required controls are fractionation-only, transposition-only,
the combined pipeline, varied keys and column widths, same-family/new-document
calibration, and a family-blind holdout. A two-coordinate ciphertext view and
an FST representation should be compared with the current width-two token view.
Voynichese remains excluded until the combined known-payload control passes.
