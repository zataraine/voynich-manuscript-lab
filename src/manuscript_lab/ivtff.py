"""Lossless structural parsing for IVTFF transliteration witnesses.

The parser deliberately does not interpret alphabet-specific glyph runs. It
recognises only syntax defined by IVTFF and retains every physical source line,
line ending, witness identifier, and diplomatic surface.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from manuscript_lab.provenance import sha256_file

FILE_HEADER = re.compile(
    r"^#=IVTFF\s+(?P<alphabet>\S{4})\s+(?P<version>\d+\.\d+)"
    r"(?:\s+(?P<completeness>\S)\s+(?P<source>\S))?\s*$"
)
PAGE_HEADER = re.compile(r"^<(?P<page>f[^>.]+)>\s*(?:<!\s*(?P<metadata>.*?)\s*>)?\s*$")
METADATA_FIELD = re.compile(r"\$([A-Z])=([^\s>]+)")
LOCUS_LINE = re.compile(
    r"^<(?P<page>f[^>.,]+)\.(?P<number>[1-9]\d{0,2}),"
    r"(?P<locator>.)(?P<locus_type>[A-Z][a-z0-9])"
    r"(?:;(?P<transcriber>.))?>"
    r"(?P<spacing>\s*)(?P<text>.*)$"
)


class IVTFFFormatError(ValueError):
    """Raised when strict parsing finds structural IVTFF errors."""


@dataclass(frozen=True)
class FileHeader:
    alphabet: str
    version: str
    completeness: str | None
    source: str | None
    raw: str


@dataclass(frozen=True)
class PhysicalLine:
    """A byte-reversible physical source line."""

    number: int
    kind: str
    content: str
    ending: str


@dataclass(frozen=True)
class PageHeader:
    """One IVTFF page header and its uninterpreted metadata fields."""

    page: str
    fields: dict[str, str]
    line_number: int
    raw: str


@dataclass(frozen=True)
class SurfaceUnit:
    """One structural unit with an exact character span in a diplomatic surface."""

    kind: str
    raw: str
    start: int
    end: int
    alternatives: tuple[str, ...] = ()


@dataclass(frozen=True)
class LocusRecord:
    """One logical IVTFF locus, possibly wrapped over several physical lines."""

    witness_id: str
    locus: str
    page: str
    number: int
    locator: str
    relative_locator: str
    locus_type: str
    transcriber: str | None
    text: str
    units: tuple[SurfaceUnit, ...]
    line_numbers: tuple[int, ...]
    raw_lines: tuple[str, ...]

    @property
    def record_id(self) -> str:
        return f"{self.witness_id}:locus:{self.locus}"

    @property
    def raw(self) -> str:
        """Backward-compatible access to the first physical source line."""
        return self.raw_lines[0]


TextLine = LocusRecord


@dataclass(frozen=True)
class ParseIssue:
    line_number: int
    code: str
    message: str


@dataclass(frozen=True)
class IVTFFDocument:
    """A parsed witness whose physical-line layer renders byte-for-byte."""

    path: Path
    witness_id: str
    source_sha256: str
    header: FileHeader
    physical_lines: tuple[PhysicalLine, ...]
    pages: tuple[PageHeader, ...]
    loci: tuple[LocusRecord, ...]
    issues: tuple[ParseIssue, ...]

    def render_bytes(self) -> bytes:
        return "".join(line.content + line.ending for line in self.physical_lines).encode("ascii")


def _split_physical_lines(raw: bytes) -> list[tuple[str, str]]:
    text = raw.decode("ascii", errors="strict")
    result: list[tuple[str, str]] = []
    for physical in text.splitlines(keepends=True):
        content = physical.rstrip("\r\n")
        result.append((content, physical[len(content) :]))
    if text and not result:
        result.append((text, ""))
    return result


def _surface_issue(units: list[SurfaceUnit], start: int, end: int, raw: str) -> None:
    units.append(SurfaceUnit("invalid_markup", raw[start:end], start, end))


def parse_surface(surface: str) -> tuple[SurfaceUnit, ...]:
    """Tokenize IVTFF syntax without segmenting alphabet-specific glyph runs."""
    units: list[SurfaceUnit] = []
    index = 0
    specials = ".,<@{[?"
    dedicated = {
        "<%>": "paragraph_start",
        "<$>": "paragraph_end",
        "<->": "drawing_space",
        "<~>": "misaligned_drawing_space",
    }
    while index < len(surface):
        matched = False
        for marker, kind in dedicated.items():
            if surface.startswith(marker, index):
                units.append(SurfaceUnit(kind, marker, index, index + len(marker)))
                index += len(marker)
                matched = True
                break
        if matched:
            continue
        character = surface[index]
        if character == ".":
            units.append(SurfaceUnit("certain_space", character, index, index + 1))
            index += 1
        elif character == ",":
            units.append(SurfaceUnit("uncertain_space", character, index, index + 1))
            index += 1
        elif character == "?":
            length = 3 if surface.startswith("???", index) else 1
            units.append(
                SurfaceUnit(
                    "unreadable_unknown_count" if length == 3 else "unreadable_character",
                    surface[index : index + length],
                    index,
                    index + length,
                )
            )
            index += length
        elif character == "@":
            match = re.match(r"@[0-9]{3};", surface[index:])
            if match is None or not 128 <= int(match.group()[1:4]) <= 255:
                _surface_issue(units, index, index + 1, surface)
                index += 1
            else:
                end = index + len(match.group())
                units.append(SurfaceUnit("high_ascii", surface[index:end], index, end))
                index = end
        elif character == "[":
            end = surface.find("]", index + 1)
            if end < 0:
                _surface_issue(units, index, len(surface), surface)
                index = len(surface)
            else:
                end += 1
                raw = surface[index:end]
                alternatives = tuple(raw[1:-1].split(":"))
                kind = "alternative_reading" if 2 <= len(alternatives) <= 3 else "invalid_markup"
                units.append(SurfaceUnit(kind, raw, index, end, alternatives))
                index = end
        elif character == "{":
            end = surface.find("}", index + 1)
            if end < 0:
                _surface_issue(units, index, len(surface), surface)
                index = len(surface)
            else:
                end += 1
                units.append(SurfaceUnit("ligature", surface[index:end], index, end))
                index = end
        elif character == "<":
            end = surface.find(">", index + 1)
            if end < 0:
                _surface_issue(units, index, len(surface), surface)
                index = len(surface)
            else:
                end += 1
                raw = surface[index:end]
                kind = "text_tag" if re.fullmatch(r"<@[A-Z]=.>", raw) else "free_comment"
                if not raw.startswith(("<!", "<@")):
                    kind = "invalid_markup"
                units.append(SurfaceUnit(kind, raw, index, end))
                index = end
        else:
            end = index + 1
            while end < len(surface) and surface[end] not in specials:
                end += 1
            units.append(SurfaceUnit("glyph_run", surface[index:end], index, end))
            index = end
    return tuple(units)


def _unwrap_segment(text: str, *, continuation: bool) -> tuple[str, bool]:
    if continuation:
        text = text[1:]
        if text.startswith(" "):
            text = text[1:]
    wrapped = text.endswith("/")
    if wrapped:
        text = text[:-1]
        if text.endswith(" "):
            text = text[:-1]
    return text, wrapped


def parse_ivtff(path: Path, *, witness_id: str | None = None, strict: bool = True) -> IVTFFDocument:
    """Parse a format-2 IVTFF witness and optionally reject structural errors."""
    raw = path.read_bytes()
    split_lines = _split_physical_lines(raw)
    if not split_lines:
        raise IVTFFFormatError("empty IVTFF file")
    header_match = FILE_HEADER.fullmatch(split_lines[0][0])
    if header_match is None:
        raise IVTFFFormatError("line 1 is not a valid IVTFF header")
    header = FileHeader(
        alphabet=header_match.group("alphabet"),
        version=header_match.group("version"),
        completeness=header_match.group("completeness"),
        source=header_match.group("source"),
        raw=split_lines[0][0],
    )
    if not header.version.startswith("2."):
        raise IVTFFFormatError(f"unsupported IVTFF version {header.version}; expected 2.x")

    resolved_witness = witness_id or path.stem
    physical: list[PhysicalLine] = []
    pages: list[PageHeader] = []
    loci: list[LocusRecord] = []
    issues: list[ParseIssue] = []
    current_page: str | None = None
    pending: dict[str, Any] | None = None

    def finish_pending() -> None:
        nonlocal pending
        if pending is None:
            return
        pending.pop("expects_continuation", None)
        text = "".join(pending.pop("segments"))
        pending["text"] = text
        pending["units"] = parse_surface(text)
        if any(unit.kind == "invalid_markup" for unit in pending["units"]):
            issues.append(
                ParseIssue(pending["line_numbers"][0], "invalid-surface", pending["locus"])
            )
        loci.append(LocusRecord(**pending))
        pending = None

    for line_number, (content, ending) in enumerate(split_lines, start=1):
        kind = "unknown"
        if line_number == 1:
            kind = "file_header"
        elif content.startswith("#"):
            finish_pending()
            kind = "comment"
        elif content.startswith("/"):
            kind = "continuation"
            if pending is None or not pending.get("expects_continuation", False):
                issues.append(
                    ParseIssue(line_number, "orphan-continuation", "unexpected continuation line")
                )
            else:
                segment, wrapped = _unwrap_segment(content, continuation=True)
                pending["segments"].append(segment)
                pending["line_numbers"] += (line_number,)
                pending["raw_lines"] += (content,)
                pending["expects_continuation"] = wrapped
                if not wrapped:
                    finish_pending()
        else:
            finish_pending()
            page_match = PAGE_HEADER.fullmatch(content)
            locus_match = LOCUS_LINE.fullmatch(content)
            if page_match is not None:
                kind = "page_header"
                current_page = page_match.group("page")
                fields = dict(METADATA_FIELD.findall(page_match.group("metadata") or ""))
                pages.append(PageHeader(current_page, fields, line_number, content))
            elif locus_match is not None:
                kind = "locus"
                page = locus_match.group("page")
                if current_page != page:
                    issues.append(
                        ParseIssue(
                            line_number,
                            "page-mismatch",
                            f"locus page {page!r} follows page header {current_page!r}",
                        )
                    )
                segment, wrapped = _unwrap_segment(locus_match.group("text"), continuation=False)
                locus = content[1 : content.index(">")]
                pending = {
                    "witness_id": resolved_witness,
                    "locus": locus,
                    "page": page,
                    "number": int(locus_match.group("number")),
                    "locator": locus_match.group("locator") + locus_match.group("locus_type"),
                    "relative_locator": locus_match.group("locator"),
                    "locus_type": locus_match.group("locus_type"),
                    "transcriber": locus_match.group("transcriber"),
                    "segments": [segment],
                    "line_numbers": (line_number,),
                    "raw_lines": (content,),
                    "expects_continuation": wrapped,
                }
                if not wrapped:
                    finish_pending()
            else:
                issues.append(ParseIssue(line_number, "unknown-line", content[:80]))
        physical.append(PhysicalLine(line_number, kind, content, ending))
    if pending is not None:
        if pending.get("expects_continuation", False):
            issues.append(
                ParseIssue(pending["line_numbers"][-1], "missing-continuation", pending["locus"])
            )
        finish_pending()

    document = IVTFFDocument(
        path=path,
        witness_id=resolved_witness,
        source_sha256=sha256_file(path),
        header=header,
        physical_lines=tuple(physical),
        pages=tuple(pages),
        loci=tuple(loci),
        issues=tuple(issues),
    )
    if strict and document.issues:
        details = "; ".join(
            f"line {issue.line_number} {issue.code}: {issue.message}"
            for issue in document.issues[:5]
        )
        raise IVTFFFormatError(details)
    return document


def iter_page_headers(path: Path) -> Iterator[PageHeader]:
    yield from parse_ivtff(path, strict=False).pages


def iter_text_lines(path: Path) -> Iterator[TextLine]:
    yield from parse_ivtff(path, strict=False).loci


def summarize_page_metadata(path: Path) -> dict[str, Any]:
    """Summarize page metadata while retaining missing values explicitly."""
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
