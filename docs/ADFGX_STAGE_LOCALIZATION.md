# ADFGX stage-localization protocol

## Question

E-006 retrieved eight of nine cipher families but failed ADFGX even in its
same-family diagnostic. E-007 asks whether that failure occurs in Polybius
fractionation, columnar transposition, or their composition and unitization.
It is a control experiment, not a manuscript test.

## Why this can be useful

ADFGX first replaces each plaintext symbol with a two-symbol coordinate and
then columnarly transposes the entire coordinate stream. Adjacent characters
in the final ciphertext are therefore generally not coordinate pairs. A
stage-aware diagnostic can undo a hypothesized column count without knowing
the keyword order or Polybius square, then test whether candidate plaintext
symbols and recovered coordinate pairs form a consistent bijection. This is
also useful for future fractionating/nomenclator hypotheses: it provides
explicit transform stages, reversible FSTs, and a width-scan interface rather
than another opaque classifier.

## Frozen tests

Use one 600-character E-005 segment from each of twelve source documents.
Evaluate widths five, six, and a ragged width-seven case. At each width, hide
the square, keyword, column order, and correct candidate from the scorer.
Enumerate all column read orders and score the best recovered stream by the
mean of forward and reverse modal consistency: a plaintext symbol should map
to one coordinate pair, and one coordinate pair should map back to one
plaintext symbol.

The three stages are:

1. fractionation only, which tests the symbol/coordinate score;
2. transposition only, which tests exhaustive column-order recovery;
3. the composition, which tests whether correct unit boundaries reappear
   after the hidden transposition is inverted.

Ranks use average tie ranks. Column-order recovery succeeds if the true order
is in the complete set of maximizers; iteration order may not break ties.
Every correct width has a frozen lower neighboring wrong-width control.

## Oracles and validity

The local implementation must match the pinned pycipher implementation and
the independent cryptii `CARGO` known vector. Pynini must encode and invert
each Polybius mapping exactly. All stage encipher/decipher roundtrips must be
exact. A failure of either oracle invalidates the campaign.

All nine gates in the experiment configuration are mandatory. Failure at one
stage stops scaling and localizes the next engineering question. Passing says
only that this deterministic diagnostic works on these known ADFGX controls.
It does not show that Voynichese is ADFGX-like, establish a writing direction
or alphabet, or permit a language/cipher/hoax posterior.

## Compute discipline

The score is deterministic and needs no language model. Exhaustive searches
are bounded at 7! orders over twelve candidates. A compiled numeric kernel may
be used, but it must reproduce a small pure-Python reference exactly. Local
models may critique the protocol and report; they do not see or score candidate
texts.
