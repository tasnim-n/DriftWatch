from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from driftbench.label_quality import LabelQualityTier
from research.human_review_adjudication import EXPECTED_DISAGREEMENT_IDS
from research.human_review_integration import sha256_bytes, sha256_file, verify_file_sha256
from research.human_review_quality_promotion import (
    DEFAULT_SOURCE_PATHS,
    PROMOTED_TIER,
    PROMOTION_IDS,
    PROMOTION_POLICY_VERSION,
    UNCERTAIN_RECORD_ID,
)
from research.phase3h5 import (
    PHASE3H5_GOLD_SET_VERSION,
    build_gold_set_manifest as build_canonical_gold_set_manifest,
    stable_hash,
)


GOLD_SET_POLICY_VERSION = "driftwatch-human-gold-set-v1"
GOLD_SET_SCHEMA_VERSION = "driftwatch-governed-human-gold-set-v1"
GOLD_SET_VERSION = "driftwatch-human-gold-set-v1"
GOLD_SET_ID_PREFIX = "GOLD1"
CANONICAL_QUALIFYING_TIERS = {
    LabelQualityTier.EXTERNAL_CONFIRMED.value,
    LabelQualityTier.MULTI_REVIEWER_ADJUDICATED.value,
    LabelQualityTier.CONTROLLED_GROUND_TRUTH.value,
}
CANONICAL_EXCLUDED_LABELS = {"uncertain", "excluded"}
QUALIFYING_SEMANTIC_LABELS = {
    "benign_transition",
    "risky_transition",
    "malicious_transition",
}


class HumanReviewGoldSetError(ValueError):
    """Raised when governed Gold Set construction cannot fail closed."""


def _read_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HumanReviewGoldSetError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise HumanReviewGoldSetError(f"JSON object required in {path}")
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HumanReviewGoldSetError(message)


def _canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(raw.encode("utf-8"))


def _records_by_id(payload: Mapping[str, Any], source: str) -> dict[str, dict[str, Any]]:
    records = payload.get("records")
    _require(isinstance(records, list), f"records list missing from {source}")
    result: dict[str, dict[str, Any]] = {}
    for row in records:
        _require(isinstance(row, dict), f"non-object record in {source}")
        record_id = row.get("record_id")
        _require(isinstance(record_id, str) and record_id, f"record_id missing in {source}")
        _require(record_id not in result, f"duplicate record_id {record_id} in {source}")
        result[record_id] = row
    return result


def validate_gold_set_inputs(
    *,
    promotion_root: str | Path,
    phase5f_root: str | Path,
    phase3h_provenance_path: str | Path,
    holdout_manifest_path: str | Path,
    disagreement_path: str | Path,
    canonical_gold_manifest_path: str | Path,
    source_paths: Mapping[str, str | Path] = DEFAULT_SOURCE_PATHS,
    expected_decision_id: str | None = None,
    expected_promotion_ids: Sequence[str] = PROMOTION_IDS,
) -> dict[str, Any]:
    promotion_root = Path(promotion_root)
    phase5f_root = Path(phase5f_root)
    promotion_paths = {
        "promotion_manifest": promotion_root / "promotion_manifest.json",
        "promoted_view": promotion_root / "promoted_label_quality_view.json",
        "readiness": promotion_root / "gold_set_readiness_assessment.json",
        "promotion_summary": promotion_root / "human_validation_governance_summary.json",
        "promotion_provenance": promotion_root / "provenance_manifest.json",
        "promotion_validation": promotion_root / "validation_report.json",
    }
    for name, path in promotion_paths.items():
        _require(path.is_file(), f"required Phase 5G artifact missing: {name}")
    promotion = {name: _read_json(path) for name, path in promotion_paths.items()}
    promotion_hashes = {name: sha256_file(path) for name, path in promotion_paths.items()}
    manifest = promotion["promotion_manifest"]
    view = promotion["promoted_view"]
    readiness = promotion["readiness"]
    validation = promotion["promotion_validation"]
    promotion_provenance = promotion["promotion_provenance"]

    decision_id = manifest.get("decision_id")
    _require(isinstance(decision_id, str) and decision_id.startswith("QPD1::"), "invalid promotion decision ID")
    if expected_decision_id is not None:
        _require(decision_id == expected_decision_id, "promotion decision ID differs")
    _require(manifest.get("promotion_policy_version") == PROMOTION_POLICY_VERSION, "promotion policy version differs")
    _require(manifest.get("gold_set_created") is False, "Phase 5G already created a Gold Set")
    _require(manifest.get("frozen_dataset_modified") is False, "Phase 5G modified frozen data")
    _require(manifest.get("tuning_authorized") is False, "Phase 5G authorized tuning")
    _require(validation.get("status") == "VALIDATED_AND_RECORDED", "Phase 5G validation did not pass")
    _require(validation.get("source_provenance_complete") is True, "Phase 5G source provenance incomplete")
    _require(validation.get("external_holdout_overlap_count") == 0, "Phase 5G reported holdout overlap")
    _require(validation.get("agreed_nine_promoted_count") == 0, "Phase 5G promoted agreement-only records")

    actual_source_hashes: dict[str, str] = {}
    source_hashes = promotion_provenance.get("source_hashes", {})
    _require(set(source_paths) == set(source_hashes), "authoritative source set differs")
    for name in sorted(source_paths):
        actual_source_hashes[name] = verify_file_sha256(
            source_paths[name], source_hashes[name]
        )

    _require(
        promotion_provenance.get("promotion_policy_document_sha256")
        == sha256_file("HUMAN_REVIEW_QUALITY_PROMOTION_POLICY.md"),
        "Phase 5G promotion policy hash differs",
    )
    _require(
        promotion_provenance.get("canonical_label_quality_policy_sha256")
        == sha256_file("driftbench/label_quality.py"),
        "canonical label-quality policy hash differs",
    )

    phase5f_quality_path = phase5f_root / "quality_tier_eligibility_assessment.json"
    phase5f_provenance_path = phase5f_root / "provenance_manifest.json"
    _require(phase5f_quality_path.is_file(), "Phase 5F quality assessment missing")
    _require(phase5f_provenance_path.is_file(), "Phase 5F provenance missing")
    expected_phase5f_hashes = promotion_provenance.get("phase5f_artifact_hashes", {})
    _require(sha256_file(phase5f_quality_path) == expected_phase5f_hashes.get("quality"), "Phase 5F quality hash differs")
    _require(sha256_file(phase5f_provenance_path) == expected_phase5f_hashes.get("provenance"), "Phase 5F provenance hash differs")
    phase5f_quality = _read_json(phase5f_quality_path)
    agreed = phase5f_quality.get("agreed_nine_read_only_assessment", {})
    agreed_rows = _records_by_id(agreed, "Phase 5F agreed-nine assessment")
    _require(len(agreed_rows) == 9, "agreed-nine record set differs")
    _require(agreed.get("records_changed") == 0, "an agreed-nine record changed")
    _require(all(row.get("promotion_performed") is False for row in agreed_rows.values()), "an agreed-nine record was promoted")

    disagreement_path = Path(disagreement_path)
    _require(
        sha256_file(disagreement_path)
        == promotion_provenance.get("disagreement_selection_sha256"),
        "disagreement-selection hash differs",
    )
    disagreement_rows = _records_by_id(_read_json(disagreement_path), "disagreement selection")
    _require(set(disagreement_rows) == set(EXPECTED_DISAGREEMENT_IDS), "disagreement record set differs")

    phase3h_provenance_path = Path(phase3h_provenance_path)
    _require(
        sha256_file(phase3h_provenance_path)
        == promotion_provenance.get("phase3h_provenance_sha256"),
        "Phase 3H provenance hash differs",
    )
    frozen_rows = _records_by_id(_read_json(phase3h_provenance_path), "Phase 3H provenance")
    holdout_manifest_path = Path(holdout_manifest_path)
    _require(
        sha256_file(holdout_manifest_path)
        == promotion_provenance.get("holdout_manifest_sha256"),
        "holdout manifest hash differs",
    )
    holdout_rows = _records_by_id(_read_json(holdout_manifest_path), "external holdout")

    manifest_rows = _records_by_id(manifest, "Phase 5G promotion manifest")
    view_rows = _records_by_id(view, "Phase 5G promoted view")
    readiness_rows = _records_by_id(readiness, "Phase 5G readiness")
    expected_five = set(EXPECTED_DISAGREEMENT_IDS)
    _require(set(manifest_rows) == expected_five, "Phase 5G manifest case set differs")
    _require(set(view_rows) == expected_five, "Phase 5G view case set differs")
    _require(set(readiness_rows) == expected_five, "Phase 5G readiness case set differs")

    candidates: list[dict[str, Any]] = []
    provenance_by_id: dict[str, dict[str, Any]] = {}
    exclusions: list[dict[str, Any]] = []
    for record_id in sorted(expected_five):
        promotion_row = manifest_rows[record_id]
        view_row = view_rows[record_id]
        readiness_row = readiness_rows[record_id]
        frozen = frozen_rows.get(record_id)
        _require(frozen is not None, f"frozen source row missing for {record_id}")
        _require(view_row.get("frozen_row") == frozen, f"frozen row linkage differs for {record_id}")
        _require(view_row.get("frozen_row_sha256") == _canonical_hash(frozen), f"frozen row hash differs for {record_id}")
        _require(promotion_row.get("source_artifact_hashes", {}).get("frozen_row_sha256") == view_row["frozen_row_sha256"], f"promotion frozen-row hash differs for {record_id}")
        final_resolution_path = phase5f_root / "final_resolutions" / f"{record_id}.json"
        _require(final_resolution_path.is_file(), f"Phase 5F final resolution missing for {record_id}")
        _require(
            sha256_file(final_resolution_path)
            == promotion_row.get("source_artifact_hashes", {}).get("final_resolution_sha256"),
            f"Phase 5F final resolution hash differs for {record_id}",
        )
        resolution = _read_json(final_resolution_path)
        _require(resolution.get("final_resolution_status") == "ADJUDICATION_COMPLETE", f"adjudication incomplete for {record_id}")
        _require(
            resolution.get("final_adjudicated_label")
            == promotion_row.get("final_adjudicated_label"),
            f"final adjudicated label differs for {record_id}",
        )
        source_hash_fields = promotion_row.get("source_artifact_hashes", {})
        for key in (
            "reviewer01_submission_sha256",
            "reviewer02_submission_sha256",
            "stage_a_submission_sha256",
            "stage_b_submission_sha256",
            "validated_stage_b_submission_sha256",
        ):
            _require(source_hash_fields.get(key), f"{key} missing for {record_id}")
        overlap = record_id in holdout_rows
        _require(not overlap, f"Gold Set candidate overlaps external holdout: {record_id}")
        qualifies = (
            promotion_row.get("promotion_decision") == "APPROVED"
            and promotion_row.get("target_quality_tier") == PROMOTED_TIER
            and view_row.get("promotion_applied") is True
            and view_row.get("derived_quality_tier") == PROMOTED_TIER
            and readiness_row.get("gold_set_ready_candidate") is True
            and promotion_row.get("final_adjudicated_semantic_label")
            in QUALIFYING_SEMANTIC_LABELS
            and promotion_row.get("provenance_complete") is True
            and not overlap
        )
        if qualifies:
            candidates.append(
                {
                    "pair_id": record_id,
                    "label": promotion_row["final_adjudicated_semantic_label"],
                    "label_quality_tier": promotion_row["target_quality_tier"],
                    "label_source": "multi_analyst_manual_review",
                    "label_review_status": "adjudicated",
                    "label_confidence": resolution.get("adjudication_confidence"),
                    "extension_id": frozen["extension_id"],
                    "controlled_mutation_type": None,
                }
            )
            provenance_by_id[record_id] = {
                "old_sha256": frozen["old_sha256"],
                "new_sha256": frozen["new_sha256"],
                "provenance_id": frozen["provenance_id"],
            }
        else:
            reasons = list(readiness_row.get("non_ready_reasons", []))
            if record_id == UNCERTAIN_RECORD_ID:
                _require(
                    promotion_row.get("final_adjudicated_semantic_label") == "uncertain",
                    "Save Tabbed Images is not uncertain",
                )
                _require(
                    "UNCERTAIN_SEMANTIC_LABEL_EXCLUDED" in reasons,
                    "canonical uncertain exclusion reason missing",
                )
            exclusions.append(
                {
                    "record_id": record_id,
                    "category": "ADJUDICATED_NON_CANDIDATE",
                    "reasons": reasons,
                }
            )

    candidate_ids = [row["pair_id"] for row in candidates]
    _require(len(candidate_ids) == len(set(candidate_ids)), "duplicate Gold Set candidate ID")
    _require(set(candidate_ids) == set(expected_promotion_ids), "mechanically derived Gold Set candidates differ")
    _require(UNCERTAIN_RECORD_ID not in candidate_ids, "uncertain case entered Gold Set candidates")
    _require(not (set(candidate_ids) & set(agreed_rows)), "agreement-only case entered Gold Set candidates")

    canonical_manifest = build_canonical_gold_set_manifest(
        candidates, provenance_by_id, {"records": []}
    )
    canonical_ids = {row["record_id"] for row in canonical_manifest["records"]}
    _require(canonical_ids == set(candidate_ids), "canonical builder membership differs")
    _require(canonical_manifest["gold_record_count"] == len(candidates), "canonical Gold count differs")
    _require(canonical_manifest["gold_set_version"] == PHASE3H5_GOLD_SET_VERSION, "canonical Gold policy version differs")

    canonical_policy_artifact = _read_json(canonical_gold_manifest_path)
    _require(
        canonical_policy_artifact.get("gold_set_version") == PHASE3H5_GOLD_SET_VERSION,
        "canonical Gold policy artifact version differs",
    )
    _require(
        "MULTI_REVIEWER_ADJUDICATED"
        in canonical_policy_artifact.get("gold_set_policy", ""),
        "canonical Gold policy omits promoted tier",
    )
    for record_id in sorted(agreed_rows):
        exclusions.append(
            {
                "record_id": record_id,
                "category": "AGREEMENT_ONLY_NOT_CANONICALLY_PROMOTED",
                "reasons": ["NO_QUALIFYING_CANONICAL_QUALITY_TIER_PROMOTION"],
            }
        )

    return {
        "schema_version": GOLD_SET_SCHEMA_VERSION,
        "canonical_rules": {
            "accepted_quality_tiers": sorted(CANONICAL_QUALIFYING_TIERS),
            "excluded_semantic_labels": sorted(CANONICAL_EXCLUDED_LABELS),
            "required_provenance_fields": ["old_sha256", "new_sha256"],
            "canonical_builder_mutates_sources": False,
            "canonical_builder_internal_holdout_filter": False,
            "governed_wrapper_requires_zero_holdout_overlap": True,
            "governed_wrapper_rejects_duplicates": True,
        },
        "promotion_decision_id": decision_id,
        "promotion_policy_version": PROMOTION_POLICY_VERSION,
        "promotion_artifact_hashes": promotion_hashes,
        "authoritative_source_hashes": actual_source_hashes,
        "phase5f_quality_sha256": sha256_file(phase5f_quality_path),
        "phase5f_provenance_sha256": sha256_file(phase5f_provenance_path),
        "disagreement_selection_sha256": sha256_file(disagreement_path),
        "phase3h_provenance_sha256": sha256_file(phase3h_provenance_path),
        "holdout_manifest_sha256": sha256_file(holdout_manifest_path),
        "canonical_gold_policy_artifact_sha256": sha256_file(
            canonical_gold_manifest_path
        ),
        "canonical_gold_builder_sha256": sha256_file("research/phase3h5.py"),
        "canonical_manifest": canonical_manifest,
        "candidate_records": candidates,
        "provenance_by_id": provenance_by_id,
        "promotion_records": manifest_rows,
        "frozen_records": {record_id: frozen_rows[record_id] for record_id in candidate_ids},
        "exclusions": sorted(exclusions, key=lambda row: row["record_id"]),
        "agreed_nine_record_count": 9,
        "external_holdout_overlap_count": 0,
        "frozen_dataset_modified": False,
    }


def build_gold_set_artifacts(validation: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    candidates = sorted(validation["candidate_records"], key=lambda row: row["pair_id"])
    canonical_by_id = {
        row["record_id"]: row for row in validation["canonical_manifest"]["records"]
    }
    records: list[dict[str, Any]] = []
    for candidate in candidates:
        record_id = candidate["pair_id"]
        promotion = validation["promotion_records"][record_id]
        frozen = validation["frozen_records"][record_id]
        canonical = canonical_by_id[record_id]
        records.append(
            {
                "record_id": record_id,
                "extension_id": frozen["extension_id"],
                "extension_name": frozen.get("extension_name"),
                "repository": frozen.get("repository"),
                "old_version": frozen.get("old_version"),
                "new_version": frozen.get("new_version"),
                "final_semantic_label": candidate["label"],
                "final_human_label": promotion["final_adjudicated_label"],
                "quality_tier": candidate["label_quality_tier"],
                "label_source": candidate["label_source"],
                "adjudication_status": promotion["phase5f_adjudication_status"],
                "review_status": canonical["review_status"],
                "confidence": canonical["confidence"],
                "evidence_tier": canonical["evidence_tier"],
                "promotion_decision": promotion["promotion_decision"],
                "promotion_decision_id": validation["promotion_decision_id"],
                "provenance_id": frozen["provenance_id"],
                "old_sha256": frozen["old_sha256"],
                "new_sha256": frozen["new_sha256"],
                "source_frozen_row_sha256": promotion["source_artifact_hashes"][
                    "frozen_row_sha256"
                ],
                "source_final_resolution_sha256": promotion[
                    "source_artifact_hashes"
                ]["final_resolution_sha256"],
                "source_submission_hashes": {
                    key: value
                    for key, value in promotion["source_artifact_hashes"].items()
                    if "submission_sha256" in key
                },
                "external_holdout_overlap": False,
                "gold_set_policy_version": GOLD_SET_POLICY_VERSION,
                "usage_restrictions_reference": "USAGE_RESTRICTIONS.json",
            }
        )
    membership_basis = {
        "promotion_decision_id": validation["promotion_decision_id"],
        "record_ids": [row["record_id"] for row in records],
        "canonical_manifest_hash": validation["canonical_manifest"]["manifest_hash"],
    }
    gold_set_id = f"{GOLD_SET_ID_PREFIX}::{_canonical_hash(membership_basis)}"
    label_distribution = dict(
        sorted(Counter(row["final_semantic_label"] for row in records).items())
    )
    human_label_distribution = dict(
        sorted(Counter(row["final_human_label"] for row in records).items())
    )
    quality_distribution = dict(
        sorted(Counter(row["quality_tier"] for row in records).items())
    )
    manifest = {
        "schema_version": GOLD_SET_SCHEMA_VERSION,
        "gold_set_version": GOLD_SET_VERSION,
        "gold_set_policy_version": GOLD_SET_POLICY_VERSION,
        "canonical_gold_set_policy_version": PHASE3H5_GOLD_SET_VERSION,
        "gold_set_id": gold_set_id,
        "purpose": "GOVERNED_HIGH_QUALITY_HUMAN_VALIDATION_SUBSET",
        "promotion_decision_id": validation["promotion_decision_id"],
        "record_count": len(records),
        "label_distribution": label_distribution,
        "human_label_distribution": human_label_distribution,
        "quality_tier_distribution": quality_distribution,
        "external_holdout_overlap_count": 0,
        "records": records,
        "usage_restrictions_reference": "USAGE_RESTRICTIONS.json",
        "frozen_dataset_modified": False,
        "training_authorized": False,
        "tuning_authorized": False,
        "non_ground_truth_warning": (
            "This governed validation subset is not malware ground truth and does not establish "
            "maliciousness, safety, prevalence, or population-level performance."
        ),
    }
    manifest["manifest_hash"] = stable_hash(
        {key: value for key, value in manifest.items() if key != "manifest_hash"}
    )
    usage = {
        "schema_version": GOLD_SET_SCHEMA_VERSION,
        "gold_set_version": GOLD_SET_VERSION,
        "policy_version": GOLD_SET_POLICY_VERSION,
        "allowed": [
            "RESEARCH_REPORTING",
            "QUALITATIVE_CASE_ANALYSIS",
            "FUTURE_EVALUATION_UNDER_SEPARATELY_APPROVED_PROTOCOL",
            "REPRODUCIBILITY_AND_AUDIT",
        ],
        "prohibited_without_separate_governed_authorization": [
            "TRAINING",
            "FINE_TUNING",
            "THRESHOLD_SELECTION",
            "RULE_DEVELOPMENT",
            "SCORING_WEIGHT_TUNING",
            "FEATURE_SELECTION",
            "MODEL_SELECTION",
            "HYPERPARAMETER_TUNING",
            "EXTERNAL_HOLDOUT_CONTAMINATION",
        ],
        "training_authorized": False,
        "tuning_authorized": False,
        "external_holdout_use_authorized": False,
        "restriction": "Separate governed authorization is required for any use not explicitly allowed.",
    }
    membership_audit = {
        "schema_version": GOLD_SET_SCHEMA_VERSION,
        "gold_set_id": gold_set_id,
        "promoted_candidates_considered": len(candidates),
        "included_count": len(records),
        "candidate_excluded_count": len(candidates) - len(records),
        "included_record_ids": [row["record_id"] for row in records],
        "candidate_exclusions": [],
        "non_candidate_exclusion_count": len(validation["exclusions"]),
        "non_candidate_exclusions": validation["exclusions"],
        "uncertain_included": False,
        "agreement_only_included_count": 0,
        "external_holdout_overlap_count": 0,
    }
    summary = {
        "schema_version": GOLD_SET_SCHEMA_VERSION,
        "gold_set_version": GOLD_SET_VERSION,
        "gold_set_id": gold_set_id,
        "record_count": len(records),
        "label_distribution": label_distribution,
        "human_label_distribution": human_label_distribution,
        "quality_tier_distribution": quality_distribution,
        "provenance_complete_count": len(records),
        "external_holdout_overlap_count": 0,
        "policy_version": GOLD_SET_POLICY_VERSION,
        "creation_basis": (
            "Independent dual review, governed two-stage adjudication, explicit derived "
            "MULTI_REVIEWER_ADJUDICATED promotion, and canonical Phase 3H.5 qualification."
        ),
        "limitations": [
            "The Gold Set contains only four scoped cases.",
            "All current labels are risky_transition, so the set cannot estimate class-balanced performance.",
            "The distribution is not representative of the browser-extension population.",
            "Gold Set membership is not malware ground truth or training authorization.",
        ],
    }
    provenance = {
        "schema_version": GOLD_SET_SCHEMA_VERSION,
        "gold_set_version": GOLD_SET_VERSION,
        "gold_set_id": gold_set_id,
        "public_safe_no_human_rationale_text": True,
        "chain": [
            "FROZEN_SOURCE_ROW",
            "REVIEWER_01_AND_REVIEWER_02",
            "PHASE5C_AGREEMENT_AND_DISAGREEMENT_SELECTION",
            "STAGE_A",
            "STAGE_B",
            "PHASE5F_FINAL_RESOLUTION",
            "PHASE5G_QUALITY_PROMOTION",
            "PHASE5H_GOLD_SET_INCLUSION",
        ],
        "source_hashes": {
            "authoritative_human_sources": validation[
                "authoritative_source_hashes"
            ],
            "phase5f_quality_sha256": validation["phase5f_quality_sha256"],
            "phase5f_provenance_sha256": validation["phase5f_provenance_sha256"],
            "phase5g_promotion_artifacts": validation[
                "promotion_artifact_hashes"
            ],
            "disagreement_selection_sha256": validation[
                "disagreement_selection_sha256"
            ],
            "phase3h_provenance_sha256": validation[
                "phase3h_provenance_sha256"
            ],
            "holdout_manifest_sha256": validation["holdout_manifest_sha256"],
            "canonical_gold_policy_artifact_sha256": validation[
                "canonical_gold_policy_artifact_sha256"
            ],
            "canonical_gold_builder_sha256": validation[
                "canonical_gold_builder_sha256"
            ],
            "gold_set_policy_document_sha256": sha256_file(
                "HUMAN_REVIEW_GOLD_SET_POLICY.md"
            ),
        },
        "canonical_builder_manifest_hash": validation["canonical_manifest"][
            "manifest_hash"
        ],
        "record_source_hashes": {
            row["record_id"]: {
                "source_frozen_row_sha256": row["source_frozen_row_sha256"],
                "source_final_resolution_sha256": row[
                    "source_final_resolution_sha256"
                ],
                "source_submission_hashes": row["source_submission_hashes"],
            }
            for row in records
        },
        "frozen_dataset_modified": False,
        "promotion_artifacts_modified": False,
    }
    paper = {
        "schema_version": GOLD_SET_SCHEMA_VERSION,
        "gold_set_version": GOLD_SET_VERSION,
        "gold_set_size": len(records),
        "membership_basis": summary["creation_basis"],
        "label_distribution": human_label_distribution,
        "governance_workflow": (
            "Two independent reviewers, disagreement analysis, two-stage adjudication, explicit "
            "quality-tier promotion, and separate canonical Gold Set inclusion audit."
        ),
        "supportable_claims": [
            "DriftWatch constructed a governed four-case Gold Set from browser-extension version transitions that completed independent review, two-stage adjudication, and explicit quality-tier promotion.",
            "All four Gold Set records are adjudicated risky transitions with MULTI_REVIEWER_ADJUDICATED quality and zero external-holdout overlap.",
        ],
        "unsupported_claims": [
            "malware ground truth",
            "model or malware-detection accuracy",
            "sensitivity or specificity",
            "external validation",
            "representative prevalence or population-level performance",
            "safety certification",
        ],
        "limitations": summary["limitations"],
        "paper_modified": False,
    }
    validation_report = {
        "schema_version": GOLD_SET_SCHEMA_VERSION,
        "gold_set_version": GOLD_SET_VERSION,
        "gold_set_id": gold_set_id,
        "status": "VALIDATED_FOR_CREATION",
        "canonical_policy_revalidated": True,
        "promotion_linkage_valid": True,
        "candidate_count": len(candidates),
        "included_count": len(records),
        "candidate_excluded_count": 0,
        "uncertain_excluded": True,
        "agreed_nine_excluded": True,
        "external_holdout_overlap_count": 0,
        "provenance_complete": True,
        "duplicate_record_count": 0,
        "private_human_text_included": False,
        "frozen_dataset_modified": False,
        "phase5g_promotion_modified": False,
        "training_or_tuning_authorized": False,
    }
    return {
        "gold_set_manifest": manifest,
        "USAGE_RESTRICTIONS": usage,
        "membership_audit": membership_audit,
        "gold_set_summary": summary,
        "provenance_manifest": provenance,
        "paper_ready_assessment": paper,
        "validation_report": validation_report,
    }


def write_gold_set_layer(
    output_root: str | Path,
    artifacts: Mapping[str, Mapping[str, Any]],
    *,
    creation_timestamp: str,
    git_commit: str,
) -> dict[str, Any]:
    try:
        datetime.fromisoformat(creation_timestamp.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise HumanReviewGoldSetError("creation timestamp must be ISO-8601") from exc
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=False)
    filenames = {
        "gold_set_manifest": "gold_set_manifest.json",
        "USAGE_RESTRICTIONS": "USAGE_RESTRICTIONS.json",
        "membership_audit": "membership_audit.json",
        "gold_set_summary": "gold_set_summary.json",
        "provenance_manifest": "provenance_manifest.json",
        "paper_ready_assessment": "paper_ready_assessment.json",
        "validation_report": "validation_report.json",
    }
    _require(set(artifacts) == set(filenames), "Gold Set artifact set differs")
    manifest_path = output / filenames["gold_set_manifest"]
    _write_json(manifest_path, artifacts["gold_set_manifest"])
    manifest_file_sha256 = sha256_file(manifest_path)
    checksum_path = output / "gold_set_manifest.sha256"
    checksum_path.write_text(
        f"{manifest_file_sha256}  {manifest_path.name}\n",
        encoding="ascii",
        newline="\n",
    )
    enriched = {key: dict(value) for key, value in artifacts.items()}
    enriched["provenance_manifest"].update(
        {
            "gold_set_manifest_file_sha256": manifest_file_sha256,
            "creation_timestamp": creation_timestamp,
            "generation_git_commit": git_commit,
        }
    )
    enriched["validation_report"].update(
        {
            "status": "VALIDATED_AND_CREATED",
            "gold_set_manifest_file_sha256": manifest_file_sha256,
            "creation_timestamp": creation_timestamp,
            "generation_git_commit": git_commit,
        }
    )
    for key, filename in filenames.items():
        if key == "gold_set_manifest":
            continue
        _write_json(output / filename, enriched[key])
    return {
        "status": "VALIDATED_AND_CREATED",
        "output_root": str(output),
        "gold_set_version": GOLD_SET_VERSION,
        "gold_set_id": artifacts["gold_set_manifest"]["gold_set_id"],
        "record_count": artifacts["gold_set_manifest"]["record_count"],
        "manifest_sha256": manifest_file_sha256,
        "gold_set_package_created": False,
        "training_or_tuning_authorized": False,
        "created_files": sorted([*filenames.values(), checksum_path.name]),
    }


def run_phase5h(
    *,
    promotion_root: str | Path,
    phase5f_root: str | Path,
    phase3h_provenance_path: str | Path,
    holdout_manifest_path: str | Path,
    disagreement_path: str | Path,
    canonical_gold_manifest_path: str | Path,
    output_root: str | Path,
    creation_timestamp: str | None = None,
    git_commit: str = "8b83e2df6f84c070615b7bf81a2dfe3a0f427ac9",
) -> dict[str, Any]:
    validation = validate_gold_set_inputs(
        promotion_root=promotion_root,
        phase5f_root=phase5f_root,
        phase3h_provenance_path=phase3h_provenance_path,
        holdout_manifest_path=holdout_manifest_path,
        disagreement_path=disagreement_path,
        canonical_gold_manifest_path=canonical_gold_manifest_path,
    )
    artifacts = build_gold_set_artifacts(validation)
    timestamp = creation_timestamp or datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    return write_gold_set_layer(
        output_root,
        artifacts,
        creation_timestamp=timestamp,
        git_commit=git_commit,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Construct the versioned governed human-review Gold Set."
    )
    parser.add_argument(
        "--promotion-root",
        default=(
            "artifacts/human_review/quality_promotion/"
            "driftwatch-human-review-quality-promotion-v1"
        ),
    )
    parser.add_argument(
        "--phase5f-root", default="artifacts/human_review/adjudication/final"
    )
    parser.add_argument(
        "--phase3h-provenance-path",
        default="artifacts/driftbench/phase3h/provenance_manifest.json",
    )
    parser.add_argument(
        "--holdout-manifest-path",
        default="artifacts/driftbench/phase3h/external_holdout_manifest.json",
    )
    parser.add_argument(
        "--disagreement-path",
        default="artifacts/human_review/agreement/reviewer01_vs_reviewer02/disagreements.json",
    )
    parser.add_argument(
        "--canonical-gold-manifest-path",
        default="artifacts/driftbench/phase3h5/gold_set_manifest.json",
    )
    parser.add_argument(
        "--output-root",
        default="artifacts/human_review/gold_set/driftwatch-human-gold-set-v1",
    )
    parser.add_argument("--creation-timestamp")
    parser.add_argument(
        "--git-commit", default="8b83e2df6f84c070615b7bf81a2dfe3a0f427ac9"
    )
    args = parser.parse_args()
    print(json.dumps(run_phase5h(**vars(args)), indent=2))


if __name__ == "__main__":
    main()
