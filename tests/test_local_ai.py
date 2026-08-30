from __future__ import annotations

from pathlib import Path

import pytest

from manuscript_lab.local_ai import (
    LocalAIClient,
    LocalAIError,
    LocalAISettings,
    _validate,
    review_schema,
)


def _settings(tmp_path: Path) -> LocalAISettings:
    return LocalAISettings(
        stack_root=tmp_path,
        paths={},
        chat_base_url="http://127.0.0.1:1/v1",
        health_url="http://127.0.0.1:1/health",
        chat_model="test-model",
        chat_timeout=1,
        chat_max_tokens=32,
        chat_temperature=0.0,
        enable_thinking=False,
        review_system_prompt=tmp_path / "routine-system.txt",
        review_user_prompt=tmp_path / "routine-user.txt",
        aux_runner=tmp_path / "ai-aux-run",
        ollama_url="http://127.0.0.1:2",
        embedding_model="embedding-test",
        critic_model="critic-test",
        critic_modelfile=tmp_path / "critic.Modelfile",
        critic_system_prompt=tmp_path / "critic-system.txt",
        critic_user_prompt=tmp_path / "critic-user.txt",
        reranker_path=tmp_path / "reranker",
        aux_timeout=1,
        embedding_allowed=frozenset({"reference", "metadata", "research-note"}),
        embedding_denied=frozenset({"manuscript-transcription", "voynichese", "corpus"}),
        max_request_bytes=4096,
    )


def test_local_review_schema_accepts_complete_review() -> None:
    value = {
        "experiment_id": "E-001",
        "assessment": "No controlled effect.",
        "anomalies": [],
        "confounds": ["Small held-out set"],
        "effect_strength": "none",
        "followups": ["Repeat with a second transcription"],
        "confidence": 0.8,
        "escalate": False,
    }
    _validate(review_schema(), value, "test review")


@pytest.mark.parametrize("kind", ["manuscript-transcription", "voynichese", "corpus"])
def test_manuscript_content_is_never_sent_to_auxiliary_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    client = LocalAIClient(_settings(tmp_path))
    called = False

    def fail_if_called(_: object) -> dict[str, object]:
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(client, "_run_auxiliary", fail_if_called)
    with pytest.raises(LocalAIError, match="prohibited"):
        client.embed_reference(["qokedy"], content_kind=kind)  # type: ignore[arg-type]
    assert not called


def test_unlisted_content_kind_is_denied(tmp_path: Path) -> None:
    client = LocalAIClient(_settings(tmp_path))
    with pytest.raises(LocalAIError, match="not explicitly allowed"):
        client.embed_reference(["reference"], content_kind="other")  # type: ignore[arg-type]
