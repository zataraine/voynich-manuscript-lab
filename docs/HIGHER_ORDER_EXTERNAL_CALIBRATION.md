# Higher-order external calibration protocol

## Purpose

E-014 asks whether a fixed panel of higher-order, nonsemantic sequence
measurements can distinguish intentional-payload controls from structured
no-intended-payload controls more specifically than E-013R1's low-level effect
signature. Voynichese is excluded from feature development, fitting, threshold
selection, and scoring.

The panel is motivated before implementation by work on vocabulary growth,
long-range correlation, recurrence intermittency, distribution over contextual
domains, and word-co-occurrence networks. In particular, Altmann et al. link
long-range textual correlation to bursty recurrence at higher linguistic levels;
Amancio et al. evaluate intermittency and network topology across languages and
texts; and Montemurro and Zanette quantify how token distributions vary across
text domains. These papers motivate measurements, not a target conclusion.

Direct long-lag mutual information over a large token alphabet is excluded: at
these sample sizes it is dominated by sparse-count bias. Pretrained semantic
embeddings, language-model likelihoods, manuscript values, and features selected
from E-013R1 errors are also excluded.

## Frozen controls

Use the exact E-013 control construction and source split:

- development: twelve E-005 books;
- independent test: fourteen disjoint E-008/E-009 books;
- external tests: meaningful/conlang documents, human-produced gibberish, and
  Naibbe ciphertext from the pinned Gaskell/Bowern/Naibbe archive;
- payload families: natural, monoalphabetic, Vigenere, progressive-key,
  homophonic, and nomenclator-hybrid;
- no-payload families: character Markov-1, token Markov-1, two copy/mutate rates,
  and the position-conditioned slot generator.

Each case uses the same deterministic contiguous 70--280-group window as
E-013R1. Length is not a feature. All variants of a source document remain in
one fold. External cases are used only after the final model is frozen.

## Frozen feature panel

The classifier receives exactly these 21 measurements:

1. Heaps-law log-log exponent and fit R-squared over fixed prefix sizes;
2. early-minus-late vocabulary-growth exponent;
3. token-length autocorrelation at lags 1, 2, 5, 10, and 20;
4. low-frequency fraction of token-length spectral power;
5. coefficients of variation of blockwise length means and standard deviations;
6. mean recurrence-gap burstiness and coefficient of variation for token types
   occurring at least three times;
7. mean block-count Fano factor for up to sixteen most frequent recurring types;
8. token identity/block mutual information at block sizes 20 and 40;
9. observed-minus-shuffled compression gain for canonical token-pattern and
   token-length sequences, averaged over 32 seeded shuffles; and
10. weighted adjacent-token graph degree assortativity, average clustering, and
    selectivity coefficient of variation.

All measurements operate on token equality, order, and code-point length only.
They must be invariant to a bijective renaming of complete token identities.
Undefined small-sample quantities have a specified neutral value of zero and
must remain finite. No training-time feature selection is permitted.

## Fitting and null test

Use median/IQR scaling learned inside each training boundary, treating IQR at or
below `1e-12` as constant. Fit L2 logistic regression with `C=1`, balanced class
weights, the frozen seed, and threshold 0.5.

Primary development predictions are doubly held out by source-document fold and
complete mechanism family. The label-null test permutes labels only at the eleven
mechanism-family level, preserves the six/five class counts, and repeats the
entire held-out procedure 1,024 times. Fit the final model on development cases
only, then score the independent and external controls.

E-013R1 is the fixed baseline. Its eight effects are not included in E-014, and
its failed classifier is not retuned or combined post hoc.

## Gates

All construction controls and all nine scientific gates are conjunctive:

1. doubly-held-out development balanced accuracy >= 0.70;
2. worst development mechanism recall >= 0.55;
3. family-label permutation p <= 0.01;
4. independent-book balanced accuracy >= 0.70;
5. worst independent mechanism recall >= 0.55;
6. external meaningful/conlang recall >= 0.65;
7. human-gibberish specificity >= 0.65;
8. Naibbe payload recall >= 0.60; and
9. Naibbe median payload score >= 0.60.

Construction additionally requires exact source hashes, disjoint development
and independent source hashes, deterministic feature replay, finite vectors in
the frozen order, exact token-renaming invariance within `1e-12`, successful
payload roundtrips, and proof that no manuscript transcription was read.

## Decision boundary

A pass only establishes an externally calibrated control panel. It permits a
new experiment on measurement stability across independent manuscript witnesses;
it does not permit direct target classification, odds, language identification,
or decipherment.

Any failed construction control invalidates the run. Any failed scientific gate
closes this fixed panel. Features, thresholds, families, or short external cases
must not be removed after inspection to manufacture a pass.

## Method references

- Altmann, Cristadoro, and Degli Esposti (2012), [*On the origin of long-range
  correlations in texts*](https://doi.org/10.1073/pnas.1117723109).
- Amancio et al. (2013), [*Probing the statistical properties of unknown texts:
  application to the Voynich Manuscript*](https://arxiv.org/abs/1303.0347).
- Montemurro and Zanette (2013), [*Keywords and Co-Occurrence Patterns in the
  Voynich Manuscript*](https://doi.org/10.1371/journal.pone.0066344).

