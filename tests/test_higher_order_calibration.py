from __future__ import annotations

import math

import numpy as np

from manuscript_lab.higher_order_calibration import (
    _fit_model,
    _length_preserving_token_rename,
    extract_higher_order_features,
)

FEATURES = [
    "heaps_exponent",
    "heaps_r2",
    "heaps_early_late_delta",
    "length_autocorrelation_lag_1",
    "length_autocorrelation_lag_2",
    "length_autocorrelation_lag_5",
    "length_autocorrelation_lag_10",
    "length_autocorrelation_lag_20",
    "length_low_frequency_power_fraction",
    "length_block_mean_cv",
    "length_block_std_cv",
    "recurrence_gap_burstiness",
    "recurrence_gap_cv",
    "frequent_token_block_fano",
    "token_block_information_20",
    "token_block_information_40",
    "token_pattern_compression_shuffle_gain",
    "length_pattern_compression_shuffle_gain",
    "cooccurrence_degree_assortativity",
    "cooccurrence_average_clustering",
    "cooccurrence_selectivity_cv",
]


PARAMS = {
    "features": FEATURES,
    "length_lags": [1, 2, 5, 10, 20],
    "length_block_size": 10,
    "information_block_sizes": [20, 40],
    "frequent_token_limit": 16,
    "compression_shuffle_replicates": 8,
}


def test_frozen_feature_panel_is_finite_ordered_and_deterministic() -> None:
    tokens = tuple(("alpha", "beta", "gamma", "alpha", "delta") * 20)
    first = extract_higher_order_features(tokens, params=PARAMS, seed=17)
    second = extract_higher_order_features(tokens, params=PARAMS, seed=17)
    assert list(first) == FEATURES
    assert first == second
    assert all(math.isfinite(value) for value in first.values())


def test_panel_is_invariant_to_length_preserving_token_rename() -> None:
    tokens = tuple(("alpha", "beta", "gamma", "alpha", "delta") * 20)
    renamed = _length_preserving_token_rename(tokens)
    original = extract_higher_order_features(tokens, params=PARAMS, seed=19)
    transformed = extract_higher_order_features(renamed, params=PARAMS, seed=19)
    assert max(abs(original[key] - transformed[key]) for key in FEATURES) <= 1e-12


def test_order_sensitive_compression_responds_to_destroyed_runs() -> None:
    clustered = tuple("aaaa" if index < 50 else "bbbb" for index in range(100))
    alternating = tuple("aaaa" if index % 2 == 0 else "bbbb" for index in range(100))
    first = extract_higher_order_features(clustered, params=PARAMS, seed=23)
    second = extract_higher_order_features(alternating, params=PARAMS, seed=23)
    assert (
        first["token_pattern_compression_shuffle_gain"]
        != second["token_pattern_compression_shuffle_gain"]
    )


def test_robust_scaler_floors_constant_features() -> None:
    rows = []
    for index in range(8):
        values = {feature: float(index + offset) for offset, feature in enumerate(FEATURES)}
        values["heaps_r2"] = 1.0 + index * 1e-16
        rows.append({"features": values})
    labels = np.asarray([0, 0, 0, 0, 1, 1, 1, 1])
    _median, scale, model = _fit_model(
        rows,
        labels,
        feature_order=FEATURES,
        c=1.0,
        seed=7,
        scale_tolerance=1e-12,
    )
    assert scale[1] == 1.0
    assert np.all(np.isfinite(model.coef_))
