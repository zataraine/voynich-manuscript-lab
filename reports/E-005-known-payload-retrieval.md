# E-005 known-payload retrieval

## Result

The frozen relative-feature metric detected some plaintext identity signal in a
balanced known-payload benchmark, but it did not generalize robustly across
cipher families. Four of six preregistered gates failed. The significant
aggregate permutation result was driven mainly by affine substitution and the
two transposition families; the polyalphabetic, fractionating, and rotor
families were weak or near chance. Voynichese was absent, no target was scored,
and no posterior probability was calculated.

## Design

- Twelve independently authored Project Gutenberg works supplied four fixed
  600-character segments each. Complete documents remained within one of three
  fixed folds.
- Text was reduced to A-Z, with J mapped to I, and grouped into fixed
  five-character units. Word boundaries were unavailable to every method.
- Nine independently implemented `pycipher` families generated 432 exact
  plaintext/ciphertext pairs: affine, Vigenere, autokey, Beaufort, Bifid,
  columnar transposition, rail fence, Enigma, and ADFGX.
- For each held-out family and document fold, the pair classifier was fitted
  only on other families and other documents. Each of 16 queries was ranked
  against the correct plaintext and 15 same-length candidates.
- The pair representation comprised normalized absolute differences between
  the 29 frozen sequence features. A 128-permutation identity null preserved
  the candidate sets and folds.
- Encryption and decryption were audited byte-for-byte after normalization.
  All keys, segment offsets, source hashes, and transform metadata are retained
  in the machine-readable result.

## Family transfer

| Held-out family | Mean normalized MRR | Mean top-1 lift | Mean pair ROC AUC |
|---|---:|---:|---:|
| Affine | 0.4400 | 4.33 | 0.8806 |
| Vigenere | 0.0379 | 1.00 | 0.6184 |
| Autokey | 0.0484 | 1.33 | 0.5990 |
| Beaufort | 0.0892 | 2.00 | 0.6155 |
| Bifid | 0.0077 | 1.00 | 0.5247 |
| Columnar | 0.8954 | 14.00 | 0.9388 |
| Rail fence | 0.8120 | 12.33 | 0.9451 |
| Enigma | 0.0252 | 1.33 | 0.4916 |
| ADFGX | 0.0563 | 2.00 | 0.5210 |

The mean normalized MRR across all family-fold evaluations was 0.2680, compared
with a permutation-null mean of -0.0019 (one-sided empirical p = 0.00775).
That aggregate significance does not establish family-general retrieval: the
median family result was only 0.0563, and the largest effects were confined to
three transformations whose output preserves substantial distributional or
ordering information. In particular, this is not evidence that the manuscript
uses transposition.

## Gate outcome

| Gate | Threshold | Observed | Outcome |
|---|---:|---:|---|
| Median family normalized MRR | at least 0.20 | 0.0563 | fail |
| Worst family normalized MRR | at least 0.05 | 0.0077 | fail |
| Median family top-1 lift | at least 2.5 | 2.00 | fail |
| Worst family pair ROC AUC | at least 0.55 | 0.4916 | fail |
| Identity-permutation p-value | at most 0.05 | 0.00775 | pass |
| Exact roundtrip fraction | exactly 1.0 | 1.0 (432/432) | pass |

Overall outcome: **fail; no Voynich target comparison permitted**. The
posterior probability remains null by design.

## Local review

The Qwen reviewer rated the effect `none`, requested escalation, and identified
the concentration of performance in columnar and rail-fence transforms. The
GLM critic rated it `weak`, emphasizing the significant aggregate null test but
also the chance-level Enigma AUC and weak Bifid result. Both reviews correctly
recognized the failed gates. Reviews are advisory; the deterministic
preregistered decision controls the outcome.

## Provenance

- Preregistration commit: `cde3dd9`.
- Deterministic implementation commit:
  `c51e9e0d14e8204320edc71d5734c9c2ebf38584`; clean working tree.
- Deterministic result SHA-256:
  `3dbbacc53cb0df616ce9f5921a70e12489a207b99dbbc4f8f5efd24e509d0e4d`.
- Qwen review SHA-256:
  `ca71ac9424382a9c9298f4c43d2666250d93e93b1c2b6915a2002cc877f73416`.
- GLM review SHA-256:
  `1d7fbf0b4e8ebfc553ce1e5fe05a742fc5901bdb1bc797e22a59f7c0152199ee`.
- Source-manifest SHA-256:
  `ae6a26ac04a22bc20bcf746d852cb4d394707ee3fa13126e0d2fb5f8870842c1`.
- Pinned `pycipher` source-archive SHA-256:
  `91e6b4d9ae8c9fa7cc620b8aa46910bf6b822e679e928844eff19fa255793259`.
- Config SHA-256:
  `a2dc503a34bb29ba7e7359ee4a7296822cde1c21f2281b52aedcbac91b61a99b`.
- CPU fitting; local Qwen and GLM GPU review. Machine-readable artifacts are
  under `artifacts/runs/E-005-known-payload-retrieval/` and remain uncommitted.

## Next falsifiable campaign

E-006 should keep this source corpus, transforms, splits, and gates frozen while
testing representations designed for character sequences rather than tuning
the present classifier. Candidate representations must be preregistered and
include cheap baselines such as character n-gram sketches, lag/spectral
statistics, and compression distance before any learned contrastive encoder.
Evaluation should report each family separately and reserve complete cipher
families and documents. Voynichese remains excluded until a representation
retrieves payload through the difficult polyalphabetic, fractionating, and
rotor families rather than succeeding mainly on transposition.
