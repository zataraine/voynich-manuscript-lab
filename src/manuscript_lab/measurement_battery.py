"""Frozen, target-independent measurements for reversible numeric records."""

from __future__ import annotations

import hashlib
import math
import random
import statistics
import zlib
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import orjson
import yaml
from jsonschema import Draft202012Validator
from scipy.stats import rankdata

from manuscript_lab.provenance import repository_root, sha256_file

BATTERY_PATH = Path("config/research/measurement-battery-v1.yaml")
SCHEMA_PATH = Path("schemas/measurement-battery.schema.json")
Unit = int | tuple["Unit", "Unit"]


class MeasurementError(ValueError):
    """A record or battery configuration violates the frozen measurement contract."""


@dataclass(frozen=True)
class MeasurementRecord:
    """One reversible, already-numbered source record with physical context."""

    record_id: str
    page: str
    section: str | None
    line_index: int
    groups: tuple[tuple[int, ...], ...]
    boundaries: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.groups or any(not group for group in self.groups):
            raise MeasurementError("measurement records require nonempty groups")
        if len(self.boundaries) != len(self.groups) - 1:
            raise MeasurementError("boundary count must equal group count minus one")


@dataclass(frozen=True)
class MeasurementBattery:
    path: Path
    sha256: str
    battery_id: str
    config: dict[str, Any]


def load_measurement_battery(
    path: Path | None = None, *, root: Path | None = None
) -> MeasurementBattery:
    """Load the frozen target-independent battery contract."""
    project = (root or repository_root()).resolve()
    battery_path = path or project / BATTERY_PATH
    if not battery_path.is_absolute():
        battery_path = project / battery_path
    value = yaml.safe_load(battery_path.read_text(encoding="utf-8"))
    schema = orjson.loads((project / SCHEMA_PATH).read_bytes())
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.absolute_path)
    )
    if errors:
        rendered = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise MeasurementError(f"invalid measurement battery: {rendered}")
    merge_counts = value["learned_unit_policy"]["merge_counts"]
    if merge_counts != sorted(merge_counts):
        raise MeasurementError("learned-unit merge counts must be ascending")
    return MeasurementBattery(
        path=battery_path,
        sha256=sha256_file(battery_path),
        battery_id=value["battery_id"],
        config=value,
    )


def _entropy(values: Iterable[Any]) -> float:
    counts = Counter(values)
    total = sum(counts.values())
    if not total:
        return 0.0
    return -sum(count / total * math.log2(count / total) for count in counts.values())


def _conditional_entropy(groups: Sequence[tuple[int, ...]]) -> float:
    contexts: dict[int, Counter[int]] = defaultdict(Counter)
    total = 0
    for group in groups:
        for left, right in pairwise(group):
            contexts[left][right] += 1
            total += 1
    if not total:
        return 0.0
    return sum(
        sum(outcomes.values()) / total * _entropy(outcomes.elements())
        for outcomes in contexts.values()
    )


def _mutual_information(pairs: Iterable[tuple[Any, Any]]) -> float:
    values = tuple(pairs)
    if not values:
        return 0.0
    joint = Counter(values)
    left = Counter(first for first, _ in values)
    right = Counter(second for _, second in values)
    total = len(values)
    return sum(
        count / total * math.log2(count * total / (left[first] * right[second]))
        for (first, second), count in joint.items()
    )


def _canonical_group_bytes(groups: Sequence[tuple[int, ...]]) -> bytes:
    codes: dict[tuple[int, ...], int] = {}
    values: list[int] = []
    for group in groups:
        codes.setdefault(group, len(codes))
        values.append(codes[group])
    return np.asarray(values, dtype="<u4").tobytes()


def _compression_gain(groups: Sequence[tuple[int, ...]], *, seed: int, replicates: int) -> float:
    observed = len(zlib.compress(_canonical_group_bytes(groups), 9))
    rng = random.Random(seed)
    shuffled: list[int] = []
    working = list(groups)
    for _ in range(replicates):
        rng.shuffle(working)
        shuffled.append(len(zlib.compress(_canonical_group_bytes(working), 9)))
    return float(statistics.mean(shuffled) - observed) / max(1, len(groups))


def _rank_correlation(values: Sequence[float], positions: Sequence[float]) -> float:
    if len(values) < 3 or len(set(values)) < 2:
        return 0.0
    left = rankdata(np.asarray(values, dtype=float), method="average")
    right = rankdata(np.asarray(positions, dtype=float), method="average")
    result = float(np.corrcoef(left, right)[0, 1])
    return result if math.isfinite(result) else 0.0


def _js_divergence(left: Counter[int], right: Counter[int]) -> float:
    left_total, right_total = sum(left.values()), sum(right.values())
    if not left_total or not right_total:
        return 0.0
    result = 0.0
    for symbol in left.keys() | right.keys():
        p, q = left[symbol] / left_total, right[symbol] / right_total
        midpoint = (p + q) / 2
        if p:
            result += p / 2 * math.log2(p / midpoint)
        if q:
            result += q / 2 * math.log2(q / midpoint)
    return result


def _mean_partition_drift(records: Sequence[MeasurementRecord], key: str) -> float:
    partitions: dict[str, Counter[int]] = defaultdict(Counter)
    for record in records:
        label = record.page if key == "page" else record.section
        if label is not None:
            partitions[str(label)].update(symbol for group in record.groups for symbol in group)
    values = [partitions[label] for label in sorted(partitions)]
    return (
        statistics.mean(_js_divergence(left, right) for left, right in pairwise(values))
        if len(values) > 1
        else 0.0
    )


def _median_recurrence(groups: Sequence[tuple[int, ...]]) -> float:
    positions: dict[tuple[int, ...], list[int]] = defaultdict(list)
    for index, group in enumerate(groups):
        positions[group].append(index)
    gaps = [right - left for indexes in positions.values() for left, right in pairwise(indexes)]
    return float(statistics.median(gaps)) if gaps else 0.0


def _flatten(records: Sequence[MeasurementRecord]) -> tuple[tuple[int, ...], ...]:
    return tuple(group for record in records for group in record.groups)


def measure_core(
    records: Sequence[MeasurementRecord], *, battery: MeasurementBattery, seed: int
) -> dict[str, float]:
    """Measure one view/witness scope without learned-unit fitting or target logic."""
    if len(records) < battery.config["minimum_records"]:
        raise MeasurementError("insufficient records for frozen measurement battery")
    groups = _flatten(records)
    units = tuple(symbol for group in groups for symbol in group)
    counts = Counter(groups)
    group_pairs = list(pairwise(groups))
    boundary_pairs = [
        (boundary, int(left == right))
        for record in records
        for left, boundary, right in zip(
            record.groups[:-1], record.boundaries, record.groups[1:], strict=True
        )
    ]
    line_lengths = [len(group) for record in records for group in record.groups]
    line_positions = [record.line_index for record in records for _ in record.groups]
    context_pairs = [
        (index // battery.config["context_block_size"], group) for index, group in enumerate(groups)
    ]
    result = {
        "unit_entropy_bits": _entropy(units),
        "conditional_unit_entropy_order1_bits": _conditional_entropy(groups),
        "group_type_token_ratio": len(counts) / len(groups),
        "singleton_type_ratio": sum(count == 1 for count in counts.values()) / max(1, len(counts)),
        "median_recurrence_distance": _median_recurrence(groups),
        "adjacent_group_identity_rate": sum(left == right for left, right in group_pairs)
        / max(1, len(group_pairs)),
        "cross_separator_edge_mi_bits": _mutual_information(boundary_pairs),
        "line_position_length_spearman": _rank_correlation(line_lengths, line_positions),
        "page_unigram_drift_js": _mean_partition_drift(records, "page"),
        "section_unigram_drift_js": _mean_partition_drift(records, "section"),
        "contextual_block_mi_bits": _mutual_information(context_pairs),
        "compression_shuffle_gain": _compression_gain(
            groups,
            seed=seed,
            replicates=battery.config["compression_shuffle_replicates"],
        ),
    }
    if set(result) != set(battery.config["metric_rules"]):
        raise MeasurementError("implemented metrics differ from frozen battery config")
    if not all(math.isfinite(value) for value in result.values()):
        raise MeasurementError("measurement battery produced a non-finite value")
    return {name: float(result[name]) for name in battery.config["metric_rules"]}


def _replace_pairs(sequence: Sequence[Unit], pair: tuple[Unit, Unit]) -> list[Unit]:
    result: list[Unit] = []
    index = 0
    while index < len(sequence):
        if index + 1 < len(sequence) and (sequence[index], sequence[index + 1]) == pair:
            result.append(pair)
            index += 2
        else:
            result.append(sequence[index])
            index += 1
    return result


def fit_learned_units(
    training_records: Sequence[MeasurementRecord], *, merge_count: int
) -> tuple[tuple[Unit, Unit], ...]:
    """Fit a deterministic pair-merge table on training records only."""
    sequences: list[list[Unit]] = [
        [symbol for group in record.groups for symbol in group] for record in training_records
    ]
    merges: list[tuple[Unit, Unit]] = []
    for _ in range(merge_count):
        counts = Counter(pair for sequence in sequences for pair in pairwise(sequence))
        if not counts:
            break
        best = min(counts, key=lambda pair: (-counts[pair], repr(pair)))
        merges.append(best)
        sequences = [_replace_pairs(sequence, best) for sequence in sequences]
    return tuple(merges)


def _unit_width(unit: Unit) -> int:
    return 1 if isinstance(unit, int) else _unit_width(unit[0]) + _unit_width(unit[1])


def measure_learned_units(
    heldout_records: Sequence[MeasurementRecord], *, merges: Sequence[tuple[Unit, Unit]]
) -> dict[str, float]:
    """Apply a frozen learned-unit table to held-out records without refitting."""
    sequences: list[list[Unit]] = [
        [symbol for group in record.groups for symbol in group] for record in heldout_records
    ]
    raw_count = sum(len(sequence) for sequence in sequences)
    for pair in merges:
        sequences = [_replace_pairs(sequence, pair) for sequence in sequences]
    units = [unit for sequence in sequences for unit in sequence]
    return {
        "unit_count_ratio": len(units) / max(1, raw_count),
        "mean_unit_width": statistics.mean(_unit_width(unit) for unit in units) if units else 0.0,
    }


def measure_training_heldout(
    training_records: Sequence[MeasurementRecord],
    heldout_records: Sequence[MeasurementRecord],
    *,
    battery: MeasurementBattery,
    seed: int,
) -> dict[str, Any]:
    """Produce core metrics and held-out learned-unit diagnostics with no refitting."""
    learned = {}
    for merge_count in battery.config["learned_unit_policy"]["merge_counts"]:
        merges = fit_learned_units(training_records, merge_count=merge_count)
        learned[str(merge_count)] = {
            "merge_table_sha256": hashlib.sha256(repr(merges).encode()).hexdigest(),
            "trained_merge_count": len(merges),
            "heldout": measure_learned_units(heldout_records, merges=merges),
        }
    return {
        "battery_id": battery.battery_id,
        "battery_sha256": battery.sha256,
        "training": measure_core(training_records, battery=battery, seed=seed),
        "heldout": measure_core(heldout_records, battery=battery, seed=seed),
        "learned_units": learned,
    }


def structural_nulls(
    records: Sequence[MeasurementRecord], *, seed: int
) -> dict[str, tuple[MeasurementRecord, ...]]:
    """Return deterministic order and within-group structural diagnostic nulls."""
    rng = random.Random(seed)
    order = []
    within = []
    for record in records:
        shuffled_groups = list(record.groups)
        rng.shuffle(shuffled_groups)
        order.append(replace(record, groups=tuple(shuffled_groups)))
        unit_groups = []
        for group in record.groups:
            shuffled = list(group)
            rng.shuffle(shuffled)
            unit_groups.append(tuple(shuffled))
        within.append(replace(record, groups=tuple(unit_groups)))
    return {"group_order_shuffle": tuple(order), "within_group_unit_shuffle": tuple(within)}
