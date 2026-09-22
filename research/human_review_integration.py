from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from driftbench.labels import LABEL_ONTOLOGY
from research.phase3h5 import ALLOWED_CONFIDENCE, ALLOWED_REVIEW_LABELS, reviewer_schema


RAW_REVIEWER01_SHA256 = "E4843AE0A1241D4E69A70E2C16063DA447EB97BA82CFF2AAF92CF258D4668A5C"
RAW_REVIEWER02_SHA256 = "E9E19CDF330C5F41B794823FF9A5C02300F03A7EEEBE5139820521ACC5A57CDA"
LABEL_MAPPING_VERSION = "driftwatch-human-review-label-mapping-v1"
REVIEW_ID_POLICY_VERSION = "driftwatch-human-review-id-v1"
DERIVED_REVIEW_SCHEMA_VERSION = "driftwatch-validated-human-review-v1"
COMPARISON_SCHEMA_VERSION = "driftwatch-human-vs-provisional-concordance-v1"
REVIEWER02_PACKAGE_SCHEMA_VERSION = "driftwatch-independent-reviewer02-package-v1"
NOT_COMPARABLE = "NOT_COMPARABLE"

HUMAN_TO_DATASET_LABEL = {
    "BENIGN_TRANSITION": "benign_transition",
    "RISKY_TRANSITION": "risky_transition",
    "MALICIOUS_TRANSITION": "malicious_transition",
    "UNCERTAIN": "uncertain",
    "EXCLUDED": "excluded",
}

REVIEWER01_ID = "human_reviewer_01"
REVIEWER02_ID = "human_reviewer_02"
INITIAL_BLIND = "INITIAL_BLIND"
PLACEHOLDER_CONFIRMED = "PLACEHOLDER_CONFIRMED"

FORBIDDEN_PACKET_KEYS = {
    "current_dataset_label",
    "current_label_quality_tier",
    "current_label_confidence",
    "risk_score",
    "risk_classification",
    "final_severity",
    "rule_recommendation",
    "recommendation",
    "predicted_label",
    "predicted_probability",
    "prediction",
    "probability",
    "ml_output",
    "gold_set_flag",
    "gold_label_source",
    "reviewer_a_label",
    "reviewer_01_label",
}


class HumanReviewIntegrationError(ValueError):
    """Raised when human-review evidence fails governed validation."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def verify_file_sha256(path: str | Path, expected_sha256: str) -> str:
    actual = sha256_file(path)
    expected = expected_sha256.upper()
    if actual != expected:
        raise HumanReviewIntegrationError(
            f"SHA-256 mismatch for {Path(path)}: expected {expected}, got {actual}"
        )
    return actual


def map_human_label(label: str) -> str:
    mapped = HUMAN_TO_DATASET_LABEL.get(label, NOT_COMPARABLE)
    if mapped != NOT_COMPARABLE and mapped not in LABEL_ONTOLOGY:
        raise HumanReviewIntegrationError(
            f"mapping target {mapped!r} is not in the dataset ontology"
        )
    return mapped


def derive_review_id(reviewer_id: str, record_id: str, review_round: str) -> str:
    parts = (reviewer_id, record_id, review_round)
    if any(not part or "::" in part for part in parts):
        raise HumanReviewIntegrationError(
            "reviewer_id, record_id, and review_round must be nonempty and must not contain '::'"
        )
    return f"HRV1::{reviewer_id}::{record_id}::{review_round}"


def _normalized_entry_name(name: str) -> str:
    return str(PurePosixPath(name.replace("\\", "/")))


def _json_from_bytes(raw: bytes, entry_name: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HumanReviewIntegrationError(f"invalid JSON in {entry_name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise HumanReviewIntegrationError(f"JSON object required in {entry_name}")
    return payload


def _entry_kind(name: str) -> str | None:
    normalized = _normalized_entry_name(name)
    parts = normalized.split("/")
    if len(parts) >= 2 and parts[-2] in {"packets", "submissions"} and parts[-1].endswith(".json"):
        return parts[-2]
    return None


def _field_exists(payload: Mapping[str, Any], dotted_path: str) -> bool:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False
        current = current[part]
    return True


def _valid_iso_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
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


def validate_completed_submission(
    submission: Mapping[str, Any],
    packet: Mapping[str, Any],
    *,
    expected_reviewer_id: str,
    allow_derived_review_id: bool,
) -> list[str]:
    errors: list[str] = []
    record_id = submission.get("record_id")
    if not isinstance(record_id, str) or not record_id:
        errors.append("record_id is required")
    elif record_id != packet.get("record_id"):
        errors.append("submission record_id does not match packet record_id")
    if submission.get("reviewer_id") != expected_reviewer_id:
        errors.append(f"reviewer_id must equal {expected_reviewer_id}")
    if submission.get("review_round") != INITIAL_BLIND:
        errors.append(f"review_round must equal {INITIAL_BLIND}")
    if submission.get("independent_label") not in ALLOWED_REVIEW_LABELS:
        errors.append("independent_label is invalid")
    if submission.get("confidence") not in ALLOWED_CONFIDENCE:
        errors.append("confidence is invalid")
    if not isinstance(submission.get("rationale"), str) or not submission["rationale"].strip():
        errors.append("rationale is required")
    references = submission.get("evidence_references")
    if not isinstance(references, list) or not references:
        errors.append("evidence_references must be a nonempty list")
    elif any(not isinstance(item, str) or not item or not _field_exists(packet, item) for item in references):
        errors.append("every evidence reference must resolve to a packet field")
    if submission.get("blind_review") is not True:
        errors.append("blind_review must be true")
    if submission.get("review_status") != "SUBMITTED":
        errors.append("review_status must equal SUBMITTED")
    if not _valid_iso_timestamp(submission.get("review_timestamp")):
        errors.append("review_timestamp must be a valid ISO-8601 timestamp")

    review_id = submission.get("review_id")
    expected_id = derive_review_id(expected_reviewer_id, str(record_id), INITIAL_BLIND) if record_id else None
    if allow_derived_review_id:
        if review_id not in (None, "", expected_id):
            errors.append("supplied review_id conflicts with the governed derived review ID")
    elif review_id != expected_id:
        errors.append("review_id must equal the preassigned governed review ID")
    return errors


def validate_pending_submission(
    submission: Mapping[str, Any],
    *,
    expected_reviewer_id: str,
    expected_record_id: str,
) -> list[str]:
    errors: list[str] = []
    expected_review_id = derive_review_id(expected_reviewer_id, expected_record_id, INITIAL_BLIND)
    expected_values = {
        "review_id": expected_review_id,
        "reviewer_id": expected_reviewer_id,
        "record_id": expected_record_id,
        "review_round": INITIAL_BLIND,
        "independent_label": "",
        "confidence": "",
        "rationale": "",
        "evidence_references": [],
        "blind_review": True,
        "review_timestamp": "",
        "review_status": "PENDING",
    }
    for key, expected in expected_values.items():
        if submission.get(key) != expected:
            errors.append(f"{key} must equal {expected!r}")
    return errors


def load_and_validate_reviewer01_archive(
    raw_zip_path: str | Path,
    *,
    expected_sha256: str = RAW_REVIEWER01_SHA256,
) -> dict[str, Any]:
    raw_zip_path = Path(raw_zip_path)
    source_sha256 = verify_file_sha256(raw_zip_path, expected_sha256)
    packet_entries: dict[str, dict[str, Any]] = {}
    submission_entries: dict[str, dict[str, Any]] = {}

    with zipfile.ZipFile(raw_zip_path, "r") as archive:
        for info in archive.infolist():
            kind = _entry_kind(info.filename)
            if kind is None or info.is_dir():
                continue
            raw = archive.read(info)
            payload = _json_from_bytes(raw, info.filename)
            record_id = payload.get("record_id")
            if not isinstance(record_id, str) or not record_id:
                raise HumanReviewIntegrationError(f"record_id missing from {info.filename}")
            filename_record_id = Path(_normalized_entry_name(info.filename)).stem
            if filename_record_id != record_id:
                raise HumanReviewIntegrationError(
                    f"filename/record_id mismatch in {info.filename}: {record_id}"
                )
            destination = packet_entries if kind == "packets" else submission_entries
            if record_id in destination:
                raise HumanReviewIntegrationError(f"duplicate {kind} record_id {record_id}")
            destination[record_id] = {
                "entry_name": _normalized_entry_name(info.filename),
                "filename": Path(_normalized_entry_name(info.filename)).name,
                "sha256": sha256_bytes(raw),
                "raw_bytes": raw,
                "payload": payload,
            }

    if len(packet_entries) != 14 or len(submission_entries) != 14:
        raise HumanReviewIntegrationError(
            f"expected 14 packets and 14 submissions, got {len(packet_entries)} and {len(submission_entries)}"
        )
    if set(packet_entries) != set(submission_entries):
        raise HumanReviewIntegrationError("packet and submission record IDs do not match")

    canonical_required = set(reviewer_schema()["required_fields"])
    records: list[dict[str, Any]] = []
    derived_ids: set[str] = set()
    for record_id in sorted(submission_entries):
        packet_entry = packet_entries[record_id]
        submission_entry = submission_entries[record_id]
        packet = packet_entry["payload"]
        submission = submission_entry["payload"]
        if packet.get("blind_review") is not True:
            raise HumanReviewIntegrationError(f"packet blind_review is not true for {record_id}")
        errors = validate_completed_submission(
            submission,
            packet,
            expected_reviewer_id=REVIEWER01_ID,
            allow_derived_review_id=True,
        )
        if errors:
            raise HumanReviewIntegrationError(f"{record_id}: {'; '.join(errors)}")
        derived_review_id = derive_review_id(
            submission["reviewer_id"], submission["record_id"], submission["review_round"]
        )
        if derived_review_id in derived_ids:
            raise HumanReviewIntegrationError(f"duplicate derived review_id {derived_review_id}")
        derived_ids.add(derived_review_id)
        records.append(
            {
                "record_id": record_id,
                "derived_review_id": derived_review_id,
                "raw_submission_filename": submission_entry["filename"],
                "raw_submission_entry_name": submission_entry["entry_name"],
                "raw_submission_sha256": submission_entry["sha256"],
                "raw_packet_entry_name": packet_entry["entry_name"],
                "raw_packet_sha256": packet_entry["sha256"],
                "missing_canonical_fields": sorted(canonical_required - set(submission)),
                "submission": submission,
                "packet": packet,
                "packet_raw_bytes": packet_entry["raw_bytes"],
            }
        )

    return {
        "raw_zip_path": str(raw_zip_path),
        "raw_source_sha256": source_sha256,
        "packet_count": len(packet_entries),
        "submission_count": len(submission_entries),
        "records": records,
    }


def load_and_validate_reviewer02_archive(
    raw_zip_path: str | Path,
    *,
    packet_root: str | Path,
    expected_sha256: str = RAW_REVIEWER02_SHA256,
) -> dict[str, Any]:
    """Validate the authoritative Reviewer 02 return without altering it.

    The authoritative first return contains only completed submissions. Evidence
    references are therefore resolved against the immutable packet workspace
    from which the Reviewer 02 package was built.
    """

    raw_zip_path = Path(raw_zip_path)
    packet_root = Path(packet_root)
    source_sha256 = verify_file_sha256(raw_zip_path, expected_sha256)
    submission_entries: dict[str, dict[str, Any]] = {}

    with zipfile.ZipFile(raw_zip_path, "r") as archive:
        for info in archive.infolist():
            if _entry_kind(info.filename) != "submissions" or info.is_dir():
                continue
            raw = archive.read(info)
            payload = _json_from_bytes(raw, info.filename)
            record_id = payload.get("record_id")
            if not isinstance(record_id, str) or not record_id:
                raise HumanReviewIntegrationError(f"record_id missing from {info.filename}")
            filename_record_id = Path(_normalized_entry_name(info.filename)).stem
            if filename_record_id != record_id:
                raise HumanReviewIntegrationError(
                    f"filename/record_id mismatch in {info.filename}: {record_id}"
                )
            if record_id in submission_entries:
                raise HumanReviewIntegrationError(f"duplicate submissions record_id {record_id}")
            submission_entries[record_id] = {
                "entry_name": _normalized_entry_name(info.filename),
                "filename": Path(_normalized_entry_name(info.filename)).name,
                "sha256": sha256_bytes(raw),
                "payload": payload,
            }

    packet_entries: dict[str, dict[str, Any]] = {}
    for path in sorted(packet_root.glob("*.json")):
        raw = path.read_bytes()
        payload = _json_from_bytes(raw, str(path))
        record_id = payload.get("record_id")
        if not isinstance(record_id, str) or not record_id:
            raise HumanReviewIntegrationError(f"record_id missing from {path}")
        if path.stem != record_id:
            raise HumanReviewIntegrationError(f"filename/record_id mismatch in {path}: {record_id}")
        if record_id in packet_entries:
            raise HumanReviewIntegrationError(f"duplicate packet record_id {record_id}")
        packet_entries[record_id] = {
            "entry_name": path.as_posix(),
            "filename": path.name,
            "sha256": sha256_bytes(raw),
            "payload": payload,
        }

    if len(packet_entries) != 14 or len(submission_entries) != 14:
        raise HumanReviewIntegrationError(
            f"expected 14 packets and 14 submissions, got {len(packet_entries)} and {len(submission_entries)}"
        )
    if set(packet_entries) != set(submission_entries):
        raise HumanReviewIntegrationError("packet and submission record IDs do not match")

    canonical_required = set(reviewer_schema()["required_fields"])
    records: list[dict[str, Any]] = []
    derived_ids: set[str] = set()
    for record_id in sorted(submission_entries):
        packet_entry = packet_entries[record_id]
        submission_entry = submission_entries[record_id]
        packet = packet_entry["payload"]
        submission = submission_entry["payload"]
        if packet.get("blind_review") is not True:
            raise HumanReviewIntegrationError(f"packet blind_review is not true for {record_id}")
        errors = validate_completed_submission(
            submission,
            packet,
            expected_reviewer_id=REVIEWER02_ID,
            allow_derived_review_id=True,
        )
        if errors:
            raise HumanReviewIntegrationError(f"{record_id}: {'; '.join(errors)}")
        derived_review_id = derive_review_id(
            submission["reviewer_id"], submission["record_id"], submission["review_round"]
        )
        if derived_review_id in derived_ids:
            raise HumanReviewIntegrationError(f"duplicate derived review_id {derived_review_id}")
        derived_ids.add(derived_review_id)
        missing_fields = set(canonical_required - set(submission))
        if not submission.get("review_id"):
            missing_fields.add("review_id")
        records.append(
            {
                "record_id": record_id,
                "derived_review_id": derived_review_id,
                "raw_submission_filename": submission_entry["filename"],
                "raw_submission_entry_name": submission_entry["entry_name"],
                "raw_submission_sha256": submission_entry["sha256"],
                "packet_source_name": packet_entry["entry_name"],
                "packet_source_sha256": packet_entry["sha256"],
                "missing_canonical_fields": sorted(missing_fields),
                "submission": submission,
                "packet": packet,
            }
        )

    return {
        "raw_zip_path": str(raw_zip_path),
        "raw_source_sha256": source_sha256,
        "packet_source_path": str(packet_root),
        "packet_count": len(packet_entries),
        "submission_count": len(submission_entries),
        "timestamp_quality": PLACEHOLDER_CONFIRMED,
        "records": records,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _prepare_new_directory(path: str | Path) -> Path:
    output = Path(path)
    output.mkdir(parents=True, exist_ok=False)
    return output


def mapping_metadata() -> dict[str, Any]:
    return {
        "mapping_version": LABEL_MAPPING_VERSION,
        "not_comparable_value": NOT_COMPARABLE,
        "human_to_dataset_label": dict(HUMAN_TO_DATASET_LABEL),
        "dataset_only_not_comparable_labels": [
            label for label in ("controlled_malicious_transition", "needs_review") if label in LABEL_ONTOLOGY
        ],
        "policy_document": "HUMAN_REVIEW_LABEL_MAPPING.md",
        "purpose": "human-vs-provisional label concordance only",
        "changes_raw_or_dataset_labels": False,
    }


def write_reviewer01_derived_layer(bundle: Mapping[str, Any], output_root: str | Path) -> dict[str, Any]:
    output = _prepare_new_directory(output_root)
    validated_dir = output / "validated_submissions"
    validated_dir.mkdir()
    source_metadata = {
        "schema_version": DERIVED_REVIEW_SCHEMA_VERSION,
        "raw_source_path": bundle["raw_zip_path"],
        "raw_source_sha256": bundle["raw_source_sha256"],
        "immutable_source": True,
        "raw_source_modified": False,
        "packet_count": bundle["packet_count"],
        "submission_count": bundle["submission_count"],
    }
    _write_json(output / "RAW_SOURCE_METADATA.json", source_metadata)
    _write_json(output / "mapping_version.json", mapping_metadata())

    provenance_records: list[dict[str, Any]] = []
    missing_field_distribution: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    confidence: Counter[str] = Counter()
    for record in bundle["records"]:
        submission = record["submission"]
        for field in record["missing_canonical_fields"]:
            missing_field_distribution[field] += 1
        labels[submission["independent_label"]] += 1
        confidence[submission["confidence"]] += 1
        wrapper = {
            "schema_version": DERIVED_REVIEW_SCHEMA_VERSION,
            "review_id_policy_version": REVIEW_ID_POLICY_VERSION,
            "raw_source_sha256": bundle["raw_source_sha256"],
            "raw_submission_filename": record["raw_submission_filename"],
            "raw_submission_sha256": record["raw_submission_sha256"],
            "derived_review_id": record["derived_review_id"],
            "original_submission": submission,
        }
        _write_json(validated_dir / record["raw_submission_filename"], wrapper)
        provenance_records.append(
            {
                "derived_review_id": record["derived_review_id"],
                "reviewer_id": submission["reviewer_id"],
                "record_id": submission["record_id"],
                "review_round": submission["review_round"],
                "raw_submission_filename": record["raw_submission_filename"],
                "raw_submission_entry_name": record["raw_submission_entry_name"],
                "raw_submission_sha256": record["raw_submission_sha256"],
                "raw_packet_entry_name": record["raw_packet_entry_name"],
                "raw_packet_sha256": record["raw_packet_sha256"],
                "raw_source_sha256": bundle["raw_source_sha256"],
            }
        )

    validation_report = {
        "schema_version": DERIVED_REVIEW_SCHEMA_VERSION,
        "status": "VALIDATED_WITH_DOCUMENTED_LEGACY_SCHEMA_OMISSION",
        "packet_count": bundle["packet_count"],
        "submission_count": bundle["submission_count"],
        "validated_submission_count": len(bundle["records"]),
        "derived_review_id_count": len({row["derived_review_id"] for row in provenance_records}),
        "reviewer_id_distribution": dict(Counter(row["reviewer_id"] for row in provenance_records)),
        "label_distribution": dict(sorted(labels.items())),
        "confidence_distribution": dict(sorted(confidence.items())),
        "rationale_complete_count": sum(bool(row["submission"]["rationale"].strip()) for row in bundle["records"]),
        "evidence_references_complete_count": sum(bool(row["submission"]["evidence_references"]) for row in bundle["records"]),
        "canonical_missing_field_distribution": dict(sorted(missing_field_distribution.items())),
        "legacy_schema_discrepancy": (
            "Reviewer 01 raw submissions omit schema-required review_id because the distributed template omitted it; "
            "derived_review_id is wrapper metadata and the raw submission is unchanged."
        ),
        "raw_values_modified": False,
        "project_labels_in_validated_submissions": False,
    }
    _write_json(output / "validation_report.json", validation_report)
    _write_json(
        output / "provenance_manifest.json",
        {
            "schema_version": DERIVED_REVIEW_SCHEMA_VERSION,
            "review_id_policy_version": REVIEW_ID_POLICY_VERSION,
            "raw_source_sha256": bundle["raw_source_sha256"],
            "record_count": len(provenance_records),
            "records": provenance_records,
        },
    )
    return validation_report


def write_reviewer02_derived_layer(
    bundle: Mapping[str, Any], output_root: str | Path
) -> dict[str, Any]:
    """Write provenance-preserving wrappers for the authoritative Reviewer 02 return."""

    output = _prepare_new_directory(output_root)
    validated_dir = output / "validated_submissions"
    validated_dir.mkdir()
    source_metadata = {
        "schema_version": DERIVED_REVIEW_SCHEMA_VERSION,
        "raw_source_path": bundle["raw_zip_path"],
        "raw_source_sha256": bundle["raw_source_sha256"],
        "immutable_source": True,
        "raw_source_modified": False,
        "packet_source_path": bundle["packet_source_path"],
        "packet_count": bundle["packet_count"],
        "submission_count": bundle["submission_count"],
        "timestamp_quality": PLACEHOLDER_CONFIRMED,
    }
    _write_json(output / "RAW_SOURCE_METADATA.json", source_metadata)
    _write_json(output / "mapping_version.json", mapping_metadata())

    provenance_records: list[dict[str, Any]] = []
    missing_field_distribution: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    confidence: Counter[str] = Counter()
    for record in bundle["records"]:
        submission = record["submission"]
        for field in record["missing_canonical_fields"]:
            missing_field_distribution[field] += 1
        labels[submission["independent_label"]] += 1
        confidence[submission["confidence"]] += 1
        wrapper = {
            "schema_version": DERIVED_REVIEW_SCHEMA_VERSION,
            "review_id_policy_version": REVIEW_ID_POLICY_VERSION,
            "mapping_version": LABEL_MAPPING_VERSION,
            "raw_source_sha256": bundle["raw_source_sha256"],
            "raw_submission_filename": record["raw_submission_filename"],
            "raw_submission_sha256": record["raw_submission_sha256"],
            "derived_review_id": record["derived_review_id"],
            "timestamp_quality": PLACEHOLDER_CONFIRMED,
            "original_submission": submission,
        }
        _write_json(validated_dir / record["raw_submission_filename"], wrapper)
        provenance_records.append(
            {
                "derived_review_id": record["derived_review_id"],
                "reviewer_id": submission["reviewer_id"],
                "record_id": submission["record_id"],
                "review_round": submission["review_round"],
                "raw_submission_filename": record["raw_submission_filename"],
                "raw_submission_entry_name": record["raw_submission_entry_name"],
                "raw_submission_sha256": record["raw_submission_sha256"],
                "packet_source_name": record["packet_source_name"],
                "packet_source_sha256": record["packet_source_sha256"],
                "raw_source_sha256": bundle["raw_source_sha256"],
                "timestamp_quality": PLACEHOLDER_CONFIRMED,
            }
        )

    validation_report = {
        "schema_version": DERIVED_REVIEW_SCHEMA_VERSION,
        "status": "VALIDATED_WITH_DERIVED_IDS_AND_PLACEHOLDER_TIMESTAMPS",
        "packet_count": bundle["packet_count"],
        "submission_count": bundle["submission_count"],
        "validated_submission_count": len(bundle["records"]),
        "derived_review_id_count": len({row["derived_review_id"] for row in provenance_records}),
        "reviewer_id_distribution": dict(Counter(row["reviewer_id"] for row in provenance_records)),
        "label_distribution": dict(sorted(labels.items())),
        "confidence_distribution": dict(sorted(confidence.items())),
        "rationale_complete_count": sum(
            bool(row["submission"]["rationale"].strip()) for row in bundle["records"]
        ),
        "evidence_references_complete_count": sum(
            bool(row["submission"]["evidence_references"]) for row in bundle["records"]
        ),
        "evidence_references_resolved_count": len(bundle["records"]),
        "canonical_missing_field_distribution": dict(sorted(missing_field_distribution.items())),
        "review_id_discrepancy": (
            "Reviewer 02 raw submissions contain blank review_id values; derived_review_id is "
            "wrapper metadata and the raw submissions are unchanged."
        ),
        "timestamp_quality": PLACEHOLDER_CONFIRMED,
        "timestamp_disposition": (
            "Reviewer 02 confirmed the timestamps were placeholders. They are preserved verbatim "
            "and are not used for identity, ordering, independence, or agreement analysis."
        ),
        "raw_values_modified": False,
        "project_labels_in_validated_submissions": False,
    }
    _write_json(output / "validation_report.json", validation_report)
    _write_json(
        output / "provenance_manifest.json",
        {
            "schema_version": DERIVED_REVIEW_SCHEMA_VERSION,
            "review_id_policy_version": REVIEW_ID_POLICY_VERSION,
            "mapping_version": LABEL_MAPPING_VERSION,
            "raw_source_sha256": bundle["raw_source_sha256"],
            "record_count": len(provenance_records),
            "authoritative_return": "FIRST_COMPLETED_REVIEWER02_RETURN",
            "independence_confirmation": (
                "Reviewer 02 confirmed that the first completed package contains genuine initial "
                "independent judgements based only on supplied blind evidence."
            ),
            "timestamp_quality": PLACEHOLDER_CONFIRMED,
            "later_attempts_disposition": (
                "Later Reviewer 02 attempts are non-authoritative provenance/history only and are "
                "excluded from agreement, adjudication, Gold Set qualification, paper results, "
                "and label promotion."
            ),
            "records": provenance_records,
        },
    )
    return validation_report


def write_human_vs_provisional_comparison(
    bundle: Mapping[str, Any],
    dataset_manifest_path: str | Path,
    output_root: str | Path,
) -> dict[str, Any]:
    output = _prepare_new_directory(output_root)
    with Path(dataset_manifest_path).open(encoding="utf-8") as handle:
        dataset_manifest = json.load(handle)
    project_by_id = {row["pair_id"]: row for row in dataset_manifest["records"]}
    rows: list[dict[str, Any]] = []
    cross_tab: dict[str, Counter[str]] = {}
    for record in bundle["records"]:
        record_id = record["record_id"]
        if record_id not in project_by_id:
            raise HumanReviewIntegrationError(f"record {record_id} is absent from the dataset manifest")
        project = project_by_id[record_id]
        human = record["submission"]
        mapped = map_human_label(human["independent_label"])
        comparable = mapped != NOT_COMPARABLE and project["label"] in LABEL_ONTOLOGY
        exact_match = mapped == project["label"] if comparable else None
        if comparable:
            cross_tab.setdefault(project["label"], Counter())[mapped] += 1
        rows.append(
            {
                "record_id": record_id,
                "provisional_project_label": project["label"],
                "project_label_source": project.get("label_source"),
                "project_label_quality_tier": project.get("label_quality_tier"),
                "project_label_review_status": project.get("label_review_status"),
                "original_human_label": human["independent_label"],
                "mapped_human_comparison_label": mapped,
                "human_confidence": human["confidence"],
                "comparable": comparable,
                "exact_match": exact_match,
                "derived_review_id": record["derived_review_id"],
            }
        )

    comparable_rows = [row for row in rows if row["comparable"]]
    exact_matches = sum(row["exact_match"] is True for row in comparable_rows)
    report = {
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "title": "HUMAN-vs-PROVISIONAL LABEL CONCORDANCE",
        "mapping_version": LABEL_MAPPING_VERSION,
        "review_id_policy_version": REVIEW_ID_POLICY_VERSION,
        "raw_source_sha256": bundle["raw_source_sha256"],
        "record_count": len(rows),
        "comparable_record_count": len(comparable_rows),
        "not_comparable_record_count": len(rows) - len(comparable_rows),
        "exact_match_count": exact_matches,
        "exact_match_proportion": exact_matches / len(comparable_rows) if comparable_rows else None,
        "category_cross_tabulation": {
            project_label: dict(sorted(human_counts.items()))
            for project_label, human_counts in sorted(cross_tab.items())
        },
        "methodological_status": (
            "Descriptive concordance between one independent human reviewer and non-independent provisional project labels; "
            "not human-human inter-rater agreement, reviewer consensus, ground-truth accuracy, or adjudication."
        ),
        "dataset_labels_modified": False,
        "records": rows,
    }
    _write_json(output / "concordance_report.json", report)
    csv_path = output / "comparison.csv"
    with csv_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return report


def _reviewer02_manifest(record_ids: Sequence[str]) -> str:
    rows = "\n".join(f"| {index} | `{record_id}` |" for index, record_id in enumerate(record_ids, 1))
    return f"""# DriftWatch Independent Human Review — Reviewer 02 Package

- Review type: independent blind human security review
- Package schema: `{REVIEWER02_PACKAGE_SCHEMA_VERSION}`
- Package scope: 14 version-pair transitions
- Packet count: 14
- Submission count: 14
- Case set: the same scoped case set supplied to Reviewer 01
- Protected external-holdout records are excluded
- Reviewer 01 outcomes are intentionally unavailable
- Use only the evidence supplied in this package
- No project labels, DriftWatch scores, recommendations, ML outputs, concordance results, adjudication results, or Gold Set status are supplied

## Packet IDs

| # | Packet ID |
|---:|---|
{rows}
"""


def _reviewer02_instructions() -> str:
    return """# DriftWatch Independent Human Review Instructions — Reviewer 02

## Purpose

Independently review each browser-extension version transition using only the evidence supplied in this package. Do not browse the DriftWatch repository or internal project artifacts. Do not search for project conclusions or attempt to discover Reviewer 01's decisions.

## Labels

- `BENIGN_TRANSITION`: the relevant security-sensitive changes have a documented legitimate purpose and no independent evidence supports harmful intent or unacceptable security behaviour.
- `RISKY_TRANSITION`: meaningful security-sensitive capability or behaviour was introduced and warrants security review, even when malicious intent is not proven.
- `MALICIOUS_TRANSITION`: use only when strong independent evidence supports intentionally harmful behaviour.
- `UNCERTAIN`: available evidence is insufficient or contradictory.
- `EXCLUDED`: the version pair cannot be validly reviewed.

Permission additions, obfuscation, source-to-sink heuristics, and network indicators require context and are not automatic proof of maliciousness or exfiltration. Risky does not mean malware.

## Confidence

- `HIGH`: strong evidence and clear interpretation.
- `MEDIUM`: reasonable evidence but meaningful ambiguity remains.
- `LOW`: weak or incomplete evidence.

## Required submission

For every case, edit only its matching file under `submissions/`. Do not edit packet files, `review_id`, `reviewer_id`, `record_id`, or `review_round`.

Supply:

- `independent_label`
- `confidence`
- `rationale`
- `evidence_references`
- `review_timestamp`

Set `review_status` to `SUBMITTED` and retain `blind_review=true`. Use `UNCERTAIN` rather than guessing when evidence is insufficient.
"""


def _pending_submission(record_id: str) -> dict[str, Any]:
    return {
        "review_id": derive_review_id(REVIEWER02_ID, record_id, INITIAL_BLIND),
        "reviewer_id": REVIEWER02_ID,
        "record_id": record_id,
        "review_round": INITIAL_BLIND,
        "independent_label": "",
        "confidence": "",
        "rationale": "",
        "evidence_references": [],
        "blind_review": True,
        "review_timestamp": "",
        "review_status": "PENDING",
    }


def _reviewer02_template() -> dict[str, Any]:
    return {
        "review_id": "",
        "reviewer_id": REVIEWER02_ID,
        "record_id": "",
        "review_round": INITIAL_BLIND,
        "independent_label": "",
        "confidence": "",
        "rationale": "",
        "evidence_references": [],
        "blind_review": True,
        "review_timestamp": "",
        "review_status": "PENDING",
    }


def audit_reviewer02_workspace(
    workspace: str | Path,
    holdout_ids: Iterable[str],
) -> dict[str, Any]:
    workspace = Path(workspace)
    packet_paths = sorted((workspace / "packets").glob("*.json"))
    submission_paths = sorted((workspace / "submissions").glob("*.json"))
    packets = [_json_from_bytes(path.read_bytes(), str(path)) for path in packet_paths]
    submissions = [_json_from_bytes(path.read_bytes(), str(path)) for path in submission_paths]
    packet_ids = [row.get("record_id") for row in packets]
    submission_ids = [row.get("record_id") for row in submissions]
    submission_errors: list[str] = []
    for path, submission in zip(submission_paths, submissions):
        errors = validate_pending_submission(
            submission,
            expected_reviewer_id=REVIEWER02_ID,
            expected_record_id=path.stem,
        )
        submission_errors.extend(f"{path.name}: {error}" for error in errors)

    forbidden_key_hits: list[dict[str, str]] = []
    reviewer01_hits: list[str] = []
    project_label_hits: list[dict[str, str]] = []
    for path, packet in zip(packet_paths, packets):
        for key in sorted(_collect_keys(packet) & FORBIDDEN_PACKET_KEYS):
            forbidden_key_hits.append({"file": path.name, "key": key})
        text = path.read_text(encoding="utf-8")
        if REVIEWER01_ID in text:
            reviewer01_hits.append(path.name)
        for label in LABEL_ONTOLOGY:
            if f'"{label}"' in text:
                project_label_hits.append({"file": path.name, "label": label})

    review_ids = [row.get("review_id") for row in submissions]
    holdout_overlap = sorted(set(packet_ids) & set(holdout_ids))
    allowed_files = {
        "PACKAGE_MANIFEST.md",
        "REVIEW_INSTRUCTIONS.md",
        "review_submission_template.json",
        *(f"packets/{path.name}" for path in packet_paths),
        *(f"submissions/{path.name}" for path in submission_paths),
    }
    actual_files = {
        path.relative_to(workspace).as_posix()
        for path in workspace.rglob("*")
        if path.is_file()
    }
    checks = {
        "packet_count_is_14": len(packets) == 14,
        "submission_count_is_14": len(submissions) == 14,
        "packet_submission_ids_match": sorted(packet_ids) == sorted(submission_ids),
        "record_ids_unique": len(set(packet_ids)) == 14 and len(set(submission_ids)) == 14,
        "review_ids_unique": len(set(review_ids)) == 14 and None not in review_ids,
        "pending_submissions_valid": not submission_errors,
        "external_holdout_overlap_zero": not holdout_overlap,
        "reviewer01_outcome_leakage_zero": not reviewer01_hits,
        "project_label_leakage_zero": not project_label_hits,
        "score_recommendation_ml_leakage_zero": not forbidden_key_hits,
        "contents_allowlisted": actual_files == allowed_files,
    }
    return {
        "schema_version": REVIEWER02_PACKAGE_SCHEMA_VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "packet_count": len(packets),
        "submission_count": len(submissions),
        "holdout_overlap": holdout_overlap,
        "submission_errors": submission_errors,
        "reviewer01_leakage_files": reviewer01_hits,
        "project_label_leakage_hits": project_label_hits,
        "forbidden_key_hits": forbidden_key_hits,
        "unexpected_or_missing_files": sorted(actual_files ^ allowed_files),
    }


def _create_deterministic_zip(workspace: Path, output_zip: Path) -> None:
    if output_zip.exists():
        raise FileExistsError(f"refusing to overwrite {output_zip}")
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in workspace.rglob("*") if item.is_file()):
            relative = path.relative_to(workspace).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build_reviewer02_package(
    bundle: Mapping[str, Any],
    *,
    workspace: str | Path,
    output_zip: str | Path,
    audit_output: str | Path,
    holdout_ids: Iterable[str],
) -> dict[str, Any]:
    workspace_path = _prepare_new_directory(workspace)
    packet_dir = workspace_path / "packets"
    submission_dir = workspace_path / "submissions"
    packet_dir.mkdir()
    submission_dir.mkdir()
    record_ids = sorted(record["record_id"] for record in bundle["records"])
    (workspace_path / "PACKAGE_MANIFEST.md").write_text(
        _reviewer02_manifest(record_ids), encoding="utf-8", newline="\n"
    )
    (workspace_path / "REVIEW_INSTRUCTIONS.md").write_text(
        _reviewer02_instructions(), encoding="utf-8", newline="\n"
    )
    _write_json(workspace_path / "review_submission_template.json", _reviewer02_template())

    by_id = {record["record_id"]: record for record in bundle["records"]}
    for record_id in record_ids:
        record = by_id[record_id]
        (packet_dir / f"{record_id}.json").write_bytes(record["packet_raw_bytes"])
        _write_json(submission_dir / f"{record_id}.json", _pending_submission(record_id))

    audit = audit_reviewer02_workspace(workspace_path, holdout_ids)
    if not audit["passed"]:
        raise HumanReviewIntegrationError(f"Reviewer 02 blinding audit failed: {audit}")
    output_zip_path = Path(output_zip)
    _create_deterministic_zip(workspace_path, output_zip_path)
    audit["package_path"] = str(output_zip_path)
    audit["package_sha256"] = sha256_file(output_zip_path)
    audit["package_file_count"] = len(
        [path for path in workspace_path.rglob("*") if path.is_file()]
    )
    _write_json(Path(audit_output), audit)
    return audit


def run_phase5b(
    *,
    raw_zip_path: str | Path,
    expected_sha256: str,
    dataset_manifest_path: str | Path,
    external_holdout_manifest_path: str | Path,
    reviewer01_output: str | Path,
    comparison_output: str | Path,
    reviewer02_workspace: str | Path,
    reviewer02_zip: str | Path,
    reviewer02_audit: str | Path,
) -> dict[str, Any]:
    bundle = load_and_validate_reviewer01_archive(
        raw_zip_path, expected_sha256=expected_sha256
    )
    reviewer01_report = write_reviewer01_derived_layer(bundle, reviewer01_output)
    concordance = write_human_vs_provisional_comparison(
        bundle, dataset_manifest_path, comparison_output
    )
    with Path(external_holdout_manifest_path).open(encoding="utf-8") as handle:
        holdout = json.load(handle)
    holdout_ids = [row["record_id"] for row in holdout.get("records", [])]
    reviewer02_report = build_reviewer02_package(
        bundle,
        workspace=reviewer02_workspace,
        output_zip=reviewer02_zip,
        audit_output=reviewer02_audit,
        holdout_ids=holdout_ids,
    )
    return {
        "reviewer01_validation": reviewer01_report,
        "concordance": concordance,
        "reviewer02_package_audit": reviewer02_report,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create governed derived human-review artifacts without changing raw evidence."
    )
    parser.add_argument(
        "--raw-zip",
        default="DriftWatch_Human_Review_Raw_Return_Reviewer01_2026-09-22.zip",
    )
    parser.add_argument("--expected-sha256", default=RAW_REVIEWER01_SHA256)
    parser.add_argument(
        "--dataset-manifest",
        default="artifacts/driftbench/phase3h/dataset_manifest.json",
    )
    parser.add_argument(
        "--external-holdout-manifest",
        default="artifacts/driftbench/phase3h/external_holdout_manifest.json",
    )
    parser.add_argument(
        "--reviewer01-output", default="artifacts/human_review/reviewer01"
    )
    parser.add_argument(
        "--comparison-output",
        default="artifacts/human_review/comparisons/reviewer01_vs_provisional",
    )
    parser.add_argument("--reviewer02-workspace", default="reviewer_human_02")
    parser.add_argument(
        "--reviewer02-zip",
        default="DriftWatch_Independent_Human_Review_Reviewer02_Package.zip",
    )
    parser.add_argument(
        "--reviewer02-audit",
        default="artifacts/human_review/reviewer02/package_audit.json",
    )
    args = parser.parse_args()
    result = run_phase5b(
        raw_zip_path=args.raw_zip,
        expected_sha256=args.expected_sha256,
        dataset_manifest_path=args.dataset_manifest,
        external_holdout_manifest_path=args.external_holdout_manifest,
        reviewer01_output=args.reviewer01_output,
        comparison_output=args.comparison_output,
        reviewer02_workspace=args.reviewer02_workspace,
        reviewer02_zip=args.reviewer02_zip,
        reviewer02_audit=args.reviewer02_audit,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
