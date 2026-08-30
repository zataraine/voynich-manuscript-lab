from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

from manuscript_lab.cipher_relation_representation import (
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
