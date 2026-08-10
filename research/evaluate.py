from __future__ import annotations

import csv
import datetime as dt
import json
import time
from pathlib import Path
from typing import Dict, List

from research.baselines import BASELINE_RULES, evaluate_rule_baseline
from research.leakage import leakage_audit
from research.loaders import METADATA_COLUMNS, load_feature_rows, load_feature_schema
from research.readiness import dataset_readiness_report


def run_phase3c_pilot(
    *,
    feature_artifact_dir: str | Path = "artifacts/driftbench",
    output_dir: str | Path = "artifacts/experiments",
    experiment_id: str = "phase3c_pilot_controlled",
    dataset_version: str = "phase3b-controlled-v1",
    seed: int = 1337,
) -> Dict:
    start = time.perf_counter()
    artifact_dir = Path(feature_artifact_dir)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "confusion_matrices").mkdir(exist_ok=True)
    (output / "predictions").mkdir(exist_ok=True)

    schema = load_feature_schema(artifact_dir / "feature_schema.json")
    full_rows = load_feature_rows(artifact_dir / "full_driftwatch.csv")
    readiness = dataset_readiness_report(full_rows)
    feature_names = [name for name in full_rows[0].keys() if name not in METADATA_COLUMNS] if full_rows else []
    leakage = leakage_audit(full_rows, feature_names)

    readiness_path = output / "dataset_readiness.json"
    leakage_path = output / "leakage_audit.json"
    readiness_path.write_text(json.dumps(readiness, indent=2, sort_keys=True), encoding="utf-8")
    leakage_path.write_text(json.dumps(leakage, indent=2, sort_keys=True), encoding="utf-8")

    if not leakage["passed"]:
        manifest = _manifest(
            experiment_id=experiment_id,
            dataset_version=dataset_version,
            schema=schema,
            seed=seed,
            status="blocked_leakage",
            readiness=readiness,
            leakage=leakage,
            duration=time.perf_counter() - start,
        )
        manifest_path = output / "experiment_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return manifest

    baseline_results = []
    for baseline in BASELINE_RULES:
        rows = load_feature_rows(artifact_dir / f"{baseline}.csv")
        result = evaluate_rule_baseline(baseline, rows)
        baseline_results.append(result)
        _write_json(output / "confusion_matrices" / f"{baseline}.json", result["metrics"]["confusion_matrix"])
        _write_jsonl(output / "predictions" / f"{baseline}.jsonl", result["predictions"])

    _write_baseline_comparison(output / "baseline_comparison.csv", baseline_results)
    _write_json(output / "error_analysis.json", _error_analysis(baseline_results))
    _write_ablation_placeholder(output / "ablation_results.csv", readiness)
    _write_chronological_placeholder(output / "chronological_results.csv", readiness)
    _write_model_comparison_placeholder(output / "model_comparison.csv", readiness)

    manifest = _manifest(
        experiment_id=experiment_id,
        dataset_version=dataset_version,
        schema=schema,
        seed=seed,
        status="pilot_completed_ml_blocked" if not readiness["ml_training_permitted"] else "pilot_completed_ml_ready",
        readiness=readiness,
        leakage=leakage,
        duration=time.perf_counter() - start,
    )
    manifest["baseline_results"] = [
        {"baseline": item["baseline"], **item["metrics"]}
        for item in baseline_results
    ]
    manifest["ml_models"] = {
        "logistic_regression": "not_run_dataset_readiness_gate_failed" if not readiness["ml_training_permitted"] else "not_run_in_pilot_function",
        "random_forest": "not_run_dataset_readiness_gate_failed" if not readiness["ml_training_permitted"] else "not_run_in_pilot_function",
    }
    (output / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def _manifest(experiment_id: str, dataset_version: str, schema: Dict, seed: int, status: str, readiness: Dict, leakage: Dict, duration: float) -> Dict:
    return {
        "experiment_id": experiment_id,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "dataset_version": dataset_version,
        "feature_schema_version": schema.get("driftbench_feature_schema_version"),
        "split_strategy": "preserved_phase3b_assignments",
        "seed": seed,
        "status": status,
        "training_duration_seconds": round(duration, 6),
        "code_version": None,
        "readiness_gate": readiness,
        "leakage_audit": leakage,
        "note": "Current artifacts are controlled pilot records only; metrics are not generalizable.",
    }


def _write_json(path: Path, payload: Dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: List[Dict]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _write_baseline_comparison(path: Path, results: List[Dict]) -> None:
    fields = ["baseline", "record_count", "precision", "recall", "f1", "balanced_accuracy", "false_positive_rate", "false_negative_rate", "false_alerts_per_100_benign"]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in results:
            metrics = result["metrics"]
            writer.writerow({
                "baseline": result["baseline"],
                "record_count": result["record_count"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "balanced_accuracy": metrics["balanced_accuracy"],
                "false_positive_rate": metrics["false_positive_rate"],
                "false_negative_rate": metrics["false_negative_rate"],
                "false_alerts_per_100_benign": metrics["false_alerts_per_100_benign"],
            })


def _error_analysis(results: List[Dict]) -> Dict:
    by_baseline = {}
    for result in results:
        errors = [
            prediction for prediction in result["predictions"]
            if prediction["true_binary"] != prediction["predicted_binary"]
        ]
        by_baseline[result["baseline"]] = {
            "error_count": len(errors),
            "errors": errors,
            "recurring_failure_modes": [] if not errors else ["See per-record errors; dataset too small for recurring-pattern claims."],
        }
    return {
        "scope": "pilot_controlled_records",
        "by_baseline": by_baseline,
    }


def _write_ablation_placeholder(path: Path, readiness: Dict) -> None:
    _write_placeholder_csv(path, "ablation", "not_run_dataset_too_small", "; ".join(readiness["ml_block_reasons"]))


def _write_chronological_placeholder(path: Path, readiness: Dict) -> None:
    _write_placeholder_csv(path, "chronological", "not_run_unavailable_timestamps_or_splits", "; ".join(readiness["ml_block_reasons"]))


def _write_model_comparison_placeholder(path: Path, readiness: Dict) -> None:
    _write_placeholder_csv(path, "model", "not_run_dataset_readiness_gate_failed", "; ".join(readiness["ml_block_reasons"]))


def _write_placeholder_csv(path: Path, first_column: str, status: str, reason: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[first_column, "status", "reason"])
        writer.writeheader()
        writer.writerow({first_column: "all", "status": status, "reason": reason})
