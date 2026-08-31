# Blind ADFGX replication protocol

## Purpose

E-008 tests whether the frozen E-007 stage-aware diagnostic transfers to new
source documents and unseen ADFGX parameters when the correct width is no
longer supplied. It is a parameter-blind known-payload retrieval experiment,
not ciphertext-only decryption and not a manuscript experiment.

## Separation boundary

Generation and scoring are different commands and files. The generator uses
the pinned pycipher `PolybiusSquare` and `ColTrans` components, never E-007's
transform functions. It writes candidate plaintext and ciphertext into a
public suite, while correct identity, width, square, keyword, column order,
source offsets, and generator seeds remain in a separately hashed truth file.

The scorer accepts only the public suite and a scoring-only configuration that
contains widths 4–7. That configuration contains no truth path, parameter seed,
or correct identity. Scores and their public-suite hash are frozen before the
unblinder reads truth. This is procedural separation, not a claim that the
local operator cannot inspect reproducible files.

## Independent controls

Eight Project Gutenberg works absent from E-005 supply candidates. Twelve
suites use different fixed lengths from 401 to 757 characters. Each suite has
eight balanced queries, for 96 total. Widths 4–7 occur equally often, and every
query receives a new uniformly shuffled Polybius square and unique-letter
keyword.

For each query, a destructive control permutes complete coordinate-pair
positions before transposition. It therefore preserves length and the exact
coordinate-pair multiset but breaks which plaintext occurrence receives which
pair. The same blind width/order search is applied to real and broken streams.

## Scoring and correction

For every query/candidate pair the scorer enumerates all column orders at all
four widths, restores candidate coordinate streams, and retains the maximum
bidirectional modal-consistency score. It preserves all maximizing widths and
uses average ranks for score ties. Runtime is recorded by width.

The identity-permutation null is applied only after the complete maximization,
so every null replicate inherits the same width/order search advantage as the
observed statistic. Width-stratified metrics are mandatory, and the worst
width—not an average—controls one gate.

## Interpretation boundary

All nine frozen gates are required. A pass shows only that a deterministic
known-payload consistency diagnostic generalizes across this independent
ADFGX suite. Candidate plaintext remains available, and widths above seven are
excluded because exhaustive order search grows factorially. No Voynich text,
transcription, glyph assumption, or semantic model enters E-008.
