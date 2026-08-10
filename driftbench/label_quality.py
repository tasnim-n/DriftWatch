from __future__ import annotations

from enum import Enum
from typing import Iterable, Sequence

from driftbench.labels import Label


class LabelQualityTier(str, Enum):
    CONTROLLED_GROUND_TRUTH = "CONTROLLED_GROUND_TRUTH"
    EXTERNAL_CONFIRMED = "EXTERNAL_CONFIRMED"
    MULTI_REVIEWER_ADJUDICATED = "MULTI_REVIEWER_ADJUDICATED"
    SINGLE_REVIEWER_PROVISIONAL = "SINGLE_REVIEWER_PROVISIONAL"
    UNCERTAIN = "UNCERTAIN"


LABEL_QUALITY_TIERS = {tier.value for tier in LabelQualityTier}

SUPERVISED_LABELS = {
    Label.BENIGN.value,
    Label.RISKY.value,
    Label.MALICIOUS_TRANSITION.value,
}


def is_valid_label_quality_tier(value: str) -> bool:
    return value in LABEL_QUALITY_TIERS


def infer_label_quality_tier(
    *,
    label: str,
    label_source: str,
    review_status: str,
    explicit_tier: str | None = None,
) -> str:
    if explicit_tier:
        if not is_valid_label_quality_tier(explicit_tier):
            raise ValueError(f"invalid label_quality_tier {explicit_tier!r}")
        return explicit_tier

    if label in {Label.UNCERTAIN.value, Label.NEEDS_REVIEW.value, Label.EXCLUDED.value}:
        return LabelQualityTier.UNCERTAIN.value
    if label_source == "controlled_ground_truth":
        return LabelQualityTier.CONTROLLED_GROUND_TRUTH.value
    if label_source in {"peer_reviewed_dataset_label", "reputable_security_report"}:
        return LabelQualityTier.EXTERNAL_CONFIRMED.value
    if label_source == "multi_analyst_manual_review" or review_status == "adjudicated":
        return LabelQualityTier.MULTI_REVIEWER_ADJUDICATED.value
    return LabelQualityTier.SINGLE_REVIEWER_PROVISIONAL.value


def eligible_for_supervised_training(
    *,
    label: str,
    label_quality_tier: str,
    provenance_complete: bool,
    validation_stage: str = "ACCEPTED",
    explicit_eligible: bool | None = None,
) -> bool:
    if explicit_eligible is False:
        return False
    if validation_stage != "ACCEPTED":
        return False
    if not provenance_complete:
        return False
    if label not in SUPERVISED_LABELS:
        return False
    if label_quality_tier == LabelQualityTier.UNCERTAIN.value:
        return False
    return True if explicit_eligible is None else bool(explicit_eligible)


def count_values(values: Iterable[str | None]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = value or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def supervised_label_distribution(records: Sequence) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        if getattr(record, "eligible_for_supervised_training", False):
            label = getattr(record, "label", "unknown")
            counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))
