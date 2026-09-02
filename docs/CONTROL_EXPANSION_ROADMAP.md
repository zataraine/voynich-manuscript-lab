# Calibrated mechanism-comparison roadmap

The lab does not estimate the probability that the manuscript is a hoax,
language, or cipher. It tests whether frozen, explicit production mechanisms
can reproduce preregistered observations outside and then, at most once per
frozen bundle, across admissible manuscript representations. The estimand and
interpretive limits are fixed in `docs/MECHANISM_COMPATIBILITY_ESTIMAND.md`.

No new manuscript-facing inference starts until phases 1--6 have passed their
readiness gates. Control-only power studies, replications, simulations, and
negative tests are required development work; they may not read a manuscript
transcription. Unit tests, schema checks, smoke checks, and dry-runs remain
software verification rather than research results.

## Phase 1. Estimand and failure semantics

Freeze the question, mechanism-family registry, admissible conclusions, and
rejection semantics. Compatibility is not identity, decipherment, meaning, or
posterior probability. Failure of one implementation rejects that
implementation over its tested parameter range, not every possible member of a
broad family.

**Ready when:** the estimand contract is machine-addressable from every future
experiment config and reports refuse forbidden probability or semantic labels.

## Phase 2. Human and documentary controls

Revise the long-form human protocol using the public Gaskell--Bowern corpus for
pilot variance and power planning. Keep intuitive invention, copy/mutate,
slot-table, and self-devised-rule conditions separate. Record typed versus
handwritten-transcribed production, longitudinal sessions, correction handling,
prior Voynich exposure, and coarse relevant experience without collecting
direct identifiers. Add matched meaningful human-production controls so that
production modality cannot become the classifier.

The existing `human-pseudotext-v1` contract is a validated pilot intake format,
not a confirmatory sampling plan. Do not recruit against it until a versioned
successor and an appropriate consent/ethics review are complete.

**Ready when:** a versioned pilot collection packet and validator cover both
no-payload and matched payload arms; pilot balance and exclusions are frozen;
no condition is pooled into a generic "gibberish" class. Confirmatory sample
size cannot be frozen until the phase-4 endpoints exist and is therefore a
phase-6 gate.

## Phase 3. Representation and witness contract

Move the former witness adapter ahead of generator design. Implement reversible
views in which observed marks remain glyphs, blank-delimited strings remain
groups, and gaps remain separators until evidence supports linguistic names.
Views must include primary transcription lineages, uncertainty alternatives,
composite versus decomposed glyphs, certain versus uncertain separators,
space-erased learned units, and preserved line/page/section boundaries. Never
merge witnesses into a vote.

This phase defines measurement interfaces without selecting a view because it
favours any mechanism.

**Ready when:** synthetic fixtures round-trip exactly; all metrics report
coverage and missingness by view; split groups are physical pages or larger;
view choice cannot be changed by a model implementation.

## Phase 4. Frozen joint measurement battery

Implement a compact battery motivated independently of target classification:

- conditional uncertainty at several reversible unit scales;
- learned-unit scale and out-of-group stability;
- vocabulary growth, singleton tail, and recurrence distance;
- adjacent group-identity and cross-separator edge association;
- separator-class and space-erasure sensitivity;
- line/paragraph position effects;
- page, section, and longitudinal drift; and
- compression and contextual-domain measures with length-matched nulls.

Each statistic needs finite-sample bias checks, structure-preserving nulls,
known positive and negative controls, and a declared direction or two-sided
criterion. A single attractive statistic can never decide compatibility.

**Ready when:** the complete battery passes estimator, length, rename,
round-trip, and synthetic recovery tests without reading Voynichese.

## Phase 5. Literature-anchored mechanism controls

Replicate published mechanisms before inventing flexible ones:

1. intuitive human no-payload production;
2. Rugg-style table and grille production;
3. Timm--Schinner-style local self-citation/copy-mutation;
4. the published Naibbe verbose homophonic cipher;
5. natural, constructed, catalogue, formulaic, and abbreviated meaningful
   controls; and
6. classical through polyalphabetic, nomenclator, fractionating,
   transposition, progressive-key, and rotor transforms with known truth.

Only after those replications pass may manuscript-scale cache/renewal,
sectional-state, vocabulary-growth, or other hierarchical generators be added.
Such extensions must have a plausible production interpretation, expose their
parameters and seeds, and be calibrated on controls rather than tuned to the
target.

**Ready when:** independent implementations reproduce their published
headline behaviour within declared tolerance; every family has a deliberately
broken control; generator selection and parameter ranges are frozen.

## Phase 6. External validation and sealed target boundary

Implement contributor/document/family isolation and prospective power for the
now-frozen phase-4 endpoints,
sample-length diagnostics, nested model selection, multiplicity control,
serialized replay, and a target-access barrier. Development and independent
evaluation corpora must remain separate. The harness reports family-specific
failure rather than hiding it in aggregate accuracy.

**Ready when:** the frozen bundle passes all construction and scientific gates
on external controls, replays byte-for-byte, and refuses target access when any
gate fails.

## Phase 7. Preregistered manuscript compatibility run

A separate command accepts only a calibrated immutable bundle, a predeclared
witness/view registry, and a new target-run identifier. It cannot alter
features, thresholds, mechanism ranges, splits, or multiplicity corrections.
It reports compatibility or incompatibility with the tested implementations,
including worst-view and family-specific uncertainty. It never reports
posterior odds, a translation, or a semantic label.

One bundle receives one target application. A later application requires a
new externally calibrated bundle and a new preregistration, not retuning the
failed bundle.

## Parallel evidence programmes

These are required lab capabilities but are not global blockers for
control-only work:

### Visual and layout evidence

Use versioned annotations for page regions, lines, labels, plants, diagrams,
stars, vessels, and figures, preserving canvas coordinates and annotator
provenance. Split by physical page or larger codicological unit and compare
against page-position, section, and frequency baselines.

### Predictive numerical cryptanalysis

Represent every reversible segmentation numerically and support explicit
stages for alphabet/unit selection, nomenclators, homophonic substitution,
polyalphabetic and progressive keys, fractionation, and transposition. Search
may be exhaustive where the keyspace is genuinely bounded. A candidate must
predict held-out pages or known control truth under a frozen mapping and beat
structure-preserving nulls. Readability and local language-model scores are not
verifiers.

## Implementation order

Phases 1, 2, and 3 come first. Phases 4 and 5 then co-develop against external
controls, followed by phase 6. Phase 7 is the only manuscript-facing inference.
The visual and numerical-cryptanalysis programmes can be built in parallel once
the phase-3 representation contract is stable.
