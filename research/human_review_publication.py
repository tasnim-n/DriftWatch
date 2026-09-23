from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from research.human_review_quality_promotion import (
    DEFAULT_SOURCE_HASHES,
    DEFAULT_SOURCE_PATHS,
    PROMOTION_IDS,
    UNCERTAIN_RECORD_ID,
)


PUBLICATION_SCHEMA_VERSION = "driftwatch-human-validation-public-v1"
PUBLICATION_POLICY_VERSION = "driftwatch-human-validation-publication-v1"
PRIVACY_CLASSIFICATION = "PUBLIC_SAFE_AGGREGATE"

DEFAULT_AGREEMENT_SOURCE = Path(
    "artifacts/human_review/agreement/reviewer01_vs_reviewer02/agreement_summary.json"
)
DEFAULT_ADJUDICATION_SOURCE = Path(
    "artifacts/human_review/adjudication/final/human_validation_summary.json"
)
DEFAULT_COMPARISON_SOURCE = Path(
    "artifacts/human_review/adjudication/final/stage_a_to_stage_b_comparison.json"
)
DEFAULT_PUBLIC_ROOT = Path("artifacts/human_review/public_validation")
DEFAULT_GOLD_MANIFEST = Path(
    "artifacts/human_review/gold_set/driftwatch-human-gold-set-v1/gold_set_manifest.json"
)

EXPECTED_SOURCE_HASHES = {
    "agreement_aggregate": "369FFA3352E11542574618EBEECD3095271DA7DCDA4029E79C0231C3C5D10089",
    "adjudication_aggregate": "076ED1350680853540184CC22208CA53ACCE548D0C4ED241EF1714AD8C8354B2",
    "stage_comparison": "A94A77E84E5596F95CA3FCC5C5EEC1A008CDA53DB749CC28A801AC578B548D8E",
}

PUBLIC_ARCHIVE_HASH_NAMES = {
    "reviewer01_raw_zip": "review_1_raw_archive",
    "reviewer02_raw_zip": "review_2_raw_archive",
    "stage_a_raw_zip": "adjudication_stage_a_raw_archive",
    "stage_b_released_package": "adjudication_stage_b_released_package",
    "stage_b_raw_return": "adjudication_stage_b_raw_archive",
}

AGREEMENT_SOURCE_KEYS = {
    "schema_version",
    "mapping_version",
    "review_id_policy_version",
    "case_set",
    "total_common_cases",
    "comparable_cases",
    "not_comparable_cases",
    "exact_agreements",
    "disagreements",
    "percent_exact_agreement",
    "mapped_label_cross_tabulation",
    "cohens_kappa",
    "methodological_status",
}
CASE_SET_KEYS = {
    "reviewer01_count",
    "reviewer02_count",
    "common_record_count",
    "missing_from_reviewer02",
    "extra_in_reviewer02",
    "external_holdout_overlap",
    "case_sets_identical",
}
CROSS_TAB_KEYS = {"row_dimension", "column_dimension", "categories", "matrix"}
KAPPA_SOURCE_KEYS = {
    "status",
    "method",
    "formula",
    "comparable_count",
    "observed_agreement",
    "expected_agreement",
    "cohens_kappa",
    "reviewer01_marginals",
    "reviewer02_marginals",
    "limitations",
}
ADJUDICATION_SOURCE_KEYS = {
    "schema_version",
    "original_blind_cases",
    "independent_reviewers",
    "exact_human_human_agreements",
    "human_human_disagreements",
    "percent_exact_agreement",
    "percent_exact_agreement_display",
    "nominal_unweighted_cohens_kappa",
    "disagreement_cases_entering_adjudication",
    "stage_a_complete",
    "stage_b_complete",
    "stage_a_labels_changed_in_stage_b",
    "final_adjudicated_benign",
    "final_adjudicated_risky",
    "final_adjudicated_uncertain",
    "gold_set_created",
    "limitations",
}
COMPARISON_SOURCE_KEYS = {
    "schema_version",
    "record_count",
    "retained_stage_a_label_count",
    "changed_stage_a_label_count",
    "records",
}
COMPARISON_RECORD_KEYS = {
    "record_id",
    "stage_a_label",
    "stage_a_confidence",
    "stage_b_final_label",
    "stage_b_confidence",
    "changed",
    "reported_initial_label_changed",
    "change_reason",
    "resolution_basis",
    "stage_a_source_sha256",
    "stage_b_source_sha256",
}

PRIVACY_NOTICE = (
    "Raw review submissions, human rationale, evidence references, identity mappings, "
    "and detailed adjudication records are retained privately and are not included."
)
AGREEMENT_LIMITATIONS = (
    "The scoped review set contains 14 cases.",
    "The statistic is descriptive of this review set and is not an accuracy measure.",
    "Cohen's kappa is sensitive to concentrated and imbalanced category marginals.",
    "No weighted kappa is reported because the governed label ontology is not ordinal.",
)
ADJUDICATION_LIMITATIONS = (
    "The final labels are governed human-review outcomes, not malware ground truth.",
    "The public artifact supports aggregate verification but intentionally omits private human reasoning.",
)
MANIFEST_LIMITATIONS = (
    "A clean clone can verify the published aggregates and their internal consistency.",
    "A clean clone cannot reconstruct the intentionally withheld raw human reasoning.",
    "The governed Gold Set is a validation subset and is not malware ground truth.",
)
SUPPORTED_CLAIMS = (
    "Two independent reviewers assessed the same 14-case blind review set.",
    "Exact agreement was 9 of 14 (64.29%), with nominal unweighted Cohen kappa 0.3396226415.",
    "Five disagreements entered adjudication; four resolved as RISKY_TRANSITION and one as UNCERTAIN.",
    "No Stage A label changed in Stage B, and four governed risky cases form the Gold Set.",
)

PROHIBITED_KEY_FRAGMENTS = {
    "rationale",
    "resolution_basis",
    "change_reason",
    "evidence_reference",
    "reviewer_id",
    "adjudicator_id",
    "alias_mapping",
    "private_notes",
    "verbatim",
    "password",
    "api_key",
    "access_token",
    "token",
    "secret",
}
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
WINDOWS_PATH_RE = re.compile(r"(?i)(?:^|[\s'\"])[A-Z]:\\")
PRIVATE_UNIX_PATH_RE = re.compile(r"(?:^|[\s'\"])/(?:home|Users)/")
PRIVATE_ID_RE = re.compile(
    r"(?i)\b(?:human[_-]?reviewer[_-]?\d+|reviewer0?\d+|reviewer\s+[AB]|adjudicator[_-]?\d+)\b"
)


class HumanReviewPublicationError(ValueError):
    """Raised when public human-validation evidence cannot fail closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HumanReviewPublicationError(message)


def _read_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HumanReviewPublicationError(f"cannot read JSON object {path}: {exc}") from exc
    _require(isinstance(payload, dict), f"JSON object required in {path}")
    return payload


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _require_exact_keys(value: Mapping[str, Any], allowed: set[str], source: str) -> None:
    actual = set(value)
    _require(actual == allowed, f"{source} fields differ: {sorted(actual ^ allowed)}")


def _require_number(value: Any, source: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{source} must be numeric")
    return float(value)


def _validate_source_schemas(
    agreement: Mapping[str, Any],
    adjudication: Mapping[str, Any],
    comparison: Mapping[str, Any],
) -> None:
    _require_exact_keys(agreement, AGREEMENT_SOURCE_KEYS, "agreement source")
    case_set = agreement.get("case_set")
    cross_tab = agreement.get("mapped_label_cross_tabulation")
    kappa = agreement.get("cohens_kappa")
    _require(isinstance(case_set, dict), "agreement case_set must be an object")
    _require(isinstance(cross_tab, dict), "agreement cross-tabulation must be an object")
    _require(isinstance(kappa, dict), "agreement kappa must be an object")
    _require_exact_keys(case_set, CASE_SET_KEYS, "agreement case_set")
    _require_exact_keys(cross_tab, CROSS_TAB_KEYS, "agreement cross-tabulation")
    _require_exact_keys(kappa, KAPPA_SOURCE_KEYS, "agreement kappa")

    categories = cross_tab.get("categories")
    matrix = cross_tab.get("matrix")
    _require(isinstance(categories, list) and all(isinstance(x, str) for x in categories), "invalid categories")
    _require(isinstance(matrix, dict) and set(matrix) == set(categories), "invalid cross-tabulation rows")
    for category in categories:
        row = matrix[category]
        _require(isinstance(row, dict) and set(row) == set(categories), "invalid cross-tabulation columns")
        _require(all(isinstance(v, int) and v >= 0 for v in row.values()), "invalid cross-tabulation count")

    for key in ("reviewer01_marginals", "reviewer02_marginals"):
        marginals = kappa.get(key)
        _require(isinstance(marginals, dict), f"{key} must be an object")
        _require(all(isinstance(k, str) and isinstance(v, int) and v >= 0 for k, v in marginals.items()), f"invalid {key}")

    _require_exact_keys(adjudication, ADJUDICATION_SOURCE_KEYS, "adjudication source")
    _require_exact_keys(comparison, COMPARISON_SOURCE_KEYS, "comparison source")
    records = comparison.get("records")
    _require(isinstance(records, list), "comparison records must be a list")
    for index, record in enumerate(records):
        _require(isinstance(record, dict), f"comparison record {index} must be an object")
        _require_exact_keys(record, COMPARISON_RECORD_KEYS, f"comparison record {index}")


def _derive_agreement(agreement: Mapping[str, Any]) -> dict[str, Any]:
    case_set = agreement["case_set"]
    kappa = agreement["cohens_kappa"]
    cross_tab = agreement["mapped_label_cross_tabulation"]
    categories = cross_tab["categories"]
    matrix = cross_tab["matrix"]

    case_count = agreement["total_common_cases"]
    exact = agreement["exact_agreements"]
    disagreements = agreement["disagreements"]
    _require(isinstance(case_count, int) and case_count > 0, "invalid agreement case count")
    _require(isinstance(exact, int) and isinstance(disagreements, int), "invalid agreement counts")
    _require(exact + disagreements == case_count, "agreement counts do not sum to the case count")
    _require(agreement["comparable_cases"] == case_count, "not all agreement cases are comparable")
    _require(agreement["not_comparable_cases"] == 0, "agreement source contains non-comparable cases")
    _require(case_set["common_record_count"] == case_count, "agreement case-set count differs")
    _require(case_set["reviewer01_count"] == case_count and case_set["reviewer02_count"] == case_count, "review set sizes differ")
    _require(case_set["case_sets_identical"] is True, "review case sets are not identical")
    _require(not case_set["missing_from_reviewer02"] and not case_set["extra_in_reviewer02"], "review case sets differ")
    _require(not case_set["external_holdout_overlap"], "review set overlaps external holdout")

    row_marginals = {category: sum(matrix[category].values()) for category in categories}
    column_marginals = {
        category: sum(matrix[row][category] for row in categories) for category in categories
    }
    row_marginals = {key: value for key, value in row_marginals.items() if value}
    column_marginals = {key: value for key, value in column_marginals.items() if value}
    _require(row_marginals == kappa["reviewer01_marginals"], "review 1 marginals differ from cross-tabulation")
    _require(column_marginals == kappa["reviewer02_marginals"], "review 2 marginals differ from cross-tabulation")
    _require(sum(row_marginals.values()) == case_count, "review 1 marginals do not sum")
    _require(sum(column_marginals.values()) == case_count, "review 2 marginals do not sum")

    observed = exact / case_count
    expected = sum(
        row_marginals.get(category, 0) * column_marginals.get(category, 0)
        for category in categories
    ) / (case_count * case_count)
    calculated_kappa = (observed - expected) / (1 - expected)
    _require(math.isclose(observed, _require_number(kappa["observed_agreement"], "observed agreement"), abs_tol=1e-15), "observed agreement differs")
    _require(math.isclose(expected, _require_number(kappa["expected_agreement"], "expected agreement"), abs_tol=1e-15), "expected agreement differs")
    _require(math.isclose(calculated_kappa, _require_number(kappa["cohens_kappa"], "Cohen kappa"), abs_tol=1e-15), "Cohen kappa differs")
    _require(math.isclose(agreement["percent_exact_agreement"], observed * 100, abs_tol=1e-12), "agreement percentage differs")

    return {
        "schema_version": PUBLICATION_SCHEMA_VERSION,
        "artifact_type": "HUMAN_REVIEW_AGREEMENT_SUMMARY",
        "derivation_policy_version": PUBLICATION_POLICY_VERSION,
        "privacy_classification": PRIVACY_CLASSIFICATION,
        "raw_human_text_included": False,
        "review_set": {
            "blind_case_count": case_count,
            "independent_reviewer_count": len(("reviewer01", "reviewer02")),
            "case_sets_identical": True,
            "external_holdout_overlap_count": 0,
        },
        "agreement": {
            "exact_agreements": exact,
            "disagreements": disagreements,
            "exact_agreement_fraction": observed,
            "exact_agreement_percent": round(observed * 100, 2),
            "observed_agreement": observed,
            "expected_agreement": expected,
            "cohens_kappa": calculated_kappa,
            "method": "UNWEIGHTED_NOMINAL",
        },
        "label_distributions": {
            "review_1": row_marginals,
            "review_2": column_marginals,
        },
        "privacy_notice": PRIVACY_NOTICE,
        "limitations": list(AGREEMENT_LIMITATIONS),
    }


def _derive_adjudication(
    adjudication: Mapping[str, Any], comparison: Mapping[str, Any]
) -> dict[str, Any]:
    records = comparison["records"]
    case_count = adjudication["disagreement_cases_entering_adjudication"]
    _require(isinstance(case_count, int) and case_count == len(records), "adjudication case count differs")
    _require(comparison["record_count"] == case_count, "comparison record count differs")
    _require(adjudication["stage_a_complete"] is True and adjudication["stage_b_complete"] is True, "adjudication is incomplete")

    public_records: list[dict[str, str]] = []
    changed_count = 0
    label_counts = {"BENIGN_TRANSITION": 0, "RISKY_TRANSITION": 0, "UNCERTAIN": 0}
    seen: set[str] = set()
    for record in records:
        record_id = record["record_id"]
        final_label = record["stage_b_final_label"]
        changed = record["changed"]
        _require(isinstance(record_id, str) and record_id and record_id not in seen, "invalid or duplicate adjudication record ID")
        _require(final_label in label_counts, f"unexpected final label for {record_id}")
        _require(isinstance(changed, bool), f"invalid changed flag for {record_id}")
        _require(changed == (record["stage_a_label"] != final_label), f"changed flag differs for {record_id}")
        seen.add(record_id)
        changed_count += int(changed)
        label_counts[final_label] += 1
        public_records.append({"record_id": record_id, "final_label": final_label})

    expected_ids = set(PROMOTION_IDS) | {UNCERTAIN_RECORD_ID}
    _require(seen == expected_ids, "adjudication record set differs")
    _require(changed_count == comparison["changed_stage_a_label_count"], "comparison changed count differs")
    _require(changed_count == adjudication["stage_a_labels_changed_in_stage_b"], "summary changed count differs")
    _require(comparison["retained_stage_a_label_count"] + changed_count == case_count, "comparison retention counts do not sum")
    _require(label_counts["BENIGN_TRANSITION"] == adjudication["final_adjudicated_benign"], "benign count differs")
    _require(label_counts["RISKY_TRANSITION"] == adjudication["final_adjudicated_risky"], "risky count differs")
    _require(label_counts["UNCERTAIN"] == adjudication["final_adjudicated_uncertain"], "uncertain count differs")

    return {
        "schema_version": PUBLICATION_SCHEMA_VERSION,
        "artifact_type": "HUMAN_ADJUDICATION_SUMMARY",
        "derivation_policy_version": PUBLICATION_POLICY_VERSION,
        "privacy_classification": PRIVACY_CLASSIFICATION,
        "raw_human_text_included": False,
        "workflow": {
            "cases_entering_adjudication": case_count,
            "stage_a_complete": True,
            "stage_b_complete": True,
            "stage_a_to_stage_b_changed_count": changed_count,
        },
        "final_label_distribution": label_counts,
        "records": sorted(public_records, key=lambda row: row["record_id"]),
        "privacy_notice": PRIVACY_NOTICE,
        "limitations": list(ADJUDICATION_LIMITATIONS),
    }


def _validate_public_privacy(payload: Any, location: str = "$") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = str(key).lower()
            for fragment in PROHIBITED_KEY_FRAGMENTS:
                _require(fragment not in normalized, f"prohibited public field {location}.{key}")
            _validate_public_privacy(value, f"{location}.{key}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            _validate_public_privacy(value, f"{location}[{index}]")
    elif isinstance(payload, str):
        _require(not EMAIL_RE.search(payload), f"email address found at {location}")
        _require(not WINDOWS_PATH_RE.search(payload), f"Windows path found at {location}")
        _require(not PRIVATE_UNIX_PATH_RE.search(payload), f"private Unix path found at {location}")
        _require(not PRIVATE_ID_RE.search(payload), f"private human identifier found at {location}")


def _require_public_schema(agreement: Mapping[str, Any], adjudication: Mapping[str, Any]) -> None:
    _require_exact_keys(
        agreement,
        {
            "schema_version", "artifact_type", "derivation_policy_version",
            "privacy_classification", "raw_human_text_included", "review_set",
            "agreement", "label_distributions", "privacy_notice", "limitations",
        },
        "public agreement artifact",
    )
    _require_exact_keys(
        agreement["review_set"],
        {"blind_case_count", "independent_reviewer_count", "case_sets_identical", "external_holdout_overlap_count"},
        "public agreement review_set",
    )
    _require_exact_keys(
        agreement["agreement"],
        {"exact_agreements", "disagreements", "exact_agreement_fraction", "exact_agreement_percent", "observed_agreement", "expected_agreement", "cohens_kappa", "method"},
        "public agreement statistics",
    )
    _require_exact_keys(agreement["label_distributions"], {"review_1", "review_2"}, "public label distributions")
    for key in ("review_1", "review_2"):
        _require(isinstance(agreement["label_distributions"][key], dict), f"{key} distribution must be an object")
        _require(set(agreement["label_distributions"][key]) <= {"benign_transition", "risky_transition", "malicious_transition", "uncertain", "excluded"}, f"unexpected {key} label")

    _require_exact_keys(
        adjudication,
        {
            "schema_version", "artifact_type", "derivation_policy_version",
            "privacy_classification", "raw_human_text_included", "workflow",
            "final_label_distribution", "records", "privacy_notice", "limitations",
        },
        "public adjudication artifact",
    )
    _require_exact_keys(
        adjudication["workflow"],
        {"cases_entering_adjudication", "stage_a_complete", "stage_b_complete", "stage_a_to_stage_b_changed_count"},
        "public adjudication workflow",
    )
    _require_exact_keys(adjudication["final_label_distribution"], {"BENIGN_TRANSITION", "RISKY_TRANSITION", "UNCERTAIN"}, "public adjudication labels")
    _require(isinstance(adjudication["records"], list), "public adjudication records must be a list")
    for index, record in enumerate(adjudication["records"]):
        _require(isinstance(record, dict), f"public adjudication record {index} must be an object")
        _require_exact_keys(record, {"record_id", "final_label"}, f"public adjudication record {index}")

    for payload, artifact_type, limitations in (
        (agreement, "HUMAN_REVIEW_AGREEMENT_SUMMARY", AGREEMENT_LIMITATIONS),
        (adjudication, "HUMAN_ADJUDICATION_SUMMARY", ADJUDICATION_LIMITATIONS),
    ):
        _require(payload["schema_version"] == PUBLICATION_SCHEMA_VERSION, "public schema version differs")
        _require(payload["artifact_type"] == artifact_type, "public artifact type differs")
        _require(payload["derivation_policy_version"] == PUBLICATION_POLICY_VERSION, "public derivation policy differs")
        _require(payload["privacy_classification"] == PRIVACY_CLASSIFICATION, "public privacy classification differs")
        _require(payload["raw_human_text_included"] is False, "public artifact claims to include raw human text")
        _require(payload["privacy_notice"] == PRIVACY_NOTICE, "public privacy notice differs")
        _require(payload["limitations"] == list(limitations), "public limitations differ")
        _validate_public_privacy(payload)


def _verify_arithmetic(agreement: Mapping[str, Any], adjudication: Mapping[str, Any]) -> None:
    review_set = agreement["review_set"]
    stats = agreement["agreement"]
    count = review_set["blind_case_count"]
    _require(count == 14 and review_set["independent_reviewer_count"] == 2, "public review-set claims differ")
    _require(stats["exact_agreements"] + stats["disagreements"] == count, "public agreement counts do not sum")
    observed = stats["exact_agreements"] / count
    _require(math.isclose(stats["exact_agreement_fraction"], observed, abs_tol=1e-15), "public agreement fraction differs")
    _require(stats["exact_agreement_percent"] == round(observed * 100, 2), "public agreement percentage differs")
    _require(math.isclose(stats["observed_agreement"], observed, abs_tol=1e-15), "public observed agreement differs")
    distributions = agreement["label_distributions"]
    expected = sum(
        distributions["review_1"].get(label, 0) * distributions["review_2"].get(label, 0)
        for label in set(distributions["review_1"]) | set(distributions["review_2"])
    ) / (count * count)
    _require(math.isclose(stats["expected_agreement"], expected, abs_tol=1e-15), "public expected agreement differs")
    kappa = (observed - expected) / (1 - expected)
    _require(math.isclose(stats["cohens_kappa"], kappa, abs_tol=1e-15), "public Cohen kappa differs")
    _require(stats["method"] == "UNWEIGHTED_NOMINAL", "public kappa method differs")

    workflow = adjudication["workflow"]
    counts = adjudication["final_label_distribution"]
    _require(workflow["cases_entering_adjudication"] == 5, "public adjudication case count differs")
    _require(workflow["stage_a_complete"] is True and workflow["stage_b_complete"] is True, "public adjudication is incomplete")
    _require(workflow["stage_a_to_stage_b_changed_count"] == 0, "public adjudication changed count differs")
    _require(sum(counts.values()) == 5, "public adjudication labels do not sum")
    _require(counts == {"BENIGN_TRANSITION": 0, "RISKY_TRANSITION": 4, "UNCERTAIN": 1}, "public adjudication distribution differs")
    records = adjudication["records"]
    record_ids = {record["record_id"] for record in records}
    _require(len(record_ids) == len(records), "duplicate public adjudication record")
    _require(record_ids == set(PROMOTION_IDS) | {UNCERTAIN_RECORD_ID}, "public adjudication record set differs")
    by_id = {record["record_id"]: record["final_label"] for record in records}
    _require(all(by_id[record_id] == "RISKY_TRANSITION" for record_id in PROMOTION_IDS), "promoted record label differs")
    _require(by_id[UNCERTAIN_RECORD_ID] == "UNCERTAIN", "uncertain record label differs")


def _build_manifest(
    agreement: Mapping[str, Any],
    adjudication: Mapping[str, Any],
    source_aggregate_hashes: Mapping[str, str],
    source_archive_hashes: Mapping[str, str],
    gold_manifest_path: str | Path,
) -> dict[str, Any]:
    gold_path = Path(gold_manifest_path)
    gold = _read_json(gold_path)
    gold_records = gold.get("records")
    _require(isinstance(gold_records, list), "Gold Set records must be a list")
    gold_ids = sorted(record.get("record_id") for record in gold_records if isinstance(record, dict))
    _require(gold_ids == sorted(PROMOTION_IDS), "Gold Set record set differs from adjudicated risky records")
    _require(gold.get("record_count") == len(PROMOTION_IDS), "Gold Set count differs")

    manifest = {
        "schema_version": PUBLICATION_SCHEMA_VERSION,
        "artifact_type": "HUMAN_VALIDATION_PUBLIC_MANIFEST",
        "derivation_policy_version": PUBLICATION_POLICY_VERSION,
        "privacy_classification": PRIVACY_CLASSIFICATION,
        "source_aggregate_sha256": dict(sorted(source_aggregate_hashes.items())),
        "source_archive_sha256": dict(sorted(source_archive_hashes.items())),
        "public_artifact_sha256": {
            "agreement_summary_public.json": _sha256_bytes(_json_bytes(agreement)),
            "adjudication_summary_public.json": _sha256_bytes(_json_bytes(adjudication)),
        },
        "gold_set_linkage": {
            "manifest_path": str(gold_path.as_posix()),
            "manifest_sha256": sha256_file(gold_path),
            "record_count": len(gold_ids),
            "record_ids": gold_ids,
        },
        "claims_supported": list(SUPPORTED_CLAIMS),
        "privacy_notice": PRIVACY_NOTICE,
        "limitations": list(MANIFEST_LIMITATIONS),
        "clean_clone_verification_command": ".venv/Scripts/python.exe -m research.human_review_publication verify",
    }
    _validate_public_privacy(manifest)
    return manifest


def _require_manifest_schema(manifest: Mapping[str, Any]) -> None:
    _require_exact_keys(
        manifest,
        {
            "schema_version", "artifact_type", "derivation_policy_version",
            "privacy_classification", "source_aggregate_sha256", "source_archive_sha256",
            "public_artifact_sha256", "gold_set_linkage", "claims_supported",
            "privacy_notice", "limitations", "clean_clone_verification_command",
        },
        "public validation manifest",
    )
    _require_exact_keys(manifest["source_aggregate_sha256"], set(EXPECTED_SOURCE_HASHES), "manifest aggregate hashes")
    _require_exact_keys(manifest["source_archive_sha256"], set(PUBLIC_ARCHIVE_HASH_NAMES.values()), "manifest archive hashes")
    _require_exact_keys(manifest["public_artifact_sha256"], {"agreement_summary_public.json", "adjudication_summary_public.json"}, "manifest public hashes")
    _require_exact_keys(manifest["gold_set_linkage"], {"manifest_path", "manifest_sha256", "record_count", "record_ids"}, "manifest Gold Set linkage")
    _require(manifest["schema_version"] == PUBLICATION_SCHEMA_VERSION, "manifest schema differs")
    _require(manifest["artifact_type"] == "HUMAN_VALIDATION_PUBLIC_MANIFEST", "manifest artifact type differs")
    _require(manifest["derivation_policy_version"] == PUBLICATION_POLICY_VERSION, "manifest policy differs")
    _require(manifest["privacy_classification"] == PRIVACY_CLASSIFICATION, "manifest privacy classification differs")
    _require(manifest["privacy_notice"] == PRIVACY_NOTICE, "manifest privacy notice differs")
    _require(manifest["claims_supported"] == list(SUPPORTED_CLAIMS), "manifest supported claims differ")
    _require(manifest["limitations"] == list(MANIFEST_LIMITATIONS), "manifest limitations differ")
    _require(manifest["clean_clone_verification_command"] == ".venv/Scripts/python.exe -m research.human_review_publication verify", "manifest verification command differs")
    _validate_public_privacy(manifest)


def generate_publication_layer(
    *,
    agreement_source: str | Path = DEFAULT_AGREEMENT_SOURCE,
    adjudication_source: str | Path = DEFAULT_ADJUDICATION_SOURCE,
    comparison_source: str | Path = DEFAULT_COMPARISON_SOURCE,
    source_paths: Mapping[str, str | Path] = DEFAULT_SOURCE_PATHS,
    public_root: str | Path = DEFAULT_PUBLIC_ROOT,
    gold_manifest_path: str | Path = DEFAULT_GOLD_MANIFEST,
) -> dict[str, str]:
    aggregate_paths = {
        "agreement_aggregate": Path(agreement_source),
        "adjudication_aggregate": Path(adjudication_source),
        "stage_comparison": Path(comparison_source),
    }
    actual_aggregate_hashes = {name: sha256_file(path) for name, path in aggregate_paths.items()}
    _require(actual_aggregate_hashes == EXPECTED_SOURCE_HASHES, "authoritative aggregate hashes differ")
    _require(set(source_paths) == set(DEFAULT_SOURCE_HASHES), "authoritative archive source set differs")
    actual_archive_hashes: dict[str, str] = {}
    for private_name, expected_hash in DEFAULT_SOURCE_HASHES.items():
        actual = sha256_file(source_paths[private_name])
        _require(actual == expected_hash, f"authoritative archive hash differs: {private_name}")
        actual_archive_hashes[PUBLIC_ARCHIVE_HASH_NAMES[private_name]] = actual

    source_agreement = _read_json(agreement_source)
    source_adjudication = _read_json(adjudication_source)
    source_comparison = _read_json(comparison_source)
    _validate_source_schemas(source_agreement, source_adjudication, source_comparison)
    agreement = _derive_agreement(source_agreement)
    adjudication = _derive_adjudication(source_adjudication, source_comparison)
    _require_public_schema(agreement, adjudication)
    _verify_arithmetic(agreement, adjudication)
    manifest = _build_manifest(
        agreement,
        adjudication,
        actual_aggregate_hashes,
        actual_archive_hashes,
        gold_manifest_path,
    )
    _require_manifest_schema(manifest)

    root = Path(public_root)
    root.mkdir(parents=True, exist_ok=True)
    outputs = {
        "agreement_summary_public.json": agreement,
        "adjudication_summary_public.json": adjudication,
        "human_validation_public_manifest.json": manifest,
    }
    for filename, payload in outputs.items():
        path = root / filename
        encoded = _json_bytes(payload)
        if path.exists():
            _require(path.read_bytes() == encoded, f"refusing to overwrite non-deterministic output: {path}")
        else:
            path.write_bytes(encoded)
    return {filename: sha256_file(root / filename) for filename in outputs}


def verify_publication_layer(
    *,
    public_root: str | Path = DEFAULT_PUBLIC_ROOT,
    gold_manifest_path: str | Path = DEFAULT_GOLD_MANIFEST,
) -> dict[str, Any]:
    root = Path(public_root)
    expected_files = {
        "agreement_summary_public.json",
        "adjudication_summary_public.json",
        "human_validation_public_manifest.json",
    }
    actual_files = {path.name for path in root.iterdir() if path.is_file()} if root.is_dir() else set()
    _require(actual_files == expected_files, f"public validation file set differs: {sorted(actual_files ^ expected_files)}")
    agreement = _read_json(root / "agreement_summary_public.json")
    adjudication = _read_json(root / "adjudication_summary_public.json")
    manifest = _read_json(root / "human_validation_public_manifest.json")
    _require_public_schema(agreement, adjudication)
    _require_manifest_schema(manifest)
    _verify_arithmetic(agreement, adjudication)

    for filename in ("agreement_summary_public.json", "adjudication_summary_public.json"):
        _require(
            sha256_file(root / filename) == manifest["public_artifact_sha256"][filename],
            f"public artifact hash differs: {filename}",
        )
    _require(manifest["source_aggregate_sha256"] == EXPECTED_SOURCE_HASHES, "manifest aggregate provenance differs")
    expected_archive_hashes = {
        PUBLIC_ARCHIVE_HASH_NAMES[name]: digest for name, digest in DEFAULT_SOURCE_HASHES.items()
    }
    _require(manifest["source_archive_sha256"] == dict(sorted(expected_archive_hashes.items())), "manifest archive provenance differs")

    gold_path = Path(gold_manifest_path)
    gold = _read_json(gold_path)
    linkage = manifest["gold_set_linkage"]
    _require(linkage["manifest_path"] == str(gold_path.as_posix()), "Gold Set manifest path differs")
    _require(linkage["manifest_sha256"] == sha256_file(gold_path), "Gold Set manifest hash differs")
    gold_records = gold.get("records")
    _require(isinstance(gold_records, list), "Gold Set records must be a list")
    gold_ids = sorted(record.get("record_id") for record in gold_records if isinstance(record, dict))
    _require(linkage["record_count"] == gold.get("record_count") == 4, "Gold Set count differs")
    _require(linkage["record_ids"] == gold_ids == sorted(PROMOTION_IDS), "Gold Set record linkage differs")

    return {
        "status": "VERIFIED",
        "public_artifact_count": len(expected_files),
        "blind_case_count": agreement["review_set"]["blind_case_count"],
        "exact_agreements": agreement["agreement"]["exact_agreements"],
        "disagreements": agreement["agreement"]["disagreements"],
        "adjudication_case_count": adjudication["workflow"]["cases_entering_adjudication"],
        "gold_set_record_count": linkage["record_count"],
        "private_sources_required": False,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate or verify public human-validation evidence")
    parser.add_argument("command", choices=("generate", "verify"))
    parser.add_argument("--public-root", default=str(DEFAULT_PUBLIC_ROOT))
    parser.add_argument("--gold-manifest", default=str(DEFAULT_GOLD_MANIFEST))
    parser.add_argument("--agreement-source", default=str(DEFAULT_AGREEMENT_SOURCE))
    parser.add_argument("--adjudication-source", default=str(DEFAULT_ADJUDICATION_SOURCE))
    parser.add_argument("--comparison-source", default=str(DEFAULT_COMPARISON_SOURCE))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "generate":
        result: Mapping[str, Any] = generate_publication_layer(
            agreement_source=args.agreement_source,
            adjudication_source=args.adjudication_source,
            comparison_source=args.comparison_source,
            public_root=args.public_root,
            gold_manifest_path=args.gold_manifest,
        )
    else:
        result = verify_publication_layer(
            public_root=args.public_root,
            gold_manifest_path=args.gold_manifest,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
