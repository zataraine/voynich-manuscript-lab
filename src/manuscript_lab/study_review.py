"""Reference retrieval and schema-bound local review for mechanism studies."""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import orjson
import yaml

from manuscript_lab.local_ai import LocalAIClient
from manuscript_lab.provenance import repository_root, sha256_file
from manuscript_lab.retrieval import bm25_rank, cosine_rank, reciprocal_rank_fusion

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class ReferencePassage:
    passage_id: str
    source_path: str
    heading: str
    text: str


def markdown_passages(path: Path, *, max_chars: int = 1800) -> list[ReferencePassage]:
    """Create stable, heading-aware chunks from an allowed project reference note."""
    relative = path.relative_to(repository_root()).as_posix()
    heading = path.stem
    buffer: list[str] = []
    passages: list[ReferencePassage] = []

    def flush() -> None:
        nonlocal buffer
        text = "\n".join(buffer).strip()
        buffer = []
        while text:
            split_at = min(max_chars, len(text))
            if split_at < len(text):
                paragraph = text.rfind("\n\n", 0, split_at)
                if paragraph > max_chars // 2:
                    split_at = paragraph
            chunk, text = text[:split_at].strip(), text[split_at:].strip()
            if chunk:
                digest = hashlib.sha256(f"{relative}\0{heading}\0{chunk}".encode()).hexdigest()[:16]
                passages.append(ReferencePassage(f"ref-{digest}", relative, heading, chunk))

    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING.match(line)
        if match:
            flush()
            heading = match.group(2)
            continue
        buffer.append(line)
        if sum(len(value) + 1 for value in buffer) >= max_chars:
            flush()
    flush()
    return passages


def build_reference_packet(
    config_path: Path,
    *,
    client: LocalAIClient | None = None,
) -> dict[str, Any]:
    """Run lexical, embedding, fusion, and reranking over approved notes only."""
    root = repository_root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    settings = config["parameters"]["local_ai"]
    query = settings["reference_query"]
    passages = [
        passage
        for name in settings["reference_documents"]
        for passage in markdown_passages(root / name)
    ]
    documents = {passage.passage_id: passage.text for passage in passages}
    passage_by_id = {passage.passage_id: passage for passage in passages}
    lexical = bm25_rank(query, documents)
    candidate_ids = [item.document_id for item in lexical[: int(settings["lexical_candidates"])]]
    candidate_texts = [documents[passage_id] for passage_id in candidate_ids]
    local_client = client or LocalAIClient()
    embedding = local_client.embed_reference(
        [query, *candidate_texts], content_kind="research-note"
    )
    vectors = embedding["embeddings"]
    vector_ranking = cosine_rank(vectors[0], dict(zip(candidate_ids, vectors[1:], strict=True)))
    fused = reciprocal_rank_fusion(
        [[item for item in lexical if item.document_id in set(candidate_ids)], vector_ranking]
    )
    rerank_ids = [item.document_id for item in fused[: int(settings["rerank_candidates"])]]
    reranked = local_client.rerank_reference(
        query,
        [documents[passage_id] for passage_id in rerank_ids],
        content_kind="research-note",
        instruction=(
            "Rank methodological passages for evaluating held-out sequence structure, explicit "
            "null mechanisms, leakage, calibration, and limits on claims about meaning."
        ),
    )
    ordered = [rerank_ids[item["corpus_id"]] for item in reranked["results"]]
    selected = ordered[: int(settings["packet_passages"])]
    return {
        "schema_version": "1.0",
        "query": query,
        "content_kind": "research-note",
        "policy_note": "No manuscript transcription or Voynichese was embedded or reranked.",
        "passages": [
            {
                "passage_id": passage_by_id[passage_id].passage_id,
                "source_path": passage_by_id[passage_id].source_path,
                "heading": passage_by_id[passage_id].heading,
                "text": passage_by_id[passage_id].text,
            }
            for passage_id in selected
        ],
        "provenance": {
            "embedding_model": embedding["model"],
            "reranker_model_path": reranked["model_path"],
            "config_sha256": sha256_file(config_path),
            "reference_sha256": {
                name: sha256_file(root / name) for name in settings["reference_documents"]
            },
        },
    }


def review_with_packet(
    result: dict[str, Any], packet: dict[str, Any], *, client: LocalAIClient | None = None
) -> dict[str, Any]:
    """Ask Qwen to review metrics and a bounded methodological reference packet."""
    null_summary = {
        family: {
            metric: {key: value for key, value in summary.items() if key != "samples"}
            | {"replicate_count": len(summary.get("samples", []))}
            for metric, summary in metrics.items()
        }
        for family, metrics in result["null_results"].items()
    }
    split = result["split"]
    review_record = {
        **result,
        "null_results": null_summary,
        "split": {
            **split,
            "train_page_count": len(split["train_pages"]),
            "heldout_page_count": len(split["heldout_pages"]),
            "train_pages_sha256": hashlib.sha256(orjson.dumps(split["train_pages"])).hexdigest(),
            "heldout_pages_sha256": hashlib.sha256(
                orjson.dumps(split["heldout_pages"])
            ).hexdigest(),
            "train_pages": "omitted-from-bounded-review",
            "heldout_pages": "omitted-from-bounded-review",
        },
        "full_result_sha256": hashlib.sha256(
            orjson.dumps(result, option=orjson.OPT_SORT_KEYS)
        ).hexdigest(),
        "reference_context": packet["passages"],
        "reference_context_policy": packet["policy_note"],
    }
    review = (client or LocalAIClient()).review_experiment(review_record)
    review["reference_packet_sha256"] = hashlib.sha256(
        orjson.dumps(packet, option=orjson.OPT_SORT_KEYS)
    ).hexdigest()
    return review


def _write_immutable(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"Immutable output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(orjson.dumps(value, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE))


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="operation", required=True)
    packet_parser = subparsers.add_parser("packet")
    packet_parser.add_argument("--config", type=Path, required=True)
    packet_parser.add_argument("--output", type=Path, required=True)
    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("--result", type=Path, required=True)
    review_parser.add_argument("--packet", type=Path, required=True)
    review_parser.add_argument("--output", type=Path, required=True)
    critic_parser = subparsers.add_parser("critic")
    critic_parser.add_argument("--result", type=Path, required=True)
    critic_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.operation == "packet":
        value = build_reference_packet(args.config.resolve())
    elif args.operation == "review":
        result = orjson.loads(args.result.read_bytes())
        packet = orjson.loads(args.packet.read_bytes())
        value = review_with_packet(result, packet)
    else:
        result = orjson.loads(args.result.read_bytes())
        value = LocalAIClient().critic(result)
    _write_immutable(args.output, value)


if __name__ == "__main__":
    main()
