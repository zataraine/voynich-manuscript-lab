from __future__ import annotations

import math

import pytest
import yaml

from manuscript_lab.measurement_battery import MeasurementError
from manuscript_lab.multialphabet_calibration import (
    CONFIG_PATH,
    markov_records,
    population_truth,
    run_calibration,
)
from manuscript_lab.provenance import repository_root
from manuscript_lab.uncertainty_calibration import _oracle, scoped_uncertainty


def test_population_truth_and_extremes():
    for alphabet in (2, 4, 32):
        assert population_truth(alphabet, 0)[
            "conditional_unit_entropy_order1_bits"
        ] == pytest.approx(math.log2(alphabet))
        assert population_truth(alphabet, 1)["conditional_unit_entropy_order1_bits"] == 0
        assert population_truth(alphabet, 0.9)["unit_entropy_bits"] == math.log2(alphabet)


def test_variable_widths_exact_budgets_and_no_cross_group_transitions():
    records = markov_records(
        alphabet=4,
        copy_probability=1,
        units_per_split=100,
        widths=[1, 2, 4, 8],
        seed=19,
        split="test",
    )
    assert [len(g) for g in records[0].groups] == [1, 2, 4, 8, 1, 2, 4, 3]
    panel = scoped_uncertainty(records)
    assert panel["support"]["unit_count"] == 100
    assert panel["support"]["transition_count"] == 100 - sum(len(r.groups) for r in records)
    assert panel["metrics"]["conditional_unit_entropy_order1_bits"] == 0
    assert (
        markov_records(
            alphabet=4,
            copy_probability=1,
            units_per_split=100,
            widths=[1, 2, 4, 8],
            seed=19,
            split="test",
        )
        == records
    )


def test_multialphabet_oracle_and_missing_transition_scope():
    records = markov_records(
        alphabet=7,
        copy_probability=0.3,
        units_per_split=200,
        widths=[1, 3, 7],
        seed=23,
        split="test",
    )
    measured = scoped_uncertainty(records)["metrics"]
    for name, value in _oracle(records).items():
        assert measured[name] == pytest.approx(value, abs=1e-12)
    singleton = markov_records(
        alphabet=7, copy_probability=0.3, units_per_split=20, widths=[1], seed=23, split="test"
    )
    assert scoped_uncertainty(singleton)["status"] == "abstain"


def test_campaign_refuses_tuning_without_executing_the_grid():
    config = yaml.safe_load((repository_root() / CONFIG_PATH).read_text())
    config["parameters"]["units_per_split"] = [512]
    with pytest.raises(MeasurementError, match="frozen bounded design"):
        run_calibration(config)
