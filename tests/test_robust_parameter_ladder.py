from __future__ import annotations

import numpy as np
import pytest

from manuscript_lab.cipher_transforms import apply_transform_variant
from manuscript_lab.robust_parameter_ladder import (
    select_invariant_features,
    validate_variants,
)

TOKENS = ("alpha", "beta", "alpha", "gamma") * 10


@pytest.mark.parametrize(
    ("variant", "expected_multiplier"),
    [
        (
            {"id": "h2", "family": "homophonic", "parameters": {"homophones": 2}},
            1,
        ),
        (
            {"id": "v3", "family": "verbose_homophonic", "parameters": {"width": 3}},
            3,
        ),
    ],
)
def test_parameterized_variants_are_seeded(
    variant: dict[str, object], expected_multiplier: int
) -> None:
    first = apply_transform_variant(TOKENS, variant, seed=31, sample_id="sample")
    second = apply_transform_variant(TOKENS, variant, seed=31, sample_id="sample")
    assert first == second
    assert all(
        len(encoded) == len(plain) * expected_multiplier
        for plain, encoded in zip(TOKENS, first, strict=True)
    )


def test_selector_prefers_stable_separation_and_ignores_unlisted_matrix() -> None:
    labels = np.asarray([0, 0, 1, 1])
    train = np.arange(4)
    matrices = {
        "a": np.asarray([[0.0, 0.0], [0.0, 0.0], [2.0, 10.0], [2.0, 10.0]]),
        "b": np.asarray([[0.0, 10.0], [0.0, 10.0], [2.0, 0.0], [2.0, 0.0]]),
        "heldout": np.asarray([[999.0, 0.0]] * 4),
    }
    selected, _ = select_invariant_features(
        matrices, labels, train, ["a", "b"], ["stable", "unstable"], count=1
    )
    assert selected.tolist() == [0]
    matrices["heldout"][:] = -999.0
    repeated, _ = select_invariant_features(
        matrices, labels, train, ["a", "b"], ["stable", "unstable"], count=1
    )
    assert repeated.tolist() == selected.tolist()


def test_variant_registry_requires_every_family() -> None:
    with pytest.raises(ValueError, match="complete transform registry"):
        validate_variants([{"id": "only", "family": "identity"}])
