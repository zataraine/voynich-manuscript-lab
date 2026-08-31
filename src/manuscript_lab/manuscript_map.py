"""Deterministic, claim-explicit links between IVTFF pages and IIIF canvases."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from manuscript_lab.ivtff import IVTFFDocument
from manuscript_lab.provenance import sha256_file

FOLIO_LABEL = re.compile(r"(?<!\d)(\d{1,3}[rv])\b")
PART_PAGE = re.compile(r"^(f\d+[rv])(?:[1-9])?$")


@dataclass(frozen=True)
class CanvasRecord:
    page_id: str
    physical_index: int
    canvas_id: str
    label: str
    width: int
    height: int
    folios: tuple[str, ...]
    image_id: str
    image_service_id: str | None


@dataclass(frozen=True)
class LocusCanvasLink:
    witness_id: str
    locus_record_id: str
    ivtff_page: str
    physical_folios: tuple[str, ...]
    page_id: str
    canvas_id: str
    canvas_label: str
    method: str = "deterministic-label"
    confidence: float = 1.0


def _label_value(canvas: dict[str, Any], fallback: str) -> str:
    values = next(iter(canvas.get("label", {}).values()), [])
    return str(values[0]) if values else fallback


def load_iiif_canvases(path: Path, *, source_id: str = "yale-ms408") -> tuple[CanvasRecord, ...]:
    """Load ordered Presentation 3 canvases without choosing a preferred foldout image."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    records: list[CanvasRecord] = []
    for index, canvas in enumerate(manifest.get("items", []), start=1):
        label = _label_value(canvas, f"canvas-{index}")
        folios = tuple(f"f{value}" for value in FOLIO_LABEL.findall(label))
        annotation = canvas["items"][0]["items"][0]
        body = annotation["body"]
        services = body.get("service", [])
        service_id = None
        if services:
            service_id = services[0].get("id") or services[0].get("@id")
        records.append(
            CanvasRecord(
                page_id=f"{source_id}:page:{index:04d}",
                physical_index=index,
                canvas_id=canvas["id"],
                label=label,
                width=int(canvas["width"]),
                height=int(canvas["height"]),
                folios=folios,
                image_id=body["id"],
                image_service_id=service_id,
            )
        )
    return tuple(records)


def physical_folios_for_ivtff_page(page: str) -> tuple[str, ...]:
    """Resolve only physical identities defined by IVTFF 2.0.2 page conventions."""
    if page == "fRos":
        return ("f85v", "f86r")
    match = PART_PAGE.fullmatch(page)
    return (match.group(1),) if match else ()


def link_loci_to_canvases(
    document: IVTFFDocument, canvases: tuple[CanvasRecord, ...]
) -> tuple[LocusCanvasLink, ...]:
    """Create all valid canvas links; foldout loci may intentionally have several."""
    by_folio: dict[str, list[CanvasRecord]] = {}
    for canvas in canvases:
        for folio in canvas.folios:
            by_folio.setdefault(folio, []).append(canvas)
    links: list[LocusCanvasLink] = []
    for locus in document.loci:
        folios = physical_folios_for_ivtff_page(locus.page)
        matches = {
            canvas.canvas_id: canvas for folio in folios for canvas in by_folio.get(folio, [])
        }
        for canvas in sorted(matches.values(), key=lambda item: item.physical_index):
            links.append(
                LocusCanvasLink(
                    witness_id=document.witness_id,
                    locus_record_id=locus.record_id,
                    ivtff_page=locus.page,
                    physical_folios=folios,
                    page_id=canvas.page_id,
                    canvas_id=canvas.canvas_id,
                    canvas_label=canvas.label,
                )
            )
    return tuple(links)


def mapping_audit(
    document: IVTFFDocument, canvases: tuple[CanvasRecord, ...], manifest_path: Path
) -> dict[str, Any]:
    """Report coverage without hiding one-to-many foldout mappings."""
    links = link_loci_to_canvases(document, canvases)
    linked = {link.locus_record_id for link in links}
    counts: dict[str, int] = {}
    for link in links:
        counts[link.locus_record_id] = counts.get(link.locus_record_id, 0) + 1
    return {
        "schema_version": "1.0",
        "witness_id": document.witness_id,
        "witness_sha256": document.source_sha256,
        "iiif_manifest_sha256": sha256_file(manifest_path),
        "locus_count": len(document.loci),
        "linked_locus_count": len(linked),
        "unlinked_locus_ids": [
            locus.record_id for locus in document.loci if locus.record_id not in linked
        ],
        "multi_canvas_locus_count": sum(value > 1 for value in counts.values()),
        "link_count": len(links),
    }
