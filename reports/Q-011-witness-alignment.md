# Q-011 lineage-aware witness alignment

## Outcome

Q-011 passes its data-engineering acceptance test. The lattice contains 5,386
canonical IVTFF loci and preserves all 38,200 native format-2 readings. It does
not create a consensus transcript. All 5,386 loci have the same structural
locator/type code wherever more than one witness is present, so canonical IVTFF
page plus locus number is a stable alignment key for these sources.

Only 2,185 loci occur in all eight native files because the older CD and FG
witnesses have substantially less coverage. The only union locus omitted by
both current complete references is `f89v2.26`. GC, IT, and VT retain it; the
source history identifies it as a removed spurious label caused by show-through.
This is a useful positive check that the lattice exposes known source history.

## Cross-alphabet comparison

Native Curr, FSG, v101, EvaT, full EVA, and basic EVA strings were not compared
directly. Seven registered witnesses were compared through the separately
acquired official STA1 files. RF1b-er is another rendering of RF and therefore
has no second STA1 vote.

Across one representative from each of five non-synthetic lineage groups:

| Whole-locus result | Loci |
|---|---:|
| Exact STA1 reading | 601 |
| Reading difference | 4,767 |
| Insufficient lineage coverage | 18 |

Exact whole-locus equality is deliberately strict: one family-member choice,
separator, unreadable mark, or retained alternative makes a locus different.
Atomic STA1-token similarity shows that the differing readings are usually
close rather than wholesale replacements. Median pairwise similarity among the
five primary lineage representatives ranges from 0.904 to 0.971. The related
IT/VT pair agrees exactly at 4,467 loci, differs at 740, and has median token
similarity 1.0; that is sensitivity information, not independent replication.

RF is an automatically generated combination of ZL and GC. Its agreement with
either parent is consequently not independent evidence and is never included as
a new primary lineage. The full pairwise table remains in the machine audit.

## Conversion and uncertainty sensitivity

The supplied alternate STA1 conversions change 43 of 2,196 CD loci (1.96%) and
49 of 5,367 GC loci (0.91%). Both views remain attached to each lattice reading;
the alternate is not treated as another witness.

Uncertainty notation is strongly editorial-policy dependent. Native loci with
at least one explicit uncertainty marker range from zero in VT to 2,302 in ZL.
ZL alone records 728 loci with alternative readings and 1,833 with uncertain
spaces; GC records 1,595 loci with uncertain spaces. These counts cannot be used
as direct measures of manuscript legibility without controlling for witness.

## Provenance and reproducibility

- Witness registry SHA-256:
  `52d782700f6c8d3372ee99303d1c8e081cc847f30bf4777416f427be4b156778`
- Source manifest SHA-256:
  `76db756b0cd15bbe9a65055447757ae0590690ad64dc20e2f51065cb49537ae8`
- Alignment implementation SHA-256 before final documentation commit:
  `f0d9db7fbe8c26a6caf975665123c8046ae4a0ee58c6da7458170c205b6c0d4c`
- Final generated lattice v4 SHA-256:
  `0988585945ac0740900af4398059663456a5a61559c2726b775972fd3f982634`
- Final generated audit v4 SHA-256:
  `859824adb6e6ea279a1b2db0b2867664044d73a12d26907a169602b675c5aef9`
- Generated paths:
  `artifacts/runs/q011-witness-alignment/lattice-v4.jsonl` and
  `artifacts/runs/q011-witness-alignment/audit-v4.json`.

The tracked registry records alphabet, lineage group, comparison role,
derivation edges, primary STA1 view, alternate conversions, and every input
hash. A cached repository-root lookup reduced a full rebuild from roughly four
minutes to 13 seconds without changing the audit result.

## Limits and next question

STA1 supplies a common representation but remains a transliteration conversion,
not ground truth about glyph identity. Token similarity does not establish
language, plaintext, or meaning. The lattice also does not yet locate individual
lines geometrically on foldout images.

Q-012 should now test which previously interesting structure measurements remain
stable across primary witness selection and admissible uncertainty/conversion
views. That is a necessary bridge back to the manufactured-language versus hoax
question: conclusions that depend on one preferred transcription should be
discarded before any classifier or long local-model campaign is run.
