from __future__ import annotations

import sys
from pathlib import Path

import pytest

from manuscript_lab.experiment_runner import execute_experiment
from manuscript_lab.ledger import ExperimentLedger, LedgerError


def _record() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "experiment_id": "E-RUNNER-001",
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
    }


def test_runner_records_command_output_and_completion(tmp_path: Path) -> None:
    database = tmp_path / "experiments.duckdb"
    ledger = ExperimentLedger(database)
    ledger.register(_record())
    return_code = execute_experiment(
        "E-RUNNER-001",
        [sys.executable, "-c", "print('bounded deterministic job')"],
        ledger_path=database,
        heartbeat_seconds=0.01,
        runs_root=tmp_path / "runs",
    )
    assert return_code == 0
    record = ledger.get("E-RUNNER-001")
    assert record["status"] == "COMPLETE"
    log_path = Path(record["artifacts"]["runner_log"])
    assert log_path.read_text(encoding="utf-8").strip() == "bounded deterministic job"
    assert ledger.verify_event_chain()["passed"]


def test_runner_refuses_to_append_to_an_existing_log(tmp_path: Path) -> None:
    database = tmp_path / "experiments.duckdb"
    ledger = ExperimentLedger(database)
    record = _record()
    record["experiment_id"] = "E-RUNNER-EXISTS"
    ledger.register(record)
    log = tmp_path / "runs" / "E-RUNNER-EXISTS" / "runner.log"
    log.parent.mkdir(parents=True)
    log.write_text("prior immutable attempt\n", encoding="utf-8")
    with pytest.raises(LedgerError, match="Immutable runner log"):
        execute_experiment(
            "E-RUNNER-EXISTS",
            [sys.executable, "-c", "print('must not run')"],
            ledger_path=database,
            runs_root=tmp_path / "runs",
        )
    assert ledger.get("E-RUNNER-EXISTS")["status"] == "PENDING"
