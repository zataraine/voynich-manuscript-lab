from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from manuscript_lab.numeric import (
    decode_sequence,
    encode_bytes,
    verify_numeric_artifact,
    write_numeric_artifact,
)


@pytest.mark.parametrize("mode", ["byte", "codepoint", "grapheme"])
def test_numeric_encoding_exact_round_trip(mode: str) -> None:
    data = "A\r\ne\u0301 👩🏽‍🔬\n".encode()
    sequence, symbols = encode_bytes(data, mode=mode)  # type: ignore[arg-type]
    assert decode_sequence(sequence, symbols, mode=mode, codec="utf-8") == data  # type: ignore[arg-type]


def test_byte_mode_handles_arbitrary_bytes() -> None:
    data = b"\x00\xff\r\n\x00"
    sequence, symbols = encode_bytes(data)
    assert decode_sequence(sequence, symbols, mode="byte", codec="utf-8") == data


def test_artifact_verifies_and_detects_tampering(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"ABBA\r\n")
    prefix = tmp_path / "encoded"
    artifact = write_numeric_artifact(source, prefix)
    assert verify_numeric_artifact(prefix)["source"]["bytes"] == 6

    sequence = np.load(artifact.sequence_path, allow_pickle=False)
    sequence[0] = sequence[1]
    np.save(artifact.sequence_path, sequence, allow_pickle=False)
    with pytest.raises(ValueError, match="SHA-256"):
        verify_numeric_artifact(prefix)


def test_prefix_dots_are_preserved(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_bytes(b"AB")
    prefix = tmp_path / "source.v1"
    artifact = write_numeric_artifact(source, prefix)
    assert artifact.sequence_path.name == "source.v1.npy"
    assert artifact.manifest_path.name == "source.v1.symbols.json"
