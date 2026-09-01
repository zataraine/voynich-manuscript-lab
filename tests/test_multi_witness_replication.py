from __future__ import annotations

from manuscript_lab.multi_witness_replication import encode_atomic_groups, evaluate_replication


def test_atomic_transport_is_bijective() -> None:
    source = {
        "a": {"p1": (("A1", "B1"), ("<UNK1>",))},
        "b": {"p1": (("B1", "A1"),)},
    }
    encoded, symbol_map, roundtrip = encode_atomic_groups(source)

    assert roundtrip == 1.0
    assert len(symbol_map) == 3
    assert len(encoded["a"]["p1"][0]) == 2
    assert encoded["a"]["p1"][0] != encoded["b"]["p1"][0]


def test_worst_view_conjunction_and_holm_are_strict() -> None:
    config = {
        "metrics": {
            "primary": ["m"],
            "maximum_adjusted_p": 0.05,
            "replicated_effects": [
                {"id": "R1", "family": "f", "metric": "m"},
                {"id": "R2", "family": "g", "metric": "m"},
            ],
        }
    }
    observed = {"v1": {"m": 2.0}, "v2": {"m": 2.0}}
    low = [0.0] * 99
    mixed = {"v1": low, "v2": [3.0, *([0.0] * 98)]}
    samples = {
        "v1": {
            "f": {"m": low},
            "g": {"m": low},
            "copy_mutate_pseudotext": {"m": low},
        },
        "v2": {
            "f": {"m": mixed["v2"]},
            "g": {"m": low},
            "copy_mutate_pseudotext": {"m": low},
        },
    }
    _, effects, _ = evaluate_replication(config, observed, samples)

    assert effects["R1"]["conjunction_raw_p"] == 0.02
    assert effects["R1"]["holm_adjusted_conjunction_p"] == 0.02
    assert effects["R2"]["holm_adjusted_conjunction_p"] == 0.02
    assert effects["R1"]["passed"]


def test_negative_effect_fails_even_with_small_p() -> None:
    config = {
        "metrics": {
            "primary": ["m"],
            "maximum_adjusted_p": 0.05,
            "replicated_effects": [{"id": "R1", "family": "f", "metric": "m"}],
        }
    }
    observed = {"v1": {"m": -1.0}}
    sparse_high_tail = [200.0, *([-2.0] * 98)]
    samples = {
        "v1": {
            "f": {"m": sparse_high_tail},
            "copy_mutate_pseudotext": {"m": [-2.0] * 99},
        }
    }
    _, effects, _ = evaluate_replication(config, observed, samples)

    assert effects["R1"]["conjunction_raw_p"] == 0.02
    assert not effects["R1"]["all_effects_positive"]
    assert not effects["R1"]["passed"]
