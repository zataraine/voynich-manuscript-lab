"""Fail-closed availability audit; no numeric reliability or target permission."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

import orjson
import yaml

from manuscript_lab.layout_measurements import METRICS as LAYOUT_METRICS
from manuscript_lab.measurement_battery import (
    LEARNED_UNCERTAINTY_METRICS,
    MeasurementError,
    load_measurement_battery,
)
from manuscript_lab.provenance import repository_root, sha256_file
from manuscript_lab.vocabulary_growth import METRICS as GROWTH_METRICS

POLICY_PATH = Path("config/research/measurement-availability-v1.yaml")
POLICY = {
    "policy_id": "measurement-availability-v1",
    "target_access": "forbidden",
    "partial_panel": "forbidden",
    "missing_source_records": "abstain",
    "missing_assigned_pages": "abstain",
    "missing_required_annotations": "abstain",
    "ineligible_declared_paragraphs": "abstain",
    "undefined_required_metrics": "abstain",
    "all_singleton_context": "abstain",
    "scientific_calibration": "required_separately",
}


def assess_measurement_availability(record: dict[str, Any]) -> dict[str, Any]:
    """Audit a control record after canonical schema/consistency validation.

    Missing extensions are legitimate in historical records but cannot pass
    this policy. No placeholder is interpreted as an observed zero. No fitted
    minimum-support cutoff is invented. Available is not reliable/calibrated.
    """
    path = repository_root() / POLICY_PATH
    if yaml.safe_load(path.read_text()) != POLICY:
        raise MeasurementError("availability policy differs from its frozen implementation")
    battery = load_measurement_battery()
    reasons = []

    def add(scope, code, detail):
        reasons.append({"scope": scope, "code": code, "detail": detail})

    def panel(scope, metrics, support, expected):
        if not isinstance(metrics, dict) or set(metrics) != set(expected):
            add(scope, "missing_or_mismatched_metrics", "required metric set is absent or differs")
        elif any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in metrics.values()
        ):
            add(scope, "invalid_metric_value", "required values must be finite real numbers")
        if not isinstance(support, dict) or not isinstance(support.get("undefined_metrics"), dict):
            add(scope, "missing_definedness", "undefined-metric map is required")
            return
        for name, reason in sorted(support["undefined_metrics"].items()):
            add(f"{scope}/{name}", "undefined_metric", str(reason))

    if (record.get("battery_id"), record.get("battery_sha256")) != (
        battery.battery_id,
        battery.sha256,
    ):
        add("record", "battery_mismatch", "policy requires the current frozen battery")
    if record.get("provenance", {}).get("source_kind") not in {"synthetic", "external-control"}:
        add("record", "source_kind_not_control", "this development policy grants no target access")
    coverage = record.get("coverage", {})
    if "missing_records" not in coverage:
        add("coverage", "missing_coverage", "source-record coverage is required")
    elif coverage["missing_records"]:
        add("coverage", "missing_source_records", "source loci have no retained groups")
    splits = record.get("split", {})
    measurements = record.get("measurements", {})
    for split in ("training", "heldout"):
        missing_key = f"{split}_pages_without_usable_records"
        if missing_key not in splits or splits[missing_key]:
            add(split, "missing_assigned_pages", "assigned-page coverage is missing or incomplete")
        metrics = measurements.get(split, {})
        support = measurements.get(f"{split}_support", {})
        panel(f"core/{split}", metrics, support, battery.config["metric_rules"])
        if support.get("records_missing_section", 1):
            add(f"core/{split}", "missing_required_annotations", "section metadata is incomplete")
        if metrics.get("singleton_type_ratio") == 1:
            add(
                f"core/{split}/contextual_block_mi_bits",
                "all_singleton_context",
                "unique groups identify blocks mechanically; no contextual reuse is observed",
            )
    nulls = record.get("nulls", {})
    if set(nulls) != set(battery.config["null_families"]):
        add("nulls", "missing_null_family", "all configured single-draw null families are required")
    for name, entry in sorted(nulls.items()):
        panel(
            f"core/null/{name}",
            entry.get("metrics"),
            entry.get("support"),
            battery.config["metric_rules"],
        )
    layout = record.get("layout", {})
    growth = record.get("vocabulary_growth", {})
    scopes = [(split, layout.get(split), growth.get(split)) for split in ("training", "heldout")]
    scopes.extend(
        (f"null/{name}", layout.get("nulls", {}).get(name), growth.get("nulls", {}).get(name))
        for name in battery.config["null_families"]
    )
    for scope, lp, gp in scopes:
        if not isinstance(lp, dict):
            add(f"layout/{scope}", "missing_panel", "layout extension is required")
        else:
            panel(f"layout/{scope}", lp.get("metrics"), lp.get("support"), LAYOUT_METRICS)
            support = lp.get("support", {})
            if "ineligible_paragraphs" not in support or support["ineligible_paragraphs"]:
                add(
                    f"layout/{scope}",
                    "ineligible_declared_paragraphs",
                    "declared paragraph eligibility is missing or incomplete",
                )
            if support.get("records_missing_paragraph", 1) or support.get(
                "records_missing_session", 1
            ):
                add(
                    f"layout/{scope}",
                    "missing_required_annotations",
                    "paragraph/session annotations are incomplete",
                )
        if not isinstance(gp, dict):
            add(f"growth/{scope}", "missing_panel", "vocabulary-growth extension is required")
        else:
            summaries = [("pooled", gp.get("pooled", {}))]
            summaries.extend(
                (f"page/{entry['page']}", entry["summary"]) for entry in gp.get("page_reset", [])
            )
            if not gp.get("page_reset"):
                add(f"growth/{scope}", "missing_page_scopes", "page-reset summaries are required")
            for reset, summary in summaries:
                panel(f"growth/{scope}/{reset}", summary.get("metrics"), summary, GROWTH_METRICS)
    learned = measurements.get("learned_units", {})
    scales = {str(n) for n in battery.config["learned_unit_policy"]["merge_counts"]}
    if set(learned) != scales:
        add("learned", "missing_or_extra_scales", "all frozen merge budgets are required")
    for scale in sorted(scales, key=int):
        for split in ("training", "heldout"):
            entry = learned.get(scale, {}).get("uncertainty", {}).get(split)
            scope = f"learned/{scale}/{split}"
            if not isinstance(entry, dict):
                add(scope, "missing_panel", "learned uncertainty extension is required")
            else:
                panel(
                    scope, entry.get("metrics"), entry.get("support"), LEARNED_UNCERTAINTY_METRICS
                )
    source = {key: value for key, value in record.items() if key != "availability"}
    return {
        "policy_id": POLICY["policy_id"],
        "policy_sha256": sha256_file(path),
        "input_sha256": hashlib.sha256(
            orjson.dumps(source, option=orjson.OPT_SORT_KEYS)
        ).hexdigest(),
        "status": "abstain" if reasons else "available_not_calibrated",
        "reasons": reasons,
        "joint_comparison_allowed": False,
        "target_access": "forbidden",
        "calibration_status": "not_established_by_availability",
    }


def require_available_measurements(record: dict[str, Any]) -> dict[str, Any]:
    """Validate and refuse an unavailable panel; never authorize scientific use."""
    from manuscript_lab.measurement_records import canonical_measurement_bytes

    validated = orjson.loads(canonical_measurement_bytes(record))
    audit = assess_measurement_availability(validated)
    if audit["status"] == "abstain":
        raise MeasurementError(
            f"joint measurement availability requires abstention: {len(audit['reasons'])} reasons"
        )
    return audit
