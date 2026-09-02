from __future__ import annotations

import math
from copy import deepcopy

import pytest

from manuscript_lab.measurement_battery import (
    MeasurementError,
    MeasurementRecord,
    adapt_locus_projections,
    fit_learned_units,
    load_measurement_battery,
    measure_core,
    measure_learned_units,
    measure_training_heldout,
    structural_nulls,
)
from manuscript_lab.representation_views import load_representation_registry, project_surface


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


def test_reversible_locus_projections_become_scoped_numeric_groups() -> None:
    spec = next(
        view
        for view in load_representation_registry().views
        if view.view_id == "sta1-atomic-structural"
    )
    projections = []
    for index, surface in enumerate(("A1B2,C3.D4", "A1,B2", "A1B2.C3", "<%>A1B2")):
        projection = project_surface(surface, spec, alphabet="STA1", witness_id="synthetic-a")
        projection["source"] = {
            "record_id": f"synthetic-a:locus:f1r.{index + 1}",
            "page": "f1r",
            "section": "H",
            "line_numbers": [index + 1],
        }
        projections.append(projection)
    adapted = adapt_locus_projections(projections)
    first = adapted["records"][0]
    assert [len(group) for group in first.groups] == [2, 1, 1]
    assert first.boundaries == ("uncertain_space", "certain_space")
    assert adapted["scope"]["witness_id"] == "synthetic-a"
    assert adapted["coverage"]["adapted_record_count"] == 4
    assert all(item["projection_sha256"] for item in adapted["record_provenance"])
    incompatible = deepcopy(projections)
    incompatible[-1]["witness_id"] = "synthetic-b"
    with pytest.raises(MeasurementError, match="cannot merge"):
        adapt_locus_projections(incompatible)
