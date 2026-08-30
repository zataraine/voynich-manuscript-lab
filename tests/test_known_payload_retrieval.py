from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

from manuscript_lab.known_payload_retrieval import (
    document_segments,
    encipher_roundtrip,
    normalize_gutenberg,
    pair_feature_vector,
    retrieval_metrics,
)
from manuscript_lab.provenance import repository_root


def test_gutenberg_normalization_strips_frame_and_maps_j() -> None:
    raw = (
        "header\n*** START OF THE PROJECT GUTENBERG EBOOK TEST ***\n"
        "Jig saw!\n*** END OF THE PROJECT GUTENBERG EBOOK TEST ***\nfooter"
    )
    assert normalize_gutenberg(raw) == "IIGSAW"


def test_document_segments_are_fixed_and_nonoverlapping() -> None:
    values = document_segments("A" * 1000, segment_characters=100, count=4)
    assert [offset for offset, _text in values] == [0, 300, 600, 900]
    assert all(len(text) == 100 for _offset, text in values)


def test_pair_features_and_perfect_retrieval() -> None:
    vector = np.asarray([0.0, 1.0, -2.0])
    assert np.allclose(pair_feature_vector(vector, vector), 0)
    metrics = retrieval_metrics(np.eye(4))
    assert metrics["mean_reciprocal_rank"] == 1.0
    assert metrics["normalized_mrr"] == 1.0
    assert metrics["top1_lift_over_chance"] == 4.0


def test_every_preregistered_cipher_roundtrips() -> None:
    config_path = repository_root() / "config/experiments/E-005-known-payload-retrieval.yaml"
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    plaintext = ("THEQUICKBROWNFOXLEAPSOVERTHELAZYDOG" * 20)[:600].replace("J", "I")
    for spec in config["parameters"]["cipher_families"]:
        ciphertext, exact = encipher_roundtrip(plaintext, spec)
        assert ciphertext
        assert exact, spec["id"]
