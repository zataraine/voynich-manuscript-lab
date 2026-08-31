# E-008 parameter-blind ADFGX replication

## Result

E-008 passed all nine preregistered gates. The frozen E-007 structural scorer
retrieved the correct known plaintext for all 96 independently generated ADFGX
queries while searching widths 4–7 and every column order. It also retained
the true width among the maximizing widths for every query. When complete
coordinate-pair positions were shuffled before transposition, retrieval fell
to chance.

This independently replicates parameter-blind known-payload retrieval. It is
not ciphertext-only decryption: eight plaintext candidates were deliberately
supplied for each query, while correct identity, square, keyword, column order,
width, source offset, and seeds were withheld from scoring.

## Separation and design

- Eight Project Gutenberg works absent from E-005/E-007 supplied candidates.
- Twelve suites used segment lengths from 401 to 757 characters. Each suite
  queried all eight candidates once, producing 96 balanced queries.
- Every query received a new uniformly shuffled 25-symbol square and a new
  unique-letter keyword. Widths 4, 5, 6, and 7 each occurred 24 times.
- The generator used pinned pycipher `PolybiusSquare` and `ColTrans` components
  and did not import E-007 transform functions.
- Generation wrote a public candidate/ciphertext bundle and a separately
  hashed truth file. The scorer accepted only the public bundle and a distinct
  scorer config containing widths 4–7. It recorded `truth_accessed: false`.
- Scores and their input hash were frozen before the unblinder joined truth.
  All public, truth, score, config, and manifest hashes were checked.
- For every query/candidate pair, scoring maximized bidirectional symbol/pair
  consistency across the complete preregistered width/order search.
- The destructive control shuffled complete coordinate-pair positions before
  transposition, preserving length and the exact pair multiset.
- The 512-replicate identity null was applied after complete maximization, so
  nulls received the same search advantage as the observed statistic.

This is procedural truth separation, not cryptographic secrecy from the local
operator. Its purpose is to prevent score selection or code paths from using
the answer during the recorded campaign.

## Gate outcome

| Measurement | Gate | Observed | Outcome |
|---|---:|---:|---|
| Generator roundtrip fraction | 1.0 | 1.0 | pass |
| Forbidden truth keys in public bundle | 0 | 0 | pass |
| Overall normalized MRR | at least 0.90 | 1.0 | pass |
| Worst-width normalized MRR | at least 0.75 | 1.0 | pass |
| Overall pair ROC AUC | at least 0.98 | 1.0 | pass |
| True width in maximizer set | at least 0.95 | 1.0 | pass |
| Median real-minus-broken correct score | at least 0.50 | 0.81487 | pass |
| Median broken correct score | at most 0.45 | 0.18513 | pass |
| Post-search identity-permutation p | at most 0.01 | 0.001949 | pass |

Each width separately had 24 queries, normalized MRR 1.0, AUC 1.0, and top-1
fraction 1.0. Mapping-destruction score drops ranged from 0.77556 to 0.84346.
The broken suite had normalized MRR -0.00728, AUC 0.50425, top-1 fraction
0.1146 versus chance 0.125, and median rank 4.5. Thus exact pair-frequency and
length preservation did not explain the successful retrieval; alignment
between plaintext occurrences and recovered pairs was necessary.

## Compute result

Blind scoring required 13.10 seconds inside the width kernels and 16.65 seconds
wall time including startup and serialization. Real plus broken search time was:

| Width | Permutations per search | Total seconds |
|---:|---:|---:|
| 4 | 24 | 0.191 |
| 5 | 120 | 0.265 |
| 6 | 720 | 1.579 |
| 7 | 5,040 | 11.068 |

Generation required 3.05 seconds and unblinding 4.37 seconds. Peak memory during
scoring was 374 MB. Width seven dominates, confirming factorial enumeration is
not a sensible path to substantially wider keys without a different search.

## What this resolves

E-007's perfect score was not limited to its exposed documents, three named
keys, supplied correct width, or one fixed square. The same frozen diagnostic
transferred to new sources, 96 new transformations, varied lengths, and a
complete unknown-width search. A control preserving exact coordinate-pair
counts failed at chance, rejecting a simple pair-frequency explanation.

It is therefore reasonable to retain the E-007 stage-aware implementation as
a verified known-payload control primitive. There is no reason to rewrite or
rerun E-006: its failure remains the evidence that motivated this independently
replicated correction.

## What this does not resolve

The supplied candidate set makes this retrieval, not plaintext generation.
The scorer asks which known candidate is structurally consistent with the
ciphertext; it cannot invent or translate an unknown plaintext. Only ADFGX,
widths 4–7, a five-symbol coordinate alphabet, and classical columnar
transposition were tested. Natural-language sources, the pycipher generator,
and the score's deterministic mechanism may share assumptions that other
fractionating systems violate.

No Voynich symbol inventory, direction, pair boundary, width, coordinate
alphabet, candidate plaintext, or ADFGX hypothesis is established. Target
application would be circular because the current score requires supplied
plaintext candidates. The next bridge must work from ciphertext alone on
controls before a manuscript-side protocol can be justified.

## Local reviews

The Qwen reviewer used 2,151 local tokens, assigned effect strength `none`, and
escalated because it interpreted “blind” as ciphertext-only cryptanalysis. Its
warning is valid for claim wording but not a failure of the preregistered task:
the record explicitly defined parameter/truth-blind known-payload retrieval and
supplied candidates by design. It incorrectly said the scoring process had
ground-truth plaintext access; it had candidate plaintexts but not correct
identity, parameters, or sealed truth.

The GLM critic assigned `strong`, accurately noted perfect width-stratified
retrieval and the p-value, and warned that the deterministic generator may
match the scoring heuristic and that non-ADFGX mechanisms and widths above 7
remain untested. Both reviews support the same conservative next step: replace
candidate retrieval with a ciphertext-only, symbol-renaming-invariant control
objective before considering any target experiment. Reviews remain advisory;
the preregistered deterministic gates control the result.

## Provenance

- Independent-source commit: `04964fa`.
- Preregistration commit: `7f2ada2`.
- Generator/scorer/unblinder commit:
  `01a9f1b88ce484547c9be9495003b91570f7baa0`; clean tree for all stages.
- Deterministic result SHA-256:
  `be3f43947b39d5d89d9fb9f0b71eb429c489c8809296cfbc92c3927358801ad2`.
- Public suite SHA-256:
  `bd7d06839783190214b0692dbaec58b6c89c1c71a330b25b9094639804d391d0`.
- Sealed truth SHA-256:
  `28a3b2cada30968778baefbe73eb660a211e212e0d1ef20b581edeb849a8534b`.
- Blind score SHA-256:
  `d5785b8c776bbeae0c55d5442a625d1e714ece47377d6046368f88d4001a5282`.
- Qwen review SHA-256:
  `1cbd1eabf9c2646ab18087416467d655b39c19b3ad2ec1e53f52ccab03a6f4e0`.
- GLM review SHA-256:
  `5085afd974d0f04b3a56102eaee5e95db833571c61e73783ebce0eed933358e0`.
- Experiment config SHA-256:
  `8d052f5c6b6f8726d5385dd9eed136b4261d34e637cc333ec9044f3174e4179e`.
- Truth-free scorer config SHA-256:
  `631f53b3433a01d9e999bfe613deea22450d6dfa90a9c36979afdb8ce624cc59`.
- Source manifest SHA-256:
  `33eb2860f78cde48009fd5aee99d2fe2189db220a7f6df5d7d0b8b26ef5209e2`.
- Machine artifacts remain under
  `artifacts/runs/E-008-blind-adfgx-replication/` and are uncommitted.

## Next falsifiable campaign

E-009 should receive ciphertext only—no candidate plaintexts or plaintext
hashes. On independently generated controls, it should search the same bounded
width/order space, convert restored coordinate pairs to anonymous symbol IDs,
and use only symbol-renaming-invariant sequence objectives selected before
execution. It must distinguish natural payloads from pair-frequency-, length-,
and local-transition-preserving nonsemantic controls, recover width/order above
corrected nulls, and report failure by length and width. Only a successful
independent replication of that ciphertext-only objective could justify
preregistering a target-side null comparison.
