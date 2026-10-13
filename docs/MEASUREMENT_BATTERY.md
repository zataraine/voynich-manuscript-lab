# Frozen joint measurement battery

`measurement-battery-v2` is target-independent software for comparing explicit
production mechanisms. It is not an experiment, classifier, target score, or
decipherment method. It accepts only reversible numeric records whose symbols,
groups, separator classes, page, section, and line identities have already been
frozen by the representation contract.

V2 corrects boundary, metric-definition, ordering, and learned-unit tie handling
found in the synthetic audit. The v1 config remains historical; the current
loader rejects it so that corrected outputs cannot be labelled as v1. Historical
E-001--E-014 experiments use separate modules and are unaffected.

The adapter accepts only one `(registry, view, alphabet, witness)` scope at a
time. It converts retained non-separator observations to deterministic integer
IDs, turns certain and uncertain separators into distinct typed boundaries, and
keeps the projection hash plus the physical record/page/section/line identity.
Loci with no retained group are reported in coverage as missing records.

## Measurements

The battery reports conditional unit uncertainty, group vocabulary and singleton
tails, recurrence distances, adjacent-group identity, separator-edge association,
line-position association, page and section drift, contextual-domain
information, and observed-minus-shuffled compression. Every rule is two-sided
at this stage: a mechanism may be incompatible because a value is either too
high or too low. It does not select a feature or direction from manuscript
results.

Adjacent-group identity counts only pairs within a record. Cross-separator edge
information measures dependence between the last unit of the left group and
the first unit of the right group. The separate `separator_identity_mi_bits`
measures dependence between separator class and whole-group equality; v1 had
reported that quantity under the edge-information name. Page and section drift
compare successive partitions in first-appearance order, following supplied
physical order rather than sorting arbitrary labels.

Recurrence, contextual blocks, and compression currently use the supplied pooled
record order. Their scope differs from within-record adjacency; the remaining
Phase-4 review must evaluate page resets and layout sensitivity before freezing
the final calibration bundle.

The `layout-measurements-v1` extension now supplies a separate page-reset
compression gain. It uses the same canonical group-equality encoding and zlib
settings, resets compression/shuffling at each page, and weights gains by group
count. A synthetic control where each page is constant but pages differ gives
positive pooled gain and zero page-reset gain. Unique groups give zero gain;
ordered repeated runs give positive gain at both tested lengths. These checks
do not turn compression into a semantic or calibrated mechanism score.

## Ordered vocabulary growth and recurrence

`vocabulary_growth.measure_vocabulary_growth` now adds a separate
`vocabulary-growth-v1` extension to training, held-out and each single-draw null.
It retains one-based first-discovery positions and successive recurrence gaps
for exact numeric group types. With N groups and h=floor(N/2), the growth
endpoint is `(V(N)-V(h))/(N-h)`: new types discovered in the remaining groups
per remaining group. It is undefined for N<2. Curves retain powers-of-two,
half-prefix and final checkpoints; discovery positions recover all prefixes.
No power law is fitted and no unseen vocabulary is estimated.

Pooled results follow supplied record/group order, including cross-page gaps.
Page-reset results reunite each page's records in their relative supplied order
and reset both discovery and recurrence by page. Pages retain first-appearance
order. No-repeat recurrence is explicitly undefined. Serialized summaries replay
from events and are checked against core group/page/gap counts and pooled median
recurrence. Historical records lacking the extension remain readable. Existing
repeated core-null ensembles do not yet include these panels. See ADR 0034.

## Explicit paragraph and session annotations

Numeric records accept optional paired `paragraph_id`/`paragraph_line_index`
and `session_id`/`session_index` fields from projection source metadata. IDs are
opaque; indices are nonnegative integers. Paragraph IDs are scoped by page, and
each annotated record must have a unique relative line position in its paragraph.
Callers must supply line-resolved records for this endpoint. Annotation versions
and provenance belong in the source manifest. Missing annotations remain missing.

`layout_measurements.measure_layout` computes mean group width per record, then
correlates it with relative line position within each eligible paragraph (at
least three positions and variable widths). It averages eligible paragraph
correlations equally, avoiding pooling between-paragraph length offsets.

Longitudinal endpoints aggregate units and group widths by explicit production
session, order sessions by supplied index, and report mean adjacent-session JS
drift and session-position/mean-width Spearman association. Session order is not
inferred from page order, section labels or record ordering. Conflicting or
aliased session indices are rejected. Callers must isolate contributors and
documents and choose larger split groups when warranted.

The extension reports its panel ID, four ordered two-sided criteria, annotation
missingness, eligible/ineligible paragraphs, ordered sessions, and reasons for
undefined zero placeholders. Its output accompanies training, held-out and
each diagnostic null in serialized control records. V1 records without this
optional extension remain readable; new builder outputs include it.

Learned units use a deterministic pair-merge tokenizer. Its merge table is fit
only on supplied training records, frozen, then applied to held-out records.
Merge counts are fixed in the config. The units are compression devices, not
assertions about letters, morphemes, or words.

Equal-frequency pair merges break ties by first occurrence, which is invariant
to any bijection of symbol IDs. The training/held-out interface rejects duplicate
record IDs, overlapping IDs, and overlapping physical pages before fitting.
Larger codicological/document grouping remains the caller's responsibility.

Merge tables are now included alongside their SHA-256 hashes with encoding
`nested-pair-json-v1`. `restore_learned_merge_table` restores JSON arrays to pair
trees; `apply_learned_units` applies them without fitting, and
`expand_learned_units` recovers the exact space-erased numeric sequence with a
reset at each record. The original projections retain group/separator inverses.
Earlier v2 development hashes used Python `repr`; the explicit encoding field
distinguishes the saved-table contract introduced by ADR 0029.

Each new saved-table entry also includes `learned-uncertainty-v1` training and
held-out panels. Both apply the same training-fitted table. They report empirical
unit entropy and transition-weighted order-1 conditional entropy in bits,
erasing spaces and resetting transitions at each record. These are descriptive
plug-in estimates, not training-model predictive cross-entropy. Bits are per
learned unit/transition, not per base glyph; comparisons across merge scales
must not treat them as a common entropy rate. Each panel records record, base
unit, learned unit/type and transition counts, with explicit undefined reasons.
No transitions means an undefined conditional estimate, not measured certainty.
Historical records without these optional panels remain readable. The core
metric vector is unchanged. See ADR 0033 for scope and acceptance checks.

## Nulls and finite samples

The supplied structural nulls shuffle group order, shuffle units inside each
group, or draw independent units from the observed global marginal while
preserving every record, group width, and typed boundary sequence. The last is
therefore length-matched and marginal-matched *in expectation*, not a deceptive
claim that every generated sample retains exact symbol totals. These retain only
the aspects named by their labels; they are diagnostic nulls, not universal null
models.

The battery also emits a fixed increasing complete-record profile at sizes named
in its config. It is a finite-sample sensitivity diagnostic, not a correction:
it makes drift attributable to available record count visible without cutting a
physical record or silently changing boundaries. Undefined quantities return the
declared neutral value `0.0`; all output must be finite. Each future calibration
must report coverage, missingness, source manifest, view registry, seed, null
family, finite-sample profile, and the complete vector in config order.

`measurement_support` records transition, edge, recurrence, page, and section
support and names undefined metrics separately from measured zero values. The
training/held-out and finite-sample interfaces attach this support beside the
numeric vector. A caller using the low-level `measure_core` must also call the
support interface; the numeric zero placeholder alone cannot indicate validity.

## Verification status

Synthetic tests now cover exact entropy, vocabulary, recurrence, adjacency,
binary edge and separator dependence, positive/negative line-position and
context-domain controls, finite-size fair-binary entropy, arbitrary learned-unit
renaming, partition-label renaming, unequal-length null invariants, and split
leakage rejection. These are software checks with known answers, not new
manuscript findings or external mechanism calibration.

All seven registered views and all four configured merge budgets also have
synthetic raw-inverse, learned-unit expansion and JSON replay checks. A repeated
motif compresses under a training-fitted table while an unseen symbol inventory
does not. View checks assert expected differences rather than requiring numeric
invariance when spaces, ligatures, alternatives or glyph scales actually change.

## Serializable control record

`measurement_records.build_control_measurement_record` accepts already supplied
projections, one view specification, declared disjoint page assignments, the
battery, seed, and provenance. It verifies projection replay and emits metrics,
support, missing loci/pages, finite-size profiles and held-out structural nulls
under `schemas/measurement-record.schema.json`. It retains full merge tables,
symbol identities, projection hashes and a digest covering input order and
physical metadata. `canonical_measurement_bytes` validates and serializes the
result reproducibly; altered table hashes, incomplete vectors, non-finite
values and inconsistent battery identity are rejected.

The caller supplies source-manifest path/hash, code revision, working-tree hash,
software-environment hash, device and output path. These are required metadata,
not proof of source integrity: acquisition verification belongs to the run
harness. The source-kind declaration restricts this development interface to
synthetic/external controls but does not implement the future target barrier.
Records contain one draw per diagnostic null, no p-values or compatibility
thresholds, and the fixed decision `not_calibrated`. Immutable file creation,
replay from acquired sources, ensemble budgets and calibration remain run-harness
responsibilities.

Callers can now opt into a repeated core-null diagnostic with `null_replicates=N`.
The `null-ensemble-v1` record retains every replicate seed and raw metric sample,
defined-replicate counts, means, sample SDs and unscaled observed-minus-null
differences. Undefined draws remain `null`, and undefined observed quantities
have no contrast. Serialization recomputes summaries and rejects inconsistent
identity, dimensions or values. There is no variance division or significance
label. The run harness still chooses and freezes its budget and calibration;
the layout panel is not yet included in these ensembles.

Phase 4 remains in progress. Remaining work includes broader view/scale recovery,
calibrated missingness handling, broader estimator-bias and compression controls,
paragraph/session sensitivity across external controls, and the complete joint acceptance
report. Passing the current tests does not mark the phase complete.

The [Phase 4 acceptance audit](PHASE4_ACCEPTANCE.md) lists implemented evidence,
missing endpoints and remaining gates. Learned-scale uncertainty and ordered
vocabulary growth now accompany width/count and type/token diagnostics, but
broader calibration and missingness checks remain open. The audit prevents these gaps from being
mistaken for completed roadmap requirements.

## Boundary

The module has no manuscript loader and refuses to infer a direction, threshold,
or compatibility decision. Phase 5 supplies mechanism controls; Phase 6 supplies
external calibration and the sealed target barrier.
