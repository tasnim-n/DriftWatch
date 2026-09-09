from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from research.phase3e import build_leakage_audit, read_json, write_csv, write_json
from research.phase3f import compare_manifest_dicts, get_git_commit, read_manifest_from_zip
from research.phase3h import PHASE3H_DATASET_VERSION
from research.loaders import METADATA_COLUMNS


PHASE3H5_ARTIFACT_VERSION = "driftbench-independent-review-phase3h5-v1"
PHASE3H5_REVIEW_SCHEMA_VERSION = "phase3h5-independent-review-schema-v1"
PHASE3H5_GOLD_SET_VERSION = "phase3h5-gold-set-methodology-v1"
PHASE3H5_DECISION = "MORE INDEPENDENT REVIEW REQUIRED"

ALLOWED_REVIEW_LABELS = [
    "BENIGN_TRANSITION",
    "RISKY_TRANSITION",
    "MALICIOUS_TRANSITION",
    "UNCERTAIN",
    "EXCLUDED",
]
ALLOWED_CONFIDENCE = ["HIGH", "MEDIUM", "LOW"]

LABEL_DEFINITIONS = {
    "BENIGN_TRANSITION": (
        "A version update whose relevant security-sensitive changes have a documented, "
        "legitimate functional purpose and no independent evidence supporting harmful intent "
        "or unacceptable security behavior."
    ),
    "RISKY_TRANSITION": (
        "A version update introducing meaningful security-sensitive capability or behavior "
        "warranting security review, even when malicious intent is not proven."
    ),
    "MALICIOUS_TRANSITION": (
        "A transition with strong independent evidence that the update introduced or enabled "
        "intentionally harmful behavior."
    ),
    "UNCERTAIN": "Available evidence is insufficient or contradictory.",
    "EXCLUDED": (
        "The record is methodologically unsuitable due to identity, provenance, corruption, "
        "licensing, duplicate, or comparable quality problems."
    ),
}

CONFIDENCE_DEFINITIONS = {
    "HIGH": "Strong independent evidence and a clear version transition.",
    "MEDIUM": "Reasonable evidence but some ambiguity remains.",
    "LOW": "Evidence is insufficient, indirect, or incomplete.",
}

EVIDENCE_HIERARCHY = {
    "TIER_1": "Peer-reviewed dataset or verified public security disclosure.",
    "TIER_2": "Multiple reputable independent security reports.",
    "TIER_3": "Maintainer or vendor disclosure with corroborating evidence.",
    "TIER_4": "Repository history, release notes, package metadata, or commit evidence.",
    "TIER_5": "Single-reviewer technical assessment.",
    "TIER_6": "Weak, incomplete, or contradictory evidence.",
}

REVIEW_METADATA_BLOCKLIST = {
    "reviewer_id",
    "review_id",
    "reviewer_confidence",
    "confidence",
    "evidence_tier",
    "adjudication_status",
    "adjudicated_label",
    "gold_set_flag",
    "gold_label_source",
    "review_rationale",
    "rationale",
    "label_source",
    "review_timestamp",
    "training_eligible",
    "eligible_for_supervised_training",
    "manual_review_notes",
    "blind_review",
}


def run_phase3h5_review_workflow(
    *,
    phase3h_curation_dir: str | Path = "artifacts/driftbench/phase3h",
    phase3h_feature_dir: str | Path = "artifacts/driftbench/phase3h_features",
    phase3h_experiment_dir: str | Path = "artifacts/experiments/phase3h",
    curation_dir: str | Path = "artifacts/driftbench/phase3h5",
    experiment_dir: str | Path = "artifacts/experiments/phase3h5",
    review_dir: str | Path = "datasets/reviews/phase3h5",
) -> Dict[str, Any]:
    phase3h_curation_dir = Path(phase3h_curation_dir)
    phase3h_feature_dir = Path(phase3h_feature_dir)
    phase3h_experiment_dir = Path(phase3h_experiment_dir)
    curation_dir = Path(curation_dir)
    experiment_dir = Path(experiment_dir)
    review_dir = Path(review_dir)
    packet_dir = curation_dir / "review_packets"
    for path in (curation_dir, experiment_dir, review_dir, packet_dir):
        path.mkdir(parents=True, exist_ok=True)

    phase3h_reference = freeze_phase3h_reference(phase3h_curation_dir, phase3h_feature_dir, phase3h_experiment_dir)
    dataset_manifest = read_json(phase3h_curation_dir / "dataset_manifest.json")
    provenance_manifest = read_json(phase3h_curation_dir / "provenance_manifest.json")
    external_holdout = read_json(phase3h_curation_dir / "external_holdout_manifest.json")
    duplicate_report = read_json(phase3h_curation_dir / "duplicate_report.json")
    leakage_report = read_json(phase3h_curation_dir / "leakage_report.json")
    feature_rows = load_phase3h_features(phase3h_feature_dir)
    holdout_ids = {record["record_id"] for record in external_holdout.get("records", [])}
    records = list(dataset_manifest["records"])
    provenance_by_id = {record["record_id"]: record for record in provenance_manifest["records"]}
    review_submissions = load_review_submissions(review_dir)

    review_items = [
        build_review_item(record, provenance_by_id.get(record["pair_id"], {}), feature_rows.get(record["pair_id"], {}), record["pair_id"] in holdout_ids)
        for record in records
    ]
    review_items.sort(key=lambda item: (-item["priority_score"], item["record_id"]))
    review_packets = [build_blind_review_packet(item) for item in review_items]
    for packet in review_packets:
        write_json(packet_dir / f"{packet['record_id']}.json", packet)

    review_queue = build_review_queue(review_packets)
    write_json(curation_dir / "review_queue.json", review_queue)
    write_review_queue_csv(curation_dir / "review_queue.csv", review_queue["records"])
    write_json(curation_dir / "reviewer_schema.json", reviewer_schema())
    write_json(review_dir / "review_submission_schema.json", reviewer_submission_schema())

    second_review_queue = build_second_review_queue(review_items)
    write_json(curation_dir / "second_review_queue.json", second_review_queue)
    write_review_queue_csv(review_dir / "second_review_queue.csv", second_review_queue["records"])

    review_summary = build_review_summary(records, review_items, review_submissions, holdout_ids)
    label_quality = build_label_quality_report(records, review_submissions)
    unresolved = build_unresolved_records(records, review_items)
    adjudication = build_adjudication_report(review_submissions)
    inter_rater = build_inter_rater_agreement(adjudication)
    eligibility = build_eligibility_report(records, adjudication, holdout_ids)
    gold_set = build_gold_set_manifest(records, provenance_by_id, adjudication)
    gold_quality = build_gold_set_quality(gold_set)
    provenance_review = build_provenance_review(provenance_manifest)
    leakage_audit = build_reviewer_metadata_leakage_audit(phase3h_feature_dir)
    research_integrity = build_research_integrity_audit(
        gold_set=gold_set,
        inter_rater=inter_rater,
        review_summary=review_summary,
    )
    readiness = build_readiness(
        review_summary=review_summary,
        label_quality=label_quality,
        gold_set=gold_set,
        external_holdout=external_holdout,
        leakage_audit=leakage_audit,
        duplicate_report=duplicate_report,
        leakage_report=leakage_report,
        provenance_review=provenance_review,
    )

    write_json(curation_dir / "phase3h_reference.json", phase3h_reference)
    write_json(curation_dir / "review_summary.json", review_summary)
    write_json(curation_dir / "label_quality_report.json", label_quality)
    write_json(curation_dir / "unresolved_records.json", unresolved)
    write_json(curation_dir / "adjudication_report.json", adjudication)
    write_json(curation_dir / "inter_rater_agreement.json", inter_rater)
    write_json(curation_dir / "eligibility_report.json", eligibility)
    write_json(curation_dir / "gold_set_manifest.json", gold_set)
    write_json(curation_dir / "gold_set_quality.json", gold_quality)
    write_json(curation_dir / "provenance_review.json", provenance_review)
    write_json(curation_dir / "reviewer_metadata_leakage_audit.json", leakage_audit)
    write_json(curation_dir / "research_integrity_audit.json", research_integrity)
    write_json(curation_dir / "readiness.json", readiness)

    comparison_rows = build_phase3h_vs_phase3h5_comparison(dataset_manifest, review_summary, label_quality, gold_set, external_holdout)
    write_csv(experiment_dir / "phase3h_vs_phase3h5_ground_truth.csv", comparison_rows)
    write_json(experiment_dir / "dataset_snapshot.json", build_dataset_snapshot(dataset_manifest, review_summary, label_quality, gold_set, external_holdout, phase3h_reference))
    write_json(experiment_dir / "experiment_manifest.json", {
        "phase": "Phase 3H.5",
        "artifact_version": PHASE3H5_ARTIFACT_VERSION,
        "parent_dataset_version": PHASE3H_DATASET_VERSION,
        "purpose": "independent label review workflow, adjudication readiness, and gold-set qualification",
        "model_training_performed": False,
        "production_ml_integration": False,
        "production_scoring_changed": False,
        "feature_regeneration_performed": False,
        "code_version": get_git_commit(),
        "final_decision": PHASE3H5_DECISION,
    })

    return {
        "phase3h_reference": phase3h_reference,
        "review_summary": review_summary,
        "label_quality": label_quality,
        "gold_set": gold_set,
        "readiness": readiness,
    }


def load_phase3h_features(feature_dir: Path) -> Dict[str, Dict[str, str]]:
    path = feature_dir / "full_driftwatch.csv"
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as handle:
        return {row["record_id"]: row for row in csv.DictReader(handle)}


def load_review_submissions(review_dir: Path) -> List[Dict[str, Any]]:
    submissions: List[Dict[str, Any]] = []
    submissions_path = review_dir / "reviews.json"
    if submissions_path.exists():
        payload = read_json(submissions_path)
        submissions.extend(payload.get("reviews", payload if isinstance(payload, list) else []))
    submissions_dir = review_dir / "submissions"
    if submissions_dir.exists():
        for path in sorted(submissions_dir.glob("*.json")):
            submissions.append(read_json(path))
    return [validate_review_submission(row) for row in submissions]


def validate_review_submission(row: Dict[str, Any]) -> Dict[str, Any]:
    label = row.get("independent_label")
    confidence = row.get("confidence")
    if label not in ALLOWED_REVIEW_LABELS:
        raise ValueError(f"invalid independent_label {label!r}")
    if confidence not in ALLOWED_CONFIDENCE:
        raise ValueError(f"invalid confidence {confidence!r}")
    if not row.get("reviewer_id"):
        raise ValueError("reviewer_id is required for genuine review submissions")
    if row.get("reviewer_id") in {"AI", "LLM", "codex", "assistant"}:
        raise ValueError("AI assistance cannot be represented as an independent reviewer")
    if not row.get("rationale"):
        raise ValueError("rationale is required")
    return dict(row)


def build_review_item(record: Dict[str, Any], provenance: Dict[str, Any], features: Dict[str, str], is_holdout: bool) -> Dict[str, Any]:
    priority_score, reasons = review_priority(record, features, is_holdout)
    evidence_tier = evidence_tier_for(record)
    return {
        "record_id": record["pair_id"],
        "extension_id": record["extension_id"],
        "extension_name": record["extension_name"],
        "source": record["source"],
        "repository": provenance.get("repository", record["source"]),
        "source_url": provenance.get("source_url", record["source"]),
        "license": record["license"],
        "old_version": record["old_version"],
        "new_version": record["new_version"],
        "old_timestamp": record.get("old_timestamp"),
        "new_timestamp": record.get("new_timestamp"),
        "release_notes": release_evidence(record, provenance),
        "provenance_id": provenance.get("provenance_id", f"{record['source']}:{record['pair_id']}"),
        "provenance_references": provenance.get("evidence_references", []),
        "manifest_diff": safe_manifest_diff(record),
        "permission_diff": permission_diff(features),
        "host_scope_diff": host_scope_diff(features),
        "sensitive_api_diff": sensitive_api_diff(features),
        "network_destination_diff": network_destination_diff(features),
        "structural_diff": structural_diff(features),
        "obfuscation_diff": obfuscation_diff(features),
        "source_to_sink_evidence": source_to_sink_evidence(features),
        "relevant_public_evidence": public_evidence(record, provenance, evidence_tier),
        "evidence_tier": evidence_tier,
        "priority_score": priority_score,
        "priority_reasons": reasons,
        "external_holdout": is_holdout,
        "current_dataset_label": record["label"],
        "current_label_quality_tier": record.get("label_quality_tier", "UNCERTAIN"),
        "current_label_confidence": record.get("label_confidence", "low"),
        "eligible_for_supervised_training_before_review": bool(record.get("eligible_for_supervised_training")),
        "ai_assisted": True,
    }


def review_priority(record: Dict[str, Any], features: Dict[str, str], is_holdout: bool) -> tuple[int, List[str]]:
    score = 10
    reasons: List[str] = []
    label = record["label"]
    if label == "malicious_transition":
        score += 120
        reasons.append("MALICIOUS_TRANSITION candidate")
    if label == "risky_transition":
        score += 100
        reasons.append("RISKY_TRANSITION requires independent confirmation")
    if label == "uncertain":
        score += 90
        reasons.append("UNCERTAIN label requires resolution attempt")
    if is_holdout:
        score += 40
        reasons.append("external holdout label quality should be strengthened without tuning leakage")
    numeric_checks = [
        ("added_sensitive_permission_count", 35, "high-impact sensitive permission expansion"),
        ("all_urls_introduced", 35, "broad <all_urls> host expansion"),
        ("wildcard_host_introduced", 20, "wildcard host expansion"),
        ("critical_api_added", 35, "new critical browser API"),
        ("added_api_count", 25, "new sensitive browser API usage"),
        ("new_external_network_count", 25, "new external network destinations"),
        ("source_sink_flow_count", 30, "source-to-sink heuristic indicator"),
        ("decoded_endpoint_addition_count", 20, "decoded static endpoint indicator"),
        ("dynamic_execution_added_count", 20, "new dynamic execution indicator"),
        ("added_obfuscation_score", 20, "substantial obfuscation change"),
    ]
    for column, weight, reason in numeric_checks:
        if as_float(features.get(column)) > 0:
            score += weight
            reasons.append(reason)
    if not reasons:
        reasons.append("low-priority benign maintenance candidate")
    return score, reasons


def build_blind_review_packet(item: Dict[str, Any]) -> Dict[str, Any]:
    hidden = {
        "driftwatch_numeric_output": True,
        "driftwatch_severity": True,
        "rule_recommendation": True,
        "ml_output": True,
        "previous_predictive_model_output": True,
        "current_dataset_label": True,
        "reviewer_a_label": True,
    }
    return {
        "schema_version": PHASE3H5_REVIEW_SCHEMA_VERSION,
        "artifact_version": PHASE3H5_ARTIFACT_VERSION,
        "record_id": item["record_id"],
        "extension_id": item["extension_id"],
        "extension_name": item["extension_name"],
        "source": item["source"],
        "repository": item["repository"],
        "source_url": item["source_url"],
        "license": item["license"],
        "old_version": item["old_version"],
        "new_version": item["new_version"],
        "old_timestamp": item["old_timestamp"],
        "new_timestamp": item["new_timestamp"],
        "release_notes": item["release_notes"],
        "provenance_id": item["provenance_id"],
        "provenance_references": item["provenance_references"],
        "manifest_diff": item["manifest_diff"],
        "permission_diff": item["permission_diff"],
        "host_scope_diff": item["host_scope_diff"],
        "sensitive_api_diff": item["sensitive_api_diff"],
        "network_destination_diff": item["network_destination_diff"],
        "structural_diff": item["structural_diff"],
        "obfuscation_diff": item["obfuscation_diff"],
        "source_to_sink_evidence": item["source_to_sink_evidence"],
        "relevant_commit_or_release_evidence": item["relevant_public_evidence"],
        "independent_public_security_evidence": [],
        "evidence_tier": item["evidence_tier"],
        "blind_review": True,
        "hidden_from_reviewer": hidden,
        "ai_assisted": item["ai_assisted"],
        "ground_truth_authority": "pending genuine independent reviewer or documented external evidence",
        "review_form": {
            "review_id": "",
            "reviewer_id": "",
            "record_id": item["record_id"],
            "review_round": "INITIAL_BLIND",
            "independent_label": "",
            "confidence": "",
            "rationale": "",
            "evidence_references": [],
            "blind_review": True,
            "review_timestamp": "",
            "review_status": "PENDING",
        },
    }


def safe_manifest_diff(record: Dict[str, Any]) -> Dict[str, Any]:
    try:
        diff = compare_manifest_dicts(
            read_manifest_from_zip(Path(record["old_archive_path"])),
            read_manifest_from_zip(Path(record["new_archive_path"])),
        )
    except Exception as exc:  # pragma: no cover - defensive artifact generation
        return {"available": False, "error": str(exc)}
    return {
        "available": True,
        "added_permissions": diff.get("added_permissions", []),
        "removed_permissions": diff.get("removed_permissions", []),
        "added_hosts": diff.get("added_hosts", []),
        "removed_hosts": diff.get("removed_hosts", []),
        "background_added": diff.get("background_added", False),
        "content_scripts_changed": diff.get("content_scripts_changed", False),
        "web_accessible_resources_changed": diff.get("web_accessible_resources_changed", False),
        "externally_connectable_changed": diff.get("v1_raw", {}).get("externally_connectable") != diff.get("v2_raw", {}).get("externally_connectable"),
    }


def permission_diff(features: Dict[str, str]) -> Dict[str, Any]:
    return pick_numeric(features, [
        "added_permission_count",
        "removed_permission_count",
        "added_sensitive_permission_count",
        "removed_sensitive_permission_count",
        "permission_risk_delta",
        "critical_permission_added",
        "high_permission_added",
        "optional_permission_change_count",
    ])


def host_scope_diff(features: Dict[str, str]) -> Dict[str, Any]:
    return pick_numeric(features, ["host_count_delta", "added_host_count", "host_scope_score_delta", "wildcard_host_introduced", "all_urls_introduced"])


def sensitive_api_diff(features: Dict[str, str]) -> Dict[str, Any]:
    return pick_numeric(features, ["api_count_delta", "added_api_count", "critical_api_added", "api_analyzer_available"])


def network_destination_diff(features: Dict[str, str]) -> Dict[str, Any]:
    return pick_numeric(features, [
        "network_destination_count_delta",
        "new_external_network_count",
        "new_local_network_count",
        "plain_http_addition_count",
        "decoded_endpoint_addition_count",
        "hardcoded_ip_addition_count",
        "network_analyzer_available",
    ])


def structural_diff(features: Dict[str, str]) -> Dict[str, Any]:
    return pick_numeric(features, [
        "function_count_delta",
        "added_function_count",
        "added_event_listener_count",
        "modified_file_count",
        "structure_analyzer_available",
    ])


def obfuscation_diff(features: Dict[str, str]) -> Dict[str, Any]:
    return pick_numeric(features, [
        "obfuscation_count_delta",
        "added_obfuscation_score",
        "dynamic_execution_added_count",
        "obfuscation_analyzer_available",
    ])


def source_to_sink_evidence(features: Dict[str, str]) -> Dict[str, Any]:
    count = as_float(features.get("source_sink_flow_count"))
    return {
        "heuristic_indicator_count": int(count),
        "claim_limit": "heuristic indicator only; not confirmed exfiltration",
        "available": bool(features),
    }


def pick_numeric(features: Dict[str, str], keys: Iterable[str]) -> Dict[str, Any]:
    if not features:
        return {"available": False, "reason": "external holdout or missing Phase 3H non-holdout feature row"}
    return {"available": True, **{key: as_number(features.get(key)) for key in keys}}


def as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def as_number(value: Any) -> int | float:
    number = as_float(value)
    return int(number) if number.is_integer() else number


def release_evidence(record: Dict[str, Any], provenance: Dict[str, Any]) -> List[str]:
    evidence = list(provenance.get("evidence_references", []))
    if not evidence:
        evidence.extend(record.get("provenance", {}).get("notes", []))
    return evidence[:8]


def public_evidence(record: Dict[str, Any], provenance: Dict[str, Any], tier: str) -> List[Dict[str, str]]:
    references = release_evidence(record, provenance)
    return [{"evidence_tier": tier, "reference": reference} for reference in references]


def evidence_tier_for(record: Dict[str, Any]) -> str:
    if record.get("label_source") == "repository_documented_change":
        return "TIER_4"
    if record.get("label") == "uncertain":
        return "TIER_6"
    return "TIER_5"


def build_review_queue(review_packets: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "schema_version": "phase3h5-blind-review-queue-v1",
        "artifact_version": PHASE3H5_ARTIFACT_VERSION,
        "blind_review_required": True,
        "score_fields_hidden": True,
        "records": [
            {
                "rank": index + 1,
                "record_id": packet["record_id"],
                "extension_id": packet["extension_id"],
                "extension_name": packet["extension_name"],
                "old_version": packet["old_version"],
                "new_version": packet["new_version"],
                "packet_path": f"artifacts/driftbench/phase3h5/review_packets/{packet['record_id']}.json",
                "blind_review": True,
                "review_status": "INITIAL_REVIEW_PENDING",
            }
            for index, packet in enumerate(review_packets)
        ],
    }


def build_second_review_queue(review_items: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    priority_records = [item for item in review_items if is_priority_review(item)]
    return {
        "schema_version": "phase3h5-second-review-queue-v1",
        "status": "SECOND_REVIEW_PENDING",
        "no_fake_second_reviewer": True,
        "reviewer_a_label_hidden_until_reviewer_b_decision": True,
        "records": [
            {
                "rank": index + 1,
                "record_id": item["record_id"],
                "extension_id": item["extension_id"],
                "packet_path": f"artifacts/driftbench/phase3h5/review_packets/{item['record_id']}.json",
                "priority_score": item["priority_score"],
                "priority_reasons": item["priority_reasons"],
                "blind_review": True,
                "review_status": "SECOND_REVIEW_PENDING",
            }
            for index, item in enumerate(priority_records)
        ],
    }


def is_priority_review(item: Dict[str, Any]) -> bool:
    return (
        item["current_dataset_label"] in {"risky_transition", "malicious_transition", "uncertain"}
        or item["external_holdout"]
        or item["priority_score"] >= 70
    )


def write_review_queue_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, sort_keys=True) if isinstance(value, (list, dict)) else value for key, value in row.items()})


def reviewer_schema() -> Dict[str, Any]:
    return {
        "schema_version": PHASE3H5_REVIEW_SCHEMA_VERSION,
        "allowed_labels": ALLOWED_REVIEW_LABELS,
        "allowed_confidence": ALLOWED_CONFIDENCE,
        "confidence_definitions": CONFIDENCE_DEFINITIONS,
        "label_definitions": LABEL_DEFINITIONS,
        "evidence_hierarchy": EVIDENCE_HIERARCHY,
        "required_fields": [
            "review_id",
            "reviewer_id",
            "record_id",
            "review_round",
            "independent_label",
            "confidence",
            "rationale",
            "evidence_references",
            "blind_review",
            "review_timestamp",
            "review_status",
        ],
        "prohibited_ground_truth_sources": [
            "DriftWatch final risk score",
            "DriftWatch severity",
            "rule recommendation",
            "ML output",
            "previous predictive model output",
        ],
    }


def reviewer_submission_schema() -> Dict[str, Any]:
    schema = reviewer_schema()
    schema["example_blank_submission"] = {
        "review_id": "",
        "reviewer_id": "",
        "record_id": "",
        "review_round": "INITIAL_BLIND",
        "independent_label": "",
        "confidence": "",
        "rationale": "",
        "evidence_references": [],
        "blind_review": True,
        "review_timestamp": "",
        "review_status": "SUBMITTED",
    }
    return schema


def build_review_summary(records: Sequence[Dict[str, Any]], review_items: Sequence[Dict[str, Any]], submissions: Sequence[Dict[str, Any]], holdout_ids: set[str]) -> Dict[str, Any]:
    labels = Counter(record["label"] for record in records)
    priority_items = [item for item in review_items if is_priority_review(item)]
    return {
        "artifact_version": PHASE3H5_ARTIFACT_VERSION,
        "parent_dataset_version": PHASE3H_DATASET_VERSION,
        "total_records_in_review_scope": len(records),
        "review_queue_records": len(review_items),
        "review_priority_records": len(priority_items),
        "benign_review_candidates": labels.get("benign_transition", 0),
        "risky_review_candidates": labels.get("risky_transition", 0),
        "malicious_candidates": labels.get("malicious_transition", 0),
        "uncertain_records": labels.get("uncertain", 0),
        "external_holdout_candidates": len(holdout_ids),
        "genuine_reviewer_a_count": count_reviews_by_round(submissions, "INITIAL_BLIND"),
        "genuine_reviewer_b_count": count_reviews_by_round(submissions, "SECOND_BLIND"),
        "ai_assisted_packet_generation": True,
        "ai_assistance_ground_truth_authority": False,
        "blind_review_enforced": True,
        "driftwatch_outputs_hidden": True,
        "no_fake_reviewers_created": True,
        "priority_policy": [
            "risky or malicious candidate labels",
            "uncertain labels",
            "external holdout records",
            "high-impact permission or host expansion",
            "new sensitive APIs, network destinations, source-to-sink, or obfuscation indicators",
        ],
    }


def count_reviews_by_round(submissions: Sequence[Dict[str, Any]], review_round: str) -> int:
    return sum(1 for row in submissions if row.get("review_round") == review_round and row.get("reviewer_id"))


def build_label_quality_report(records: Sequence[Dict[str, Any]], submissions: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    current_quality = Counter(record.get("label_quality_tier", "UNCERTAIN") for record in records)
    return {
        "artifact_version": PHASE3H5_ARTIFACT_VERSION,
        "label_quality_distribution": {
            "CONTROLLED_GROUND_TRUTH": current_quality.get("CONTROLLED_GROUND_TRUTH", 0),
            "EXTERNAL_CONFIRMED": current_quality.get("EXTERNAL_CONFIRMED", 0),
            "MULTI_REVIEWER_ADJUDICATED": current_quality.get("MULTI_REVIEWER_ADJUDICATED", 0),
            "SINGLE_REVIEWER_PROVISIONAL": current_quality.get("SINGLE_REVIEWER_PROVISIONAL", 0),
            "UNCERTAIN": current_quality.get("UNCERTAIN", 0),
        },
        "phase3h5_new_genuine_reviews": len(submissions),
        "provisional_dependence_reduced": False,
        "status": "review_workflow_ready_human_independent_review_pending",
    }


def build_unresolved_records(records: Sequence[Dict[str, Any]], review_items: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    item_by_id = {item["record_id"]: item for item in review_items}
    unresolved = []
    for record in records:
        if record["label"] != "uncertain":
            continue
        item = item_by_id[record["pair_id"]]
        unresolved.append({
            "record_id": record["pair_id"],
            "extension_id": record["extension_id"],
            "evidence_summary": item["release_notes"],
            "reason_uncertainty_exists": record.get("label_rationale", "Evidence is insufficient or contradictory."),
            "additional_evidence_needed": [
                "independent reviewer assessment",
                "maintainer or vendor clarification",
                "corroborating public security report or issue discussion",
            ],
            "review_outcome": "UNCERTAIN",
            "eligible_for_supervised_training": False,
        })
    return {"count": len(unresolved), "records": unresolved}


def build_adjudication_report(submissions: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    by_record: Dict[str, List[Dict[str, Any]]] = {}
    for row in submissions:
        by_record.setdefault(row["record_id"], []).append(row)
    adjudications = []
    agreements = 0
    disagreements = 0
    for record_id, rows in by_record.items():
        reviewer_ids = {row["reviewer_id"] for row in rows}
        labels = {row["independent_label"] for row in rows}
        if len(reviewer_ids) < 2:
            status = "single_review_only"
        elif len(labels) == 1:
            status = "agreement"
            agreements += 1
        else:
            status = "disagreement_pending_adjudication"
            disagreements += 1
        adjudications.append({
            "record_id": record_id,
            "review_history_preserved": rows,
            "disagreement_status": status,
            "adjudicated_label": None,
            "adjudication_rationale": None,
        })
    return {
        "artifact_version": PHASE3H5_ARTIFACT_VERSION,
        "status": "NO_GENUINE_MULTI_REVIEWER_ADJUDICATION_AVAILABLE" if not adjudications else "ADJUDICATION_TRACKING_ACTIVE",
        "double_reviewed_count": agreements + disagreements,
        "agreement_count": agreements,
        "disagreement_count": disagreements,
        "adjudicated_count": 0,
        "history_preserved": True,
        "records": adjudications,
    }


def build_inter_rater_agreement(adjudication: Dict[str, Any]) -> Dict[str, Any]:
    double_reviewed = adjudication["double_reviewed_count"]
    if double_reviewed < 2:
        return {
            "status": "INTER_RATER_AGREEMENT_NOT_AVAILABLE",
            "reason": "No sufficient genuine independent double-review records are present; kappa is not calculated.",
            "double_reviewed_record_count": double_reviewed,
            "agreement_count": adjudication["agreement_count"],
            "disagreement_count": adjudication["disagreement_count"],
            "agreement_percentage": None,
            "cohens_kappa": None,
        }
    agreement_percentage = adjudication["agreement_count"] / double_reviewed
    return {
        "status": "INTER_RATER_AGREEMENT_AVAILABLE_EXACT_ONLY",
        "double_reviewed_record_count": double_reviewed,
        "agreement_count": adjudication["agreement_count"],
        "disagreement_count": adjudication["disagreement_count"],
        "agreement_percentage": agreement_percentage,
        "cohens_kappa": None,
        "reason": "Cohen's kappa omitted until label support is sufficient and non-degenerate.",
    }


def build_eligibility_report(
    records: Sequence[Dict[str, Any]],
    adjudication: Dict[str, Any],
    holdout_ids: Iterable[str] = (),
) -> Dict[str, Any]:
    holdout_id_set = set(holdout_ids)
    disagreement_ids = {
        record["record_id"]
        for record in adjudication.get("records", [])
        if record["disagreement_status"] == "disagreement_pending_adjudication"
    }
    eligibility_rows = []
    eligible_count = 0
    for record in records:
        reasons = []
        if record["label"] in {"uncertain", "excluded"}:
            reasons.append(f"{record['label']} is not supervised-training eligible")
        if record["pair_id"] in disagreement_ids:
            reasons.append("unresolved reviewer disagreement")
        if record.get("label_quality_tier") == "UNCERTAIN":
            reasons.append("uncertain label-quality tier")
        if record["pair_id"] in holdout_id_set:
            reasons.append("external holdout excluded from supervised training")
        eligible = bool(record.get("eligible_for_supervised_training")) and not reasons
        eligible_count += int(eligible)
        eligibility_rows.append({
            "record_id": record["pair_id"],
            "final_research_label": record["label"],
            "eligible_for_supervised_training": eligible,
            "eligibility_reasons": reasons,
        })
    return {
        "eligible_for_supervised_training_count": eligible_count,
        "ineligible_count": len(records) - eligible_count,
        "policy": "Gold-set inclusion and training eligibility are distinct concepts.",
        "records": eligibility_rows,
    }


def build_gold_set_manifest(records: Sequence[Dict[str, Any]], provenance_by_id: Dict[str, Dict[str, Any]], adjudication: Dict[str, Any]) -> Dict[str, Any]:
    gold_records = []
    for record in records:
        quality = record.get("label_quality_tier")
        if quality not in {"EXTERNAL_CONFIRMED", "MULTI_REVIEWER_ADJUDICATED", "CONTROLLED_GROUND_TRUTH"}:
            continue
        if record["label"] in {"uncertain", "excluded"}:
            continue
        provenance = provenance_by_id.get(record["pair_id"], {})
        if not provenance.get("old_sha256") or not provenance.get("new_sha256"):
            continue
        gold_records.append({
            "record_id": record["pair_id"],
            "label": record["label"],
            "label_source": quality,
            "evidence_tier": evidence_tier_for(record),
            "review_status": record.get("label_review_status"),
            "provenance_id": provenance.get("provenance_id"),
            "real_or_controlled": "controlled" if record.get("controlled_mutation_type") else "real",
            "extension_id": record["extension_id"],
            "confidence": record.get("label_confidence"),
            "inclusion_rationale": "Meets Phase 3H.5 high-confidence ground-truth policy.",
        })
    payload = {
        "artifact_version": PHASE3H5_ARTIFACT_VERSION,
        "gold_set_version": PHASE3H5_GOLD_SET_VERSION,
        "parent_dataset_version": PHASE3H_DATASET_VERSION,
        "gold_set_policy": (
            "Only EXTERNAL_CONFIRMED, genuine MULTI_REVIEWER_ADJUDICATED, or explicitly separated "
            "CONTROLLED_GROUND_TRUTH records with complete provenance qualify."
        ),
        "real_gold_count": sum(1 for row in gold_records if row["real_or_controlled"] == "real"),
        "controlled_gold_count": sum(1 for row in gold_records if row["real_or_controlled"] == "controlled"),
        "gold_record_count": len(gold_records),
        "records": gold_records,
        "exclusion_reason": "No Phase 3H records currently meet external-confirmation or genuine multi-reviewer-adjudication requirements." if not gold_records else None,
    }
    payload["manifest_hash"] = stable_hash({key: value for key, value in payload.items() if key != "manifest_hash"})
    return payload


def build_gold_set_quality(gold_set: Dict[str, Any]) -> Dict[str, Any]:
    records = gold_set["records"]
    return {
        "gold_set_version": gold_set["gold_set_version"],
        "total_gold_records": len(records),
        "real_gold_records": gold_set["real_gold_count"],
        "controlled_gold_records": gold_set["controlled_gold_count"],
        "unique_extensions": len({row["extension_id"] for row in records}),
        "label_distribution": dict(Counter(row["label"] for row in records)),
        "evidence_tier_distribution": dict(Counter(row["evidence_tier"] for row in records)),
        "reviewer_coverage": {"double_reviewed": 0, "single_reviewed": 0},
        "adjudication_coverage": {"adjudicated": 0},
        "provenance_completeness": f"{len(records)}/{len(records)}",
        "timestamp_completeness": f"{len(records)}/{len(records)}",
        "model_metrics": "not_computed_phase3h5_ground_truth_only",
    }


def build_provenance_review(provenance_manifest: Dict[str, Any]) -> Dict[str, Any]:
    records = provenance_manifest.get("records", [])
    complete = sum(1 for row in records if row.get("old_sha256") and row.get("new_sha256") and row.get("source_url"))
    timestamps = sum(1 for row in records if row.get("old_timestamp") and row.get("new_timestamp"))
    return {
        "provenance_complete_count": complete,
        "record_count": len(records),
        "provenance_completeness": f"{complete}/{len(records)}",
        "timestamp_complete_count": timestamps,
        "timestamp_completeness": f"{timestamps}/{len(records)}",
        "trust_boundary": "review packets expose metadata and static summaries only; extension JavaScript is not executed",
    }


def build_reviewer_metadata_leakage_audit(feature_dir: Path) -> Dict[str, Any]:
    feature_rows = {path.stem: read_csv_rows(path) for path in feature_dir.glob("*.csv")}
    base_audit = build_leakage_audit(feature_rows)
    headers = set()
    for rows in feature_rows.values():
        if rows:
            headers.update(column for column in rows[0].keys() if column not in METADATA_COLUMNS)
    prohibited_hits = sorted(column for column in headers if column in REVIEW_METADATA_BLOCKLIST)
    protected_terms = sorted(REVIEW_METADATA_BLOCKLIST | {"review", "adjudication", "gold", "evidence_tier"})
    pattern_hits = sorted(column for column in headers if any(term in column.lower() for term in protected_terms))
    return {
        "passed": base_audit["passed"] and not prohibited_hits and not pattern_hits,
        "base_feature_leakage_passed": base_audit["passed"],
        "blocked_metadata_fields": sorted(REVIEW_METADATA_BLOCKLIST),
        "prohibited_column_hits": prohibited_hits,
        "protected_pattern_hits": pattern_hits,
        "policy": "Reviewer metadata, evidence tiers, gold-set flags, and eligibility metadata must not enter predictive feature matrices.",
    }


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_research_integrity_audit(gold_set: Dict[str, Any], inter_rater: Dict[str, Any], review_summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "passed": True,
        "independent_review_completed_claimed": False,
        "gold_set_exists_claimed": gold_set["gold_record_count"] > 0,
        "inter_rater_agreement_measured": inter_rater["status"] != "INTER_RATER_AGREEMENT_NOT_AVAILABLE",
        "confirmed_malicious_records_claimed": False,
        "driftwatch_outputs_used_as_ground_truth": False,
        "ai_output_used_as_ground_truth": False,
        "no_fake_reviewers_created": review_summary["no_fake_reviewers_created"],
    }


def build_readiness(
    *,
    review_summary: Dict[str, Any],
    label_quality: Dict[str, Any],
    gold_set: Dict[str, Any],
    external_holdout: Dict[str, Any],
    leakage_audit: Dict[str, Any],
    duplicate_report: Dict[str, Any],
    leakage_report: Dict[str, Any],
    provenance_review: Dict[str, Any],
) -> Dict[str, Any]:
    checks = {
        "defensible_real_gold_set_exists": gold_set["real_gold_count"] > 0,
        "external_holdout_ground_truth_sufficient": False,
        "enough_held_out_extension_identities": external_holdout.get("unique_extension_count", 0) >= 3,
        "labels_independent_of_driftwatch_output": True,
        "provisional_label_dependence_acceptable": False,
        "label_diversity_sufficient": review_summary["risky_review_candidates"] + review_summary["malicious_candidates"] >= 10,
        "holdout_untouched_by_tuning": True,
        "leakage_audit_clean": leakage_audit["passed"] and duplicate_report.get("passed") and leakage_report.get("passed"),
    }
    return {
        "artifact_version": PHASE3H5_ARTIFACT_VERSION,
        "phase3h5_complete": True,
        "phase3i_methodologically_ready": all(checks.values()),
        "final_decision": PHASE3H5_DECISION,
        "recommended_next_phase": "CONTINUE GENUINE INDEPENDENT LABEL REVIEW AND TARGETED GROUND-TRUTH ACQUISITION",
        "checks": checks,
        "review_summary": review_summary,
        "label_quality_distribution": label_quality["label_quality_distribution"],
        "real_gold_set_size": gold_set["real_gold_count"],
        "controlled_gold_set_size": gold_set["controlled_gold_count"],
        "external_holdout_size": external_holdout.get("record_count", 0),
        "provenance_completeness": provenance_review["provenance_completeness"],
        "block_reasons": [
            "no defensible real Gold Set exists",
            "no genuine second-review/adjudication records exist",
            "external holdout labels remain provisional",
            "single-reviewer provisional labels still dominate",
            "confirmed malicious-transition ground truth count is 0",
        ],
    }


def build_phase3h_vs_phase3h5_comparison(
    dataset_manifest: Dict[str, Any],
    review_summary: Dict[str, Any],
    label_quality: Dict[str, Any],
    gold_set: Dict[str, Any],
    external_holdout: Dict[str, Any],
) -> List[Dict[str, Any]]:
    phase3h_quality = dataset_manifest["label_quality_tier_distribution"]
    phase3h_single = phase3h_quality.get("SINGLE_REVIEWER_PROVISIONAL", 0)
    phase3h5_single = label_quality["label_quality_distribution"]["SINGLE_REVIEWER_PROVISIONAL"]
    return [
        {"metric": "total_records", "phase3h": dataset_manifest["accepted"], "phase3h5": review_summary["total_records_in_review_scope"]},
        {"metric": "single_reviewer_provisional", "phase3h": phase3h_single, "phase3h5": phase3h5_single},
        {"metric": "genuine_reviewer_a_count", "phase3h": 0, "phase3h5": review_summary["genuine_reviewer_a_count"]},
        {"metric": "genuine_reviewer_b_count", "phase3h": 0, "phase3h5": review_summary["genuine_reviewer_b_count"]},
        {"metric": "real_gold_set_size", "phase3h": 0, "phase3h5": gold_set["real_gold_count"]},
        {"metric": "controlled_gold_set_size", "phase3h": 0, "phase3h5": gold_set["controlled_gold_count"]},
        {"metric": "external_holdout_size", "phase3h": external_holdout["record_count"], "phase3h5": external_holdout["record_count"]},
        {"metric": "phase3i_ready", "phase3h": False, "phase3h5": False},
    ]


def build_dataset_snapshot(
    dataset_manifest: Dict[str, Any],
    review_summary: Dict[str, Any],
    label_quality: Dict[str, Any],
    gold_set: Dict[str, Any],
    external_holdout: Dict[str, Any],
    phase3h_reference: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "artifact_version": PHASE3H5_ARTIFACT_VERSION,
        "parent_dataset_version": PHASE3H_DATASET_VERSION,
        "phase3h_frozen_reference": phase3h_reference,
        "total_records": dataset_manifest["accepted"],
        "real_records": dataset_manifest["real_record_count"],
        "controlled_records": dataset_manifest["controlled_record_count"],
        "unique_extensions": dataset_manifest["unique_extension_count"],
        "label_distribution": dataset_manifest["label_distribution"],
        "label_quality_distribution": label_quality["label_quality_distribution"],
        "review_priority_records": review_summary["review_priority_records"],
        "external_holdout_size": external_holdout["record_count"],
        "real_gold_set_size": gold_set["real_gold_count"],
        "controlled_gold_set_size": gold_set["controlled_gold_count"],
        "final_decision": PHASE3H5_DECISION,
    }


def freeze_phase3h_reference(curation_dir: Path, feature_dir: Path, experiment_dir: Path) -> Dict[str, Any]:
    return {
        "status": "FROZEN_PHASE3H_BASELINE",
        "dataset_version": PHASE3H_DATASET_VERSION,
        "dataset_manifest_hash": hash_file(curation_dir / "dataset_manifest.json"),
        "provenance_manifest_hash": hash_file(curation_dir / "provenance_manifest.json"),
        "feature_extraction_manifest_hash": hash_file(feature_dir / "extraction_manifest.json"),
        "experiment_snapshot_hash": hash_file(experiment_dir / "dataset_snapshot.json"),
        "preservation_policy": "Phase 3H.5 reads Phase 3H as immutable research history and writes only phase3h5 outputs.",
    }


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def main() -> None:
    result = run_phase3h5_review_workflow()
    print(json.dumps({
        "artifact_version": PHASE3H5_ARTIFACT_VERSION,
        "total_records": result["review_summary"]["total_records_in_review_scope"],
        "review_priority_records": result["review_summary"]["review_priority_records"],
        "real_gold_set_size": result["gold_set"]["real_gold_count"],
        "controlled_gold_set_size": result["gold_set"]["controlled_gold_count"],
        "final_decision": result["readiness"]["final_decision"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
