from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path

import pytest
import yaml

from manuscript_lab.human_control_pilot import HumanPilotError, validate_pilot_submission


def _payload() -> bytes:
    pages = []
    for page in range(8):
        lines = []
        for line in range(8):
            groups = [
                "p" + chr(97 + page) + chr(97 + line) + chr(97 + index // 26) + chr(97 + index % 26)
                for index in range(32)
            ]
            lines.append(" ".join(groups))
        pages.append("\n".join(lines))
    return ("\n\n".join(pages) + "\n").encode()


def _write_pilot(
    root: Path,
    *,
    modality: str = "typed",
    payload_intent: str = "no_intended_payload",
) -> Path:
    raw_directory = root / "data/raw/controls/human-production-pilot"
    interim_directory = root / "data/interim/controls/human-production-pilot"
    raw_directory.mkdir(parents=True)
    interim_directory.mkdir(parents=True)
    submission_id = "HCP-7K3M9Q2R5T8V"
    analysis = _payload()
    analysis_path = interim_directory / f"{submission_id}.txt"
    analysis_path.write_bytes(analysis)
    if modality == "typed":
        raw_path = raw_directory / f"{submission_id}-capture.txt"
        raw_payload = analysis
        media_type = "text/plain"
        method = "identity"
        entry_records = []
    else:
        raw_path = raw_directory / f"{submission_id}-capture.png"
        raw_payload = b"private-handwriting-capture-fixture"
        media_type = "image/png"
        method = "manual_double_entry_adjudicated"
        entry_records = []
        for entry_index in (1, 2):
            entry_path = interim_directory / f"{submission_id}-entry-{entry_index}.txt"
            entry_path.write_bytes(analysis)
            entry_records.append(
                {
                    "path": str(entry_path.relative_to(root)),
                    "sha256": hashlib.sha256(analysis).hexdigest(),
                }
            )
    raw_path.write_bytes(raw_payload)
    source_material = None
    if payload_intent == "intended_payload":
        source_material = {
            "source_identifier": "participant-original fixture",
            "rights_basis": "participant_original",
            "source_sha256": None,
            "use_description": "Original meaningful composition for the assigned strategy.",
        }
    attestations = {
        "adult": True,
        "voluntary": True,
        "followed_assigned_cell": True,
        "payload_intent_attestation": payload_intent,
        "no_ai_or_software_generation": True,
        "source_use_matches_assignment": True,
        "rights_to_submit": True,
        "consent_computational_analysis": True,
        "consent_private_raw_capture": True,
        "understands_withdrawal_boundary": True,
    }
    if modality == "handwritten_transcribed":
        attestations["understands_handwriting_may_identify"] = True
    metadata = {
        "schema_version": "2.0",
        "protocol_id": "human-production-pilot-v2",
        "submission_id": submission_id,
        "contributor_id": "C-4A19D75E02BC86F1",
        "assignment_id": "A-895CD12BA6307FE4",
        "allocation_slot_id": {
            ("no_intended_payload", "typed"): "HCPV2-001",
            ("no_intended_payload", "handwritten_transcribed"): "HCPV2-003",
            ("intended_payload", "typed"): "HCPV2-017",
            ("intended_payload", "handwritten_transcribed"): "HCPV2-019",
        }[(payload_intent, modality)],
        "payload_intent": payload_intent,
        "production_strategy": "freeform",
        "modality": modality,
        "raw_capture": {
            "path": str(raw_path.relative_to(root)),
            "sha256": hashlib.sha256(raw_payload).hexdigest(),
            "media_type": media_type,
            "private": True,
        },
        "analysis_text": {
            "path": str(analysis_path.relative_to(root)),
            "sha256": hashlib.sha256(analysis).hexdigest(),
        },
        "sessions": [
            {
                "session_index": 1,
                "first_page": 1,
                "last_page": 4,
                "elapsed_minutes": 90,
                "gap_since_previous": None,
            },
            {
                "session_index": 2,
                "first_page": 5,
                "last_page": 8,
                "elapsed_minutes": 90,
                "gap_since_previous": "one_to_seven_days",
            },
        ],
        "experience": {
            "voynich_exposure": "none",
            "linguistics_experience": "none",
            "constructed_language_experience": "none",
            "familiar_script_count_band": "one",
        },
        "source_material": source_material,
        "transcription_record": {
            "method": method,
            "entry_records": entry_records,
            "corrections": {"strikeouts": 0, "overwrites": 0, "insertions": 0},
            "uncertain_readings": 0,
        },
        "attestations": attestations,
        "rights": {
            "distribution": "private-research-only",
            "public_release_permitted": False,
        },
        "created_at": "2026-09-02T00:00:00Z",
        "withdrawal_deadline": "2026-12-31T00:00:00Z",
    }
    metadata_path = raw_directory / f"{submission_id}.yaml"
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    return metadata_path


@pytest.mark.parametrize(
    ("modality", "payload_intent"),
    [("typed", "no_intended_payload"), ("handwritten_transcribed", "intended_payload")],
)
def test_pilot_validator_accepts_separate_factor_cells(
    tmp_path: Path, modality: str, payload_intent: str
) -> None:
    path = _write_pilot(tmp_path, modality=modality, payload_intent=payload_intent)
    report = validate_pilot_submission(path, root=tmp_path)
    assert report["passed"]
    assert report["counts"]["groups"] == 2048
    assert report["sessions"] == 2
    assert report["factor_cell"]["payload_intent"] == payload_intent
    assert not report["confirmatory_use_permitted"]
    assert not report["manuscript_scoring_permitted"]


def test_pilot_validator_rejects_typed_transcript_drift(tmp_path: Path) -> None:
    path = _write_pilot(tmp_path)
    metadata = yaml.safe_load(path.read_text(encoding="utf-8"))
    analysis_path = tmp_path / metadata["analysis_text"]["path"]
    changed = analysis_path.read_bytes().replace(b"paaaa", b"qaaaa", 1)
    analysis_path.write_bytes(changed)
    metadata["analysis_text"]["sha256"] = hashlib.sha256(changed).hexdigest()
    path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    with pytest.raises(HumanPilotError, match="byte-identical"):
        validate_pilot_submission(path, root=tmp_path)


def test_pilot_validator_rejects_session_gaps(tmp_path: Path) -> None:
    path = _write_pilot(tmp_path)
    metadata = yaml.safe_load(path.read_text(encoding="utf-8"))
    metadata["sessions"][1]["first_page"] = 6
    path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    with pytest.raises(HumanPilotError, match="consecutive"):
        validate_pilot_submission(path, root=tmp_path)


def test_pilot_validator_rejects_assignment_leaking_symbol_inventory(tmp_path: Path) -> None:
    path = _write_pilot(tmp_path)
    metadata = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw_path = tmp_path / metadata["raw_capture"]["path"]
    analysis_path = tmp_path / metadata["analysis_text"]["path"]
    changed = analysis_path.read_bytes().replace(b"paaaa", b"paa1a", 1)
    raw_path.write_bytes(changed)
    analysis_path.write_bytes(changed)
    digest = hashlib.sha256(changed).hexdigest()
    metadata["raw_capture"]["sha256"] = digest
    metadata["analysis_text"]["sha256"] = digest
    path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    with pytest.raises(HumanPilotError, match="allowed symbol inventory"):
        validate_pilot_submission(path, root=tmp_path)


def test_pilot_validator_rejects_missing_intended_source(tmp_path: Path) -> None:
    path = _write_pilot(tmp_path, payload_intent="intended_payload")
    metadata = yaml.safe_load(path.read_text(encoding="utf-8"))
    metadata["source_material"] = None
    path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    with pytest.raises(HumanPilotError, match="invalid pilot metadata"):
        validate_pilot_submission(path, root=tmp_path)


def test_pilot_allocation_freezes_two_independent_slots_per_factor_cell() -> None:
    root = Path(__file__).parents[1]
    allocation = yaml.safe_load(
        (root / "config/controls/human-production-pilot-allocation-v2.yaml").read_text()
    )
    slots = allocation["slots"]
    assert allocation["status"] == "frozen_not_allocated"
    assert len(slots) == 32
    assert len({slot["slot_id"] for slot in slots}) == 32
    cells = Counter(
        (slot["payload_intent"], slot["production_strategy"], slot["modality"]) for slot in slots
    )
    assert len(cells) == 16
    assert set(cells.values()) == {2}
    assert all(slot["replicate"] in {1, 2} for slot in slots)
