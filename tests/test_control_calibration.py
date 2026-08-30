from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from manuscript_lab.calibration_review import bounded_record
from manuscript_lab.control_calibration import _document_metrics, _sample_weights
from manuscript_lab.control_corpus import ControlDocument, chunk_document, normalize_tokens
from manuscript_lab.feature_panel import extract_features


def test_normalization_and_chunks_are_deterministic() -> None:
    tokens = normalize_tokens("Álpha, BETA 42 gamma\u2019s delta-delta!")
    assert tokens == ("álpha", "beta", "gamma's", "delta-delta")
    document = ControlDocument(
        "doc", "meaningful", "test", "member.txt", hashlib.sha256(b"x").hexdigest(), tokens * 40
    )
    first = chunk_document(document, chunk_tokens=40, max_chunks=3)
    second = chunk_document(document, chunk_tokens=40, max_chunks=3)
    assert first == second
    assert {sample.document_id for sample in first} == {"doc"}
    assert all(len(sample.tokens) == 40 for sample in first)


def test_feature_panel_is_finite_and_order_sensitive() -> None:
    tokens = ("alpha", "beta", "gamma", "delta", "epsilon") * 20
    features = extract_features(tokens)
    reordered_features = extract_features(tuple(sorted(tokens)))
    assert len(features) == 21
    assert all(np.isfinite(value) for value in features.values())
    assert features["token_length_lag1"] != reordered_features["token_length_lag1"]


def test_document_weighting_and_metrics_operate_at_document_level() -> None:
    groups = np.asarray(["long", "long", "long", "short"])
    assert np.allclose(_sample_weights(groups), [1 / 3, 1 / 3, 1 / 3, 1])
    labels = np.asarray([0, 0, 1, 1])
    scores = np.asarray([0.1, 0.2, 0.8, 0.9])
    metric_groups = np.asarray(["n1", "n1", "p1", "p2"])
    metrics, grouped = _document_metrics(labels, scores, metric_groups)
    assert len(grouped) == 3
    assert metrics["document_roc_auc"] == 1.0


def test_bounded_review_drops_per_sample_target_values(tmp_path: Path) -> None:
    result = {
        "experiment_id": "E-test",
        "naibbe_positive_control": {"sample_count": 1, "samples": [{"secret": 1}]},
        "voynich_targets": {
            "w": {
                "sample_count": 1,
                "median_meaningful_similarity": 0.5,
                "samples": [{"secret": 2}],
            }
        },
    }
    packet = {"passages": [], "policy_note": "notes only"}
    bounded = bounded_record(result, packet)
    assert "samples" not in bounded["naibbe_positive_control"]
    assert "samples" not in bounded["voynich_targets"]["w"]
