# Long-form human pseudo-text control protocol

## Status

`human-pseudotext-v1` is a validated pilot intake format, not an approved or
powered confirmatory collection plan. Do not begin recruitment against this
version. The successor must be informed by a target-blind power analysis of the
public Gaskell--Bowern controls and add matched meaningful production, separate
typed and handwritten-transcribed modalities, longitudinal session boundaries,
correction handling, prior-exposure screening, and coarse relevant experience.
The public controls can inform a pilot, but confirmatory sample size must wait
for the frozen measurement endpoints. See `docs/CONTROL_EXPANSION_ROADMAP.md`.

## Purpose

This protocol collects long sequences intentionally produced without a semantic
message. The resulting material is a negative control for computational method
development; it is not a psychological, linguistic, or artistic assessment of
the contributor. A declaration of no intended payload documents the production
task but cannot prove that no reader will perceive patterns or meaning.

No Voynich image, transcription, glyph inventory, statistic, or manuscript
claim is shown to contributors. That separation prevents target imitation.

## Participation boundary

- Contributors must be adults and participate voluntarily.
- Do not collect names, email addresses, IP addresses, precise locations,
  demographic narratives, medical information, or handwriting samples.
- Assign a random contributor ID outside the payload. One contributor may make
  multiple submissions, but the shared contributor ID keeps all of them in one
  future train/evaluation split.
- The repository templates are not a substitute for institutional ethics,
  privacy, employment, or contract review when one is required.
- Contributors may withdraw before the stated freeze date. Once a submission is
  irreversibly published under CC0 or included in a hash-identified public
  release, withdrawal may no longer be technically or legally possible.

The default template is `private-research-only`. Public redistribution requires
the contributor to make a separate informed rights choice. CC0 is irrevocable
and should not be selected casually; its canonical terms are at
<https://creativecommons.org/publicdomain/zero/1.0/>.

## Conditions

Assign conditions before collection and balance them across contributors:

1. `freeform`: invent groups continuously without intending a message or using
   a fixed table;
2. `copy_mutate`: repeatedly reuse and manually alter previously invented
   groups without a plaintext source;
3. `manual_slot`: construct groups by hand from a supplied abstract
   prefix/middle/suffix table; or
4. `self_devised_rule`: invent and follow a documented mechanical rule that
   carries no plaintext payload.

Do not use an LLM, text generator, cipher program, random-number generator,
dictionary, existing book, song, prayer, or other source text. A plain-text
editor is allowed. Spell-check, autocomplete, and predictive text must be off.
Short accidental natural-language fragments do not invalidate a submission,
but intentionally embedding a message does.

## Payload format

The payload is byte-preserved UTF-8 plain text:

- one non-empty physical line represents one generated line;
- groups are separated by exactly one ASCII space;
- one empty line separates pages;
- tabs, leading/trailing spaces, repeated spaces, NULs, byte-order marks, and
  control characters other than CR/LF are prohibited;
- a group contains 1--64 Unicode code points and no whitespace;
- target length is 2,000--20,000 groups, at least 64 lines and eight pages;
- each page contains at least four non-empty lines.

Do not normalize spelling, Unicode, punctuation, or line endings after receipt.
Corrections create a new submission ID and new SHA-256 rather than overwriting
the original.

## Collection procedure

1. Generate random `submission_id` and pseudonymous `contributor_id` values.
2. Assign one condition without showing results from earlier submissions.
3. Provide only this protocol and the condition-specific instruction sheet.
4. Receive the payload and metadata sidecar through a private channel.
5. Store both under `data/raw/controls/human-pseudotext/`; never commit them
   until rights, privacy, and release scope have been reviewed.
6. Run:

   ```bash
   ./scripts/lab controls validate-submission \
     data/raw/controls/human-pseudotext/SUBMISSION.yaml
   ```

7. Resolve validation failures by requesting a new version, not editing raw
   bytes. After acceptance, add the exact files to a tracked source manifest.

Validation confirms format, metadata, path confinement, size, and hashes. It
cannot verify the contributor's intention or attestations.

## Minimum corpus target

Before any research test, obtain at least twelve independent contributors and
24 accepted submissions, with at least four submissions in each condition and
no contributor appearing in both development and final evaluation partitions.
Freeze contributor-level splits before feature fitting. Report refusals,
withdrawals, exclusions, and failed validations without retaining unnecessary
personal information.
