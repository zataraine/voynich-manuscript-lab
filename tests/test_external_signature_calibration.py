from __future__ import annotations

import numpy as np

from manuscript_lab.external_signature_calibration import (
    _classification_summary,
    _select_window,
    transform_family,
)


def test_payload_transforms_roundtrip_and_preserve_group_count() -> None:
    tokens = ("abracadabra", "cabalistic", "cipher", "manuscript", "language") * 20
    rates = {"copy_mutate_008": 0.08, "copy_mutate_018": 0.18}
    for family in (
        "natural",
        "monoalphabetic",
        "vigenere",
        "progressive_key",
        "homophonic",
        "nomenclator_hybrid",
    ):
        transformed, roundtrip = transform_family(
            tokens, family, seed=71, mutation_rates=rates, block_size=10
        )
        assert roundtrip
        assert len(transformed) == len(tokens)


def test_procedural_generators_are_seeded_and_shape_safe() -> None:
    tokens = (
        "alpha",
        "beta",
        "gamma",
        "delta",
        "epsilon",
        "zeta",
        "eta",
        "theta",
        "iota",
        "kappa",
    ) * 10
    rates = {"copy_mutate_008": 0.08, "copy_mutate_018": 0.18}
    for family in (
        "character_markov1",
        "token_markov1",
        "copy_mutate_008",
        "copy_mutate_018",
        "positional_slot",
    ):
        first, _ = transform_family(tokens, family, seed=99, mutation_rates=rates, block_size=10)
        second, _ = transform_family(tokens, family, seed=99, mutation_rates=rates, block_size=10)
        assert first == second
        assert len(first) == len(tokens)
        assert all(first)


def test_window_is_contiguous_deterministic_and_block_aligned() -> None:
    tokens = tuple(f"g{index}" for index in range(1000))
    first, start = _select_window(
        tokens, document_id="doc", seed=7, minimum=70, maximum=283, block_size=10
    )
    second, second_start = _select_window(
        tokens, document_id="doc", seed=7, minimum=70, maximum=283, block_size=10
    )
    assert first == second
    assert start == second_start
    assert len(first) == 280
    assert first == tokens[start : start + 280]


def test_classification_summary_uses_family_specific_recall() -> None:
    scores = np.asarray([0.9, 0.8, 0.2, 0.6])
    labels = np.asarray([1, 1, 0, 0])
    summary = _classification_summary(scores, labels, ["p", "p", "n", "n"], 0.5)
    assert summary["balanced_accuracy"] == 0.75
    assert summary["family_recall"] == {"n": 0.5, "p": 1.0}
    assert summary["worst_family_recall"] == 0.5
