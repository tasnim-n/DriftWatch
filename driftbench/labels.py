from enum import Enum
from typing import Dict, Any


class Label(str, Enum):
    BENIGN = "benign_transition"
    RISKY = "risky_transition"
    MALICIOUS_TRANSITION = "malicious_transition"
    CONTROLLED_MALICIOUS = "controlled_malicious_transition"
    NEEDS_REVIEW = "needs_review"
    UNCERTAIN = "uncertain"
    EXCLUDED = "excluded"


LABEL_ONTOLOGY: Dict[str, Dict[str, Any]] = {
    Label.BENIGN.value: {
        "severity_order": 0,
        "definition": "A version transition with no meaningful new security or privacy-sensitive capability.",
        "decision_rule": "No new sensitive permissions, broad hosts, sensitive APIs, external destinations, obfuscation, or source-to-sink heuristic indicators.",
        "allowed_for_training": True,
    },
    Label.RISKY.value: {
        "severity_order": 1,
        "definition": "A transition that introduces security- or privacy-relevant capability expansion requiring analyst review.",
        "decision_rule": "Evidence may include permission creep, host expansion, new sensitive APIs, network destinations, obfuscation, or structural source-to-sink heuristics.",
        "allowed_for_training": True,
    },
    Label.MALICIOUS_TRANSITION.value: {
        "severity_order": 2,
        "definition": "A real-world transition with defensible external evidence that malicious behavior or intent was introduced.",
        "decision_rule": "Requires a reputable security report, peer-reviewed dataset label, or comparable external evidence. DriftWatch's own score must not be used as ground truth.",
        "allowed_for_training": True,
    },
    Label.CONTROLLED_MALICIOUS.value: {
        "severity_order": 2,
        "definition": "A synthetic laboratory transition intentionally constructed to model malicious capability patterns without deployable malware.",
        "decision_rule": "Must be generated from controlled samples or mutation tooling and must not contain real credential theft, exploit payloads, or live exfiltration infrastructure.",
        "allowed_for_training": False,
    },
    Label.NEEDS_REVIEW.value: {
        "severity_order": -1,
        "definition": "A transition with insufficient or conflicting evidence for a defensible label.",
        "decision_rule": "May be retained for audit trails but must be excluded from supervised model training until reviewed.",
        "allowed_for_training": False,
    },
    Label.UNCERTAIN.value: {
        "severity_order": -1,
        "definition": "Evidence is insufficient, contradictory, or ambiguous.",
        "decision_rule": "Retain for curation/review only; do not force into benign/risky/malicious classes.",
        "allowed_for_training": False,
    },
    Label.EXCLUDED.value: {
        "severity_order": -2,
        "definition": "Record fails methodology, provenance, integrity, licensing, or quality gates.",
        "decision_rule": "Retain only in exclusion reports; do not use for supervised training.",
        "allowed_for_training": False,
    },
}

LABEL_SOURCE_CATEGORIES = {
    "controlled_ground_truth": {"reliability_order": 5, "description": "Synthetic DriftWatch-controlled laboratory label."},
    "peer_reviewed_dataset_label": {"reliability_order": 4, "description": "Label from a peer-reviewed or curated public research dataset."},
    "reputable_security_report": {"reliability_order": 4, "description": "Label supported by an external security advisory or reputable report."},
    "repository_documented_change": {"reliability_order": 3, "description": "Label based on documented repository/release evidence."},
    "multi_analyst_manual_review": {"reliability_order": 3, "description": "Independent reviewers agreed or adjudicated the label."},
    "single_reviewer_provisional": {"reliability_order": 2, "description": "Single-reviewer provisional label requiring caution."},
    "unknown": {"reliability_order": 0, "description": "No defensible label source."},
}

LABEL_REVIEW_STATUSES = {"unreviewed", "provisional", "reviewed", "adjudicated", "excluded"}


def is_valid_label(label: str) -> bool:
    return label in LABEL_ONTOLOGY


def is_valid_label_source(label_source: str) -> bool:
    return label_source in LABEL_SOURCE_CATEGORIES
