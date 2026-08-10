from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Any, Dict, Sequence

from driftbench.schema import DatasetPairRecord
from driftbench.split_audit import split_leakage_report


PROTECTED_SPLITS = ("train", "validation", "test")


def split_quality_report(records: Sequence[DatasetPairRecord], *, minimum_test_records: int = 5) -> Dict[str, Any]:
    split_counts: dict[str, int] = defaultdict(int)
    split_extensions: dict[str, set[str]] = {split: set() for split in PROTECTED_SPLITS}
    split_labels: dict[str, dict[str, int]] = {split: {} for split in PROTECTED_SPLITS}
    split_eligible_labels: dict[str, dict[str, int]] = {split: {} for split in PROTECTED_SPLITS}
    split_real_controlled: dict[str, dict[str, int]] = {split: {"real": 0, "controlled": 0} for split in PROTECTED_SPLITS}
    extension_counts: dict[str, int] = defaultdict(int)
    category_counts: dict[str, int] = defaultdict(int)

    for record in records:
        split = record.split or "unsplit"
        split_counts[split] += 1
        extension_counts[record.extension_id] += 1
        category_counts[record.functional_category or "unknown"] += 1
        if split in split_extensions:
            split_extensions[split].add(record.extension_id)
            _increment(split_labels[split], record.label)
            if record.eligible_for_supervised_training:
                _increment(split_eligible_labels[split], record.label)
            bucket = "controlled" if record.controlled_mutation_type else "real"
            split_real_controlled[split][bucket] += 1

    leakage = split_leakage_report(records)
    test_count = split_counts.get("test", 0)
    test_extension_count = len(split_extensions["test"])
    test_eligible_labels = split_eligible_labels["test"]
    warnings: list[str] = []
    block_reasons: list[str] = []

    if test_count < minimum_test_records:
        block_reasons.append("test split contains fewer than five records")
    if test_extension_count < 2:
        block_reasons.append("test split contains fewer than two extension identities")
    if len(test_eligible_labels) < 2:
        warnings.append("test split has a single eligible supervised label class")
    if not leakage.get("passed", False):
        block_reasons.append("protected split leakage detected")

    pair_counts = list(extension_counts.values())
    return {
        "split_counts": dict(sorted(split_counts.items())),
        "unique_extensions_per_split": {split: len(values) for split, values in split_extensions.items()},
        "labels_per_split": {split: dict(sorted(values.items())) for split, values in split_labels.items()},
        "eligible_labels_per_split": {split: dict(sorted(values.items())) for split, values in split_eligible_labels.items()},
        "real_controlled_per_split": split_real_controlled,
        "unique_extension_count": len(extension_counts),
        "version_pair_distribution_per_extension": dict(sorted(extension_counts.items())),
        "pair_count_stats_per_extension": {
            "min": min(pair_counts) if pair_counts else 0,
            "max": max(pair_counts) if pair_counts else 0,
            "median": median(pair_counts) if pair_counts else 0,
        },
        "functional_category_distribution": dict(sorted(category_counts.items())),
        "leakage_passed": leakage.get("passed", False),
        "leakage_violations": leakage.get("violations", []),
        "warnings": warnings,
        "block_reasons": block_reasons,
        "minimum_test_quality_passed": not block_reasons,
    }


def _increment(counts: dict[str, int], value: str) -> None:
    counts[value] = counts.get(value, 0) + 1
