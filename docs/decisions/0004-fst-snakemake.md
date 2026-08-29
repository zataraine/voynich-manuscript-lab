# 0004: Pynini/OpenFST and Snakemake

- Status: accepted
- Date: 2026-08-29

## Decision

Use Pynini 2.1.7+ as the Python weighted finite-state interface and Ubuntu's
OpenFST command-line tools for inspection/interchange. Use Snakemake 9 as the
workflow DAG and provenance-oriented execution layer. Install Graphviz alongside
OpenFST for visualizing machines.

Pynini is Linux-only in this project because the supported precompiled wheel is
available for CPython 3.12 on manylinux x86-64. Snakemake remains in the locked
project environment. The lab doctor performs a real encode/invert/decode FST
round trip, while the full smoke test parses and dry-runs the repository DAG.

## Consequences

Finite-state cipher stages, alternative tokenizations, weighted witness readings,
and reversible normalization can be composed explicitly. Snakemake can isolate
raw, interim, processed, and experiment layers without relying on notebook order.
Neither tool makes a linguistic assumption or validates a decipherment.
