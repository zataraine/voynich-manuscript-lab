"""Serializable control measurements over one verified representation scope."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import orjson
from jsonschema import Draft202012Validator

from manuscript_lab.measurement_battery import (
    MeasurementBattery,
    MeasurementError,
    adapt_locus_projections,
    measure_core,
    measure_finite_sample_profile,
    measure_training_heldout,
    measurement_support,
    restore_learned_merge_table,
    structural_nulls,
)
from manuscript_lab.provenance import repository_root
from manuscript_lab.representation_views import ViewSpec, verify_projection

SCHEMA_PATH = Path("schemas/measurement-record.schema.json")


def canonical_measurement_bytes(record: dict[str, Any]) -> bytes:
    """Validate and serialize a result without machine-dependent key ordering."""
    schema = orjson.loads((repository_root() / SCHEMA_PATH).read_bytes())
    # Normalize tuples to their JSON array representation before schema checking.
    encoded = orjson.dumps(record, option=orjson.OPT_SORT_KEYS)
    value = orjson.loads(encoded)
    errors = list(Draft202012Validator(schema).iter_errors(value))
    if errors:
        raise MeasurementError(f"invalid measurement record: {errors[0].message}")
    metric_order = value["metric_order"]
    measurements = value["measurements"]
    if (measurements["battery_id"], measurements["battery_sha256"]) != (
        value["battery_id"],
        value["battery_sha256"],
    ):
        raise MeasurementError("inconsistent measurement battery identity")
    vectors = [measurements["training"], measurements["heldout"]]
    vectors.extend(entry["metrics"] for entry in value["nulls"].values())
    for split in ("training", "heldout"):
        vectors.extend(entry["metrics"] for entry in value["finite_sample"][split])
    for vector in vectors:
        if set(vector) != set(metric_order) or any(
            not isinstance(number, (int, float))
            or isinstance(number, bool)
            or not math.isfinite(number)
            for number in vector.values()
        ):
            raise MeasurementError("metric vector is incomplete or non-finite")
    for entry in measurements["learned_units"].values():
        table = restore_learned_merge_table(entry["merge_table"])
        if hashlib.sha256(orjson.dumps(table)).hexdigest() != entry["merge_table_sha256"]:
            raise MeasurementError("learned-unit table SHA-256 mismatch")
    return encoded


def build_control_measurement_record(
    projections: Sequence[dict[str, Any]],
    *,
    spec: ViewSpec,
    training_pages: Sequence[str],
    heldout_pages: Sequence[str],
    battery: MeasurementBattery,
    seed: int,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    """Bundle controls, splits, nulls and support; make no calibration decision.

    Source-kind declarations are supplied by the caller, not an access barrier.
    Phase 6 must independently enforce sealed target access. This module opens
    no corpus files and accepts only already supplied projections.
    """
    if provenance.get("source_kind") not in {"synthetic", "external-control"}:
        raise MeasurementError("measurement development requires declared control sources")
    train, heldout = set(training_pages), set(heldout_pages)
    if not train or not heldout or train & heldout:
        raise MeasurementError(
            "training and heldout page assignments must be nonempty and disjoint"
        )
    if len(train) != len(training_pages) or len(heldout) != len(heldout_pages):
        raise MeasurementError("duplicate page assignments")
    for projection in projections:
        if (projection["registry_sha256"], projection["view_id"]) != (
            spec.registry_sha256,
            spec.view_id,
        ):
            raise MeasurementError("projection scope differs from supplied view specification")
        verify_projection(projection, spec)
    adapted = adapt_locus_projections(projections)
    ids = [projection["source"]["record_id"] for projection in projections]
    if len(ids) != len(set(ids)):
        raise MeasurementError("duplicate source record IDs")
    source_pages = {projection["source"]["page"] for projection in projections}
    if not source_pages <= train | heldout:
        raise MeasurementError("source pages fall outside declared split assignments")
    records = adapted["records"]
    training = tuple(record for record in records if record.page in train)
    evaluation = tuple(record for record in records if record.page in heldout)
    measurements = measure_training_heldout(training, evaluation, battery=battery, seed=seed)
    null_records = structural_nulls(evaluation, seed=seed)
    if set(null_records) != set(battery.config["null_families"]):
        raise MeasurementError("null implementations differ from battery config")
    result = {
        "schema_version": "1.0",
        "record_type": "control-measurement-v1",
        "provenance": provenance,
        "seed": seed,
        "battery_id": battery.battery_id,
        "battery_sha256": battery.sha256,
        "metric_order": list(battery.config["metric_rules"]),
        "scope": adapted["scope"],
        "input_projections_sha256": hashlib.sha256(
            orjson.dumps(projections, option=orjson.OPT_SORT_KEYS)
        ).hexdigest(),
        "symbol_table": adapted["symbol_table"],
        "coverage": adapted["coverage"],
        "record_provenance": adapted["record_provenance"],
        "split": {
            "minimum_group": "physical_page",
            "training_pages": sorted(train),
            "heldout_pages": sorted(heldout),
            "training_record_ids": [record.record_id for record in training],
            "heldout_record_ids": [record.record_id for record in evaluation],
            "training_pages_without_usable_records": sorted(train - {r.page for r in training}),
            "heldout_pages_without_usable_records": sorted(heldout - {r.page for r in evaluation}),
        },
        "measurements": measurements,
        "finite_sample": {
            "training": measure_finite_sample_profile(training, battery=battery, seed=seed),
            "heldout": measure_finite_sample_profile(evaluation, battery=battery, seed=seed),
        },
        "nulls": {
            name: {
                "metrics": measure_core(null_records[name], battery=battery, seed=seed),
                "support": measurement_support(null_records[name], battery=battery),
            }
            for name in battery.config["null_families"]
        },
        "decision": "not_calibrated",
    }
    canonical_measurement_bytes(result)
    return result
