from __future__ import annotations

import datetime as dt
import random
from collections import defaultdict
from typing import Dict, List, Sequence

from driftbench.schema import DatasetPairRecord


def assign_group_random_splits(
    records: Sequence[DatasetPairRecord],
    *,
    train_ratio: float = 0.7,
    validation_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 1337,
) -> Dict[str, str]:
    _validate_ratios(train_ratio, validation_ratio, test_ratio)
    groups = sorted({record.extension_id for record in records})
    rng = random.Random(seed)
    rng.shuffle(groups)

    total = len(groups)
    train_cut = int(total * train_ratio)
    validation_cut = train_cut + int(total * validation_ratio)

    assignments = {}
    for index, extension_id in enumerate(groups):
        if index < train_cut:
            split = "train"
        elif index < validation_cut:
            split = "validation"
        else:
            split = "test"
        assignments[extension_id] = split
    return assignments


def assign_chronological_group_splits(
    records: Sequence[DatasetPairRecord],
    *,
    train_ratio: float = 0.7,
    validation_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> Dict[str, str]:
    _validate_ratios(train_ratio, validation_ratio, test_ratio)
    grouped = defaultdict(list)
    for record in records:
        grouped[record.extension_id].append(record)

    ordered_groups = sorted(
        grouped.keys(),
        key=lambda extension_id: _group_sort_timestamp(grouped[extension_id]),
    )

    total = len(ordered_groups)
    train_cut = int(total * train_ratio)
    validation_cut = train_cut + int(total * validation_ratio)

    assignments = {}
    for index, extension_id in enumerate(ordered_groups):
        if index < train_cut:
            split = "train"
        elif index < validation_cut:
            split = "validation"
        else:
            split = "test"
        assignments[extension_id] = split
    return assignments


def apply_split_assignments(records: Sequence[DatasetPairRecord], assignments: Dict[str, str]) -> List[DatasetPairRecord]:
    for record in records:
        record.split = assignments.get(record.extension_id)
    return list(records)


def _validate_ratios(train_ratio: float, validation_ratio: float, test_ratio: float) -> None:
    total = train_ratio + validation_ratio + test_ratio
    if abs(total - 1.0) > 1e-6:
        raise ValueError("split ratios must sum to 1.0")
    if min(train_ratio, validation_ratio, test_ratio) < 0:
        raise ValueError("split ratios must be non-negative")


def _parse_timestamp(value: str | None) -> dt.datetime:
    if not value:
        return dt.datetime.max.replace(tzinfo=dt.timezone.utc)
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _group_sort_timestamp(records: Sequence[DatasetPairRecord]) -> dt.datetime:
    return max(_parse_timestamp(record.new_timestamp) for record in records)
