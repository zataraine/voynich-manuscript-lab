# Q-010 lossless representation audit

## Outcome

Q-010 passes its representation acceptance test. All eight acquired IVTFF 2.0
witnesses parse in strict mode, reconstruct their source bytes exactly, and map
every logical locus to every applicable Yale IIIF canvas. This is an
infrastructure result, not evidence that the manuscript contains language,
ciphertext, or meaning.

| Witness | Pages | Loci | Linked loci | Multi-canvas loci | Canvas links |
|---|---:|---:|---:|---:|---:|
| CD2a-n | 131 | 2,196 | 2,196 | 0 | 2,196 |
| FG2a-n | 202 | 4,060 | 4,060 | 245 | 4,305 |
| GC2a-n | 226 | 5,367 | 5,367 | 515 | 5,882 |
| IT2a-n | 225 | 5,215 | 5,215 | 514 | 5,729 |
| RF1b-e | 227 | 5,385 | 5,385 | 514 | 5,899 |
| RF1b-er | 227 | 5,385 | 5,385 | 514 | 5,899 |
| VT0e-n | 225 | 5,207 | 5,207 | 514 | 5,721 |
| ZL3b-n | 227 | 5,385 | 5,385 | 514 | 5,899 |
| **Total** | — | **38,200** | **38,200** | **3,330** | **41,530** |

The link count exceeds the locus count because partial and composite foldouts
are genuinely many-to-many. For example, IVTFF part pages can share one folio
side, Yale can provide multiple canvases for that side, and `fRos` spans f85v
and f86r. The audit keeps those facts instead of choosing one convenient image.

## Contract tested

- Exact physical lines and line endings reconstruct the original bytes.
- Witness ID, optional transcriber ID, page, sequence number, relative locator,
  locus type, raw source lines, and diplomatic surface remain explicit.
- Certain/uncertain spaces, drawing interruptions, paragraph markers, text
  tags, comments, ligatures, unreadable marks, high-ASCII escapes, and all
  alternative readings are structural units with exact spans.
- Alphabet-specific runs are deliberately not tokenized into assumed glyphs.
- Malformed markup, page mismatch, orphan continuation, and unsupported IVTFF
  versions fail strict parsing.
- Canvas records retain Presentation 3 order, IDs, labels, dimensions, image
  IDs/services, stable neutral page IDs, and all folio labels.

## Provenance

- IVTFF format PDF SHA-256:
  `7ac9c4a82064763cac8767cca6f661cc4e1b4503ab9342acc03032ddb6939d49`
- Yale Presentation 3 manifest SHA-256:
  `317d58fd9ea90392a83d9858a91eada3d0b41416a3c835857dc0154bd123a309`
- Parser SHA-256 before final documentation commit:
  `7b5951445b623413ecb74cf9b2a45941736ed30d46943ff19cf89daf550437e6`
- Canvas mapper SHA-256 before final documentation commit:
  `3449bdfc75d8c2aaddd2027ea872c4f59af775b9a0f9bbca8f0930be2d8a2222`
- Machine-readable audits:
  `artifacts/runs/q010-representation/*.json` (ignored generated layer; each
  embeds its witness and IIIF manifest hash).
- Durable design decision:
  `docs/decisions/0016-lossless-ivtff-and-many-to-many-canvas-map.md`.

## Boundary and next question

The acquired LSI interlinear archive declares IVTFF 1.5 and includes historical
byte values, so it is rejected rather than silently coerced into the format-2
contract. A separately versioned compatibility importer may be justified later.

The next useful step is Q-011: align the eight format-2 witnesses by canonical
locus while retaining omissions, alternatives, surface markup, and the identity
of every source. Only after measuring disagreement should the lab define any
analysis view that selects or normalizes readings.
