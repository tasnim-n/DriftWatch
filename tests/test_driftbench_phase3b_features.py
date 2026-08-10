import csv
import json
import os
import zipfile

import pytest

from analyzers.api_analyzer import APIAnalyzer
from driftbench.features import (
    BASELINE_FULL_DRIFTWATCH,
    BASELINE_LATEST_STATIC,
    BASELINE_MANIFEST_PERMISSION,
    BASELINE_PERMISSION_ONLY,
    BASELINE_SIMPLE_DIFFERENTIAL,
    BASELINES,
    DriftBenchFeatureExtractor,
    FEATURE_SCHEMA_VERSION,
    LEAKAGE_FORBIDDEN_FEATURE_TERMS,
    build_feature_schema,
    write_feature_artifacts,
)
from driftbench.labels import Label
from driftbench.provenance import sha256_file
from driftbench.schema import DatasetPairRecord, ProvenanceRecord
from driftbench.validator import DatasetValidator


def _write_zip(path, manifest, files=None):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for name, content in (files or {}).items():
            archive.writestr(name, content)


def _record(tmp_path, pair_id="pair-1", extension_id="ext-1", split="train", label=Label.BENIGN.value):
    old_zip = tmp_path / f"{pair_id}_old.zip"
    new_zip = tmp_path / f"{pair_id}_new.zip"
    _write_zip(
        old_zip,
        {
            "manifest_version": 3,
            "name": "Neutral Notes",
            "version": "1.0.0",
            "permissions": ["storage"],
            "host_permissions": ["https://notes.local/*"],
            "action": {"default_popup": "popup.html"},
        },
        {"popup.js": "function saveNote() { console.log('save'); }"},
    )
    _write_zip(
        new_zip,
        {
            "manifest_version": 3,
            "name": "Neutral Notes",
            "version": "1.1.0",
            "permissions": ["storage", "history"],
            "host_permissions": ["https://notes.local/*"],
            "action": {"default_popup": "popup.html"},
            "background": {"service_worker": "worker.js"},
        },
        {"popup.js": "function saveNote() { console.log('save'); }", "worker.js": 'fetch("http://127.0.0.1:8000/test");'},
    )
    return DatasetPairRecord(
        pair_id=pair_id,
        extension_id=extension_id,
        extension_name="Neutral Notes",
        old_version="1.0.0",
        new_version="1.1.0",
        old_archive_path=old_zip.name,
        new_archive_path=new_zip.name,
        old_timestamp="2026-01-01T00:00:00+00:00",
        new_timestamp="2026-02-01T00:00:00+00:00",
        source="controlled",
        license="synthetic-research",
        label=label,
        label_rationale="Controlled test label.",
        provenance=ProvenanceRecord(
            source_type="controlled_sample",
            source_uri="pytest",
            collection_timestamp="2026-08-10T00:00:00+00:00",
            license="synthetic-research",
            collector="pytest",
            old_sha256=sha256_file(old_zip),
            new_sha256=sha256_file(new_zip),
            generation_method="phase3b-test",
        ),
        split=split,
    )


def _extract_one(tmp_path):
    record = _record(tmp_path)
    extractor = DriftBenchFeatureExtractor(base_dir=tmp_path)
    result = extractor.extract([record])
    assert result.is_valid
    return result.feature_rows[0], result


def test_feature_extraction_never_executes_javascript(tmp_path):
    marker = tmp_path / "executed.txt"
    old_zip = tmp_path / "old.zip"
    new_zip = tmp_path / "new.zip"
    manifest = {"manifest_version": 3, "name": "No Exec", "version": "1.0.0", "permissions": []}
    _write_zip(old_zip, manifest, {"payload.js": "console.log('old');"})
    _write_zip(
        new_zip,
        dict(manifest, version="1.1.0"),
        {"payload.js": f"require('fs').writeFileSync('{marker.as_posix()}', 'executed');"},
    )
    record = _record(tmp_path)
    record.pair_id = "no-exec"
    record.extension_id = "no-exec"
    record.old_archive_path = old_zip.name
    record.new_archive_path = new_zip.name
    record.provenance.old_sha256 = sha256_file(old_zip)
    record.provenance.new_sha256 = sha256_file(new_zip)

    result = DriftBenchFeatureExtractor(base_dir=tmp_path).extract([record])

    assert result.is_valid
    assert not marker.exists()


def test_invalid_record_rejected_before_extraction(tmp_path):
    record = _record(tmp_path)
    record.extension_id = ""

    result = DriftBenchFeatureExtractor(base_dir=tmp_path).extract([record])

    assert not result.is_valid
    assert result.feature_rows == []
    assert any("missing extension_id" in error for error in result.validation_errors)


def test_untrusted_absolute_archive_path_outside_base_is_quarantined(tmp_path):
    outside_dir = tmp_path.parent / f"{tmp_path.name}_outside"
    outside_dir.mkdir(exist_ok=True)
    outside_zip = outside_dir / "outside.zip"
    _write_zip(outside_zip, {"manifest_version": 3, "name": "Outside", "version": "1.0.0"})
    record = _record(tmp_path)
    record.old_archive_path = str(outside_zip)
    record.provenance.old_sha256 = sha256_file(outside_zip)

    result = DriftBenchFeatureExtractor(base_dir=tmp_path).extract([record])

    assert not result.is_valid
    assert result.failed_records
    assert "escapes DriftBench base directory" in result.failed_records[0]["error"]


def test_metadata_preserves_provenance_label_versions_and_split(tmp_path):
    row, _ = _extract_one(tmp_path)

    assert row.metadata["record_id"] == "pair-1"
    assert row.metadata["extension_id"] == "ext-1"
    assert row.metadata["old_version"] == "1.0.0"
    assert row.metadata["new_version"] == "1.1.0"
    assert row.metadata["label"] == Label.BENIGN.value
    assert row.metadata["split"] == "train"
    assert row.metadata["provenance_id"] == "controlled_sample:pair-1"


def test_label_and_target_derived_fields_are_metadata_only(tmp_path):
    row, result = _extract_one(tmp_path)
    feature_names = set(row.features)

    assert "label" not in feature_names
    assert "risk_score" not in feature_names
    assert "risk_classification" not in feature_names
    assert "recommendation" not in feature_names
    assert row.metadata["label"] == Label.BENIGN.value
    for definition in result.schema:
        lowered = definition.name.lower()
        assert not any(term in lowered for term in LEAKAGE_FORBIDDEN_FEATURE_TERMS)


def test_sample_folder_names_do_not_create_features(tmp_path):
    row, _ = _extract_one(tmp_path)

    for value in row.features.values():
        assert not isinstance(value, str)


def test_baseline_feature_family_boundaries(tmp_path):
    _, result = _extract_one(tmp_path)
    by_baseline = {
        baseline: [definition for definition in result.schema if baseline in definition.baselines]
        for baseline in BASELINES
    }

    assert {definition.family for definition in by_baseline[BASELINE_PERMISSION_ONLY]} <= {"permission_drift", "manifest_permission"}
    assert all(definition.family not in {"api_drift", "network_drift", "obfuscation_drift", "structural_drift"} for definition in by_baseline[BASELINE_MANIFEST_PERMISSION])
    assert all(not definition.name.endswith("_delta") and not definition.name.startswith(("added_", "removed_")) for definition in by_baseline[BASELINE_LATEST_STATIC] if not definition.name.endswith("_available"))
    assert all(definition.family in {"simple_differential", "host_drift", "analyzer_health"} for definition in by_baseline[BASELINE_SIMPLE_DIFFERENTIAL])
    full_families = {definition.family for definition in by_baseline[BASELINE_FULL_DRIFTWATCH]}
    assert {"permission_drift", "api_drift", "network_drift", "obfuscation_drift", "structural_drift", "package_drift"} <= full_families


def test_repeated_extraction_is_deterministic(tmp_path):
    record = _record(tmp_path)
    extractor = DriftBenchFeatureExtractor(base_dir=tmp_path)

    first = extractor.extract([record])
    second = extractor.extract([record])

    assert [definition.name for definition in first.schema] == [definition.name for definition in second.schema]
    assert first.feature_rows[0].features == second.feature_rows[0].features


def test_analyzer_failure_is_distinguishable_from_genuine_zero(tmp_path, monkeypatch):
    record = _record(tmp_path)

    def fail_api(cls, old_dir, new_dir):
        raise RuntimeError("forced api failure")

    monkeypatch.setattr(APIAnalyzer, "compare_api_drift", classmethod(fail_api))
    result = DriftBenchFeatureExtractor(base_dir=tmp_path).extract([record])

    assert result.is_valid
    row = result.feature_rows[0]
    assert row.features["api_analyzer_available"] == 0
    assert row.features["added_api_count"] == 0


def test_split_assignments_preserved_without_reshuffle(tmp_path):
    first = _record(tmp_path, pair_id="a", extension_id="ext-a", split="train")
    second = _record(tmp_path, pair_id="b", extension_id="ext-b", split="test")
    result = DriftBenchFeatureExtractor(base_dir=tmp_path).extract([first, second])

    splits = {row.metadata["record_id"]: row.metadata["split"] for row in result.feature_rows}

    assert splits == {"a": "train", "b": "test"}
    assert DatasetValidator.validate_records([first, second], base_dir=tmp_path).is_valid


def test_artifact_output_csv_jsonl_schema_manifest_and_summary(tmp_path):
    row, result = _extract_one(tmp_path)
    output = tmp_path / "artifacts"

    paths = write_feature_artifacts(
        result,
        output,
        dataset_id="pytest-driftbench",
        dataset_version="phase3b-test",
        generation_timestamp="2026-08-10T00:00:00+00:00",
        code_version=None,
        seed=1337,
    )

    assert os.path.exists(paths["feature_schema"])
    assert os.path.exists(paths["permission_only_csv"])
    assert os.path.exists(paths["permission_only_jsonl"])
    assert os.path.exists(paths["extraction_manifest"])
    with open(paths["feature_schema"], encoding="utf-8") as handle:
        schema = json.loads(handle.read())
    with open(paths["extraction_manifest"], encoding="utf-8") as handle:
        manifest = json.loads(handle.read())
    with open(paths["dataset_summary"], encoding="utf-8") as handle:
        summary = json.loads(handle.read())

    assert schema["driftbench_feature_schema_version"] == FEATURE_SCHEMA_VERSION
    assert manifest["record_count"] == 1
    assert summary["record_count"] == 1

    with open(paths["full_driftwatch_csv"], newline="", encoding="utf-8") as handle:
        csv_row = next(csv.DictReader(handle))
    with open(paths["full_driftwatch_jsonl"], encoding="utf-8") as handle:
        jsonl_row = json.loads(handle.readline())

    feature_names = {feature["name"] for feature in schema["features"] if "full_driftwatch" in feature["baselines"]}
    assert feature_names <= set(csv_row.keys())
    assert set(jsonl_row.keys()) == set(csv_row.keys())
    assert csv_row["record_id"] == row.metadata["record_id"]


def test_artifact_output_is_deterministic_with_fixed_timestamp(tmp_path):
    _, result = _extract_one(tmp_path)
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"

    first = write_feature_artifacts(result, first_dir, dataset_id="det", dataset_version="1", generation_timestamp="2026-08-10T00:00:00+00:00")
    second = write_feature_artifacts(result, second_dir, dataset_id="det", dataset_version="1", generation_timestamp="2026-08-10T00:00:00+00:00")

    for key in first:
        with open(first[key], encoding="utf-8") as first_handle, open(second[key], encoding="utf-8") as second_handle:
            assert first_handle.read() == second_handle.read()
