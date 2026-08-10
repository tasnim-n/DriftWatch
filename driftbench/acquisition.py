from __future__ import annotations

import re
import shutil
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, Iterable
from urllib.parse import urlparse

from driftbench.provenance import sha256_file


ALLOWED_ACQUISITION_SCHEMES = {"https"}
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024


def validate_acquisition_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_ACQUISITION_SCHEMES:
        raise ValueError("only HTTPS acquisition URLs are allowed")
    if not parsed.netloc:
        raise ValueError("acquisition URL must include a host")
    if parsed.username or parsed.password:
        raise ValueError("credentials are not allowed in acquisition URLs")


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    if not cleaned:
        raise ValueError("filename is empty after sanitization")
    return cleaned[:180]


def download_https_package(url: str, output_path: str | Path, *, max_bytes: int = MAX_DOWNLOAD_BYTES, timeout: int = 30) -> Dict[str, str | int]:
    validate_acquisition_url(url)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(url, headers={"User-Agent": "DriftWatch-Research-Intake/0.1"})
    total = 0
    with urllib.request.urlopen(request, timeout=timeout) as response:
        length = response.headers.get("Content-Length")
        if length and int(length) > max_bytes:
            raise ValueError("download exceeds configured size limit")
        with open(output, "wb") as handle:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("download exceeds configured size limit")
                handle.write(chunk)

    return {"path": str(output), "size_bytes": total, "sha256": sha256_file(output)}


def find_manifest_path(zip_path: str | Path) -> str | None:
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        if "manifest.json" in names:
            return "manifest.json"
        candidates = [name for name in names if name.endswith("/manifest.json")]
        if len(candidates) == 1:
            return candidates[0]
    return None


def normalize_extension_zip(input_zip: str | Path, output_zip: str | Path) -> Dict[str, str | bool]:
    source = Path(input_zip)
    destination = Path(output_zip)
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = find_manifest_path(source)
    if not manifest_path:
        raise ValueError("archive does not contain exactly one manifest.json")

    raw_hash = sha256_file(source)
    root_prefix = "" if manifest_path == "manifest.json" else manifest_path.rsplit("/", 1)[0] + "/"
    with zipfile.ZipFile(source) as archive, zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as normalized:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if root_prefix and not info.filename.startswith(root_prefix):
                continue
            normalized_name = info.filename[len(root_prefix):] if root_prefix else info.filename
            if not normalized_name or _unsafe_archive_name(normalized_name):
                continue
            normalized.writestr(normalized_name, archive.read(info.filename))

    if find_manifest_path(destination) != "manifest.json":
        raise ValueError("normalized archive does not expose manifest.json at root")

    return {
        "input_zip": str(source),
        "output_zip": str(destination),
        "raw_sha256": raw_hash,
        "normalized_sha256": sha256_file(destination),
        "manifest_path": manifest_path,
        "normalized_layout": bool(root_prefix),
    }


def _unsafe_archive_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    return normalized.startswith("/") or "/../" in f"/{normalized}/" or normalized.startswith("../")


def normalize_many(paths: Iterable[str | Path], output_dir: str | Path) -> Dict[str, Dict[str, str | bool]]:
    output = Path(output_dir)
    results = {}
    for path in paths:
        source = Path(path)
        normalized_path = output / safe_filename(source.name)
        results[source.name] = normalize_extension_zip(source, normalized_path)
    return results
