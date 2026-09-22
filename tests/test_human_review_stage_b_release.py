from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from research.human_review_adjudication import (
    DEFAULT_ADJUDICATOR_ID,
    EXPECTED_DISAGREEMENT_IDS,
    STAGE_A,
    HumanReviewAdjudicationError,
    create_adjudicator_workspace,
    derive_adjudication_review_id,
    evaluate_stage_b_release_gate,
)
from research.human_review_agreement import build_agreement_analysis
from research.human_review_integration import (
    INITIAL_BLIND,
    REVIEWER01_ID,
    REVIEWER02_ID,
    HumanReviewIntegrationError,
    derive_review_id,
    sha256_bytes,
    sha256_file,
)
from research.human_review_stage_b_release import (
    EXPECTED_STAGE_A_JUDGMENTS,
    STAGE_A_TIMESTAMP_PROVENANCE,
    audit_stage_b_package,
    build_stage_b_package,
    create_stage_b_release_workspace,
    load_and_validate_stage_a_return,
    write_stage_a_validation_layer,
)


def _packet(record_id: str, value: int) -> tuple[dict, bytes]:
    packet = {
        "record_id": record_id,
        "blind_review": True,
        "observed_signal": {"value": value},
    }
    raw = b"\xef\xbb\xbf" + (json.dumps(packet, indent=2) + "\n").encode("utf-8")
    return packet, raw


def _review_record(record_id: str, reviewer_id: str, label: str, value: int) -> dict:
    packet, raw = _packet(record_id, value)
    submission = {
        "reviewer_id": reviewer_id,
        "record_id": record_id,
        "review_round": INITIAL_BLIND,
        "independent_label": label,
        "confidence": "MEDIUM",
        "rationale": f"Verbatim evidence assessment {value} for {record_id}.",
        "evidence_references": [
            "observed_signal.value=observed; observed_signal.value=confirmed"
        ],
        "blind_review": True,
        "review_status": "SUBMITTED",
        "review_timestamp": "2026-09-22T09:00:00+06:00",
    }
    record = {
        "record_id": record_id,
        "derived_review_id": derive_review_id(reviewer_id, record_id, INITIAL_BLIND),
        "raw_submission_entry_name": f"submissions/{record_id}.json",
        "raw_submission_sha256": sha256_bytes(json.dumps(submission).encode("utf-8")),
        "submission": submission,
        "packet": packet,
    }
    if reviewer_id == REVIEWER01_ID:
        record["packet_raw_bytes"] = raw
    else:
        record["packet_source_sha256"] = sha256_bytes(raw)
    return record


def _review_bundles() -> tuple[dict, dict, dict]:
    record_ids = list(EXPECTED_DISAGREEMENT_IDS) + [f"agreed_{index:02d}" for index in range(9)]
    reviewer01_records = []
    reviewer02_records = []
    for index, record_id in enumerate(record_ids):
        if index < 5:
            reviewer01_label, reviewer02_label = "RISKY_TRANSITION", "UNCERTAIN"
        elif index < 8:
            reviewer01_label = reviewer02_label = "RISKY_TRANSITION"
        else:
            reviewer01_label = reviewer02_label = "UNCERTAIN"
        reviewer01_records.append(
            _review_record(record_id, REVIEWER01_ID, reviewer01_label, index)
        )
        reviewer02_records.append(
            _review_record(record_id, REVIEWER02_ID, reviewer02_label, index)
        )
    reviewer01 = {"raw_source_sha256": "R1", "records": reviewer01_records}
    reviewer02 = {"raw_source_sha256": "R2", "records": reviewer02_records}
    return reviewer01, reviewer02, build_agreement_analysis(reviewer01, reviewer02, [])


def _completed_stage_a(record_id: str) -> dict:
    label, confidence = EXPECTED_STAGE_A_JUDGMENTS[record_id]
    return {
        "review_id": derive_adjudication_review_id(
            DEFAULT_ADJUDICATOR_ID, record_id, STAGE_A
        ),
        "adjudicator_id": DEFAULT_ADJUDICATOR_ID,
        "record_id": record_id,
        "review_round": STAGE_A,
        "adjudicator_initial_label": label,
        "adjudicator_initial_confidence": confidence,
        "adjudicator_initial_rationale": f"Independent Stage A rationale for {record_id}.",
        "evidence_references": [
            "observed_signal.value=observed; observed_signal.value=confirmed"
        ],
        "blind_review": True,
        "review_status": "SUBMITTED",
        "review_timestamp": "2026-09-22T12:06:34Z",
        "review_timestamp_provenance": STAGE_A_TIMESTAMP_PROVENANCE,
    }


def _phase5e_fixture(tmp_path: Path):
    reviewer01, reviewer02, analysis = _review_bundles()
    phase5d = tmp_path / "phase5d"
    create_adjudicator_workspace(
        workspace=phase5d,
        disagreement_ids=EXPECTED_DISAGREEMENT_IDS,
        reviewer01_bundle=reviewer01,
        reviewer02_bundle=reviewer02,
        analysis=analysis,
    )
    raw_return = tmp_path / "stage_a_raw.zip"
    with zipfile.ZipFile(raw_return, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for record_id in EXPECTED_DISAGREEMENT_IDS:
            archive.writestr(
                f"submissions/{record_id}.json",
                json.dumps(_completed_stage_a(record_id)),
            )
    digest = sha256_file(raw_return)
    bundle = load_and_validate_stage_a_return(
        raw_return,
        adjudicator_workspace=phase5d,
        expected_sha256=digest,
    )
    return phase5d, raw_return, digest, bundle, reviewer01, reviewer02


def _gate(phase5d: Path, bundle: dict) -> dict:
    return evaluate_stage_b_release_gate(
        phase5d,
        submission_records={
            record["record_id"]: record["submission"] for record in bundle["records"]
        },
        source_submission_hashes={
            record["record_id"]: record["entry_sha256"] for record in bundle["records"]
        },
        expected_timestamp_provenance=STAGE_A_TIMESTAMP_PROVENANCE,
    )


def test_authoritative_stage_a_hash_validation_timestamp_and_packet_linkage(tmp_path):
    phase5d, raw_return, digest, bundle, _, _ = _phase5e_fixture(tmp_path)
    before = sha256_file(raw_return)

    assert bundle["raw_source_sha256"] == digest
    assert bundle["submission_count"] == 5
    assert bundle["unique_review_id_count"] == 5
    assert {record["record_id"] for record in bundle["records"]} == set(
        EXPECTED_DISAGREEMENT_IDS
    )
    assert {
        record["submission"]["review_timestamp_provenance"]
        for record in bundle["records"]
    } == {STAGE_A_TIMESTAMP_PROVENANCE}
    packet_manifest = json.loads(
        (phase5d / "metadata" / "stage_a_packet_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    expected_hashes = {row["record_id"]: row["sha256"] for row in packet_manifest["records"]}
    assert {record["record_id"]: record["packet_sha256"] for record in bundle["records"]} == expected_hashes
    assert sha256_file(raw_return) == before
    with pytest.raises(HumanReviewIntegrationError, match="SHA-256 mismatch"):
        load_and_validate_stage_a_return(
            raw_return,
            adjudicator_workspace=phase5d,
            expected_sha256="0" * 64,
        )


def test_stage_a_derived_layer_preserves_human_fields_and_timestamp_provenance(tmp_path):
    _, raw_return, _, bundle, _, _ = _phase5e_fixture(tmp_path)
    before = sha256_file(raw_return)
    output = tmp_path / "derived"

    report = write_stage_a_validation_layer(bundle, output)
    wrapper = json.loads(
        sorted((output / "validated_submissions").glob("*.json"))[0].read_text(
            encoding="utf-8"
        )
    )

    source = next(
        record for record in bundle["records"] if record["record_id"] == wrapper["original_submission"]["record_id"]
    )
    assert wrapper["original_submission"] == source["submission"]
    assert wrapper["timestamp_provenance"] == STAGE_A_TIMESTAMP_PROVENANCE
    assert report["packet_hash_linkage_passed"] is True
    assert report["project_labels_added"] is False
    assert sha256_file(raw_return) == before


def test_release_gate_accepts_five_valid_records_and_rejects_provenance_change(tmp_path):
    phase5d, _, _, bundle, _, _ = _phase5e_fixture(tmp_path)
    gate = _gate(phase5d, bundle)
    assert gate["status"] == "RELEASABLE"
    assert gate["required_submission_count"] == 5
    assert gate["valid_submission_count"] == 5
    assert gate["invalid_submission_count"] == 0
    assert gate["stage_a_source_hashes_preserved"] is True

    altered = json.loads(json.dumps(bundle))
    altered["records"][0]["submission"]["review_timestamp_provenance"] = "duration"
    blocked = _gate(phase5d, altered)
    assert blocked["status"] == "LOCKED"
    assert blocked["valid_submission_count"] == 4
    assert blocked["invalid_submission_count"] == 1


def test_stage_b_construction_has_no_manual_gate_bypass(tmp_path):
    phase5d, _, _, bundle, reviewer01, reviewer02 = _phase5e_fixture(tmp_path)
    with pytest.raises(HumanReviewAdjudicationError, match="RELEASABLE"):
        create_stage_b_release_workspace(
            output_root=tmp_path / "release",
            phase5d_workspace=phase5d,
            stage_a_bundle=bundle,
            gate={"status": "LOCKED"},
            reviewer01_bundle=reviewer01,
            reviewer02_bundle=reviewer02,
        )


def test_stage_b_package_is_five_case_deidentified_blank_and_hashed(tmp_path):
    phase5d, raw_return, _, bundle, reviewer01, reviewer02 = _phase5e_fixture(tmp_path)
    raw_before = sha256_file(raw_return)
    release = tmp_path / "release"
    gate = _gate(phase5d, bundle)
    create_stage_b_release_workspace(
        output_root=release,
        phase5d_workspace=phase5d,
        stage_a_bundle=bundle,
        gate=gate,
        reviewer01_bundle=reviewer01,
        reviewer02_bundle=reviewer02,
    )
    package = tmp_path / "stage_b.zip"
    checksum = tmp_path / "stage_b.sha256"

    audit = build_stage_b_package(
        release_workspace=release,
        output_zip=package,
        checksum_path=checksum,
    )

    assert audit["passed"] is True
    assert audit["case_count"] == 5
    assert audit["submission_count"] == 5
    assert all(audit["checks"].values())
    assert audit["package_sha256"] == sha256_file(package)
    assert checksum.read_text(encoding="ascii").startswith(audit["package_sha256"])
    assert audit_stage_b_package(package)["passed"] is True
    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()
        text = "\n".join(archive.read(name).decode("utf-8") for name in names)
        submissions = [
            json.loads(archive.read(name).decode("utf-8"))
            for name in names
            if name.startswith("submissions/")
        ]
    assert len([name for name in names if name.startswith("cases/")]) == 5
    assert len(submissions) == 5
    assert REVIEWER01_ID not in text and REVIEWER02_ID not in text
    assert "reviewer_alias_mapping" not in text
    assert "cohens_kappa" not in text
    assert {row["review_status"] for row in submissions} == {"PENDING"}
    assert {row["final_adjudicated_label"] for row in submissions} == {""}
    assert {row["initial_label_changed"] for row in submissions} == {None}
    assert all(row["stage_a_submission_sha256"] for row in submissions)
    assert sha256_file(raw_return) == raw_before
