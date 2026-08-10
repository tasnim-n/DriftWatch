from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Sequence

from research.loaders import METADATA_COLUMNS


def dataset_readiness_report(rows: Sequence[Dict[str, str]]) -> Dict:
    labels = Counter(row.get("label", "") for row in rows)
    splits = Counter(row.get("split", "") or "unsplit" for row in rows)
    extensions = {row.get("extension_id", "") for row in rows}
    controlled = sum(1 for row in rows if row.get("source_type") == "controlled_sample" or row.get("split") == "controlled_holdout")
    real = len(rows) - controlled
    duplicate_records = [record_id for record_id, count in Counter(row.get("record_id", "") for row in rows).items() if count > 1]

    extensions_by_split = defaultdict(set)
    for row in rows:
        extensions_by_split[row.get("split", "") or "unsplit"].add(row.get("extension_id", ""))

    analyzer_flags = [key for key in rows[0].keys() if key.endswith("_available")] if rows else []
    analyzer_availability = {
        flag: sum(1 for row in rows if str(row.get(flag, "0")) in {"1", "1.0"})
        for flag in analyzer_flags
    }
    missingness = {
        flag: len(rows) - available
        for flag, available in analyzer_availability.items()
    }

    provenance_complete = sum(
        1 for row in rows
        if row.get("provenance_id") and row.get("source_type") and row.get("extension_id") and row.get("record_id")
    )

    train_like = splits.get("train", 0)
    test_like = splits.get("test", 0)
    class_count = len([label for label, count in labels.items() if label and count > 0])
    ml_permitted = (
        len(rows) >= 20
        and train_like >= 10
        and test_like >= 5
        and class_count >= 2
        and real > 0
        and not duplicate_records
    )

    reasons = []
    if len(rows) < 20:
        reasons.append("fewer than 20 records")
    if train_like == 0 or test_like == 0:
        reasons.append("no train/test split assignments")
    if real == 0:
        reasons.append("all records are controlled/synthetic")
    if class_count < 2:
        reasons.append("fewer than two evaluable classes")
    if duplicate_records:
        reasons.append("duplicate record IDs present")

    return {
        "record_count": len(rows),
        "unique_extension_count": len(extensions - {""}),
        "version_pair_count": len(rows),
        "labels": sorted(label for label in labels if label),
        "label_distribution": dict(sorted(labels.items())),
        "split_counts": dict(sorted(splits.items())),
        "unique_extensions_per_split": {split: len(values - {""}) for split, values in sorted(extensions_by_split.items())},
        "controlled_record_count": controlled,
        "real_record_count": real,
        "missingness": missingness,
        "analyzer_availability": analyzer_availability,
        "duplicate_records": duplicate_records,
        "provenance_complete_count": provenance_complete,
        "provenance_incomplete_count": len(rows) - provenance_complete,
        "ml_training_permitted": ml_permitted,
        "ml_block_reasons": reasons,
    }
