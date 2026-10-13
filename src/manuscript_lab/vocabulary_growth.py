"""Ordered group discovery and recurrence, with explicit pooled/page resets."""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from typing import Any

from manuscript_lab.measurement_battery import MeasurementError, MeasurementRecord

METRICS = ("second_half_novel_type_rate", "median_recurrence_distance")


def _summary(count: int, discoveries: list[int], gaps: list[int]) -> dict[str, Any]:
    """Replay all reported summaries from retained one-based event positions."""
    if (
        not isinstance(count, int)
        or isinstance(count, bool)
        or count < 0
        or any(not isinstance(x, int) or isinstance(x, bool) for x in discoveries + gaps)
        or discoveries != sorted(set(discoveries))
        or any(not 1 <= x <= count for x in discoveries)
        or (count > 0 and (not discoveries or discoveries[0] != 1))
        or any(not 1 <= x < count for x in gaps)
        or len(gaps) != count - len(discoveries)
    ):
        raise MeasurementError("invalid vocabulary growth events")
    half = count // 2
    prefix_types = sum(position <= half for position in discoveries)
    undefined = {}
    if count < 2:
        undefined[METRICS[0]] = "fewer_than_two_groups"
    if not gaps:
        undefined[METRICS[1]] = "no_repeated_groups_in_scope"
    checkpoints = {half, count} - {0}
    index = 1
    while index <= count:
        checkpoints.add(index)
        index *= 2
    # One sweep rather than rescanning every discovery for each checkpoint.
    curve = []
    discovered = 0
    for checkpoint in sorted(checkpoints):
        while discovered < len(discoveries) and discoveries[discovered] <= checkpoint:
            discovered += 1
        curve.append({"group_count": checkpoint, "type_count": discovered})
    return {
        "group_count": count,
        "type_count": len(discoveries),
        "half_prefix_group_count": half,
        "half_prefix_type_count": prefix_types,
        "discovery_positions": discoveries,
        "recurrence_gaps": gaps,
        "curve": curve,
        "metrics": {
            METRICS[0]: (len(discoveries) - prefix_types) / (count - half) if count >= 2 else 0.0,
            METRICS[1]: float(statistics.median(gaps)) if gaps else 0.0,
        },
        "undefined_metrics": undefined,
    }


def _measure(groups: Sequence[tuple[int, ...]]) -> dict[str, Any]:
    last = {}
    discoveries = []
    gaps = []
    for position, group in enumerate(groups, start=1):
        if group in last:
            gaps.append(position - last[group])
        else:
            discoveries.append(position)
        last[group] = position
    return _summary(len(groups), discoveries, gaps)


def measure_vocabulary_growth(records: Sequence[MeasurementRecord]) -> dict[str, Any]:
    """Measure supplied record order and separately reset each physical page.

    Group identity means exact numeric-tuple equality, not a lexical judgement.
    Noncontiguous records of a page are reunited in their supplied relative order.
    No exponent is fitted, no smoothing is used, and no probabilities are inferred.
    """
    pages: dict[str, list[tuple[int, ...]]] = {}
    pooled = []
    for record in records:
        pooled.extend(record.groups)
        pages.setdefault(record.page, []).extend(record.groups)
    return {
        "panel_id": "vocabulary-growth-v1",
        "order": "supplied_record_then_group_order",
        "metric_order": list(METRICS),
        "metric_rules": {name: "two_sided" for name in METRICS},
        "pooled": _measure(pooled),
        "page_reset": [
            {"page": page, "summary": _measure(groups)} for page, groups in pages.items()
        ],
    }


def validate_vocabulary_growth(panel: dict[str, Any]) -> None:
    """Check derived summaries and basic cross-scope event consistency."""
    if (
        panel["panel_id"] != "vocabulary-growth-v1"
        or panel["order"] != "supplied_record_then_group_order"
        or panel["metric_order"] != list(METRICS)
        or panel["metric_rules"] != {name: "two_sided" for name in METRICS}
    ):
        raise MeasurementError("vocabulary growth panel identity differs")
    summaries = [panel["pooled"]] + [entry["summary"] for entry in panel["page_reset"]]
    for summary in summaries:
        if summary != _summary(
            summary["group_count"], summary["discovery_positions"], summary["recurrence_gaps"]
        ):
            raise MeasurementError("vocabulary growth summaries do not replay from events")
    pages = [entry["page"] for entry in panel["page_reset"]]
    if (
        len(pages) != len(set(pages))
        or sum(summary["group_count"] for summary in summaries[1:]) != summaries[0]["group_count"]
        or any(summary["group_count"] == 0 for summary in summaries[1:])
        or any(summary["type_count"] > summaries[0]["type_count"] for summary in summaries[1:])
        or sum(summary["type_count"] for summary in summaries[1:]) < summaries[0]["type_count"]
    ):
        raise MeasurementError("vocabulary growth page scopes are inconsistent")
