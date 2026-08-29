"""Deterministic lexical/vector rankers for non-manuscript reference material."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np

TOKEN = re.compile(r"[A-Za-z0-9]+(?:[._:/-][A-Za-z0-9]+)*", re.ASCII)


@dataclass(frozen=True)
class RankedDocument:
    document_id: str
    score: float


def lexical_tokens(text: str) -> list[str]:
    """Tokenize while retaining exact technical identifiers as single units."""
    return [match.group(0).casefold() for match in TOKEN.finditer(text)]


def bm25_rank(
    query: str,
    documents: dict[str, str],
    *,
    k1: float = 1.5,
    b: float = 0.75,
    exact_bonus: float = 2.0,
) -> list[RankedDocument]:
    """Rank a small auditable reference collection with Okapi BM25."""
    if not documents:
        return []
    query_terms = lexical_tokens(query)
    tokenized = {key: lexical_tokens(value) for key, value in documents.items()}
    average_length = sum(map(len, tokenized.values())) / len(tokenized)
    document_frequency = Counter(term for terms in tokenized.values() for term in set(terms))
    scores: list[RankedDocument] = []
    normalized_query = query.casefold().strip()
    for document_id, terms in tokenized.items():
        frequencies = Counter(terms)
        length_normalizer = k1 * (1 - b + b * len(terms) / average_length if average_length else 1)
        score = 0.0
        for term in query_terms:
            frequency = frequencies[term]
            if frequency == 0:
                continue
            inverse_document_frequency = math.log(
                1
                + (len(documents) - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            score += inverse_document_frequency * (
                frequency * (k1 + 1) / (frequency + length_normalizer)
            )
        if normalized_query and normalized_query in documents[document_id].casefold():
            score += exact_bonus
        scores.append(RankedDocument(document_id, score))
    return sorted(scores, key=lambda item: (-item.score, item.document_id))


def cosine_rank(
    query_embedding: Sequence[float],
    document_embeddings: dict[str, Sequence[float]],
) -> list[RankedDocument]:
    """Rank precomputed reference embeddings without invoking a model."""
    query = np.asarray(query_embedding, dtype=np.float64)
    query_norm = float(np.linalg.norm(query))
    if query.ndim != 1 or query_norm == 0 or not np.isfinite(query).all():
        raise ValueError("Query embedding must be a finite, non-zero vector")
    scores: list[RankedDocument] = []
    for document_id, values in document_embeddings.items():
        vector = np.asarray(values, dtype=np.float64)
        if vector.shape != query.shape or not np.isfinite(vector).all():
            raise ValueError(f"Invalid embedding for {document_id}")
        norm = float(np.linalg.norm(vector))
        score = float(np.dot(query, vector) / (query_norm * norm)) if norm else -1.0
        scores.append(RankedDocument(document_id, score))
    return sorted(scores, key=lambda item: (-item.score, item.document_id))


def reciprocal_rank_fusion(
    rankings: Iterable[Sequence[RankedDocument]],
    *,
    rank_constant: int = 60,
) -> list[RankedDocument]:
    """Fuse independent rankings without treating incomparable scores as equal."""
    if rank_constant <= 0:
        raise ValueError("rank_constant must be positive")
    scores: Counter[str] = Counter()
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item.document_id] += 1.0 / (rank_constant + rank)
    return sorted(
        (RankedDocument(document_id, score) for document_id, score in scores.items()),
        key=lambda item: (-item.score, item.document_id),
    )


def hybrid_reference_rank(
    query: str,
    documents: dict[str, str],
    query_embedding: Sequence[float],
    document_embeddings: dict[str, Sequence[float]],
) -> list[RankedDocument]:
    """Fuse exact/BM25 and semantic rankings of reference text."""
    if set(documents) != set(document_embeddings):
        raise ValueError("Document text and embedding identifiers must match exactly")
    return reciprocal_rank_fusion(
        [bm25_rank(query, documents), cosine_rank(query_embedding, document_embeddings)]
    )
