from __future__ import annotations

from dataclasses import replace

import pytest

from manuscript_lab.layout_measurements import METRICS, measure_layout
from manuscript_lab.measurement_battery import (
    MeasurementError,
    MeasurementRecord,
    load_measurement_battery,
    measure_core,
    measure_page_compression,
    structural_nulls,
)


def _records():
    return tuple(
        MeasurementRecord(
            record_id=f"p{page}-line{line}",
            page=f"p{page}",
            section=None,
            line_index=line,
            groups=((0,) * (line + 1),),
            boundaries=(),
            paragraph_id="paragraph-a",
            paragraph_line_index=line,
            session_id=f"session-{page}",
            session_index=page,
        )
        for page in range(4)
        for line in range(3)
    )


def test_paragraph_positive_negative_and_missing_annotations() -> None:
    battery = load_measurement_battery()
    records = _records()
    positive = measure_layout(records, battery=battery, seed=11)
    negative = measure_layout(
        tuple(replace(r, paragraph_line_index=2 - r.paragraph_line_index) for r in records),
        battery=battery,
        seed=11,
    )
    assert positive["metrics"][METRICS[0]] == pytest.approx(1)
    assert negative["metrics"][METRICS[0]] == pytest.approx(-1)
    assert positive["support"]["eligible_paragraph_count"] == 4
    missing = tuple(
        replace(
            r, paragraph_id=None, paragraph_line_index=None, session_id=None, session_index=None
        )
        for r in records
    )
    result = measure_layout(missing, battery=battery, seed=11)
    assert result["support"]["records_missing_paragraph"] == 12
    assert result["support"]["records_missing_session"] == 12
    assert all(name in result["support"]["undefined_metrics"] for name in METRICS[:3])


def test_paragraphs_are_averaged_without_pooling_between_paragraph_length_offsets() -> None:
    # Opposing within-paragraph slopes must cancel even with a large offset.
    records = tuple(
        replace(
            r,
            groups=((0,) * (r.line_index + 1 if r.session_index % 2 == 0 else 100 - r.line_index),),
        )
        for r in _records()
    )
    result = measure_layout(records, battery=load_measurement_battery(), seed=13)
    assert result["metrics"][METRICS[0]] == pytest.approx(0)


def test_longitudinal_drift_uses_explicit_sessions_and_ignores_label_names() -> None:
    battery = load_measurement_battery()
    records = tuple(
        replace(r, groups=((r.session_index,) * (r.session_index + 1),)) for r in _records()
    )
    first = measure_layout(records, battery=battery, seed=17)
    renamed = tuple(
        replace(r, session_id=f"opaque-{10 - r.session_index}") for r in reversed(records)
    )
    second = measure_layout(renamed, battery=battery, seed=17)
    assert first["metrics"][METRICS[1]] == pytest.approx(1)
    assert first["metrics"][METRICS[2]] == pytest.approx(1)
    assert [second["metrics"][name] for name in METRICS[1:3]] == [1, 1]
    stationary = tuple(replace(r, groups=((0,),)) for r in records)
    result = measure_layout(stationary, battery=battery, seed=17)
    assert result["metrics"][METRICS[1]] == 0
    assert METRICS[2] in result["support"]["undefined_metrics"]


@pytest.mark.parametrize(
    "failure", ["partial", "negative", "duplicate-line", "conflicting-session", "aliased-session"]
)
def test_invalid_annotation_relationships_are_rejected(failure) -> None:
    records = list(_records())
    with pytest.raises(MeasurementError):
        if failure == "partial":
            records[0] = replace(records[0], paragraph_id=None)
        elif failure == "negative":
            records[0] = replace(records[0], session_index=-1)
        elif failure == "duplicate-line":
            records[0] = replace(records[0], paragraph_line_index=1)
        elif failure == "conflicting-session":
            records[0] = replace(records[0], session_index=100)
        else:
            records[0] = replace(records[0], session_id="another-session")
        measure_layout(records, battery=load_measurement_battery(), seed=19)


def test_structural_nulls_retain_layout_annotations() -> None:
    records = _records()
    for generated in structural_nulls(records, seed=23).values():
        assert [
            (r.paragraph_id, r.paragraph_line_index, r.session_id, r.session_index)
            for r in generated
        ] == [
            (r.paragraph_id, r.paragraph_line_index, r.session_id, r.session_index) for r in records
        ]


@pytest.mark.parametrize("repeats", [16, 64])
def test_compression_recovers_ordered_runs_at_matched_lengths(repeats) -> None:
    battery = load_measurement_battery()
    records = tuple(
        replace(
            r,
            groups=tuple((unit,) for unit in range(4) for _ in range(repeats)),
            boundaries=("certain",) * (4 * repeats - 1),
        )
        for r in _records()[::3]
    )
    assert measure_core(records, battery=battery, seed=29)["compression_shuffle_gain"] > 0
    assert measure_page_compression(records, battery=battery, seed=29) > 0
    # Canonical equality-pattern coding has no order signal for unique groups.
    unique = tuple(
        replace(r, groups=tuple((page * 4 * repeats + i,) for i in range(4 * repeats)))
        for page, r in enumerate(records)
    )
    assert measure_core(unique, battery=battery, seed=29)["compression_shuffle_gain"] == 0
    assert measure_page_compression(unique, battery=battery, seed=29) == 0


def test_page_reset_exposes_pooled_concatenation_effect() -> None:
    battery = load_measurement_battery()
    records = tuple(
        replace(r, groups=((i,),) * 128, boundaries=("certain",) * 127)
        for i, r in enumerate(_records()[::3])
    )
    assert measure_core(records, battery=battery, seed=31)["compression_shuffle_gain"] > 0
    assert measure_page_compression(records, battery=battery, seed=31) == 0


def test_compression_is_invariant_to_arbitrary_unit_and_page_names() -> None:
    battery = load_measurement_battery()
    records = tuple(
        replace(r, groups=((0,), (0,), (1,), (2,)) * 8, boundaries=("certain",) * 31)
        for r in _records()[::3]
    )
    mapping = {0: 100, 1: 2, 2: 91}
    renamed = tuple(
        replace(
            r,
            page=f"opaque-{10 - i}",
            groups=tuple(tuple(mapping[u] for u in group) for group in r.groups),
        )
        for i, r in enumerate(records)
    )
    assert measure_page_compression(records, battery=battery, seed=37) == measure_page_compression(
        renamed, battery=battery, seed=37
    )
