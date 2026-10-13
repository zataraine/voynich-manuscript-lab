from __future__ import annotations

from dataclasses import replace

import orjson
import pytest
import yaml

from manuscript_lab.measurement_battery import MeasurementError
from manuscript_lab.provenance import repository_root
from manuscript_lab.uncertainty_calibration import (
    CONFIG_PATH,
    PROFILE,
    PROFILE_PATH,
    _oracle,
    generate_records,
    run_calibration,
    scoped_uncertainty,
)


def test_scoped_profile_is_frozen_and_does_not_require_session_annotations():
    assert yaml.safe_load((repository_root() / PROFILE_PATH).read_text()) == PROFILE
    records = generate_records(
        probability=0.5, groups_per_record=2, group_width=4, seed=3, split="test"
    )
    panel = scoped_uncertainty(records)
    assert panel["status"] == "available_not_calibrated"
    assert panel["target_access"] == "forbidden"
    assert all(r.session_id is None and r.paragraph_id is None for r in records)
    annotated = tuple(replace(r, session_id="a", session_index=0) for r in records)
    assert scoped_uncertainty(annotated) == panel


def test_boundary_resets_and_known_extreme_processes():
    constant = generate_records(
        probability=0, groups_per_record=2, group_width=8, seed=5, split="test"
    )
    alternating = generate_records(
        probability=1, groups_per_record=2, group_width=8, seed=5, split="test"
    )
    assert scoped_uncertainty(constant)["metrics"]["conditional_unit_entropy_order1_bits"] == 0
    panel = scoped_uncertainty(alternating)
    assert panel["metrics"]["unit_entropy_bits"] == 1
    assert panel["metrics"]["conditional_unit_entropy_order1_bits"] == 0
    assert panel["support"]["transition_count"] == 4 * 2 * 7
    assert (
        generate_records(probability=1, groups_per_record=2, group_width=8, seed=5, split="test")
        == alternating
    )


def test_independent_entropy_oracle_and_exact_regeneration():
    records = generate_records(
        probability=0.3, groups_per_record=3, group_width=9, seed=7, split="test"
    )
    metrics = scoped_uncertainty(records)["metrics"]
    for name, value in _oracle(records).items():
        assert metrics[name] == pytest.approx(value, abs=1e-12)
    assert orjson.dumps([r.groups for r in records]) == orjson.dumps(
        [
            r.groups
            for r in generate_records(
                probability=0.3, groups_per_record=3, group_width=9, seed=7, split="test"
            )
        ]
    )


def test_undefined_is_not_zero_evidence_and_duplicate_records_are_rejected():
    records = generate_records(
        probability=0.5, groups_per_record=2, group_width=1, seed=9, split="test"
    )
    assert scoped_uncertainty(records)["status"] == "abstain"
    assert scoped_uncertainty([])["status"] == "abstain"
    with pytest.raises(MeasurementError):
        scoped_uncertainty([records[0], records[0]])


def test_campaign_refuses_posthoc_parameter_changes_without_running_it():
    config = yaml.safe_load((repository_root() / CONFIG_PATH).read_text())
    config["parameters"]["maximum_mean_error_bits"] = 0.2
    with pytest.raises(MeasurementError, match="frozen bounded design"):
        run_calibration(config)
