# Executable Phase 4 acceptance inventory

The report combines freshly executed software evidence with the ten reviewed
requirement areas in the Phase 4 audit. It is a readiness inventory, not a
manuscript experiment, external calibration, or automatic scientific approval.

```bash
./scripts/run python -m manuscript_lab.phase4_acceptance \
  --output artifacts/diagnostics/phase4-acceptance-NEW-ID
```

One command creates a new directory containing:

- `report.md`: the readable requirement-by-requirement summary;
- `report.json`: exact evidence counts, remaining work and provenance;
- `pytest.xml`: fresh machine-readable test outcomes;
- `pytest.log`: retained test output and errors.

Existing paths are refused. The selected tests run once as a union rather than
being rerun for every requirement. They cover core, learned units, reversible
views, growth, layout, sampling/nulls, availability, schema and bounded stress
checks. The test command has a five-minute ceiling. It does not rerun the full
54-case stress sweep or the infrastructure smoke gate; those remain separate.

The registry is `config/research/phase4-acceptance-v1.yaml`. It maps every audit
area to existing test files and explicitly reviewed remaining work. File-level
test coverage verifies a **subset**, not every assertion in a broad requirement.
Remaining work is human-reviewed registry content, not inferred from a passing
test or the existence of a file. Publication review must keep it synchronized
with the roadmap and Phase 4 audit. Removing a row, leaving no declared open
work, escaping the test directory, or enabling target access is rejected by
this version; completing readiness needs a deliberately reviewed successor.

An area is `verified_subset` only if the fresh test process succeeds and each
mapped file has passing test cases with no failures or skips. Missing/unmapped
or malformed evidence cannot count as success. Any process failure makes every
software row unverified. Each readiness area remains `open` in v1, even if its
software evidence passes. This makes outstanding scientific work explicit
instead of treating unit-test success as calibration.

The report snapshots Git/dirty-tree provenance before execution and checks it
again afterward. It also hashes the registry, lockfile, mapped tests, roadmap
and acceptance audit before/after execution. A changing working tree invalidates
the fresh verification result. Report provenance includes UTC time, exact
command, CPU device, output path and evidence-file hashes. Generated artifacts
are ignored by Git; they contain execution provenance and do not promise
identical file hashes across machines or revisions.

To use the inventory as a fail-closed readiness check:

```bash
./scripts/run python -m manuscript_lab.phase4_acceptance --require-ready \
  --output artifacts/diagnostics/phase4-acceptance-GATE-ID
```

Exit 0 means the inventory was generated with successful software evidence.
Exit 1 means verification failed. `--require-ready` returns exit 2 after saving
an otherwise successful report because Phase 4 remains open. Neither outcome
grants target access or joint scientific comparison. Later phases still require
their own production-mechanism replication, external validation and sealed
target boundary. A registry report is not a filesystem access-control barrier.

## Verification

The first full inventory on 2026-10-14 saved its four artifacts under
`artifacts/diagnostics/phase4-acceptance-20261014/`. Its selected 139 tests passed,
before/after provenance matched, and all ten areas reported `verified_subset`
with readiness still `open`. Readiness mode refused to pass, as intended.
This is an execution snapshot, not new manuscript or external-control evidence.

```bash
./scripts/run pytest tests/test_phase4_acceptance.py
./scripts/smoke.sh
```

Tests exercise complete requirement coverage, success without readiness
promotion, failed/skipped/missing evidence, JUnit decoding, explicit open-work
requirements and path/target restrictions. The reporter's own tests are not
included in its child process, avoiding recursive self-execution; the full
smoke gate verifies them separately.
