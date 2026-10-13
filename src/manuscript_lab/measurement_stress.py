"""Synthetic-only, bounded joint-measurement stress checks, not calibration."""

from __future__ import annotations

import argparse
import hashlib
import math
import random
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import orjson
import yaml

from manuscript_lab.layout_measurements import measure_layout
from manuscript_lab.ledger import git_provenance
from manuscript_lab.measurement_battery import (
    MeasurementError,
    MeasurementRecord,
    load_measurement_battery,
    measure_core,
    measure_learned_uncertainty,
    measure_training_heldout,
    restore_learned_merge_table,
    structural_nulls,
)
from manuscript_lab.provenance import repository_root, sha256_file
from manuscript_lab.vocabulary_growth import measure_vocabulary_growth, validate_vocabulary_growth

CONFIG_PATH = Path("config/research/measurement-stress-v1.yaml")
SCENARIOS = {
    "constant",
    "unique",
    "binary_iid",
    "large_inventory_iid",
    "imbalanced_iid",
    "unequal_pages",
}
MASKS = {"none", "alternating", "longest_lines"}


def synthetic_records(*, scenario: str, count: int, seed: int, split: str, groups: int):
    """Generate numeric fixtures only; no corpus or external-text loader exists."""
    rng = random.Random(seed)
    records = []
    symbol_index = 0
    for i in range(count):
        width = 1 + i % 3
        content = []
        for _ in range(groups):
            units = []
            for _ in range(width):
                if scenario == "constant":
                    value = 0
                elif scenario == "unique":
                    value = symbol_index
                elif scenario == "imbalanced_iid":
                    value = int(rng.random() >= 0.95)
                else:
                    value = rng.randrange(32 if scenario == "large_inventory_iid" else 2)
                symbol_index += 1
                units.append(value)
            content.append(tuple(units))
        page = 0 if scenario == "unequal_pages" and i < count - 1 else i // 3
        session = i // max(1, count // 4)
        records.append(
            MeasurementRecord(
                record_id=f"{split}:r{i}",
                page=f"{split}:p{page}",
                section=f"s{i // 3 % 2}",
                line_index=i,
                groups=tuple(content),
                boundaries=tuple("rare" if j == 0 else "common" for j in range(groups - 1)),
                paragraph_id=f"paragraph-{i // 3}",
                paragraph_line_index=i % 3,
                session_id=f"session-{session}",
                session_index=session,
            )
        )
    return tuple(records)


def _finite(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite(item) for item in value)
    return True


def run_stress_suite(config: dict[str, Any]) -> dict[str, Any]:
    """Apply fixed checks and retain all cases, including any failed checks."""
    if (
        set(config)
        != {
            "suite_id",
            "target_access",
            "numeric_absolute_tolerance",
            "record_counts",
            "seeds",
            "scenarios",
            "groups_per_record",
            "annotation_masks",
        }
        or config["suite_id"] != "measurement-stress-v1"
        or config["target_access"] != "forbidden"
        or config["numeric_absolute_tolerance"] != 1e-12
        or not config["scenarios"]
        or not set(config["scenarios"]) <= SCENARIOS
        or not config["annotation_masks"]
        or not set(config["annotation_masks"]) <= MASKS
        or not config["record_counts"]
        or not config["seeds"]
        or any(type(n) is not int or not 4 <= n <= 64 for n in config["record_counts"])
        or any(type(seed) is not int for seed in config["seeds"])
        or type(config["groups_per_record"]) is not int
        or not 2 <= config["groups_per_record"] <= 16
        or len(config["seeds"]) > 8
        or len(config["record_counts"]) > 3
        or len(config["record_counts"]) != len(set(config["record_counts"]))
        or len(config["seeds"]) != len(set(config["seeds"]))
        or len(config["scenarios"]) != len(set(config["scenarios"]))
        or len(config["annotation_masks"]) != len(set(config["annotation_masks"]))
    ):
        raise MeasurementError("invalid or unbounded synthetic stress configuration")
    battery = load_measurement_battery()
    cases = []
    for scenario in config["scenarios"]:
        for count in config["record_counts"]:
            for seed in config["seeds"]:
                training = synthetic_records(
                    scenario=scenario,
                    count=count,
                    seed=seed,
                    split="training",
                    groups=config["groups_per_record"],
                )
                heldout = synthetic_records(
                    scenario=scenario,
                    count=count,
                    seed=seed + 1,
                    split="heldout",
                    groups=config["groups_per_record"],
                )
                measurements = measure_training_heldout(
                    training, heldout, battery=battery, seed=seed
                )
                tables = {
                    scale: restore_learned_merge_table(entry["merge_table"])
                    for scale, entry in measurements["learned_units"].items()
                }
                layout = measure_layout(heldout, battery=battery, seed=seed)
                growth = measure_vocabulary_growth(heldout)
                validate_vocabulary_growth(growth)
                checks = {
                    "disjoint_pages": not ({r.page for r in training} & {r.page for r in heldout}),
                    "finite_panels": _finite([measurements, layout, growth]),
                    "known_paragraph_direction": abs(
                        layout["metrics"]["within_paragraph_position_length_spearman"] - 1
                    )
                    < 1e-12,
                }
                renamed = tuple(
                    replace(r, groups=tuple(tuple(100000 - x for x in g) for g in r.groups))
                    for r in heldout
                )
                renamed_metrics = measure_core(renamed, battery=battery, seed=seed)
                rename_max_delta = max(
                    abs(renamed_metrics[name] - value)
                    for name, value in measurements["heldout"].items()
                )
                checks["core_rename_invariance"] = (
                    rename_max_delta <= config["numeric_absolute_tolerance"]
                )
                checks["growth_rename_invariance"] = measure_vocabulary_growth(renamed) == growth
                masks = {}
                for mask in config["annotation_masks"]:
                    masked = tuple(
                        replace(
                            r,
                            paragraph_id=None,
                            paragraph_line_index=None,
                            session_id=None,
                            session_index=None,
                        )
                        if (
                            mask == "none"
                            or (mask == "alternating" and i % 2 == 0)
                            or (mask == "longest_lines" and i % 3 == 2)
                        )
                        else r
                        for i, r in enumerate(heldout)
                    )
                    panel = measure_layout(masked, battery=battery, seed=seed)
                    checks[f"{mask}_core_unchanged"] = (
                        measure_core(masked, battery=battery, seed=seed) == measurements["heldout"]
                    )
                    checks[f"{mask}_growth_unchanged"] = measure_vocabulary_growth(masked) == growth
                    checks[f"{mask}_finite"] = _finite(panel)
                    checks[f"{mask}_learned_unchanged"] = all(
                        measure_learned_uncertainty(masked, merges=table)
                        == measurements["learned_units"][scale]["uncertainty"]["heldout"]
                        for scale, table in tables.items()
                    )
                    if mask == "none":
                        checks["missing_annotations_explicit"] = (
                            len(panel["support"]["undefined_metrics"]) == 3
                        )
                    masks[mask] = panel
                nulls = {}
                for name, records in structural_nulls(heldout, seed=seed).items():
                    panel = {
                        "core": measure_core(records, battery=battery, seed=seed),
                        "layout": measure_layout(records, battery=battery, seed=seed),
                        "growth": measure_vocabulary_growth(records),
                        "learned_uncertainty": {
                            scale: measure_learned_uncertainty(records, merges=table)
                            for scale, table in tables.items()
                        },
                    }
                    validate_vocabulary_growth(panel["growth"])
                    checks[f"{name}_finite"] = _finite(panel)
                    nulls[name] = panel
                if scenario == "unique":
                    checks["unique_novelty"] = (
                        growth["pooled"]["metrics"]["second_half_novel_type_rate"] == 1
                    )
                    checks["unique_recurrence_undefined"] = (
                        "median_recurrence_distance" in growth["pooled"]["undefined_metrics"]
                    )
                cases.append(
                    {
                        "scenario": scenario,
                        "records_per_split": count,
                        "seed": seed,
                        "source_kind": "synthetic",
                        "device": "cpu",
                        "input_records": {
                            "training": [asdict(r) for r in training],
                            "heldout": [asdict(r) for r in heldout],
                        },
                        "measurements": measurements,
                        "layout": layout,
                        "growth": growth,
                        "annotation_masks": masks,
                        "nulls": nulls,
                        "checks": checks,
                        "rename_max_absolute_delta": rename_max_delta,
                    }
                )
    return {
        "suite_id": config["suite_id"],
        "config": config,
        "battery_id": battery.battery_id,
        "battery_sha256": battery.sha256,
        "case_count": len(cases),
        "cases": cases,
        "failed_checks": [
            {"case_index": i, "check": name}
            for i, case in enumerate(cases)
            for name, passed in case["checks"].items()
            if not passed
        ],
        "decision": "software_diagnostics_only",
        "phase4_complete": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = repository_root()
    output = args.output.resolve()
    if not output.is_relative_to(root / "artifacts") or output.exists():
        parser.error("choose a new output path under artifacts/")
    config = yaml.safe_load((root / CONFIG_PATH).read_text())
    result = run_stress_suite(config)
    result["provenance"] = {
        **git_provenance(root),
        "config_sha256": sha256_file(root / CONFIG_PATH),
        "environment_lock_sha256": sha256_file(root / "uv.lock"),
        "output_path": str(output.relative_to(root)),
        "synthetic_inputs_sha256": hashlib.sha256(
            orjson.dumps(
                [case["input_records"] for case in result["cases"]], option=orjson.OPT_SORT_KEYS
            )
        ).hexdigest(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(orjson.dumps(result, option=orjson.OPT_INDENT_2))
    print(f"{result['case_count']} cases; {len(result['failed_checks'])} failed software checks")
    if result["failed_checks"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
