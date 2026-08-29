from __future__ import annotations

import pytest

from manuscript_lab.retrieval import (
    RankedDocument,
    bm25_rank,
    cosine_rank,
    hybrid_reference_rank,
    lexical_tokens,
    reciprocal_rank_fusion,
)


def test_lexical_retrieval_preserves_exact_identifiers() -> None:
    documents = {
        "currier": "Currier A occurs on f1r and f8v.",
        "generic": "A discussion of page groups without exact folio labels.",
    }
    assert "f1r" in lexical_tokens(documents["currier"])
    assert bm25_rank("f1r", documents)[0].document_id == "currier"


def test_cosine_and_rank_fusion_are_deterministic() -> None:
    semantic = cosine_rank([1.0, 0.0], {"a": [1.0, 0.0], "b": [0.0, 1.0]})
    lexical = [RankedDocument("b", 5.0), RankedDocument("a", 1.0)]
    fused = reciprocal_rank_fusion([lexical, semantic])
    assert [item.document_id for item in fused] == ["a", "b"]


def test_hybrid_requires_identical_document_sets() -> None:
    with pytest.raises(ValueError, match="identifiers"):
        hybrid_reference_rank("folio", {"a": "folio"}, [1.0], {"b": [1.0]})


def test_cosine_rejects_zero_query() -> None:
    with pytest.raises(ValueError, match="non-zero"):
        cosine_rank([0.0, 0.0], {"a": [1.0, 0.0]})
