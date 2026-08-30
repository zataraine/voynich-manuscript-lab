"""Seeded, explicit control transforms for cipher-domain transfer tests."""

from __future__ import annotations

import hashlib
import random
from collections import Counter
from collections.abc import Sequence

PUA_START = 0xE000


def _seed(seed: int, transform: str, sample_id: str) -> int:
    payload = f"{seed}\0{transform}\0{sample_id}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _alphabet(tokens: Sequence[str]) -> list[str]:
    return sorted({character for token in tokens for character in token})


def _symbols(count: int, *, offset: int = 0) -> list[str]:
    if count < 1 or PUA_START + offset + count >= 0xF8FF:
        raise ValueError("Requested cipher alphabet is outside the private-use range")
    return [chr(PUA_START + offset + index) for index in range(count)]


def monoalphabetic(tokens: Sequence[str], *, seed: int, sample_id: str) -> tuple[str, ...]:
    """Apply a document-specific random bijection over observed characters."""
    source = _alphabet(tokens)
    target = _symbols(len(source))
    random.Random(_seed(seed, "monoalphabetic", sample_id)).shuffle(target)
    mapping = dict(zip(source, target, strict=True))
    return tuple("".join(mapping[character] for character in token) for token in tokens)


def homophonic(
    tokens: Sequence[str], *, seed: int, sample_id: str, homophones: int = 3
) -> tuple[str, ...]:
    """Map each source character to one of a fixed number of seeded homophones."""
    if homophones < 1:
        raise ValueError("homophones must be positive")
    source = _alphabet(tokens)
    target = _symbols(len(source) * homophones)
    choices = {
        character: target[index * homophones : index * homophones + homophones]
        for index, character in enumerate(source)
    }
    rng = random.Random(_seed(seed, "homophonic", sample_id))
    return tuple("".join(rng.choice(choices[character]) for character in token) for token in tokens)


def progressive_polyalphabetic(
    tokens: Sequence[str], *, seed: int, sample_id: str, period: int = 7, step: int = 3
) -> tuple[str, ...]:
    """Apply per-cycle progressive polyalphabetic shifts without changing boundaries."""
    source = _alphabet(tokens)
    modulus = len(source)
    index = {character: position for position, character in enumerate(source)}
    target = _symbols(modulus)
    rng = random.Random(_seed(seed, "progressive_polyalphabetic", sample_id))
    key = [rng.randrange(modulus) for _ in range(period)]
    position = 0
    output = []
    for token in tokens:
        encoded = []
        for character in token:
            shift = key[position % period] + step * (position // period)
            encoded.append(target[(index[character] + shift) % modulus])
            position += 1
        output.append("".join(encoded))
    return tuple(output)


def nomenclator_homophonic(
    tokens: Sequence[str],
    *,
    seed: int,
    sample_id: str,
    codebook_size: int = 12,
    homophones: int = 3,
) -> tuple[str, ...]:
    """Code frequent whole tokens; homophonically substitute remaining characters."""
    counts = Counter(tokens)
    codewords = [token for token, count in counts.most_common(codebook_size) if count > 1]
    codes = _symbols(len(codewords), offset=1024)
    codebook = dict(zip(codewords, codes, strict=True))
    substituted = homophonic(
        tokens, seed=seed, sample_id=f"{sample_id}:fallback", homophones=homophones
    )
    return tuple(
        codebook.get(token, fallback) for token, fallback in zip(tokens, substituted, strict=True)
    )


def verbose_homophonic(
    tokens: Sequence[str], *, seed: int, sample_id: str, width: int = 2
) -> tuple[str, ...]:
    """Encode every character as a seeded fixed-width code group."""
    if width < 2:
        raise ValueError("verbose code width must be at least two")
    source = _alphabet(tokens)
    columns = [
        _symbols(max(11, len(source)), offset=2048 + column * 1024) for column in range(width)
    ]
    rng = random.Random(_seed(seed, "verbose_homophonic", sample_id))
    base = {character: [rng.randrange(len(column)) for column in columns] for character in source}
    output = []
    occurrence: Counter[str] = Counter()
    for token in tokens:
        encoded = []
        for character in token:
            origins = base[character]
            encoded.extend(
                column[(origin + occurrence[character] * (index + 1)) % len(column)]
                for index, (column, origin) in enumerate(zip(columns, origins, strict=True))
            )
            occurrence[character] += 1
        output.append("".join(encoded))
    return tuple(output)


TRANSFORMS = {
    "identity": lambda tokens, **_kwargs: tuple(tokens),
    "monoalphabetic": monoalphabetic,
    "homophonic": homophonic,
    "progressive_polyalphabetic": progressive_polyalphabetic,
    "nomenclator_homophonic": nomenclator_homophonic,
    "verbose_homophonic": verbose_homophonic,
}


def apply_transform(
    tokens: Sequence[str], family: str, *, seed: int, sample_id: str
) -> tuple[str, ...]:
    """Apply one named transform through the fixed campaign registry."""
    try:
        function = TRANSFORMS[family]
    except KeyError as exc:
        raise ValueError(f"Unknown cipher transform: {family}") from exc
    return function(tokens, seed=seed, sample_id=sample_id)


def apply_transform_variant(
    tokens: Sequence[str], variant: dict[str, object], *, seed: int, sample_id: str
) -> tuple[str, ...]:
    """Apply a validated parameterized transform variant from an experiment config."""
    family = str(variant["family"])
    try:
        function = TRANSFORMS[family]
    except KeyError as exc:
        raise ValueError(f"Unknown cipher transform: {family}") from exc
    replicate = int(variant.get("replicate", 0))
    parameters = variant.get("parameters", {})
    if not isinstance(parameters, dict):
        raise TypeError("Transform variant parameters must be a mapping")
    variant_seed = seed + replicate * 1_000_003
    variant_id = str(variant.get("id", family))
    return function(
        tokens,
        seed=variant_seed,
        sample_id=f"{sample_id}:{variant_id}",
        **parameters,
    )


def destroy_token_order(tokens: Sequence[str], *, seed: int, sample_id: str) -> tuple[str, ...]:
    """Seed-shuffle token order while preserving the complete token multiset."""
    values = list(tokens)
    random.Random(_seed(seed, "destroy_token_order", sample_id)).shuffle(values)
    return tuple(values)
