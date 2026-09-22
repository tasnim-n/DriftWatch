import json
import zipfile
from pathlib import Path

import pytest

from research.human_review_integration import (
    HUMAN_TO_DATASET_LABEL,
    INITIAL_BLIND,
    NOT_COMPARABLE,
    REVIEWER01_ID,
    REVIEWER02_ID,
    PLACEHOLDER_CONFIRMED,
    HumanReviewIntegrationError,
    audit_reviewer02_workspace,
    build_reviewer02_package,
    derive_review_id,
    load_and_validate_reviewer01_archive,
    load_and_validate_reviewer02_archive,
    map_human_label,
    sha256_file,
    validate_completed_submission,
    verify_file_sha256,
    write_human_vs_provisional_comparison,
    write_reviewer01_derived_layer,
    write_reviewer02_derived_layer,
)


def _packet(record_id: str, value: int) -> dict:
    return {
        "record_id": record_id,
        "blind_review": True,
        "observed_signal": {"value": value},
    }


def _completed_submission(record_id: str, label: str = "RISKY_TRANSITION") -> dict:
    return {
        "reviewer_id": REVIEWER01_ID,
        "record_id": record_id,
        "review_round": INITIAL_BLIND,
        "independent_label": label,
        "confidence": "MEDIUM",
        "rationale": f"Independent rationale for {record_id}.",
        "evidence_references": ["observed_signal.value"],
        "blind_review": True,
        "review_timestamp": "2026-09-22T09:00:00+06:00",
        "review_status": "SUBMITTED",
    }


def _sample_archive(tmp_path: Path) -> tuple[Path, str, list[str]]:
    archive_path = tmp_path / "reviewer01.zip"
    record_ids = [f"record_{index:02d}" for index in range(14)]
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for index, record_id in enumerate(record_ids):
            archive.writestr(
                f"return/packets/{record_id}.json",
                json.dumps(_packet(record_id, index)),
            )
            label = "UNCERTAIN" if index % 3 == 0 else "RISKY_TRANSITION"
            archive.writestr(
                f"return/submissions/{record_id}.json",
                json.dumps(_completed_submission(record_id, label)),
            )
    return archive_path, sha256_file(archive_path), record_ids


def _sample_reviewer02_archive(tmp_path: Path) -> tuple[Path, str, Path, list[str]]:
    archive_path = tmp_path / "reviewer02.zip"
    packet_root = tmp_path / "packets"
    packet_root.mkdir()
    record_ids = [f"record_{index:02d}" for index in range(14)]
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for index, record_id in enumerate(record_ids):
            (packet_root / f"{record_id}.json").write_text(
                json.dumps(_packet(record_id, index)), encoding="utf-8"
            )
            submission = {
                **_completed_submission(record_id),
                "review_id": "",
                "reviewer_id": REVIEWER02_ID,
                "review_timestamp": "2026-09-22T01:41:08.233Z",
            }
            archive.writestr(
                f"submissions/{record_id}.json",
                json.dumps(submission),
            )
    return archive_path, sha256_file(archive_path), packet_root, record_ids


def test_raw_zip_hash_verification_accepts_exact_hash_and_rejects_mismatch(tmp_path):
    archive_path, digest, _ = _sample_archive(tmp_path)

    assert verify_file_sha256(archive_path, digest) == digest
    with pytest.raises(HumanReviewIntegrationError, match="SHA-256 mismatch"):
        verify_file_sha256(archive_path, "0" * 64)


def test_label_mapping_matches_documented_ontologies_and_preserves_unknowns():
    assert HUMAN_TO_DATASET_LABEL == {
        "BENIGN_TRANSITION": "benign_transition",
        "RISKY_TRANSITION": "risky_transition",
        "MALICIOUS_TRANSITION": "malicious_transition",
        "UNCERTAIN": "uncertain",
        "EXCLUDED": "excluded",
    }
    assert map_human_label("RISKY_TRANSITION") == "risky_transition"
    assert map_human_label("UNRECOGNIZED") == NOT_COMPARABLE


def test_derived_review_ids_are_deterministic_reviewer_and_record_aware():
    first = derive_review_id(REVIEWER01_ID, "record_a", INITIAL_BLIND)
    assert first == derive_review_id(REVIEWER01_ID, "record_a", INITIAL_BLIND)
    assert first != derive_review_id(REVIEWER02_ID, "record_a", INITIAL_BLIND)
    assert first != derive_review_id(REVIEWER01_ID, "record_b", INITIAL_BLIND)
    with pytest.raises(HumanReviewIntegrationError):
        derive_review_id(REVIEWER01_ID, "bad::record", INITIAL_BLIND)


def test_completed_submission_validation_is_strict_but_allows_legacy_missing_review_id():
    packet = _packet("record_a", 1)
    submission = _completed_submission("record_a")

    assert validate_completed_submission(
        submission,
        packet,
        expected_reviewer_id=REVIEWER01_ID,
        allow_derived_review_id=True,
    ) == []
    invalid = {**submission, "rationale": "", "blind_review": False}
    errors = validate_completed_submission(
        invalid,
        packet,
        expected_reviewer_id=REVIEWER01_ID,
        allow_derived_review_id=True,
    )
    assert "rationale is required" in errors
    assert "blind_review must be true" in errors


def test_derived_reviewer01_layer_preserves_raw_values_and_refuses_overwrite(tmp_path):
    archive_path, digest, _ = _sample_archive(tmp_path)
    bundle = load_and_validate_reviewer01_archive(archive_path, expected_sha256=digest)
    output = tmp_path / "derived"

    report = write_reviewer01_derived_layer(bundle, output)

    assert report["validated_submission_count"] == 14
    assert report["canonical_missing_field_distribution"] == {"review_id": 14}
    first_record = bundle["records"][0]
    wrapper = json.loads(
        (output / "validated_submissions" / first_record["raw_submission_filename"]).read_text(
            encoding="utf-8"
        )
    )
    assert wrapper["original_submission"] == first_record["submission"]
    assert "mapped_human_comparison_label" not in wrapper
    with pytest.raises(FileExistsError):
        write_reviewer01_derived_layer(bundle, output)


def test_reviewer02_placeholder_timestamps_and_blank_review_ids_are_derived_only(tmp_path):
    archive_path, digest, packet_root, _ = _sample_reviewer02_archive(tmp_path)
    before = sha256_file(archive_path)

    bundle = load_and_validate_reviewer02_archive(
        archive_path,
        packet_root=packet_root,
        expected_sha256=digest,
    )
    report = write_reviewer02_derived_layer(bundle, tmp_path / "derived02")

    assert bundle["timestamp_quality"] == PLACEHOLDER_CONFIRMED
    assert report["status"] == "VALIDATED_WITH_DERIVED_IDS_AND_PLACEHOLDER_TIMESTAMPS"
    assert report["canonical_missing_field_distribution"] == {"review_id": 14}
    assert report["evidence_references_resolved_count"] == 14
    wrapper_path = sorted((tmp_path / "derived02" / "validated_submissions").glob("*.json"))[0]
    wrapper = json.loads(wrapper_path.read_text(encoding="utf-8"))
    assert wrapper["original_submission"]["review_id"] == ""
    assert wrapper["derived_review_id"].startswith("HRV1::human_reviewer_02::")
    assert wrapper["timestamp_quality"] == PLACEHOLDER_CONFIRMED
    assert sha256_file(archive_path) == before


def test_human_vs_provisional_concordance_is_separate_and_descriptive(tmp_path):
    archive_path, digest, record_ids = _sample_archive(tmp_path)
    bundle = load_and_validate_reviewer01_archive(archive_path, expected_sha256=digest)
    manifest = {
        "records": [
            {
                "pair_id": record_id,
                "label": "risky_transition",
                "label_source": "single_reviewer_provisional",
                "label_quality_tier": "SINGLE_REVIEWER_PROVISIONAL",
                "label_review_status": "provisional",
            }
            for record_id in record_ids
        ]
    }
    manifest_path = tmp_path / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = write_human_vs_provisional_comparison(
        bundle, manifest_path, tmp_path / "comparison"
    )

    assert report["title"] == "HUMAN-vs-PROVISIONAL LABEL CONCORDANCE"
    assert report["comparable_record_count"] == 14
    assert report["exact_match_count"] == 9
    assert "inter-rater agreement" in report["methodological_status"]


def test_reviewer02_package_is_pending_blind_unique_and_contains_only_allowlisted_files(tmp_path):
    archive_path, digest, _ = _sample_archive(tmp_path)
    bundle = load_and_validate_reviewer01_archive(archive_path, expected_sha256=digest)
    workspace = tmp_path / "reviewer02"
    package = tmp_path / "reviewer02.zip"
    audit_path = tmp_path / "audit" / "package_audit.json"

    audit = build_reviewer02_package(
        bundle,
        workspace=workspace,
        output_zip=package,
        audit_output=audit_path,
        holdout_ids=[],
    )

    assert audit["passed"] is True
    assert audit["packet_count"] == 14
    assert audit["submission_count"] == 14
    assert audit["holdout_overlap"] == []
    assert audit["package_sha256"] == sha256_file(package)
    submissions = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((workspace / "submissions").glob("*.json"))
    ]
    assert {row["reviewer_id"] for row in submissions} == {REVIEWER02_ID}
    assert {row["review_status"] for row in submissions} == {"PENDING"}
    assert {row["independent_label"] for row in submissions} == {""}
    assert len({row["review_id"] for row in submissions}) == 14
    assert audit_reviewer02_workspace(workspace, ["not_in_package"])["passed"] is True
    with zipfile.ZipFile(package) as archive:
        names = set(archive.namelist())
    assert "PACKAGE_MANIFEST.md" in names
    assert all("reviewer01" not in name.lower() for name in names)
