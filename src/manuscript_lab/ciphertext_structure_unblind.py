"""Unblind E-009 ciphertext-only scores after the scorer output is frozen."""

from __future__ import annotations

import argparse
import itertools
import random
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import orjson
import yaml
from sklearn.metrics import roc_auc_score

from manuscript_lab.ciphertext_structure_scorer import FORBIDDEN_PUBLIC_KEYS
from manuscript_lab.ledger import git_provenance
from manuscript_lab.provenance import repository_root, sha256_file


def _recursive_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(value)
        for item in value.values():
            keys.update(_recursive_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_recursive_keys(item))
    return keys


def _paired_auc(natural: list[float], control: list[float]) -> float:
    labels = [1] * len(natural) + [0] * len(control)
    return float(roc_auc_score(labels, natural + control))


def _sign_permutation_p(
    differences: list[float], iterations: int, seed: int
) -> tuple[float, float]:
    observed = float(np.mean(differences))
    rng = random.Random(seed)
    null = []
    for _ in range(iterations):
        null.append(float(np.mean([value * rng.choice((-1, 1)) for value in differences])))
    return float((1 + sum(value >= observed for value in null)) / (iterations + 1)), float(
        np.mean(null)
    )


def unblind(config_path: Path) -> dict[str, Any]:
    root = repository_root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if sha256_file(root / config["source_manifest"]) != config["source_manifest_sha256"]:
        raise ValueError("Frozen E-009 source manifest hash changed")
    predecessor = config["predecessor"]
    if sha256_file(root / predecessor["result"]) != predecessor["result_sha256"]:
        raise ValueError("Frozen E-008 result hash changed")
    separation = config["separation"]
    scorer_config_path = root / separation["scorer_config"]
    if sha256_file(scorer_config_path) != separation["scorer_config_sha256"]:
        raise ValueError("Frozen E-009 scorer config hash changed")

    public_path = root / separation["public_suite"]
    truth_path = root / separation["sealed_truth"]
    scores_path = root / separation["blind_scores"]
    public = orjson.loads(public_path.read_bytes())
    truth = orjson.loads(truth_path.read_bytes())
    scores = orjson.loads(scores_path.read_bytes())
    public_hash = sha256_file(public_path)
    if truth["public_suite_sha256"] != public_hash or scores["public_suite_sha256"] != public_hash:
        raise ValueError("Public suite, sealed truth, and blind scores are not hash-aligned")
    if scores["scorer_config_sha256"] != separation["scorer_config_sha256"]:
        raise ValueError("Blind scores used a different scorer config")
    for boundary in ("plaintext_accessed", "candidate_plaintext_accessed", "truth_accessed"):
        if scores.get(boundary) is not False:
            raise ValueError(f"Scorer did not attest {boundary}=false")

    truth_by_query = {item["query_id"]: item for item in truth["queries"]}
    order_indices = {
        width: {order: index for index, order in enumerate(itertools.permutations(range(width)))}
        for width in config["parameters"]["widths"]
    }
    records = []
    for query in scores["queries"]:
        query_truth = truth_by_query[query["query_id"]]
        corrected = {
            int(width): float(values["corrected_score"])
            for width, values in query["widths"].items()
        }
        selected_score = max(corrected.values())
        maximizing_widths = [
            width for width, value in corrected.items() if np.isclose(value, selected_score)
        ]
        true_width = int(query_truth["width"])
        true_order = tuple(query_truth["read_order"])
        true_index = order_indices[true_width][true_order]
        raw_scores = np.asarray(
            query["widths"][str(true_width)]["raw_order_scores"], dtype=np.float64
        )
        true_score = raw_scores[true_index]
        percentile = (
            float(np.sum(raw_scores < true_score))
            + 0.5 * float(np.sum(np.isclose(raw_scores, true_score)))
        ) / raw_scores.size
        records.append(
            {
                "query_id": query["query_id"],
                "base_id": query_truth["base_id"],
                "family": query_truth["family"],
                "true_width": true_width,
                "maximizing_widths": maximizing_widths,
                "selected_score": selected_score,
                "true_order_raw_score": float(true_score),
                "true_order_percentile": percentile,
            }
        )

    by_base: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        by_base.setdefault(record["base_id"], {})[record["family"]] = record
    families = list(config["parameters"]["control_families"])
    family_scores = {
        family: [by_base[base][family]["selected_score"] for base in sorted(by_base)]
        for family in families
    }
    natural = family_scores["natural"]
    unigram = family_scores["unigram_shuffle"]
    markov = family_scores["markov1"]
    block = family_scores["block8_shuffle"]
    copy = family_scores["copy_mutate"]
    natural_records = [by_base[base]["natural"] for base in sorted(by_base)]
    natural_unigram_differences = [
        left - right for left, right in zip(natural, unigram, strict=True)
    ]
    simple_differences = [
        left - (right_unigram + right_markov) / 2.0
        for left, right_unigram, right_markov in zip(natural, unigram, markov, strict=True)
    ]
    iterations = int(config["parameters"]["sign_permutation_iterations"])
    p_value, null_mean = _sign_permutation_p(
        simple_differences,
        iterations,
        int(config["parameters"]["sign_permutation_seed"]),
    )
    public_leaks = sorted(FORBIDDEN_PUBLIC_KEYS & _recursive_keys(public))
    metrics = {
        "generator_roundtrip_fraction": float(truth["roundtrip_fraction"]),
        "public_truth_leak_count": len(public_leaks),
        "natural_vs_unigram_roc_auc": _paired_auc(natural, unigram),
        "natural_vs_markov1_roc_auc": _paired_auc(natural, markov),
        "median_natural_minus_unigram_score": float(np.median(natural_unigram_differences)),
        "natural_correct_width_fraction": float(
            np.mean(
                [record["true_width"] in record["maximizing_widths"] for record in natural_records]
            )
        ),
        "natural_true_order_median_percentile": float(
            np.median([record["true_order_percentile"] for record in natural_records])
        ),
        "natural_beats_paired_unigram_fraction": float(
            np.mean(np.asarray(natural_unigram_differences) > 0)
        ),
        "paired_sign_permutation_one_sided_p": p_value,
    }
    diagnostics = {
        "natural_vs_block8_roc_auc": _paired_auc(natural, block),
        "natural_vs_copy_mutate_roc_auc": _paired_auc(natural, copy),
        "median_natural_minus_block8_score": float(
            np.median(np.asarray(natural) - np.asarray(block))
        ),
        "median_natural_minus_copy_mutate_score": float(
            np.median(np.asarray(natural) - np.asarray(copy))
        ),
        "natural_beats_block8_fraction": float(np.mean(np.asarray(natural) > np.asarray(block))),
        "natural_beats_copy_mutate_fraction": float(
            np.mean(np.asarray(natural) > np.asarray(copy))
        ),
        "family_score_summary": {
            family: {
                "median": float(np.median(values)),
                "minimum": float(np.min(values)),
                "maximum": float(np.max(values)),
            }
            for family, values in family_scores.items()
        },
    }
    thresholds = config["metrics"]["interpretation_gates"]
    gates = {
        "generator_roundtrip": metrics["generator_roundtrip_fraction"]
        >= thresholds["minimum_generator_roundtrip_fraction"],
        "public_truth_isolation": metrics["public_truth_leak_count"]
        <= thresholds["maximum_public_truth_leak_count"],
        "natural_vs_unigram_auc": metrics["natural_vs_unigram_roc_auc"]
        >= thresholds["minimum_natural_vs_unigram_roc_auc"],
        "natural_vs_markov_auc": metrics["natural_vs_markov1_roc_auc"]
        >= thresholds["minimum_natural_vs_markov1_roc_auc"],
        "natural_unigram_margin": metrics["median_natural_minus_unigram_score"]
        >= thresholds["minimum_median_natural_minus_unigram_score"],
        "width_recovery": metrics["natural_correct_width_fraction"]
        >= thresholds["minimum_natural_correct_width_fraction"],
        "order_recovery": metrics["natural_true_order_median_percentile"]
        >= thresholds["minimum_natural_true_order_median_percentile"],
        "paired_unigram_wins": metrics["natural_beats_paired_unigram_fraction"]
        >= thresholds["minimum_natural_beats_paired_unigram_fraction"],
        "paired_sign_permutation": metrics["paired_sign_permutation_one_sided_p"]
        <= thresholds["maximum_paired_sign_permutation_p"],
    }
    result = {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "hypothesis_id": config["hypothesis_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "pass" if all(gates.values()) else "fail",
        "target_scored": False,
        "plaintext_supplied_to_scorer": False,
        "config": str(config_path.relative_to(root)),
        "config_sha256": sha256_file(config_path),
        "public_suite_sha256": public_hash,
        "sealed_truth_sha256": sha256_file(truth_path),
        "blind_scores_sha256": sha256_file(scores_path),
        "source_manifest_sha256": config["source_manifest_sha256"],
        "public_forbidden_keys": public_leaks,
        "metrics": metrics,
        "adversarial_diagnostics": diagnostics,
        "gates": gates,
        "gate_count": {"passed": sum(gates.values()), "total": len(gates)},
        "permutation": {
            "iterations": iterations,
            "observed_mean_difference": float(np.mean(simple_differences)),
            "null_mean": null_mean,
            "one_sided_p": p_value,
        },
        "runtime": {
            "width_seconds": scores["width_seconds"],
            "total_scoring_seconds": sum(scores["width_seconds"].values()),
        },
        "query_audit": records,
        "provenance": {
            **git_provenance(root),
            "python": sys.version.split()[0],
            "generator": truth["generator_implementation"],
            "pycipher_commit": truth["pycipher_commit"],
            "blind_scorer_git_commit": scores["provenance"]["git_commit"],
            "blind_scorer_git_dirty": scores["provenance"]["git_dirty"],
        },
        "interpretation": (
            "Ciphertext-only bounded ADFGX control result; no Voynich inference, "
            "semantic identification, or general language-versus-hoax claim is permitted."
        ),
    }
    output = root / separation["result"]
    if output.exists():
        raise FileExistsError(f"Immutable output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(
        orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    result = unblind(args.config.resolve())
    print(
        orjson.dumps(
            {
                "status": result["status"],
                "metrics": result["metrics"],
                "diagnostics": result["adversarial_diagnostics"],
                "gates": result["gates"],
            },
            option=orjson.OPT_INDENT_2,
        ).decode()
    )


if __name__ == "__main__":
    main()
