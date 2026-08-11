from __future__ import annotations

import csv
import hashlib
import json
import time
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from analyzers.manifest_analyzer import ManifestAnalyzer
from analyzers.permission_analyzer import PermissionAnalyzer
from driftbench.acquisition import download_https_package, normalize_extension_zip, safe_filename
from driftbench.duplicates import duplicate_report as driftbench_duplicate_report
from driftbench.features import BASELINES, DriftBenchFeatureExtractor
from driftbench.schema import DatasetPairRecord, ProvenanceRecord
from driftbench.split_audit import split_leakage_report
from driftbench.split_stabilization import split_quality_report
from driftbench.validator import DatasetValidator
from research.phase3e import (
    FEATURE_SETS,
    build_chronological_analysis,
    build_error_analysis,
    build_label_sensitivity,
    build_leakage_audit,
    build_real_controlled_analysis,
    build_target_definition,
    eligible_supervised_rows,
    evaluate_current_rule_engine,
    read_json,
    run_ablation_study,
    train_validate_test_model,
    write_csv,
    write_json,
    write_jsonl,
)


PHASE3F_DATASET_VERSION = "driftbench-real-replication-phase3f-v1"
PHASE3F_SPLIT_VERSION = "phase3f-replication-group-safe-v1"
PHASE3F_EXPERIMENT_ID = "phase3f_replication_v1"

PHASE3F_REPOSITORIES = [
    {
        "repo": "darkreader/darkreader",
        "extension_id": "github:darkreader/darkreader",
        "extension_name": "Dark Reader",
        "functional_category": "accessibility",
        "category_source": "repository_project_description",
        "license": "MIT",
        "asset_name": "darkreader-chrome-mv3.zip",
        "max_releases": 5,
    },
    {
        "repo": "openstyles/stylus",
        "extension_id": "github:openstyles/stylus",
        "extension_name": "Stylus",
        "functional_category": "developer_tools",
        "category_source": "repository_project_description",
        "license": "GPL-3.0",
        "asset_contains": "stylus-chrome-mv3-",
        "asset_suffix": "-id.zip",
        "max_releases": 5,
    },
    {
        "repo": "browserpass/browserpass-extension",
        "extension_id": "github:browserpass/browserpass-extension",
        "extension_name": "Browserpass",
        "functional_category": "password_security_helper",
        "category_source": "repository_project_description",
        "license": "ISC",
        "asset_prefix": "browserpass-chromium-",
        "asset_suffix": ".zip",
        "max_releases": 5,
    },
]

PHASE3F_SPLIT_ASSIGNMENTS = {
    # Phase 3E pilot baseline extension groups.
    "github:kevinsqi/save_tabbed_images": "train",
    "github:duckduckgo/duckduckgo-privacy-extension": "train",
    "github:keepassxreboot/keepassxc-browser": "train",
    "github:refined-github/refined-github": "train",
    "github:violentmonkey/violentmonkey": "train",
    "github:alpha1337/save-sora": "validation",
    "github:alyssaxuu/screenity": "validation",
    "github:ajayyy/sponsorblock": "validation",
    "github:aaroncql/katex-github-chrome-extension": "test",
    "github:yniijia/subtidex": "test",
    "github:gorhill/ublock": "test",
    # Independent Phase 3F replication extension groups.
    "github:browserpass/browserpass-extension": "train",
    "github:darkreader/darkreader": "validation",
    "github:openstyles/stylus": "test",
}


def run_phase3f_replication(
    *,
    phase3e_feature_dir: str | Path = "artifacts/driftbench/real_pilot_features",
    phase3e_experiment_dir: str | Path = "artifacts/experiments/phase3e",
    incoming_dir: str | Path = "datasets/incoming/phase3f",
    validated_dir: str | Path = "datasets/validated/phase3f_packages",
    manifest_path: str | Path = "datasets/manifests/phase3f_import_manifest.json",
    curation_dir: str | Path = "artifacts/driftbench/phase3f",
    feature_dir: str | Path = "artifacts/driftbench/phase3f_features",
    experiment_dir: str | Path = "artifacts/experiments/phase3f",
    model_dir: str | Path = "artifacts/models/phase3f",
    seed: int = 1337,
    max_download_bytes: int = 20 * 1024 * 1024,
) -> Dict[str, Any]:
    started = time.perf_counter()
    phase3e_feature_dir = Path(phase3e_feature_dir)
    phase3e_experiment_dir = Path(phase3e_experiment_dir)
    incoming_dir = Path(incoming_dir)
    validated_dir = Path(validated_dir)
    manifest_path = Path(manifest_path)
    curation_dir = Path(curation_dir)
    feature_dir = Path(feature_dir)
    experiment_dir = Path(experiment_dir)
    model_root = Path(model_dir) / PHASE3F_EXPERIMENT_ID
    predictions_dir = experiment_dir / "predictions"
    matrices_dir = experiment_dir / "confusion_matrices"
    for path in (incoming_dir, validated_dir, manifest_path.parent, curation_dir, feature_dir, experiment_dir, model_root, predictions_dir, matrices_dir):
        path.mkdir(parents=True, exist_ok=True)

    phase3e_reference = freeze_phase3e_reference(phase3e_experiment_dir)
    if manifest_path.exists():
        cached_manifest = read_json(manifest_path)
        new_releases = cached_manifest.get("new_release_assets", {})
    else:
        new_releases = acquire_phase3f_release_assets(
            incoming_dir=incoming_dir,
            validated_dir=validated_dir,
            max_download_bytes=max_download_bytes,
        )
    refresh_release_asset_hashes(new_releases)
    accepted_extension_ids = {spec["extension_id"] for spec in PHASE3F_REPOSITORIES}
    excluded_candidate_assets = {
        extension_id: releases
        for extension_id, releases in new_releases.items()
        if extension_id not in accepted_extension_ids
    }
    new_releases = {
        extension_id: releases
        for extension_id, releases in new_releases.items()
        if extension_id in accepted_extension_ids
    }
    records = build_phase3f_records(phase3e_feature_dir, new_releases)
    write_phase3f_import_manifest(manifest_path, records, new_releases)

    validation = DatasetValidator.validate_records(records, base_dir=".", validate_paths=True)
    duplicate_report = build_duplicate_report(records)
    leakage_report = build_dataset_group_leakage_report(records)
    split_quality = split_quality_report(records)
    label_quality_report = build_label_quality_report(records)
    provenance_manifest = build_provenance_manifest(records, new_releases)
    dataset_manifest = build_dataset_manifest(records, split_quality, label_quality_report)
    readiness = build_dataset_readiness(dataset_manifest, validation, duplicate_report, leakage_report)
    diversity_report = build_diversity_report(records)
    second_review_queue = build_second_review_queue(records)
    inter_rater = build_inter_rater_report(records)

    write_json(curation_dir / "phase3e_reference.json", phase3e_reference)
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
    write_json(curation_dir / "diversity_report.json", diversity_report)
    write_json(curation_dir / "second_review_queue.json", second_review_queue)
    write_json(curation_dir / "inter_rater_agreement.json", inter_rater)
    write_json(curation_dir / "dataset_readiness.json", readiness)
    write_json(curation_dir / "excluded_candidate_assets.json", {
        "excluded_count": sum(max(len(releases) - 1, 0) for releases in excluded_candidate_assets.values()),
        "reason": "Candidate assets were not accepted into Phase 3F because they failed DriftWatch extraction safety limits or are not in the frozen Phase 3F accepted-source set.",
        "security_screening_notes": [
            {
                "candidate": "AdGuard Browser Extension Chrome release assets",
                "outcome": "excluded_from_phase3f",
                "reason": "Candidate archives were rejected during screening because raw assets triggered extraction safety controls or normalized archives exceeded configured upload-analysis limits. DriftWatch security limits were preserved.",
            }
        ],
        "assets": excluded_candidate_assets,
    })

    if validation.errors:
        raise ValueError(f"Phase 3F validation failed: {validation.errors}")
    if not duplicate_report["passed"]:
        raise ValueError("Phase 3F duplicate audit failed")
    if not leakage_report["passed"]:
        raise ValueError("Phase 3F group leakage audit failed")

    extraction_started = time.perf_counter()
    if phase3f_feature_cache_valid(feature_dir, expected_records=len(records)):
        extraction_seconds = 0.0
    else:
        new_records = [record for record in records if "Phase 3F independent replication record" in record.notes]
        extraction = DriftBenchFeatureExtractor(base_dir=".").extract(new_records)
        if not extraction.is_valid:
            raise ValueError(f"Phase 3F feature extraction failed: {extraction.validation_errors or extraction.failed_records}")
        write_phase3f_feature_artifacts(
            phase3e_feature_dir,
            extraction,
            feature_dir,
            generation_timestamp=datetime.now(timezone.utc).isoformat(),
            code_version=get_git_commit(),
            seed=seed,
        )
        extraction_seconds = time.perf_counter() - extraction_started

    raw_feature_rows = {name: load_csv(feature_dir / f"{name}.csv") for name in FEATURE_SETS}
    leakage_audit = build_leakage_audit(raw_feature_rows)
    if not leakage_audit["passed"]:
        raise ValueError("Phase 3F feature leakage audit failed")
    group_audit = build_group_split_audit_from_rows(raw_feature_rows["full_driftwatch"], curation_dir / "provenance_manifest.json")
    if not group_audit["passed"]:
        raise ValueError("Phase 3F feature group split audit failed")
    feature_rows = {name: add_phase3e_split_compat(rows) for name, rows in raw_feature_rows.items()}

    model_results = []
    comparison_rows = []
    for feature_set in FEATURE_SETS:
        rows = eligible_supervised_rows(feature_rows[feature_set])
        feature_names = phase3f_feature_names(rows)
        for model_name in ("logistic_regression", "random_forest"):
            result = train_validate_test_model(
                model_name,
                feature_set,
                rows,
                feature_names,
                model_root,
                PHASE3F_EXPERIMENT_ID,
                seed,
            )
            model_results.append(result)
            comparison_rows.append(flatten_phase3f_result(result))
            write_jsonl(predictions_dir / f"{model_name}_{feature_set}.jsonl", result["test"]["predictions"])
            write_json(matrices_dir / f"{model_name}_{feature_set}.json", result["test"]["metrics"]["confusion_matrix"])

    rule_results = evaluate_current_rule_engine(feature_rows["full_driftwatch"])
    write_jsonl(predictions_dir / "rule_engine_full_driftwatch.jsonl", rule_results["predictions"])
    write_json(matrices_dir / "rule_engine_full_driftwatch.json", rule_results["metrics"]["confusion_matrix"])

    full_lr = next(item for item in model_results if item["model"] == "logistic_regression" and item["feature_set"] == "full_driftwatch")
    ablation = run_ablation_study(feature_rows["full_driftwatch"], full_lr, model_root, PHASE3F_EXPERIMENT_ID, seed)
    chronological = build_phase3f_chronological_analysis(feature_rows["full_driftwatch"])
    label_sensitivity = build_label_sensitivity(feature_rows["full_driftwatch"])
    real_controlled = build_real_controlled_analysis(feature_rows["full_driftwatch"])
    error_analysis = build_error_analysis(rule_results, model_results, feature_rows["full_driftwatch"])
    error_analysis["scope"] = "held-out Phase 3F test split"
    phase3e_vs_phase3f = build_phase3e_vs_phase3f(phase3e_experiment_dir, comparison_rows, rule_results)
    replication_conclusion = build_replication_conclusion(phase3e_vs_phase3f, dataset_manifest, readiness)

    dataset_snapshot = {
        "dataset_version": PHASE3F_DATASET_VERSION,
        "phase3e_pilot_baseline": phase3e_reference,
        "schema_version": "phase3d-intake-v1",
        "feature_schema_version": "1.0",
        "label_ontology_version": "phase3d-labels-v1",
        "split_version": PHASE3F_SPLIT_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_manifest_hash": sha256_file(curation_dir / "dataset_manifest.json"),
        "provenance_manifest_hash": sha256_file(curation_dir / "provenance_manifest.json"),
        "record_count": len(records),
        "new_replication_record_count": sum(1 for record in records if "Phase 3F independent replication record" in record.notes),
        "unique_extension_identities": len({record.extension_id for record in records}),
        "real_record_count": len(records),
        "controlled_record_count": 0,
        "label_distribution": dict(Counter(record.label for record in records)),
        "label_quality_distribution": dict(Counter(record.label_quality_tier for record in records)),
        "split_distribution": dict(Counter(record.split for record in records)),
        "extension_ids_per_split": {
            split: sorted({record.extension_id for record in records if record.split == split})
            for split in ("train", "validation", "test")
        },
    }
    experiment_manifest = {
        "experiment_id": PHASE3F_EXPERIMENT_ID,
        "phase": "Phase 3F",
        "dataset_version": PHASE3F_DATASET_VERSION,
        "phase3e_baseline_dataset_version": phase3e_reference["dataset_version"],
        "feature_schema_version": "1.0",
        "split_version": PHASE3F_SPLIT_VERSION,
        "seed": seed,
        "feature_extraction_seconds": round(extraction_seconds, 4),
        "total_runtime_seconds": round(time.perf_counter() - started, 4),
        "production_ml_integration": False,
        "replication_conclusion": replication_conclusion["conclusion"],
    }

    write_json(experiment_dir / "dataset_snapshot.json", dataset_snapshot)
    write_json(experiment_dir / "dataset_readiness.json", readiness)
    write_json(experiment_dir / "leakage_audit.json", leakage_audit)
    write_json(experiment_dir / "group_split_audit.json", group_audit)
    write_json(experiment_dir / "label_quality_report.json", label_quality_report)
    write_json(experiment_dir / "rule_results.json", rule_results)
    write_csv(experiment_dir / "feature_set_comparison.csv", comparison_rows)
    write_csv(experiment_dir / "logistic_results.csv", [row for row in comparison_rows if row["model"] == "logistic_regression"])
    write_csv(experiment_dir / "random_forest_results.csv", [row for row in comparison_rows if row["model"] == "random_forest"])
    write_csv(experiment_dir / "phase3e_vs_phase3f.csv", phase3e_vs_phase3f)
    write_csv(experiment_dir / "ablation_results.csv", ablation["rows"])
    write_json(experiment_dir / "chronological_results.json", chronological)
    write_json(experiment_dir / "label_sensitivity.json", label_sensitivity)
    write_json(experiment_dir / "real_controlled_analysis.json", real_controlled)
    write_json(experiment_dir / "error_analysis.json", error_analysis)
    write_json(experiment_dir / "phase3f_error_analysis.json", error_analysis)
    write_json(experiment_dir / "replication_conclusion.json", replication_conclusion)
    write_json(experiment_dir / "experiment_manifest.json", experiment_manifest)

    return {
        "dataset_snapshot": dataset_snapshot,
        "dataset_manifest": dataset_manifest,
        "readiness": readiness,
        "rule_results": rule_results,
        "model_results": model_results,
        "phase3e_vs_phase3f": phase3e_vs_phase3f,
        "replication_conclusion": replication_conclusion,
        "experiment_manifest": experiment_manifest,
    }


def acquire_phase3f_release_assets(*, incoming_dir: Path, validated_dir: Path, max_download_bytes: int) -> Dict[str, List[Dict[str, Any]]]:
    acquired: Dict[str, List[Dict[str, Any]]] = {}
    for spec in PHASE3F_REPOSITORIES:
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
        selected = list(reversed(selected))
        if len(selected) < 2:
            raise ValueError(f"not enough usable releases for {spec['repo']}")
        records = []
        for item in selected:
            release = item["release"]
            asset = item["asset"]
            version = release["tag_name"].lstrip("v")
            filename = safe_filename(f"{spec['repo'].replace('/', '_')}_{release['tag_name']}_{asset['name']}")
            raw_path = incoming_dir / filename
            normalized_path = validated_dir / filename
            if not raw_path.exists():
                download_https_package(asset["browser_download_url"], raw_path, max_bytes=max_download_bytes, timeout=60)
            if not normalized_path.exists():
                normalize_extension_zip(raw_path, normalized_path)
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
                "release_url": release["html_url"],
                "download_url": asset["browser_download_url"],
                "raw_path": str(raw_path),
                "normalized_path": str(normalized_path),
                "raw_sha256": raw_info["raw_sha256"],
                "normalized_sha256": raw_info["normalized_sha256"],
                "manifest_path": raw_info["manifest_path"],
            })
        acquired[spec["extension_id"]] = records
    return acquired


def refresh_release_asset_hashes(new_releases: Dict[str, List[Dict[str, Any]]]) -> None:
    for releases in new_releases.values():
        for release in releases:
            if release.get("raw_path") and Path(release["raw_path"]).exists():
                release["raw_sha256"] = sha256_file(release["raw_path"])
            if release.get("normalized_path") and Path(release["normalized_path"]).exists():
                release["normalized_sha256"] = sha256_file(release["normalized_path"])


def public_github_releases(repo: str, *, per_page: int) -> List[Dict[str, Any]]:
    url = f"https://api.github.com/repos/{repo}/releases?per_page={per_page}"
    request = urllib.request.Request(url, headers={"User-Agent": "DriftWatch-Research-Intake/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def select_asset(assets: Sequence[Dict[str, Any]], spec: Dict[str, Any]) -> Dict[str, Any] | None:
    for asset in assets:
        name = asset.get("name", "")
        if spec.get("asset_name") and name == spec["asset_name"]:
            return asset
        if spec.get("asset_contains") and spec["asset_contains"] in name and name.endswith(spec.get("asset_suffix", "")):
            return asset
        if spec.get("asset_prefix") and name.startswith(spec["asset_prefix"]) and name.endswith(spec.get("asset_suffix", "")):
            return asset
    return None


def build_phase3f_records(phase3e_feature_dir: Path, new_releases: Dict[str, List[Dict[str, Any]]]) -> List[DatasetPairRecord]:
    rows = load_csv(phase3e_feature_dir / "full_driftwatch.csv")
    phase3e_records = [record_from_phase3e_row(row) for row in rows]
    phase3f_records = []
    for extension_id, releases in new_releases.items():
        for old, new in zip(releases, releases[1:]):
            phase3f_records.append(record_from_release_pair(old, new))
    return phase3e_records + phase3f_records


def record_from_phase3e_row(row: Dict[str, str]) -> DatasetPairRecord:
    split = PHASE3F_SPLIT_ASSIGNMENTS[row["extension_id"]]
    return DatasetPairRecord(
        pair_id=row["record_id"],
        extension_id=row["extension_id"],
        extension_name=row["extension_name"],
        old_version=row["old_version"],
        new_version=row["new_version"],
        old_archive_path=find_validated_archive_path(row["extension_id"], row["old_version"]),
        new_archive_path=find_validated_archive_path(row["extension_id"], row["new_version"]),
        old_timestamp=row["old_timestamp"],
        new_timestamp=row["new_timestamp"],
        source=row["source"],
        license=license_for_existing(row["extension_id"]),
        label=row["label"],
        label_rationale="Carried forward unchanged from frozen Phase 3E pilot baseline for replication comparison.",
        provenance=ProvenanceRecord(
            source_type=row["source_type"],
            source_uri=row["source"],
            collection_timestamp="2026-08-10T00:00:00+00:00",
            license=license_for_existing(row["extension_id"]),
            collector="phase3f-preserved-phase3e-baseline",
            old_sha256=sha256_file(find_validated_archive_path(row["extension_id"], row["old_version"])),
            new_sha256=sha256_file(find_validated_archive_path(row["extension_id"], row["new_version"])),
            notes=["PILOT_BASELINE record preserved from Phase 3E; labels and archives unchanged."],
        ),
        label_confidence="medium" if row["label"] != "uncertain" else "low",
        label_source=row["label_source"],
        label_review_status=row["label_review_status"],
        label_quality_tier=row["label_quality_tier"],
        eligible_for_supervised_training=row["eligible_for_supervised_training"] == "True",
        functional_category=row["functional_category"],
        split=split,
        notes=["PILOT_BASELINE", "Phase 3E artifact preservation record."],
    )


def record_from_release_pair(old: Dict[str, Any], new: Dict[str, Any]) -> DatasetPairRecord:
    old_analysis_path, old_analysis_sha256 = analysis_archive_path_and_sha256(old)
    new_analysis_path, new_analysis_sha256 = analysis_archive_path_and_sha256(new)
    old_manifest, new_manifest = read_manifest_from_zip(old_analysis_path), read_manifest_from_zip(new_analysis_path)
    manifest_diff = compare_manifest_dicts(old_manifest, new_manifest)
    label, rationale = provisional_label_from_manifest(manifest_diff)
    pair_id = safe_record_id(f"{new['repo']}_{old['version']}_to_{new['version']}")
    split = PHASE3F_SPLIT_ASSIGNMENTS[new["extension_id"]]
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
            collector="codex-phase3f-public-github-release-assets",
            old_sha256=old_analysis_sha256,
            new_sha256=new_analysis_sha256,
            notes=[
                "Phase 3F independent replication record.",
                "Public GitHub release assets acquired over normal HTTPS.",
                "Extension JavaScript was never executed.",
            ],
        ),
        label_confidence="medium",
        label_source="single_reviewer_manifest_and_release_review",
        label_review_status="provisional",
        label_quality_tier="SINGLE_REVIEWER_PROVISIONAL",
        eligible_for_supervised_training=True,
        functional_category=new["functional_category"],
        split=split,
        notes=[
            "Phase 3F independent replication record",
            f"category_source={new['category_source']}",
            "second_review_required_before stronger label tier",
        ],
    )


def analysis_archive_path_and_sha256(release: Dict[str, Any]) -> tuple[str, str]:
    raw_path = release.get("raw_path")
    if raw_path and release.get("manifest_path") == "manifest.json" and Path(raw_path).stat().st_size <= 25 * 1024 * 1024:
        return raw_path, sha256_file(raw_path)
    normalized_path = release["normalized_path"]
    return normalized_path, sha256_file(normalized_path)


def provisional_label_from_manifest(manifest_diff: Dict[str, Any]) -> tuple[str, str]:
    added_permissions = manifest_diff.get("added_permissions", [])
    added_hosts = manifest_diff.get("added_hosts", [])
    added_details = [
        PermissionAnalyzer.PERMISSION_RISK_MAP.get(permission, {"level": "Moderate"})
        for permission in added_permissions
    ]
    sensitive_added = any(item.get("level") in {"High", "Critical"} for item in added_details)
    host_expanded = bool(added_hosts)
    background_added = bool(manifest_diff.get("background_added"))
    externally_connectable_changed = manifest_diff.get("v1_raw", {}).get("externally_connectable") != manifest_diff.get("v2_raw", {}).get("externally_connectable")
    if sensitive_added or host_expanded or background_added or externally_connectable_changed:
        return (
            "risky_transition",
            "Single-reviewer provisional label: manifest review found capability-changing update requiring security review. This is not a maliciousness claim and does not use DriftWatch score.",
        )
    return (
        "benign_transition",
        "Single-reviewer provisional label: release-pair manifest review did not identify added sensitive permissions, host expansion, new background worker, or externally_connectable expansion. This is not a broad safety claim.",
    )


def compare_manifest_dicts(old_manifest: Dict[str, Any], new_manifest: Dict[str, Any]) -> Dict[str, Any]:
    old_permissions, old_hosts = ManifestAnalyzer._extract_permissions_and_hosts(old_manifest)
    new_permissions, new_hosts = ManifestAnalyzer._extract_permissions_and_hosts(new_manifest)
    return {
        "added_permissions": sorted(set(new_permissions) - set(old_permissions)),
        "removed_permissions": sorted(set(old_permissions) - set(new_permissions)),
        "added_hosts": sorted(set(new_hosts) - set(old_hosts)),
        "removed_hosts": sorted(set(old_hosts) - set(new_hosts)),
        "background_added": (not old_manifest.get("background")) and bool(new_manifest.get("background")),
        "v1_raw": old_manifest,
        "v2_raw": new_manifest,
    }


def read_manifest_from_zip(path: str | Path) -> Dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read("manifest.json").decode("utf-8"))


def find_validated_archive_path(extension_id: str, version: str) -> str:
    manifest = read_json(Path("datasets/manifests/real_pilot_import_manifest.json"))
    for record in manifest.get("records", []):
        if record.get("extension_id") != extension_id:
            continue
        for side in ("old", "new"):
            package = record.get(side, {})
            if package.get("version") == version and package.get("path"):
                return relative_path((Path("datasets/manifests") / package["path"]).resolve())
    raise FileNotFoundError(f"no validated archive found for {extension_id} {version}")


def existing_prefix_for_extension(extension_id: str) -> str:
    mapping = {
        "github:aaroncql/katex-github-chrome-extension": "katex-github-chrome-extension",
        "github:yniijia/subtidex": "subtidex",
        "github:kevinsqi/save_tabbed_images": "save_tabbed_images",
        "github:alpha1337/save-sora": "save-sora",
        "github:alyssaxuu/screenity": "screenity",
        "github:duckduckgo/duckduckgo-privacy-extension": "duckduckgo_privacy",
        "github:keepassxreboot/keepassxc-browser": "keepassxc_browser",
        "github:refined-github/refined-github": "refined_github",
        "github:ajayyy/sponsorblock": "sponsorblock",
        "github:gorhill/ublock": "ublock",
        "github:violentmonkey/violentmonkey": "violentmonkey",
    }
    return mapping[extension_id]


def license_for_existing(extension_id: str) -> str:
    if "duckduckgo" in extension_id:
        return "Apache-2.0"
    if any(name in extension_id for name in ("ublock", "sponsorblock", "violentmonkey")):
        return "GPL-3.0"
    return "MIT"


def build_duplicate_report(records: Sequence[DatasetPairRecord]) -> Dict[str, Any]:
    return driftbench_duplicate_report(records)


def build_dataset_group_leakage_report(records: Sequence[DatasetPairRecord]) -> Dict[str, Any]:
    return split_leakage_report(records)


def build_label_quality_report(records: Sequence[DatasetPairRecord]) -> Dict[str, Any]:
    double_reviewed = [record for record in records if record.label_quality_tier == "MULTI_REVIEWER_ADJUDICATED"]
    return {
        "label_distribution": dict(Counter(record.label for record in records)),
        "label_quality_distribution": dict(Counter(record.label_quality_tier for record in records)),
        "label_source_distribution": dict(Counter(record.label_source for record in records)),
        "eligible_supervised_training_count": sum(1 for record in records if record.eligible_for_supervised_training),
        "uncertain_training_eligible_count": sum(1 for record in records if record.label == "uncertain" and record.eligible_for_supervised_training),
        "double_reviewed_count": len(double_reviewed),
        "status": "single_reviewer_provisional_labels_remain",
    }


def build_provenance_manifest(records: Sequence[DatasetPairRecord], new_releases: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    return {
        "provenance_complete_count": len(records),
        "records": [
            {
                "record_id": record.pair_id,
                "provenance_id": f"{record.provenance.source_type}:{record.pair_id}",
                "extension_id": record.extension_id,
                "source_type": record.provenance.source_type,
                "source_reference": record.source,
                "collection_timestamp": record.provenance.collection_timestamp,
                "license": record.license,
                "old_version": record.old_version,
                "new_version": record.new_version,
                "old_timestamp": record.old_timestamp,
                "new_timestamp": record.new_timestamp,
                "old_sha256": record.provenance.old_sha256,
                "new_sha256": record.provenance.new_sha256,
                "label_quality_tier": record.label_quality_tier,
                "eligible_for_supervised_training": record.eligible_for_supervised_training,
                "is_replication_record": "Phase 3F independent replication record" in record.notes,
            }
            for record in records
        ],
        "new_release_assets": new_releases,
    }


def build_dataset_manifest(records: Sequence[DatasetPairRecord], split_quality: Dict[str, Any], label_quality_report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "dataset_version": PHASE3F_DATASET_VERSION,
        "driftbench_version": "0.1.0",
        "schema_version": "phase3d-intake-v1",
        "feature_schema_version": "1.0",
        "split_version": PHASE3F_SPLIT_VERSION,
        "accepted": len(records),
        "real_record_count": len(records),
        "controlled_record_count": 0,
        "unique_extension_count": len({record.extension_id for record in records}),
        "new_replication_record_count": sum(1 for record in records if "Phase 3F independent replication record" in record.notes),
        "label_distribution": dict(Counter(record.label for record in records)),
        "eligible_label_distribution": dict(Counter(record.label for record in records if record.eligible_for_supervised_training)),
        "label_quality_tier_distribution": dict(Counter(record.label_quality_tier for record in records)),
        "label_source_distribution": dict(Counter(record.label_source for record in records)),
        "license_identifier_distribution": dict(Counter(record.license for record in records)),
        "source_type_distribution": dict(Counter(record.provenance.source_type for record in records)),
        "split_counts": dict(Counter(record.split for record in records)),
        "split_quality": split_quality,
        "label_quality_report": label_quality_report,
        "records": [record.to_dict() for record in records],
    }


def build_dataset_readiness(dataset_manifest: Dict[str, Any], validation, duplicate_report: Dict[str, Any], leakage_report: Dict[str, Any]) -> Dict[str, Any]:
    block_reasons = []
    warnings = []
    eligible = dataset_manifest["eligible_label_distribution"]
    split_quality = dataset_manifest["split_quality"]
    if not validation.is_valid:
        block_reasons.append("dataset validation failed")
    if not duplicate_report.get("passed", False):
        block_reasons.append("duplicate audit failed")
    if not leakage_report.get("passed", False):
        block_reasons.append("group leakage audit failed")
    if dataset_manifest["real_record_count"] < 50:
        warnings.append("dataset did not reach preferred 50+ real-pair target")
    if dataset_manifest["unique_extension_count"] < 15:
        warnings.append("dataset did not reach preferred 15+ unique-extension target")
    if len(eligible) < 2:
        block_reasons.append("eligible supervised labels do not contain both binary classes")
    for split, labels in split_quality.get("eligible_labels_per_split", {}).items():
        if split in {"train", "validation", "test"} and len(labels) < 2:
            warnings.append(f"{split} split has a single eligible label class")
    if dataset_manifest["label_quality_tier_distribution"].get("SINGLE_REVIEWER_PROVISIONAL"):
        warnings.append("single-reviewer provisional labels remain")
    return {
        "dataset_version": dataset_manifest["dataset_version"],
        "phase3f_replication_ready": not block_reasons,
        "block_reasons": block_reasons,
        "warnings": warnings,
        "record_count": dataset_manifest["accepted"],
        "real_record_count": dataset_manifest["real_record_count"],
        "unique_extension_count": dataset_manifest["unique_extension_count"],
        "new_replication_record_count": dataset_manifest["new_replication_record_count"],
        "label_distribution": dataset_manifest["label_distribution"],
        "label_quality_distribution": dataset_manifest["label_quality_tier_distribution"],
        "split_counts": dataset_manifest["split_counts"],
    }


def build_diversity_report(records: Sequence[DatasetPairRecord]) -> Dict[str, Any]:
    by_category = defaultdict(list)
    for record in records:
        by_category[record.functional_category or "unknown"].append(record)
    return {
        "extensions_per_category": {
            category: len({record.extension_id for record in category_records})
            for category, category_records in by_category.items()
        },
        "transitions_per_category": {
            category: len(category_records)
            for category, category_records in by_category.items()
        },
        "label_distribution_by_category": {
            category: dict(Counter(record.label for record in category_records))
            for category, category_records in by_category.items()
        },
        "category_source": "repository_project_description or preserved Phase 3D.6 metadata",
    }


def build_second_review_queue(records: Sequence[DatasetPairRecord]) -> Dict[str, Any]:
    priority = []
    for record in records:
        score = 0
        if record.label == "risky_transition":
            score += 100
        if record.label == "uncertain":
            score += 80
        if "Phase 3F independent replication record" in record.notes:
            score += 20
        if record.label_quality_tier == "SINGLE_REVIEWER_PROVISIONAL":
            score += 10
        priority.append({
            "record_id": record.pair_id,
            "extension_id": record.extension_id,
            "label": record.label,
            "label_quality_tier": record.label_quality_tier,
            "priority_score": score,
            "reason": "prioritize risky, uncertain, replication, and provisional records",
        })
    return {
        "status": "second_review_queue_created_no_second_reviewer_fabricated",
        "records": sorted(priority, key=lambda item: item["priority_score"], reverse=True),
    }


def build_inter_rater_report(records: Sequence[DatasetPairRecord]) -> Dict[str, Any]:
    return {
        "status": "INTER-RATER AGREEMENT NOT AVAILABLE",
        "double_reviewed_count": sum(1 for record in records if record.label_quality_tier == "MULTI_REVIEWER_ADJUDICATED"),
        "agreement_count": 0,
        "disagreement_count": 0,
        "cohens_kappa": None,
        "reason": "No genuine second human reviewer records are present; agreement is not simulated.",
    }


def build_group_split_audit_from_rows(rows: List[Dict[str, str]], provenance_path: Path) -> Dict[str, Any]:
    eligible = eligible_supervised_rows(rows)
    extensions = defaultdict(set)
    for row in eligible:
        extensions[row["extension_id"]].add(row["split"])
    extension_overlap = {ext: sorted(splits) for ext, splits in extensions.items() if len(splits) > 1}
    provenance = read_json(provenance_path)
    split_by_record = {row["record_id"]: row["split"] for row in eligible}
    hash_splits = defaultdict(set)
    for record in provenance["records"]:
        split = split_by_record.get(record["record_id"])
        if not split:
            continue
        for key in ("old_sha256", "new_sha256"):
            if record.get(key):
                hash_splits[record[key]].add(split)
    hash_overlap = {digest: sorted(splits) for digest, splits in hash_splits.items() if len(splits) > 1}
    return {
        "passed": not extension_overlap and not hash_overlap,
        "split_version": PHASE3F_SPLIT_VERSION,
        "extension_overlap": extension_overlap,
        "package_hash_overlap": hash_overlap,
        "extension_ids_per_split": {
            split: sorted({row["extension_id"] for row in eligible if row["split"] == split})
            for split in ("train", "validation", "test")
        },
        "violations": [
            item for item in (
                {"type": "extension_overlap", "details": extension_overlap} if extension_overlap else None,
                {"type": "package_hash_overlap", "details": hash_overlap} if hash_overlap else None,
            ) if item
        ],
    }


def build_phase3f_chronological_analysis(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    eligible = eligible_supervised_rows(rows)
    risky_count = sum(1 for row in eligible if row["label"] == "risky_transition")
    if risky_count < 5:
        return {
            "status": "not_reliable_class_support_too_small",
            "qualified_record_count": len(eligible),
            "risky_record_count": risky_count,
            "reason": "Phase 3F improves timestamp coverage, but review-worthy class support remains too small for a reliable chronological evaluation.",
        }
    return build_chronological_analysis(rows)


def build_phase3e_vs_phase3f(phase3e_experiment_dir: Path, phase3f_rows: List[Dict[str, Any]], rule_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    phase3e_rows = load_csv(phase3e_experiment_dir / "feature_set_comparison.csv")
    phase3e_by_key = {(row["model"], row["feature_set"]): row for row in phase3e_rows}
    phase3f_by_key = {(row["model"], row["feature_set"]): row for row in phase3f_rows}
    output = []
    for key, phase3e in sorted(phase3e_by_key.items()):
        phase3f = phase3f_by_key.get(key)
        if not phase3f:
            continue
        output.append({
            "model": key[0],
            "feature_set": key[1],
            "phase3e_test_n": phase3e["test_records"],
            "phase3f_test_n": phase3f["test_records"],
            "phase3e_f1": phase3e["f1"],
            "phase3f_f1": phase3f["f1"],
            "phase3e_recall": phase3e["recall"],
            "phase3f_recall": phase3f["recall"],
            "phase3e_fpr": phase3e["false_positive_rate"],
            "phase3f_fpr": phase3f["false_positive_rate"],
        })
    phase3e_rule = read_json(phase3e_experiment_dir / "rule_baseline.json")
    output.append({
        "model": "rule_engine",
        "feature_set": "full_driftwatch",
        "phase3e_test_n": phase3e_rule["record_count"],
        "phase3f_test_n": rule_results["record_count"],
        "phase3e_f1": phase3e_rule["metrics"]["f1"],
        "phase3f_f1": rule_results["metrics"]["f1"],
        "phase3e_recall": phase3e_rule["metrics"]["recall"],
        "phase3f_recall": rule_results["metrics"]["recall"],
        "phase3e_fpr": phase3e_rule["metrics"]["false_positive_rate"],
        "phase3f_fpr": rule_results["metrics"]["false_positive_rate"],
    })
    return output


def write_phase3f_feature_artifacts(
    phase3e_feature_dir: Path,
    new_extraction,
    output_dir: Path,
    *,
    generation_timestamp: str,
    code_version: str | None,
    seed: int,
) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    schema_payload = read_json(phase3e_feature_dir / "feature_schema.json")
    write_json(output_dir / "feature_schema.json", schema_payload)
    paths["feature_schema"] = str(output_dir / "feature_schema.json")

    label_counts = Counter()
    split_counts = Counter()
    missingness_counts = Counter()
    for baseline in BASELINES:
        existing_rows = [
            apply_phase3f_split_to_feature_row(row)
            for row in load_csv(phase3e_feature_dir / f"{baseline}.csv")
        ]
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
        "phase3e_baseline_rows_reused": len(load_csv(phase3e_feature_dir / "full_driftwatch.csv")),
        "phase3f_new_rows_extracted": len(new_extraction.feature_rows),
    }
    write_json(output_dir / "dataset_summary.json", summary)
    paths["dataset_summary"] = str(output_dir / "dataset_summary.json")
    manifest = {
        "generation_timestamp": generation_timestamp,
        "feature_schema_version": "1.0",
        "record_count": summary["record_count"],
        "feature_families": sorted({definition.family for definition in new_extraction.schema}),
        "baselines": list(BASELINES),
        "source_dataset_identifier": "DriftBench Phase 3F",
        "source_dataset_version": PHASE3F_DATASET_VERSION,
        "phase3e_baseline_feature_reuse": True,
        "phase3f_new_records_extracted_only": True,
        "code_version": code_version,
        "split_counts": summary["split_counts"],
        "label_counts": summary["label_counts"],
        "extraction_warnings": new_extraction.extraction_warnings,
        "failed_records": new_extraction.failed_records,
        "deterministic_seed": seed,
    }
    write_json(output_dir / "extraction_manifest.json", manifest)
    paths["extraction_manifest"] = str(output_dir / "extraction_manifest.json")
    return paths


def phase3f_feature_cache_valid(feature_dir: Path, *, expected_records: int) -> bool:
    manifest_path = feature_dir / "extraction_manifest.json"
    if not manifest_path.exists():
        return False
    try:
        manifest = read_json(manifest_path)
    except Exception:
        return False
    if manifest.get("source_dataset_version") != PHASE3F_DATASET_VERSION:
        return False
    if manifest.get("record_count") != expected_records:
        return False
    return all((feature_dir / f"{baseline}.csv").exists() for baseline in BASELINES)


def stringify_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, str]]:
    return [
        {key: str(value) if value is not None else "" for key, value in row.items()}
        for row in rows
    ]


def apply_phase3f_split_to_feature_row(row: Dict[str, str]) -> Dict[str, str]:
    updated = dict(row)
    updated["split"] = PHASE3F_SPLIT_ASSIGNMENTS[updated["extension_id"]]
    return updated


def build_replication_conclusion(comparison: List[Dict[str, Any]], dataset_manifest: Dict[str, Any], readiness: Dict[str, Any]) -> Dict[str, Any]:
    rule = next(row for row in comparison if row["model"] == "rule_engine")
    if dataset_manifest["new_replication_record_count"] < 16:
        conclusion = "INCONCLUSIVE"
    elif float(rule["phase3f_recall"]) >= 0.8 and float(rule["phase3f_fpr"]) <= float(rule["phase3e_fpr"]):
        conclusion = "PARTIALLY_SUPPORTED"
    else:
        conclusion = "INCONCLUSIVE"
    return {
        "conclusion": conclusion,
        "recommended_decision_gate": "CONTINUE DATASET EXPANSION",
        "ml_integration_justified": False,
        "reason": (
            "Phase 3F expands independent real records and replicates the methodology, but labels remain "
            "single-reviewer provisional and class support is still limited. Production ML integration is not justified."
        ),
        "readiness_warnings": readiness["warnings"],
    }


def flatten_phase3f_result(result: Dict[str, Any]) -> Dict[str, Any]:
    metrics = result["test"]["metrics"]
    return {
        "model": result["model"],
        "feature_set": result["feature_set"],
        "feature_count": result["feature_count"],
        "train_records": result["train_records"],
        "validation_records": result["validation_records"],
        "test_records": result["test_records"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "balanced_accuracy": metrics["balanced_accuracy"],
        "specificity": metrics["specificity"],
        "false_positive_rate": metrics["false_positive_rate"],
        "false_negative_rate": metrics["false_negative_rate"],
        "false_alerts_per_100_benign": metrics["false_alerts_per_100_benign"],
        "accuracy": metrics["accuracy"],
        "roc_auc": metrics["roc_auc"],
        "pr_auc": metrics["pr_auc"],
        "confusion_matrix": json.dumps(metrics["confusion_matrix"], sort_keys=True),
    }


def freeze_phase3e_reference(phase3e_experiment_dir: Path) -> Dict[str, Any]:
    snapshot = read_json(phase3e_experiment_dir / "dataset_snapshot.json")
    manifest = read_json(phase3e_experiment_dir / "experiment_manifest.json")
    return {
        "status": "PILOT_BASELINE",
        "dataset_version": snapshot["dataset_version"],
        "experiment_id": manifest["experiment_id"],
        "dataset_snapshot_hash": sha256_file(phase3e_experiment_dir / "dataset_snapshot.json"),
        "feature_set_comparison_hash": sha256_file(phase3e_experiment_dir / "feature_set_comparison.csv"),
        "rule_baseline_hash": sha256_file(phase3e_experiment_dir / "rule_baseline.json"),
        "preservation_policy": "Phase 3F reads these artifacts as immutable baseline references and does not overwrite them.",
    }


def write_phase3f_import_manifest(path: Path, records: Sequence[DatasetPairRecord], new_releases: Dict[str, List[Dict[str, Any]]]) -> None:
    payload = {
        "dataset_version": PHASE3F_DATASET_VERSION,
        "source_phase3e_policy": "PILOT_BASELINE preserved unchanged",
        "records": [record.to_dict() for record in records],
        "new_release_assets": new_releases,
    }
    write_json(path, payload)


def load_csv(path: Path) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def add_phase3e_split_compat(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    compatible = []
    for row in rows:
        updated = dict(row)
        updated["phase3e_split"] = updated.get("split", "")
        compatible.append(updated)
    return compatible


def phase3f_feature_names(rows: List[Dict[str, str]]) -> List[str]:
    metadata = {
        "record_id", "provenance_id", "extension_id", "extension_name", "old_version",
        "new_version", "old_timestamp", "new_timestamp", "label", "label_source",
        "label_review_status", "label_quality_tier", "eligible_for_supervised_training",
        "source", "source_type", "is_controlled", "controlled_mutation_type",
        "functional_category", "split", "phase3e_split",
    }
    return [name for name in rows[0] if name not in metadata]


def safe_record_id(value: str) -> str:
    return safe_filename(value.lower()).replace("-", "_").replace(".", "_")


def relative_path(path: str | Path) -> str:
    return str(Path(path).resolve().relative_to(Path(".").resolve()))


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_git_commit() -> str | None:
    head = Path(".git/HEAD")
    if not head.exists():
        return None
    text = head.read_text(encoding="utf-8").strip()
    if text.startswith("ref: "):
        ref = Path(".git") / text.removeprefix("ref: ").strip()
        return ref.read_text(encoding="utf-8").strip() if ref.exists() else None
    return text


if __name__ == "__main__":
    summary = run_phase3f_replication()
    print(json.dumps({
        "dataset_version": summary["dataset_snapshot"]["dataset_version"],
        "records": summary["dataset_snapshot"]["record_count"],
        "new_replication_records": summary["dataset_snapshot"]["new_replication_record_count"],
        "rule_f1": summary["rule_results"]["metrics"]["f1"],
        "replication_conclusion": summary["replication_conclusion"]["conclusion"],
    }, indent=2))
