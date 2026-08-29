from __future__ import annotations

import numpy as np
import pytest

from manuscript_lab.cryptanalysis.ciphers import (
    homophonic_decrypt,
    homophonic_encrypt,
    polyalphabetic,
    progressive_key,
)
from manuscript_lab.cryptanalysis.statistics import (
    index_of_coincidence,
    lag_coincidence,
    periodic_slice_ic,
    repeated_ngram_spacings,
    shannon_entropy,
)


def test_sequence_statistics_known_values() -> None:
    values = [0, 0, 1, 1]
    assert index_of_coincidence(values) == pytest.approx(1 / 3)
    assert shannon_entropy(values) == pytest.approx(1.0)
    assert lag_coincidence([1, 2, 1, 2], 2)[2] == 1.0
    assert periodic_slice_ic([1, 2] * 8, 2)[2] == 1.0
    assert repeated_ngram_spacings([1, 2, 1, 2, 1], 2)[(1, 2)] == [2]


def test_polyalphabetic_round_trip() -> None:
    plain = [0, 1, 4, 3, 2, 1]
    encrypted = polyalphabetic(plain, [2, 4], 5)
    assert np.array_equal(polyalphabetic(encrypted, [2, 4], 5, decrypt=True), plain)


@pytest.mark.parametrize("progression", ["per-symbol", "per-cycle"])
def test_progressive_key_round_trip(progression: str) -> None:
    plain = [0, 1, 4, 3, 2, 1]
    encrypted = progressive_key(plain, [2, 4], 7, step=3, progression=progression)
    decrypted = progressive_key(encrypted, [2, 4], 7, step=3, progression=progression, decrypt=True)
    assert np.array_equal(decrypted, plain)


def test_progression_definitions_are_not_interchangeable() -> None:
    values = [0] * 6
    per_symbol = progressive_key(values, [1, 2], 11, step=1, progression="per-symbol")
    per_cycle = progressive_key(values, [1, 2], 11, step=1, progression="per-cycle")
    assert not np.array_equal(per_symbol, per_cycle)


def test_homophonic_round_trip_and_overlap_rejection() -> None:
    mapping = {0: [10, 11], 1: [20, 21, 22]}
    encrypted = homophonic_encrypt([0, 1, 1, 0], mapping, [0, 1, 2, 1])
    assert np.array_equal(homophonic_decrypt(encrypted, mapping), [0, 1, 1, 0])
    with pytest.raises(ValueError, match="multiple"):
        homophonic_decrypt([10], {0: [10], 1: [10]})
