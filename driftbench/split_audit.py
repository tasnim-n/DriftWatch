from __future__ import annotations

from collections import defaultdict
from typing import Dict, Sequence

from driftbench.schema import DatasetPairRecord


PROTECTED_SPLITS = {"train", "validation", "test"}


def split_leakage_report(records: Sequence[DatasetPairRecord]) -> Dict:
    extension_splits = defaultdict(set)
    hash_splits = defaultdict(set)
    controlled_family_splits = defaultdict(set)

    for record in records:
        split = record.split
        if split not in PROTECTED_SPLITS:
            continue
        extension_splits[record.extension_id].add(split)
        for digest in (record.provenance.old_sha256, record.provenance.new_sha256):
            if digest:
                hash_splits[digest].add(split)
        if record.controlled_mutation_type:
            controlled_family_splits[(record.extension_id, record.controlled_mutation_type)].add(split)

    violations = []
    for extension_id, splits in extension_splits.items():
        if extension_id and len(splits) > 1:
            violations.append({"type": "extension_group", "extension_id": extension_id, "splits": sorted(splits)})
    for digest, splits in hash_splits.items():
        if len(splits) > 1:
            violations.append({"type": "package_hash", "sha256": digest, "splits": sorted(splits)})
    for (extension_id, mutation_type), splits in controlled_family_splits.items():
        if len(splits) > 1:
            violations.append({"type": "controlled_mutation_family", "extension_id": extension_id, "mutation_type": mutation_type, "splits": sorted(splits)})

    return {
        "passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }
