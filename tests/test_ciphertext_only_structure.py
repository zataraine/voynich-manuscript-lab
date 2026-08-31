from __future__ import annotations

import random

import numpy as np
import orjson

from manuscript_lab.adfgx_stage_localization import (
    _encode_coordinates,
    _permutations,
    columnar_encipher,
)
from manuscript_lab.ciphertext_structure_generator import (
    block8_shuffle,
    copy_mutate,
    markov1,
    unigram_shuffle,
)
from manuscript_lab.ciphertext_structure_review import bounded_record
from manuscript_lab.ciphertext_structure_scorer import order2_over_order1_scores
from manuscript_lab.ciphertext_structure_unblind import _paired_auc, _sign_permutation_p


def _pair_stream(symbols: list[int]) -> str:
    coordinates = "ADFGX"
    return "".join(coordinates[value // 5] + coordinates[value % 5] for value in symbols)


def test_exact_count_controls_preserve_length_and_inventory() -> None:
    text = "THEQUICKBROWNFOXIUMPSOVERTHELAZYDOG" * 4
    shuffled = unigram_shuffle(text, random.Random(3))
    blocked = block8_shuffle(text, random.Random(4))
    assert len(shuffled) == len(blocked) == len(text)
    assert sorted(shuffled) == sorted(blocked) == sorted(text)
    assert len(markov1(text, random.Random(5))) == len(text)
    assert len(copy_mutate(text, random.Random(6))) == len(text)


def test_predictive_gain_is_symbol_renaming_invariant() -> None:
    symbols = ([0, 1, 2, 0, 1, 3, 0, 1, 2, 0, 1, 4] * 40)[:401]
    renamed = [((value * 7) + 3) % 25 for value in symbols]
    order = (2, 0, 3, 1)
    first = _encode_coordinates(columnar_encipher(_pair_stream(symbols), order))
    second = _encode_coordinates(columnar_encipher(_pair_stream(renamed), order))
    permutations = _permutations(4)
    first_scores = order2_over_order1_scores(first, permutations, 0.7, 0.5, 5.0)
    second_scores = order2_over_order1_scores(second, permutations, 0.7, 0.5, 5.0)
    correct_index = next(
        index for index, permutation in enumerate(permutations) if tuple(permutation) == order
    )
    assert np.isclose(first_scores[correct_index], second_scores[correct_index])


def test_pairwise_auc_and_sign_null() -> None:
    natural = [0.5, 0.6, 0.7, 0.8]
    control = [0.1, 0.2, 0.3, 0.4]
    assert _paired_auc(natural, control) == 1.0
    p_value, null_mean = _sign_permutation_p(
        [left - right for left, right in zip(natural, control, strict=True)],
        255,
        11,
    )
    assert 0 < p_value <= 1
    assert abs(null_mean) < 0.1


def test_review_record_drops_query_level_text_and_keeps_failure() -> None:
    result = {
        "experiment_id": "E-009-ciphertext-only-structure",
        "hypothesis_id": "H-009",
        "status": "fail",
        "target_scored": False,
        "plaintext_supplied_to_scorer": False,
        "metrics": {},
        "adversarial_diagnostics": {},
        "gates": {"scientific": False},
        "permutation": {},
        "runtime": {},
        "provenance": {},
        "query_audit": [
            {
                "family": family,
                "true_order_raw_score": score,
                "maximizing_widths": [4],
                "true_width": 5,
                "text": "DO NOT SEND",
            }
            for family, score in (("natural", 0.2), ("unigram_shuffle", 0.1))
        ],
    }
    record = bounded_record(result)
    assert record["status"] == "fail"
    assert "DO NOT SEND" not in orjson.dumps(record).decode()
