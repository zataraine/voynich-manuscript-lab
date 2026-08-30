"""Leakage-safe calibration of surface statistics against known control texts.

The returned classifier values are similarity scores under this deliberately
limited control panel.  They are not probabilities that a manuscript has meaning.
"""

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
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from manuscript_lab.control_corpus import TextSample, control_samples
from manuscript_lab.feature_panel import extract_features
from manuscript_lab.ledger import git_provenance
from manuscript_lab.mechanism_test import load_ivtff_pages
from manuscript_lab.provenance import repository_root, sha256_file


def _matrix(samples: list[TextSample]) -> tuple[np.ndarray, list[str]]:
    rows = [extract_features(sample.tokens) for sample in samples]
    names = sorted(rows[0])
    return np.asarray([[row[name] for name in names] for row in rows]), names


def _models(seed: int, *, workers: int, trees: int = 400) -> list[Any]:
    return [
        make_pipeline(
            StandardScaler(),
            LogisticRegression(C=1.0, class_weight="balanced", max_iter=4000, random_state=seed),
        ),
        ExtraTreesClassifier(
            n_estimators=trees,
            min_samples_leaf=3,
            max_features="sqrt",
            class_weight="balanced",
            n_jobs=workers,
            random_state=seed,
        ),
    ]


def _sample_weights(groups: np.ndarray) -> np.ndarray:
    """Give every source document equal total weight regardless of chunk count."""
    counts = Counter(groups)
    return np.asarray([1.0 / counts[group] for group in groups], dtype=float)


def _fit_model(model: Any, matrix: np.ndarray, labels: np.ndarray, groups: np.ndarray) -> None:
    weights = _sample_weights(groups)
    if hasattr(model, "named_steps"):
        model.fit(matrix, labels, logisticregression__sample_weight=weights)
    else:
        model.fit(matrix, labels, sample_weight=weights)


def _oof_scores(
    matrix: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
    *,
    folds: int,
    seed: int,
    workers: int,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed)
    predictions = np.zeros(len(labels), dtype=float)
    audit: list[dict[str, Any]] = []
    for fold, (train, test) in enumerate(splitter.split(matrix, labels, groups)):
        if set(groups[train]) & set(groups[test]):
            raise AssertionError("Document leakage across a calibration fold")
        fold_scores = []
        for model in _models(seed + fold, workers=workers):
            _fit_model(model, matrix[train], labels[train], groups[train])
            fold_scores.append(model.predict_proba(matrix[test])[:, 1])
        predictions[test] = np.mean(fold_scores, axis=0)
        audit.append(
            {
                "fold": fold,
                "train_documents": len(set(groups[train])),
                "test_documents": len(set(groups[test])),
                "overlap_documents": 0,
            }
        )
    return predictions, audit


def _document_metrics(
    labels: np.ndarray, scores: np.ndarray, groups: np.ndarray
) -> tuple[dict[str, float], list[tuple[int, float]]]:
    grouped: list[tuple[int, float]] = []
    for group in sorted(set(groups)):
        where = groups == group
        group_labels = set(labels[where])
        if len(group_labels) != 1:
            raise ValueError("One source document has multiple calibration labels")
        grouped.append((int(labels[where][0]), float(np.mean(scores[where]))))
    y = np.asarray([row[0] for row in grouped])
    p = np.asarray([row[1] for row in grouped])
    return {
        "document_roc_auc": float(roc_auc_score(y, p)),
        "document_balanced_accuracy": float(balanced_accuracy_score(y, p >= 0.5)),
        "document_brier": float(brier_score_loss(y, p)),
    }, grouped


def _bootstrap_interval(
    grouped: list[tuple[int, float]], *, iterations: int, seed: int
) -> dict[str, list[float]]:
    rng = random.Random(seed)
    by_class = {label: [score for actual, score in grouped if actual == label] for label in (0, 1)}
    values = {"document_roc_auc": [], "document_balanced_accuracy": [], "document_brier": []}
    for _ in range(iterations):
        sample = [
            (label, rng.choice(by_class[label]))
            for label in (0, 1)
            for _index in range(len(by_class[label]))
        ]
        y = np.asarray([row[0] for row in sample])
        p = np.asarray([row[1] for row in sample])
        values["document_roc_auc"].append(float(roc_auc_score(y, p)))
        values["document_balanced_accuracy"].append(float(balanced_accuracy_score(y, p >= 0.5)))
        values["document_brier"].append(float(brier_score_loss(y, p)))
    return {
        name: [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))]
        for name, samples in values.items()
    }


def _target_samples(path: Path, *, witness: str, chunk_tokens: int) -> list[TextSample]:
    pages = load_ivtff_pages(path, currier={"A", "B"}, paragraph_only=True)
    source_hash = sha256_file(path)
    samples = []
    for page in pages:
        if len(page.groups) < chunk_tokens:
            continue
        start = (len(page.groups) - chunk_tokens) // 2
        samples.append(
            TextSample(
                sample_id=f"{witness}:{page.page_id}",
                document_id=page.page_id,
                family="voynich_target",
                subgroup=page.currier or "unknown",
                tokens=page.groups[start : start + chunk_tokens],
                source_ref=path.as_posix(),
                source_sha256=source_hash,
            )
        )
    return samples


def _fit_predict(
    train_x: np.ndarray,
    train_y: np.ndarray,
    train_groups: np.ndarray,
    target_x: np.ndarray,
    *,
    seed: int,
    workers: int,
) -> np.ndarray:
    scores = []
    for model in _models(seed, workers=workers):
        _fit_model(model, train_x, train_y, train_groups)
        scores.append(model.predict_proba(target_x)[:, 1])
    return np.mean(scores, axis=0)


def _summarize_scores(samples: list[TextSample], scores: np.ndarray) -> dict[str, Any]:
    pairs = sorted(zip(samples, scores, strict=True), key=lambda pair: pair[0].sample_id)
    by_subgroup: dict[str, list[float]] = {}
    for sample, score in pairs:
        by_subgroup.setdefault(sample.subgroup, []).append(float(score))
    return {
        "sample_count": len(samples),
        "median_meaningful_similarity": float(np.median(scores)),
        "interquartile_range": [float(np.quantile(scores, 0.25)), float(np.quantile(scores, 0.75))],
        "subgroups": {
            name: {"count": len(values), "median": float(np.median(values))}
            for name, values in sorted(by_subgroup.items())
        },
        "samples": [
            {
                "sample_id": sample.sample_id,
                "document_id": sample.document_id,
                "subgroup": sample.subgroup,
                "meaningful_similarity": float(score),
            }
            for sample, score in pairs
        ],
    }


def run_calibration(config_path: Path) -> dict[str, Any]:
    root = repository_root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    params = config["parameters"]
    seed = int(config["seed"])
    workers = int(params.get("workers", 1))
    archive = root / params["control_archive"]
    all_controls = control_samples(
        archive,
        chunk_tokens=int(params["chunk_tokens"]),
        max_chunks_per_document=int(params["max_chunks_per_document"]),
    )
    training = [s for s in all_controls if s.family in {"meaningful", "human_gibberish"}]
    positive = [s for s in all_controls if s.family == "naibbe_payload"]
    matrix, feature_names = _matrix(training)
    labels = np.asarray([int(sample.family == "meaningful") for sample in training])
    groups = np.asarray([sample.document_id for sample in training])
    print(
        f"control calibration: {len(training)} chunks from {len(set(groups))} documents; "
        f"{params['folds']} folds",
        flush=True,
    )
    oof, fold_audit = _oof_scores(
        matrix,
        labels,
        groups,
        folds=int(params["folds"]),
        seed=seed,
        workers=workers,
    )
    metrics, grouped = _document_metrics(labels, oof, groups)
    bootstrap = _bootstrap_interval(
        grouped, iterations=int(params["bootstrap_iterations"]), seed=seed + 1
    )

    observed = metrics["document_balanced_accuracy"]
    rng = random.Random(seed + 2)
    document_labels = {
        group: int(labels[np.flatnonzero(groups == group)[0]]) for group in sorted(set(groups))
    }
    permutation_values = []
    original = list(document_labels.values())
    for index in range(int(params["permutation_iterations"])):
        shuffled = original.copy()
        rng.shuffle(shuffled)
        mapping = dict(zip(document_labels, shuffled, strict=True))
        permuted = np.asarray([mapping[group] for group in groups])
        perm_oof, _ = _oof_scores(
            matrix,
            permuted,
            groups,
            folds=int(params["folds"]),
            seed=seed + 1000 + index,
            workers=workers,
        )
        perm_metrics, _ = _document_metrics(permuted, perm_oof, groups)
        permutation_values.append(perm_metrics["document_balanced_accuracy"])
        if (index + 1) % 8 == 0 or index + 1 == int(params["permutation_iterations"]):
            print(
                f"control calibration: completed {index + 1}/"
                f"{params['permutation_iterations']} label permutations",
                flush=True,
            )

    positive_matrix, positive_features = _matrix(positive)
    if positive_features != feature_names:
        raise AssertionError("Feature panel changed between calibration and positive control")
    positive_scores = _fit_predict(
        matrix, labels, groups, positive_matrix, seed=seed, workers=workers
    )
    positive_summary = _summarize_scores(positive, positive_scores)

    targets: dict[str, Any] = {}
    target_hashes = {}
    common_page_scores: dict[str, dict[str, float]] = {}
    for witness, relative in params["voynich_witnesses"].items():
        path = root / relative
        samples = _target_samples(path, witness=witness, chunk_tokens=int(params["chunk_tokens"]))
        target_matrix, target_features = _matrix(samples)
        if target_features != feature_names:
            raise AssertionError("Feature panel changed for target corpus")
        scores = _fit_predict(matrix, labels, groups, target_matrix, seed=seed, workers=workers)
        targets[witness] = _summarize_scores(samples, scores)
        common_page_scores[witness] = {
            sample.document_id: float(score) for sample, score in zip(samples, scores, strict=True)
        }
        target_hashes[relative] = sha256_file(path)

    common_pages = set.intersection(*(set(values) for values in common_page_scores.values()))
    ranges = [
        max(common_page_scores[witness][page] for witness in common_page_scores)
        - min(common_page_scores[witness][page] for witness in common_page_scores)
        for page in common_pages
    ]
    gates = config["metrics"]["interpretation_gates"]
    gate_status = {
        "calibration_balanced_accuracy": observed >= float(gates["minimum_balanced_accuracy"]),
        "naibbe_positive_control": positive_summary["median_meaningful_similarity"]
        >= float(gates["minimum_naibbe_median"]),
        "witness_stability": bool(ranges)
        and float(np.median(ranges)) <= float(gates["maximum_witness_median_range"]),
    }
    interpretation_allowed = all(gate_status.values())
    manifest = root / config["source_manifest"]
    return {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "hypothesis_id": config["hypothesis_id"],
        "run_finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "feature_panel": {"version": "surface-panel-v1", "features": feature_names},
        "corpus_audit": {
            "source_documents": dict(
                Counter(
                    sample.family for sample in all_controls if sample.sample_id.endswith(":000")
                )
            ),
            "chunks": dict(Counter(sample.family for sample in all_controls)),
            "chunk_tokens": int(params["chunk_tokens"]),
            "normalization": config["normalization"],
        },
        "cross_validation": {
            "metrics": metrics,
            "bootstrap_95_percent_intervals": bootstrap,
            "folds": fold_audit,
            "permutation": {
                "iterations": len(permutation_values),
                "balanced_accuracy_mean": float(np.mean(permutation_values)),
                "one_sided_p": (1 + sum(value >= observed for value in permutation_values))
                / (len(permutation_values) + 1),
            },
        },
        "naibbe_positive_control": positive_summary,
        "voynich_targets": targets,
        "witness_sensitivity": {
            "common_page_count": len(common_pages),
            "median_across_witness_score_range": float(np.median(ranges)) if ranges else None,
            "maximum_across_witness_score_range": max(ranges) if ranges else None,
        },
        "interpretation_gate": {
            "checks": gate_status,
            "passed": interpretation_allowed,
            "permitted_claim": (
                "surface similarity under this control panel"
                if interpretation_allowed
                else "none; calibration or sensitivity gate failed"
            ),
            "posterior_probability": None,
            "warning": (
                "Classifier scores are not probabilities of meaning, language, cipher, or hoax."
            ),
        },
        "provenance": {
            "control_archive": params["control_archive"],
            "control_archive_sha256": sha256_file(archive),
            "source_manifest": config["source_manifest"],
            "source_manifest_sha256": sha256_file(manifest),
            "target_sha256": target_hashes,
            "config_path": config_path.relative_to(root).as_posix(),
            "config_sha256": sha256_file(config_path),
            "seed": seed,
            "workers": workers,
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
    """Validate the durable campaign result before its immutable write."""
    schema = orjson.loads(
        (repository_root() / "schemas" / "control-calibration-result.schema.json").read_bytes()
    )
    Draft202012Validator(schema).validate(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Immutable output already exists: {args.output}")
    result = run_calibration(args.config.resolve())
    validate_result(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(
        orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    )


if __name__ == "__main__":
    main()
