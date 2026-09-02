"""E-014 control-only calibration of a frozen higher-order sequence panel."""

from __future__ import annotations

import hashlib
import math
import multiprocessing
import platform
import random
import subprocess
import sys
import time
import zlib
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import orjson
import yaml
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, brier_score_loss, roc_auc_score

from manuscript_lab.external_signature_calibration import Case, build_cases
from manuscript_lab.ledger import git_provenance
from manuscript_lab.provenance import repository_root, sha256_file


def _stable_seed(seed: int, *parts: str) -> int:
    digest = hashlib.sha256(":".join((str(seed), *parts)).encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _safe_cv(values: list[float] | np.ndarray) -> float:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return 0.0
    mean = float(np.mean(array))
    return float(np.std(array) / mean) if mean > 0 else 0.0


def _linear_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    if len(x) < 2 or float(np.var(x)) == 0:
        return 0.0, 0.0
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    denominator = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum((y - predicted) ** 2)) / denominator if denominator else 0.0
    return float(slope), float(r2)


def _vocabulary_growth(tokens: tuple[str, ...]) -> tuple[float, float, float]:
    count = len(tokens)
    sizes = sorted({max(10, min(count, round(count * fraction / 8))) for fraction in range(1, 9)})
    types = [len(set(tokens[:size])) for size in sizes]
    x = np.log(np.asarray(sizes, dtype=float))
    y = np.log(np.asarray(types, dtype=float))
    exponent, r2 = _linear_fit(x, y)
    midpoint = len(x) // 2
    early, _ = _linear_fit(x[: midpoint + 1], y[: midpoint + 1])
    late, _ = _linear_fit(x[midpoint:], y[midpoint:])
    return exponent, r2, early - late


def _autocorrelation(values: np.ndarray, lag: int) -> float:
    if lag <= 0 or len(values) <= lag:
        return 0.0
    left = values[:-lag]
    right = values[lag:]
    if float(np.var(left)) == 0 or float(np.var(right)) == 0:
        return 0.0
    value = float(np.corrcoef(left, right)[0, 1])
    return value if math.isfinite(value) else 0.0


def _low_frequency_power(values: np.ndarray) -> float:
    centered = values - values.mean()
    power = np.abs(np.fft.rfft(centered))[1:] ** 2
    total = float(power.sum())
    if total == 0 or power.size == 0:
        return 0.0
    low_count = max(1, math.ceil(power.size / 4))
    return float(power[:low_count].sum() / total)


def _length_block_features(lengths: np.ndarray, block_size: int) -> tuple[float, float]:
    blocks = [lengths[index : index + block_size] for index in range(0, len(lengths), block_size)]
    means = [float(np.mean(block)) for block in blocks if len(block)]
    deviations = [float(np.std(block)) for block in blocks if len(block)]
    return _safe_cv(means), _safe_cv(deviations)


def _recurrence_features(tokens: tuple[str, ...]) -> tuple[float, float]:
    positions: dict[str, list[int]] = defaultdict(list)
    for index, token in enumerate(tokens):
        positions[token].append(index)
    burstiness: list[float] = []
    cvs: list[float] = []
    for indexes in positions.values():
        if len(indexes) < 3:
            continue
        gaps = np.diff(np.asarray(indexes, dtype=float))
        mean = float(np.mean(gaps))
        deviation = float(np.std(gaps))
        if mean <= 0:
            continue
        cvs.append(deviation / mean)
        denominator = deviation + mean
        burstiness.append((deviation - mean) / denominator if denominator else 0.0)
    return (
        float(np.mean(burstiness)) if burstiness else 0.0,
        float(np.mean(cvs)) if cvs else 0.0,
    )


def _frequent_token_fano(tokens: tuple[str, ...], block_size: int, limit: int) -> float:
    counts = Counter(tokens)
    selected = [token for token, count in counts.most_common() if count >= 3][:limit]
    if not selected:
        return 0.0
    blocks = [tokens[index : index + block_size] for index in range(0, len(tokens), block_size)]
    values = []
    for token in selected:
        block_counts = np.asarray([block.count(token) for block in blocks], dtype=float)
        mean = float(np.mean(block_counts))
        values.append(float(np.var(block_counts)) / mean if mean > 0 else 0.0)
    return float(np.mean(values))


def _token_block_information(tokens: tuple[str, ...], block_size: int) -> float:
    joint: Counter[tuple[int, str]] = Counter()
    token_counts = Counter(tokens)
    block_counts: Counter[int] = Counter()
    for index, token in enumerate(tokens):
        block = index // block_size
        joint[(block, token)] += 1
        block_counts[block] += 1
    total = len(tokens)
    return float(
        sum(
            count / total * math.log2(count * total / (block_counts[block] * token_counts[token]))
            for (block, token), count in joint.items()
        )
    )


def _canonical_token_bytes(tokens: tuple[str, ...]) -> bytes:
    mapping: dict[str, int] = {}
    values = []
    for token in tokens:
        if token not in mapping:
            mapping[token] = len(mapping)
        values.append(mapping[token])
    return np.asarray(values, dtype="<u4").tobytes()


def _length_bytes(tokens: tuple[str, ...]) -> bytes:
    return np.asarray([len(token) for token in tokens], dtype="<u4").tobytes()


def _compression_shuffle_gain(
    tokens: tuple[str, ...], *, seed: int, replicates: int, mode: str
) -> float:
    encode = _canonical_token_bytes if mode == "token" else _length_bytes
    observed_raw = encode(tokens)
    observed = len(zlib.compress(observed_raw, 9)) / max(1, len(observed_raw))
    rng = random.Random(seed)
    shuffled_ratios = []
    working = list(tokens)
    for _ in range(replicates):
        rng.shuffle(working)
        raw = encode(tuple(working))
        shuffled_ratios.append(len(zlib.compress(raw, 9)) / max(1, len(raw)))
    return float(np.mean(shuffled_ratios) - observed)


def _weighted_assortativity(graph: nx.Graph) -> float:
    edges = list(graph.edges(data="weight", default=1.0))
    if not edges:
        return 0.0
    degrees = dict(graph.degree())
    total_weight = sum(float(weight) for _left, _right, weight in edges)
    mean = sum(
        float(weight) * (degrees[left] + degrees[right]) for left, right, weight in edges
    ) / (2 * total_weight)
    numerator = 2 * sum(
        float(weight) * (degrees[left] - mean) * (degrees[right] - mean)
        for left, right, weight in edges
    )
    denominator = sum(
        float(weight) * ((degrees[left] - mean) ** 2 + (degrees[right] - mean) ** 2)
        for left, right, weight in edges
    )
    return float(numerator / denominator) if denominator else 0.0


def _cooccurrence_features(tokens: tuple[str, ...]) -> tuple[float, float, float]:
    graph = nx.Graph()
    for left, right in pairwise(tokens):
        if left == right:
            graph.add_node(left)
            continue
        if graph.has_edge(left, right):
            graph[left][right]["weight"] += 1.0
        else:
            graph.add_edge(left, right, weight=1.0)
    if graph.number_of_edges() == 0:
        return 0.0, 0.0, 0.0
    assortativity = _weighted_assortativity(graph)
    clustering = float(nx.average_clustering(graph, weight="weight"))
    selectivity = []
    for node, degree in graph.degree():
        if degree:
            strength = sum(float(data["weight"]) for *_edge, data in graph.edges(node, data=True))
            selectivity.append(strength / degree)
    return assortativity, clustering, _safe_cv(selectivity)


def extract_higher_order_features(
    tokens: tuple[str, ...], *, params: dict[str, Any], seed: int
) -> dict[str, float]:
    """Compute the frozen 21-feature panel in the config-declared order."""
    if len(tokens) < 70:
        raise ValueError("E-014 features require at least 70 groups")
    lengths = np.asarray([len(token) for token in tokens], dtype=float)
    heaps_exponent, heaps_r2, heaps_delta = _vocabulary_growth(tokens)
    length_mean_cv, length_std_cv = _length_block_features(
        lengths, int(params["length_block_size"])
    )
    burstiness, recurrence_cv = _recurrence_features(tokens)
    assortativity, clustering, selectivity_cv = _cooccurrence_features(tokens)
    computed = {
        "heaps_exponent": heaps_exponent,
        "heaps_r2": heaps_r2,
        "heaps_early_late_delta": heaps_delta,
        **{
            f"length_autocorrelation_lag_{lag}": _autocorrelation(lengths, int(lag))
            for lag in params["length_lags"]
        },
        "length_low_frequency_power_fraction": _low_frequency_power(lengths),
        "length_block_mean_cv": length_mean_cv,
        "length_block_std_cv": length_std_cv,
        "recurrence_gap_burstiness": burstiness,
        "recurrence_gap_cv": recurrence_cv,
        "frequent_token_block_fano": _frequent_token_fano(
            tokens,
            int(params["length_block_size"]),
            int(params["frequent_token_limit"]),
        ),
        **{
            f"token_block_information_{size}": _token_block_information(tokens, int(size))
            for size in params["information_block_sizes"]
        },
        "token_pattern_compression_shuffle_gain": _compression_shuffle_gain(
            tokens,
            seed=_stable_seed(seed, "token-compression"),
            replicates=int(params["compression_shuffle_replicates"]),
            mode="token",
        ),
        "length_pattern_compression_shuffle_gain": _compression_shuffle_gain(
            tokens,
            seed=_stable_seed(seed, "length-compression"),
            replicates=int(params["compression_shuffle_replicates"]),
            mode="length",
        ),
        "cooccurrence_degree_assortativity": assortativity,
        "cooccurrence_average_clustering": clustering,
        "cooccurrence_selectivity_cv": selectivity_cv,
    }
    feature_order = list(params["features"])
    if set(computed) != set(feature_order):
        missing = set(feature_order) - set(computed)
        extra = set(computed) - set(feature_order)
        raise ValueError(f"frozen feature mismatch: missing={missing}, extra={extra}")
    result = {feature: float(computed[feature]) for feature in feature_order}
    if not all(math.isfinite(value) for value in result.values()):
        raise ValueError("non-finite E-014 feature")
    return result


def _length_preserving_token_rename(tokens: tuple[str, ...]) -> tuple[str, ...]:
    mapping = {
        token: chr(0x1000 + index) * len(token) for index, token in enumerate(sorted(set(tokens)))
    }
    return tuple(mapping[token] for token in tokens)


def extract_case_features(case: Case, *, params: dict[str, Any], seed: int) -> dict[str, Any]:
    case_seed = _stable_seed(seed, case.case_id, "higher-order")
    features = extract_higher_order_features(case.tokens, params=params, seed=case_seed)
    renamed = _length_preserving_token_rename(case.tokens)
    renamed_features = extract_higher_order_features(renamed, params=params, seed=case_seed)
    rename_delta = max(
        abs(features[feature] - renamed_features[feature]) for feature in params["features"]
    )
    return {
        **{key: value for key, value in asdict(case).items() if key != "tokens"},
        "selected_group_count": len(case.tokens),
        "selected_sha256": hashlib.sha256("\u241f".join(case.tokens).encode()).hexdigest(),
        "features": features,
        "token_rename_max_delta": rename_delta,
    }


def _matrix(rows: list[dict[str, Any]], feature_order: list[str]) -> np.ndarray:
    return np.asarray([[row["features"][feature] for feature in feature_order] for row in rows])


def _fit_model(
    rows: list[dict[str, Any]],
    labels: np.ndarray,
    *,
    feature_order: list[str],
    c: float,
    seed: int,
    scale_tolerance: float,
) -> tuple[np.ndarray, np.ndarray, LogisticRegression]:
    matrix = _matrix(rows, feature_order)
    median = np.median(matrix, axis=0)
    q25, q75 = np.percentile(matrix, [25, 75], axis=0)
    scale = q75 - q25
    scale[scale <= scale_tolerance] = 1.0
    model = LogisticRegression(
        C=c,
        class_weight="balanced",
        max_iter=2000,
        random_state=seed,
        solver="liblinear",
    )
    model.fit((matrix - median) / scale, labels)
    return median, scale, model


def _predict(
    rows: list[dict[str, Any]],
    median: np.ndarray,
    scale: np.ndarray,
    model: LogisticRegression,
    feature_order: list[str],
) -> np.ndarray:
    return model.predict_proba((_matrix(rows, feature_order) - median) / scale)[:, 1]


def _cross_family_predictions(
    rows: list[dict[str, Any]],
    family_labels: dict[str, int],
    *,
    feature_order: list[str],
    folds: int,
    c: float,
    seed: int,
    scale_tolerance: float,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    predictions: list[float] = []
    labels: list[int] = []
    families: list[str] = []
    for fold in range(folds):
        for family in sorted(family_labels):
            train = [row for row in rows if int(row["fold"]) != fold and row["family"] != family]
            test = [row for row in rows if int(row["fold"]) == fold and row["family"] == family]
            if not test:
                continue
            train_labels = np.asarray([family_labels[row["family"]] for row in train])
            median, scale, model = _fit_model(
                train,
                train_labels,
                feature_order=feature_order,
                c=c,
                seed=seed + fold,
                scale_tolerance=scale_tolerance,
            )
            predictions.extend(_predict(test, median, scale, model, feature_order).tolist())
            labels.extend([family_labels[family]] * len(test))
            families.extend([family] * len(test))
    return np.asarray(predictions), np.asarray(labels), families


def _classification_summary(
    scores: np.ndarray, labels: np.ndarray, families: list[str], threshold: float
) -> dict[str, Any]:
    predicted = (scores >= threshold).astype(int)
    recalls = {}
    for family in sorted(set(families)):
        indexes = np.asarray([value == family for value in families])
        recalls[family] = float(np.mean(predicted[indexes] == labels[indexes]))
    return {
        "cases": len(labels),
        "balanced_accuracy": float(balanced_accuracy_score(labels, predicted)),
        "roc_auc": float(roc_auc_score(labels, scores)),
        "brier": float(brier_score_loss(labels, scores)),
        "family_recall": recalls,
        "worst_family_recall": min(recalls.values()),
    }


def evaluate_controls(
    config: dict[str, Any], rows: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    params = config["parameters"]
    feature_order = list(params["features"])
    payload = tuple(params["payload_families"])
    no_payload = tuple(params["no_payload_families"])
    family_labels = {family: int(family in payload) for family in (*payload, *no_payload)}
    development = [row for row in rows if row["cohort"] == "development"]
    independent = [row for row in rows if row["cohort"] == "independent"]
    external = [row for row in rows if row["cohort"] == "external"]
    threshold = float(params["probability_threshold"])
    c = float(params["logistic_c"])
    seed = int(config["seed"])
    folds = int(params["development_folds"])
    tolerance = float(params["robust_iqr_constant_tolerance"])

    dev_scores, dev_labels, dev_families = _cross_family_predictions(
        development,
        family_labels,
        feature_order=feature_order,
        folds=folds,
        c=c,
        seed=seed,
        scale_tolerance=tolerance,
    )
    development_summary = _classification_summary(dev_scores, dev_labels, dev_families, threshold)
    rng = random.Random(_stable_seed(seed, "family-label-permutation"))
    families = sorted(family_labels)
    label_values = [family_labels[family] for family in families]
    null_values = []
    for _ in range(int(params["permutation_replicates"])):
        permuted = label_values.copy()
        rng.shuffle(permuted)
        mapping = dict(zip(families, permuted, strict=True))
        scores, labels, names = _cross_family_predictions(
            development,
            mapping,
            feature_order=feature_order,
            folds=folds,
            c=c,
            seed=seed,
            scale_tolerance=tolerance,
        )
        null_values.append(
            _classification_summary(scores, labels, names, threshold)["balanced_accuracy"]
        )
    permutation_p = (
        1 + sum(value >= development_summary["balanced_accuracy"] for value in null_values)
    ) / (len(null_values) + 1)

    training_labels = np.asarray([row["label"] for row in development])
    raw_iqr = np.subtract(*np.percentile(_matrix(development, feature_order), [75, 25], axis=0))
    median, scale, model = _fit_model(
        development,
        training_labels,
        feature_order=feature_order,
        c=c,
        seed=seed,
        scale_tolerance=tolerance,
    )
    independent_scores = _predict(independent, median, scale, model, feature_order)
    independent_labels = np.asarray([row["label"] for row in independent])
    independent_families = [str(row["family"]) for row in independent]
    independent_summary = _classification_summary(
        independent_scores, independent_labels, independent_families, threshold
    )

    external_scores = _predict(external, median, scale, model, feature_order)
    external_records = [
        {
            "case_id": row["case_id"],
            "family": row["family"],
            "selected_group_count": row["selected_group_count"],
            "score": float(score),
        }
        for row, score in zip(external, external_scores, strict=True)
    ]
    by_family = {
        family: np.asarray([item["score"] for item in external_records if item["family"] == family])
        for family in ("external_meaningful", "external_human_gibberish", "external_naibbe")
    }
    human_length_diagnostics = {}
    for name, lower, upper in (("70_159", 70, 159), ("160_279", 160, 279), ("280", 280, 280)):
        selected = [
            item["score"]
            for item in external_records
            if item["family"] == "external_human_gibberish"
            and lower <= int(item["selected_group_count"]) <= upper
        ]
        human_length_diagnostics[name] = {
            "cases": len(selected),
            "specificity": float(np.mean(np.asarray(selected) < threshold)) if selected else None,
        }
    external_summary = {
        "meaningful_cases": len(by_family["external_meaningful"]),
        "meaningful_recall": float(np.mean(by_family["external_meaningful"] >= threshold)),
        "human_gibberish_cases": len(by_family["external_human_gibberish"]),
        "human_gibberish_specificity": float(
            np.mean(by_family["external_human_gibberish"] < threshold)
        ),
        "human_gibberish_length_diagnostics": human_length_diagnostics,
        "naibbe_cases": len(by_family["external_naibbe"]),
        "naibbe_recall": float(np.mean(by_family["external_naibbe"] >= threshold)),
        "naibbe_median_payload_score": float(np.median(by_family["external_naibbe"])),
        "records": external_records,
    }
    gate_config = config["metrics"]["interpretation_gates"]
    gates = {
        "development_balanced_accuracy": development_summary["balanced_accuracy"]
        >= float(gate_config["minimum_development_balanced_accuracy"]),
        "worst_development_family_recall": development_summary["worst_family_recall"]
        >= float(gate_config["minimum_worst_development_family_recall"]),
        "family_label_permutation": permutation_p
        <= float(gate_config["maximum_family_label_permutation_p"]),
        "independent_balanced_accuracy": independent_summary["balanced_accuracy"]
        >= float(gate_config["minimum_independent_balanced_accuracy"]),
        "worst_independent_family_recall": independent_summary["worst_family_recall"]
        >= float(gate_config["minimum_worst_independent_family_recall"]),
        "external_meaningful_recall": external_summary["meaningful_recall"]
        >= float(gate_config["minimum_external_meaningful_recall"]),
        "external_human_gibberish_specificity": external_summary["human_gibberish_specificity"]
        >= float(gate_config["minimum_external_human_gibberish_specificity"]),
        "naibbe_payload_recall": external_summary["naibbe_recall"]
        >= float(gate_config["minimum_naibbe_payload_recall"]),
        "naibbe_median_payload_score": external_summary["naibbe_median_payload_score"]
        >= float(gate_config["minimum_naibbe_median_payload_score"]),
    }
    evaluation = {
        "development": development_summary,
        "family_label_permutation_p": permutation_p,
        "family_label_permutation_null": null_values,
        "independent": independent_summary,
        "external": external_summary,
        "gates": gates,
    }
    model_record = {
        "feature_order": feature_order,
        "median": median.tolist(),
        "raw_iqr": raw_iqr.tolist(),
        "iqr": scale.tolist(),
        "robust_iqr_constant_tolerance": tolerance,
        "constant_features": [
            feature
            for feature, value in zip(feature_order, raw_iqr, strict=True)
            if value <= tolerance
        ],
        "coefficient": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
        "probability_threshold": threshold,
        "training_case_ids": [row["case_id"] for row in development],
    }
    return evaluation, model_record


def _preregistration_revision(root: Path, config_path: Path) -> str:
    result = subprocess.run(
        [
            "git",
            "log",
            "--diff-filter=A",
            "-1",
            "--format=%H",
            "--",
            str(config_path.relative_to(root)),
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write_immutable(path: Path, payload: bytes) -> None:
    if path.exists():
        raise FileExistsError(f"immutable E-014 output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def run_campaign(config_path: Path) -> dict[str, Any]:
    """Run E-014 without loading or scoring any manuscript transcription."""
    started = time.monotonic()
    root = repository_root()
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config.get("experiment_id") != "E-014-higher-order-external-calibration":
        raise ValueError("not the frozen E-014 config")
    if (
        sha256_file(root / config["predecessor"]["result"])
        != config["predecessor"]["result_sha256"]
    ):
        raise ValueError("frozen E-013R1 predecessor hash changed")
    source_specs = [
        (
            config["sources"]["development_manifest"],
            config["sources"]["development_manifest_sha256"],
        ),
        *[(item["path"], item["sha256"]) for item in config["sources"]["independent_manifests"]],
        (config["sources"]["external_manifest"], config["sources"]["external_manifest_sha256"]),
        (config["sources"]["external_archive"], config["sources"]["external_archive_sha256"]),
    ]
    for path, expected in source_specs:
        if sha256_file(root / path) != expected:
            raise ValueError(f"frozen E-014 source hash changed: {path}")
    provenance = git_provenance(root)
    if provenance["git_dirty"]:
        raise ValueError("E-014 calculation requires a clean committed worktree")

    cases, corpus_audit = build_cases(config)
    params = config["parameters"]
    workers = min(int(params["workers"]), len(cases))
    rows: list[dict[str, Any]] = []
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        futures = {
            executor.submit(
                extract_case_features, case, params=params, seed=int(config["seed"])
            ): case.case_id
            for case in cases
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            rows.append(future.result())
            if completed % 50 == 0 or completed == len(cases):
                print(f"E-014 features {completed}/{len(cases)}", flush=True)
    rows.sort(key=lambda row: row["case_id"])

    replay = [
        extract_case_features(case, params=params, seed=int(config["seed"]))
        for case in sorted(cases, key=lambda item: item.case_id)
    ]
    replay_exact = all(
        left["features"] == right["features"]
        and left["token_rename_max_delta"] == right["token_rename_max_delta"]
        for left, right in zip(rows, replay, strict=True)
    )
    evaluation, model_record = evaluate_controls(config, rows)
    rename_tolerance = float(config["metrics"]["construction_gates"]["maximum_token_rename_delta"])
    controls = {
        "manuscript_transcription_absent": all(
            not row["source_ref"].startswith("data/raw/transcriptions/") for row in rows
        ),
        "all_payload_roundtrips_exact": all(row["roundtrip"] for row in rows),
        "case_ids_unique": len({row["case_id"] for row in rows}) == len(rows),
        "development_and_independent_documents_disjoint": not (
            {row["source_sha256"] for row in rows if row["cohort"] == "development"}
            & {row["source_sha256"] for row in rows if row["cohort"] == "independent"}
        ),
        "feature_shape_and_order_exact": all(
            list(row["features"]) == list(params["features"]) for row in rows
        ),
        "finite_features": all(
            math.isfinite(value) for row in rows for value in row["features"].values()
        ),
        "deterministic_replay_exact": replay_exact,
        "length_preserving_token_rename_invariant": max(
            row["token_rename_max_delta"] for row in rows
        )
        <= rename_tolerance,
    }
    gates = {"construction_controls": all(controls.values()), **evaluation["gates"]}
    feature_path = root / config["artifacts"]["case_features"]
    model_path = root / config["artifacts"]["model"]
    result_path = root / config["artifacts"]["result"]
    _write_immutable(
        feature_path,
        b"".join(orjson.dumps(row, option=orjson.OPT_SORT_KEYS) + b"\n" for row in rows),
    )
    _write_immutable(
        model_path,
        orjson.dumps(model_record, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n",
    )
    result = {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "hypothesis_id": config["hypothesis_id"],
        "question_id": config["question_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "pass" if all(gates.values()) else "fail",
        "witness_robustness_preregistration_permitted": all(gates.values()),
        "target_scored": False,
        "corpus_audit": corpus_audit,
        "controls": controls,
        "maximum_token_rename_delta": max(row["token_rename_max_delta"] for row in rows),
        "evaluation": evaluation,
        "gates": gates,
        "runtime_seconds": time.monotonic() - started,
        "provenance": {
            **provenance,
            "preregistration_git_commit": _preregistration_revision(root, config_path),
            "config_sha256": sha256_file(config_path),
            "protocol_sha256": sha256_file(root / config["protocol"]),
            "case_features_sha256": sha256_file(feature_path),
            "model_sha256": sha256_file(model_path),
            "seed": int(config["seed"]),
            "workers": int(params["workers"]),
            "device": "CPU",
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "uv_lock_sha256": sha256_file(root / "uv.lock"),
        },
        "interpretation": (
            "External calibration of a fixed nonsemantic higher-order panel only; scores are "
            "not posterior probabilities of meaning, language, cipher, construction, or hoaxing."
        ),
    }
    _write_immutable(
        result_path,
        orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n",
    )
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/E-014-higher-order-external-calibration.yaml"),
    )
    args = parser.parse_args()
    result = run_campaign(args.config)
    print(
        orjson.dumps(
            {
                "status": result["status"],
                "witness_robustness_preregistration_permitted": result[
                    "witness_robustness_preregistration_permitted"
                ],
                "controls": result["controls"],
                "evaluation": {
                    "development": result["evaluation"]["development"],
                    "family_label_permutation_p": result["evaluation"][
                        "family_label_permutation_p"
                    ],
                    "independent": result["evaluation"]["independent"],
                    "external": {
                        key: value
                        for key, value in result["evaluation"]["external"].items()
                        if key != "records"
                    },
                },
                "gates": result["gates"],
                "runtime_seconds": result["runtime_seconds"],
            },
            option=orjson.OPT_INDENT_2,
        ).decode()
    )


if __name__ == "__main__":
    main()
