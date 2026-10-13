from __future__ import annotations

from copy import deepcopy

import pytest

from manuscript_lab.layout_measurements import METRICS as LAYOUT_METRICS
from manuscript_lab.measurement_availability import assess_measurement_availability
from manuscript_lab.measurement_battery import (
    MeasurementRecord,
    load_measurement_battery,
    measure_learned_uncertainty,
)
from manuscript_lab.vocabulary_growth import measure_vocabulary_growth


def _policy_fixture():
    # Deliberately synthetic policy-input fixture, not a claimed research record.
    # Canonical builder/serializer enforcement is covered in test_measurement_records.
    battery = load_measurement_battery()
    records = tuple(
        MeasurementRecord(f"r{i}", f"p{i // 2}", "s", i, ((0,), (0,)), ("certain",))
        for i in range(4)
    )
    core = dict.fromkeys(battery.config["metric_rules"], 0.0)
    supported = {"undefined_metrics": {}, "records_missing_section": 0}
    layout = {
        "metrics": dict.fromkeys(LAYOUT_METRICS, 0.0),
        "support": {
            "undefined_metrics": {},
            "records_missing_paragraph": 0,
            "records_missing_session": 0,
            "ineligible_paragraphs": [],
        },
    }
    growth = measure_vocabulary_growth(records)
    uncertainty = measure_learned_uncertainty(records, merges=())
    result = {
        "battery_id": battery.battery_id,
        "battery_sha256": battery.sha256,
        "provenance": {"source_kind": "synthetic"},
        "coverage": {"missing_records": []},
        "split": {f"{split}_pages_without_usable_records": [] for split in ("training", "heldout")},
        "measurements": {
            "training": core,
            "heldout": core,
            "training_support": supported,
            "heldout_support": supported,
            "learned_units": {
                str(scale): {"uncertainty": {"training": uncertainty, "heldout": uncertainty}}
                for scale in battery.config["learned_unit_policy"]["merge_counts"]
            },
        },
        "nulls": {
            name: {"metrics": core, "support": supported}
            for name in battery.config["null_families"]
        },
        "layout": {
            "training": layout,
            "heldout": layout,
            "nulls": {name: layout for name in battery.config["null_families"]},
        },
        "vocabulary_growth": {
            "training": growth,
            "heldout": growth,
            "nulls": {name: growth for name in battery.config["null_families"]},
        },
    }
    return deepcopy(result)


def test_defined_zero_is_available_but_not_calibrated_or_authorized():
    result = assess_measurement_availability(_policy_fixture())
    assert result["status"] == "available_not_calibrated"
    assert result["reasons"] == []
    assert result["joint_comparison_allowed"] is False
    assert result["target_access"] == "forbidden"


@pytest.mark.parametrize(
    "failure",
    [
        "core",
        "learned",
        "growth",
        "layout",
        "annotations",
        "records",
        "pages",
        "legacy",
        "null",
        "singleton",
    ],
)
def test_any_missing_required_component_causes_abstention(failure):
    record = _policy_fixture()
    if failure == "core":
        record["measurements"]["heldout_support"]["undefined_metrics"] = {
            "unit_entropy_bits": "missing"
        }
    elif failure == "learned":
        del record["measurements"]["learned_units"]["128"]
    elif failure == "growth":
        record["vocabulary_growth"]["heldout"]["page_reset"][0]["summary"]["undefined_metrics"] = {
            "median_recurrence_distance": "no_repeats"
        }
    elif failure == "layout":
        del record["layout"]
    elif failure == "annotations":
        record["layout"]["training"]["support"]["records_missing_session"] = 1
    elif failure == "records":
        record["coverage"]["missing_records"] = [{"record_id": "absent"}]
    elif failure == "pages":
        record["split"]["heldout_pages_without_usable_records"] = ["absent"]
    elif failure == "legacy":
        del record["measurements"]["learned_units"]["16"]["uncertainty"]
    elif failure == "null":
        del record["nulls"]["group_order_shuffle"]
    else:
        record["measurements"]["heldout"]["singleton_type_ratio"] = 1
    result = assess_measurement_availability(record)
    assert result["status"] == "abstain"
    assert result["reasons"]
    assert result["joint_comparison_allowed"] is False


def test_availability_hash_ignores_only_its_own_audit():
    record = _policy_fixture()
    first = assess_measurement_availability(record)
    record["availability"] = first
    assert assess_measurement_availability(record) == first
    record["provenance"]["note"] = "changed"
    assert assess_measurement_availability(record)["input_sha256"] != first["input_sha256"]
