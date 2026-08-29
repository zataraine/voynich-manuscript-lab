# Research protocol

One book can support strong structural observations but invites accidental
overfitting and persuasive stories. The lab therefore advances claims by gates.

## Phase gates

### 0. Intake and audit

Pass when originals have verified hashes, rights/provenance are recorded, page
order is explicit, and the supplied transcription encoding has a written grammar.

### 1. Representation

Pass when page, region, line, sequence, separator, alternative, and uncertainty
records are reversible to the supplied data. Measure transcription disagreements
or ambiguities before collapsing them.

### 2. Descriptive structure

Characterize inventory, position, adjacency, repetition, sequence lengths, page
variation, layout, and image classes without semantic labels. Publish counts and
confidence intervals, not only plots.

### 3. Null tests and controls

Test whether apparent structure survives controls that preserve appropriate
marginals: shuffled page labels, within-page sequence permutation, circular
shifts, frequency-matched synthetic sequences, block bootstrap, and duplicated
page detection. Choose the null before viewing the target statistic when possible.

### 4. Multimodal association

Align images and nearby text only after geometric provenance is stable. Evaluate
on held-out pages. Compare learned models with page-position, section, frequency,
and nearest-neighbor baselines. A visual association does not establish a word
meaning, taxonomy, or translation.

### 5. Explanatory hypotheses

Pre-register a prediction that distinguishes the hypothesis from alternatives.
Specify success, failure, and ambiguity thresholds. Prefer hypotheses that make
new page-level predictions over post-hoc interpretations.

### 6. Semantic or linguistic claims

Require converging independent evidence and an explicit account of competing
explanations such as scribal convention, layout templates, ciphers, cataloguing,
generated text, or transcription artifacts. Pretrained embeddings can suggest
probes but cannot serve as ground truth.

## Experiment record

Before a run, add an entry to `research/HYPOTHESES.md` and create a config derived
from `config/experiments/base.yaml`. Afterward, record:

- question and preregistered hypothesis ID;
- source/transcription manifest hashes;
- code commit or `dirty` plus diff hash;
- exact config and random seed;
- split group and assignment artifact;
- runtime, device, package snapshot, and model revisions;
- primary metric and confidence interval;
- null/baseline results and multiple-testing correction;
- output paths, failures, and interpretation limits.

Runs are immutable. A rerun receives a new run ID and references the predecessor.

## Claim levels

Use these labels in `research/CLAIMS.md`:

1. `observation`: directly recoverable from audited data.
2. `association`: statistical relationship with stated uncertainty and controls.
3. `mechanistic-hypothesis`: a falsifiable explanation with novel predictions.
4. `semantic-hypothesis`: a tentative meaning/reading proposal.
5. `supported-claim`: replicated or independently convergent evidence.

No level is promoted because a result is visually compelling. Record the evidence
IDs, counterevidence, alternatives, and reviewer decision.

## Reproducibility minimum

Set seeds for Python, NumPy, and PyTorch. Record deterministic settings and any
known nondeterministic CUDA operations. Do not imply bitwise cross-device
reproducibility; report numeric tolerances. Unit tests use synthetic fixtures, not
the protected book. The acceptance gate is `./scripts/smoke.sh`.
