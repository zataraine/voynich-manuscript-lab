# ADR 0028: Correct measurement definitions before external calibration

## Status

Accepted on 2026-10-10.

## Context

The Phase-4 synthetic audit identified definition and interface defects: pooled
adjacency created edges at record joins; the named edge-information metric
measured separator class versus group identity; partition drift sorted opaque
labels; learned-unit tie breaks sorted integer names; and page-isolated splits
were a caller convention without enforcement. Numeric zero also conflated some
undefined statistics with measured zero values.

## Decision

Use `measurement-battery-v2` for corrected calculations. Preserve the historical
v1 config and refuse to evaluate it using v2 code. Measure adjacency within
records, implement actual edge-unit mutual information, retain separator-class
versus identity information under its own name, order partitions by first
appearance, and resolve learned-unit frequency ties by first occurrence.

Reject duplicate and overlapping record IDs and overlapping pages before
training. Attach explicit support and undefined-metric reasons to joint and
finite-sample outputs. Keep low-level numeric vectors finite for compatibility.
Validate definitions against analytic synthetic positive/negative controls and
arbitrary renaming. Preserve the existing null seed namespace to avoid an
unnecessary change to null draws.

## Consequences

- Battery ID and config hash identify these changed definitions.
- The loader cannot silently replay a v1-labelled calculation with corrected
  code; historical software remains recoverable through Git.
- E-001--E-014 reports and calculations are unchanged: their separate modules
  do not depend on this battery.
- Global recurrence/context/compression scope, larger-unit split policy, and
  the remaining Phase-4 gates still require explicit completion.
- No manuscript measurement or new inference is authorized by these fixes.
