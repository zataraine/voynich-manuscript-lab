"""Run one explicit command with durable state and periodic heartbeats."""

from __future__ import annotations

import os
import socket
import subprocess
import threading
from pathlib import Path

from manuscript_lab.ledger import ExperimentLedger, LedgerError
from manuscript_lab.provenance import repository_root


def execute_experiment(
    experiment_id: str,
    command: list[str],
    *,
    ledger_path: Path | None = None,
    heartbeat_seconds: float = 60.0,
    runs_root: Path | None = None,
) -> int:
    """Execute argv without a shell, recording completion or failure."""
    if not command:
        raise LedgerError("Experiment execution requires a command")
    root = repository_root()
    ledger = ExperimentLedger(ledger_path)
    run_root = (runs_root or root / "artifacts" / "runs") / experiment_id
    log_path = run_root / "runner.log"
    if log_path.exists():
        raise LedgerError(
            f"Immutable runner log already exists for {experiment_id}; register a new experiment ID"
        )
    run_root.mkdir(parents=True, exist_ok=True)
    lease_owner = f"{socket.gethostname()}:{os.getpid()}:{threading.get_native_id()}"
    try:
        recorded_log = str(log_path.relative_to(root))
    except ValueError:
        recorded_log = str(log_path)
    ledger.transition(
        experiment_id,
        "RUNNING",
        actor="experiment-runner",
        details={"command": command, "log": recorded_log},
        lease_owner=lease_owner,
    )

    stop = threading.Event()
    heartbeat_error: list[Exception] = []

    def heartbeat() -> None:
        while not stop.wait(heartbeat_seconds):
            try:
                ledger.heartbeat(experiment_id, lease_owner=lease_owner)
            except Exception as exc:  # preserve failure for the controlling thread
                heartbeat_error.append(exc)
                stop.set()

    thread = threading.Thread(target=heartbeat, name=f"heartbeat-{experiment_id}", daemon=True)
    thread.start()
    return_code = 1
    try:
        with log_path.open("ab") as log:
            process = subprocess.run(
                command,
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
            return_code = process.returncode
    except Exception as exc:
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"\nrunner exception: {type(exc).__name__}: {exc}\n")
    finally:
        stop.set()
        thread.join(timeout=max(heartbeat_seconds * 2, 1.0))

    artifacts = {"runner_log": recorded_log}
    if heartbeat_error:
        return_code = return_code or 1
        details = {"return_code": return_code, "heartbeat_error": str(heartbeat_error[0])}
    else:
        details = {"return_code": return_code}
    ledger.transition(
        experiment_id,
        "COMPLETE" if return_code == 0 and not heartbeat_error else "FAILED",
        actor="experiment-runner",
        details=details,
        patch={"artifacts": artifacts},
    )
    return return_code
