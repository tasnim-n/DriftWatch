from __future__ import annotations

import copy
import json
import zipfile
from pathlib import Path

import pytest

from research.human_review_adjudication import (
    DEFAULT_ADJUDICATOR_ID,
    EXPECTED_DISAGREEMENT_IDS,
    STAGE_A,
    HumanReviewAdjudicationError,
    audit_stage_a_package,
    build_stage_a_package,
    create_adjudicator_workspace,
    derive_adjudication_review_id,
    evaluate_stage_b_release_gate,
    validate_disagreement_set,
)
from research.human_review_agreement import build_agreement_analysis
from research.human_review_integration import (
    INITIAL_BLIND,
    REVIEWER01_ID,
    REVIEWER02_ID,
    derive_review_id,
    sha256_bytes,
    sha256_file,
)


def _packet(record_id: str, value: int) -> tuple[dict, bytes]:
    packet = {
        "record_id": record_id,
        "blind_review": True,
        "observed_signal": {"value": value},
    }
    raw = b"\xef\xbb\xbf" + (json.dumps(packet, indent=2) + "\n").encode("utf-8")
    return packet, raw


def _record(record_id: str, reviewer_id: str, label: str, value: int) -> dict:
    packet, raw = _packet(record_id, value)
    submission = {
        "reviewer_id": reviewer_id,
        "record_id": record_id,
        "review_round": INITIAL_BLIND,
        "independent_label": label,
        "confidence": "MEDIUM",
        "rationale": (
            f"Verbatim first-review rationale for {record_id}."
            if reviewer_id == REVIEWER01_ID
            else f"Verbatim second-review rationale for {record_id}."
        ),
        "evidence_references": ["observed_signal.value"],
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


def _bundles() -> tuple[dict, dict, dict]:
    extra_ids = [f"agreed_{index:02d}" for index in range(9)]
    record_ids = list(EXPECTED_DISAGREEMENT_IDS) + extra_ids
    reviewer01_records = []
    reviewer02_records = []
    for index, record_id in enumerate(record_ids):
        if index < 5:
            reviewer01_label = "RISKY_TRANSITION"
            reviewer02_label = "UNCERTAIN"
        elif index < 8:
            reviewer01_label = reviewer02_label = "RISKY_TRANSITION"
        else:
            reviewer01_label = reviewer02_label = "UNCERTAIN"
        reviewer01_records.append(
            _record(record_id, REVIEWER01_ID, reviewer01_label, index)
        )
        reviewer02_records.append(
            _record(record_id, REVIEWER02_ID, reviewer02_label, index)
        )
    reviewer01 = {"raw_source_sha256": "R1", "records": reviewer01_records}
    reviewer02 = {"raw_source_sha256": "R2", "records": reviewer02_records}
    analysis = build_agreement_analysis(reviewer01, reviewer02, [])
    return reviewer01, reviewer02, analysis


def _disagreement_file(tmp_path: Path, ids=EXPECTED_DISAGREEMENT_IDS) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "disagreements.json"
    path.write_text(
        json.dumps(
            {
                "record_count": len(ids),
                "records": [{"record_id": record_id} for record_id in ids],
            }
        ),
        encoding="utf-8",
    )
    return path


def _workspace(tmp_path: Path):
    reviewer01, reviewer02, analysis = _bundles()
    workspace = tmp_path / "adjudicator"
    report = create_adjudicator_workspace(
        workspace=workspace,
        disagreement_ids=EXPECTED_DISAGREEMENT_IDS,
        reviewer01_bundle=reviewer01,
        reviewer02_bundle=reviewer02,
        analysis=analysis,
    )
    return workspace, reviewer01, reviewer02, analysis, report


def test_disagreement_set_is_exactly_the_governed_five(tmp_path):
    path = _disagreement_file(tmp_path)
    assert validate_disagreement_set(path) == sorted(EXPECTED_DISAGREEMENT_IDS)

    invalid = _disagreement_file(tmp_path / "invalid", EXPECTED_DISAGREEMENT_IDS[:-1])
    with pytest.raises(HumanReviewAdjudicationError, match="exactly five"):
        validate_disagreement_set(invalid)


def test_stage_a_contains_only_five_blind_packets_and_blank_unique_submissions(tmp_path):
    workspace, _, _, _, report = _workspace(tmp_path)
    packets = sorted((workspace / "STAGE_A" / "packets").glob("*.json"))
    submissions = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((workspace / "STAGE_A" / "submissions").glob("*.json"))
    ]

    assert report["stage_a_packet_count"] == 5
    assert report["stage_a_submission_count"] == 5
    assert {path.stem for path in packets} == set(EXPECTED_DISAGREEMENT_IDS)
    assert {row["record_id"] for row in submissions} == set(EXPECTED_DISAGREEMENT_IDS)
    assert len({row["review_id"] for row in submissions}) == 5
    assert {row["review_status"] for row in submissions} == {"PENDING"}
    assert {row["blind_review"] for row in submissions} == {True}
    assert {row["adjudicator_initial_label"] for row in submissions} == {""}
    assert {row["adjudicator_initial_confidence"] for row in submissions} == {""}
    assert {row["adjudicator_initial_rationale"] for row in submissions} == {""}
    assert all(row["evidence_references"] == [] for row in submissions)


def test_stage_b_is_locked_until_every_stage_a_submission_is_complete(tmp_path):
    workspace, _, _, _, report = _workspace(tmp_path)
    assert report["stage_b_status"] == "LOCKED"
    assert evaluate_stage_b_release_gate(workspace)["status"] == "LOCKED"

    first_path = sorted((workspace / "STAGE_A" / "submissions").glob("*.json"))[0]
    first = json.loads(first_path.read_text(encoding="utf-8"))
    first.update(
        {
            "adjudicator_initial_label": "UNCERTAIN",
            "adjudicator_initial_confidence": "MEDIUM",
            "adjudicator_initial_rationale": "The supplied evidence remains ambiguous.",
            "evidence_references": ["observed_signal.value"],
            "review_status": "SUBMITTED",
            "review_timestamp": "2026-09-22T12:00:00+06:00",
        }
    )
    first_path.write_text(json.dumps(first), encoding="utf-8")
    assert evaluate_stage_b_release_gate(workspace)["status"] == "LOCKED"


def test_all_five_valid_stage_a_submissions_make_stage_b_releasable(tmp_path):
    workspace, _, _, _, _ = _workspace(tmp_path)
    for path in (workspace / "STAGE_A" / "submissions").glob("*.json"):
        submission = json.loads(path.read_text(encoding="utf-8"))
        submission.update(
            {
                "adjudicator_initial_label": "UNCERTAIN",
                "adjudicator_initial_confidence": "MEDIUM",
                "adjudicator_initial_rationale": "The supplied evidence remains ambiguous.",
                "evidence_references": ["observed_signal.value"],
                "review_status": "SUBMITTED",
                "review_timestamp": "2026-09-22T12:00:00+06:00",
            }
        )
        path.write_text(json.dumps(submission), encoding="utf-8")

    gate = evaluate_stage_b_release_gate(workspace)
    assert gate["status"] == "RELEASABLE"
    assert gate["valid_submission_count"] == 5
    assert gate["stage_a_source_hashes_preserved"] is True
    assert len(gate["stage_a_submission_hashes"]) == 5
    assert gate["stage_b_released"] is False


def test_stage_b_opinions_are_deidentified_verbatim_and_sources_are_immutable(tmp_path):
    reviewer01, reviewer02, _ = _bundles()
    reviewer01_before = copy.deepcopy(reviewer01)
    reviewer02_before = copy.deepcopy(reviewer02)
    workspace = tmp_path / "adjudicator"
    analysis = build_agreement_analysis(reviewer01, reviewer02, [])
    create_adjudicator_workspace(
        workspace=workspace,
        disagreement_ids=EXPECTED_DISAGREEMENT_IDS,
        reviewer01_bundle=reviewer01,
        reviewer02_bundle=reviewer02,
        analysis=analysis,
    )

    opinion_path = sorted((workspace / "STAGE_B" / "reviewer_opinions").glob("*.json"))[0]
    opinion = json.loads(opinion_path.read_text(encoding="utf-8"))
    text = opinion_path.read_text(encoding="utf-8")
    assert set(opinion["opinions"]) == {"Reviewer A", "Reviewer B"}
    assert REVIEWER01_ID not in text
    assert REVIEWER02_ID not in text
    assert {row["label"] for row in opinion["opinions"].values()} == {
        "RISKY_TRANSITION",
        "UNCERTAIN",
    }
    private_mapping = (workspace / "metadata" / "reviewer_alias_mapping.json").read_text(
        encoding="utf-8"
    )
    assert REVIEWER01_ID in private_mapping and REVIEWER02_ID in private_mapping
    assert reviewer01 == reviewer01_before
    assert reviewer02 == reviewer02_before


def test_stage_a_zip_hash_and_blinding_audit_pass(tmp_path):
    workspace, reviewer01, reviewer02, _, _ = _workspace(tmp_path)
    package = tmp_path / "stage_a.zip"
    checksum = tmp_path / "stage_a.sha256"

    audit = build_stage_a_package(
        workspace=workspace,
        output_zip=package,
        checksum_path=checksum,
        expected_ids=EXPECTED_DISAGREEMENT_IDS,
        holdout_ids=["not_in_scope"],
        reviewer01_bundle=reviewer01,
        reviewer02_bundle=reviewer02,
    )

    assert audit["passed"] is True
    assert audit["packet_count"] == 5
    assert audit["submission_count"] == 5
    assert audit["external_holdout_overlap"] == []
    assert audit["package_sha256"] == sha256_file(package)
    assert checksum.read_text(encoding="ascii").startswith(audit["package_sha256"])
    assert all(audit["checks"].values())
    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()
        json_text = "\n".join(
            archive.read(name).decode("utf-8")
            for name in names
            if name.endswith(".json")
        )
    assert not any(name.startswith("STAGE_B") for name in names)
    assert REVIEWER01_ID not in json_text
    assert REVIEWER02_ID not in json_text
    assert "cohens_kappa" not in json_text
    assert "risk_score" not in json_text


def test_review_ids_are_deterministic_and_reviewer_aware():
    record_id = EXPECTED_DISAGREEMENT_IDS[0]
    review_id = derive_adjudication_review_id(
        DEFAULT_ADJUDICATOR_ID, record_id, STAGE_A
    )
    assert review_id == derive_adjudication_review_id(
        DEFAULT_ADJUDICATOR_ID, record_id, STAGE_A
    )
    assert review_id.startswith("ADV1::human_adjudicator_01::")
    with pytest.raises(HumanReviewAdjudicationError):
        derive_adjudication_review_id(DEFAULT_ADJUDICATOR_ID, record_id, "EXTRA_STAGE")
