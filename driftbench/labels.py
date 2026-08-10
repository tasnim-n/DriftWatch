from enum import Enum
from typing import Dict, Any


class Label(str, Enum):
    BENIGN = "benign_transition"
    RISKY = "risky_transition"
    CONTROLLED_MALICIOUS = "controlled_malicious_transition"
    NEEDS_REVIEW = "needs_review"


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
}


def is_valid_label(label: str) -> bool:
    return label in LABEL_ONTOLOGY
