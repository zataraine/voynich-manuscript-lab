"""Minimal lossless inspection of IVTFF page metadata."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from manuscript_lab.provenance import sha256_file

PAGE_HEADER = re.compile(r"^<(?P<page>f[^>.]+)>\s+<!\s*(?P<metadata>.*?)\s*>\s*$")
METADATA_FIELD = re.compile(r"\$([A-Z])=([^\s>]+)")
TEXT_LINE = re.compile(r"^<(?P<locus>f[^>]+\.[^>]+)>\s*(?P<text>.*)$")


@dataclass(frozen=True)
class PageHeader:
    """One IVTFF physical-page header and its uninterpreted metadata fields."""

    page: str
    fields: dict[str, str]
    line_number: int
    raw: str


@dataclass(frozen=True)
class TextLine:
    """One diplomatic IVTFF text line with its raw transcription intact."""

    locus: str
    page: str
    locator: str
    text: str
    line_number: int
    raw: str


def iter_page_headers(path: Path) -> Iterator[PageHeader]:
    """Yield physical-page headers without modifying or normalizing their values."""
    with path.open(encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, start=1):
            raw = line.rstrip("\r\n")
            match = PAGE_HEADER.match(raw)
            if match is None:
                continue
            fields = dict(METADATA_FIELD.findall(match.group("metadata")))
            yield PageHeader(match.group("page"), fields, line_number, raw)


def iter_text_lines(path: Path) -> Iterator[TextLine]:
    """Yield IVTFF text-line records without interpreting their transcription."""
    with path.open(encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, start=1):
            raw = line.rstrip("\r\n")
            match = TEXT_LINE.match(raw)
            if match is None:
                continue
            locus = match.group("locus")
            page_and_line, _, locator = locus.partition(",")
            page, _, _line = page_and_line.partition(".")
            yield TextLine(
                locus=locus,
                page=page,
                locator=locator,
                text=match.group("text"),
                line_number=line_number,
                raw=raw,
            )


def summarize_page_metadata(path: Path) -> dict[str, Any]:
    """Summarize page-level metadata while retaining missing values explicitly."""
    headers = list(iter_page_headers(path))
    field_names = sorted({name for header in headers for name in header.fields})
    counts = {
        name: dict(
            sorted(Counter(header.fields.get(name, "<missing>") for header in headers).items())
        )
        for name in field_names
    }
    return {
        "schema_version": "1.0",
        "source_path": path.as_posix(),
        "source_sha256": sha256_file(path),
        "page_header_count": len(headers),
        "field_counts": counts,
        "currier_language_counts": counts.get("L", {}),
        "scribal_hand_counts": counts.get("H", {}),
    }
