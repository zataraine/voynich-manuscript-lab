"""E-004 parameter-distribution ladder with training-only feature selection."""

from __future__ import annotations

import argparse
import platform
import random
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import orjson
import yaml
from jsonschema import Draft202012Validator

from manuscript_lab.cipher_transforms import (
    TRANSFORMS,
    apply_transform_variant,
    destroy_token_order,
)
from manuscript_lab.control_calibration import _document_metrics, _fit_model, _models
from manuscript_lab.control_corpus import TextSample, control_samples
from manuscript_lab.feature_panel import extract_sequence_features
from manuscript_lab.ledger import git_provenance
from manuscript_lab.provenance import repository_root, sha256_file
from manuscript_lab.transformation_ladder import _folds


def validate_variants(variants: list[dict[str, Any]]) -> None:
    ids = [str(variant["id"]) for variant in variants]
    if len(ids) != len(set(ids)):
        raise ValueError("Transform variant IDs must be unique")
    families = {str(variant["family"]) for variant in variants}
    if families != set(TRANSFORMS):
        raise ValueError("Variants must cover the complete transform registry")


def feature_matrices(
    samples: list[TextSample], variants: list[dict[str, Any]], *, seed: int
) -> tuple[dict[str, np.ndarray], list[str]]:
    matrices: dict[str, np.ndarray] = {}
    names: list[str] | None = None
    for variant in variants:
        variant_id = str(variant["id"])
        rows = [
            extract_sequence_features(
                apply_transform_variant(
                    sample.tokens, variant, seed=seed, sample_id=sample.sample_id
                )
            )
            for sample in samples
        ]
        current = sorted(rows[0])
        if names is None:
            names = current
        elif current != names:
            raise AssertionError("Feature panel changed across transform variants")
        matrices[variant_id] = np.asarray([[row[name] for name in names] for row in rows])
    assert names is not None
    return matrices, names


def select_invariant_features(
    matrices: dict[str, np.ndarray],
    labels: np.ndarray,
    train: np.ndarray,
    variant_ids: list[str],
    names: list[str],
    *,
    count: int,
) -> tuple[np.ndarray, dict[str, float]]:
    """Rank features using only supplied training rows and transform variants."""
    if not 1 <= count <= len(names):
        raise ValueError("Selected feature count is outside the panel")
    standardized = []
    separations = []
    for variant_id in variant_ids:
        matrix = matrices[variant_id][train]
        scale = np.std(matrix, axis=0)
        scale[scale == 0] = 1.0
        standardized.append((matrix - np.mean(matrix, axis=0)) / scale)
        separations.append(
            np.abs(
                np.mean(matrix[labels[train] == 1], axis=0)
                - np.mean(matrix[labels[train] == 0], axis=0)
            )
            / scale
        )
    separation = np.median(np.asarray(separations), axis=0)
    variant_cube = np.stack(standardized, axis=0)
    instability = np.median(np.std(variant_cube, axis=0), axis=0)
    scores = separation / (1.0 + instability)
    ranked = sorted(range(len(names)), key=lambda index: (-scores[index], names[index]))
    selected = np.asarray(sorted(ranked[:count]), dtype=int)
    return selected, {names[index]: float(scores[index]) for index in ranked}


def _variant_families(variants: list[dict[str, Any]]) -> dict[str, str]:
    return {str(variant["id"]): str(variant["family"]) for variant in variants}


def _ensemble_predict_many(
    train_x: np.ndarray,
    train_y: np.ndarray,
    train_groups: np.ndarray,
    targets: dict[str, np.ndarray],
    *,
    seed: int,
    workers: int,
    trees: int,
) -> dict[str, np.ndarray]:
    """Fit one ensemble and score several matrices without redundant refitting."""
    predictions = {name: [] for name in targets}
    for model in _models(seed, workers=workers, trees=trees):
        _fit_model(model, train_x, train_y, train_groups)
        for name, matrix in targets.items():
            predictions[name].append(model.predict_proba(matrix)[:, 1])
    return {name: np.mean(values, axis=0) for name, values in predictions.items()}


def evaluate_seed(
    matrices: dict[str, np.ndarray],
    names: list[str],
    variants: list[dict[str, Any]],
    labels: np.ndarray,
    groups: np.ndarray,
    folds: list[Any],
    *,
    seed: int,
    workers: int,
    trees: int,
    feature_count: int,
    include_baseline: bool = True,
) -> dict[str, Any]:
    family_by_variant = _variant_families(variants)
    families = sorted(set(family_by_variant.values()))
    primary: dict[str, Any] = {}
    baseline: dict[str, Any] = {}
    selection_records: list[dict[str, Any]] = []
    for family_index, family in enumerate(families):
        train_variants = [key for key, value in family_by_variant.items() if value != family]
        test_variants = [key for key, value in family_by_variant.items() if value == family]
        variant_scores = {variant_id: np.zeros(len(labels)) for variant_id in test_variants}
        baseline_variant_scores = {
            variant_id: np.zeros(len(labels)) for variant_id in test_variants
        }
        for fold_number, (train, test) in enumerate(folds):
            selected, ranking = select_invariant_features(
                matrices,
                labels,
                train,
                train_variants,
                names,
                count=feature_count,
            )
            selection_records.append(
                {
                    "heldout_family": family,
                    "fold": fold_number,
                    "features": [names[index] for index in selected],
                    "highest_ranking_score": max(ranking.values()),
                }
            )
            train_x = np.concatenate([matrices[key][train][:, selected] for key in train_variants])
            train_y = np.tile(labels[train], len(train_variants))
            train_groups = np.tile(groups[train], len(train_variants))
            model_seed = seed + family_index * 100 + fold_number
            fold_predictions = _ensemble_predict_many(
                train_x,
                train_y,
                train_groups,
                {
                    variant_id: matrices[variant_id][test][:, selected]
                    for variant_id in test_variants
                },
                seed=model_seed,
                workers=workers,
                trees=trees,
            )
            for variant_id, predictions in fold_predictions.items():
                variant_scores[variant_id][test] = predictions
            if include_baseline:
                full_train_x = np.concatenate([matrices[key][train] for key in train_variants])
                baseline_predictions = _ensemble_predict_many(
                    full_train_x,
                    train_y,
                    train_groups,
                    {variant_id: matrices[variant_id][test] for variant_id in test_variants},
                    seed=model_seed,
                    workers=workers,
                    trees=trees,
                )
                for variant_id, predictions in baseline_predictions.items():
                    baseline_variant_scores[variant_id][test] = predictions
        aggregate_scores = np.mean(np.asarray(list(variant_scores.values())), axis=0)
        metrics, _ = _document_metrics(labels, aggregate_scores, groups)
        primary[family] = {
            **metrics,
            "variant_metrics": {
                variant_id: _document_metrics(labels, scores, groups)[0]
                for variant_id, scores in variant_scores.items()
            },
        }
        if include_baseline:
            baseline_scores = np.mean(np.asarray(list(baseline_variant_scores.values())), axis=0)
            baseline[family] = _document_metrics(labels, baseline_scores, groups)[0]
    return {
        "selected_panel": primary,
        "full_panel_baseline": baseline,
        "selection_records": selection_records,
    }


def _final_challenges(
    samples: list[TextSample],
    naibbe: list[TextSample],
    matrices: dict[str, np.ndarray],
    names: list[str],
    variants: list[dict[str, Any]],
    labels: np.ndarray,
    groups: np.ndarray,
    *,
    seed: int,
    workers: int,
    trees: int,
    feature_count: int,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    variant_ids = [str(variant["id"]) for variant in variants]
    all_rows = np.arange(len(samples))
    selected, _ranking = select_invariant_features(
        matrices, labels, all_rows, variant_ids, names, count=feature_count
    )
    train_x = np.concatenate([matrices[key][:, selected] for key in variant_ids])
    train_y = np.tile(labels, len(variant_ids))
    train_groups = np.tile(groups, len(variant_ids))

    naibbe_rows = [extract_sequence_features(sample.tokens) for sample in naibbe]
    naibbe_x = np.asarray([[row[name] for name in names] for row in naibbe_rows])[:, selected]
    destroyed_by_variant: dict[str, np.ndarray] = {}
    for variant in variants:
        variant_id = str(variant["id"])
        rows = []
        for sample in samples:
            destroyed = destroy_token_order(sample.tokens, seed=seed, sample_id=sample.sample_id)
            transformed = apply_transform_variant(
                destroyed,
                variant,
                seed=seed,
                sample_id=f"{sample.sample_id}:destroyed",
            )
            features = extract_sequence_features(transformed)
            rows.append([features[name] for name in names])
        destroyed_by_variant[variant_id] = np.asarray(rows)[:, selected]
    targets = {"naibbe": naibbe_x}
    targets.update(
        {f"original:{variant_id}": matrices[variant_id][:, selected] for variant_id in variant_ids}
    )
    targets.update(
        {f"destroyed:{variant_id}": destroyed_by_variant[variant_id] for variant_id in variant_ids}
    )
    predictions = _ensemble_predict_many(
        train_x,
        train_y,
        train_groups,
        targets,
        seed=seed + 50_000,
        workers=workers,
        trees=trees,
    )
    naibbe_scores = predictions["naibbe"]
    original_scores = [predictions[f"original:{variant_id}"] for variant_id in variant_ids]
    destroyed_scores = [predictions[f"destroyed:{variant_id}"] for variant_id in variant_ids]
    meaningful = labels == 1
    drops = (
        np.mean(np.asarray(original_scores), axis=0)[meaningful]
        - np.mean(np.asarray(destroyed_scores), axis=0)[meaningful]
    )
    return naibbe_scores, drops, [names[index] for index in selected]


def _selection_audit(seed_results: dict[str, Any], names: list[str]) -> dict[str, Any]:
    counts = Counter(
        feature
        for result in seed_results.values()
        for record in result["selection_records"]
        for feature in record["features"]
    )
    total = sum(len(result["selection_records"]) for result in seed_results.values())
    return {
        "opportunities_per_feature": total,
        "selection_counts": {name: counts[name] for name in names},
        "always_selected": sorted(name for name in names if counts[name] == total),
        "never_selected": sorted(name for name in names if counts[name] == 0),
    }


def run_campaign(config_path: Path) -> dict[str, Any]:
    root = repository_root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    params = config["parameters"]
    variants = list(params["transform_variants"])
    validate_variants(variants)
    archive = root / params["control_archive"]
    all_samples = control_samples(
        archive,
        chunk_tokens=int(params["chunk_tokens"]),
        max_chunks_per_document=int(params["max_chunks_per_document"]),
    )
    samples = [
        sample for sample in all_samples if sample.family in {"meaningful", "human_gibberish"}
    ]
    naibbe = [sample for sample in all_samples if sample.family == "naibbe_payload"]
    labels = np.asarray([int(sample.family == "meaningful") for sample in samples])
    groups = np.asarray([sample.document_id for sample in samples])
    workers = int(params["workers"])
    trees = int(params["extra_trees_estimators"])
    feature_count = int(params["selected_feature_count"])
    evaluation_seeds = [int(seed) for seed in params["evaluation_seeds"]]
    seed_results: dict[str, Any] = {}
    seed_matrices: dict[int, dict[str, np.ndarray]] = {}
    feature_names: list[str] | None = None
    naibbe_seed_scores = []
    order_seed_drops = []
    final_features: dict[str, list[str]] = {}
    print(
        f"robust ladder: {len(samples)} chunks, {len(variants)} variants, "
        f"{len(evaluation_seeds)} seeds",
        flush=True,
    )
    for seed in evaluation_seeds:
        matrices, names = feature_matrices(samples, variants, seed=seed)
        if feature_names is None:
            feature_names = names
        elif feature_names != names:
            raise AssertionError("Feature panel changed across evaluation seeds")
        seed_matrices[seed] = matrices
        folds = _folds(labels, groups, count=int(params["folds"]), seed=seed)
        evaluation = evaluate_seed(
            matrices,
            names,
            variants,
            labels,
            groups,
            folds,
            seed=seed,
            workers=workers,
            trees=trees,
            feature_count=feature_count,
        )
        seed_results[str(seed)] = evaluation
        naibbe_scores, drops, selected = _final_challenges(
            samples,
            naibbe,
            matrices,
            names,
            variants,
            labels,
            groups,
            seed=seed,
            workers=workers,
            trees=trees,
            feature_count=feature_count,
        )
        naibbe_seed_scores.append(naibbe_scores)
        order_seed_drops.append(drops)
        final_features[str(seed)] = selected
        print(f"robust ladder: completed evaluation seed {seed}", flush=True)
    assert feature_names is not None

    permutation_seed = int(config["null_model"]["evaluation_seed"])
    matrices = seed_matrices[permutation_seed]
    folds = _folds(labels, groups, count=int(params["folds"]), seed=permutation_seed)
    observed = float(
        np.mean(
            [
                metrics["document_balanced_accuracy"]
                for metrics in seed_results[str(permutation_seed)]["selected_panel"].values()
            ]
        )
    )
    rng = random.Random(int(config["seed"]) + 77)
    document_labels = {
        group: int(labels[np.flatnonzero(groups == group)[0]]) for group in sorted(set(groups))
    }
    original_labels = list(document_labels.values())
    permutation_values = []
    for iteration in range(int(params["permutation_iterations"])):
        shuffled = original_labels.copy()
        rng.shuffle(shuffled)
        mapping = dict(zip(document_labels, shuffled, strict=True))
        permuted = np.asarray([mapping[group] for group in groups])
        evaluation = evaluate_seed(
            matrices,
            feature_names,
            variants,
            permuted,
            groups,
            folds,
            seed=permutation_seed + 100_000 + iteration,
            workers=workers,
            trees=trees,
            feature_count=feature_count,
            include_baseline=False,
        )
        permutation_values.append(
            float(
                np.mean(
                    [
                        metrics["document_balanced_accuracy"]
                        for metrics in evaluation["selected_panel"].values()
                    ]
                )
            )
        )
        if (iteration + 1) % 4 == 0:
            print(
                f"robust ladder: completed {iteration + 1}/"
                f"{params['permutation_iterations']} permutations",
                flush=True,
            )

    family_accuracies = [
        metrics["document_balanced_accuracy"]
        for result in seed_results.values()
        for metrics in result["selected_panel"].values()
    ]
    seed_means = {
        seed: float(
            np.mean(
                [
                    metrics["document_balanced_accuracy"]
                    for metrics in result["selected_panel"].values()
                ]
            )
        )
        for seed, result in seed_results.items()
    }
    naibbe_ensemble = np.mean(np.asarray(naibbe_seed_scores), axis=0)
    order_ensemble = np.mean(np.asarray(order_seed_drops), axis=0)
    gates = config["metrics"]["interpretation_gates"]
    checks = {
        "median_heldout_family_accuracy": float(np.median(family_accuracies))
        >= float(gates["minimum_median_heldout_family_accuracy"]),
        "worst_heldout_family_accuracy": min(family_accuracies)
        >= float(gates["minimum_worst_heldout_family_accuracy"]),
        "worst_seed_mean_accuracy": min(seed_means.values())
        >= float(gates["minimum_worst_seed_mean_accuracy"]),
        "naibbe_transfer": float(np.median(naibbe_ensemble))
        >= float(gates["minimum_naibbe_median"]),
        "order_destruction_sensitivity": float(np.median(order_ensemble))
        >= float(gates["minimum_order_destruction_median_drop"]),
    }
    passed = all(checks.values())
    return {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "hypothesis_id": config["hypothesis_id"],
        "run_finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "corpus_audit": {
            "documents": dict(
                Counter(sample.family for sample in samples if sample.sample_id.endswith(":000"))
            ),
            "chunks": dict(Counter(sample.family for sample in samples)),
            "naibbe_chunks": len(naibbe),
        },
        "feature_panel": {
            "version": "surface-sequence-panel-v2",
            "available_features": feature_names,
            "selected_count": feature_count,
            "selection_audit": _selection_audit(seed_results, feature_names),
            "final_model_features_by_seed": final_features,
        },
        "transform_variants": variants,
        "seed_results": seed_results,
        "aggregate": {
            "median_seed_family_document_balanced_accuracy": float(np.median(family_accuracies)),
            "worst_seed_family_document_balanced_accuracy": float(min(family_accuracies)),
            "seed_mean_document_balanced_accuracy": seed_means,
            "worst_seed_mean_document_balanced_accuracy": float(min(seed_means.values())),
        },
        "naibbe_external_positive_control": {
            "sample_count": len(naibbe),
            "seed_medians": [float(np.median(scores)) for scores in naibbe_seed_scores],
            "ensemble_median_meaningful_similarity": float(np.median(naibbe_ensemble)),
            "ensemble_interquartile_range": [
                float(np.quantile(naibbe_ensemble, 0.25)),
                float(np.quantile(naibbe_ensemble, 0.75)),
            ],
        },
        "order_destruction_challenge": {
            "meaningful_sample_count": int(np.sum(labels == 1)),
            "seed_median_score_drops": [float(np.median(drops)) for drops in order_seed_drops],
            "ensemble_median_score_drop": float(np.median(order_ensemble)),
            "ensemble_mean_score_drop": float(np.mean(order_ensemble)),
            "ensemble_fraction_with_positive_drop": float(np.mean(order_ensemble > 0)),
        },
        "permutation": {
            "evaluation_seed": permutation_seed,
            "iterations": len(permutation_values),
            "observed_mean_heldout_family_accuracy": observed,
            "null_mean": float(np.mean(permutation_values)),
            "one_sided_p": (1 + sum(value >= observed for value in permutation_values))
            / (len(permutation_values) + 1),
        },
        "interpretation_gate": {
            "checks": checks,
            "passed": passed,
            "permitted_next_step": (
                "independent external replication before a separately preregistered "
                "target comparison"
                if passed
                else "revise controls or features; no Voynich target comparison"
            ),
            "voynich_scored": False,
            "posterior_probability": None,
        },
        "provenance": {
            "control_archive": params["control_archive"],
            "control_archive_sha256": sha256_file(archive),
            "source_manifest": config["source_manifest"],
            "source_manifest_sha256": sha256_file(root / config["source_manifest"]),
            "config_path": config_path.relative_to(root).as_posix(),
            "config_sha256": sha256_file(config_path),
            "evaluation_seeds": evaluation_seeds,
            "workers": workers,
            "extra_trees_estimators": trees,
            "git": git_provenance(root),
            "environment": {
                "device": "cpu",
                "python": sys.version,
                "platform": platform.platform(),
                "uv_lock_sha256": sha256_file(root / "uv.lock"),
            },
        },
    }


def validate_result(result: dict[str, Any]) -> None:
    schema = orjson.loads(
        (repository_root() / "schemas" / "robust-parameter-ladder-result.schema.json").read_bytes()
    )
    Draft202012Validator(schema).validate(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Immutable output already exists: {args.output}")
    result = run_campaign(args.config.resolve())
    validate_result(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(
        orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    )


if __name__ == "__main__":
    main()
