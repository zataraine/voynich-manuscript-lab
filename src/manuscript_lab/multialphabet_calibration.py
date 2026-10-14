"""E-016: uniform-stationary Markov controls with variable group boundaries."""

from __future__ import annotations

import argparse
import hashlib
import math
import random
import statistics
from dataclasses import asdict, replace
from itertools import pairwise
from pathlib import Path

import orjson
import yaml
from scipy.stats import entropy, t

from manuscript_lab.ledger import git_provenance
from manuscript_lab.measurement_battery import MeasurementError, MeasurementRecord
from manuscript_lab.provenance import repository_root, sha256_file
from manuscript_lab.uncertainty_calibration import (
    METRICS,
    PROFILE_PATH,
    _oracle,
    scoped_uncertainty,
)

CONFIG_PATH = Path("config/experiments/E-016-multialphabet-calibration.yaml")
DESIGN = {
    "alphabet_sizes": [4, 16, 32],
    "copy_probabilities": [0.0, 0.5, 0.9],
    "units_per_split": [512, 8192, 65536],
    "width_cycle": [1, 2, 4, 8, 16, 32],
    "replicates": 32,
    "maximum_mean_error_bits": 0.05,
    "minimum_separation_bits": 0.2,
    "family_alpha": 0.05,
}


def markov_records(*, alphabet, copy_probability, units_per_split, widths, seed, split):
    """Every group starts uniform; copy or redraw uniformly within that group."""
    if alphabet < 2 or not 0 <= copy_probability <= 1 or units_per_split % 4 or units_per_split < 4:
        raise MeasurementError("invalid uniform-stationary process parameters")
    if not widths or any(type(width) is not int or width < 1 for width in widths):
        raise MeasurementError("group widths must be positive integers")
    rng = random.Random(seed)
    result = []
    for page in range(4):
        remaining, index, groups = units_per_split // 4, 0, []
        while remaining:
            width = min(widths[index % len(widths)], remaining)
            group = [rng.randrange(alphabet)]
            for _ in range(width - 1):
                group.append(
                    group[-1] if rng.random() < copy_probability else rng.randrange(alphabet)
                )
            groups.append(tuple(group))
            index += 1
            remaining -= width
        result.append(
            MeasurementRecord(
                f"{split}:r{page}",
                f"{split}:p{page}",
                None,
                page,
                tuple(groups),
                ("observed",) * (len(groups) - 1),
            )
        )
    return tuple(result)


def population_truth(alphabet, probability):
    redraw = (1 - probability) / alphabet
    return {
        METRICS[0]: math.log2(alphabet),
        METRICS[1]: float(entropy([probability + redraw] + [redraw] * (alphabet - 1), base=2)),
    }


def run_calibration(config):
    if (
        config["experiment_id"] != "E-016-multialphabet-calibration"
        or config["parameters"] != DESIGN
        or config["seed"] != 20261015
        or config["transcription"] != "none; synthetic numeric controls only"
    ):
        raise MeasurementError("E-016 requires its frozen bounded design")
    cases = []
    for alphabet in DESIGN["alphabet_sizes"]:
        for probability in DESIGN["copy_probabilities"]:
            for size in DESIGN["units_per_split"]:
                for replicate in range(DESIGN["replicates"]):
                    tag = f"E016:{config['seed']}:{alphabet}:{probability}:{size}:{replicate}"
                    seed = int.from_bytes(hashlib.sha256(tag.encode()).digest()[:8], "big")
                    records = {
                        split: markov_records(
                            alphabet=alphabet,
                            copy_probability=probability,
                            units_per_split=size,
                            widths=DESIGN["width_cycle"],
                            seed=seed + offset,
                            split=split,
                        )
                        for split, offset in (("training", 0), ("heldout", 1))
                    }
                    panels = {split: scoped_uncertainty(value) for split, value in records.items()}
                    oracle = _oracle(records["heldout"])
                    renamed = tuple(
                        replace(r, groups=tuple(tuple(100 - x for x in g) for g in r.groups))
                        for r in records["heldout"]
                    )
                    other = scoped_uncertainty(renamed)["metrics"]
                    cases.append(
                        {
                            "alphabet": alphabet,
                            "copy_probability": probability,
                            "units_per_split": size,
                            "replicate": replicate,
                            "seed": seed,
                            "panels": panels,
                            "input_sha256": {
                                split: hashlib.sha256(
                                    orjson.dumps([asdict(r) for r in value])
                                ).hexdigest()
                                for split, value in records.items()
                            },
                            "oracle_max_delta": max(
                                abs(panels["heldout"]["metrics"][name] - oracle[name])
                                for name in METRICS
                            ),
                            "rename_max_delta": max(
                                abs(panels["heldout"]["metrics"][name] - other[name])
                                for name in METRICS
                            ),
                            "pages_disjoint": not (
                                {r.page for r in records["training"]}
                                & {r.page for r in records["heldout"]}
                            ),
                        }
                    )
    critical = float(t.ppf(1 - DESIGN["family_alpha"] / (2 * 24), DESIGN["replicates"] - 1))
    summaries = []
    for alphabet in DESIGN["alphabet_sizes"]:
        for probability in DESIGN["copy_probabilities"]:
            truth = population_truth(alphabet, probability)
            for size in DESIGN["units_per_split"]:
                selected = [
                    c
                    for c in cases
                    if (c["alphabet"], c["copy_probability"], c["units_per_split"])
                    == (alphabet, probability, size)
                ]
                metrics = {}
                for name in METRICS:
                    samples = [c["panels"]["heldout"]["metrics"][name] for c in selected]
                    mean, sd = statistics.mean(samples), statistics.stdev(samples)
                    se = sd / math.sqrt(len(samples))
                    metrics[name] = {
                        "mean": mean,
                        "sample_sd": sd,
                        "standard_error": se,
                        "truth": truth[name],
                        "signed_mean_error": mean - truth[name],
                        "mean_error_upper_bound": abs(mean - truth[name]) + critical * se,
                    }
                summaries.append(
                    {
                        "alphabet": alphabet,
                        "copy_probability": probability,
                        "units_per_split": size,
                        "metrics": metrics,
                    }
                )
    largest = {
        (r["alphabet"], r["copy_probability"]): r["metrics"]
        for r in summaries
        if r["units_per_split"] == max(DESIGN["units_per_split"])
    }
    gates = {
        f"mean_accuracy_k{k}_r{p}_{name}": metrics[name]["mean_error_upper_bound"]
        <= DESIGN["maximum_mean_error_bits"]
        for (k, p), metrics in largest.items()
        for name in METRICS
    }
    separation = []
    for alphabet in DESIGN["alphabet_sizes"]:
        for left, right in pairwise(DESIGN["copy_probabilities"]):
            a, b = largest[alphabet, left][METRICS[1]], largest[alphabet, right][METRICS[1]]
            lower = (
                a["mean"]
                - b["mean"]
                - critical * math.hypot(a["standard_error"], b["standard_error"])
            )
            separation.append(
                {
                    "alphabet": alphabet,
                    "left_copy_probability": left,
                    "right_copy_probability": right,
                    "gap_lower_bound": lower,
                }
            )
            gates[f"separation_k{alphabet}_{left}_{right}"] = (
                lower >= DESIGN["minimum_separation_bits"]
            )
    construction = {
        "independent_oracle": max(c["oracle_max_delta"] for c in cases) <= 1e-12,
        "bijective_rename": max(c["rename_max_delta"] for c in cases) <= 1e-12,
        "disjoint_pages": all(c["pages_disjoint"] for c in cases),
        "all_panels_defined": all(
            p["status"] == "available_not_calibrated" for c in cases for p in c["panels"].values()
        ),
        "unique_split_seeds": len({c["seed"] + offset for c in cases for offset in (0, 1)})
        == 2 * len(cases),
        "exact_sample_sizes": all(
            p["support"]["unit_count"] == c["units_per_split"]
            for c in cases
            for p in c["panels"].values()
        ),
    }
    return {
        "experiment_id": config["experiment_id"],
        "profile_id": "uncertainty-scope-v1",
        "case_count": len(cases),
        "cases": cases,
        "summaries": summaries,
        "separation": separation,
        "construction_gates": construction,
        "calibration_gates": gates,
        "status": "passed_tested_domain"
        if all(construction.values()) and all(gates.values())
        else "failed_tested_domain",
        "target_access": "forbidden",
        "phase4_complete": False,
        "limits": [
            "Uniform stationary marginals and first-order copy/redraw processes only.",
            "Widths are a deterministic cycle, not observed manuscript lengths.",
            "Primary gates use 65,536 units; shorter lengths remain diagnostic, even if biased.",
            "Approximate intervals address mean estimator error, not individual-document accuracy.",
            "No semantic, cipher or manuscript conclusion follows.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    root = repository_root()
    config_path = root / CONFIG_PATH
    config = yaml.safe_load(config_path.read_text())
    output = root / config["artifacts"]["root"] / "result.json"
    before = git_provenance(root)
    if (
        before["git_dirty"]
        or output.exists()
        or not output.resolve().is_relative_to(root / "artifacts/runs")
    ):
        parser.error("commit the design and choose an unused immutable research-run path")
    manifest_path = root / config["source_manifest"]
    manifest = yaml.safe_load(manifest_path.read_text())
    if manifest["generator_sha256"] != sha256_file(Path(__file__)):
        parser.error("synthetic generator differs from its source definition")
    result = run_calibration(config)
    if before != git_provenance(root):
        parser.error("working tree changed during the research run")
    result["provenance"] = {
        **before,
        "config_sha256": sha256_file(config_path),
        "source_manifest": config["source_manifest"],
        "source_manifest_sha256": sha256_file(manifest_path),
        "profile_sha256": sha256_file(root / PROFILE_PATH),
        "environment_lock_sha256": sha256_file(root / "uv.lock"),
        "device": "cpu",
        "output_path": str(output.relative_to(root)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(orjson.dumps(result, option=orjson.OPT_INDENT_2))
    print(f"{result['case_count']} paired simulations: {result['status']}")


if __name__ == "__main__":
    main()
