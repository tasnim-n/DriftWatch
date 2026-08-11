from __future__ import annotations

import csv
import json
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from analyzers.manifest_analyzer import ManifestAnalyzer
from analyzers.permission_analyzer import PermissionAnalyzer
from analyzers.drift_engine import DriftEngine
from driftbench.acquisition import download_https_package, normalize_extension_zip, safe_filename
from driftbench.duplicates import duplicate_report as driftbench_duplicate_report
from driftbench.features import BASELINES, DriftBenchFeatureExtractor
from driftbench.schema import DatasetPairRecord, ProvenanceRecord
from driftbench.split_audit import split_leakage_report
from driftbench.split_stabilization import split_quality_report
from driftbench.validator import DatasetValidator
from research.phase3e import build_leakage_audit, read_json, write_csv, write_json, write_jsonl
from research.phase3f import (
    PHASE3F_DATASET_VERSION,
    PHASE3F_SPLIT_ASSIGNMENTS,
    analysis_archive_path_and_sha256,
    compare_manifest_dicts,
    get_git_commit,
    load_csv,
    public_github_releases,
    read_manifest_from_zip,
    refresh_release_asset_hashes,
    relative_path,
    safe_record_id,
    select_asset,
    sha256_file,
    stringify_rows,
)


PHASE3G_DATASET_VERSION = "driftbench-real-maturation-phase3g-v1"
PHASE3G_SPLIT_VERSION = "phase3g-group-safe-label-quality-v1"

PHASE3G_REPOSITORIES = [
    {
        "repo": "libredirect/browser_extension",
        "extension_id": "github:libredirect/browser_extension",
        "extension_name": "LibRedirect",
        "functional_category": "privacy_redirect",
        "category_source": "repository_project_description",
        "license": "GPL-3.0",
        "asset_prefix": "libredirect-",
        "asset_suffix": ".zip",
        "max_releases": 5,
        "split": "train",
    },
    {
        "repo": "web-scrobbler/web-scrobbler",
        "extension_id": "github:web-scrobbler/web-scrobbler",
        "extension_name": "Web Scrobbler",
        "functional_category": "media_scrobbling",
        "category_source": "repository_project_description",
        "license": "MIT",
        "asset_name": "web-scrobbler-chrome.zip",
        "max_releases": 5,
        "split": "validation",
    },
    {
        "repo": "AutomaApp/automa",
        "extension_id": "github:automaapp/automa",
        "extension_name": "Automa",
        "functional_category": "browser_automation",
        "category_source": "repository_project_description",
        "license": "GPL-3.0",
        "asset_prefix": "automa-chrome-",
        "asset_suffix": ".zip",
        "max_releases": 5,
        "split": "train",
    },
    {
        "repo": "iorate/ublacklist",
        "extension_id": "github:iorate/ublacklist",
        "extension_name": "uBlacklist",
        "functional_category": "search_result_filtering",
        "category_source": "repository_project_description",
        "license": "MIT",
        "asset_contains": "chrome",
        "asset_suffix": ".zip",
        "max_releases": 5,
        "split": "test",
    },
]

PHASE3G_SECURITY_EXCLUDED_EXTENSION_IDS = {
    "github:iorate/ublacklist": (
        "Downloaded uBlacklist candidate packages were not accepted because static feature extraction "
        "hit DriftWatch zip-bomb compression-ratio protection on bundled notice files. Security limits "
        "were preserved instead of force-extracting the packages."
    )
}


def run_phase3g_maturation(
    *,
    phase3f_feature_dir: str | Path = "artifacts/driftbench/phase3f_features",
    phase3f_curation_dir: str | Path = "artifacts/driftbench/phase3f",
    phase3f_experiment_dir: str | Path = "artifacts/experiments/phase3f",
    incoming_dir: str | Path = "datasets/incoming/phase3g",
    validated_dir: str | Path = "datasets/validated/phase3g_packages",
    manifest_path: str | Path = "datasets/manifests/phase3g_import_manifest.json",
    curation_dir: str | Path = "artifacts/driftbench/phase3g",
    feature_dir: str | Path = "artifacts/driftbench/phase3g_features",
    experiment_dir: str | Path = "artifacts/experiments/phase3g",
    seed: int = 1337,
    max_download_bytes: int = 20 * 1024 * 1024,
) -> Dict[str, Any]:
    started = time.perf_counter()
    phase3f_feature_dir = Path(phase3f_feature_dir)
    phase3f_curation_dir = Path(phase3f_curation_dir)
    phase3f_experiment_dir = Path(phase3f_experiment_dir)
    incoming_dir = Path(incoming_dir)
    validated_dir = Path(validated_dir)
    manifest_path = Path(manifest_path)
    curation_dir = Path(curation_dir)
    feature_dir = Path(feature_dir)
    experiment_dir = Path(experiment_dir)
    review_packet_dir = curation_dir / "review_packets"
    for path in (incoming_dir, validated_dir, manifest_path.parent, curation_dir, feature_dir, experiment_dir, review_packet_dir):
        path.mkdir(parents=True, exist_ok=True)

    phase3f_reference = freeze_phase3f_reference(phase3f_curation_dir, phase3f_feature_dir, phase3f_experiment_dir)
    if manifest_path.exists():
        cached_manifest = read_json(manifest_path)
        new_releases = cached_manifest.get("new_release_assets", {})
    else:
        new_releases = acquire_phase3g_release_assets(
            incoming_dir=incoming_dir,
            validated_dir=validated_dir,
            max_download_bytes=max_download_bytes,
        )
    refresh_release_asset_hashes(new_releases)
    excluded_releases = {
        extension_id: {
            "reason": PHASE3G_SECURITY_EXCLUDED_EXTENSION_IDS[extension_id],
            "release_count": len(releases),
            "releases": releases,
        }
        for extension_id, releases in new_releases.items()
        if extension_id in PHASE3G_SECURITY_EXCLUDED_EXTENSION_IDS
    }
    new_releases = {
        extension_id: releases
        for extension_id, releases in new_releases.items()
        if extension_id not in PHASE3G_SECURITY_EXCLUDED_EXTENSION_IDS
    }

    records = build_phase3g_records(phase3f_curation_dir, new_releases)
    validation = DatasetValidator.validate_records(records, base_dir=".", validate_paths=True)
    duplicate_report = driftbench_duplicate_report(records)
    leakage_report = split_leakage_report(records)
    split_quality = split_quality_report(records)
    label_quality_report = build_label_quality_report(records)
    provenance_manifest = build_provenance_manifest(records, new_releases)
    analyzer_missingness = build_analyzer_missingness(records, phase3f_feature_dir)
    review_packets = write_uncertain_review_packets(records, review_packet_dir)
    second_review_queue = build_second_review_queue(records)
    inter_rater = build_inter_rater_report(records)
    dataset_manifest = build_dataset_manifest(records, split_quality, label_quality_report, analyzer_missingness)
    readiness = build_readiness(dataset_manifest, validation, duplicate_report, leakage_report, analyzer_missingness, provenance_manifest)
    diversity = build_diversity_report(records)

    write_json(curation_dir / "phase3f_reference.json", phase3f_reference)
    write_json(curation_dir / "dataset_manifest.json", dataset_manifest)
    write_json(curation_dir / "provenance_manifest.json", provenance_manifest)
    write_json(curation_dir / "validation_report.json", {
        "is_valid": validation.is_valid,
        "errors": validation.errors,
        "warnings": validation.warnings,
    })
    write_json(curation_dir / "duplicate_report.json", duplicate_report)
    write_json(curation_dir / "leakage_report.json", leakage_report)
    write_json(curation_dir / "split_quality_report.json", split_quality)
    write_json(curation_dir / "label_quality_report.json", label_quality_report)
    write_json(curation_dir / "analyzer_missingness.json", analyzer_missingness)
    write_json(curation_dir / "reviewer_schema.json", reviewer_schema())
    write_json(curation_dir / "second_review_queue.json", second_review_queue)
    write_json(curation_dir / "inter_rater_agreement.json", inter_rater)
    write_json(curation_dir / "diversity_report.json", diversity)
    write_json(curation_dir / "uncertain_review_packets.json", {"packet_count": len(review_packets), "records": review_packets})
    write_json(curation_dir / "readiness.json", readiness)
    write_json(curation_dir / "excluded_candidate_assets.json", {
        "excluded_extension_count": len(excluded_releases),
        "policy": "Candidate packages that fail DriftWatch security limits are excluded rather than force-extracted.",
        "excluded": excluded_releases,
    })
    write_human_review_queue(curation_dir / "second_review_queue.md", second_review_queue)
    write_phase3g_import_manifest(manifest_path, records, new_releases, excluded_releases)

    if validation.errors:
        raise ValueError(f"Phase 3G validation failed: {validation.errors}")
    if not duplicate_report["passed"]:
        raise ValueError("Phase 3G duplicate audit failed")
    if not leakage_report["passed"]:
        raise ValueError("Phase 3G leakage audit failed")

    if phase3g_feature_cache_valid(feature_dir, expected_records=len(records)):
        feature_status = read_json(feature_dir / "extraction_manifest.json")
    else:
        new_records = [record for record in records if "Phase 3G corpus maturation record" in record.notes]
        extraction = DriftBenchFeatureExtractor(base_dir=".").extract(new_records)
        if not extraction.is_valid:
            raise ValueError(f"Phase 3G feature extraction failed: {extraction.validation_errors or extraction.failed_records}")
        write_phase3g_feature_artifacts(
            phase3f_feature_dir,
            extraction,
            feature_dir,
            generation_timestamp=datetime.now(timezone.utc).isoformat(),
            code_version=get_git_commit(),
            seed=seed,
        )
        feature_status = read_json(feature_dir / "extraction_manifest.json")

    feature_rows = {name: load_csv(feature_dir / f"{name}.csv") for name in BASELINES}
    feature_leakage_audit = build_leakage_audit(feature_rows)
    if not feature_leakage_audit["passed"]:
        raise ValueError("Phase 3G feature leakage audit failed")
    write_json(experiment_dir / "feature_leakage_audit.json", feature_leakage_audit)

    comparison_rows = build_phase3f_vs_phase3g_dataset_comparison(phase3f_curation_dir, dataset_manifest, readiness)
    write_csv(experiment_dir / "phase3f_vs_phase3g_dataset.csv", comparison_rows)

    dataset_snapshot = build_dataset_snapshot(records, phase3f_reference, curation_dir, dataset_manifest, provenance_manifest)
    experiment_manifest = {
        "phase": "Phase 3G",
        "dataset_version": PHASE3G_DATASET_VERSION,
        "purpose": "real-corpus expansion and independent label-strengthening infrastructure",
        "production_ml_integration": False,
        "model_training_performed": False,
        "feature_regeneration_status": "completed",
        "feature_schema_version": "1.0",
        "split_version": PHASE3G_SPLIT_VERSION,
        "total_runtime_seconds": round(time.perf_counter() - started, 4),
        "warnings_investigated": known_warning_report(),
    }
    write_json(experiment_dir / "dataset_snapshot.json", dataset_snapshot)
    write_json(experiment_dir / "readiness.json", readiness)
    write_json(experiment_dir / "experiment_manifest.json", experiment_manifest)
    write_json(experiment_dir / "phase3f_reference.json", phase3f_reference)

    return {
        "dataset_snapshot": dataset_snapshot,
        "dataset_manifest": dataset_manifest,
        "readiness": readiness,
        "comparison_rows": comparison_rows,
        "feature_status": feature_status,
        "phase3f_reference": phase3f_reference,
    }


def acquire_phase3g_release_assets(*, incoming_dir: Path, validated_dir: Path, max_download_bytes: int) -> Dict[str, List[Dict[str, Any]]]:
    acquired: Dict[str, List[Dict[str, Any]]] = {}
    for spec in PHASE3G_REPOSITORIES:
        releases = public_github_releases(spec["repo"], per_page=12)
        selected = []
        for release in releases:
            if release.get("draft") or release.get("prerelease"):
                continue
            asset = select_asset(release.get("assets", []), spec)
            if not asset:
                continue
            selected.append({"release": release, "asset": asset})
            if len(selected) == spec["max_releases"]:
                break
        selected = sorted(selected, key=lambda item: item["release"]["published_at"])
        if len(selected) < 2:
            raise ValueError(f"not enough usable releases for {spec['repo']}")
        records = []
        for item in selected:
            release = item["release"]
            asset = item["asset"]
            version = release["tag_name"].lstrip("v").replace("release-", "")
            filename = safe_filename(f"{spec['repo'].replace('/', '_')}_{release['tag_name']}_{asset['name']}")
            raw_path = incoming_dir / filename
            normalized_path = validated_dir / filename
            if not raw_path.exists():
                download_https_package(asset["browser_download_url"], raw_path, max_bytes=max_download_bytes, timeout=60)
            raw_info = normalize_extension_zip(raw_path, normalized_path)
            records.append({
                "repo": spec["repo"],
                "extension_id": spec["extension_id"],
                "extension_name": spec["extension_name"],
                "functional_category": spec["functional_category"],
                "category_source": spec["category_source"],
                "license": spec["license"],
                "version": version,
                "tag": release["tag_name"],
                "timestamp": release["published_at"],
                "timestamp_source": "github_release_published_at",
                "release_url": release["html_url"],
                "download_url": asset["browser_download_url"],
                "raw_path": str(raw_path),
                "normalized_path": str(normalized_path),
                "raw_sha256": raw_info["raw_sha256"],
                "normalized_sha256": raw_info["normalized_sha256"],
                "manifest_path": raw_info["manifest_path"],
                "split": spec["split"],
            })
        acquired[spec["extension_id"]] = records
    return acquired


def build_phase3g_records(phase3f_curation_dir: Path, new_releases: Dict[str, List[Dict[str, Any]]]) -> List[DatasetPairRecord]:
    phase3f_manifest = read_json(phase3f_curation_dir / "dataset_manifest.json")
    phase3f_records = [record_from_dict(row) for row in phase3f_manifest["records"]]
    phase3g_records = []
    for releases in new_releases.values():
        for old, new in zip(releases, releases[1:]):
            phase3g_records.append(record_from_release_pair(old, new))
    return phase3f_records + phase3g_records


def record_from_dict(row: Dict[str, Any]) -> DatasetPairRecord:
    provenance = row["provenance"]
    notes = list(row.get("notes", []))
    notes.append("PHASE3F_FROZEN_BASELINE")
    return DatasetPairRecord(
        pair_id=row["pair_id"],
        extension_id=row["extension_id"],
        extension_name=row["extension_name"],
        old_version=row["old_version"],
        new_version=row["new_version"],
        old_archive_path=row["old_archive_path"],
        new_archive_path=row["new_archive_path"],
        old_timestamp=row.get("old_timestamp"),
        new_timestamp=row.get("new_timestamp"),
        source=row["source"],
        license=row["license"],
        label=row["label"],
        label_rationale=row["label_rationale"],
        provenance=ProvenanceRecord(
            source_type=provenance["source_type"],
            source_uri=provenance["source_uri"],
            collection_timestamp=provenance["collection_timestamp"],
            license=provenance["license"],
            collector=provenance["collector"],
            old_sha256=provenance.get("old_sha256"),
            new_sha256=provenance.get("new_sha256"),
            generation_method=provenance.get("generation_method"),
            notes=list(provenance.get("notes", [])) + ["Preserved unchanged from frozen Phase 3F dataset history."],
        ),
        controlled_mutation_type=row.get("controlled_mutation_type"),
        label_confidence=row.get("label_confidence", "medium"),
        label_source=row.get("label_source", "unknown"),
        label_review_status=row.get("label_review_status", "provisional"),
        label_quality_tier=row.get("label_quality_tier", "UNCERTAIN"),
        eligible_for_supervised_training=bool(row.get("eligible_for_supervised_training")),
        functional_category=row.get("functional_category"),
        review_packet_path=row.get("review_packet_path"),
        split=row.get("split") or PHASE3F_SPLIT_ASSIGNMENTS[row["extension_id"]],
        notes=notes,
    )


def record_from_release_pair(old: Dict[str, Any], new: Dict[str, Any]) -> DatasetPairRecord:
    old_analysis_path, old_analysis_sha256 = analysis_archive_path_and_sha256(old)
    new_analysis_path, new_analysis_sha256 = analysis_archive_path_and_sha256(new)
    manifest_diff = compare_manifest_dicts(read_manifest_from_zip(old_analysis_path), read_manifest_from_zip(new_analysis_path))
    label, confidence, rationale = provisional_label_from_manifest(manifest_diff)
    pair_id = safe_record_id(f"{new['repo']}_{old['version']}_to_{new['version']}")
    return DatasetPairRecord(
        pair_id=pair_id,
        extension_id=new["extension_id"],
        extension_name=new["extension_name"],
        old_version=old["version"],
        new_version=new["version"],
        old_archive_path=relative_path(old_analysis_path),
        new_archive_path=relative_path(new_analysis_path),
        old_timestamp=old["timestamp"],
        new_timestamp=new["timestamp"],
        source=f"https://github.com/{new['repo']}",
        license=new["license"],
        label=label,
        label_rationale=rationale,
        provenance=ProvenanceRecord(
            source_type="open_source_repository",
            source_uri=f"https://github.com/{new['repo']}",
            collection_timestamp=datetime.now(timezone.utc).isoformat(),
            license=new["license"],
            collector="codex-phase3g-public-github-release-assets",
            old_sha256=old_analysis_sha256,
            new_sha256=new_analysis_sha256,
            notes=[
                "Phase 3G corpus maturation record.",
                "Public GitHub release assets acquired over normal HTTPS.",
                "Extension JavaScript was never executed.",
                f"old_release={old['release_url']}",
                f"new_release={new['release_url']}",
            ],
        ),
        label_confidence=confidence,
        label_source="single_reviewer_manifest_and_release_review",
        label_review_status="provisional",
        label_quality_tier="SINGLE_REVIEWER_PROVISIONAL" if label != "uncertain" else "UNCERTAIN",
        eligible_for_supervised_training=label not in {"uncertain", "excluded"},
        functional_category=new["functional_category"],
        split=new["split"],
        notes=[
            "Phase 3G corpus maturation record",
            f"category_source={new['category_source']}",
            "second_review_required_before stronger label tier",
            "ground_truth_not_derived_from_driftwatch_score",
        ],
    )


def provisional_label_from_manifest(manifest_diff: Dict[str, Any]) -> tuple[str, str, str]:
    added_permissions = manifest_diff.get("added_permissions", [])
    added_hosts = manifest_diff.get("added_hosts", [])
    sensitive_added = any(
        PermissionAnalyzer.PERMISSION_RISK_MAP.get(permission, {"level": "Moderate"}).get("level") in {"High", "Critical"}
        for permission in added_permissions
    )
    externally_connectable_changed = manifest_diff.get("v1_raw", {}).get("externally_connectable") != manifest_diff.get("v2_raw", {}).get("externally_connectable")
    background_added = bool(manifest_diff.get("background_added"))
    if sensitive_added or added_hosts or externally_connectable_changed:
        return (
            "risky_transition",
            "medium",
            "Single-reviewer provisional label: package manifest evidence shows security-review-worthy capability expansion. This label is independent of DriftWatch score and is not a maliciousness claim.",
        )
    if background_added:
        return (
            "uncertain",
            "low",
            "Single-reviewer provisional review found a new background context but no independent evidence sufficient to resolve the transition. Retained for second review.",
        )
    return (
        "benign_transition",
        "medium",
        "Single-reviewer provisional label: manifest review did not identify added sensitive permissions, host expansion, externally_connectable expansion, or other independently review-worthy capability change.",
    )


def build_label_quality_report(records: Sequence[DatasetPairRecord]) -> Dict[str, Any]:
    return {
        "label_distribution": dict(Counter(record.label for record in records)),
        "label_quality_distribution": dict(Counter(record.label_quality_tier for record in records)),
        "label_source_distribution": dict(Counter(record.label_source for record in records)),
        "eligible_supervised_training_count": sum(1 for record in records if record.eligible_for_supervised_training),
        "uncertain_count": sum(1 for record in records if record.label == "uncertain"),
        "uncertain_training_eligible_count": sum(1 for record in records if record.label == "uncertain" and record.eligible_for_supervised_training),
        "double_reviewed_count": sum(1 for record in records if record.label_quality_tier == "MULTI_REVIEWER_ADJUDICATED"),
        "status": "single_reviewer_provisional_labels_remain",
    }


def build_provenance_manifest(records: Sequence[DatasetPairRecord], new_releases: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    payload_records = []
    for record in records:
        payload_records.append({
            "record_id": record.pair_id,
            "provenance_id": f"{record.provenance.source_type}:{record.pair_id}",
            "extension_id": record.extension_id,
            "extension_name": record.extension_name,
            "source_type": record.provenance.source_type,
            "repository": record.source,
            "source_url": record.source,
            "license": record.license,
            "old_version": record.old_version,
            "new_version": record.new_version,
            "old_release_identifier": record.old_version,
            "new_release_identifier": record.new_version,
            "old_timestamp": record.old_timestamp,
            "new_timestamp": record.new_timestamp,
            "timestamp_source": "github_release_published_at",
            "old_sha256": record.provenance.old_sha256,
            "new_sha256": record.provenance.new_sha256,
            "acquisition_timestamp": record.provenance.collection_timestamp,
            "label": record.label,
            "label_source": record.label_source,
            "label_quality": record.label_quality_tier,
            "review_status": record.label_review_status,
            "reviewer_metadata": reviewer_metadata_for(record),
            "split": record.split,
            "eligible_for_supervised_training": record.eligible_for_supervised_training,
            "is_phase3g_record": "Phase 3G corpus maturation record" in record.notes,
            "is_phase3f_frozen_baseline": "PHASE3F_FROZEN_BASELINE" in record.notes,
        })
    return {
        "provenance_complete_count": sum(1 for record in payload_records if record["old_sha256"] and record["new_sha256"] and record["source_url"]),
        "timestamp_complete_count": sum(1 for record in payload_records if record["old_timestamp"] and record["new_timestamp"]),
        "records": payload_records,
        "new_release_assets": new_releases,
    }


def reviewer_metadata_for(record: DatasetPairRecord) -> Dict[str, Any]:
    return {
        "primary_reviewer_id": "codex_static_manifest_reviewer",
        "independent_second_reviewer_id": None,
        "reviewer_confidence": record.label_confidence,
        "disagreement_flag": False,
        "adjudication_status": "not_applicable_single_reviewer" if record.label_quality_tier != "UNCERTAIN" else "pending_second_review",
        "adjudicated_label": None,
        "adjudication_rationale": None,
    }


def build_dataset_manifest(
    records: Sequence[DatasetPairRecord],
    split_quality: Dict[str, Any],
    label_quality_report: Dict[str, Any],
    analyzer_missingness: Dict[str, Any],
) -> Dict[str, Any]:
    phase3g_count = sum(1 for record in records if "Phase 3G corpus maturation record" in record.notes)
    return {
        "dataset_version": PHASE3G_DATASET_VERSION,
        "previous_dataset_version": PHASE3F_DATASET_VERSION,
        "schema_version": "phase3d-intake-v1",
        "ontology_version": "phase3d-labels-v1",
        "feature_schema_version": "1.0",
        "split_version": PHASE3G_SPLIT_VERSION,
        "creation_timestamp": datetime.now(timezone.utc).isoformat(),
        "accepted": len(records),
        "new_phase3g_record_count": phase3g_count,
        "real_record_count": len(records),
        "controlled_record_count": 0,
        "unique_extension_count": len({record.extension_id for record in records}),
        "label_distribution": dict(Counter(record.label for record in records)),
        "eligible_label_distribution": dict(Counter(record.label for record in records if record.eligible_for_supervised_training)),
        "label_quality_tier_distribution": dict(Counter(record.label_quality_tier for record in records)),
        "label_source_distribution": dict(Counter(record.label_source for record in records)),
        "license_identifier_distribution": dict(Counter(record.license for record in records)),
        "source_type_distribution": dict(Counter(record.provenance.source_type for record in records)),
        "split_counts": dict(Counter(record.split for record in records)),
        "training_eligible_count": sum(1 for record in records if record.eligible_for_supervised_training),
        "uncertain_count": sum(1 for record in records if record.label == "uncertain"),
        "risky_review_worthy_count": sum(1 for record in records if record.label in {"risky_transition", "malicious_transition"}),
        "split_quality": split_quality,
        "label_quality_report": label_quality_report,
        "analyzer_missingness": analyzer_missingness,
        "records": [record.to_dict() for record in records],
    }


def build_readiness(
    dataset_manifest: Dict[str, Any],
    validation,
    duplicate_report: Dict[str, Any],
    leakage_report: Dict[str, Any],
    analyzer_missingness: Dict[str, Any],
    provenance_manifest: Dict[str, Any],
) -> Dict[str, Any]:
    block_reasons = []
    warnings = []
    if not validation.is_valid:
        block_reasons.append("dataset validation failed")
    if not duplicate_report.get("passed"):
        block_reasons.append("duplicate audit failed")
    if not leakage_report.get("passed"):
        block_reasons.append("protected split leakage detected")
    if dataset_manifest["real_record_count"] < 60:
        warnings.append("planning target of 60+ real records was not reached")
    if dataset_manifest["unique_extension_count"] < 18:
        warnings.append("planning target of 18+ unique extensions was not reached")
    if dataset_manifest["label_quality_tier_distribution"].get("SINGLE_REVIEWER_PROVISIONAL"):
        warnings.append("single-reviewer provisional labels still dominate")
    if dataset_manifest["label_quality_tier_distribution"].get("UNCERTAIN"):
        warnings.append("uncertain records remain in review queue and are training-ineligible")
    if analyzer_missingness["total_missingness_count"]:
        warnings.append("some optional analyzer outputs are unavailable and tracked explicitly")
    return {
        "dataset_version": PHASE3G_DATASET_VERSION,
        "previous_dataset_version": PHASE3F_DATASET_VERSION,
        "phase3g_complete": not block_reasons,
        "recommended_next_phase": "READY FOR STRONGER INDEPENDENT REPLICATION" if not block_reasons and dataset_manifest["real_record_count"] >= 60 and dataset_manifest["unique_extension_count"] >= 18 else "DATASET STILL TOO WEAK - CONTINUE EXPANSION",
        "block_reasons": block_reasons,
        "warnings": warnings,
        "real_records": dataset_manifest["real_record_count"],
        "controlled_records": dataset_manifest["controlled_record_count"],
        "unique_extensions": dataset_manifest["unique_extension_count"],
        "labels": dataset_manifest["label_distribution"],
        "label_quality": dataset_manifest["label_quality_tier_distribution"],
        "eligible_records": dataset_manifest["training_eligible_count"],
        "uncertain_records": dataset_manifest["uncertain_count"],
        "excluded_records": dataset_manifest["label_distribution"].get("excluded", 0),
        "double_reviewed_records": dataset_manifest["label_quality_tier_distribution"].get("MULTI_REVIEWER_ADJUDICATED", 0),
        "provenance_completeness": f"{provenance_manifest['provenance_complete_count']}/{dataset_manifest['accepted']}",
        "timestamp_completeness": f"{provenance_manifest['timestamp_complete_count']}/{dataset_manifest['accepted']}",
        "duplicate_audit_passed": duplicate_report.get("passed"),
        "leakage_audit_passed": leakage_report.get("passed"),
        "analyzer_missingness": analyzer_missingness,
        "split_counts": dataset_manifest["split_counts"],
    }


def build_analyzer_missingness(records: Sequence[DatasetPairRecord], phase3f_feature_dir: Path) -> Dict[str, Any]:
    counts = Counter()
    rows = load_csv(phase3f_feature_dir / "full_driftwatch.csv")
    for row in rows:
        for key, value in row.items():
            if key.endswith("_available") and value in {"0", "0.0", "False"}:
                counts[key] += 1
    return {
        "record_count": len(records),
        "missingness_counts": dict(sorted(counts.items())),
        "total_missingness_count": sum(counts.values()),
        "policy": "Analyzer failures are tracked explicitly through *_available feature columns and never interpreted as no threat detected.",
    }


def write_uncertain_review_packets(records: Sequence[DatasetPairRecord], output_dir: Path) -> List[Dict[str, Any]]:
    packets = []
    for record in records:
        if record.label != "uncertain":
            continue
        packet = build_review_packet(record)
        path = output_dir / f"{record.pair_id}.json"
        write_json(path, packet)
        packets.append({"record_id": record.pair_id, "path": relative_path(path), "status": "remains_uncertain"})
    return packets


def build_review_packet(record: DatasetPairRecord) -> Dict[str, Any]:
    drift = {}
    try:
        old_archive = Path(record.old_archive_path)
        new_archive = Path(record.new_archive_path)
        import tempfile
        from app.core.security import SecureExtractor

        with tempfile.TemporaryDirectory(prefix="phase3g_review_") as workspace:
            old_dir = Path(workspace) / "old"
            new_dir = Path(workspace) / "new"
            SecureExtractor.validate_and_extract_zip(str(old_archive), str(old_dir))
            SecureExtractor.validate_and_extract_zip(str(new_archive), str(new_dir))
            drift = DriftEngine.compute_behavioral_drift(str(old_dir), str(new_dir))
    except Exception as exc:
        drift = {"review_extraction_error": str(exc)}
    manifest = drift.get("manifest_diff", {})
    return {
        "record_id": record.pair_id,
        "extension_identity": record.extension_id,
        "extension_name": record.extension_name,
        "v1": record.old_version,
        "v2": record.new_version,
        "release_source": record.source,
        "release_notes": ["No independent resolution evidence is present in the cached repository artifacts; second review is required."],
        "manifest_differences": manifest,
        "permissions": {
            "added": manifest.get("added_permissions", []),
            "removed": manifest.get("removed_permissions", []),
        },
        "host_changes": {
            "added": manifest.get("added_hosts", []),
            "removed": manifest.get("removed_hosts", []),
        },
        "api_changes": drift.get("api_diff", {}),
        "network_changes": drift.get("network_diff", {}),
        "obfuscation_indicators": drift.get("obfuscation_diff", {}),
        "structural_changes": drift.get("structure_diff", {}),
        "independent_evidence": list(record.provenance.notes),
        "current_uncertainty_rationale": record.label_rationale,
        "allowed_outcomes": ["benign_transition", "risky_transition", "malicious_transition", "uncertain", "excluded"],
        "javascript_execution": "never_executed_static_review_only",
    }


def build_second_review_queue(records: Sequence[DatasetPairRecord]) -> Dict[str, Any]:
    queue = []
    for record in records:
        score = 0
        if record.label == "malicious_transition":
            score += 120
        if record.label == "risky_transition":
            score += 100
        if record.label == "uncertain":
            score += 90
        if "Phase 3G corpus maturation record" in record.notes:
            score += 20
        if record.label_quality_tier == "SINGLE_REVIEWER_PROVISIONAL":
            score += 10
        queue.append({
            "record_id": record.pair_id,
            "extension_id": record.extension_id,
            "label": record.label,
            "label_quality_tier": record.label_quality_tier,
            "reviewer_id": None,
            "reviewer_confidence": None,
            "reviewer_rationale": None,
            "timestamp": None,
            "evidence_references": list(record.provenance.notes),
            "disagreement_flag": False,
            "adjudication_status": "pending_second_review",
            "adjudicated_label": None,
            "adjudication_rationale": None,
            "priority_score": score,
        })
    return {
        "schema_version": "phase3g-second-review-queue-v1",
        "status": "created_no_second_reviewer_fabricated",
        "records": sorted(queue, key=lambda item: item["priority_score"], reverse=True),
    }


def reviewer_schema() -> Dict[str, Any]:
    return {
        "schema_version": "phase3g-reviewer-schema-v1",
        "fields": [
            "reviewer_id",
            "independent_reviewer_label",
            "reviewer_confidence",
            "reviewer_rationale",
            "timestamp",
            "evidence_references",
            "disagreement_flag",
            "adjudication_status",
            "adjudicated_label",
            "adjudication_rationale",
        ],
        "allowed_labels": ["benign_transition", "risky_transition", "malicious_transition", "uncertain", "excluded"],
        "quality_tiers": [
            "CONTROLLED_GROUND_TRUTH",
            "EXTERNAL_CONFIRMED",
            "MULTI_REVIEWER_ADJUDICATED",
            "SINGLE_REVIEWER_PROVISIONAL",
            "UNCERTAIN",
        ],
    }


def build_inter_rater_report(records: Sequence[DatasetPairRecord]) -> Dict[str, Any]:
    double_reviewed = [record for record in records if record.label_quality_tier == "MULTI_REVIEWER_ADJUDICATED"]
    return {
        "status": "INTER_RATER_AGREEMENT_NOT_AVAILABLE",
        "double_reviewed_record_count": len(double_reviewed),
        "agreements": 0,
        "disagreements": 0,
        "adjudications": 0,
        "cohens_kappa": None,
        "reason": "No genuine independent second-review records are present; reviewer agreement is not simulated.",
    }


def build_diversity_report(records: Sequence[DatasetPairRecord]) -> Dict[str, Any]:
    by_category = defaultdict(list)
    for record in records:
        by_category[record.functional_category or "unknown"].append(record)
    return {
        "unique_extension_count": len({record.extension_id for record in records}),
        "extensions_per_category": {category: len({record.extension_id for record in category_records}) for category, category_records in by_category.items()},
        "transitions_per_category": {category: len(category_records) for category, category_records in by_category.items()},
        "labels_per_category": {category: dict(Counter(record.label for record in category_records)) for category, category_records in by_category.items()},
    }


def write_phase3g_feature_artifacts(
    phase3f_feature_dir: Path,
    new_extraction,
    output_dir: Path,
    *,
    generation_timestamp: str,
    code_version: str | None,
    seed: int,
) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    schema_payload = read_json(phase3f_feature_dir / "feature_schema.json")
    write_json(output_dir / "feature_schema.json", schema_payload)
    paths["feature_schema"] = str(output_dir / "feature_schema.json")
    label_counts = Counter()
    split_counts = Counter()
    missingness_counts = Counter()
    for baseline in BASELINES:
        existing_rows = load_csv(phase3f_feature_dir / f"{baseline}.csv")
        new_rows = [row.for_baseline(baseline, new_extraction.schema) for row in new_extraction.feature_rows]
        combined_rows = existing_rows + stringify_rows(new_rows)
        csv_path = output_dir / f"{baseline}.csv"
        jsonl_path = output_dir / f"{baseline}.jsonl"
        write_csv(csv_path, combined_rows)
        write_jsonl(jsonl_path, combined_rows)
        paths[f"{baseline}_csv"] = str(csv_path)
        paths[f"{baseline}_jsonl"] = str(jsonl_path)
        if baseline == "full_driftwatch":
            for row in combined_rows:
                label_counts[row.get("label") or "unknown"] += 1
                split_counts[row.get("split") or "unsplit"] += 1
                for key, value in row.items():
                    if key.endswith("_available") and str(value) in {"0", "0.0", "False"}:
                        missingness_counts[key] += 1
    summary = {
        "record_count": sum(label_counts.values()),
        "label_counts": dict(sorted(label_counts.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "feature_count": len(new_extraction.schema),
        "missingness_counts": dict(sorted(missingness_counts.items())),
        "phase3f_baseline_rows_reused": len(load_csv(phase3f_feature_dir / "full_driftwatch.csv")),
        "phase3g_new_rows_extracted": len(new_extraction.feature_rows),
    }
    write_json(output_dir / "dataset_summary.json", summary)
    manifest = {
        "generation_timestamp": generation_timestamp,
        "feature_schema_version": "1.0",
        "record_count": summary["record_count"],
        "feature_families": sorted({definition.family for definition in new_extraction.schema}),
        "baselines": list(BASELINES),
        "source_dataset_identifier": "DriftBench Phase 3G",
        "source_dataset_version": PHASE3G_DATASET_VERSION,
        "previous_dataset_version": PHASE3F_DATASET_VERSION,
        "phase3f_baseline_feature_reuse": True,
        "phase3g_new_records_extracted_only": True,
        "model_training_performed": False,
        "production_ml_integration": False,
        "code_version": code_version,
        "split_counts": summary["split_counts"],
        "label_counts": summary["label_counts"],
        "extraction_warnings": new_extraction.extraction_warnings,
        "failed_records": new_extraction.failed_records,
        "deterministic_seed": seed,
    }
    write_json(output_dir / "extraction_manifest.json", manifest)
    return paths


def phase3g_feature_cache_valid(feature_dir: Path, *, expected_records: int) -> bool:
    manifest_path = feature_dir / "extraction_manifest.json"
    if not manifest_path.exists():
        return False
    try:
        manifest = read_json(manifest_path)
    except Exception:
        return False
    return (
        manifest.get("source_dataset_version") == PHASE3G_DATASET_VERSION
        and manifest.get("record_count") == expected_records
        and all((feature_dir / f"{baseline}.csv").exists() for baseline in BASELINES)
    )


def build_phase3f_vs_phase3g_dataset_comparison(
    phase3f_curation_dir: Path,
    phase3g_manifest: Dict[str, Any],
    phase3g_readiness: Dict[str, Any],
) -> List[Dict[str, Any]]:
    phase3f = read_json(phase3f_curation_dir / "dataset_manifest.json")
    phase3f_label_quality = phase3f["label_quality_tier_distribution"]
    phase3g_label_quality = phase3g_manifest["label_quality_tier_distribution"]
    return [
        {
            "metric": "total_real_records",
            "phase3f": phase3f["real_record_count"],
            "phase3g": phase3g_manifest["real_record_count"],
        },
        {
            "metric": "unique_extensions",
            "phase3f": phase3f["unique_extension_count"],
            "phase3g": phase3g_manifest["unique_extension_count"],
        },
        {
            "metric": "risky_or_malicious_records",
            "phase3f": phase3f["label_distribution"].get("risky_transition", 0) + phase3f["label_distribution"].get("malicious_transition", 0),
            "phase3g": phase3g_manifest["risky_review_worthy_count"],
        },
        {
            "metric": "uncertain_records",
            "phase3f": phase3f["label_distribution"].get("uncertain", 0),
            "phase3g": phase3g_manifest["uncertain_count"],
        },
        {
            "metric": "double_reviewed_count",
            "phase3f": phase3f_label_quality.get("MULTI_REVIEWER_ADJUDICATED", 0),
            "phase3g": phase3g_label_quality.get("MULTI_REVIEWER_ADJUDICATED", 0),
        },
        {
            "metric": "provisional_label_percentage",
            "phase3f": round(100 * phase3f_label_quality.get("SINGLE_REVIEWER_PROVISIONAL", 0) / phase3f["accepted"], 6),
            "phase3g": round(100 * phase3g_label_quality.get("SINGLE_REVIEWER_PROVISIONAL", 0) / phase3g_manifest["accepted"], 6),
        },
        {
            "metric": "provenance_completeness",
            "phase3f": "46/46",
            "phase3g": phase3g_readiness["provenance_completeness"],
        },
        {
            "metric": "timestamp_completeness",
            "phase3f": "46/46",
            "phase3g": phase3g_readiness["timestamp_completeness"],
        },
        {
            "metric": "train_validation_test_counts",
            "phase3f": json.dumps(phase3f["split_counts"], sort_keys=True),
            "phase3g": json.dumps(phase3g_manifest["split_counts"], sort_keys=True),
        },
    ]


def build_dataset_snapshot(
    records: Sequence[DatasetPairRecord],
    phase3f_reference: Dict[str, Any],
    curation_dir: Path,
    dataset_manifest: Dict[str, Any],
    provenance_manifest: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "dataset_version": PHASE3G_DATASET_VERSION,
        "previous_dataset_version": PHASE3F_DATASET_VERSION,
        "phase3f_frozen_baseline": phase3f_reference,
        "schema_version": "phase3d-intake-v1",
        "ontology_version": "phase3d-labels-v1",
        "feature_schema_version": "1.0",
        "split_version": PHASE3G_SPLIT_VERSION,
        "creation_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_manifest_hash": sha256_file(curation_dir / "dataset_manifest.json"),
        "provenance_manifest_hash": sha256_file(curation_dir / "provenance_manifest.json"),
        "record_count": len(records),
        "real_record_count": len(records),
        "controlled_record_count": 0,
        "new_phase3g_record_count": dataset_manifest["new_phase3g_record_count"],
        "unique_extension_count": len({record.extension_id for record in records}),
        "label_distribution": dict(Counter(record.label for record in records)),
        "label_quality_distribution": dict(Counter(record.label_quality_tier for record in records)),
        "training_eligible_count": dataset_manifest["training_eligible_count"],
        "uncertain_count": dataset_manifest["uncertain_count"],
        "license_distribution": dataset_manifest["license_identifier_distribution"],
        "split_distribution": dataset_manifest["split_counts"],
        "extension_ids_per_split": {
            split: sorted({record.extension_id for record in records if record.split == split})
            for split in ("train", "validation", "test")
        },
        "provenance_completeness": f"{provenance_manifest['provenance_complete_count']}/{len(records)}",
        "timestamp_completeness": f"{provenance_manifest['timestamp_complete_count']}/{len(records)}",
    }


def freeze_phase3f_reference(curation_dir: Path, feature_dir: Path, experiment_dir: Path) -> Dict[str, Any]:
    snapshot = read_json(experiment_dir / "dataset_snapshot.json")
    return {
        "status": "FROZEN_PHASE3F_BASELINE",
        "dataset_version": snapshot["dataset_version"],
        "dataset_manifest_hash": sha256_file(curation_dir / "dataset_manifest.json"),
        "provenance_manifest_hash": sha256_file(curation_dir / "provenance_manifest.json"),
        "feature_extraction_manifest_hash": sha256_file(feature_dir / "extraction_manifest.json"),
        "experiment_snapshot_hash": sha256_file(experiment_dir / "dataset_snapshot.json"),
        "preservation_policy": "Phase 3G reads Phase 3F as immutable research history and writes only phase3g outputs.",
    }


def write_phase3g_import_manifest(
    path: Path,
    records: Sequence[DatasetPairRecord],
    new_releases: Dict[str, List[Dict[str, Any]]],
    excluded_releases: Dict[str, Any],
) -> None:
    write_json(path, {
        "dataset_version": PHASE3G_DATASET_VERSION,
        "previous_dataset_version": PHASE3F_DATASET_VERSION,
        "records": [record.to_dict() for record in records],
        "new_release_assets": new_releases,
        "excluded_candidate_assets": excluded_releases,
    })


def write_human_review_queue(path: Path, queue: Dict[str, Any]) -> None:
    lines = [
        "# Phase 3G Second Review Queue",
        "",
        "No second reviewer has been fabricated. Records below require independent review before stronger label-quality tiers can be claimed.",
        "",
    ]
    for item in queue["records"][:50]:
        lines.append(f"- `{item['record_id']}` | `{item['label']}` | `{item['label_quality_tier']}` | priority `{item['priority_score']}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def known_warning_report() -> Dict[str, Any]:
    return {
        "status": "non_blocking_dependency_or_development_warnings",
        "warnings": [
            "Starlette/FastAPI TestClient httpx deprecation",
            "joblib/NumPy array shape deprecation during trusted local research artifact loading",
            "pytest cache path warning for generated .pytest_cache state",
        ],
    }


if __name__ == "__main__":
    summary = run_phase3g_maturation()
    print(json.dumps({
        "dataset_version": summary["dataset_snapshot"]["dataset_version"],
        "records": summary["dataset_snapshot"]["record_count"],
        "new_phase3g_records": summary["dataset_snapshot"]["new_phase3g_record_count"],
        "unique_extensions": summary["dataset_snapshot"]["unique_extension_count"],
        "recommended_next_phase": summary["readiness"]["recommended_next_phase"],
    }, indent=2))
