"""Validation for prospectively collected long-form human pseudo-text controls."""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Any

import orjson
import yaml
from jsonschema import Draft202012Validator, FormatChecker

from manuscript_lab.provenance import repository_root, sha256_file

PAYLOAD_ROOT = Path("data/raw/controls/human-pseudotext")
PROTOCOL_PATH = Path("config/controls/human-pseudotext-protocol-v1.yaml")
SCHEMA_PATH = Path("schemas/human-pseudotext-submission.schema.json")


class HumanControlError(ValueError):
    """A prospective human-control submission violates its frozen contract."""


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _load_metadata(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise HumanControlError("submission metadata root must be a mapping")
    return value


def _schema_errors(metadata: dict[str, Any], root: Path) -> list[str]:
    schema = orjson.loads((root / SCHEMA_PATH).read_bytes())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
        for error in sorted(
            validator.iter_errors(metadata), key=lambda item: list(item.absolute_path)
        )
    ]


def _parse_payload(raw: bytes, protocol: dict[str, Any]) -> dict[str, Any]:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise HumanControlError("payload must be UTF-8 without a byte-order mark")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise HumanControlError(f"payload is not strict UTF-8: {exc}") from exc
    if "\x00" in text or "\t" in text:
        raise HumanControlError("payload contains a prohibited NUL or tab")
    for character in text:
        if character in "\r\n":
            continue
        if unicodedata.category(character).startswith("C"):
            raise HumanControlError(
                f"payload contains prohibited control/format code point U+{ord(character):04X}"
            )
    lines = text.splitlines()
    while lines and lines[-1] == "":
        lines.pop()
    if not lines:
        raise HumanControlError("payload is empty")
    if lines[0] == "":
        raise HumanControlError("payload begins with an empty page separator")
    pages: list[list[list[str]]] = [[]]
    prior_blank = False
    maximum_group_length = int(protocol["payload_format"]["maximum_group_codepoints"])
    for physical_line, line in enumerate(lines, start=1):
        if line == "":
            if prior_blank:
                raise HumanControlError(f"multiple empty page separators at line {physical_line}")
            pages.append([])
            prior_blank = True
            continue
        prior_blank = False
        if line != line.strip() or "  " in line:
            raise HumanControlError(
                f"line {physical_line} has leading, trailing, or repeated ASCII spaces"
            )
        groups = line.split(" ")
        for group in groups:
            if not group or any(character.isspace() for character in group):
                raise HumanControlError(f"line {physical_line} contains an invalid group")
            if len(group) > maximum_group_length:
                raise HumanControlError(
                    f"line {physical_line} contains a group longer than {maximum_group_length}"
                )
        pages[-1].append(groups)
    if not pages[-1]:
        raise HumanControlError("payload ends with an empty page")

    page_line_counts = [len(page) for page in pages]
    line_count = sum(page_line_counts)
    group_count = sum(len(line) for page in pages for line in page)
    limits = protocol["payload_format"]
    failures = []
    if group_count < int(limits["minimum_groups"]):
        failures.append(f"{group_count} groups is below minimum {limits['minimum_groups']}")
    if group_count > int(limits["maximum_groups"]):
        failures.append(f"{group_count} groups exceeds maximum {limits['maximum_groups']}")
    if line_count < int(limits["minimum_lines"]):
        failures.append(f"{line_count} lines is below minimum {limits['minimum_lines']}")
    if len(pages) < int(limits["minimum_pages"]):
        failures.append(f"{len(pages)} pages is below minimum {limits['minimum_pages']}")
    minimum_lines = int(limits["minimum_lines_per_page"])
    if any(count < minimum_lines for count in page_line_counts):
        failures.append(f"every page must contain at least {minimum_lines} lines")
    if failures:
        raise HumanControlError("; ".join(failures))
    return {
        "bytes": len(raw),
        "groups": group_count,
        "lines": line_count,
        "pages": len(pages),
        "page_line_counts": page_line_counts,
    }


def validate_submission(metadata_path: Path, *, root: Path | None = None) -> dict[str, Any]:
    """Validate metadata, confinement, exact hash, and hierarchical payload format."""
    project = (root or repository_root()).resolve()
    contract_root = repository_root()
    metadata_path = metadata_path if metadata_path.is_absolute() else project / metadata_path
    if not _inside(metadata_path, project / PAYLOAD_ROOT):
        raise HumanControlError(f"metadata must remain under {PAYLOAD_ROOT}")
    metadata = _load_metadata(metadata_path)
    errors = _schema_errors(metadata, contract_root)
    if errors:
        raise HumanControlError("invalid submission metadata: " + "; ".join(errors))
    expected_stem = str(metadata["submission_id"])
    if metadata_path.stem != expected_stem:
        raise HumanControlError("metadata filename must equal submission_id")
    payload_path = project / str(metadata["payload_path"])
    if not _inside(payload_path, project / PAYLOAD_ROOT):
        raise HumanControlError(f"payload must remain under {PAYLOAD_ROOT}")
    if payload_path.stem != expected_stem:
        raise HumanControlError("payload filename must equal submission_id")
    if not payload_path.is_file():
        raise HumanControlError(f"payload does not exist: {payload_path}")
    actual_hash = sha256_file(payload_path)
    if actual_hash != metadata["payload_sha256"]:
        raise HumanControlError("payload SHA-256 does not match metadata")
    protocol = yaml.safe_load((contract_root / PROTOCOL_PATH).read_text(encoding="utf-8"))
    if metadata["condition"] not in protocol["conditions"]:
        raise HumanControlError("condition is not registered by the frozen protocol")
    counts = _parse_payload(payload_path.read_bytes(), protocol)
    return {
        "schema_version": "1.0",
        "passed": True,
        "protocol_id": metadata["protocol_id"],
        "submission_id": metadata["submission_id"],
        "contributor_id": metadata["contributor_id"],
        "condition": metadata["condition"],
        "payload_path": str(payload_path.relative_to(project)),
        "payload_sha256": actual_hash,
        "metadata_sha256": sha256_file(metadata_path),
        "counts": counts,
        "rights": metadata["rights"],
        "attestations_recorded": sorted(metadata["attestations"]),
        "content_intention_verified": False,
    }
