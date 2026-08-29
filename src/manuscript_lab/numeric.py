"""Lossless, provenance-bearing conversion of source bytes to integer sequences."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import orjson
import regex

Mode = Literal["byte", "codepoint", "grapheme"]
Ordering = Literal["first", "sorted"]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _units(data: bytes, mode: Mode, codec: str) -> list[bytes | str]:
    if mode == "byte":
        return [bytes([value]) for value in data]
    text = data.decode(codec, errors="strict")
    if mode == "codepoint":
        return list(text)
    if mode == "grapheme":
        return regex.findall(r"\X", text)
    raise ValueError(f"Unsupported mode: {mode}")


def _ordered_symbols(units: list[bytes | str], ordering: Ordering) -> list[bytes | str]:
    if ordering == "first":
        return list(dict.fromkeys(units))
    if ordering == "sorted":
        return sorted(set(units))
    raise ValueError(f"Unsupported ordering: {ordering}")


def encode_bytes(
    data: bytes,
    *,
    mode: Mode = "byte",
    codec: str = "utf-8",
    ordering: Ordering = "first",
) -> tuple[np.ndarray, list[bytes | str]]:
    """Encode bytes without normalization; the returned symbol table reverses the mapping."""
    units = _units(data, mode, codec)
    symbols = _ordered_symbols(units, ordering)
    lookup = {symbol: index for index, symbol in enumerate(symbols)}
    dtype = np.uint8 if len(symbols) <= 256 else np.uint32
    return np.asarray([lookup[unit] for unit in units], dtype=dtype), symbols


def decode_sequence(
    sequence: np.ndarray,
    symbols: list[bytes | str],
    *,
    mode: Mode,
    codec: str,
) -> bytes:
    """Reconstruct the exact source bytes represented by a sequence and symbol table."""
    try:
        selected = [symbols[int(value)] for value in sequence]
    except (IndexError, TypeError) as exc:
        raise ValueError("Sequence contains a symbol ID outside the symbol table") from exc
    if mode == "byte":
        return b"".join(selected)  # type: ignore[arg-type]
    return "".join(selected).encode(codec, errors="strict")  # type: ignore[arg-type]


def _symbol_record(index: int, symbol: bytes | str, codec: str) -> dict[str, Any]:
    encoded = symbol if isinstance(symbol, bytes) else symbol.encode(codec, errors="strict")
    return {
        "id": index,
        "surface": None if isinstance(symbol, bytes) else symbol,
        "bytes_hex": encoded.hex(),
    }


@dataclass(frozen=True)
class NumericArtifact:
    sequence_path: Path
    manifest_path: Path


def artifact_paths(output_prefix: Path) -> NumericArtifact:
    """Append artifact extensions without discarding dots in the caller's prefix."""
    return NumericArtifact(Path(f"{output_prefix}.npy"), Path(f"{output_prefix}.symbols.json"))


def write_numeric_artifact(
    source: Path,
    output_prefix: Path,
    *,
    mode: Mode = "byte",
    codec: str = "utf-8",
    ordering: Ordering = "first",
    force: bool = False,
) -> NumericArtifact:
    """Write ``.npy`` plus a JSON manifest and prove an exact byte round trip first."""
    source_data = source.read_bytes()
    sequence, symbols = encode_bytes(source_data, mode=mode, codec=codec, ordering=ordering)
    reconstructed = decode_sequence(sequence, symbols, mode=mode, codec=codec)
    if reconstructed != source_data:
        raise ValueError("Numeric encoding failed exact byte round-trip verification")

    paths = artifact_paths(output_prefix)
    sequence_path = paths.sequence_path
    manifest_path = paths.manifest_path
    if not force and (sequence_path.exists() or manifest_path.exists()):
        raise FileExistsError("Output exists; choose another prefix or pass force=True")
    sequence_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(sequence_path, sequence, allow_pickle=False)
    array_data = sequence_path.read_bytes()
    manifest = {
        "schema_version": "1.0",
        "source": {
            "path": source.as_posix(),
            "bytes": len(source_data),
            "sha256": _sha256(source_data),
        },
        "encoding": {"mode": mode, "codec": codec, "ordering": ordering},
        "sequence": {
            "path": sequence_path.as_posix(),
            "length": int(sequence.size),
            "dtype": str(sequence.dtype),
            "sha256": _sha256(array_data),
        },
        "symbols": [_symbol_record(i, symbol, codec) for i, symbol in enumerate(symbols)],
    }
    manifest_path.write_bytes(orjson.dumps(manifest, option=orjson.OPT_INDENT_2) + b"\n")
    return NumericArtifact(sequence_path, manifest_path)


def verify_numeric_artifact(output_prefix: Path) -> dict[str, Any]:
    """Verify array hash, symbol IDs, and exact reconstruction against the source hash."""
    paths = artifact_paths(output_prefix)
    sequence_path = paths.sequence_path
    manifest_path = paths.manifest_path
    manifest = orjson.loads(manifest_path.read_bytes())
    if _sha256(sequence_path.read_bytes()) != manifest["sequence"]["sha256"]:
        raise ValueError("Sequence SHA-256 mismatch")
    sequence = np.load(sequence_path, allow_pickle=False)
    if int(sequence.size) != manifest["sequence"]["length"]:
        raise ValueError("Sequence length mismatch")
    records = manifest["symbols"]
    if [record["id"] for record in records] != list(range(len(records))):
        raise ValueError("Symbol IDs must be contiguous and ordered")
    mode: Mode = manifest["encoding"]["mode"]
    codec = manifest["encoding"]["codec"]
    symbols: list[bytes | str] = [
        bytes.fromhex(record["bytes_hex"]) if mode == "byte" else record["surface"]
        for record in records
    ]
    reconstructed = decode_sequence(sequence, symbols, mode=mode, codec=codec)
    if _sha256(reconstructed) != manifest["source"]["sha256"]:
        raise ValueError("Reconstructed source SHA-256 mismatch")
    return manifest
