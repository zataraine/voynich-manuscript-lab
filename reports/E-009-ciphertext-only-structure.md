# E-009 ciphertext-only structure recovery

## Result

E-009 failed seven of nine preregistered gates. The two integrity gates passed:
all 120 pycipher controls round-tripped exactly, and the public scoring bundle
contained no forbidden truth. The ciphertext-only objective did not recover
the hidden transform or distinguish natural payloads from simple matched
nonsemantic controls.

This is a decisive negative result for the tested intrinsic objective. It does
not contradict E-008's known-payload retrieval result; it shows that removing
the candidate plaintext removes the information that made that diagnostic
useful. No Voynich data was scored.

## Design

- Six Project Gutenberg works absent from E-005 and E-008 supplied 24 natural
  segments at lengths 401, 499, 613, and 757.
- Each segment produced matched natural, exact-unigram shuffle, first-order
  Markov, eight-symbol block-shuffle, and copy/mutate payloads.
- The five matched variants shared one new Polybius square, keyword, width, and
  order; widths 4–7 were balanced across the 24 bases.
- Independent pycipher components generated 120 ADFGX ciphertexts.
- The public scorer received only opaque query ID and ciphertext. Plaintext,
  candidate text, source, family, hashes, width, square, keyword, order, and
  generator seeds remained in sealed truth.
- For every width and order, the scorer restored coordinate pairs as anonymous
  symbol IDs. It fit order-one and interpolated order-two models on the first
  70% and measured held-out order-two-over-order-one log2 predictive gain.
- Width scores subtracted the preregistered
  `sqrt(2 ln(k) / n_eval)` complexity penalty before selecting across widths.
- A 2,048-replicate paired sign permutation was applied after the complete
  search. Block shuffle and copy/mutate were mandatory ambiguity diagnostics,
  not substitute primary gates.

The unigram baseline was changed to order one before implementation because a
first-order Markov control would otherwise receive credit for the dependency
it deliberately preserves. Sparse order-two contexts received a fixed
count-dependent backoff. Both changes were committed before any E-009 code or
outputs existed.

## Gate outcome

| Measurement | Gate | Observed | Outcome |
|---|---:|---:|---|
| Generator roundtrip fraction | 1.0 | 1.0 | pass |
| Forbidden truth keys in public bundle | 0 | 0 | pass |
| Natural vs unigram AUC | at least 0.95 | 0.52257 | **fail** |
| Natural vs Markov AUC | at least 0.75 | 0.51042 | **fail** |
| Median natural-minus-unigram score | at least 0.15 | 0.00034 | **fail** |
| Natural correct-width fraction | at least 0.60 | 0.29167 | **fail** |
| Natural true-order median percentile | at least 0.90 | 0.04583 | **fail** |
| Natural beats paired unigram fraction | at least 0.85 | 0.54167 | **fail** |
| Paired sign-permutation p | at most 0.01 | 0.13909 | **fail** |

The failure is not marginal. Natural/unigram and natural/Markov AUCs are near
0.5, the median margin is nearly zero, and the true order usually lies near the
bottom rather than top of the order distribution.

## Adversarial diagnostics

Natural versus eight-symbol block shuffle also remained near chance: AUC
0.5260, median margin 0.00096, and paired win fraction 0.5417. Copy/mutate
pseudo-text was more attractive to the objective than natural text: natural
versus copy/mutate AUC was 0.3333, the median natural-minus-copy score was
-0.00645, and natural won only one third of matched comparisons.

These results directly matter to the manufactured-versus-nonsensical question.
A locally repetitive procedural sequence can be more predictable than language,
while destroying global order in eight-symbol blocks can retain nearly the
same local score. Higher predictability is therefore not evidence of meaning.

## Failure localization

Post-hoc diagnostics were computed only to localize failure and cannot replace
the preregistered gates:

| True-order comparison | AUC |
|---|---:|
| Natural vs unigram shuffle | 0.63194 |
| Natural vs first-order Markov | 1.00000 |
| Natural vs block-8 shuffle | 0.62847 |
| Natural vs copy/mutate | 0.09896 |

At the true order, the objective does detect higher-order dependence missing
from the Markov generator, but only weakly separates exact-unigram and block
controls and strongly favors copy/mutate. Thus the objective itself is
insufficient even if an oracle supplies the transform.

The search adds a separate failure. Despite balanced true widths, the corrected
search selected width 4 for 23 of 24 natural queries. True widths were recovered
only 7/24 times, and wrong orders generally produced higher gains. The chosen
complexity correction over-penalizes larger width spaces while the maximization
still discovers accidental predictive artifacts.

Both components fail: changing only the penalty would not solve weak natural-
versus-null discrimination, and changing only the language score would not
validate the current search correction.

## Compute result

Generation took 3.61 seconds. Ciphertext-only scoring took 7.93 seconds wall
time and 4.07 seconds inside the width kernels: 0.155 seconds at width 4, 0.081
at width 5, 0.479 at width 6, and 3.351 at width 7. Unblinding took 3.93 seconds.
Peak scoring memory was 451 MB. Compute capacity is not the limiting factor;
identifiability and objective validity are.

## Local reviews

The Qwen reviewer assigned effect strength `none`, accurately stated that all
seven scientific gates failed, highlighted width-4 bias and copy/mutate, and
recommended stopping the ADFGX branch. It incorrectly described the generated
ciphertext as “indistinguishable from noise”; the tested comparison is with
specific matched controls, not all noise families.

The GLM critic also assigned `none`, identified chance AUC and the width-4
selection anomaly, and requested investigation of copy/mutate. Both reviews
agree with the deterministic boundary: do not tune this exposed suite and do
not apply the method to the manuscript.

## Provenance

- Independent-source commit: `d3fe729`.
- Initial preregistration commit: `ae57b53`.
- Pre-implementation baseline correction: `8ed3098`.
- Pre-implementation sparse-context backoff freeze: `c4509b1`.
- Generator/scorer/unblinder commit:
  `60cd4c6`; clean tree for generation, scoring, and unblinding.
- Deterministic result SHA-256:
  `ff22d1f23b79cf46f57682a748fa92a09492925272542b12efc84a5da99f55c9`.
- Public suite SHA-256:
  `33930687b29b1f5d5c2246e637707b76538dce09f04faab1abd2cb22ec11a784`.
- Sealed truth SHA-256:
  `d34a11cf7dcaefa1733e314435558b027a4cd81680c9c70614f39f210e5fa78b`.
- Blind score SHA-256:
  `48520a6cad9e2c4cabe3813f7acff083e7462ac965849adf648ba0fc67ae104b`.
- Qwen review SHA-256:
  `7e202d7cd0f5f40157a440648add3b18bda0b73176d8fb739c4f0851c57850a3`.
- GLM review SHA-256:
  `b3950114ce54d61e427e78029bb784b9f8e820119ace68d5a152c875ed0f6780`.
- Experiment config SHA-256:
  `2e09403f7fe116ff4809b22c69306b52f943c09fc497cdbbf492b40cb25462f0`.
- Truth-free scorer config SHA-256:
  `0da4ee333ed0991285c672d2446f395d115f76de2d3af58ae6aeaa0717c9e24b`.
- Source manifest SHA-256:
  `1da4ca63c550dea208e5d81425b041e75c3853e8d3a6218fb3be508ae6ebebb3`.
- Machine artifacts remain under
  `artifacts/runs/E-009-ciphertext-only-structure/` and are uncommitted.

## Decision and next work

Stop the ADFGX-specific branch. E-006's failure was correctly explained and
E-007/E-008 produced a reusable known-payload control primitive, but E-009 shows
that the primitive does not become target-applicable when plaintext candidates
are removed. A new context order, threshold, penalty, or compressor on these
same controls would be post-hoc tuning.

The lab should return to the direct manuscript prerequisites already identified
in the source catalog: lossless IVTFF 2 parsing, multi-witness alignment,
deterministic page/locus mapping, and page-preserving structured nulls. Those
interfaces can advance the manufactured-versus-nonsensical question without
assuming a cipher or candidate plaintext.
