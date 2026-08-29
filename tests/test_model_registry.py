from __future__ import annotations

from pathlib import Path

import yaml


def test_local_model_registry_is_revision_pinned() -> None:
    root = Path(__file__).parents[1]
    registry = yaml.safe_load((root / "models" / "local-ai.yaml").read_text(encoding="utf-8"))
    models = registry["models"]
    assert {model["id"] for model in models} >= {
        "voynich-qwen",
        "qwen3-embedding-reference",
        "qwen3-reranker-0.6b",
        "bge-reranker-v2-m3",
        "glm-critic",
    }
    for model in models:
        assert model["revision"]
        assert model["license"]
        assert model["expected_size_bytes"] > 0
        assert model["trust_remote_code"] is False


def test_routine_reranker_registry_matches_installed_identity() -> None:
    root = Path(__file__).parents[1]
    registry = yaml.safe_load((root / "models" / "local-ai.yaml").read_text(encoding="utf-8"))
    model = next(item for item in registry["models"] if item["id"] == "qwen3-reranker-0.6b")
    assert model["revision"] == "e61197ed45024b0ed8a2d74b80b4d909f1255473"
    assert model["expected_size_bytes"] == 1191588280
    assert model["sha256"] == "27cd75a405b9c1b46b59abfd88aaa209e6fed2a1972cde9b70e7659537c5e65b"
