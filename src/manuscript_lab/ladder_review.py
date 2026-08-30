"""Bounded local review for the cipher-transformation ladder."""

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
    result: dict[str, Any], packet: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    survival = {
        family: {key: value for key, value in summary.items() if key != "feature_spearman"}
        for family, summary in result["feature_survival"].items()
    }
    return {
        **result,
        "feature_survival": survival,
        "full_result_sha256": hashlib.sha256(
            orjson.dumps(result, option=orjson.OPT_SORT_KEYS)
        ).hexdigest(),
        "review_semantics": [
            "Each test family is absent from fitting and scored only on unseen source documents.",
            "Both labels receive identical seeded transforms, so transform identity cannot "
            "define a label.",
            "Naibbe is an external known-payload positive control and is never fitting data.",
            "Token-order destruction preserves token inventory and tests sequence sensitivity, "
            "not total meaning loss.",
            "A failed gate is a valid negative result and forbids a Voynich target comparison.",
            "Voynichese is absent from this experiment and no posterior probability is computed.",
        ],
        "review_facts": {
            "preregistered_thresholds": (
                config["metrics"]["interpretation_gates"] if config is not None else "not supplied"
            ),
            "voynich_or_witness_data_present": False,
            "leakage_evidence_reported": False,
            "failed_gate_count": sum(
                not value for value in result["interpretation_gate"]["checks"].values()
            ),
            "permitted_effect_strength_values_when_gate_fails": ["none", "weak"],
        },
        "reference_context": packet["passages"],
        "reference_context_policy": packet["policy_note"],
    }


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
    value = client.review_experiment(record) if args.operation == "qwen" else client.critic(record)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(
        orjson.dumps(value, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    )


if __name__ == "__main__":
    main()
