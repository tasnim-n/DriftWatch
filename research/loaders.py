from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple


METADATA_COLUMNS = {
    "record_id",
    "provenance_id",
    "extension_id",
    "extension_name",
    "old_version",
    "new_version",
    "old_timestamp",
    "new_timestamp",
    "label",
    "label_source",
    "label_review_status",
    "label_quality_tier",
    "eligible_for_supervised_training",
    "source",
    "source_type",
    "is_controlled",
    "controlled_mutation_type",
    "functional_category",
    "split",
}


def load_feature_rows(csv_path: str | Path) -> List[Dict[str, str]]:
    with open(csv_path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_feature_schema(schema_path: str | Path) -> Dict:
    with open(schema_path, encoding="utf-8") as handle:
        return json.load(handle)


def split_metadata_features(row: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, float]]:
    metadata = {key: value for key, value in row.items() if key in METADATA_COLUMNS}
    features = {}
    for key, value in row.items():
        if key in METADATA_COLUMNS:
            continue
        features[key] = float(value) if value not in ("", None) else 0.0
    return metadata, features


def label_to_binary(label: str) -> int:
    if label == "benign_transition":
        return 0
    if label in {"risky_transition", "controlled_malicious_transition"}:
        return 1
    raise ValueError(f"label is not binary-evaluable: {label}")
