import csv
import json
from pathlib import Path

import pytest

from research.phase3h5 import validate_review_submission


PHASE3H = Path("artifacts/driftbench/phase3h")
PHASE3H5 = Path("artifacts/driftbench/phase3h5")
PHASE3H5_EXPERIMENTS = Path("artifacts/experiments/phase3h5")
PHASE3H_FEATURES = Path("artifacts/driftbench/phase3h_features")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_phase3h5_freezes_phase3h_reference_and_writes_separate_artifacts():
    reference = read_json(PHASE3H5 / "phase3h_reference.json")
    phase3h_manifest = PHASE3H / "dataset_manifest.json"

    assert reference["status"] == "FROZEN_PHASE3H_BASELINE"
    assert reference["dataset_version"] == "driftbench-real-adjudication-holdout-phase3h-v1"
    assert reference["dataset_manifest_hash"]
    assert phase3h_manifest.exists()
    assert "writes only phase3h5 outputs" in reference["preservation_policy"]


def test_phase3h5_review_scope_and_priority_counts_are_actual():
    summary = read_json(PHASE3H5 / "review_summary.json")

    assert summary["total_records_in_review_scope"] == 76
    assert summary["review_queue_records"] == 76
    assert summary["review_priority_records"] == 47
    assert summary["benign_review_candidates"] == 71
    assert summary["risky_review_candidates"] == 3
    assert summary["malicious_candidates"] == 0
    assert summary["uncertain_records"] == 2
    assert summary["external_holdout_candidates"] == 10


def test_phase3h5_review_packets_are_blind_and_hide_driftwatch_outputs():
    packet = read_json(PHASE3H5 / "review_packets" / "katex-github-chrome-extension_0_1_0_to_0_2_0.json")

    assert packet["blind_review"] is True
    assert packet["hidden_from_reviewer"]["driftwatch_numeric_output"] is True
    assert packet["hidden_from_reviewer"]["driftwatch_severity"] is True
    assert packet["hidden_from_reviewer"]["rule_recommendation"] is True
    assert packet["hidden_from_reviewer"]["ml_output"] is True
    assert packet["hidden_from_reviewer"]["current_dataset_label"] is True
    assert "current_dataset_label" not in packet
    assert "risk_score" not in json.dumps(packet).lower()
    assert "risk_classification" not in json.dumps(packet).lower()
    assert "final_severity" not in json.dumps(packet).lower()


def test_phase3h5_reviewer_schema_defines_labels_confidence_and_evidence_tiers():
    schema = read_json(PHASE3H5 / "reviewer_schema.json")

    assert schema["allowed_labels"] == [
        "BENIGN_TRANSITION",
        "RISKY_TRANSITION",
        "MALICIOUS_TRANSITION",
        "UNCERTAIN",
        "EXCLUDED",
    ]
    assert schema["allowed_confidence"] == ["HIGH", "MEDIUM", "LOW"]
    assert "TIER_1" in schema["evidence_hierarchy"]
    assert "TIER_6" in schema["evidence_hierarchy"]
    assert "DriftWatch final risk score" in schema["prohibited_ground_truth_sources"]


def test_phase3h5_no_fake_reviewer_and_second_review_queue_pending():
    summary = read_json(PHASE3H5 / "review_summary.json")
    queue = read_json(PHASE3H5 / "second_review_queue.json")
    inter_rater = read_json(PHASE3H5 / "inter_rater_agreement.json")

    assert summary["genuine_reviewer_a_count"] == 0
    assert summary["genuine_reviewer_b_count"] == 0
    assert summary["no_fake_reviewers_created"] is True
    assert queue["status"] == "SECOND_REVIEW_PENDING"
    assert queue["no_fake_second_reviewer"] is True
    assert inter_rater["status"] == "INTER_RATER_AGREEMENT_NOT_AVAILABLE"
    assert inter_rater["cohens_kappa"] is None


def test_phase3h5_rejects_ai_or_invalid_reviewer_submissions():
    valid = {
        "reviewer_id": "reviewer_a",
        "record_id": "example",
        "review_round": "INITIAL_BLIND",
        "independent_label": "UNCERTAIN",
        "confidence": "LOW",
        "rationale": "Evidence remains incomplete.",
    }
    assert validate_review_submission(valid)["reviewer_id"] == "reviewer_a"

    with pytest.raises(ValueError):
        validate_review_submission({**valid, "reviewer_id": "LLM"})
    with pytest.raises(ValueError):
        validate_review_submission({**valid, "independent_label": "MALWARE"})
    with pytest.raises(ValueError):
        validate_review_submission({**valid, "confidence": "0.99"})


def test_phase3h5_uncertain_records_are_preserved_and_not_forced():
    unresolved = read_json(PHASE3H5 / "unresolved_records.json")
    eligibility = read_json(PHASE3H5 / "eligibility_report.json")
    eligibility_by_id = {record["record_id"]: record for record in eligibility["records"]}

    assert unresolved["count"] == 2
    assert {record["review_outcome"] for record in unresolved["records"]} == {"UNCERTAIN"}
    for record in unresolved["records"]:
        assert record["eligible_for_supervised_training"] is False
        assert eligibility_by_id[record["record_id"]]["eligible_for_supervised_training"] is False


def test_phase3h5_malicious_labels_require_external_evidence_and_are_absent():
    integrity = read_json(PHASE3H5 / "research_integrity_audit.json")
    summary = read_json(PHASE3H5 / "review_summary.json")

    assert summary["malicious_candidates"] == 0
    assert integrity["confirmed_malicious_records_claimed"] is False
    assert integrity["driftwatch_outputs_used_as_ground_truth"] is False
    assert integrity["ai_output_used_as_ground_truth"] is False


def test_phase3h5_gold_set_is_empty_and_real_controlled_split_is_explicit():
    gold = read_json(PHASE3H5 / "gold_set_manifest.json")
    quality = read_json(PHASE3H5 / "gold_set_quality.json")

    assert gold["gold_record_count"] == 0
    assert gold["real_gold_count"] == 0
    assert gold["controlled_gold_count"] == 0
    assert gold["records"] == []
    assert gold["manifest_hash"]
    assert quality["real_gold_records"] == 0
    assert quality["controlled_gold_records"] == 0
    assert quality["model_metrics"] == "not_computed_phase3h5_ground_truth_only"


def test_phase3h5_external_holdout_is_isolated_from_feature_tuning():
    holdout = read_json(PHASE3H / "external_holdout_manifest.json")
    feature_rows = read_csv(PHASE3H_FEATURES / "full_driftwatch.csv")
    holdout_ids = {record["record_id"] for record in holdout["records"]}

    assert holdout["training_use_allowed"] is False
    assert holdout["tuning_use_allowed"] is False
    assert holdout_ids.isdisjoint({row["record_id"] for row in feature_rows})


def test_phase3h5_reviewer_metadata_leakage_audit_passes():
    audit = read_json(PHASE3H5 / "reviewer_metadata_leakage_audit.json")

    assert audit["passed"] is True
    assert audit["base_feature_leakage_passed"] is True
    assert audit["prohibited_column_hits"] == []
    assert audit["protected_pattern_hits"] == []
    assert "evidence_tier" in audit["blocked_metadata_fields"]


def test_phase3h5_adjudication_history_is_preserved_without_fabrication():
    adjudication = read_json(PHASE3H5 / "adjudication_report.json")

    assert adjudication["history_preserved"] is True
    assert adjudication["double_reviewed_count"] == 0
    assert adjudication["agreement_count"] == 0
    assert adjudication["disagreement_count"] == 0
    assert adjudication["adjudicated_count"] == 0
    assert adjudication["records"] == []


def test_phase3h5_readiness_gate_blocks_phase3i():
    readiness = read_json(PHASE3H5 / "readiness.json")

    assert readiness["phase3h5_complete"] is True
    assert readiness["phase3i_methodologically_ready"] is False
    assert readiness["final_decision"] == "MORE INDEPENDENT REVIEW REQUIRED"
    assert readiness["checks"]["defensible_real_gold_set_exists"] is False
    assert readiness["checks"]["external_holdout_ground_truth_sufficient"] is False
    assert readiness["checks"]["holdout_untouched_by_tuning"] is True
    assert readiness["checks"]["leakage_audit_clean"] is True


def test_phase3h5_artifact_serialization_and_comparison_outputs_exist():
    queue = read_json(PHASE3H5 / "review_queue.json")
    rows = read_csv(PHASE3H5_EXPERIMENTS / "phase3h_vs_phase3h5_ground_truth.csv")
    metrics = {row["metric"]: row for row in rows}

    assert len(queue["records"]) == 76
    assert Path("artifacts/driftbench/phase3h5/review_packets").exists()
    assert metrics["total_records"]["phase3h"] == "76"
    assert metrics["total_records"]["phase3h5"] == "76"
    assert metrics["real_gold_set_size"]["phase3h5"] == "0"
    assert metrics["phase3i_ready"]["phase3h5"] == "False"
