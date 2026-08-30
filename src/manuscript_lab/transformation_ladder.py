"""E-003 paired cipher-family transfer and feature-survival campaign."""

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
from scipy.stats import spearmanr
from sklearn.model_selection import StratifiedGroupKFold

from manuscript_lab.cipher_transforms import TRANSFORMS, apply_transform, destroy_token_order
from manuscript_lab.control_calibration import _document_metrics, _fit_model, _models
from manuscript_lab.control_corpus import TextSample, control_samples
from manuscript_lab.feature_panel import extract_sequence_features
from manuscript_lab.ledger import git_provenance
from manuscript_lab.provenance import repository_root, sha256_file


def _feature_matrices(
    samples: list[TextSample], families: list[str], *, seed: int
) -> tuple[dict[str, np.ndarray], list[str]]:
    matrices: dict[str, np.ndarray] = {}
    names: list[str] | None = None
    for family in families:
        rows = [
            extract_sequence_features(
                apply_transform(sample.tokens, family, seed=seed, sample_id=sample.sample_id)
            )
            for sample in samples
        ]
        current = sorted(rows[0])
        if names is None:
            names = current
        elif current != names:
            raise AssertionError("Feature panel changed across transform families")
        matrices[family] = np.asarray([[row[name] for name in names] for row in rows])
    assert names is not None
    return matrices, names


def _folds(labels: np.ndarray, groups: np.ndarray, *, count: int, seed: int) -> list[Any]:
    placeholder = np.zeros((len(labels), 1))
    return list(
        StratifiedGroupKFold(n_splits=count, shuffle=True, random_state=seed).split(
            placeholder, labels, groups
        )
    )


def _ensemble_predict(
    train_x: np.ndarray,
    train_y: np.ndarray,
    train_groups: np.ndarray,
    test_x: np.ndarray,
    *,
    seed: int,
    workers: int,
    trees: int,
) -> np.ndarray:
    predictions = []
    for model in _models(seed, workers=workers, trees=trees):
        _fit_model(model, train_x, train_y, train_groups)
        predictions.append(model.predict_proba(test_x)[:, 1])
    return np.mean(predictions, axis=0)


def transfer_scores(
    matrices: dict[str, np.ndarray],
    labels: np.ndarray,
    groups: np.ndarray,
    folds: list[Any],
    *,
    train_families: list[str],
    test_family: str,
    seed: int,
    workers: int,
    trees: int,
) -> tuple[dict[str, float], np.ndarray]:
    """Fit on selected families and score an unseen family on unseen documents."""
    scores = np.zeros(len(labels), dtype=float)
    for fold_number, (train, test) in enumerate(folds):
        train_x = np.concatenate([matrices[family][train] for family in train_families])
        train_y = np.tile(labels[train], len(train_families))
        train_groups = np.tile(groups[train], len(train_families))
        scores[test] = _ensemble_predict(
            train_x,
            train_y,
            train_groups,
            matrices[test_family][test],
            seed=seed + fold_number,
            workers=workers,
            trees=trees,
        )
    metrics, _grouped = _document_metrics(labels, scores, groups)
    return metrics, scores


def _feature_survival(
    matrices: dict[str, np.ndarray], names: list[str]
) -> dict[str, dict[str, Any]]:
    baseline = matrices["identity"]
    result = {}
    for family, matrix in matrices.items():
        if family == "identity":
            continue
        correlations = {}
        for index, name in enumerate(names):
            correlation = spearmanr(baseline[:, index], matrix[:, index]).statistic
            correlations[name] = None if not np.isfinite(correlation) else float(correlation)
        finite = [value for value in correlations.values() if value is not None]
        standardized = np.std(baseline, axis=0)
        standardized[standardized == 0] = 1.0
        shift = np.median(np.abs(matrix - baseline) / standardized, axis=0)
        result[family] = {
            "median_feature_spearman": float(np.median(finite)) if finite else None,
            "median_standardized_absolute_shift": float(np.median(shift)),
            "feature_spearman": correlations,
        }
    return result


def _order_destruction_challenge(
    samples: list[TextSample],
    matrices: dict[str, np.ndarray],
    labels: np.ndarray,
    groups: np.ndarray,
    folds: list[Any],
    families: list[str],
    names: list[str],
    *,
    seed: int,
    workers: int,
    trees: int,
) -> dict[str, Any]:
    shuffled_matrices = {}
    for family in families:
        rows = []
        for sample in samples:
            destroyed = destroy_token_order(sample.tokens, seed=seed, sample_id=sample.sample_id)
            transformed = apply_transform(
                destroyed, family, seed=seed, sample_id=f"{sample.sample_id}:destroyed"
            )
            features = extract_sequence_features(transformed)
            rows.append([features[name] for name in names])
        shuffled_matrices[family] = np.asarray(rows)

    original_scores = np.zeros((len(families), len(samples)))
    destroyed_scores = np.zeros((len(families), len(samples)))
    for fold_number, (train, test) in enumerate(folds):
        train_x = np.concatenate([matrices[family][train] for family in families])
        train_y = np.tile(labels[train], len(families))
        train_groups = np.tile(groups[train], len(families))
        for family_index, family in enumerate(families):
            original_scores[family_index, test] = _ensemble_predict(
                train_x,
                train_y,
                train_groups,
                matrices[family][test],
                seed=seed + fold_number,
                workers=workers,
                trees=trees,
            )
            destroyed_scores[family_index, test] = _ensemble_predict(
                train_x,
                train_y,
                train_groups,
                shuffled_matrices[family][test],
                seed=seed + fold_number,
                workers=workers,
                trees=trees,
            )
    meaningful = labels == 1
    per_sample_drop = np.mean(original_scores[:, meaningful], axis=0) - np.mean(
        destroyed_scores[:, meaningful], axis=0
    )
    return {
        "meaningful_sample_count": int(np.sum(meaningful)),
        "median_score_drop": float(np.median(per_sample_drop)),
        "mean_score_drop": float(np.mean(per_sample_drop)),
        "fraction_with_positive_drop": float(np.mean(per_sample_drop > 0)),
    }


def run_ladder(config_path: Path) -> dict[str, Any]:
    root = repository_root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    params = config["parameters"]
    seed = int(config["seed"])
    workers = int(params["workers"])
    trees = int(params["extra_trees_estimators"])
    families = list(params["transform_families"])
    if set(families) != set(TRANSFORMS):
        raise ValueError("Config must explicitly include the complete transform registry")
    archive = root / params["control_archive"]
    all_samples = control_samples(
        archive,
        chunk_tokens=int(params["chunk_tokens"]),
        max_chunks_per_document=int(params["max_chunks_per_document"]),
    )
    samples = [s for s in all_samples if s.family in {"meaningful", "human_gibberish"}]
    naibbe = [s for s in all_samples if s.family == "naibbe_payload"]
    labels = np.asarray([int(sample.family == "meaningful") for sample in samples])
    groups = np.asarray([sample.document_id for sample in samples])
    fold_indices = _folds(labels, groups, count=int(params["folds"]), seed=seed)
    matrices, feature_names = _feature_matrices(samples, families, seed=seed)
    print(
        f"transformation ladder: {len(samples)} chunks, {len(set(groups))} documents, "
        f"{len(families)} families",
        flush=True,
    )

    identity_transfer = {}
    leave_family_out = {}
    lofo_scores = {}
    for family in families:
        identity_transfer[family], _ = transfer_scores(
            matrices,
            labels,
            groups,
            fold_indices,
            train_families=["identity"],
            test_family=family,
            seed=seed,
            workers=workers,
            trees=trees,
        )
        train_families = [candidate for candidate in families if candidate != family]
        leave_family_out[family], lofo_scores[family] = transfer_scores(
            matrices,
            labels,
            groups,
            fold_indices,
            train_families=train_families,
            test_family=family,
            seed=seed + 100,
            workers=workers,
            trees=trees,
        )
        print(f"transformation ladder: completed held-out family {family}", flush=True)

    observed = float(
        np.mean([metrics["document_balanced_accuracy"] for metrics in leave_family_out.values()])
    )
    rng = random.Random(seed + 200)
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
        family_values = []
        for family in families:
            metrics, _ = transfer_scores(
                matrices,
                permuted,
                groups,
                fold_indices,
                train_families=[candidate for candidate in families if candidate != family],
                test_family=family,
                seed=seed + 10_000 + iteration,
                workers=workers,
                trees=trees,
            )
            family_values.append(metrics["document_balanced_accuracy"])
        permutation_values.append(float(np.mean(family_values)))
        if (iteration + 1) % 4 == 0:
            print(
                f"transformation ladder: completed {iteration + 1}/"
                f"{params['permutation_iterations']} permutations",
                flush=True,
            )

    train_x = np.concatenate([matrices[family] for family in families])
    train_y = np.tile(labels, len(families))
    train_groups = np.tile(groups, len(families))
    naibbe_rows = [extract_sequence_features(sample.tokens) for sample in naibbe]
    naibbe_x = np.asarray([[row[name] for name in feature_names] for row in naibbe_rows])
    naibbe_scores = _ensemble_predict(
        train_x,
        train_y,
        train_groups,
        naibbe_x,
        seed=seed,
        workers=workers,
        trees=trees,
    )
    order_challenge = _order_destruction_challenge(
        samples,
        matrices,
        labels,
        groups,
        fold_indices,
        families,
        feature_names,
        seed=seed,
        workers=workers,
        trees=trees,
    )

    accuracies = [value["document_balanced_accuracy"] for value in leave_family_out.values()]
    gates = config["metrics"]["interpretation_gates"]
    checks = {
        "median_heldout_family_accuracy": float(np.median(accuracies))
        >= float(gates["minimum_median_heldout_family_accuracy"]),
        "worst_heldout_family_accuracy": min(accuracies)
        >= float(gates["minimum_worst_heldout_family_accuracy"]),
        "naibbe_transfer": float(np.median(naibbe_scores)) >= float(gates["minimum_naibbe_median"]),
        "order_destruction_sensitivity": order_challenge["median_score_drop"]
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
        "feature_panel": {"version": "surface-sequence-panel-v2", "features": feature_names},
        "transforms": {
            "families": families,
            "parameters": config["transforms"],
            "property": "Every transform is seeded and applied identically to both labels.",
        },
        "identity_only_transfer": identity_transfer,
        "leave_family_out_transfer": leave_family_out,
        "feature_survival": _feature_survival(matrices, feature_names),
        "naibbe_external_positive_control": {
            "sample_count": len(naibbe),
            "median_meaningful_similarity": float(np.median(naibbe_scores)),
            "interquartile_range": [
                float(np.quantile(naibbe_scores, 0.25)),
                float(np.quantile(naibbe_scores, 0.75)),
            ],
        },
        "order_destruction_challenge": order_challenge,
        "permutation": {
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
                "independent replication before a separately preregistered target comparison"
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
            "seed": seed,
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
        (repository_root() / "schemas" / "transformation-ladder-result.schema.json").read_bytes()
    )
    Draft202012Validator(schema).validate(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Immutable output already exists: {args.output}")
    result = run_ladder(args.config.resolve())
    validate_result(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(
        orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    )


if __name__ == "__main__":
    main()
