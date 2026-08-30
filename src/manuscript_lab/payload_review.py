"""Bounded local review for E-005 known-payload retrieval."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

import orjson
import yaml

from manuscript_lab.local_ai import LocalAIClient
from manuscript_lab.provenance import repository_root, sha256_file


def bounded_record(
    result: dict[str, Any], packet: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    return {
        "experiment_id": result["experiment_id"],
        "hypothesis_id": result["hypothesis_id"],
        "source_summary": {
            "document_count": len(result["source_audit"]),
            "genres": sorted({item["genre"] for item in result["source_audit"]}),
            "folds": sorted({item["fold"] for item in result["source_audit"]}),
        },
        "normalization": result["normalization"],
        "feature_panel": result["feature_panel"],
        "cipher_suite": result["cipher_suite"],
        "family_results": result["family_results"],
        "aggregate": result["aggregate"],
        "permutation": result["permutation"],
        "interpretation_gate": result["interpretation_gate"],
        "provenance": result["provenance"],
        "full_result_sha256": hashlib.sha256(
            orjson.dumps(result, option=orjson.OPT_SORT_KEYS)
        ).hexdigest(),
        "review_semantics": [
            "Every retrieval query has 16 equal-length plaintext candidates in fixed groups.",
            "The heldout cipher family and heldout source documents are absent from fitting.",
            "Exact roundtrip verifies implementation behavior but is not evidence of retrieval.",
            "Payload retrieval is not semantic understanding, decryption, or language "
            "identification.",
            "Naibbe is not a primary paired gate because exact corpus-scale pair truth is absent.",
            "A failed gate forbids Voynich scoring regardless of favorable secondary metrics.",
            "Voynichese and witness data are absent; no posterior probability is computed.",
        ],
        "review_facts": {
            "preregistered_thresholds": config["metrics"]["interpretation_gates"],
            "failed_gate_count": sum(
                not value for value in result["interpretation_gate"]["checks"].values()
            ),
            "passed_gate_count": sum(result["interpretation_gate"]["checks"].values()),
            "total_gate_count": len(result["interpretation_gate"]["checks"]),
            "gate_checks_verbatim": result["interpretation_gate"]["checks"],
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
    compact["cipher_suite"] = {
        "implementation": record["cipher_suite"]["implementation"],
        "installed_version": record["cipher_suite"]["installed_version"],
        "revision": record["cipher_suite"]["revision"],
        "family_ids": [item["id"] for item in record["cipher_suite"]["families"]],
        "roundtrip": record["cipher_suite"]["roundtrip"],
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
