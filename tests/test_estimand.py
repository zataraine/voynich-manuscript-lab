from __future__ import annotations

from pathlib import Path

import pytest

from manuscript_lab.estimand import (
    EstimandError,
    build_interpretation_boundary,
    load_estimand,
)


def _scope() -> dict[str, str]:
    return {
        "implementation_id": "published-mechanism-v1",
        "parameter_domain_id": "domain-v1",
        "representation_registry_id": "views-v1",
        "measurement_battery_id": "battery-v1",
        "calibration_bundle_id": "bundle-v1",
    }


def test_frozen_estimand_loads_and_is_machine_addressable() -> None:
    estimand = load_estimand()
    assert estimand["estimand_id"] == "mechanism-compatibility-v1"
    assert estimand["target_access"]["applications_per_frozen_bundle"] == 1


@pytest.mark.parametrize("status", ["compatible", "incompatible", "indeterminate"])
def test_interpretation_boundary_refuses_posterior_and_semantic_claims(status: str) -> None:
    boundary = build_interpretation_boundary(status, _scope())
    assert boundary["status"] == status
    assert boundary["posterior_probability"] is None
    assert boundary["semantic_label"] is None
    assert boundary["historical_identity"] is None
    assert not boundary["family_wide_rejection"]


def test_interpretation_boundary_requires_exact_frozen_scope() -> None:
    scope = _scope()
    del scope["parameter_domain_id"]
    with pytest.raises(EstimandError, match="missing"):
        build_interpretation_boundary("compatible", scope)


def test_estimand_rejects_schema_drift(tmp_path: Path) -> None:
    (tmp_path / "config/research").mkdir(parents=True)
    (tmp_path / "schemas").mkdir()
    project = Path(__file__).parents[1]
    (tmp_path / "schemas/mechanism-compatibility-estimand.schema.json").write_bytes(
        (project / "schemas/mechanism-compatibility-estimand.schema.json").read_bytes()
    )
    (tmp_path / "config/research/mechanism-compatibility-v1.yaml").write_text(
        'schema_version: "1.0"\nestimand_id: wrong\n', encoding="utf-8"
    )
    with pytest.raises(EstimandError, match="invalid estimand"):
        load_estimand(root=tmp_path)
