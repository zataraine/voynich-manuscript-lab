# E-007 ADFGX stage localization

## Result

E-007 passed all nine preregistered gates on known controls. Payload identity
was perfectly retrieved after the coordinate stream was restored under an
exhaustive hidden column-order search at widths five, six, and a ragged width
seven. Fractionation alone, transposition alone, and their composition each
had normalized MRR 1.0. The result explains the E-006 ADFGX failure as a
stage/unitization mismatch: adjacent symbols in final ADFGX ciphertext are not
the Polybius pairs formed before transposition.

This is a mechanical localization result. It neither decrypts unknown text nor
shows that Voynichese uses ADFGX, fractionation, or any cipher.

## Design

- One frozen 600-character segment from each of twelve E-005 documents formed
  a twelve-way retrieval set without same-document duplicates.
- Three variants used column widths 5, 6, and 7; the final case had ragged
  columns because its 1,200-symbol coordinate stream is not divisible by 7.
- The scorer received candidate plaintexts, ciphertext, and one hypothesized
  width. It did not receive the square, keyword, column order, or correct
  candidate.
- Every order was enumerated (120, 720, and 5,040 permutations). After each
  inverse transposition, a deterministic score measured whether plaintext
  symbols and recovered coordinate pairs formed a bidirectionally consistent
  mapping.
- Ranks used average tie positions. The actual order had to belong to the full
  maximizer set; enumeration order could not create a success.
- Lower neighboring widths 4, 5, and 6 were frozen negative controls. A
  256-replicate identity permutation supplied the retrieval null.
- A pure-Python score was tested against the Numba kernel. Pynini encoded and
  inverted every square. The pinned pycipher implementation and cryptii's
  independent `CARGO` vector supplied external implementation oracles.

## Measurements

| Measurement | Gate | Observed | Outcome |
|---|---:|---:|---|
| Independent oracle fraction | 1.0 | 1.0 | pass |
| Pynini roundtrip fraction | 1.0 | 1.0 | pass |
| Fractionation normalized MRR | at least 0.95 | 1.0 | pass |
| Transposition normalized MRR | at least 0.95 | 1.0 | pass |
| Worst combined normalized MRR | at least 0.50 | 1.0 | pass |
| Worst combined pair AUC | at least 0.90 | 1.0 | pass |
| True order in maximizer set | at least 0.95 | 1.0 | pass |
| Median correct-minus-wrong-width margin | at least 0.05 | 0.82125 | pass |
| Combined identity-permutation p | at most 0.05 | 0.003891 | pass |

Exact stage roundtrips also passed in all 36 variant/document cases. Each
variant achieved top-1 fraction 1.0 at all three stages. The per-variant median
correct-minus-wrong-width margins were 0.8317, 0.8208, and 0.8075. The full
campaign required 7.35 seconds wall time and 395 MB peak resident memory.

## What was learned

The E-006 representation used a width-two view after ADFGX's columnar stage.
That view joined symbols which were not original Polybius coordinate pairs.
E-007 shows that when the stream is first inverted under the correct width and
hidden order, pair consistency becomes completely identifying on these
controls. All individual stages, the ragged implementation, and independent
oracles passed, so the earlier failure is not explained by broken ADFGX
generation, Polybius mapping, column inversion, or loss of payload identity.

The reusable output is more important than the perfect score: the lab now has
explicit fractionation and transposition stages, reversible FST mappings,
tie-safe retrieval metrics, a compiled exhaustive-order solver, and a wrong-
width interface. Those primitives apply to future fractionating and hybrid
cipher controls without asking a language model to recognize semantics.

## Limitations

The E-005 texts and all three E-007 transform specifications are exposed. Width
is supplied rather than inferred, the wrong-width controls are neighboring
lower widths rather than a complete corrected scan, and exhaustive order
search grows factorially. Candidate plaintext is available, so this is known-
payload retrieval, not blind decryption. Perfect scores are expected when the
correct deterministic inverse is in a small exhaustive search; they must not
be described as learned generalization.

No direction, glyph inventory, word boundary, coordinate alphabet, width, or
candidate plaintext is known for the Voynich Manuscript. Applying this solver
to the target now would create an uncontrolled multiple-hypothesis search.

## Local review

The bounded Qwen review used 2,078 local tokens and correctly described the
result as perfect deterministic known-control recovery with no semantic or
unseen-data evidence. It assigned effect strength `none` and requested an
unseen-ciphertext test. The GLM critic assigned `strong` to the control effect
but likewise limited the claim to known plaintext and requested an independent
blind test. Its generated assessment was truncated by the review schema's
field limit and mentioned widths five and six while omitting the equally
successful ragged width-seven case. The deterministic record, not either
advisory review, controls the claim.

## Provenance

- Preregistration commit: `6700c1d`.
- Deterministic implementation commit:
  `b42f4d6821fc7745558e4a26fd6a2224ae014972`; clean working tree.
- Deterministic result SHA-256:
  `8bcc38afec4a5d29406dbff0fa566b4295a79f34d0b8c03d0d37a04ee0c760a2`.
- Qwen review SHA-256:
  `713b2405c2daeb91b0b38d0d0c9cfe4047b10c55b4ead57d32ae58a37ffc0735`.
- GLM review SHA-256:
  `ff27c407a5a4ff18762d3611492bf7d5062e4cb4a142992eacacab7b60ca7946`.
- Experiment config SHA-256:
  `49ef0a59f2c4861d07fdcec1637fad96a4eea71b196cc14974db0063a4c8ec8f`.
- E-005 manifest SHA-256: `ae6a26ac04a22bc20bcf746d852cb4d394707ee3fa13126e0d2fb5f8870842c1`.
- cryptii oracle manifest SHA-256:
  `935a4aa0349cdb18227a97268669ba2f1b1f8b1883bb4808837191e10034cabc`.
- cryptii source archive SHA-256:
  `7c118e270643d264fdf1b5a897ed75c1f8ede130dff8961d2483e00185415ced`.
- Machine-readable artifacts remain under
  `artifacts/runs/E-007-adfgx-stage-localization/` and are uncommitted.

## Next falsifiable campaign

E-008 should be an independently generated blind robustness suite, not more
tuning on these perfect controls. A separate implementation should choose
unseen squares, keys, widths, ragged lengths, and candidate sources after the
E-007 code is frozen. The solver should receive a preregistered width range
rather than one correct width, correct for the width/order search, include
broken-mapping and structure-preserving nulls, and report compute scaling and
failure by width. Only that replication can establish whether the diagnostic
generalizes enough to justify designing a target-side null experiment.
