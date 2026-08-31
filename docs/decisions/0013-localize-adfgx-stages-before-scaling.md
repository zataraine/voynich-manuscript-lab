# 0013: Localize ADFGX stages before scaling

Date: 2026-08-31

## Status

Accepted for E-007 before implementation or execution.

## Context

E-006 passed six of eight aggregate gates and retrieved eight cipher families,
but ADFGX missed both family minima even under same-family calibration. ADFGX
creates coordinate pairs before transposing the coordinate stream. Treating
adjacent final-ciphertext symbols as coordinate units is therefore structurally
incorrect. More classifier tuning would neither test that explanation nor
produce a reusable analysis primitive.

## Decision

Factor ADFGX into independently reversible Polybius and columnar stages.
Freeze three widths, including a ragged case, and an independent known vector.
Given a hypothesized width, enumerate every hidden column order and measure
bidirectional consistency between recovered coordinate pairs and each
candidate plaintext. Test fractionation, transposition, and composition
separately, with exact oracles, reversible Pynini maps, wrong-width controls,
tie-safe ranks, and within-score identity permutations.

Use one segment per source document to avoid same-document duplicates and keep
the exhaustive test bounded. Do not use embeddings or language models to
score text. Add a compiled kernel only if it exactly matches the reference
implementation.

## Consequences

A failed stage is still actionable: it identifies where the representation or
inversion is wrong and prevents another large campaign. A pass yields a
key-agnostic structural solver for known fractionating controls and a reusable
stage/FST interface. It does not authorize target scoring. Any later width
scan over manuscript data must preregister the unitization, widths, correction
for multiple comparisons, and structure-preserving nulls.
