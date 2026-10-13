from __future__ import annotations

import math
import random
import statistics
from collections import Counter

import pytest

from manuscript_lab.measurement_battery import (
    MeasurementError,
    MeasurementRecord,
    _conditional_entropy,
    _entropy,
    _js_divergence,
    _mutual_information,
    load_measurement_battery,
    measure_core,
)
from manuscript_lab.sampling_diagnostics import measure_null_ensemble


def _records():
    return tuple(
        MeasurementRecord(
            record_id=f"r{i}",
            page=f"p{i}",
            section=None,
            line_index=i,
            groups=((0,), (1,), (0,), (1,)),
            boundaries=("certain",) * 3,
        )
        for i in range(4)
    )


def test_null_ensemble_replays_without_normalizing_zero_variance() -> None:
    battery = load_measurement_battery()
    first = measure_null_ensemble(_records(), battery=battery, seed=103, replicates=8)
    assert first == measure_null_ensemble(_records(), battery=battery, seed=103, replicates=8)
    assert len(set(first["replicate_seeds"])) == 8
    for family in ("group_order_shuffle", "within_group_unit_shuffle"):
        summary = first["families"][family]["unit_entropy_bits"]
        assert summary["samples"] == [1.0] * 8
        assert summary["null_sample_sd"] == 0
        assert summary["observed_minus_null_mean"] == 0
    assert first["decision"] == "not_calibrated"


def test_undefined_measurements_never_become_zero_effect_estimates() -> None:
    result = measure_null_ensemble(
        _records(), battery=load_measurement_battery(), seed=107, replicates=4
    )
    for family in result["families"].values():
        summary = family["conditional_unit_entropy_order1_bits"]
        assert summary["samples"] == [None] * 4
        assert summary["defined_replicates"] == 0
        assert summary["null_mean"] is None
        assert summary["null_sample_sd"] is None
        assert summary["observed_minus_null_mean"] is None


@pytest.mark.parametrize("replicates", [0, 1, True, 2.5])
def test_invalid_ensemble_size_is_rejected(replicates) -> None:
    with pytest.raises(MeasurementError, match="integer replicates"):
        measure_null_ensemble(
            _records(), battery=load_measurement_battery(), seed=109, replicates=replicates
        )


def test_known_iid_sampling_bias_decreases_without_claiming_unbiasedness() -> None:
    # Fixed-seed software checks: independent fair bits have true H=H1=1, MI=JS=0.
    # Empirical plug-in estimators need not equal those population values.
    rng = random.Random(113)
    averages = {}
    for size in (16, 512):
        values = {"entropy": [], "conditional": [], "mi": [], "js": []}
        for _ in range(64):
            left = tuple(rng.randrange(2) for _ in range(size))
            right = tuple(rng.randrange(2) for _ in range(size))
            values["entropy"].append(_entropy(left))
            values["conditional"].append(_conditional_entropy((left,)))
            values["mi"].append(_mutual_information(zip(left, right, strict=True)))
            values["js"].append(_js_divergence(Counter(left), Counter(right)))
        averages[size] = {name: statistics.mean(samples) for name, samples in values.items()}
    for name in ("entropy", "conditional"):
        assert averages[16][name] < averages[512][name] <= 1
        assert averages[512][name] > 0.98
    for name in ("mi", "js"):
        assert 0 < averages[512][name] < averages[16][name]


def test_unique_groups_create_contextual_information_without_contextual_reuse() -> None:
    records = tuple(
        MeasurementRecord(
            record_id=f"r{i}",
            page=f"p{i}",
            section=None,
            line_index=i,
            groups=tuple((i * 10 + j,) for j in range(10)),
            boundaries=("certain",) * 9,
        )
        for i in range(4)
    )
    metrics = measure_core(records, battery=load_measurement_battery(), seed=127)
    # Every group uniquely identifies its block: positive MI is mechanically
    # inevitable even though no group repeats within or between the two blocks.
    assert metrics["contextual_block_mi_bits"] == pytest.approx(math.log2(2))
    assert metrics["singleton_type_ratio"] == 1
