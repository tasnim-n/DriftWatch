import json
import zipfile

from driftbench.duplicates import duplicate_report
from driftbench.features import DriftBenchFeatureExtractor
from driftbench.governance import DRIFTBENCH_VERSION
from driftbench.acquisition import normalize_extension_zip, safe_filename, validate_acquisition_url
from driftbench.intake import curate_import_manifest, main as ingest_main
from driftbench.label_quality import LabelQualityTier, infer_label_quality_tier
from driftbench.labels import Label
from driftbench.manifests import write_phase3d_manifests
from driftbench.review import AdjudicationRecord, ManualReview, ReviewPacket, write_review_queue
from driftbench.real_pilot import write_real_pilot_readiness
from driftbench.schema import DatasetPairRecord, ProvenanceRecord
from driftbench.split_audit import split_leakage_report
from driftbench.split_stabilization import split_quality_report
from driftbench.versioning import VersionEntry, build_consecutive_pairs, compare_versions


def _write_zip(path, *, name="Phase 3D Fixture", version="1.0.0", manifest=True, files=None):
    with zipfile.ZipFile(path, "w") as archive:
        if manifest:
            archive.writestr(
                "manifest.json",
                json.dumps({
                    "manifest_version": 3,
                    "name": name,
                    "version": version,
                    "permissions": ["storage"],
                }),
            )
        for filename, content in (files or {}).items():
            archive.writestr(filename, content)


def _manifest(tmp_path, *, record_id="real-pair-1", label=Label.BENIGN.value, source_type="real_public", license_status="allowed", label_source="repository_documented_change", split="train", extension_id="fixture-extension", category="fixture"):
    old_zip = tmp_path / f"{record_id}-old.zip"
    new_zip = tmp_path / f"{record_id}-new.zip"
    _write_zip(old_zip, version="1.0.0", files={"payload.js": "console.log('old');"})
    _write_zip(new_zip, version="1.1.0", files={"payload.js": "const api = 'http://127.0.0.1:8000/test';"})
    manifest = {
        "dataset_version": "0.1.0-test",
        "records": [{
            "record_id": record_id,
            "extension_id": extension_id,
            "extension_name": "Phase 3D Fixture",
            "source_type": source_type,
            "source_reference": "local-fixture://phase3d",
            "source_repository": "https://example.invalid/repo",
            "source_url": "https://example.invalid/archive",
            "acquisition_timestamp": "2026-08-10T00:00:00+00:00",
            "collector": "pytest",
            "license": "MIT",
            "license_status": license_status,
            "redistribution_allowed": True,
            "research_use_allowed": True,
            "attribution_required": True,
            "is_controlled": False,
            "label": label,
            "label_source": label_source,
            "label_confidence": "medium",
            "label_review_status": "reviewed",
            "functional_category": category,
            "label_rationale": "Fixture label based on test metadata, not DriftWatch score.",
            "evidence_references": ["local-fixture://evidence"],
            "split": split,
            "old": {
                "path": old_zip.name,
                "version": "1.0.0",
                "timestamp": "2026-01-01T00:00:00+00:00",
                "timestamp_source": "fixture",
                "timestamp_confidence": "high",
                "extension_id": extension_id,
            },
            "new": {
                "path": new_zip.name,
                "version": "1.1.0",
                "timestamp": "2026-02-01T00:00:00+00:00",
                "timestamp_source": "fixture",
                "timestamp_confidence": "high",
                "extension_id": extension_id,
            },
        }],
    }
    path = tmp_path / "import_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path, old_zip, new_zip


def test_phase3d_intake_accepts_provenance_rich_real_public_record(tmp_path):
    manifest_path, old_zip, new_zip = _manifest(tmp_path)

    result = curate_import_manifest(manifest_path, dry_run=True)

    assert result.summary()["dataset_version"] == "0.1.0-test"
    assert len(result.accepted) == 1
    curated = result.accepted[0]
    assert curated.record.provenance.old_sha256
    assert curated.record.provenance.new_sha256
    assert curated.metadata["source_reference"] == "local-fixture://phase3d"
    assert curated.metadata["license_status"] == "allowed"
    assert curated.metadata["is_controlled"] is False
    assert curated.record.old_archive_path == str(old_zip.resolve())
    assert curated.record.new_archive_path == str(new_zip.resolve())


def test_missing_provenance_is_not_accepted(tmp_path):
    manifest_path, _, _ = _manifest(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["records"][0]["source_reference"] = ""
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    result = curate_import_manifest(manifest_path)

    assert len(result.accepted) == 0
    assert len(result.excluded) == 1
    assert any("missing source_reference" in reason for reason in result.excluded[0].reasons)


def test_unknown_source_and_unknown_license_are_quarantined(tmp_path):
    manifest_path, _, _ = _manifest(tmp_path, source_type="unknown/unverified", license_status="unknown")

    result = curate_import_manifest(manifest_path)

    assert len(result.accepted) == 0
    assert len(result.quarantined) == 1
    assert any("source_type" in reason for reason in result.quarantined[0].reasons)
    assert any("license_status" in reason for reason in result.quarantined[0].reasons)


def test_extension_identity_mismatch_is_rejected(tmp_path):
    manifest_path, _, _ = _manifest(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["records"][0]["new"]["extension_id"] = "different-extension"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    result = curate_import_manifest(manifest_path)

    assert len(result.accepted) == 0
    assert len(result.excluded) == 1
    assert any("extension IDs do not match" in reason for reason in result.excluded[0].reasons)


def test_version_ordering_uses_temporal_then_semantic_evidence():
    assert compare_versions("1.0.0", "1.1.0") == 1
    assert compare_versions("2.0.0", "1.0.0") == -1
    assert compare_versions("release-a", "release-b") is None
    assert compare_versions("2.0.0", "1.0.0", old_timestamp="2026-01-01T00:00:00+00:00", new_timestamp="2026-02-01T00:00:00+00:00") == 1


def test_consecutive_pair_builder_avoids_all_pair_combinations():
    versions = [
        VersionEntry("1.2.0"),
        VersionEntry("1.0.0"),
        VersionEntry("2.0.0"),
        VersionEntry("1.1.0"),
    ]

    pairs = build_consecutive_pairs(versions)

    assert [(old.version, new.version) for old, new in pairs] == [
        ("1.0.0", "1.1.0"),
        ("1.1.0", "1.2.0"),
        ("1.2.0", "2.0.0"),
    ]


def test_uncertain_label_supported_but_not_accepted_without_review_resolution(tmp_path):
    manifest_path, _, _ = _manifest(tmp_path, label=Label.UNCERTAIN.value)

    result = curate_import_manifest(manifest_path)

    assert len(result.accepted) == 1
    assert result.accepted[0].record.label == Label.UNCERTAIN.value
    assert result.accepted[0].quality_status == "QUESTIONABLE"
    assert result.accepted[0].record.label_quality_tier == LabelQualityTier.UNCERTAIN.value
    assert result.accepted[0].record.eligible_for_supervised_training is False


def test_label_quality_tier_validation_and_training_eligibility(tmp_path):
    manifest_path, _, _ = _manifest(tmp_path, label=Label.RISKY.value, label_source="reputable_security_report")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["records"][0]["label_quality_tier"] = LabelQualityTier.EXTERNAL_CONFIRMED.value
    payload["records"][0]["eligible_for_supervised_training"] = True
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    result = curate_import_manifest(manifest_path)

    record = result.accepted[0].record
    assert record.label_quality_tier == LabelQualityTier.EXTERNAL_CONFIRMED.value
    assert record.eligible_for_supervised_training is True
    assert result.summary()["eligible_supervised_training_count"] == 1
    assert infer_label_quality_tier(label=Label.BENIGN.value, label_source="controlled_ground_truth", review_status="reviewed") == LabelQualityTier.CONTROLLED_GROUND_TRUTH.value


def test_invalid_label_quality_tier_is_rejected(tmp_path):
    manifest_path, _, _ = _manifest(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["records"][0]["label_quality_tier"] = "MADE_UP"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    result = curate_import_manifest(manifest_path)

    assert len(result.accepted) == 0
    assert result.excluded
    assert any("invalid label_quality_tier" in reason for reason in result.excluded[0].reasons)


def test_driftwatch_score_cannot_be_label_source(tmp_path):
    manifest_path, _, _ = _manifest(tmp_path, label_source="driftwatch_score")

    result = curate_import_manifest(manifest_path)

    assert len(result.accepted) == 0
    assert result.excluded
    assert any("DriftWatch score" in reason for reason in result.excluded[0].reasons)


def test_duplicate_detection_finds_record_pair_and_package_duplicates(tmp_path):
    manifest_path, _, _ = _manifest(tmp_path)
    result = curate_import_manifest(manifest_path)
    first = result.accepted[0].record
    duplicate = DatasetPairRecord(
        **{**first.__dict__, "provenance": ProvenanceRecord(**first.provenance.__dict__)}
    )

    report = duplicate_report([first, duplicate])

    assert report["passed"] is False
    assert first.pair_id in report["duplicate_record_ids"]
    assert report["duplicate_pairs"]
    assert first.provenance.old_sha256 in report["duplicate_package_hashes"]


def test_split_audit_detects_group_and_hash_leakage(tmp_path):
    first_manifest, _, _ = _manifest(tmp_path, record_id="pair-a", split="train")
    first = curate_import_manifest(first_manifest).accepted[0].record
    second_manifest, _, _ = _manifest(tmp_path, record_id="pair-b", split="test")
    second = curate_import_manifest(second_manifest).accepted[0].record
    second.extension_id = first.extension_id
    second.provenance.old_sha256 = first.provenance.old_sha256

    report = split_leakage_report([first, second])

    assert report["passed"] is False
    assert any(item["type"] == "extension_group" for item in report["violations"])
    assert any(item["type"] == "package_hash" for item in report["violations"])


def test_malformed_missing_manifest_and_corrupted_archives_are_excluded(tmp_path):
    old_zip = tmp_path / "old.zip"
    missing_manifest_zip = tmp_path / "missing.zip"
    corrupt_zip = tmp_path / "corrupt.zip"
    _write_zip(old_zip, version="1.0.0")
    _write_zip(missing_manifest_zip, manifest=False)
    corrupt_zip.write_text("not a zip", encoding="utf-8")
    manifest = {
        "dataset_version": "0.1.0-test",
        "records": [
            {
                "record_id": "missing-manifest",
                "extension_id": "bad",
                "extension_name": "Bad",
                "source_type": "real_public",
                "source_reference": "fixture",
                "license": "MIT",
                "license_status": "allowed",
                "label": Label.BENIGN.value,
                "label_source": "repository_documented_change",
                "label_confidence": "low",
                "label_review_status": "reviewed",
                "label_rationale": "fixture",
                "old": {"path": old_zip.name, "version": "1.0.0"},
                "new": {"path": missing_manifest_zip.name, "version": "1.1.0"},
            },
            {
                "record_id": "corrupt",
                "extension_id": "bad2",
                "extension_name": "Bad2",
                "source_type": "real_public",
                "source_reference": "fixture",
                "license": "MIT",
                "license_status": "allowed",
                "label": Label.BENIGN.value,
                "label_source": "repository_documented_change",
                "label_confidence": "low",
                "label_review_status": "reviewed",
                "label_rationale": "fixture",
                "old": {"path": old_zip.name, "version": "1.0.0"},
                "new": {"path": corrupt_zip.name, "version": "1.1.0"},
            },
        ],
    }
    manifest_path = tmp_path / "bad_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = curate_import_manifest(manifest_path)

    assert len(result.excluded) == 2
    reasons = " ".join(reason for item in result.excluded for reason in item.reasons)
    assert "missing manifest.json" in reasons
    assert "not a valid ZIP" in reasons


def test_static_safety_and_phase3b_feature_integration_for_accepted_record(tmp_path):
    marker = tmp_path / "executed.txt"
    manifest_path, _, _ = _manifest(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["records"][0]["new"]["path"] = "real-pair-1-new.zip"
    new_zip = tmp_path / "real-pair-1-new.zip"
    _write_zip(
        new_zip,
        version="1.1.0",
        files={"payload.js": f"require('fs').writeFileSync('{marker.as_posix()}', 'bad'); atob('Y29uc29sZS5sb2coMSk=');"},
    )
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    result = curate_import_manifest(manifest_path)
    extraction = DriftBenchFeatureExtractor(base_dir=tmp_path).extract(result.accepted_records)

    assert result.accepted_records
    assert extraction.is_valid
    assert extraction.feature_rows[0].metadata["provenance_id"] == "real_public:real-pair-1"
    assert "eligible_for_supervised_training" in extraction.feature_rows[0].metadata
    assert extraction.feature_rows[0].metadata["functional_category"] == "fixture"
    assert not marker.exists()


def test_phase3d_manifests_and_cli_dry_run_are_written(tmp_path):
    manifest_path, _, _ = _manifest(tmp_path)
    result = curate_import_manifest(manifest_path, dry_run=True)
    output = tmp_path / "phase3d_artifacts"

    paths = write_phase3d_manifests(result, output, source_manifest_path=manifest_path)
    exit_code = ingest_main(["--manifest", str(manifest_path), "--output", str(output / "cli"), "--dry-run"])

    assert exit_code == 0
    assert "dataset_manifest.json" in paths
    dataset_manifest = json.loads((output / "dataset_manifest.json").read_text(encoding="utf-8"))
    assert dataset_manifest["driftbench_version"] == DRIFTBENCH_VERSION
    assert dataset_manifest["accepted"] == 1
    assert dataset_manifest["dataset_manifest_sha256"]
    assert (output / "provenance_manifest.json").exists()
    assert (output / "quality_report.json").exists()
    assert (output / "duplicate_report.json").exists()
    assert (output / "leakage_report.json").exists()
    assert (output / "license_report.json").exists()
    assert (output / "validation_report.json").exists()


def test_manual_review_form_validates_without_using_score_as_label():
    review = ManualReview(
        record_id="real-pair-1",
        reviewer_id="reviewer-a",
        assigned_label=Label.RISKY.value,
        confidence="medium",
        rationale="Evidence-based human label; DriftWatch score is not the source of truth.",
        evidence_examined=["manifest permissions", "network destinations"],
    )

    assert review.validate() == []
    payload = review.to_dict()
    assert payload["assigned_label"] == Label.RISKY.value
    assert "score" not in payload["evidence_examined"]


def test_review_queue_and_adjudication_schema(tmp_path):
    packet = ReviewPacket(
        record_id="uncertain-one",
        extension_id="github:example/ext",
        extension_name="Example",
        old_version="1.0.0",
        new_version="2.0.0",
        release_notes=["No independently reviewed release note available."],
        source_metadata={"source_reference": "https://example.invalid/repo"},
        permission_changes={"added_permissions": []},
        host_changes={"added_hosts": []},
        api_changes={"added_apis": []},
        network_changes={"added_indicators": []},
        obfuscation_changes={"added_indicators": []},
        structural_changes={"source_sink_flows": []},
        external_evidence=[],
        current_label=Label.UNCERTAIN.value,
        current_label_confidence="low",
        current_rationale="Evidence is ambiguous.",
        uncertainty_rationale="No independent evidence justifies benign/risky resolution.",
    )

    queue = write_review_queue(tmp_path / "queue.json", [packet])
    adjudication = AdjudicationRecord(
        record_id="uncertain-one",
        reviewer_labels=[
            {
                "reviewer_id": "reviewer-a",
                "reviewer_label": Label.UNCERTAIN.value,
                "reviewer_confidence": "low",
                "rationale": "Still ambiguous.",
            }
        ],
        disagreement_status="pending",
        adjudicated_label=None,
        adjudication_rationale=None,
    )

    assert queue["packet_count"] == 1
    assert queue["adjudication_template"]["disagreement_status"] == "pending"
    assert adjudication.validate() == []


def test_acquisition_url_validation_and_safe_filename():
    validate_acquisition_url("https://github.com/example/repo/releases/download/v1/build.zip")

    for bad_url in ("http://example.com/file.zip", "file:///tmp/file.zip", "https://user:pass@example.com/file.zip"):
        try:
            validate_acquisition_url(bad_url)
        except ValueError:
            pass
        else:
            raise AssertionError(f"bad URL accepted: {bad_url}")

    assert safe_filename("../bad name?.zip") == "bad_name_.zip"


def test_normalize_extension_zip_preserves_raw_and_normalized_hashes(tmp_path):
    nested_zip = tmp_path / "nested.zip"
    with zipfile.ZipFile(nested_zip, "w") as archive:
        archive.writestr("dist/manifest.json", json.dumps({"manifest_version": 3, "name": "Nested", "version": "1.0.0"}))
        archive.writestr("dist/popup.js", "console.log('static only');")
    normalized_zip = tmp_path / "normalized.zip"

    result = normalize_extension_zip(nested_zip, normalized_zip)

    assert result["normalized_layout"] is True
    assert result["raw_sha256"]
    assert result["normalized_sha256"]
    with zipfile.ZipFile(normalized_zip) as archive:
        assert "manifest.json" in archive.namelist()
        assert "popup.js" in archive.namelist()


def test_real_pilot_readiness_separates_curation_quality_from_ml_readiness(tmp_path):
    dataset = {
        "dataset_version": "0.1.0-real-pilot",
        "driftbench_version": "0.1.0",
        "real_record_count": 1,
        "controlled_record_count": 0,
        "unique_extension_count": 1,
        "accepted": 1,
        "excluded": 0,
        "quarantined": 0,
        "label_distribution": {"uncertain": 1},
        "label_source_distribution": {"single_reviewer_provisional": 1},
        "label_quality_tier_distribution": {"UNCERTAIN": 1},
        "eligible_supervised_training_count": 0,
        "eligible_label_distribution": {},
        "eligible_uncertain_count": 0,
        "license_status_distribution": {"allowed": 1},
        "split_counts": {"test": 1},
        "split_quality": {
            "unique_extensions_per_split": {"test": 1},
            "eligible_labels_per_split": {"test": {}},
        },
    }
    provenance = {
        "provenance_complete_count": 1,
        "records": [{"record_id": "one", "old_tag": "v1", "new_tag": "v2"}],
    }
    duplicate = {"passed": True, "duplicate_record_ids": [], "duplicate_pairs": [], "duplicate_package_hashes": {}, "adjacent_version_reuse": {}}
    leakage = {"passed": True, "violation_count": 0, "violations": []}
    feature_summary = {"record_count": 1, "missingness_counts": {}, "split_counts": {"test": 1}}
    extraction = {"failed_records": [], "feature_schema_version": "1.0", "baselines": ["full_driftwatch"]}
    paths = {}
    for name, payload in {
        "dataset.json": dataset,
        "provenance.json": provenance,
        "duplicate.json": duplicate,
        "leakage.json": leakage,
        "feature_summary.json": feature_summary,
        "extraction.json": extraction,
    }.items():
        path = tmp_path / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path

    report = write_real_pilot_readiness(
        tmp_path / "readiness.json",
        dataset_manifest_path=paths["dataset.json"],
        provenance_manifest_path=paths["provenance.json"],
        duplicate_report_path=paths["duplicate.json"],
        leakage_report_path=paths["leakage.json"],
        feature_summary_path=paths["feature_summary.json"],
        extraction_manifest_path=paths["extraction.json"],
        existing_controlled_count=2,
    )

    assert report["pilot_quality_gate_passed"] is True
    assert report["phase3e_ml_re_evaluation_ready"] is False
    assert report["real_vs_controlled_counts"]["existing_controlled_artifact_records"] == 2


def test_split_quality_blocks_weak_test_split_and_warns_on_single_label(tmp_path):
    records = []
    for index in range(6):
        manifest_path, _, _ = _manifest(
            tmp_path,
            record_id=f"pair-{index}",
            split="test",
            extension_id=f"fixture-extension-{index // 3}",
        )
        records.append(curate_import_manifest(manifest_path).accepted[0].record)

    report = split_quality_report(records)

    assert report["minimum_test_quality_passed"] is True
    assert report["unique_extensions_per_split"]["test"] == 2
    assert "single eligible supervised label class" in " ".join(report["warnings"])


def test_split_quality_rejects_insufficient_test_split(tmp_path):
    records = []
    for index in range(4):
        manifest_path, _, _ = _manifest(tmp_path, record_id=f"small-{index}", split="test", extension_id=f"ext-{index}")
        records.append(curate_import_manifest(manifest_path).accepted[0].record)

    report = split_quality_report(records)

    assert report["minimum_test_quality_passed"] is False
    assert any("fewer than five records" in reason for reason in report["block_reasons"])


def test_phase3e_readiness_passes_only_when_methodology_is_strong(tmp_path):
    dataset = {
        "dataset_version": "0.1.0-real-pilot",
        "driftbench_version": "0.1.0",
        "real_record_count": 20,
        "controlled_record_count": 0,
        "unique_extension_count": 5,
        "accepted": 20,
        "excluded": 0,
        "quarantined": 0,
        "label_distribution": {Label.BENIGN.value: 12, Label.RISKY.value: 8},
        "label_source_distribution": {"single_reviewer_provisional": 20},
        "label_quality_tier_distribution": {"SINGLE_REVIEWER_PROVISIONAL": 20},
        "eligible_supervised_training_count": 20,
        "eligible_label_distribution": {Label.BENIGN.value: 12, Label.RISKY.value: 8},
        "eligible_uncertain_count": 0,
        "license_status_distribution": {"allowed": 20},
        "split_counts": {"train": 10, "validation": 5, "test": 5},
        "split_quality": {
            "unique_extensions_per_split": {"train": 2, "validation": 1, "test": 2},
            "eligible_labels_per_split": {"test": {Label.BENIGN.value: 3, Label.RISKY.value: 2}},
        },
    }
    provenance = {
        "provenance_complete_count": 20,
        "records": [{"record_id": f"r{i}", "old_tag": "v1", "new_tag": "v2"} for i in range(20)],
    }
    duplicate = {"passed": True, "duplicate_record_ids": [], "duplicate_pairs": [], "duplicate_package_hashes": {}, "adjacent_version_reuse": {}}
    leakage = {"passed": True, "violation_count": 0, "violations": []}
    feature_summary = {"record_count": 20, "missingness_counts": {}, "split_counts": {"train": 10, "validation": 5, "test": 5}}
    extraction = {"failed_records": [], "feature_schema_version": "1.0", "baselines": ["full_driftwatch"]}
    paths = {}
    for name, payload in {
        "dataset.json": dataset,
        "provenance.json": provenance,
        "duplicate.json": duplicate,
        "leakage.json": leakage,
        "feature_summary.json": feature_summary,
        "extraction.json": extraction,
    }.items():
        path = tmp_path / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path

    report = write_real_pilot_readiness(
        tmp_path / "readiness.json",
        dataset_manifest_path=paths["dataset.json"],
        provenance_manifest_path=paths["provenance.json"],
        duplicate_report_path=paths["duplicate.json"],
        leakage_report_path=paths["leakage.json"],
        feature_summary_path=paths["feature_summary.json"],
        extraction_manifest_path=paths["extraction.json"],
    )

    assert report["phase3e_ml_re_evaluation_ready"] is True
    assert report["phase3e_block_reasons"] == []
    assert report["phase3e_warnings"]


def test_phase3e_readiness_blocks_when_methodology_is_weak(tmp_path):
    dataset = {
        "dataset_version": "0.1.0-real-pilot",
        "driftbench_version": "0.1.0",
        "real_record_count": 6,
        "controlled_record_count": 0,
        "unique_extension_count": 2,
        "accepted": 6,
        "excluded": 0,
        "quarantined": 0,
        "label_distribution": {Label.BENIGN.value: 5, Label.UNCERTAIN.value: 1},
        "label_source_distribution": {"single_reviewer_provisional": 6},
        "label_quality_tier_distribution": {"SINGLE_REVIEWER_PROVISIONAL": 5, "UNCERTAIN": 1},
        "eligible_supervised_training_count": 5,
        "eligible_label_distribution": {Label.BENIGN.value: 5},
        "eligible_uncertain_count": 0,
        "license_status_distribution": {"allowed": 6},
        "split_counts": {"train": 4, "test": 2},
        "split_quality": {
            "unique_extensions_per_split": {"test": 1},
            "eligible_labels_per_split": {"test": {Label.BENIGN.value: 2}},
        },
    }
    provenance = {
        "provenance_complete_count": 6,
        "records": [{"record_id": f"r{i}", "old_tag": "v1", "new_tag": "v2"} for i in range(6)],
    }
    duplicate = {"passed": True, "duplicate_record_ids": [], "duplicate_pairs": [], "duplicate_package_hashes": {}, "adjacent_version_reuse": {}}
    leakage = {"passed": True, "violation_count": 0, "violations": []}
    feature_summary = {"record_count": 6, "missingness_counts": {}, "split_counts": {"train": 4, "test": 2}}
    extraction = {"failed_records": [], "feature_schema_version": "1.0", "baselines": ["full_driftwatch"]}
    paths = {}
    for name, payload in {
        "dataset.json": dataset,
        "provenance.json": provenance,
        "duplicate.json": duplicate,
        "leakage.json": leakage,
        "feature_summary.json": feature_summary,
        "extraction.json": extraction,
    }.items():
        path = tmp_path / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path

    report = write_real_pilot_readiness(
        tmp_path / "readiness.json",
        dataset_manifest_path=paths["dataset.json"],
        provenance_manifest_path=paths["provenance.json"],
        duplicate_report_path=paths["duplicate.json"],
        leakage_report_path=paths["leakage.json"],
        feature_summary_path=paths["feature_summary.json"],
        extraction_manifest_path=paths["extraction.json"],
    )

    assert report["phase3e_ml_re_evaluation_ready"] is False
    assert report["phase3e_block_reasons"]
