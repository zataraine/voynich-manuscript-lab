# Naibbe cipher research note

## Status and sources

Michael A. Greshko's 2025 Cryptologia paper introduces Naibbe as a historically
plausible, hand-operable **verbose homophonic substitution cipher** that converts
Latin or Italian into reversible EVA-like ciphertext. The author presents it as
a constructive compatibility result and statistical baseline, not the actual
Voynich key or a decipherment.

The lab retains:

- GitHub source pinned to commit
  `f2675ec5dd275268bc64dd48ea64fc0e0e9827a2`;
- Zenodo record `17219445`, version 2.1, including the original Excel cipher,
  Voynichesque macro workbook, supplementary methods, figures, comparison data,
  and network data; and
- SHA-256 manifests and the original Zenodo metadata/checksums.

The [paper](https://doi.org/10.1080/01611194.2025.2566408) is CC BY 4.0 and
openly readable, but its publisher PDF endpoint rejected the reproducible client;
the complete supplementary PDF is local. The
[repository](https://github.com/greshko/naibbe-cipher) uses a modified MIT-style
license that additionally requires citation of the 2025 publication. The Zenodo
record declares CC BY 4.0.

## Mechanism

At a high level, the reference implementation:

1. normalizes Latin/Italian letters and removes original spacing;
2. randomly respaces the plaintext into one- and two-letter units;
3. selects among six weighted substitution tables using a shuffled 52- or
   78-card deck model;
4. maps a plaintext unigram to a complete EVA-like word, or maps the first and
   second letters of a bigram to an EVA-like prefix and suffix; and
5. optionally removes some ciphertext spaces.

The result is verbose and homophonic: one plaintext letter has multiple possible
ciphertext realizations, and ciphertext token structure carries information about
whether the plaintext unit was a unigram or bigram. The decoder searches the
inverse tables and explicitly displays some ambiguous readings.

## Why it is useful here

Naibbe gives us a controlled positive example of meaningful plaintext filtered
through a process that reproduces several Voynich-like distributions. It can be
used to:

- test whether our diagnostics recognize verbose homophonic structure;
- measure which Voynich features are generic consequences of respacing/table
  design and which Naibbe fails to reproduce;
- benchmark plaintext recovery when the generative family is known but the table
  choices are hidden;
- create held-out Latin/Italian ciphertext with exact plaintext truth; and
- compare A/B, hand, line-position, paragraph, long-range, and local-edit-distance
  signatures against a structure-aware null rather than ordinary substitution.

OpenFST/Pynini is a natural representation for deterministic table components,
alternative tokenizations, weighted table choices, and inversion. Random deck
state and space deletion must remain explicit state/process layers rather than be
silently averaged away.

## Code audit and cautions

The pinned source contains no network or subprocess execution in its main cipher
scripts and primarily depends on Python, Pandas, CSV tables, and standard-library
randomness. It is retained as untrusted reference code and has not been imported
into the lab package.

Reproduction requires wrappers because the upstream scripts:

- use global, unseeded `random`, so outputs are not reproducible by default;
- use working-directory-relative paths;
- provide no Python environment/requirements lock;
- use module-level mutable configuration and counters;
- resolve some decoder ambiguity heuristically; and
- include an `.xlsm` workbook, whose macros must never be enabled or executed in
  the research pipeline.

The lab should first reproduce a published reference output byte-for-byte or
metric-for-metric with recorded versions and seed behavior. Any cleaned port must
be a separate implementation with parity tests against the pinned source. A
successful imitation of selected statistics is evidence that those statistics
do not rule out this cipher family; it is not evidence that the manuscript used
Naibbe.
