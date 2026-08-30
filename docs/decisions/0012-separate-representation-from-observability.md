# 0012: Separate representation failure from observability

Date: 2026-08-30

## Status

Accepted for E-006 before implementation or execution.

## Context

E-005 detected exact-payload identity overall but failed four of six robustness
gates. Affine, columnar, and rail-fence transformations dominated; Bifid,
ADFGX, and Enigma were near chance. Repeated tuning against those exposed
family outcomes would overfit the only independent paired benchmark.

Some transformations preserve obvious blind invariants while others are
designed to suppress them. A family-blind failure under a fixed rotor cipher is
not equivalent to failure after the family and key are supplied. The next test
must distinguish representation weakness, cross-family transfer failure, and a
correct implementation ceiling.

## Decision

Freeze the E-005 sources, normalization, segments, candidate sets, cipher
families and parameters, document folds, and six thresholds by configuration
and result hashes. Evaluate exactly one primary representation:
`fused-character-relation-v1`. It concatenates four prespecified components:

1. the frozen E-005 relative surface/sequence panel;
2. symbol-renaming-invariant frequency, n-gram-count, recurrence, and
   residue-period signatures;
3. aligned modular difference, sum, affine-residual, mutual-information, and
   lag profiles, including a two-character ciphertext view for fractionation;
4. normalized zlib, bzip2, and LZMA compression distances over raw and
   first-occurrence-canonical sequences.

Fit only on other documents and other cipher families in the primary regime.
Repeat the complete evaluation over three fixed classifier seeds. Report each
component without allowing post-run substitution. Add a same-family/new-document
diagnostic and an exact-decryption ceiling so a negative result is localized.
Add ciphertext-position destruction as a sequence-dependence control.

The original six E-005 gates remain unchanged. Add a minimum worst-seed mean
normalized MRR of 0.15 and require the exact-decryption ceiling to achieve MRR
1.0. All eight gates must pass.

## Consequences

E-006 remains a diagnostic experiment on an exposed benchmark. A pass permits
replication with another independent implementation suite; it does not permit
Voynich scoring. A failure of family-blind transfer alongside successful
same-family calibration localizes the problem to generalization. Failure in
both regimes indicates that the proposed pair representation is inadequate.
Failure of the exact ceiling invalidates the campaign implementation.

Pretrained language-model embeddings are excluded from corpus representation:
the local embedding/reranking stack may retrieve methodological notes only.
Neural sequence encoders are deferred until an interpretable relation bank has
been evaluated; the outer training folds contain only 32 benchmark segments,
making an unconstrained encoder a high-variance first move.
