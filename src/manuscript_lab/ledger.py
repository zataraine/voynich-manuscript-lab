"""Durable experiment state with validated transitions and hash-linked events."""

from __future__ import annotations

import hashlib
import os
import socket
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import orjson
import yaml
from jsonschema import Draft202012Validator

from manuscript_lab.provenance import repository_root, sha256_file

STATUSES = (
    "PENDING",
    "RUNNING",
    "COMPLETE",
    "FAILED",
    "REVIEW_LOCAL",
    "REJECTED",
    "PROMISING",
    "REPLICATE",
    "ESCALATE_CODEX",
)

TRANSITIONS: dict[str, frozenset[str]] = {
    "PENDING": frozenset({"RUNNING", "REJECTED"}),
    "RUNNING": frozenset({"COMPLETE", "FAILED"}),
    "COMPLETE": frozenset({"REVIEW_LOCAL"}),
    "FAILED": frozenset({"PENDING"}),
    "REVIEW_LOCAL": frozenset({"REJECTED", "PROMISING", "REPLICATE", "ESCALATE_CODEX"}),
    "PROMISING": frozenset({"REPLICATE", "ESCALATE_CODEX"}),
    "REPLICATE": frozenset({"RUNNING", "REJECTED", "ESCALATE_CODEX"}),
    "REJECTED": frozenset(),
    "ESCALATE_CODEX": frozenset(),
}

JSON_FIELDS = {
    "normalization",
    "parameters",
    "train_split",
    "heldout_split",
    "null_model",
    "metrics",
    "effects",
    "artifacts",
    "local_review",
    "escalation",
}
PATCHABLE_FIELDS = JSON_FIELDS | {"notes"}


class LedgerError(RuntimeError):
    """An experiment ledger invariant was violated."""


def default_ledger_path(root: Path | None = None) -> Path:
    return (root or repository_root()) / "artifacts" / "state" / "experiments.duckdb"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    return orjson.dumps(value, option=orjson.OPT_SORT_KEYS).decode()


def _event_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(orjson.dumps(payload, option=orjson.OPT_SORT_KEYS)).hexdigest()


def _git_provenance(root: Path) -> dict[str, Any]:
    def run(*args: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
        )

    revision_result = run("rev-parse", "HEAD")
    revision = (
        revision_result.stdout.decode().strip() if revision_result.returncode == 0 else "unborn"
    )
    status = run("status", "--porcelain=v1", "-z", "--untracked-files=all").stdout
    diff = run("diff", "--binary", "--no-ext-diff").stdout
    staged = run("diff", "--binary", "--cached", "--no-ext-diff").stdout
    digest = hashlib.sha256()
    digest.update(status)
    digest.update(diff)
    digest.update(staged)
    for entry in status.split(b"\0"):
        if not entry.startswith(b"?? "):
            continue
        relative = entry[3:].decode("utf-8", errors="surrogateescape")
        path = root / relative
        if path.is_file():
            digest.update(relative.encode("utf-8", errors="surrogateescape"))
            digest.update(bytes.fromhex(sha256_file(path)))
    return {
        "git_commit": revision,
        "git_dirty": bool(status),
        "working_tree_sha256": digest.hexdigest(),
    }


class ExperimentLedger:
    """DuckDB-backed experiment registry."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_ledger_path()

    def _connect(self) -> duckdb.DuckDBPyConnection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return duckdb.connect(str(self.path))

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id VARCHAR PRIMARY KEY,
                    status VARCHAR NOT NULL CHECK (status IN {STATUSES}),
                    created_at VARCHAR NOT NULL,
                    updated_at VARCHAR NOT NULL,
                    git_commit VARCHAR NOT NULL,
                    git_dirty BOOLEAN NOT NULL,
                    working_tree_sha256 VARCHAR NOT NULL,
                    dataset_manifest_sha256 VARCHAR NOT NULL,
                    source_manifest VARCHAR NOT NULL,
                    transcription VARCHAR NOT NULL,
                    folio_section VARCHAR,
                    currier VARCHAR,
                    normalization VARCHAR NOT NULL,
                    hypothesis_id VARCHAR NOT NULL,
                    hypothesis_family VARCHAR NOT NULL,
                    parameters VARCHAR NOT NULL,
                    seed UBIGINT NOT NULL,
                    train_split VARCHAR NOT NULL,
                    heldout_split VARCHAR NOT NULL,
                    null_model VARCHAR NOT NULL,
                    metrics VARCHAR NOT NULL,
                    effects VARCHAR NOT NULL,
                    artifacts VARCHAR NOT NULL,
                    local_review VARCHAR,
                    escalation VARCHAR,
                    notes VARCHAR,
                    last_heartbeat_at VARCHAR,
                    lease_owner VARCHAR
                )
                """
            )
            connection.execute(
                """
                CREATE SEQUENCE IF NOT EXISTS experiment_event_sequence START 1;
                CREATE TABLE IF NOT EXISTS experiment_events (
                    event_seq UBIGINT PRIMARY KEY DEFAULT nextval('experiment_event_sequence'),
                    experiment_id VARCHAR NOT NULL,
                    occurred_at VARCHAR NOT NULL,
                    actor VARCHAR NOT NULL,
                    from_status VARCHAR,
                    to_status VARCHAR NOT NULL,
                    details VARCHAR NOT NULL,
                    previous_hash VARCHAR,
                    event_hash VARCHAR NOT NULL UNIQUE
                )
                """
            )

    @staticmethod
    def _append_event(
        connection: duckdb.DuckDBPyConnection,
        *,
        experiment_id: str,
        occurred_at: str,
        actor: str,
        from_status: str | None,
        to_status: str,
        details: dict[str, Any],
    ) -> str:
        row = connection.execute(
            "SELECT event_hash FROM experiment_events ORDER BY event_seq DESC LIMIT 1"
        ).fetchone()
        previous_hash = row[0] if row else None
        payload = {
            "experiment_id": experiment_id,
            "occurred_at": occurred_at,
            "actor": actor,
            "from_status": from_status,
            "to_status": to_status,
            "details": details,
            "previous_hash": previous_hash,
        }
        digest = _event_hash(payload)
        connection.execute(
            """
            INSERT INTO experiment_events (
                experiment_id, occurred_at, actor, from_status, to_status,
                details, previous_hash, event_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                experiment_id,
                occurred_at,
                actor,
                from_status,
                to_status,
                _canonical(details),
                previous_hash,
                digest,
            ],
        )
        return digest

    def register(self, record: dict[str, Any], *, actor: str = "lab") -> dict[str, Any]:
        self.initialize()
        root = repository_root()
        schema = orjson.loads((root / "schemas" / "experiment-record.schema.json").read_bytes())
        errors = sorted(
            Draft202012Validator(schema).iter_errors(record),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            detail = "; ".join(
                f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
                for error in errors
            )
            raise LedgerError(f"Invalid experiment record: {detail}")

        source_manifest = (root / record["source_manifest"]).resolve()
        try:
            source_manifest.relative_to(root.resolve())
        except ValueError as exc:
            raise LedgerError("source_manifest must remain inside the repository") from exc
        if not source_manifest.is_file():
            raise LedgerError(f"Source manifest does not exist: {source_manifest}")
        provenance = _git_provenance(root)
        now = _now()
        scope = record["scope"]
        values = [
            record["experiment_id"],
            "PENDING",
            now,
            now,
            provenance["git_commit"],
            provenance["git_dirty"],
            provenance["working_tree_sha256"],
            sha256_file(source_manifest),
            record["source_manifest"],
            record["transcription"],
            scope["folio_section"],
            scope["currier"],
            _canonical(record["normalization"]),
            record["hypothesis_id"],
            record["hypothesis_family"],
            _canonical(record["parameters"]),
            record["seed"],
            _canonical(record["splits"]["train"]),
            _canonical(record["splits"]["heldout"]),
            _canonical(record["null_model"]),
            _canonical(record["metrics"]),
            _canonical(record["effects"]),
            _canonical(record["artifacts"]),
            record.get("notes"),
        ]
        with self._connect() as connection:
            connection.execute("BEGIN TRANSACTION")
            try:
                connection.execute(
                    """
                    INSERT INTO experiments (
                        experiment_id, status, created_at, updated_at, git_commit,
                        git_dirty, working_tree_sha256, dataset_manifest_sha256,
                        source_manifest, transcription, folio_section, currier,
                        normalization, hypothesis_id, hypothesis_family, parameters,
                        seed, train_split, heldout_split, null_model, metrics, effects,
                        artifacts, notes
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    values,
                )
                self._append_event(
                    connection,
                    experiment_id=record["experiment_id"],
                    occurred_at=now,
                    actor=actor,
                    from_status=None,
                    to_status="PENDING",
                    details={"action": "registered"},
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
        return self.get(record["experiment_id"])

    def register_file(self, path: Path, *, actor: str = "lab") -> dict[str, Any]:
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise LedgerError("Experiment config root must be a mapping")
        return self.register(record, actor=actor)

    def get(self, experiment_id: str) -> dict[str, Any]:
        self.initialize()
        with self._connect() as connection:
            cursor = connection.execute(
                "SELECT * FROM experiments WHERE experiment_id = ?", [experiment_id]
            )
            row = cursor.fetchone()
            if row is None:
                raise LedgerError(f"Unknown experiment: {experiment_id}")
            columns = [item[0] for item in cursor.description]
        result = dict(zip(columns, row, strict=True))
        for field in JSON_FIELDS:
            if result.get(field) is not None:
                result[field] = orjson.loads(result[field])
        return result

    def list(self, *, status: str | None = None) -> list[dict[str, Any]]:
        self.initialize()
        query = (
            "SELECT experiment_id, status, updated_at, last_heartbeat_at, lease_owner "
            "FROM experiments"
        )
        parameters: list[Any] = []
        if status is not None:
            if status not in STATUSES:
                raise LedgerError(f"Unknown status: {status}")
            query += " WHERE status = ?"
            parameters.append(status)
        query += " ORDER BY updated_at DESC, experiment_id"
        with self._connect() as connection:
            cursor = connection.execute(query, parameters)
            columns = [item[0] for item in cursor.description]
            return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    def transition(
        self,
        experiment_id: str,
        to_status: str,
        *,
        actor: str = "lab",
        details: dict[str, Any] | None = None,
        patch: dict[str, Any] | None = None,
        lease_owner: str | None = None,
    ) -> dict[str, Any]:
        if to_status not in STATUSES:
            raise LedgerError(f"Unknown status: {to_status}")
        patch = patch or {}
        unknown_fields = set(patch) - PATCHABLE_FIELDS
        if unknown_fields:
            raise LedgerError(f"Fields may not be patched: {sorted(unknown_fields)}")
        self.initialize()
        now = _now()
        with self._connect() as connection:
            connection.execute("BEGIN TRANSACTION")
            try:
                row = connection.execute(
                    "SELECT status FROM experiments WHERE experiment_id = ?", [experiment_id]
                ).fetchone()
                if row is None:
                    raise LedgerError(f"Unknown experiment: {experiment_id}")
                from_status = row[0]
                if to_status not in TRANSITIONS[from_status]:
                    raise LedgerError(f"Invalid transition: {from_status} -> {to_status}")

                assignments = ["status = ?", "updated_at = ?"]
                parameters: list[Any] = [to_status, now]
                for field, value in sorted(patch.items()):
                    assignments.append(f"{field} = ?")
                    parameters.append(_canonical(value) if field in JSON_FIELDS else value)
                if to_status == "RUNNING":
                    assignments.extend(["last_heartbeat_at = ?", "lease_owner = ?"])
                    parameters.extend([now, lease_owner or f"{socket.gethostname()}:{os.getpid()}"])
                elif from_status == "RUNNING":
                    assignments.append("lease_owner = NULL")
                parameters.append(experiment_id)
                connection.execute(
                    f"UPDATE experiments SET {', '.join(assignments)} WHERE experiment_id = ?",
                    parameters,
                )
                self._append_event(
                    connection,
                    experiment_id=experiment_id,
                    occurred_at=now,
                    actor=actor,
                    from_status=from_status,
                    to_status=to_status,
                    details=details or {},
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
        return self.get(experiment_id)

    def heartbeat(self, experiment_id: str, *, lease_owner: str) -> str:
        self.initialize()
        now = _now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, lease_owner FROM experiments WHERE experiment_id = ?",
                [experiment_id],
            ).fetchone()
            if row is None:
                raise LedgerError(f"Unknown experiment: {experiment_id}")
            if row[0] != "RUNNING":
                raise LedgerError(f"Heartbeat requires RUNNING status, found {row[0]}")
            if row[1] != lease_owner:
                raise LedgerError(f"Lease is owned by {row[1]!r}, not {lease_owner!r}")
            connection.execute(
                "UPDATE experiments SET last_heartbeat_at = ?, updated_at = ? "
                "WHERE experiment_id = ?",
                [now, now, experiment_id],
            )
        return now

    def stale(self, *, older_than: timedelta) -> list[dict[str, Any]]:
        threshold = (datetime.now(UTC) - older_than).isoformat().replace("+00:00", "Z")
        self.initialize()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT experiment_id, status, last_heartbeat_at, lease_owner
                FROM experiments
                WHERE status = 'RUNNING' AND last_heartbeat_at < ?
                ORDER BY last_heartbeat_at
                """,
                [threshold],
            )
            columns = [item[0] for item in cursor.description]
            return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    def verify_event_chain(self) -> dict[str, Any]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_seq, experiment_id, occurred_at, actor, from_status,
                       to_status, details, previous_hash, event_hash
                FROM experiment_events ORDER BY event_seq
                """
            ).fetchall()
        previous_hash: str | None = None
        errors: list[str] = []
        for row in rows:
            (
                event_seq,
                experiment_id,
                occurred_at,
                actor,
                from_status,
                to_status,
                details,
                recorded_previous,
                recorded_hash,
            ) = row
            payload = {
                "experiment_id": experiment_id,
                "occurred_at": occurred_at,
                "actor": actor,
                "from_status": from_status,
                "to_status": to_status,
                "details": orjson.loads(details),
                "previous_hash": recorded_previous,
            }
            actual_hash = _event_hash(payload)
            if recorded_previous != previous_hash:
                errors.append(f"event {event_seq}: previous hash mismatch")
            if actual_hash != recorded_hash:
                errors.append(f"event {event_seq}: event hash mismatch")
            previous_hash = recorded_hash
        return {"passed": not errors, "event_count": len(rows), "errors": errors}
