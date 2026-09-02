# E-014 higher-order external calibration

## Outcome

H-014 fails. The fixed 21-feature higher-order panel does not distinguish
intentional payload from structured no-intended-payload controls with the
required out-of-family reliability. Only two of nine scientific gates pass.
Voynichese was not read or scored, and no manuscript witness experiment is
authorized.

This is a valid negative result, not a technical failure. Every construction
control passes, all 415 feature vectors are finite and in the frozen order, the
complete extraction replays exactly, and the serialized model and 1,024-label-
permutation evaluation reproduce exactly.

## Control design

The campaign reused E-013's document-disjoint controls and deterministic
contiguous windows:

- 132 development cases from twelve E-005 books;
- 154 independent cases from fourteen disjoint E-008/E-009 books; and
- 129 external cases: 71 meaningful/conlang documents, 38 human-produced
  gibberish documents, and 20 Naibbe ciphertext variants.

Six payload families and five no-intended-payload families were represented.
The model received only the 21 preregistered vocabulary-growth, token-length,
recurrence, contextual-domain, compression, and co-occurrence measurements. It
did not receive the E-012 effects, document length, family, source identity,
language, manuscript values, semantic embeddings, or LLM output.

## Frozen gates

| Gate | Threshold | Result | Pass |
|---|---:|---:|---:|
| Doubly held-out development balanced accuracy | >= 0.70 | 0.6375 | no |
| Worst development mechanism recall | >= 0.55 | 0.0000 | no |
| Family-label permutation p | <= 0.01 | 0.1551 | no |
| Independent-book balanced accuracy | >= 0.70 | 0.7833 | yes |
| Worst independent mechanism recall | >= 0.55 | 0.3571 | no |
| External meaningful/conlang recall | >= 0.65 | 0.7606 | yes |
| Human-gibberish specificity | >= 0.65 | 0.2895 | no |
| Naibbe payload recall | >= 0.60 | 0.5000 | no |
| Naibbe median payload score | >= 0.60 | 0.5057 | no |

All gates were conjunctive. Passing aggregate accuracy on the independent books
does not override the family and external failures.

## Failure localization

Complete-family omission fails in both directions. In development, token
Markov-1 recall is 0.0, while character Markov-1 is 0.333 and positional-slot is
0.5: several structured no-payload mechanisms are labelled as payload. Vigenere
recall is 0.333 and homophonic recall is 0.417: the same panel also rejects
known payload after some cipher transformations. The family-label permutation
result (`p=0.155`) shows that the development separation is not independently
distinguishable from family assignment chance at the preregistered level.

The independent aggregate score improves, but positional-slot recall remains
0.357 and is the worst family. The human experiment is again decisive: only 11
of 38 human-gibberish documents are rejected. Specificity is 0.20 for the five
70--159-group cases, 0.118 for the seventeen 160--279-group cases, and 0.50 for
the sixteen 280-group cases. These length strata were diagnostic only, not
additional gates. Poor performance is not confined to the shortest documents.

Naibbe transfer also degrades relative to E-013R1: only half of the twenty
variants cross 0.5 and their median score is 0.5057. Thus the higher-order-only
panel neither solves E-013R1's human-gibberish false positives nor preserves its
Naibbe sensitivity.

The largest final-model coefficients belong to order-sensitive length and token
compression, co-occurrence assortativity, and token/block information. Their
magnitudes diagnose the fitted development model; they are not feature
importance claims because the features are correlated and the complete-family
test fails.

## Integrity and provenance

- Preregistration commit: `f11b1c4dcb15a274c43a0d4602fc5d9189a7244b`.
- Clean implementation commit: `8681cf9e8537aac5ddc4f2420a881e1e4c4a7cb5`.
- Config SHA-256: `ab8e1ca9a44371da82c526912e585c24f6bdd61a596893e519dfdecd2343fbaf`.
- Case-feature SHA-256: `ebb8462699651ca0ca3efc2aec447171f366d83d632139c64198ae8e1eea521b`.
- Model SHA-256: `e3b72ad4c42fa71019d539868f4b103856e0ff055b219938c08eefcdd4facb83`.
- Result SHA-256: `ad9ebb00b46dc4f2c1ede23fa1528a1daff68cf6d2b92aacf8f7a21bc5452e13`.
- Seed 20260908; 12 CPU workers; runtime 87.76 seconds.
- Maximum length-preserving token-renaming delta: 0.0.
- The pre-run full gate passed 118 tests, all workflow dry-runs, machine
  diagnostics, and local-AI health checks. No LLM supplied numeric evidence.
- A fresh serialized replay exactly reproduced the model, all 1,024 permutation
  values, predictions, summaries, and gates.

## Consequence

Close this fixed higher-order classifier panel. Do not combine it with the
failed E-013R1 model, remove difficult families or short human controls, alter
the threshold, select coefficients, or score Voynichese.

The evidence now points to a control limitation as well as a feature limitation:
the available human no-intended-payload documents contain only 79--480 groups,
too little for manuscript-scale page/quire hierarchy. A defensible next step is
to acquire or prospectively create longer, provenance-rich human pseudo-text
controls and separately validate hierarchical generators that reproduce Zipf,
Heaps, recurrence, and section drift. Until such controls exist, another binary
payload classifier would repeat the same ambiguity rather than answer the
manufactured-language-versus-nonsense question.

