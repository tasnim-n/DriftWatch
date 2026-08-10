from __future__ import annotations

from typing import Dict, List, Sequence

from research.loaders import METADATA_COLUMNS


FORBIDDEN_FEATURE_TERMS = [
    "label",
    "rationale",
    "risk_score",
    "risk_classification",
    "recommendation",
    "severity",
    "split",
    "path",
    "filename",
    "benign",
    "risky",
    "malicious",
    "conclusion",
]


def leakage_audit(rows: Sequence[Dict[str, str]], feature_names: Sequence[str]) -> Dict:
    violations: List[Dict[str, str]] = []

    for name in feature_names:
        lowered = name.lower()
        for term in FORBIDDEN_FEATURE_TERMS:
            if term in lowered:
                violations.append({"type": "feature_name", "feature": name, "reason": f"contains forbidden term {term}"})

    for row in rows:
        record_id = row.get("record_id", "")
        for name in feature_names:
            value = row.get(name, "")
            if not isinstance(value, str):
                continue
            lowered = value.lower()
            for term in ("benign", "risky", "malicious", "samples", "risk_score"):
                if term in lowered:
                    violations.append({"type": "feature_value", "record_id": record_id, "feature": name, "reason": f"value contains {term}"})

    extension_splits: Dict[str, set] = {}
    for row in rows:
        split = row.get("split", "")
        if split == "controlled_holdout":
            continue
        extension_splits.setdefault(row.get("extension_id", ""), set()).add(split)
    extension_overlap = {}
    for extension_id, splits in extension_splits.items():
        if extension_id and len(splits - {""}) > 1:
            extension_overlap[extension_id] = sorted(splits)
            violations.append({"type": "group_leakage", "extension_id": extension_id, "reason": f"extension appears in multiple splits: {sorted(splits)}"})
    group_split_safe = not extension_overlap

    return {
        "passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
        "metadata_columns": sorted(METADATA_COLUMNS),
        "audited_feature_count": len(feature_names),
        "group_split_safe": group_split_safe,
        "extension_overlap": extension_overlap,
    }
