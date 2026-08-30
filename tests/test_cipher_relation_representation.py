from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

from manuscript_lab.cipher_relation_representation import (
    PairRepresentations,
    compression_distance_vector,
    first_occurrence_canonical,
    invariant_signature,
    modular_relation_vector,
)
from manuscript_lab.provenance import repository_root, sha256_file


def _representation_config() -> dict:
    path = repository_root() / "config/experiments/E-006-cipher-relation-representation.yaml"
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))["parameters"]["representations"]


def test_first_occurrence_canonical_is_symbol_renaming_invariant() -> None:
    assert first_occurrence_canonical("ABACABA") == first_occurrence_canonical(
        "XYXZX YX".replace(" ", "")
    )
    assert first_occurrence_canonical("ABACABA") == bytes([0, 1, 0, 2, 0, 1, 0])


def test_invariant_signature_survives_monoalphabetic_renaming() -> None:
    config = _representation_config()["invariant_signature"]
    plain = ("ABACABADABACABA" * 50)[:600]
    renamed = plain.translate(str.maketrans({"A": "Q", "B": "R", "C": "S", "D": "T"}))
    assert np.allclose(invariant_signature(plain, config), invariant_signature(renamed, config))


def test_relation_and_compression_vectors_are_finite_and_fixed() -> None:
    config = _representation_config()
    plain = ("THEQUICKBROWNFOXLEAPSOVERTHELAZYDOG" * 20)[:600].replace("J", "I")
    shifted = "".join(
        "ABCDEFGHIKLMNOPQRSTUVWXYZ"[("ABCDEFGHIKLMNOPQRSTUVWXYZ".index(value) + 3) % 25]
        for value in plain
    )
    relation = modular_relation_vector(plain, shifted, config["modular_relation"])
    compression = compression_distance_vector(plain, shifted, config["compression"])
    assert relation.ndim == compression.ndim == 1
    assert relation.size > 100
    assert compression.size == 12
    assert np.isfinite(relation).all()
    assert np.isfinite(compression).all()


def test_modular_view_maps_ciphertext_j_into_preregistered_modulus() -> None:
    config = _representation_config()["modular_relation"]
    plain = "I" * 600
    cipher = "J" * 600
    result = modular_relation_vector(plain, cipher, config)
    assert np.isfinite(result).all()


def test_frozen_e005_contract_hashes_match() -> None:
    root = repository_root()
    config = yaml.safe_load(
        (root / "config/experiments/E-006-cipher-relation-representation.yaml").read_text(
            encoding="utf-8"
        )
    )
    parameters = config["parameters"]
    assert (
        sha256_file(root / parameters["benchmark_config"]) == parameters["benchmark_config_sha256"]
    )
    assert (
        sha256_file(root / parameters["predecessor_result"])
        == parameters["predecessor_result_sha256"]
    )


def test_process_feature_bank_populates_normal_and_destruction_views() -> None:
    config = _representation_config()
    texts = [("ABAC" * 150), ("BACA" * 150)]
    segments = [{"text": text} for text in texts]
    surface = np.asarray([[2.0], [2.0]])
    factory = PairRepresentations(
        segments,
        {"test": texts},
        config,
        ["alphabet_size"],
        surface,
        {"test": surface},
        destruction_seed=1,
    )
    factory.precompute(
        "fused-character-relation-v1",
        ["test"],
        np.asarray([0, 1]),
        workers=2,
    )
    normal = factory.vector("fused-character-relation-v1", "test", 0, 1)
    destroyed = factory.vector("fused-character-relation-v1", "test", 0, 0, destroyed=True)
    assert normal.shape == destroyed.shape
    assert np.isfinite(normal).all()
    assert np.isfinite(destroyed).all()
