# 0033: Uncertainty at frozen learned-unit scales

Date: 2026-10-14
Status: accepted

## Question and acceptance

Do the already-frozen pair-merge scales expose descriptive uncertainty, rather
than only width/count? Require exact synthetic answers, record-boundary reset,
bijective-label invariance, frozen-table replay across all registered views and
merge budgets, explicit missingness, and rejection of corrupted serialized panels.
This is software verification, not a new research experiment.

## Decision

Add optional `learned-uncertainty-v1` panels to each saved learned-unit entry.
New builders always emit training and held-out panels with the same table,
fitted only on training records. Keep the existing core vector and width/count
diagnostics unchanged; historical records lacking this extension remain readable.

Measure empirical Shannon entropy and transition-weighted first-order
conditional entropy in bits. The formula is the standard discrete entropy
definition documented by [SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.entropy.html);
tests also check the joint-minus-context identity independently. Spaces are
erased by the existing tokenizer; transitions reset at each record. Do not
silently substitute within-group or pooled-across-record scope.

## Limits

Bits are per learned unit or eligible transition, not per base glyph. These
are plug-in descriptive estimates of each split, not predictive cross-entropy
under probabilities fitted to training. Unit counts, type counts, base widths,
transition counts and undefined reasons accompany the values. Zero without
transitions is missing, not evidence of predictability. Values across merge
scales have different units and cannot be interpreted as a common entropy rate.

This adds no null calibration, posterior, translation or target access. Broader
finite-size/sparsity recovery and joint missingness gates remain open. Vocabulary
growth is the next missing endpoint; it is not supplied by this change.
