"""Reversible integer-sequence cipher transforms for controlled experiments."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def polyalphabetic(
    values: Sequence[int], key: Sequence[int], modulus: int, *, decrypt: bool = False
) -> np.ndarray:
    """Apply a repeating modular key (Vigenere-like over an arbitrary alphabet)."""
    if modulus < 2 or not key:
        raise ValueError("modulus must be >= 2 and key must not be empty")
    sign = -1 if decrypt else 1
    return np.asarray(
        [(int(value) + sign * int(key[i % len(key)])) % modulus for i, value in enumerate(values)],
        dtype=np.int64,
    )


def progressive_key(
    values: Sequence[int],
    key: Sequence[int],
    modulus: int,
    *,
    step: int,
    progression: str = "per-cycle",
    decrypt: bool = False,
) -> np.ndarray:
    """Apply an explicitly defined per-symbol or per-key-cycle progressive shift."""
    if modulus < 2 or not key:
        raise ValueError("modulus must be >= 2 and key must not be empty")
    if progression not in {"per-symbol", "per-cycle"}:
        raise ValueError("progression must be 'per-symbol' or 'per-cycle'")
    sign = -1 if decrypt else 1
    period = len(key)
    result = []
    for index, value in enumerate(values):
        epoch = index if progression == "per-symbol" else index // period
        shift = int(key[index % period]) + step * epoch
        result.append((int(value) + sign * shift) % modulus)
    return np.asarray(result, dtype=np.int64)


def homophonic_encrypt(
    values: Sequence[int], mapping: dict[int, Sequence[int]], choices: Sequence[int]
) -> np.ndarray:
    """Encrypt using caller-recorded homophone choices for deterministic reproduction."""
    if len(values) != len(choices):
        raise ValueError("one recorded choice is required per input symbol")
    output = []
    for value, choice in zip(values, choices, strict=True):
        candidates = mapping.get(int(value))
        if not candidates:
            raise ValueError(f"no homophones configured for symbol {value}")
        output.append(int(candidates[int(choice) % len(candidates)]))
    return np.asarray(output, dtype=np.int64)


def invert_homophonic_mapping(mapping: dict[int, Sequence[int]]) -> dict[int, int]:
    """Build the unique inverse mapping; reject overlapping cipher symbols."""
    inverse: dict[int, int] = {}
    for plain, cipher_values in mapping.items():
        for cipher in cipher_values:
            if int(cipher) in inverse:
                raise ValueError(f"cipher symbol {cipher} maps to multiple plaintext symbols")
            inverse[int(cipher)] = int(plain)
    return inverse


def homophonic_decrypt(values: Sequence[int], mapping: dict[int, Sequence[int]]) -> np.ndarray:
    inverse = invert_homophonic_mapping(mapping)
    try:
        return np.asarray([inverse[int(value)] for value in values], dtype=np.int64)
    except KeyError as exc:
        raise ValueError(f"unknown cipher symbol: {exc.args[0]}") from exc
