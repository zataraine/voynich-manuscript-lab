from __future__ import annotations

import hashlib
from pathlib import Path

from manuscript_lab.provenance import (
    build_manifest,
    sha256_file,
    validate_manifest,
    verify_manifest_files,
)


def _minimal_repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path
    raw = root / "data" / "raw" / "transcriptions"
    raw.mkdir(parents=True)
    (root / "schemas").mkdir()
    project_schema = Path(__file__).parents[1] / "schemas" / "source-manifest.schema.json"
    (root / "schemas" / "source-manifest.schema.json").write_bytes(project_schema.read_bytes())
    source = raw / "encoding.txt"
    source.write_bytes(b"alpha\r\nbeta\x00gamma\n")
    return root, source


def test_sha256_file_is_byte_exact(tmp_path: Path) -> None:
    source = tmp_path / "sample.bin"
    payload = b"\x00\xff\r\nnot-text"
    source.write_bytes(payload)
    assert sha256_file(source) == hashlib.sha256(payload).hexdigest()


def test_manifest_build_and_verify(tmp_path: Path) -> None:
    root, source = _minimal_repo(tmp_path)
    manifest = build_manifest("source-a", [source], root)
    assert manifest["files"][0]["role"] == "transcription"
    assert not validate_manifest(manifest, root)
    assert not verify_manifest_files(manifest, root)


def test_manifest_detects_changed_raw_file(tmp_path: Path) -> None:
    root, source = _minimal_repo(tmp_path)
    manifest = build_manifest("source-a", [source], root)
    source.write_bytes(b"changed")
    errors = verify_manifest_files(manifest, root)
    assert errors
    assert "size mismatch" in errors[0] or "SHA-256 mismatch" in errors[0]


def test_manifest_rejects_file_outside_raw(tmp_path: Path) -> None:
    root, _ = _minimal_repo(tmp_path)
    outside = root / "notes.txt"
    outside.write_text("not raw")
    try:
        build_manifest("source-a", [outside], root)
    except ValueError as exc:
        assert "inside" in str(exc)
    else:
        raise AssertionError("Expected a file outside data/raw to be rejected")
