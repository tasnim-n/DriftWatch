from __future__ import annotations

from typing import Dict, Iterable, List


FEATURE_FAMILY_TERMS: Dict[str, tuple[str, ...]] = {
    "permission": ("permission", "critical_permission", "high_permission"),
    "host": ("host", "all_urls"),
    "api": ("api", "sensitive_api"),
    "network": ("network", "endpoint", "domain", "websocket", "beacon"),
    "obfuscation": ("obfuscation", "entropy", "encoded", "decoded", "base64"),
    "structural": ("structural", "function", "line_count", "js_file", "package_file"),
    "source_sink": ("source_sink", "source_to_sink"),
}


def feature_names_without_family(feature_names: Iterable[str], family: str) -> List[str]:
    if family not in FEATURE_FAMILY_TERMS:
        raise ValueError(f"unknown ablation family: {family}")
    terms = FEATURE_FAMILY_TERMS[family]
    return [
        name for name in feature_names
        if not any(term in name.lower() for term in terms)
    ]


def ablation_status(rows: Iterable[dict]) -> Dict[str, str]:
    row_count = len(list(rows))
    if row_count < 20:
        return {
            "status": "not_run_dataset_too_small",
            "reason": "fewer than 20 records",
        }
    return {
        "status": "ready",
        "reason": "dataset size gate passed; run with a valid model/split configuration",
    }
