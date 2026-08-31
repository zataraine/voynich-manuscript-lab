from __future__ import annotations

import inspect
import random

import numpy as np

from manuscript_lab import blind_adfgx_generator
from manuscript_lab.blind_adfgx_generator import _shuffle_pairs, _source_starts
from manuscript_lab.blind_adfgx_scorer import FORBIDDEN_SCORER_KEYS, _recursive_keys
from manuscript_lab.blind_adfgx_unblind import retrieval_rows


def test_independent_generator_does_not_import_e007_transforms() -> None:
    source = inspect.getsource(blind_adfgx_generator)
    assert "adfgx_stage_localization" not in source


def test_pair_shuffle_preserves_complete_pair_multiset() -> None:
    stream = "ADAFAGAXDADFDGDXFDFGFXGAGFGGGX"
    shuffled, unchanged = _shuffle_pairs(stream, random.Random(17))

    def pairs(value: str) -> list[str]:
        return sorted(value[index : index + 2] for index in range(0, len(value), 2))

    assert pairs(shuffled) == pairs(stream)
    assert 0 <= unchanged < len(stream) // 2


def test_seeded_source_starts_are_spaced_for_maximum_segments() -> None:
    starts = _source_starts(100_000, 12, 757, random.Random(5))
    assert len(starts) == len(set(starts)) == 12
    assert (
        min(abs(left - right) for index, left in enumerate(starts) for right in starts[index + 1 :])
        >= 757
    )


def test_public_shape_has_no_forbidden_truth_keys() -> None:
    public = {
        "suites": [
            {
                "suite_id": "s00",
                "candidates": [{"candidate_id": "c0", "text": "ABC"}],
                "queries": [{"query_id": "q0", "ciphertext": "AD", "broken_ciphertext": "DA"}],
            }
        ]
    }
    assert not (FORBIDDEN_SCORER_KEYS & _recursive_keys(public))


def test_retrieval_rows_uses_average_tie_ranks() -> None:
    metrics = retrieval_rows(
        [np.asarray([1.0, 1.0, 0.0]), np.asarray([0.0, 1.0, 0.0])],
        [0, 1],
    )
    assert metrics["median_rank"] == 1.25
    assert metrics["top1_fraction"] == 0.5
