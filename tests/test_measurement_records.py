from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import replace

import orjson
import pytest

from manuscript_lab.measurement_battery import (
    MeasurementError,
    adapt_locus_projections,
    apply_learned_units,
    expand_learned_units,
    fit_learned_units,
    load_measurement_battery,
    measure_learned_uncertainty,
    measure_learned_units,
    restore_learned_merge_table,
)
from manuscript_lab.measurement_records import (
    build_control_measurement_record,
    canonical_measurement_bytes,
)
from manuscript_lab.representation_views import (
    RepresentationError,
    load_representation_registry,
    project_surface,
    verify_projection,
)
from manuscript_lab.vocabulary_growth import measure_vocabulary_growth

VIEWS = load_representation_registry().views


def _projections(spec, surface: str = "<%>A1B2,C3.[D4:E5]{F6G7}A1B2"):
    result = []
    for index in range(8):
        item = project_surface(surface, spec, alphabet="STA1", witness_id="synthetic-control")
        item["source"] = {
            "record_id": f"synthetic-control:r{index}",
            "page": f"p{index}",
            "line_numbers": [1],
            "section": "A" if index < 4 else "B",
        }
        result.append(item)
    return result


def _provenance():
    # Unit-test metadata only, never a claimed research acquisition.
    return {
        "source_kind": "synthetic",
        "source_manifest": "synthetic-fixture",
        "source_manifest_sha256": "0" * 64,
        "code_revision": "0" * 40,
        "working_tree_sha256": "0" * 64,
        "software_environment_sha256": "0" * 64,
        "device": "cpu",
        "output_path": "synthetic-fixture-result.json",
    }


def _build(projections, spec, **changes):
    kwargs = {
        "spec": spec,
        "training_pages": [f"p{i}" for i in range(4)],
        "heldout_pages": [f"p{i}" for i in range(4, 8)],
        "battery": load_measurement_battery(),
        "seed": 101,
        "provenance": _provenance(),
    }
    kwargs.update(changes)
    return build_control_measurement_record(projections, **kwargs)


@pytest.mark.parametrize("spec", VIEWS, ids=lambda view: view.view_id)
def test_every_registered_view_and_learned_scale_roundtrips(spec) -> None:
    projections = _projections(spec)
    for item in projections:
        verify_projection(item, spec)
    records = adapt_locus_projections(projections)["records"]
    base = tuple(tuple(unit for group in r.groups for unit in group) for r in records)
    for count in load_measurement_battery().config["learned_unit_policy"]["merge_counts"]:
        merges = fit_learned_units(records[:4], merge_count=count)
        encoded = apply_learned_units(records[4:], merges=merges)
        assert expand_learned_units(encoded) == base[4:]
        assert expand_learned_units(orjson.loads(orjson.dumps(encoded))) == base[4:]
        assert len(encoded) == 4


@pytest.mark.parametrize("spec", VIEWS, ids=lambda view: view.view_id)
def test_scoped_result_replays_byte_for_byte_through_json(spec) -> None:
    projections = _projections(spec)
    result = _build(projections, spec)
    encoded = canonical_measurement_bytes(result)
    assert encoded == canonical_measurement_bytes(_build(projections, spec))
    replay = orjson.loads(encoded)
    assert canonical_measurement_bytes(replay) == encoded
    assert replay["scope"]["view_id"] == spec.view_id
    assert replay["decision"] == "not_calibrated"
    assert replay["split"]["training_record_ids"] == [f"synthetic-control:r{i}" for i in range(4)]
    assert set(replay["nulls"]) == set(load_measurement_battery().config["null_families"])
    records = adapt_locus_projections(projections)["records"]
    assert replay["vocabulary_growth"]["training"] == measure_vocabulary_growth(records[:4])
    assert replay["vocabulary_growth"]["heldout"] == measure_vocabulary_growth(records[4:])
    for entry in replay["measurements"]["learned_units"].values():
        assert (
            entry["merge_table_sha256"]
            == hashlib.sha256(orjson.dumps(entry["merge_table"])).hexdigest()
        )

        merges = restore_learned_merge_table(entry["merge_table"])
        assert measure_learned_units(records[4:], merges=merges) == entry["heldout"]
        assert (
            measure_learned_uncertainty(records[4:], merges=merges)
            == entry["uncertainty"]["heldout"]
        )
        assert (
            measure_learned_uncertainty(records[:4], merges=merges)
            == entry["uncertainty"]["training"]
        )


def test_separator_and_ligature_views_have_declared_differences() -> None:
    by_id = {spec.view_id: spec for spec in VIEWS}
    expected = {
        "sta1-atomic-structural": (2, 1, 4),
        "sta1-atomic-first-alternative": (2, 1, 4),
        "sta1-atomic-ligature-decomposed": (2, 1, 5),
        "sta1-atomic-uncertain-internal": (3, 4),
        "sta1-atomic-space-erased": (7,),
    }
    for view_id, widths in expected.items():
        records = adapt_locus_projections(_projections(by_id[view_id]))["records"]
        assert tuple(map(len, records[0].groups)) == widths
        assert records[0].page == "p0"
        assert records[0].line_index == 1


def test_learned_unit_transfer_distinguishes_known_motif_from_unseen_inventory() -> None:
    spec = next(view for view in VIEWS if view.view_id == "sta1-atomic-space-erased")
    records = adapt_locus_projections(_projections(spec, "A1B2A1B2A1B2A1B2"))["records"]
    merges = fit_learned_units(records[:4], merge_count=16)
    matched = measure_learned_units(records[4:], merges=merges)
    unseen = tuple(replace(r, groups=((99, 100) * 4,)) for r in records[4:])
    assert matched["unit_count_ratio"] < 1
    assert measure_learned_units(unseen, merges=merges)["unit_count_ratio"] == 1


def test_result_records_expose_missing_loci_pages_and_metric_support() -> None:
    spec = VIEWS[2]
    projections = _projections(spec)
    missing = _projections(spec, "<%>")[0]
    missing["source"] = {"record_id": "empty-locus", "page": "p8", "line_numbers": [1]}
    projections.append(missing)
    result = _build(projections, spec, heldout_pages=["p4", "p5", "p6", "p7", "p8", "p9"])
    assert result["coverage"]["missing_records"] == [
        {"record_id": "empty-locus", "reason": "no_retained_group"}
    ]
    assert result["split"]["heldout_pages_without_usable_records"] == ["p8", "p9"]
    assert (
        "line_position_length_spearman"
        in result["measurements"]["heldout_support"]["undefined_metrics"]
    )


@pytest.mark.parametrize(
    "failure", ["mixed", "tampered", "unassigned", "duplicate", "target", "provenance", "scope"]
)
def test_result_interface_rejects_invalid_or_incomplete_inputs(failure) -> None:
    spec = VIEWS[2]
    projections = deepcopy(_projections(spec))
    changes = {}
    if failure == "mixed":
        projections[-1]["witness_id"] = "other"
    elif failure == "tampered":
        projections[-1]["observations"][0]["surface"] = "X9"
    elif failure == "unassigned":
        projections[-1]["source"]["page"] = "p99"
    elif failure == "duplicate":
        projections[-1]["source"]["record_id"] = projections[0]["source"]["record_id"]
    elif failure == "scope":
        projections[-1]["view_id"] = "invented"
    else:
        provenance = _provenance()
        if failure == "target":
            provenance["source_kind"] = "voynichese"
        else:
            del provenance["source_manifest_sha256"]
        changes["provenance"] = provenance
    with pytest.raises((MeasurementError, RepresentationError)):
        _build(projections, spec, **changes)


def test_invalid_unit_tree_cannot_masquerade_as_reversible_encoding() -> None:
    with pytest.raises(MeasurementError, match="invalid learned-unit tree"):
        expand_learned_units([[[1, 2, 3]]])


@pytest.mark.parametrize("failure", ["nonfinite", "metric", "table", "battery"])
def test_serialization_rejects_corrupted_results(failure) -> None:
    spec = VIEWS[2]
    result = _build(_projections(spec), spec)
    if failure == "nonfinite":
        result["measurements"]["heldout"]["unit_entropy_bits"] = float("nan")
    elif failure == "metric":
        del result["nulls"]["group_order_shuffle"]["metrics"]["unit_entropy_bits"]
    elif failure == "table":
        result["measurements"]["learned_units"]["16"]["merge_table_sha256"] = "0" * 64
    else:
        result["measurements"]["battery_sha256"] = "0" * 64
    with pytest.raises(MeasurementError):
        canonical_measurement_bytes(result)


def test_source_metadata_participates_in_replay_identity() -> None:
    spec = VIEWS[2]
    projections = _projections(spec)
    original = _build(projections, spec)
    projections[0]["source"]["line_numbers"] = [2]
    changed = _build(projections, spec)
    assert original["input_projections_sha256"] != changed["input_projections_sha256"]


def test_native_grapheme_and_codepoint_scales_preserve_the_same_surface() -> None:
    for spec, width in ((VIEWS[0], 2), (VIEWS[1], 1)):
        projections = _projections(spec, "a\u0301.b")
        for projection in projections:
            verify_projection(projection, spec)
        adapted = adapt_locus_projections(projections)
        record = adapted["records"][0]
        assert len(record.groups[0]) == width
        symbols = {item["id"]: item["surface"] for item in adapted["symbol_table"]}
        assert "".join(symbols[unit] for unit in record.groups[0]) == "a\u0301"


def test_layout_annotations_reach_serialized_results() -> None:
    spec = VIEWS[2]
    projections = _projections(spec)
    for index, projection in enumerate(projections):
        projection["source"].update(
            {
                "paragraph_id": "explicit-paragraph",
                "paragraph_line_index": 0,
                "session_id": f"session-{index}",
                "session_index": index,
            }
        )
    result = _build(projections, spec)
    assert result["layout"]["heldout"]["support"]["records_missing_session"] == 0
    assert result["layout"]["heldout"]["support"]["ordered_session_ids"] == [
        "session-4",
        "session-5",
        "session-6",
        "session-7",
    ]
    assert canonical_measurement_bytes(
        orjson.loads(canonical_measurement_bytes(result))
    ) == canonical_measurement_bytes(result)


def test_optional_null_ensemble_serializes_and_rejects_corrupt_summaries() -> None:
    spec = VIEWS[2]
    result = _build(_projections(spec), spec, null_replicates=4)
    encoded = canonical_measurement_bytes(result)
    assert canonical_measurement_bytes(orjson.loads(encoded)) == encoded
    result["null_ensemble"]["families"]["group_order_shuffle"]["unit_entropy_bits"]["null_mean"] = (
        999
    )
    with pytest.raises(MeasurementError, match="summaries do not replay"):
        canonical_measurement_bytes(result)


@pytest.mark.parametrize("failure", ["missing_metric", "nonfinite", "support", "scope"])
def test_learned_uncertainty_serialization_rejects_corruption(failure) -> None:
    spec = VIEWS[2]
    result = _build(_projections(spec), spec)
    panel = result["measurements"]["learned_units"]["16"]["uncertainty"]["heldout"]
    if failure == "missing_metric":
        del panel["metrics"]["unit_entropy_bits"]
    elif failure == "nonfinite":
        panel["metrics"]["unit_entropy_bits"] = float("nan")
    elif failure == "scope":
        panel["scope"] = "pooled"
    else:
        panel["support"]["learned_unit_count"] = 0
    with pytest.raises(MeasurementError):
        canonical_measurement_bytes(result)


def test_historical_records_without_learned_uncertainty_remain_readable() -> None:
    spec = VIEWS[2]
    result = _build(_projections(spec), spec)
    for entry in result["measurements"]["learned_units"].values():
        del entry["uncertainty"]
    assert canonical_measurement_bytes(result)


@pytest.mark.parametrize(
    "failure", ["metric", "events", "curve", "missingness", "page", "nonfinite"]
)
def test_growth_serialization_rejects_corrupted_summaries(failure):
    spec = VIEWS[2]
    result = _build(_projections(spec), spec)
    panel = result["vocabulary_growth"]["heldout"]
    summary = panel["pooled"]
    if failure == "metric":
        summary["metrics"]["second_half_novel_type_rate"] = 0.125
    elif failure == "events":
        summary["discovery_positions"].append(1)
    elif failure == "curve":
        summary["curve"][0]["type_count"] = 2
    elif failure == "missingness":
        summary["undefined_metrics"] = {"median_recurrence_distance": "invented"}
    elif failure == "nonfinite":
        summary["metrics"]["median_recurrence_distance"] = float("inf")
    else:
        panel["page_reset"][0]["page"] = panel["page_reset"][1]["page"]
    with pytest.raises(MeasurementError):
        canonical_measurement_bytes(result)


def test_historical_records_without_growth_remain_readable():
    spec = VIEWS[2]
    result = _build(_projections(spec), spec)
    del result["vocabulary_growth"]
    assert canonical_measurement_bytes(result)
