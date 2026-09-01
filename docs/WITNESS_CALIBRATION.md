# Cross-fitted witness calibration protocol

## Question

E-011 asks whether the witness-dependent magnitudes exposed by E-010 are stable
measurement offsets/scales that can be estimated without using the evaluated
page. It does not choose a preferred transcription, create a consensus text, or
test whether the manuscript is meaningful.

Method-comparison work distinguishes correlation from agreement: two methods
can preserve ordering while differing materially in scale. E-011 therefore
retains E-010's separate rank and paired-difference gates. See Altman and Bland,
*Measurement in Medicine: The Analysis of Method Comparison Studies* (1983),
DOI `10.2307/2987937`, and Bland and Altman, *Measuring agreement in method
comparison studies* (1999), DOI `10.1177/096228029900800204`.

## Frozen input and split

Use only E-010's immutable `page-features.jsonl`: 131 eligible pages, 13 views,
and the same ten features. Verify its SHA-256 and the E-010 result SHA-256 before
fitting. Preserve the E-010 primary, conversion, and uncertainty view roles.

Order eligible pages by their existing E-010 order and partition them into five
contiguous folds with sizes differing by at most one. Each fold is a held-out
physical-page block. All views and derivatives of a page remain in the same
fold. No random page split is permitted.

## Frozen calibration

For each feature, view, and fold independently:

1. calculate the training-page median and interquartile range using the other
   four folds;
2. fail the view/feature/fold if the IQR is zero or non-finite; and
3. transform held-out values as `(value - training_median) / training_IQR`.

Concatenate only held-out transformed values to form the cross-fitted page
series. No evaluated page contributes to its transform. The transform is
monotone and therefore cannot improve within-view page ranks. Robust
median/IQR calibration is the sole primary method. Mean/standard-deviation or
paired regression may be reported only in a future preregistered experiment.

## Controls

Run both controls before interpreting target gates, using seed 20260903 and the
same five blocked folds.

- Recoverable control: generate 256 latent standard-normal pages and five
  views with independently seeded additive offsets in [-3, 3], positive scales
  in [0.5, 2.0], and Gaussian noise with standard deviation 0.03. Cross-fitted
  calibration must give worst pairwise Spearman rho >= 0.95 and maximum median
  normalized paired difference <= 0.20.
- Broken control: independently permute page identity for four of the five
  recoverable views before calibration. Its median pairwise Spearman rho must
  be <= 0.15. It cannot be substituted for a failed recoverable control.

For the manuscript views, independently permute held-out page labels of every
non-reference primary view 1,024 times with seed 20260904 after the complete
cross-fitting procedure. Compute one-sided empirical p-values for the median
primary-pair Spearman statistic and apply Holm correction across the ten frozen
features.

## Feature gates

A feature is cross-fitted stable only if every condition holds:

- all 65 view-feature-fold calibration IQRs relevant to the five primary, two
  conversion-alternate, and six uncertainty views are finite and positive;
- worst primary Spearman rho >= 0.80 and its 1,000-replicate page-bootstrap 95%
  lower bound, seed 20260905, is >= 0.70;
- maximum primary median absolute paired difference is <= 0.25 calibrated IQR;
- at least four of five held-out folds have maximum primary median absolute
  paired difference <= 0.35;
- worst conversion rho >= 0.95 and maximum conversion difference <= 0.10;
- worst uncertainty rho >= 0.90 and maximum uncertainty difference <= 0.15;
- Holm-adjusted aligned-page permutation p <= 0.05.

H-011 passes only if both controls pass and at least four of ten features pass
all gates, including at least two from E-010's fixed order-sensitive subset.
Failed features remain excluded. Passing permits a later control-calibrated
experiment to use only cross-fitted values from the passing subset; it does not
permit a language, cipher, semantic, constructed-language, or hoax claim.

## Prohibited responses to failure

Do not exclude GC or another difficult witness, switch to random folds, choose
one transcript, form a modal transcript, tune thresholds, or replace the frozen
calibrator after seeing E-011. Any new calibrator requires a new hypothesis and
experiment ID.
