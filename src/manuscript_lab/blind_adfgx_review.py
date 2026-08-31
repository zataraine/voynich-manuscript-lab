"""Bounded local-model review records for E-008."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

import orjson

from manuscript_lab.local_ai import LocalAIClient


def bounded_record(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "experiment_id": result["experiment_id"],
        "hypothesis_id": result["hypothesis_id"],
        "status": result["status"],
        "target_scored": result["target_scored"],
        "candidate_plaintext_supplied": result["candidate_plaintext_supplied"],
        "metrics": result["metrics"],
        "gates": result["gates"],
        "overall": result["overall"],
        "by_true_width": result["by_true_width"],
        "broken_control": result["broken_control"],
        "permutation": result["permutation"],
        "runtime": result["runtime"],
        "provenance": result["provenance"],
        "full_result_sha256": hashlib.sha256(
            orjson.dumps(result, option=orjson.OPT_SORT_KEYS)
        ).hexdigest(),
        "review_semantics": [
            "Generation, truth-free scoring, and unblinding were separate immutable stages.",
            "The eight plaintext sources were absent from E-005 and E-007.",
            "Ninety-six queries used a new square and keyword each, balanced across widths 4-7.",
            "The scorer searched all preregistered widths and all column orders before ranking.",
            "The identity null was applied after the same complete maximization.",
            "The destructive control shuffled complete coordinate-pair positions, "
            "preserving the exact pair multiset.",
            "Candidate plaintext was supplied; this is not ciphertext-only cryptanalysis.",
            "Widths above seven and non-ADFGX fractionating mechanisms remain untested.",
            "No Voynich text, transcript, glyph assumption, semantic model, or target "
            "score entered E-008.",
            "A pass can justify designing a target-side null protocol, not running one "
            "without preregistration.",
        ],
        "review_question": (
            "Does E-008 establish independent parameter-blind generalization of the frozen "
            "known-payload diagnostic, which alternative explanations were rejected, and "
            "what exact controls are still required before any target-side experiment?"
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
