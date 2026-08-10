from __future__ import annotations

from collections import defaultdict
from typing import Dict, Sequence

from driftbench.schema import DatasetPairRecord


def duplicate_report(records: Sequence[DatasetPairRecord]) -> Dict:
    record_ids = defaultdict(list)
    pair_keys = defaultdict(list)
    package_hashes = defaultdict(list)

    for record in records:
        record_ids[record.pair_id].append(record.pair_id)
        pair_key = (record.extension_id, record.old_version, record.new_version)
        pair_keys[pair_key].append(record.pair_id)
        if record.provenance.old_sha256:
            package_hashes[record.provenance.old_sha256].append({"record": record, "side": "old"})
        if record.provenance.new_sha256:
            package_hashes[record.provenance.new_sha256].append({"record": record, "side": "new"})

    duplicate_record_ids = sorted(key for key, values in record_ids.items() if key and len(values) > 1)
    duplicate_pairs = [
        {"extension_id": key[0], "old_version": key[1], "new_version": key[2], "record_ids": sorted(values)}
        for key, values in pair_keys.items()
        if len(values) > 1
    ]
    duplicate_package_hashes = {}
    adjacent_version_reuse = {}
    for digest, values in package_hashes.items():
        if not digest or len(values) <= 1:
            continue
        labels = sorted(f"{item['record'].pair_id}:{item['side']}" for item in values)
        if _is_expected_adjacent_reuse(values):
            adjacent_version_reuse[digest] = labels
        else:
            duplicate_package_hashes[digest] = labels

    return {
        "passed": not duplicate_record_ids and not duplicate_pairs and not duplicate_package_hashes,
        "duplicate_record_ids": duplicate_record_ids,
        "duplicate_pairs": duplicate_pairs,
        "duplicate_package_hashes": duplicate_package_hashes,
        "adjacent_version_reuse": adjacent_version_reuse,
    }


def _is_expected_adjacent_reuse(values: list[dict]) -> bool:
    if len(values) != 2:
        return False
    first, second = values
    sides = {first["side"], second["side"]}
    if sides != {"old", "new"}:
        return False
    old_item = first if first["side"] == "old" else second
    new_item = first if first["side"] == "new" else second
    old_record = old_item["record"]
    new_record = new_item["record"]
    return (
        old_record.extension_id == new_record.extension_id
        and old_record.old_version == new_record.new_version
    )
