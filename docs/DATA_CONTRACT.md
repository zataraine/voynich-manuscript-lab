# Data contract

The contract prevents a one-book corpus from becoming a collection of silently
incompatible files. It will be refined when the transcription encoding and scan
details are supplied; until then, neutral identifiers and reversible transforms
are mandatory.

## Layers

### Raw

`data/raw/` contains byte-identical acquisitions. Each file appears in a tracked
source manifest with its path relative to the repository, byte size, SHA-256,
role, media type, acquisition information, and rights status. Raw files are never
edited in place. A corrected transcription is a new file and a new manifest
version.

### Interim

`data/interim/` contains reversible transforms: rendered pages, deskewed copies,
segmentation masks, region crops, and parsed-but-not-normalized transcription
records. Every interim artifact must point to its raw parent and transform config.

### Processed

`data/processed/` contains analysis-ready records, features, alignments, and
leakage-safe splits. These are disposable and must be reproducible from raw files,
tracked code/config, and a recorded environment.

## Stable identifiers

Do not derive identity from a filename alone. Use ASCII identifiers:

- source: a user-confirmed slug, for example `source-a`;
- page: `{source_id}:page:{physical_index:04d}`;
- region: `{page_id}:region:{region_index:04d}`;
- line: `{page_id}:line:{line_index:04d}`;
- token occurrence: `{line_id}:token:{token_index:04d}`;
- image: `{page_id}:image:{image_index:04d}`.

Physical indices record source order, not an assumed foliation. If the book has
recto/verso labels, record them as metadata while retaining the neutral page ID.

## Text representation

- Store raw encodings exactly as received, including whitespace, case, line
  endings, separators, and uncertainty notation.
- Decode only with an explicit declared character encoding. Never use replacement
  characters silently.
- Store parsed observations as UTF-8 JSON Lines. Preserve `raw_surface` beside any
  normalized field and record a `normalization_version`.
- Do not call encoded units letters, words, or sentences until those unit types
  are established. Prefer `symbol`, `group`, `separator`, and `sequence`.
- Represent alternatives and damaged/uncertain readings structurally, not by
  deleting them or selecting a favorite reading.

Minimum parsed text record:

```json
{
  "schema_version": "1.0",
  "record_id": "source-a:page:0001:line:0001",
  "page_id": "source-a:page:0001",
  "raw_surface": "...",
  "parsed_units": [],
  "uncertainty": [],
  "source_manifest": "data/manifests/source-a.yaml",
  "parser_version": "unassigned"
}
```

## Page and image alignment

An alignment is a claim with a method and confidence, not a directory convention.
Record source/target IDs, alignment method (`supplied`, `manual`, `geometric`, or
`model`), confidence, reviewer, and provenance. Keep page-level, region-level, and
sequence-level alignments separate.

Coordinates use pixel-space `[x_min, y_min, x_max, y_max]`, origin at top-left,
with the exact parent image dimensions recorded. Never reuse coordinates after a
resize/crop without a transform matrix.

## Splits and leakage

Create split assignments before fitting. The default grouping unit is a physical
page; use a larger codicological unit when pages share templates or duplicated
content. All crops, alternate transcriptions, and derived features from one group
must remain in the same split. Store assignments in `data/processed/splits/` with
the source manifest and seed.

## Formats

- Tables: Parquet for analysis, UTF-8 JSONL for auditable records, CSV only for
  interchange.
- Images: retain originals; use lossless PNG/TIFF for derived evidence crops.
- Arrays: Parquet for tabular vectors or `.npy`/safetensors with a JSON manifest.
- Config and registries: YAML; schemas and machine reports: JSON.
- Timestamps: RFC 3339 UTC. Hashes: lowercase SHA-256 hex.
