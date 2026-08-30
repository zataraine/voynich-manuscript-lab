"""Auditable surface-statistic panel for unknown-writing calibration."""

from __future__ import annotations

import math
import statistics
import zlib
from collections import Counter
from collections.abc import Sequence
from itertools import pairwise

import numpy as np
from rapidfuzz.distance import Levenshtein
from scipy.stats import skew


def _entropy(values: Sequence[str]) -> float:
    counts = Counter(values)
    total = len(values)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def _conditional_char_entropy(tokens: Sequence[str]) -> float:
    contexts: dict[str, Counter[str]] = {}
    total = 0
    for token in tokens:
        for left, right in zip("^" + token, token + "$", strict=True):
            contexts.setdefault(left, Counter())[right] += 1
            total += 1
    value = 0.0
    for outcomes in contexts.values():
        subtotal = sum(outcomes.values())
        value += (
            subtotal
            / total
            * -sum((count / subtotal) * math.log2(count / subtotal) for count in outcomes.values())
        )
    return value


def _safe_skew(values: Sequence[float]) -> float:
    return float(skew(values, bias=False)) if len(values) > 2 and len(set(values)) > 1 else 0.0


def _autocorrelation(values: Sequence[float]) -> float:
    if len(values) < 3 or statistics.pvariance(values) == 0:
        return 0.0
    left = np.asarray(values[:-1], dtype=float)
    right = np.asarray(values[1:], dtype=float)
    return float(np.corrcoef(left, right)[0, 1])


def _zipf_fit(counts: Counter[str]) -> tuple[float, float]:
    frequencies = sorted(counts.values(), reverse=True)
    if len(frequencies) < 3:
        return 0.0, 0.0
    x = np.log(np.arange(1, len(frequencies) + 1, dtype=float))
    y = np.log(np.asarray(frequencies, dtype=float))
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    denominator = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum((y - predicted) ** 2)) / denominator if denominator else 0.0
    return float(slope), r2


def extract_features(tokens: Sequence[str]) -> dict[str, float]:
    """Compute length-normalized features without assigning semantic meaning."""
    values = tuple(token for token in tokens if token)
    if len(values) < 20:
        raise ValueError("At least 20 tokens are required for stable feature extraction")
    lengths = [len(token) for token in values]
    token_counts = Counter(values)
    characters = tuple(character for token in values for character in token)
    char_counts = Counter(characters)
    token_bigrams = list(pairwise(values))
    repeats = sum(left == right for left, right in token_bigrams)
    triples = sum(
        values[index] == values[index - 1] == values[index - 2] for index in range(2, len(values))
    )
    char_repeats = sum(
        token[index] == token[index - 1] for token in values for index in range(1, len(token))
    )
    char_triples = sum(
        token[index] == token[index - 1] == token[index - 2]
        for token in values
        for index in range(2, len(token))
    )
    nearby = sum(
        Levenshtein.distance(left, right, score_cutoff=1) <= 1 for left, right in token_bigrams
    )
    encoded = " ".join(values).encode()
    zipf_slope, zipf_r2 = _zipf_fit(token_counts)
    return {
        "mean_token_length": statistics.mean(lengths),
        "token_length_std": statistics.pstdev(lengths),
        "token_length_skew": _safe_skew(lengths),
        "token_length_lag1": _autocorrelation(lengths),
        "token_type_ratio": len(token_counts) / len(values),
        "token_hapax_ratio": sum(count == 1 for count in token_counts.values()) / len(token_counts),
        "token_entropy_bits": _entropy(values),
        "token_repeat_rate": repeats / max(1, len(values) - 1),
        "token_triple_rate": triples / max(1, len(values) - 2),
        "adjacent_edit1_rate": nearby / max(1, len(values) - 1),
        "token_bigram_type_ratio": len(set(token_bigrams)) / max(1, len(token_bigrams)),
        "alphabet_size": float(len(char_counts)),
        "char_entropy_bits": _entropy(characters),
        "char_conditional_entropy_bits": _conditional_char_entropy(values),
        "char_repeat_rate": char_repeats / max(1, len(characters) - len(values)),
        "char_triple_rate": char_triples / max(1, len(characters) - 2 * len(values)),
        "compression_ratio": len(zlib.compress(encoded, 9)) / len(encoded),
        "zipf_loglog_slope": zipf_slope,
        "zipf_loglog_r2": zipf_r2,
        "most_common_token_rate": token_counts.most_common(1)[0][1] / len(values),
        "most_common_char_rate": char_counts.most_common(1)[0][1] / len(characters),
    }


def _mutual_information(pairs: Sequence[tuple[str, str]]) -> float:
    if not pairs:
        return 0.0
    joint = Counter(pairs)
    left = Counter(first for first, _second in pairs)
    right = Counter(second for _first, second in pairs)
    total = len(pairs)
    return sum(
        count / total * math.log2(count * total / (left[first] * right[second]))
        for (first, second), count in joint.items()
    )


def extract_sequence_features(tokens: Sequence[str]) -> dict[str, float]:
    """Extend the v1 panel with order and within-token positional measurements."""
    values = tuple(token for token in tokens if token)
    result = extract_features(values)
    token_pairs = list(pairwise(values))
    character_pairs = [pair for token in values for pair in pairwise(token)]
    length_pairs = [(str(len(left)), str(len(right))) for left, right in token_pairs]
    first = [token[0] for token in values]
    last = [token[-1] for token in values]
    local_matches = 0
    comparisons = 0
    for index, token in enumerate(values):
        recent = values[max(0, index - 20) : index]
        if not recent:
            continue
        comparisons += 1
        if any(Levenshtein.distance(token, candidate, score_cutoff=1) <= 1 for candidate in recent):
            local_matches += 1
    result.update(
        {
            "token_bigram_mutual_information": _mutual_information(token_pairs),
            "char_bigram_mutual_information": _mutual_information(character_pairs),
            "length_transition_mutual_information": _mutual_information(length_pairs),
            "token_trigram_type_ratio": len(set(zip(values, values[1:], values[2:], strict=False)))
            / max(1, len(values) - 2),
            "first_char_entropy_bits": _entropy(first),
            "last_char_entropy_bits": _entropy(last),
            "boundary_char_distribution_l1": sum(
                abs(first.count(character) / len(first) - last.count(character) / len(last))
                for character in set(first) | set(last)
            ),
            "window20_edit1_copy_rate": local_matches / comparisons if comparisons else 0.0,
        }
    )
    return result
