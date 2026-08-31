# Ciphertext-only structure recovery protocol

## Question

E-009 asks whether an anonymous-symbol sequence with natural-language
predictability can be recovered from bounded ADFGX ciphertext without any
plaintext candidates, hashes, labels, keys, or transform parameters. It is a
control bridge, not a manuscript experiment.

## Objective

For every width 4–7 and every column read order, invert the columnar stage and
pair the restored `ADFGX` coordinates. Treat the resulting 25 pair types as
anonymous symbol IDs. Fit unigram and order-two context counts on the first 70%
of that sequence with Jeffreys smoothing, then measure held-out log2 predictive
gain of the order-two model over an order-one model. The first-order baseline
is necessary because the matched Markov control deliberately preserves
one-step dependency; comparing with a unigram model would reward that control
for the property it was designed to retain.

Because 625 possible two-symbol contexts are sparse at the frozen lengths, the
order-two probability is interpolated toward order one with weight
`context_count / (context_count + 5)`. This backoff is fixed before execution;
it prevents unseen or rare contexts from manufacturing a negative result by
parameter count alone.

This score is unchanged by any renaming of the 25 symbols. It does not know the
Polybius square or map symbols to letters. Width selection subtracts
`sqrt(2 ln(k) / n_eval)` from the best raw gain, where `k` is the number of
column orders at that width. The penalty is frozen before execution to reduce
the larger-search advantage of wide keys; its adequacy is itself tested.

## Controls

Six new source works provide 24 natural segments at four lengths. Each segment
has four matched nonsemantic variants:

1. an exact-unigram position shuffle;
2. a first-order Markov sequence fitted to the segment;
3. a permutation of eight-symbol blocks, retaining most local transitions;
4. a copy/mutate process which can be highly repetitive and structured.

All five variants receive the same independently generated ADFGX parameters.
Only ciphertext and opaque query IDs enter scoring. The first two null families
control the preregistered natural-structure claim. Block shuffle and copy/mutate
are mandatory adversarial diagnostics: failure to separate them defines an
identifiability limit rather than invalidating a narrower simple-null result.

## Blind boundary

The generator and scorer are separate modules and immutable stages. Source,
family, plaintext, width, square, keyword, and order remain in sealed truth.
The scorer config contains only ciphertext fields, widths, and the mathematical
objective. Unblinding verifies every input hash and occurs once after scoring.

## Interpretation

Passing every gate would show that the fixed intrinsic objective recovers and
distinguishes natural structure from simple matched nulls in this bounded
classical mechanism. It would not identify semantics, distinguish every
manufactured pseudo-language from language, or imply that Voynichese uses
ADFGX. Target data remains prohibited pending an independent mechanism-level
replication and a separate target/null preregistration.
