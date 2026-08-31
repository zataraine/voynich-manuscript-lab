# Representation-robustness protocol

## Purpose

This protocol tests whether descriptive measurements of the manuscript survive
admissible transcription choices. It does not select a best transcription,
infer a language, translate text, or estimate the probability of a hoax. A
measurement that fails this protocol must not be used as stable evidence in a
later manufactured-text analysis without an explicit witness-dependent model.

## Frozen analysis population

Use the Q-011 witness lattice and the official STA1 comparison files registered
in `config/corpora/ivtff-witnesses.yaml`. The five non-synthetic analysis views
are CD2a, FG2a, GC2a, IT2a, and ZL3b. They are lineage representatives, not five
independent human votes: IT2a's Takahashi/LSI ancestry remains explicit. VT0e
and RF1b are excluded from primary gates because VT0e is a related derivative
and RF1b is synthetic. They may appear only as labelled diagnostics.

The primary STA1 variants are CD2a_0, FG2a, GC2a_0, IT2a, and ZL3b. CD2a_1 and
GC2a_1 are conversion-sensitivity views. Comparisons use only canonical loci
present in all five primary views. A page is eligible only when every primary
view and every ZL3b uncertainty view contains at least 20 groups and 100 STA1
symbols after the common-locus restriction. This minimum-across-views rule is
fixed before measurement so representation choice cannot select the pages.

## Reversible unitization

STA1 codes are symbols, not characters. Two-character STA1 codes remain one
symbol. Firm `.` separators always end a group. An uncertain `,` separator is
either a group boundary (`split`) or no boundary (`join`) according to the
declared view. Physical locus boundaries are hard sequence boundaries, so no
n-gram or adjacency spans loci. Paragraph markers, free comments, and text tags
are excluded exactly as in Q-011; drawing interruptions terminate a group.

Alternative readings are resolved as the first branch, last branch, or a
single opaque `<ALT>` symbol. The primary view uses `first` plus `split`, which
matches the documented preferred-first convention while conservatively
retaining a possible space. Unreadable single and multiple marks remain atomic
`<UNK1>` and `<UNKN>` symbols. Ligatures remain atomic, losslessly labelled STA1
symbols. No uncertain material is silently deleted.

The ZL3b uncertainty ensemble is the Cartesian product of alternative policy
`first`, `last`, or `opaque` and uncertain-space policy `split` or `join`.
Conversion sensitivity compares CD2a_0 with CD2a_1 and GC2a_0 with GC2a_1 under
the primary uncertainty policy.

## Frozen feature panel

Every feature is computed once per eligible page. Symbol-sequence features use
only within-locus transitions; group recurrence also resets at a locus.

1. `symbol_entropy_normalized`: unigram entropy divided by log2 alphabet size.
2. `symbol_conditional_entropy_normalized`: next-symbol conditional entropy
   divided by log2 alphabet size.
3. `symbol_repeat_rate`: fraction of valid adjacent symbol pairs that are equal.
4. `symbol_bigram_type_ratio`: distinct within-locus bigrams divided by all
   within-locus bigrams.
5. `group_length_mean`: arithmetic mean group length in STA1 symbols.
6. `group_length_cv`: population standard deviation divided by mean group
   length.
7. `group_type_token_ratio`: distinct groups divided by group count.
8. `group_hapax_ratio`: groups occurring once divided by distinct groups.
9. `adjacent_group_repeat_rate`: equal adjacent groups divided by valid
   within-locus adjacent group pairs.
10. `window20_group_recurrence`: fraction of groups repeated among the prior 20
    groups in the same locus.

The order-sensitive subset is features 2, 3, 4, 9, and 10. Feature definitions,
the panel, and thresholds may not change after the preregistration commit. A
separate future experiment is required for additions.

## Stability measurements

For each feature, define its scale as the interquartile range of the per-page
median across the five primary views. A zero or non-finite scale automatically
fails the feature. Calculate:

- every pairwise Spearman page-rank correlation among primary witnesses;
- the median absolute paired difference divided by the frozen feature scale;
- the same quantities for each CD/GC conversion pair; and
- the same quantities for every pair of the six ZL3b uncertainty views.

Bootstrap eligible pages 1,000 times with seed 20260901. Report percentile 95%
confidence intervals for every primary witness pair and for the worst-pair
correlation. The bootstrap is descriptive; its lower bound is an additional
stability gate, not a null-hypothesis p-value.

The primary null independently permutes page labels of each non-reference
witness 1,024 times with seed 20260902, recomputing each feature's median
primary-pair Spearman correlation after the complete comparison. Compute
one-sided empirical p-values and apply Holm correction across all ten frozen
features. This asks whether aligned pages agree more than unrelated pages; it
does not test whether text is meaningful.

## Per-feature gates

A feature is representation-stable only when all conditions hold:

- at least 40 pages are eligible and no more than 5% of eligible page/view
  values are non-finite;
- worst primary-witness Spearman rho is at least 0.80, and its bootstrap 95%
  lower bound is at least 0.70;
- maximum primary median normalized difference is at most 0.25;
- worst CD/GC conversion-pair rho is at least 0.95 and maximum conversion
  median normalized difference is at most 0.10;
- worst ZL3b uncertainty-view rho is at least 0.90 and maximum uncertainty
  median normalized difference is at most 0.15; and
- the Holm-adjusted page-label permutation p-value is at most 0.05.

H-010 passes only if at least four of ten features pass every gate and at least
two passing features are from the frozen order-sensitive subset. Otherwise the
feature panel is inadequate for a representation-robust return to Q-002.

## Reporting boundary

Publish every feature and every failed gate, including negative and ambiguous
results. The report must identify the source/lattice hashes, preregistration and
code revisions, config hash, seeds, environment, device, eligible pages, and
output paths. Passing authorizes a later control-calibrated experiment using
only the stable subset. It does not support a language, cipher, authorship,
meaning, constructed-language, or hoax conclusion by itself.
