"""Polite, atomic, provenance-preserving acquisition of the Voynich source set."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

from manuscript_lab.provenance import repository_root, sha256_file

CHUNK_SIZE = 4 * 1024 * 1024
SAFE_LABEL = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class Receipt:
    asset_id: str
    url: str
    path: str
    acquired_at: str
    bytes: int
    sha256: str
    content_type: str | None
    etag: str | None
    last_modified: str | None
    status: str


def _safe_raw_destination(root: Path, relative: str) -> Path:
    """Resolve a configured path and constrain it to data/raw."""
    raw = (root / "data" / "raw").resolve()
    destination = (root / relative).resolve()
    try:
        destination.relative_to(raw)
    except ValueError as exc:
        raise ValueError(f"Destination must be below data/raw: {relative}") from exc
    return destination


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _download(asset: dict[str, Any], root: Path, user_agent: str, retries: int = 3) -> Receipt:
    destination = _safe_raw_destination(root, asset["destination"])
    if destination.exists():
        return Receipt(
            asset_id=asset["id"],
            url=asset["url"],
            path=asset["destination"],
            acquired_at=_timestamp(),
            bytes=destination.stat().st_size,
            sha256=sha256_file(destination),
            content_type=None,
            etag=None,
            last_modified=None,
            status="already-present",
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    request = Request(asset["url"], headers={"User-Agent": user_agent})
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urlopen(request, timeout=120) as response, partial.open("wb") as handle:
                content_type = response.headers.get_content_type()
                expected = asset.get("expected_media")
                if expected and content_type != expected:
                    aliases = {
                        ("text/plain", "text/x-c"),
                        ("application/gzip", "application/octet-stream"),
                        ("application/gzip", "application/x-gzip"),
                        ("application/json", "application/ld+json"),
                    }
                    if (expected, content_type) not in aliases:
                        raise ValueError(
                            f"{asset['id']}: expected {expected}, received {content_type}"
                        )
                shutil.copyfileobj(response, handle, CHUNK_SIZE)
                headers = response.headers
            if partial.stat().st_size == 0:
                raise ValueError(f"{asset['id']}: server returned an empty file")
            expected_bytes = asset.get("expected_bytes")
            if expected_bytes is not None and partial.stat().st_size != int(expected_bytes):
                raise ValueError(
                    f"{asset['id']}: expected {expected_bytes} bytes, "
                    f"received {partial.stat().st_size}"
                )
            expected_md5 = asset.get("expected_md5")
            if expected_md5 is not None:
                digest = hashlib.md5(usedforsecurity=False)
                with partial.open("rb") as check_handle:
                    for chunk in iter(lambda: check_handle.read(CHUNK_SIZE), b""):
                        digest.update(chunk)
                if digest.hexdigest() != expected_md5:
                    raise ValueError(f"{asset['id']}: source-repository MD5 checksum mismatch")
            partial.replace(destination)
            return Receipt(
                asset_id=asset["id"],
                url=asset["url"],
                path=asset["destination"],
                acquired_at=_timestamp(),
                bytes=destination.stat().st_size,
                sha256=sha256_file(destination),
                content_type=content_type,
                etag=headers.get("ETag"),
                last_modified=headers.get("Last-Modified"),
                status="downloaded",
            )
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = exc
            partial.unlink(missing_ok=True)
            if attempt < retries:
                time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"Failed {asset['id']} after {retries} attempts: {last_error}")


def iiif_image_assets(manifest: dict[str, Any], destination_directory: str) -> list[dict[str, str]]:
    """Extract stable, full-resolution image requests from a IIIF Presentation 3 manifest."""
    assets: list[dict[str, str]] = []
    for index, canvas in enumerate(manifest.get("items", []), start=1):
        label_map = canvas.get("label", {})
        labels = next(iter(label_map.values()), [f"canvas-{index}"])
        label = str(labels[0]) if labels else f"canvas-{index}"
        page = canvas["items"][0]
        annotation = page["items"][0]
        body = annotation["body"]
        services = body.get("service", [])
        if services:
            service_id = (services[0].get("id") or services[0]["@id"]).rstrip("/")
            url = f"{service_id}/full/full/0/default.jpg"
            image_id = service_id.rsplit("/", 1)[-1]
        else:
            url = body["id"]
            image_id = hashlib.sha256(url.encode()).hexdigest()[:12]
        safe_label = SAFE_LABEL.sub("-", label).strip("-") or f"canvas-{index}"
        filename = f"{index:03d}-{safe_label}-{image_id}.jpg"
        assets.append(
            {
                "id": f"yale-iiif-{index:03d}",
                "url": url,
                "destination": f"{destination_directory.rstrip('/')}/{filename}",
                "expected_media": "image/jpeg",
            }
        )
    return assets


def _write_receipts(receipts: list[Receipt], root: Path) -> Path:
    output = root / "artifacts" / "acquisition" / "voynich-receipts.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    by_path: dict[str, dict[str, Any]] = {}
    if output.exists():
        previous = json.loads(output.read_text(encoding="utf-8"))
        by_path.update({item["path"]: item for item in previous.get("files", [])})
    by_path.update({item.path: asdict(item) for item in receipts})
    payload = {
        "schema_version": "1.0",
        "generated_at": _timestamp(),
        "files": [by_path[path] for path in sorted(by_path)],
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output


def acquire(config_path: Path, groups: set[str] | None, skip_images: bool) -> list[Receipt]:
    root = repository_root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assets = config["assets"]
    if groups:
        assets = [asset for asset in assets if asset["group"] in groups]
    receipts: list[Receipt] = []
    for number, asset in enumerate(assets, start=1):
        print(f"[{number}/{len(assets)}] {asset['id']}", flush=True)
        receipts.append(_download(asset, root, config["user_agent"]))

    iiif = config.get("iiif_images", {})
    image_group_selected = not groups or "yale-images" in groups or "yale" in groups
    if iiif.get("enabled") and not skip_images and image_group_selected:
        manifest_asset = next(
            item for item in config["assets"] if item["id"] == iiif["manifest_asset_id"]
        )
        manifest_path = _safe_raw_destination(root, manifest_asset["destination"])
        if not manifest_path.exists():
            receipts.append(_download(manifest_asset, root, config["user_agent"]))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        image_assets = iiif_image_assets(manifest, iiif["destination_directory"])
        print(f"Acquiring {len(image_assets)} Yale IIIF canvases...", flush=True)
        with ThreadPoolExecutor(max_workers=int(iiif.get("workers", 4))) as executor:
            futures = {
                executor.submit(_download, asset, root, config["user_agent"]): asset
                for asset in image_assets
            }
            for completed, future in enumerate(as_completed(futures), start=1):
                receipts.append(future.result())
                if completed % 10 == 0 or completed == len(image_assets):
                    print(f"  images: {completed}/{len(image_assets)}", flush=True)
    return receipts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=repository_root() / "config" / "sources" / "voynich-acquisition.yaml",
    )
    parser.add_argument("--group", action="append", help="Acquire only a named group")
    parser.add_argument("--skip-images", action="store_true", help="Do not fetch IIIF images")
    args = parser.parse_args()
    receipts = acquire(args.config, set(args.group) if args.group else None, args.skip_images)
    output = _write_receipts(receipts, repository_root())
    print(f"Recorded {len(receipts)} receipts in {output}")


if __name__ == "__main__":
    main()
