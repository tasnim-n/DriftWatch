import hashlib
from pathlib import Path
from typing import Optional


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_license(value: Optional[str]) -> str:
    if not value or not value.strip():
        return "unknown"
    return value.strip()
