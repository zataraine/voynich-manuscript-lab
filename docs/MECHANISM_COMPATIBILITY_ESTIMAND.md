# Mechanism-compatibility estimand

## Question

For a frozen production-mechanism implementation, parameter domain,
representation registry, measurement battery, and external calibration, are the
manuscript observations incompatible with the distribution that implementation
produces?

This is an implementation-level falsification question. It is deliberately not:

- the probability that the manuscript is meaningful, meaningless, a hoax, a
  constructed language, or a cipher;
- the probability that a mechanism is historically true;
- a translation or identification of an underlying language; or
- evidence that every untested member of a rejected mechanism family fails.

## Objects

- `M`: an exact versioned implementation and frozen parameter distribution;
- `R`: a registry of reversible observation views, with no preferred witness;
- `T`: a frozen joint measurement battery;
- `C`: independent external controls and their contributor/document/family
  groups;
- `A(M, R, T, C)`: the acceptance region calibrated without target access; and
- `Y_r`: the manuscript measurement vector under view `r` in `R`.

`M` is compatible only if its preregistered joint criterion accepts every
required `Y_r` or the prospectively declared worst-view aggregation. The exact
criterion, finite-sample correction, multiplicity procedure, and missing-data
rule must be frozen before target access.

## Interpretation

- **Incompatible:** the tested implementation over its tested parameter domain
  fails. Broader historical or mathematical families remain open unless the
  frozen domain exhausts them.
- **Compatible:** the implementation has not been rejected by this battery. It
  is not thereby true, meaningful, historically plausible, or unique.
- **Indeterminate:** calibration, power, view coverage, or robustness gates
  failed. No target interpretation follows.

Comparative rankings may be reported only among implementations that passed the
same external gates. They are descriptive compatibility scores, never posterior
probabilities, unless explicit defensible priors and a validated likelihood
model are established in a separate future protocol.

## Why numerical search still matters

Every view ultimately becomes exact integer sequences, boundary arrays, and
page/section indices. That permits exhaustive search for genuinely bounded
cipher components, constraint solving, finite-state composition, Bayesian or
likelihood-free parameter search, and GPU-scale simulation.

Unlike a password hash, however, the manuscript supplies no known verification
function. A search score learned from the target can reward coincidental
readability or structural mimicry. External known-truth ciphers, broken
controls, held-out physical units, and the frozen acceptance region provide the
missing verifier. They make large numerical searches useful by giving wrong
answers a defined way to fail.

## Target-access rule

Exploratory description of source quality and representation coverage is kept
separate from mechanism scoring. A calibrated bundle receives one immutable
target run. Feature changes, threshold changes, parameter expansion, or view
selection after that run create a new bundle that must repeat external
calibration before any later target application.
