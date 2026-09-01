from __future__ import annotations

import numpy as np

from manuscript_lab.witness_calibration import contiguous_folds, cross_fit, synthetic_controls


def test_contiguous_folds_cover_order_without_overlap() -> None:
    folds = contiguous_folds(13, 5)
    assert [len(fold) for fold in folds] == [3, 3, 3, 2, 2]
    assert np.array_equal(np.concatenate(folds), np.arange(13))


def test_cross_fit_never_uses_heldout_outlier_for_parameters() -> None:
    values = {"a": np.asarray([0.0, 1.0, 2.0, 3.0, 1000.0])}
    folds = (np.asarray([0, 1, 2, 3]), np.asarray([4]))
    calibrated, parameters = cross_fit(values, folds)

    assert parameters["a"][1]["training_median"] == 1.5
    assert parameters["a"][1]["training_iqr"] == 1.5
    assert np.isclose(calibrated["a"][4], (1000.0 - 1.5) / 1.5)


def test_frozen_synthetic_controls_pass() -> None:
    config = {
        "split": {"folds": 5},
        "controls": {
            "seed": 20260903,
            "pages": 256,
            "views": 5,
            "noise_standard_deviation": 0.03,
            "recoverable_minimum_worst_spearman": 0.95,
            "recoverable_maximum_median_normalized_difference": 0.20,
            "broken_maximum_median_pair_spearman": 0.15,
        },
    }
    result = synthetic_controls(config)

    assert result["passed"]
    assert all(result["gates"].values())
