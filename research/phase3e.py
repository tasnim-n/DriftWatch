from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from research.ablation import feature_names_without_family
from research.baselines import BASELINE_RULES
from research.loaders import METADATA_COLUMNS, label_to_binary, load_feature_rows, split_metadata_features
from research.metrics import binary_classification_metrics, binary_confusion_matrix
from risk_engine.scoring import RiskScorer


FEATURE_SETS = [
    "permission_only",
    "manifest_permission",
    "latest_version_static",
    "simple_differential",
    "full_driftwatch",
]

PHASE3E_SPLIT_VERSION = "phase3e-group-safe-label-aware-v1"
PHASE3E_SPLIT_ASSIGNMENTS = {
    "github:kevinsqi/save_tabbed_images": "train",
    "github:duckduckgo/duckduckgo-privacy-extension": "train",
    "github:keepassxreboot/keepassxc-browser": "train",
    "github:refined-github/refined-github": "train",
    "github:violentmonkey/violentmonkey": "train",
    "github:alpha1337/save-sora": "validation",
    "github:alyssaxuu/screenity": "validation",
    "github:ajayyy/sponsorblock": "validation",
    "github:aaroncql/katex-github-chrome-extension": "test",
    "github:yniijia/subtidex": "test",
    "github:gorhill/ublock": "test",
}

TARGET_MAPPING = {
    "benign_transition": "BENIGN",
    "risky_transition": "REVIEW_WORTHY",
    "controlled_malicious_transition": "REVIEW_WORTHY",
}

PROTECTED_LEAKAGE_TERMS = (
    "label",
    "rationale",
    "reviewer",
    "review_",
    "confidence",
    "eligible",
    "split",
    "target",
    "ground_truth",
    "risk_score",
    "risk_classification",
    "recommendation",
    "severity",
    "mutation_label",
    "controlled_folder_class",
    "filename",
    "file_path",
    "path_",
    "benign",
    "risky",
    "malicious",
    "conclusion",
)


def run_phase3e_pilot(
    feature_dir: str | Path = "artifacts/driftbench/real_pilot_features",
    curation_dir: str | Path = "artifacts/driftbench/real_pilot",
    readiness_path: str | Path = "artifacts/driftbench/real_pilot_readiness.json",
    experiment_dir: str | Path = "artifacts/experiments/phase3e",
    model_dir: str | Path = "artifacts/models/phase3e",
    experiment_id: str = "phase3e_real_pilot_v1",
    seed: int = 1337,
) -> Dict[str, Any]:
    start = time.perf_counter()
    feature_dir = Path(feature_dir)
    curation_dir = Path(curation_dir)
    readiness_path = Path(readiness_path)
    experiment_root = Path(experiment_dir)
    model_root = Path(model_dir) / experiment_id
    predictions_dir = experiment_root / "predictions"
    matrices_dir = experiment_root / "confusion_matrices"
    for path in (experiment_root, model_root, predictions_dir, matrices_dir):
        path.mkdir(parents=True, exist_ok=True)

    loaded_at = datetime.now(timezone.utc).isoformat()
    feature_rows = {name: load_feature_rows(feature_dir / f"{name}.csv") for name in FEATURE_SETS}
    canonical_rows = feature_rows["full_driftwatch"]
    rows_with_split = [_apply_phase3e_split(row) for row in canonical_rows]
    eligibility = build_eligibility_report(rows_with_split)
    if not eligibility["phase3e_supervised_ready"]:
        raise ValueError(f"Phase 3E supervised readiness failed: {eligibility['block_reasons']}")

    dataset_snapshot = build_dataset_snapshot(
        rows_with_split,
        feature_dir,
        curation_dir,
        readiness_path,
        experiment_id,
        loaded_at,
    )
    target_definition = build_target_definition(rows_with_split)
    leakage_audit = build_leakage_audit(feature_rows)
    if not leakage_audit["passed"]:
        raise ValueError(f"protected feature leakage detected: {leakage_audit['violations']}")
    group_audit = build_group_split_audit(rows_with_split, curation_dir / "provenance_manifest.json")
    if not group_audit["passed"]:
        raise ValueError(f"group split audit failed: {group_audit['violations']}")

    split_manifest = {
        "split_version": PHASE3E_SPLIT_VERSION,
        "protocol": "label-aware extension-group-safe pilot split",
        "reason": (
            "The preserved Phase 3D.6 split contained no REVIEW_WORTHY records in train. "
            "Phase 3E freezes this separate experiment split before model fitting so train, "
            "validation, and test each contain both target classes while preserving extension identity isolation."
        ),
        "assignments": PHASE3E_SPLIT_ASSIGNMENTS,
        "record_splits": {
            row["record_id"]: row["phase3e_split"]
            for row in rows_with_split
        },
    }

    all_results: List[Dict[str, Any]] = []
    comparison_rows: List[Dict[str, Any]] = []
    confidence_intervals: Dict[str, Any] = {}
    model_comparison: List[Dict[str, Any]] = []
    feature_importance_summary: Dict[str, Any] = {}
    training_started = time.perf_counter()

    for feature_set in FEATURE_SETS:
        rows = [_apply_phase3e_split(row) for row in feature_rows[feature_set]]
        eligible_rows = eligible_supervised_rows(rows)
        feature_names = get_feature_names(eligible_rows)
        for model_name in ("logistic_regression", "random_forest"):
            result = train_validate_test_model(
                model_name,
                feature_set,
                eligible_rows,
                feature_names,
                model_root,
                experiment_id,
                seed,
            )
            all_results.append(result)
            comparison_rows.append(flatten_result_for_csv(result))
            model_comparison.append(flatten_model_comparison(result))
            confidence_intervals[f"{model_name}:{feature_set}"] = bootstrap_confidence_intervals(
                result["test"]["y_true"],
                result["test"]["y_pred"],
                seed=seed,
            )
            feature_importance_summary[f"{model_name}:{feature_set}"] = result["interpretability"]
            write_jsonl(predictions_dir / f"{model_name}_{feature_set}.jsonl", result["test"]["predictions"])
            write_json(matrices_dir / f"{model_name}_{feature_set}.json", result["test"]["metrics"]["confusion_matrix"])

    rule_baseline = evaluate_current_rule_engine(rows_with_split)
    write_jsonl(predictions_dir / "rule_engine_full_driftwatch.jsonl", rule_baseline["predictions"])
    write_json(matrices_dir / "rule_engine_full_driftwatch.json", rule_baseline["metrics"]["confusion_matrix"])

    full_lr = next(
        item for item in all_results
        if item["model"] == "logistic_regression" and item["feature_set"] == "full_driftwatch"
    )
    ablation_results = run_ablation_study(
        [_apply_phase3e_split(row) for row in feature_rows["full_driftwatch"]],
        full_lr,
        model_root,
        experiment_id,
        seed,
    )
    chronological_results = build_chronological_analysis(rows_with_split)
    label_sensitivity = build_label_sensitivity(rows_with_split)
    real_controlled = build_real_controlled_analysis(rows_with_split)
    error_analysis = build_error_analysis(rule_baseline, all_results, rows_with_split)
    false_positive = build_false_alert_analysis(error_analysis)
    false_negative = build_false_negative_analysis(error_analysis)

    experiment_manifest = {
        "experiment_id": experiment_id,
        "phase": "Phase 3E",
        "created_at": loaded_at,
        "dataset_version": dataset_snapshot["dataset_version"],
        "feature_schema_version": dataset_snapshot["feature_schema_version"],
        "target_version": target_definition["target_version"],
        "split_version": PHASE3E_SPLIT_VERSION,
        "seed": seed,
        "python_version": sys.version,
        "platform": platform.platform(),
        "scikit_learn_version": sklearn.__version__,
        "git_commit": get_git_commit(),
        "feature_loading_seconds": round(training_started - start, 4),
        "total_runtime_seconds": round(time.perf_counter() - start, 4),
        "artifact_paths": {
            "experiment_dir": str(experiment_root),
            "model_dir": str(model_root),
            "predictions_dir": str(predictions_dir),
            "confusion_matrices_dir": str(matrices_dir),
        },
        "quality_gate": {
            "dataset_frozen": True,
            "training_eligibility_enforced": True,
            "uncertain_excluded_from_supervised_training": True,
            "leakage_audit_passed": leakage_audit["passed"],
            "group_split_audit_passed": group_audit["passed"],
            "production_ml_integration": False,
            "pilot_preliminary_only": True,
        },
    }

    write_json(experiment_root / "dataset_snapshot.json", dataset_snapshot)
    write_json(experiment_root / "eligibility_report.json", eligibility)
    write_json(experiment_root / "target_definition.json", target_definition)
    write_json(experiment_root / "leakage_audit.json", leakage_audit)
    write_json(experiment_root / "group_split_audit.json", group_audit)
    write_json(experiment_root / "split_manifest.json", split_manifest)
    write_json(experiment_root / "rule_baseline.json", rule_baseline)
    write_csv(experiment_root / "logistic_results.csv", [r for r in comparison_rows if r["model"] == "logistic_regression"])
    write_csv(experiment_root / "random_forest_results.csv", [r for r in comparison_rows if r["model"] == "random_forest"])
    write_csv(experiment_root / "feature_set_comparison.csv", comparison_rows)
    write_csv(experiment_root / "model_comparison.csv", model_comparison + [flatten_rule_comparison(rule_baseline)])
    write_csv(experiment_root / "ablation_results.csv", ablation_results["rows"])
    write_json(experiment_root / "chronological_results.json", chronological_results)
    write_json(experiment_root / "label_sensitivity.json", label_sensitivity)
    write_json(experiment_root / "real_controlled_analysis.json", real_controlled)
    write_json(experiment_root / "confidence_intervals.json", confidence_intervals)
    write_json(experiment_root / "error_analysis.json", error_analysis)
    write_json(experiment_root / "false_positive_analysis.json", false_positive)
    write_json(experiment_root / "false_negative_analysis.json", false_negative)
    write_json(experiment_root / "feature_interpretability.json", feature_importance_summary)
    write_json(experiment_root / "experiment_manifest.json", experiment_manifest)

    return {
        "experiment_manifest": experiment_manifest,
        "dataset_snapshot": dataset_snapshot,
        "eligibility_report": eligibility,
        "target_definition": target_definition,
        "rule_baseline": rule_baseline,
        "model_results": all_results,
        "ablation_results": ablation_results,
        "chronological_results": chronological_results,
        "label_sensitivity": label_sensitivity,
        "real_controlled_analysis": real_controlled,
    }


def _apply_phase3e_split(row: Dict[str, str]) -> Dict[str, str]:
    updated = dict(row)
    phase3e_split = PHASE3E_SPLIT_ASSIGNMENTS.get(updated["extension_id"])
    if phase3e_split is None:
        raise ValueError(f"missing Phase 3E split assignment for {updated['extension_id']}")
    updated["original_split"] = updated.get("split", "")
    updated["phase3e_split"] = phase3e_split
    updated["split"] = phase3e_split
    return updated


def eligible_supervised_rows(rows: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    return [
        row for row in rows
        if str(row.get("eligible_for_supervised_training")).lower() == "true"
        and row.get("label") in TARGET_MAPPING
    ]


def build_eligibility_report(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    eligible = eligible_supervised_rows(rows)
    ineligible = [row for row in rows if row not in eligible]
    split_labels = {
        split: dict(Counter(row["label"] for row in eligible if row["phase3e_split"] == split))
        for split in ("train", "validation", "test")
    }
    block_reasons = []
    for split in ("train", "validation", "test"):
        labels = set(split_labels[split])
        if {"benign_transition", "risky_transition"} - labels:
            block_reasons.append(f"{split} split lacks both binary target classes: {split_labels[split]}")
    if len(eligible) < 20:
        block_reasons.append("fewer than 20 eligible supervised records")
    if len({row["extension_id"] for row in eligible}) < 6:
        block_reasons.append("fewer than 6 eligible extension groups")
    return {
        "total_records": len(rows),
        "eligible_supervised_records": len(eligible),
        "ineligible_records": len(ineligible),
        "excluded_record_ids": [row["record_id"] for row in ineligible],
        "excluded_labels": dict(Counter(row["label"] for row in ineligible)),
        "split_label_distribution": split_labels,
        "phase3e_supervised_ready": not block_reasons,
        "block_reasons": block_reasons,
    }


def build_dataset_snapshot(
    rows: List[Dict[str, str]],
    feature_dir: Path,
    curation_dir: Path,
    readiness_path: Path,
    experiment_id: str,
    created_at: str,
) -> Dict[str, Any]:
    eligible = eligible_supervised_rows(rows)
    label_distribution = dict(Counter(row["label"] for row in rows))
    split_distribution = {
        split: {
            "records": sum(1 for row in rows if row["phase3e_split"] == split),
            "eligible": sum(1 for row in eligible if row["phase3e_split"] == split),
            "labels": dict(Counter(row["label"] for row in eligible if row["phase3e_split"] == split)),
            "extensions": sorted({row["extension_id"] for row in rows if row["phase3e_split"] == split}),
        }
        for split in ("train", "validation", "test")
    }
    feature_schema = read_json(feature_dir / "feature_schema.json")
    dataset_manifest = read_json(curation_dir / "dataset_manifest.json")
    readiness = read_json(readiness_path) if readiness_path.exists() else {}
    return {
        "dataset_version": "driftbench-real-pilot-phase3e-v1",
        "experiment_id": experiment_id,
        "created_at": created_at,
        "source_dataset_version": dataset_manifest.get("dataset_version", "real_pilot"),
        "schema_version": dataset_manifest.get("schema_version", "phase3d-intake-v1"),
        "feature_schema_version": feature_schema.get("feature_schema_version", "1.0"),
        "label_ontology_version": "phase3d-labels-v1",
        "split_version": PHASE3E_SPLIT_VERSION,
        "dataset_manifest_hash": sha256_file(curation_dir / "dataset_manifest.json"),
        "provenance_manifest_hash": sha256_file(curation_dir / "provenance_manifest.json"),
        "feature_artifact_hashes": {
            feature_set: sha256_file(feature_dir / f"{feature_set}.csv")
            for feature_set in FEATURE_SETS
        },
        "total_records": len(rows),
        "eligible_supervised_records": len(eligible),
        "ineligible_records": len(rows) - len(eligible),
        "unique_extension_identities": len({row["extension_id"] for row in rows}),
        "real_record_count": sum(1 for row in rows if row.get("is_controlled") != "True"),
        "controlled_record_count": sum(1 for row in rows if row.get("is_controlled") == "True"),
        "label_distribution": label_distribution,
        "eligible_label_distribution": dict(Counter(row["label"] for row in eligible)),
        "split_distribution": split_distribution,
        "extension_ids_per_split": {
            split: split_distribution[split]["extensions"]
            for split in ("train", "validation", "test")
        },
        "unresolved_uncertain_records": [
            row["record_id"] for row in rows if row["label"] == "uncertain"
        ],
        "phase3d6_readiness_reference": {
            "phase3e_ml_re_evaluation_ready": readiness.get("phase3e_ml_re_evaluation_ready"),
            "phase3e_block_reasons": readiness.get("phase3e_block_reasons"),
            "warnings": readiness.get("warnings"),
        },
    }


def build_target_definition(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    source_labels = dict(Counter(row["label"] for row in rows))
    return {
        "target_version": "phase3e-binary-review-worthy-v1",
        "problem_type": "binary_classification",
        "source_labels": source_labels,
        "target_labels": {"BENIGN": 0, "REVIEW_WORTHY": 1},
        "mapping": TARGET_MAPPING,
        "excluded_labels": {
            "uncertain": "excluded from supervised fitting/evaluation; retained in dataset audit"
        },
        "justification": (
            "The pilot corpus contains 29 benign, 3 risky, and 2 uncertain records. "
            "This is insufficient for defensible multiclass classification, so Phase 3E "
            "uses a binary security-review target while preserving original labels."
        ),
        "limitations": [
            "REVIEW_WORTHY is a research target, not confirmed malicious intent.",
            "All eligible labels remain pilot labels and most are single-reviewer provisional.",
            "UNCERTAIN records are not deleted and require future adjudication.",
        ],
    }


def build_leakage_audit(feature_rows: Dict[str, List[Dict[str, str]]]) -> Dict[str, Any]:
    per_feature_set = {}
    violations = []
    for feature_set, rows in feature_rows.items():
        feature_names = get_feature_names(rows)
        name_hits = [
            {"feature": name, "term": term}
            for name in feature_names
            for term in PROTECTED_LEAKAGE_TERMS
            if term in name.lower()
        ]
        non_numeric = []
        for row in rows:
            _, features = split_metadata_features(row)
            for name in feature_names:
                if name not in features:
                    non_numeric.append({"record_id": row.get("record_id"), "feature": name})
        if name_hits or non_numeric:
            violations.append({
                "feature_set": feature_set,
                "name_hits": name_hits,
                "non_numeric_feature_values": non_numeric[:20],
            })
        per_feature_set[feature_set] = {
            "feature_count": len(feature_names),
            "metadata_columns_excluded": sorted(METADATA_COLUMNS | {"phase3e_split", "original_split"}),
            "protected_term_hits": name_hits,
            "non_numeric_feature_values": non_numeric[:20],
        }
    return {
        "passed": not violations,
        "audit_scope": "feature matrices only; metadata remains attached only to predictions and audit records",
        "protected_terms": PROTECTED_LEAKAGE_TERMS,
        "per_feature_set": per_feature_set,
        "violations": violations,
    }


def build_group_split_audit(rows: List[Dict[str, str]], provenance_path: Path) -> Dict[str, Any]:
    eligible = eligible_supervised_rows(rows)
    splits_by_extension = defaultdict(set)
    for row in eligible:
        splits_by_extension[row["extension_id"]].add(row["phase3e_split"])
    extension_overlap = {
        extension_id: sorted(splits)
        for extension_id, splits in splits_by_extension.items()
        if len(splits) > 1
    }
    provenance_records = read_json(provenance_path).get("records", []) if provenance_path.exists() else []
    split_by_record = {row["record_id"]: row["phase3e_split"] for row in eligible}
    hash_to_splits = defaultdict(set)
    pair_to_records = defaultdict(list)
    for record in provenance_records:
        split = split_by_record.get(record.get("record_id"))
        if not split:
            continue
        old_hash = record.get("old_sha256") or record.get("old_normalized_sha256")
        new_hash = record.get("new_sha256") or record.get("new_normalized_sha256")
        for value in (old_hash, new_hash):
            if value:
                hash_to_splits[value].add(split)
        pair_to_records[(old_hash, new_hash)].append(record.get("record_id"))
    hash_overlap = {
        digest: sorted(splits)
        for digest, splits in hash_to_splits.items()
        if len(splits) > 1
    }
    duplicate_pairs = {
        f"{old_hash}->{new_hash}": record_ids
        for (old_hash, new_hash), record_ids in pair_to_records.items()
        if old_hash and new_hash and len(record_ids) > 1
    }
    violations = []
    if extension_overlap:
        violations.append({"type": "extension_overlap", "details": extension_overlap})
    if hash_overlap:
        violations.append({"type": "package_hash_overlap", "details": hash_overlap})
    if duplicate_pairs:
        violations.append({"type": "duplicate_transition_pairs", "details": duplicate_pairs})
    return {
        "passed": not violations,
        "split_version": PHASE3E_SPLIT_VERSION,
        "eligible_record_count": len(eligible),
        "extension_ids_per_split": {
            split: sorted({row["extension_id"] for row in eligible if row["phase3e_split"] == split})
            for split in ("train", "validation", "test")
        },
        "extension_overlap": extension_overlap,
        "package_hash_overlap": hash_overlap,
        "duplicate_transition_pairs": duplicate_pairs,
        "repository_fork_duplicate_status": "not_detected_by_current provenance fields",
        "controlled_base_extension_leakage_status": "not_applicable_real_pilot_only",
        "violations": violations,
    }


def train_validate_test_model(
    model_name: str,
    feature_set: str,
    rows: List[Dict[str, str]],
    feature_names: List[str],
    model_root: Path,
    experiment_id: str,
    seed: int,
    fixed_params: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    train_rows = [row for row in rows if row["phase3e_split"] == "train"]
    validation_rows = [row for row in rows if row["phase3e_split"] == "validation"]
    test_rows = [row for row in rows if row["phase3e_split"] == "test"]
    _assert_binary_support(train_rows, "train")
    _assert_binary_support(validation_rows, "validation")
    _assert_binary_support(test_rows, "test")

    x_train, y_train = build_matrix(train_rows, feature_names)
    x_validation, y_validation = build_matrix(validation_rows, feature_names)
    x_test, y_test = build_matrix(test_rows, feature_names)
    candidates = model_candidates(model_name, seed) if fixed_params is None else [fixed_params]
    selected = None
    validation_records = []
    best_key = None
    for params in candidates:
        model = instantiate_model(model_name, params, seed)
        fit_started = time.perf_counter()
        model.fit(x_train, y_train)
        fit_seconds = time.perf_counter() - fit_started
        val_pred = model.predict(x_validation)
        val_score = predict_scores(model, x_validation)
        val_metrics = extended_binary_metrics(y_validation, val_pred, val_score)
        selection_key = (
            val_metrics["f1"],
            val_metrics["balanced_accuracy"],
            -val_metrics["false_positive_rate"],
            -len(str(params)),
        )
        validation_records.append({
            "params": params,
            "metrics": val_metrics,
            "training_seconds": round(fit_seconds, 6),
        })
        if best_key is None or selection_key > best_key:
            best_key = selection_key
            selected = (model, params, fit_seconds)
    assert selected is not None
    model, params, fit_seconds = selected
    test_started = time.perf_counter()
    test_pred = model.predict(x_test)
    test_score = predict_scores(model, x_test)
    evaluation_seconds = time.perf_counter() - test_started
    test_metrics = extended_binary_metrics(y_test, test_pred, test_score)
    predictions = build_prediction_records(test_rows, y_test, test_pred, test_score)
    model_path = model_root / f"{model_name}_{feature_set}" / "model.joblib"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    metadata = {
        "experiment_id": experiment_id,
        "model": model_name,
        "feature_set": feature_set,
        "feature_count": len(feature_names),
        "selected_hyperparameters": params,
        "selection_protocol": "validation_f1_then_balanced_accuracy_then_lower_fpr",
        "random_seed": seed,
        "training_seconds": round(fit_seconds, 6),
        "model_artifact": str(model_path),
    }
    write_json(model_path.parent / "model_metadata.json", metadata)
    result = {
        "experiment_id": experiment_id,
        "model": model_name,
        "feature_set": feature_set,
        "feature_count": len(feature_names),
        "train_records": len(train_rows),
        "validation_records": len(validation_rows),
        "test_records": len(test_rows),
        "train_extensions": len({row["extension_id"] for row in train_rows}),
        "test_extensions": len({row["extension_id"] for row in test_rows}),
        "train_label_distribution": dict(Counter(row["label"] for row in train_rows)),
        "validation_label_distribution": dict(Counter(row["label"] for row in validation_rows)),
        "test_label_distribution": dict(Counter(row["label"] for row in test_rows)),
        "selected_hyperparameters": params,
        "validation_candidates": validation_records,
        "training_seconds": round(fit_seconds, 6),
        "evaluation_seconds": round(evaluation_seconds, 6),
        "model_artifact": str(model_path),
        "test": {
            "metrics": test_metrics,
            "predictions": predictions,
            "y_true": list(map(int, y_test)),
            "y_pred": list(map(int, test_pred)),
            "scores": [round(float(score), 6) for score in test_score],
        },
        "interpretability": extract_interpretability(model, model_name, feature_names),
    }
    write_json(model_path.parent / "metrics.json", test_metrics)
    write_json(model_path.parent / "interpretability.json", result["interpretability"])
    return result


def model_candidates(model_name: str, seed: int) -> List[Dict[str, Any]]:
    if model_name == "logistic_regression":
        return [
            {"C": c, "class_weight": cw}
            for c in (0.1, 1.0, 10.0)
            for cw in (None, "balanced")
        ]
    if model_name == "random_forest":
        return [
            {"n_estimators": n, "max_depth": depth, "min_samples_leaf": leaf, "class_weight": cw}
            for n in (50, 100)
            for depth in (2, 4, None)
            for leaf in (1, 2)
            for cw in (None, "balanced")
        ]
    raise ValueError(f"unsupported model: {model_name}")


def instantiate_model(model_name: str, params: Dict[str, Any], seed: int):
    if model_name == "logistic_regression":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(
                C=params["C"],
                class_weight=params["class_weight"],
                solver="liblinear",
                random_state=seed,
                max_iter=1000,
            )),
        ])
    if model_name == "random_forest":
        return RandomForestClassifier(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            min_samples_leaf=params["min_samples_leaf"],
            class_weight=params["class_weight"],
            random_state=seed,
        )
    raise ValueError(f"unsupported model: {model_name}")


def build_matrix(rows: List[Dict[str, str]], feature_names: List[str]) -> Tuple[np.ndarray, np.ndarray]:
    x_values = []
    y_values = []
    for row in rows:
        features = numeric_features(row)
        x_values.append([float(features.get(name, 0.0)) for name in feature_names])
        y_values.append(label_to_binary(row["label"]))
    return np.array(x_values, dtype=float), np.array(y_values, dtype=int)


def predict_scores(model, matrix: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return model.predict_proba(matrix)[:, 1]
    decision = model.decision_function(matrix)
    return 1 / (1 + np.exp(-decision))


def extended_binary_metrics(
    y_true: Sequence[int],
    y_pred: Sequence[int],
    y_score: Sequence[float] | None = None,
) -> Dict[str, Any]:
    metrics = binary_classification_metrics(y_true, y_pred)
    matrix = binary_confusion_matrix(y_true, y_pred)
    accuracy = sum(int(a == b) for a, b in zip(y_true, y_pred)) / len(y_true) if len(y_true) else 0.0
    metrics["accuracy"] = round(accuracy, 6)
    metrics["specificity"] = metrics["false_alert_specificity"] = round(
        matrix["tn"] / (matrix["tn"] + matrix["fp"]), 6
    ) if matrix["tn"] + matrix["fp"] else 0.0
    if y_score is not None and len(set(y_true)) == 2:
        metrics["roc_auc"] = round(float(roc_auc_score(y_true, y_score)), 6)
        metrics["pr_auc"] = round(float(average_precision_score(y_true, y_score)), 6)
    else:
        metrics["roc_auc"] = None
        metrics["pr_auc"] = None
    metrics["n"] = len(y_true)
    metrics["positive_count"] = int(sum(y_true))
    metrics["negative_count"] = int(len(y_true) - sum(y_true))
    return metrics


def build_prediction_records(
    rows: List[Dict[str, str]],
    y_true: Sequence[int],
    y_pred: Sequence[int],
    scores: Sequence[float],
) -> List[Dict[str, Any]]:
    predictions = []
    for row, truth, pred, score in zip(rows, y_true, y_pred, scores):
        predictions.append({
            "record_id": row["record_id"],
            "extension_id": row["extension_id"],
            "extension_name": row["extension_name"],
            "old_version": row["old_version"],
            "new_version": row["new_version"],
            "split": row["phase3e_split"],
            "true_label": row["label"],
            "true_target": "REVIEW_WORTHY" if truth else "BENIGN",
            "predicted_binary": int(pred),
            "predicted_target": "REVIEW_WORTHY" if pred else "BENIGN",
            "score": round(float(score), 6),
            "label_quality_tier": row.get("label_quality_tier"),
            "source_type": row.get("source_type"),
            "is_controlled": row.get("is_controlled"),
        })
    return predictions


def evaluate_current_rule_engine(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    test_rows = [row for row in eligible_supervised_rows(rows) if row["phase3e_split"] == "test"]
    y_true = []
    y_pred = []
    y_score = []
    predictions = []
    for row in test_rows:
        features = numeric_features(row)
        drift_data = drift_data_from_features(features)
        risk = RiskScorer.calculate_risk_score(drift_data)
        truth = label_to_binary(row["label"])
        pred = int(risk["risk_score"] >= 40.0)
        y_true.append(truth)
        y_pred.append(pred)
        y_score.append(risk["risk_score"] / 100.0)
        predictions.append({
            "record_id": row["record_id"],
            "extension_id": row["extension_id"],
            "true_label": row["label"],
            "true_target": "REVIEW_WORTHY" if truth else "BENIGN",
            "predicted_target": "REVIEW_WORTHY" if pred else "BENIGN",
            "predicted_binary": pred,
            "risk_score": risk["risk_score"],
            "risk_classification": risk["risk_classification"],
            "score_breakdown": risk["score_breakdown"],
            "triggered_rules": risk["triggered_rules"],
            "label_quality_tier": row.get("label_quality_tier"),
            "source_type": row.get("source_type"),
        })
    return {
        "baseline": "current_deterministic_risk_scorer",
        "protocol": "fixed High-or-Critical threshold; no test-set tuning",
        "threshold": "risk_score >= 40.0",
        "record_count": len(test_rows),
        "metrics": extended_binary_metrics(y_true, y_pred, y_score),
        "predictions": predictions,
    }


def drift_data_from_features(features: Dict[str, float]) -> Dict[str, Any]:
    external_count = int(max(features.get("new_external_network_count", 0), 0))
    local_count = int(max(features.get("new_local_network_count", 0), 0))
    decoded_count = int(max(features.get("decoded_endpoint_addition_count", 0), 0))
    plain_http_count = int(max(features.get("plain_http_addition_count", 0), 0))
    added_api_count = int(max(features.get("added_api_count", 0), 0))
    added_obfuscation_score = max(features.get("added_obfuscation_score", 0), 0)
    source_sink_count = int(max(features.get("source_sink_flow_count", 0), 0))
    return {
        "perm_diff": {
            "added_permissions": synthetic_permissions(features),
            "added_permission_risk_score": max(features.get("permission_risk_delta", 0), 0),
        },
        "host_diff": {
            "global_expansion": bool(features.get("all_urls_introduced", 0)),
            "is_expanded": bool(features.get("added_host_count", 0) or features.get("host_scope_score_delta", 0)),
            "scope_score_delta": max(features.get("host_scope_score_delta", 0), 0),
        },
        "manifest_diff": {
            "background_added": bool(features.get("service_worker_introduced", 0)),
        },
        "pkg_diff": {},
        "api_diff": {
            "is_api_drift": added_api_count > 0,
            "unique_added_api_names": [f"static_api_{i}" for i in range(added_api_count)],
        },
        "network_diff": {
            "new_external_destinations": [{"value": f"external-{i}.example"} for i in range(external_count)],
            "new_local_destinations": [{"value": f"localhost:{i}"} for i in range(local_count)],
            "decoded_static_endpoints": [{"value": f"decoded-{i}.example"} for i in range(decoded_count)],
            "plain_http_additions": [{"value": f"http://external-{i}.example"} for i in range(plain_http_count)],
        },
        "obfuscation_diff": {
            "added_obfuscation_score": added_obfuscation_score,
            "added_indicators": [{"type": "static_indicator"} for _ in range(int(added_obfuscation_score > 0))],
        },
        "structure_diff": {
            "source_sink_flows": [
                {"sources": ["sensitive_source"], "sinks": ["network_sink"]}
                for _ in range(source_sink_count)
            ],
            "added_functions": [f"function_{i}" for i in range(int(max(features.get("added_function_count", 0), 0)))],
            "added_event_listeners": [
                f"listener_{i}" for i in range(int(max(features.get("added_event_listener_count", 0), 0)))
            ],
        },
        "analyzer_errors": {},
    }


def synthetic_permissions(features: Dict[str, float]) -> List[str]:
    permissions = []
    if features.get("critical_permission_added", 0):
        permissions.append("scripting")
    if features.get("high_permission_added", 0):
        permissions.append("webRequest")
    if features.get("added_sensitive_permission_count", 0) and not permissions:
        permissions.append("cookies")
    return permissions


def run_ablation_study(
    rows: List[Dict[str, str]],
    full_lr_result: Dict[str, Any],
    model_root: Path,
    experiment_id: str,
    seed: int,
) -> Dict[str, Any]:
    eligible_rows = eligible_supervised_rows(rows)
    feature_names = get_feature_names(eligible_rows)
    base_metrics = full_lr_result["test"]["metrics"]
    base_params = full_lr_result["selected_hyperparameters"]
    output_rows = []
    for family in ("permission", "host", "api", "network", "obfuscation", "structural", "source_sink"):
        reduced_features = feature_names_without_family(feature_names, family)
        if len(reduced_features) == len(feature_names):
            status = "no_matching_features_removed"
            metrics = base_metrics
        elif len(reduced_features) == 0:
            status = "not_run_all_features_removed"
            metrics = None
        else:
            status = "completed"
            result = train_validate_test_model(
                "logistic_regression",
                f"full_driftwatch_without_{family}",
                eligible_rows,
                reduced_features,
                model_root,
                experiment_id,
                seed,
                fixed_params=base_params,
            )
            metrics = result["test"]["metrics"]
        output_rows.append({
            "family_removed": family,
            "status": status,
            "remaining_feature_count": len(reduced_features),
            "base_f1": base_metrics["f1"],
            "f1": metrics["f1"] if metrics else "",
            "delta_f1": round((metrics["f1"] - base_metrics["f1"]), 6) if metrics else "",
            "base_recall": base_metrics["recall"],
            "recall": metrics["recall"] if metrics else "",
            "delta_recall": round((metrics["recall"] - base_metrics["recall"]), 6) if metrics else "",
            "base_fpr": base_metrics["false_positive_rate"],
            "false_positive_rate": metrics["false_positive_rate"] if metrics else "",
            "delta_fpr": round((metrics["false_positive_rate"] - base_metrics["false_positive_rate"]), 6) if metrics else "",
            "base_balanced_accuracy": base_metrics["balanced_accuracy"],
            "balanced_accuracy": metrics["balanced_accuracy"] if metrics else "",
            "delta_balanced_accuracy": round((metrics["balanced_accuracy"] - base_metrics["balanced_accuracy"]), 6) if metrics else "",
        })
    return {
        "model": "logistic_regression",
        "feature_set": "full_driftwatch",
        "same_hyperparameters": base_params,
        "rows": output_rows,
        "interpretation": "Pilot ablation only; one positive held-out test example makes deltas unstable.",
    }


def build_chronological_analysis(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    eligible = eligible_supervised_rows(rows)
    dated = [row for row in eligible if row.get("new_timestamp")]
    by_extension = defaultdict(list)
    for row in dated:
        by_extension[row["extension_id"]].append(row)
    risky_extensions = {
        extension_id
        for extension_id, extension_rows in by_extension.items()
        if any(row["label"] == "risky_transition" for row in extension_rows)
    }
    return {
        "status": "not_reliable_pilot_too_small",
        "qualified_record_count": len(dated),
        "qualified_extension_count": len(by_extension),
        "risky_extension_count": len(risky_extensions),
        "timestamp_source": "version transition metadata from real pilot manifest",
        "reason": (
            "All eligible records have timestamps, but only three review-worthy records across "
            "three extension groups are available. A chronological group-safe train/validation/test "
            "split would be dominated by split artifacts, so Phase 3E records it as a limitation."
        ),
    }


def build_label_sensitivity(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    eligible = eligible_supervised_rows(rows)
    high_confidence = [
        row for row in eligible
        if row.get("label_quality_tier") not in {"SINGLE_REVIEWER_PROVISIONAL", "UNCERTAIN", ""}
    ]
    return {
        "all_eligible_count": len(eligible),
        "all_eligible_label_distribution": dict(Counter(row["label"] for row in eligible)),
        "higher_confidence_count": len(high_confidence),
        "higher_confidence_label_distribution": dict(Counter(row["label"] for row in high_confidence)),
        "status": "not_run_high_confidence_subset_too_small",
        "reason": (
            "The current real pilot does not yet contain a sufficient multi-reviewer or externally "
            "confirmed subset with both target classes. Results remain sensitive to provisional labels."
        ),
    }


def build_real_controlled_analysis(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    eligible = eligible_supervised_rows(rows)
    real = [row for row in eligible if row.get("is_controlled") != "True"]
    controlled = [row for row in eligible if row.get("is_controlled") == "True"]
    return {
        "real_only": {
            "record_count": len(real),
            "label_distribution": dict(Counter(row["label"] for row in real)),
            "status": "primary_phase3e_evaluation_dataset",
        },
        "controlled_only": {
            "record_count": len(controlled),
            "label_distribution": dict(Counter(row["label"] for row in controlled)),
            "status": "not_run_no_controlled_records_in_real_pilot_feature_snapshot",
        },
        "combined": {
            "status": "not_run_to_avoid_controlled_samples_dominating_real_world_claims",
        },
    }


def build_error_analysis(rule_baseline: Dict[str, Any], model_results: List[Dict[str, Any]], rows: List[Dict[str, str]]) -> Dict[str, Any]:
    by_record = {row["record_id"]: row for row in rows}
    analyses = {}
    candidates = [rule_baseline] + [
        result for result in model_results
        if result["feature_set"] == "full_driftwatch"
    ]
    for result in candidates:
        key = result.get("baseline") or result["model"]
        predictions = result["predictions"] if "predictions" in result else result["test"]["predictions"]
        errors = []
        for prediction in predictions:
            if prediction["true_target"] == prediction["predicted_target"]:
                continue
            row = by_record[prediction["record_id"]]
            features = numeric_features(row)
            errors.append({
                "record_id": row["record_id"],
                "extension_id": row["extension_id"],
                "old_version": row["old_version"],
                "new_version": row["new_version"],
                "true_label": row["label"],
                "predicted_target": prediction["predicted_target"],
                "score": prediction.get("score", prediction.get("risk_score")),
                "label_quality_tier": row.get("label_quality_tier"),
                "source_type": row.get("source_type"),
                "feature_values": {
                    "permission_risk_delta": features.get("permission_risk_delta", 0),
                    "host_scope_score_delta": features.get("host_scope_score_delta", 0),
                    "new_external_network_count": features.get("new_external_network_count", 0),
                    "added_obfuscation_score": features.get("added_obfuscation_score", 0),
                    "source_sink_flow_count": features.get("source_sink_flow_count", 0),
                    "service_worker_introduced": features.get("service_worker_introduced", 0),
                },
                "failure_category": categorize_error(row, features, prediction),
            })
        analyses[key] = {
            "error_count": len(errors),
            "errors": errors,
            "category_counts": dict(Counter(error["failure_category"] for error in errors)),
        }
    return {
        "scope": "held-out Phase 3E test split",
        "analyses": analyses,
        "summary": "Errors are pilot observations and may reflect static-analysis limitations or provisional labels.",
    }


def categorize_error(row: Dict[str, str], features: Dict[str, float], prediction: Dict[str, Any]) -> str:
    if row["label"] == "benign_transition":
        if features.get("new_external_network_count", 0) > 0:
            return "feature-rich benign update / network false positive"
        if features.get("added_obfuscation_score", 0) > 0:
            return "benign minification or obfuscation-like static signal"
        return "benign update flagged by broad static drift signal"
    if features.get("added_api_count", 0) == 0 and features.get("new_external_network_count", 0) == 0:
        return "insufficient behaviour signal"
    return "model missed review-worthy transition despite available static drift"


def build_false_alert_analysis(error_analysis: Dict[str, Any]) -> Dict[str, Any]:
    output = {}
    for key, analysis in error_analysis["analyses"].items():
        fps = [error for error in analysis["errors"] if error["true_label"] == "benign_transition"]
        output[key] = {
            "false_positive_count": len(fps),
            "category_counts": dict(Counter(error["failure_category"] for error in fps)),
            "records": fps,
        }
    return output


def build_false_negative_analysis(error_analysis: Dict[str, Any]) -> Dict[str, Any]:
    output = {}
    for key, analysis in error_analysis["analyses"].items():
        fns = [error for error in analysis["errors"] if error["true_label"] == "risky_transition"]
        output[key] = {
            "false_negative_count": len(fns),
            "category_counts": dict(Counter(error["failure_category"] for error in fns)),
            "records": fns,
        }
    return output


def bootstrap_confidence_intervals(y_true: Sequence[int], y_pred: Sequence[int], seed: int = 1337, samples: int = 1000) -> Dict[str, Any]:
    if len(y_true) < 20:
        return {
            "status": "computed_but_not_reliable_for_inference",
            "reason": "held-out test sample has fewer than 20 records",
            "test_record_count": len(y_true),
            "intervals": _bootstrap_intervals(y_true, y_pred, seed, samples),
        }
    return {
        "status": "computed",
        "test_record_count": len(y_true),
        "intervals": _bootstrap_intervals(y_true, y_pred, seed, samples),
    }


def _bootstrap_intervals(y_true: Sequence[int], y_pred: Sequence[int], seed: int, samples: int) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    values = defaultdict(list)
    n = len(y_true)
    for _ in range(samples):
        indexes = rng.integers(0, n, size=n)
        sample_true = [y_true[i] for i in indexes]
        sample_pred = [y_pred[i] for i in indexes]
        metrics = binary_classification_metrics(sample_true, sample_pred)
        for metric in ("precision", "recall", "f1", "balanced_accuracy"):
            values[metric].append(metrics[metric])
    return {
        metric: {
            "p05": round(float(np.percentile(metric_values, 5)), 6),
            "p50": round(float(np.percentile(metric_values, 50)), 6),
            "p95": round(float(np.percentile(metric_values, 95)), 6),
        }
        for metric, metric_values in values.items()
    }


def extract_interpretability(model, model_name: str, feature_names: List[str]) -> Dict[str, Any]:
    if model_name == "logistic_regression":
        classifier = model.named_steps["classifier"]
        coefficients = classifier.coef_[0]
        ordered = sorted(
            zip(feature_names, coefficients),
            key=lambda item: abs(item[1]),
            reverse=True,
        )
        return {
            "top_coefficients": [
                {"feature": name, "coefficient": round(float(coef), 6)}
                for name, coef in ordered[:10]
            ],
            "intercept": round(float(classifier.intercept_[0]), 6),
            "note": "Coefficients are associations in this pilot corpus, not causal claims.",
        }
    if model_name == "random_forest":
        ordered = sorted(
            zip(feature_names, model.feature_importances_),
            key=lambda item: item[1],
            reverse=True,
        )
        return {
            "top_feature_importances": [
                {"feature": name, "importance": round(float(value), 6)}
                for name, value in ordered[:10]
            ],
            "note": "Impurity importances are descriptive and unstable on this small corpus.",
        }
    return {}


def get_feature_names(rows: List[Dict[str, str]]) -> List[str]:
    if not rows:
        return []
    excluded = METADATA_COLUMNS | {"phase3e_split", "original_split"}
    return [name for name in rows[0] if name not in excluded]


def numeric_features(row: Dict[str, str]) -> Dict[str, float]:
    excluded = METADATA_COLUMNS | {"phase3e_split", "original_split"}
    features = {}
    for key, value in row.items():
        if key in excluded:
            continue
        features[key] = float(value) if value not in ("", None) else 0.0
    return features


def flatten_result_for_csv(result: Dict[str, Any]) -> Dict[str, Any]:
    metrics = result["test"]["metrics"]
    return {
        "model": result["model"],
        "feature_set": result["feature_set"],
        "feature_count": result["feature_count"],
        "train_records": result["train_records"],
        "validation_records": result["validation_records"],
        "test_records": result["test_records"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "balanced_accuracy": metrics["balanced_accuracy"],
        "specificity": metrics["specificity"],
        "false_positive_rate": metrics["false_positive_rate"],
        "false_negative_rate": metrics["false_negative_rate"],
        "false_alerts_per_100_benign": metrics["false_alerts_per_100_benign"],
        "accuracy": metrics["accuracy"],
        "roc_auc": metrics["roc_auc"],
        "pr_auc": metrics["pr_auc"],
        "confusion_matrix": json.dumps(metrics["confusion_matrix"], sort_keys=True),
    }


def flatten_model_comparison(result: Dict[str, Any]) -> Dict[str, Any]:
    row = flatten_result_for_csv(result)
    row["interpretability"] = "coefficient table" if result["model"] == "logistic_regression" else "feature importance table"
    row["training_requirement"] = "requires labeled training data"
    row["operational_complexity"] = "research artifact only; not production integrated"
    return row


def flatten_rule_comparison(rule_baseline: Dict[str, Any]) -> Dict[str, Any]:
    metrics = rule_baseline["metrics"]
    return {
        "model": "rule_engine",
        "feature_set": "full_driftwatch",
        "feature_count": "current deterministic scorer",
        "train_records": 0,
        "validation_records": 0,
        "test_records": rule_baseline["record_count"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "balanced_accuracy": metrics["balanced_accuracy"],
        "specificity": metrics["specificity"],
        "false_positive_rate": metrics["false_positive_rate"],
        "false_negative_rate": metrics["false_negative_rate"],
        "false_alerts_per_100_benign": metrics["false_alerts_per_100_benign"],
        "accuracy": metrics["accuracy"],
        "roc_auc": metrics["roc_auc"],
        "pr_auc": metrics["pr_auc"],
        "confusion_matrix": json.dumps(metrics["confusion_matrix"], sort_keys=True),
        "interpretability": "explicit deterministic score breakdown",
        "training_requirement": "none",
        "operational_complexity": "current production explainable scoring logic",
    }


def _assert_binary_support(rows: List[Dict[str, str]], split: str) -> None:
    labels = {row["label"] for row in rows}
    if not {"benign_transition", "risky_transition"} <= labels:
        raise ValueError(f"{split} split lacks both target classes: {dict(Counter(row['label'] for row in rows))}")


def read_json(path: Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_git_commit() -> str | None:
    git_head = Path(".git/HEAD")
    if not git_head.exists():
        return None
    head = git_head.read_text(encoding="utf-8").strip()
    if head.startswith("ref: "):
        ref = Path(".git") / head.removeprefix("ref: ").strip()
        if ref.exists():
            return ref.read_text(encoding="utf-8").strip()
        return None
    return head


if __name__ == "__main__":
    summary = run_phase3e_pilot()
    print(json.dumps({
        "experiment_id": summary["experiment_manifest"]["experiment_id"],
        "dataset_version": summary["dataset_snapshot"]["dataset_version"],
        "eligible_supervised_records": summary["dataset_snapshot"]["eligible_supervised_records"],
        "rule_f1": summary["rule_baseline"]["metrics"]["f1"],
        "artifacts": summary["experiment_manifest"]["artifact_paths"],
    }, indent=2))
