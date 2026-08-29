# Cryptanalysis protocol

This lane tests whether the supplied code is compatible with a cipher process.
It does not assume that it is encrypted, that its visible units are characters,
or that a readable-looking output is a decipherment.

## Representation gate

1. Preserve the supplied file in `data/raw/` and verify its source manifest.
2. Produce byte, code-point, grapheme, token, or region sequences separately.
3. Keep the symbol table, codec, ordering rule, hashes, and exact inverse with
   every sequence. Never assign semantic names to IDs.
4. Treat boundary marks and uncertainty syntax as data until their role is
   documented. Test both retained and removed variants as separate transforms.

Use `numeric encode` and `numeric verify` for the first three unitizations. Byte
mode is the universal baseline because it accepts arbitrary input and preserves
every byte. Code-point and grapheme modes decode strictly and never normalize.

## Family decomposition

A hybrid is a pipeline, not one opaque label. Record the order of stages:

| Stage | Candidate mechanism | Necessary recorded parameters |
|---|---|---|
| segmentation | glyph, token, region, code group | rules and ambiguity |
| nomenclator | whole-token or phrase codebook | domain, ranges, collisions, nulls |
| substitution | monoalphabetic or homophonic | mapping cardinalities and unmapped units |
| alphabet selection | repeating or keyed alphabets | period, reset boundary, alphabet |
| progression | per-symbol or per-cycle shift | step, modulus, origin, reset boundary |
| transposition | local or global reordering | permutation and block boundaries |

“Progressive key” is ambiguous unless specified. This lab distinguishes:

- per-symbol: `shift(i) = key[i mod p] + step * i (mod m)`;
- per-cycle: `shift(i) = key[i mod p] + step * floor(i / p) (mod m)`.

A nomenclator is tested at the token/code-group layer. Its codebook may coexist
with a homophonic character layer, but the two mappings remain separately
invertible and separately scored.

## Search sequence

1. Describe observables: inventory, frequency, entropy, coincidence, repeats,
   spacing, lag peaks, page/line position, and image-region alignment.
2. Compare page-preserving shuffles, frequency-preserving shuffles, Markov nulls,
   and synthetic ciphers generated with known parameters.
3. Fit only on training pages. Tune periods, progression, codebook sizes, and
   objective weights without seeing held-out pages.
4. Use deterministic enumeration where feasible; Z3 or CP-SAT for discrete
   constraints; annealing/evolutionary search only with seeds and repeated runs.
5. Decode held-out physical units with the frozen transform. Report prediction
   coverage, stability, compression or language-model gain, and null percentile.

## Evidence threshold

A candidate is not a result because it resembles a word or illustration. It
must beat preregistered nulls and simpler cipher families on held-out pages,
remain stable across seeds/unitizations, predict unseen structure, and expose a
complete reversible path. Record every attempted family to control researcher
degrees of freedom and apply the stated multiple-testing correction.

Standard cryptographic libraries here generate and verify transforms. Password
crackers are deliberately excluded: they do not address an unknown manuscript
model and encourage an unjustified modern-cipher assumption.
