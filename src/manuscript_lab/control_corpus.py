"""Immutable adapters for calibration corpora stored in the pinned Naibbe archive."""

from __future__ import annotations

import hashlib
import re
import tarfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path

TOKEN = re.compile(r"[^\W\d_]+(?:['\u2019-][^\W\d_]+)*", re.UNICODE)


@dataclass(frozen=True)
class ControlDocument:
    """One source document with archive-member provenance."""

    document_id: str
    family: str
    subgroup: str
    member: str
    member_sha256: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class TextSample:
    """A contiguous chunk that remains grouped with its parent document."""

    sample_id: str
    document_id: str
    family: str
    subgroup: str
    tokens: tuple[str, ...]
    source_ref: str
    source_sha256: str


def normalize_tokens(text: str) -> tuple[str, ...]:
    """Apply the declared control-corpus transform without altering raw bytes."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return tuple(match.group(0).replace("\u2019", "'") for match in TOKEN.finditer(normalized))


def _family(name: str) -> str | None:
    if "/gibberish_transcriptions/" in name and name.endswith(".txt"):
        return "human_gibberish"
    if "/meaningful/texts/" in name and name.endswith(".txt"):
        return "meaningful"
    if "/naibbe_reference_ciphertexts/" in name and name.endswith(".txt"):
        return "naibbe_payload"
    return None


def load_control_documents(archive: Path) -> list[ControlDocument]:
    """Read eligible members directly from a tarball; never extract the raw archive."""
    documents: list[ControlDocument] = []
    with tarfile.open(archive, mode="r:gz") as handle:
        for member in sorted(handle.getmembers(), key=lambda value: value.name):
            family = _family(member.name)
            if family is None or not member.isfile():
                continue
            stream = handle.extractfile(member)
            if stream is None:
                raise ValueError(f"Could not read archive member: {member.name}")
            payload = stream.read()
            tokens = normalize_tokens(payload.decode("utf-8-sig", errors="strict"))
            if not tokens:
                continue
            stem = Path(member.name).stem
            subgroup = stem.split(" - ", 1)[0] if " - " in stem else stem.split("_", 2)[0]
            digest = hashlib.sha256(payload).hexdigest()
            document_id = hashlib.sha256(member.name.encode()).hexdigest()[:20]
            documents.append(
                ControlDocument(document_id, family, subgroup, member.name, digest, tokens)
            )
    return documents


def chunk_document(
    document: ControlDocument, *, chunk_tokens: int, max_chunks: int
) -> list[TextSample]:
    """Take deterministic, evenly spread contiguous chunks from one document."""
    if chunk_tokens < 20 or max_chunks < 1:
        raise ValueError("chunk_tokens must be >=20 and max_chunks must be positive")
    possible = max(1, len(document.tokens) // chunk_tokens)
    count = min(max_chunks, possible)
    if len(document.tokens) <= chunk_tokens:
        starts = [0]
    elif count == 1:
        starts = [(len(document.tokens) - chunk_tokens) // 2]
    else:
        limit = len(document.tokens) - chunk_tokens
        starts = [round(index * limit / (count - 1)) for index in range(count)]
    return [
        TextSample(
            sample_id=f"{document.document_id}:{index:03d}",
            document_id=document.document_id,
            family=document.family,
            subgroup=document.subgroup,
            tokens=document.tokens[start : start + chunk_tokens],
            source_ref=document.member,
            source_sha256=document.member_sha256,
        )
        for index, start in enumerate(starts)
    ]


def control_samples(
    archive: Path, *, chunk_tokens: int, max_chunks_per_document: int
) -> list[TextSample]:
    """Load and chunk all supported calibration and positive-control documents."""
    return [
        sample
        for document in load_control_documents(archive)
        for sample in chunk_document(
            document, chunk_tokens=chunk_tokens, max_chunks=max_chunks_per_document
        )
    ]
