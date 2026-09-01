# Multi-witness mechanism replication protocol

## Purpose

E-012 replicates a fixed subset of E-001's held-out structure effects across
five lineage-representative STA1 witnesses and explicit ZL3b uncertainty views.
It asks whether simple mechanism rejections are transcription-robust. It does
not classify meaning, estimate hoax probability, or identify a cipher.

## Frozen representation

Load CD2a, FG2a, GC2a, IT2a, and ZL3b only through the official primary STA1
files in `config/corpora/ivtff-witnesses.yaml`. Restrict to canonical paragraph
loci present in all five witnesses and pages labelled Currier A or B. A page is
eligible only if every primary witness has at least 20 groups and 100 atomic
STA1 symbols. STA1 two-character codes remain atomic. Unreadable marks and
ligatures remain atomic; no uncertain material is deleted.

The primary witness views use preferred-first alternatives and split uncertain
spaces. Add five ZL3b sensitivity views: preferred-first/join, last/split,
last/join, opaque/split, and opaque/join. The preferred-first/split ZL3b view is
already the primary ZL3b witness and is not duplicated. Thus every replicated
effect must survive ten analysis views.

Map the union of atomic symbols bijectively to Unicode private-use code points
solely so E-001's tested character-string machinery operates on atomic STA1
symbols. Record the map, require exact roundtrip, and require observed metrics
to be invariant under an order-preserving relabelling within `1e-12`.

## Split

Create one seeded 75/25 physical-page split, seed 20260906, stratified by the
registered Currier, hand, and section metadata. Apply the identical page IDs to
every witness and uncertainty view. All derivatives of a page remain on the
same side. Require zero train/held-out overlap and complete eligible-page
coverage.

## Frozen measurements and nulls

Reuse E-001 without changing definitions:

- character trigram gain over a unigram model;
- group bigram gain over a unigram model; and
- recent edit-distance-one local copy rate.

For each view, generate 512 seeded replicates of the five E-001 families:
within-page group shuffle, within-group symbol shuffle, global intact-group
resampling, IID symbol generation with observed group lengths, and local
copy/mutate pseudo-text. Use alpha 0.1 and mutation rate 0.18. Each null corpus
preserves page IDs and group counts.

## Eight replication effects

E-001 previously reported the following positive target-minus-null effects.
These eight—and no others—are E-012's primary family:

1. within-page shuffle: group-bigram gain;
2. within-page shuffle: local-copy rate;
3. within-group symbol shuffle: character-trigram gain;
4. within-group symbol shuffle: local-copy rate;
5. global group resampling: group-bigram gain;
6. global group resampling: local-copy rate;
7. IID symbol/length matching: character-trigram gain; and
8. IID symbol/length matching: local-copy rate.

For each effect and view, calculate the one-sided empirical p-value
`(1 + null >= observed) / 513` and the observed-minus-null-mean effect. The
intersection-union/conjunction p-value for an effect is the maximum p-value
across all ten views: one weak view therefore fails the replication. Apply Holm
correction across the eight conjunction p-values. An effect passes only if its
effect is strictly positive in all ten views and its adjusted conjunction
p-value is at most 0.05.

H-012 passes only if the encoding, split, shape, and rename-invariance controls
pass and all eight primary effects replicate. Partial replication is reported
but cannot authorize a return to the manufactured-versus-nonsemantic question.

## Mandatory ambiguity diagnostic

Report all three metrics against copy/mutate pseudo-text in every view, without
using them to rescue or fail H-012. E-001 found copy/mutate compatible on two of
three dimensions. Readable-looking structure or rejection of simpler shuffles
cannot override compatibility with a structured nonsemantic generator.

## Boundary

Passing would validate only these structure effects across the acquired
representations. A separately preregistered external-control campaign over
known natural, ciphered, and nonsemantic sources would still be required before
any target classification or odds. Failure closes this E-001 feature/null branch
instead of prompting threshold or witness selection.
