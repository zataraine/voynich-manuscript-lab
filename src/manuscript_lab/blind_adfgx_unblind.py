"""Unblind and evaluate the E-008 scores only after blind scoring is complete."""

from __future__ import annotations

import argparse
import random
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import orjson
import yaml
from sklearn.metrics import roc_auc_score

from manuscript_lab.ledger import git_provenance
from manuscript_lab.provenance import repository_root, sha256_file

PUBLIC_FORBIDDEN_KEYS = {
    "broken_mapping_seed",
    "correct_candidate_id",
    "generator_seed",
    "generator_seeds",
    "keyword",
    "offset",
    "read_order",
    "segment_seed",
    "source_id",
    "source_path",
    "square",
    "width",
}


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


def retrieval_rows(rows: list[np.ndarray], correct: list[int]) -> dict[str, float]:
    if not rows or len(rows) != len(correct):
        raise ValueError("Retrieval rows and correct identities must be nonempty and aligned")
    candidate_count = rows[0].size
    ranks = []
    labels = []
    flattened = []
    for scores, target_index in zip(rows, correct, strict=True):
        if scores.size != candidate_count:
            raise ValueError("Every retrieval row must have the same candidate count")
        target = scores[target_index]
        rank = 1.0 + float(np.sum(scores > target)) + 0.5 * float(np.sum(scores == target) - 1)
        ranks.append(rank)
        labels.extend(int(index == target_index) for index in range(candidate_count))
        flattened.extend(float(value) for value in scores)
    mrr = float(np.mean(1.0 / np.asarray(ranks)))
    chance = float(sum(1.0 / rank for rank in range(1, candidate_count + 1)) / candidate_count)
    return {
        "queries": len(rows),
        "candidates_per_query": candidate_count,
        "mean_reciprocal_rank": mrr,
        "normalized_mrr": (mrr - chance) / (1.0 - chance),
        "pair_roc_auc": float(roc_auc_score(labels, flattened)),
        "top1_fraction": float(np.mean(np.asarray(ranks) == 1.0)),
        "median_rank": float(np.median(ranks)),
    }


def _permutation_p(
    suite_rows: list[list[np.ndarray]],
    suite_correct: list[list[int]],
    observed: float,
    *,
    iterations: int,
    seed: int,
) -> tuple[float, float]:
    rng = random.Random(seed)
    null = []
    for _ in range(iterations):
        rows: list[np.ndarray] = []
        correct: list[int] = []
        for local_rows, local_correct in zip(suite_rows, suite_correct, strict=True):
            assignment = list(local_correct)
            rng.shuffle(assignment)
            rows.extend(local_rows)
            correct.extend(assignment)
        null.append(retrieval_rows(rows, correct)["normalized_mrr"])
    p_value = (1 + sum(value >= observed for value in null)) / (iterations + 1)
    return float(p_value), float(np.mean(null))


def unblind(config_path: Path) -> dict[str, Any]:
    root = repository_root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if sha256_file(root / config["source_manifest"]) != config["source_manifest_sha256"]:
        raise ValueError("Frozen E-008 source manifest hash changed")
    predecessor = config["predecessor"]
    if sha256_file(root / predecessor["result"]) != predecessor["result_sha256"]:
        raise ValueError("Frozen E-007 result hash changed")
    separation = config["separation"]
    scorer_config_path = root / separation["scorer_config"]
    if sha256_file(scorer_config_path) != separation["scorer_config_sha256"]:
        raise ValueError("Frozen truth-free scorer config hash changed")

    public_path = root / separation["public_suite"]
    truth_path = root / separation["sealed_truth"]
    scores_path = root / separation["blind_scores"]
    public = orjson.loads(public_path.read_bytes())
    truth = orjson.loads(truth_path.read_bytes())
    scores = orjson.loads(scores_path.read_bytes())
    public_hash = sha256_file(public_path)
    if truth["public_suite_sha256"] != public_hash:
        raise ValueError("Sealed truth was not generated for this public suite")
    if scores["public_suite_sha256"] != public_hash:
        raise ValueError("Blind scores were not generated from this public suite")
    if scores["scorer_config_sha256"] != separation["scorer_config_sha256"]:
        raise ValueError("Blind scores used a different scorer config")
    if scores.get("truth_accessed") is not False:
        raise ValueError("Blind scorer did not attest truth isolation")

    truth_by_query = {item["query_id"]: item for item in truth["queries"]}
    suite_rows: list[list[np.ndarray]] = []
    suite_correct: list[list[int]] = []
    overall_rows: list[np.ndarray] = []
    overall_broken_rows: list[np.ndarray] = []
    overall_correct: list[int] = []
    width_rows: dict[int, list[np.ndarray]] = {
        int(width): [] for width in config["parameters"]["widths"]
    }
    width_correct: dict[int, list[int]] = {width: [] for width in width_rows}
    width_recovery = []
    correct_drops = []
    broken_correct_scores = []
    query_audit = []
    for suite in scores["suites"]:
        candidate_ids = suite["candidate_ids"]
        local_rows = []
        local_correct = []
        for query in suite["queries"]:
            query_truth = truth_by_query[query["query_id"]]
            correct_index = candidate_ids.index(query_truth["correct_candidate_id"])
            ordered_widths = sorted(int(width) for width in query["scores_by_width"])
            by_width = np.asarray(
                [query["scores_by_width"][str(width)] for width in ordered_widths],
                dtype=np.float64,
            )
            broken_by_width = np.asarray(
                [query["broken_scores_by_width"][str(width)] for width in ordered_widths],
                dtype=np.float64,
            )
            best = by_width.max(axis=0)
            broken_best = broken_by_width.max(axis=0)
            correct_score = float(best[correct_index])
            broken_correct = float(broken_best[correct_index])
            maximizing_widths = [
                width
                for width, score in zip(ordered_widths, by_width[:, correct_index], strict=True)
                if np.isclose(score, correct_score)
            ]
            true_width = int(query_truth["width"])
            width_recovery.append(true_width in maximizing_widths)
            correct_drops.append(correct_score - broken_correct)
            broken_correct_scores.append(broken_correct)
            local_rows.append(best)
            local_correct.append(correct_index)
            overall_rows.append(best)
            overall_broken_rows.append(broken_best)
            overall_correct.append(correct_index)
            width_rows[true_width].append(best)
            width_correct[true_width].append(correct_index)
            query_audit.append(
                {
                    "suite_id": suite["suite_id"],
                    "query_id": query["query_id"],
                    "true_width": true_width,
                    "maximizing_widths_for_correct_candidate": maximizing_widths,
                    "correct_score": correct_score,
                    "broken_correct_score": broken_correct,
                    "score_drop": correct_score - broken_correct,
                }
            )
        suite_rows.append(local_rows)
        suite_correct.append(local_correct)

    overall = retrieval_rows(overall_rows, overall_correct)
    broken = retrieval_rows(overall_broken_rows, overall_correct)
    by_width_metrics = {
        str(width): retrieval_rows(width_rows[width], width_correct[width])
        for width in sorted(width_rows)
    }
    iterations = int(config["parameters"]["identity_permutation_iterations"])
    p_value, null_mean = _permutation_p(
        suite_rows,
        suite_correct,
        overall["normalized_mrr"],
        iterations=iterations,
        seed=int(config["parameters"]["identity_permutation_seed"]),
    )
    public_leaks = sorted(PUBLIC_FORBIDDEN_KEYS & _recursive_keys(public))
    metrics = {
        "generator_roundtrip_fraction": float(truth["roundtrip_fraction"]),
        "public_truth_leak_count": len(public_leaks),
        "overall_normalized_mrr": overall["normalized_mrr"],
        "worst_width_normalized_mrr": min(
            value["normalized_mrr"] for value in by_width_metrics.values()
        ),
        "overall_pair_roc_auc": overall["pair_roc_auc"],
        "true_width_in_maximizer_fraction": float(np.mean(width_recovery)),
        "median_correct_mapping_score_drop": float(np.median(correct_drops)),
        "median_broken_correct_score": float(np.median(broken_correct_scores)),
        "identity_permutation_one_sided_p": p_value,
    }
    thresholds = config["metrics"]["interpretation_gates"]
    gates = {
        "generator_roundtrip": metrics["generator_roundtrip_fraction"]
        >= thresholds["minimum_generator_roundtrip_fraction"],
        "public_truth_isolation": metrics["public_truth_leak_count"]
        <= thresholds["maximum_public_truth_leak_count"],
        "overall_retrieval": metrics["overall_normalized_mrr"]
        >= thresholds["minimum_overall_normalized_mrr"],
        "worst_width_retrieval": metrics["worst_width_normalized_mrr"]
        >= thresholds["minimum_worst_width_normalized_mrr"],
        "pair_auc": metrics["overall_pair_roc_auc"] >= thresholds["minimum_overall_pair_roc_auc"],
        "width_recovery": metrics["true_width_in_maximizer_fraction"]
        >= thresholds["minimum_true_width_in_maximizer_fraction"],
        "mapping_destruction_drop": metrics["median_correct_mapping_score_drop"]
        >= thresholds["minimum_median_correct_mapping_score_drop"],
        "broken_score": metrics["median_broken_correct_score"]
        <= thresholds["maximum_median_broken_correct_score"],
        "identity_permutation": metrics["identity_permutation_one_sided_p"]
        <= thresholds["maximum_identity_permutation_p"],
    }
    result = {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "hypothesis_id": config["hypothesis_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "pass" if all(gates.values()) else "fail",
        "target_scored": False,
        "candidate_plaintext_supplied": True,
        "config": str(config_path.relative_to(root)),
        "config_sha256": sha256_file(config_path),
        "public_suite_sha256": public_hash,
        "sealed_truth_sha256": sha256_file(truth_path),
        "blind_scores_sha256": sha256_file(scores_path),
        "source_manifest_sha256": config["source_manifest_sha256"],
        "public_forbidden_keys": public_leaks,
        "overall": overall,
        "broken_control": broken,
        "by_true_width": by_width_metrics,
        "metrics": metrics,
        "gates": gates,
        "gate_count": {"passed": sum(gates.values()), "total": len(gates)},
        "permutation": {
            "iterations": iterations,
            "null_mean_normalized_mrr": null_mean,
            "one_sided_p": p_value,
        },
        "runtime": {
            "width_seconds_real_plus_broken": scores["width_seconds_real_plus_broken"],
            "total_scoring_seconds": sum(scores["width_seconds_real_plus_broken"].values()),
        },
        "query_audit": query_audit,
        "provenance": {
            **git_provenance(root),
            "python": sys.version.split()[0],
            "generator": truth["generator_implementation"],
            "pycipher_commit": truth["pycipher_commit"],
            "frozen_solver_commit": config["predecessor"]["frozen_solver_commit"],
            "blind_scorer_git_commit": scores["provenance"]["git_commit"],
            "blind_scorer_git_dirty": scores["provenance"]["git_dirty"],
        },
        "interpretation": (
            "Independent parameter-blind known-payload replication only; no Voynich "
            "inference or ciphertext-only decryption claim is permitted."
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
            {"status": result["status"], "metrics": result["metrics"], "gates": result["gates"]},
            option=orjson.OPT_INDENT_2,
        ).decode()
    )


if __name__ == "__main__":
    main()
