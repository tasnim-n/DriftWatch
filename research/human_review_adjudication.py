from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from research.human_review_agreement import build_agreement_analysis
from research.human_review_integration import (
    FORBIDDEN_PACKET_KEYS,
    RAW_REVIEWER01_SHA256,
    RAW_REVIEWER02_SHA256,
    REVIEWER01_ID,
    REVIEWER02_ID,
    HumanReviewIntegrationError,
    load_and_validate_reviewer01_archive,
    load_and_validate_reviewer02_archive,
    sha256_bytes,
    sha256_file,
)
from research.phase3h5 import ALLOWED_CONFIDENCE, ALLOWED_REVIEW_LABELS


ADJUDICATION_POLICY_VERSION = "driftwatch-human-adjudication-v1"
ADJUDICATION_ID_POLICY_VERSION = "driftwatch-adjudication-id-v1"
ADJUDICATION_SCHEMA_VERSION = "driftwatch-human-adjudication-workflow-v1"
ADJUDICATION_ID_PREFIX = "ADV1"
DEFAULT_ADJUDICATOR_ID = "human_adjudicator_01"
STAGE_A = "ADJUDICATION_STAGE_A"
STAGE_B = "ADJUDICATION_STAGE_B"

EXPECTED_DISAGREEMENT_IDS = (
    "automaapp_automa_1_29_11_to_1_29_12",
    "bitwarden_clients_browser_v2026_6_1_to_browser_v2026_7_0",
    "browserpass_browserpass_extension_3_10_2_to_3_11_0",
    "duckduckgo_privacy_2026_1_12_to_2026_4_28",
    "save_tabbed_images_0_4_0_to_0_4_1",
)

PROJECT_LABEL_KEYS = {
    "current_dataset_label",
    "current_label_quality_tier",
    "current_label_confidence",
    "provisional_project_label",
    "project_label",
    "original_project_label",
}
SCORE_KEYS = {"risk_score", "risk_classification", "final_severity", "score"}
RECOMMENDATION_KEYS = {"rule_recommendation", "recommendation"}
ML_KEYS = {
    "predicted_label",
    "predicted_probability",
    "prediction",
    "probability",
    "ml_output",
}
AGREEMENT_KEYS = {
    "agreement_percentage",
    "percent_exact_agreement",
    "cohens_kappa",
    "kappa",
    "gold_set_status",
}


class HumanReviewAdjudicationError(ValueError):
    """Raised when governed adjudication preparation fails validation."""


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise HumanReviewAdjudicationError(f"JSON object required in {path}")
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _field_exists(payload: Mapping[str, Any], dotted_path: str) -> bool:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False
        current = current[part]
    return True


def _collect_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(_collect_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_collect_keys(child))
    return keys


def _valid_iso_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def derive_adjudication_review_id(
    adjudicator_id: str, record_id: str, review_round: str
) -> str:
    if review_round not in {STAGE_A, STAGE_B}:
        raise HumanReviewAdjudicationError(f"unsupported review_round {review_round!r}")
    parts = (adjudicator_id, record_id, review_round)
    if any(not part or "::" in part for part in parts):
        raise HumanReviewAdjudicationError(
            "adjudicator_id, record_id, and review_round must be nonempty and exclude '::'"
        )
    return f"{ADJUDICATION_ID_PREFIX}::{adjudicator_id}::{record_id}::{review_round}"


def validate_disagreement_set(
    disagreement_path: str | Path,
    expected_ids: Sequence[str] = EXPECTED_DISAGREEMENT_IDS,
) -> list[str]:
    payload = _read_json(disagreement_path)
    records = payload.get("records")
    if not isinstance(records, list):
        raise HumanReviewAdjudicationError("disagreement artifact records must be a list")
    record_ids = [record.get("record_id") for record in records if isinstance(record, Mapping)]
    if payload.get("record_count") != 5 or len(record_ids) != 5:
        raise HumanReviewAdjudicationError("exactly five disagreement records are required")
    if len(set(record_ids)) != 5:
        raise HumanReviewAdjudicationError("disagreement record IDs must be unique")
    if set(record_ids) != set(expected_ids):
        raise HumanReviewAdjudicationError(
            f"disagreement IDs differ from the governed Phase 5C set: {record_ids}"
        )
    return sorted(str(record_id) for record_id in record_ids)


def _load_holdout_ids(path: str | Path) -> list[str]:
    payload = _read_json(path)
    return [row["record_id"] for row in payload.get("records", [])]


def _stage_a_submission(record_id: str, adjudicator_id: str) -> dict[str, Any]:
    return {
        "review_id": derive_adjudication_review_id(adjudicator_id, record_id, STAGE_A),
        "adjudicator_id": adjudicator_id,
        "record_id": record_id,
        "review_round": STAGE_A,
        "adjudicator_initial_label": "",
        "adjudicator_initial_confidence": "",
        "adjudicator_initial_rationale": "",
        "evidence_references": [],
        "blind_review": True,
        "review_status": "PENDING",
        "review_timestamp": "",
    }


def _stage_b_submission(record_id: str, adjudicator_id: str) -> dict[str, Any]:
    return {
        "review_id": derive_adjudication_review_id(adjudicator_id, record_id, STAGE_B),
        "adjudicator_id": adjudicator_id,
        "record_id": record_id,
        "review_round": STAGE_B,
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


def _stage_a_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "DriftWatch adjudication Stage A submission",
        "type": "object",
        "required": list(_stage_a_submission("record_id", DEFAULT_ADJUDICATOR_ID)),
        "properties": {
            "review_id": {"type": "string", "pattern": "^ADV1::"},
            "adjudicator_id": {"type": "string", "minLength": 1},
            "record_id": {"type": "string", "minLength": 1},
            "review_round": {"const": STAGE_A},
            "adjudicator_initial_label": {"enum": sorted(ALLOWED_REVIEW_LABELS)},
            "adjudicator_initial_confidence": {"enum": sorted(ALLOWED_CONFIDENCE)},
            "adjudicator_initial_rationale": {"type": "string", "minLength": 1},
            "evidence_references": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string", "minLength": 1},
            },
            "blind_review": {"const": True},
            "review_status": {"const": "SUBMITTED"},
            "review_timestamp": {"type": "string", "format": "date-time"},
        },
        "additionalProperties": False,
    }


def _stage_b_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "DriftWatch adjudication Stage B submission",
        "type": "object",
        "required": list(_stage_b_submission("record_id", DEFAULT_ADJUDICATOR_ID)),
        "properties": {
            "review_id": {"type": "string", "pattern": "^ADV1::"},
            "adjudicator_id": {"type": "string", "minLength": 1},
            "record_id": {"type": "string", "minLength": 1},
            "review_round": {"const": STAGE_B},
            "final_adjudicated_label": {"enum": sorted(ALLOWED_REVIEW_LABELS)},
            "adjudication_confidence": {"enum": sorted(ALLOWED_CONFIDENCE)},
            "adjudication_rationale": {"type": "string", "minLength": 1},
            "adjudication_evidence_references": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string", "minLength": 1},
            },
            "initial_label_changed": {"type": "boolean"},
            "change_reason": {"type": "string"},
            "resolution_basis": {"type": "string", "minLength": 1},
            "review_status": {"const": "SUBMITTED"},
            "review_timestamp": {"type": "string", "format": "date-time"},
        },
        "additionalProperties": False,
    }


def _manifest() -> str:
    return """# DriftWatch Human Adjudication — Stage A Package

- Project: DriftWatch
- Review type: independent blind adjudication Stage A
- Case count: 5
- Scope: all five cases arise from genuine Reviewer 01 / Reviewer 02 disagreements
- Stage A hides all prior reviewer outcomes
- External-holdout overlap: 0
- Reviewer opinions are released only in Stage B after all Stage A submissions pass the completion and integrity gate
- Adjudication does not imply maliciousness
- Stage A results do not overwrite either original review
- Adjudicator role identifier: `human_adjudicator_01` (prospectively reserved; assignment is not completion)

Use only `packets/` and `submissions/` in this package. Stage B material is intentionally absent.
"""


def _instructions() -> str:
    return """# DriftWatch Independent Adjudication — Stage A Instructions

Review each supplied version transition independently using only its matching evidence packet. Do not browse the DriftWatch repository, search for project conclusions, or attempt to discover earlier reviewer outcomes.

## Labels

- `BENIGN_TRANSITION`: supplied evidence supports a legitimate transition without a meaningful unsupported security concern.
- `RISKY_TRANSITION`: the transition introduces security-sensitive capability or behaviour warranting review; this does not mean maliciousness.
- `UNCERTAIN`: evidence is insufficient, incomplete, or contradictory. This is a valid outcome.
- `MALICIOUS_TRANSITION`: use only when strong supplied evidence supports intentionally harmful behaviour.
- `EXCLUDED`: the case cannot be reviewed validly because of a methodological or evidence-integrity problem.

Confidence is `HIGH`, `MEDIUM`, or `LOW`; it is not probability.

For every case, edit only its matching file under `submissions/`. Supply an independent label, confidence, rationale, packet-field evidence references, and timestamp. Set `review_status` to `SUBMITTED`. Keep `blind_review=true` and do not change identifiers or `review_round`. Do not modify packet files.

Submit only the five Stage A submission files. Stage B is unavailable until all five pass validation and are preserved.
"""


def _alias_assignment(record_id: str) -> dict[str, str]:
    selector = hashlib.sha256(
        f"driftwatch-reviewer-alias-v1::{record_id}".encode("utf-8")
    ).digest()[0]
    if selector % 2 == 0:
        return {"Reviewer A": REVIEWER01_ID, "Reviewer B": REVIEWER02_ID}
    return {"Reviewer A": REVIEWER02_ID, "Reviewer B": REVIEWER01_ID}


def _deidentified_opinion(
    record_id: str,
    reviewer01_record: Mapping[str, Any],
    reviewer02_record: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    records_by_reviewer = {
        REVIEWER01_ID: reviewer01_record,
        REVIEWER02_ID: reviewer02_record,
    }
    aliases = _alias_assignment(record_id)
    opinions: dict[str, Any] = {}
    private_aliases: dict[str, Any] = {}
    for alias, reviewer_id in aliases.items():
        record = records_by_reviewer[reviewer_id]
        submission = record["submission"]
        opinions[alias] = {
            "label": submission["independent_label"],
            "confidence": submission["confidence"],
            "rationale": submission["rationale"],
            "evidence_references": submission["evidence_references"],
        }
        private_aliases[alias] = {
            "reviewer_id": reviewer_id,
            "raw_submission_entry_name": record["raw_submission_entry_name"],
            "raw_submission_sha256": record["raw_submission_sha256"],
            "derived_review_id": record["derived_review_id"],
        }
    return (
        {
            "schema_version": ADJUDICATION_SCHEMA_VERSION,
            "record_id": record_id,
            "release_status": "LOCKED_PENDING_STAGE_A_GATE",
            "opinions": opinions,
        },
        {"record_id": record_id, "aliases": private_aliases},
    )


def validate_pending_stage_a_submission(
    submission: Mapping[str, Any], record_id: str, adjudicator_id: str
) -> list[str]:
    expected = _stage_a_submission(record_id, adjudicator_id)
    return [
        f"{key} must equal {value!r}"
        for key, value in expected.items()
        if submission.get(key) != value
    ]


def validate_completed_stage_a_submission(
    submission: Mapping[str, Any],
    packet: Mapping[str, Any],
    record_id: str,
    adjudicator_id: str,
) -> list[str]:
    errors: list[str] = []
    expected_identity = {
        "review_id": derive_adjudication_review_id(adjudicator_id, record_id, STAGE_A),
        "adjudicator_id": adjudicator_id,
        "record_id": record_id,
        "review_round": STAGE_A,
        "blind_review": True,
        "review_status": "SUBMITTED",
    }
    for key, value in expected_identity.items():
        if submission.get(key) != value:
            errors.append(f"{key} must equal {value!r}")
    if submission.get("adjudicator_initial_label") not in ALLOWED_REVIEW_LABELS:
        errors.append("adjudicator_initial_label is invalid or blank")
    if submission.get("adjudicator_initial_confidence") not in ALLOWED_CONFIDENCE:
        errors.append("adjudicator_initial_confidence is invalid or blank")
    rationale = submission.get("adjudicator_initial_rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        errors.append("adjudicator_initial_rationale is required")
    references = submission.get("evidence_references")
    if not isinstance(references, list) or not references:
        errors.append("evidence_references must be nonempty")
    elif any(
        not isinstance(reference, str)
        or not reference
        or not _field_exists(packet, reference)
        for reference in references
    ):
        errors.append("every evidence reference must resolve to a packet field")
    if not _valid_iso_timestamp(submission.get("review_timestamp")):
        errors.append("review_timestamp must be valid ISO-8601")
    return errors


def evaluate_stage_b_release_gate(workspace: str | Path) -> dict[str, Any]:
    workspace = Path(workspace)
    packet_manifest = _read_json(workspace / "metadata" / "stage_a_packet_manifest.json")
    adjudicator_id = packet_manifest["adjudicator_id"]
    records = packet_manifest["records"]
    errors: list[str] = []
    submission_hashes: dict[str, str] = {}
    for source in records:
        record_id = source["record_id"]
        packet_path = workspace / "STAGE_A" / "packets" / f"{record_id}.json"
        submission_path = workspace / "STAGE_A" / "submissions" / f"{record_id}.json"
        if not packet_path.is_file():
            errors.append(f"{record_id}: Stage A packet is missing")
            continue
        if sha256_file(packet_path) != source["sha256"]:
            errors.append(f"{record_id}: Stage A packet hash changed")
        if not submission_path.is_file():
            errors.append(f"{record_id}: Stage A submission is missing")
            continue
        packet = _read_json(packet_path)
        submission = _read_json(submission_path)
        errors.extend(
            f"{record_id}: {error}"
            for error in validate_completed_stage_a_submission(
                submission, packet, record_id, adjudicator_id
            )
        )
        submission_hashes[record_id] = sha256_file(submission_path)

    expected_ids = {row["record_id"] for row in records}
    actual_packet_ids = {path.stem for path in (workspace / "STAGE_A" / "packets").glob("*.json")}
    actual_submission_ids = {
        path.stem for path in (workspace / "STAGE_A" / "submissions").glob("*.json")
    }
    if actual_packet_ids != expected_ids:
        errors.append("Stage A packet IDs differ from the governed manifest")
    if actual_submission_ids != expected_ids:
        errors.append("Stage A submission IDs differ from the governed manifest")
    releasable = not errors and len(submission_hashes) == 5
    return {
        "schema_version": ADJUDICATION_SCHEMA_VERSION,
        "status": "RELEASABLE" if releasable else "LOCKED",
        "required_submission_count": 5,
        "valid_submission_count": 5 if releasable else sum(
            1
            for source in records
            if not any(error.startswith(f"{source['record_id']}:") for error in errors)
        ),
        "all_packet_ids_match": actual_packet_ids == expected_ids,
        "all_submission_ids_match": actual_submission_ids == expected_ids,
        "stage_a_source_hashes_preserved": not any(
            "packet hash changed" in error for error in errors
        ),
        "validation_errors": errors,
        "stage_a_submission_hashes": submission_hashes if releasable else {},
        "stage_a_lock_required_before_release": True,
        "stage_b_released": False,
    }


def _promotion_assessment(analysis: Mapping[str, Any]) -> dict[str, Any]:
    agreed = [row for row in analysis["comparison_rows"] if row["exact_match"] is True]
    return {
        "schema_version": ADJUDICATION_SCHEMA_VERSION,
        "status": "ASSESSMENT_ONLY_NO_PROMOTION",
        "agreed_record_count": len(agreed),
        "agreed_record_ids": [row["record_id"] for row in agreed],
        "current_multi_reviewer_agreed_tier_exists": False,
        "agreement_alone_satisfies_multi_reviewer_adjudicated": False,
        "recommendation": (
            "Consider a future derived MULTI_REVIEWER_AGREED state to distinguish genuine exact "
            "agreement from single-reviewer evidence. Do not add it to the frozen dataset or treat "
            "it as MULTI_REVIEWER_ADJUDICATED without a separately versioned policy decision."
        ),
        "gold_set_qualification": False,
        "dataset_labels_modified": False,
    }


def _gold_set_path(analysis: Mapping[str, Any]) -> dict[str, Any]:
    agreed_ids = [
        row["record_id"] for row in analysis["comparison_rows"] if row["exact_match"] is True
    ]
    disagreement_ids = [row["record_id"] for row in analysis["disagreement_rows"]]
    return {
        "schema_version": ADJUDICATION_SCHEMA_VERSION,
        "status": "ASSESSMENT_ONLY_NO_QUALIFICATION_OR_PROMOTION",
        "existing_qualifying_tiers": [
            "EXTERNAL_CONFIRMED",
            "MULTI_REVIEWER_ADJUDICATED",
            "CONTROLLED_GROUND_TRUTH",
        ],
        "agreed_nine": {
            "record_ids": agreed_ids,
            "current_status": "GENUINE_AGREEMENT_NOT_ADJUDICATED",
            "requirements": [
                "adopt an explicit versioned policy for agreement-only quality or conduct governed adjudication",
                "preserve both independent reviews and complete provenance",
                "make an explicit non-automatic quality-tier promotion decision",
                "retain only a qualifying non-UNCERTAIN and non-EXCLUDED label for Gold Set consideration",
                "pass a separate Gold Set inclusion audit",
            ],
            "currently_gold_eligible": False,
        },
        "disagreement_five": {
            "record_ids": disagreement_ids,
            "current_status": "PENDING_TWO_STAGE_ADJUDICATION",
            "requirements": [
                "complete and lock all five valid Stage A submissions",
                "release de-identified Stage B material only after the gate passes",
                "complete a valid Stage B label, confidence, rationale, evidence references, and resolution basis",
                "preserve both source reviews and the immutable Stage A record",
                "make an explicit non-automatic MULTI_REVIEWER_ADJUDICATED promotion decision",
                "retain only a qualifying non-UNCERTAIN and non-EXCLUDED label for Gold Set consideration",
                "pass complete-provenance and separate Gold Set inclusion audits",
            ],
            "currently_gold_eligible": False,
        },
        "external_holdout_may_be_used": False,
        "gold_set_created": False,
    }


def create_adjudicator_workspace(
    *,
    workspace: str | Path,
    disagreement_ids: Sequence[str],
    reviewer01_bundle: Mapping[str, Any],
    reviewer02_bundle: Mapping[str, Any],
    analysis: Mapping[str, Any],
    adjudicator_id: str = DEFAULT_ADJUDICATOR_ID,
) -> dict[str, Any]:
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=False)
    stage_a_packets = workspace / "STAGE_A" / "packets"
    stage_a_submissions = workspace / "STAGE_A" / "submissions"
    stage_b_opinions = workspace / "STAGE_B" / "reviewer_opinions"
    stage_b_submissions = workspace / "STAGE_B" / "submissions"
    schemas = workspace / "schemas"
    metadata = workspace / "metadata"
    for path in (
        stage_a_packets,
        stage_a_submissions,
        stage_b_opinions,
        stage_b_submissions,
        schemas,
        metadata,
    ):
        path.mkdir(parents=True)

    (workspace / "PACKAGE_MANIFEST.md").write_text(_manifest(), encoding="utf-8", newline="\n")
    (workspace / "REVIEW_INSTRUCTIONS.md").write_text(
        _instructions(), encoding="utf-8", newline="\n"
    )
    _write_json(schemas / "stage_a_submission_schema.json", _stage_a_schema())
    _write_json(schemas / "stage_b_submission_schema.json", _stage_b_schema())

    reviewer01_by_id = {
        record["record_id"]: record for record in reviewer01_bundle["records"]
    }
    reviewer02_by_id = {
        record["record_id"]: record for record in reviewer02_bundle["records"]
    }
    packet_manifest_records: list[dict[str, str]] = []
    private_alias_records: list[dict[str, Any]] = []
    for record_id in sorted(disagreement_ids):
        reviewer01_record = reviewer01_by_id[record_id]
        reviewer02_record = reviewer02_by_id[record_id]
        packet_raw = reviewer01_record["packet_raw_bytes"]
        reviewer02_packet_hash = reviewer02_record["packet_source_sha256"]
        if sha256_bytes(packet_raw) != reviewer02_packet_hash:
            raise HumanReviewAdjudicationError(
                f"Reviewer 01 and Reviewer 02 packet evidence differs for {record_id}"
            )
        packet_path = stage_a_packets / f"{record_id}.json"
        packet_path.write_bytes(packet_raw)
        _write_json(
            stage_a_submissions / f"{record_id}.json",
            _stage_a_submission(record_id, adjudicator_id),
        )
        opinion, private_alias = _deidentified_opinion(
            record_id, reviewer01_record, reviewer02_record
        )
        _write_json(stage_b_opinions / f"{record_id}.json", opinion)
        _write_json(
            stage_b_submissions / f"{record_id}.json",
            _stage_b_submission(record_id, adjudicator_id),
        )
        packet_manifest_records.append(
            {
                "record_id": record_id,
                "filename": packet_path.name,
                "sha256": sha256_file(packet_path),
                "source": "original blind packet supplied to both independent reviewers",
            }
        )
        private_alias_records.append(private_alias)

    _write_json(
        metadata / "stage_a_packet_manifest.json",
        {
            "schema_version": ADJUDICATION_SCHEMA_VERSION,
            "policy_version": ADJUDICATION_POLICY_VERSION,
            "review_id_policy_version": ADJUDICATION_ID_POLICY_VERSION,
            "adjudicator_id": adjudicator_id,
            "record_count": len(packet_manifest_records),
            "external_holdout_overlap": [],
            "records": packet_manifest_records,
        },
    )
    _write_json(
        metadata / "reviewer_alias_mapping.json",
        {
            "schema_version": ADJUDICATION_SCHEMA_VERSION,
            "privacy": "PRIVATE_DO_NOT_RELEASE_TO_ADJUDICATOR",
            "assignment_method": "SHA-256 parity of versioned record-specific alias seed",
            "reviewer01_raw_source_sha256": reviewer01_bundle["raw_source_sha256"],
            "reviewer02_raw_source_sha256": reviewer02_bundle["raw_source_sha256"],
            "records": private_alias_records,
        },
    )
    _write_json(
        metadata / "adjudication_provenance.json",
        {
            "schema_version": ADJUDICATION_SCHEMA_VERSION,
            "policy_version": ADJUDICATION_POLICY_VERSION,
            "review_id_policy_version": ADJUDICATION_ID_POLICY_VERSION,
            "disagreement_record_ids": sorted(disagreement_ids),
            "reviewer01_raw_source_sha256": reviewer01_bundle["raw_source_sha256"],
            "reviewer02_raw_source_sha256": reviewer02_bundle["raw_source_sha256"],
            "source_reviews_immutable": True,
            "stage_a_packet_substance_unchanged": True,
            "stage_b_prepared_locally": True,
            "stage_b_released": False,
            "adjudication_performed": False,
            "gold_set_created": False,
            "dataset_labels_modified": False,
        },
    )
    _write_json(metadata / "agreed_nine_promotion_assessment.json", _promotion_assessment(analysis))
    _write_json(metadata / "gold_set_qualification_path.json", _gold_set_path(analysis))
    gate = evaluate_stage_b_release_gate(workspace)
    _write_json(metadata / "stage_b_release_gate.json", gate)
    return {
        "workspace": str(workspace),
        "stage_a_packet_count": len(packet_manifest_records),
        "stage_a_submission_count": len(list(stage_a_submissions.glob("*.json"))),
        "stage_b_opinion_count": len(list(stage_b_opinions.glob("*.json"))),
        "stage_b_submission_count": len(list(stage_b_submissions.glob("*.json"))),
        "stage_b_status": gate["status"],
    }


def _create_stage_a_zip(workspace: Path, output_zip: Path) -> None:
    if output_zip.exists():
        raise FileExistsError(f"refusing to overwrite {output_zip}")
    entries: list[tuple[Path, str]] = [
        (workspace / "PACKAGE_MANIFEST.md", "PACKAGE_MANIFEST.md"),
        (workspace / "REVIEW_INSTRUCTIONS.md", "REVIEW_INSTRUCTIONS.md"),
    ]
    entries.extend(
        (path, f"packets/{path.name}")
        for path in sorted((workspace / "STAGE_A" / "packets").glob("*.json"))
    )
    entries.extend(
        (path, f"submissions/{path.name}")
        for path in sorted((workspace / "STAGE_A" / "submissions").glob("*.json"))
    )
    with zipfile.ZipFile(
        output_zip, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path, entry_name in sorted(entries, key=lambda item: item[1]):
            info = zipfile.ZipInfo(entry_name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info,
                path.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )


def audit_stage_a_package(
    package_zip: str | Path,
    *,
    expected_ids: Sequence[str],
    holdout_ids: Iterable[str],
    reviewer01_bundle: Mapping[str, Any],
    reviewer02_bundle: Mapping[str, Any],
    adjudicator_id: str = DEFAULT_ADJUDICATOR_ID,
) -> dict[str, Any]:
    package_zip = Path(package_zip)
    packet_entries: dict[str, dict[str, Any]] = {}
    submission_entries: dict[str, dict[str, Any]] = {}
    all_text: list[str] = []
    names: list[str] = []
    with zipfile.ZipFile(package_zip, "r") as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            normalized = str(PurePosixPath(info.filename.replace("\\", "/")))
            names.append(normalized)
            raw = archive.read(info)
            text = raw.decode("utf-8-sig")
            all_text.append(text)
            if normalized.startswith("packets/") and normalized.endswith(".json"):
                packet_entries[Path(normalized).stem] = json.loads(text)
            if normalized.startswith("submissions/") and normalized.endswith(".json"):
                submission_entries[Path(normalized).stem] = json.loads(text)

    expected_id_set = set(expected_ids)
    packet_ids = set(packet_entries)
    submission_ids = set(submission_entries)
    review_ids = [row.get("review_id") for row in submission_entries.values()]
    pending_errors = [
        f"{record_id}: {error}"
        for record_id, submission in submission_entries.items()
        for error in validate_pending_stage_a_submission(
            submission, record_id, adjudicator_id
        )
    ]
    packet_keys = set().union(*(_collect_keys(packet) for packet in packet_entries.values()))
    json_text = json.dumps(
        {"packets": packet_entries, "submissions": submission_entries}, ensure_ascii=False
    ).lower()
    package_text = "\n".join(all_text).lower()
    reviewer01_rationales = [
        record["submission"]["rationale"].strip().lower()
        for record in reviewer01_bundle["records"]
        if record["record_id"] in expected_id_set
    ]
    reviewer02_rationales = [
        record["submission"]["rationale"].strip().lower()
        for record in reviewer02_bundle["records"]
        if record["record_id"] in expected_id_set
    ]
    project_labels = {
        "benign_transition",
        "risky_transition",
        "malicious_transition",
        "uncertain",
        "excluded",
        "controlled_malicious_transition",
        "needs_review",
    }
    # Human ontology labels are required in instructions. Project-label checks
    # therefore operate on packet/submission JSON, where no outcome is permitted.
    checks = {
        "packet_count_is_5": len(packet_entries) == 5,
        "submission_count_is_5": len(submission_entries) == 5,
        "record_ids_unique_and_exact": packet_ids == submission_ids == expected_id_set,
        "review_ids_unique": len(review_ids) == 5 and len(set(review_ids)) == 5,
        "pending_submissions_valid": not pending_errors,
        "external_holdout_overlap_zero": not (expected_id_set & set(holdout_ids)),
        "reviewer01_outcomes_hidden": not any(
            rationale and rationale in package_text for rationale in reviewer01_rationales
        )
        and REVIEWER01_ID not in json_text,
        "reviewer02_outcomes_hidden": not any(
            rationale and rationale in package_text for rationale in reviewer02_rationales
        )
        and REVIEWER02_ID not in json_text,
        "project_labels_hidden": not (packet_keys & PROJECT_LABEL_KEYS)
        and not any(f'"{label}"' in json_text for label in project_labels),
        "driftwatch_scores_hidden": not (packet_keys & SCORE_KEYS),
        "recommendations_hidden": not (packet_keys & RECOMMENDATION_KEYS),
        "ml_outputs_hidden": not (packet_keys & ML_KEYS),
        "agreement_percentage_hidden": "64.29" not in package_text
        and "9/14" not in package_text
        and "percent_exact_agreement" not in package_text,
        "cohens_kappa_hidden": "cohen" not in package_text
        and "kappa" not in package_text
        and "0.3396" not in package_text,
        "stage_b_hidden": not any("stage_b" in name.lower() for name in names)
        and "reviewer_opinions" not in package_text,
        "contents_allowlisted": set(names)
        == {
            "PACKAGE_MANIFEST.md",
            "REVIEW_INSTRUCTIONS.md",
            *(f"packets/{record_id}.json" for record_id in expected_id_set),
            *(f"submissions/{record_id}.json" for record_id in expected_id_set),
        },
    }
    return {
        "schema_version": ADJUDICATION_SCHEMA_VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "package_sha256": sha256_file(package_zip),
        "packet_count": len(packet_entries),
        "submission_count": len(submission_entries),
        "record_ids": sorted(packet_ids),
        "external_holdout_overlap": sorted(expected_id_set & set(holdout_ids)),
        "pending_submission_errors": pending_errors,
        "zip_entries": sorted(names),
    }


def build_stage_a_package(
    *,
    workspace: str | Path,
    output_zip: str | Path,
    checksum_path: str | Path,
    expected_ids: Sequence[str],
    holdout_ids: Iterable[str],
    reviewer01_bundle: Mapping[str, Any],
    reviewer02_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    workspace = Path(workspace)
    output_zip = Path(output_zip)
    checksum_path = Path(checksum_path)
    if checksum_path.exists():
        raise FileExistsError(f"refusing to overwrite {checksum_path}")
    _create_stage_a_zip(workspace, output_zip)
    audit = audit_stage_a_package(
        output_zip,
        expected_ids=expected_ids,
        holdout_ids=holdout_ids,
        reviewer01_bundle=reviewer01_bundle,
        reviewer02_bundle=reviewer02_bundle,
    )
    if not audit["passed"]:
        raise HumanReviewAdjudicationError(f"Stage A package audit failed: {audit}")
    checksum_path.write_text(
        f"{audit['package_sha256']}  {output_zip.name}\n", encoding="ascii", newline="\n"
    )
    _write_json(Path(workspace) / "metadata" / "stage_a_package_audit.json", audit)
    return audit


def run_phase5d(
    *,
    reviewer01_zip: str | Path,
    reviewer02_zip: str | Path,
    reviewer02_packet_root: str | Path,
    disagreement_path: str | Path,
    holdout_manifest: str | Path,
    workspace: str | Path,
    output_zip: str | Path,
    checksum_path: str | Path,
) -> dict[str, Any]:
    disagreement_ids = validate_disagreement_set(disagreement_path)
    reviewer01_bundle = load_and_validate_reviewer01_archive(
        reviewer01_zip, expected_sha256=RAW_REVIEWER01_SHA256
    )
    reviewer02_bundle = load_and_validate_reviewer02_archive(
        reviewer02_zip,
        packet_root=reviewer02_packet_root,
        expected_sha256=RAW_REVIEWER02_SHA256,
    )
    holdout_ids = _load_holdout_ids(holdout_manifest)
    analysis = build_agreement_analysis(reviewer01_bundle, reviewer02_bundle, holdout_ids)
    reconstructed_ids = sorted(row["record_id"] for row in analysis["disagreement_rows"])
    if reconstructed_ids != disagreement_ids:
        raise HumanReviewAdjudicationError(
            "stored disagreement artifact does not match authoritative raw-return reconstruction"
        )
    overlap = sorted(set(disagreement_ids) & set(holdout_ids))
    if overlap:
        raise HumanReviewAdjudicationError(f"external-holdout overlap detected: {overlap}")
    workspace_report = create_adjudicator_workspace(
        workspace=workspace,
        disagreement_ids=disagreement_ids,
        reviewer01_bundle=reviewer01_bundle,
        reviewer02_bundle=reviewer02_bundle,
        analysis=analysis,
    )
    package_audit = build_stage_a_package(
        workspace=workspace,
        output_zip=output_zip,
        checksum_path=checksum_path,
        expected_ids=disagreement_ids,
        holdout_ids=holdout_ids,
        reviewer01_bundle=reviewer01_bundle,
        reviewer02_bundle=reviewer02_bundle,
    )
    return {
        "disagreement_record_ids": disagreement_ids,
        "external_holdout_overlap": overlap,
        "workspace": workspace_report,
        "stage_a_package_audit": package_audit,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare the governed two-stage DriftWatch human-adjudication workflow."
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
        "--disagreement-path",
        default="artifacts/human_review/agreement/reviewer01_vs_reviewer02/disagreements.json",
    )
    parser.add_argument(
        "--holdout-manifest",
        default="artifacts/driftbench/phase3h/external_holdout_manifest.json",
    )
    parser.add_argument("--workspace", default="reviewer_human_adjudicator")
    parser.add_argument(
        "--output-zip", default="DriftWatch_Human_Adjudication_StageA_Package.zip"
    )
    parser.add_argument(
        "--checksum-path", default="DriftWatch_Human_Adjudication_StageA_Package.sha256"
    )
    args = parser.parse_args()
    result = run_phase5d(
        reviewer01_zip=args.reviewer01_zip,
        reviewer02_zip=args.reviewer02_zip,
        reviewer02_packet_root=args.reviewer02_packet_root,
        disagreement_path=args.disagreement_path,
        holdout_manifest=args.holdout_manifest,
        workspace=args.workspace,
        output_zip=args.output_zip,
        checksum_path=args.checksum_path,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
