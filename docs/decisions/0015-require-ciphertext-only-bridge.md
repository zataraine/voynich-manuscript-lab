# 0015: Require a ciphertext-only bridge

Date: 2026-08-31

## Status

Accepted for E-009 before implementation, generation, scoring, or unblinding.

## Context

E-008 independently validated parameter-blind known-payload retrieval, but the
score requires candidate plaintext. No such candidate set exists for the
manuscript, so applying E-008 to Voynichese would be circular. The next control
must remove plaintext entirely and determine whether sequence structure can be
recovered up to anonymous symbol renaming.

## Decision

Freeze one intrinsic held-out predictive-gain objective and search widths 4–7
with an explicit complexity penalty. Generate natural, unigram-shuffled,
first-order Markov, block-shuffled, and copy/mutate payloads from six new source
works, then ADFGX-encipher matched variants with identical parameters. Separate
public ciphertext, sealed truth, scoring, and unblinding.

Require recovery and natural-vs-simple-null gates. Treat block shuffle and
copy/mutate as mandatory ambiguity diagnostics rather than moving goalposts if
they retain language-like local structure.

## Consequences

A pass would validate only a bounded ciphertext-only structural objective and
permit independent replication across mechanisms. A failure would identify
search bias or insufficient discrimination and prohibit target design. Either
outcome records whether structured nonsemantic generation remains statistically
indistinguishable. Voynichese remains excluded.
