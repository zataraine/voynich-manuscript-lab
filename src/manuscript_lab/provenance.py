"""Source-manifest creation and verification."""

from __future__ import annotations

import hashlib
import mimetypes
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_VERSION = "1.0"
CHUNK_SIZE = 4 * 1024 * 1024


def repository_root() -> Path:
    """Return the repository root from this source checkout."""
    return Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    """Hash a file without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def infer_role(path: Path) -> str:
    """Infer a conservative file role from its raw-layer parent."""
    parts = set(path.parts)
    if "books" in parts:
        return "book"
    if "images" in parts:
        return "page-image"
    if "transcriptions" in parts:
        return "transcription"
    if "metadata" in parts:
        return "metadata"
    return "other"


def _relative_raw_path(path: Path, root: Path) -> tuple[Path, Path]:
    absolute = path.resolve(strict=True)
    raw_root = (root / "data" / "raw").resolve(strict=True)
    try:
        relative = absolute.relative_to(root.resolve(strict=True))
        absolute.relative_to(raw_root)
    except ValueError as exc:
        raise ValueError(f"Source must be inside {raw_root}: {absolute}") from exc
    if not absolute.is_file():
        raise ValueError(f"Source is not a regular file: {absolute}")
    return absolute, relative


def build_manifest(source_id: str, paths: list[Path], root: Path | None = None) -> dict[str, Any]:
    """Build an in-memory manifest for immutable raw files."""
    if not paths:
        raise ValueError("At least one source file is required")
    root = (root or repository_root()).resolve(strict=True)
    files: list[dict[str, Any]] = []
    for path in paths:
        absolute, relative = _relative_raw_path(path, root)
        media_type = mimetypes.guess_type(absolute.name)[0] or "application/octet-stream"
        files.append(
            {
                "path": relative.as_posix(),
                "role": infer_role(relative),
                "media_type": media_type,
                "bytes": absolute.stat().st_size,
                "sha256": sha256_file(absolute),
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "source_id": source_id,
        "manifest_created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "acquisition": {"obtained_at": None, "obtained_from": None, "custodian": None},
        "rights": {"status": "unknown", "license": None, "restrictions": None},
        "transcription": {
            "scheme_name": None,
            "scheme_version": None,
            "character_encoding": None,
            "unit_definition": None,
            "uncertainty_notation": None,
        },
        "files": sorted(files, key=lambda item: item["path"]),
        "notes": "Complete the null metadata fields before analysis.",
    }


def schema(root: Path | None = None) -> dict[str, Any]:
    """Load the tracked manifest JSON Schema."""
    root = root or repository_root()
    return yaml.safe_load((root / "schemas" / "source-manifest.schema.json").read_text())


def validate_manifest(manifest: dict[str, Any], root: Path | None = None) -> list[str]:
    """Return human-readable schema errors."""
    validator = Draft202012Validator(schema(root), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(manifest), key=lambda error: list(error.absolute_path))
    return [
        f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
        for error in errors
    ]


def load_manifest(path: Path) -> dict[str, Any]:
    """Load one YAML manifest and require a mapping at its root."""
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Manifest root must be a mapping")
    return value


def verify_manifest_files(manifest: dict[str, Any], root: Path | None = None) -> list[str]:
    """Return file-integrity errors for a schema-valid manifest."""
    root = (root or repository_root()).resolve(strict=True)
    raw_root = (root / "data" / "raw").resolve(strict=True)
    errors: list[str] = []
    for item in manifest["files"]:
        path = (root / item["path"]).resolve()
        try:
            path.relative_to(raw_root)
        except ValueError:
            errors.append(f"outside raw data root: {item['path']}")
            continue
        if not path.is_file():
            errors.append(f"missing: {item['path']}")
            continue
        actual_size = path.stat().st_size
        if actual_size != item["bytes"]:
            errors.append(f"size mismatch: {item['path']} ({actual_size} != {item['bytes']})")
            continue
        actual_hash = sha256_file(path)
        if actual_hash != item["sha256"]:
            errors.append(f"SHA-256 mismatch: {item['path']}")
    return errors


def dump_manifest(manifest: dict[str, Any], path: Path) -> None:
    """Write a manifest in stable, readable YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
        newline="\n",
    )
