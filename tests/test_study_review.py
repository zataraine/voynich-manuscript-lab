from __future__ import annotations

from pathlib import Path

import yaml

import manuscript_lab.study_review as study_review
from manuscript_lab.study_review import build_reference_packet, review_with_packet


class FakeClient:
    def embed_reference(self, texts, *, content_kind):
        assert content_kind == "research-note"
        return {
            "model": "fake-embedding",
            "embeddings": [[1.0, float(index + 1)] for index, _ in enumerate(texts)],
        }

    def rerank_reference(self, query, documents, *, content_kind, instruction=None):
        assert query and instruction and content_kind == "research-note"
        return {
            "model_path": "/fake/reranker",
            "results": [
                {"corpus_id": index, "score": 1.0 / (index + 1)} for index in range(len(documents))
            ],
        }

    def review_experiment(self, record):
        assert record["reference_context"]
        assert len(record["review_semantics"]) >= 4
        assert any("source_manifest_sha256" in item for item in record["review_semantics"])
        assert all(
            "samples" not in summary
            for metrics in record["null_results"].values()
            for summary in metrics.values()
        )
        return {"review": {"experiment_id": record["experiment_id"]}, "provenance": {}}


def test_reference_pipeline_never_sends_manuscript_content(tmp_path: Path, monkeypatch) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "METHOD.md").write_text(
        "# Controls\nHeld-out pages and explicit null mechanisms.\n\n"
        "## Limits\nStructure is not evidence of meaning.\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "parameters": {
                    "local_ai": {
                        "reference_query": "held-out null calibration",
                        "reference_documents": ["docs/METHOD.md"],
                        "lexical_candidates": 4,
                        "rerank_candidates": 4,
                        "packet_passages": 2,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(study_review, "repository_root", lambda: tmp_path)
    packet = build_reference_packet(config_path, client=FakeClient())  # type: ignore[arg-type]
    assert packet["content_kind"] == "research-note"
    assert "No manuscript transcription" in packet["policy_note"]
    reviewed = review_with_packet(
        {
            "experiment_id": "E-TEST",
            "null_results": {"iid": {"metric": {"mean": 1.0, "samples": [1.0, 2.0]}}},
            "split": {
                "train_pages": ["f1r"],
                "heldout_pages": ["f1v"],
                "train_group_count": 2,
                "heldout_group_count": 2,
            },
        },
        packet,
        client=FakeClient(),  # type: ignore[arg-type]
    )
    assert reviewed["review"]["experiment_id"] == "E-TEST"
    assert reviewed["reference_packet_sha256"]
