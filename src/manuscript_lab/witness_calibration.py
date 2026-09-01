"""E-011 cross-fitted robust calibration of E-010 witness measurements."""

from __future__ import annotations

import math
import subprocess
import sys
import time
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import orjson
import yaml

from manuscript_lab.ledger import git_provenance
from manuscript_lab.provenance import repository_root, sha256_file
from manuscript_lab.representation_robustness import FEATURES, _holm, _spearman


def contiguous_folds(size: int, count: int) -> tuple[np.ndarray, ...]:
    """Partition ordered positions into deterministic contiguous folds."""
    if count < 2 or size < count:
        raise ValueError("need at least two non-empty folds")
    return tuple(
        np.asarray(part, dtype=np.int64) for part in np.array_split(np.arange(size), count)
    )


def cross_fit(
    values: dict[str, np.ndarray], folds: tuple[np.ndarray, ...]
) -> tuple[dict[str, np.ndarray], dict[str, list[dict[str, float | int | bool]]]]:
    """Apply training-only median/IQR calibration to each held-out fold."""
    size = len(next(iter(values.values())))
    if any(len(item) != size for item in values.values()):
        raise ValueError("all views must contain the same ordered pages")
    calibrated = {name: np.full(size, np.nan, dtype=np.float64) for name in values}
    parameters: dict[str, list[dict[str, float | int | bool]]] = {name: [] for name in values}
    all_positions = np.arange(size)
    for fold_index, test in enumerate(folds):
        train = np.setdiff1d(all_positions, test, assume_unique=True)
        for name, series in values.items():
            median = float(np.median(series[train]))
            q75, q25 = np.percentile(series[train], [75, 25])
            iqr = float(q75 - q25)
            valid = math.isfinite(median) and math.isfinite(iqr) and iqr > 0
            parameters[name].append(
                {
                    "fold": fold_index,
                    "training_pages": len(train),
                    "heldout_pages": len(test),
                    "training_median": median,
                    "training_iqr": iqr,
                    "valid": valid,
                }
            )
            if valid:
                calibrated[name][test] = (series[test] - median) / iqr
    return calibrated, parameters


def synthetic_controls(config: dict[str, Any]) -> dict[str, Any]:
    """Run the frozen recoverable and page-identity-destroyed controls."""
    control = config["controls"]
    rng = np.random.default_rng(int(control["seed"]))
    pages = int(control["pages"])
    view_count = int(control["views"])
    latent = rng.standard_normal(pages)
    offsets = rng.uniform(-3.0, 3.0, view_count)
    scales = rng.uniform(0.5, 2.0, view_count)
    noise = float(control["noise_standard_deviation"])
    raw = {
        f"view-{index}": offsets[index] + scales[index] * latent + rng.normal(0.0, noise, pages)
        for index in range(view_count)
    }
    folds = contiguous_folds(pages, int(config["split"]["folds"]))
    recovered, recovered_parameters = cross_fit(raw, folds)
    pairs = tuple(combinations(recovered, 2))
    recovered_rhos = [_spearman(recovered[left], recovered[right]) for left, right in pairs]
    recovered_differences = [
        float(np.median(np.abs(recovered[left] - recovered[right]))) for left, right in pairs
    ]

    broken_raw = {"view-0": raw["view-0"]}
    for index in range(1, view_count):
        broken_raw[f"view-{index}"] = raw[f"view-{index}"][rng.permutation(pages)]
    broken, broken_parameters = cross_fit(broken_raw, folds)
    broken_rhos = [_spearman(broken[left], broken[right]) for left, right in pairs]
    metrics = {
        "recoverable_worst_pair_spearman": float(min(recovered_rhos)),
        "recoverable_maximum_median_absolute_difference": float(max(recovered_differences)),
        "broken_median_pair_spearman": float(np.median(broken_rhos)),
    }
    gates = {
        "recoverable_rank": metrics["recoverable_worst_pair_spearman"]
        >= float(control["recoverable_minimum_worst_spearman"]),
        "recoverable_agreement": metrics["recoverable_maximum_median_absolute_difference"]
        <= float(control["recoverable_maximum_median_normalized_difference"]),
        "broken_page_identity": metrics["broken_median_pair_spearman"]
        <= float(control["broken_maximum_median_pair_spearman"]),
        "all_calibration_iqrs": all(
            item["valid"]
            for parameter_set in (recovered_parameters, broken_parameters)
            for items in parameter_set.values()
            for item in items
        ),
    }
    return {"metrics": metrics, "gates": gates, "passed": all(gates.values())}


def load_e010_rows(
    path: Path, expected_views: tuple[str, ...]
) -> tuple[tuple[str, ...], dict[str, dict[str, np.ndarray]], list[dict[str, Any]]]:
    """Load the immutable E-010 page-view table and require a complete rectangle."""
    rows = [orjson.loads(line) for line in path.read_bytes().splitlines() if line]
    page_order: list[str] = []
    seen_pages: set[str] = set()
    values: dict[str, dict[str, dict[str, float]]] = {
        feature: {view: {} for view in expected_views} for feature in FEATURES
    }
    seen_cells: set[tuple[str, str]] = set()
    for row in rows:
        page = str(row["page"])
        view = str(row["view"])
        if view not in expected_views:
            raise ValueError(f"unexpected E-010 view {view}")
        cell = (page, view)
        if cell in seen_cells:
            raise ValueError(f"duplicate E-010 page/view cell {cell}")
        seen_cells.add(cell)
        if page not in seen_pages:
            seen_pages.add(page)
            page_order.append(page)
        if set(row["features"]) != set(FEATURES):
            raise ValueError(f"feature panel differs at {page}/{view}")
        for feature in FEATURES:
            values[feature][view][page] = float(row["features"][feature])
    expected_cells = {(page, view) for page in page_order for view in expected_views}
    if seen_cells != expected_cells:
        raise ValueError("E-010 page/view table is not a complete rectangle")
    arrays = {
        feature: {
            view: np.asarray([values[feature][view][page] for page in page_order])
            for view in expected_views
        }
        for feature in FEATURES
    }
    return tuple(page_order), arrays, rows


def _pair_metrics(
    values: dict[str, np.ndarray], names: tuple[str, ...]
) -> dict[str, dict[str, float]]:
    return {
        f"{left}::{right}": {
            "spearman_rho": _spearman(values[left], values[right]),
            "median_absolute_difference": float(np.median(np.abs(values[left] - values[right]))),
        }
        for left, right in combinations(names, 2)
    }


def analyze(
    config: dict[str, Any],
    page_order: tuple[str, ...],
    raw: dict[str, dict[str, np.ndarray]],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Cross-fit every feature and evaluate the frozen E-011 gates."""
    primary = tuple(config["views"]["primary"])
    uncertainty = tuple(config["views"]["uncertainty"])
    conversion_pairs = tuple(tuple(pair) for pair in config["views"]["conversion_pairs"])
    all_views = tuple(next(iter(raw.values())))
    folds = contiguous_folds(len(page_order), int(config["split"]["folds"]))
    split = {
        "schema_version": "1.0",
        "method": config["split"]["method"],
        "folds": [
            {"fold": index, "pages": [page_order[position] for position in positions]}
            for index, positions in enumerate(folds)
        ],
    }
    calibrated: dict[str, dict[str, np.ndarray]] = {}
    parameters: dict[str, dict[str, list[dict[str, float | int | bool]]]] = {}
    for feature in FEATURES:
        calibrated[feature], parameters[feature] = cross_fit(raw[feature], folds)

    bootstrap_rng = np.random.default_rng(int(config["bootstrap"]["seed"]))
    bootstrap_indices = bootstrap_rng.integers(
        0,
        len(page_order),
        size=(int(config["bootstrap"]["page_replicates"]), len(page_order)),
    )
    primary_pairs = tuple(combinations(primary, 2))
    bootstrap_lower: dict[str, float] = {}
    for feature in FEATURES:
        worst = []
        for indices in bootstrap_indices:
            worst.append(
                min(
                    _spearman(
                        calibrated[feature][left][indices],
                        calibrated[feature][right][indices],
                    )
                    for left, right in primary_pairs
                )
            )
        bootstrap_lower[feature] = float(np.nanpercentile(worst, 2.5))

    null_rng = np.random.default_rng(int(config["null_model"]["seed"]))
    null_replicates = int(config["null_model"]["replicates"])
    reference = str(config["views"]["reference_for_null_only"])
    raw_p: dict[str, float] = {}
    null_summary: dict[str, dict[str, float]] = {}
    for feature in FEATURES:
        observed_pairs = [
            _spearman(calibrated[feature][left], calibrated[feature][right])
            for left, right in primary_pairs
        ]
        observed = float(np.median(observed_pairs))
        null_values = []
        for _ in range(null_replicates):
            permuted = {
                name: (
                    calibrated[feature][name]
                    if name == reference
                    else calibrated[feature][name][null_rng.permutation(len(page_order))]
                )
                for name in primary
            }
            null_values.append(
                float(
                    np.median(
                        [
                            _spearman(permuted[left], permuted[right])
                            for left, right in primary_pairs
                        ]
                    )
                )
            )
        raw_p[feature] = float(
            (1 + sum(value >= observed for value in null_values)) / (null_replicates + 1)
        )
        null_summary[feature] = {
            "observed_median_pair_spearman": observed,
            "null_mean": float(np.mean(null_values)),
            "null_p95": float(np.percentile(null_values, 95)),
        }
    adjusted_p = _holm(raw_p)

    gates_config = config["gates"]
    feature_results: dict[str, Any] = {}
    output_rows: list[dict[str, Any]] = []
    for feature in FEATURES:
        for page_index, page in enumerate(page_order):
            fold_index = next(
                index for index, positions in enumerate(folds) if page_index in positions
            )
            for view in all_views:
                output_rows.append(
                    {
                        "page": page,
                        "fold": fold_index,
                        "view": view,
                        "feature": feature,
                        "raw_value": float(raw[feature][view][page_index]),
                        "calibrated_value": float(calibrated[feature][view][page_index]),
                    }
                )
        primary_metrics = _pair_metrics(calibrated[feature], primary)
        conversion_metrics = {
            f"{left}::{right}": {
                "spearman_rho": _spearman(calibrated[feature][left], calibrated[feature][right]),
                "median_absolute_difference": float(
                    np.median(np.abs(calibrated[feature][left] - calibrated[feature][right]))
                ),
            }
            for left, right in conversion_pairs
        }
        uncertainty_metrics = _pair_metrics(calibrated[feature], uncertainty)
        fold_maximum_differences = []
        for positions in folds:
            fold_maximum_differences.append(
                max(
                    float(
                        np.median(
                            np.abs(
                                calibrated[feature][left][positions]
                                - calibrated[feature][right][positions]
                            )
                        )
                    )
                    for left, right in primary_pairs
                )
            )
        calibration_valid = all(
            item["valid"] for items in parameters[feature].values() for item in items
        )
        worst_primary = min(item["spearman_rho"] for item in primary_metrics.values())
        max_primary_difference = max(
            item["median_absolute_difference"] for item in primary_metrics.values()
        )
        worst_conversion = min(item["spearman_rho"] for item in conversion_metrics.values())
        max_conversion_difference = max(
            item["median_absolute_difference"] for item in conversion_metrics.values()
        )
        worst_uncertainty = min(item["spearman_rho"] for item in uncertainty_metrics.values())
        max_uncertainty_difference = max(
            item["median_absolute_difference"] for item in uncertainty_metrics.values()
        )
        passing_folds = sum(
            value <= float(gates_config["maximum_fold_primary_median_absolute_difference"])
            for value in fold_maximum_differences
        )
        gates = {
            "calibration_iqrs": calibration_valid,
            "primary_rank": worst_primary >= float(gates_config["minimum_worst_primary_spearman"]),
            "primary_bootstrap": bootstrap_lower[feature]
            >= float(gates_config["minimum_worst_primary_bootstrap_lower"]),
            "primary_agreement": max_primary_difference
            <= float(gates_config["maximum_primary_median_absolute_difference"]),
            "heldout_fold_agreement": passing_folds
            >= int(gates_config["minimum_passing_heldout_folds"]),
            "conversion_rank": worst_conversion
            >= float(gates_config["minimum_worst_conversion_spearman"]),
            "conversion_agreement": max_conversion_difference
            <= float(gates_config["maximum_conversion_median_absolute_difference"]),
            "uncertainty_rank": worst_uncertainty
            >= float(gates_config["minimum_worst_uncertainty_spearman"]),
            "uncertainty_agreement": max_uncertainty_difference
            <= float(gates_config["maximum_uncertainty_median_absolute_difference"]),
            "aligned_page_null": adjusted_p[feature]
            <= float(gates_config["maximum_holm_adjusted_permutation_p"]),
        }
        feature_results[feature] = {
            "stable": all(gates.values()),
            "worst_primary_spearman": worst_primary,
            "primary_bootstrap_95_lower": bootstrap_lower[feature],
            "maximum_primary_median_absolute_difference": max_primary_difference,
            "fold_maximum_primary_median_absolute_differences": fold_maximum_differences,
            "passing_heldout_folds": passing_folds,
            "worst_conversion_spearman": worst_conversion,
            "maximum_conversion_median_absolute_difference": max_conversion_difference,
            "worst_uncertainty_spearman": worst_uncertainty,
            "maximum_uncertainty_median_absolute_difference": max_uncertainty_difference,
            "primary_pairs": primary_metrics,
            "conversion_pairs": conversion_metrics,
            "uncertainty_pairs": uncertainty_metrics,
            "page_label_null": {
                **null_summary[feature],
                "raw_p": raw_p[feature],
                "holm_adjusted_p": adjusted_p[feature],
            },
            "calibration_parameters": parameters[feature],
            "gates": gates,
        }
    return output_rows, feature_results, split


def _preregistration_revision(root: Path, config_path: Path) -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", str(config_path.relative_to(root))],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def run_campaign(config_path: Path) -> dict[str, Any]:
    """Run the immutable E-011 campaign from E-010's frozen page features."""
    started = time.monotonic()
    root = repository_root()
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config.get("experiment_id") != "E-011-cross-fitted-witness-calibration":
        raise ValueError("not the frozen E-011 config")
    if tuple(config["features"]["all"]) != FEATURES:
        raise ValueError("E-011 feature panel changed")
    predecessor = config["predecessor"]
    result_path = root / predecessor["result"]
    features_path = root / predecessor["page_features"]
    if sha256_file(result_path) != predecessor["result_sha256"]:
        raise ValueError("frozen E-010 result hash changed")
    if sha256_file(features_path) != predecessor["page_features_sha256"]:
        raise ValueError("frozen E-010 page-feature hash changed")
    predecessor_result = orjson.loads(result_path.read_bytes())
    expected_views = (
        tuple(config["views"]["primary"])
        + tuple(pair[1] for pair in config["views"]["conversion_pairs"])
        + tuple(config["views"]["uncertainty"])
    )
    if len(expected_views) != len(set(expected_views)):
        raise ValueError("E-011 view registry contains duplicates")
    page_order, raw, _ = load_e010_rows(features_path, expected_views)
    controls = synthetic_controls(config)
    calibrated_rows, feature_results, split = analyze(config, page_order, raw)
    stable = [feature for feature in FEATURES if feature_results[feature]["stable"]]
    order_sensitive = set(config["features"]["order_sensitive"])
    stable_order = [feature for feature in stable if feature in order_sensitive]
    gates = {
        "synthetic_controls": controls["passed"],
        "minimum_stable_features": len(stable) >= int(config["gates"]["minimum_stable_features"]),
        "minimum_stable_order_sensitive_features": len(stable_order)
        >= int(config["gates"]["minimum_stable_order_sensitive_features"]),
    }
    provenance = git_provenance(root)
    if provenance["git_dirty"]:
        raise ValueError("E-011 target calculation requires a clean committed worktree")
    destination = root / config["artifacts"]["root"]
    outputs = {
        "split": destination / config["artifacts"]["split"],
        "calibrated_features": destination / config["artifacts"]["calibrated_features"],
        "result": destination / config["artifacts"]["result"],
    }
    if any(path.exists() for path in outputs.values()):
        raise FileExistsError(f"immutable E-011 output already exists under {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    outputs["split"].write_bytes(
        orjson.dumps(split, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n"
    )
    with outputs["calibrated_features"].open("wb") as handle:
        for row in calibrated_rows:
            handle.write(orjson.dumps(row, option=orjson.OPT_SORT_KEYS) + b"\n")
    result = {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "hypothesis_id": config["hypothesis_id"],
        "question_id": config["question_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "pass" if all(gates.values()) else "fail",
        "target_inference_permitted": False,
        "page_count": len(page_order),
        "view_count": len(expected_views),
        "controls": controls,
        "feature_results": feature_results,
        "stable_features": stable,
        "stable_order_sensitive_features": stable_order,
        "gates": gates,
        "runtime_seconds": time.monotonic() - started,
        "provenance": {
            **provenance,
            "preregistration_git_commit": _preregistration_revision(root, config_path),
            "config_sha256": sha256_file(config_path),
            "protocol_sha256": sha256_file(root / config["protocol"]),
            "predecessor_result_sha256": predecessor["result_sha256"],
            "predecessor_page_features_sha256": predecessor["page_features_sha256"],
            "predecessor_git_commit": predecessor_result["provenance"]["git_commit"],
            "split_sha256": sha256_file(outputs["split"]),
            "calibrated_features_sha256": sha256_file(outputs["calibrated_features"]),
            "python": sys.version.split()[0],
            "device": "CPU",
        },
        "interpretation": (
            "Held-out witness measurement calibration only; no language, cipher, meaning, "
            "constructed-language, or hoax inference is permitted."
        ),
    }
    outputs["result"].write_bytes(
        orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n"
    )
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/E-011-cross-fitted-witness-calibration.yaml"),
    )
    args = parser.parse_args()
    result = run_campaign(args.config)
    print(
        orjson.dumps(
            {
                "status": result["status"],
                "controls": result["controls"],
                "stable_features": result["stable_features"],
                "stable_order_sensitive_features": result["stable_order_sensitive_features"],
                "gates": result["gates"],
                "runtime_seconds": result["runtime_seconds"],
            },
            option=orjson.OPT_INDENT_2,
        ).decode()
    )


if __name__ == "__main__":
    main()
