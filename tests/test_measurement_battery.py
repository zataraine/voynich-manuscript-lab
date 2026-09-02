from __future__ import annotations

import math

from manuscript_lab.measurement_battery import (
    MeasurementRecord,
    fit_learned_units,
    load_measurement_battery,
    measure_core,
    measure_learned_units,
    measure_training_heldout,
    structural_nulls,
)


def _records(offset: int = 0) -> tuple[MeasurementRecord, ...]:
    return tuple(
        MeasurementRecord(
            record_id=f"r{index}",
            page=f"p{index // 2}",
            section="A" if index < 2 else "B",
            line_index=index,
            groups=(
                (offset + 1, offset + 2),
                (offset + 2, offset + 1),
                (offset + 1, offset + 2),
                (offset + 3, offset + index % 2),
            ),
            boundaries=("certain", "uncertain", "certain"),
        )
        for index in range(4)
    )


def test_battery_is_finite_ordered_and_rename_invariant() -> None:
    battery = load_measurement_battery()
    records = _records()
    renamed = tuple(
        MeasurementRecord(
            **{
                **record.__dict__,
                "groups": tuple(tuple(symbol + 100 for symbol in group) for group in record.groups),
            }
        )
        for record in records
    )
    first = measure_core(records, battery=battery, seed=17)
    second = measure_core(renamed, battery=battery, seed=17)
    assert list(first) == list(battery.config["metric_rules"])
    assert first == second
    assert all(math.isfinite(value) for value in first.values())


def test_structural_nulls_are_seeded_and_change_order_sensitive_measurements() -> None:
    battery = load_measurement_battery()
    records = _records()
    first = structural_nulls(records, seed=23)
    second = structural_nulls(records, seed=23)
    assert first == second
    observed = measure_core(records, battery=battery, seed=23)
    shuffled = measure_core(first["group_order_shuffle"], battery=battery, seed=23)
    assert observed["compression_shuffle_gain"] != shuffled["compression_shuffle_gain"]


def test_learned_units_are_fit_only_on_training_records() -> None:
    battery = load_measurement_battery()
    training, heldout = _records()[:2], _records()[2:]
    merges = fit_learned_units(training, merge_count=16)
    changed_heldout = _records(100)[2:]
    assert merges == fit_learned_units(training, merge_count=16)
    original = measure_learned_units(heldout, merges=merges)
    changed = measure_learned_units(changed_heldout, merges=merges)
    assert original != changed
    result = measure_training_heldout(training * 2, heldout * 2, battery=battery, seed=29)
    assert result["battery_sha256"] == battery.sha256
    assert set(result["learned_units"]) == {"16", "32", "64", "128"}
