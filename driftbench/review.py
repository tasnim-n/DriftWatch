from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence

from driftbench.labels import LABEL_REVIEW_STATUSES, is_valid_label


@dataclass
class ManualReview:
    record_id: str
    reviewer_id: str
    assigned_label: str
    confidence: str
    rationale: str
    evidence_examined: List[str] = field(default_factory=list)
    permissions_notes: str | None = None
    host_changes_notes: str | None = None
    api_notes: str | None = None
    network_notes: str | None = None
    obfuscation_notes: str | None = None
    structural_notes: str | None = None
    documented_release_purpose: str | None = None
    external_evidence_source: str | None = None
    review_timestamp: str = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat())
    review_status: str = "provisional"

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.record_id:
            errors.append("record_id is required")
        if not self.reviewer_id:
            errors.append("reviewer_id is required")
        if not is_valid_label(self.assigned_label):
            errors.append("assigned_label is invalid")
        if self.review_status not in LABEL_REVIEW_STATUSES:
            errors.append("review_status is invalid")
        if not self.rationale:
            errors.append("rationale is required")
        return errors

    def to_dict(self) -> Dict:
        return {
            "record_id": self.record_id,
            "reviewer_id": self.reviewer_id,
            "review_timestamp": self.review_timestamp,
            "evidence_examined": list(self.evidence_examined),
            "permissions_notes": self.permissions_notes,
            "host_changes_notes": self.host_changes_notes,
            "api_notes": self.api_notes,
            "network_notes": self.network_notes,
            "obfuscation_notes": self.obfuscation_notes,
            "structural_notes": self.structural_notes,
            "documented_release_purpose": self.documented_release_purpose,
            "external_evidence_source": self.external_evidence_source,
            "assigned_label": self.assigned_label,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "review_status": self.review_status,
        }


def write_review(path: str | Path, review: ManualReview) -> None:
    errors = review.validate()
    if errors:
        raise ValueError("; ".join(errors))
    Path(path).write_text(json.dumps(review.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


@dataclass
class ReviewPacket:
    record_id: str
    extension_id: str
    extension_name: str
    old_version: str
    new_version: str
    release_notes: List[str]
    source_metadata: Dict[str, Any]
    permission_changes: Dict[str, Any]
    host_changes: Dict[str, Any]
    api_changes: Dict[str, Any]
    network_changes: Dict[str, Any]
    obfuscation_changes: Dict[str, Any]
    structural_changes: Dict[str, Any]
    external_evidence: List[str]
    current_label: str
    current_label_confidence: str
    current_rationale: str
    uncertainty_rationale: str
    allowed_resolution_options: List[str] = field(default_factory=lambda: [
        "benign_transition",
        "risky_transition",
        "malicious_transition",
        "uncertain",
        "excluded",
    ])
    generated_timestamp: str = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat())

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.record_id:
            errors.append("record_id is required")
        if not self.extension_id:
            errors.append("extension_id is required")
        if not is_valid_label(self.current_label):
            errors.append("current_label is invalid")
        if not self.uncertainty_rationale:
            errors.append("uncertainty_rationale is required")
        for option in self.allowed_resolution_options:
            if not is_valid_label(option):
                errors.append(f"invalid resolution option {option!r}")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "extension_id": self.extension_id,
            "extension_name": self.extension_name,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "release_notes": list(self.release_notes),
            "source_metadata": dict(self.source_metadata),
            "permission_changes": dict(self.permission_changes),
            "host_changes": dict(self.host_changes),
            "api_changes": dict(self.api_changes),
            "network_changes": dict(self.network_changes),
            "obfuscation_changes": dict(self.obfuscation_changes),
            "structural_changes": dict(self.structural_changes),
            "external_evidence": list(self.external_evidence),
            "current_label": self.current_label,
            "current_label_confidence": self.current_label_confidence,
            "current_rationale": self.current_rationale,
            "uncertainty_rationale": self.uncertainty_rationale,
            "allowed_resolution_options": list(self.allowed_resolution_options),
            "generated_timestamp": self.generated_timestamp,
        }


@dataclass
class AdjudicationRecord:
    record_id: str
    reviewer_labels: List[Dict[str, Any]]
    disagreement_status: str
    adjudicated_label: str | None
    adjudication_rationale: str | None
    adjudicator_id: str | None = None
    adjudication_timestamp: str | None = None

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.record_id:
            errors.append("record_id is required")
        if self.disagreement_status not in {"pending", "agreement", "disagreement", "adjudicated"}:
            errors.append("disagreement_status is invalid")
        reviewer_ids = [item.get("reviewer_id") for item in self.reviewer_labels]
        if len([value for value in reviewer_ids if value]) != len(set(value for value in reviewer_ids if value)):
            errors.append("reviewer_id values must be unique")
        for item in self.reviewer_labels:
            if not item.get("reviewer_id"):
                errors.append("reviewer_id is required")
            if not is_valid_label(item.get("reviewer_label", "")):
                errors.append("reviewer_label is invalid")
            if not item.get("rationale"):
                errors.append("reviewer rationale is required")
        if self.adjudicated_label is not None and not is_valid_label(self.adjudicated_label):
            errors.append("adjudicated_label is invalid")
        if self.disagreement_status == "adjudicated" and not self.adjudication_rationale:
            errors.append("adjudication_rationale is required after adjudication")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "reviewer_labels": list(self.reviewer_labels),
            "disagreement_status": self.disagreement_status,
            "adjudicated_label": self.adjudicated_label,
            "adjudication_rationale": self.adjudication_rationale,
            "adjudicator_id": self.adjudicator_id,
            "adjudication_timestamp": self.adjudication_timestamp,
        }


def write_review_packet(path: str | Path, packet: ReviewPacket) -> None:
    errors = packet.validate()
    if errors:
        raise ValueError("; ".join(errors))
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(packet.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def write_review_queue(path: str | Path, packets: Sequence[ReviewPacket]) -> Dict[str, Any]:
    payload = {
        "schema_version": "driftbench-review-queue-v1",
        "generated_timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "packet_count": len(packets),
        "records": [packet.to_dict() for packet in packets],
        "adjudication_template": {
            "record_id": "",
            "reviewer_labels": [
                {
                    "reviewer_id": "",
                    "reviewer_label": "",
                    "reviewer_confidence": "",
                    "rationale": "",
                    "timestamp": "",
                }
            ],
            "disagreement_status": "pending",
            "adjudicated_label": None,
            "adjudication_rationale": None,
            "adjudicator_id": None,
            "adjudication_timestamp": None,
        },
    }
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload
