"""Bounded local-model reviews for the E-007 deterministic result."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

import orjson

from manuscript_lab.local_ai import LocalAIClient


def bounded_record(result: dict[str, Any]) -> dict[str, Any]:
    """Remove raw text and retain only facts needed for methodological review."""
    return {
        "experiment_id": result["experiment_id"],
        "hypothesis_id": result["hypothesis_id"],
        "status": result["status"],
        "target_scored": result["target_scored"],
        "metrics": result["metrics"],
        "gates": result["gates"],
        "variants": result["variants"],
        "provenance": result["provenance"],
        "full_result_sha256": hashlib.sha256(
            orjson.dumps(result, option=orjson.OPT_SORT_KEYS)
        ).hexdigest(),
        "review_semantics": [
            "This is a known-plaintext diagnostic on twelve exposed E-005 controls.",
            "Width is supplied as a hypothesis; it is not inferred from manuscript data.",
            "The square, keyword, order, correct candidate, and target identity are hidden.",
            "The scorer exhaustively tries column orders, so factorial scaling limits widths.",
            "Correct pairs score 1.0 because the deterministic mapping is exactly consistent.",
            "Wrong-width controls are lower neighboring widths, not a complete width scan.",
            "The cryptii vector and pinned pycipher implementation are implementation oracles.",
            "No Voynich text, embeddings, or language-model text scores enter the experiment.",
            "Passing validates a control diagnostic, not an ADFGX or language claim for MS 408.",
        ],
        "review_question": (
            "Does this result actually localize E-006's ADFGX failure to post-transposition "
            "pair unitization, what limitations remain, and what cheapest independent test "
            "should precede any manuscript application?"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("qwen", "critic"))
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Immutable output already exists: {args.output}")
    record = bounded_record(orjson.loads(args.result.read_bytes()))
    client = LocalAIClient()
    review = client.review_experiment(record) if args.operation == "qwen" else client.critic(record)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(
        orjson.dumps(review, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    )


if __name__ == "__main__":
    main()
