from __future__ import annotations

from typing import Callable, Dict, List

from research.loaders import label_to_binary, split_metadata_features
from research.metrics import binary_classification_metrics


BASELINE_RULES: Dict[str, Callable[[Dict[str, float]], int]] = {
    "permission_only": lambda f: int(
        f.get("added_sensitive_permission_count", 0) > 0
        or f.get("permission_risk_delta", 0) > 0
        or f.get("critical_permission_added", 0) > 0
        or f.get("high_permission_added", 0) > 0
    ),
    "manifest_permission": lambda f: int(
        f.get("added_sensitive_permission_count", 0) > 0
        or f.get("permission_risk_delta", 0) > 0
        or f.get("host_scope_score_delta", 0) > 0
        or f.get("all_urls_introduced", 0) > 0
        or f.get("service_worker_introduced", 0) > 0
        or f.get("content_script_changed", 0) > 0
        or f.get("externally_connectable_changed", 0) > 0
    ),
    "latest_version_static": lambda f: int(
        f.get("v2_sensitive_permission_count", 0) > 0
        or f.get("v2_all_urls_present", 0) > 0
        or f.get("v2_sensitive_api_count", 0) > 0
        or f.get("v2_external_domain_count", 0) > 0
        or f.get("v2_obfuscation_indicator_count", 0) > 0
        or f.get("v2_source_sink_indicator_count", 0) > 0
    ),
    "simple_differential": lambda f: int(
        f.get("permission_count_delta", 0) > 0
        or f.get("host_count_delta", 0) > 0
        or f.get("api_count_delta", 0) > 0
        or f.get("network_destination_count_delta", 0) > 0
        or f.get("obfuscation_count_delta", 0) > 0
    ),
    "full_driftwatch": lambda f: int(
        f.get("added_sensitive_permission_count", 0) > 0
        or f.get("all_urls_introduced", 0) > 0
        or f.get("added_api_count", 0) > 0
        or f.get("new_external_network_count", 0) > 0
        or f.get("decoded_endpoint_addition_count", 0) > 0
        or f.get("added_obfuscation_score", 0) > 0
        or f.get("source_sink_flow_count", 0) > 0
    ),
}


def evaluate_rule_baseline(baseline_name: str, rows: List[Dict[str, str]]) -> Dict:
    if baseline_name not in BASELINE_RULES:
        raise ValueError(f"unknown baseline: {baseline_name}")

    y_true = []
    y_pred = []
    predictions = []
    rule = BASELINE_RULES[baseline_name]

    for row in rows:
        metadata, features = split_metadata_features(row)
        truth = label_to_binary(metadata["label"])
        pred = rule(features)
        y_true.append(truth)
        y_pred.append(pred)
        predictions.append({
            "record_id": metadata["record_id"],
            "extension_id": metadata["extension_id"],
            "true_label": metadata["label"],
            "true_binary": truth,
            "predicted_binary": pred,
            "predicted_label": "risky_transition" if pred else "benign_transition",
            "split": metadata.get("split"),
        })

    metrics = binary_classification_metrics(y_true, y_pred)
    return {
        "baseline": baseline_name,
        "protocol": "deterministic_pilot_rule",
        "record_count": len(rows),
        "metrics": metrics,
        "predictions": predictions,
    }
