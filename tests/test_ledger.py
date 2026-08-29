from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from manuscript_lab.ledger import ExperimentLedger, LedgerError


def _record(experiment_id: str) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "hypothesis_id": "H-TEST",
        "source_manifest": "data/manifests/source.example.yaml",
        "transcription": "synthetic-test-fixture",
        "scope": {"folio_section": None, "currier": None},
        "normalization": {"version": "identity"},
        "hypothesis_family": "infrastructure-test",
        "parameters": {},
        "seed": 20260829,
        "splits": {"train": {"pages": ["p1"]}, "heldout": {"pages": ["p2"]}},
        "null_model": {"family": "fixed-fixture"},
        "metrics": {},
        "effects": {},
        "artifacts": {},
        "notes": "No manuscript data is used.",
    }


def test_ledger_enforces_transitions_and_verifies_chain(tmp_path: Path) -> None:
    ledger = ExperimentLedger(tmp_path / "experiments.duckdb")
    registered = ledger.register(_record("E-TEST-001"))
    assert registered["status"] == "PENDING"
    running = ledger.transition("E-TEST-001", "RUNNING", lease_owner="test:1")
    assert running["lease_owner"] == "test:1"
    ledger.heartbeat("E-TEST-001", lease_owner="test:1")
    complete = ledger.transition(
        "E-TEST-001",
        "COMPLETE",
        patch={"metrics": {"primary": 0.0}, "effects": {"strength": "none"}},
    )
    assert complete["metrics"] == {"primary": 0.0}
    assert ledger.verify_event_chain() == {"passed": True, "event_count": 3, "errors": []}

    with pytest.raises(LedgerError, match="Invalid transition"):
        ledger.transition("E-TEST-001", "RUNNING")


def test_ledger_detects_event_tampering(tmp_path: Path) -> None:
    path = tmp_path / "experiments.duckdb"
    ledger = ExperimentLedger(path)
    ledger.register(_record("E-TEST-002"))
    with duckdb.connect(str(path)) as connection:
        connection.execute(
            "UPDATE experiment_events SET details = ? WHERE event_seq = 1",
            ['{"action":"altered"}'],
        )
    report = ledger.verify_event_chain()
    assert not report["passed"]
    assert "event hash mismatch" in report["errors"][0]
