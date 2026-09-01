# E-013 technical failure

## Status

The first E-013 run is invalid for scientific interpretation. Corpus
construction and all 415 eight-effect records completed, but a numerical defect
in robust scaling corrupted every fitted classifier and its downstream gates.
H-013 therefore remains untested.

The second effect's development IQR was `2.7755575615628914e-17`, ordinary
floating-point residue around a constant value. The implementation replaced
only an IQR exactly equal to zero. Dividing by the residue produced standardized
values near `1e15`; L2 logistic coefficients collapsed to approximately
`1e-28`, and 70 of 129 external scores became exactly `0.5`. The apparent
balanced accuracies, permutation p-value, family recalls, and gate failures are
not admissible evidence.

## Preserved artifacts

- Clean implementation commit: `1f9b9d287b69e530ab84d050ca128cdf31a06757`.
- Preregistration commit: `660d666f5b091b0eb2fa34e2d42f8abd0408e31a`.
- Result SHA-256: `15051a0e568337bc0edf750098108d1e6513f1d440e0685c8a294fee4ae8cfb7`.
- Case-feature SHA-256: `9f340f7388b48d04e0aed588ed017385a3f7426d257142eda64ed5020ed2d16e`.
- Corrupted-model SHA-256: `026a130ccd15358945f5a22caccccb1c018575a6a7125d424628fa16c9c7272a`.
- Runtime: 109.53 seconds; all construction controls passed.

The untracked machine artifacts remain immutable at
`artifacts/runs/E-013-external-signature-calibration/`. They will not be
overwritten or reused as a scientific result.

## Frozen correction

E-013R1 changes one numerical rule: any training IQR less than or equal to
`1e-12` is treated as constant and assigned scale 1.0. This matches the lab's
existing metric-invariance tolerance and prevents floating-point residue from
becoming signal. A synthetic near-constant-scale regression test is mandatory.
All sources, cases, effects, labels, folds, transformations, seeds, model class,
thresholds, permutations, and scientific gates remain unchanged. E-013R1 will
write a new immutable run directory and recompute every case from source.
