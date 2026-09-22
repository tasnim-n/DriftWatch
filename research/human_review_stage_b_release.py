from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from research.human_review_adjudication import (
    ADJUDICATION_ID_POLICY_VERSION,
    ADJUDICATION_POLICY_VERSION,
    ADJUDICATION_SCHEMA_VERSION,
    DEFAULT_ADJUDICATOR_ID,
    EXPECTED_DISAGREEMENT_IDS,
    ML_KEYS,
    PROJECT_LABEL_KEYS,
    RECOMMENDATION_KEYS,
    SCORE_KEYS,
    STAGE_A,
    STAGE_B,
    HumanReviewAdjudicationError,
    _collect_keys,
    _stage_b_submission,
    derive_adjudication_review_id,
    evaluate_stage_b_release_gate,
    validate_completed_stage_a_submission,
)
from research.human_review_integration import (
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


RAW_STAGE_A_SHA256 = "C66C3D5349F701BE4ECA75C049BB0382E105B79B801F2737D7069BDBD26A11DC"
STAGE_A_TIMESTAMP_PROVENANCE = "actual file-finalization time"
STAGE_B_RELEASE_SCHEMA_VERSION = "driftwatch-stage-a-validation-stage-b-release-v1"
ADJUDICATOR_WORKFLOW_ID = "ADJWF1::human_adjudicator_01::FIVE_CASE_TWO_STAGE"

EXPECTED_STAGE_A_JUDGMENTS = {
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


def load_and_validate_stage_a_return(
    raw_zip_path: str | Path,
    *,
    adjudicator_workspace: str | Path,
    expected_sha256: str = RAW_STAGE_A_SHA256,
    expected_ids: Sequence[str] = EXPECTED_DISAGREEMENT_IDS,
    expected_judgments: Mapping[str, tuple[str, str]] = EXPECTED_STAGE_A_JUDGMENTS,
) -> dict[str, Any]:
    raw_zip_path = Path(raw_zip_path)
    workspace = Path(adjudicator_workspace)
    source_sha256 = verify_file_sha256(raw_zip_path, expected_sha256)
    packet_manifest = _read_json(workspace / "metadata" / "stage_a_packet_manifest.json")
    packet_sources = {row["record_id"]: row for row in packet_manifest["records"]}
    expected_id_set = set(expected_ids)
    if set(packet_sources) != expected_id_set:
        raise HumanReviewAdjudicationError(
            "Phase 5D Stage A packet manifest differs from the governed disagreement set"
        )

    entries: dict[str, dict[str, Any]] = {}
    review_ids: set[str] = set()
    with zipfile.ZipFile(raw_zip_path, "r") as archive:
        file_infos = [info for info in archive.infolist() if not info.is_dir()]
        if len(file_infos) != 5:
            raise HumanReviewAdjudicationError(
                f"authoritative Stage A ZIP must contain exactly 5 files, got {len(file_infos)}"
            )
        for info in file_infos:
            normalized = str(PurePosixPath(info.filename.replace("\\", "/")))
            if not normalized.startswith("submissions/") or not normalized.endswith(".json"):
                raise HumanReviewAdjudicationError(
                    f"unexpected authoritative Stage A entry {normalized}"
                )
            raw = archive.read(info)
            submission = _json_from_bytes(raw, normalized)
            record_id = submission.get("record_id")
            if not isinstance(record_id, str) or not record_id:
                raise HumanReviewAdjudicationError(f"record_id missing from {normalized}")
            if Path(normalized).stem != record_id:
                raise HumanReviewAdjudicationError(
                    f"filename/record_id mismatch in {normalized}: {record_id}"
                )
            if record_id in entries:
                raise HumanReviewAdjudicationError(f"duplicate Stage A record_id {record_id}")
            review_id = submission.get("review_id")
            if not isinstance(review_id, str) or not review_id:
                raise HumanReviewAdjudicationError(f"review_id missing for {record_id}")
            if review_id in review_ids:
                raise HumanReviewAdjudicationError(f"duplicate Stage A review_id {review_id}")
            review_ids.add(review_id)

            packet_path = workspace / "STAGE_A" / "packets" / f"{record_id}.json"
            if not packet_path.is_file():
                raise HumanReviewAdjudicationError(
                    f"original Stage A packet missing for {record_id}"
                )
            packet_hash = sha256_file(packet_path)
            expected_packet_hash = packet_sources.get(record_id, {}).get("sha256")
            if packet_hash != expected_packet_hash:
                raise HumanReviewAdjudicationError(
                    f"Phase 5D Stage A packet hash mismatch for {record_id}"
                )
            packet = _read_json(packet_path)
            errors = validate_completed_stage_a_submission(
                submission,
                packet,
                record_id,
                DEFAULT_ADJUDICATOR_ID,
                expected_timestamp_provenance=STAGE_A_TIMESTAMP_PROVENANCE,
            )
            if errors:
                raise HumanReviewAdjudicationError(
                    f"{record_id}: {'; '.join(errors)}"
                )
            actual_judgment = (
                submission["adjudicator_initial_label"],
                submission["adjudicator_initial_confidence"],
            )
            if actual_judgment != expected_judgments.get(record_id):
                raise HumanReviewAdjudicationError(
                    f"Stage A judgment differs from the expected authoritative set for {record_id}"
                )
            entries[record_id] = {
                "record_id": record_id,
                "review_id": review_id,
                "entry_name": normalized,
                "entry_sha256": sha256_bytes(raw),
                "submission": submission,
                "packet_path": str(packet_path),
                "packet_sha256": packet_hash,
                "packet": packet,
            }

    if set(entries) != expected_id_set:
        raise HumanReviewAdjudicationError(
            f"Stage A record set mismatch: expected {sorted(expected_id_set)}, got {sorted(entries)}"
        )
    return {
        "schema_version": STAGE_B_RELEASE_SCHEMA_VERSION,
        "raw_source_path": str(raw_zip_path),
        "raw_source_filename": raw_zip_path.name,
        "raw_source_sha256": source_sha256,
        "submission_count": len(entries),
        "unique_review_id_count": len(review_ids),
        "adjudicator_id": DEFAULT_ADJUDICATOR_ID,
        "adjudicator_workflow_id": ADJUDICATOR_WORKFLOW_ID,
        "timestamp_provenance": STAGE_A_TIMESTAMP_PROVENANCE,
        "records": [entries[record_id] for record_id in sorted(entries)],
    }


def write_stage_a_validation_layer(
    bundle: Mapping[str, Any], output_root: str | Path
) -> dict[str, Any]:
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=False)
    validated = output / "validated_submissions"
    validated.mkdir()
    validation_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    provenance_records: list[dict[str, Any]] = []
    for record in bundle["records"]:
        wrapper = {
            "schema_version": STAGE_B_RELEASE_SCHEMA_VERSION,
            "validation_status": "VALIDATED_AUTHORITATIVE_STAGE_A",
            "policy_version": ADJUDICATION_POLICY_VERSION,
            "review_id_policy_version": ADJUDICATION_ID_POLICY_VERSION,
            "adjudicator_workflow_id": bundle["adjudicator_workflow_id"],
            "raw_source_filename": bundle["raw_source_filename"],
            "raw_source_sha256": bundle["raw_source_sha256"],
            "raw_entry_name": record["entry_name"],
            "raw_entry_sha256": record["entry_sha256"],
            "stage_a_review_id": record["review_id"],
            "packet_sha256": record["packet_sha256"],
            "timestamp_provenance": bundle["timestamp_provenance"],
            "validation_timestamp": validation_timestamp,
            "original_submission": record["submission"],
        }
        _write_json(validated / f"{record['record_id']}.json", wrapper)
        provenance_records.append(
            {
                "record_id": record["record_id"],
                "stage_a_review_id": record["review_id"],
                "raw_entry_name": record["entry_name"],
                "raw_entry_sha256": record["entry_sha256"],
                "packet_sha256": record["packet_sha256"],
                "timestamp_provenance": bundle["timestamp_provenance"],
            }
        )

    labels = Counter(
        record["submission"]["adjudicator_initial_label"]
        for record in bundle["records"]
    )
    confidence = Counter(
        record["submission"]["adjudicator_initial_confidence"]
        for record in bundle["records"]
    )
    validation_report = {
        "schema_version": STAGE_B_RELEASE_SCHEMA_VERSION,
        "status": "VALIDATED_AUTHORITATIVE_STAGE_A",
        "validated_submission_count": len(bundle["records"]),
        "unique_record_id_count": len(
            {record["record_id"] for record in bundle["records"]}
        ),
        "unique_review_id_count": len(
            {record["review_id"] for record in bundle["records"]}
        ),
        "adjudicator_id": bundle["adjudicator_id"],
        "review_round": STAGE_A,
        "label_distribution": dict(sorted(labels.items())),
        "confidence_distribution": dict(sorted(confidence.items())),
        "packet_hash_linkage_passed": True,
        "evidence_references_resolved": True,
        "timestamp_provenance": bundle["timestamp_provenance"],
        "timestamp_interpretation": (
            "Actual file-finalization metadata only; not a review-duration measurement."
        ),
        "raw_human_fields_modified": False,
        "project_labels_added": False,
        "validation_timestamp": validation_timestamp,
    }
    _write_json(
        output / "RAW_SOURCE_METADATA.json",
        {
            "schema_version": STAGE_B_RELEASE_SCHEMA_VERSION,
            "raw_source_filename": bundle["raw_source_filename"],
            "raw_source_sha256": bundle["raw_source_sha256"],
            "immutable_source": True,
            "raw_source_modified": False,
            "submission_count": bundle["submission_count"],
            "timestamp_provenance": bundle["timestamp_provenance"],
        },
    )
    _write_json(output / "validation_report.json", validation_report)
    _write_json(
        output / "provenance_manifest.json",
        {
            "schema_version": STAGE_B_RELEASE_SCHEMA_VERSION,
            "policy_version": ADJUDICATION_POLICY_VERSION,
            "review_id_policy_version": ADJUDICATION_ID_POLICY_VERSION,
            "adjudicator_workflow_id": bundle["adjudicator_workflow_id"],
            "raw_source_sha256": bundle["raw_source_sha256"],
            "record_count": len(provenance_records),
            "superseded_stage_a_returns_used": False,
            "records": provenance_records,
        },
    )
    return validation_report


def _stage_b_manifest() -> str:
    return """# DriftWatch Human Adjudication — Stage B Package

- Project: DriftWatch
- Purpose: governed Stage B adjudication
- Case count: 5
- Stage A was completed, validated, and preserved before Stage B release
- Reviewer A and Reviewer B identities are intentionally hidden
- Previous human opinions are advisory evidence, not ground truth
- Final adjudication must remain evidence-based; majority voting is not required
- `UNCERTAIN` remains an acceptable final outcome
- An adjudicated result does not automatically create a Gold Set
- The original reviews and Stage A assessments remain immutable

Use only the supplied case files and matching blank submissions. Do not attempt to identify Reviewer A or Reviewer B.
"""


def _stage_b_instructions() -> str:
    return """# DriftWatch Governed Adjudication — Stage B Instructions

Stage A has been completed and preserved. For each case you now receive the original blind evidence, your immutable Stage A assessment, and two de-identified prior human-review opinions.

Reconsider each case using all three evidence sources. Reviewer A and Reviewer B identities are intentionally hidden. Their opinions are advisory and are not ground truth. Do not attempt to identify them, and do not decide by majority vote.

Use exactly one final label: `BENIGN_TRANSITION`, `RISKY_TRANSITION`, `UNCERTAIN`, `MALICIOUS_TRANSITION`, or `EXCLUDED`. `UNCERTAIN` remains valid when evidence is insufficient. `RISKY_TRANSITION` does not mean maliciousness, and `MALICIOUS_TRANSITION` requires strong supplied evidence of intentional harm.

For each matching file in `submissions/`, provide the final label, confidence (`HIGH`, `MEDIUM`, or `LOW`), rationale, evidence references, whether your Stage A assessment changed, a change reason when applicable, a resolution basis, and a timestamp. Set `review_status` to `SUBMITTED`. Do not modify identifiers, linkage hashes, case files, or source opinions.
"""


def _validate_prepared_opinions(
    *,
    phase5d_workspace: Path,
    expected_ids: Sequence[str],
    reviewer01_bundle: Mapping[str, Any],
    reviewer02_bundle: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    opinion_root = phase5d_workspace / "STAGE_B" / "reviewer_opinions"
    opinion_paths = sorted(opinion_root.glob("*.json"))
    if {path.stem for path in opinion_paths} != set(expected_ids):
        raise HumanReviewAdjudicationError(
            "prepared Stage B opinion case set differs from the governed five"
        )
    private_mapping = _read_json(
        phase5d_workspace / "metadata" / "reviewer_alias_mapping.json"
    )
    mapping_by_id = {row["record_id"]: row["aliases"] for row in private_mapping["records"]}
    bundles_by_reviewer = {
        REVIEWER01_ID: {
            record["record_id"]: record for record in reviewer01_bundle["records"]
        },
        REVIEWER02_ID: {
            record["record_id"]: record for record in reviewer02_bundle["records"]
        },
    }
    validated: dict[str, dict[str, Any]] = {}
    for path in opinion_paths:
        record_id = path.stem
        payload = _read_json(path)
        if payload.get("record_id") != record_id:
            raise HumanReviewAdjudicationError(
                f"prepared Stage B opinion record mismatch in {path}"
            )
        opinions = payload.get("opinions")
        if not isinstance(opinions, Mapping) or set(opinions) != {
            "Reviewer A",
            "Reviewer B",
        }:
            raise HumanReviewAdjudicationError(
                f"prepared Stage B opinions must contain Reviewer A and Reviewer B for {record_id}"
            )
        for alias in ("Reviewer A", "Reviewer B"):
            opinion = opinions[alias]
            if set(opinion) != {"label", "confidence", "rationale", "evidence_references"}:
                raise HumanReviewAdjudicationError(
                    f"unexpected de-identified opinion fields for {record_id} {alias}"
                )
            reviewer_id = mapping_by_id[record_id][alias]["reviewer_id"]
            original = bundles_by_reviewer[reviewer_id][record_id]["submission"]
            expected = {
                "label": original["independent_label"],
                "confidence": original["confidence"],
                "rationale": original["rationale"],
                "evidence_references": original["evidence_references"],
            }
            if opinion != expected:
                raise HumanReviewAdjudicationError(
                    f"prepared Stage B opinion is not verbatim for {record_id} {alias}"
                )
        public_text = json.dumps(payload, ensure_ascii=False)
        if REVIEWER01_ID in public_text or REVIEWER02_ID in public_text:
            raise HumanReviewAdjudicationError(
                f"reviewer identity leaked in prepared Stage B opinion for {record_id}"
            )
        validated[record_id] = payload
    return validated


def _create_deterministic_zip(workspace: Path, output_zip: Path) -> None:
    if output_zip.exists():
        raise FileExistsError(f"refusing to overwrite {output_zip}")
    entries = [
        path
        for path in workspace.rglob("*")
        if path.is_file() and path.relative_to(workspace).parts[0] != "metadata"
    ]
    with zipfile.ZipFile(
        output_zip, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(entries, key=lambda item: item.relative_to(workspace).as_posix()):
            relative = path.relative_to(workspace).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info,
                path.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )


def create_stage_b_release_workspace(
    *,
    output_root: str | Path,
    phase5d_workspace: str | Path,
    stage_a_bundle: Mapping[str, Any],
    gate: Mapping[str, Any],
    reviewer01_bundle: Mapping[str, Any],
    reviewer02_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    if gate.get("status") != "RELEASABLE":
        raise HumanReviewAdjudicationError(
            "Stage B cannot be constructed unless the release gate is RELEASABLE"
        )
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=False)
    cases = output / "cases"
    submissions = output / "submissions"
    metadata = output / "metadata"
    cases.mkdir()
    submissions.mkdir()
    metadata.mkdir()
    (output / "PACKAGE_MANIFEST.md").write_text(
        _stage_b_manifest(), encoding="utf-8", newline="\n"
    )
    (output / "REVIEW_INSTRUCTIONS.md").write_text(
        _stage_b_instructions(), encoding="utf-8", newline="\n"
    )
    expected_ids = [record["record_id"] for record in stage_a_bundle["records"]]
    opinions = _validate_prepared_opinions(
        phase5d_workspace=Path(phase5d_workspace),
        expected_ids=expected_ids,
        reviewer01_bundle=reviewer01_bundle,
        reviewer02_bundle=reviewer02_bundle,
    )
    for record in stage_a_bundle["records"]:
        record_id = record["record_id"]
        opinion = opinions[record_id]["opinions"]
        case = {
            "schema_version": STAGE_B_RELEASE_SCHEMA_VERSION,
            "record_id": record_id,
            "sections": {
                "ORIGINAL_BLIND_EVIDENCE": record["packet"],
                "MY_STAGE_A_ASSESSMENT": {
                    "source_review_id": record["review_id"],
                    "source_submission_sha256": record["entry_sha256"],
                    "assessment": record["submission"],
                },
                "REVIEWER_A_OPINION": opinion["Reviewer A"],
                "REVIEWER_B_OPINION": opinion["Reviewer B"],
            },
        }
        _write_json(cases / f"{record_id}.json", case)
        _write_json(
            submissions / f"{record_id}.json",
            _stage_b_submission(
                record_id,
                DEFAULT_ADJUDICATOR_ID,
                stage_a_submission_sha256=record["entry_sha256"],
            ),
        )
    _write_json(
        metadata / "stage_b_release_provenance.json",
        {
            "schema_version": STAGE_B_RELEASE_SCHEMA_VERSION,
            "policy_version": ADJUDICATION_POLICY_VERSION,
            "gate_status": gate["status"],
            "stage_a_raw_source_sha256": stage_a_bundle["raw_source_sha256"],
            "case_count": len(expected_ids),
            "private_alias_mapping_in_reviewer_package": False,
            "stage_b_submissions_completed": False,
            "final_adjudication_performed": False,
            "gold_set_created": False,
        },
    )
    return {
        "workspace": str(output),
        "case_count": len(list(cases.glob("*.json"))),
        "submission_count": len(list(submissions.glob("*.json"))),
    }


def audit_stage_b_package(
    package_zip: str | Path,
    *,
    expected_ids: Sequence[str] = EXPECTED_DISAGREEMENT_IDS,
) -> dict[str, Any]:
    package_zip = Path(package_zip)
    cases: dict[str, dict[str, Any]] = {}
    submissions: dict[str, dict[str, Any]] = {}
    names: list[str] = []
    all_text: list[str] = []
    with zipfile.ZipFile(package_zip, "r") as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            normalized = str(PurePosixPath(info.filename.replace("\\", "/")))
            raw = archive.read(info)
            text = raw.decode("utf-8-sig")
            names.append(normalized)
            all_text.append(text)
            if normalized.startswith("cases/") and normalized.endswith(".json"):
                cases[Path(normalized).stem] = json.loads(text)
            if normalized.startswith("submissions/") and normalized.endswith(".json"):
                submissions[Path(normalized).stem] = json.loads(text)

    expected_id_set = set(expected_ids)
    case_keys = set().union(*(_collect_keys(case) for case in cases.values()))
    package_text = "\n".join(all_text)
    package_text_lower = package_text.lower()
    answer_fields = {
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
    pending_errors: list[str] = []
    for record_id, submission in submissions.items():
        for field, expected in answer_fields.items():
            if submission.get(field) != expected:
                pending_errors.append(
                    f"{record_id}: {field} must equal {expected!r}"
                )
        if submission.get("review_round") != STAGE_B:
            pending_errors.append(f"{record_id}: invalid Stage B review_round")
        if submission.get("stage_a_review_id") != derive_adjudication_review_id(
            DEFAULT_ADJUDICATOR_ID, record_id, STAGE_A
        ):
            pending_errors.append(f"{record_id}: invalid Stage A review linkage")
        if not submission.get("stage_a_submission_sha256"):
            pending_errors.append(f"{record_id}: Stage A source hash linkage missing")

    allowed_names = {
        "PACKAGE_MANIFEST.md",
        "REVIEW_INSTRUCTIONS.md",
        *(f"cases/{record_id}.json" for record_id in expected_id_set),
        *(f"submissions/{record_id}.json" for record_id in expected_id_set),
    }
    checks = {
        "case_count_is_5": len(cases) == 5,
        "submission_count_is_5": len(submissions) == 5,
        "case_and_submission_ids_exact": set(cases)
        == set(submissions)
        == expected_id_set,
        "stage_b_submissions_blank_pending": not pending_errors,
        "reviewer01_identity_hidden": REVIEWER01_ID not in package_text,
        "reviewer02_identity_hidden": REVIEWER02_ID not in package_text,
        "project_labels_hidden": not (case_keys & PROJECT_LABEL_KEYS)
        and not any(
            f'"{label}"' in package_text
            for label in (
                "benign_transition",
                "risky_transition",
                "malicious_transition",
                "controlled_malicious_transition",
                "needs_review",
                "uncertain",
                "excluded",
            )
        ),
        "driftwatch_scores_hidden": not (case_keys & SCORE_KEYS),
        "recommendations_hidden": not (case_keys & RECOMMENDATION_KEYS),
        "ml_outputs_hidden": not (case_keys & ML_KEYS),
        "agreement_percentage_hidden": "64.29" not in package_text
        and "9/14" not in package_text
        and "percent_exact_agreement" not in package_text,
        "cohens_kappa_hidden": "cohen" not in package_text_lower
        and "kappa" not in package_text_lower
        and "0.3396" not in package_text,
        "private_alias_mapping_hidden": "human_reviewer_" not in package_text
        and "reviewer_alias_mapping" not in package_text_lower
        and "raw_submission_entry_name" not in package_text,
        "superseded_attempts_absent": "superseded" not in package_text_lower
        and "corrected package" not in package_text_lower
        and "redo" not in package_text_lower,
        "gold_set_decision_absent": "gold_set_status" not in package_text
        and "ready for governed adjudication" not in package_text_lower,
        "contents_allowlisted": set(names) == allowed_names,
    }
    return {
        "schema_version": STAGE_B_RELEASE_SCHEMA_VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "case_count": len(cases),
        "submission_count": len(submissions),
        "record_ids": sorted(cases),
        "pending_submission_errors": pending_errors,
        "package_sha256": sha256_file(package_zip),
        "zip_entries": sorted(names),
    }


def build_stage_b_package(
    *,
    release_workspace: str | Path,
    output_zip: str | Path,
    checksum_path: str | Path,
    expected_ids: Sequence[str] = EXPECTED_DISAGREEMENT_IDS,
) -> dict[str, Any]:
    release_workspace = Path(release_workspace)
    output_zip = Path(output_zip)
    checksum_path = Path(checksum_path)
    if checksum_path.exists():
        raise FileExistsError(f"refusing to overwrite {checksum_path}")
    _create_deterministic_zip(release_workspace, output_zip)
    audit = audit_stage_b_package(output_zip, expected_ids=expected_ids)
    if not audit["passed"]:
        raise HumanReviewAdjudicationError(f"Stage B package audit failed: {audit}")
    checksum_path.write_text(
        f"{audit['package_sha256']}  {output_zip.name}\n",
        encoding="ascii",
        newline="\n",
    )
    _write_json(release_workspace / "metadata" / "stage_b_package_audit.json", audit)
    return audit


def run_phase5e(
    *,
    stage_a_raw_zip: str | Path,
    phase5d_workspace: str | Path,
    stage_a_validation_output: str | Path,
    reviewer01_zip: str | Path,
    reviewer02_zip: str | Path,
    reviewer02_packet_root: str | Path,
    stage_b_release_workspace: str | Path,
    stage_b_zip: str | Path,
    stage_b_checksum: str | Path,
) -> dict[str, Any]:
    stage_a_bundle = load_and_validate_stage_a_return(
        stage_a_raw_zip,
        adjudicator_workspace=phase5d_workspace,
        expected_sha256=RAW_STAGE_A_SHA256,
    )
    validation_report = write_stage_a_validation_layer(
        stage_a_bundle, stage_a_validation_output
    )
    submission_records = {
        record["record_id"]: record["submission"]
        for record in stage_a_bundle["records"]
    }
    submission_hashes = {
        record["record_id"]: record["entry_sha256"]
        for record in stage_a_bundle["records"]
    }
    gate = evaluate_stage_b_release_gate(
        phase5d_workspace,
        submission_records=submission_records,
        source_submission_hashes=submission_hashes,
        expected_timestamp_provenance=STAGE_A_TIMESTAMP_PROVENANCE,
    )
    _write_json(Path(stage_a_validation_output) / "stage_b_release_gate.json", gate)
    if gate["status"] != "RELEASABLE":
        raise HumanReviewAdjudicationError(
            f"Stage B release gate did not pass: {gate}"
        )

    reviewer01_bundle = load_and_validate_reviewer01_archive(
        reviewer01_zip, expected_sha256=RAW_REVIEWER01_SHA256
    )
    reviewer02_bundle = load_and_validate_reviewer02_archive(
        reviewer02_zip,
        packet_root=reviewer02_packet_root,
        expected_sha256=RAW_REVIEWER02_SHA256,
    )
    release_report = create_stage_b_release_workspace(
        output_root=stage_b_release_workspace,
        phase5d_workspace=phase5d_workspace,
        stage_a_bundle=stage_a_bundle,
        gate=gate,
        reviewer01_bundle=reviewer01_bundle,
        reviewer02_bundle=reviewer02_bundle,
    )
    package_audit = build_stage_b_package(
        release_workspace=stage_b_release_workspace,
        output_zip=stage_b_zip,
        checksum_path=stage_b_checksum,
    )
    return {
        "stage_a_validation": validation_report,
        "stage_b_release_gate": gate,
        "stage_b_release_workspace": release_report,
        "stage_b_package_audit": package_audit,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate authoritative Stage A and release the governed Stage B package."
    )
    parser.add_argument(
        "--stage-a-raw-zip",
        default="DriftWatch_Human_Adjudication_StageA_Raw_Return_2026-09-22.zip",
    )
    parser.add_argument("--phase5d-workspace", default="reviewer_human_adjudicator")
    parser.add_argument(
        "--stage-a-validation-output",
        default="artifacts/human_review/adjudication/stage_a",
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
        "--stage-b-release-workspace", default="reviewer_human_adjudicator_stage_b"
    )
    parser.add_argument(
        "--stage-b-zip", default="DriftWatch_Human_Adjudication_StageB_Package.zip"
    )
    parser.add_argument(
        "--stage-b-checksum",
        default="DriftWatch_Human_Adjudication_StageB_Package.sha256",
    )
    args = parser.parse_args()
    result = run_phase5e(
        stage_a_raw_zip=args.stage_a_raw_zip,
        phase5d_workspace=args.phase5d_workspace,
        stage_a_validation_output=args.stage_a_validation_output,
        reviewer01_zip=args.reviewer01_zip,
        reviewer02_zip=args.reviewer02_zip,
        reviewer02_packet_root=args.reviewer02_packet_root,
        stage_b_release_workspace=args.stage_b_release_workspace,
        stage_b_zip=args.stage_b_zip,
        stage_b_checksum=args.stage_b_checksum,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
