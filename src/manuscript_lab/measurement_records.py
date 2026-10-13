"""Serializable control measurements over one verified representation scope."""

from __future__ import annotations

import hashlib
import math
import statistics
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import orjson
from jsonschema import Draft202012Validator

from manuscript_lab.layout_measurements import METRICS as LAYOUT_METRICS
from manuscript_lab.layout_measurements import measure_layout
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
from manuscript_lab.sampling_diagnostics import measure_null_ensemble
from manuscript_lab.vocabulary_growth import measure_vocabulary_growth, validate_vocabulary_growth

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
        for panel in entry.get("uncertainty", {}).values():
            support = panel["support"]
            undefined = {}
            if not support["learned_unit_count"]:
                undefined["unit_entropy_bits"] = "no_learned_units"
            if not support["transition_count"]:
                undefined["conditional_unit_entropy_order1_bits"] = "no_within_record_transitions"
            if (
                support["undefined_metrics"] != undefined
                or support["learned_type_count"] > support["learned_unit_count"]
                or support["transition_count"] > support["learned_unit_count"]
                or support["base_unit_count"] < support["learned_unit_count"]
                or any(panel["metrics"][name] != 0 for name in undefined)
            ):
                raise MeasurementError("learned uncertainty support is inconsistent")
    if "layout" in value:
        panels = [value["layout"]["training"], value["layout"]["heldout"]]
        panels.extend(value["layout"]["nulls"].values())
        for panel in panels:
            if set(panel["metrics"]) != set(LAYOUT_METRICS) or any(
                not isinstance(number, (int, float)) or not math.isfinite(number)
                for number in panel["metrics"].values()
            ):
                raise MeasurementError("layout vector is incomplete or non-finite")
    if "null_ensemble" in value:
        ensemble = value["null_ensemble"]
        if (
            ensemble["battery_id"] != value["battery_id"]
            or ensemble["battery_sha256"] != value["battery_sha256"]
            or ensemble["base_seed"] != value["seed"]
            or ensemble["metric_order"] != metric_order
            or ensemble["observed"] != measurements["heldout"]
            or ensemble["observed_support"] != measurements["heldout_support"]
            or len(ensemble["replicate_seeds"]) != ensemble["replicates"]
            or set(ensemble["families"]) != set(value["nulls"])
        ):
            raise MeasurementError("null ensemble does not match result identity or dimensions")
        for summaries in ensemble["families"].values():
            if set(summaries) != set(metric_order):
                raise MeasurementError("null ensemble metric coverage differs from result")
            for name, summary in summaries.items():
                samples = summary["samples"]
                defined = [sample for sample in samples if sample is not None]
                mean = statistics.mean(defined) if defined else None
                sd = statistics.stdev(defined) if len(defined) > 1 else None
                contrast = (
                    ensemble["observed"][name] - mean
                    if (
                        mean is not None
                        and name not in ensemble["observed_support"]["undefined_metrics"]
                    )
                    else None
                )
                if (
                    len(samples) != ensemble["replicates"]
                    or len(defined) != summary["defined_replicates"]
                    or (mean, sd, contrast)
                    != (
                        summary["null_mean"],
                        summary["null_sample_sd"],
                        summary["observed_minus_null_mean"],
                    )
                ):
                    raise MeasurementError("null ensemble summaries do not replay from samples")
    if "vocabulary_growth" in value:
        growth = value["vocabulary_growth"]
        contexts = [
            (growth[split], measurements[f"{split}_support"], measurements[split])
            for split in ("training", "heldout")
        ]
        contexts.extend(
            (panel, value["nulls"][name]["support"], value["nulls"][name]["metrics"])
            for name, panel in growth["nulls"].items()
        )
        for panel, support, metrics in contexts:
            validate_vocabulary_growth(panel)
            pooled = panel["pooled"]
            if (
                pooled["group_count"] != support["group_count"]
                or len(panel["page_reset"]) != support["page_count"]
                or len(pooled["recurrence_gaps"]) != support["recurrence_gap_count"]
                or pooled["metrics"]["median_recurrence_distance"]
                != metrics["median_recurrence_distance"]
            ):
                raise MeasurementError("vocabulary growth differs from core measurement scope")
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
    null_replicates: int | None = None,
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
        "layout": {
            "training": measure_layout(training, battery=battery, seed=seed),
            "heldout": measure_layout(evaluation, battery=battery, seed=seed),
            "nulls": {
                name: measure_layout(null_records[name], battery=battery, seed=seed)
                for name in battery.config["null_families"]
            },
        },
        "vocabulary_growth": {
            "training": measure_vocabulary_growth(training),
            "heldout": measure_vocabulary_growth(evaluation),
            "nulls": {
                name: measure_vocabulary_growth(null_records[name])
                for name in battery.config["null_families"]
            },
        },
        "decision": "not_calibrated",
    }
    if null_replicates is not None:
        result["null_ensemble"] = measure_null_ensemble(
            evaluation, battery=battery, seed=seed, replicates=null_replicates
        )
    canonical_measurement_bytes(result)
    return result
