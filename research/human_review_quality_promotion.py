from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from driftbench.label_quality import (
    LABEL_QUALITY_TIERS,
    LabelQualityTier,
    infer_label_quality_tier,
)
from research.human_review_adjudication import EXPECTED_DISAGREEMENT_IDS
from research.human_review_final_adjudication import (
    FINAL_ADJUDICATION_SCHEMA_VERSION,
    RAW_STAGE_B_RETURN_SHA256,
    RELEASED_STAGE_B_PACKAGE_SHA256,
)
from research.human_review_integration import (
    RAW_REVIEWER01_SHA256,
    RAW_REVIEWER02_SHA256,
    sha256_bytes,
    sha256_file,
    verify_file_sha256,
)
from research.human_review_stage_b_release import RAW_STAGE_A_SHA256


PROMOTION_POLICY_VERSION = "driftwatch-human-review-quality-promotion-v1"
PROMOTION_SCHEMA_VERSION = "driftwatch-derived-quality-promotion-v1"
PROMOTION_DECISION_PREFIX = "QPD1"
PROMOTED_TIER = LabelQualityTier.MULTI_REVIEWER_ADJUDICATED.value
UNCERTAIN_TIER = LabelQualityTier.UNCERTAIN.value

PROMOTION_IDS = (
    "automaapp_automa_1_29_11_to_1_29_12",
    "bitwarden_clients_browser_v2026_6_1_to_browser_v2026_7_0",
    "browserpass_browserpass_extension_3_10_2_to_3_11_0",
    "duckduckgo_privacy_2026_1_12_to_2026_4_28",
)
UNCERTAIN_RECORD_ID = "save_tabbed_images_0_4_0_to_0_4_1"

DEFAULT_SOURCE_PATHS = {
    "reviewer01_raw_zip": "DriftWatch_Human_Review_Raw_Return_Reviewer01_2026-09-22.zip",
    "reviewer02_raw_zip": "DriftWatch_Human_Review_Raw_Return_Reviewer02_2026-09-22.zip",
    "stage_a_raw_zip": "DriftWatch_Human_Adjudication_StageA_Raw_Return_2026-09-22.zip",
    "stage_b_released_package": "DriftWatch_Human_Adjudication_StageB_Package.zip",
    "stage_b_raw_return": "DriftWatch_Human_Adjudication_StageB_Raw_Return_2026-09-22.zip",
}
DEFAULT_SOURCE_HASHES = {
    "reviewer01_raw_zip": RAW_REVIEWER01_SHA256,
    "reviewer02_raw_zip": RAW_REVIEWER02_SHA256,
    "stage_a_raw_zip": RAW_STAGE_A_SHA256,
    "stage_b_released_package": RELEASED_STAGE_B_PACKAGE_SHA256,
    "stage_b_raw_return": RAW_STAGE_B_RETURN_SHA256,
}


class HumanReviewQualityPromotionError(ValueError):
    """Raised when a governed quality promotion cannot fail closed."""


def _read_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HumanReviewQualityPromotionError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise HumanReviewQualityPromotionError(f"JSON object required in {path}")
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(raw.encode("utf-8"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HumanReviewQualityPromotionError(message)


def _records_by_id(payload: Mapping[str, Any], source: str) -> dict[str, dict[str, Any]]:
    records = payload.get("records")
    _require(isinstance(records, list), f"records list missing from {source}")
    rows: dict[str, dict[str, Any]] = {}
    for row in records:
        _require(isinstance(row, dict), f"non-object record in {source}")
        record_id = row.get("record_id")
        _require(isinstance(record_id, str) and record_id, f"record_id missing in {source}")
        _require(record_id not in rows, f"duplicate record_id {record_id} in {source}")
        rows[record_id] = row
    return rows


def validate_phase5f_promotion_inputs(
    *,
    phase5f_root: str | Path,
    phase3h_provenance_path: str | Path,
    holdout_manifest_path: str | Path,
    disagreement_path: str | Path,
    source_paths: Mapping[str, str | Path] = DEFAULT_SOURCE_PATHS,
    expected_source_hashes: Mapping[str, str] = DEFAULT_SOURCE_HASHES,
    expected_ids: Sequence[str] = EXPECTED_DISAGREEMENT_IDS,
) -> dict[str, Any]:
    root = Path(phase5f_root)
    expected_id_set = set(expected_ids)
    _require(PROMOTED_TIER in LABEL_QUALITY_TIERS, "canonical promoted tier does not exist")
    _require(UNCERTAIN_TIER in LABEL_QUALITY_TIERS, "canonical uncertain tier does not exist")

    source_hashes: dict[str, str] = {}
    _require(set(source_paths) == set(expected_source_hashes), "source path/hash keys differ")
    for name in sorted(source_paths):
        source_hashes[name] = verify_file_sha256(
            source_paths[name], expected_source_hashes[name]
        )

    required_files = {
        "validation": root / "validation_report.json",
        "quality": root / "quality_tier_eligibility_assessment.json",
        "gold": root / "gold_set_eligibility_assessment.json",
        "provenance": root / "provenance_manifest.json",
        "comparison": root / "stage_a_to_stage_b_comparison.json",
        "human_summary": root / "human_validation_summary.json",
    }
    for name, path in required_files.items():
        _require(path.is_file(), f"required Phase 5F artifact missing: {name}")
    payloads = {name: _read_json(path) for name, path in required_files.items()}
    artifact_hashes = {name: sha256_file(path) for name, path in required_files.items()}

    validation = payloads["validation"]
    _require(validation.get("status") == "VALIDATED", "Phase 5F validation did not pass")
    for field in (
        "immutable_package_material_match",
        "stage_a_linkage_valid",
        "evidence_hashes_unchanged",
        "reviewer_opinion_source_linkage_valid",
    ):
        _require(validation.get(field) is True, f"Phase 5F integrity field failed: {field}")
    _require(validation.get("valid_submission_count") == 5, "Phase 5F does not contain 5 valid submissions")
    _require(validation.get("invalid_submission_count") == 0, "Phase 5F contains invalid submissions")
    _require(validation.get("external_holdout_overlap_count") == 0, "Phase 5F reported holdout overlap")
    _require(validation.get("dataset_modified") is False, "Phase 5F modified the dataset")
    _require(validation.get("gold_set_created") is False, "Phase 5F created a Gold Set")

    quality = payloads["quality"]
    _require(set(quality.get("canonical_tiers", [])) == LABEL_QUALITY_TIERS, "Phase 5F canonical tiers differ")
    _require(quality.get("invented_quality_tier") is False, "Phase 5F invented a quality tier")
    _require(quality.get("promotion_performed") is False, "Phase 5F unexpectedly performed promotion")
    quality_rows = _records_by_id(quality, "Phase 5F quality assessment")
    _require(set(quality_rows) == expected_id_set, "Phase 5F quality case set differs")

    provenance = payloads["provenance"]
    _require(provenance.get("schema_version") == FINAL_ADJUDICATION_SCHEMA_VERSION, "Phase 5F provenance schema differs")
    provenance_rows = _records_by_id(provenance, "Phase 5F provenance")
    _require(set(provenance_rows) == expected_id_set, "Phase 5F provenance case set differs")
    source_artifacts = provenance.get("source_artifacts", {})
    for name, digest in source_hashes.items():
        _require(
            source_artifacts.get(name, {}).get("sha256") == digest,
            f"Phase 5F provenance hash differs for {name}",
        )

    disagreement_path = Path(disagreement_path)
    disagreements = _read_json(disagreement_path)
    disagreement_rows = _records_by_id(disagreements, "disagreement selection")
    _require(set(disagreement_rows) == expected_id_set, "disagreement selection differs")
    _require(
        source_artifacts.get("disagreement_selection", {}).get("sha256")
        == sha256_file(disagreement_path),
        "Phase 5F disagreement provenance hash differs",
    )

    frozen_rows = _records_by_id(
        _read_json(phase3h_provenance_path), "Phase 3H provenance manifest"
    )
    _require(expected_id_set <= set(frozen_rows), "a frozen source row is missing")
    holdout_rows = _records_by_id(_read_json(holdout_manifest_path), "external holdout")
    holdout_overlap = sorted(expected_id_set & set(holdout_rows))
    _require(not holdout_overlap, f"adjudication records overlap external holdout: {holdout_overlap}")

    final_resolution_hashes: dict[str, str] = {}
    validated_submission_hashes: dict[str, str] = {}
    considered: list[dict[str, Any]] = []
    for record_id in sorted(expected_ids):
        resolution_path = root / "final_resolutions" / f"{record_id}.json"
        wrapper_path = root / "validated_stage_b_submissions" / f"{record_id}.json"
        _require(resolution_path.is_file(), f"final resolution missing for {record_id}")
        _require(wrapper_path.is_file(), f"validated Stage B wrapper missing for {record_id}")
        resolution_hash = sha256_file(resolution_path)
        wrapper_hash = sha256_file(wrapper_path)
        final_resolution_hashes[record_id] = resolution_hash
        validated_submission_hashes[record_id] = wrapper_hash
        source_record = provenance_rows[record_id]
        _require(
            source_record.get("derived", {}).get("final_resolution_sha256")
            == resolution_hash,
            f"final resolution hash linkage failed for {record_id}",
        )
        _require(
            source_record.get("derived", {}).get("validated_submission_sha256")
            == wrapper_hash,
            f"validated submission hash linkage failed for {record_id}",
        )
        for stage in ("reviewer01", "reviewer02", "stage_a", "stage_b"):
            _require(isinstance(source_record.get(stage), dict), f"{stage} provenance missing for {record_id}")
        _require(source_record["reviewer01"].get("raw_submission_sha256"), f"R1 hash missing for {record_id}")
        _require(source_record["reviewer02"].get("raw_submission_sha256"), f"R2 hash missing for {record_id}")
        _require(source_record["stage_a"].get("raw_submission_sha256"), f"Stage A hash missing for {record_id}")
        _require(source_record["stage_b"].get("raw_submission_sha256"), f"Stage B hash missing for {record_id}")

        resolution = _read_json(resolution_path)
        _require(resolution.get("record_id") == record_id, f"resolution ID mismatch for {record_id}")
        _require(resolution.get("final_resolution_status") == "ADJUDICATION_COMPLETE", f"adjudication incomplete for {record_id}")
        quality_row = quality_rows[record_id]
        final_label = resolution.get("final_adjudicated_label")
        _require(final_label == quality_row.get("final_human_label"), f"final label mismatch for {record_id}")
        semantic_label = quality_row.get("final_semantic_label")
        inferred_tier = infer_label_quality_tier(
            label=semantic_label,
            label_source="multi_analyst_manual_review",
            review_status="adjudicated",
        )
        _require(inferred_tier == quality_row.get("canonical_assessed_tier"), f"canonical tier inference differs for {record_id}")
        eligible = (
            quality_row.get("eligible_for_multi_reviewer_adjudicated") is True
            and quality_row.get("assessment_status") == "ELIGIBLE_FOR_PROMOTION"
            and semantic_label in {"benign_transition", "risky_transition", "malicious_transition"}
            and inferred_tier == PROMOTED_TIER
        )
        frozen = frozen_rows[record_id]
        provenance_complete = all(
            frozen.get(field) for field in ("provenance_id", "old_sha256", "new_sha256")
        )
        _require(provenance_complete, f"frozen provenance incomplete for {record_id}")
        considered.append(
            {
                "record_id": record_id,
                "final_human_label": final_label,
                "final_semantic_label": semantic_label,
                "final_adjudication_status": resolution["final_resolution_status"],
                "frozen_row": frozen,
                "frozen_row_sha256": _canonical_hash(frozen),
                "frozen_quality_tier": quality_row["current_frozen_quality_tier"],
                "frozen_review_status": quality_row["current_frozen_review_status"],
                "phase5f_eligible": eligible,
                "phase5f_assessment_status": quality_row["assessment_status"],
                "canonical_assessed_tier": inferred_tier,
                "provenance_complete": provenance_complete,
                "external_holdout_overlap": False,
                "source_provenance": source_record,
                "final_resolution_sha256": resolution_hash,
                "validated_submission_sha256": wrapper_hash,
            }
        )

    derived_eligible_ids = {
        row["record_id"] for row in considered if row["phase5f_eligible"]
    }
    _require(derived_eligible_ids == set(PROMOTION_IDS), "eligible promotion set is not the governed four")
    uncertain = next(row for row in considered if row["record_id"] == UNCERTAIN_RECORD_ID)
    _require(uncertain["final_human_label"] == "UNCERTAIN", "Save Tabbed Images is not UNCERTAIN")
    _require(uncertain["canonical_assessed_tier"] == UNCERTAIN_TIER, "UNCERTAIN canonical tier differs")
    _require(uncertain["phase5f_eligible"] is False, "UNCERTAIN was marked promotion eligible")

    agreed = quality.get("agreed_nine_read_only_assessment", {})
    _require(agreed.get("record_count") == 9, "agreed-nine assessment count differs")
    _require(agreed.get("records_changed") == 0, "an agreed-nine record was changed")
    _require(agreed.get("new_tier_created") is False, "an agreement-only tier was created")
    _require(all(row.get("promotion_performed") is False for row in agreed.get("records", [])), "an agreed-nine record was promoted")

    return {
        "schema_version": PROMOTION_SCHEMA_VERSION,
        "canonical_tiers": sorted(LABEL_QUALITY_TIERS),
        "canonical_tier_verified": True,
        "source_hashes": source_hashes,
        "phase5f_artifact_hashes": artifact_hashes,
        "phase5f_provenance_sha256": artifact_hashes["provenance"],
        "phase3h_provenance_sha256": sha256_file(phase3h_provenance_path),
        "holdout_manifest_sha256": sha256_file(holdout_manifest_path),
        "disagreement_selection_sha256": sha256_file(disagreement_path),
        "external_holdout_overlap": holdout_overlap,
        "considered_records": considered,
        "promotion_ids": sorted(derived_eligible_ids),
        "uncertain_record_id": UNCERTAIN_RECORD_ID,
        "agreed_nine_record_count": 9,
        "agreed_nine_promoted_count": 0,
        "source_artifacts_modified": False,
        "frozen_dataset_modified": False,
        "gold_set_created": False,
    }


def build_promotion_artifacts(
    validation: Mapping[str, Any], *, decision_timestamp: str
) -> dict[str, dict[str, Any]]:
    try:
        datetime.fromisoformat(decision_timestamp.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise HumanReviewQualityPromotionError("decision timestamp must be ISO-8601") from exc
    _require(validation.get("canonical_tier_verified") is True, "canonical tier was not verified")
    decisions: list[dict[str, Any]] = []
    view_rows: list[dict[str, Any]] = []
    readiness_rows: list[dict[str, Any]] = []
    for source in sorted(validation["considered_records"], key=lambda row: row["record_id"]):
        approved = source["record_id"] in set(PROMOTION_IDS) and source["phase5f_eligible"]
        target_tier = PROMOTED_TIER if approved else UNCERTAIN_TIER
        decision = "APPROVED" if approved else "NOT_QUALIFYING"
        decision_row = {
            "record_id": source["record_id"],
            "frozen_original_label": source["frozen_row"]["label"],
            "frozen_original_quality_tier": source["frozen_quality_tier"],
            "frozen_original_review_status": source["frozen_review_status"],
            "final_adjudicated_label": source["final_human_label"],
            "final_adjudicated_semantic_label": source["final_semantic_label"],
            "phase5f_adjudication_status": source["final_adjudication_status"],
            "target_quality_tier": target_tier,
            "promotion_eligibility": source["phase5f_assessment_status"],
            "promotion_decision": decision,
            "promotion_policy_version": PROMOTION_POLICY_VERSION,
            "decision_timestamp": decision_timestamp,
            "source_artifact_hashes": {
                "frozen_row_sha256": source["frozen_row_sha256"],
                "final_resolution_sha256": source["final_resolution_sha256"],
                "validated_stage_b_submission_sha256": source[
                    "validated_submission_sha256"
                ],
                "reviewer01_submission_sha256": source["source_provenance"][
                    "reviewer01"
                ]["raw_submission_sha256"],
                "reviewer02_submission_sha256": source["source_provenance"][
                    "reviewer02"
                ]["raw_submission_sha256"],
                "stage_a_submission_sha256": source["source_provenance"]["stage_a"][
                    "raw_submission_sha256"
                ],
                "stage_b_submission_sha256": source["source_provenance"]["stage_b"][
                    "raw_submission_sha256"
                ],
            },
            "provenance_complete": source["provenance_complete"],
            "external_holdout_overlap": source["external_holdout_overlap"],
            "gold_set_status": "NOT_CREATED_READINESS_ONLY",
            "frozen_dataset_modified": False,
        }
        decisions.append(decision_row)
        view_rows.append(
            {
                "record_id": source["record_id"],
                "lineage_status": "DERIVED_DOES_NOT_REWRITE_FROZEN_ROW",
                "frozen_row": source["frozen_row"],
                "frozen_row_sha256": source["frozen_row_sha256"],
                "final_adjudicated_semantic_label": source["final_semantic_label"],
                "derived_quality_tier": target_tier,
                "derived_label_source": (
                    "multi_analyst_manual_review" if approved else "adjudicated_uncertain"
                ),
                "derived_review_status": "adjudicated",
                "promotion_applied": approved,
                "promotion_decision": decision,
            }
        )
        ready = (
            approved
            and target_tier == PROMOTED_TIER
            and source["final_semantic_label"]
            in {"benign_transition", "risky_transition", "malicious_transition"}
            and source["provenance_complete"]
            and not source["external_holdout_overlap"]
        )
        reasons: list[str] = []
        if not approved:
            reasons.append("NOT_APPROVED_FOR_DEFINITIVE_QUALITY_PROMOTION")
        if source["final_semantic_label"] == "uncertain":
            reasons.append("UNCERTAIN_SEMANTIC_LABEL_EXCLUDED")
        if not source["provenance_complete"]:
            reasons.append("PROVENANCE_INCOMPLETE")
        if source["external_holdout_overlap"]:
            reasons.append("EXTERNAL_HOLDOUT_FORBIDDEN")
        readiness_rows.append(
            {
                "record_id": source["record_id"],
                "promoted_quality_tier": target_tier if approved else None,
                "semantic_label_qualifies": source["final_semantic_label"]
                in {"benign_transition", "risky_transition", "malicious_transition"},
                "quality_tier_qualifies": approved and target_tier == PROMOTED_TIER,
                "provenance_complete": source["provenance_complete"],
                "external_holdout_overlap": source["external_holdout_overlap"],
                "gold_set_ready_candidate": ready,
                "non_ready_reasons": reasons,
            }
        )

    decision_basis = {
        "policy_version": PROMOTION_POLICY_VERSION,
        "phase5f_provenance_sha256": validation["phase5f_provenance_sha256"],
        "records": [
            {
                "record_id": row["record_id"],
                "promotion_decision": row["promotion_decision"],
                "target_quality_tier": row["target_quality_tier"],
                "final_adjudicated_semantic_label": row[
                    "final_adjudicated_semantic_label"
                ],
            }
            for row in decisions
        ],
    }
    decision_id = f"{PROMOTION_DECISION_PREFIX}::{_canonical_hash(decision_basis)}"
    manifest = {
        "schema_version": PROMOTION_SCHEMA_VERSION,
        "promotion_policy_version": PROMOTION_POLICY_VERSION,
        "decision_id": decision_id,
        "decision_timestamp": decision_timestamp,
        "scope": "FIVE_PHASE5F_FINAL_ADJUDICATION_RECORDS",
        "considered_record_count": len(decisions),
        "approved_promotion_count": sum(
            row["promotion_decision"] == "APPROVED" for row in decisions
        ),
        "not_qualifying_count": sum(
            row["promotion_decision"] == "NOT_QUALIFYING" for row in decisions
        ),
        "target_tier": PROMOTED_TIER,
        "records": decisions,
        "agreed_nine_promoted_count": 0,
        "frozen_dataset_modified": False,
        "gold_set_created": False,
        "tuning_authorized": False,
        "public_safe_no_human_rationale_text": True,
    }
    derived_view = {
        "schema_version": PROMOTION_SCHEMA_VERSION,
        "decision_id": decision_id,
        "promotion_policy_version": PROMOTION_POLICY_VERSION,
        "lineage_rule": (
            "Each row preserves the immutable frozen-row snapshot and separately records the "
            "later adjudicated semantic label and governed derived quality tier."
        ),
        "record_count": len(view_rows),
        "promoted_record_count": sum(row["promotion_applied"] for row in view_rows),
        "records": view_rows,
        "frozen_dataset_modified": False,
    }
    gold_readiness = {
        "schema_version": PROMOTION_SCHEMA_VERSION,
        "decision_id": decision_id,
        "assessment_mode": "READ_ONLY_NO_GOLD_SET_CONSTRUCTION",
        "considered_record_count": len(readiness_rows),
        "ready_candidate_count": sum(
            row["gold_set_ready_candidate"] for row in readiness_rows
        ),
        "non_ready_count": sum(
            not row["gold_set_ready_candidate"] for row in readiness_rows
        ),
        "external_holdout_overlap_count": sum(
            row["external_holdout_overlap"] for row in readiness_rows
        ),
        "records": readiness_rows,
        "gold_set_created": False,
        "required_next_action": "Separate Phase 5H authorization and construction.",
    }
    summary = {
        "schema_version": PROMOTION_SCHEMA_VERSION,
        "decision_id": decision_id,
        "governed_quality_promotions": 4,
        "promoted_final_label_distribution": {"risky_transition": 4},
        "adjudicated_uncertain_not_promoted": 1,
        "agreed_nine_promoted": 0,
        "external_holdout_overlap": 0,
        "frozen_dataset_modified": False,
        "gold_set_created": False,
        "interpretation": (
            "The four promoted RISKY_TRANSITION records warrant elevated manual security-review "
            "attention; promotion does not establish maliciousness."
        ),
    }
    provenance = {
        "schema_version": PROMOTION_SCHEMA_VERSION,
        "decision_id": decision_id,
        "promotion_policy_version": PROMOTION_POLICY_VERSION,
        "public_safe_no_human_rationale_text": True,
        "source_hashes": validation["source_hashes"],
        "phase5f_artifact_hashes": validation["phase5f_artifact_hashes"],
        "phase3h_provenance_sha256": validation["phase3h_provenance_sha256"],
        "holdout_manifest_sha256": validation["holdout_manifest_sha256"],
        "disagreement_selection_sha256": validation[
            "disagreement_selection_sha256"
        ],
        "canonical_label_quality_policy_sha256": sha256_file(
            "driftbench/label_quality.py"
        ),
        "promotion_policy_document_sha256": sha256_file(
            "HUMAN_REVIEW_QUALITY_PROMOTION_POLICY.md"
        ),
        "record_source_hashes": {
            row["record_id"]: row["source_artifact_hashes"] for row in decisions
        },
        "frozen_dataset_modified": False,
        "gold_set_created": False,
    }
    validation_report = {
        "schema_version": PROMOTION_SCHEMA_VERSION,
        "decision_id": decision_id,
        "status": "VALIDATED_AND_RECORDED",
        "canonical_tier_verified": True,
        "considered_record_count": 5,
        "eligible_record_count": 4,
        "approved_record_count": 4,
        "not_qualifying_record_count": 1,
        "uncertain_preserved": True,
        "agreed_nine_promoted_count": 0,
        "external_holdout_overlap_count": 0,
        "source_provenance_complete": True,
        "frozen_dataset_modified": False,
        "gold_set_created": False,
        "tuning_or_scoring_changed": False,
    }
    return {
        "promotion_manifest": manifest,
        "promoted_label_quality_view": derived_view,
        "gold_set_readiness_assessment": gold_readiness,
        "human_validation_governance_summary": summary,
        "provenance_manifest": provenance,
        "validation_report": validation_report,
    }


def write_promotion_layer(
    output_root: str | Path, artifacts: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=False)
    filenames = {
        "promotion_manifest": "promotion_manifest.json",
        "promoted_label_quality_view": "promoted_label_quality_view.json",
        "gold_set_readiness_assessment": "gold_set_readiness_assessment.json",
        "human_validation_governance_summary": "human_validation_governance_summary.json",
        "provenance_manifest": "provenance_manifest.json",
        "validation_report": "validation_report.json",
    }
    _require(set(artifacts) == set(filenames), "promotion artifact set differs")
    for key, filename in filenames.items():
        _write_json(output / filename, artifacts[key])
    return {
        "status": "VALIDATED_AND_RECORDED",
        "output_root": str(output),
        "decision_id": artifacts["promotion_manifest"]["decision_id"],
        "approved_record_count": artifacts["promotion_manifest"][
            "approved_promotion_count"
        ],
        "gold_set_ready_candidate_count": artifacts[
            "gold_set_readiness_assessment"
        ]["ready_candidate_count"],
        "gold_set_created": False,
        "created_files": sorted(filenames.values()),
    }


def run_phase5g(
    *,
    phase5f_root: str | Path,
    phase3h_provenance_path: str | Path,
    holdout_manifest_path: str | Path,
    disagreement_path: str | Path,
    output_root: str | Path,
    decision_timestamp: str | None = None,
) -> dict[str, Any]:
    validation = validate_phase5f_promotion_inputs(
        phase5f_root=phase5f_root,
        phase3h_provenance_path=phase3h_provenance_path,
        holdout_manifest_path=holdout_manifest_path,
        disagreement_path=disagreement_path,
    )
    timestamp = decision_timestamp or datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    artifacts = build_promotion_artifacts(validation, decision_timestamp=timestamp)
    return write_promotion_layer(output_root, artifacts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record governed derived quality-tier promotions after Phase 5F."
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
        "--output-root",
        default=(
            "artifacts/human_review/quality_promotion/"
            "driftwatch-human-review-quality-promotion-v1"
        ),
    )
    parser.add_argument("--decision-timestamp")
    args = parser.parse_args()
    print(json.dumps(run_phase5g(**vars(args)), indent=2))


if __name__ == "__main__":
    main()
