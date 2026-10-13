from __future__ import annotations

import random
from dataclasses import replace

import pytest

from manuscript_lab.measurement_battery import (
    MeasurementRecord,
    load_measurement_battery,
    measure_core,
)
from manuscript_lab.vocabulary_growth import measure_vocabulary_growth, validate_vocabulary_growth


def _record(values, page="p0", identity="r0"):
    groups = tuple((value,) for value in values)
    return MeasurementRecord(identity, page, None, 0, groups, ("certain",) * (len(groups) - 1))


@pytest.mark.parametrize("length", [2, 3, 16, 257])
def test_unique_and_constant_sequences_have_known_growth(length):
    unique = measure_vocabulary_growth([_record(range(length))])
    constant = measure_vocabulary_growth([_record([0] * length)])
    assert unique["pooled"]["metrics"]["second_half_novel_type_rate"] == 1
    assert unique["pooled"]["undefined_metrics"] == {
        "median_recurrence_distance": "no_repeated_groups_in_scope"
    }
    assert constant["pooled"]["metrics"] == {
        "second_half_novel_type_rate": 0,
        "median_recurrence_distance": 1,
    }
    assert constant["pooled"]["recurrence_gaps"] == [1] * (length - 1)
    validate_vocabulary_growth(unique)
    validate_vocabulary_growth(constant)


def test_order_matters_even_when_final_type_token_ratio_is_identical():
    early = measure_vocabulary_growth([_record([0, 1, 2, 0, 1, 2])])["pooled"]
    late = measure_vocabulary_growth([_record([0, 0, 0, 1, 2, 2])])["pooled"]
    assert early["type_count"] == late["type_count"] == 3
    assert early["metrics"]["second_half_novel_type_rate"] == 0
    assert late["metrics"]["second_half_novel_type_rate"] == pytest.approx(2 / 3)
    assert late["curve"] == [
        {"group_count": 1, "type_count": 1},
        {"group_count": 2, "type_count": 1},
        {"group_count": 3, "type_count": 1},
        {"group_count": 4, "type_count": 2},
        {"group_count": 6, "type_count": 3},
    ]


def test_page_resets_do_not_count_cross_page_recurrence():
    panel = measure_vocabulary_growth([_record([0], "z", "r0"), _record([0], "a", "r1")])
    assert panel["pooled"]["recurrence_gaps"] == [1]
    assert [entry["page"] for entry in panel["page_reset"]] == ["z", "a"]
    assert all(entry["summary"]["recurrence_gaps"] == [] for entry in panel["page_reset"])
    assert all(len(entry["summary"]["undefined_metrics"]) == 2 for entry in panel["page_reset"])


def test_noncontiguous_page_records_keep_relative_order_and_reset_only_by_page():
    records = [_record([0], "z", "r0"), _record([1], "a", "r1"), _record([0], "z", "r2")]
    panel = measure_vocabulary_growth(records)
    assert panel["pooled"]["recurrence_gaps"] == [2]
    assert panel["page_reset"][0]["summary"]["recurrence_gaps"] == [1]
    renamed = [replace(r, groups=tuple((99 - g[0],) for g in r.groups)) for r in records]
    assert measure_vocabulary_growth(renamed) == panel


def test_empty_input_is_explicitly_undefined():
    panel = measure_vocabulary_growth([])
    assert len(panel["pooled"]["undefined_metrics"]) == 2
    assert panel["pooled"]["curve"] == []
    assert panel["page_reset"] == []
    validate_vocabulary_growth(panel)


def test_growth_matches_naive_prefix_and_recurrence_oracles():
    rng = random.Random(185)
    values = [rng.randrange(17) for _ in range(301)]
    records = [
        _record(values[i : i + 43], f"p{i // 43}", f"r{i}") for i in range(0, len(values), 43)
    ]
    summary = measure_vocabulary_growth(records)["pooled"]
    assert summary["discovery_positions"] == [
        i + 1 for i, value in enumerate(values) if value not in values[:i]
    ]
    assert summary["recurrence_gaps"] == [
        i - max(j for j in range(i) if values[j] == value)
        for i, value in enumerate(values)
        if value in values[:i]
    ]
    for point in summary["curve"]:
        assert point["type_count"] == len(set(values[: point["group_count"]]))
    assert (
        summary["metrics"]["median_recurrence_distance"]
        == measure_core(records, battery=load_measurement_battery(), seed=4)[
            "median_recurrence_distance"
        ]
    )
