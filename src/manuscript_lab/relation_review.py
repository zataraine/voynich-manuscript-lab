"""Bounded local review records for E-006."""

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
    family_results = {
        family: {
            "mean_normalized_mrr": values["mean_normalized_mrr"],
            "mean_top1_lift_over_chance": values["mean_top1_lift_over_chance"],
            "mean_pair_roc_auc": values["mean_pair_roc_auc"],
        }
        for family, values in result["family_results"].items()
    }
    same_family = {
        family: {
            "mean_normalized_mrr": values["mean_normalized_mrr"],
            "mean_pair_roc_auc": values["mean_pair_roc_auc"],
        }
        for family, values in result["same_family_diagnostic"].items()
    }
    diagnostic_components = {
        representation: {
            family: {
                "mean_normalized_mrr": values["mean_normalized_mrr"],
                "mean_pair_roc_auc": values["mean_pair_roc_auc"],
            }
            for family, values in families.items()
        }
        for representation, families in result["representations"]["diagnostic_results"].items()
    }
    ordered_primary = sorted(
        (
            {
                "family": family,
                "mean_normalized_mrr": values["mean_normalized_mrr"],
                "mean_pair_roc_auc": values["mean_pair_roc_auc"],
            }
            for family, values in family_results.items()
        ),
        key=lambda value: value["mean_normalized_mrr"],
    )
    failed_gates = [
        name for name, passed in result["interpretation_gate"]["checks"].items() if not passed
    ]
    same_family_failures = {
        family: values
        for family, values in same_family.items()
        if values["mean_normalized_mrr"] <= 0 or values["mean_pair_roc_auc"] < 0.5
    }
    record = {
        "experiment_id": result["experiment_id"],
        "hypothesis_id": result["hypothesis_id"],
        "source_summary": {
            "documents": len(result["source_audit"]),
            "folds": sorted({item["fold"] for item in result["source_audit"]}),
            "cipher_families": list(family_results),
        },
        "primary_representation": result["representations"]["primary"],
        "representation_dimensions": result["representations"]["dimensions"],
        "family_results": family_results,
        "same_family_diagnostic": same_family,
        "diagnostic_components": diagnostic_components,
        "destruction_control": result["destruction_control"],
        "seed_means": result["seed_means"],
        "aggregate": result["aggregate"],
        "permutation": result["permutation"],
        "interpretation_gate": result["interpretation_gate"],
        "provenance": result["provenance"],
        "full_result_sha256": hashlib.sha256(
            orjson.dumps(result, option=orjson.OPT_SORT_KEYS)
        ).hexdigest(),
        "review_semantics": [
            "The fused representation was named before implementation; components are diagnostic.",
            "Every primary fit excludes the complete evaluated cipher family and "
            "source-document fold.",
            "Same-family calibration is diagnostic and cannot replace family-blind transfer.",
            "Exact decryption is an implementation ceiling, not blind retrieval evidence.",
            "E-005 is exposed, so even a pass requires a new independent cipher suite.",
            "Voynichese and manuscript witnesses are absent; no posterior is computed.",
            "A failed gate forbids target scoring regardless of a favorable component.",
            "Enigma is not near chance in the primary fusion: its normalized MRR is 0.6225 "
            "and pair ROC AUC is 0.9193.",
            "ADFGX also fails the same-family diagnostic; do not say every same-family "
            "calibration succeeded.",
            "The cipher family identifier is ADFGX. No reported normalized MRR exceeds 1.0; "
            "Affine and Vigenere are exactly 1.0.",
        ],
        "review_facts": {
            "preregistered_thresholds": config["metrics"]["interpretation_gates"],
            "gate_checks_verbatim": result["interpretation_gate"]["checks"],
            "failed_gate_count": sum(
                not value for value in result["interpretation_gate"]["checks"].values()
            ),
            "passed_gate_count": sum(result["interpretation_gate"]["checks"].values()),
            "failed_gate_names": failed_gates,
            "primary_families_ordered_worst_first": ordered_primary,
            "same_family_failures": same_family_failures,
            "explicit_result_boundary": (
                "Two of eight gates failed. Both failed aggregate gates are caused by ADFGX: "
                "family normalized MRR 0.0472 is below 0.05 and pair ROC AUC 0.5078 is below "
                "0.55. Enigma passed these family-level magnitudes. No target scoring."
            ),
            "permitted_effect_strength_values_when_gate_fails": ["none", "weak"],
        },
        "reference_context": packet["passages"],
        "reference_context_policy": packet["policy_note"],
    }
    record["review_config_sha256"] = sha256_file(
        repository_root() / result["provenance"]["config_path"]
    )
    return record


def critic_record(record: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "experiment_id",
        "hypothesis_id",
        "source_summary",
        "primary_representation",
        "representation_dimensions",
        "family_results",
        "same_family_diagnostic",
        "destruction_control",
        "seed_means",
        "aggregate",
        "permutation",
        "interpretation_gate",
        "review_semantics",
        "review_facts",
        "full_result_sha256",
        "review_config_sha256",
    )
    return {key: record[key] for key in keep}


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
