# 0009: Hold out cipher families before manuscript targets

- Date: 2026-08-30
- Status: accepted

## Context

E-002 separated plaintext control collections but scored known-payload Naibbe
ciphertext as gibberish-like. A larger classifier trained on the same domain
would not address that failure. Testing a target before demonstrating cipher
domain transfer would turn model selection into target tuning.

## Decision

Exclude Voynichese from E-003. Apply explicit seeded transforms identically to
both control labels. Hold out complete source documents and a complete cipher
family in every primary evaluation. Retain actual Naibbe ciphertext as external
positive control and add a token-order destruction challenge. Require all four
preregistered gates before independent replication.

## Consequences

E-003 can identify invariant or fragile measurements and can reject the current
panel. It cannot identify a cipher, establish semantic content, distinguish a
constructed language from a hoax, or create posterior odds. A failed family
directly specifies which control domain needs improvement.
