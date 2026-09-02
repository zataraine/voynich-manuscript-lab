# Raw data

Place byte-identical acquisitions here. Do not edit or overwrite them. Organize
the original book, separately supplied images, transcription encodings, and
metadata in the existing subdirectories, then build and verify a tracked manifest.
Contents are intentionally ignored by Git.

For the Voynich corpus, do not hand-edit or replace acquisitions. Run
`scripts/acquire-voynich`, inspect `artifacts/acquisition/voynich-receipts.json`,
and verify the tracked manifests with `scripts/validate-voynich-intake`. Source
classification and rights notes are in `docs/SOURCE_CATALOG.md`.

Prospective human pseudo-text controls use the separate contract in
`docs/LONG_FORM_HUMAN_CONTROLS.md`. Store private payloads and their sidecars
under `data/raw/controls/human-pseudotext/`; validate them before manifesting,
and do not commit them merely because they pass the format validator.
