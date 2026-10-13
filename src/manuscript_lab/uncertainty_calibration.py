"""E-015: bounded known-process calibration; no manuscript loader or classifier."""

from __future__ import annotations

import argparse
import hashlib
import math
import random
import statistics
from collections import Counter
from dataclasses import asdict
from itertools import pairwise
from pathlib import Path

import orjson
import yaml
from scipy.stats import entropy, t

from manuscript_lab.ledger import git_provenance
from manuscript_lab.measurement_battery import (
    MeasurementError,
    MeasurementRecord,
    _conditional_entropy,
    _entropy,
)
from manuscript_lab.provenance import repository_root, sha256_file

PROFILE_PATH = Path("config/research/uncertainty-scope-v1.yaml")
CONFIG_PATH = Path("config/experiments/E-015-uncertainty-calibration.yaml")
METRICS = ("unit_entropy_bits", "conditional_unit_entropy_order1_bits")
PROFILE = {
    "profile_id": "uncertainty-scope-v1",
    "metrics": list(METRICS),
    "unit_scale": "supplied_reversible_base_units",
    "conditional_reset": "each_observed_group",
    "required_metadata": ["record_id", "physical_page_id", "reversible_grouping"],
    "not_required": ["production_session", "paragraph_annotation", "section_annotation"],
    "undefined_metric": "abstain",
    "partial_panel": "forbidden",
    "target_access": "forbidden_until_external_calibration",
    "full_battery_policy": "unchanged",
}


def scoped_uncertainty(records):
    """Measure only the prospectively named profile; never fall back from a full panel."""
    ids = [r.record_id for r in records]
    if len(ids) != len(set(ids)):
        raise MeasurementError("duplicate uncertainty-scope record IDs")
    groups = [group for record in records for group in record.groups]
    units = [unit for group in groups for unit in group]
    transitions = sum(len(group) - 1 for group in groups)
    undefined = {}
    if not units:
        undefined[METRICS[0]] = "no_observed_units"
    if not transitions:
        undefined[METRICS[1]] = "no_within_group_transitions"
    return {
        "profile_id": "uncertainty-scope-v1",
        "metrics": {METRICS[0]: _entropy(units), METRICS[1]: _conditional_entropy(groups)},
        "support": {
            "record_count": len(records),
            "page_count": len({r.page for r in records}),
            "unit_count": len(units),
            "transition_count": transitions,
            "undefined_metrics": undefined,
        },
        "status": "abstain" if undefined else "available_not_calibrated",
        "target_access": "forbidden",
    }


def generate_records(*, probability, groups_per_record, group_width, seed, split):
    rng = random.Random(seed)
    records = []
    for i in range(4):
        groups = []
        for _ in range(groups_per_record):
            group = [rng.randrange(2)]
            for _ in range(group_width - 1):
                group.append(group[-1] ^ int(rng.random() < probability))
            groups.append(tuple(group))
        records.append(
            MeasurementRecord(
                f"{split}:r{i}",
                f"{split}:p{i}",
                None,
                i,
                tuple(groups),
                ("observed",) * (groups_per_record - 1),
            )
        )
    return tuple(records)


def _oracle(records):
    groups = [g for r in records for g in r.groups]
    units = Counter(x for g in groups for x in g)
    joint = Counter(pair for g in groups for pair in pairwise(g))
    contexts = Counter()
    for (left, _), count in joint.items():
        contexts[left] += count
    return {
        METRICS[0]: float(entropy(list(units.values()), base=2)),
        METRICS[1]: float(
            entropy(list(joint.values()), base=2) - entropy(list(contexts.values()), base=2)
        ),
    }


def run_calibration(config):
    params = config["parameters"]
    if (
        config["experiment_id"] != "E-015-uncertainty-calibration"
        or config["transcription"] != "none; synthetic numeric controls only"
        or config["seed"] != 20261014
        or params["flip_probabilities"] != [0.5, 0.1, 0.01]
        or params["groups_per_record"] != [4, 16, 64]
        or params["group_width"] != 32
        or params["replicates"] != 32
        or params["maximum_mean_error_bits"] != 0.05
        or params["minimum_separation_bits"] != 0.2
        or params["family_alpha"] != 0.05
    ):
        raise MeasurementError("E-015 requires its frozen bounded design")
    rows = []
    for probability in params["flip_probabilities"]:
        for count in params["groups_per_record"]:
            for replicate in range(params["replicates"]):
                material = f"E015:{config['seed']}:{probability}:{count}:{replicate}"
                seed = int.from_bytes(hashlib.sha256(material.encode()).digest()[:8], "big")
                records = {
                    split: generate_records(
                        probability=probability,
                        groups_per_record=count,
                        group_width=params["group_width"],
                        seed=seed + offset,
                        split=split,
                    )
                    for split, offset in (("training", 0), ("heldout", 1))
                }
                panels = {split: scoped_uncertainty(value) for split, value in records.items()}
                oracle = _oracle(records["heldout"])
                renamed = tuple(
                    MeasurementRecord(
                        r.record_id,
                        r.page,
                        None,
                        r.line_index,
                        tuple(tuple(9 - x for x in g) for g in r.groups),
                        r.boundaries,
                    )
                    for r in records["heldout"]
                )
                rename_delta = max(
                    abs(
                        scoped_uncertainty(renamed)["metrics"][name]
                        - panels["heldout"]["metrics"][name]
                    )
                    for name in METRICS
                )
                delta = max(
                    abs(panels["heldout"]["metrics"][name] - oracle[name]) for name in METRICS
                )
                rows.append(
                    {
                        "flip_probability": probability,
                        "groups_per_record": count,
                        "replicate": replicate,
                        "seed": seed,
                        "panels": panels,
                        "input_sha256": {
                            split: hashlib.sha256(
                                orjson.dumps([asdict(r) for r in value])
                            ).hexdigest()
                            for split, value in records.items()
                        },
                        "oracle_max_delta": delta,
                        "rename_max_delta": rename_delta,
                        "split_pages_disjoint": not (
                            {r.page for r in records["training"]}
                            & {r.page for r in records["heldout"]}
                        ),
                    }
                )
    # Eight simultaneous approximate Student-t intervals: six mean-error and two separation checks.
    critical = float(t.ppf(1 - params["family_alpha"] / (2 * 8), params["replicates"] - 1))
    summaries = []
    for probability in params["flip_probabilities"]:
        expected = {
            METRICS[0]: 1.0,
            METRICS[1]: float(entropy([probability, 1 - probability], base=2)),
        }
        for count in params["groups_per_record"]:
            selected = [
                r
                for r in rows
                if r["flip_probability"] == probability and r["groups_per_record"] == count
            ]
            values = {}
            for metric in METRICS:
                samples = [r["panels"]["heldout"]["metrics"][metric] for r in selected]
                mean = statistics.mean(samples)
                se = statistics.stdev(samples) / math.sqrt(len(samples))
                values[metric] = {
                    "mean": mean,
                    "sample_sd": statistics.stdev(samples),
                    "standard_error": se,
                    "truth": expected[metric],
                    "absolute_mean_error": abs(mean - expected[metric]),
                    "mean_error_upper_bound": abs(mean - expected[metric]) + critical * se,
                }
            summaries.append(
                {"flip_probability": probability, "groups_per_record": count, "metrics": values}
            )
    largest = {
        r["flip_probability"]: r["metrics"] for r in summaries if r["groups_per_record"] == 64
    }
    gates = {
        f"mean_accuracy_p{p}_{name}": values[name]["mean_error_upper_bound"]
        <= params["maximum_mean_error_bits"]
        for p, values in largest.items()
        for name in METRICS
    }
    separation = []
    for left, right in pairwise(params["flip_probabilities"]):
        a, b = largest[left][METRICS[1]], largest[right][METRICS[1]]
        lower = (
            a["mean"] - b["mean"] - critical * math.hypot(a["standard_error"], b["standard_error"])
        )
        separation.append(
            {"left_probability": left, "right_probability": right, "gap_lower_bound": lower}
        )
        gates[f"separation_{left}_{right}"] = lower >= params["minimum_separation_bits"]
    construction = {
        "bijective_rename": max(r["rename_max_delta"] for r in rows) <= 1e-12,
        "disjoint_pages": all(r["split_pages_disjoint"] for r in rows),
        "independent_oracle": max(r["oracle_max_delta"] for r in rows) <= 1e-12,
        "all_scoped_panels_defined": all(
            panel["status"] == "available_not_calibrated"
            for r in rows
            for panel in r["panels"].values()
        ),
    }
    return {
        "experiment_id": config["experiment_id"],
        "profile_id": "uncertainty-scope-v1",
        "case_count": len(rows),
        "cases": rows,
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
            "Only symmetric binary first-order processes at the frozen lengths are tested.",
            "Intervals describe mean estimator error, not individual-corpus accuracy.",
            "Student-t intervals are approximate; Bonferroni allocation does not make them exact.",
            "No payload classification, published-mechanism replication or manuscript scoring.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()
    root = repository_root()
    config_path = args.config.resolve()
    if config_path != (root / CONFIG_PATH).resolve():
        parser.error("E-015 requires the tracked preregistered config")
    if yaml.safe_load((root / PROFILE_PATH).read_text()) != PROFILE:
        parser.error("uncertainty profile differs from its frozen definition")
    config = yaml.safe_load(config_path.read_text())
    output = root / config["artifacts"]["root"] / "result.json"
    if not output.resolve().is_relative_to(root / "artifacts" / "runs") or output.exists():
        parser.error("choose a new immutable run path under artifacts/runs/")
    before = git_provenance(root)
    if before["git_dirty"]:
        parser.error("commit the preregistered design before the research run")
    manifest = root / config["source_manifest"]
    definition = yaml.safe_load(manifest.read_text())
    if definition["generator_sha256"] != sha256_file(Path(__file__)):
        parser.error("synthetic generator differs from its source definition")
    result = run_calibration(config)
    if before != git_provenance(root):
        parser.error("working tree changed during the run")
    result["provenance"] = {
        **before,
        "config_sha256": sha256_file(config_path),
        "source_manifest": config["source_manifest"],
        "source_manifest_sha256": sha256_file(manifest),
        "profile_sha256": sha256_file(root / PROFILE_PATH),
        "environment_lock_sha256": sha256_file(root / "uv.lock"),
        "device": "cpu",
        "output_path": str(output.relative_to(root)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(orjson.dumps(result, option=orjson.OPT_INDENT_2))
    print(f"{result['case_count']} simulated corpora: {result['status']}")


if __name__ == "__main__":
    main()
