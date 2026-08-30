# 0008: Version and benchmark local reviewer profiles

- Date: 2026-08-30
- Status: accepted

## Context

The baseline E-002 reviews reached the correct claim boundary but also invented
unsupported explanations. Qwen suggested leakage without evidence and confused
the three all-witness common pages with a witness sample count. GLM returned a
verdict word instead of an evidential assessment and alleged an unsubstantiated
data discrepancy. These failures do not affect deterministic results, but they
make unattended triage less reliable.

## Decision

Store Qwen and GLM role prompts as tracked, hashed assets. Store a reproducible
Ollama Modelfile for the GLM critic alias and verify that alias in the local-AI
doctor. Add deterministic review facts to bounded packets when similar numeric
fields are easy to confuse. Require reviewers to separate observations from
possible causes and forbid tuning a gate merely to obtain a pass.

Keep the llama.cpp Qwen runtime baseline unchanged. The profile changes affect
review only; local models remain prohibited from computing metrics or receiving
manuscript/corpus text through semantic retrieval.

## Benchmark evidence

The fixed E-002 packet served as the initial regression case. GLM profiles with
`num_predict` set to 768 and 2,048 both exhausted the hidden reasoning allowance
and emitted no schema JSON, so the selected profile has no output cap. The
revised Qwen prompt correctly reported no leakage evidence, separated surface
discrimination from semantic recognition, resolved GC2a versus common-page
counts, and set target effect strength to `none`.

GLM remains a fallible optional critic. Schema validity is necessary but not
sufficient; its review cannot promote an experimental claim.
