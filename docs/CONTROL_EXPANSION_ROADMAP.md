# Pre-experiment implementation roadmap

No new manuscript-facing or control-calibration research experiment starts
until all seven lanes below have an implemented, reviewed interface. Unit tests,
schema validation, smoke checks, and dry-runs are software verification and do
not count as research experiments.

## 1. Long-form human no-payload controls

Implement a privacy-minimal collection protocol, immutable UTF-8 payload format,
consent/rights metadata, schema, validator, and manifest path. Collection is
complete only after multiple independent adult contributors supply at least
2,000 groups each under balanced documented conditions. No contributor names,
email addresses, IP addresses, or free-form biographies enter the repository.

## 2. Manuscript-scale hierarchical generators

Implement independently seeded generators for hierarchical cache/renewal,
sectional topic-state, Pitman--Yor/Simon vocabulary growth, page/line slots, and
section-conditioned copy/mutate processes. Each generator must expose its exact
parameters and inverse/audit information where applicable and must produce line,
page, and section records rather than a flat string.

## 3. External-control validation harness

Implement document/family isolation, power and sample-length diagnostics,
multiple-comparison control, serialized replay, and a sealed target boundary.
The harness must accept the human and hierarchical controls without reading a
manuscript transcription.

## 4. Witness-robust measurement adapter

Implement every candidate metric over the five primary transcription lineages
and admissible uncertainty views without merging them. Require page/section
alignment, length-coverage reporting, worst-view conjunctions, and reversible
unitization.

## 5. Sealed target application

Implement a separate command that accepts only a frozen model bundle and a
predeclared witness registry. It must refuse uncalibrated bundles, record a
one-time target run ID, prevent threshold/feature changes, and report
compatibility rather than posterior odds or semantic labels.

## 6. Visual and layout lane

Implement a versioned annotation schema and tool for page regions, lines,
labels, plants, diagrams, stars, vessels, and figures. Preserve canvas
coordinates and annotator provenance. Multimodal evaluation must split by
physical page or larger codicological unit and compare against page-position,
section, and frequency baselines.

## 7. Predictive cipher-hypothesis workbench

Implement an explicit staged pipeline for segmentation, nomenclator,
homophonic/substitution, alphabet selection, progression, and transposition.
Every candidate must be reversible, freeze mappings before held-out scoring,
record rejected candidates, and test new page-level predictions against
structure-preserving nulls. Readable fragments remain inadmissible evidence.

## Ordering

Lanes 1 and 2 supply the controls required by lane 3. Lane 3 must be complete
before lanes 4 and 5 can be scientifically exercised, although their interfaces
can be built and tested with synthetic fixtures. Lanes 6 and 7 are independent
evidence channels and can be implemented in parallel after the control data
contract is stable.

