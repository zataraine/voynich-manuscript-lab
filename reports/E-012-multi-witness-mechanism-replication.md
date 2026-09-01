# E-012 multi-witness mechanism replication

## Outcome

H-012 passes. All eight effects frozen from E-001 remain strictly positive in
all ten preregistered transcription and uncertainty views. For every
view/effect comparison, none of 512 null replicates equalled or exceeded the
observed value, giving the minimum one-sided empirical p-value of 1/513 =
0.001949. The worst-view conjunction p-value is therefore 0.001949 for each
effect and its Holm-adjusted value is 0.015595.

This establishes that the selected held-out character-order, group-order, and
local-copy effects are not peculiar to E-001's EVA rendering, a preferred
witness, or one treatment of uncertain readings and spaces. It does not show
that the text has meaning, identify a language or cipher, estimate hoax odds,
or distinguish payload-bearing construction from structured nonsemantic text.

## Corpus and integrity controls

The run used 2,168 common paragraph loci on all 131 eligible Currier A/B pages.
The shared physical-page split placed 99 pages in training and 32 in held-out
evaluation, with no overlap. Five primary STA1 witnesses (CD2a, FG2a, GC2a,
IT2a, and ZL3b) and five additional ZL3b ambiguity/space views supplied ten
separate replication series.

The atomic STA1 transport contained 236 symbols and round-tripped every group.
All views had identical page sets, the split was complete and disjoint, and an
order-preserving bijective symbol relabelling changed no required metric beyond
the frozen `1e-12` tolerance. Every integrity gate passed.

## Replicated effects

| ID | Null family | Measurement | Effect range across ten views | Weakest view | Holm conjunction p |
|---|---|---|---:|---|---:|
| R1 | within-page group shuffle | group-bigram gain | 0.1515–0.1933 bits/group | ZL3b first/join | 0.015595 |
| R2 | within-page group shuffle | local-copy rate | 0.0167–0.0278 | FG2a | 0.015595 |
| R3 | within-group symbol shuffle | character-trigram gain | 1.2435–1.3273 bits/symbol | FG2a | 0.015595 |
| R4 | within-group symbol shuffle | local-copy rate | 0.2955–0.3491 | GC2a | 0.015595 |
| R5 | global intact-group resample | group-bigram gain | 0.5360–0.6002 bits/group | FG2a | 0.015595 |
| R6 | global intact-group resample | local-copy rate | 0.1033–0.1252 | GC2a | 0.015595 |
| R7 | IID symbol/length matched | character-trigram gain | 1.5973–1.6623 bits/symbol | FG2a | 0.015595 |
| R8 | IID symbol/length matched | local-copy rate | 0.3575–0.4215 | GC2a | 0.015595 |

These are observed-minus-null-mean effects on pages excluded from model fitting.
Each row is a conjunction: the maximum raw p-value over all ten views was
corrected together with the other seven rows. No witness was merged, averaged,
selected, or calibrated after inspection.

## Mandatory copy/mutate diagnostic

The strong structured nonsemantic comparator remains unresolved. In every view,
the manuscript has greater character-trigram gain than copy/mutate pseudo-text
(effect 0.975–1.217 bits/symbol), but copy/mutate has substantially greater
group-bigram gain (manuscript-minus-null effect -2.904 to -2.595 bits/group) and
local-copy rate (-0.306 to -0.269). Thus E-012 robustly rejects the four simpler
null mechanisms on their frozen dimensions while still failing to reject a
plausible family of locally generated, nonsemantic structured text.

## Provenance and verification

- Preregistration commit: `ba85a4c3cc0715728080c3d7b3e86d6e801b5b88`.
- Clean run implementation: `d9cec37138859ef7c27b74f01b106304afb2709c`.
- Source lattice SHA-256: `0988585945ac0740900af4398059663456a5a61559c2726b775972fd3f982634`.
- Source manifest SHA-256: `76db756b0cd15bbe9a65055447757ae0590690ad64dc20e2f51065cb49537ae8`.
- Result SHA-256: `58110e686f8f19648a6aef348f9ed5b97b1d7a23ca9a90d541c511392ada466e`.
- Split SHA-256: `d67879788120484439e654cd0a600d45000dae471bb3df58571f4ad98d46c10f`.
- Symbol-map SHA-256: `31c8334d92b28ff5eebcc240716630ea98227cb9a121633cc7812bb35529bd97`.
- Seed 20260906; 512 replicates per null family and view; 12 CPU workers;
  runtime 692.25 seconds.
- The pre-run full gate passed 109 tests, all workflow dry-runs, machine
  diagnostics, and local-AI health checks. No LLM review supplied evidence.

## Consequence

The E-001 effects are now sufficiently transcription-robust to justify one
external-control campaign. The next experiment should freeze this eight-effect
signature and measure it, unchanged, on physically page-like samples from
known natural prose, known cipher systems, deliberately generated nonsense,
and multiple copy/mutate or procedural-text mechanisms. Training and threshold
selection must use only those controls. Voynichese remains sealed until the
control panel demonstrates out-of-family discrimination and calibrated error;
otherwise no manufactured-versus-nonsemantic classification or odds are
permitted.
