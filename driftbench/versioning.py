from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Sequence


@dataclass(frozen=True)
class VersionEntry:
    version: str
    timestamp: str | None = None
    package_path: str | None = None
    metadata: dict | None = None


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def semantic_version_key(version: str) -> tuple[int, ...] | None:
    parts = re.findall(r"\d+", version or "")
    if not parts:
        return None
    return tuple(int(part) for part in parts)


def compare_versions(old_version: str, new_version: str, *, old_timestamp: str | None = None, new_timestamp: str | None = None) -> int | None:
    old_time = parse_timestamp(old_timestamp)
    new_time = parse_timestamp(new_timestamp)
    if old_time and new_time:
        return (new_time > old_time) - (new_time < old_time)

    old_key = semantic_version_key(old_version)
    new_key = semantic_version_key(new_version)
    if old_key is None or new_key is None:
        return None
    return (new_key > old_key) - (new_key < old_key)


def order_versions(versions: Sequence[VersionEntry]) -> List[VersionEntry]:
    def key(entry: VersionEntry):
        timestamp = parse_timestamp(entry.timestamp)
        semver = semantic_version_key(entry.version)
        if timestamp:
            return (0, timestamp)
        if semver:
            return (1, semver)
        return (2, entry.version)

    return sorted(versions, key=key)


def build_consecutive_pairs(versions: Iterable[VersionEntry]) -> List[tuple[VersionEntry, VersionEntry]]:
    ordered = order_versions(list(versions))
    return list(zip(ordered, ordered[1:]))
