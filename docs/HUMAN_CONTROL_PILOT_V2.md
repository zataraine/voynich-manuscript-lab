# Human production control pilot v2

## Status and purpose

This is a target-blind pilot design, not an invitation to recruit and not a
confirmatory experiment. Human or institutional review appropriate to the place
and manner of recruitment must occur before anyone participates. The pilot
tests feasibility, transcription, burden, and between-contributor variance. It
does not classify the manuscript and cannot determine confirmatory sample size
before the phase-4 endpoints are frozen.

The design extends the useful part of Gaskell and Bowern's short handwritten
exercise: real people can produce highly non-random text without intending a
message. Their public corpus informs this pilot but is not treated as ground
truth for every kind of meaningless production.

## Factorial assignment

Each contributor is randomly assigned exactly one cell. The factors are never
collapsed during analysis.

### Payload intention

- `no_intended_payload`: produce marks or groups without intending them to
  communicate propositions, instructions, narrative, labels, or data.
- `intended_payload`: produce material intended to preserve recoverable
  information. The validator records the attestation; it cannot verify meaning.

### Production strategy

- `freeform`: continuously invent material. In the intended arm, compose
  original meaningful material; in the no-payload arm, invent as you go.
- `copy_mutate`: repeatedly copy and manually alter available material. The
  intended arm paraphrases or transforms a declared public-domain source while
  preserving information; the no-payload arm reuses only its own invented
  material and carries no source message.
- `supplied_slots`: use an abstract supplied prefix/middle/suffix or record
  template. The intended arm fills a declared template with information from a
  public-domain source; the no-payload arm fills a structurally matched template
  without assigning meanings.
- `self_devised_rule`: invent and follow a manual rule. The intended arm applies
  it to declared plaintext; the no-payload arm applies a content-free rule.

The intended arms are controls for payload-bearing composition, copying,
template use, and hand-executable encoding—not presumed models of Voynichese.

### Modality

- `typed`: work in a plain-text editor with predictive text, autocomplete,
  spell-check, macros, and AI assistance disabled.
- `handwritten_transcribed`: work in pen on supplied pages. Preserve the private
  capture and make a double-entry Unicode transcription. Record corrections and
  uncertain readings; never publish handwriting merely because the transcript
  is releasable.

The pilot has 16 cells: two intentions by four strategies by two modalities.
Its feasibility target is two independent contributors per cell, 32 total, one
submission per contributor. This number is not a power claim and cannot be used
as the confirmatory sample size. The 32 factor cells are frozen in
`config/controls/human-production-pilot-allocation-v2.yaml`; a submission must
match its assigned slot.

## Blinding and exposure

Do not show contributors manuscript images, EVA, Voynich statistics, generated
examples, earlier submissions, or study outcomes. Record pre-existing exposure
as `none`, `name_only`, `general`, or `technical`; do not exclude it silently.
Assignment instructions contain only the contributor's own cell.

## Longitudinal structure

Each submission contains 2,000--20,000 groups, at least eight pages and 64
lines, created over at least two sessions. Sidecar records use page ranges and
coarse gaps rather than wall-clock timestamps. Sessions and pages are physical
or task boundaries, not inferred linguistic units.

Every factor cell uses the same 26 lowercase Latin symbols `a` through `z`, one
ASCII space between groups, and no punctuation, digits, uppercase letters or
diacritics. This deliberately prevents alphabet choice from trivially revealing
the intended/no-payload assignment. It is a matched production control, not an
assumption that Voynich glyphs are letters.

## Privacy and source layers

- Use random contributor, assignment, and submission identifiers.
- Do not collect names, contact details, IP addresses, precise locations,
  demographic narratives, keystrokes, or device fingerprints in the research
  repository.
- Keep the original typed file or handwriting capture immutable in the private
  raw layer. Handwriting may be identifying and is never committed.
- Store the strict analysis transcript in the interim layer. Typed transcripts
  must be byte-identical to their raw capture. Handwritten transcripts use two
  independently preserved entries followed by adjudication; all three hashes
  remain in the sidecar or validation report.
- Store only coarse experience bands needed to assess contamination and task
  strategy.

Public-domain or participant-owned meaningful source material must be declared.
The source is independently manifested; do not embed copyrighted text in the
metadata sidecar.

## Validation and limitations

After privately placing the source capture, transcript, and sidecar, run:

```bash
./scripts/lab controls validate-pilot-submission \
  data/raw/controls/human-production-pilot/SUBMISSION.yaml
```

Validation checks schemas, hashes, path confinement, page/session coverage,
factor consistency, typed identity, and structural limits. It does not verify
intention, meaningfulness, source rights, honest completion, or consent.

Failed source captures are never edited. Corrections produce a new submission
identifier and hashes. Pilot exclusions, withdrawals, refusals, burden, and
validation failures are reported without retaining unnecessary personal data.

## Frozen exclusions

Exclude a submission from endpoint estimation, while retaining its disposition
in the non-content collection audit, only for a reason fixed here:

- withdrawal before the declared freeze;
- ineligible or non-voluntary participation;
- duplicate contributor or allocation slot;
- use of prohibited generation assistance or exposure to target materials
  during the task;
- factor assignment not followed;
- missing source rights or consent;
- irrecoverable raw-capture, hash, transcription, session, or format failure; or
- failure to reach the frozen length/session requirement.

Do not exclude material because it looks meaningful, meaningless, language-like,
Voynich-like, unusually repetitive, statistically inconvenient, or difficult
for a model. Pre-existing technical Voynich exposure is reported as a stratum
and sensitivity exclusion, not silently removed. Every assigned slot—including
refusal, withdrawal and validation failure—remains in the feasibility
denominator.
