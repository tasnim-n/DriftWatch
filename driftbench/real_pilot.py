from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def build_real_pilot_readiness(
    *,
    dataset_manifest_path: str | Path,
    provenance_manifest_path: str | Path,
    duplicate_report_path: str | Path,
    leakage_report_path: str | Path,
    feature_summary_path: str | Path,
    extraction_manifest_path: str | Path,
    existing_controlled_count: int = 0,
) -> Dict[str, Any]:
    dataset = _read_json(dataset_manifest_path)
    provenance = _read_json(provenance_manifest_path)
    duplicate = _read_json(duplicate_report_path)
    leakage = _read_json(leakage_report_path)
    feature_summary = _read_json(feature_summary_path)
    extraction = _read_json(extraction_manifest_path)

    records = provenance.get("records", [])
    timestamp_records = [
        record for record in records
        if record.get("old_tag") and record.get("new_tag")
    ]
    analyzer_missing = feature_summary.get("missingness_counts", {})
    total_missing = sum(analyzer_missing.values())
    feature_records = feature_summary.get("record_count", 0)
    missing_analyzer_rate = 0.0
    if feature_records:
        missing_analyzer_rate = total_missing / feature_records

    uncertain_pairs = dataset.get("label_distribution", {}).get("uncertain", 0)
    split_counts = dataset.get("split_counts", feature_summary.get("split_counts", {}))
    eligible_count = dataset.get("eligible_supervised_training_count", 0)
    label_quality_distribution = dataset.get("label_quality_tier_distribution", {})
    split_quality = dataset.get("split_quality", {})
    test_count = split_counts.get("test", 0)
    test_extensions = split_quality.get("unique_extensions_per_split", {}).get("test", 0)
    eligible_test_labels = split_quality.get("eligible_labels_per_split", {}).get("test", {})
    methodology_block_reasons = []
    warnings = []

    if dataset.get("real_record_count", 0) < 20:
        methodology_block_reasons.append("real record count is below the minimum pilot supervised evaluation threshold")
    if eligible_count < 20:
        methodology_block_reasons.append("fewer than 20 eligible supervised-training real records")
    if test_count < 5:
        methodology_block_reasons.append("test split contains fewer than five records")
    if test_extensions < 2:
        methodology_block_reasons.append("test split contains fewer than two extension identities")
    if not eligible_test_labels:
        methodology_block_reasons.append("test split has no eligible supervised labels")
    elif len(eligible_test_labels) < 2:
        warnings.append("test split has a single eligible supervised label class")
    if provenance.get("provenance_complete_count", 0) != len(records):
        methodology_block_reasons.append("provenance is incomplete for one or more accepted records")
    if not duplicate.get("passed", False):
        methodology_block_reasons.append("duplicate audit failed")
    if not leakage.get("passed", False):
        methodology_block_reasons.append("protected leakage audit failed")
    if extraction.get("failed_records"):
        methodology_block_reasons.append("feature extraction failed for one or more records")
    if uncertain_pairs and dataset.get("eligible_uncertain_count", 0):
        methodology_block_reasons.append("uncertain records are marked eligible for supervised training")
    if not label_quality_distribution:
        methodology_block_reasons.append("label quality distribution is not documented")
    if label_quality_distribution.get("SINGLE_REVIEWER_PROVISIONAL", 0):
        warnings.append("single-reviewer provisional labels remain and must be treated as a limitation")

    phase3e_ready = not methodology_block_reasons
    readiness = {
        "dataset_version": dataset.get("dataset_version"),
        "driftbench_version": dataset.get("driftbench_version"),
        "total_real_records": dataset.get("real_record_count", 0),
        "unique_real_extensions": dataset.get("unique_extension_count", 0),
        "accepted_pairs": dataset.get("accepted", 0),
        "uncertain_pairs": uncertain_pairs,
        "excluded_pairs": dataset.get("excluded", 0),
        "quarantined_pairs": dataset.get("quarantined", 0),
        "label_distribution": dataset.get("label_distribution", {}),
        "label_source_distribution": dataset.get("label_source_distribution", {}),
        "label_quality_tier_distribution": label_quality_distribution,
        "eligible_supervised_training_count": eligible_count,
        "eligible_label_distribution": dataset.get("eligible_label_distribution", {}),
        "eligible_uncertain_count": dataset.get("eligible_uncertain_count", 0),
        "license_distribution": dataset.get("license_status_distribution", {}),
        "license_identifier_distribution": dataset.get("license_identifier_distribution", {}),
        "source_type_distribution": dataset.get("source_type_distribution", {}),
        "provenance_complete_count": provenance.get("provenance_complete_count", 0),
        "provenance_total_count": len(records),
        "timestamp_available_count": len(timestamp_records),
        "timestamp_total_count": len(records),
        "timestamp_source": "github_release_published_at",
        "timestamp_confidence": "medium",
        "duplicate_count": len(duplicate.get("duplicate_record_ids", [])) + len(duplicate.get("duplicate_pairs", [])) + len(duplicate.get("duplicate_package_hashes", {})),
        "adjacent_version_reuse_count": len(duplicate.get("adjacent_version_reuse", {})),
        "duplicate_report_passed": duplicate.get("passed", False),
        "leakage_violations": leakage.get("violation_count", 0),
        "leakage_report_passed": leakage.get("passed", False),
        "missing_analyzer_rate": missing_analyzer_rate,
        "analyzer_missingness": analyzer_missing,
        "feature_extraction_record_count": feature_records,
        "feature_extraction_failed_records": extraction.get("failed_records", []),
        "feature_schema_version": extraction.get("feature_schema_version"),
        "feature_representations": extraction.get("baselines", []),
        "real_vs_controlled_counts": {
            "real_pilot_records": dataset.get("real_record_count", 0),
            "phase3d5_controlled_records": dataset.get("controlled_record_count", 0),
            "existing_controlled_artifact_records": existing_controlled_count,
        },
        "split_distribution": split_counts,
        "split_quality": split_quality,
        "pilot_quality_gate_passed": (
            dataset.get("accepted", 0) > 0
            and dataset.get("unique_extension_count", 0) > 0
            and provenance.get("provenance_complete_count", 0) == len(records)
            and duplicate.get("passed", False)
            and leakage.get("passed", False)
            and not extraction.get("failed_records")
        ),
        "phase3e_ml_re_evaluation_ready": phase3e_ready,
        "phase3e_block_reasons": methodology_block_reasons,
        "phase3e_warnings": warnings,
        "notes": [
            "This readiness report contains descriptive curation facts only.",
            "No classifier performance metrics are reported.",
            "No ML retraining was performed.",
            "Single-reviewer provisional labels are methodology metadata and are not used as predictive features.",
        ],
    }
    return readiness


def write_real_pilot_readiness(output_path: str | Path, **kwargs) -> Dict[str, Any]:
    report = build_real_pilot_readiness(**kwargs)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def _read_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
