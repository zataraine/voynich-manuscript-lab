# E-001 preliminary mechanism-elimination result

## Status

- Experiment: `E-001-manufactured-vs-hoax`
- Hypothesis: `H-001`
- Code: `c1adb6af8819af7729a861d377c3f62a3079e6f7`, clean
- Run status: complete; local review requires adjudication/replication
- Result SHA-256: `b016040784cad0402e29c1ac5f3ac6ba2109d10cb122a848663713d688a8557d`
- Qwen review SHA-256: `ef22a44043d500154450bbbccf75a4343eb35361fef90696427559aaea6ed895`
- Runtime: 5 minutes 27 seconds on five CPU workers, followed by local embedding,
  reranking, and Qwen review under exclusive GPU control

The full machine artifacts remain untracked at
`artifacts/runs/E-001-manufactured-vs-hoax/`. This report is a compact reviewed
index, not a replacement for those immutable records.

## Audited corpus and split

The conservative ZL3b/EVA transform produced 32,695 stable groups from 197
Currier A/B-labelled pages and excluded 1,088 uncertainty/markup-bearing groups.
The seeded, Currier/hand/section-stratified split contains 146 training pages and
51 held-out pages. The recorded overlap is zero and the union covers all 197
included pages.

## Observed held-out measurements

| Measurement | Value |
|---|---:|
| Character unigram cross-entropy | 3.8742 bits/symbol |
| Character trigram cross-entropy | 1.9028 bits/symbol |
| Character trigram gain | 1.9714 bits/symbol |
| Group unigram cross-entropy | 10.8279 bits/group |
| Group bigram cross-entropy | 11.7332 bits/group |
| Group bigram gain | -0.9054 bits/group |
| Recent edit-distance-one copy rate | 0.3964 |

The negative absolute group-bigram gain is not silently converted into positive
evidence. With this vocabulary and smoothing, the sparse higher-order group
model generalizes worse than the unigram model. The preregistered comparisons
therefore use observed-minus-null as well as the absolute measurement.

## Mechanism comparison

With 512 replicates per family and Holm correction over 15 comparisons, the
minimum adjusted p-value is `0.02924`.

- Within-page group shuffling is incompatible on group-order gain and local-copy
  rate, while character structure is invariant by construction.
- Within-group symbol shuffling is incompatible on character gain and local-copy
  rate; its group-identity model is not rejected in the positive direction.
- Global intact-group resampling is incompatible on group-order gain and
  local-copy rate; character structure is largely preserved by construction.
- IID length-matched symbol generation is incompatible on character gain and
  local-copy rate; its sparse group-bigram result is not rejected.
- Copy/mutate pseudo-text is incompatible with the observed internal character
  structure but **remains compatible on group-bigram gain and local-copy rate**.

The result rejects several simple generators on selected dimensions. It does not
reject the strong nonsemantic comparator as a family, does not demonstrate a
semantic payload, and does not justify manufactured-language versus hoax odds.

## Review adjudication

The local Qwen review returned `escalate=true`. Its useful follow-ups are to
investigate the negative group-bigram gain, add Naibbe and other known-payload
controls, and repeat across transcriptions/unitizations. Several anomalies were
false positives:

- the empty-diff SHA-256 is the expected clean-working-tree digest;
- the manifest and transcription hashes refer to different files and should not
  match;
- near-zero character-metric variance under group shuffling is an intended
  invariant; and
- a strong copy/mutate null exceeding the target copy rate is compatibility, not
  a metric contradiction.

Future review prompts now receive these deterministic metric/hash definitions.
The next scientific gate is replication and positive-control calibration, not a
claim promotion.
