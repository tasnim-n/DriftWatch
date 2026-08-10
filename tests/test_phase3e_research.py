import csv
import json
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
import pytest

from research.phase3e import (
    FEATURE_SETS,
    PHASE3E_SPLIT_ASSIGNMENTS,
    build_leakage_audit,
    build_matrix,
    build_target_definition,
    eligible_supervised_rows,
    extended_binary_metrics,
    run_phase3e_pilot,
)


@pytest.fixture(scope="module")
def phase3e_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("phase3e")
    return run_phase3e_pilot(
        experiment_dir=root / "experiments",
        model_dir=root / "models",
        experiment_id="phase3e_pytest_repro",
    )


def test_phase3e_freezes_dataset_identity(phase3e_run):
    snapshot = phase3e_run["dataset_snapshot"]
    assert snapshot["dataset_version"] == "driftbench-real-pilot-phase3e-v1"
    assert snapshot["feature_schema_version"] == "1.0"
    assert snapshot["schema_version"] == "phase3d-intake-v1"
    assert snapshot["total_records"] == 34
    assert snapshot["eligible_supervised_records"] == 32
    assert snapshot["ineligible_records"] == 2
    assert snapshot["unique_extension_identities"] == 11
    assert snapshot["real_record_count"] == 34
    assert snapshot["controlled_record_count"] == 0


def test_phase3e_target_mapping_excludes_uncertain(phase3e_run):
    target = phase3e_run["target_definition"]
    assert target["problem_type"] == "binary_classification"
    assert target["mapping"]["benign_transition"] == "BENIGN"
    assert target["mapping"]["risky_transition"] == "REVIEW_WORTHY"
    assert "uncertain" in target["excluded_labels"]

    eligibility = phase3e_run["eligibility_report"]
    assert eligibility["phase3e_supervised_ready"] is True
    assert eligibility["excluded_labels"] == {"uncertain": 2}


def test_phase3e_split_is_group_safe_and_trainable(phase3e_run):
    snapshot = phase3e_run["dataset_snapshot"]
    split_distribution = snapshot["split_distribution"]
    assert split_distribution["train"]["labels"] == {"benign_transition": 19, "risky_transition": 1}
    assert split_distribution["validation"]["labels"] == {"benign_transition": 5, "risky_transition": 1}
    assert split_distribution["test"]["labels"] == {"benign_transition": 5, "risky_transition": 1}

    experiment_dir = Path(phase3e_run["experiment_manifest"]["artifact_paths"]["experiment_dir"])
    group_audit = json.loads((experiment_dir / "group_split_audit.json").read_text(encoding="utf-8"))
    assert group_audit["passed"] is True
    assert group_audit["extension_overlap"] == {}
    assert group_audit["package_hash_overlap"] == {}


def test_phase3e_feature_metadata_separation_prevents_split_leakage():
    with open("artifacts/driftbench/real_pilot_features/full_driftwatch.csv", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    augmented = []
    for row in rows:
        row = dict(row)
        row["phase3e_split"] = PHASE3E_SPLIT_ASSIGNMENTS[row["extension_id"]]
        row["original_split"] = row["split"]
        row["split"] = row["phase3e_split"]
        augmented.append(row)
    eligible = eligible_supervised_rows(augmented)
    feature_names = [
        name for name in eligible[0]
        if name not in {
            "record_id", "provenance_id", "extension_id", "extension_name", "old_version",
            "new_version", "old_timestamp", "new_timestamp", "label", "label_source",
            "label_review_status", "label_quality_tier", "eligible_for_supervised_training",
            "source", "source_type", "is_controlled", "controlled_mutation_type",
            "functional_category", "split", "phase3e_split", "original_split",
        }
    ]
    matrix, target = build_matrix(eligible, feature_names)
    assert matrix.shape[0] == 32
    assert len(target) == 32
    assert "phase3e_split" not in feature_names
    assert "original_split" not in feature_names


def test_phase3e_leakage_audit_passes_real_features_and_fails_bad_feature():
    with open("artifacts/driftbench/real_pilot_features/full_driftwatch.csv", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert build_leakage_audit({"full_driftwatch": rows})["passed"] is True

    bad_rows = [dict(rows[0])]
    bad_rows[0]["label_text_proxy"] = "1"
    audit = build_leakage_audit({"bad": bad_rows})
    assert audit["passed"] is False
    assert audit["violations"][0]["name_hits"][0]["feature"] == "label_text_proxy"


def test_phase3e_metrics_include_fpr_fnr_specificity_and_false_alerts():
    metrics = extended_binary_metrics([0, 0, 1, 1], [0, 1, 0, 1], [0.1, 0.4, 0.2, 0.7])
    assert metrics["confusion_matrix"] == {"tn": 1, "fp": 1, "fn": 1, "tp": 1}
    assert metrics["specificity"] == 0.5
    assert metrics["false_positive_rate"] == 0.5
    assert metrics["false_negative_rate"] == 0.5
    assert metrics["false_alerts_per_100_benign"] == 50.0
    assert metrics["roc_auc"] == 0.75


def test_phase3e_evaluates_all_locked_feature_sets(phase3e_run):
    feature_sets = {result["feature_set"] for result in phase3e_run["model_results"]}
    assert feature_sets == set(FEATURE_SETS)
    assert Counter(result["model"] for result in phase3e_run["model_results"]) == {
        "logistic_regression": 5,
        "random_forest": 5,
    }


def test_phase3e_logistic_scaler_is_train_only_artifact(phase3e_run):
    result = next(
        item for item in phase3e_run["model_results"]
        if item["model"] == "logistic_regression" and item["feature_set"] == "full_driftwatch"
    )
    model = joblib.load(result["model_artifact"])
    scaler_mean = model.named_steps["scaler"].mean_

    with open("artifacts/driftbench/real_pilot_features/full_driftwatch.csv", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["phase3e_split"] = PHASE3E_SPLIT_ASSIGNMENTS[row["extension_id"]]
        row["split"] = row["phase3e_split"]
    eligible = eligible_supervised_rows(rows)
    feature_names = [
        name for name in eligible[0]
        if name not in {
            "record_id", "provenance_id", "extension_id", "extension_name", "old_version",
            "new_version", "old_timestamp", "new_timestamp", "label", "label_source",
            "label_review_status", "label_quality_tier", "eligible_for_supervised_training",
            "source", "source_type", "is_controlled", "controlled_mutation_type",
            "functional_category", "split", "phase3e_split",
        }
    ]
    train_rows = [row for row in eligible if row["phase3e_split"] == "train"]
    all_matrix, _ = build_matrix(eligible, feature_names)
    train_matrix, _ = build_matrix(train_rows, feature_names)

    assert np.allclose(scaler_mean, train_matrix.mean(axis=0))
    assert not np.allclose(scaler_mean, all_matrix.mean(axis=0))


def test_phase3e_rule_engine_and_ml_results_are_actual_counts(phase3e_run):
    rule = phase3e_run["rule_baseline"]
    assert rule["metrics"]["confusion_matrix"] == {"tn": 1, "fp": 4, "fn": 0, "tp": 1}
    assert rule["metrics"]["recall"] == 1.0
    assert rule["metrics"]["false_positive_rate"] == 0.8

    full_lr = next(
        item for item in phase3e_run["model_results"]
        if item["model"] == "logistic_regression" and item["feature_set"] == "full_driftwatch"
    )
    assert full_lr["test"]["metrics"]["confusion_matrix"] == {"tn": 5, "fp": 0, "fn": 1, "tp": 0}


def test_phase3e_ablation_and_sensitivity_are_documented(phase3e_run):
    ablation = phase3e_run["ablation_results"]
    assert len(ablation["rows"]) == 7
    assert {row["family_removed"] for row in ablation["rows"]} >= {"permission", "network", "source_sink"}

    chronological = phase3e_run["chronological_results"]
    assert chronological["status"] == "not_reliable_pilot_too_small"
    assert chronological["qualified_record_count"] == 32

    label_sensitivity = phase3e_run["label_sensitivity"]
    assert label_sensitivity["status"] == "not_run_high_confidence_subset_too_small"

    real_controlled = phase3e_run["real_controlled_analysis"]
    assert real_controlled["real_only"]["record_count"] == 32
    assert real_controlled["controlled_only"]["record_count"] == 0
