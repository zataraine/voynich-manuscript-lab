"""Repeated finite-size null diagnostics, without calibration or significance labels."""

from __future__ import annotations

import hashlib
import statistics
from collections.abc import Sequence
from typing import Any

from manuscript_lab.measurement_battery import (
    MeasurementBattery,
    MeasurementError,
    MeasurementRecord,
    measure_core,
    measurement_support,
    structural_nulls,
)


def measure_null_ensemble(
    records: Sequence[MeasurementRecord],
    *,
    battery: MeasurementBattery,
    seed: int,
    replicates: int,
) -> dict[str, Any]:
    """Retain raw draws, definedness and unscaled observed-minus-null differences.

    Matching source layout and length does not make these universal bias
    corrections. No percentile, z-score, p-value or compatibility label is
    produced. The outer draws include inner compression shuffles, whose seed
    and replicate count remain fixed by the battery contract.
    """
    if not isinstance(replicates, int) or isinstance(replicates, bool) or replicates < 2:
        raise MeasurementError("null ensembles require at least two integer replicates")
    observed = measure_core(records, battery=battery, seed=seed)
    observed_support = measurement_support(records, battery=battery)
    names = list(battery.config["metric_rules"])
    families = battery.config["null_families"]
    draws: dict[str, dict[str, list[float | None]]] = {
        family: {name: [] for name in names} for family in families
    }
    replicate_seeds = [
        int.from_bytes(
            hashlib.sha256(f"null-ensemble-v1:{seed}:{index}".encode()).digest()[:8], "big"
        )
        for index in range(replicates)
    ]
    for replicate_seed in replicate_seeds:
        nulls = structural_nulls(records, seed=replicate_seed)
        if set(nulls) != set(families):
            raise MeasurementError("null implementations differ from battery config")
        for family in families:
            metrics = measure_core(nulls[family], battery=battery, seed=replicate_seed)
            support = measurement_support(nulls[family], battery=battery)
            for name in names:
                draws[family][name].append(
                    None if name in support["undefined_metrics"] else metrics[name]
                )
    summaries = {}
    for family in families:
        summaries[family] = {}
        for name in names:
            samples = draws[family][name]
            defined = [sample for sample in samples if sample is not None]
            mean = statistics.mean(defined) if defined else None
            is_observed_defined = name not in observed_support["undefined_metrics"]
            summaries[family][name] = {
                "samples": samples,
                "defined_replicates": len(defined),
                "null_mean": mean,
                "null_sample_sd": statistics.stdev(defined) if len(defined) > 1 else None,
                "observed_minus_null_mean": observed[name] - mean
                if is_observed_defined and mean is not None
                else None,
            }
    return {
        "diagnostic_id": "null-ensemble-v1",
        "battery_id": battery.battery_id,
        "battery_sha256": battery.sha256,
        "base_seed": seed,
        "replicate_seeds": replicate_seeds,
        "replicates": replicates,
        "metric_order": names,
        "observed": observed,
        "observed_support": observed_support,
        "families": summaries,
        "decision": "not_calibrated",
    }
