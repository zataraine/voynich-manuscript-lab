# Robust parameter ladder

E-004 tests whether the partial transfer found by E-003 survives parameter
variation and repeated seeds. Voynichese is excluded. Six complete cipher
families comprise 16 fixed variants: three monoalphabetic mappings, homophonic
alphabets of size two, three, and five, four progressive-key settings, three
nomenclator sizes with matched homophony, two verbose widths, and identity.

For every outer test, all variants of one family and all evaluation documents
are absent from fitting. Inside that boundary, the selector ranks features by
median standardized class separation divided by cross-variant instability and
retains exactly 12 of 29 measurements. This is recomputed using only training
rows. The full panel is a labelled baseline and cannot replace the primary
result after execution.

Three fixed evaluation seeds exercise folds, transform mappings, and model
initialization. The four E-003 thresholds remain frozen. E-004 adds a requirement
that the worst seed's mean family accuracy reach 0.60. Thirty-two label
permutations apply to the first seed; Naibbe remains an external known-payload
control; token-order destruction remains the sequence-sensitivity challenge.
Failure of any gate blocks target scoring.

Run the immutable Snakemake campaign with:

```bash
./scripts/run-robust-parameter-ladder
```
