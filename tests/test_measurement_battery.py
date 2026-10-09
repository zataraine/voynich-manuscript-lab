from __future__ import annotations

import math
import random
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from manuscript_lab.measurement_battery import (
    MeasurementError,
    MeasurementRecord,
    adapt_locus_projections,
    fit_learned_units,
    load_measurement_battery,
    measure_core,
    measure_finite_sample_profile,
    measure_learned_units,
    measure_training_heldout,
    measurement_support,
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
    assert set(first) == set(battery.config["null_families"])
    for name, null_records in first.items():
        assert [record.boundaries for record in null_records] == [
            record.boundaries for record in records
        ]
        assert [tuple(map(len, record.groups)) for record in null_records] == [
            tuple(map(len, record.groups)) for record in records
        ], name
    observed = measure_core(records, battery=battery, seed=23)
    shuffled = measure_core(first["group_order_shuffle"], battery=battery, seed=23)
    assert observed["compression_shuffle_gain"] != shuffled["compression_shuffle_gain"]


def test_finite_sample_profile_is_finite_and_stable_for_exact_balanced_control() -> None:
    battery = load_measurement_battery()
    records = tuple(
        MeasurementRecord(
            record_id=f"balanced-{index}",
            page=f"p{index // 4}",
            section="balanced",
            line_index=index,
            groups=((0,), (1,), (0,), (1,)),
            boundaries=("certain", "certain", "certain"),
        )
        for index in range(32)
    )
    profile = measure_finite_sample_profile(records, battery=battery, seed=31)
    assert [item["record_count"] for item in profile] == [4, 8, 16, 32]
    assert [item["metrics"]["unit_entropy_bits"] for item in profile] == [1.0] * 4
    assert all(math.isfinite(value) for item in profile for value in item["metrics"].values())


def test_known_order_signal_is_recovered_against_length_matched_iid_null() -> None:
    battery = load_measurement_battery()
    records = tuple(
        MeasurementRecord(
            record_id=f"order-{index}",
            page=f"p{index // 4}",
            section="order",
            line_index=index,
            groups=((0, 1, 0, 1), (0, 1, 0, 1)),
            boundaries=("certain",),
        )
        for index in range(16)
    )
    observed = measure_core(records, battery=battery, seed=37)
    null_records = structural_nulls(records, seed=37)["iid_symbol_length_matched"]
    null = measure_core(null_records, battery=battery, seed=37)
    assert observed["unit_entropy_bits"] == 1.0
    assert observed["conditional_unit_entropy_order1_bits"] == 0.0
    assert (
        null["conditional_unit_entropy_order1_bits"]
        > observed["conditional_unit_entropy_order1_bits"]
    )


def test_learned_units_are_fit_only_on_training_records() -> None:
    battery = load_measurement_battery()
    training, heldout = _records()[:2], _records()[2:]
    merges = fit_learned_units(training, merge_count=16)
    changed_heldout = _records(100)[2:]
    assert merges == fit_learned_units(training, merge_count=16)
    original = measure_learned_units(heldout, merges=merges)
    changed = measure_learned_units(changed_heldout, merges=merges)
    assert original != changed
    training = training + tuple(replace(r, record_id=f"copy-{r.record_id}") for r in training)
    heldout = heldout + tuple(replace(r, record_id=f"copy-{r.record_id}") for r in heldout)
    result = measure_training_heldout(training, heldout, battery=battery, seed=29)
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


def _control(
    groups: tuple[tuple[int, ...], ...],
    *,
    boundaries: tuple[str, ...] | None = None,
) -> tuple[MeasurementRecord, ...]:
    return tuple(
        MeasurementRecord(
            record_id=f"control-{index}",
            page=f"page-{index}",
            section=None,
            line_index=index,
            groups=groups,
            boundaries=boundaries if boundaries is not None else ("certain",) * (len(groups) - 1),
        )
        for index in range(4)
    )


def test_adjacency_never_creates_edges_between_records() -> None:
    battery = load_measurement_battery()
    # Within each record the groups differ, but every record join matches.
    records = tuple(
        replace(record, groups=((index % 2,), (1 - index % 2,)))
        for index, record in enumerate(_control(((0,), (1,))))
    )
    assert measure_core(records, battery=battery, seed=41)["adjacent_group_identity_rate"] == 0
    singletons = _control(((0,),))
    support = measurement_support(singletons, battery=battery)
    assert support["within_record_group_edge_count"] == 0
    assert "adjacent_group_identity_rate" in support["undefined_metrics"]


def test_edge_association_and_separator_identity_are_distinct() -> None:
    battery = load_measurement_battery()
    # Balanced binary edges: perfect dependence versus all four independent pairs.
    dependent = _control(((0,), (0,)))
    dependent = tuple(replace(r, groups=((i % 2,), (i % 2,))) for i, r in enumerate(dependent))
    independent = tuple(
        replace(r, groups=((i // 2,), (i % 2,))) for i, r in enumerate(_control(((0,), (0,))))
    )
    yes = measure_core(dependent, battery=battery, seed=43)
    no = measure_core(independent, battery=battery, seed=43)
    assert yes["cross_separator_edge_mi_bits"] == pytest.approx(1.0)
    assert no["cross_separator_edge_mi_bits"] == pytest.approx(0.0)
    # A constant separator class carries zero information about group identity.
    assert yes["separator_identity_mi_bits"] == pytest.approx(0.0)
    labelled = tuple(
        replace(r, boundaries=("same" if i in (0, 3) else "different",))
        for i, r in enumerate(independent)
    )
    assert measure_core(labelled, battery=battery, seed=43)[
        "separator_identity_mi_bits"
    ] == pytest.approx(1.0)


def test_analytic_entropy_vocabulary_and_recurrence_controls() -> None:
    battery = load_measurement_battery()
    records = _control(((0, 1, 0, 1), (0, 1, 0, 1)))
    metrics = measure_core(records, battery=battery, seed=47)
    assert metrics["unit_entropy_bits"] == pytest.approx(1.0)
    assert metrics["conditional_unit_entropy_order1_bits"] == pytest.approx(0.0)
    assert metrics["group_type_token_ratio"] == pytest.approx(1 / 8)
    assert metrics["singleton_type_ratio"] == pytest.approx(0.0)
    assert metrics["median_recurrence_distance"] == pytest.approx(1.0)
    assert metrics["adjacent_group_identity_rate"] == pytest.approx(1.0)
    unique = tuple(replace(r, groups=((i,),), boundaries=()) for i, r in enumerate(records))
    unique_metrics = measure_core(unique, battery=battery, seed=47)
    assert unique_metrics["group_type_token_ratio"] == 1.0
    assert unique_metrics["singleton_type_ratio"] == 1.0
    assert (
        "median_recurrence_distance"
        in measurement_support(unique, battery=battery)["undefined_metrics"]
    )


def test_drift_uses_supplied_order_and_is_invariant_to_partition_names() -> None:
    battery = load_measurement_battery()
    records = tuple(
        replace(r, page=f"p{i}", section=f"s{i}", groups=((int(i > 0),),))
        for i, r in enumerate(_control(((0,),)))
    )
    names = (1, 3, 0, 2)
    renamed = tuple(
        replace(r, page=f"p{names[i]}", section=f"s{names[i]}") for i, r in enumerate(records)
    )
    first = measure_core(records, battery=battery, seed=53)
    second = measure_core(renamed, battery=battery, seed=53)
    assert first["page_unigram_drift_js"] == pytest.approx(1 / 3)
    assert first["section_unigram_drift_js"] == pytest.approx(1 / 3)
    assert first == second


def test_learned_unit_ties_ignore_arbitrary_symbol_labels() -> None:
    records = _control(((0, 1, 2, 0),))
    mapping = {0: 9, 1: 2, 2: 0}
    renamed = tuple(
        replace(r, groups=tuple(tuple(mapping[u] for u in group) for group in r.groups))
        for r in records
    )
    for count in (1, 2, 3, 16):
        original = fit_learned_units(records, merge_count=count)
        other = fit_learned_units(renamed, merge_count=count)
        assert original[0] == (0, 1)
        assert other[0] == (9, 2)
        assert measure_learned_units(records, merges=original) == measure_learned_units(
            renamed, merges=other
        )


@pytest.mark.parametrize("overlap", ["page", "record", "duplicate"])
def test_training_heldout_rejects_leakage(overlap: str) -> None:
    records = _control(((0, 1),))
    heldout = tuple(
        replace(r, record_id=f"held-{r.record_id}", page=f"held-{r.page}") for r in records
    )
    if overlap == "page":
        heldout = (replace(heldout[0], page=records[0].page), *heldout[1:])
    elif overlap == "record":
        heldout = (replace(heldout[0], record_id=records[0].record_id), *heldout[1:])
    else:
        heldout = (heldout[0], heldout[0], *heldout[2:])
    with pytest.raises(MeasurementError, match=r"overlap|duplicate"):
        measure_training_heldout(records, heldout, battery=load_measurement_battery(), seed=59)


def test_historical_config_cannot_silently_use_corrected_metrics() -> None:
    with pytest.raises(MeasurementError, match="v1 is historical"):
        load_measurement_battery(Path("config/research/measurement-battery-v1.yaml"))


def test_line_position_known_positive_negative_and_degenerate_controls() -> None:
    battery = load_measurement_battery()
    increasing = tuple(
        replace(r, groups=((0,) * (i + 1),)) for i, r in enumerate(_control(((0,),)))
    )
    decreasing = tuple(replace(r, line_index=3 - i) for i, r in enumerate(increasing))
    constant = tuple(replace(r, line_index=0) for r in increasing)
    assert measure_core(increasing, battery=battery, seed=61)[
        "line_position_length_spearman"
    ] == pytest.approx(1.0)
    assert measure_core(decreasing, battery=battery, seed=61)[
        "line_position_length_spearman"
    ] == pytest.approx(-1.0)
    assert measure_core(constant, battery=battery, seed=61)["line_position_length_spearman"] == 0
    assert (
        "line_position_length_spearman"
        in measurement_support(constant, battery=battery)["undefined_metrics"]
    )


def test_context_domain_known_positive_and_negative_controls() -> None:
    battery = load_measurement_battery()
    positive = tuple(
        replace(r, groups=((i % 2,),) * 20, boundaries=("certain",) * 19)
        for i, r in enumerate(_control(((0,),)))
    )
    negative = tuple(replace(r, groups=((0,), (1,)) * 10) for r in positive)
    assert measure_core(positive, battery=battery, seed=67)[
        "contextual_block_mi_bits"
    ] == pytest.approx(1.0)
    assert measure_core(negative, battery=battery, seed=67)[
        "contextual_block_mi_bits"
    ] == pytest.approx(0.0)


def test_iid_finite_sample_entropy_converges_without_claiming_unbiasedness() -> None:
    battery = load_measurement_battery()
    rng = random.Random(71)
    # Deterministic software check against the analytic fair binary entropy.
    # A mean over fixed independent draws checks finite-size bias, not significance.
    for width, tolerance in ((16, 0.10), (1024, 0.005)):
        estimates = []
        for _ in range(16):
            records = tuple(
                replace(r, groups=(tuple(rng.randrange(2) for _ in range(width)),))
                for r in _control(((0,),))
            )
            metrics = measure_core(records, battery=battery, seed=71)
            estimates.append(metrics["unit_entropy_bits"])
            assert 0 <= metrics["conditional_unit_entropy_order1_bits"] <= 1
        assert 1 - tolerance < sum(estimates) / len(estimates) <= 1


def test_null_invariants_for_unequal_group_widths() -> None:
    records = _control(((0,), (1, 2), (2, 0, 1)))
    nulls = structural_nulls(records, seed=73)
    for name, generated in nulls.items():
        for before, after in zip(records, generated, strict=True):
            assert (before.record_id, before.page, before.section, before.line_index) == (
                after.record_id,
                after.page,
                after.section,
                after.line_index,
            )
            assert before.boundaries == after.boundaries
            if name == "group_order_shuffle":
                assert sorted(before.groups) == sorted(after.groups)
            else:
                assert tuple(map(len, before.groups)) == tuple(map(len, after.groups))
            if name == "within_group_unit_shuffle":
                assert [sorted(group) for group in before.groups] == [
                    sorted(group) for group in after.groups
                ]
