# 0011: Retrieve known payloads instead of classifying meaning

Date: 2026-08-30

## Status

Accepted for E-005 before implementation or execution.

## Context

E-002 through E-004 trained a binary meaningful-versus-human-gibberish model.
They detected reproducible surface signal but failed transfer magnitude,
parameter stability, and the external Naibbe control. Repeatedly modifying that
classifier against the same archive would invite benchmark overfitting.

The acquired Naibbe repository contains many ciphertext samples but only three
small example decryptions with ambiguity notation, not a corpus-scale set of
exact plaintext/ciphertext pairs. It must not be described as exact paired truth.
Project Gutenberg supplies independent public-domain-in-the-USA source works,
and the pinned MIT-licensed pycipher revision supplies an independently authored
implementation of multiple classical cipher systems.

## Decision

E-005 asks whether a learned pair metric retrieves the exact source segment for
ciphertext from an entirely unseen cipher family. Use 12 documents, three fixed
document folds, four equal 600-character segments per document, and fixed
five-character groups. Normalize to a common A-Z alphabet with J mapped to I.
Every candidate therefore has equal plaintext length and no supplied word
boundaries.

Generate pairs with nine pycipher families and verify every deciphered output
against its normalized plaintext. In each outer test, exclude the complete
cipher family and one complete document fold from fitting. Train on true pairs
and three seeded same-length decoys per ciphertext. Evaluate full retrieval over
all 16 plaintext segments in the heldout document fold. Compare observed ranks
with 128 within-fold identity permutations.

Freeze six gates in the E-005 configuration. Keep Naibbe contextual rather than
fabricating an exact-pair gate. Keep Voynichese absent.

## Consequences

Success would establish cross-family payload matching for this benchmark, not
semantic understanding or decipherment. Failure would show that the current
feature representation cannot preserve enough document identity across unseen
classical systems and should redirect work toward representations rather than
more binary-classifier tuning.
