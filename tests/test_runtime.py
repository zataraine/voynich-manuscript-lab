from __future__ import annotations

from manuscript_lab.runtime import _fst_probe, _inference_probe


def test_cpu_inference_probe() -> None:
    probe = _inference_probe("cpu")
    assert probe["passed"]
    assert probe["shape"] == [32, 16]


def test_cpu_inference_probe_is_reproducible() -> None:
    first = _inference_probe("cpu")
    second = _inference_probe("cpu")
    assert first["checksum"] == second["checksum"]


def test_fst_probe_round_trips() -> None:
    probe = _fst_probe()
    assert probe["passed"]
    assert probe["round_trip"] == "abba"
