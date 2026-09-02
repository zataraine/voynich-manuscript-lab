from __future__ import annotations

from copy import deepcopy

import pytest

from manuscript_lab.ivtff import LocusRecord, parse_surface
from manuscript_lab.representation_views import (
    RepresentationError,
    integerize_projections,
    load_representation_registry,
    project_locus,
    project_surface,
    summarize_projection_coverage,
    verify_projection,
)


def _view(view_id: str):
    registry = load_representation_registry()
    return next(view for view in registry.views if view.view_id == view_id)


def test_registry_freezes_witness_independence_and_split_policy() -> None:
    registry = load_representation_registry()
    assert registry.registry_id == "representation-views-v1"
    assert registry.witness_policy["merge_or_vote"] == "forbidden"
    assert registry.witness_policy["required_primary"] == [
        "CD2a",
        "FG2a",
        "GC2a",
        "IT2a",
        "ZL3b",
    ]
    assert registry.split_policy == {
        "minimum_group": "physical_page",
        "shared_across_views": True,
    }


def test_sta_projection_preserves_structural_uncertainty_and_roundtrips() -> None:
    spec = _view("sta1-atomic-structural")
    projection = project_surface(
        "<%>A1B2,C3.[D4:E5]{F6}???",
        spec,
        alphabet="STA1",
        witness_id="synthetic-a",
    )
    assert [(item["kind"], item["surface"]) for item in projection["observations"]] == [
        ("observed_unit", "A1"),
        ("observed_unit", "B2"),
        ("uncertain_space", ","),
        ("observed_unit", "C3"),
        ("certain_space", "."),
        ("alternative_reading", "[D4:E5]"),
        ("ligature", "{F6}"),
        ("unreadable_unknown_count", "???"),
    ]
    assert projection["excluded_with_audit"][0]["kind"] == "paragraph_start"
    assert projection["registry_sha256"] == spec.registry_sha256
    verify_projection(projection, spec)


def test_space_erasure_and_first_alternative_are_audited_not_silent() -> None:
    erased = project_surface(
        "A1,B2.C3",
        _view("sta1-atomic-space-erased"),
        alphabet="STA1",
        witness_id="synthetic-a",
    )
    assert [item["surface"] for item in erased["observations"]] == ["A1", "B2", "C3"]
    assert [item["kind"] for item in erased["excluded_with_audit"]] == [
        "uncertain_space",
        "certain_space",
    ]
    first = project_surface(
        "A1[D4:E5]B2",
        _view("sta1-atomic-first-alternative"),
        alphabet="STA1",
        witness_id="synthetic-a",
    )
    assert [item["surface"] for item in first["observations"]] == ["A1", "D4", "B2"]
    assert first["excluded_with_audit"][0]["reason"] == (
        "nonfirst_alternatives_retained_in_raw_inverse"
    )
    decomposed = project_surface(
        "A1{B2C3}D4",
        _view("sta1-atomic-ligature-decomposed"),
        alphabet="STA1",
        witness_id="synthetic-a",
    )
    assert [item["surface"] for item in decomposed["observations"]] == [
        "A1",
        "B2",
        "C3",
        "D4",
    ]
    assert [item["source_span"] for item in decomposed["observations"]] == [
        [0, 2],
        [3, 5],
        [5, 7],
        [8, 10],
    ]


def test_integerization_is_deterministic_and_kind_sensitive() -> None:
    spec = _view("native-codepoint-structural")
    left = project_surface("a.b", spec, alphabet="Eva-", witness_id="synthetic-a")
    right = project_surface("b,a", spec, alphabet="Eva-", witness_id="synthetic-a")
    first = integerize_projections([left, right])
    second = integerize_projections([left, right])
    assert first == second
    table = {(item["kind"], item["surface"]) for item in first["symbol_table"]}
    assert ("certain_space", ".") in table
    assert ("uncertain_space", ",") in table


def test_integerization_refuses_cross_witness_tables() -> None:
    spec = _view("native-codepoint-structural")
    left = project_surface("a.b", spec, alphabet="Eva-", witness_id="synthetic-a")
    right = project_surface("a.b", spec, alphabet="Eva-", witness_id="synthetic-b")
    with pytest.raises(RepresentationError, match="cannot merge"):
        integerize_projections([left, right])


def test_locus_projection_retains_physical_split_identity() -> None:
    text = "a.b"
    locus = LocusRecord(
        witness_id="synthetic-a",
        locus="f1r.1",
        page="f1r",
        number=1,
        locator="P",
        relative_locator="0",
        locus_type="L0",
        transcriber=None,
        text=text,
        units=parse_surface(text),
        line_numbers=(12, 13),
        raw_lines=("first", "second"),
    )
    projection = project_locus(
        locus,
        _view("native-codepoint-structural"),
        alphabet="Eva-",
        page_metadata={"I": "H", "L": "A"},
    )
    assert projection["witness_id"] == "synthetic-a"
    assert projection["source"] == {
        "record_id": "synthetic-a:locus:f1r.1",
        "page": "f1r",
        "locus": "f1r.1",
        "locator": "P",
        "locus_type": "L0",
        "line_numbers": [12, 13],
        "page_metadata": {"I": "H", "L": "A"},
        "section": "H",
    }
    coverage = summarize_projection_coverage([projection], expected_pages={"f1r", "f1v"})
    assert coverage["missing_pages"] == ["f1v"]
    assert coverage["scope"]["witness_id"] == "synthetic-a"


def test_projection_refuses_wrong_alphabet_and_detects_tampering() -> None:
    spec = _view("sta1-atomic-structural")
    with pytest.raises(RepresentationError, match="requires STA1"):
        project_surface("ab", spec, alphabet="Eva-", witness_id="synthetic-a")
    projection = project_surface("A1B2", spec, alphabet="STA1", witness_id="synthetic-a")
    tampered = deepcopy(projection)
    tampered["observations"][0]["surface"] = "Z9"
    with pytest.raises(RepresentationError, match="differ on replay"):
        verify_projection(tampered, spec)
