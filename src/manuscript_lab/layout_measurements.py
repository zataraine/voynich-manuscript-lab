"""Explicit paragraph/session diagnostics, without inferred layout or chronology."""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from collections.abc import Sequence
from itertools import pairwise
from typing import Any

from manuscript_lab.measurement_battery import (
    MeasurementBattery,
    MeasurementError,
    MeasurementRecord,
    _js_divergence,
    _rank_correlation,
    measure_page_compression,
)

PANEL_ID = "layout-measurements-v1"
METRICS = (
    "within_paragraph_position_length_spearman",
    "session_unigram_drift_js",
    "session_position_length_spearman",
    "pagewise_compression_shuffle_gain",
)


def measure_layout(
    records: Sequence[MeasurementRecord], *, battery: MeasurementBattery, seed: int
) -> dict[str, Any]:
    """Measure supplied annotations and expose their missingness/support.

    Paragraph correlations use record-mean group widths, then average equally
    across eligible page-scoped paragraphs. Sessions aggregate by supplied ID
    and are ordered by explicit index; neither page IDs nor input order supply
    a chronology. Caller must isolate documents/contributors before this call.
    """
    if not records:
        raise MeasurementError("layout diagnostics require records")
    paragraphs: dict[tuple[str, str], list[MeasurementRecord]] = defaultdict(list)
    sessions: dict[str, list[MeasurementRecord]] = defaultdict(list)
    session_order: dict[str, int] = {}
    order_ids: dict[int, str] = {}
    for record in records:
        if record.paragraph_id is not None:
            paragraphs[(record.page, record.paragraph_id)].append(record)
        if record.session_id is not None:
            index = record.session_index
            assert index is not None
            if record.session_id in session_order and session_order[record.session_id] != index:
                raise MeasurementError("one session has conflicting chronological indices")
            if index in order_ids and order_ids[index] != record.session_id:
                raise MeasurementError("distinct sessions share a chronological index")
            session_order[record.session_id] = index
            order_ids[index] = record.session_id
            sessions[record.session_id].append(record)
    correlations = []
    ineligible = []
    for (page, paragraph_id), members in paragraphs.items():
        positions = [record.paragraph_line_index for record in members]
        if len(positions) != len(set(positions)):
            raise MeasurementError("duplicate line positions within an annotated paragraph")
        widths = [statistics.mean(map(len, record.groups)) for record in members]
        if len(members) < 3 or len(set(widths)) < 2:
            ineligible.append({"page": page, "paragraph_id": paragraph_id})
            continue
        correlations.append(_rank_correlation(widths, positions))
    ordered = sorted(sessions, key=session_order.__getitem__)
    counts = [
        Counter(unit for record in sessions[name] for group in record.groups for unit in group)
        for name in ordered
    ]
    session_widths = [
        statistics.mean(len(group) for record in sessions[name] for group in record.groups)
        for name in ordered
    ]
    undefined = {}
    if not correlations:
        undefined[METRICS[0]] = "no_paragraph_with_three_positions_and_variable_lengths"
    if len(ordered) < 2:
        undefined[METRICS[1]] = "fewer_than_two_annotated_sessions"
    if len(ordered) < 3 or len(set(session_widths)) < 2:
        undefined[METRICS[2]] = "insufficient_sessions_or_constant_lengths"
    metrics = {
        METRICS[0]: statistics.mean(correlations) if correlations else 0.0,
        METRICS[1]: statistics.mean(_js_divergence(a, b) for a, b in pairwise(counts))
        if len(counts) > 1
        else 0.0,
        METRICS[2]: _rank_correlation(session_widths, [session_order[name] for name in ordered]),
        METRICS[3]: measure_page_compression(records, battery=battery, seed=seed),
    }
    return {
        "panel_id": PANEL_ID,
        "metric_order": list(METRICS),
        "metric_rules": dict.fromkeys(METRICS, "two_sided"),
        "metrics": metrics,
        "support": {
            "record_count": len(records),
            "records_missing_paragraph": sum(r.paragraph_id is None for r in records),
            "records_missing_session": sum(r.session_id is None for r in records),
            "eligible_paragraph_count": len(correlations),
            "ineligible_paragraphs": ineligible,
            "ordered_session_ids": ordered,
            "undefined_metrics": undefined,
        },
    }
