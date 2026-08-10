from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict

from driftbench.duplicates import duplicate_report
from driftbench.governance import DRIFTBENCH_VERSION
from driftbench.intake import IntakeResult
from driftbench.provenance import sha256_file
from driftbench.split_stabilization import split_quality_report
from driftbench.split_audit import split_leakage_report


def write_phase3d_manifests(result: IntakeResult, output_dir: str | Path, *, source_manifest_path: str | Path | None = None) -> Dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
    records = result.accepted_records
    source_manifest_hash = sha256_file(source_manifest_path) if source_manifest_path and Path(source_manifest_path).exists() else None

    duplicate = duplicate_report(records)
    leakage = split_leakage_report(records)
    summary = result.summary()
    summary["split_quality"] = split_quality_report(records)
    summary["eligible_label_distribution"] = _eligible_label_distribution(records)
    summary["eligible_uncertain_count"] = sum(
        1 for record in records
        if record.label in {"uncertain", "needs_review", "excluded"} and record.eligible_for_supervised_training
    )
    summary["creation_timestamp"] = timestamp
    summary["driftbench_version"] = DRIFTBENCH_VERSION
    summary["source_manifest_sha256"] = source_manifest_hash

    payloads: Dict[str, Any] = {
        "dataset_manifest.json": {
            **summary,
            "schema_version": "phase3d-intake-v1",
            "feature_schema_version": "1.0",
            "label_ontology_version": "phase3d-labels-v1",
            "split_version": "phase3d-preserved-splits-v1",
        },
        "provenance_manifest.json": {
            "records": [
                {
                    "record_id": record.pair_id,
                    "provenance_id": f"{record.provenance.source_type}:{record.pair_id}",
                    "extension_id": record.extension_id,
                    "source_type": record.provenance.source_type,
                    "source_reference": record.provenance.source_uri,
                    "old_sha256": record.provenance.old_sha256,
                    "new_sha256": record.provenance.new_sha256,
                    "old_raw_sha256": item.metadata.get("old_raw_sha256"),
                    "new_raw_sha256": item.metadata.get("new_raw_sha256"),
                    "old_normalized_sha256": item.metadata.get("old_normalized_sha256"),
                    "new_normalized_sha256": item.metadata.get("new_normalized_sha256"),
                    "old_download_url": item.metadata.get("old_download_url"),
                    "new_download_url": item.metadata.get("new_download_url"),
                    "old_tag": item.metadata.get("old_tag"),
                    "new_tag": item.metadata.get("new_tag"),
                    "label_source": record.label_source,
                    "label_review_status": record.label_review_status,
                    "label_quality_tier": record.label_quality_tier,
                    "eligible_for_supervised_training": record.eligible_for_supervised_training,
                    "functional_category": record.functional_category,
                    "review_packet_path": record.review_packet_path,
                    "old_manifest_path_in_raw_archive": item.metadata.get("old_manifest_path_in_raw_archive"),
                    "new_manifest_path_in_raw_archive": item.metadata.get("new_manifest_path_in_raw_archive"),
                    "collection_timestamp": record.provenance.collection_timestamp,
                }
                for item in result.accepted
                for record in [item.record]
            ],
            "provenance_complete_count": sum(1 for item in result.accepted if _has_complete_provenance(item)),
        },
        "quality_report.json": {
            "accepted": [_curated_summary(item) for item in result.accepted],
            "quarantined": [_curated_summary(item) for item in result.quarantined],
            "excluded": [_curated_summary(item) for item in result.excluded],
        },
        "duplicate_report.json": duplicate,
        "leakage_report.json": leakage,
        "license_report.json": {
            "license_status_distribution": summary["license_status_distribution"],
            "records": [
                {
                    "record_id": item.record.pair_id,
                    "license": item.metadata.get("license"),
                    "license_status": item.metadata.get("license_status"),
                    "redistribution_allowed": item.metadata.get("redistribution_allowed"),
                    "research_use_allowed": item.metadata.get("research_use_allowed"),
                    "attribution_required": item.metadata.get("attribution_required"),
                    "stage": item.stage,
                }
                for group in (result.accepted, result.quarantined, result.excluded)
                for item in group
            ],
        },
        "validation_report.json": {
            "validation_errors": result.validation_errors,
            "accepted_count": len(result.accepted),
            "quarantined_count": len(result.quarantined),
            "excluded_count": len(result.excluded),
            "reasons": {
                item.record.pair_id: item.reasons
                for group in (result.accepted, result.quarantined, result.excluded)
                for item in group
                if item.reasons
            },
        },
    }

    paths: Dict[str, str] = {}
    for filename, payload in payloads.items():
        path = output / filename
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        paths[filename] = str(path)

    dataset_hash = sha256_file(output / "dataset_manifest.json")
    dataset_manifest = json.loads((output / "dataset_manifest.json").read_text(encoding="utf-8"))
    dataset_manifest["dataset_manifest_sha256"] = dataset_hash
    (output / "dataset_manifest.json").write_text(json.dumps(dataset_manifest, indent=2, sort_keys=True), encoding="utf-8")
    return paths


def _curated_summary(item) -> Dict[str, Any]:
    return {
        "record_id": item.record.pair_id,
        "extension_id": item.record.extension_id,
        "label": item.record.label,
        "label_source": item.metadata.get("label_source"),
        "label_review_status": item.metadata.get("label_review_status"),
        "label_quality_tier": item.metadata.get("label_quality_tier"),
        "eligible_for_supervised_training": item.metadata.get("eligible_for_supervised_training"),
        "functional_category": item.metadata.get("functional_category"),
        "review_packet_path": item.metadata.get("review_packet_path"),
        "stage": item.stage,
        "quality_status": item.quality_status,
        "reasons": list(item.reasons),
    }


def _has_complete_provenance(item) -> bool:
    record = item.record
    required = [
        record.pair_id,
        record.extension_id,
        record.extension_name,
        record.provenance.source_type,
        record.provenance.source_uri,
        record.provenance.collection_timestamp,
        record.provenance.old_sha256,
        record.provenance.new_sha256,
        item.metadata.get("old_raw_sha256"),
        item.metadata.get("new_raw_sha256"),
        item.metadata.get("license_status"),
        item.metadata.get("label_source"),
        item.metadata.get("label_review_status"),
        item.metadata.get("label_quality_tier"),
        item.metadata.get("previous_release_time"),
        item.metadata.get("current_release_time"),
    ]
    return all(required)


def _eligible_label_distribution(records) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for record in records:
        if record.eligible_for_supervised_training:
            counts[record.label] = counts.get(record.label, 0) + 1
    return dict(sorted(counts.items()))
