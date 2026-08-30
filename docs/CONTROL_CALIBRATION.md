# Control-calibration campaign

## Question

E-002 asks whether a deliberately limited panel of surface statistics can distinguish
held-out meaningful texts from human-produced meaningless text, survive a known-payload
cipher stress test, and produce stable measurements across transcription witnesses. It
does **not** detect meaning and cannot estimate the probability that Voynichese is a
language, cipher, constructed system, or hoax.

## Data boundary

The adapter reads eligible files directly from the pinned Naibbe reference tarball. It
does not extract or alter the archive. Every member is identified by its archive path and
SHA-256. The included meaningful texts and human-gibberish transcriptions are local
calibration inputs; the Naibbe ciphertexts are withheld known-payload positive controls.
No corpus excerpts are committed or sent to a language model.

The primary transform is `unicode-words-v1`: NFKC, Unicode case folding, removal of
numbers/punctuation as boundaries, and preservation of internal apostrophes or hyphens.
Voynich targets use the existing conservative `eva-stable-groups-v1` transform. This
difference is declared because the source encodings differ and is a possible confound.

## Leakage and fitting

Each document supplies at most four evenly spaced contiguous 100-token chunks. All
chunks from one document stay in the same stratified cross-validation fold and their
weights sum to one, preventing longer documents from dominating. Two fixed baselines—a
regularized logistic model and an extra-trees model—are averaged. There is no target-data
hyperparameter tuning. Performance is measured after averaging chunk scores back to the
source-document level, with document bootstrap intervals and a document-label
permutation test.

Neither Voynichese nor Naibbe ciphertext is used for fitting. Naibbe therefore tests a
critical failure mode: a meaningful payload transformed by a cipher can look unlike the
plain meaningful training texts. Multiple IVTFF witnesses are scored independently on
the same physical-page identifiers to expose transcription sensitivity.

## Interpretation gates

All three preregistered gates must pass before even the phrase “surface similarity” is
allowed:

1. held-out document balanced accuracy is at least 0.65;
2. the median Naibbe known-payload score is at least 0.60;
3. the median range across witness scores on common pages is at most 0.25.

A pass permits only a comparison under this feature panel. A failure withholds Voynich
interpretation and identifies which calibration assumption broke. In every case the
posterior probability field remains null.

## Running and resuming

Run the complete campaign in WSL with:

```bash
./scripts/run-control-calibration
```

Snakemake resumes completed immutable stages. The deterministic result is followed by
reference retrieval over approved methodological notes, then separate bounded Qwen and
GLM reviews. The local models receive numeric summaries and notes, never manuscript or
control-corpus text. Outputs live under
`artifacts/runs/E-002-control-calibration/` and are intentionally uncommitted.
