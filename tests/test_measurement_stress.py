from __future__ import annotations

from copy import deepcopy

import orjson
import pytest

from manuscript_lab.measurement_battery import MeasurementError
from manuscript_lab.measurement_stress import run_stress_suite


def _config():
    return {
        "suite_id": "measurement-stress-v1",
        "target_access": "forbidden",
        "numeric_absolute_tolerance": 1e-12,
        "record_counts": [4],
        "seeds": [211],
        "scenarios": [
            "constant",
            "unique",
            "binary_iid",
            "large_inventory_iid",
            "imbalanced_iid",
            "unequal_pages",
        ],
        "groups_per_record": 4,
        "annotation_masks": ["none", "alternating", "longest_lines"],
    }


@pytest.fixture(scope="module")
def diagnostic():
    return run_stress_suite(_config())


def test_joint_stress_cases_pass_and_replay(diagnostic):
    assert diagnostic["case_count"] == 6
    assert diagnostic["failed_checks"] == []
    assert diagnostic["phase4_complete"] is False
    assert diagnostic["decision"] == "software_diagnostics_only"
    first = orjson.dumps(diagnostic, option=orjson.OPT_SORT_KEYS)
    assert first == orjson.dumps(run_stress_suite(_config()), option=orjson.OPT_SORT_KEYS)
    assert orjson.loads(first)["cases"][0]["source_kind"] == "synthetic"


def test_masking_exposes_undefined_estimates_not_numeric_evidence(diagnostic):
    for case in diagnostic["cases"]:
        assert len(case["layout"]["support"]["undefined_metrics"]) == 0
        masked = case["annotation_masks"]["none"]
        assert masked["support"]["records_missing_paragraph"] == 4
        assert masked["support"]["records_missing_session"] == 4
        assert len(masked["support"]["undefined_metrics"]) == 3
        assert all(masked["metrics"][name] == 0 for name in masked["support"]["undefined_metrics"])
        assert case["checks"]["none_learned_unchanged"]


def test_null_learned_tables_remain_frozen_and_sparse_growth_is_explicit(diagnostic):
    unique = next(case for case in diagnostic["cases"] if case["scenario"] == "unique")
    assert unique["growth"]["pooled"]["metrics"]["second_half_novel_type_rate"] == 1
    for case in diagnostic["cases"]:
        for null in case["nulls"].values():
            assert set(null["learned_uncertainty"]) == {"16", "32", "64", "128"}


@pytest.mark.parametrize(
    "field,value",
    [
        ("target_access", "allowed"),
        ("record_counts", [3]),
        ("record_counts", [100000]),
        ("record_counts", [4, 4]),
        ("seeds", [211, 211]),
        ("groups_per_record", True),
        ("scenarios", ["voynich"]),
        ("annotation_masks", ["invented"]),
    ],
)
def test_invalid_or_unbounded_stress_configs_are_rejected(field, value):
    config = deepcopy(_config())
    config[field] = value
    with pytest.raises(MeasurementError):
        run_stress_suite(config)
