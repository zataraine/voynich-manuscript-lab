"""Machine-enforced interpretation boundary for mechanism comparisons."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import orjson
import yaml
from jsonschema import Draft202012Validator

from manuscript_lab.provenance import repository_root, sha256_file

ESTIMAND_PATH = Path("config/research/mechanism-compatibility-v1.yaml")
ESTIMAND_SCHEMA_PATH = Path("schemas/mechanism-compatibility-estimand.schema.json")

STATUS_CLAIMS = {
    "compatible": (
        "The named implementation over its frozen parameter domain was not rejected by "
        "the calibrated battery; truth, uniqueness, meaning, and historical identity "
        "are not implied."
    ),
    "incompatible": (
        "The named implementation over its frozen tested parameter domain was rejected; "
        "untested implementations and broader mechanism families remain open."
    ),
    "indeterminate": (
        "Calibration, power, coverage, or robustness was insufficient; no manuscript "
        "mechanism interpretation is permitted."
    ),
}


class EstimandError(ValueError):
    """An estimand or interpretation boundary violates its contract."""


def load_estimand(*, root: Path | None = None) -> dict[str, Any]:
    """Load and validate the frozen mechanism-compatibility estimand."""
    project = (root or repository_root()).resolve()
    path = project / ESTIMAND_PATH
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EstimandError("estimand root must be a mapping")
    schema = orjson.loads((project / ESTIMAND_SCHEMA_PATH).read_bytes())
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        rendered = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise EstimandError(f"invalid estimand: {rendered}")
    return value


def build_interpretation_boundary(
    status: str,
    scope: Mapping[str, str],
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Build the only permitted conclusion block for a future target result."""
    project = (root or repository_root()).resolve()
    estimand = load_estimand(root=project)
    if status not in estimand["allowed_statuses"]:
        raise EstimandError(f"unsupported compatibility status: {status}")
    required = list(estimand["required_scope_fields"])
    missing = [field for field in required if not scope.get(field)]
    extras = sorted(set(scope) - set(required))
    if missing or extras:
        raise EstimandError(f"invalid scope fields; missing={missing}, extras={extras}")
    return {
        "estimand_id": estimand["estimand_id"],
        "estimand_sha256": sha256_file(project / ESTIMAND_PATH),
        "status": status,
        "scope": {field: str(scope[field]) for field in required},
        "claim": STATUS_CLAIMS[status],
        "posterior_probability": None,
        "semantic_label": None,
        "historical_identity": None,
        "family_wide_rejection": False,
    }
