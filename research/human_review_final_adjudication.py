from __future__ import annotations

import argparse
import json
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from driftbench.label_quality import LABEL_QUALITY_TIERS, LabelQualityTier, infer_label_quality_tier
from research.human_review_adjudication import (
    ADJUDICATION_ID_POLICY_VERSION,
    ADJUDICATION_POLICY_VERSION,
    DEFAULT_ADJUDICATOR_ID,
    EXPECTED_DISAGREEMENT_IDS,
    STAGE_A,
    STAGE_B,
    HumanReviewAdjudicationError,
    _evidence_reference_resolves,
    _valid_iso_timestamp,
    derive_adjudication_review_id,
)
from research.human_review_integration import (
    HUMAN_TO_DATASET_LABEL,
    LABEL_MAPPING_VERSION,
    RAW_REVIEWER01_SHA256,
    RAW_REVIEWER02_SHA256,
    REVIEWER01_ID,
    REVIEWER02_ID,
    load_and_validate_reviewer01_archive,
    load_and_validate_reviewer02_archive,
    sha256_bytes,
    sha256_file,
    verify_file_sha256,
)
from research.human_review_stage_b_release import (
    ADJUDICATOR_WORKFLOW_ID,
    EXPECTED_STAGE_A_JUDGMENTS,
    RAW_STAGE_A_SHA256,
    STAGE_A_TIMESTAMP_PROVENANCE,
    STAGE_B_RELEASE_SCHEMA_VERSION,
    load_and_validate_stage_a_return,
)
from research.phase3h5 import ALLOWED_CONFIDENCE, ALLOWED_REVIEW_LABELS


RAW_STAGE_B_RETURN_SHA256 = "F5990ED098DE626A748EFABC4AF452C6994F1683375AB0E0E7E6361E2F00C843"
RELEASED_STAGE_B_PACKAGE_SHA256 = "F4703D89F32502770F428B744401466423F2152CBB1093B50109F7EF928C6C89"
FINAL_ADJUDICATION_SCHEMA_VERSION = "driftwatch-final-human-adjudication-v1"
STAGE_B_TIMESTAMP_PROVENANCE = "UNSPECIFIED_NOT_USED_FOR_REVIEW_DURATION_ANALYSIS"
GOLD_SET_POLICY_VERSION = "phase3h5-gold-set-methodology-v1"

EXPECTED_STAGE_B_JUDGMENTS = {
    "automaapp_automa_1_29_11_to_1_29_12": ("RISKY_TRANSITION", "HIGH"),
    "bitwarden_clients_browser_v2026_6_1_to_browser_v2026_7_0": (
        "RISKY_TRANSITION",
        "HIGH",
    ),
    "browserpass_browserpass_extension_3_10_2_to_3_11_0": (
        "RISKY_TRANSITION",
        "MEDIUM",
    ),
    "duckduckgo_privacy_2026_1_12_to_2026_4_28": (
        "RISKY_TRANSITION",
        "HIGH",
    ),
    "save_tabbed_images_0_4_0_to_0_4_1": ("UNCERTAIN", "MEDIUM"),
}

_STAGE_B_ANSWER_DEFAULTS = {
    "final_adjudicated_label": "",
    "adjudication_confidence": "",
    "adjudication_rationale": "",
    "adjudication_evidence_references": [],
    "initial_label_changed": None,
    "change_reason": "",
    "resolution_basis": "",
    "review_status": "PENDING",
    "review_timestamp": "",
}


def _json_from_bytes(raw: bytes, source: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HumanReviewAdjudicationError(f"invalid JSON in {source}: {exc}") from exc
    if not isinstance(payload, dict):
        raise HumanReviewAdjudicationError(f"JSON object required in {source}")
    return payload


def _read_json(path: str | Path) -> dict[str, Any]:
    return _json_from_bytes(Path(path).read_bytes(), str(path))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _read_zip_files(path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(path, "r") as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            normalized = str(PurePosixPath(info.filename.replace("\\", "/")))
            if normalized in files:
                raise HumanReviewAdjudicationError(
                    f"duplicate normalized ZIP entry {normalized} in {path}"
                )
            files[normalized] = archive.read(info)
    return files


def _expected_package_names(expected_ids: Sequence[str]) -> set[str]:
    return {
        "PACKAGE_MANIFEST.md",
        "REVIEW_INSTRUCTIONS.md",
        *(f"cases/{record_id}.json" for record_id in expected_ids),
        *(f"submissions/{record_id}.json" for record_id in expected_ids),
    }


def _canonical_json_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(raw.encode("utf-8"))


def load_and_validate_stage_b_return(
    raw_zip_path: str | Path,
    *,
    released_package_path: str | Path,
    stage_a_bundle: Mapping[str, Any],
    expected_raw_sha256: str = RAW_STAGE_B_RETURN_SHA256,
    expected_package_sha256: str = RELEASED_STAGE_B_PACKAGE_SHA256,
    expected_ids: Sequence[str] = EXPECTED_DISAGREEMENT_IDS,
    expected_judgments: Mapping[str, tuple[str, str]] = EXPECTED_STAGE_B_JUDGMENTS,
) -> dict[str, Any]:
    raw_zip_path = Path(raw_zip_path)
    released_package_path = Path(released_package_path)
    raw_sha256 = verify_file_sha256(raw_zip_path, expected_raw_sha256)
    package_sha256 = verify_file_sha256(released_package_path, expected_package_sha256)
    returned = _read_zip_files(raw_zip_path)
    released = _read_zip_files(released_package_path)
    expected_names = _expected_package_names(expected_ids)
    if set(returned) != expected_names:
        raise HumanReviewAdjudicationError(
            "Stage B return entries differ from the exact governed package set"
        )
    if set(released) != expected_names:
        raise HumanReviewAdjudicationError(
            "released Stage B package entries differ from the exact governed package set"
        )

    immutable_names = expected_names - {
        f"submissions/{record_id}.json" for record_id in expected_ids
    }
    mutated = sorted(name for name in immutable_names if returned[name] != released[name])
    if mutated:
        raise HumanReviewAdjudicationError(
            f"immutable Stage B package entries changed in the return: {mutated}"
        )

    stage_a_by_id = {record["record_id"]: record for record in stage_a_bundle["records"]}
    expected_id_set = set(expected_ids)
    if set(stage_a_by_id) != expected_id_set:
        raise HumanReviewAdjudicationError("Stage A bundle differs from the governed five")

    records: list[dict[str, Any]] = []
    review_ids: set[str] = set()
    for record_id in sorted(expected_ids):
        case_name = f"cases/{record_id}.json"
        submission_name = f"submissions/{record_id}.json"
        case = _json_from_bytes(returned[case_name], case_name)
        released_submission = _json_from_bytes(released[submission_name], submission_name)
        submission = _json_from_bytes(returned[submission_name], submission_name)
        stage_a = stage_a_by_id[record_id]

        if case.get("record_id") != record_id:
            raise HumanReviewAdjudicationError(f"Stage B case record_id mismatch for {record_id}")
        sections = case.get("sections")
        if not isinstance(sections, Mapping):
            raise HumanReviewAdjudicationError(f"Stage B case sections missing for {record_id}")
        required_sections = {
            "ORIGINAL_BLIND_EVIDENCE",
            "MY_STAGE_A_ASSESSMENT",
            "REVIEWER_A_OPINION",
            "REVIEWER_B_OPINION",
        }
        if set(sections) != required_sections:
            raise HumanReviewAdjudicationError(f"Stage B case sections invalid for {record_id}")
        if sections["ORIGINAL_BLIND_EVIDENCE"] != stage_a["packet"]:
            raise HumanReviewAdjudicationError(
                f"original blind evidence differs from Stage A for {record_id}"
            )
        stage_a_section = sections["MY_STAGE_A_ASSESSMENT"]
        if (
            not isinstance(stage_a_section, Mapping)
            or stage_a_section.get("source_review_id") != stage_a["review_id"]
            or stage_a_section.get("source_submission_sha256") != stage_a["entry_sha256"]
            or stage_a_section.get("assessment") != stage_a["submission"]
        ):
            raise HumanReviewAdjudicationError(
                f"Stage A case linkage differs for {record_id}"
            )

        expected_identity = {
            "review_id": derive_adjudication_review_id(
                DEFAULT_ADJUDICATOR_ID, record_id, STAGE_B
            ),
            "adjudicator_id": DEFAULT_ADJUDICATOR_ID,
            "record_id": record_id,
            "review_round": STAGE_B,
            "stage_a_review_id": derive_adjudication_review_id(
                DEFAULT_ADJUDICATOR_ID, record_id, STAGE_A
            ),
            "stage_a_submission_sha256": stage_a["entry_sha256"],
        }
        for key, value in {**expected_identity, **_STAGE_B_ANSWER_DEFAULTS}.items():
            if released_submission.get(key) != value:
                raise HumanReviewAdjudicationError(
                    f"released Stage B submission template invalid for {record_id}: {key}"
                )
        if set(released_submission) != set(expected_identity) | set(_STAGE_B_ANSWER_DEFAULTS):
            raise HumanReviewAdjudicationError(
                f"released Stage B submission fields changed for {record_id}"
            )
        if set(submission) != set(released_submission):
            raise HumanReviewAdjudicationError(
                f"returned Stage B submission fields changed for {record_id}"
            )
        for key, value in expected_identity.items():
            if submission.get(key) != value or submission.get(key) != released_submission.get(key):
                raise HumanReviewAdjudicationError(
                    f"Stage B identity/linkage mismatch for {record_id}: {key}"
                )
        review_id = submission["review_id"]
        if review_id in review_ids:
            raise HumanReviewAdjudicationError(f"duplicate Stage B review_id {review_id}")
        review_ids.add(review_id)

        label = submission.get("final_adjudicated_label")
        confidence = submission.get("adjudication_confidence")
        if label not in ALLOWED_REVIEW_LABELS:
            raise HumanReviewAdjudicationError(f"invalid final label for {record_id}")
        if confidence not in ALLOWED_CONFIDENCE:
            raise HumanReviewAdjudicationError(f"invalid confidence for {record_id}")
        if (label, confidence) != expected_judgments.get(record_id):
            raise HumanReviewAdjudicationError(
                f"Stage B judgment differs from the expected authoritative result for {record_id}"
            )
        rationale = submission.get("adjudication_rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise HumanReviewAdjudicationError(f"adjudication rationale missing for {record_id}")
        references = submission.get("adjudication_evidence_references")
        blind_evidence = sections["ORIGINAL_BLIND_EVIDENCE"]
        if not isinstance(references, list) or not references:
            raise HumanReviewAdjudicationError(f"evidence references missing for {record_id}")
        if any(not _evidence_reference_resolves(blind_evidence, ref) for ref in references):
            raise HumanReviewAdjudicationError(
                f"an evidence reference does not resolve for {record_id}"
            )
        changed = submission.get("initial_label_changed")
        if not isinstance(changed, bool):
            raise HumanReviewAdjudicationError(
                f"initial_label_changed must be boolean for {record_id}"
            )
        actual_changed = label != stage_a["submission"]["adjudicator_initial_label"]
        if changed != actual_changed:
            raise HumanReviewAdjudicationError(
                f"initial_label_changed disagrees with Stage A comparison for {record_id}"
            )
        change_reason = submission.get("change_reason")
        if not isinstance(change_reason, str) or (changed and not change_reason.strip()):
            raise HumanReviewAdjudicationError(f"change_reason invalid for {record_id}")
        if not changed and change_reason.strip():
            raise HumanReviewAdjudicationError(
                f"change_reason must be blank when the Stage A label is retained for {record_id}"
            )
        resolution_basis = submission.get("resolution_basis")
        if not isinstance(resolution_basis, str) or not resolution_basis.strip():
            raise HumanReviewAdjudicationError(f"resolution_basis missing for {record_id}")
        if submission.get("review_status") != "SUBMITTED":
            raise HumanReviewAdjudicationError(f"review_status invalid for {record_id}")
        if not _valid_iso_timestamp(submission.get("review_timestamp")):
            raise HumanReviewAdjudicationError(f"review_timestamp invalid for {record_id}")

        records.append(
            {
                "record_id": record_id,
                "review_id": review_id,
                "case_entry_name": case_name,
                "case_sha256": sha256_bytes(returned[case_name]),
                "released_case_sha256": sha256_bytes(released[case_name]),
                "released_submission_entry_name": submission_name,
                "released_submission_sha256": sha256_bytes(released[submission_name]),
                "raw_submission_entry_name": submission_name,
                "raw_submission_sha256": sha256_bytes(returned[submission_name]),
                "stage_a_review_id": stage_a["review_id"],
                "stage_a_submission_sha256": stage_a["entry_sha256"],
                "stage_a_packet_sha256": stage_a["packet_sha256"],
                "reviewer_a_opinion_sha256": _canonical_json_hash(
                    sections["REVIEWER_A_OPINION"]
                ),
                "reviewer_b_opinion_sha256": _canonical_json_hash(
                    sections["REVIEWER_B_OPINION"]
                ),
                "timestamp_provenance": STAGE_B_TIMESTAMP_PROVENANCE,
                "submission": submission,
                "case": case,
            }
        )

    return {
        "schema_version": FINAL_ADJUDICATION_SCHEMA_VERSION,
        "raw_source_path": str(raw_zip_path),
        "raw_source_filename": raw_zip_path.name,
        "raw_source_sha256": raw_sha256,
        "released_package_path": str(released_package_path),
        "released_package_filename": released_package_path.name,
        "released_package_sha256": package_sha256,
        "submission_count": len(records),
        "unique_review_id_count": len(review_ids),
        "immutable_entry_count": len(immutable_names),
        "immutable_entries_match": True,
        "case_linkage_valid": True,
        "evidence_hashes_unchanged": True,
        "stage_a_linkage_valid": True,
        "timestamp_provenance": STAGE_B_TIMESTAMP_PROVENANCE,
        "records": records,
    }


def build_stage_a_to_stage_b_comparison(
    stage_a_bundle: Mapping[str, Any], stage_b_bundle: Mapping[str, Any]
) -> dict[str, Any]:
    stage_a = {record["record_id"]: record for record in stage_a_bundle["records"]}
    rows: list[dict[str, Any]] = []
    for record in stage_b_bundle["records"]:
        record_id = record["record_id"]
        a = stage_a[record_id]
        a_submission = a["submission"]
        b_submission = record["submission"]
        changed = (
            a_submission["adjudicator_initial_label"]
            != b_submission["final_adjudicated_label"]
        )
        rows.append(
            {
                "record_id": record_id,
                "stage_a_label": a_submission["adjudicator_initial_label"],
                "stage_a_confidence": a_submission["adjudicator_initial_confidence"],
                "stage_b_final_label": b_submission["final_adjudicated_label"],
                "stage_b_confidence": b_submission["adjudication_confidence"],
                "changed": changed,
                "reported_initial_label_changed": b_submission["initial_label_changed"],
                "change_reason": b_submission["change_reason"],
                "resolution_basis": b_submission["resolution_basis"],
                "stage_a_source_sha256": a["entry_sha256"],
                "stage_b_source_sha256": record["raw_submission_sha256"],
            }
        )
    retained = sum(not row["changed"] for row in rows)
    return {
        "schema_version": FINAL_ADJUDICATION_SCHEMA_VERSION,
        "record_count": len(rows),
        "retained_stage_a_label_count": retained,
        "changed_stage_a_label_count": len(rows) - retained,
        "records": rows,
    }


def validate_reviewer_opinion_source_linkage(
    stage_b_bundle: Mapping[str, Any],
    *,
    reviewer01_bundle: Mapping[str, Any],
    reviewer02_bundle: Mapping[str, Any],
    alias_mapping_path: str | Path,
) -> dict[str, Any]:
    alias_payload = _read_json(alias_mapping_path)
    aliases_by_id = {
        row["record_id"]: row["aliases"] for row in alias_payload.get("records", [])
    }
    sources = {
        REVIEWER01_ID: {
            row["record_id"]: row for row in reviewer01_bundle["records"]
        },
        REVIEWER02_ID: {
            row["record_id"]: row for row in reviewer02_bundle["records"]
        },
    }
    expected_ids = {row["record_id"] for row in stage_b_bundle["records"]}
    if set(aliases_by_id) != expected_ids:
        raise HumanReviewAdjudicationError(
            "private reviewer alias mapping differs from the governed Stage B set"
        )
    rows: list[dict[str, Any]] = []
    for record in stage_b_bundle["records"]:
        record_id = record["record_id"]
        aliases = aliases_by_id[record_id]
        if set(aliases) != {"Reviewer A", "Reviewer B"}:
            raise HumanReviewAdjudicationError(
                f"reviewer alias set invalid for {record_id}"
            )
        row = {"record_id": record_id, "aliases": {}}
        for alias in ("Reviewer A", "Reviewer B"):
            mapping = aliases[alias]
            reviewer_id = mapping.get("reviewer_id")
            if reviewer_id not in sources or record_id not in sources[reviewer_id]:
                raise HumanReviewAdjudicationError(
                    f"reviewer alias source missing for {record_id} {alias}"
                )
            source = sources[reviewer_id][record_id]
            for key in (
                "raw_submission_entry_name",
                "raw_submission_sha256",
                "derived_review_id",
            ):
                if mapping.get(key) != source.get(key):
                    raise HumanReviewAdjudicationError(
                        f"reviewer alias source linkage mismatch for {record_id} {alias}: {key}"
                    )
            submission = source["submission"]
            expected_opinion = {
                "label": submission["independent_label"],
                "confidence": submission["confidence"],
                "rationale": submission["rationale"],
                "evidence_references": submission["evidence_references"],
            }
            actual_opinion = record["case"]["sections"][f"{alias.upper().replace(' ', '_')}_OPINION"]
            if actual_opinion != expected_opinion:
                raise HumanReviewAdjudicationError(
                    f"Stage B opinion is not verbatim from its raw reviewer source for {record_id} {alias}"
                )
            row["aliases"][alias] = {
                "source_submission_sha256": source["raw_submission_sha256"],
                "opinion_material_sha256": _canonical_json_hash(actual_opinion),
            }
        rows.append(row)
    return {
        "status": "VALID",
        "record_count": len(rows),
        "opinion_count": len(rows) * 2,
        "opinion_material_verbatim": True,
        "source_hash_linkage_valid": True,
        "records": rows,
    }


def _phase3h_records(path: str | Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(path)
    return {row["record_id"]: row for row in payload.get("records", [])}


def assess_quality_tier_eligibility(
    comparison: Mapping[str, Any],
    *,
    phase3h_provenance_path: str | Path,
    agreement_comparison_path: str | Path,
) -> dict[str, Any]:
    current = _phase3h_records(phase3h_provenance_path)
    records: list[dict[str, Any]] = []
    for row in comparison["records"]:
        record_id = row["record_id"]
        dataset_row = current[record_id]
        final_label = row["stage_b_final_label"]
        semantic_label = HUMAN_TO_DATASET_LABEL[final_label]
        inferred = infer_label_quality_tier(
            label=semantic_label,
            label_source="multi_analyst_manual_review",
            review_status="adjudicated",
        )
        eligible = inferred == LabelQualityTier.MULTI_REVIEWER_ADJUDICATED.value
        records.append(
            {
                "record_id": record_id,
                "final_human_label": final_label,
                "final_semantic_label": semantic_label,
                "current_frozen_dataset_label": dataset_row["label"],
                "current_frozen_quality_tier": dataset_row["label_quality"],
                "current_frozen_review_status": dataset_row["review_status"],
                "canonical_assessed_tier": inferred,
                "eligible_for_multi_reviewer_adjudicated": eligible,
                "assessment_status": (
                    "ELIGIBLE_FOR_PROMOTION"
                    if eligible
                    else "NOT_ELIGIBLE_SEMANTIC_LABEL_UNCERTAIN"
                ),
                "promotion_performed": False,
                "dataset_modified": False,
                "review_quality": "TWO_REVIEWER_INDEPENDENT_REVIEW_PLUS_TWO_STAGE_ADJUDICATION_COMPLETE",
                "provenance_quality": "COMPLETE",
            }
        )

    agreement = _read_json(agreement_comparison_path)
    agreed_records: list[dict[str, Any]] = []
    for row in agreement.get("records", []):
        if not row.get("exact_match"):
            continue
        dataset_row = current[row["record_id"]]
        current_tier = dataset_row["label_quality"]
        already_qualifying = current_tier in {
            LabelQualityTier.MULTI_REVIEWER_ADJUDICATED.value,
            LabelQualityTier.EXTERNAL_CONFIRMED.value,
            LabelQualityTier.CONTROLLED_GROUND_TRUTH.value,
        }
        agreed_records.append(
            {
                "record_id": row["record_id"],
                "reviewer_agreed_label": row["reviewer01_original_label"],
                "current_frozen_quality_tier": current_tier,
                "qualifies_under_current_canonical_tier": already_qualifying,
                "assessment": (
                    "ALREADY_QUALIFYING_UNDER_EXISTING_TIER"
                    if already_qualifying
                    else "FUTURE_GOVERNED_POLICY_CHANGE_OR_ADDITIONAL_ADJUDICATION_REQUIRED"
                ),
                "promotion_performed": False,
                "dataset_modified": False,
            }
        )

    return {
        "schema_version": FINAL_ADJUDICATION_SCHEMA_VERSION,
        "canonical_tiers": sorted(LABEL_QUALITY_TIERS),
        "canonical_policy_source": "driftbench/label_quality.py",
        "invented_quality_tier": False,
        "promotion_performed": False,
        "dataset_modified": False,
        "adjudicated_record_count": len(records),
        "eligible_for_promotion_count": sum(
            row["eligible_for_multi_reviewer_adjudicated"] for row in records
        ),
        "records": records,
        "agreed_nine_read_only_assessment": {
            "record_count": len(agreed_records),
            "records_changed": 0,
            "new_tier_created": False,
            "records": agreed_records,
        },
    }


def assess_gold_set_eligibility(
    quality_assessment: Mapping[str, Any],
    *,
    phase3h_provenance_path: str | Path,
    holdout_manifest_path: str | Path,
    gold_manifest_path: str | Path,
) -> dict[str, Any]:
    provenance = _phase3h_records(phase3h_provenance_path)
    holdout = _read_json(holdout_manifest_path)
    holdout_ids = {row["record_id"] for row in holdout.get("records", [])}
    gold_policy = _read_json(gold_manifest_path)
    rows: list[dict[str, Any]] = []
    for quality in quality_assessment["records"]:
        record_id = quality["record_id"]
        source = provenance[record_id]
        provenance_complete = all(
            source.get(field) for field in ("old_sha256", "new_sha256", "provenance_id")
        )
        holdout_overlap = record_id in holdout_ids
        label_eligible = quality["final_semantic_label"] in {
            "benign_transition",
            "risky_transition",
            "malicious_transition",
        }
        promotion_eligible = quality["eligible_for_multi_reviewer_adjudicated"]
        candidate = (
            label_eligible and promotion_eligible and provenance_complete and not holdout_overlap
        )
        reasons: list[str] = []
        if not label_eligible:
            reasons.append("SEMANTIC_LABEL_UNCERTAIN_EXCLUDED_BY_GOLD_SET_POLICY")
        if not provenance_complete:
            reasons.append("PROVENANCE_INCOMPLETE")
        if holdout_overlap:
            reasons.append("EXTERNAL_HOLDOUT_FORBIDDEN")
        if not promotion_eligible and label_eligible:
            reasons.append("QUALITY_TIER_NOT_ELIGIBLE")
        rows.append(
            {
                "record_id": record_id,
                "final_semantic_label": quality["final_semantic_label"],
                "current_quality_tier": quality["current_frozen_quality_tier"],
                "quality_tier_eligibility": quality["assessment_status"],
                "provenance_complete": provenance_complete,
                "external_holdout_overlap": holdout_overlap,
                "policy_qualification": (
                    "ELIGIBLE_CANDIDATE_AFTER_EXPLICIT_QUALITY_TIER_PROMOTION"
                    if candidate
                    else "NOT_ELIGIBLE"
                ),
                "gold_set_label_eligible": candidate,
                "currently_gold_eligible": False,
                "exclusion_reasons": reasons,
                "old_sha256": source.get("old_sha256"),
                "new_sha256": source.get("new_sha256"),
            }
        )
    return {
        "schema_version": FINAL_ADJUDICATION_SCHEMA_VERSION,
        "gold_set_policy_version": gold_policy["gold_set_version"],
        "gold_set_policy": gold_policy["gold_set_policy"],
        "eligible_candidate_count": sum(row["gold_set_label_eligible"] for row in rows),
        "noneligible_count": sum(not row["gold_set_label_eligible"] for row in rows),
        "uncertain_exclusion_count": sum(
            row["final_semantic_label"] == "uncertain" for row in rows
        ),
        "external_holdout_overlap_count": sum(row["external_holdout_overlap"] for row in rows),
        "gold_set_created": False,
        "dataset_modified": False,
        "required_explicit_next_action": (
            "A separate governed action must explicitly promote qualifying records, revalidate "
            "policy and holdout exclusion, and construct any Gold Set."
        ),
        "records": rows,
    }


def _artifact_ref(path: str | Path) -> dict[str, str]:
    path = Path(path)
    return {"path": str(path), "sha256": sha256_file(path)}


def write_final_adjudication_layer(
    *,
    output_root: str | Path,
    stage_a_bundle: Mapping[str, Any],
    stage_b_bundle: Mapping[str, Any],
    comparison: Mapping[str, Any],
    quality_assessment: Mapping[str, Any],
    gold_assessment: Mapping[str, Any],
    reviewer01_bundle: Mapping[str, Any],
    reviewer02_bundle: Mapping[str, Any],
    agreement_root: str | Path,
    phase3h_provenance_path: str | Path,
    holdout_manifest_path: str | Path,
    gold_manifest_path: str | Path,
) -> dict[str, Any]:
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=False)
    validated_dir = output / "validated_stage_b_submissions"
    resolution_dir = output / "final_resolutions"
    validated_dir.mkdir()
    resolution_dir.mkdir()
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    stage_a_by_id = {row["record_id"]: row for row in stage_a_bundle["records"]}
    r1_by_id = {row["record_id"]: row for row in reviewer01_bundle["records"]}
    r2_by_id = {row["record_id"]: row for row in reviewer02_bundle["records"]}
    quality_by_id = {row["record_id"]: row for row in quality_assessment["records"]}
    gold_by_id = {row["record_id"]: row for row in gold_assessment["records"]}
    comparison_by_id = {row["record_id"]: row for row in comparison["records"]}

    resolution_paths: dict[str, Path] = {}
    validated_paths: dict[str, Path] = {}
    for record in stage_b_bundle["records"]:
        record_id = record["record_id"]
        wrapper = {
            "schema_version": FINAL_ADJUDICATION_SCHEMA_VERSION,
            "validation_status": "VALIDATED_AUTHORITATIVE_STAGE_B",
            "privacy_classification": "KEEP_LOCAL_PRIVATE_HUMAN_TEXT",
            "policy_version": ADJUDICATION_POLICY_VERSION,
            "review_id_policy_version": ADJUDICATION_ID_POLICY_VERSION,
            "raw_source_filename": stage_b_bundle["raw_source_filename"],
            "raw_source_sha256": stage_b_bundle["raw_source_sha256"],
            "raw_entry_name": record["raw_submission_entry_name"],
            "raw_entry_sha256": record["raw_submission_sha256"],
            "released_case_sha256": record["released_case_sha256"],
            "released_submission_sha256": record["released_submission_sha256"],
            "timestamp_provenance": STAGE_B_TIMESTAMP_PROVENANCE,
            "original_submission": record["submission"],
        }
        validated_path = validated_dir / f"{record_id}.json"
        _write_json(validated_path, wrapper)
        validated_paths[record_id] = validated_path

        resolution = {
            "schema_version": FINAL_ADJUDICATION_SCHEMA_VERSION,
            "record_id": record_id,
            "final_resolution_status": "ADJUDICATION_COMPLETE",
            "final_adjudicated_label": record["submission"]["final_adjudicated_label"],
            "adjudication_confidence": record["submission"]["adjudication_confidence"],
            "adjudication_rationale": record["submission"]["adjudication_rationale"],
            "adjudication_evidence_references": record["submission"][
                "adjudication_evidence_references"
            ],
            "stage_a_to_stage_b": comparison_by_id[record_id],
            "quality_tier_assessment": quality_by_id[record_id],
            "gold_set_eligibility_assessment": gold_by_id[record_id],
            "interpretation": (
                "RISKY_TRANSITION warrants elevated manual security-review attention and "
                "does not establish maliciousness."
                if record["submission"]["final_adjudicated_label"] == "RISKY_TRANSITION"
                else "UNCERTAIN is preserved as a non-definitive semantic outcome."
            ),
            "dataset_modified": False,
            "gold_set_created": False,
            "privacy_classification": "KEEP_LOCAL_PRIVATE_HUMAN_TEXT",
        }
        resolution_path = resolution_dir / f"{record_id}.json"
        _write_json(resolution_path, resolution)
        resolution_paths[record_id] = resolution_path

    _write_json(output / "stage_a_to_stage_b_comparison.json", comparison)
    _write_json(output / "quality_tier_eligibility_assessment.json", quality_assessment)
    _write_json(output / "gold_set_eligibility_assessment.json", gold_assessment)

    label_counts = Counter(
        row["submission"]["final_adjudicated_label"] for row in stage_b_bundle["records"]
    )
    human_summary = {
        "schema_version": FINAL_ADJUDICATION_SCHEMA_VERSION,
        "original_blind_cases": 14,
        "independent_reviewers": 2,
        "exact_human_human_agreements": 9,
        "human_human_disagreements": 5,
        "percent_exact_agreement": 64.28571428571429,
        "percent_exact_agreement_display": "64.29%",
        "nominal_unweighted_cohens_kappa": 0.3396226415094341,
        "disagreement_cases_entering_adjudication": 5,
        "stage_a_complete": True,
        "stage_b_complete": True,
        "stage_a_labels_changed_in_stage_b": comparison["changed_stage_a_label_count"],
        "final_adjudicated_benign": label_counts.get("BENIGN_TRANSITION", 0),
        "final_adjudicated_risky": label_counts.get("RISKY_TRANSITION", 0),
        "final_adjudicated_uncertain": label_counts.get("UNCERTAIN", 0),
        "gold_set_created": False,
        "limitations": [
            "The reviewed set contains only 14 scoped cases.",
            "Cohen's kappa is sensitive to the concentrated and imbalanced category marginals.",
            "No independent ground truth exists, so these results do not establish accuracy.",
        ],
    }
    _write_json(output / "human_validation_summary.json", human_summary)

    raw_metadata = {
        "schema_version": FINAL_ADJUDICATION_SCHEMA_VERSION,
        "generated_at": generated_at,
        "sources": {
            "reviewer01": {
                "filename": Path(reviewer01_bundle["raw_zip_path"]).name,
                "sha256": reviewer01_bundle["raw_source_sha256"],
            },
            "reviewer02": {
                "filename": Path(reviewer02_bundle["raw_zip_path"]).name,
                "sha256": reviewer02_bundle["raw_source_sha256"],
            },
            "stage_a": {
                "filename": stage_a_bundle["raw_source_filename"],
                "sha256": stage_a_bundle["raw_source_sha256"],
                "timestamp_provenance": STAGE_A_TIMESTAMP_PROVENANCE,
            },
            "stage_b_released_package": {
                "filename": stage_b_bundle["released_package_filename"],
                "sha256": stage_b_bundle["released_package_sha256"],
            },
            "stage_b_return": {
                "filename": stage_b_bundle["raw_source_filename"],
                "sha256": stage_b_bundle["raw_source_sha256"],
                "timestamp_provenance": STAGE_B_TIMESTAMP_PROVENANCE,
            },
        },
        "source_artifacts_modified": False,
    }
    _write_json(output / "RAW_SOURCE_METADATA.json", raw_metadata)

    paper_ready = {
        "schema_version": FINAL_ADJUDICATION_SCHEMA_VERSION,
        "supported_claims": [
            "Two independent human reviewers reviewed the same 14 blind cases.",
            "Exact agreement was 9/14 (64.29%).",
            "Unweighted nominal Cohen's kappa was approximately 0.34.",
            "Five disagreements underwent governed two-stage adjudication.",
            "Stage A was completed before de-identified prior opinions were exposed in Stage B.",
            "The independent adjudicator produced four final RISKY_TRANSITION outcomes and one final UNCERTAIN outcome.",
        ],
        "unsupported_claims": [
            "model accuracy or malware-detection accuracy",
            "sensitivity or specificity",
            "external validation or population-level generalization",
            "objective ground truth",
            "Gold Set completion",
        ],
        "paper_rewritten": False,
    }
    _write_json(output / "paper_ready_results_assessment.json", paper_ready)

    agreement_root = Path(agreement_root)
    provenance_records: list[dict[str, Any]] = []
    for record in stage_b_bundle["records"]:
        record_id = record["record_id"]
        r1 = r1_by_id[record_id]
        r2 = r2_by_id[record_id]
        a = stage_a_by_id[record_id]
        provenance_records.append(
            {
                "record_id": record_id,
                "reviewer01": {
                    "derived_review_id": r1["derived_review_id"],
                    "raw_submission_entry_name": r1["raw_submission_entry_name"],
                    "raw_submission_sha256": r1["raw_submission_sha256"],
                    "packet_sha256": r1["raw_packet_sha256"],
                },
                "reviewer02": {
                    "derived_review_id": r2["derived_review_id"],
                    "raw_submission_entry_name": r2["raw_submission_entry_name"],
                    "raw_submission_sha256": r2["raw_submission_sha256"],
                    "packet_sha256": r2["packet_source_sha256"],
                },
                "stage_a": {
                    "review_id": a["review_id"],
                    "raw_submission_entry_name": a["entry_name"],
                    "raw_submission_sha256": a["entry_sha256"],
                    "packet_sha256": a["packet_sha256"],
                },
                "stage_b": {
                    "review_id": record["review_id"],
                    "released_case_sha256": record["released_case_sha256"],
                    "released_blank_submission_sha256": record[
                        "released_submission_sha256"
                    ],
                    "raw_submission_sha256": record["raw_submission_sha256"],
                    "reviewer_a_opinion_sha256": record["reviewer_a_opinion_sha256"],
                    "reviewer_b_opinion_sha256": record["reviewer_b_opinion_sha256"],
                },
                "derived": {
                    "validated_submission_sha256": sha256_file(validated_paths[record_id]),
                    "final_resolution_sha256": sha256_file(resolution_paths[record_id]),
                },
            }
        )
    provenance_manifest = {
        "schema_version": FINAL_ADJUDICATION_SCHEMA_VERSION,
        "generated_at": generated_at,
        "public_safe_no_human_rationale_text": True,
        "chain": [
            "REVIEWER_01",
            "REVIEWER_02",
            "AGREEMENT_ANALYSIS",
            "DISAGREEMENT_SELECTION",
            "STAGE_A",
            "STAGE_B",
            "FINAL_RESOLUTION",
            "QUALITY_TIER_ASSESSMENT",
            "GOLD_SET_ELIGIBILITY_ASSESSMENT",
        ],
        "source_artifacts": {
            "reviewer01_raw_zip": raw_metadata["sources"]["reviewer01"],
            "reviewer02_raw_zip": raw_metadata["sources"]["reviewer02"],
            "agreement_summary": _artifact_ref(agreement_root / "agreement_summary.json"),
            "agreement_comparison": _artifact_ref(agreement_root / "comparison_table.json"),
            "disagreement_selection": _artifact_ref(agreement_root / "disagreements.json"),
            "stage_a_raw_zip": raw_metadata["sources"]["stage_a"],
            "stage_b_released_package": raw_metadata["sources"]["stage_b_released_package"],
            "stage_b_raw_return": raw_metadata["sources"]["stage_b_return"],
        },
        "policy_versions": {
            "label_mapping": LABEL_MAPPING_VERSION,
            "adjudication": ADJUDICATION_POLICY_VERSION,
            "adjudication_review_id": ADJUDICATION_ID_POLICY_VERSION,
            "stage_b_release_schema": STAGE_B_RELEASE_SCHEMA_VERSION,
            "gold_set": GOLD_SET_POLICY_VERSION,
            "label_quality_policy_sha256": sha256_file("driftbench/label_quality.py"),
            "gold_set_policy_artifact_sha256": sha256_file(gold_manifest_path),
        },
        "protected_research_sources": {
            "phase3h_provenance": _artifact_ref(phase3h_provenance_path),
            "external_holdout_manifest": _artifact_ref(holdout_manifest_path),
        },
        "record_count": len(provenance_records),
        "records": provenance_records,
        "dataset_modified": False,
        "gold_set_created": False,
    }
    _write_json(output / "provenance_manifest.json", provenance_manifest)

    validation_report = {
        "schema_version": FINAL_ADJUDICATION_SCHEMA_VERSION,
        "status": "VALIDATED",
        "expected_submission_count": 5,
        "valid_submission_count": stage_b_bundle["submission_count"],
        "invalid_submission_count": 0,
        "missing_submission_count": 0,
        "extra_submission_count": 0,
        "unique_review_id_count": stage_b_bundle["unique_review_id_count"],
        "immutable_package_material_match": stage_b_bundle["immutable_entries_match"],
        "stage_a_linkage_valid": stage_b_bundle["stage_a_linkage_valid"],
        "evidence_hashes_unchanged": stage_b_bundle["evidence_hashes_unchanged"],
        "reviewer_opinion_source_linkage_valid": stage_b_bundle[
            "reviewer_opinion_source_linkage_valid"
        ],
        "retained_stage_a_label_count": comparison["retained_stage_a_label_count"],
        "changed_stage_a_label_count": comparison["changed_stage_a_label_count"],
        "external_holdout_overlap_count": gold_assessment[
            "external_holdout_overlap_count"
        ],
        "source_artifacts_modified": False,
        "dataset_modified": False,
        "gold_set_created": False,
    }
    _write_json(output / "validation_report.json", validation_report)

    return {
        "status": "VALIDATED",
        "output_root": str(output),
        "record_count": 5,
        "final_label_counts": dict(sorted(label_counts.items())),
        "validation_report": validation_report,
        "human_validation_summary": human_summary,
        "paper_ready_results_assessment": paper_ready,
        "created_files": sorted(
            str(path.relative_to(output)) for path in output.rglob("*") if path.is_file()
        ),
    }


def run_phase5f(
    *,
    reviewer01_zip: str | Path,
    reviewer02_zip: str | Path,
    reviewer02_packet_root: str | Path,
    stage_a_raw_zip: str | Path,
    phase5d_workspace: str | Path,
    stage_b_package_zip: str | Path,
    stage_b_raw_zip: str | Path,
    output_root: str | Path,
    agreement_root: str | Path,
    phase3h_provenance_path: str | Path,
    holdout_manifest_path: str | Path,
    gold_manifest_path: str | Path,
) -> dict[str, Any]:
    stage_a_bundle = load_and_validate_stage_a_return(
        stage_a_raw_zip,
        adjudicator_workspace=phase5d_workspace,
        expected_sha256=RAW_STAGE_A_SHA256,
        expected_judgments=EXPECTED_STAGE_A_JUDGMENTS,
    )
    reviewer01_bundle = load_and_validate_reviewer01_archive(
        reviewer01_zip, expected_sha256=RAW_REVIEWER01_SHA256
    )
    reviewer02_bundle = load_and_validate_reviewer02_archive(
        reviewer02_zip,
        packet_root=reviewer02_packet_root,
        expected_sha256=RAW_REVIEWER02_SHA256,
    )
    stage_b_bundle = load_and_validate_stage_b_return(
        stage_b_raw_zip,
        released_package_path=stage_b_package_zip,
        stage_a_bundle=stage_a_bundle,
    )
    opinion_linkage = validate_reviewer_opinion_source_linkage(
        stage_b_bundle,
        reviewer01_bundle=reviewer01_bundle,
        reviewer02_bundle=reviewer02_bundle,
        alias_mapping_path=Path(phase5d_workspace)
        / "metadata"
        / "reviewer_alias_mapping.json",
    )
    stage_b_bundle["reviewer_opinion_source_linkage_valid"] = (
        opinion_linkage["status"] == "VALID"
    )
    comparison = build_stage_a_to_stage_b_comparison(stage_a_bundle, stage_b_bundle)
    quality = assess_quality_tier_eligibility(
        comparison,
        phase3h_provenance_path=phase3h_provenance_path,
        agreement_comparison_path=Path(agreement_root) / "comparison_table.json",
    )
    gold = assess_gold_set_eligibility(
        quality,
        phase3h_provenance_path=phase3h_provenance_path,
        holdout_manifest_path=holdout_manifest_path,
        gold_manifest_path=gold_manifest_path,
    )
    return write_final_adjudication_layer(
        output_root=output_root,
        stage_a_bundle=stage_a_bundle,
        stage_b_bundle=stage_b_bundle,
        comparison=comparison,
        quality_assessment=quality,
        gold_assessment=gold,
        reviewer01_bundle=reviewer01_bundle,
        reviewer02_bundle=reviewer02_bundle,
        agreement_root=agreement_root,
        phase3h_provenance_path=phase3h_provenance_path,
        holdout_manifest_path=holdout_manifest_path,
        gold_manifest_path=gold_manifest_path,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate Stage B and create governed final adjudication assessments."
    )
    parser.add_argument(
        "--reviewer01-zip",
        default="DriftWatch_Human_Review_Raw_Return_Reviewer01_2026-09-22.zip",
    )
    parser.add_argument(
        "--reviewer02-zip",
        default="DriftWatch_Human_Review_Raw_Return_Reviewer02_2026-09-22.zip",
    )
    parser.add_argument("--reviewer02-packet-root", default="reviewer_human_02/packets")
    parser.add_argument(
        "--stage-a-raw-zip",
        default="DriftWatch_Human_Adjudication_StageA_Raw_Return_2026-09-22.zip",
    )
    parser.add_argument("--phase5d-workspace", default="reviewer_human_adjudicator")
    parser.add_argument(
        "--stage-b-package-zip",
        default="DriftWatch_Human_Adjudication_StageB_Package.zip",
    )
    parser.add_argument(
        "--stage-b-raw-zip",
        default="DriftWatch_Human_Adjudication_StageB_Raw_Return_2026-09-22.zip",
    )
    parser.add_argument(
        "--output-root", default="artifacts/human_review/adjudication/final"
    )
    parser.add_argument(
        "--agreement-root",
        default="artifacts/human_review/agreement/reviewer01_vs_reviewer02",
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
        "--gold-manifest-path",
        default="artifacts/driftbench/phase3h5/gold_set_manifest.json",
    )
    args = parser.parse_args()
    result = run_phase5f(**vars(args))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
