import csv
import json
from pathlib import Path


PHASE3F = Path("artifacts/experiments/phase3f")
PHASE3F_DRIFTBENCH = Path("artifacts/driftbench/phase3f")
PHASE3F_FEATURES = Path("artifacts/driftbench/phase3f_features")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_phase3f_preserves_phase3e_pilot_baseline_reference():
    snapshot = read_json(PHASE3F / "dataset_snapshot.json")
    baseline = snapshot["phase3e_pilot_baseline"]
    assert baseline["status"] == "PILOT_BASELINE"
    assert baseline["dataset_version"] == "driftbench-real-pilot-phase3e-v1"
    assert baseline["experiment_id"] == "phase3e_real_pilot_v1"
    assert baseline["dataset_snapshot_hash"]
    assert baseline["rule_baseline_hash"]


def test_phase3f_dataset_version_and_replication_counts():
    snapshot = read_json(PHASE3F / "dataset_snapshot.json")
    assert snapshot["dataset_version"] == "driftbench-real-replication-phase3f-v1"
    assert snapshot["record_count"] == 46
    assert snapshot["real_record_count"] == 46
    assert snapshot["controlled_record_count"] == 0
    assert snapshot["new_replication_record_count"] == 12
    assert snapshot["unique_extension_identities"] == 14
    assert snapshot["label_distribution"] == {
        "benign_transition": 41,
        "risky_transition": 3,
        "uncertain": 2,
    }


def test_phase3f_replication_records_are_marked_and_provenance_complete():
    provenance = read_json(PHASE3F_DRIFTBENCH / "provenance_manifest.json")
    assert provenance["provenance_complete_count"] == 46
    replication_records = [
        record for record in provenance["records"]
        if record["is_replication_record"]
    ]
    assert len(replication_records) == 12
    assert {record["extension_id"] for record in replication_records} == {
        "github:browserpass/browserpass-extension",
        "github:darkreader/darkreader",
        "github:openstyles/stylus",
    }


def test_phase3f_group_and_duplicate_audits_pass():
    group_audit = read_json(PHASE3F / "group_split_audit.json")
    duplicate_audit = read_json(PHASE3F_DRIFTBENCH / "duplicate_report.json")
    assert group_audit["passed"] is True
    assert group_audit["extension_overlap"] == {}
    assert group_audit["package_hash_overlap"] == {}
    assert duplicate_audit["passed"] is True
    assert duplicate_audit["duplicate_record_ids"] == []
    assert duplicate_audit["duplicate_pairs"] == []
    assert duplicate_audit["duplicate_package_hashes"] == {}


def test_phase3f_leakage_audit_passes_and_feature_schema_matches_phase3e():
    leakage = read_json(PHASE3F / "leakage_audit.json")
    assert leakage["passed"] is True
    assert leakage["violations"] == []

    phase3e_schema = read_json(Path("artifacts/driftbench/real_pilot_features/feature_schema.json"))
    phase3f_schema = read_json(PHASE3F_FEATURES / "feature_schema.json")
    assert phase3f_schema["driftbench_feature_schema_version"] == phase3e_schema["driftbench_feature_schema_version"]
    assert [f["name"] for f in phase3f_schema["features"]] == [
        f["name"] for f in phase3e_schema["features"]
    ]


def test_phase3f_split_counts_and_temporal_status():
    snapshot = read_json(PHASE3F / "dataset_snapshot.json")
    assert snapshot["split_distribution"] == {
        "train": 24,
        "validation": 12,
        "test": 10,
    }
    chronological = read_json(PHASE3F / "chronological_results.json")
    assert chronological["status"] == "not_reliable_class_support_too_small"
    assert chronological["qualified_record_count"] == 44


def test_phase3f_rule_engine_and_ml_replication_results_are_actual():
    rule = read_json(PHASE3F / "rule_results.json")
    assert rule["metrics"]["confusion_matrix"] == {"tn": 1, "fp": 8, "fn": 0, "tp": 1}
    assert rule["metrics"]["f1"] == 0.2
    assert rule["metrics"]["false_positive_rate"] == 0.888889

    rows = read_csv(PHASE3F / "feature_set_comparison.csv")
    full_lr = next(row for row in rows if row["model"] == "logistic_regression" and row["feature_set"] == "full_driftwatch")
    full_rf = next(row for row in rows if row["model"] == "random_forest" and row["feature_set"] == "full_driftwatch")
    assert full_lr["confusion_matrix"] == '{"fn": 1, "fp": 0, "tn": 9, "tp": 0}'
    assert full_rf["confusion_matrix"] == '{"fn": 1, "fp": 0, "tn": 9, "tp": 0}'


def test_phase3f_comparison_and_decision_gate_are_honest():
    comparison = read_csv(PHASE3F / "phase3e_vs_phase3f.csv")
    rule = next(row for row in comparison if row["model"] == "rule_engine")
    assert rule["phase3e_f1"] == "0.333333"
    assert rule["phase3f_f1"] == "0.2"
    assert rule["phase3f_fpr"] == "0.888889"

    conclusion = read_json(PHASE3F / "replication_conclusion.json")
    assert conclusion["conclusion"] == "INCONCLUSIVE"
    assert conclusion["ml_integration_justified"] is False
    assert conclusion["recommended_decision_gate"] == "CONTINUE DATASET EXPANSION"


def test_phase3f_label_quality_and_inter_rater_limits_are_documented():
    label_quality = read_json(PHASE3F / "label_quality_report.json")
    inter_rater = read_json(PHASE3F_DRIFTBENCH / "inter_rater_agreement.json")
    assert label_quality["label_quality_distribution"] == {
        "SINGLE_REVIEWER_PROVISIONAL": 44,
        "UNCERTAIN": 2,
    }
    assert label_quality["uncertain_training_eligible_count"] == 0
    assert inter_rater["status"] == "INTER-RATER AGREEMENT NOT AVAILABLE"
    assert inter_rater["double_reviewed_count"] == 0
