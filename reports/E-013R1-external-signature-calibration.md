# E-013R1 external signature calibration

## Outcome

H-013 fails. The fixed eight-effect E-012 signature does not distinguish
intentional payload from hard no-intended-payload controls with the required
out-of-family reliability. Target application is prohibited.

This does not undo E-012: Voynichese still rejects four simple random/shuffle
mechanisms on eight transcription-robust dimensions. E-013R1 shows that those
rejections are not specific to meaning or payload. Other structured generators
and human-produced gibberish can occupy the same low-level effect space.

## Corrected numerical control

E-013R1 is the preregistered technical retry of the invalid E-013 attempt. Its
only change treats training IQR <= `1e-12` as constant. The corrected final model
records R2 as constant: its raw development IQR was
`2.7755575615628914e-17`, and its divisor was correctly replaced by 1.0. The
remaining seven scales were unchanged. Coefficients are finite and of ordinary
magnitude; no external score is artificially fixed at 0.5.

The recomputed case-feature file is byte-identical to the invalid attempt
(`9f340f73…`), proving that the correction affected only scaling and fitting,
not source selection, transformations, null generation, or effects. The first
attempt and its invalid apparent results remain documented separately in
`reports/E-013-technical-failure.md`.

## Corpus and construction controls

The campaign computed 415 cases:

- 132 development cases from 12 E-005 books;
- 154 independent cases from 14 disjoint E-008/E-009 books; and
- 129 external cases: 71 meaningful natural/conlang documents, 38 independent
  human-gibberish documents, and 20 Naibbe ciphertext variants.

Every document met the frozen 70-group minimum; none was excluded. The six
payload and five no-intended-payload mechanisms used 70–280 contiguous groups
in ten-group blocks and 64 replicates of each of four null families. All
payload transforms round-tripped exactly, case IDs were unique, development and
independent source hashes were disjoint, all case vectors contained exactly R1
through R8, all features were finite, and no manuscript transcription was read.

## Frozen gates

| Gate | Threshold | Result | Pass |
|---|---:|---:|---:|
| Doubly held-out development balanced accuracy | >= 0.70 | 0.6111 | no |
| Worst development mechanism recall | >= 0.55 | 0.0000 | no |
| Family-label permutation p | <= 0.01 | 0.2332 | no |
| Independent-book balanced accuracy | >= 0.70 | 0.7583 | yes |
| Worst independent mechanism recall | >= 0.55 | 0.1429 | no |
| External meaningful/conlang recall | >= 0.65 | 0.8310 | yes |
| Human-gibberish specificity | >= 0.65 | 0.3684 | no |
| Naibbe payload recall | >= 0.60 | 1.0000 | yes |
| Naibbe median payload score | >= 0.60 | 0.8001 | yes |

Only five of nine scientific gates pass. Construction controls pass, but all
scientific gates were conjunctive.

## Failure localization

The omitted-family development test is the most important result. Natural,
monoalphabetic, and nomenclator-hybrid cases each reached recall 1.0;
homophonic and Vigenere reached 0.917. However, progressive-key payload recall
was 0.0 when that complete mechanism was omitted from fitting. The signature is
therefore not generally stable across payload transformations.

Among development no-payload controls, both copy/mutate rates were rejected
perfectly. Character Markov-1 and the positional-slot generator had recall 0.0,
and token Markov-1 had recall 0.083: almost all were incorrectly labelled as
payload. This is not merely a development-set accident. In the independent
books, character Markov-1 recall was 0.214 and positional-slot recall 0.143,
even though aggregate balanced accuracy passed. The worst-family gate correctly
prevents this aggregate success from hiding mechanism collapse.

The truly external human experiment is decisive. Only 14 of 38 human-produced
gibberish documents were correctly rejected (specificity 0.368); their median
payload score was 0.587, compared with 0.719 for meaningful/conlang documents.
The distributions overlap substantially. Naibbe, by contrast, transfers well:
all 20 variants exceed the 0.5 threshold and their median score is 0.800. Thus
the signature can recognize this verbose-homophonic payload control while still
being far too permissive toward structured meaningless writing.

## Provenance and verification

- E-013R1 preregistration commit: `991e1fb5792ad78e8fc3958148b0256cc57c186c`.
- Clean corrected implementation: `e057be2e8fa74698e9cd4d40a369570f23491c1b`.
- Base E-013 config SHA-256: `ca27c9fd702a1f15e8924f8742d560948d60f6df1514f55e9d1c66cc34cfde24`.
- Result SHA-256: `3c8cef151f3fdfff4db6f185f16e820ce86c65b5ddf522f7e13c39cf61d201d8`.
- Case-feature SHA-256: `9f340f7388b48d04e0aed588ed017385a3f7426d257142eda64ed5020ed2d16e`.
- Corrected-model SHA-256: `f4cc897c8938cc12130cc6c33d9c310072fc529f0d72add0d7761103c2f60228`.
- Seed 20260907; 12 CPU workers; runtime 114.16 seconds.
- A fresh serialized replay exactly reproduced the model, 1,024 family-label
  permutations, all predictions, summaries, and gates.
- The pre-run full gate passed 114 tests, every workflow dry-run, all machine
  diagnostics, and local-AI health checks. No LLM supplied numeric evidence.

## Consequence

Do not score Voynichese with this model, reinterpret E-012 as evidence of
meaning, adjust the 0.5 threshold, remove difficult generator families, or add
features chosen from target behavior. The eight-effect classification branch is
closed.

The defensible next control-only question is whether independently motivated
higher-level structure can add specificity: information content/compression,
triple repetition, word-length autocorrelation, line and section positional
bias, long-range intermittency, vocabulary growth, and hierarchical page/quire
organization. These are precisely the levels at which the available human-
gibberish study reports differences or acknowledges insufficient sample length.
Any such panel must be developed and validated on external controls before a
new manuscript test is preregistered.
