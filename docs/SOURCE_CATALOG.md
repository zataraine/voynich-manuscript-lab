# Voynich source catalog

This catalog records the evidence hierarchy for Beinecke MS 408. A file being
present in the lab means only that it is available for study; it does not make
its assertions true. Exact acquisition URLs and destinations are in
`config/sources/voynich-acquisition.yaml`; tracked byte counts and SHA-256 hashes
are in `data/manifests/`.

## A. Primary manuscript object

| Source | Local material | Use |
|---|---:|---|
| [Yale catalog record](https://collections.library.yale.edu/catalog/2002046) | 213 full-resolution IIIF canvases, Presentation 3 manifest, 1 complete PDF | Canonical pixels, canvas order, dimensions, and labels |
| [Beinecke collection page](https://beinecke.library.yale.edu/beinecke/collections/beinecke-cipher-voynich-manuscript) | HTML snapshot | Custodial and historical context |
| [Beinecke physical catalog](https://pre1600ms.beinecke.library.yale.edu/docs/pre1600.ms408.HTM) | HTML snapshot | Physical description and bibliography |

Yale's public-access statement is not treated as a blanket open-content
license. The raw images remain uncommitted and their reuse must follow Yale's
terms and applicable law.

## B. Page structure and transcription witnesses

| Source | Local material | Use |
|---|---:|---|
| [Folio/quire navigator](https://voynich.nu/folios.html) | HTML snapshot | Missing folios, foldouts, quire structure, and page descriptions |
| [Transcription index](https://voynich.nu/transcr.html) | HTML plus 10 IVTFF/legacy source files and 9 STA conversions | Independent readings, uncertainty, loci, scribal/Currier metadata |
| [IVTFF and conversion tools](https://voynich.nu/software/ivtt/IVTFF_format.pdf) | Specifications, manuals, C sources, conversion tables | Exact parsing and reversible encoding conversion |

The witnesses are deliberately separate. Agreement may support a stable reading;
disagreement is evidence about transcription uncertainty. EVA, reduced EVA, and
STA are encodings, not decipherments, and visual spaces are not assumed to be
linguistic word boundaries.

## C. Physical and historical technical evidence

Downloaded research copies include the 2009 carbon-dating letter, the six-page
McCrone materials report (from an exact Internet Archive capture because Yale's
old file URL currently redirects), and Currier's paper and tables. These constrain
date, materials, folio groupings, and reported statistical strata; they do not
identify a plaintext language or cipher.

The McCrone report's first page, the Yale PDF, and all other PDFs were rendered
or structurally checked during intake. The archived original URL remains in the
acquisition configuration so the chain of custody is visible.

## D. Computational baselines

The local reference set contains:

- Reddy and Knight, *What We Know About the Voynich Manuscript* (ACL, 2011);
- Lindemann and Bowern, *Character Entropy in Modern and Historical Texts*, plus
  the Yale Working Group corpus pinned to Git commit
  `decc4caaa6515b86e42a219d1da8d81114736f2e`;
- a Voynich topic-modeling study; and
- a word-probability study from the ACL Anthology.

They provide reproducible comparisons and known methodological cautions, not a
target answer. The Working Group repository has no `LICENSE` file, so its local
snapshot is marked research-only and must not be assumed to be open-source.

## E. Analysis and decipherment claims

The [voynich.nu analysis index](https://voynich.nu/analysis.html) and its five
linked chapters are archived as secondary technical commentary. Claims from
these pages must be restated as testable hypotheses before use.

The supplied [Voynich Research viewer](https://voynichresearch.com/viewer.html)
is catalogued but not copied. Its [terms](https://voynichresearch.com/terms.html)
prohibit automated scraping, crawling, data extraction, reproduction of the
decode/key/methodology, and AI-training use without permission. It is therefore
an external hypothesis source only. If its author supplies permission or a
licensed export, add that as a new immutable source; do not scrape the viewer.

## F. Generative cipher controls

The lab includes Greshko's Naibbe source and complete Zenodo v2.1 supplementary
dataset as a licensed, reversible verbose-homophonic control. See
`docs/NAIBBE.md`. It is kept apart from the manuscript/transcription manifests so
generated-cipher properties cannot become manuscript labels.

EVA and the Currier A/B evidence, terminology, current local page counts, and
consensus boundary are summarized in `docs/EVA_CURRIER.md`.

E-007 also pins cryptii commit
`c04a823b5f3f0c8dfc9d8a4bd10e35ef8177d642` under its MIT license. Its ADFGX
`CARGO` known vector is an independent implementation oracle for the lab's
stage-wise fractionation and columnar-transposition code; it is not evidence
about the manuscript.

E-008 adds eight Project Gutenberg works absent from E-005 as an independent
known-payload source set. Their raw bytes, acquisition endpoints, and hashes
are isolated in the E-008 source manifest. They test control generalization;
they are not linguistic comparators for Voynichese.

E-009 adds six further Project Gutenberg works absent from E-005 and E-008.
They supply natural-payload controls for a ciphertext-only scorer; their
plaintext and generated-control identities remain outside the scoring input.

## Known but not acquired

| Resource | Reason | Next action |
|---|---|---|
| NSA, [D'Imperio, *The Voynich Manuscript: An Elegant Enigma*](https://www.nsa.gov/History/Cryptologic-History/Historical-Publications/Historical-Publications-Lists/igphoto/2002761512/), [1976 seminar proceedings](https://www.nsa.gov/Press-Room/Digital-Media-Center/Document-Gallery/igphoto/2002761428/), and cluster-analysis papers | The official download endpoints return HTTP 403 to the reproducible client | Retain official catalog links; acquire manually only if the host permits it and record the exact bytes |
| Lisa Fagin Davis, scribal-hands study, DOI `10.1353/mns.2020.0011` | Publisher access is restricted | Add a lawfully supplied copy; use bibliographic metadata only until then |
| Multispectral or scientific image stack | No public, stable dataset was found in the supplied sources | Ask Yale/Beinecke whether calibrated or multispectral captures are available |
| Licensed export from the Voynich Research viewer | Explicit permission required | Request permission if testing its complete key becomes a research priority |

## Remaining data-engineering gaps

Before cipher searches, the lab still needs derived—not raw—artifacts:

1. a deterministic Yale-canvas ↔ folio ↔ IVTFF-locus table, including foldouts,
   missing folios, and non-text covers;
2. an IVTFF 2 parser/validator that preserves uncertain readings, comments,
   alternative spaces, and witness identity;
3. a multi-witness alignment lattice rather than a prematurely merged transcript;
4. page-region annotations linking lines, labels, plants, diagrams, stars, vessels,
   and human figures to image coordinates; and
5. structure-preserving null generators for homophonic/nomenclator,
   polyalphabetic, progressive-key, verbose-cipher, and non-linguistic controls.

Those are the important missing tools. Generic cryptographic and ML packages are
already sufficient for the first experiments; adding more solvers before these
interfaces exist would not improve evidential quality.
