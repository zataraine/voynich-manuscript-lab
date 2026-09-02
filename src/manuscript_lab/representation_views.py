"""Target-independent, reversible projections of observed transcription surfaces."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import orjson
import regex
import yaml
from jsonschema import Draft202012Validator

from manuscript_lab.ivtff import LocusRecord, SurfaceUnit, parse_surface
from manuscript_lab.provenance import repository_root, sha256_file

REGISTRY_PATH = Path("config/corpora/representation-views-v1.yaml")
SCHEMA_PATH = Path("schemas/representation-view-registry.schema.json")
EDITORIAL_KINDS = frozenset({"paragraph_start", "paragraph_end", "free_comment", "text_tag"})


@dataclass(frozen=True)
class ViewSpec:
    registry_sha256: str
    view_id: str
    source_layer: str
    alphabet_requirement: str
    glyph_unit: str
    alternative_policy: str
    ligature_policy: str
    certain_space_policy: str
    uncertain_space_policy: str
    editorial_policy: str
    role: str


@dataclass(frozen=True)
class RepresentationRegistry:
    path: Path
    sha256: str
    registry_id: str
    witness_registry: Path
    witness_policy: dict[str, Any]
    split_policy: dict[str, Any]
    views: tuple[ViewSpec, ...]
    learned_unit_policy: dict[str, Any]


class RepresentationError(ValueError):
    """A representation registry or projection violates its frozen contract."""


def load_representation_registry(
    path: Path | None = None, *, root: Path | None = None
) -> RepresentationRegistry:
    """Load the frozen view registry and reject duplicate or incoherent views."""
    project = (root or repository_root()).resolve()
    registry_path = path or project / REGISTRY_PATH
    if not registry_path.is_absolute():
        registry_path = project / registry_path
    value = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    schema = orjson.loads((project / SCHEMA_PATH).read_bytes())
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        rendered = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise RepresentationError(f"invalid representation registry: {rendered}")
    raw_views = value["views"]
    view_ids = [item["id"] for item in raw_views]
    if len(view_ids) != len(set(view_ids)):
        raise RepresentationError("representation view IDs must be unique")
    for item in raw_views:
        is_sta = item["source_layer"] == "sta1_comparison"
        sta_encoding = item["alphabet_requirement"] == "STA1" and item["glyph_unit"] == "sta1_pair"
        native_encoding = item["alphabet_requirement"] == "any" and item["glyph_unit"] in {
            "codepoint",
            "grapheme",
        }
        if (is_sta and not sta_encoding) or (not is_sta and not native_encoding):
            raise RepresentationError(
                f"view {item['id']} has an incoherent source/alphabet/unit combination"
            )
    witness_registry = project / value["witness_registry"]
    witness_value = yaml.safe_load(witness_registry.read_text(encoding="utf-8"))
    witnesses = {item["id"]: item for item in witness_value["witnesses"]}
    policy = value["witness_policy"]
    policy_sets = {
        key: set(policy[key])
        for key in ("required_primary", "sensitivity_only", "prohibited_as_independent")
    }
    named_witnesses = set().union(*policy_sets.values())
    unknown = named_witnesses - witnesses.keys()
    if unknown:
        raise RepresentationError(
            f"representation policy names unregistered witnesses: {sorted(unknown)}"
        )
    for left_name, left in policy_sets.items():
        for right_name, right in policy_sets.items():
            if left_name < right_name and left & right:
                raise RepresentationError(
                    f"witness policy roles overlap: {left_name}/{right_name}: "
                    f"{sorted(left & right)}"
                )
    invalid_primary = [
        witness_id
        for witness_id in policy["required_primary"]
        if witnesses[witness_id]["independence_role"]
        in {"related-derivative", "synthetic-derivative"}
    ]
    if invalid_primary:
        raise RepresentationError(
            f"derived witnesses cannot be required primary: {invalid_primary}"
        )
    learned = value["learned_unit_policy"]
    if learned["base_view"] not in view_ids:
        raise RepresentationError("learned-unit base_view is not a registered view")
    merge_counts = learned["merge_counts"]
    if merge_counts != sorted(set(merge_counts)):
        raise RepresentationError("learned-unit merge_counts must be unique and ascending")
    registry_sha256 = sha256_file(registry_path)
    views = tuple(
        ViewSpec(
            registry_sha256=registry_sha256,
            view_id=item["id"],
            source_layer=item["source_layer"],
            alphabet_requirement=item["alphabet_requirement"],
            glyph_unit=item["glyph_unit"],
            alternative_policy=item["alternative_policy"],
            ligature_policy=item["ligature_policy"],
            certain_space_policy=item["certain_space_policy"],
            uncertain_space_policy=item["uncertain_space_policy"],
            editorial_policy=item["editorial_policy"],
            role=item["role"],
        )
        for item in raw_views
    )
    return RepresentationRegistry(
        path=registry_path,
        sha256=registry_sha256,
        registry_id=value["registry_id"],
        witness_registry=witness_registry,
        witness_policy=policy,
        split_policy=value["split_policy"],
        views=views,
        learned_unit_policy=value["learned_unit_policy"],
    )


def _glyph_observations(
    surface: str,
    unit: SurfaceUnit,
    spec: ViewSpec,
    *,
    content_offset: int = 0,
) -> list[dict[str, Any]]:
    if spec.glyph_unit == "codepoint":
        pieces = [(piece, index, index + 1) for index, piece in enumerate(surface)]
    elif spec.glyph_unit == "grapheme":
        pieces = [
            (match.group(), match.start(), match.end()) for match in regex.finditer(r"\X", surface)
        ]
    elif spec.glyph_unit == "sta1_pair":
        if len(surface) % 2 or regex.fullmatch(r"(?:[A-Z][0-9a-z])+", surface) is None:
            raise RepresentationError(f"invalid STA1 run for atomic-pair view: {surface!r}")
        pieces = [
            (surface[index : index + 2], index, index + 2) for index in range(0, len(surface), 2)
        ]
    else:
        raise RepresentationError(f"unsupported glyph unit: {spec.glyph_unit}")
    return [
        {
            "kind": "observed_unit",
            "surface": piece,
            "source_span": [
                unit.start + content_offset + start,
                unit.start + content_offset + end,
            ],
            "source_kind": unit.kind,
        }
        for piece, start, end in pieces
    ]


def project_surface(
    surface: str, spec: ViewSpec, *, alphabet: str, witness_id: str
) -> dict[str, Any]:
    """Project one surface while retaining an exact raw inverse and source-span audit."""
    if spec.alphabet_requirement != "any" and alphabet != spec.alphabet_requirement:
        raise RepresentationError(
            f"view {spec.view_id} requires {spec.alphabet_requirement}, received {alphabet}"
        )
    observations: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for unit in parse_surface(surface):
        audit = {
            "kind": unit.kind,
            "raw": unit.raw,
            "source_span": [unit.start, unit.end],
        }
        if unit.kind in EDITORIAL_KINDS:
            excluded.append(audit)
            continue
        if unit.kind == "glyph_run":
            observations.extend(_glyph_observations(unit.raw, unit, spec))
            continue
        if unit.kind == "alternative_reading" and spec.alternative_policy == "first":
            observations.extend(
                _glyph_observations(unit.alternatives[0], unit, spec, content_offset=1)
            )
            excluded.append({**audit, "reason": "nonfirst_alternatives_retained_in_raw_inverse"})
            continue
        if unit.kind == "ligature" and spec.ligature_policy == "decompose":
            observations.extend(_glyph_observations(unit.raw[1:-1], unit, spec, content_offset=1))
            continue
        if unit.kind in {"certain_space", "uncertain_space"}:
            policy = (
                spec.certain_space_policy
                if unit.kind == "certain_space"
                else spec.uncertain_space_policy
            )
            if policy == "erase_with_audit":
                excluded.append({**audit, "reason": policy})
                continue
            observations.append(
                {
                    "kind": unit.kind,
                    "surface": unit.raw,
                    "source_span": [unit.start, unit.end],
                    "source_kind": unit.kind,
                }
            )
            continue
        observations.append(
            {
                "kind": unit.kind,
                "surface": unit.raw,
                "source_span": [unit.start, unit.end],
                "source_kind": unit.kind,
            }
        )
    derived = {
        "registry_sha256": spec.registry_sha256,
        "view_id": spec.view_id,
        "alphabet": alphabet,
        "witness_id": witness_id,
        "observations": observations,
        "excluded_with_audit": excluded,
    }
    encoded = orjson.dumps(derived, option=orjson.OPT_SORT_KEYS)
    return {
        **derived,
        "raw_surface": surface,
        "raw_surface_sha256": hashlib.sha256(surface.encode("utf-8")).hexdigest(),
        "projection_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def project_locus(
    locus: LocusRecord,
    spec: ViewSpec,
    *,
    alphabet: str,
    page_metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Project a locus while retaining its physical split and source identity."""
    projection = project_surface(
        locus.text,
        spec,
        alphabet=alphabet,
        witness_id=locus.witness_id,
    )
    projection["source"] = {
        "record_id": locus.record_id,
        "page": locus.page,
        "locus": locus.locus,
        "locator": locus.locator,
        "locus_type": locus.locus_type,
        "line_numbers": list(locus.line_numbers),
        "page_metadata": dict(sorted((page_metadata or {}).items())),
        "section": (page_metadata or {}).get("I"),
    }
    return projection


def summarize_projection_coverage(
    projections: list[dict[str, Any]], *, expected_pages: set[str] | None = None
) -> dict[str, Any]:
    """Report coverage and missingness for one isolated projection scope."""
    if not projections:
        raise RepresentationError("cannot summarize an empty projection set")
    scopes = {
        (
            projection["registry_sha256"],
            projection["view_id"],
            projection["alphabet"],
            projection["witness_id"],
        )
        for projection in projections
    }
    if len(scopes) != 1:
        raise RepresentationError("coverage must be reported separately by projection scope")
    if any("source" not in projection for projection in projections):
        raise RepresentationError("coverage requires locus projections with source identity")
    registry_sha256, view_id, alphabet, witness_id = next(iter(scopes))
    observed_pages = {projection["source"]["page"] for projection in projections}
    expected = set(expected_pages) if expected_pages is not None else observed_pages
    if not observed_pages <= expected:
        raise RepresentationError("observed pages fall outside the declared coverage universe")
    return {
        "scope": {
            "registry_sha256": registry_sha256,
            "view_id": view_id,
            "alphabet": alphabet,
            "witness_id": witness_id,
        },
        "locus_count": len(projections),
        "observed_page_count": len(observed_pages),
        "expected_page_count": len(expected),
        "missing_pages": sorted(expected - observed_pages),
        "observation_count": sum(len(item["observations"]) for item in projections),
        "excluded_count": sum(len(item["excluded_with_audit"]) for item in projections),
    }


def integerize_projections(projections: list[dict[str, Any]]) -> dict[str, Any]:
    """Assign deterministic integers without merging observation kinds or witnesses."""
    if not projections:
        raise RepresentationError("cannot integerize an empty projection set")
    scopes = {
        (
            projection["registry_sha256"],
            projection["view_id"],
            projection["alphabet"],
            projection["witness_id"],
        )
        for projection in projections
    }
    if len(scopes) != 1:
        raise RepresentationError("one symbol table cannot merge views, alphabets, or witnesses")
    registry_sha256, view_id, alphabet, witness_id = next(iter(scopes))
    keys = sorted(
        {
            (observation["kind"], observation["surface"])
            for projection in projections
            for observation in projection["observations"]
        }
    )
    lookup = {key: index for index, key in enumerate(keys)}
    return {
        "scope": {
            "registry_sha256": registry_sha256,
            "view_id": view_id,
            "alphabet": alphabet,
            "witness_id": witness_id,
        },
        "symbol_table": [
            {"id": index, "kind": kind, "surface": surface}
            for index, (kind, surface) in enumerate(keys)
        ],
        "sequences": [
            [lookup[(item["kind"], item["surface"])] for item in projection["observations"]]
            for projection in projections
        ],
    }


def verify_projection(projection: dict[str, Any], spec: ViewSpec) -> None:
    """Recompute a projection and prove its exact raw inverse and observation identity."""
    raw = projection["raw_surface"]
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != projection["raw_surface_sha256"]:
        raise RepresentationError("raw surface SHA-256 mismatch")
    rebuilt = project_surface(
        raw,
        spec,
        alphabet=projection["alphabet"],
        witness_id=projection["witness_id"],
    )
    if rebuilt["projection_sha256"] != projection["projection_sha256"]:
        raise RepresentationError("projection does not replay from its raw inverse")
    if rebuilt["observations"] != projection["observations"]:
        raise RepresentationError("projected observations differ on replay")
    if rebuilt["excluded_with_audit"] != projection["excluded_with_audit"]:
        raise RepresentationError("projection exclusion audit differs on replay")
