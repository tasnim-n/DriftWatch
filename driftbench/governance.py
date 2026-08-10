from __future__ import annotations

SOURCE_CATEGORIES = {
    "real_public",
    "research_dataset",
    "open_source_repository",
    "controlled",
    "unknown/unverified",
}

ACCEPTABLE_SOURCE_CATEGORIES = {
    "real_public",
    "research_dataset",
    "open_source_repository",
    "controlled",
}

LICENSE_STATUSES = {
    "allowed",
    "research_only",
    "redistribution_restricted",
    "unknown",
    "disallowed",
}

QUARANTINE_LICENSE_STATUSES = {"unknown", "disallowed"}

DATASET_STAGES = {
    "INCOMING",
    "VALIDATED",
    "REVIEWED",
    "ACCEPTED",
    "QUARANTINED",
    "EXCLUDED",
}

DATA_QUALITY_STATUSES = {
    "COMPLETE",
    "PARTIAL",
    "QUESTIONABLE",
    "REJECTED",
}

DRIFTBENCH_VERSION = "0.1.0"


def source_category_is_acceptable(source_type: str) -> bool:
    return source_type in ACCEPTABLE_SOURCE_CATEGORIES


def license_allows_research_dataset(license_status: str) -> bool:
    return license_status in {"allowed", "research_only", "redistribution_restricted"}
