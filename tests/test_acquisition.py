import json
from pathlib import Path

import pytest

from manuscript_lab.acquisition import (
    Receipt,
    _safe_raw_destination,
    _write_receipts,
    iiif_image_assets,
)


def test_destination_is_confined_to_raw(tmp_path: Path) -> None:
    (tmp_path / "data" / "raw").mkdir(parents=True)
    assert _safe_raw_destination(tmp_path, "data/raw/images/page.jpg").is_relative_to(
        tmp_path / "data" / "raw"
    )
    with pytest.raises(ValueError, match="below data/raw"):
        _safe_raw_destination(tmp_path, "data/raw/../../escape.txt")


def test_extracts_presentation_3_image_service() -> None:
    manifest = {
        "items": [
            {
                "label": {"en": ["f1r"]},
                "items": [
                    {
                        "items": [
                            {
                                "body": {
                                    "id": "https://example.invalid/full.jpg",
                                    "service": [{"id": "https://example.invalid/iiif/2/123"}],
                                }
                            }
                        ]
                    }
                ],
            }
        ]
    }
    assets = iiif_image_assets(manifest, "data/raw/images/yale")
    assert assets == [
        {
            "id": "yale-iiif-001",
            "url": "https://example.invalid/iiif/2/123/full/full/0/default.jpg",
            "destination": "data/raw/images/yale/001-f1r-123.jpg",
            "expected_media": "image/jpeg",
        }
    ]


def test_accepts_presentation_3_manifest_with_image_api_2_service() -> None:
    manifest = {
        "items": [
            {
                "label": {"none": ["[Front cover]"]},
                "items": [
                    {
                        "items": [
                            {
                                "body": {
                                    "id": "https://example.invalid/iiif/2/456/full/full/0/default.jpg",
                                    "service": [{"@id": "https://example.invalid/iiif/2/456"}],
                                }
                            }
                        ]
                    }
                ],
            }
        ]
    }
    asset = iiif_image_assets(manifest, "data/raw/images/yale")[0]
    assert asset["url"] == "https://example.invalid/iiif/2/456/full/full/0/default.jpg"
    assert asset["destination"] == "data/raw/images/yale/001-Front-cover-456.jpg"


def test_receipts_merge_across_grouped_runs(tmp_path: Path) -> None:
    common = {
        "acquired_at": "2026-08-30T00:00:00Z",
        "bytes": 1,
        "sha256": "a" * 64,
        "content_type": "text/plain",
        "etag": None,
        "last_modified": None,
        "status": "downloaded",
    }
    first = Receipt(asset_id="one", url="https://example.invalid/1", path="data/raw/1", **common)
    second = Receipt(asset_id="two", url="https://example.invalid/2", path="data/raw/2", **common)
    _write_receipts([first], tmp_path)
    output = _write_receipts([second], tmp_path)
    payload = json.loads(output.read_text())
    assert [item["path"] for item in payload["files"]] == ["data/raw/1", "data/raw/2"]
