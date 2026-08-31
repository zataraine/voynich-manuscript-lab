# 0014: Separate blind generation from scoring

Date: 2026-08-31

## Status

Accepted for E-008 before implementation, generation, scoring, or unblinding.

## Context

E-007 perfectly recovered known ADFGX controls after a supplied-width order
search, but its documents, parameters, and widths were exposed. Retrofitting
E-006 or adding more visible variants would overfit the same benchmark. The
next useful question is whether the frozen structural score survives new
sources, new parameters, and an unknown-width search.

## Decision

Acquire eight source works absent from E-005. Generate 96 new transformations
with pycipher components independent of the E-007 transform code, balanced
across widths four through seven. Write public candidates/ciphertexts and
sealed truth separately. Make the scorer consume a scoring-only configuration
which contains no truth location or seeds, and freeze score hashes before
unblinding.

Apply the complete width/order search to a coordinate-pair-position shuffle
control and to every identity-permutation null replicate. Require all nine
gates, including worst-width retrieval, width recovery, mapping-destruction
response, and a search-corrected p-value.

## Consequences

This design tests transfer without pretending to provide cryptographic secrecy
from the local operator. It remains known-payload retrieval because plaintext
candidates are supplied. A pass permits design of a target-side null study,
not target scoring. A failure identifies a width, source, or control boundary
and stops further scaling.
