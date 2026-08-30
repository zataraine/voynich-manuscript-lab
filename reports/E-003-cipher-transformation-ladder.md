# E-003 cipher-transformation ladder

## Result

The paired surface/sequence panel retained statistically detectable class signal
when entire cipher families and source documents were withheld, and it responded
to token-order destruction. It did not meet the preregistered transfer thresholds:
the median and worst-family accuracy gates failed, as did the external Naibbe
positive-control gate. The experiment therefore stops before any Voynich target
comparison. It estimates no probability of language, cipher, constructed
language, or hoax.

## Design

- 71 meaningful and 38 human-gibberish source documents produced 284 and 84
  fixed 100-token chunks respectively; complete source documents stayed within
  one fold.
- The same seeded transformation was applied to both labels. The six families
  were identity, document-specific monoalphabetic substitution, three-way
  homophonic substitution, progressive polyalphabetic substitution,
  nomenclator-plus-homophonic substitution, and verbose homophonic encoding.
- Each primary transfer test withheld both unseen documents and one complete
  transformation family from fitting.
- The external Naibbe ciphertexts were never fitting data. Token-order
  destruction preserved each chunk's token inventory, and 32 fixed-fold label
  permutations supplied the null distribution.

## Held-out family transfer

| Withheld family | Balanced accuracy | ROC AUC | Brier score |
|---|---:|---:|---:|
| Identity | 0.6964 | 0.8714 | 0.1481 |
| Monoalphabetic | 0.6640 | 0.8710 | 0.1573 |
| Homophonic | 0.6896 | 0.7617 | 0.2151 |
| Progressive polyalphabetic | 0.5211 | 0.7391 | 0.4623 |
| Nomenclator + homophonic | 0.6447 | 0.8540 | 0.1665 |
| Verbose homophonic | 0.6483 | 0.6913 | 0.2319 |

The mean held-out-family balanced accuracy was 0.6440. The permutation null mean
was 0.4912 and its one-sided empirical p-value was 0.0303. This supports a narrow
observation that the configured panel carries some cross-family class signal. It
does not rescue the failed magnitude gates and does not identify what the signal
represents.

Progressive polyalphabetic substitution was the clearest weakness. Its balanced
accuracy was 0.5211 and its median feature-rank survival was 0.4531. By comparison,
monoalphabetic relabelling preserved feature ranks almost exactly (median
Spearman 1.0), as expected for many symbol-identity-invariant statistics.

## External and destruction challenges

The 80 Naibbe chunks had median meaningful-similarity 0.2419 (interquartile range
0.2197–0.2693), below the 0.55 gate. This shows that the synthetic ladder did not
make the current model transferable to this independent known-payload cipher.
It does not show that Naibbe and the synthetic transforms are equivalent.

Token-order destruction reduced scores by a median 0.0939 and a mean 0.1044;
84.2% of the 284 meaningful chunks had a positive drop. The 0.05 sensitivity gate
passed. This establishes sensitivity to the configured ordering perturbation,
not semantic understanding.

## Gate outcome

| Gate | Threshold | Observed | Outcome |
|---|---:|---:|---|
| Median held-out-family balanced accuracy | at least 0.68 | 0.6465 | fail |
| Worst held-out-family balanced accuracy | at least 0.55 | 0.5211 | fail |
| Naibbe median similarity | at least 0.55 | 0.2419 | fail |
| Token-order destruction median drop | at least 0.05 | 0.0939 | pass |

Overall outcome: **fail; no Voynich target comparison permitted**. The posterior
probability remains null by design.

## Local review

Qwen and the independently prompted GLM critic both assigned effect strength
`none` under the failed-gate policy. Both highlighted the Naibbe failure and
surface-feature dependence. These reviews are advisory summaries; the
preregistered deterministic gate supplies the decision.

## Provenance

- Deterministic code commit: `5027998a4b19a0f7360eb82010108ea64a1a7f52`;
  clean working tree.
- Deterministic result SHA-256:
  `323bbd488e2700e3f77db56c9767cf7f17bc6ac26381eb147b9b362a6949b6e5`.
- Qwen review SHA-256:
  `06aba2d4e8184ffcb5c64749a62c88b31197fff3d2e96bc49e3ee22609571c19`.
- GLM review SHA-256:
  `58b83fe98ede8336420b2020ca4058d4289441010494f1046037a50ca9d18b82`.
- Source archive SHA-256:
  `553b05807727b81361e127ca04b788d4ea64298527deffdec875db629346bffc`.
- Seed 20260830; CPU fitting with 12 workers; local GPU review.
- Full machine-readable artifacts are under
  `artifacts/runs/E-003-cipher-transformation-ladder/` and remain uncommitted.

## Next falsifiable campaign

E-004 should vary cipher parameters rather than represent each family by one
setting, evaluate invariant feature subsets selected without the held-out family,
and repeat across seeds and source genres. Progressive-key settings and genuinely
paired external plaintext/ciphertext controls are the priority. Thresholds remain
frozen for a confirmatory rerun; Voynichese stays excluded until an independently
preregistered ladder passes.
