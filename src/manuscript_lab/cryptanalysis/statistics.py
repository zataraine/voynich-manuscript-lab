"""Assumption-light diagnostics for integer sequences."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Sequence
from itertools import pairwise


def shannon_entropy(values: Sequence[int]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def index_of_coincidence(values: Sequence[int]) -> float:
    size = len(values)
    if size < 2:
        return 0.0
    return sum(count * (count - 1) for count in Counter(values).values()) / (size * (size - 1))


def lag_coincidence(values: Sequence[int], max_lag: int) -> dict[int, float]:
    if max_lag < 1:
        raise ValueError("max_lag must be positive")
    return {
        lag: sum(a == b for a, b in zip(values[:-lag], values[lag:], strict=True))
        / (len(values) - lag)
        for lag in range(1, min(max_lag, len(values) - 1) + 1)
    }


def periodic_slice_ic(values: Sequence[int], max_period: int) -> dict[int, float]:
    if max_period < 1:
        raise ValueError("max_period must be positive")
    return {
        period: sum(index_of_coincidence(values[offset::period]) for offset in range(period))
        / period
        for period in range(1, min(max_period, len(values)) + 1)
    }


def repeated_ngram_spacings(values: Sequence[int], width: int) -> dict[tuple[int, ...], list[int]]:
    if width < 1:
        raise ValueError("width must be positive")
    positions: dict[tuple[int, ...], list[int]] = defaultdict(list)
    for index in range(max(0, len(values) - width + 1)):
        positions[tuple(int(value) for value in values[index : index + width])].append(index)
    return {
        gram: [b - a for a, b in pairwise(indices)]
        for gram, indices in positions.items()
        if len(indices) > 1
    }
