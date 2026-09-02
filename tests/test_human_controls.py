from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from manuscript_lab.human_controls import HumanControlError, validate_submission


def _payload() -> bytes:
    pages = []
    for page in range(8):
        lines = []
        for line in range(8):
            groups = [f"z{page:02d}{line:02d}{index:02d}" for index in range(32)]
            lines.append(" ".join(groups))
        pages.append("\n".join(lines))
    return ("\n\n".join(pages) + "\n").encode()


def _write_submission(root: Path, *, digest: str | None = None) -> Path:
    directory = root / "data/raw/controls/human-pseudotext"
    directory.mkdir(parents=True)
    payload = _payload()
    payload_path = directory / "HPT-7K3M9Q2R5T8V.txt"
    payload_path.write_bytes(payload)
    metadata = {
        "schema_version": "1.0",
        "protocol_id": "human-pseudotext-v1",
        "submission_id": "HPT-7K3M9Q2R5T8V",
        "contributor_id": "C-4A19D75E02BC86F1",
        "condition": "freeform",
        "payload_path": str(payload_path.relative_to(root)),
        "payload_sha256": digest or hashlib.sha256(payload).hexdigest(),
        "created_at": "2026-09-02T00:00:00Z",
        "generation_record": {
            "elapsed_minutes": 180,
            "interruption_count": 0,
            "tools_used": ["plain-text editor"],
            "self_devised_rule_description": None,
        },
        "attestations": {
            "adult": True,
            "voluntary": True,
            "no_intended_semantic_payload": True,
            "no_copied_source_text": True,
            "no_ai_or_software_generation": True,
            "sole_rightsholder": True,
            "consent_computational_analysis": True,
            "understands_withdrawal_boundary": True,
        },
        "rights": {
            "distribution": "private-research-only",
            "public_release_permitted": False,
            "attribution": None,
        },
        "withdrawal_deadline": "2026-12-31T00:00:00Z",
    }
    metadata_path = directory / "HPT-7K3M9Q2R5T8V.yaml"
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    return metadata_path


def test_submission_validator_checks_hash_hierarchy_and_counts(tmp_path: Path) -> None:
    path = _write_submission(tmp_path)
    report = validate_submission(path, root=tmp_path)
    assert report["passed"]
    assert report["counts"] == {
        "bytes": len(_payload()),
        "groups": 2048,
        "lines": 64,
        "pages": 8,
        "page_line_counts": [8] * 8,
    }
    assert not report["content_intention_verified"]


def test_submission_validator_rejects_hash_mismatch(tmp_path: Path) -> None:
    path = _write_submission(tmp_path, digest="0" * 64)
    with pytest.raises(HumanControlError, match="SHA-256"):
        validate_submission(path, root=tmp_path)


def test_submission_validator_rejects_bad_spacing(tmp_path: Path) -> None:
    path = _write_submission(tmp_path)
    payload_path = path.with_suffix(".txt")
    payload_path.write_bytes(payload_path.read_bytes().replace(b" ", b"  ", 1))
    metadata = yaml.safe_load(path.read_text(encoding="utf-8"))
    metadata["payload_sha256"] = hashlib.sha256(payload_path.read_bytes()).hexdigest()
    path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    with pytest.raises(HumanControlError, match="repeated ASCII spaces"):
        validate_submission(path, root=tmp_path)
