from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


def test_all_json_schemas_are_valid() -> None:
    root = Path(__file__).parents[1]
    schemas = list((root / "schemas").glob("*.schema.json"))
    assert schemas
    for path in schemas:
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_project_layout_has_governance_files() -> None:
    root = Path(__file__).parents[1]
    required = (
        "AGENTS.md",
        "INFRASTRUCTURE.md",
        "docs/DATA_CONTRACT.md",
        "docs/RESEARCH_PROTOCOL.md",
        "docs/CRYPTANALYSIS_PROTOCOL.md",
        "research/HYPOTHESES.md",
        "research/CIPHER_HYPOTHESES.md",
        "research/CLAIMS.md",
        "config/experiments/base.yaml",
    )
    assert all((root / relative).is_file() for relative in required)


def test_cipher_templates_match_schema() -> None:
    root = Path(__file__).parents[1]
    schema = json.loads((root / "schemas/cipher-hypothesis.schema.json").read_text())
    validator = Draft202012Validator(schema)
    templates = list((root / "config/ciphers").glob("*.yaml"))
    assert templates
    for path in templates:
        validator.validate(yaml.safe_load(path.read_text(encoding="utf-8")))
