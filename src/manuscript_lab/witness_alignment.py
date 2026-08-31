"""Lineage-aware, lossless alignment of IVTFF 2 witness loci."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from functools import cache
from itertools import combinations
from pathlib import Path
from typing import Any

import orjson
import yaml
from rapidfuzz.distance import Levenshtein

from manuscript_lab.ivtff import IVTFFDocument, LocusRecord, parse_ivtff
from manuscript_lab.provenance import repository_root, sha256_file

EXCLUDED_READING_UNITS = frozenset({"paragraph_start", "paragraph_end", "free_comment", "text_tag"})


@cache
def _root() -> Path:
    return repository_root()


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(_root()).as_posix()
    except ValueError:
        return path.as_posix()


@dataclass(frozen=True)
class WitnessSpec:
    witness_id: str
    path: Path
    alphabet: str
    lineage_group: str
    comparison_group: str | None
    comparison_path: Path | None
    comparison_alternates: tuple[Path, ...]
    independence_role: str
    derived_from: tuple[str, ...]


@dataclass(frozen=True)
class WitnessCorpus:
    config_path: Path
    config_sha256: str
    source_manifest: Path
    source_manifest_sha256: str
    order_witness: str
    specs: tuple[WitnessSpec, ...]
    documents: dict[str, IVTFFDocument]
    comparison_documents: dict[str, IVTFFDocument]
    comparison_alternates: dict[str, tuple[IVTFFDocument, ...]]


@dataclass(frozen=True)
class AlignmentResult:
    metadata: dict[str, Any]
    cells: tuple[dict[str, Any], ...]
    audit: dict[str, Any]


def load_witness_corpus(config_path: Path) -> WitnessCorpus:
    """Load, validate, and strictly parse the registered format-2 witnesses."""
    root = _root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("schema_version") != "1.0":
        raise ValueError("witness registry must be a schema 1.0 mapping")
    raw_specs = config.get("witnesses")
    if not isinstance(raw_specs, list) or not raw_specs:
        raise ValueError("witness registry must contain a non-empty witnesses list")
    specs: list[WitnessSpec] = []
    documents: dict[str, IVTFFDocument] = {}
    comparison_documents: dict[str, IVTFFDocument] = {}
    comparison_alternates: dict[str, tuple[IVTFFDocument, ...]] = {}
    for raw_spec in raw_specs:
        if not isinstance(raw_spec, dict):
            raise ValueError("each witness specification must be a mapping")
        witness_id = str(raw_spec["id"])
        if witness_id in documents:
            raise ValueError(f"duplicate witness id {witness_id}")
        path = root / str(raw_spec["path"])
        comparison_group = raw_spec.get("comparison_group")
        comparison_value = raw_spec.get("comparison_path")
        comparison_path = root / str(comparison_value) if comparison_value is not None else None
        alternate_paths = tuple(
            root / str(value) for value in raw_spec.get("comparison_alternates", [])
        )
        spec = WitnessSpec(
            witness_id=witness_id,
            path=path,
            alphabet=str(raw_spec["alphabet"]),
            lineage_group=str(raw_spec["lineage_group"]),
            comparison_group=str(comparison_group) if comparison_group is not None else None,
            comparison_path=comparison_path,
            comparison_alternates=alternate_paths,
            independence_role=str(raw_spec["independence_role"]),
            derived_from=tuple(str(value) for value in raw_spec.get("derived_from", [])),
        )
        document = parse_ivtff(path, witness_id=witness_id)
        if document.header.alphabet != spec.alphabet:
            raise ValueError(
                f"{witness_id} registry alphabet {spec.alphabet!r} differs from "
                f"header {document.header.alphabet!r}"
            )
        specs.append(spec)
        documents[witness_id] = document
        if spec.comparison_group is not None:
            if spec.comparison_path is None:
                raise ValueError(f"{witness_id} has a comparison group but no comparison path")
            comparison = parse_ivtff(spec.comparison_path, witness_id=witness_id)
            if comparison.header.alphabet != "STA1":
                raise ValueError(f"{witness_id} comparison view is not STA1")
            native_keys = [(item.page, item.number) for item in document.loci]
            comparison_keys = [(item.page, item.number) for item in comparison.loci]
            if native_keys != comparison_keys:
                raise ValueError(f"{witness_id} native and comparison locus keys differ")
            comparison_documents[witness_id] = comparison
            alternates = tuple(
                parse_ivtff(item, witness_id=witness_id) for item in spec.comparison_alternates
            )
            for alternate in alternates:
                if [(item.page, item.number) for item in alternate.loci] != native_keys:
                    raise ValueError(f"{witness_id} alternate comparison locus keys differ")
                if alternate.header.alphabet != "STA1":
                    raise ValueError(f"{witness_id} alternate comparison view is not STA1")
            comparison_alternates[witness_id] = alternates
    order_witness = str(config["order_witness"])
    if order_witness not in documents:
        raise ValueError(f"unknown order_witness {order_witness}")
    source_manifest = root / str(config["source_manifest"])
    return WitnessCorpus(
        config_path=config_path,
        config_sha256=sha256_file(config_path),
        source_manifest=source_manifest,
        source_manifest_sha256=sha256_file(source_manifest),
        order_witness=order_witness,
        specs=tuple(specs),
        documents=documents,
        comparison_documents=comparison_documents,
        comparison_alternates=comparison_alternates,
    )


def reading_surface(locus: LocusRecord) -> str:
    """Remove editorial metadata only; retain every reading uncertainty marker."""
    return "".join(unit.raw for unit in locus.units if unit.kind not in EXCLUDED_READING_UNITS)


def sta_tokens(locus: LocusRecord) -> tuple[str, ...]:
    """Represent STA1 codes atomically while retaining non-editorial structure."""
    tokens: list[str] = []
    for unit in locus.units:
        if unit.kind in EXCLUDED_READING_UNITS:
            continue
        if unit.kind == "glyph_run":
            if len(unit.raw) % 2 or re.fullmatch(r"(?:[A-Z][0-9a-z])+", unit.raw) is None:
                raise ValueError(f"invalid STA1 glyph run {unit.raw!r} in {locus.record_id}")
            tokens.extend(unit.raw[index : index + 2] for index in range(0, len(unit.raw), 2))
        else:
            tokens.append(unit.raw)
    return tuple(tokens)


def _comparison_view(document: IVTFFDocument, locus: LocusRecord) -> dict[str, Any]:
    return {
        "path": _display_path(document.path),
        "sha256": document.source_sha256,
        "diplomatic_surface": locus.text,
        "reading_surface": reading_surface(locus),
    }


def _reading_record(
    locus: LocusRecord,
    comparison: tuple[IVTFFDocument, LocusRecord] | None,
    alternates: tuple[tuple[IVTFFDocument, LocusRecord], ...],
) -> dict[str, Any]:
    record = {
        "record_id": locus.record_id,
        "witness_id": locus.witness_id,
        "locus": locus.locus,
        "locator": locus.locator,
        "relative_locator": locus.relative_locator,
        "locus_type": locus.locus_type,
        "transcriber": locus.transcriber,
        "diplomatic_surface": locus.text,
        "reading_surface": reading_surface(locus),
        "line_numbers": list(locus.line_numbers),
        "raw_lines": list(locus.raw_lines),
        "units": [asdict(unit) for unit in locus.units],
    }
    if comparison is not None:
        record["comparison_view"] = _comparison_view(*comparison)
        record["comparison_alternates"] = [
            _comparison_view(document, item) for document, item in alternates
        ]
    return record


def _comparison_record(
    group: str,
    member_specs: list[WitnessSpec],
    readings: dict[str, list[LocusRecord]],
) -> dict[str, Any]:
    member_ids = [spec.witness_id for spec in member_specs]
    present = [witness_id for witness_id in member_ids if readings.get(witness_id)]
    if len(present) < 2 or any(len(readings[witness_id]) != 1 for witness_id in present):
        return {
            "status": "insufficient",
            "members": member_ids,
            "present": present,
            "primary_lineage_status": "insufficient",
        }
    diplomatic = {readings[witness_id][0].text for witness_id in present}
    surfaces = {reading_surface(readings[witness_id][0]) for witness_id in present}
    if len(diplomatic) == 1:
        status = "exact-diplomatic"
    elif len(surfaces) == 1:
        status = "markup-only-difference"
    else:
        status = "reading-difference"
    primary_by_lineage: dict[str, str] = {}
    for spec in member_specs:
        if spec.witness_id not in present or spec.independence_role == "synthetic-derivative":
            continue
        primary_by_lineage.setdefault(spec.lineage_group, spec.witness_id)
    primary_surfaces = [
        reading_surface(readings[witness_id][0]) for witness_id in primary_by_lineage.values()
    ]
    modal = Counter(primary_surfaces).most_common(1)[0][1] if primary_surfaces else 0
    if len(primary_surfaces) < 2:
        primary_status = "insufficient"
    elif len(set(primary_surfaces)) == 1:
        primary_status = "exact-reading"
    else:
        primary_status = "reading-difference"
    pairs = {}
    for left, right in combinations(present, 2):
        left_surface = reading_surface(readings[left][0])
        right_surface = reading_surface(readings[right][0])
        pairs[f"{left}::{right}"] = {
            "status": "same" if left_surface == right_surface else "different",
            "sta1_token_similarity": Levenshtein.normalized_similarity(
                sta_tokens(readings[left][0]), sta_tokens(readings[right][0])
            ),
        }
    return {
        "status": status,
        "members": member_ids,
        "present": present,
        "primary_lineage_status": primary_status,
        "primary_lineage_representatives": primary_by_lineage,
        "primary_lineage_modal_support": modal,
        "primary_lineage_count": len(primary_surfaces),
        "primary_lineage_modal_fraction": (
            modal / len(primary_surfaces) if primary_surfaces else None
        ),
        "pairs": pairs,
        "note": f"comparison group {group} uses registered STA1 views",
    }


def _similarity_summary(values: list[float]) -> dict[str, float | int]:
    ordered = sorted(values)
    if not ordered:
        return {"count": 0}

    def percentile(fraction: float) -> float:
        return ordered[round(fraction * (len(ordered) - 1))]

    return {
        "count": len(ordered),
        "mean": sum(ordered) / len(ordered),
        "median": percentile(0.5),
        "p10": percentile(0.1),
        "p90": percentile(0.9),
    }


def build_alignment(corpus: WitnessCorpus) -> AlignmentResult:
    """Build a deterministic union lattice and a family-aware audit."""
    by_witness: dict[str, dict[tuple[str, int], list[LocusRecord]]] = {}
    page_coverage: dict[str, set[str]] = {}
    union: set[tuple[str, int]] = set()
    input_reading_count = 0
    for spec in corpus.specs:
        document = corpus.documents[spec.witness_id]
        page_coverage[spec.witness_id] = {page.page for page in document.pages}
        index: dict[tuple[str, int], list[LocusRecord]] = {}
        for locus in document.loci:
            key = (locus.page, locus.number)
            index.setdefault(key, []).append(locus)
            union.add(key)
            input_reading_count += 1
        by_witness[spec.witness_id] = index

    comparison_by_witness = {
        witness_id: {(locus.page, locus.number): [locus] for locus in document.loci}
        for witness_id, document in corpus.comparison_documents.items()
    }
    alternate_by_witness = {
        witness_id: tuple(
            {(locus.page, locus.number): [locus] for locus in document.loci}
            for document in documents
        )
        for witness_id, documents in corpus.comparison_alternates.items()
    }

    order_document = corpus.documents[corpus.order_witness]
    page_order = {page.page: index for index, page in enumerate(order_document.pages)}
    unseen_pages = sorted({page for page, _ in union} - page_order.keys())
    for page in unseen_pages:
        page_order[page] = len(page_order)
    ordered_keys = sorted(union, key=lambda item: (page_order[item[0]], item[1]))

    groups: dict[str, list[WitnessSpec]] = {}
    for spec in corpus.specs:
        if spec.comparison_group is not None:
            groups.setdefault(spec.comparison_group, []).append(spec)

    cells: list[dict[str, Any]] = []
    coverage_counts: dict[str, Counter[str]] = {spec.witness_id: Counter() for spec in corpus.specs}
    comparison_counts: dict[str, Counter[str]] = {group: Counter() for group in groups}
    primary_lineage_counts: dict[str, Counter[str]] = {group: Counter() for group in groups}
    pair_counts: dict[str, Counter[str]] = {}
    pair_similarities: dict[str, list[float]] = {}
    alternate_counts: dict[str, Counter[str]] = {
        spec.witness_id: Counter() for spec in corpus.specs if spec.comparison_alternates
    }
    page_counts: dict[str, Counter[str]] = {}
    structural_counts: Counter[str] = Counter()
    record_ids: set[str] = set()
    output_reading_count = 0

    for page, number in ordered_keys:
        readings = {
            spec.witness_id: by_witness[spec.witness_id].get((page, number), [])
            for spec in corpus.specs
        }
        comparison_readings = {
            witness_id: index.get((page, number), [])
            for witness_id, index in comparison_by_witness.items()
        }
        coverage: dict[str, str] = {}
        reading_records: list[dict[str, Any]] = []
        for spec in corpus.specs:
            witness_readings = readings[spec.witness_id]
            if witness_readings:
                status = "present"
                for locus in witness_readings:
                    if locus.record_id in record_ids:
                        raise ValueError(f"duplicate reading record id {locus.record_id}")
                    record_ids.add(locus.record_id)
                    primary_items = comparison_readings.get(spec.witness_id, [])
                    comparison_pair = None
                    if primary_items:
                        comparison_pair = (
                            corpus.comparison_documents[spec.witness_id],
                            primary_items[0],
                        )
                    alternate_pairs = tuple(
                        (document, index[(page, number)][0])
                        for document, index in zip(
                            corpus.comparison_alternates.get(spec.witness_id, ()),
                            alternate_by_witness.get(spec.witness_id, ()),
                            strict=True,
                        )
                        if (page, number) in index
                    )
                    reading_records.append(_reading_record(locus, comparison_pair, alternate_pairs))
                    if comparison_pair is not None:
                        primary_surface = reading_surface(comparison_pair[1])
                        for _document, alternate in alternate_pairs:
                            alternate_counts[spec.witness_id][
                                "same"
                                if reading_surface(alternate) == primary_surface
                                else "different"
                            ] += 1
                    output_reading_count += 1
            elif page in page_coverage[spec.witness_id]:
                status = "locus-omitted"
            else:
                status = "page-not-covered"
            coverage[spec.witness_id] = status
            coverage_counts[spec.witness_id][status] += 1

        codes = {
            (locus.relative_locator, locus.locus_type)
            for values in readings.values()
            for locus in values
        }
        structural_status = "same" if len(codes) <= 1 else "different"
        structural_counts[structural_status] += 1
        comparisons = {
            group: _comparison_record(group, member_specs, comparison_readings)
            for group, member_specs in groups.items()
        }
        for group, comparison in comparisons.items():
            comparison_counts[group][comparison["status"]] += 1
            primary_lineage_counts[group][comparison["primary_lineage_status"]] += 1
            for pair, pair_result in comparison.get("pairs", {}).items():
                pair_counts.setdefault(pair, Counter())[pair_result["status"]] += 1
                pair_similarities.setdefault(pair, []).append(pair_result["sta1_token_similarity"])
        page_counter = page_counts.setdefault(page, Counter())
        page_counter["canonical_loci"] += 1
        if all(value == "present" for value in coverage.values()):
            page_counter["all_witnesses_present"] += 1
        for group, comparison in comparisons.items():
            page_counter[f"{group}:{comparison['primary_lineage_status']}"] += 1
        cells.append(
            {
                "record_type": "locus",
                "locus_key": f"{page}.{number}",
                "page": page,
                "number": number,
                "coverage": coverage,
                "structural_code_status": structural_status,
                "structural_codes": [
                    {"relative_locator": locator, "locus_type": locus_type}
                    for locator, locus_type in sorted(codes)
                ],
                "comparisons": comparisons,
                "readings": reading_records,
            }
        )

    if input_reading_count != output_reading_count:
        raise ValueError(
            f"alignment lost readings: input={input_reading_count}, output={output_reading_count}"
        )
    witness_metadata = [
        {
            "witness_id": spec.witness_id,
            "path": _display_path(spec.path),
            "sha256": corpus.documents[spec.witness_id].source_sha256,
            "alphabet": spec.alphabet,
            "lineage_group": spec.lineage_group,
            "comparison_group": spec.comparison_group,
            "comparison_path": (
                _display_path(spec.comparison_path) if spec.comparison_path is not None else None
            ),
            "comparison_sha256": (
                corpus.comparison_documents[spec.witness_id].source_sha256
                if spec.witness_id in corpus.comparison_documents
                else None
            ),
            "comparison_alternates": [
                {"path": _display_path(document.path), "sha256": document.source_sha256}
                for document in corpus.comparison_alternates.get(spec.witness_id, ())
            ],
            "independence_role": spec.independence_role,
            "derived_from": list(spec.derived_from),
            "page_count": len(corpus.documents[spec.witness_id].pages),
            "locus_count": len(corpus.documents[spec.witness_id].loci),
        }
        for spec in corpus.specs
    ]
    metadata = {
        "record_type": "metadata",
        "schema_version": "1.0",
        "alignment_key": "IVTFF page name plus canonical locus number",
        "order_witness": corpus.order_witness,
        "config_path": _display_path(corpus.config_path),
        "config_sha256": corpus.config_sha256,
        "source_manifest": _display_path(corpus.source_manifest),
        "source_manifest_sha256": corpus.source_manifest_sha256,
        "implementation_sha256": sha256_file(Path(__file__)),
        "excluded_reading_unit_kinds": sorted(EXCLUDED_READING_UNITS),
        "witnesses": witness_metadata,
    }
    uncertainty_by_witness: dict[str, dict[str, int]] = {}
    uncertainty_kinds = {
        "alternative_reading",
        "uncertain_space",
        "unreadable_character",
        "unreadable_unknown_count",
    }
    for spec in corpus.specs:
        counts: Counter[str] = Counter()
        for locus in corpus.documents[spec.witness_id].loci:
            kinds = {unit.kind for unit in locus.units}
            matched = kinds & uncertainty_kinds
            if matched:
                counts["loci_with_any_uncertainty"] += 1
            for kind in matched:
                counts[f"loci_with_{kind}"] += 1
        uncertainty_by_witness[spec.witness_id] = dict(sorted(counts.items()))
    audit = {
        "schema_version": "1.0",
        "canonical_locus_count": len(cells),
        "input_reading_count": input_reading_count,
        "output_reading_count": output_reading_count,
        "unique_reading_record_count": len(record_ids),
        "all_witness_coverage_count": sum(
            all(value == "present" for value in cell["coverage"].values()) for cell in cells
        ),
        "coverage_by_witness": {
            witness_id: dict(sorted(counts.items()))
            for witness_id, counts in coverage_counts.items()
        },
        "structural_code_status": dict(sorted(structural_counts.items())),
        "comparison_groups": {
            group: dict(sorted(counts.items())) for group, counts in comparison_counts.items()
        },
        "primary_lineage_comparison": {
            group: dict(sorted(counts.items())) for group, counts in primary_lineage_counts.items()
        },
        "pairwise_sta1_reading_comparison": {
            pair: {
                **dict(sorted(counts.items())),
                "similarity": _similarity_summary(pair_similarities[pair]),
            }
            for pair, counts in sorted(pair_counts.items())
        },
        "alternate_conversion_sensitivity": {
            witness_id: dict(sorted(counts.items()))
            for witness_id, counts in alternate_counts.items()
        },
        "uncertainty_by_witness": uncertainty_by_witness,
        "by_page": {page: dict(sorted(counts.items())) for page, counts in page_counts.items()},
        "lineage_groups": {
            group: [spec.witness_id for spec in corpus.specs if spec.lineage_group == group]
            for group in sorted({spec.lineage_group for spec in corpus.specs})
        },
        "synthetic_derivative_witnesses": [
            spec.witness_id
            for spec in corpus.specs
            if spec.independence_role == "synthetic-derivative"
        ],
    }
    return AlignmentResult(metadata=metadata, cells=tuple(cells), audit=audit)


def write_alignment(result: AlignmentResult, output: Path, audit_output: Path) -> None:
    """Write deterministic JSONL lattice and JSON audit to new artifact paths."""
    if output.exists() or audit_output.exists():
        raise ValueError("alignment outputs are immutable; choose new paths")
    output.parent.mkdir(parents=True, exist_ok=True)
    audit_output.parent.mkdir(parents=True, exist_ok=True)
    options = orjson.OPT_SORT_KEYS | orjson.OPT_APPEND_NEWLINE
    with output.open("wb") as handle:
        handle.write(orjson.dumps(result.metadata, option=options))
        for cell in result.cells:
            handle.write(orjson.dumps(cell, option=options))
    audit_output.write_bytes(orjson.dumps(result.audit, option=options | orjson.OPT_INDENT_2))
