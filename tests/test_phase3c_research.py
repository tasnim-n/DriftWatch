import csv
import json

from research.baselines import evaluate_rule_baseline
from research.ablation import feature_names_without_family
from research.chronological import chronological_evaluation_status, chronological_order
from research.experiment_config import ExperimentConfig
from research.evaluate import run_phase3c_pilot
from research.leakage import leakage_audit
from research.loaders import load_feature_rows
from research.metrics import binary_classification_metrics, binary_confusion_matrix
from research.readiness import dataset_readiness_report
from research.train_logistic import train_logistic_regression
from research.train_random_forest import train_random_forest


def _rows():
    return load_feature_rows("artifacts/driftbench/full_driftwatch.csv")


def _eligible_rows():
    rows = []
    for index in range(20):
        risky = index % 2 == 1
        split = "train" if index < 15 else "test"
        rows.append({
            "record_id": f"real-{index}",
            "provenance_id": f"prov-{index}",
            "extension_id": f"extension-{index}",
            "extension_name": f"Extension {index}",
            "old_version": "1.0.0",
            "new_version": "1.1.0",
            "old_timestamp": f"2026-01-{(index % 9) + 1:02d}T00:00:00+00:00",
            "new_timestamp": f"2026-02-{(index % 9) + 1:02d}T00:00:00+00:00",
            "label": "risky_transition" if risky else "benign_transition",
            "source": "local-fixture",
            "source_type": "real_extension",
            "controlled_mutation_type": "",
            "split": split,
            "signal_feature": "1.0" if risky else "0.0",
            "noise_feature": str(index % 3),
        })
    return rows


def test_binary_metric_correctness():
    y_true = [0, 0, 1, 1]
    y_pred = [0, 1, 1, 0]

    matrix = binary_confusion_matrix(y_true, y_pred)
    metrics = binary_classification_metrics(y_true, y_pred)

    assert matrix == {"tn": 1, "fp": 1, "fn": 1, "tp": 1}
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.5
    assert metrics["balanced_accuracy"] == 0.5
    assert metrics["false_positive_rate"] == 0.5
    assert metrics["false_negative_rate"] == 0.5
    assert metrics["false_alerts_per_100_benign"] == 50.0


def test_dataset_readiness_blocks_ml_for_current_controlled_artifacts():
    report = dataset_readiness_report(_rows())

    assert report["record_count"] == 2
    assert report["unique_extension_count"] == 2
    assert report["controlled_record_count"] == 2
    assert report["real_record_count"] == 0
    assert report["ml_training_permitted"] is False
    assert "fewer than 20 records" in report["ml_block_reasons"]
    assert "no train/test split assignments" in report["ml_block_reasons"]


def test_leakage_audit_passes_current_feature_columns():
    rows = _rows()
    feature_names = [key for key in rows[0] if key not in {"record_id", "provenance_id", "extension_id", "extension_name", "old_version", "new_version", "old_timestamp", "new_timestamp", "label", "source", "source_type", "controlled_mutation_type", "split"}]

    report = leakage_audit(rows, feature_names)

    assert report["passed"] is True
    assert report["violation_count"] == 0
    assert report["group_split_safe"] is True
    assert report["extension_overlap"] == {}


def test_leakage_audit_detects_target_derived_feature_names():
    report = leakage_audit(_rows(), ["final_risk_score", "safe_feature"])

    assert report["passed"] is False
    assert any(item["feature"] == "final_risk_score" for item in report["violations"])


def test_leakage_audit_detects_extension_group_split_overlap():
    rows = _eligible_rows()
    rows[1]["extension_id"] = rows[0]["extension_id"]
    rows[1]["split"] = "test"

    report = leakage_audit(rows, ["signal_feature"])

    assert report["passed"] is False
    assert report["group_split_safe"] is False
    assert rows[0]["extension_id"] in report["extension_overlap"]


def test_invalid_experiment_config_is_rejected():
    config = ExperimentConfig(
        experiment_id="bad",
        dataset_version="test",
        feature_set="unknown_feature_set",
    )

    try:
        config.validate()
    except ValueError as exc:
        assert "unknown feature_set" in str(exc)
    else:
        raise AssertionError("invalid feature set should be rejected")


def test_deterministic_baseline_evaluation_uses_actual_rows():
    rows = _rows()

    first = evaluate_rule_baseline("full_driftwatch", rows)
    second = evaluate_rule_baseline("full_driftwatch", rows)

    assert first == second
    assert first["record_count"] == 2
    assert first["metrics"]["confusion_matrix"] == {"tn": 1, "fp": 0, "fn": 0, "tp": 1}


def test_all_pilot_baselines_are_evaluable_on_controlled_artifacts():
    expected = {"permission_only", "manifest_permission", "latest_version_static", "simple_differential", "full_driftwatch"}
    for baseline in expected:
        rows = load_feature_rows(f"artifacts/driftbench/{baseline}.csv")
        result = evaluate_rule_baseline(baseline, rows)
        assert result["baseline"] == baseline
        assert set(result["metrics"]["confusion_matrix"]) == {"tn", "fp", "fn", "tp"}


def test_phase3c_pilot_artifacts_are_written(tmp_path):
    manifest = run_phase3c_pilot(output_dir=tmp_path, experiment_id="pytest_phase3c", dataset_version="test")

    assert manifest["status"] == "pilot_completed_ml_blocked"
    assert manifest["readiness_gate"]["ml_training_permitted"] is False
    assert manifest["leakage_audit"]["passed"] is True
    assert (tmp_path / "dataset_readiness.json").exists()
    assert (tmp_path / "leakage_audit.json").exists()
    assert (tmp_path / "baseline_comparison.csv").exists()
    assert (tmp_path / "confusion_matrices" / "full_driftwatch.json").exists()
    assert (tmp_path / "predictions" / "full_driftwatch.jsonl").exists()
    assert (tmp_path / "model_comparison.csv").exists()
    assert manifest["ml_models"]["logistic_regression"] == "not_run_dataset_readiness_gate_failed"
    assert manifest["ml_models"]["random_forest"] == "not_run_dataset_readiness_gate_failed"


def test_phase3c_artifact_manifest_is_reproducible_except_timestamp_and_duration(tmp_path):
    first = run_phase3c_pilot(output_dir=tmp_path / "first", experiment_id="pytest_phase3c", dataset_version="test")
    second = run_phase3c_pilot(output_dir=tmp_path / "second", experiment_id="pytest_phase3c", dataset_version="test")

    for payload in (first, second):
        payload.pop("timestamp", None)
        payload.pop("training_duration_seconds", None)

    assert first == second


def test_baseline_comparison_csv_contains_required_metrics(tmp_path):
    run_phase3c_pilot(output_dir=tmp_path)
    with open(tmp_path / "baseline_comparison.csv", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 5
    assert {
        "baseline",
        "precision",
        "recall",
        "f1",
        "balanced_accuracy",
        "false_positive_rate",
        "false_negative_rate",
    } <= set(rows[0])


def test_chronological_and_ablation_are_marked_not_run_for_small_dataset(tmp_path):
    run_phase3c_pilot(output_dir=tmp_path)
    with open(tmp_path / "chronological_results.csv", newline="", encoding="utf-8") as handle:
        chronological = next(csv.DictReader(handle))
    with open(tmp_path / "ablation_results.csv", newline="", encoding="utf-8") as handle:
        ablation = next(csv.DictReader(handle))

    assert chronological["status"] == "not_run_unavailable_timestamps_or_splits"
    assert ablation["status"] == "not_run_dataset_too_small"


def test_chronological_validation_blocks_current_controlled_artifacts():
    status = chronological_evaluation_status(_rows())

    assert status["status"] == "not_run_unavailable_timestamps_or_splits"


def test_chronological_order_uses_transition_timestamp():
    rows = _eligible_rows()[:3]
    rows[0]["new_timestamp"] = "2026-03-01T00:00:00+00:00"
    rows[1]["new_timestamp"] = "2026-01-01T00:00:00+00:00"
    rows[2]["new_timestamp"] = "2026-02-01T00:00:00+00:00"

    ordered = chronological_order(rows)

    assert [row["record_id"] for row in ordered] == ["real-1", "real-2", "real-0"]


def test_ablation_feature_removal_is_family_specific():
    features = [
        "added_sensitive_permission_count",
        "new_external_network_count",
        "source_sink_flow_count",
        "line_count_delta",
    ]

    remaining = feature_names_without_family(features, "network")

    assert "new_external_network_count" not in remaining
    assert "added_sensitive_permission_count" in remaining


def test_logistic_regression_blocks_current_controlled_artifacts():
    result = train_logistic_regression(_rows(), ["added_sensitive_permission_count"])

    assert result["status"] == "blocked_dataset_readiness_gate_failed"
    assert "fewer than 20 records" in result["ml_block_reasons"]


def test_logistic_regression_scaler_is_fit_on_train_only():
    rows = _eligible_rows()
    result = train_logistic_regression(rows, ["signal_feature", "noise_feature"], seed=7)

    assert result["status"] == "trained"
    scaler = result["model"].named_steps["scaler"]
    train_rows = [row for row in rows if row["split"] == "train"]
    expected_signal_mean = sum(float(row["signal_feature"]) for row in train_rows) / len(train_rows)
    assert round(float(scaler.mean_[0]), 6) == round(expected_signal_mean, 6)


def test_random_forest_training_is_deterministic_when_gate_passes():
    rows = _eligible_rows()
    first = train_random_forest(rows, ["signal_feature", "noise_feature"], seed=11)
    second = train_random_forest(rows, ["signal_feature", "noise_feature"], seed=11)

    assert first["status"] == "trained"
    assert first["metrics"] == second["metrics"]
    assert first["feature_importances"] == second["feature_importances"]
