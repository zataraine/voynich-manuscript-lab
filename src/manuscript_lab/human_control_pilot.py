"""Validation for the paired human-production pilot contract."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import orjson
import yaml
from jsonschema import Draft202012Validator, FormatChecker

from manuscript_lab.human_controls import HumanControlError, parse_control_payload
from manuscript_lab.provenance import repository_root, sha256_file

RAW_ROOT = Path("data/raw/controls/human-production-pilot")
INTERIM_ROOT = Path("data/interim/controls/human-production-pilot")
PROTOCOL_PATH = Path("config/controls/human-production-pilot-v2.yaml")
ALLOCATION_PATH = Path("config/controls/human-production-pilot-allocation-v2.yaml")
SCHEMA_PATH = Path("schemas/human-production-pilot-submission.schema.json")


class HumanPilotError(ValueError):
    """A human-production pilot submission violates its frozen contract."""


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _schema_errors(metadata: dict[str, Any], root: Path) -> list[str]:
    schema = orjson.loads((root / SCHEMA_PATH).read_bytes())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
        for error in sorted(
            validator.iter_errors(metadata), key=lambda item: list(item.absolute_path)
        )
    ]


def _load_metadata(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise HumanPilotError("submission metadata root must be a mapping")
    return value


def _validate_sessions(sessions: list[dict[str, Any]], page_count: int) -> None:
    expected_page = 1
    for expected_index, session in enumerate(sessions, start=1):
        if session["session_index"] != expected_index:
            raise HumanPilotError("session indices must be consecutive from one")
        if session["first_page"] != expected_page:
            raise HumanPilotError("session page ranges must be consecutive and non-overlapping")
        if session["last_page"] < session["first_page"]:
            raise HumanPilotError("session last_page precedes first_page")
        if expected_index == 1 and session["gap_since_previous"] is not None:
            raise HumanPilotError("the first session gap_since_previous must be null")
        if expected_index > 1 and session["gap_since_previous"] is None:
            raise HumanPilotError("later sessions must record a coarse gap")
        expected_page = int(session["last_page"]) + 1
    if expected_page - 1 != page_count:
        raise HumanPilotError("session page ranges must cover every analysis-text page exactly")


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_pilot_submission(metadata_path: Path, *, root: Path | None = None) -> dict[str, Any]:
    """Validate the v2 pilot sidecar, immutable captures, and transcript structure."""
    project = (root or repository_root()).resolve()
    contract_root = repository_root()
    metadata_path = metadata_path if metadata_path.is_absolute() else project / metadata_path
    if not _inside(metadata_path, project / RAW_ROOT):
        raise HumanPilotError(f"metadata must remain under {RAW_ROOT}")
    metadata = _load_metadata(metadata_path)
    errors = _schema_errors(metadata, contract_root)
    if errors:
        raise HumanPilotError("invalid pilot metadata: " + "; ".join(errors))

    submission_id = str(metadata["submission_id"])
    if metadata_path.stem != submission_id:
        raise HumanPilotError("metadata filename must equal submission_id")

    raw_path = project / metadata["raw_capture"]["path"]
    analysis_path = project / metadata["analysis_text"]["path"]
    if not _inside(raw_path, project / RAW_ROOT):
        raise HumanPilotError(f"raw capture must remain under {RAW_ROOT}")
    if not _inside(analysis_path, project / INTERIM_ROOT):
        raise HumanPilotError(f"analysis text must remain under {INTERIM_ROOT}")
    if raw_path.stem != f"{submission_id}-capture":
        raise HumanPilotError("raw capture filename must derive from submission_id")
    if analysis_path.stem != submission_id:
        raise HumanPilotError("analysis filename must equal submission_id")
    for label, path in (("raw capture", raw_path), ("analysis text", analysis_path)):
        if not path.is_file():
            raise HumanPilotError(f"{label} does not exist: {path}")

    raw_hash = sha256_file(raw_path)
    analysis_hash = sha256_file(analysis_path)
    if raw_hash != metadata["raw_capture"]["sha256"]:
        raise HumanPilotError("raw capture SHA-256 does not match metadata")
    if analysis_hash != metadata["analysis_text"]["sha256"]:
        raise HumanPilotError("analysis text SHA-256 does not match metadata")
    if metadata["modality"] == "typed" and raw_path.read_bytes() != analysis_path.read_bytes():
        raise HumanPilotError("typed raw capture and analysis text must be byte-identical")

    protocol = yaml.safe_load((contract_root / PROTOCOL_PATH).read_text(encoding="utf-8"))
    factors = protocol["factorial_design"]
    for field in ("payload_intent", "production_strategy", "modality"):
        if metadata[field] not in factors[field]:
            raise HumanPilotError(f"{field} is not registered by the pilot protocol")
    allocation = yaml.safe_load((contract_root / ALLOCATION_PATH).read_text(encoding="utf-8"))
    slots = {slot["slot_id"]: slot for slot in allocation["slots"]}
    slot = slots.get(metadata["allocation_slot_id"])
    if slot is None:
        raise HumanPilotError("allocation_slot_id is absent from the frozen allocation")
    for field in ("payload_intent", "production_strategy", "modality"):
        if slot[field] != metadata[field]:
            raise HumanPilotError(f"submission {field} does not match its frozen allocation slot")

    entry_hashes = []
    for entry in metadata["transcription_record"]["entry_records"]:
        entry_path = project / entry["path"]
        if not _inside(entry_path, project / INTERIM_ROOT):
            raise HumanPilotError(f"transcription entry must remain under {INTERIM_ROOT}")
        if not entry_path.is_file():
            raise HumanPilotError(f"transcription entry does not exist: {entry_path}")
        entry_hash = sha256_file(entry_path)
        if entry_hash != entry["sha256"]:
            raise HumanPilotError("transcription entry SHA-256 does not match metadata")
        entry_path.read_text(encoding="utf-8", errors="strict")
        entry_hashes.append(entry_hash)
    try:
        counts = parse_control_payload(analysis_path.read_bytes(), protocol)
    except HumanControlError as exc:
        raise HumanPilotError(str(exc)) from exc
    if len(metadata["sessions"]) < int(protocol["payload_format"]["minimum_sessions"]):
        raise HumanPilotError("submission has fewer sessions than the pilot minimum")
    _validate_sessions(metadata["sessions"], int(counts["pages"]))
    if _parse_time(metadata["withdrawal_deadline"]) <= _parse_time(metadata["created_at"]):
        raise HumanPilotError("withdrawal_deadline must follow created_at")

    return {
        "schema_version": "2.0",
        "passed": True,
        "protocol_id": metadata["protocol_id"],
        "protocol_status": protocol["status"],
        "submission_id": submission_id,
        "contributor_id": metadata["contributor_id"],
        "assignment_id": metadata["assignment_id"],
        "allocation_slot_id": metadata["allocation_slot_id"],
        "factor_cell": {
            field: metadata[field]
            for field in ("payload_intent", "production_strategy", "modality")
        },
        "raw_capture": {
            "path": str(raw_path.relative_to(project)),
            "sha256": raw_hash,
            "private": True,
        },
        "analysis_text": {
            "path": str(analysis_path.relative_to(project)),
            "sha256": analysis_hash,
        },
        "metadata_sha256": sha256_file(metadata_path),
        "counts": counts,
        "sessions": len(metadata["sessions"]),
        "transcription_entry_sha256s": entry_hashes,
        "total_elapsed_minutes": sum(
            int(session["elapsed_minutes"]) for session in metadata["sessions"]
        ),
        "payload_intention_attested_not_verified": True,
        "content_meaning_not_validated": True,
        "confirmatory_use_permitted": False,
        "manuscript_scoring_permitted": False,
    }
