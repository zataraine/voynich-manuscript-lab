"""Bounded local review for E-004."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

import orjson
import yaml

from manuscript_lab.local_ai import LocalAIClient
from manuscript_lab.provenance import repository_root, sha256_file

METRICS = ("document_roc_auc", "document_balanced_accuracy", "document_brier")


def _panel_summary(panel: dict[str, Any]) -> dict[str, Any]:
    return {family: {name: metrics[name] for name in METRICS} for family, metrics in panel.items()}


def bounded_record(
    result: dict[str, Any], packet: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    seeds = {
        seed: {
            "selected_panel": _panel_summary(value["selected_panel"]),
            "full_panel_baseline": _panel_summary(value["full_panel_baseline"]),
        }
        for seed, value in result["seed_results"].items()
    }
    return {
        "experiment_id": result["experiment_id"],
        "hypothesis_id": result["hypothesis_id"],
        "corpus_audit": result["corpus_audit"],
        "feature_panel": result["feature_panel"],
        "transform_variants": result["transform_variants"],
        "seed_results": seeds,
        "aggregate": result["aggregate"],
        "naibbe_external_positive_control": result["naibbe_external_positive_control"],
        "order_destruction_challenge": result["order_destruction_challenge"],
        "permutation": result["permutation"],
        "interpretation_gate": result["interpretation_gate"],
        "provenance": result["provenance"],
        "full_result_sha256": hashlib.sha256(
            orjson.dumps(result, option=orjson.OPT_SORT_KEYS)
        ).hexdigest(),
        "review_semantics": [
            "The 12-feature primary selector sees only training documents and "
            "non-heldout families.",
            "The 29-feature panel is a baseline and cannot replace the primary result post hoc.",
            "All variants are applied identically to both labels.",
            "Naibbe is external known-payload data and is never used for fitting or selection.",
            "A failed gate forbids Voynich scoring regardless of other favorable metrics.",
            "Voynichese and witness data are absent; no posterior probability is computed.",
        ],
        "review_facts": {
            "preregistered_thresholds": config["metrics"]["interpretation_gates"],
            "failed_gate_count": sum(
                not value for value in result["interpretation_gate"]["checks"].values()
            ),
            "voynich_or_witness_data_present": False,
            "permitted_effect_strength_values_when_gate_fails": ["none", "weak"],
        },
        "reference_context": packet["passages"],
        "reference_context_policy": packet["policy_note"],
    }


def critic_record(record: dict[str, Any]) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in record.items()
        if key not in {"reference_context", "reference_context_policy"}
    }
    compact["feature_panel"] = {
        "version": record["feature_panel"]["version"],
        "available_count": len(record["feature_panel"]["available_features"]),
        "selected_count": record["feature_panel"]["selected_count"],
        "always_selected": record["feature_panel"]["selection_audit"]["always_selected"],
        "never_selected": record["feature_panel"]["selection_audit"]["never_selected"],
        "final_model_features_by_seed": record["feature_panel"]["final_model_features_by_seed"],
    }
    compact["reference_context"] = [
        {"source_path": passage["source_path"], "heading": passage["heading"]}
        for passage in record["reference_context"]
    ]
    return compact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("qwen", "critic"))
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Immutable output already exists: {args.output}")
    result = orjson.loads(args.result.read_bytes())
    packet = orjson.loads(args.packet.read_bytes())
    config_path = repository_root() / result["provenance"]["config_path"]
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    record = bounded_record(result, packet, config)
    record["review_config_sha256"] = sha256_file(config_path)
    client = LocalAIClient()
    value = (
        client.review_experiment(record)
        if args.operation == "qwen"
        else client.critic(critic_record(record))
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(
        orjson.dumps(value, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    )


if __name__ == "__main__":
    main()
