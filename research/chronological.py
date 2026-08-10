from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def chronological_evaluation_status(rows: Iterable[dict]) -> Dict:
    materialized = list(rows)
    dated = [row for row in materialized if parse_timestamp(row.get("new_timestamp"))]
    splits = {row.get("split", "") for row in materialized}
    if len(dated) != len(materialized) or not materialized:
        return {
            "status": "not_run_unavailable_timestamps_or_splits",
            "qualified_record_count": len(dated),
            "reason": "missing or invalid transition timestamps",
        }
    if not {"train", "test"} <= splits:
        return {
            "status": "not_run_unavailable_timestamps_or_splits",
            "qualified_record_count": len(dated),
            "reason": "train/test split assignments unavailable",
        }
    return {
        "status": "ready",
        "qualified_record_count": len(dated),
        "reason": "timestamps and train/test splits are available",
    }


def chronological_order(rows: Iterable[dict]) -> List[dict]:
    materialized = list(rows)
    if any(parse_timestamp(row.get("new_timestamp")) is None for row in materialized):
        raise ValueError("all rows must have valid new_timestamp values")
    return sorted(materialized, key=lambda row: parse_timestamp(row.get("new_timestamp")))
