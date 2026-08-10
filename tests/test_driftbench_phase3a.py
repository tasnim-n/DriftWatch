import json
import os
import shutil
import tempfile
import zipfile

from driftbench.labels import LABEL_ONTOLOGY, Label, is_valid_label
from driftbench.mutations import ControlledMutationFramework, MutationSpec, MutationType
from driftbench.provenance import sha256_file
from driftbench.schema import DatasetPairRecord, ProvenanceRecord
from driftbench.splits import (
    apply_split_assignments,
    assign_chronological_group_splits,
    assign_group_random_splits,
)
from driftbench.validator import DatasetValidator
from analyzers.drift_engine import DriftEngine


def _record(pair_id, extension_id, old_path, new_path, label=Label.BENIGN.value, split=None):
    return DatasetPairRecord(
        pair_id=pair_id,
        extension_id=extension_id,
        extension_name=f"Extension {extension_id}",
        old_version="1.0.0",
        new_version="1.1.0",
        old_archive_path=old_path,
        new_archive_path=new_path,
        old_timestamp="2026-01-01T00:00:00+00:00",
        new_timestamp="2026-02-01T00:00:00+00:00",
        source="controlled",
        license="synthetic-research",
        label=label,
        label_rationale="Controlled test label with explicit rationale.",
        provenance=ProvenanceRecord(
            source_type="controlled_sample",
            source_uri="samples",
            collection_timestamp="2026-08-10T00:00:00+00:00",
            license="synthetic-research",
            collector="pytest",
            old_sha256=sha256_file(old_path),
            new_sha256=sha256_file(new_path),
            generation_method="unit-test",
        ),
        controlled_mutation_type=None,
        split=split,
    )


def test_label_ontology_has_operational_definitions():
    assert is_valid_label(Label.BENIGN.value)
    assert is_valid_label(Label.RISKY.value)
    assert LABEL_ONTOLOGY[Label.CONTROLLED_MALICIOUS.value]["allowed_for_training"] is False
    assert "decision_rule" in LABEL_ONTOLOGY[Label.RISKY.value]


def test_dataset_validator_accepts_valid_controlled_records():
    record = _record(
        "pair-benign",
        "quick-note-benign",
        "samples/v1_note_benign.zip",
        "samples/v2_note_benign.zip",
    )

    report = DatasetValidator.validate_records([record], base_dir=".", validate_paths=True)

    assert report.is_valid is True
    assert report.errors == []
    assert report.record_count == 1


def test_dataset_validator_rejects_bad_label_and_hash_mismatch():
    record = _record(
        "pair-bad",
        "quick-note-bad",
        "samples/v1_note_benign.zip",
        "samples/v2_note_benign.zip",
        label="malware-ish",
    )
    record.provenance.new_sha256 = "0" * 64

    report = DatasetValidator.validate_records([record], base_dir=".", validate_paths=True)

    assert report.is_valid is False
    assert any("invalid label" in error for error in report.errors)
    assert any("SHA-256 mismatch" in error for error in report.errors)


def test_dataset_validator_detects_split_leakage_by_extension_id():
    first = _record("pair-1", "same-extension", "samples/v1_note_benign.zip", "samples/v2_note_benign.zip", split="train")
    second = _record("pair-2", "same-extension", "samples/v1_safe_note.zip", "samples/v2_risky_note.zip", split="test")

    report = DatasetValidator.validate_records([first, second], base_dir=".", validate_paths=False)

    assert report.is_valid is False
    assert any("multiple experiment splits" in error for error in report.errors)


def test_group_random_split_keeps_extension_groups_together():
    records = [
        _record("a-1", "a", "samples/v1_note_benign.zip", "samples/v2_note_benign.zip"),
        _record("a-2", "a", "samples/v1_safe_note.zip", "samples/v2_risky_note.zip"),
        _record("b-1", "b", "samples/v1_note_benign.zip", "samples/v2_note_benign.zip"),
        _record("c-1", "c", "samples/v1_note_benign.zip", "samples/v2_note_benign.zip"),
    ]

    assignments = assign_group_random_splits(records, train_ratio=0.5, validation_ratio=0.25, test_ratio=0.25, seed=7)
    apply_split_assignments(records, assignments)

    assert records[0].split == records[1].split
    assert set(assignments.values()) <= {"train", "validation", "test"}


def test_chronological_split_orders_by_group_latest_timestamp():
    early = _record("early", "early-extension", "samples/v1_note_benign.zip", "samples/v2_note_benign.zip")
    late = _record("late", "late-extension", "samples/v1_note_benign.zip", "samples/v2_note_benign.zip")
    early.new_timestamp = "2026-01-01T00:00:00+00:00"
    late.new_timestamp = "2026-12-01T00:00:00+00:00"

    assignments = assign_chronological_group_splits([early, late], train_ratio=0.5, validation_ratio=0.0, test_ratio=0.5)

    assert assignments["early-extension"] == "train"
    assert assignments["late-extension"] == "test"


def test_controlled_mutation_creates_safe_network_update_detected_by_phase2():
    temp_dir = tempfile.mkdtemp()
    output_dir = os.path.join(temp_dir, "mutated")
    try:
        result = ControlledMutationFramework.apply_mutation(
            "samples/v1_note_benign",
            output_dir,
            MutationSpec(
                mutation_type=MutationType.NETWORK_ENDPOINT_INTRODUCTION,
                output_version="1.1.0",
                endpoint="http://127.0.0.1:8000/driftbench-controlled",
            ),
        )

        drift = DriftEngine.compute_behavioral_drift("samples/v1_note_benign", output_dir)

        assert result["mutation_type"] == MutationType.NETWORK_ENDPOINT_INTRODUCTION.value
        assert drift["network_diff"]["new_local_count"] == 1
        assert drift["network_diff"]["new_external_count"] == 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_controlled_obfuscation_mutation_uses_static_base64_without_execution():
    temp_dir = tempfile.mkdtemp()
    output_dir = os.path.join(temp_dir, "encoded")
    try:
        ControlledMutationFramework.apply_mutation(
            "samples/v1_note_benign",
            output_dir,
            MutationSpec(
                mutation_type=MutationType.OBFUSCATION_INTRODUCTION,
                output_version="1.1.0",
                endpoint="http://127.0.0.1:8000/encoded",
            ),
        )

        drift = DriftEngine.compute_behavioral_drift("samples/v1_note_benign", output_dir)

        assert drift["obfuscation_diff"]["added_obfuscation_score"] > 0
        assert drift["network_diff"]["decoded_static_endpoints"][0]["decoded_indicator"] == "http://127.0.0.1:8000/encoded"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
