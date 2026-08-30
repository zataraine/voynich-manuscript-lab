from __future__ import annotations

import numpy as np
import pytest

from manuscript_lab.cipher_transforms import (
    TRANSFORMS,
    apply_transform,
    destroy_token_order,
)
from manuscript_lab.feature_panel import extract_sequence_features
from manuscript_lab.ladder_review import bounded_record

TOKENS = ("alpha", "beta", "alpha", "gamma", "delta") * 20


@pytest.mark.parametrize("family", sorted(TRANSFORMS))
def test_cipher_transforms_are_seeded_and_preserve_token_count(family: str) -> None:
    first = apply_transform(TOKENS, family, seed=17, sample_id="sample")
    second = apply_transform(TOKENS, family, seed=17, sample_id="sample")
    assert first == second
    assert len(first) == len(TOKENS)
    assert all(first)


def test_transform_properties_are_explicit() -> None:
    mono = apply_transform(TOKENS, "monoalphabetic", seed=17, sample_id="sample")
    verbose = apply_transform(TOKENS, "verbose_homophonic", seed=17, sample_id="sample")
    nomenclator = apply_transform(TOKENS, "nomenclator_homophonic", seed=17, sample_id="sample")
    assert mono[0] == mono[2]
    assert all(len(cipher) == len(plain) * 2 for plain, cipher in zip(TOKENS, verbose, strict=True))
    assert nomenclator[0] == nomenclator[2]
    assert len(nomenclator[0]) == 1


def test_order_destruction_preserves_multiset_and_changes_sequence() -> None:
    destroyed = destroy_token_order(TOKENS, seed=17, sample_id="sample")
    assert sorted(destroyed) == sorted(TOKENS)
    assert destroyed != TOKENS


def test_sequence_panel_detects_order_change() -> None:
    original = extract_sequence_features(TOKENS)
    destroyed = extract_sequence_features(destroy_token_order(TOKENS, seed=17, sample_id="sample"))
    assert len(original) == 29
    assert all(np.isfinite(value) for value in original.values())
    assert (
        original["token_bigram_mutual_information"] != destroyed["token_bigram_mutual_information"]
    )


def test_ladder_review_removes_per_feature_correlations() -> None:
    result = {
        "experiment_id": "E-test",
        "feature_survival": {
            "cipher": {
                "median_feature_spearman": 0.2,
                "feature_spearman": {"secret": 0.1},
            }
        },
    }
    bounded = bounded_record(result, {"passages": [], "policy_note": "notes only"})
    assert "feature_spearman" not in bounded["feature_survival"]["cipher"]
