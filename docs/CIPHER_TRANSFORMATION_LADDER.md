# Cipher transformation ladder

## Purpose

E-003 tests a prerequisite exposed by E-002: whether measurements learned from
known meaningful and human-produced nonsemantic controls survive an unseen
cipher family. It excludes Voynichese entirely. A successful result would allow
independent replication, not a manuscript interpretation.

## Paired design

Every 100-token control chunk is transformed by the same six-family registry:

1. identity;
2. document-specific monoalphabetic bijection;
3. three-way homophonic substitution;
4. period-seven, step-three per-cycle progressive polyalphabetic substitution;
5. repeated whole-token nomenclator codes with homophonic fallback;
6. verbose homophonic two-symbol encoding.

Transforms use SHA-256-derived seeds and private-use Unicode code points as
abstract single cipher symbols. They preserve token boundaries except when the
nomenclator replaces an entire repeated token with one code symbol. The verbose
family doubles the number of cipher symbols per source character. These are
controlled mechanism families, not claims about the manuscript or exact
reproductions of Naibbe.

## Leakage boundary

All chunks and transformations from a source document remain in one grouped
fold. For each family, fitting uses only other transform families on training
documents; evaluation uses the excluded family on unseen documents. Applying
every transform to both labels prevents transform identity from defining the
class. The actual Naibbe ciphertexts remain an external positive control.

An additional challenge shuffles the complete token order of meaningful chunks
before applying each cipher. This preserves token inventory and tests whether
the panel notices sequence destruction. It does not erase the meanings of
individual source words and is not treated as perfect ground-truth gibberish.

## Preregistered gates

All gates must pass:

- median leave-family-out document balanced accuracy at least 0.68;
- worst-family document balanced accuracy at least 0.55;
- external Naibbe median meaningful-similarity at least 0.55;
- median score drop after meaningful-token order destruction at least 0.05.

The mean leave-family-out accuracy is also compared with 32 fixed-fold,
document-label permutations. Failure blocks any Voynich target comparison.
Passing authorizes only independent replication with additional payloads,
nonsemantic generators, parameter ranges, and seeds.

## Execution

```bash
./scripts/run-transformation-ladder
```

Snakemake writes immutable deterministic, reference-packet, Qwen, and GLM
artifacts under `artifacts/runs/E-003-cipher-transformation-ladder/`. Local
models receive numeric summaries and approved notes, never corpus text.
