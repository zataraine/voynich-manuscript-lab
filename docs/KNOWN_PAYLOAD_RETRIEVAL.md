# Known-payload retrieval benchmark

E-005 replaces the failed meaningful-versus-gibberish transfer task with direct
known-payload retrieval. Twelve independently acquired Project Gutenberg works
provide 48 equal 600-character source segments. A pinned MIT-licensed pycipher
revision generates exact pairs under nine classical cipher families.

All source streams are normalized to A-Z with J mapped to I and unitized into
fixed five-character groups. Every retrieval query therefore compares 16
equal-length candidate plaintexts without supplied word boundaries. Pair
features are bounded relative differences between the 29 frozen sequence
measurements; neither plaintext nor ciphertext absolute features are supplied
alone.

For every cipher family and document fold, fitting excludes the complete family
and four complete documents. Training contains true pairs and three seeded
same-length decoys per ciphertext. Evaluation ranks all 16 heldout plaintext
segments. Exact decipher/encipher roundtrip is audited for every generated pair,
and 128 within-fold identity permutations supply the retrieval null.

Naibbe is not treated as exact paired ground truth: the acquired repository has
many ciphertext files but only three small example decryptions containing
ambiguity notation. E-005 excludes Voynichese and cannot authorize a manuscript
interpretation even if every gate passes.

Run the acquisition and campaign with `./scripts/acquire-e005-benchmark` and
`./scripts/run-known-payload-retrieval`.
