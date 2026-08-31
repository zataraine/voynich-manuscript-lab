"""Bounded local review records for the failed E-009 ciphertext-only bridge."""

from __future__ import annotations

import argparse
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

import orjson
from sklearn.metrics import roc_auc_score

from manuscript_lab.local_ai import LocalAIClient


def bounded_record(result: dict[str, Any]) -> dict[str, Any]:
    records = result["query_audit"]
    natural = [item for item in records if item["family"] == "natural"]
    true_order_auc = {}
    natural_scores = [item["true_order_raw_score"] for item in natural]
    for family in sorted({item["family"] for item in records} - {"natural"}):
        control = [item["true_order_raw_score"] for item in records if item["family"] == family]
        true_order_auc[family] = float(
            roc_auc_score([1] * len(natural_scores) + [0] * len(control), natural_scores + control)
        )
    return {
        "experiment_id": result["experiment_id"],
        "hypothesis_id": result["hypothesis_id"],
        "status": result["status"],
        "target_scored": result["target_scored"],
        "plaintext_supplied_to_scorer": result["plaintext_supplied_to_scorer"],
        "metrics": result["metrics"],
        "adversarial_diagnostics": result["adversarial_diagnostics"],
        "gates": result["gates"],
        "permutation": result["permutation"],
        "runtime": result["runtime"],
        "provenance": result["provenance"],
        "posthoc_failure_localization": {
            "true_order_auc_natural_vs_controls": true_order_auc,
            "natural_selected_width_counts": dict(
                (str(width), count)
                for width, count in Counter(
                    width for item in natural for width in item["maximizing_widths"]
                ).items()
            ),
            "natural_true_width_counts": dict(
                (str(width), count)
                for width, count in Counter(item["true_width"] for item in natural).items()
            ),
            "interpretation": (
                "At the true order, the objective separates natural from Markov1 but weakly "
                "from unigram/block controls and reverses against copy/mutate. The complexity-"
                "penalized search selects width 4 for 23/24 natural queries despite balanced "
                "truth. These are post-hoc diagnostics and cannot replace failed gates."
            ),
        },
        "full_result_sha256": hashlib.sha256(
            orjson.dumps(result, option=orjson.OPT_SORT_KEYS)
        ).hexdigest(),
        "review_semantics": [
            "Only two integrity gates passed; all seven scientific gates failed.",
            "The result must remain failed regardless of favorable true-order diagnostics.",
            "The scorer received only query ID and ciphertext and never accessed "
            "plaintext or truth.",
            "Correct width was selected for 7/24 natural queries and width 4 was "
            "favored 23/24 times.",
            "The true order's median percentile was 0.0458, so wrong inversions "
            "usually scored higher.",
            "Copy/mutate pseudo-text scored above natural text and remains an "
            "identifiability warning.",
            "No Voynich target, transcription, or semantic model entered the experiment.",
            "Do not tune thresholds, penalty, context order, or backoff on this exposed suite.",
        ],
        "review_question": (
            "Does the evidence localize E-009 failure to width correction, order search, weak "
            "natural/null discrimination, or all three; and should this ADFGX branch stop?"
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
