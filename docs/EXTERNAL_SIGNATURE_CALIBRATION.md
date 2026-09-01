# External eight-effect signature calibration protocol

## Purpose

E-013 asks whether the eight transcription-robust effects established by E-012
carry information specific to an intentional payload, rather than merely
detecting non-random surface structure. It uses only known controls. No
Voynichese input, feature selection, threshold adjustment, or target score is
permitted in this experiment.

The primary comparison is **payload-bearing** versus **no-intended-payload**.
The latter label describes a documented generation process; it does not claim
that every generated fragment is impossible to interpret. “Hoax” is not a
machine label.

## Frozen signature

For each control sample, divide one contiguous token sequence into consecutive
ten-group blocks. Retain 70–280 groups and use the first 75% of complete blocks
for fitting and the final 25% for held-out evaluation. No block crosses the
boundary. Apply the E-001/E-012 character-trigram gain, group-bigram gain, and
recent edit-distance-one copy-rate definitions without modification.

Estimate the eight E-012 observed-minus-null-mean effects with 64 seeded
replicates of the four corresponding simple null families:

1. within-page group shuffle: group-bigram gain and local-copy rate;
2. within-group symbol shuffle: character-trigram gain and local-copy rate;
3. global intact-group resampling: group-bigram gain and local-copy rate; and
4. IID symbol generation with observed lengths: character-trigram gain and
   local-copy rate.

The classifier receives exactly these eight signed effects. It does not receive
raw metrics, alphabet identity, source length, document ID, family ID, language,
character inventory size, null p-values, or manuscript values.

## Control construction

The twelve E-005 Project Gutenberg works are the development documents. Each
supplies the same contiguous token window to six payload-bearing views:
natural text, monoalphabetic substitution, Vigenere, per-symbol progressive-key
polyalphabetic substitution, seeded homophonic substitution, and a reversible
whole-token nomenclator plus homophonic fallback. Exact inversion is mandatory
for all transformed payloads.

The same window supplies five no-intended-payload views: character Markov-1
with observed group lengths, token Markov-1, local copy/mutate at rates 0.08 and
0.18, and an independent position-conditioned slot generator. Seeds and keys
derive only from the frozen experiment seed, document ID, and family ID.

The eight E-008 and six E-009 books form an untouched 14-document test set with
new parameters. Development and test raw files have disjoint Project Gutenberg
identifiers and separate source manifests.

Three acquired external sets are scored only after model freezing:

- every eligible meaningful natural/conlang document in the pinned Gaskell and
  Bowern archive;
- every eligible human-produced gibberish document in that archive; and
- the twenty supplied Naibbe verbose-homophonic ciphertext variants.

Documents with fewer than 70 token groups are excluded by the frozen length
rule and counted. Longer documents use a deterministic hash-selected contiguous
window of at most 280 groups. Raw archive members remain unextracted.

## Fitting and leakage controls

Use median/IQR scaling learned inside each training boundary and an L2 logistic
regression with `C=1`, balanced class weights, and the frozen seed. All variants
of a source document remain in one of the three fixed development folds.

Primary development predictions are doubly held out: for each document fold and
each mechanism family, fit without that fold and without that complete family,
then score only the omitted family in the omitted documents. This prevents a
model from recognizing a source or memorizing a generator. Fit the final model
on all development cases only after producing these predictions.

For the label-null test, permute the payload/no-payload assignment at the eleven
mechanism-family level, preserve class counts, repeat the complete doubly-held-
out procedure 1,024 times, and use the one-sided plus-one p-value. Document-level
permutations are invalid because each source contributes both labels.

## Preregistered gates

All construction controls and all seven scientific gates must pass:

1. doubly-held-out development balanced accuracy >= 0.70;
2. worst development mechanism-family recall >= 0.55;
3. family-label permutation p <= 0.01;
4. independent E-008/E-009 balanced accuracy >= 0.70;
5. worst independent mechanism-family recall >= 0.55;
6. external meaningful/conlang recall >= 0.65 and human-gibberish specificity
   >= 0.65; and
7. Naibbe payload recall >= 0.60 and median payload score >= 0.60.

The probability threshold is 0.5. Scores are classifier outputs, not posterior
probabilities about meaning or hoaxing. Report ROC AUC, Brier score, every family
recall, excluded-document counts, and copy/mutate results regardless of outcome.

## Decision boundary

Passing authorizes a separately preregistered, witness-replicated target
application using the frozen model and decision rule. It does not authorize
odds, a language claim, or decipherment. Failure establishes that these eight
effects are insufficiently specific and closes the signature-classification
branch; new work must add independently motivated information (for example
long-range, layout, or hierarchical structure) rather than tune this panel on
Voynichese.
