# 0002: Layered cryptanalysis toolchain

- Status: accepted
- Date: 2026-08-29

## Decision

Use lossless NumPy integer artifacts as the interchange layer. Use native Python
for descriptive tests and cipher simulators, Z3 and OR-Tools CP-SAT for finite
constraints, DEAP and simanneal for recorded heuristic searches, and
PyCryptodome/cryptography for standard transform verification. Install PARI/GP,
GAP, MiniZinc, CBC, GLPK, and fplll as reproducible specialist command-line
backends. Every backend is checked by the lab doctor.

Do not install SageMath from an unofficial source or a password-cracking suite.
SageMath is not packaged for this Ubuntu 24.04 baseline, and its useful algebraic
components are covered by smaller maintained packages. Password recovery tools
encode the wrong threat model for an unknown historical or constructed system.

## Consequences

The system supports modular arithmetic, group exploration, constraint models,
mixed/integer optimization, lattice experiments, suffix-array repeat searches,
and seeded stochastic search. A proposed decipherment still requires an
explicit cipher specification and held-out evidence; tool output is not itself
linguistic evidence.
