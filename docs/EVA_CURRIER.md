# EVA and the Currier A/B strata

## What EVA is

The Extensible Voynich Alphabet (EVA) is a transliteration convention: it maps
visible Voynich glyph shapes to convenient Latin-character strings for storage,
display, and analysis. It is not a decipherment, a phonetic alphabet, or evidence
that an EVA letter has the sound/value of its Latin lookalike.

Gabriel Landini and René Zandbergen designed EVA in the late 1990s with important
input from Jacques Guy. “EVA” first meant *European Voynich Alphabet* and later
*Extensible Voynich Alphabet*. Basic EVA covers the common inventory; extended
EVA can retain rare shapes and components. Some visually complex manuscript
units are deliberately represented analytically by multiple ASCII characters,
for example `ch`, while sequences such as `iin` may or may not correspond to the
right underlying character unit. This is why analyses must declare whether they
operate on EVA code points, EVA glyph groups, strokes, or manuscript shapes.

The lab's primary working witnesses are the current independent IVTFF sources in
`data/raw/transcriptions/ivtff/`. The IVTFF specification, Zandbergen's
[transliteration survey](https://ceur-ws.org/Vol-3313/keynote1.pdf), and the
[voynich.nu transcription history](https://voynich.nu/transcr.html) are retained
with checksums. EVA, reduced EVA, STA, Currier, FSG, and v101 encodings must remain
distinguishable in every derived artifact.

## What Currier A and B mean

Prescott Currier used “Language A” and “Language B” for two clearly different
statistical profiles in the manuscript text. In his own 1976 notes he explicitly
said that *language* was a convenient loose term and did not imply an identified
underlying natural language. The careful modern wording is therefore **Currier
A/B statistical strata**.

The original and repeatedly reproduced signals include:

- EVA-like final `dy` patterns are much more characteristic of B;
- `chol`/`chor`, `chain`/`chaiin`, and some initial `ch`/gallows combinations are
  more characteristic of A;
- modern summaries find `ed` essentially absent in A and frequent in B;
- `daiin` is the most frequent type in a commonly used A corpus, while `chedy`
  is the most frequent in B and absent from that A corpus; and
- B pages tend to contain more text and include several internally distinguishable
  variants or “dialects.”

These are distributional observations, not translations. They remain visible
under character-, bigram-, and word-distribution analyses and have been recovered
by unsupervised clustering. A 2026 preprint independently reports a two-component
model and 89% held-out prediction of Currier labels, but its stronger generative
interpretations remain recent research rather than settled consensus.

## Current local classification

The ZL3b witness acquired on 2026-08-29 contains 227 physical-page headers:

| IVTFF `$L` value | Page headers |
|---|---:|
| A | 114 |
| B | 83 |
| Missing/unassigned | 30 |

These are header counts, not word totals or independent folio counts. The report
is reproducible with:

```bash
./scripts/lab ivtff summarize data/raw/transcriptions/ivtff/ZL3b-n.txt \
  --output artifacts/runs/zl3b-page-metadata.json
```

The same headers record five numbered scribal hands plus one unknown marker.
Lisa Fagin Davis's palaeographic work supersedes Currier's informal hand count;
hand and A/B stratum must be modeled as separate variables even though they are
correlated. Section/illustration type, quire, hand, folio order, text length, and
transcriber are all potential confounders.

## Consensus boundary

Well supported:

- EVA is the standard practical transliteration family, with known limitations.
- A/B is a strong, reproducible statistical distinction.
- The manuscript has multiple scribal hands; the modern palaeographic model has
  five.
- A/B, hand, and illustration section are correlated but not interchangeable.

Not established:

- that A and B are two natural languages, dialects, cipher keys, authors, or
  chronological phases;
- that manuscript spaces are linguistic word boundaries;
- that EVA sequences are phonemes or even the correct atomic glyph inventory; or
- that any A↔B difference identifies plaintext semantics.

For experiments, stratify or match by A/B, hand, section, and page length; report
results both pooled and separated. Never infer A/B from a test feature and then
claim the same feature independently validates A/B.
