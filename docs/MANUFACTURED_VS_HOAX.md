# Manufactured-language versus nonsemantic-text study

## The question we can actually test

“Manufactured language” and “hoax” are not statistical opposites. A meaningful
constructed language, a cipher over meaningful plaintext, a mnemonic system,
and deliberately meaningless pseudo-text can all be regular. Conversely, a
meaningful text can look locally noisy after encipherment. Sequence statistics
alone do not observe meaning.

This study therefore uses two explicit mechanism classes:

- **payload-bearing constrained systems**: controls in which a stable source
  message passes through a constructed grammar or reversible transform; and
- **nonsemantic generators**: systems that generate or copy/mutate forms without
  a stable message, even when their output is highly structured.

A literal posterior probability is deferred until both classes have multiple
independent calibrated generators and explicit prior weights. The first study is
a mechanism-elimination test: it asks which simple nonsemantic mechanisms fail
to reproduce held-out Voynichese structure.

## Preregistered pilot: H-001 / E-001

The pilot uses the ZL3b IVTFF/EVA witness. Only paragraph loci on pages labelled
Currier A or B are included. Physical pages are stratified by Currier label,
hand, and section before a seeded 75/25 train/held-out split. No adjacent crop,
alternate witness, or derived sequence crosses that boundary.

The `eva-stable-groups-v1` transform removes IVTFF comments and control marks,
joins physical intrusion markers, splits firm and uncertain group boundaries,
and excludes every resulting group containing ambiguity or non-ASCII markup.
The raw source is never changed, and excluded counts are reported.

Primary held-out measurements are:

1. character trigram gain over a unigram model, in bits per symbol;
2. group bigram gain over a unigram model, in bits per group; and
3. the rate at which a group is within edit distance one of a recent group on
   the same held-out page.

Each is compared with 512 seeded replicates from five explicit families. One
worker process owns each family so the five families run concurrently without
GPU contention:

- within-page group shuffle;
- within-group symbol shuffle;
- global frequency-weighted group resampling;
- IID symbol sampling with observed group lengths; and
- a local copy/mutate pseudo-text generator.

The one-sided tests ask whether the observed positive structure exceeds the
generated distribution. Holm correction covers every family/metric comparison.
A family is only provisionally incompatible when the adjusted value is below
0.05 in the preregistered direction. Failure to reject means “compatible with
these measurements,” not “the mechanism is true.” Rejection of every current
family still does not demonstrate meaning.

## Local-AI role

Deterministic Python computes every split, model, null, statistic, p-value, and
correction. The local stack is used sequentially after the result exists:

1. lexical retrieval finds methodological passages in approved lab notes;
2. Qwen3-Embedding embeds only those notes and the methodological query;
3. rank fusion and Qwen3-Reranker select a bounded reference packet; and
4. Qwen3.6 performs a schema-constrained review of metrics, controls, leakage,
   confounds, limitations, and escalation need.

No manuscript transcription or Voynichese is sent to the pretrained embedding
or reranking models. Qwen's review is an auditable review artifact, not a metric
and not a state transition. GLM remains an optional adversarial review after a
result survives controls.

## Long-run commands

From WSL at the repository root:

```bash
./scripts/lab experiment init
./scripts/lab experiment register \
  config/experiments/E-001-manufactured-vs-hoax.yaml
./scripts/lab experiment execute E-001-manufactured-vs-hoax -- \
  ./scripts/run snakemake \
    --snakefile workflow/mechanism-study.smk \
    --profile workflow/profiles/local
./scripts/lab experiment verify
```

The runner supplies immutable logs, leases, heartbeats, failure state, and a
clean resumption boundary. Snakemake serializes the embedding, reranking, and
Qwen phases through the shared `gpu` and `local_ai` resources. Outputs live in
`artifacts/runs/E-001-manufactured-vs-hoax/` and are never overwritten.

Dry-run the complete DAG without starting inference:

```bash
./scripts/run snakemake --snakefile workflow/mechanism-study.smk \
  --dry-run --cores 12 --resources gpu=1 local_ai=1
```

## Route to calibrated odds

The next gate adds independently sourced positive and negative controls:

- known payload-bearing natural and constructed texts matched by length;
- Naibbe ciphertext with hidden but recoverable plaintext;
- more than one nonsemantic copy/mutate, table, and procedural generator;
- multiple IVTFF witnesses and reversible unitizations; and
- leave-one-generator-family-out calibration.

Only after those controls pass can a likelihood-free classifier or hierarchical
Bayesian model provide probability estimates. Those estimates must be published
as a sensitivity table over explicit priors and generator coverage, not as one
context-free number. Later multimodal tests can add held-out image/text
association evidence, but illustrations are not semantic labels by assumption.
