# ADR 0016: Lossless IVTFF parsing and many-to-many canvas mapping

## Status

Accepted on 2026-08-31.

## Context

IVTFF 2.0.2 distinguishes physical source lines, logical loci, alternative
readings, uncertain spaces, drawing interruptions, ligatures, unreadable marks,
comments, text tags, page variables, and optional transcriber IDs. The Yale IIIF
manifest describes ordered image canvases. On foldouts, an IVTFF page can be one
part of a folio side while one Yale canvas can show several sides; `fRos` spans
f85v and f86r. Therefore neither a flattened EVA string nor a one-locus/one-image
join is reversible or accurate.

The IVTFF specification is the authority for syntax and page names. The IIIF
Presentation 3 manifest is the authority for canvas order, identifiers,
dimensions, image services, and labels. TEI critical-apparatus concepts inform
the requirement to retain readings and witnesses, but TEI is an export option,
not the lab's canonical internal representation.

## Decision

Parse only IVTFF format 2.x into two linked layers:

1. byte-reversible physical lines, retaining exact ASCII content and line endings;
2. structural logical loci retaining witness/transcriber identity, raw lines,
   locus fields, and diplomatic surface units.

Alphabet-specific strings remain uninterpreted `glyph_run` values. Syntax such
as alternatives and uncertain spaces is structured without selecting a reading.
Strict mode rejects structural issues; non-strict mode returns explicit issues.

Map IVTFF page names to physical folio sides using the IVTFF conventions, then
emit every matching Yale canvas link. Foldout mappings are intentionally
many-to-many. A later region-annotation stage may narrow a locus to coordinates,
but it must not replace these page-level source claims.

## Consequences

- Witness disagreement remains measurable rather than disappearing into a
  consensus transcript.
- Every parsed source can be round-tripped byte-for-byte.
- Canvas links are deterministic and auditable, including repeated/partial
  foldout images.
- IVTFF 1.x interlinear material is not silently accepted by the format-2 parser;
  it requires a separately versioned compatibility path.
- Automated collation and TEI/IIIF annotation exports come after this contract,
  not before it.
